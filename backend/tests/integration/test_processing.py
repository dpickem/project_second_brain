"""
Integration tests for the LLM processing pipeline.

These tests verify end-to-end functionality of the processing module,
including stage coordination, output generation, and error handling.

Note: These tests use mocked LLM and database clients to avoid external
dependencies. For true integration tests with real services, configure
the appropriate environment variables and use the @pytest.mark.real_llm
marker.
"""

from contextlib import contextmanager
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
from app.services.processing import process_content, PipelineConfig
from app.services.processing.stages import (
    analyze_content,
    generate_all_summaries,
    extract_concepts,
    assign_tags,
    discover_connections,
    generate_followups,
    generate_mastery_questions,
    TagTaxonomy,
    TagTaxonomyLoader,
)
from app.services.processing.validation import validate_processing_result
from app.services.processing.output.obsidian_generator import _prepare_template_data


# =============================================================================
# Helper Functions and Context Managers
# =============================================================================


def make_analysis_response(
    content_type: str = "paper",
    domain: str = "ml",
    complexity: str = "advanced",
    length: str = "long",
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
        "key_topics": topics or ["transformers", "attention"],
    }


def make_extraction_response(
    concepts: list = None,
    findings: list = None,
) -> dict:
    """Create a standard extraction response dict."""
    return {
        "concepts": concepts or [
            {"name": "Transformer", "definition": "Attention-based architecture", "importance": "CORE"}
        ],
        "key_findings": findings or ["Finding 1"],
        "methodologies": [],
        "tools_mentioned": [],
        "people_mentioned": [],
    }


def make_tagging_response(
    domain_tags: list = None,
    meta_tags: list = None,
) -> dict:
    """Create a standard tagging response dict."""
    return {
        "domain_tags": domain_tags or ["ml/transformers/attention"],
        "meta_tags": meta_tags or ["status/actionable"],
        "suggested_new_tags": [],
        "reasoning": "ML paper",
    }


@contextmanager
def pipeline_mocks(mock_llm_usage):
    """Context manager that sets up all pipeline stage mocks."""
    with patch("app.services.processing.pipeline.analyze_content") as mock_analyze, \
         patch("app.services.processing.pipeline.generate_all_summaries") as mock_summarize, \
         patch("app.services.processing.pipeline.extract_concepts") as mock_extract, \
         patch("app.services.processing.pipeline.assign_tags") as mock_tag, \
         patch("app.services.processing.pipeline.discover_connections") as mock_connections, \
         patch("app.services.processing.pipeline.generate_followups") as mock_followups, \
         patch("app.services.processing.pipeline.generate_mastery_questions") as mock_questions, \
         patch("app.services.processing.pipeline.CostTracker") as mock_cost_tracker, \
         patch("app.config.processing.processing_settings") as mock_settings:

        mock_cost_tracker.log_usages_batch = AsyncMock()
        mock_settings.GENERATE_OBSIDIAN_NOTES = False
        mock_settings.GENERATE_NEO4J_NODES = False

        yield {
            "analyze": mock_analyze,
            "summarize": mock_summarize,
            "extract": mock_extract,
            "tag": mock_tag,
            "connections": mock_connections,
            "followups": mock_followups,
            "questions": mock_questions,
            "cost_tracker": mock_cost_tracker,
            "settings": mock_settings,
        }


