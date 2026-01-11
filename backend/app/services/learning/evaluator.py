"""
Response Evaluation Service

LLM-powered evaluation of learner responses to exercises. This service acts as
an intelligent tutor that analyzes student submissions and provides pedagogically
sound feedback to support learning.

The evaluator handles two primary response types:
1. **Text responses**: Free-form explanations, definitions, and conceptual answers
   evaluated against expected key points using semantic understanding.
2. **Code responses**: Programming solutions evaluated through a combination of
   automated test execution and LLM-based code review.

Evaluation outputs include:
- **Covered points**: Key concepts the learner demonstrated understanding of,
  with evidence quotes from their response.
- **Missing points**: Important concepts that were not addressed or were
  inadequately explained.
- **Misconceptions**: Identified errors in understanding with corrections and
  explanations to help the learner course-correct.
- **Score**: Normalized 0-1 score indicating overall quality (0.6+ is "correct").
- **Specific feedback**: Personalized, actionable guidance for improvement.

The evaluation workflow:
1. Receive exercise and learner response
2. Select appropriate evaluation prompt (text vs code)
3. For code: optionally run tests via CodeSandbox first
4. Send to LLM for semantic evaluation
5. Parse structured JSON response
6. Persist attempt record to database
7. Return evaluation with revealed solution

Usage:
    from app.services.learning.evaluator import ResponseEvaluator

    evaluator = ResponseEvaluator(llm_client, db_session)

    result = await evaluator.evaluate_response(
        exercise=exercise,
        request=AttemptSubmitRequest(response="My answer...", confidence_before=3),
    )

    # Result includes score, feedback, and exercise solution
    print(f"Score: {result.score}, Correct: {result.is_correct}")
    print(f"Feedback: {result.feedback}")
"""

import json
import logging
import uuid
from typing import Optional
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import update

from app.db.models_learning import Exercise, ExerciseAttempt
from app.enums.learning import ExerciseType, ExerciseDifficulty
from app.models.learning import (
    AttemptSubmitRequest,
    AttemptEvaluationResponse,
    ExerciseWithSolution,
    CodeExecutionResult,
)
from app.services.llm.client import LLMClient, build_messages, get_default_text_model
from app.enums.pipeline import PipelineOperation

logger = logging.getLogger(__name__)


EVALUATION_PROMPT = """You are evaluating a learner's response to an exercise.

EXERCISE TYPE: {exercise_type}
TOPIC: {topic}
DIFFICULTY: {difficulty}

EXERCISE PROMPT:
{prompt}

EXPECTED KEY POINTS:
{key_points}

LEARNER'S RESPONSE:
{response}

Evaluate the response and return a JSON object with:
{{
    "covered_points": [
        {{"point": "key point text", "evidence": "quote from response showing coverage"}}
    ],
    "missing_points": [
        "key point that was not addressed"
    ],
    "misconceptions": [
        {{"error": "what was wrong", "correction": "what is correct", "explanation": "why"}}
    ],
    "overall_score": 4,  // 1-5 scale
    "specific_feedback": "Personalized feedback for the learner",
    "suggested_review": ["topics to review"]
}}

Scoring guide:
- 5: Excellent - covers all key points accurately with depth
- 4: Good - covers most key points with minor gaps
- 3: Adequate - covers core points but missing important details
- 2: Partial - significant gaps or misconceptions
- 1: Insufficient - major misconceptions or minimal coverage

Be encouraging but honest. Focus on specific improvements."""


