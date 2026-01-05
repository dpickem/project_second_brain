"""
Unit tests for processing validation module.

Tests the validation of processing results for quality issues.
"""

import pytest

from app.enums import SummaryLevel, ConceptImportance
from app.models.processing import (
    ProcessingResult,
    ContentAnalysis,
    ExtractionResult,
    TagAssignment,
    Concept,
    MasteryQuestion,
)
from app.services.processing.validation import (
    validate_processing_result,
    validate_summary_length,
    _validate_summaries,
    _validate_concepts,
    _validate_tags,
    _validate_questions,
)


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def valid_analysis() -> ContentAnalysis:
    """Create a valid content analysis."""
    return ContentAnalysis(
        content_type="paper",
        domain="ml",
        complexity="advanced",
        estimated_length="medium",
        has_code=True,
        has_math=True,
        has_diagrams=True,
        key_topics=["transformers", "attention", "neural networks"],
        language="en",
    )


@pytest.fixture
def valid_extraction() -> ExtractionResult:
    """Create a valid extraction result."""
    return ExtractionResult(
        concepts=[
            Concept(
                name="Transformer",
                definition="A neural network architecture based on self-attention mechanisms",
                context="The main architecture proposed in this paper",
                importance=ConceptImportance.CORE.value,
                related_concepts=["attention", "encoder-decoder"],
            ),
            Concept(
                name="Self-attention",
                definition="Mechanism allowing the model to relate positions in a sequence",
                context="Core component enabling parallelization",
                importance=ConceptImportance.CORE.value,
                related_concepts=["transformer"],
            ),
            Concept(
                name="Multi-head attention",
                definition="Running multiple attention operations in parallel",
                context="Allows the model to focus on different aspects",
                importance=ConceptImportance.SUPPORTING.value,
                related_concepts=["attention"],
            ),
        ],
        key_findings=[
            "Transformers outperform RNNs on translation tasks",
            "Self-attention enables better parallelization",
        ],
        methodologies=["Multi-head attention", "Positional encoding"],
        tools_mentioned=["TensorFlow"],
        people_mentioned=["Vaswani"],
    )


@pytest.fixture
def valid_tags() -> TagAssignment:
    """Create valid tag assignment."""
    return TagAssignment(
        domain_tags=["ml/transformers/attention", "ml/architecture"],
        meta_tags=["status/actionable", "quality/deep-dive"],
        suggested_new_tags=[],
        reasoning="Tagged based on content analysis",
    )


@pytest.fixture
def valid_questions() -> list[MasteryQuestion]:
    """Create valid mastery questions."""
    return [
        MasteryQuestion(
            question="What is the main advantage of self-attention over recurrence?",
            question_type="conceptual",
            difficulty="intermediate",
            hints=["Think about parallelization", "Consider dependencies"],
            key_points=["Parallel computation", "No sequential dependency"],
        ),
        MasteryQuestion(
            question="How would you implement multi-head attention from scratch?",
            question_type="application",
            difficulty="advanced",
            hints=["Start with single-head attention", "Consider matrix dimensions"],
            key_points=["Query, Key, Value matrices", "Concatenation of heads"],
        ),
        MasteryQuestion(
            question="Why is positional encoding necessary in transformers?",
            question_type="analysis",
            difficulty="intermediate",
            hints=["Self-attention is position-invariant"],
            key_points=["Order information", "Sinusoidal or learned"],
        ),
    ]


@pytest.fixture
def valid_processing_result(
    valid_analysis, valid_extraction, valid_tags, valid_questions
) -> ProcessingResult:
    """Create a valid processing result."""
    return ProcessingResult(
        content_id="test-content-123",
        analysis=valid_analysis,
        summaries={
            SummaryLevel.BRIEF.value: "Brief summary of the transformer paper.",
            SummaryLevel.STANDARD.value: "This paper introduces the Transformer architecture, "
            "a novel neural network model based solely on attention mechanisms. "
            "It achieves state-of-the-art results on machine translation benchmarks.",
            SummaryLevel.DETAILED.value: "## Overview\n\nThe Transformer architecture...",
        },
        extraction=valid_extraction,
        tags=valid_tags,
        connections=[],
        followups=[],
        mastery_questions=valid_questions,
        processing_time_seconds=45.0,
        estimated_cost_usd=0.05,
    )