def configure_pipeline_mocks(mocks: dict, mock_llm_usage, content_type: str = "paper"):
    """Configure standard responses for all pipeline stage mocks."""
    mocks["analyze"].return_value = (
        ContentAnalysis(
            content_type=content_type,
            domain="ml",
            complexity="advanced" if content_type == "paper" else "foundational",
            estimated_length="long" if content_type == "paper" else "medium",
            key_topics=["transformers"] if content_type == "paper" else ["machine learning"],
        ),
        [mock_llm_usage],
    )
    mocks["summarize"].return_value = (
        {
            SummaryLevel.BRIEF.value: "Brief",
            SummaryLevel.STANDARD.value: "Standard summary.",
            SummaryLevel.DETAILED.value: "Detailed",
        },
        [mock_llm_usage] * 3,
    )
    mocks["extract"].return_value = (
        ExtractionResult(
            concepts=[
                Concept(
                    name="Transformer" if content_type == "paper" else "Machine Learning",
                    definition="Attention architecture" if content_type == "paper" else "Learning from data",
                    importance=ConceptImportance.CORE.value,
                )
            ],
            key_findings=["Finding 1"],
        ),
        [mock_llm_usage],
    )
    mocks["tag"].return_value = (
        TagAssignment(
            domain_tags=["ml/transformers/attention"] if content_type == "paper" else ["ml/foundational"],
            meta_tags=["status/actionable"],
        ),
        [mock_llm_usage],
    )
    mocks["connections"].return_value = (
        [
            Connection(
                target_id="bert",
                target_title="BERT",
                relationship_type=RelationshipType.EXTENDS,
                strength=0.8,
                explanation="Related",
            )
        ],
        [mock_llm_usage],
    )
    mocks["followups"].return_value = (
        [FollowupTask(task="Implement attention", task_type="PRACTICE", priority="HIGH", estimated_time="2HR_PLUS")],
        [mock_llm_usage],
    )
    mocks["questions"].return_value = (
        [
            MasteryQuestion(question="What is self-attention?" * 3, hints=["hint"], key_points=["point"]),
            MasteryQuestion(question="How does multi-head attention work?" * 2, hints=["hint"], key_points=["point"]),
        ],
        [mock_llm_usage],
    )


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def sample_paper_content() -> UnifiedContent:
    """Create a realistic sample paper for integration testing."""
    return UnifiedContent(
        id="paper-integration-test-123",
        source_type=ContentType.PAPER,
        title="Attention Is All You Need: A Breakthrough in Sequence Modeling",
        authors=["Ashish Vaswani", "Noam Shazeer", "Niki Parmar"],
        full_text="""
        Abstract

        The dominant sequence transduction models are based on complex recurrent or
        convolutional neural networks that include an encoder and a decoder. The best
        performing models also connect the encoder and decoder through an attention
        mechanism. We propose a new simple network architecture, the Transformer,
        based solely on attention mechanisms, dispensing with recurrence and convolutions
        entirely. Experiments on two machine translation tasks show these models to
        be superior in quality while being more parallelizable and requiring significantly
        less time to train.

        1. Introduction

        Recurrent neural networks, long short-term memory and gated recurrent neural
        networks in particular, have been firmly established as state of the art
        approaches in sequence modeling and transduction problems such as language
        modeling and machine translation.

        In this work we propose the Transformer, a model architecture eschewing recurrence
        and instead relying entirely on an attention mechanism to draw global dependencies
        between input and output. The Transformer allows for significantly more
        parallelization and can reach a new state of the art in translation quality.

        3. Model Architecture

        The Transformer follows an encoder-decoder structure using stacked self-attention
        and point-wise, fully connected layers for both the encoder and decoder.

        3.2 Attention

        An attention function can be described as mapping a query and a set of key-value
        pairs to an output, where the query, keys, values, and output are all vectors.

        5. Conclusion

        In this work, we presented the Transformer, the first sequence transduction
        model based entirely on attention, replacing the recurrent layers most commonly
        used in encoder-decoder architectures with multi-headed self-attention.
        """,
        annotations=[
            Annotation(
                type=AnnotationType.DIGITAL_HIGHLIGHT,
                content="The Transformer allows for significantly more parallelization",
                page_number=1,
            ),
            Annotation(
                type=AnnotationType.DIGITAL_HIGHLIGHT,
                content="multi-headed self-attention",
                page_number=5,
            ),
            Annotation(
                type=AnnotationType.HANDWRITTEN_NOTE,
                content="Key insight: attention replaces recurrence completely!",
                page_number=1,
                context="We propose a new simple network architecture",
            ),
        ],
        source_url="https://arxiv.org/abs/1706.03762",
    )


@pytest.fixture
def sample_article_content() -> UnifiedContent:
    """Create a sample article for integration testing."""
    return UnifiedContent(
        id="article-integration-test-456",
        source_type=ContentType.ARTICLE,
        title="Getting Started with Machine Learning: A Practical Guide",
        authors=["Jane Developer"],
        full_text="""
        Introduction

        Machine learning has become one of the most in-demand skills in the tech
        industry. This guide will walk you through the essential concepts.

        What is Machine Learning?

        At its core, machine learning is about building systems that can learn patterns
        from data. Instead of explicitly programming rules, we let algorithms discover
        patterns by examining examples.

        The Three Types of ML

        1. Supervised Learning: Learning from labeled examples
        2. Unsupervised Learning: Finding patterns in unlabeled data
        3. Reinforcement Learning: Learning through trial and error

        Conclusion

        Machine learning is more accessible than ever. Start small, stay consistent,
        and don't be afraid to experiment.
        """,
        annotations=[
            Annotation(
                type=AnnotationType.DIGITAL_HIGHLIGHT,
                content="machine learning is about building systems that can learn patterns",
                page_number=1,
            ),
        ],
        source_url="https://example.com/ml-guide",
    )


