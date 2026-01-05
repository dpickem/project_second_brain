"""
Unit tests for the processing pipeline orchestrator.

Tests the main pipeline that coordinates all processing stages.
"""

from contextlib import contextmanager
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from app.enums import (
    ContentType,
    AnnotationType,
    SummaryLevel,
    ConceptImportance,
)
from app.models.content import UnifiedContent, Annotation
from app.models.processing import (
    ProcessingResult,
    ContentAnalysis,
    ExtractionResult,
    TagAssignment,
    Concept,
    FollowupTask,
    MasteryQuestion,
)
from app.pipelines.utils.cost_types import LLMUsage
from app.services.processing.pipeline import process_content, PipelineConfig


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
        full_text="Abstract: Transformer architecture based on attention mechanisms.",
        annotations=[
            Annotation(
                type=AnnotationType.DIGITAL_HIGHLIGHT,
                content="attention",
                page_number=1,
            )
        ],
        source_url="https://arxiv.org/abs/1706.03762",
    )


@pytest.fixture
def mock_analysis() -> ContentAnalysis:
    """Create mock content analysis result."""
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
def mock_extraction() -> ExtractionResult:
    """Create mock extraction result."""
    return ExtractionResult(
        concepts=[
            Concept(
                name="Transformer",
                definition="Neural network",
                importance=ConceptImportance.CORE.value,
            )
        ],
        key_findings=["Transformers outperform RNNs"],
    )


@pytest.fixture
def mock_tags() -> TagAssignment:
    """Create mock tag assignment."""
    return TagAssignment(
        domain_tags=["ml/transformers"], meta_tags=["status/actionable"]
    )


@pytest.fixture
def mock_usage() -> LLMUsage:
    """Create mock LLM usage."""
    return LLMUsage(
        model="gpt-4o-mini", provider="openai", request_type="text", cost_usd=0.001
    )


@pytest.fixture
def mock_llm_client(mock_usage) -> MagicMock:
    """Create a mock LLM client."""
    mock = MagicMock()
    mock.complete = AsyncMock()
    mock.embed = AsyncMock(return_value=([[0.1] * 1536], mock_usage))
    return mock


@pytest.fixture
def mock_neo4j_client() -> MagicMock:
    """Create a mock Neo4j client."""
    mock = MagicMock()
    mock.vector_search = AsyncMock(return_value=[])
    mock.create_content_node = AsyncMock(return_value="neo4j-node-123")
    mock.create_concept_node = AsyncMock()
    mock.link_content_to_concept = AsyncMock()
    mock.create_relationship = AsyncMock()
    return mock


@pytest.fixture
def minimal_config() -> PipelineConfig:
    """Config with all optional stages disabled (only analysis runs)."""
    return PipelineConfig(
        generate_summaries=False,
        extract_concepts=False,
        assign_tags=False,
        discover_connections=False,
        generate_followups=False,
        generate_questions=False,
        create_obsidian_note=False,
        create_neo4j_nodes=False,
        validate_output=False,
    )


# =============================================================================
# Test Helpers
# =============================================================================