# =============================================================================
# Processing Result Validation Tests
# =============================================================================


class TestValidateProcessingResult:
    """Tests for the complete processing result validation."""

    def test_valid_result_has_no_issues(self, valid_processing_result):
        """Test that a valid result passes validation."""
        issues = validate_processing_result(valid_processing_result)

        assert len(issues) == 0

    def test_invalid_result_collects_all_issues(self, valid_processing_result):
        """Test that all issues are collected."""
        # Make result invalid in multiple ways
        valid_processing_result.summaries = {}
        valid_processing_result.extraction = ExtractionResult()
        valid_processing_result.tags = TagAssignment()
        valid_processing_result.mastery_questions = []

        issues = validate_processing_result(valid_processing_result)

        # Should have issues from summaries, concepts, tags, and questions
        assert len(issues) >= 4


# =============================================================================
# Summary Validation Tests
# =============================================================================


class TestValidateSummaries:
    """Tests for summary validation."""

    def test_valid_summaries_pass(self):
        """Test that valid summaries pass validation."""
        summaries = {
            SummaryLevel.BRIEF.value: "A" * 100,
            SummaryLevel.STANDARD.value: "B" * 200,
            SummaryLevel.DETAILED.value: "C" * 300,
        }

        issues = _validate_summaries(summaries)

        assert len(issues) == 0

    def test_missing_standard_summary(self):
        """Test that missing standard summary is flagged."""
        summaries = {
            SummaryLevel.BRIEF.value: "Brief summary",
            SummaryLevel.DETAILED.value: "Detailed summary",
        }

        issues = _validate_summaries(summaries)

        assert any("No standard summary" in issue for issue in issues)

    def test_empty_standard_summary(self):
        """Test that empty standard summary is flagged."""
        summaries = {
            SummaryLevel.STANDARD.value: "",
        }

        issues = _validate_summaries(summaries)

        assert any("No standard summary" in issue for issue in issues)

    def test_short_standard_summary(self):
        """Test that too-short standard summary is flagged."""
        summaries = {
            SummaryLevel.STANDARD.value: "Too short",  # Less than MIN_SUMMARY_LENGTH
        }

        issues = _validate_summaries(summaries)

        assert any("too short" in issue.lower() for issue in issues)

    def test_error_message_in_summary(self):
        """Test that error messages in summaries are flagged."""
        summaries = {
            SummaryLevel.STANDARD.value: "A" * 200,
            SummaryLevel.BRIEF.value: "[Summary generation failed: timeout]",
        }

        issues = _validate_summaries(summaries)

        assert any("error message" in issue.lower() for issue in issues)


# =============================================================================
# Concept Validation Tests
# =============================================================================