@pytest.fixture
def mock_llm_usage() -> LLMUsage:
    """Create a mock LLM usage record."""
    return LLMUsage(
        model="gemini/gemini-3-flash-preview",
        provider="gemini",
        request_type="text",
        prompt_tokens=500,
        completion_tokens=200,
        total_tokens=700,
        cost_usd=0.002,
        latency_ms=1200,
    )


@pytest.fixture
def mock_llm_client(mock_llm_usage) -> MagicMock:
    """Create a comprehensive mock LLM client."""
    mock = MagicMock()
    mock.complete = AsyncMock()
    mock.embed = AsyncMock(return_value=([[0.1] * 1536], mock_llm_usage))
    return mock


@pytest.fixture
def mock_neo4j_client() -> MagicMock:
    """Create a comprehensive mock Neo4j client."""
    mock = MagicMock()
    mock.vector_search = AsyncMock(
        return_value=[
            {"id": "existing-content-1", "title": "BERT", "summary": "A language model"},
            {"id": "existing-content-2", "title": "GPT-3", "summary": "A large language model"},
        ]
    )
    mock.create_content_node = AsyncMock(return_value="neo4j-content-node-123")
    mock.create_concept_node = AsyncMock(return_value="neo4j-concept-node-123")
    mock.link_content_to_concept = AsyncMock()
    mock.create_relationship = AsyncMock()
    mock.delete_content_relationships = AsyncMock(return_value=3)
    return mock


@pytest.fixture
def sample_taxonomy() -> TagTaxonomy:
    """Create a sample taxonomy for integration testing."""
    return TagTaxonomy(
        domains=[
            "ml/transformers/attention",
            "ml/transformers/llms",
            "ml/training/optimization",
            "ml/nlp/translation",
            "software/python/libraries",
        ],
        status=["actionable", "review", "archived", "in-progress"],
        quality=["foundational", "deep-dive", "reference", "practical"],
    )


@pytest.fixture
def base_analysis() -> ContentAnalysis:
    """Create a base analysis for tests that need pre-built analysis."""
    return ContentAnalysis(
        content_type="paper",
        domain="ml",
        complexity="advanced",
        estimated_length="medium",
        key_topics=["transformers", "attention"],
    )


# =============================================================================
# Integration Tests - Stage Coordination
# =============================================================================


