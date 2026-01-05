"""
Unit tests for processing output generators.

Tests the Obsidian note generator and Neo4j knowledge graph generator.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.enums import (
    ContentType,
    AnnotationType,
    SummaryLevel,
    ConceptImportance,
    RelationshipType,
)
from app.models.content import UnifiedContent, Annotation
from app.models.processing import (
    ProcessingResult,
    ContentAnalysis,
    ExtractionResult,
    TagAssignment,
    Concept,
    Connection,
    FollowupTask,
    MasteryQuestion,
)
from app.pipelines.utils.cost_types import LLMUsage
from app.services.processing.output.obsidian_generator import (
    generate_obsidian_note,
    _get_template_name,
    _prepare_template_data,
    _escape_yaml_string,
    _sanitize_filename,
)
from app.services.processing.output.neo4j_generator import (
    create_knowledge_nodes,
    update_content_node,
)


# =============================================================================
# Helper Functions
# =============================================================================


def make_concept(
    name: str = "Transformer",
    definition: str = "A neural network architecture",
    importance: str = ConceptImportance.CORE.value,
    related: list = None,
) -> Concept:
    """Create a concept with defaults."""
    return Concept(
        name=name,
        definition=definition,
        importance=importance,
        related_concepts=related or [],
    )


def make_connection(
    target_id: str = "target-1",
    target_title: str = "Related Paper",
    rel_type: RelationshipType = RelationshipType.EXTENDS,
    strength: float = 0.8,
) -> Connection:
    """Create a connection with defaults."""
    return Connection(
        target_id=target_id,
        target_title=target_title,
        relationship_type=rel_type,
        strength=strength,
        explanation="Related content",
    )


def make_followup(
    task: str = "Implement feature", task_type: str = "PRACTICE", priority: str = "HIGH"
) -> FollowupTask:
    """Create a followup task with defaults."""
    return FollowupTask(
        task=task, task_type=task_type, priority=priority, estimated_time="1HR"
    )


def make_question(
    question: str = "What is the main concept?",
    q_type: str = "conceptual",
    difficulty: str = "intermediate",
) -> MasteryQuestion:
    """Create a mastery question with defaults."""
    return MasteryQuestion(
        question=question,
        question_type=q_type,
        difficulty=difficulty,
        hints=["Think about it"],
        key_points=["Key point 1"],
    )


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
        authors=["Vaswani et al.", "Google Brain"],
        full_text="Paper content about transformers...",
        annotations=[
            Annotation(
                type=AnnotationType.DIGITAL_HIGHLIGHT,
                content="attention mechanisms",
                page_number=1,
            ),
            Annotation(
                type=AnnotationType.HANDWRITTEN_NOTE,
                content="Key insight",
                page_number=2,
                context="self-attention",
            ),
        ],
        source_url="https://arxiv.org/abs/1706.03762",
    )


@pytest.fixture
def sample_analysis() -> ContentAnalysis:
    """Create sample content analysis."""
    return ContentAnalysis(
        content_type="paper",
        domain="ml",
        complexity="advanced",
        estimated_length="medium",
        has_code=False,
        has_math=True,
        key_topics=["transformers", "attention"],
    )


@pytest.fixture
def sample_extraction() -> ExtractionResult:
    """Create sample extraction result."""
    return ExtractionResult(
        concepts=[
            make_concept(
                "Transformer",
                "Architecture based on attention",
                ConceptImportance.CORE.value,
            ),
            make_concept(
                "Self-attention",
                "Relates positions in sequence",
                ConceptImportance.CORE.value,
            ),
            make_concept(
                "Positional encoding",
                "Injects position info",
                ConceptImportance.SUPPORTING.value,
            ),
        ],
        key_findings=[
            "Transformers outperform RNNs",
            "Self-attention is parallelizable",
        ],
        methodologies=["Multi-head attention"],
        tools_mentioned=["PyTorch"],
    )


@pytest.fixture
def sample_tags() -> TagAssignment:
    """Create sample tag assignment."""
    return TagAssignment(
        domain_tags=["ml/transformers/attention", "ml/architecture"],
        meta_tags=["status/actionable", "quality/deep-dive"],
    )


@pytest.fixture
def sample_processing_result(
    sample_analysis, sample_extraction, sample_tags
) -> ProcessingResult:
    """Create sample processing result."""
    return ProcessingResult(
        content_id="test-content-123",
        analysis=sample_analysis,
        summaries={
            SummaryLevel.BRIEF.value: "Brief summary.",
            SummaryLevel.STANDARD.value: "Standard summary of the paper.",
            SummaryLevel.DETAILED.value: "## Overview\n\nDetailed summary...",
        },
        extraction=sample_extraction,
        tags=sample_tags,
        connections=[
            make_connection("c1", "BERT Paper", RelationshipType.EXTENDS, 0.85),
            make_connection("c2", "RNN Tutorial", RelationshipType.RELATES_TO, 0.65),
        ],
        followups=[
            make_followup("Implement attention", "PRACTICE", "HIGH"),
            make_followup("Read BERT paper", "RESEARCH", "MEDIUM"),
        ],
        mastery_questions=[
            make_question(
                "What is the advantage of self-attention?", "conceptual", "intermediate"
            ),
            make_question(
                "How to implement multi-head attention?", "application", "advanced"
            ),
        ],
        processing_time_seconds=45.0,
    )


@pytest.fixture
def mock_llm_client() -> MagicMock:
    """Create a mock LLM client."""
    mock = MagicMock()
    mock.embed = AsyncMock(return_value=([[0.1] * 1536], LLMUsage()))
    return mock


@pytest.fixture
def mock_neo4j_client() -> MagicMock:
    """Create a mock Neo4j client."""
    mock = MagicMock()
    mock.create_content_node = AsyncMock(return_value="neo4j-node-123")
    mock.create_concept_node = AsyncMock(return_value="concept-node-123")
    mock.link_content_to_concept = AsyncMock()
    mock.create_relationship = AsyncMock()
    mock.delete_content_relationships = AsyncMock(return_value=5)
    return mock


# =============================================================================
# Obsidian Generator Tests
# =============================================================================


class TestObsidianGenerator:
    """Tests for the Obsidian note generator."""

    @pytest.mark.parametrize(
        "content_type,expected",
        [
            ("paper", "paper.md.j2"),
            ("article", "article.md.j2"),
            ("book", "book.md.j2"),
            ("code", "code.md.j2"),
            ("custom_type", "custom_type.md.j2"),
        ],
    )
    def test_get_template_name(self, content_type, expected):
        """Test template name for various content types."""
        assert _get_template_name(content_type) == expected

    @pytest.mark.parametrize(
        "input_str,should_not_contain",
        [
            ('Title with "quotes"', '"quotes"'),
            ("Title with\nnewline", "\n"),
        ],
    )
    def test_escape_yaml_string(self, input_str, should_not_contain):
        """Test YAML string escaping."""
        result = _escape_yaml_string(input_str)
        assert should_not_contain not in result

    @pytest.mark.parametrize("empty_input", ["", None])
    def test_escape_yaml_string_empty(self, empty_input):
        """Test YAML string escaping with empty input."""
        assert _escape_yaml_string(empty_input) == ""

    @pytest.mark.parametrize(
        "title,expected",
        [
            ("Attention Is All You Need", "Attention Is All You Need"),
            ("", "Untitled"),
            ("/:*?<>|", "Untitled"),
        ],
    )
    def test_sanitize_filename_basic(self, title, expected):
        """Test basic filename sanitization."""
        assert _sanitize_filename(title) == expected

    @pytest.mark.parametrize("char", ["/", "\\", "?", ":", "*", "<", ">", "|"])
    def test_sanitize_filename_removes_special_chars(self, char):
        """Test filename sanitization removes special characters."""
        result = _sanitize_filename(f"Title{char}Test")
        assert char not in result

    def test_sanitize_filename_truncates_long_titles(self):
        """Test filename sanitization truncates long titles."""
        assert len(_sanitize_filename("A" * 200)) <= 100

    def test_sanitize_filename_strips_spaces(self):
        """Test filename sanitization strips leading/trailing spaces."""
        result = _sanitize_filename("  Title with spaces  ")
        assert not result.startswith(" ") and not result.endswith(" ")

    def test_prepare_template_data_basic(
        self, sample_content, sample_processing_result
    ):
        """Test basic template data preparation."""
        data = _prepare_template_data(sample_content, sample_processing_result)

        assert data["title"] == "Attention Is All You Need"
        assert data["content_type"] == "paper"
        assert data["domain"] == "ml"
        assert len(data["authors"]) == 2

    @pytest.mark.parametrize(
        "field",
        [
            "summary",
            "summary_brief",
            "overview",
            "detailed_notes",
            "concepts",
            "highlights",
            "handwritten_notes",
            "connections",
            "mastery_questions",
            "tasks",
            "tags",
            "created_date",
        ],
    )
    def test_prepare_template_data_contains_field(
        self, sample_content, sample_processing_result, field
    ):
        """Test that template data contains expected fields."""
        data = _prepare_template_data(sample_content, sample_processing_result)
        assert field in data

    def test_prepare_template_data_highlights(
        self, sample_content, sample_processing_result
    ):
        """Test template data includes highlights correctly."""
        data = _prepare_template_data(sample_content, sample_processing_result)

        assert len(data["highlights"]) == 1
        assert data["highlights"][0]["text"] == "attention mechanisms"
        assert data["highlights"][0]["page"] == 1

    def test_prepare_template_data_handwritten_notes(
        self, sample_content, sample_processing_result
    ):
        """Test template data includes handwritten notes."""
        data = _prepare_template_data(sample_content, sample_processing_result)

        assert len(data["handwritten_notes"]) == 1
        assert data["has_handwritten_notes"] is True

    def test_prepare_template_data_connections(
        self, sample_content, sample_processing_result
    ):
        """Test template data includes connections."""
        data = _prepare_template_data(sample_content, sample_processing_result)

        assert len(data["connections"]) == 2
        assert "related" in data
        assert "BERT Paper" in data["related"]

    def test_prepare_template_data_questions(
        self, sample_content, sample_processing_result
    ):
        """Test template data includes mastery questions."""
        data = _prepare_template_data(sample_content, sample_processing_result)

        assert len(data["mastery_questions"]) == 2
        assert data["mastery_questions"][0]["type"] == "conceptual"

    def test_prepare_template_data_tasks(
        self, sample_content, sample_processing_result
    ):
        """Test template data includes follow-up tasks."""
        data = _prepare_template_data(sample_content, sample_processing_result)

        assert len(data["tasks"]) == 2
        assert "action_items" in data

    def test_prepare_template_data_no_annotations(
        self, sample_content, sample_processing_result
    ):
        """Test template data with no annotations."""
        sample_content.annotations = []
        data = _prepare_template_data(sample_content, sample_processing_result)

        assert data["highlights"] == []
        assert data["handwritten_notes"] == []
        assert data["has_handwritten_notes"] is False

    def test_prepare_template_data_no_authors(
        self, sample_content, sample_processing_result
    ):
        """Test template data with no authors."""
        sample_content.authors = []
        data = _prepare_template_data(sample_content, sample_processing_result)

        assert data["authors"] == []
        assert data["author"] == ""

    def test_prepare_template_data_single_author(
        self, sample_content, sample_processing_result
    ):
        """Test template data with single author."""
        sample_content.authors = ["Single Author"]
        data = _prepare_template_data(sample_content, sample_processing_result)

        assert data["author"] == "Single Author"

    def test_prepare_template_data_empty_summaries(
        self, sample_content, sample_processing_result
    ):
        """Test template data with empty summaries."""
        sample_processing_result.summaries = {}
        data = _prepare_template_data(sample_content, sample_processing_result)

        assert data["summary"] == ""
        assert data["summary_brief"] == ""

    def test_prepare_template_data_no_concepts(
        self, sample_content, sample_processing_result
    ):
        """Test template data with no concepts."""
        sample_processing_result.extraction.concepts = []
        data = _prepare_template_data(sample_content, sample_processing_result)

        assert data["concepts"] == []

    def test_prepare_template_data_no_connections(
        self, sample_content, sample_processing_result
    ):
        """Test template data with no connections."""
        sample_processing_result.connections = []
        data = _prepare_template_data(sample_content, sample_processing_result)

        assert data["connections"] == []
        assert data["related"] == []

    @pytest.mark.asyncio
    async def test_generate_obsidian_note_missing_templates(
        self, sample_content, sample_processing_result
    ):
        """Test Obsidian note generation with missing template directory."""
        with patch(
            "app.services.processing.output.obsidian_generator.TEMPLATES_DIR"
        ) as mock_templates_dir:
            mock_templates_dir.exists.return_value = False
            result = await generate_obsidian_note(
                sample_content, sample_processing_result
            )
            assert result is None


# =============================================================================
# Neo4j Generator Tests
# =============================================================================


class TestNeo4jGenerator:
    """Tests for the Neo4j knowledge graph generator."""

    @pytest.mark.asyncio
    async def test_create_knowledge_nodes_success(
        self,
        sample_content,
        sample_processing_result,
        mock_llm_client,
        mock_neo4j_client,
    ):
        """Test successful knowledge node creation."""
        node_id = await create_knowledge_nodes(
            sample_content, sample_processing_result, mock_llm_client, mock_neo4j_client
        )

        assert node_id == "neo4j-node-123"
        mock_neo4j_client.create_content_node.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_knowledge_nodes_content_node_params(
        self,
        sample_content,
        sample_processing_result,
        mock_llm_client,
        mock_neo4j_client,
    ):
        """Test that content node is created with correct parameters."""
        await create_knowledge_nodes(
            sample_content, sample_processing_result, mock_llm_client, mock_neo4j_client
        )

        call_kwargs = mock_neo4j_client.create_content_node.call_args.kwargs
        assert call_kwargs["content_id"] == sample_content.id
        assert call_kwargs["title"] == sample_content.title
        assert call_kwargs["content_type"] == "paper"
        assert "ml/transformers/attention" in call_kwargs["tags"]

    @pytest.mark.asyncio
    async def test_create_knowledge_nodes_creates_core_concepts_only(
        self,
        sample_content,
        sample_processing_result,
        mock_llm_client,
        mock_neo4j_client,
    ):
        """Test that concept nodes are created for core concepts only."""
        await create_knowledge_nodes(
            sample_content, sample_processing_result, mock_llm_client, mock_neo4j_client
        )

        # 2 CORE concepts in sample_extraction
        assert mock_neo4j_client.create_concept_node.call_count == 2
        assert mock_neo4j_client.link_content_to_concept.call_count == 2

    @pytest.mark.asyncio
    async def test_create_knowledge_nodes_creates_relationships(
        self,
        sample_content,
        sample_processing_result,
        mock_llm_client,
        mock_neo4j_client,
    ):
        """Test that cross-content relationships are created."""
        await create_knowledge_nodes(
            sample_content, sample_processing_result, mock_llm_client, mock_neo4j_client
        )

        # 2 connections in sample_processing_result
        assert mock_neo4j_client.create_relationship.call_count == 2

    @pytest.mark.asyncio
    async def test_create_knowledge_nodes_empty_embedding(
        self,
        sample_content,
        sample_processing_result,
        mock_llm_client,
        mock_neo4j_client,
    ):
        """Test graceful handling of empty embeddings."""
        mock_llm_client.embed.return_value = ([], LLMUsage())

        node_id = await create_knowledge_nodes(
            sample_content, sample_processing_result, mock_llm_client, mock_neo4j_client
        )

        assert node_id == "neo4j-node-123"

    @pytest.mark.asyncio
    async def test_create_knowledge_nodes_db_error(
        self,
        sample_content,
        sample_processing_result,
        mock_llm_client,
        mock_neo4j_client,
    ):
        """Test graceful handling of database errors."""
        mock_neo4j_client.create_content_node.side_effect = Exception("DB error")

        node_id = await create_knowledge_nodes(
            sample_content, sample_processing_result, mock_llm_client, mock_neo4j_client
        )

        assert node_id is None

    @pytest.mark.asyncio
    async def test_create_knowledge_nodes_concept_error_continues(
        self,
        sample_content,
        sample_processing_result,
        mock_llm_client,
        mock_neo4j_client,
    ):
        """Test that concept creation errors don't stop the process."""
        mock_neo4j_client.create_concept_node.side_effect = [
            Exception("Failed"),
            AsyncMock(return_value="c2"),
        ]

        node_id = await create_knowledge_nodes(
            sample_content, sample_processing_result, mock_llm_client, mock_neo4j_client
        )

        assert node_id == "neo4j-node-123"

    @pytest.mark.asyncio
    async def test_create_knowledge_nodes_relationship_error_continues(
        self,
        sample_content,
        sample_processing_result,
        mock_llm_client,
        mock_neo4j_client,
    ):
        """Test that relationship creation errors don't stop the process."""
        mock_neo4j_client.create_relationship.side_effect = Exception("Failed")

        node_id = await create_knowledge_nodes(
            sample_content, sample_processing_result, mock_llm_client, mock_neo4j_client
        )

        assert node_id == "neo4j-node-123"

    @pytest.mark.asyncio
    async def test_create_knowledge_nodes_no_concepts(
        self,
        sample_content,
        sample_processing_result,
        mock_llm_client,
        mock_neo4j_client,
    ):
        """Test node creation with no concepts."""
        sample_processing_result.extraction.concepts = []

        node_id = await create_knowledge_nodes(
            sample_content, sample_processing_result, mock_llm_client, mock_neo4j_client
        )

        assert node_id == "neo4j-node-123"
        mock_neo4j_client.create_concept_node.assert_not_called()

    @pytest.mark.asyncio
    async def test_create_knowledge_nodes_no_connections(
        self,
        sample_content,
        sample_processing_result,
        mock_llm_client,
        mock_neo4j_client,
    ):
        """Test node creation with no connections."""
        sample_processing_result.connections = []

        node_id = await create_knowledge_nodes(
            sample_content, sample_processing_result, mock_llm_client, mock_neo4j_client
        )

        assert node_id == "neo4j-node-123"
        mock_neo4j_client.create_relationship.assert_not_called()

    @pytest.mark.asyncio
    async def test_create_knowledge_nodes_only_supporting_concepts(
        self,
        sample_content,
        sample_processing_result,
        mock_llm_client,
        mock_neo4j_client,
    ):
        """Test that only CORE concepts create graph nodes."""
        sample_processing_result.extraction.concepts = [
            make_concept("Supporting", "Def", ConceptImportance.SUPPORTING.value),
            make_concept("Tangential", "Def", ConceptImportance.TANGENTIAL.value),
        ]

        node_id = await create_knowledge_nodes(
            sample_content, sample_processing_result, mock_llm_client, mock_neo4j_client
        )

        assert node_id == "neo4j-node-123"
        mock_neo4j_client.create_concept_node.assert_not_called()

    @pytest.mark.asyncio
    async def test_create_knowledge_nodes_special_chars_in_title(
        self,
        sample_content,
        sample_processing_result,
        mock_llm_client,
        mock_neo4j_client,
    ):
        """Test node creation with special characters in title."""
        sample_content.title = "Paper: With 'Quotes' & <Chars>"

        node_id = await create_knowledge_nodes(
            sample_content, sample_processing_result, mock_llm_client, mock_neo4j_client
        )

        assert node_id == "neo4j-node-123"

    @pytest.mark.asyncio
    async def test_update_content_node_success(
        self, sample_processing_result, mock_llm_client, mock_neo4j_client
    ):
        """Test successful content node update."""
        result = await update_content_node(
            "test-123",
            "Test Title",
            sample_processing_result,
            mock_llm_client,
            mock_neo4j_client,
        )

        assert result is True
        mock_neo4j_client.delete_content_relationships.assert_called_once_with(
            "test-123"
        )

    @pytest.mark.asyncio
    async def test_update_content_node_handles_exception(
        self, sample_processing_result, mock_llm_client, mock_neo4j_client
    ):
        """Test graceful handling of update exceptions."""
        mock_neo4j_client.delete_content_relationships.side_effect = Exception(
            "Delete failed"
        )

        result = await update_content_node(
            "test-123",
            "Test Title",
            sample_processing_result,
            mock_llm_client,
            mock_neo4j_client,
        )

        assert result is False


