"""
Unit tests for LLM processing stages.

Tests each processing stage in isolation with mocked LLM client.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.enums import (
    ContentType,
    AnnotationType,
    ContentDomain,
    ContentComplexity,
    ContentLength,
    ConceptImportance,
    SummaryLevel,
    RelationshipType,
    FollowupTaskType,
    FollowupPriority,
    FollowupTimeEstimate,
    QuestionType,
    QuestionDifficulty,
)
from app.models.content import UnifiedContent, Annotation
from app.models.processing import (
    ContentAnalysis,
    Concept,
    ExtractionResult,
    TagAssignment,
    FollowupTask,
    MasteryQuestion,
)
from app.pipelines.utils.cost_types import LLMUsage
from app.services.processing.stages.content_analysis import (
    analyze_content,
    _default_analysis,
)
from app.services.processing.stages.summarization import (
    generate_summary,
    generate_all_summaries,
    _format_annotations,
)
from app.services.processing.stages.extraction import (
    extract_concepts,
    _validate_importance,
)
from app.services.processing.stages.tagging import assign_tags
from app.services.processing.stages.connections import (
    discover_connections,
    _evaluate_connection,
)
from app.services.processing.stages.followups import (
    generate_followups,
    _format_annotations as format_followup_annotations,
    _validate_task_type,
    _validate_priority,
    _validate_time,
)
from app.services.processing.stages.questions import (
    generate_mastery_questions,
    _validate_question_type,
    _validate_difficulty,
)
from app.services.processing.stages.taxonomy_loader import (
    TagTaxonomy,
    TagTaxonomyLoader,
)


# =============================================================================
# Helper Functions
# =============================================================================


def make_analysis_response(
    content_type: str = "paper",
    domain: str = "ml",
    complexity: str = "advanced",
    length: str = "medium",
    topics: list = None,
    has_code: bool = False,
    has_math: bool = True,
) -> dict:
    """Create a standard analysis response dict."""
    return {
        "content_type": content_type,
        "domain": domain,
        "complexity": complexity,
        "estimated_length": length,
        "has_code": has_code,
        "has_math": has_math,
        "has_diagrams": True,
        "key_topics": topics or ["transformers", "attention"],
        "language": "en",
    }


def make_extraction_response(concepts: list = None, findings: list = None) -> dict:
    """Create a standard extraction response dict."""
    return {
        "concepts": concepts
        or [
            {"name": "Transformer", "definition": "Architecture", "importance": "CORE"}
        ],
        "key_findings": findings or ["Finding 1"],
        "methodologies": ["Multi-head attention"],
        "tools_mentioned": ["PyTorch"],
        "people_mentioned": ["Vaswani"],
    }


def make_tagging_response(domain_tags: list = None, meta_tags: list = None) -> dict:
    """Create a standard tagging response dict."""
    return {
        "domain_tags": domain_tags or ["ml/transformers/attention"],
        "meta_tags": meta_tags or ["status/actionable", "quality/deep-dive"],
        "suggested_new_tags": [],
        "reasoning": "Tagged as ML/transformers content",
    }


def make_followup_response(tasks: list = None) -> dict:
    """Create a standard followup response dict."""
    return {
        "tasks": tasks
        or [
            {
                "task": "Implement transformer",
                "type": "PRACTICE",
                "priority": "HIGH",
                "estimated_time": "2HR_PLUS",
            },
            {
                "task": "Read BERT paper",
                "type": "RESEARCH",
                "priority": "MEDIUM",
                "estimated_time": "1HR",
            },
        ]
    }


def make_question_response(questions: list = None) -> dict:
    """Create a standard question response dict."""
    return {
        "questions": questions
        or [
            {
                "question": "What is the advantage of self-attention?",
                "type": "conceptual",
                "difficulty": "intermediate",
                "hints": ["Think about parallelization"],
                "key_points": ["Parallel computation"],
            }
        ]
    }


def make_connection_response(
    has_connection: bool = True, strength: float = 0.8
) -> dict:
    """Create a standard connection evaluation response dict."""
    return {
        "has_connection": has_connection,
        "relationship_type": RelationshipType.EXTENDS,
        "strength": strength,
        "explanation": "Related content",
    }


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def sample_content() -> UnifiedContent:
    """Create sample content for testing."""
    return UnifiedContent(
        id="test-content-123",
        source_type=ContentType.PAPER,
        title="Attention Is All You Need",
        authors=["Vaswani et al."],
        full_text="""
        Abstract: We propose a new simple network architecture, the Transformer,
        based solely on attention mechanisms, dispensing with recurrence and convolutions.

        Introduction: Recurrent neural networks have been established as state of the art
        in sequence modeling. We propose the Transformer architecture.

        Results: We achieve state-of-the-art results on machine translation benchmarks.
        """,
        annotations=[
            Annotation(
                type=AnnotationType.DIGITAL_HIGHLIGHT,
                content="attention mechanisms",
                page_number=1,
            ),
            Annotation(
                type=AnnotationType.HANDWRITTEN_NOTE,
                content="Key insight about self-attention",
                page_number=2,
                context="self-attention layer",
            ),
        ],
        source_url="https://arxiv.org/abs/1706.03762",
    )


@pytest.fixture
def sample_analysis() -> ContentAnalysis:
    """Create sample content analysis for testing."""
    return ContentAnalysis(
        content_type="paper",
        domain="ml",
        complexity="advanced",
        estimated_length="medium",
        has_code=False,
        has_math=True,
        has_diagrams=True,
        key_topics=["transformers", "attention", "neural networks"],
        language="en",
    )


@pytest.fixture
def sample_extraction() -> ExtractionResult:
    """Create sample extraction result for testing."""
    return ExtractionResult(
        concepts=[
            Concept(
                name="Transformer",
                definition="Architecture based on self-attention",
                importance=ConceptImportance.CORE.value,
                related_concepts=["attention"],
            ),
            Concept(
                name="Self-attention",
                definition="Mechanism relating positions",
                importance=ConceptImportance.CORE.value,
                related_concepts=["transformer"],
            ),
        ],
        key_findings=[
            "Transformers outperform RNNs",
            "Self-attention is parallelizable",
        ],
        methodologies=["Multi-head attention"],
        tools_mentioned=["TensorFlow"],
        people_mentioned=["Vaswani"],
    )


@pytest.fixture
def mock_llm_client() -> MagicMock:
    """Create a mock LLM client."""
    mock = MagicMock()
    mock.complete = AsyncMock()
    mock.embed = AsyncMock()
    return mock


@pytest.fixture
def mock_neo4j_client() -> MagicMock:
    """Create a mock Neo4j client."""
    mock = MagicMock()
    mock.vector_search = AsyncMock(return_value=[])
    return mock


@pytest.fixture
def sample_usage() -> LLMUsage:
    """Create sample LLM usage for testing."""
    return LLMUsage(
        model="openai/gpt-4o-mini",
        provider="openai",
        request_type="text",
        prompt_tokens=100,
        completion_tokens=50,
        total_tokens=150,
        cost_usd=0.001,
        latency_ms=500,
    )


@pytest.fixture
def sample_taxonomy() -> TagTaxonomy:
    """Create sample tag taxonomy for testing."""
    return TagTaxonomy(
        domains=[
            "ml/transformers/attention",
            "ml/transformers/llms",
            "ml/training/optimization",
            "systems/distributed/consensus",
        ],
        status=["actionable", "review", "archived"],
        quality=["foundational", "deep-dive", "reference"],
    )


# =============================================================================
# Content Analysis Stage Tests
# =============================================================================


class TestContentAnalysis:
    """Tests for the content analysis stage."""

    @pytest.mark.asyncio
    async def test_analyze_content_success(
        self, sample_content, mock_llm_client, sample_usage
    ):
        """Test successful content analysis."""
        mock_llm_client.complete.return_value = (make_analysis_response(), sample_usage)

        result, usages = await analyze_content(sample_content, mock_llm_client)

        assert isinstance(result, ContentAnalysis)
        assert result.content_type == "paper"
        assert result.domain == "ml"
        assert result.complexity == "advanced"
        assert len(usages) == 1
        mock_llm_client.complete.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.parametrize("empty_text", ["", "   \n\t   "])
    async def test_analyze_content_empty_text(
        self, sample_content, mock_llm_client, empty_text
    ):
        """Test content analysis with empty/whitespace text returns defaults."""
        sample_content.full_text = empty_text

        result, usages = await analyze_content(sample_content, mock_llm_client)

        assert isinstance(result, ContentAnalysis)
        assert result.content_type == sample_content.source_type.value
        assert len(usages) == 0
        mock_llm_client.complete.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "field,invalid_value,expected_default",
        [
            ("domain", "invalid_domain", ContentDomain.GENERAL.value.lower()),
            (
                "complexity",
                "invalid_level",
                ContentComplexity.INTERMEDIATE.value.lower(),
            ),
        ],
    )
    async def test_analyze_content_normalizes_invalid_values(
        self,
        sample_content,
        mock_llm_client,
        sample_usage,
        field,
        invalid_value,
        expected_default,
    ):
        """Test that invalid enum values are normalized."""
        response = make_analysis_response()
        response[field] = invalid_value
        mock_llm_client.complete.return_value = (response, sample_usage)

        result, _ = await analyze_content(sample_content, mock_llm_client)

        assert getattr(result, field) == expected_default

    @pytest.mark.asyncio
    async def test_analyze_content_exception_returns_defaults(
        self, sample_content, mock_llm_client
    ):
        """Test that exception returns default analysis."""
        mock_llm_client.complete.side_effect = Exception("LLM error")

        result, usages = await analyze_content(sample_content, mock_llm_client)

        assert isinstance(result, ContentAnalysis)
        assert result.content_type == sample_content.source_type.value
        assert len(usages) == 0

    def test_default_analysis(self, sample_content):
        """Test the default analysis fallback."""
        result = _default_analysis(sample_content)

        assert result.content_type == sample_content.source_type.value
        assert result.domain == ContentDomain.GENERAL.value.lower()
        assert result.complexity == ContentComplexity.INTERMEDIATE.value.lower()
        assert result.estimated_length == ContentLength.MEDIUM.value.lower()

    @pytest.mark.asyncio
    async def test_analyze_content_long_text_truncation(
        self, sample_content, mock_llm_client, sample_usage
    ):
        """Test that very long content is truncated before analysis."""
        sample_content.full_text = "A" * 100000
        mock_llm_client.complete.return_value = (
            make_analysis_response(length="long"),
            sample_usage,
        )

        result, _ = await analyze_content(sample_content, mock_llm_client)

        assert isinstance(result, ContentAnalysis)
        call_args = str(mock_llm_client.complete.call_args)
        assert len(call_args) < 100000


# =============================================================================
# Summarization Stage Tests
# =============================================================================


class TestSummarization:
    """Tests for the summarization stage."""

    @pytest.mark.asyncio
    async def test_generate_summary_success(
        self, sample_content, sample_analysis, mock_llm_client, sample_usage
    ):
        """Test successful summary generation."""
        mock_llm_client.complete.return_value = (
            "This paper introduces the Transformer architecture.",
            sample_usage,
        )

        result, usage = await generate_summary(
            sample_content, sample_analysis, SummaryLevel.BRIEF, mock_llm_client
        )

        assert isinstance(result, str)
        assert "Transformer" in result
        assert isinstance(usage, LLMUsage)

    @pytest.mark.asyncio
    async def test_generate_all_summaries(
        self, sample_content, sample_analysis, mock_llm_client, sample_usage
    ):
        """Test generating all summary levels."""
        mock_llm_client.complete.return_value = ("Summary at level X", sample_usage)

        summaries, usages = await generate_all_summaries(
            sample_content, sample_analysis, mock_llm_client
        )

        assert len(summaries) == 3
        assert all(level.value in summaries for level in SummaryLevel)
        assert len(usages) == 3

    @pytest.mark.asyncio
    async def test_generate_summary_exception_returns_error_message(
        self, sample_content, sample_analysis, mock_llm_client
    ):
        """Test that exceptions are handled in generate_all_summaries."""
        mock_llm_client.complete.side_effect = Exception("LLM error")

        summaries, _ = await generate_all_summaries(
            sample_content, sample_analysis, mock_llm_client
        )

        assert len(summaries) == 3
        assert all("failed" in s.lower() for s in summaries.values())

    @pytest.mark.parametrize(
        "annotations,expected_contains",
        [
            ([], "None provided"),
            (None, "None provided"),
        ],
    )
    def test_format_annotations_empty(
        self, sample_content, annotations, expected_contains
    ):
        """Test annotation formatting with no annotations."""
        sample_content.annotations = annotations or []
        result = _format_annotations(sample_content, max_annotations=20)
        assert result == expected_contains

    def test_format_annotations_with_annotations(self, sample_content):
        """Test annotation formatting with annotations present."""
        result = _format_annotations(sample_content, max_annotations=20)
        assert "attention mechanisms" in result
        assert "Key insight" in result
        assert "[p.1]" in result

    def test_format_annotations_respects_max_count(self, sample_content):
        """Test that annotation formatting respects max count."""
        sample_content.annotations = [
            Annotation(
                type=AnnotationType.DIGITAL_HIGHLIGHT,
                content=f"Highlight {i}",
                page_number=i,
            )
            for i in range(20)
        ]
        result = _format_annotations(sample_content, max_annotations=5)
        assert "Highlight 0" in result
        assert "Highlight 4" in result
        assert "Highlight 19" not in result


# =============================================================================
# Extraction Stage Tests
# =============================================================================


class TestExtraction:
    """Tests for the concept extraction stage."""

    @pytest.mark.asyncio
    async def test_extract_concepts_success(
        self, sample_content, sample_analysis, mock_llm_client, sample_usage
    ):
        """Test successful concept extraction."""
        mock_llm_client.complete.return_value = (
            make_extraction_response(),
            sample_usage,
        )

        result, usages = await extract_concepts(
            sample_content, sample_analysis, mock_llm_client
        )

        assert isinstance(result, ExtractionResult)
        assert len(result.concepts) == 1
        assert result.concepts[0].name == "Transformer"
        assert len(usages) == 1

    @pytest.mark.asyncio
    async def test_extract_concepts_empty_text(
        self, sample_content, sample_analysis, mock_llm_client
    ):
        """Test extraction with empty text returns empty result."""
        sample_content.full_text = ""

        result, usages = await extract_concepts(
            sample_content, sample_analysis, mock_llm_client
        )

        assert len(result.concepts) == 0
        assert len(usages) == 0
        mock_llm_client.complete.assert_not_called()

    @pytest.mark.asyncio
    async def test_extract_concepts_skips_empty_names(
        self, sample_content, sample_analysis, mock_llm_client, sample_usage
    ):
        """Test that concepts with empty names are skipped."""
        mock_llm_client.complete.return_value = (
            make_extraction_response(
                concepts=[
                    {"name": "", "definition": "Empty"},
                    {"name": "Valid", "definition": "Valid"},
                ]
            ),
            sample_usage,
        )

        result, _ = await extract_concepts(
            sample_content, sample_analysis, mock_llm_client
        )

        assert len(result.concepts) == 1
        assert result.concepts[0].name == "Valid"

    @pytest.mark.asyncio
    async def test_extract_concepts_exception_returns_empty(
        self, sample_content, sample_analysis, mock_llm_client
    ):
        """Test that exception returns empty result."""
        mock_llm_client.complete.side_effect = Exception("LLM error")

        result, usages = await extract_concepts(
            sample_content, sample_analysis, mock_llm_client
        )

        assert len(result.concepts) == 0
        assert len(usages) == 0

    @pytest.mark.parametrize(
        "input_val,expected",
        [
            ("CORE", "CORE"),
            ("SUPPORTING", "SUPPORTING"),
            ("TANGENTIAL", "TANGENTIAL"),
            ("core", "CORE"),
            ("INVALID", ConceptImportance.SUPPORTING.value),
            ("", ConceptImportance.SUPPORTING.value),
        ],
    )
    def test_validate_importance(self, input_val, expected):
        """Test importance validation with various values."""
        assert _validate_importance(input_val) == expected

    @pytest.mark.asyncio
    async def test_extract_normalizes_importance(
        self, sample_content, sample_analysis, mock_llm_client, sample_usage
    ):
        """Test that various importance formats are normalized."""
        mock_llm_client.complete.return_value = (
            make_extraction_response(
                concepts=[
                    {"name": "A", "definition": "Def A", "importance": "core"},
                    {"name": "B", "definition": "Def B", "importance": "supporting"},
                ]
            ),
            sample_usage,
        )

        result, _ = await extract_concepts(
            sample_content, sample_analysis, mock_llm_client
        )

        for concept in result.concepts:
            assert concept.importance in ["CORE", "SUPPORTING", "TANGENTIAL"]


# =============================================================================
# Tagging Stage Tests
# =============================================================================


class TestTagging:
    """Tests for the tagging stage."""

    @pytest.mark.asyncio
    async def test_assign_tags_success(
        self, sample_analysis, mock_llm_client, sample_usage, sample_taxonomy
    ):
        """Test successful tag assignment."""
        mock_llm_client.complete.return_value = (make_tagging_response(), sample_usage)

        result, usages = await assign_tags(
            "Attention Is All You Need",
            sample_analysis,
            "Paper about transformers",
            mock_llm_client,
            sample_taxonomy,
        )

        assert isinstance(result, TagAssignment)
        assert "ml/transformers/attention" in result.domain_tags
        assert len(usages) == 1

    @pytest.mark.asyncio
    async def test_assign_tags_filters_invalid_tags(
        self, sample_analysis, mock_llm_client, sample_usage, sample_taxonomy
    ):
        """Test that invalid tags are filtered out."""
        mock_llm_client.complete.return_value = (
            make_tagging_response(
                domain_tags=["ml/transformers/attention", "invalid/tag"],
                meta_tags=["status/actionable", "invalid/meta"],
            ),
            sample_usage,
        )

        result, _ = await assign_tags(
            "Test", sample_analysis, "Test", mock_llm_client, sample_taxonomy
        )

        assert "ml/transformers/attention" in result.domain_tags
        assert "invalid/tag" not in result.domain_tags
        assert "status/actionable" in result.meta_tags
        assert "invalid/meta" not in result.meta_tags

    @pytest.mark.asyncio
    async def test_assign_tags_exception_returns_default(
        self, sample_analysis, mock_llm_client, sample_taxonomy
    ):
        """Test that exception returns default tag assignment."""
        mock_llm_client.complete.side_effect = Exception("LLM error")

        result, usages = await assign_tags(
            "Test", sample_analysis, "Test", mock_llm_client, sample_taxonomy
        )

        assert isinstance(result, TagAssignment)
        assert "status/review" in result.meta_tags
        assert len(usages) == 0


# =============================================================================
# Connection Discovery Stage Tests
# =============================================================================


class TestConnectionDiscovery:
    """Tests for the connection discovery stage."""

    @pytest.mark.asyncio
    async def test_discover_connections_success(
        self,
        sample_content,
        sample_extraction,
        sample_analysis,
        mock_llm_client,
        mock_neo4j_client,
        sample_usage,
    ):
        """Test successful connection discovery."""
        mock_llm_client.embed.return_value = ([[0.1] * 1536], sample_usage)
        mock_neo4j_client.vector_search.return_value = [
            {"id": "other-1", "title": "RNN Paper", "summary": "About RNNs"}
        ]
        mock_llm_client.complete.return_value = (
            make_connection_response(),
            sample_usage,
        )

        connections, _ = await discover_connections(
            sample_content,
            "Paper about transformers",
            sample_extraction,
            sample_analysis,
            mock_llm_client,
            mock_neo4j_client,
        )

        assert len(connections) == 1
        assert connections[0].target_title == "RNN Paper"
        assert connections[0].relationship_type == RelationshipType.EXTENDS

    @pytest.mark.asyncio
    async def test_discover_connections_no_candidates(
        self,
        sample_content,
        sample_extraction,
        sample_analysis,
        mock_llm_client,
        mock_neo4j_client,
        sample_usage,
    ):
        """Test connection discovery with no candidates found."""
        mock_llm_client.embed.return_value = ([[0.1] * 1536], sample_usage)
        mock_neo4j_client.vector_search.return_value = []

        connections, _ = await discover_connections(
            sample_content,
            "Paper",
            sample_extraction,
            sample_analysis,
            mock_llm_client,
            mock_neo4j_client,
        )

        assert len(connections) == 0

    @pytest.mark.asyncio
    async def test_discover_connections_skips_self(
        self,
        sample_content,
        sample_extraction,
        sample_analysis,
        mock_llm_client,
        mock_neo4j_client,
        sample_usage,
    ):
        """Test that self-connections are skipped."""
        mock_llm_client.embed.return_value = ([[0.1] * 1536], sample_usage)
        mock_neo4j_client.vector_search.return_value = [
            {"id": sample_content.id, "title": sample_content.title, "summary": "Self"}
        ]

        connections, _ = await discover_connections(
            sample_content,
            "Paper",
            sample_extraction,
            sample_analysis,
            mock_llm_client,
            mock_neo4j_client,
        )

        assert len(connections) == 0

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "has_connection,strength,expect_connection",
        [
            (True, 0.8, True),
            (True, 0.2, False),  # Below threshold
            (False, 0.8, False),  # No connection
        ],
    )
    async def test_evaluate_connection_scenarios(
        self, mock_llm_client, sample_usage, has_connection, strength, expect_connection
    ):
        """Test various connection evaluation scenarios."""
        mock_llm_client.complete.return_value = (
            make_connection_response(has_connection, strength),
            sample_usage,
        )

        connection, _ = await _evaluate_connection(
            "Test",
            "Summary",
            ["concept"],
            {"id": "c1", "title": "Candidate", "summary": "Sum"},
            mock_llm_client,
            0.4,
        )

        assert (connection is not None) == expect_connection


# =============================================================================
# Follow-up Generation Stage Tests
# =============================================================================


class TestFollowupGeneration:
    """Tests for the follow-up task generation stage."""

    @pytest.mark.asyncio
    async def test_generate_followups_success(
        self,
        sample_content,
        sample_analysis,
        sample_extraction,
        mock_llm_client,
        sample_usage,
    ):
        """Test successful follow-up generation."""
        mock_llm_client.complete.return_value = (make_followup_response(), sample_usage)

        tasks, usages = await generate_followups(
            sample_content,
            sample_analysis,
            "Summary",
            sample_extraction,
            mock_llm_client,
        )

        assert len(tasks) == 2
        assert all(isinstance(t, FollowupTask) for t in tasks)
        assert tasks[0].task == "Implement transformer"
        assert tasks[0].task_type == "PRACTICE"
        assert len(usages) == 1

    @pytest.mark.asyncio
    async def test_generate_followups_skips_empty_tasks(
        self,
        sample_content,
        sample_analysis,
        sample_extraction,
        mock_llm_client,
        sample_usage,
    ):
        """Test that empty tasks are skipped."""
        mock_llm_client.complete.return_value = (
            make_followup_response(
                tasks=[
                    {"task": "", "type": "RESEARCH"},
                    {"task": "Valid", "type": "PRACTICE"},
                ]
            ),
            sample_usage,
        )

        tasks, _ = await generate_followups(
            sample_content,
            sample_analysis,
            "Summary",
            sample_extraction,
            mock_llm_client,
        )

        assert len(tasks) == 1
        assert tasks[0].task == "Valid"

    @pytest.mark.asyncio
    async def test_generate_followups_exception_returns_empty(
        self, sample_content, sample_analysis, sample_extraction, mock_llm_client
    ):
        """Test that exception returns empty list."""
        mock_llm_client.complete.side_effect = Exception("LLM error")

        tasks, usages = await generate_followups(
            sample_content,
            sample_analysis,
            "Summary",
            sample_extraction,
            mock_llm_client,
        )

        assert len(tasks) == 0
        assert len(usages) == 0

    @pytest.mark.parametrize(
        "input_val,expected",
        [
            ("RESEARCH", "RESEARCH"),
            ("PRACTICE", "PRACTICE"),
            ("research", "RESEARCH"),
            ("INVALID", FollowupTaskType.RESEARCH.value),
        ],
    )
    def test_validate_task_type(self, input_val, expected):
        """Test task type validation."""
        assert _validate_task_type(input_val) == expected

    @pytest.mark.parametrize(
        "input_val,expected",
        [
            ("HIGH", "HIGH"),
            ("MEDIUM", "MEDIUM"),
            ("low", "LOW"),
            ("INVALID", FollowupPriority.MEDIUM.value),
        ],
    )
    def test_validate_priority(self, input_val, expected):
        """Test priority validation."""
        assert _validate_priority(input_val) == expected

    @pytest.mark.parametrize(
        "input_val,expected",
        [
            ("15MIN", "15MIN"),
            ("30MIN", "30MIN"),
            ("1HR", "1HR"),
            ("INVALID", FollowupTimeEstimate.THIRTY_MIN.value),
        ],
    )
    def test_validate_time(self, input_val, expected):
        """Test time estimate validation."""
        assert _validate_time(input_val) == expected

    def test_format_followup_annotations(self, sample_content):
        """Test annotation formatting for followups."""
        result = format_followup_annotations(sample_content)
        assert "attention mechanisms" in result
        assert "Key insight" in result

    def test_format_followup_annotations_empty(self, sample_content):
        """Test annotation formatting with no annotations."""
        sample_content.annotations = []
        assert format_followup_annotations(sample_content) == "None provided"


# =============================================================================
# Question Generation Stage Tests
# =============================================================================


class TestQuestionGeneration:
    """Tests for the mastery question generation stage."""

    @pytest.mark.asyncio
    async def test_generate_mastery_questions_success(
        self,
        sample_content,
        sample_analysis,
        sample_extraction,
        mock_llm_client,
        sample_usage,
    ):
        """Test successful question generation."""
        mock_llm_client.complete.return_value = (make_question_response(), sample_usage)

        questions, usages = await generate_mastery_questions(
            sample_content,
            sample_analysis,
            "Summary",
            sample_extraction,
            mock_llm_client,
        )

        assert len(questions) == 1
        assert all(isinstance(q, MasteryQuestion) for q in questions)
        assert questions[0].question_type == "conceptual"
        assert questions[0].difficulty == "intermediate"
        assert len(usages) == 1

    @pytest.mark.asyncio
    async def test_generate_questions_skips_empty_questions(
        self,
        sample_content,
        sample_analysis,
        sample_extraction,
        mock_llm_client,
        sample_usage,
    ):
        """Test that empty questions are skipped."""
        mock_llm_client.complete.return_value = (
            make_question_response(
                questions=[
                    {"question": "", "type": "conceptual"},
                    {"question": "Valid?", "type": "application"},
                ]
            ),
            sample_usage,
        )

        questions, _ = await generate_mastery_questions(
            sample_content,
            sample_analysis,
            "Summary",
            sample_extraction,
            mock_llm_client,
        )

        assert len(questions) == 1
        assert questions[0].question == "Valid?"

    @pytest.mark.asyncio
    async def test_generate_questions_exception_returns_empty(
        self, sample_content, sample_analysis, sample_extraction, mock_llm_client
    ):
        """Test that exception returns empty list."""
        mock_llm_client.complete.side_effect = Exception("LLM error")

        questions, usages = await generate_mastery_questions(
            sample_content,
            sample_analysis,
            "Summary",
            sample_extraction,
            mock_llm_client,
        )

        assert len(questions) == 0
        assert len(usages) == 0

    @pytest.mark.parametrize(
        "input_val,expected",
        [
            ("conceptual", "conceptual"),
            ("application", "application"),
            ("CONCEPTUAL", "conceptual"),
            ("INVALID", QuestionType.CONCEPTUAL.value),
        ],
    )
    def test_validate_question_type(self, input_val, expected):
        """Test question type validation."""
        assert _validate_question_type(input_val) == expected

    @pytest.mark.parametrize(
        "input_val,expected",
        [
            ("foundational", "foundational"),
            ("intermediate", "intermediate"),
            ("ADVANCED", "advanced"),
            ("INVALID", QuestionDifficulty.INTERMEDIATE.value),
        ],
    )
    def test_validate_difficulty(self, input_val, expected):
        """Test difficulty validation."""
        assert _validate_difficulty(input_val) == expected

    @pytest.mark.asyncio
    async def test_question_handles_missing_hints(
        self,
        sample_content,
        sample_analysis,
        sample_extraction,
        mock_llm_client,
        sample_usage,
    ):
        """Test question generation with missing hints."""
        mock_llm_client.complete.return_value = (
            make_question_response(
                questions=[
                    {
                        "question": "What?",
                        "type": "conceptual",
                        "difficulty": "intermediate",
                        "key_points": ["point"],
                    }
                ]
            ),
            sample_usage,
        )

        questions, _ = await generate_mastery_questions(
            sample_content,
            sample_analysis,
            "Summary",
            sample_extraction,
            mock_llm_client,
        )

        assert len(questions) == 1
        assert isinstance(questions[0].hints, list)


# =============================================================================
# Tag Taxonomy Tests
# =============================================================================


class TestTagTaxonomy:
    """Tests for the tag taxonomy and loader."""

    @pytest.mark.parametrize(
        "tag,expected",
        [
            ("ml/transformers/attention", True),
            ("invalid/tag", False),
            ("ml/transformers", False),  # Partial
            ("ML/TRANSFORMERS/ATTENTION", False),  # Case sensitive
        ],
    )
    def test_taxonomy_validate_domain_tag(self, sample_taxonomy, tag, expected):
        """Test domain tag validation."""
        assert sample_taxonomy.validate_domain_tag(tag) is expected

    @pytest.mark.parametrize(
        "tag,expected",
        [
            ("status/actionable", True),
            ("quality/deep-dive", True),
            ("invalid/meta", False),
        ],
    )
    def test_taxonomy_validate_meta_tag(self, sample_taxonomy, tag, expected):
        """Test meta tag validation."""
        assert sample_taxonomy.validate_meta_tag(tag) is expected

    def test_taxonomy_meta_property(self, sample_taxonomy):
        """Test that meta property combines status and quality."""
        meta = sample_taxonomy.meta
        assert all(f"status/{s}" in meta for s in sample_taxonomy.status)
        assert all(f"quality/{q}" in meta for q in sample_taxonomy.quality)

    def test_taxonomy_filter_valid_tags(self, sample_taxonomy):
        """Test filtering valid tags from a list."""
        tags = [
            "ml/transformers/attention",
            "invalid/domain",
            "status/actionable",
            "invalid/meta",
        ]
        domain_tags, meta_tags = sample_taxonomy.filter_valid_tags(tags)
        assert domain_tags == ["ml/transformers/attention"]
        assert meta_tags == ["status/actionable"]

    def test_taxonomy_get_invalid_tags(self, sample_taxonomy):
        """Test getting invalid tags from a list."""
        tags = ["ml/transformers/attention", "invalid/tag", "status/actionable"]
        assert sample_taxonomy.get_invalid_tags(tags) == ["invalid/tag"]

    def test_taxonomy_loader_singleton(self):
        """Test that TagTaxonomyLoader is a singleton."""
        assert TagTaxonomyLoader() is TagTaxonomyLoader()

    def test_taxonomy_loader_invalidate_cache(self):
        """Test cache invalidation."""
        TagTaxonomyLoader._taxonomy = "cached"
        TagTaxonomyLoader._last_loaded = 12345
        TagTaxonomyLoader.invalidate_cache()
        assert TagTaxonomyLoader._taxonomy is None
        assert TagTaxonomyLoader._last_loaded is None

    @pytest.mark.parametrize(
        "tag_section,expected",
        [
            ({"actionable": "Desc 1", "review": "Desc 2"}, ["actionable", "review"]),
            (["actionable", "review"], ["actionable", "review"]),
            ("invalid", []),
        ],
    )
    def test_extract_tag_names(self, tag_section, expected):
        """Test extracting tag names from various formats."""
        assert TagTaxonomyLoader._extract_tag_names(tag_section) == expected

    def test_flatten_domain_tags_simple(self):
        """Test flattening simple domain structure."""
        tags = TagTaxonomyLoader._flatten_domain_tags({"ml": None, "systems": None})
        assert "ml" in tags
        assert "systems" in tags

    def test_flatten_domain_tags_nested(self):
        """Test flattening nested domain structure."""
        domains = {
            "ml": {"categories": {"transformers": {"topics": ["attention", "llms"]}}}
        }
        tags = TagTaxonomyLoader._flatten_domain_tags(domains)
        assert "ml/transformers/attention" in tags
        assert "ml/transformers/llms" in tags

    def test_process_topics_simple(self):
        """Test processing simple topic list."""
        tags = TagTaxonomyLoader._process_topics(
            ["attention", "llms"], "ml/transformers"
        )
        assert "ml/transformers/attention" in tags
        assert "ml/transformers/llms" in tags

    def test_process_topics_with_descriptions(self):
        """Test processing topics with descriptions."""
        topics = [
            {"attention": "Attention mechanisms"},
            {"llms": "Large language models"},
        ]
        tags = TagTaxonomyLoader._process_topics(topics, "ml/transformers")
        assert "ml/transformers/attention" in tags
        assert "ml/transformers/llms" in tags

    def test_taxonomy_handles_empty_categories(self):
        """Test taxonomy with empty categories."""
        taxonomy = TagTaxonomy(domains=[], status=[], quality=[])
        assert len(taxonomy.all_tags) == 0
        assert taxonomy.validate_domain_tag("any/tag") is False


# =============================================================================
# Edge Case Tests - Consolidated
# =============================================================================


class TestEdgeCases:
    """Consolidated edge case tests across all stages."""

    @pytest.mark.asyncio
    async def test_analysis_handles_malformed_json(
        self, sample_content, mock_llm_client, sample_usage
    ):
        """Test handling of malformed JSON response from LLM."""
        mock_llm_client.complete.return_value = ({"incomplete": True}, sample_usage)
        result, _ = await analyze_content(sample_content, mock_llm_client)
        assert isinstance(result, ContentAnalysis)

    @pytest.mark.asyncio
    async def test_analysis_validates_length_enum(
        self, sample_content, mock_llm_client, sample_usage
    ):
        """Test that invalid length values are normalized."""
        response = make_analysis_response()
        response["estimated_length"] = "invalid_length"
        mock_llm_client.complete.return_value = (response, sample_usage)

        result, _ = await analyze_content(sample_content, mock_llm_client)
        assert result.estimated_length in [e.value.lower() for e in ContentLength]

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "content_type", [ContentType.ARTICLE, ContentType.BOOK, ContentType.PAPER]
    )
    async def test_analyze_different_source_types(
        self, mock_llm_client, sample_usage, content_type
    ):
        """Test analysis with different content source types."""
        content = UnifiedContent(
            id=f"test-{content_type.value}",
            source_type=content_type,
            title="Test",
            full_text="Some text",
        )
        mock_llm_client.complete.return_value = (
            make_analysis_response("article"),
            sample_usage,
        )
        result, _ = await analyze_content(content, mock_llm_client)
        assert isinstance(result, ContentAnalysis)

    @pytest.mark.asyncio
    async def test_summarization_handles_large_annotation_count(
        self, sample_content, sample_analysis, mock_llm_client, sample_usage
    ):
        """Test summarization with many annotations."""
        sample_content.annotations = [
            Annotation(
                type=AnnotationType.DIGITAL_HIGHLIGHT,
                content=f"Highlight {i}",
                page_number=i % 10,
            )
            for i in range(50)
        ]
        mock_llm_client.complete.return_value = ("Summary text", sample_usage)
        summaries, _ = await generate_all_summaries(
            sample_content, sample_analysis, mock_llm_client
        )
        assert len(summaries) == 3

    @pytest.mark.asyncio
    async def test_extract_handles_unicode_content(
        self, sample_content, sample_analysis, mock_llm_client, sample_usage
    ):
        """Test extraction with unicode characters in content."""
        sample_content.full_text = "Transformers: über-efficient 日本語 émojis 🤖"
        mock_llm_client.complete.return_value = (
            make_extraction_response(
                concepts=[
                    {
                        "name": "トランスフォーマー",
                        "definition": "Japanese name",
                        "importance": "CORE",
                    }
                ]
            ),
            sample_usage,
        )
        result, _ = await extract_concepts(
            sample_content, sample_analysis, mock_llm_client
        )
        assert result.concepts[0].name == "トランスフォーマー"

    @pytest.mark.asyncio
    async def test_connection_handles_empty_concepts(
        self,
        sample_content,
        sample_analysis,
        mock_llm_client,
        mock_neo4j_client,
        sample_usage,
    ):
        """Test connection discovery with no concepts."""
        extraction = ExtractionResult(concepts=[], key_findings=[])
        mock_llm_client.embed.return_value = ([[0.1] * 1536], sample_usage)
        mock_neo4j_client.vector_search.return_value = []

        connections, _ = await discover_connections(
            sample_content,
            "Summary",
            extraction,
            sample_analysis,
            mock_llm_client,
            mock_neo4j_client,
        )
        assert len(connections) == 0

    @pytest.mark.asyncio
    async def test_followup_normalizes_all_enum_values(
        self,
        sample_content,
        sample_analysis,
        sample_extraction,
        mock_llm_client,
        sample_usage,
    ):
        """Test that all enum values are properly normalized."""
        mock_llm_client.complete.return_value = (
            make_followup_response(
                tasks=[
                    {
                        "task": "Task 1",
                        "type": "research",
                        "priority": "high",
                        "estimated_time": "1hr",
                    },
                    {
                        "task": "Task 2",
                        "type": "PRACTICE",
                        "priority": "Low",
                        "estimated_time": "15min",
                    },
                ]
            ),
            sample_usage,
        )

        tasks, _ = await generate_followups(
            sample_content,
            sample_analysis,
            "Summary",
            sample_extraction,
            mock_llm_client,
        )

        assert tasks[0].task_type == "RESEARCH"
        assert tasks[0].priority == "HIGH"
        assert tasks[1].priority == "LOW"

    @pytest.mark.asyncio
    async def test_followup_handles_missing_optional_fields(
        self,
        sample_content,
        sample_analysis,
        sample_extraction,
        mock_llm_client,
        sample_usage,
    ):
        """Test followup generation with missing optional fields."""
        mock_llm_client.complete.return_value = (
            make_followup_response(tasks=[{"task": "Minimal task"}]),
            sample_usage,
        )

        tasks, _ = await generate_followups(
            sample_content,
            sample_analysis,
            "Summary",
            sample_extraction,
            mock_llm_client,
        )

        assert len(tasks) == 1
        assert tasks[0].task == "Minimal task"
        assert tasks[0].task_type is not None

    @pytest.mark.asyncio
    async def test_question_difficulty_distribution(
        self,
        sample_content,
        sample_analysis,
        sample_extraction,
        mock_llm_client,
        sample_usage,
    ):
        """Test that questions can have different difficulty levels."""
        mock_llm_client.complete.return_value = (
            make_question_response(
                questions=[
                    {
                        "question": "Basic?",
                        "type": "conceptual",
                        "difficulty": "foundational",
                        "key_points": ["p"],
                    },
                    {
                        "question": "Medium?",
                        "type": "application",
                        "difficulty": "intermediate",
                        "key_points": ["p"],
                    },
                    {
                        "question": "Hard?",
                        "type": "analysis",
                        "difficulty": "advanced",
                        "key_points": ["p"],
                    },
                ]
            ),
            sample_usage,
        )

        questions, _ = await generate_mastery_questions(
            sample_content,
            sample_analysis,
            "Summary",
            sample_extraction,
            mock_llm_client,
        )

        difficulties = [q.difficulty for q in questions]
        assert "foundational" in difficulties
        assert "intermediate" in difficulties
        assert "advanced" in difficulties

    @pytest.mark.asyncio
    async def test_tagging_preserves_reasoning(
        self, sample_analysis, mock_llm_client, sample_usage, sample_taxonomy
    ):
        """Test that tagging reasoning is preserved."""
        reasoning_text = "Detailed explanation of tag choices."
        response = make_tagging_response()
        response["reasoning"] = reasoning_text
        mock_llm_client.complete.return_value = (response, sample_usage)

        result, _ = await assign_tags(
            "Test", sample_analysis, "Test", mock_llm_client, sample_taxonomy
        )
        assert result.reasoning == reasoning_text

    @pytest.mark.asyncio
    async def test_tagging_handles_empty_response(
        self, sample_analysis, mock_llm_client, sample_usage, sample_taxonomy
    ):
        """Test tagging with empty LLM response."""
        mock_llm_client.complete.return_value = (
            {
                "domain_tags": [],
                "meta_tags": [],
                "suggested_new_tags": [],
                "reasoning": "",
            },
            sample_usage,
        )

        result, _ = await assign_tags(
            "Test", sample_analysis, "Test", mock_llm_client, sample_taxonomy
        )
        assert isinstance(result, TagAssignment)
        assert len(result.domain_tags) == 0