class TestStageCoordination:
    """Tests for coordination between processing stages."""

    @pytest.mark.asyncio
    async def test_analysis_to_summarization_flow(
        self, sample_paper_content, mock_llm_client, mock_llm_usage
    ):
        """Test that analysis results properly flow to summarization."""
        mock_llm_client.complete.side_effect = [
            (make_analysis_response(), mock_llm_usage),
            ("Brief: The Transformer paper introduces attention-based architecture.", mock_llm_usage),
            ("Standard: This seminal paper introduces the Transformer...", mock_llm_usage),
            ("Detailed: ## Overview\n\nThe Transformer paper...", mock_llm_usage),
        ]

        analysis, _ = await analyze_content(sample_paper_content, mock_llm_client)
        assert analysis.content_type == "paper"
        assert analysis.domain == "ml"

        summaries, usages = await generate_all_summaries(sample_paper_content, analysis, mock_llm_client)
        assert all(level.value in summaries for level in SummaryLevel)
        assert len(usages) == 3

    @pytest.mark.asyncio
    async def test_extraction_to_tagging_flow(
        self, sample_paper_content, mock_llm_client, mock_llm_usage, sample_taxonomy, base_analysis
    ):
        """Test that extraction results feed into tagging appropriately."""
        extraction_response = make_extraction_response(
            concepts=[
                {"name": "Transformer", "definition": "Neural network architecture", "importance": "CORE"},
                {"name": "Self-attention", "definition": "Attention within sequence", "importance": "CORE"},
            ],
            findings=["Transformers outperform RNNs", "Attention enables parallelization"],
        )
        mock_llm_client.complete.side_effect = [
            (extraction_response, mock_llm_usage),
            (make_tagging_response(meta_tags=["status/actionable", "quality/deep-dive"]), mock_llm_usage),
        ]

        extraction, _ = await extract_concepts(sample_paper_content, base_analysis, mock_llm_client)
        assert len(extraction.concepts) == 2
        assert all(c.importance == "CORE" for c in extraction.concepts)

        tags, _ = await assign_tags(
            sample_paper_content.title, base_analysis, "Paper about transformers", mock_llm_client, sample_taxonomy
        )
        assert "ml/transformers/attention" in tags.domain_tags
        assert "status/actionable" in tags.meta_tags

    @pytest.mark.asyncio
    async def test_full_stage_chain(
        self, sample_paper_content, mock_llm_client, mock_neo4j_client, mock_llm_usage, sample_taxonomy
    ):
        """Test complete stage chain from analysis to questions."""
        responses = [
            (make_analysis_response(has_math=True), mock_llm_usage),
            ("Brief summary.", mock_llm_usage),
            ("Standard summary.", mock_llm_usage),
            ("Detailed summary.", mock_llm_usage),
            (make_extraction_response(), mock_llm_usage),
            (make_tagging_response(meta_tags=["quality/deep-dive"]), mock_llm_usage),
            ({"has_connection": True, "relationship_type": RelationshipType.EXTENDS, "strength": 0.85, "explanation": "BERT builds on transformers"}, mock_llm_usage),
            ({"has_connection": True, "relationship_type": RelationshipType.EXTENDS, "strength": 0.75, "explanation": "GPT uses transformers"}, mock_llm_usage),
            ({"tasks": [{"task": "Implement self-attention", "type": "PRACTICE", "priority": "HIGH", "estimated_time": "2HR_PLUS"}]}, mock_llm_usage),
            ({"questions": [{"question": "What is self-attention?", "type": "conceptual", "difficulty": "intermediate", "hints": ["Think about parallelization"], "key_points": ["Parallel processing"]}]}, mock_llm_usage),
        ]
        mock_llm_client.complete.side_effect = responses

        analysis, _ = await analyze_content(sample_paper_content, mock_llm_client)
        summaries, _ = await generate_all_summaries(sample_paper_content, analysis, mock_llm_client)
        extraction, _ = await extract_concepts(sample_paper_content, analysis, mock_llm_client)
        tags, _ = await assign_tags(sample_paper_content.title, analysis, summaries.get(SummaryLevel.STANDARD.value, ""), mock_llm_client, sample_taxonomy)
        connections, _ = await discover_connections(sample_paper_content, summaries.get(SummaryLevel.STANDARD.value, ""), extraction, analysis, mock_llm_client, mock_neo4j_client)
        followups, _ = await generate_followups(sample_paper_content, analysis, summaries.get(SummaryLevel.STANDARD.value, ""), extraction, mock_llm_client)
        questions, _ = await generate_mastery_questions(sample_paper_content, analysis, summaries.get(SummaryLevel.DETAILED.value, ""), extraction, mock_llm_client)

        assert analysis.content_type == "paper"
        assert len(summaries) == 3
        assert len(extraction.concepts) >= 1
        assert len(tags.domain_tags) >= 1
        assert len(connections) >= 1
        assert len(followups) >= 1
        assert len(questions) >= 1


# =============================================================================
# Integration Tests - Full Pipeline
# =============================================================================