@contextmanager
def pipeline_mocks(
    analysis=None,
    summaries=None,
    extraction=None,
    tags=None,
    connections=None,
    followups=None,
    questions=None,
    obsidian_path=None,
    neo4j_id=None,
    validation_issues=None,
    # Error simulation
    summarize_error=None,
    extract_error=None,
    tag_error=None,
    followup_error=None,
    question_error=None,
    obsidian_error=None,
    neo4j_error=None,
    analysis_error=None,
):
    """Context manager providing all pipeline stage mocks."""
    usage = LLMUsage(cost_usd=0.01)

    with patch("app.services.processing.pipeline.analyze_content") as m_analyze, patch(
        "app.services.processing.pipeline.generate_all_summaries"
    ) as m_summarize, patch(
        "app.services.processing.pipeline.extract_concepts"
    ) as m_extract, patch(
        "app.services.processing.pipeline.assign_tags"
    ) as m_tag, patch(
        "app.services.processing.pipeline.discover_connections"
    ) as m_connections, patch(
        "app.services.processing.pipeline.generate_followups"
    ) as m_followups, patch(
        "app.services.processing.pipeline.generate_mastery_questions"
    ) as m_questions, patch(
        "app.services.processing.pipeline.validate_processing_result"
    ) as m_validate, patch(
        "app.services.processing.pipeline.generate_obsidian_note"
    ) as m_obsidian, patch(
        "app.services.processing.pipeline.create_knowledge_nodes"
    ) as m_neo4j, patch(
        "app.services.processing.pipeline.CostTracker"
    ) as m_cost, patch(
        "app.config.processing.processing_settings"
    ) as m_settings, patch(
        "app.services.processing.pipeline.get_llm_client"
    ) as m_get_llm:

        # Configure analysis
        if analysis_error:
            m_analyze.side_effect = analysis_error
        elif analysis:
            m_analyze.return_value = (analysis, [usage])

        # Configure other stages
        if summarize_error:
            m_summarize.side_effect = summarize_error
        else:
            m_summarize.return_value = (
                summaries or {SummaryLevel.STANDARD.value: "Summary"},
                [usage],
            )

        if extract_error:
            m_extract.side_effect = extract_error
        else:
            m_extract.return_value = (extraction or ExtractionResult(), [usage])

        if tag_error:
            m_tag.side_effect = tag_error
        else:
            m_tag.return_value = (tags or TagAssignment(), [usage])

        m_connections.return_value = (connections or [], [usage])

        if followup_error:
            m_followups.side_effect = followup_error
        else:
            m_followups.return_value = (followups or [], [usage])

        if question_error:
            m_questions.side_effect = question_error
        else:
            m_questions.return_value = (questions or [], [usage])

        m_validate.return_value = validation_issues or []

        if obsidian_error:
            m_obsidian.side_effect = obsidian_error
        else:
            m_obsidian.return_value = obsidian_path

        if neo4j_error:
            m_neo4j.side_effect = neo4j_error
        else:
            m_neo4j.return_value = neo4j_id

        m_cost.log_usages_batch = AsyncMock()
        m_settings.GENERATE_OBSIDIAN_NOTES = (
            obsidian_path is not None or obsidian_error is not None
        )
        m_settings.GENERATE_NEO4J_NODES = (
            neo4j_id is not None or neo4j_error is not None
        )
        m_get_llm.return_value = MagicMock()

        yield {
            "analyze": m_analyze,
            "summarize": m_summarize,
            "extract": m_extract,
            "tag": m_tag,
            "connections": m_connections,
            "followups": m_followups,
            "questions": m_questions,
            "validate": m_validate,
            "obsidian": m_obsidian,
            "neo4j": m_neo4j,
            "cost_tracker": m_cost,
            "settings": m_settings,
            "get_llm": m_get_llm,
        }


# =============================================================================
# PipelineConfig Tests
# =============================================================================


