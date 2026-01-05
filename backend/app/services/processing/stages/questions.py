"""
Mastery Question Generation Stage

Generates mastery questions that test true understanding of content.
If a user can answer these questions from memory, they truly understand
the material.

Question Types:
- conceptual: "What is X and why does it matter?"
- application: "How would you use X to solve Y?"
- analysis: "Why does X lead to Y?"
- synthesis: "How does X connect to Z?"

Usage:
    from app.services.processing.stages.questions import generate_mastery_questions

    questions, usages = await generate_mastery_questions(
        content, analysis, summary, extraction, llm_client
    )
    for q in questions:
        print(f"[{q.difficulty}] {q.question}")
"""

import logging

from app.config.processing import processing_settings
from app.models.content import UnifiedContent
from app.models.processing import MasteryQuestion, ContentAnalysis, ExtractionResult
from app.enums.pipeline import PipelineOperation
from app.enums.processing import QuestionType, QuestionDifficulty
from app.pipelines.utils.cost_types import LLMUsage
from app.services.llm.client import LLMClient

logger = logging.getLogger(__name__)


MASTERY_QUESTIONS_PROMPT = """Generate mastery questions for this content.

A mastery question is one where:
- If you can answer it from memory, you truly understand the material
- It tests UNDERSTANDING, not just recall of facts
- Answering requires integrating multiple concepts
- The question is specific to THIS content, not generic

Content:
- Title: {title}
- Domain: {domain}
- Complexity: {complexity}

Summary: {summary}

Key Concepts:
{concepts}

Key Findings:
{findings}

Generate 3-6 questions of different types:

Question Types:
- conceptual: "What is X and why does it matter?" or "Explain the relationship between X and Y"
- application: "How would you use X to solve Y?" or "When would you choose X over Y?"
- analysis: "Why does X lead to Y?" or "What are the trade-offs of X?"
- synthesis: "How does X connect to Z?" or "How could you combine X with Y?"

Difficulty Guidelines (based on content complexity: {complexity}):
- foundational: "what" and "how" questions, basic understanding
- intermediate: "why" and "when to use" questions, deeper understanding
- advanced: "edge cases", "trade-offs", and "design" questions

For each question, provide:
- 2-3 hints that progressively help without giving away the answer
- 2-3 key points that a good answer should include

Return as JSON:
{{
  "questions": [
    {{
      "question": "Clear, specific question",
      "type": "conceptual|application|analysis|synthesis",
      "difficulty": "foundational|intermediate|advanced",
      "hints": ["Hint that doesn't give away answer", "More specific hint"],
      "key_points": ["Point 1 for good answer", "Point 2 for good answer"]
    }}
  ]
}}
"""


async def generate_mastery_questions(
    content: UnifiedContent,
    analysis: ContentAnalysis,
    summary: str,
    extraction: ExtractionResult,
    llm_client: LLMClient,
) -> tuple[list[MasteryQuestion], list[LLMUsage]]:
    """
    Generate questions that test true understanding.

    Args:
        content: Unified content from ingestion
        analysis: Content analysis result
        summary: Generated summary (detailed preferred)
        extraction: Extracted concepts and findings
        llm_client: LLM client for completion

    Returns:
        Tuple of (list of MasteryQuestion objects, list of LLMUsage)
    """
    # Format concepts with definitions
    max_concepts = processing_settings.QUESTIONS_MAX_CONCEPTS
    concepts_text = (
        "\n".join(
            [f"- {c.name}: {c.definition}" for c in extraction.concepts[:max_concepts]]
        )
        if extraction.concepts
        else "No concepts extracted"
    )

    # Format findings
    max_findings = processing_settings.QUESTIONS_MAX_FINDINGS
    findings_text = (
        "\n".join([f"- {f}" for f in extraction.key_findings[:max_findings]])
        if extraction.key_findings
        else "No findings extracted"
    )

    summary_truncate = processing_settings.QUESTIONS_SUMMARY_TRUNCATE
    prompt = MASTERY_QUESTIONS_PROMPT.format(
        title=content.title,
        domain=analysis.domain,
        complexity=analysis.complexity,
        summary=summary[:summary_truncate] if summary else "",
        concepts=concepts_text,
        findings=findings_text,
    )

    try:
        data, usage = await llm_client.complete(
            operation=PipelineOperation.QUESTION_GENERATION,
            messages=[{"role": "user", "content": prompt}],
            temperature=processing_settings.QUESTIONS_TEMPERATURE,
            max_tokens=processing_settings.QUESTIONS_MAX_TOKENS,
            json_mode=True,
            content_id=content.id,
        )

        questions = []
        max_hints = processing_settings.QUESTIONS_MAX_HINTS
        max_key_points = processing_settings.QUESTIONS_MAX_KEY_POINTS
        for q in data.get("questions", []):
            if q.get("question"):  # Skip empty questions
                questions.append(
                    MasteryQuestion(
                        question=q.get("question", ""),
                        question_type=_validate_question_type(
                            q.get("type", QuestionType.CONCEPTUAL.value)
                        ),
                        difficulty=_validate_difficulty(
                            q.get("difficulty", analysis.complexity)
                        ),
                        hints=q.get("hints", [])[:max_hints],
                        key_points=q.get("key_points", [])[:max_key_points],
                    )
                )

        logger.debug(f"Generated {len(questions)} mastery questions")
        return questions, [usage]

    except Exception as e:
        logger.error(f"Question generation failed: {e}")
        return [], []


def _validate_question_type(qtype: str) -> str:
    """Validate and normalize question type."""
    qtype = qtype.lower().strip()
    valid_types = {t.value for t in QuestionType}
    if qtype in valid_types:
        return qtype
    return QuestionType.CONCEPTUAL.value


def _validate_difficulty(difficulty: str) -> str:
    """Validate and normalize difficulty."""
    difficulty = difficulty.lower().strip()
    valid_difficulties = {d.value for d in QuestionDifficulty}
    if difficulty in valid_difficulties:
        return difficulty
    return QuestionDifficulty.INTERMEDIATE.value