# =============================================================================
# Template Data Formatting Tests
# =============================================================================


class TestTemplateDataFormatting:
    """Tests for template data formatting details."""

    def test_connection_strength_is_float(
        self, sample_content, sample_processing_result
    ):
        """Test that connection strength is a float between 0 and 1."""
        data = _prepare_template_data(sample_content, sample_processing_result)

        for conn in data["connections"]:
            assert "strength" in conn
            assert isinstance(conn["strength"], float)
            assert 0 <= conn["strength"] <= 1

    @pytest.mark.parametrize(
        "field", ["question", "type", "difficulty", "hints", "key_points"]
    )
    def test_question_formatting_includes_field(
        self, sample_content, sample_processing_result, field
    ):
        """Test that all question fields are in template data."""
        data = _prepare_template_data(sample_content, sample_processing_result)

        for question in data["mastery_questions"]:
            assert field in question

    @pytest.mark.parametrize("field", ["task", "task_type", "priority"])
    def test_task_formatting_includes_field(
        self, sample_content, sample_processing_result, field
    ):
        """Test that all task fields are in template data."""
        data = _prepare_template_data(sample_content, sample_processing_result)

        for task in data["tasks"]:
            assert field in task

    def test_highlight_includes_page_number(
        self, sample_content, sample_processing_result
    ):
        """Test that highlights include page numbers."""
        data = _prepare_template_data(sample_content, sample_processing_result)

        for highlight in data["highlights"]:
            assert "text" in highlight
            assert "page" in highlight

    def test_concepts_include_importance(
        self, sample_content, sample_processing_result
    ):
        """Test that concepts include importance field."""
        data = _prepare_template_data(sample_content, sample_processing_result)

        for concept in data["concepts"]:
            assert "importance" in concept

    def test_all_tags_combined(self, sample_content, sample_processing_result):
        """Test that tags include both domain and meta tags."""
        data = _prepare_template_data(sample_content, sample_processing_result)

        assert "ml/transformers/attention" in data["tags"]
        assert "status/actionable" in data["tags"]

    def test_date_format(self, sample_content, sample_processing_result):
        """Test that dates are in YYYY-MM-DD format."""
        data = _prepare_template_data(sample_content, sample_processing_result)

        assert len(data["created_date"]) == 10
        assert "-" in data["created_date"]