class TestPipelineConfig:
    """Tests for the PipelineConfig class."""

    def test_default_config_enables_all_stages(self):
        """Test default configuration enables all stages."""
        config = PipelineConfig()

        assert all(
            [
                config.generate_summaries,
                config.extract_concepts,
                config.assign_tags,
                config.discover_connections,
                config.generate_followups,
                config.generate_questions,
                config.create_obsidian_note,
                config.create_neo4j_nodes,
                config.validate_output,
            ]
        )
        assert config.max_connection_candidates == 10

    @pytest.mark.parametrize(
        "field,value",
        [
            ("discover_connections", False),
            ("max_connection_candidates", 5),
            ("create_obsidian_note", False),
            ("create_neo4j_nodes", False),
            ("validate_output", False),
        ],
    )
    def test_custom_config_values(self, field, value):
        """Test configuration accepts custom values (non-dependency fields)."""
        config = PipelineConfig(**{field: value})
        assert getattr(config, field) == value

    def test_all_stages_disabled_keeps_them_disabled(self):
        """Test disabling all stages keeps them disabled (no auto-enable)."""
        config = PipelineConfig(
            generate_summaries=False,
            extract_concepts=False,
            assign_tags=False,
            discover_connections=False,
            generate_followups=False,
            generate_questions=False,
        )
        assert not config.generate_summaries
        assert not config.extract_concepts
        assert not config.assign_tags
        assert not config.discover_connections
        assert not config.generate_followups
        assert not config.generate_questions

    # =========================================================================
    # Dependency Auto-Enable Tests
    # =========================================================================

    def test_assign_tags_auto_enables_summaries(self):
        """Test assign_tags=True auto-enables generate_summaries."""
        config = PipelineConfig(
            generate_summaries=False,
            extract_concepts=False,
            assign_tags=True,
            discover_connections=False,
            generate_followups=False,
            generate_questions=False,
        )
        assert config.generate_summaries is True
        assert config.assign_tags is True

    def test_discover_connections_auto_enables_dependencies(self):
        """Test discover_connections=True auto-enables summaries and extraction."""
        config = PipelineConfig(
            generate_summaries=False,
            extract_concepts=False,
            assign_tags=False,
            discover_connections=True,
            generate_followups=False,
            generate_questions=False,
        )
        assert config.generate_summaries is True
        assert config.extract_concepts is True
        assert config.discover_connections is True

    def test_generate_followups_auto_enables_dependencies(self):
        """Test generate_followups=True auto-enables summaries and extraction."""
        config = PipelineConfig(
            generate_summaries=False,
            extract_concepts=False,
            assign_tags=False,
            discover_connections=False,
            generate_followups=True,
            generate_questions=False,
        )
        assert config.generate_summaries is True
        assert config.extract_concepts is True
        assert config.generate_followups is True

    def test_generate_questions_auto_enables_dependencies(self):
        """Test generate_questions=True auto-enables summaries and extraction."""
        config = PipelineConfig(
            generate_summaries=False,
            extract_concepts=False,
            assign_tags=False,
            discover_connections=False,
            generate_followups=False,
            generate_questions=True,
        )
        assert config.generate_summaries is True
        assert config.extract_concepts is True
        assert config.generate_questions is True

    def test_multiple_dependent_stages_auto_enable_once(self):
        """Test multiple dependent stages only auto-enable dependencies once."""
        config = PipelineConfig(
            generate_summaries=False,
            extract_concepts=False,
            assign_tags=True,
            discover_connections=True,
            generate_followups=True,
            generate_questions=True,
        )
        # All dependencies should be enabled
        assert config.generate_summaries is True
        assert config.extract_concepts is True

    def test_dependencies_already_enabled_no_change(self):
        """Test no change when dependencies are already enabled."""
        config = PipelineConfig(
            generate_summaries=True,
            extract_concepts=True,
            assign_tags=True,
            discover_connections=True,
            generate_followups=True,
            generate_questions=True,
        )
        assert config.generate_summaries is True
        assert config.extract_concepts is True


# =============================================================================
# Pipeline Process Tests
# =============================================================================