class TestFullPipeline:
    """Integration tests for the complete processing pipeline."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "content_fixture,content_type,has_connections",
        [
            ("sample_paper_content", "paper", True),
            ("sample_article_content", "article", False),
        ],
    )
    async def test_full_pipeline(
        self, content_fixture, content_type, has_connections, mock_llm_client, mock_neo4j_client, mock_llm_usage, request
    ):
        """Test full pipeline processing of different content types."""
        content = request.getfixturevalue(content_fixture)

        with pipeline_mocks(mock_llm_usage) as mocks:
            configure_pipeline_mocks(mocks, mock_llm_usage, content_type)

            config = PipelineConfig(
                discover_connections=has_connections,
                create_obsidian_note=False,
                create_neo4j_nodes=False,
            )
            result = await process_content(
                content=content,
                config=config,
                llm_client=mock_llm_client,
                neo4j_client=mock_neo4j_client if has_connections else None,
            )

            assert isinstance(result, ProcessingResult)
            assert result.content_id == content.id
            assert result.analysis.content_type == content_type
            assert len(result.summaries) >= 1
            assert len(result.extraction.concepts) >= 1
            assert result.processing_time_seconds > 0


# =============================================================================
# Integration Tests - Validation
# =============================================================================


class TestValidationIntegration:
    """Integration tests for processing result validation."""

    @pytest.fixture
    def complete_result(self) -> ProcessingResult:
        """Create a complete, valid processing result."""
        return ProcessingResult(
            content_id="test-123",
            analysis=ContentAnalysis(content_type="paper", domain="ml", complexity="advanced", estimated_length="medium"),
            summaries={
                SummaryLevel.BRIEF.value: "A" * 60,
                SummaryLevel.STANDARD.value: "B" * 200,
                SummaryLevel.DETAILED.value: "C" * 400,
            },
            extraction=ExtractionResult(
                concepts=[
                    Concept(name="Concept 1", definition="A detailed definition that is long enough", importance=ConceptImportance.CORE.value),
                    Concept(name="Concept 2", definition="Another detailed definition here", importance=ConceptImportance.SUPPORTING.value),
                ]
            ),
            tags=TagAssignment(domain_tags=["ml/transformers"], meta_tags=["status/actionable"]),
            mastery_questions=[
                MasteryQuestion(question="What is the main concept?" * 3, hints=["hint"], key_points=["point 1", "point 2"]),
                MasteryQuestion(question="How does it relate to other work?" * 3, hints=["hint"], key_points=["point"]),
            ],
        )

    @pytest.fixture
    def incomplete_result(self) -> ProcessingResult:
        """Create an incomplete processing result."""
        return ProcessingResult(
            content_id="test-123",
            analysis=ContentAnalysis(content_type="paper", domain="ml", complexity="advanced", estimated_length="medium"),
            summaries={},
            extraction=ExtractionResult(),
            tags=TagAssignment(),
            mastery_questions=[],
        )

    @pytest.mark.parametrize(
        "result_fixture,max_issues",
        [
            ("complete_result", 1),
            ("incomplete_result", 100),  # Many issues expected
        ],
    )
    def test_validate_result(self, result_fixture, max_issues, request):
        """Test validation of processing results."""
        result = request.getfixturevalue(result_fixture)
        issues = validate_processing_result(result)
        if max_issues == 1:
            assert len(issues) <= max_issues
        else:
            assert len(issues) >= 3  # At least 3 issues for incomplete


# =============================================================================
# Integration Tests - Output Generation
# =============================================================================


class TestOutputGeneration:
    """Integration tests for output generation."""

    def test_template_data_preparation(self):
        """Test that template data is prepared correctly for output."""
        content = UnifiedContent(
            id="test-123",
            source_type=ContentType.PAPER,
            title="Test Paper",
            authors=["Author One", "Author Two"],
            full_text="Content",
            annotations=[
                Annotation(type=AnnotationType.DIGITAL_HIGHLIGHT, content="Important highlight", page_number=1),
                Annotation(type=AnnotationType.HANDWRITTEN_NOTE, content="My note", page_number=2, context="Context text"),
            ],
        )
        result = ProcessingResult(
            content_id="test-123",
            analysis=ContentAnalysis(content_type="paper", domain="ml", complexity="advanced", estimated_length="medium"),
            summaries={SummaryLevel.STANDARD.value: "Standard summary text"},
            extraction=ExtractionResult(
                concepts=[Concept(name="Concept 1", definition="Definition 1", importance=ConceptImportance.CORE.value)],
                key_findings=["Finding 1"],
            ),
            tags=TagAssignment(domain_tags=["ml/test"], meta_tags=["status/new"]),
            connections=[Connection(target_id="other", target_title="Related Paper", relationship_type=RelationshipType.RELATES_TO, strength=0.7, explanation="Related topic")],
            followups=[FollowupTask(task="Do something", task_type="PRACTICE")],
            mastery_questions=[MasteryQuestion(question="Test question?", hints=["hint"], key_points=["point"])],
        )

        data = _prepare_template_data(content, result)

        assert data["title"] == "Test Paper"
        assert data["content_type"] == "paper"
        assert len(data["authors"]) == 2
        assert len(data["highlights"]) == 1
        assert data["has_handwritten_notes"] is True
        assert "ml/test" in data["tags"]


# =============================================================================
# Integration Tests - Taxonomy
# =============================================================================


class TestTaxonomyIntegration:
    """Integration tests for tag taxonomy loading and usage."""

    @pytest.mark.parametrize(
        "tag,expected_valid",
        [
            ("ml/transformers/attention", True),
            ("invalid/tag", False),
        ],
    )
    def test_taxonomy_domain_validation(self, sample_taxonomy, tag, expected_valid):
        """Test taxonomy domain tag validation."""
        assert sample_taxonomy.validate_domain_tag(tag) is expected_valid

    @pytest.mark.parametrize(
        "tag,expected_valid",
        [
            ("status/actionable", True),
            ("quality/deep-dive", True),
            ("invalid/meta", False),
        ],
    )
    def test_taxonomy_meta_validation(self, sample_taxonomy, tag, expected_valid):
        """Test taxonomy meta tag validation."""
        assert sample_taxonomy.validate_meta_tag(tag) is expected_valid

    def test_taxonomy_filter_valid_tags(self, sample_taxonomy):
        """Test filtering of valid tags."""
        tags = ["ml/transformers/attention", "invalid/domain", "status/actionable", "invalid/meta"]
        valid_domain, valid_meta = sample_taxonomy.filter_valid_tags(tags)
        assert valid_domain == ["ml/transformers/attention"]
        assert valid_meta == ["status/actionable"]

    def test_taxonomy_cache_invalidation(self):
        """Test that taxonomy cache can be invalidated."""
        TagTaxonomyLoader._taxonomy = "cached_value"
        TagTaxonomyLoader._last_loaded = 12345
        TagTaxonomyLoader.invalidate_cache()
        assert TagTaxonomyLoader._taxonomy is None
        assert TagTaxonomyLoader._last_loaded is None


# =============================================================================
# Integration Tests - Different Content Types
# =============================================================================


class TestContentTypeProcessing:
    """Integration tests for different content types."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "content_type,source_type,title,text,expected_topics,expected_code",
        [
            (
                "book",
                ContentType.BOOK,
                "Deep Learning Fundamentals",
                "Chapter 1: Deep learning is a subset of machine learning.",
                ["deep learning", "neural networks"],
                False,
            ),
            (
                "code",
                ContentType.CODE,
                "transformer-pytorch",
                "# Transformer Implementation\nclass TransformerBlock(nn.Module): pass",
                ["pytorch", "transformer"],
                True,
            ),
        ],
    )
    async def test_content_type_processing_flow(
        self, content_type, source_type, title, text, expected_topics, expected_code, mock_llm_client, mock_llm_usage
    ):
        """Test processing flow for different content types."""
        content = UnifiedContent(id=f"{content_type}-test", source_type=source_type, title=title, full_text=text)
        mock_llm_client.complete.return_value = (
            make_analysis_response(
                content_type=content_type,
                complexity="advanced" if content_type == "book" else "intermediate",
                length="long" if content_type == "book" else "short",
                topics=expected_topics,
                has_code=expected_code,
                has_math=content_type == "book",
            ),
            mock_llm_usage,
        )

        analysis, _ = await analyze_content(content, mock_llm_client)
        assert analysis.content_type == content_type
        assert analysis.has_code is expected_code