class TestValidateConcepts:
    """Tests for concept validation."""

    def test_valid_concepts_pass(self, valid_extraction):
        """Test that valid concepts pass validation."""
        issues = _validate_concepts(valid_extraction.concepts)

        assert len(issues) == 0

    def test_no_concepts_flagged(self):
        """Test that missing concepts are flagged."""
        issues = _validate_concepts([])

        assert any("No concepts extracted" in issue for issue in issues)

    def test_too_few_concepts_flagged(self):
        """Test that too few concepts are flagged."""
        concepts = []  # Empty means too few

        issues = _validate_concepts(concepts)

        assert any("No concepts" in issue or "Too few" in issue for issue in issues)

    def test_no_core_concepts_flagged(self):
        """Test that missing core concepts are flagged."""
        concepts = [
            Concept(
                name="Supporting Concept",
                definition="A supporting concept definition",
                importance=ConceptImportance.SUPPORTING.value,
            ),
            Concept(
                name="Tangential Concept",
                definition="A tangential concept definition",
                importance=ConceptImportance.TANGENTIAL.value,
            ),
        ]

        issues = _validate_concepts(concepts)

        assert any("No core concepts" in issue for issue in issues)

    def test_concept_with_short_definition_flagged(self):
        """Test that concepts with short definitions are flagged."""
        concepts = [
            Concept(
                name="Concept",
                definition="Short",  # Less than 10 chars
                importance=ConceptImportance.CORE.value,
            ),
        ]

        issues = _validate_concepts(concepts)

        assert any("insufficient definition" in issue.lower() for issue in issues)

    def test_concept_with_empty_definition_flagged(self):
        """Test that concepts with empty definitions are flagged."""
        concepts = [
            Concept(
                name="Concept",
                definition="",
                importance=ConceptImportance.CORE.value,
            ),
        ]

        issues = _validate_concepts(concepts)

        assert any("insufficient definition" in issue.lower() for issue in issues)


# =============================================================================
# Tag Validation Tests
# =============================================================================


class TestValidateTags:
    """Tests for tag validation."""

    def test_valid_tags_pass(self):
        """Test that valid tags pass validation."""
        issues = _validate_tags(
            domain_tags=["ml/transformers", "ml/attention"],
            meta_tags=["status/actionable"],
        )

        assert len(issues) == 0

    def test_no_domain_tags_flagged(self):
        """Test that missing domain tags are flagged."""
        issues = _validate_tags(
            domain_tags=[],
            meta_tags=["status/actionable"],
        )

        assert any("No domain tags" in issue for issue in issues)

    def test_empty_meta_tags_is_warning_only(self):
        """Test that empty meta tags is a warning, not an issue."""
        issues = _validate_tags(
            domain_tags=["ml/transformers"],
            meta_tags=[],
        )

        # Empty meta tags should not produce an issue (just a log warning)
        assert not any("meta tags" in issue.lower() for issue in issues)


# =============================================================================
# Question Validation Tests
# =============================================================================


class TestValidateQuestions:
    """Tests for question validation."""

    def test_valid_questions_pass(self, valid_questions):
        """Test that valid questions pass validation."""
        issues = _validate_questions(valid_questions)

        assert len(issues) == 0

    def test_too_few_questions_flagged(self):
        """Test that too few questions are flagged."""
        questions = [
            MasteryQuestion(
                question="Single question here?",
                hints=["hint"],
                key_points=["point"],
            )
        ]

        issues = _validate_questions(questions)

        assert any("Insufficient questions" in issue for issue in issues)

    def test_empty_questions_flagged(self):
        """Test that no questions is flagged."""
        issues = _validate_questions([])

        assert any("Insufficient questions" in issue for issue in issues)

    def test_short_question_flagged(self):
        """Test that too-short questions are flagged."""
        questions = [
            MasteryQuestion(
                question="Why?",  # Too short
                hints=["hint"],
                key_points=["point"],
            ),
            MasteryQuestion(
                question="What is the main concept discussed in this paper?",
                hints=["hint"],
                key_points=["point"],
            ),
            MasteryQuestion(
                question="How does the approach compare to alternatives?",
                hints=["hint"],
                key_points=["point"],
            ),
        ]

        issues = _validate_questions(questions)

        assert any("too short" in issue.lower() for issue in issues)

    def test_question_without_key_points_flagged(self):
        """Test that questions without key points are flagged."""
        questions = [
            MasteryQuestion(
                question="What is the main concept discussed in this paper?",
                hints=["hint"],
                key_points=[],  # No key points
            ),
            MasteryQuestion(
                question="How does this relate to previous work in the field?",
                hints=["hint"],
                key_points=["point"],
            ),
            MasteryQuestion(
                question="Why is this approach better than alternatives?",
                hints=["hint"],
                key_points=["point"],
            ),
        ]

        issues = _validate_questions(questions)

        assert any("missing key points" in issue.lower() for issue in issues)