CODE_EVALUATION_PROMPT = """You are evaluating a learner's code solution.

EXERCISE TYPE: {exercise_type}
TOPIC: {topic}
DIFFICULTY: {difficulty}
LANGUAGE: {language}

EXERCISE PROMPT:
{prompt}

REFERENCE SOLUTION:
{solution_code}

LEARNER'S CODE:
{response_code}

TEST RESULTS:
{test_results}

Evaluate the code and return a JSON object with:
{{
    "covered_points": [
        {{"point": "concept demonstrated", "evidence": "relevant code snippet"}}
    ],
    "missing_points": [
        "concept or best practice not demonstrated"
    ],
    "misconceptions": [
        {{"error": "code issue", "correction": "how to fix it", "explanation": "why it matters"}}
    ],
    "overall_score": 4,  // 1-5 scale
    "specific_feedback": "Code review style feedback",
    "suggested_review": ["topics to study"]
}}

Scoring guide:
- 5: Excellent - all tests pass, clean idiomatic code, proper error handling, efficient solution
- 4: Good - all/most tests pass, readable code with minor style issues or small inefficiencies
- 3: Adequate - core functionality works, but has notable style issues, missing edge cases, or suboptimal approach
- 2: Partial - some tests fail, logic errors present, or significant code quality issues
- 1: Insufficient - most tests fail, fundamental misunderstanding of the problem or language

Consider:
- Correctness (test results)
- Code style and readability
- Efficiency where relevant
- Proper use of language features
- Edge case handling

Be encouraging but honest. Provide actionable feedback to help the learner improve."""