# =============================================================================
# Integration Tests - Error Recovery
# =============================================================================


class TestErrorRecovery:
    """Integration tests for error recovery scenarios."""

    @pytest.mark.asyncio
    async def test_llm_timeout_recovery(self, sample_paper_content, mock_llm_client):
        """Test recovery from LLM timeout."""
        mock_llm_client.complete.side_effect = Exception("Timeout")
        analysis, usages = await analyze_content(sample_paper_content, mock_llm_client)
        assert analysis is not None
        assert analysis.content_type == sample_paper_content.source_type.value

    @pytest.mark.asyncio
    async def test_partial_llm_response_handling(self, sample_paper_content, mock_llm_client, mock_llm_usage):
        """Test handling of partial/incomplete LLM responses."""
        mock_llm_client.complete.return_value = ({"content_type": "paper"}, mock_llm_usage)
        analysis, _ = await analyze_content(sample_paper_content, mock_llm_client)
        assert analysis is not None
        assert analysis.content_type == "paper"

    @pytest.mark.asyncio
    async def test_extraction_with_valid_concepts(self, sample_paper_content, mock_llm_client, mock_llm_usage, base_analysis):
        """Test extraction handles valid concept data correctly."""
        mock_llm_client.complete.return_value = (
            make_extraction_response(
                concepts=[
                    {"name": "Valid", "definition": "A valid concept", "importance": "CORE"},
                    {"name": "Another", "definition": "Another valid concept", "importance": "SUPPORTING"},
                ]
            ),
            mock_llm_usage,
        )
        extraction, _ = await extract_concepts(sample_paper_content, base_analysis, mock_llm_client)
        assert len(extraction.concepts) == 2
        assert extraction.concepts[0].name == "Valid"