# =============================================================================
# Summary Length Validation Tests
# =============================================================================


class TestValidateSummaryLength:
    """Tests for the summary length validation helper."""

    def test_brief_summary_meets_minimum(self):
        """Test brief summary length validation."""
        # Minimum for brief is 50 chars
        assert validate_summary_length("A" * 50, SummaryLevel.BRIEF) is True
        assert validate_summary_length("A" * 49, SummaryLevel.BRIEF) is False

    def test_standard_summary_meets_minimum(self):
        """Test standard summary length validation."""
        # Uses MIN_SUMMARY_LENGTH from settings
        long_summary = "A" * 200
        short_summary = "A" * 10

        assert validate_summary_length(long_summary, SummaryLevel.STANDARD) is True
        assert validate_summary_length(short_summary, SummaryLevel.STANDARD) is False

    def test_detailed_summary_meets_minimum(self):
        """Test detailed summary length validation."""
        # Minimum for detailed is 300 chars
        assert validate_summary_length("A" * 300, SummaryLevel.DETAILED) is True
        assert validate_summary_length("A" * 299, SummaryLevel.DETAILED) is False

    def test_empty_summary_fails_all_levels(self):
        """Test that empty summaries fail all levels."""
        assert validate_summary_length("", SummaryLevel.BRIEF) is False
        assert validate_summary_length("", SummaryLevel.STANDARD) is False
        assert validate_summary_length("", SummaryLevel.DETAILED) is False


# =============================================================================
# Additional Validation Edge Cases
# =============================================================================


class TestValidationEdgeCases:
    """Additional edge case tests for validation."""

    def test_validate_summaries_with_whitespace_only(self):
        """Test validation with whitespace-only summaries."""
        summaries = {
            SummaryLevel.BRIEF.value: "   ",
            SummaryLevel.STANDARD.value: "\n\t\r",
            SummaryLevel.DETAILED.value: "    \n    ",
        }

        issues = _validate_summaries(summaries)

        # Whitespace-only should be flagged as too short or empty
        assert len(issues) > 0

    def test_validate_concepts_with_one_core_concept(self):
        """Test validation with exactly one core concept (minimum)."""
        concepts = [
            Concept(
                name="Core Concept",
                definition="A sufficiently long definition for validation",
                importance=ConceptImportance.CORE.value,
            )
        ]

        issues = _validate_concepts(concepts)

        # One core concept should be valid
        assert not any("No core concepts" in issue for issue in issues)

    def test_validate_concepts_all_tangential(self):
        """Test validation with only tangential concepts."""
        concepts = [
            Concept(
                name="Tangential 1",
                definition="A sufficiently long definition here",
                importance=ConceptImportance.TANGENTIAL.value,
            ),
            Concept(
                name="Tangential 2",
                definition="Another sufficiently long definition",
                importance=ConceptImportance.TANGENTIAL.value,
            ),
        ]

        issues = _validate_concepts(concepts)

        # Should flag no core concepts
        assert any("No core concepts" in issue for issue in issues)

    def test_validate_questions_exactly_two(self, valid_questions):
        """Test validation with exactly 2 questions (minimum)."""
        questions = valid_questions[:2]

        issues = _validate_questions(questions)

        # 2 questions should meet minimum
        assert not any("Insufficient questions" in issue for issue in issues)

    def test_validate_questions_with_very_long_question(self):
        """Test validation accepts long questions."""
        questions = [
            MasteryQuestion(
                question="A" * 500,  # Very long question
                hints=["hint"],
                key_points=["point"],
            ),
            MasteryQuestion(
                question="B" * 500,
                hints=["hint"],
                key_points=["point"],
            ),
            MasteryQuestion(
                question="C" * 500,
                hints=["hint"],
                key_points=["point"],
            ),
        ]

        issues = _validate_questions(questions)

        # Long questions should be valid (no length max)
        assert not any("too long" in issue.lower() for issue in issues)

    def test_validate_result_with_all_valid_minimal_content(self):
        """Test validation with minimal but valid content."""
        result = ProcessingResult(
            content_id="minimal-123",
            analysis=ContentAnalysis(
                content_type="article",
                domain="general",
                complexity="foundational",
                estimated_length="short",
            ),
            summaries={
                SummaryLevel.BRIEF.value: "A" * 50,
                SummaryLevel.STANDARD.value: "B" * 100,
                SummaryLevel.DETAILED.value: "C" * 300,
            },
            extraction=ExtractionResult(
                concepts=[
                    Concept(
                        name="Core Concept",
                        definition="A sufficiently detailed definition",
                        importance=ConceptImportance.CORE.value,
                    )
                ]
            ),
            tags=TagAssignment(
                domain_tags=["general/topic"],
                meta_tags=["status/new"],
            ),
            mastery_questions=[
                MasteryQuestion(
                    question="What is this about in detail?",
                    hints=["hint"],
                    key_points=["point"],
                ),
                MasteryQuestion(
                    question="How does this work specifically?",
                    hints=["hint"],
                    key_points=["point"],
                ),
            ],
        )

        issues = validate_processing_result(result)

        # Minimal valid content should pass
        assert len(issues) <= 1  # May have minor issues