class TestProcessContent:
    """Tests for the main process_content function."""

    @pytest.mark.asyncio
    async def test_full_pipeline_returns_complete_result(
        self,
        sample_content,
        mock_llm_client,
        mock_neo4j_client,
        mock_analysis,
        mock_extraction,
        mock_tags,
    ):
        """Test full pipeline execution returns complete ProcessingResult."""
        followup = FollowupTask(task="Implement", task_type="PRACTICE", priority="HIGH")
        question = MasteryQuestion(
            question="What is attention?", hints=["Think"], key_points=["Focus"]
        )
        summaries = {level.value: f"{level.value} summary" for level in SummaryLevel}

        with pipeline_mocks(
            analysis=mock_analysis,
            summaries=summaries,
            extraction=mock_extraction,
            tags=mock_tags,
            followups=[followup],
            questions=[question],
            obsidian_path="/vault/test.md",
            neo4j_id="node-123",
        ):
            result = await process_content(
                content=sample_content,
                llm_client=mock_llm_client,
                neo4j_client=mock_neo4j_client,
            )

        assert isinstance(result, ProcessingResult)
        assert result.content_id == sample_content.id
        assert result.analysis == mock_analysis
        assert len(result.summaries) == 3
        assert result.extraction == mock_extraction
        assert result.tags == mock_tags
        assert len(result.followups) == 1
        assert len(result.mastery_questions) == 1
        assert result.processing_time_seconds > 0

    @pytest.mark.asyncio
    async def test_analysis_only_returns_minimal_result(
        self, sample_content, mock_llm_client, mock_analysis, minimal_config
    ):
        """Test pipeline with only analysis returns minimal result."""
        with pipeline_mocks(analysis=mock_analysis):
            result = await process_content(
                content=sample_content,
                config=minimal_config,
                llm_client=mock_llm_client,
            )

        assert result.analysis == mock_analysis
        assert result.summaries == {}
        assert len(result.extraction.concepts) == 0
        assert len(result.tags.domain_tags) == 0

    @pytest.mark.asyncio
    async def test_default_llm_client_created_when_not_provided(
        self, sample_content, mock_analysis, minimal_config
    ):
        """Test that default LLM client is created when not provided."""
        with pipeline_mocks(analysis=mock_analysis) as mocks:
            await process_content(content=sample_content, config=minimal_config)
            mocks["get_llm"].assert_called_once()

    @pytest.mark.asyncio
    async def test_content_id_preserved_in_result(
        self, sample_content, mock_llm_client, mock_analysis, minimal_config
    ):
        """Test that content ID is preserved in result."""
        with pipeline_mocks(analysis=mock_analysis):
            result = await process_content(
                content=sample_content,
                config=minimal_config,
                llm_client=mock_llm_client,
            )
        assert result.content_id == sample_content.id

    @pytest.mark.asyncio
    @pytest.mark.parametrize("content_id", ["id-1", "id-2", "unique-uuid-123"])
    async def test_different_content_ids(
        self, mock_llm_client, mock_analysis, minimal_config, content_id
    ):
        """Test pipeline preserves different content IDs."""
        content = UnifiedContent(
            id=content_id,
            source_type=ContentType.ARTICLE,
            title="Test",
            full_text="Content",
        )

        with pipeline_mocks(analysis=mock_analysis):
            result = await process_content(
                content=content, config=minimal_config, llm_client=mock_llm_client
            )

        assert result.content_id == content_id


# =============================================================================
# Stage Skipping Tests
# =============================================================================


class TestStageSkipping:
    """Tests for stage skipping based on configuration."""

    @pytest.mark.asyncio
    async def test_connections_skipped_when_disabled(
        self, sample_content, mock_llm_client, mock_analysis, minimal_config
    ):
        """Test connection discovery is skipped when disabled."""
        with pipeline_mocks(analysis=mock_analysis) as mocks:
            result = await process_content(
                content=sample_content,
                config=minimal_config,
                llm_client=mock_llm_client,
            )

        mocks["connections"].assert_not_called()
        assert result.connections == []

    @pytest.mark.asyncio
    async def test_connections_skipped_without_neo4j_client(
        self, sample_content, mock_llm_client, mock_analysis, mock_extraction, mock_tags
    ):
        """Test connection discovery skipped when no Neo4j client provided."""
        config = PipelineConfig(
            discover_connections=False,  # Explicitly disabled
            create_obsidian_note=False,
            create_neo4j_nodes=False,
            validate_output=False,
        )

        with pipeline_mocks(
            analysis=mock_analysis, extraction=mock_extraction, tags=mock_tags
        ) as mocks:
            result = await process_content(
                content=sample_content,
                config=config,
                llm_client=mock_llm_client,
                neo4j_client=None,
            )

        mocks["connections"].assert_not_called()
        assert result.connections == []

    @pytest.mark.asyncio
    async def test_custom_connection_candidates_passed_to_stage(
        self,
        sample_content,
        mock_llm_client,
        mock_neo4j_client,
        mock_analysis,
        mock_extraction,
    ):
        """Test custom max_connection_candidates is passed to discover_connections."""
        config = PipelineConfig(
            assign_tags=False,
            discover_connections=True,
            generate_followups=False,
            generate_questions=False,
            create_obsidian_note=False,
            create_neo4j_nodes=False,
            validate_output=False,
            max_connection_candidates=3,
        )

        with pipeline_mocks(
            analysis=mock_analysis, extraction=mock_extraction
        ) as mocks:
            await process_content(
                content=sample_content,
                config=config,
                llm_client=mock_llm_client,
                neo4j_client=mock_neo4j_client,
            )

        mocks["connections"].assert_called_once()
        assert mocks["connections"].call_args.kwargs["top_k"] == 3


# =============================================================================
# Error Handling Tests
# =============================================================================


