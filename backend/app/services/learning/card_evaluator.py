"""
Card Answer Evaluation Service

LLM-powered evaluation of learner answers to spaced repetition cards.
Converts free-text answers into FSRS ratings (1-4) for active recall learning.

Unlike passive "flip and rate" cards, this evaluator:
1. Takes the user's typed answer
2. Compares it semantically against the expected answer
3. Returns an FSRS rating and feedback

Rating Mapping:
- AGAIN (1): Answer is incorrect or shows fundamental misunderstanding
- HARD (2): Partially correct but missing key elements or has errors
- GOOD (3): Correct with minor gaps or imprecise wording
- EASY (4): Completely correct with depth and precision
"""

import json
import logging
from typing import Optional

from app.services.llm.client import LLMClient, build_messages, get_default_text_model
from app.enums.learning import Rating
from app.enums.pipeline import PipelineOperation

logger = logging.getLogger(__name__)


CARD_EVALUATION_PROMPT = """You are evaluating a learner's answer to a flashcard question.

QUESTION:
{question}

EXPECTED ANSWER:
{expected_answer}

LEARNER'S ANSWER:
{user_answer}

Evaluate how well the learner's answer matches the expected answer and return a JSON object:
{{
    "rating": <1-4>,
    "is_correct": <true/false>,
    "feedback": "Brief, encouraging feedback explaining the rating",
    "key_points_covered": ["list of key points the learner got right"],
    "key_points_missed": ["list of important points that were missing or wrong"]
}}

Rating Guide (FSRS scale):
- 1 (AGAIN): Completely wrong, major misunderstanding, or blank/irrelevant answer
- 2 (HARD): Partially correct but missing critical elements, or has significant errors  
- 3 (GOOD): Essentially correct answer with minor gaps or less precise wording
- 4 (EASY): Complete, accurate answer demonstrating full understanding

Be fair but rigorous. Focus on semantic correctness, not exact wording.
A paraphrased correct answer should get 3 or 4, not 1 or 2.
"""


class CardAnswerEvaluator:
    """
    LLM-powered evaluation of card answers for active recall.

    This service enables "active recall" mode for spaced repetition cards,
    where learners type their answer instead of just flipping to see it.
    The LLM evaluates the answer and assigns an appropriate FSRS rating.

    Benefits of active recall over passive review:
    - Forces retrieval practice (proven to enhance memory)
    - Provides objective feedback (vs self-rating bias)
    - Identifies specific gaps in understanding
    """

    def __init__(
        self,
        llm_client: LLMClient,
        model: Optional[str] = None,
    ):
        """
        Initialize the card answer evaluator.

        Args:
            llm_client: Configured LLM client instance
            model: Model identifier (defaults to TEXT_MODEL for cost efficiency)
        """
        self.llm = llm_client
        self.model = model or get_default_text_model()

    async def evaluate_answer(
        self,
        question: str,
        expected_answer: str,
        user_answer: str,
    ) -> dict:
        """
        Evaluate a user's answer against the expected answer.

        Args:
            question: The card's front (question/prompt)
            expected_answer: The card's back (correct answer)
            user_answer: What the learner typed

        Returns:
            Dictionary with:
            - rating: int (1-4 FSRS rating)
            - is_correct: bool (rating >= 3)
            - feedback: str (explanation for the learner)
            - key_points_covered: list[str]
            - key_points_missed: list[str]
        """
        # Handle empty or very short answers
        if not user_answer or len(user_answer.strip()) < 3:
            return {
                "rating": Rating.AGAIN.value,
                "is_correct": False,
                "feedback": "Please provide an answer to evaluate.",
                "key_points_covered": [],
                "key_points_missed": ["No answer provided"],
            }

        prompt = CARD_EVALUATION_PROMPT.format(
            question=question,
            expected_answer=expected_answer,
            user_answer=user_answer,
        )

        try:
            messages = build_messages(
                prompt=prompt,
                system_prompt="You are a fair but rigorous evaluator of learning responses. Always return valid JSON.",
            )

            response, _usage = await self.llm.complete(
                operation=PipelineOperation.CONCEPT_EXTRACTION,
                messages=messages,
                model=self.model,
                temperature=0.3,  # Lower temperature for consistent evaluation
                json_mode=True,
            )

            # Response is already parsed when json_mode=True
            result = response if isinstance(response, dict) else json.loads(response)

            # Validate and normalize rating
            rating = result.get("rating", 2)
            if not isinstance(rating, int) or rating < 1 or rating > 4:
                rating = 2  # Default to HARD if invalid

            return {
                "rating": rating,
                "is_correct": rating >= 3,
                "feedback": result.get("feedback", ""),
                "key_points_covered": result.get("key_points_covered", []),
                "key_points_missed": result.get("key_points_missed", []),
            }

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            # Return a safe fallback - assume partial correctness
            return {
                "rating": Rating.HARD.value,
                "is_correct": False,
                "feedback": "Unable to fully evaluate your answer. Please try again.",
                "key_points_covered": [],
                "key_points_missed": [],
            }
        except Exception as e:
            logger.error(f"Card evaluation failed: {e}")
            raise