# =============================================================================
# Integration Tests - Stage Dependencies
# =============================================================================


class TestStageDependencies:
    """Integration tests for stage dependency handling."""

    @pytest.mark.asyncio
    async def test_tagging_uses_analysis_domain(
        self, sample_paper_content, mock_llm_client, mock_llm_usage, sample_taxonomy, base_analysis
    ):
        """Test that tagging considers analysis domain."""
        mock_llm_client.complete.return_value = (make_tagging_response(), mock_llm_usage)
        tags, _ = await assign_tags(sample_paper_content.title, base_analysis, "Paper about transformers", mock_llm_client, sample_taxonomy)
        assert any("ml/" in tag for tag in tags.domain_tags)

    @pytest.mark.asyncio
    async def test_questions_use_extraction_concepts(self, sample_paper_content, mock_llm_client, mock_llm_usage, base_analysis):
        """Test that question generation uses extracted concepts."""
        extraction = ExtractionResult(
            concepts=[Concept(name="Self-attention", definition="Attention mechanism within a sequence", importance=ConceptImportance.CORE.value)],
            key_findings=["Self-attention enables parallelization"],
        )
        mock_llm_client.complete.return_value = (
            {"questions": [{"question": "What is the role of self-attention?", "type": "conceptual", "difficulty": "intermediate", "hints": ["Think about sequence relationships"], "key_points": ["Position-independent processing"]}]},
            mock_llm_usage,
        )
        questions, _ = await generate_mastery_questions(sample_paper_content, base_analysis, "Paper about self-attention", extraction, mock_llm_client)
        assert len(questions) >= 1
        assert "attention" in questions[0].question.lower()


# =============================================================================
# Integration Tests - Concurrent Processing
# =============================================================================


class TestConcurrentProcessing:
    """Integration tests for concurrent processing scenarios."""

    @pytest.mark.asyncio
    async def test_multiple_contents_in_sequence(
        self, sample_paper_content, sample_article_content, mock_llm_client, mock_llm_usage
    ):
        """Test processing multiple contents sequentially."""
        mock_llm_client.complete.side_effect = [
            (make_analysis_response("paper", "ml", "advanced", "long", ["transformers"]), mock_llm_usage),
            (make_analysis_response("article", "ml", "foundational", "medium", ["machine learning basics"]), mock_llm_usage),
        ]

        paper_analysis, _ = await analyze_content(sample_paper_content, mock_llm_client)
        article_analysis, _ = await analyze_content(sample_article_content, mock_llm_client)

        assert paper_analysis.content_type == "paper"
        assert paper_analysis.complexity == "advanced"
        assert article_analysis.content_type == "article"
        assert article_analysis.complexity == "foundational"


# =============================================================================
# Integration Tests - Data Integrity
# =============================================================================


class TestDataIntegrity:
    """Integration tests for data integrity across stages."""

    @pytest.mark.asyncio
    async def test_content_id_preserved_across_stages(self, sample_paper_content, mock_llm_client, mock_llm_usage):
        """Test that content ID is preserved across all stages."""
        original_id = sample_paper_content.id
        mock_llm_client.complete.return_value = (make_analysis_response(), mock_llm_usage)
        await analyze_content(sample_paper_content, mock_llm_client)
        assert sample_paper_content.id == original_id

    @pytest.mark.asyncio
    async def test_annotation_data_preserved(self, sample_paper_content, mock_llm_client, mock_llm_usage):
        """Test that annotation data is preserved during processing."""
        original_count = len(sample_paper_content.annotations)
        original_content = sample_paper_content.annotations[0].content
        mock_llm_client.complete.return_value = (make_analysis_response(), mock_llm_usage)
        await analyze_content(sample_paper_content, mock_llm_client)
        assert len(sample_paper_content.annotations) == original_count
        assert sample_paper_content.annotations[0].content == original_content


# =============================================================================
# Integration Tests - Special Characters and Edge Cases
# =============================================================================