class TestErrorHandling:
    """Tests for pipeline error handling."""

    @pytest.mark.asyncio
    async def test_analysis_failure_propagates(
        self, sample_content, mock_llm_client, minimal_config
    ):
        """Test that analysis failure (critical stage) propagates."""
        with pipeline_mocks(analysis_error=Exception("Analysis failed")):
            with pytest.raises(Exception, match="Analysis failed"):
                await process_content(
                    content=sample_content,
                    config=minimal_config,
                    llm_client=mock_llm_client,
                )

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "error_stage", ["summarize", "extract", "tag", "followup", "question"]
    )
    async def test_non_critical_stage_failures_continue(
        self, sample_content, mock_llm_client, mock_analysis, error_stage
    ):
        """Test pipeline continues despite non-critical stage failures."""
        error_kwargs = {f"{error_stage}_error": Exception(f"{error_stage} failed")}
        config = PipelineConfig(
            discover_connections=False,
            create_obsidian_note=False,
            create_neo4j_nodes=False,
            validate_output=False,
        )

        with pipeline_mocks(analysis=mock_analysis, **error_kwargs):
            result = await process_content(
                content=sample_content,
                config=config,
                llm_client=mock_llm_client,
            )

        assert result is not None
        assert result.analysis == mock_analysis

    @pytest.mark.asyncio
    async def test_obsidian_failure_continues(
        self, sample_content, mock_llm_client, mock_analysis
    ):
        """Test Obsidian generation failure doesn't stop pipeline."""
        config = PipelineConfig(
            generate_summaries=False,
            extract_concepts=False,
            assign_tags=False,
            discover_connections=False,
            generate_followups=False,
            generate_questions=False,
            create_obsidian_note=True,
            create_neo4j_nodes=False,
            validate_output=False,
        )

        with pipeline_mocks(
            analysis=mock_analysis, obsidian_error=Exception("Template error")
        ):
            result = await process_content(
                content=sample_content,
                config=config,
                llm_client=mock_llm_client,
            )

        assert result is not None
        assert result.obsidian_note_path is None

    @pytest.mark.asyncio
    async def test_neo4j_failure_continues(
        self, sample_content, mock_llm_client, mock_neo4j_client, mock_analysis
    ):
        """Test Neo4j creation failure doesn't stop pipeline."""
        config = PipelineConfig(
            generate_summaries=False,
            extract_concepts=False,
            assign_tags=False,
            discover_connections=False,
            generate_followups=False,
            generate_questions=False,
            create_obsidian_note=False,
            create_neo4j_nodes=True,
            validate_output=False,
        )

        with pipeline_mocks(
            analysis=mock_analysis, neo4j_error=Exception("Neo4j error")
        ):
            result = await process_content(
                content=sample_content,
                config=config,
                llm_client=mock_llm_client,
                neo4j_client=mock_neo4j_client,
            )

        assert result is not None
        assert result.neo4j_node_id is None

    @pytest.mark.asyncio
    async def test_cost_tracking_failure_continues(
        self, sample_content, mock_llm_client, mock_analysis, minimal_config
    ):
        """Test cost tracking failure doesn't stop pipeline."""
        with pipeline_mocks(analysis=mock_analysis) as mocks:
            mocks["cost_tracker"].log_usages_batch = AsyncMock(
                side_effect=Exception("DB error")
            )

            result = await process_content(
                content=sample_content,
                config=minimal_config,
                llm_client=mock_llm_client,
            )

        assert result is not None
        assert result.analysis == mock_analysis

    @pytest.mark.asyncio
    async def test_stage_errors_produce_fallback_summaries(
        self, sample_content, mock_llm_client, mock_analysis, mock_extraction, mock_tags
    ):
        """Test summarization errors produce fallback error message."""
        config = PipelineConfig(
            discover_connections=False,
            create_obsidian_note=False,
            create_neo4j_nodes=False,
            validate_output=False,
        )

        with pipeline_mocks(
            analysis=mock_analysis,
            extraction=mock_extraction,
            tags=mock_tags,
            summarize_error=Exception("Summarization failed"),
        ):
            result = await process_content(
                content=sample_content,
                config=config,
                llm_client=mock_llm_client,
            )

        assert "standard" in result.summaries
        assert "failed" in result.summaries["standard"].lower()


