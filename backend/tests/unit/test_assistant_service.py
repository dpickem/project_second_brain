"""
Unit Tests for Assistant Service

Tests for AssistantService functionality:
- Chat conversations with RAG
- Conversation CRUD operations
- Prompt suggestions
- Knowledge search
- Quiz generation
- Concept explanations

These tests establish a baseline before refactoring.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
import uuid

import pytest

from app.db.models_assistant import (
    AssistantConversation,
    AssistantMessage,
    MessageRole,
)
from app.enums.api import ExplanationStyle
from app.services.assistant.service import AssistantService, ASSISTANT_SYSTEM_PROMPT


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def mock_db_session() -> AsyncMock:
    """Create a mock async database session."""
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.execute = AsyncMock()
    return session


@pytest.fixture
def mock_neo4j_client() -> MagicMock:
    """Create a mock Neo4j client."""
    client = MagicMock()
    client._ensure_initialized = AsyncMock()
    client._async_driver = MagicMock()
    return client


@pytest.fixture
def mock_llm_client() -> MagicMock:
    """Create a mock LLM client."""
    client = MagicMock()
    # Default complete response
    client.complete = AsyncMock(return_value=("Test response", MagicMock()))
    # Default embed response (1536-dim embeddings)
    client.embed = AsyncMock(return_value=([[0.1] * 1536], MagicMock()))
    return client


@pytest.fixture
def mock_mastery_service() -> MagicMock:
    """Create a mock MasteryService."""
    service = MagicMock()
    service.get_weak_spots = AsyncMock(return_value=[])
    service.get_mastery_state = AsyncMock(return_value=MagicMock(mastery_score=0.5))
    return service


@pytest.fixture
def mock_spaced_rep_service() -> MagicMock:
    """Create a mock SpacedRepService."""
    service = MagicMock()
    service.get_due_cards = AsyncMock(return_value=MagicMock(total_due=0, cards=[]))
    return service


@pytest.fixture
def service(
    mock_db_session: AsyncMock,
    mock_neo4j_client: MagicMock,
    mock_llm_client: MagicMock,
    mock_mastery_service: MagicMock,
    mock_spaced_rep_service: MagicMock,
) -> AssistantService:
    """Create an AssistantService with all mocked dependencies."""
    svc = AssistantService(
        db=mock_db_session,
        neo4j_client=mock_neo4j_client,
        llm_client=mock_llm_client,
    )
    # Pre-set mocked internal services to avoid database queries
    svc._mastery_service = mock_mastery_service
    svc._spaced_rep_service = mock_spaced_rep_service
    return svc


@pytest.fixture
def service_no_deps(
    mock_db_session: AsyncMock,
    mock_mastery_service: MagicMock,
    mock_spaced_rep_service: MagicMock,
) -> AssistantService:
    """Create an AssistantService with only DB (no Neo4j/LLM)."""
    svc = AssistantService(db=mock_db_session)
    # Pre-set mocked internal services to avoid database queries
    svc._mastery_service = mock_mastery_service
    svc._spaced_rep_service = mock_spaced_rep_service
    return svc


@pytest.fixture
def sample_conversation() -> AssistantConversation:
    """Create a sample conversation for testing."""
    conv = AssistantConversation(
        id=1,
        conversation_uuid=str(uuid.uuid4()),
        title="Test Conversation",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    conv.messages = []
    return conv


@pytest.fixture
def sample_conversation_with_messages(
    sample_conversation: AssistantConversation,
) -> AssistantConversation:
    """Create a conversation with existing messages."""
    msg1 = AssistantMessage(
        id=1,
        message_uuid=str(uuid.uuid4()),
        conversation_id=sample_conversation.id,
        role=MessageRole.USER,
        content="Hello",
        created_at=datetime.now(timezone.utc),
    )
    msg2 = AssistantMessage(
        id=2,
        message_uuid=str(uuid.uuid4()),
        conversation_id=sample_conversation.id,
        role=MessageRole.ASSISTANT,
        content="Hi there!",
        created_at=datetime.now(timezone.utc),
    )
    sample_conversation.messages = [msg1, msg2]
    return sample_conversation


# =============================================================================
# Chat Tests
# =============================================================================


class TestChat:
    """Tests for the chat method."""

    async def test_chat_creates_new_conversation(
        self,
        service: AssistantService,
        mock_db_session: AsyncMock,
    ) -> None:
        """chat() creates a new conversation when no conversation_id provided."""
        # Arrange
        mock_db_session.execute = AsyncMock()

        # Mock search to return empty results
        with patch(
            "app.services.assistant.service.KnowledgeSearchService"
        ) as mock_search_class:
            mock_search = MagicMock()
            mock_search.semantic_search = AsyncMock(return_value=([], 0.0))
            mock_search_class.return_value = mock_search

            # Act
            result = await service.chat(message="Hello, assistant!")

        # Assert - Pydantic model, use attribute access
        assert result.conversation_id is not None
        assert result.response is not None
        assert result.sources is not None
        mock_db_session.add.assert_called()  # Conversation was added

    async def test_chat_uses_existing_conversation(
        self,
        service: AssistantService,
        mock_db_session: AsyncMock,
        sample_conversation: AssistantConversation,
    ) -> None:
        """chat() uses existing conversation when conversation_id provided."""
        # Arrange
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_conversation
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        with patch(
            "app.services.assistant.service.KnowledgeSearchService"
        ) as mock_search_class:
            mock_search = MagicMock()
            mock_search.semantic_search = AsyncMock(return_value=([], 0.0))
            mock_search_class.return_value = mock_search

            # Act
            result = await service.chat(
                message="Follow-up question",
                conversation_id=sample_conversation.conversation_uuid,
            )

        # Assert
        assert result.conversation_id == sample_conversation.conversation_uuid

    async def test_chat_raises_for_invalid_conversation(
        self,
        service: AssistantService,
        mock_db_session: AsyncMock,
    ) -> None:
        """chat() raises ValueError for non-existent conversation_id."""
        # Arrange
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        # Act & Assert
        with pytest.raises(ValueError, match="Conversation not found"):
            await service.chat(
                message="Hello",
                conversation_id="nonexistent-uuid",
            )

    async def test_chat_includes_sources_from_search(
        self,
        service: AssistantService,
        mock_db_session: AsyncMock,
    ) -> None:
        """chat() includes sources from knowledge search in response."""
        # Arrange
        search_results = [
            {
                "id": "doc-1",
                "title": "ML Basics",
                "summary": "Intro to ML",
                "score": 0.9,
            },
            {
                "id": "doc-2",
                "title": "Deep Learning",
                "summary": "Neural nets",
                "score": 0.8,
            },
        ]

        with patch(
            "app.services.assistant.service.KnowledgeSearchService"
        ) as mock_search_class:
            mock_search = MagicMock()
            mock_search.semantic_search = AsyncMock(return_value=(search_results, 50.0))
            mock_search_class.return_value = mock_search

            # Act
            result = await service.chat(message="Tell me about ML")

        # Assert - Pydantic models
        assert len(result.sources) == 2
        assert result.sources[0].id == "doc-1"
        assert result.sources[0].title == "ML Basics"
        assert result.sources[0].relevance <= 1.0

    async def test_chat_handles_search_failure_gracefully(
        self,
        service: AssistantService,
        mock_db_session: AsyncMock,
    ) -> None:
        """chat() continues without context when search fails."""
        # Arrange
        with patch(
            "app.services.assistant.service.KnowledgeSearchService"
        ) as mock_search_class:
            mock_search = MagicMock()
            mock_search.semantic_search = AsyncMock(
                side_effect=Exception("Search failed")
            )
            mock_search_class.return_value = mock_search

            # Act
            result = await service.chat(message="Hello")

        # Assert
        assert result.response is not None
        assert result.sources == []

    async def test_chat_without_llm_returns_error_message(
        self,
        service_no_deps: AssistantService,
    ) -> None:
        """chat() returns error message when LLM client unavailable."""
        # Act
        result = await service_no_deps.chat(message="Hello")

        # Assert
        assert "unable to generate responses" in result.response.lower()


# =============================================================================
# Conversation Management Tests
# =============================================================================


class TestConversationManagement:
    """Tests for conversation CRUD operations."""

    async def test_get_conversations_returns_paginated_list(
        self,
        service: AssistantService,
        mock_db_session: AsyncMock,
        sample_conversation: AssistantConversation,
    ) -> None:
        """get_conversations() returns paginated conversation list."""
        # Arrange
        mock_count_result = MagicMock()
        mock_count_result.scalar_one.return_value = 5

        mock_list_result = MagicMock()
        mock_list_result.scalars.return_value.all.return_value = [sample_conversation]

        mock_db_session.execute = AsyncMock(
            side_effect=[mock_count_result, mock_list_result]
        )

        # Act
        result = await service.get_conversations(limit=10, offset=0)

        # Assert - Pydantic models
        assert result.total == 5
        assert len(result.conversations) == 1
        assert result.conversations[0].id == sample_conversation.conversation_uuid

    async def test_get_conversation_returns_with_messages(
        self,
        service: AssistantService,
        mock_db_session: AsyncMock,
        sample_conversation_with_messages: AssistantConversation,
    ) -> None:
        """get_conversation() returns conversation with all messages."""
        # Arrange
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_conversation_with_messages
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await service.get_conversation(
            sample_conversation_with_messages.conversation_uuid
        )

        # Assert
        assert result is not None
        assert len(result.messages) == 2
        assert result.messages[0].role == "user"
        assert result.messages[1].role == "assistant"

    async def test_get_conversation_returns_none_for_invalid_id(
        self,
        service: AssistantService,
        mock_db_session: AsyncMock,
    ) -> None:
        """get_conversation() returns None for non-existent conversation."""
        # Arrange
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await service.get_conversation("nonexistent-uuid")

        # Assert
        assert result is None

    async def test_delete_conversation_returns_true_on_success(
        self,
        service: AssistantService,
        mock_db_session: AsyncMock,
    ) -> None:
        """delete_conversation() returns True when conversation deleted."""
        # Arrange
        mock_result = MagicMock()
        mock_result.rowcount = 1
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await service.delete_conversation("some-uuid")

        # Assert
        assert result is True

    async def test_delete_conversation_returns_false_when_not_found(
        self,
        service: AssistantService,
        mock_db_session: AsyncMock,
    ) -> None:
        """delete_conversation() returns False when conversation not found."""
        # Arrange
        mock_result = MagicMock()
        mock_result.rowcount = 0
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await service.delete_conversation("nonexistent-uuid")

        # Assert
        assert result is False

    async def test_rename_conversation_updates_title(
        self,
        service: AssistantService,
        mock_db_session: AsyncMock,
        sample_conversation: AssistantConversation,
    ) -> None:
        """rename_conversation() updates the conversation title."""
        # Arrange
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_conversation
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await service.rename_conversation(
            sample_conversation.conversation_uuid,
            "New Title",
        )

        # Assert
        assert result is not None
        assert result.title == "New Title"
        assert sample_conversation.title == "New Title"

    async def test_clear_conversation_messages_returns_count(
        self,
        service: AssistantService,
        mock_db_session: AsyncMock,
        sample_conversation_with_messages: AssistantConversation,
    ) -> None:
        """clear_conversation_messages() returns deleted message count."""
        # Arrange
        mock_get_result = MagicMock()
        mock_get_result.scalar_one_or_none.return_value = (
            sample_conversation_with_messages
        )

        mock_delete_result = MagicMock()
        mock_delete_result.rowcount = 2

        mock_db_session.execute = AsyncMock(
            side_effect=[mock_get_result, mock_delete_result]
        )

        # Act
        result = await service.clear_conversation_messages(
            sample_conversation_with_messages.conversation_uuid
        )

        # Assert
        assert result == 2

    async def test_clear_all_conversations_returns_count(
        self,
        service: AssistantService,
        mock_db_session: AsyncMock,
    ) -> None:
        """clear_all_conversations() returns deleted conversation count."""
        # Arrange
        mock_result = MagicMock()
        mock_result.rowcount = 3
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        # Act
        result = await service.clear_all_conversations()

        # Assert
        assert result == 3


# =============================================================================
# Suggestions Tests
# =============================================================================


class TestSuggestions:
    """Tests for prompt suggestions."""

    async def test_get_suggestions_returns_default_suggestions(
        self,
        service: AssistantService,
    ) -> None:
        """get_suggestions() returns list of suggestions (default or personalized)."""
        # Act
        result = await service.get_suggestions()

        # Assert - Pydantic model
        assert result.suggestions is not None
        # Should return at least some suggestions (may be less than 5 if services fail)
        assert len(result.suggestions) >= 1
        # Check structure
        for suggestion in result.suggestions:
            assert suggestion.text is not None
            assert suggestion.category is not None


# =============================================================================
# Knowledge Search Tests
# =============================================================================


class TestKnowledgeSearch:
    """Tests for knowledge search."""

    async def test_search_knowledge_returns_results(
        self,
        service: AssistantService,
    ) -> None:
        """search_knowledge() returns formatted search results."""
        # Arrange
        search_results = [
            {
                "id": "doc-1",
                "title": "Result 1",
                "summary": "Summary 1",
                "score": 0.9,
                "node_type": "Content",
            },
        ]

        with patch(
            "app.services.assistant.service.KnowledgeSearchService"
        ) as mock_search_class:
            mock_search = MagicMock()
            mock_search.semantic_search = AsyncMock(return_value=(search_results, 50.0))
            mock_search_class.return_value = mock_search

            # Act
            result = await service.search_knowledge("test query")

        # Assert - Pydantic models
        assert len(result.results) == 1
        assert result.results[0].id == "doc-1"
        assert result.results[0].type == "Content"

    async def test_search_knowledge_without_neo4j_returns_empty(
        self,
        service_no_deps: AssistantService,
    ) -> None:
        """search_knowledge() returns empty results when Neo4j unavailable."""
        # Act
        result = await service_no_deps.search_knowledge("test query")

        # Assert
        assert result.results == []


# =============================================================================
# Recommendations Tests
# =============================================================================


class TestRecommendations:
    """Tests for study recommendations."""

    async def test_get_recommendations_returns_default_recommendations(
        self,
        service: AssistantService,
    ) -> None:
        """get_recommendations() returns study recommendations (default or personalized)."""
        # Act
        result = await service.get_recommendations()

        # Assert - Pydantic model
        assert result.recommendations is not None
        # Should return at least one recommendation (default if services unavailable)
        assert len(result.recommendations) >= 1
        # Check structure
        for rec in result.recommendations:
            assert rec.topic_id is not None
            assert rec.topic_name is not None
            assert rec.reason is not None
            assert rec.priority is not None


# =============================================================================
# Quiz Generation Tests
# =============================================================================


class TestQuizGeneration:
    """Tests for quiz generation."""

    async def test_generate_quiz_returns_questions(
        self,
        service: AssistantService,
    ) -> None:
        """generate_quiz() returns quiz with questions when ExerciseGenerator works."""
        # Arrange - mock the ExerciseGenerator
        from app.models.learning import ExerciseResponse
        from app.enums.learning import ExerciseType, ExerciseDifficulty

        mock_exercise = ExerciseResponse(
            id=1,
            exercise_uuid="test-uuid-1",
            exercise_type=ExerciseType.FREE_RECALL,
            topic="machine-learning",
            difficulty=ExerciseDifficulty.INTERMEDIATE,
            prompt="What is machine learning?",
            hints=["Think about data and patterns"],
            expected_key_points=["Algorithms", "Learning from data"],
        )

        mock_generator = AsyncMock()
        mock_generator.generate_exercise = AsyncMock(return_value=mock_exercise)
        service._exercise_generator = mock_generator

        # Act
        result = await service.generate_quiz("machine-learning", question_count=2)

        # Assert - Pydantic models
        assert result.quiz_id is not None
        assert result.topic == "machine-learning"
        assert len(result.questions) == 2
        # Exercises are converted to free_response quiz questions
        assert result.questions[0].type == "free_response"
        assert result.questions[0].question == "What is machine learning?"

    async def test_generate_quiz_without_llm_returns_empty_questions(
        self,
        service_no_deps: AssistantService,
    ) -> None:
        """generate_quiz() returns empty questions when LLM unavailable."""
        # Act
        result = await service_no_deps.generate_quiz("test-topic")

        # Assert
        assert result.questions == []


# =============================================================================
# Concept Explanation Tests
# =============================================================================


class TestConceptExplanation:
    """Tests for concept explanations."""

    @pytest.mark.parametrize(
        "style,expected_keyword",
        [
            (ExplanationStyle.SIMPLE, "brief"),
            (ExplanationStyle.DETAILED, "comprehensive"),
            (ExplanationStyle.ELI5, "5 years old"),
        ],
    )
    async def test_explain_concept_uses_correct_style(
        self,
        service: AssistantService,
        mock_llm_client: MagicMock,
        style: ExplanationStyle,
        expected_keyword: str,
    ) -> None:
        """explain_concept() uses appropriate instruction for each style."""
        # Arrange
        mock_llm_client.complete = AsyncMock(
            return_value=(
                {"explanation": "Test explanation", "examples": ["Example 1"]},
                MagicMock(),
            )
        )

        with patch(
            "app.services.assistant.service.KnowledgeSearchService"
        ) as mock_search_class:
            mock_search = MagicMock()
            mock_search.semantic_search = AsyncMock(return_value=([], 0.0))
            mock_search_class.return_value = mock_search

            # Act
            await service.explain_concept("neural-networks", style=style)

        # Assert - verify the prompt contains style-specific instruction
        call_args = mock_llm_client.complete.call_args
        messages = call_args.kwargs.get(
            "messages", call_args.args[1] if len(call_args.args) > 1 else []
        )
        prompt_content = messages[0]["content"]
        assert expected_keyword.lower() in prompt_content.lower()

    async def test_explain_concept_returns_related_concepts(
        self,
        service: AssistantService,
        mock_llm_client: MagicMock,
    ) -> None:
        """explain_concept() includes related concepts from search."""
        # Arrange
        search_results = [
            {"id": "concept-1", "title": "Main Concept", "summary": "..."},
            {"id": "concept-2", "title": "Related 1", "summary": "..."},
            {"id": "concept-3", "title": "Related 2", "summary": "..."},
        ]

        mock_llm_client.complete = AsyncMock(
            return_value=(
                {"explanation": "Test", "examples": []},
                MagicMock(),
            )
        )

        with patch(
            "app.services.assistant.service.KnowledgeSearchService"
        ) as mock_search_class:
            mock_search = MagicMock()
            mock_search.semantic_search = AsyncMock(return_value=(search_results, 50.0))
            mock_search_class.return_value = mock_search

            # Act
            result = await service.explain_concept("test-concept")

        # Assert - Pydantic models
        assert len(result.related_concepts) == 2  # Excludes first (self)
        assert result.related_concepts[0].id == "concept-2"

    async def test_explain_concept_without_llm_returns_error_message(
        self,
        service_no_deps: AssistantService,
    ) -> None:
        """explain_concept() returns error message when LLM unavailable."""
        # Act
        result = await service_no_deps.explain_concept("test")

        # Assert
        assert "unavailable" in result.explanation.lower()


# =============================================================================
# Helper Method Tests
# =============================================================================


class TestHelperMethods:
    """Tests for internal helper methods."""

    def test_format_context_with_results(
        self,
        service: AssistantService,
    ) -> None:
        """_format_context() formats search results as context string."""
        # Arrange
        results = [
            {"title": "Doc 1", "summary": "Summary of doc 1"},
            {"title": "Doc 2", "summary": "Summary of doc 2"},
        ]

        # Act
        context = service._format_context(results)

        # Assert
        assert "Doc 1" in context
        assert "Summary of doc 1" in context
        assert "Doc 2" in context

    def test_format_context_empty_results(
        self,
        service: AssistantService,
    ) -> None:
        """_format_context() returns empty string for empty results."""
        # Act
        context = service._format_context([])

        # Assert
        assert context == ""

    def test_format_context_truncates_long_summaries(
        self,
        service: AssistantService,
    ) -> None:
        """_format_context() truncates summaries longer than max length."""
        # Arrange
        long_summary = "x" * 600
        results = [{"title": "Doc", "summary": long_summary}]

        # Act
        context = service._format_context(results)

        # Assert
        assert len(context) < len(long_summary) + 100  # Title + some overhead

    async def test_get_conversation_history_limits_messages(
        self,
        service: AssistantService,
        sample_conversation: AssistantConversation,
    ) -> None:
        """_get_conversation_history() respects max_messages limit."""
        # Arrange - create 15 messages
        sample_conversation.messages = [
            AssistantMessage(
                message_uuid=str(uuid.uuid4()),
                conversation_id=1,
                role=MessageRole.USER if i % 2 == 0 else MessageRole.ASSISTANT,
                content=f"Message {i}",
                created_at=datetime.now(timezone.utc),
            )
            for i in range(15)
        ]

        # Act
        history = await service._get_conversation_history(
            sample_conversation, max_messages=10
        )

        # Assert
        assert len(history) == 10
        # Should be the last 10 messages
        assert history[0]["content"] == "Message 5"