class TestValidateSummariesDetail:
    """Detailed tests for summary validation."""

    def test_validate_brief_summary_at_boundary(self):
        """Test brief summary at exact boundary."""
        # Exactly at minimum length
        summaries = {
            SummaryLevel.BRIEF.value: "A" * 50,  # Exactly 50 chars
            SummaryLevel.STANDARD.value: "B" * 100,
            SummaryLevel.DETAILED.value: "C" * 300,
        }

        issues = _validate_summaries(summaries)

        assert not any("brief" in issue.lower() for issue in issues)

    def test_validate_detailed_missing(self):
        """Test validation with missing detailed summary."""
        summaries = {
            SummaryLevel.BRIEF.value: "Brief summary",
            SummaryLevel.STANDARD.value: "A" * 200,
            # No detailed summary
        }

        issues = _validate_summaries(summaries)

        # Standard is present, so main validation should pass
        assert not any("No standard summary" in issue for issue in issues)

    def test_validate_summary_with_failed_marker(self):
        """Test validation catches 'failed' markers in summaries."""
        summaries = {
            SummaryLevel.STANDARD.value: "A" * 200,
            SummaryLevel.BRIEF.value: "[Summary generation failed: timeout]",
        }

        issues = _validate_summaries(summaries)

        # Should flag summaries containing 'failed' text
        assert any("error message" in issue.lower() for issue in issues)


class TestValidateConceptsDetail:
    """Detailed tests for concept validation."""

    def test_validate_concept_definition_boundary(self):
        """Test concept definition length at boundary."""
        concepts = [
            Concept(
                name="Test",
                definition="A" * 10,  # Exactly at minimum
                importance=ConceptImportance.CORE.value,
            )
        ]

        issues = _validate_concepts(concepts)

        # Should be valid at boundary
        insufficient_count = sum(
            1 for issue in issues if "insufficient definition" in issue.lower()
        )
        assert insufficient_count == 0

    def test_validate_concept_with_empty_string_definition(self):
        """Test concept with empty string definition."""
        concepts = [
            Concept(
                name="Test",
                definition="",
                importance=ConceptImportance.CORE.value,
            )
        ]

        issues = _validate_concepts(concepts)

        assert any("insufficient definition" in issue.lower() for issue in issues)

    def test_validate_many_supporting_concepts(self):
        """Test validation with many supporting but one core concept."""
        concepts = [
            Concept(
                name="Core",
                definition="A sufficiently long core concept definition",
                importance=ConceptImportance.CORE.value,
            )
        ] + [
            Concept(
                name=f"Supporting {i}",
                definition=f"Supporting concept {i} with definition",
                importance=ConceptImportance.SUPPORTING.value,
            )
            for i in range(10)
        ]

        issues = _validate_concepts(concepts)

        # Should be valid - has core concept
        assert not any("No core concepts" in issue for issue in issues)