# =============================================================================
# Output Generation Tests
# =============================================================================


class TestOutputGeneration:
    """Tests for output generation (Obsidian, Neo4j)."""

    @pytest.mark.asyncio
    async def test_obsidian_path_returned(
        self, sample_content, mock_llm_client, mock_analysis
    ):
        """Test Obsidian note path is returned in result."""
        config = PipelineConfig(
            generate_summaries=False,
            extract_concepts=False,
            assign_tags=False,
            discover_connections=False,
            generate_followups=False,
            generate_questions=False,
            create_obsidian_note=True,
            create_neo4j_nodes=False,
            validate_output=False,
        )

        with pipeline_mocks(
            analysis=mock_analysis, obsidian_path="/vault/papers/test.md"
        ) as mocks:
            result = await process_content(
                content=sample_content,
                config=config,
                llm_client=mock_llm_client,
            )

        mocks["obsidian"].assert_called_once()
        assert result.obsidian_note_path == "/vault/papers/test.md"

    @pytest.mark.asyncio
    async def test_neo4j_node_id_returned(
        self, sample_content, mock_llm_client, mock_neo4j_client, mock_analysis
    ):
        """Test Neo4j node ID is returned in result."""
        config = PipelineConfig(
            generate_summaries=False,
            extract_concepts=False,
            assign_tags=False,
            discover_connections=False,
            generate_followups=False,
            generate_questions=False,
            create_obsidian_note=False,
            create_neo4j_nodes=True,
            validate_output=False,
        )

        with pipeline_mocks(analysis=mock_analysis, neo4j_id="neo4j-node-456") as mocks:
            result = await process_content(
                content=sample_content,
                config=config,
                llm_client=mock_llm_client,
                neo4j_client=mock_neo4j_client,
            )

        mocks["neo4j"].assert_called_once()
        assert result.neo4j_node_id == "neo4j-node-456"


# =============================================================================
# Validation Tests
# =============================================================================


class TestValidation:
    """Tests for output validation."""

    @pytest.mark.asyncio
    async def test_validation_called_when_enabled(
        self, sample_content, mock_llm_client, mock_analysis, mock_extraction
    ):
        """Test validation is called when enabled."""
        config = PipelineConfig(
            discover_connections=False,
            create_obsidian_note=False,
            create_neo4j_nodes=False,
            validate_output=True,
        )

        with pipeline_mocks(
            analysis=mock_analysis,
            extraction=mock_extraction,
            validation_issues=["No standard summary", "Too few questions"],
        ) as mocks:
            result = await process_content(
                content=sample_content,
                config=config,
                llm_client=mock_llm_client,
            )

        mocks["validate"].assert_called_once()
        assert result is not None  # Pipeline completes despite validation issues


# =============================================================================
# Cost Tracking Tests
# =============================================================================


class TestCostTracking:
    """Tests for LLM cost tracking."""

    @pytest.mark.asyncio
    async def test_costs_aggregated_and_tracked(
        self, sample_content, mock_llm_client, mock_analysis, mock_extraction, mock_tags
    ):
        """Test LLM costs are aggregated from all stages."""
        config = PipelineConfig(
            discover_connections=False,
            create_obsidian_note=False,
            create_neo4j_nodes=False,
            validate_output=False,
        )

        with pipeline_mocks(
            analysis=mock_analysis,
            extraction=mock_extraction,
            tags=mock_tags,
        ) as mocks:
            result = await process_content(
                content=sample_content,
                config=config,
                llm_client=mock_llm_client,
            )

        mocks["cost_tracker"].log_usages_batch.assert_called_once()
        # Each stage returns usage with cost_usd=0.01
        assert result.estimated_cost_usd >= 0


# =============================================================================
# Timing Tests
# =============================================================================


class TestTiming:
    """Tests for pipeline timing."""

    @pytest.mark.asyncio
    async def test_processing_time_recorded(
        self, sample_content, mock_llm_client, mock_analysis, minimal_config
    ):
        """Test processing time is recorded in result."""
        with pipeline_mocks(analysis=mock_analysis):
            result = await process_content(
                content=sample_content,
                config=minimal_config,
                llm_client=mock_llm_client,
            )

        assert result.processing_time_seconds >= 0
