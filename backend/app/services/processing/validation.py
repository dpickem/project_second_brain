"""
Processing Output Validation

Validates processing results for quality issues. Catches problems early
to ensure generated content meets quality standards.

Usage:
    from app.services.processing.validation import validate_processing_result

    issues = validate_processing_result(result)
    if issues:
        print(f"Quality issues: {issues}")
"""

import logging
from app.enums.processing import SummaryLevel, ConceptImportance
from app.models.processing import ProcessingResult
from app.config.processing import processing_settings

logger = logging.getLogger(__name__)


def validate_processing_result(result: ProcessingResult) -> list[str]:
    """
    Validate processing outputs for quality issues.

    Checks:
    - Summary lengths and presence
    - Concept extraction quality
    - Tag assignment
    - Question generation

    Args:
        result: ProcessingResult to validate

    Returns:
        List of issue descriptions (empty if all valid)
    """
    issues = []

    # Check summaries
    issues.extend(_validate_summaries(result.summaries))

    # Check concepts
    issues.extend(_validate_concepts(result.extraction.concepts))

    # Check tags
    issues.extend(_validate_tags(result.tags.domain_tags, result.tags.meta_tags))

    # Check questions
    issues.extend(_validate_questions(result.mastery_questions))

    return issues


def _validate_summaries(summaries: dict[str, str]) -> list[str]:
    """Validate summary outputs."""
    issues = []

    # Check standard summary exists and has minimum length
    standard = summaries.get(SummaryLevel.STANDARD.value, "")
    if not standard:
        issues.append("No standard summary generated")
    elif len(standard) < processing_settings.MIN_SUMMARY_LENGTH:
        issues.append(
            f"Standard summary too short ({len(standard)} chars, "
            f"min: {processing_settings.MIN_SUMMARY_LENGTH})"
        )

    # Check for error messages in summaries
    for level, summary in summaries.items():
        if summary.startswith("[") and "failed" in summary.lower():
            issues.append(f"{level} summary contains error message")

    return issues


def _validate_concepts(concepts: list) -> list[str]:
    """Validate extracted concepts."""
    issues = []

    if not concepts:
        issues.append("No concepts extracted")
        return issues

    if len(concepts) < processing_settings.MIN_CONCEPTS:
        issues.append(
            f"Too few concepts extracted ({len(concepts)}, "
            f"min: {processing_settings.MIN_CONCEPTS})"
        )

    # Check for core concepts
    core_concepts = [
        c for c in concepts if c.importance == ConceptImportance.CORE.value
    ]
    if not core_concepts:
        issues.append("No core concepts identified")

    # Check concept quality
    for concept in concepts[:5]:  # Check first 5
        if not concept.definition or len(concept.definition) < 10:
            issues.append(f"Concept '{concept.name}' has insufficient definition")

    return issues


def _validate_tags(domain_tags: list[str], meta_tags: list[str]) -> list[str]:
    """Validate tag assignments."""
    issues = []

    if not domain_tags:
        issues.append("No domain tags assigned")

    if not meta_tags:
        # This is less critical, just a warning
        logger.debug("No meta tags assigned")

    return issues


def _validate_questions(questions: list) -> list[str]:
    """Validate generated questions."""
    issues = []

    if len(questions) < processing_settings.MIN_QUESTIONS:
        issues.append(
            f"Insufficient questions generated ({len(questions)}, "
            f"min: {processing_settings.MIN_QUESTIONS})"
        )

    # Check question quality
    for question in questions[:3]:  # Check first 3
        if len(question.question) < 20:
            issues.append(f"Question too short: '{question.question[:50]}...'")
        if not question.key_points:
            issues.append(f"Question missing key points: '{question.question[:30]}...'")

    return issues


def validate_summary_length(summary: str, level: SummaryLevel) -> bool:
    """
    Check if summary meets length requirements for its level.

    Args:
        summary: Summary text
        level: Summary level

    Returns:
        True if summary meets length requirements
    """
    min_lengths = {
        SummaryLevel.BRIEF: 50,
        SummaryLevel.STANDARD: processing_settings.MIN_SUMMARY_LENGTH,
        SummaryLevel.DETAILED: 300,
    }

    min_len = min_lengths.get(level, 100)
    return len(summary) >= min_len