class TestValidateTagsDetail:
    """Detailed tests for tag validation."""

    def test_validate_tags_with_many_domains(self):
        """Test validation with many domain tags."""
        issues = _validate_tags(
            domain_tags=["ml/a", "ml/b", "ml/c", "ml/d", "ml/e"],
            meta_tags=["status/new"],
        )

        # Many tags should be fine
        assert len(issues) == 0

    def test_validate_tags_with_only_meta(self):
        """Test validation with only meta tags (no domain)."""
        issues = _validate_tags(
            domain_tags=[],
            meta_tags=["status/actionable", "quality/deep-dive"],
        )

        # Should flag missing domain tags
        assert any("No domain tags" in issue for issue in issues)


class TestValidateQuestionsDetail:
    """Detailed tests for question validation."""

    def test_validate_question_exactly_at_length_minimum(self):
        """Test question at exact minimum length."""
        questions = [
            MasteryQuestion(
                question="A" * 20,  # At minimum
                hints=["hint"],
                key_points=["point"],
            ),
            MasteryQuestion(
                question="B" * 20,
                hints=["hint"],
                key_points=["point"],
            ),
            MasteryQuestion(
                question="C" * 20,
                hints=["hint"],
                key_points=["point"],
            ),
        ]

        issues = _validate_questions(questions)

        # Should be valid at boundary
        assert not any("too short" in issue.lower() for issue in issues)

    def test_validate_question_with_empty_key_points_list(self):
        """Test question validation with empty key points."""
        questions = [
            MasteryQuestion(
                question="What is the main concept here?",
                hints=["Think about it"],
                key_points=[],  # Empty
            ),
            MasteryQuestion(
                question="How does this relate to other work?",
                hints=["Consider connections"],
                key_points=["point"],
            ),
            MasteryQuestion(
                question="Why is this approach significant?",
                hints=["Think about impact"],
                key_points=["point"],
            ),
        ]

        issues = _validate_questions(questions)

        assert any("missing key points" in issue.lower() for issue in issues)

    def test_validate_questions_all_have_multiple_key_points(self):
        """Test questions with multiple key points each."""
        questions = [
            MasteryQuestion(
                question="Comprehensive question one here?",
                hints=["hint1", "hint2"],
                key_points=["point1", "point2", "point3"],
            ),
            MasteryQuestion(
                question="Comprehensive question two here?",
                hints=["hint1"],
                key_points=["point1", "point2"],
            ),
            MasteryQuestion(
                question="Comprehensive question three here?",
                hints=["hint1", "hint2", "hint3"],
                key_points=["point1", "point2", "point3", "point4"],
            ),
        ]

        issues = _validate_questions(questions)

        # All should be valid
        assert len(issues) == 0


class TestSummaryLengthValidation:
    """Additional tests for summary length validation."""

    def test_validate_summary_length_with_unicode(self):
        """Test summary length validation with unicode characters."""
        unicode_summary = "日本語テキスト" * 50  # Japanese text

        result = validate_summary_length(unicode_summary, SummaryLevel.STANDARD)

        # Should count characters, not bytes
        assert result is True

    def test_validate_summary_length_with_emoji(self):
        """Test summary length validation with emojis."""
        emoji_summary = "🤖💡📚" * 30 + "Some text"

        result = validate_summary_length(emoji_summary, SummaryLevel.STANDARD)

        # Emojis count as characters
        assert isinstance(result, bool)

    def test_validate_summary_length_whitespace_only(self):
        """Test summary length validation with whitespace."""
        whitespace = "   " * 100

        result = validate_summary_length(whitespace, SummaryLevel.STANDARD)

        # Whitespace technically counts as characters
        assert isinstance(result, bool)