class ResponseEvaluator:
    """
    LLM-powered response evaluation service.

    This class orchestrates the evaluation of learner responses to exercises,
    combining LLM-based semantic analysis with optional automated testing for
    code exercises. It implements a pedagogically-informed evaluation strategy
    that prioritizes constructive feedback over simple correctness scoring.

    The evaluator supports multiple exercise types:
    - **Conceptual exercises** (explain, define, compare): Evaluated purely via
      LLM analysis against expected key points.
    - **Code exercises** (implement, debug, refactor): Evaluated using a weighted
      combination of test results (70%) and LLM code review (30%).

    Scoring Philosophy:
    - Uses a 0-1 normalized scale derived from a 1-5 rubric
    - 0.6 (60%) threshold for "correct" classification balances rigor with
      encouragement for partial understanding

    Database Integration:
    - Each evaluation creates an ExerciseAttempt record for progress tracking
    - Supports confidence rating capture (before/after) for metacognition analysis
    - Stores structured feedback data (covered_points, misconceptions) as JSON

    Attributes:
        CORRECT_THRESHOLD: Minimum normalized score (0.6) to classify as "correct".
            This threshold was chosen to encourage learners who demonstrate
            partial understanding while maintaining meaningful standards.
        llm: The LLM client instance for making completion requests.
        db: AsyncSession for database operations.
        model: Model identifier for evaluation calls (default: TEXT_MODEL for
            cost efficiency, as evaluation doesn't require frontier capabilities).
    """

    # Score threshold for "correct" classification.
    # Set at 0.6 (maps to ~3.4/5) to reward partial understanding while
    # maintaining meaningful standards. Adjust based on pedagogical goals.
    CORRECT_THRESHOLD = 0.6

    # LLM rubric score range (inclusive)
    LLM_SCORE_MIN = 1
    LLM_SCORE_MAX = 5
    LLM_SCORE_DEFAULT = 3  # Middle of the range, used when LLM doesn't return a score

    # Code evaluation weighting
    CODE_TEST_WEIGHT = 0.7  # 70% weight for automated test results
    CODE_LLM_WEIGHT = 0.3  # 30% weight for LLM code quality assessment

    def __init__(
        self,
        llm_client: LLMClient,
        db: AsyncSession,
        model: Optional[str] = None,
    ):
        """
        Initialize the response evaluator.

        The evaluator requires an LLM client for semantic analysis and a database
        session for persisting evaluation results. The default model uses the
        configured TEXT_MODEL (Gemini 3 Flash) which provides a good balance of
        cost efficiency and evaluation quality.

        Args:
            llm_client: Configured LLM client instance for making completion
                requests. Should be pre-configured with appropriate API keys
                and rate limiting.
            db: SQLAlchemy AsyncSession for database operations. Used to persist
                ExerciseAttempt records containing evaluation results.
            model: Model identifier for LLM evaluation calls. Defaults to
                settings.TEXT_MODEL (Gemini 3 Flash) via get_default_text_model().
                Override with a specific model for different cost/quality tradeoffs.

        Example:
            evaluator = ResponseEvaluator(
                llm_client=get_llm_client(),
                db=async_session,
                model="openai/gpt-4o"  # For higher-stakes evaluations
            )
        """
        self.llm = llm_client
        self.db = db
        self.model = model or get_default_text_model()

    def _normalize_llm_score(self, llm_score: int | float | None) -> float:
        """
        Normalize an LLM rubric score (1-5) to a 0-1 scale.

        The LLM returns scores on a 1-5 rubric defined in the evaluation prompts:
        - 5: Excellent - covers all key points accurately with depth
        - 4: Good - covers most key points with minor gaps
        - 3: Adequate - covers core points but missing important details
        - 2: Partial - significant gaps or misconceptions
        - 1: Insufficient - major misconceptions or minimal coverage

        The normalization formula maps this to 0-1:
        - 1 → 0.00 (0%)
        - 2 → 0.25 (25%)
        - 3 → 0.50 (50%)
        - 4 → 0.75 (75%)
        - 5 → 1.00 (100%)

        Args:
            llm_score: Raw score from LLM (1-5 range). If None or missing,
                defaults to LLM_SCORE_DEFAULT (3, middle of range).

        Returns:
            Normalized score in 0-1 range, clamped to valid bounds.

        Example:
            >>> self._normalize_llm_score(4)
            0.75
            >>> self._normalize_llm_score(None)
            0.5  # Default to middle score
        """
        if llm_score is None:
            llm_score = self.LLM_SCORE_DEFAULT

        # Clamp to valid range to handle edge cases
        llm_score = max(self.LLM_SCORE_MIN, min(self.LLM_SCORE_MAX, llm_score))

        # Normalize: (score - min) / (max - min) → 0-1
        score_range = self.LLM_SCORE_MAX - self.LLM_SCORE_MIN
        return (llm_score - self.LLM_SCORE_MIN) / score_range

    def _compute_test_score(
        self, tests_passed: int | None, tests_total: int | None
    ) -> float | None:
        """
        Compute a normalized score from test results.

        Calculates the pass rate as a simple ratio of passed tests to total tests.
        Returns None if test data is unavailable or invalid (no tests run).

        Args:
            tests_passed: Number of tests that passed (may be None)
            tests_total: Total number of tests run (may be None or 0)

        Returns:
            Pass rate as 0-1 float, or None if tests weren't available.

        Example:
            >>> self._compute_test_score(3, 4)
            0.75
            >>> self._compute_test_score(None, None)
            None
        """
        if tests_total is None or tests_total <= 0:
            return None
        if tests_passed is None:
            tests_passed = 0
        return tests_passed / tests_total

    def _compute_code_score(self, llm_score: float, test_score: float | None) -> float:
        """
        Compute the final score for code exercises using weighted combination.

        For code exercises, we weight automated test results more heavily than
        LLM assessment because tests provide objective correctness verification.
        The LLM component captures code quality aspects (style, efficiency,
        best practices) that tests can't measure.

        Weighting Strategy:
        - With tests: CODE_TEST_WEIGHT (70%) tests + CODE_LLM_WEIGHT (30%) LLM
        - Without tests: 100% LLM score (fallback for exercises without tests)

        This weighting was chosen because:
        - Correctness is paramount in code exercises
        - Tests are objective and reliable
        - LLM assessment adds nuance for quality feedback

        Args:
            llm_score: Normalized LLM code quality score (0-1)
            test_score: Normalized test pass rate (0-1), or None if unavailable

        Returns:
            Final weighted score in 0-1 range.

        Example:
            >>> self._compute_code_score(llm_score=0.75, test_score=1.0)
            0.925  # (1.0 * 0.7) + (0.75 * 0.3)
            >>> self._compute_code_score(llm_score=0.75, test_score=None)
            0.75   # LLM only
        """
        if test_score is not None:
            return (test_score * self.CODE_TEST_WEIGHT) + (
                llm_score * self.CODE_LLM_WEIGHT
            )
        return llm_score

    def _is_correct(self, score: float) -> bool:
        """
        Determine if a normalized score meets the correctness threshold.

        Uses CORRECT_THRESHOLD (0.6 / 60%) to classify responses as correct
        or incorrect. This threshold balances:
        - Encouraging learners who demonstrate partial understanding
        - Maintaining meaningful standards for mastery

        The 60% threshold corresponds roughly to a 3.4/5 on the LLM rubric,
        which aligns with "adequate" to "good" understanding.

        Args:
            score: Normalized score in 0-1 range

        Returns:
            True if score >= CORRECT_THRESHOLD, False otherwise.

        Example:
            >>> self._is_correct(0.75)
            True
            >>> self._is_correct(0.5)
            False
        """
        return score >= self.CORRECT_THRESHOLD

    async def evaluate_response(
        self,
        exercise: Exercise,
        request: AttemptSubmitRequest,
        code_test_results: Optional[list[CodeExecutionResult]] = None,
    ) -> AttemptEvaluationResponse:
        """
        Evaluate a learner's response to an exercise and persist the attempt.

        This is the main entry point for response evaluation. It automatically
        detects the exercise type (text vs code) and routes to the appropriate
        evaluation strategy. After evaluation, it persists an ExerciseAttempt
        record and returns a response that includes the revealed solution.

        Evaluation Flow:
        1. Detect exercise type based on ExerciseType enum
        2. For code exercises: use test results + LLM code review
        3. For text exercises: use LLM semantic analysis against key points
        4. Normalize scores to 0-1 scale and determine correctness
        5. Create and persist ExerciseAttempt record
        6. Return evaluation with solution revealed for learning

        Scoring Details:
        - Text exercises: LLM returns 1-5 score, normalized to 0-1
        - Code exercises: 70% test pass rate + 30% LLM code quality score
        - Correctness threshold: 0.6 (60%)

        Args:
            exercise: The Exercise database model being attempted. Must include
                prompt, expected_key_points (for text), or solution_code/test_cases
                (for code exercises).
            request: AttemptSubmitRequest containing:
                - response: Text answer (for conceptual exercises)
                - response_code: Code submission (for code exercises)
                - confidence_before: Learner's confidence rating (1-5) before
                  seeing feedback, used for metacognition tracking
                - time_spent_seconds: Optional duration for analytics
            code_test_results: Pre-computed test results from CodeSandbox execution.
                If None for code exercises, evaluation falls back to LLM-only
                assessment. Typically provided by the session service after
                running learner code against test cases.

        Returns:
            AttemptEvaluationResponse containing:
                - attempt_id/attempt_uuid: Identifiers for the persisted attempt
                - score: Normalized 0-1 evaluation score
                - is_correct: Boolean based on CORRECT_THRESHOLD
                - feedback: Personalized improvement guidance
                - covered_points: List of demonstrated concepts
                - missing_points: List of concepts not addressed
                - misconceptions: List of identified errors with corrections
                - tests_passed/tests_total: Test statistics (code exercises)
                - exercise_with_solution: Full exercise with solution revealed

        Raises:
            SQLAlchemyError: If database commit fails (attempt not persisted)
        """
        is_code_exercise = self._is_code_exercise(exercise.exercise_type)

        if is_code_exercise:
            evaluation = await self._evaluate_code_response(
                exercise, request, code_test_results
            )
        else:
            evaluation = await self._evaluate_text_response(exercise, request)

        # Create attempt record
        attempt = ExerciseAttempt(
            attempt_uuid=str(uuid.uuid4()),
            session_id=None,  # Will be set by session service if applicable
            exercise_id=exercise.id,
            response=request.response,
            response_code=request.response_code,
            score=evaluation["score"],
            is_correct=evaluation["is_correct"],
            feedback=evaluation["feedback"],
            covered_points=evaluation["covered_points"],
            missing_points=evaluation["missing_points"],
            misconceptions=evaluation["misconceptions"],
            tests_passed=evaluation.get("tests_passed"),
            tests_total=evaluation.get("tests_total"),
            test_results=evaluation.get("test_results"),
            execution_error=evaluation.get("execution_error"),
            confidence_before=request.confidence_before,
            time_spent_seconds=request.time_spent_seconds,
        )

        self.db.add(attempt)
        await self.db.commit()
        await self.db.refresh(attempt)

        logger.info(
            f"Evaluated attempt {attempt.id} for exercise {exercise.id}: "
            f"score={evaluation['score']:.2f}, correct={evaluation['is_correct']}"
        )

        # Build response with solution reveal
        exercise_with_solution = ExerciseWithSolution(
            id=exercise.id,
            exercise_uuid=exercise.exercise_uuid,
            exercise_type=ExerciseType(exercise.exercise_type),
            topic=exercise.topic,
            difficulty=ExerciseDifficulty(exercise.difficulty),
            prompt=exercise.prompt,
            hints=exercise.hints or [],
            expected_key_points=exercise.expected_key_points or [],
            worked_example=exercise.worked_example,
            follow_up_problem=exercise.follow_up_problem,
            language=exercise.language,
            starter_code=exercise.starter_code,
            buggy_code=exercise.buggy_code,
            estimated_time_minutes=exercise.estimated_time_minutes or 10,
            tags=exercise.tags or [],
            # Revealed after attempt
            solution_code=exercise.solution_code,
            test_cases=exercise.test_cases,
        )

        return AttemptEvaluationResponse(
            attempt_id=attempt.id,
            attempt_uuid=attempt.attempt_uuid,
            score=evaluation["score"],
            is_correct=evaluation["is_correct"],
            feedback=evaluation["feedback"],
            covered_points=evaluation["covered_points"],
            missing_points=evaluation["missing_points"],
            misconceptions=evaluation["misconceptions"],
            tests_passed=evaluation.get("tests_passed"),
            tests_total=evaluation.get("tests_total"),
            test_results=evaluation.get("test_results"),
            execution_error=evaluation.get("execution_error"),
            exercise_with_solution=exercise_with_solution,
        )

    async def _evaluate_text_response(
        self,
        exercise: Exercise,
        request: AttemptSubmitRequest,
    ) -> dict:
        """
        Evaluate a text-based response using LLM semantic analysis.

        Sends the learner's response to the LLM along with the exercise prompt
        and expected key points. The LLM acts as an expert evaluator, identifying
        which key points were covered, what was missed, and any misconceptions.

        The evaluation prompt instructs the LLM to:
        - Match response content against expected key points
        - Provide evidence quotes showing coverage
        - Identify misconceptions with corrections and explanations
        - Assign a 1-5 overall score using a defined rubric
        - Generate personalized, actionable feedback

        Args:
            exercise: Exercise with prompt and expected_key_points for evaluation
            request: Submission containing the text response to evaluate

        Returns:
            Dictionary containing:
                - score: Normalized 0-1 score (from 1-5 LLM rating)
                - is_correct: True if score >= CORRECT_THRESHOLD
                - feedback: LLM-generated personalized guidance
                - covered_points: List of key points demonstrated
                - missing_points: List of key points not addressed
                - misconceptions: List of identified errors with corrections

        Raises:
            Exception: Re-raises any LLM evaluation failures for the caller to handle.
        """
        key_points_str = "\n".join(
            f"- {point}" for point in (exercise.expected_key_points or [])
        )

        prompt = EVALUATION_PROMPT.format(
            exercise_type=exercise.exercise_type,
            topic=exercise.topic,
            difficulty=exercise.difficulty,
            prompt=exercise.prompt,
            key_points=key_points_str or "No specific key points defined",
            response=request.response or "(No response provided)",
        )

        try:
            messages = build_messages(
                prompt=prompt,
                system_prompt="You are an expert educational evaluator. Provide constructive feedback in JSON format.",
            )

            response, _usage = await self.llm.complete(
                operation=PipelineOperation.CONCEPT_EXTRACTION,  # Use concept extraction operation
                messages=messages,
                model=self.model,
                temperature=0.3,  # More deterministic for evaluation
                json_mode=True,
            )

            data = response if isinstance(response, dict) else json.loads(response)

            # Extract covered point strings
            covered_points = []
            for item in data.get("covered_points", []):
                if isinstance(item, dict):
                    covered_points.append(item.get("point", str(item)))
                else:
                    covered_points.append(str(item))

            # Extract misconception strings
            misconceptions = []
            for item in data.get("misconceptions", []):
                if isinstance(item, dict):
                    misconceptions.append(
                        f"{item.get('error', '')}: {item.get('correction', '')}"
                    )
                else:
                    misconceptions.append(str(item))

            # Normalize LLM 1-5 score to 0-1 and determine correctness
            normalized_score = self._normalize_llm_score(data.get("overall_score"))

            return {
                "score": normalized_score,
                "is_correct": self._is_correct(normalized_score),
                "feedback": data.get("specific_feedback", ""),
                "covered_points": covered_points,
                "missing_points": data.get("missing_points", []),
                "misconceptions": misconceptions,
            }

        except Exception as e:
            logger.error(f"LLM evaluation failed: {e}")
            raise

    async def _evaluate_code_response(
        self,
        exercise: Exercise,
        request: AttemptSubmitRequest,
        test_results: Optional[list[CodeExecutionResult]],
    ) -> dict:
        """
        Evaluate a code response using automated tests and LLM code review.

        Combines objective test results with subjective LLM analysis to provide
        comprehensive code feedback. The LLM reviews the code like an experienced
        developer, assessing correctness, style, efficiency, and best practices.

        Scoring Strategy:
        - When tests are available: 70% test pass rate + 30% LLM quality score
        - When tests unavailable: 100% LLM score
        - This weighting prioritizes correctness while still valuing code quality

        The LLM evaluation considers:
        - Correctness based on test results
        - Code style and readability
        - Efficiency and algorithmic choices
        - Proper use of language features
        - Edge case handling
        - Adherence to best practices

        Args:
            exercise: Exercise with solution_code as reference and test_cases
            request: Submission containing response_code to evaluate
            test_results: Optional list of CodeExecutionResult from CodeSandbox execution.
                Each CodeExecutionResult contains passed status, expected/actual values,
                and any error messages.

        Returns:
            Dictionary containing:
                - score: Weighted combination of test and LLM scores (0-1)
                - is_correct: True if score >= CORRECT_THRESHOLD
                - feedback: Code review style guidance from LLM
                - covered_points: Concepts and patterns demonstrated in code
                - missing_points: Expected patterns or best practices not shown
                - misconceptions: Code issues with explanations and fixes
                - tests_passed: Number of tests that passed (if available)
                - tests_total: Total number of tests run (if available)
                - test_results: Raw CodeExecutionResult data for detailed display

        Raises:
            Exception: Re-raises LLM evaluation failures if no test results are
                available to fall back on. When test results exist, returns
                test-only scoring on LLM failure.
        """
        # Format test results if available
        if test_results:
            tests_passed = sum(1 for t in test_results if t.passed)
            tests_total = len(test_results)
            test_results_str = "\n".join(
                f"Test {t.test_index + 1}: {'PASS' if t.passed else 'FAIL'}"
                + (
                    f" - Expected: {t.expected}, Got: {t.actual}"
                    if not t.passed
                    else ""
                )
                for t in test_results
            )
            test_results_json = [t.model_dump() for t in test_results]
        else:
            tests_passed = None
            tests_total = None
            test_results_str = "No automated tests available"
            test_results_json = None

        prompt = CODE_EVALUATION_PROMPT.format(
            exercise_type=exercise.exercise_type,
            topic=exercise.topic,
            difficulty=exercise.difficulty,
            language=exercise.language or "python",
            prompt=exercise.prompt,
            solution_code=exercise.solution_code or "(No reference solution)",
            response_code=request.response_code or "(No code provided)",
            test_results=test_results_str,
        )

        try:
            messages = build_messages(
                prompt=prompt,
                system_prompt="You are an expert code reviewer. Provide constructive feedback in JSON format.",
            )

            response, _usage = await self.llm.complete(
                operation=PipelineOperation.CONCEPT_EXTRACTION,
                messages=messages,
                model=self.model,
                temperature=0.3,
                json_mode=True,
            )

            data = response if isinstance(response, dict) else json.loads(response)

            # Extract covered point strings
            covered_points = []
            for item in data.get("covered_points", []):
                if isinstance(item, dict):
                    covered_points.append(item.get("point", str(item)))
                else:
                    covered_points.append(str(item))

            # Extract misconception strings
            misconceptions = []
            for item in data.get("misconceptions", []):
                if isinstance(item, dict):
                    misconceptions.append(
                        f"{item.get('error', '')}: {item.get('correction', '')}"
                    )
                else:
                    misconceptions.append(str(item))

            # Calculate weighted score from LLM assessment and test results
            llm_score = self._normalize_llm_score(data.get("overall_score"))
            test_score = self._compute_test_score(tests_passed, tests_total)
            normalized_score = self._compute_code_score(llm_score, test_score)

            return {
                "score": normalized_score,
                "is_correct": self._is_correct(normalized_score),
                "feedback": data.get("specific_feedback", ""),
                "covered_points": covered_points,
                "missing_points": data.get("missing_points", []),
                "misconceptions": misconceptions,
                "tests_passed": tests_passed,
                "tests_total": tests_total,
                "test_results": test_results_json,
            }

        except Exception as e:
            logger.error(f"LLM code evaluation failed: {e}")

            # Fall back to test-only evaluation if available
            test_score = self._compute_test_score(tests_passed, tests_total)
            if test_score is not None:
                return {
                    "score": test_score,
                    "is_correct": self._is_correct(test_score),
                    "feedback": f"Your code passed {tests_passed}/{tests_total} tests.",
                    "covered_points": [],
                    "missing_points": [],
                    "misconceptions": [],
                    "tests_passed": tests_passed,
                    "tests_total": tests_total,
                    "test_results": test_results_json,
                }

            # No test results to fall back on, re-raise the exception
            raise

    def _is_code_exercise(self, exercise_type: str) -> bool:
        """
        Determine if an exercise type requires code evaluation.

        Code exercises are evaluated differently from text exercises:
        - They may have automated test cases to run
        - The LLM prompt focuses on code quality and correctness
        - Scoring weights test results more heavily than LLM assessment

        Args:
            exercise_type: String value of the ExerciseType enum

        Returns:
            True if the exercise type is one of the code-related types:
            CODE_IMPLEMENT, CODE_COMPLETE, CODE_DEBUG, CODE_REFACTOR, CODE_EXPLAIN
        """
        code_types = {
            ExerciseType.CODE_IMPLEMENT.value,
            ExerciseType.CODE_COMPLETE.value,
            ExerciseType.CODE_DEBUG.value,
            ExerciseType.CODE_REFACTOR.value,
            ExerciseType.CODE_EXPLAIN.value,
        }
        return exercise_type in code_types

    async def update_confidence(
        self,
        attempt_id: int,
        confidence_after: int,
    ) -> None:
        """
        Update the learner's confidence rating after viewing feedback.

        This supports metacognition tracking by capturing how the learner's
        confidence changed after receiving evaluation feedback and seeing the
        solution. The before/after confidence delta is a valuable signal for:
        - Identifying overconfident learners (high before, low after)
        - Identifying underconfident learners (low before, high after)
        - Tracking calibration improvement over time
        - Detecting exercises that commonly surprise learners

        This is typically called as a separate API request after the learner
        has reviewed their feedback and the revealed solution.

        Args:
            attempt_id: Database ID of the ExerciseAttempt to update
            confidence_after: Learner's confidence rating (1-5) after seeing
                feedback. Scale: 1=Very uncertain, 5=Very confident

        Raises:
            SQLAlchemyError: If database update fails

        Example:
            # After learner reviews feedback and rates confidence
            await evaluator.update_confidence(
                attempt_id=attempt.id,
                confidence_after=4  # "I understand this now"
            )
        """
        await self.db.execute(
            update(ExerciseAttempt)
            .where(ExerciseAttempt.id == attempt_id)
            .values(confidence_after=confidence_after)
        )
        await self.db.commit()