class TestSpecialCharacterHandling:
    """Integration tests for special character handling."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "title,authors,text,expected_type",
        [
            ("深度学习与变压器架构", ["张三", "李四"], "深度学习是机器学习的一个子集", "article"),
            ("BERT: Pre-training <Deep> & 'Bidirectional' Transformers", None, "Paper about BERT model.", "paper"),
        ],
    )
    async def test_special_characters_in_content(self, title, authors, text, expected_type, mock_llm_client, mock_llm_usage):
        """Test processing content with special characters."""
        content = UnifiedContent(
            id="special-char-test",
            source_type=ContentType.ARTICLE if expected_type == "article" else ContentType.PAPER,
            title=title,
            authors=authors or [],
            full_text=text,
        )
        mock_llm_client.complete.return_value = (make_analysis_response(expected_type), mock_llm_usage)
        analysis, _ = await analyze_content(content, mock_llm_client)
        assert analysis is not None
        assert analysis.content_type == expected_type


class TestEdgeCases:
    """Integration tests for edge cases."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "content_id,title,text,source_type,num_authors,num_annotations,expected_length",
        [
            ("short-content", "Quick Note", "Brief.", ContentType.ARTICLE, 0, 0, "short"),
            ("many-authors", "Collaborative Paper", "Paper with many authors.", ContentType.PAPER, 50, 0, "medium"),
            ("many-annotations", "Heavily Annotated Book", "Book content here.", ContentType.BOOK, 0, 100, "long"),
        ],
    )
    async def test_edge_case_content(
        self, content_id, title, text, source_type, num_authors, num_annotations, expected_length, mock_llm_client, mock_llm_usage
    ):
        """Test processing of edge case content variations."""
        content = UnifiedContent(
            id=content_id,
            source_type=source_type,
            title=title,
            full_text=text,
            authors=[f"Author {i}" for i in range(num_authors)] if num_authors else [],
            annotations=[
                Annotation(type=AnnotationType.DIGITAL_HIGHLIGHT, content=f"Highlight {i}", page_number=i)
                for i in range(num_annotations)
            ],
        )
        mock_llm_client.complete.return_value = (
            make_analysis_response(source_type.value, length=expected_length),
            mock_llm_usage,
        )
        analysis, _ = await analyze_content(content, mock_llm_client)
        assert analysis is not None
        assert analysis.estimated_length == expected_length

    @pytest.mark.asyncio
    async def test_content_with_no_text(self, mock_llm_client):
        """Test processing content with no text."""
        content = UnifiedContent(id="no-text-content", source_type=ContentType.ARTICLE, title="Title Only", full_text="")
        analysis, usages = await analyze_content(content, mock_llm_client)
        assert analysis is not None
        assert len(usages) == 0
        mock_llm_client.complete.assert_not_called()


# =============================================================================
# Integration Tests - Validation Chain
# =============================================================================


class TestValidationChain:
    """Integration tests for validation across the pipeline."""

    def test_validate_complete_processing_result(self, sample_paper_content):
        """Test validation of a complete processing result."""
        result = ProcessingResult(
            content_id=sample_paper_content.id,
            analysis=ContentAnalysis(content_type="paper", domain="ml", complexity="advanced", estimated_length="long", key_topics=["transformers", "attention"]),
            summaries={
                SummaryLevel.BRIEF.value: "A" * 60,
                SummaryLevel.STANDARD.value: "B" * 200,
                SummaryLevel.DETAILED.value: "C" * 400,
            },
            extraction=ExtractionResult(
                concepts=[
                    Concept(name="Transformer", definition="A neural architecture based on self-attention", importance=ConceptImportance.CORE.value),
                    Concept(name="Attention", definition="Mechanism for relating sequence positions", importance=ConceptImportance.CORE.value),
                ],
                key_findings=["Transformers enable parallelization"],
            ),
            tags=TagAssignment(domain_tags=["ml/transformers/attention"], meta_tags=["status/actionable"]),
            connections=[Connection(target_id="related-paper", target_title="Related Work", relationship_type=RelationshipType.RELATES_TO, strength=0.7, explanation="Related topic")],
            followups=[FollowupTask(task="Implement attention mechanism", task_type="PRACTICE", priority="HIGH")],
            mastery_questions=[
                MasteryQuestion(question="What is the key innovation of transformers?" * 2, hints=["Think about attention"], key_points=["Self-attention", "Parallelization"]),
                MasteryQuestion(question="How does multi-head attention work?" * 2, hints=["Consider multiple perspectives"], key_points=["Parallel heads", "Concatenation"]),
            ],
        )
        issues = validate_processing_result(result)
        assert len(issues) <= 2  # Allow for minor issues
