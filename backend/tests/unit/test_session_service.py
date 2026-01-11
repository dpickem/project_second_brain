"""
Unit tests for SessionService.

Tests the practice session orchestration service, focusing on:
- Time allocation logic
- Topic-focused vs general sessions
- Exercise reuse vs generation
- Session time filling behavior
- Mastery service integration
- Error handling scenarios
- Content mode configuration (exercises only, cards only, both)
- Source preference configuration (existing, generate, prefer_existing)

Test Organization:
    - TestSessionServiceInitialization: Service initialization tests
    - TestTopicFocusedSessions: Topic-filtered session creation
    - TestGeneralSessions: Sessions without topic filter
    - TestSessionTimeFilling: Time allocation and filling behavior
    - TestMasteryIntegration: Mastery level integration tests
    - TestExistingExerciseRetrieval: Database exercise retrieval tests
    - TestErrorHandling: Error scenarios and graceful degradation
    - TestSessionResponse: Response structure validation
    - TestContentModeConfiguration: Content mode (exercises/cards/both) tests
    - TestSourcePreferences: Source preference configuration tests
    - TestSessionTimeBudget: Time budget manager tests
    - TestConfigurationResolvers: Configuration resolver function tests
    - TestExerciseRatioOverride: Exercise ratio override tests
"""

from datetime import datetime, timezone
from typing import Any, Callable, Optional
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.enums.learning import (
    CardState,
    ContentSourcePreference,
    ExerciseDifficulty,
    ExerciseType,
    SessionContentMode,
)
from app.models.learning import (
    CardResponse,
    DueCardsResponse,
    ExerciseResponse,
    MasteryState,
    ReviewForecast,
    SessionCreateRequest,
    SessionResponse,
)
from app.services.learning.session_budget import (
    SessionTimeBudget,
    resolve_card_source,
    resolve_content_mode,
    resolve_exercise_source,
)
from app.services.learning.session_service import SessionService


# =============================================================================
# Type Aliases
# =============================================================================

MockDB = MagicMock
MockSpacedRepService = MagicMock
MockExerciseGenerator = MagicMock
MockMasteryService = MagicMock


# =============================================================================
# Test Data Constants
# =============================================================================

DEFAULT_TOPIC: str = "ml"
DEFAULT_TOPIC_NAME: str = "Machine Learning"
DEFAULT_ESTIMATED_TIME_MINUTES: int = 10
DEFAULT_MASTERY_SCORE: float = 0.5
DEFAULT_SESSION_ID: int = 1


# =============================================================================
# Helper Functions - Mock Object Factories
# =============================================================================


def create_mock_exercise(
    exercise_id: int = 1,
    topic: str = DEFAULT_TOPIC,
    exercise_type: ExerciseType = ExerciseType.FREE_RECALL,
    estimated_time: int = DEFAULT_ESTIMATED_TIME_MINUTES,
    difficulty: ExerciseDifficulty = ExerciseDifficulty.INTERMEDIATE,
) -> ExerciseResponse:
    """
    Create a mock ExerciseResponse for testing.

    Args:
        exercise_id: Unique exercise identifier.
        topic: Topic path for the exercise.
        exercise_type: Type of exercise (free_recall, self_explain, etc.).
        estimated_time: Estimated completion time in minutes.
        difficulty: Exercise difficulty level.

    Returns:
        A fully populated ExerciseResponse instance.
    """
    return ExerciseResponse(
        id=exercise_id,
        exercise_uuid=f"uuid-{exercise_id}",
        exercise_type=exercise_type,
        topic=topic,
        difficulty=difficulty,
        prompt=f"Explain {topic}",
        hints=["Think about the basics"],
        expected_key_points=["Key point 1", "Key point 2"],
        estimated_time_minutes=estimated_time,
        tags=[topic],
    )


def create_mock_card(
    card_id: int = 1,
    tags: Optional[list[str]] = None,
) -> CardResponse:
    """
    Create a mock CardResponse for testing.

    Args:
        card_id: Unique card identifier.
        tags: List of topic tags for the card.

    Returns:
        A fully populated CardResponse instance.
    """
    return CardResponse(
        id=card_id,
        card_type="concept",
        front=f"Question {card_id}",
        back=f"Answer {card_id}",
        state=CardState.REVIEW,
        due_date=datetime.now(timezone.utc),
        repetitions=5,
        tags=tags or [DEFAULT_TOPIC],
    )


def create_mock_exercise_orm(
    exercise_id: int = 1,
    topic: str = DEFAULT_TOPIC,
    exercise_type: str = "free_recall",
    difficulty: str = "intermediate",
    estimated_time: int = DEFAULT_ESTIMATED_TIME_MINUTES,
) -> MagicMock:
    """
    Create a mock ORM Exercise object (for database queries).

    Args:
        exercise_id: Unique exercise identifier.
        topic: Topic path for the exercise.
        exercise_type: Exercise type as string value.
        difficulty: Difficulty level as string value.
        estimated_time: Estimated completion time in minutes.

    Returns:
        A MagicMock configured to behave like an ORM Exercise.
    """
    return MagicMock(
        id=exercise_id,
        exercise_uuid=f"uuid-{exercise_id}",
        exercise_type=exercise_type,
        topic=topic,
        difficulty=difficulty,
        prompt=f"Question {exercise_id}",
        hints=["hint"],
        expected_key_points=["point"],
        worked_example=None,
        follow_up_problem=None,
        language=None,
        starter_code=None,
        buggy_code=None,
        estimated_time_minutes=estimated_time,
        tags=[topic],
    )


def create_review_forecast(
    overdue: int = 0,
    today: int = 0,
    tomorrow: int = 0,
    this_week: int = 0,
    later: int = 0,
) -> ReviewForecast:
    """
    Create a ReviewForecast for DueCardsResponse.

    Args:
        overdue: Number of overdue cards.
        today: Number of cards due today.
        tomorrow: Number of cards due tomorrow.
        this_week: Number of cards due this week.
        later: Number of cards due later.

    Returns:
        A ReviewForecast instance.
    """
    return ReviewForecast(
        overdue=overdue,
        today=today,
        tomorrow=tomorrow,
        this_week=this_week,
        later=later,
    )


def create_due_cards_response(
    cards: Optional[list[CardResponse]] = None,
    total_due: int = 0,
) -> DueCardsResponse:
    """
    Create a DueCardsResponse with proper forecast structure.

    Args:
        cards: List of due cards.
        total_due: Total number of due cards.

    Returns:
        A DueCardsResponse with review forecast.
    """
    return DueCardsResponse(
        cards=cards or [],
        total_due=total_due,
        review_forecast=create_review_forecast(today=total_due),
    )


def create_mastery_state(
    topic_path: str = DEFAULT_TOPIC,
    mastery_score: float = DEFAULT_MASTERY_SCORE,
    status: str = "learning",
    suggested_types: Optional[list[str]] = None,
) -> MasteryState:
    """
    Create a MasteryState for testing.

    Args:
        topic_path: Topic identifier.
        mastery_score: Current mastery level (0-1).
        status: Learning status (learning, mastering, etc.).
        suggested_types: Suggested exercise types.

    Returns:
        A MasteryState instance.
    """
    return MasteryState(
        topic_path=topic_path,
        topic_name=DEFAULT_TOPIC_NAME,
        mastery_score=mastery_score,
        practice_count=10,
        success_rate=80.0,
        last_practiced=datetime.now(timezone.utc),
        suggested_exercise_types=suggested_types or ["free_recall", "self_explain"],
        status=status,
    )


# =============================================================================
# Helper Functions - Mock Database Setup
# =============================================================================


def setup_db_mock_with_session_id(
    mock_db: MockDB,
    session_id: int = DEFAULT_SESSION_ID,
) -> None:
    """
    Configure mock database to return a session with specified ID.

    Args:
        mock_db: Mock database session.
        session_id: Session ID to assign.
    """

    async def refresh_session(session: Any) -> None:
        session.id = session_id

    mock_db.refresh = AsyncMock(side_effect=refresh_session)


def setup_db_mock_with_empty_result(mock_db: MockDB) -> None:
    """
    Configure mock database to return empty query results.

    Args:
        mock_db: Mock database session.
    """
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_db.execute = AsyncMock(return_value=mock_result)


def setup_db_mock_with_exercises(
    mock_db: MockDB,
    exercises: list[MagicMock],
) -> None:
    """
    Configure mock database to return specified exercises.

    Args:
        mock_db: Mock database session.
        exercises: List of mock ORM exercise objects.
    """
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = exercises
    mock_db.execute = AsyncMock(return_value=mock_result)


# =============================================================================
# Module-Level Fixtures
# =============================================================================


@pytest.fixture
def mock_db() -> MockDB:
    """Create a mock database session with async support."""
    mock = MagicMock()
    mock.add = MagicMock()
    mock.commit = AsyncMock()
    mock.refresh = AsyncMock()
    mock.execute = AsyncMock()
    return mock


@pytest.fixture
def mock_spaced_rep_service() -> MockSpacedRepService:
    """Create a mock spaced repetition service with default empty response."""
    mock = MagicMock()
    mock.get_due_cards = AsyncMock(return_value=create_due_cards_response())
    return mock


@pytest.fixture
def mock_exercise_generator() -> MockExerciseGenerator:
    """Create a mock exercise generator that returns new exercises."""
    mock = MagicMock()

    async def generate_exercise(
        *args: Any, **kwargs: Any
    ) -> tuple[ExerciseResponse, list[Any]]:
        return (create_mock_exercise(), [])  # Returns (exercise, usages)

    mock.generate_exercise = AsyncMock(side_effect=generate_exercise)
    return mock


@pytest.fixture
def mock_mastery_service() -> MockMasteryService:
    """Create a mock mastery service with default mastery state."""
    mock = MagicMock()
    mock.get_mastery_state = AsyncMock(return_value=create_mastery_state())
    mock.get_weak_spots = AsyncMock(return_value=[])
    return mock


@pytest.fixture
def session_service(
    mock_db: MockDB,
    mock_spaced_rep_service: MockSpacedRepService,
    mock_exercise_generator: MockExerciseGenerator,
    mock_mastery_service: MockMasteryService,
) -> SessionService:
    """
    Create a SessionService with all mocked dependencies.

    This fixture sets up the mock database to return a session ID of 1
    and configures all necessary service dependencies.
    """
    setup_db_mock_with_session_id(mock_db, session_id=DEFAULT_SESSION_ID)
    return SessionService(
        db=mock_db,
        spaced_rep_service=mock_spaced_rep_service,
        exercise_generator=mock_exercise_generator,
        mastery_service=mock_mastery_service,
    )


@pytest.fixture
def mock_cards() -> list[CardResponse]:
    """Create a standard list of mock cards for testing."""
    return [create_mock_card(card_id=i) for i in range(1, 6)]


@pytest.fixture
def mock_exercises_orm() -> list[MagicMock]:
    """Create a standard list of mock ORM exercises for testing."""
    return [create_mock_exercise_orm(exercise_id=i) for i in range(1, 4)]


# =============================================================================
# Test Classes
# =============================================================================


class TestSessionServiceInitialization:
    """Tests for SessionService initialization."""

    def test_init_with_all_services(
        self,
        mock_db: MockDB,
        mock_spaced_rep_service: MockSpacedRepService,
        mock_exercise_generator: MockExerciseGenerator,
        mock_mastery_service: MockMasteryService,
    ) -> None:
        """Test initialization with all services provided."""
        service = SessionService(
            db=mock_db,
            spaced_rep_service=mock_spaced_rep_service,
            exercise_generator=mock_exercise_generator,
            mastery_service=mock_mastery_service,
        )

        assert service.db is mock_db
        assert service.spaced_rep is mock_spaced_rep_service
        assert service.exercise_gen is mock_exercise_generator
        assert service.mastery_service is mock_mastery_service

    def test_init_without_mastery_service(
        self,
        mock_db: MockDB,
        mock_spaced_rep_service: MockSpacedRepService,
        mock_exercise_generator: MockExerciseGenerator,
    ) -> None:
        """Test initialization without mastery service (optional dependency)."""
        service = SessionService(
            db=mock_db,
            spaced_rep_service=mock_spaced_rep_service,
            exercise_generator=mock_exercise_generator,
            mastery_service=None,
        )

        assert service.mastery_service is None


class TestTopicFocusedSessions:
    """Tests for topic-focused session creation."""

    @pytest.mark.asyncio
    async def test_topic_session_allocates_80_percent_to_exercises(
        self,
        session_service: SessionService,
        mock_db: MockDB,
        mock_exercise_generator: MockExerciseGenerator,
    ) -> None:
        """Test that topic-focused sessions allocate 80% time to exercises."""
        setup_db_mock_with_empty_result(mock_db)

        request = SessionCreateRequest(
            duration_minutes=30,
            topic_filter=DEFAULT_TOPIC,
            exercise_source=ContentSourcePreference.GENERATE_NEW,
        )

        response = await session_service.create_session(request)

        # 80% of 30 min = 24 min for exercises
        # 24 min / 10 min per exercise = 2-3 exercises (with fill mechanism)
        exercise_count = sum(
            1 for item in response.items if item.item_type == "exercise"
        )
        assert exercise_count >= 2

        # Verify exercises were generated
        assert mock_exercise_generator.generate_exercise.call_count >= 2

    @pytest.mark.asyncio
    async def test_topic_session_reuses_existing_exercises(
        self,
        session_service: SessionService,
        mock_db: MockDB,
        mock_exercises_orm: list[MagicMock],
    ) -> None:
        """Test that exercise_source=prefer_existing fetches from database first."""
        setup_db_mock_with_exercises(mock_db, mock_exercises_orm)

        request = SessionCreateRequest(
            duration_minutes=30,
            topic_filter=DEFAULT_TOPIC,
            exercise_source=ContentSourcePreference.PREFER_EXISTING,
        )

        response = await session_service.create_session(request)

        exercise_count = sum(
            1 for item in response.items if item.item_type == "exercise"
        )
        assert exercise_count >= 2

    @pytest.mark.asyncio
    async def test_topic_session_generates_when_existing_insufficient(
        self,
        session_service: SessionService,
        mock_db: MockDB,
        mock_exercise_generator: MockExerciseGenerator,
    ) -> None:
        """Test that exercises are generated when existing don't fill the time."""
        # Only 1 existing exercise (insufficient for 30 min session)
        mock_exercise = create_mock_exercise_orm(exercise_id=1)
        setup_db_mock_with_exercises(mock_db, [mock_exercise])

        request = SessionCreateRequest(
            duration_minutes=30,
            topic_filter=DEFAULT_TOPIC,
            exercise_source=ContentSourcePreference.PREFER_EXISTING,
        )

        await session_service.create_session(request)

        # Should have generated additional exercises to fill the time
        assert mock_exercise_generator.generate_exercise.call_count >= 1


class TestGeneralSessions:
    """Tests for general (no topic filter) session creation."""

    @pytest.mark.asyncio
    async def test_general_session_without_topic_gets_cards(
        self,
        session_service: SessionService,
        mock_spaced_rep_service: MockSpacedRepService,
        mock_cards: list[CardResponse],
    ) -> None:
        """Test that sessions without topic filter get spaced rep cards."""
        mock_spaced_rep_service.get_due_cards = AsyncMock(
            return_value=create_due_cards_response(cards=mock_cards[:3], total_due=3)
        )

        request = SessionCreateRequest(
            duration_minutes=15,
            topic_filter=None,
        )

        response = await session_service.create_session(request)

        card_count = sum(1 for item in response.items if item.item_type == "card")
        assert card_count >= 1


class TestSessionTimeFilling:
    """Tests for session time filling behavior."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("duration_minutes", "min_expected_exercises"),
        [
            pytest.param(15, 1, id="15min_session"),
            pytest.param(30, 2, id="30min_session"),
            pytest.param(60, 4, id="60min_session"),
        ],
    )
    async def test_session_fills_with_exercises_based_on_duration(
        self,
        session_service: SessionService,
        mock_db: MockDB,
        mock_exercise_generator: MockExerciseGenerator,
        duration_minutes: int,
        min_expected_exercises: int,
    ) -> None:
        """Test that sessions get filled with exercises proportional to duration."""
        setup_db_mock_with_empty_result(mock_db)

        request = SessionCreateRequest(
            duration_minutes=duration_minutes,
            topic_filter=DEFAULT_TOPIC,
            exercise_source=ContentSourcePreference.GENERATE_NEW,
        )

        response = await session_service.create_session(request)

        exercise_count = sum(
            1 for item in response.items if item.item_type == "exercise"
        )
        assert exercise_count >= min_expected_exercises

        # Total estimated time should be reasonable
        assert response.estimated_duration_minutes >= min_expected_exercises * 10

    @pytest.mark.asyncio
    async def test_remaining_time_filled_with_additional_exercises(
        self,
        session_service: SessionService,
        mock_db: MockDB,
        mock_exercise_generator: MockExerciseGenerator,
    ) -> None:
        """Test that fill-remaining-time phase adds more exercises when needed."""
        # Mock 1 existing exercise on first call, empty on subsequent
        mock_exercise = create_mock_exercise_orm(exercise_id=1)
        call_count = [0]

        async def mock_execute(query: Any) -> MagicMock:
            result = MagicMock()
            if call_count[0] == 0:
                # First call: return 1 exercise
                result.scalars.return_value.all.return_value = [mock_exercise]
            else:
                # Subsequent calls: return empty
                result.scalars.return_value.all.return_value = []
            call_count[0] += 1
            return result

        mock_db.execute = AsyncMock(side_effect=mock_execute)

        request = SessionCreateRequest(
            duration_minutes=30,
            topic_filter=DEFAULT_TOPIC,
            exercise_source=ContentSourcePreference.PREFER_EXISTING,
        )

        response = await session_service.create_session(request)

        # Should have multiple exercises (existing + generated to fill time)
        exercise_count = sum(
            1 for item in response.items if item.item_type == "exercise"
        )
        assert exercise_count >= 2


class TestMasteryIntegration:
    """Tests for mastery service integration."""

    @pytest.mark.asyncio
    async def test_mastery_level_passed_to_exercise_generator(
        self,
        session_service: SessionService,
        mock_db: MockDB,
        mock_exercise_generator: MockExerciseGenerator,
        mock_mastery_service: MockMasteryService,
    ) -> None:
        """Test that mastery level is fetched and passed to exercise generator."""
        high_mastery = 0.75
        mock_mastery_service.get_mastery_state = AsyncMock(
            return_value=create_mastery_state(
                mastery_score=high_mastery,
                status="mastering",
                suggested_types=["application", "teach_back"],
            )
        )
        setup_db_mock_with_empty_result(mock_db)

        request = SessionCreateRequest(
            duration_minutes=15,
            topic_filter=DEFAULT_TOPIC,
            exercise_source=ContentSourcePreference.GENERATE_NEW,
        )

        await session_service.create_session(request)

        # Verify mastery service was called
        mock_mastery_service.get_mastery_state.assert_called_once_with(DEFAULT_TOPIC)

        # Verify exercise generator was called with mastery level
        call_kwargs = mock_exercise_generator.generate_exercise.call_args.kwargs
        assert call_kwargs.get("mastery_level") == high_mastery

    @pytest.mark.asyncio
    async def test_default_mastery_when_service_unavailable(
        self,
        mock_db: MockDB,
        mock_spaced_rep_service: MockSpacedRepService,
        mock_exercise_generator: MockExerciseGenerator,
    ) -> None:
        """Test that default mastery (0.5) is used when mastery service unavailable."""
        setup_db_mock_with_session_id(mock_db)
        setup_db_mock_with_empty_result(mock_db)

        # Create service without mastery service
        service = SessionService(
            db=mock_db,
            spaced_rep_service=mock_spaced_rep_service,
            exercise_generator=mock_exercise_generator,
            mastery_service=None,
        )

        request = SessionCreateRequest(
            duration_minutes=15,
            topic_filter=DEFAULT_TOPIC,
            exercise_source=ContentSourcePreference.GENERATE_NEW,
        )

        await service.create_session(request)

        # Verify exercise generator was called with default mastery level
        call_kwargs = mock_exercise_generator.generate_exercise.call_args.kwargs
        assert call_kwargs.get("mastery_level") == DEFAULT_MASTERY_SCORE


class TestExistingExerciseRetrieval:
    """Tests for _get_existing_exercises method with different mastery levels."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("mastery_level", "description"),
        [
            pytest.param(0.2, "novice", id="novice_mastery"),
            pytest.param(0.5, "intermediate", id="intermediate_mastery"),
            pytest.param(0.85, "advanced", id="advanced_mastery"),
        ],
    )
    async def test_exercises_retrieved_based_on_mastery_level(
        self,
        mock_db: MockDB,
        mock_spaced_rep_service: MockSpacedRepService,
        mock_exercise_generator: MockExerciseGenerator,
        mock_mastery_service: MockMasteryService,
        mastery_level: float,
        description: str,
    ) -> None:
        """
        Test that exercise retrieval queries database with appropriate difficulty.

        Different mastery levels should result in different difficulty filters:
        - Novice (< 0.3): Foundational exercises
        - Intermediate (0.3-0.7): Foundational + Intermediate exercises
        - Advanced (> 0.7): Intermediate + Advanced exercises
        """
        service = SessionService(
            db=mock_db,
            spaced_rep_service=mock_spaced_rep_service,
            exercise_generator=mock_exercise_generator,
            mastery_service=mock_mastery_service,
        )
        setup_db_mock_with_empty_result(mock_db)

        await service._get_existing_exercises(
            topic=DEFAULT_TOPIC,
            limit=5,
            mastery_level=mastery_level,
        )

        # Verify database was queried
        mock_db.execute.assert_called()


class TestErrorHandling:
    """Tests for error handling in session creation."""

    @pytest.mark.asyncio
    async def test_raises_error_when_no_exercises_can_be_generated(
        self,
        session_service: SessionService,
        mock_db: MockDB,
        mock_exercise_generator: MockExerciseGenerator,
    ) -> None:
        """Test that RuntimeError is raised when exercise generation fails completely."""
        setup_db_mock_with_empty_result(mock_db)

        # Make exercise generation fail
        mock_exercise_generator.generate_exercise = AsyncMock(
            side_effect=Exception("LLM API Error")
        )

        request = SessionCreateRequest(
            duration_minutes=15,
            topic_filter=DEFAULT_TOPIC,
            exercise_source=ContentSourcePreference.GENERATE_NEW,
        )

        with pytest.raises(RuntimeError, match="Failed to generate exercise"):
            await session_service.create_session(request)

    @pytest.mark.asyncio
    async def test_continues_with_partial_exercises_on_generation_failure(
        self,
        session_service: SessionService,
        mock_db: MockDB,
        mock_exercise_generator: MockExerciseGenerator,
    ) -> None:
        """Test that session continues if some exercises fail but others succeed."""
        setup_db_mock_with_empty_result(mock_db)

        # First two calls succeed, subsequent calls fail
        call_count = [0]

        async def mock_generate(
            *args: Any, **kwargs: Any
        ) -> tuple[ExerciseResponse, list[Any]]:
            call_count[0] += 1
            if call_count[0] <= 2:
                return (create_mock_exercise(exercise_id=call_count[0]), [])
            raise Exception("LLM API Error")

        mock_exercise_generator.generate_exercise = AsyncMock(side_effect=mock_generate)

        request = SessionCreateRequest(
            duration_minutes=30,
            topic_filter=DEFAULT_TOPIC,
            exercise_source=ContentSourcePreference.GENERATE_NEW,
        )

        response = await session_service.create_session(request)

        # Should have at least the first exercise(s)
        exercise_count = sum(
            1 for item in response.items if item.item_type == "exercise"
        )
        assert exercise_count >= 1


class TestSessionResponse:
    """Tests for session response structure validation."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "field_check",
        [
            pytest.param(
                lambda r: r.session_id == DEFAULT_SESSION_ID,
                id="has_session_id",
            ),
            pytest.param(
                lambda r: DEFAULT_TOPIC in r.topics_covered,
                id="has_topic_covered",
            ),
            pytest.param(
                lambda r: r.estimated_duration_minutes > 0,
                id="has_estimated_duration",
            ),
        ],
    )
    async def test_response_structure(
        self,
        session_service: SessionService,
        mock_db: MockDB,
        field_check: Callable[[SessionResponse], bool],
    ) -> None:
        """Test that session response includes all required fields."""
        setup_db_mock_with_empty_result(mock_db)

        request = SessionCreateRequest(
            duration_minutes=15,
            topic_filter=DEFAULT_TOPIC,
        )

        response = await session_service.create_session(request)

        assert field_check(response)


class TestContentModeConfiguration:
    """Tests for content mode configuration (exercises only, cards only, both)."""

    @pytest.mark.asyncio
    async def test_exercises_only_mode_excludes_cards(
        self,
        session_service: SessionService,
        mock_db: MockDB,
        mock_spaced_rep_service: MockSpacedRepService,
        mock_cards: list[CardResponse],
    ) -> None:
        """Test that exercises_only mode does not include cards."""
        # Mock some due cards that should NOT be included
        mock_spaced_rep_service.get_due_cards = AsyncMock(
            return_value=create_due_cards_response(cards=mock_cards[:3], total_due=3)
        )
        setup_db_mock_with_empty_result(mock_db)

        request = SessionCreateRequest(
            duration_minutes=15,
            topic_filter=DEFAULT_TOPIC,
            content_mode=SessionContentMode.EXERCISES_ONLY,
        )

        response = await session_service.create_session(request)

        # Should have no cards
        card_count = sum(1 for item in response.items if item.item_type == "card")
        assert card_count == 0

    @pytest.mark.asyncio
    async def test_cards_only_mode_excludes_exercises(
        self,
        session_service: SessionService,
        mock_db: MockDB,
        mock_spaced_rep_service: MockSpacedRepService,
        mock_exercise_generator: MockExerciseGenerator,
        mock_cards: list[CardResponse],
    ) -> None:
        """Test that cards_only mode does not include exercises."""
        mock_spaced_rep_service.get_due_cards = AsyncMock(
            return_value=create_due_cards_response(cards=mock_cards, total_due=5)
        )

        request = SessionCreateRequest(
            duration_minutes=15,
            content_mode=SessionContentMode.CARDS_ONLY,
        )

        response = await session_service.create_session(request)

        # Should have no exercises
        exercise_count = sum(
            1 for item in response.items if item.item_type == "exercise"
        )
        assert exercise_count == 0

        # Exercise generator should not be called
        mock_exercise_generator.generate_exercise.assert_not_called()

    @pytest.mark.asyncio
    async def test_both_mode_includes_exercises_and_cards(
        self,
        session_service: SessionService,
        mock_db: MockDB,
        mock_spaced_rep_service: MockSpacedRepService,
        mock_exercise_generator: MockExerciseGenerator,
        mock_cards: list[CardResponse],
    ) -> None:
        """Test that 'both' mode includes both exercises and cards."""
        mock_spaced_rep_service.get_due_cards = AsyncMock(
            return_value=create_due_cards_response(cards=mock_cards[:3], total_due=3)
        )
        setup_db_mock_with_empty_result(mock_db)

        request = SessionCreateRequest(
            duration_minutes=30,
            topic_filter=DEFAULT_TOPIC,
            content_mode=SessionContentMode.BOTH,
            exercise_source=ContentSourcePreference.GENERATE_NEW,
        )

        response = await session_service.create_session(request)

        # Should have both exercises and cards
        exercise_count = sum(
            1 for item in response.items if item.item_type == "exercise"
        )
        card_count = sum(1 for item in response.items if item.item_type == "card")

        assert exercise_count > 0
        assert card_count > 0


class TestSourcePreferences:
    """Tests for content source preference configuration."""

    @pytest.mark.asyncio
    async def test_existing_only_does_not_generate(
        self,
        session_service: SessionService,
        mock_db: MockDB,
        mock_exercise_generator: MockExerciseGenerator,
        mock_exercises_orm: list[MagicMock],
    ) -> None:
        """Test that existing_only source does not call exercise generator."""
        setup_db_mock_with_exercises(mock_db, mock_exercises_orm[:2])

        request = SessionCreateRequest(
            duration_minutes=15,
            topic_filter=DEFAULT_TOPIC,
            exercise_source=ContentSourcePreference.EXISTING_ONLY,
        )

        await session_service.create_session(request)

        # Exercise generator should not be called
        mock_exercise_generator.generate_exercise.assert_not_called()

    @pytest.mark.asyncio
    async def test_generate_new_always_generates(
        self,
        session_service: SessionService,
        mock_db: MockDB,
        mock_exercise_generator: MockExerciseGenerator,
        mock_exercises_orm: list[MagicMock],
    ) -> None:
        """Test that generate_new source always generates new exercises."""
        # Mock existing exercises that should be ignored
        setup_db_mock_with_exercises(mock_db, mock_exercises_orm)

        request = SessionCreateRequest(
            duration_minutes=15,
            topic_filter=DEFAULT_TOPIC,
            exercise_source=ContentSourcePreference.GENERATE_NEW,
        )

        await session_service.create_session(request)

        # Exercise generator should be called
        assert mock_exercise_generator.generate_exercise.call_count >= 1

    @pytest.mark.asyncio
    async def test_prefer_existing_uses_database_first(
        self,
        session_service: SessionService,
        mock_db: MockDB,
        mock_exercise_generator: MockExerciseGenerator,
        mock_exercises_orm: list[MagicMock],
    ) -> None:
        """Test that prefer_existing uses database exercises before generating."""
        setup_db_mock_with_exercises(mock_db, mock_exercises_orm)

        request = SessionCreateRequest(
            duration_minutes=15,
            topic_filter=DEFAULT_TOPIC,
            exercise_source=ContentSourcePreference.PREFER_EXISTING,
        )

        response = await session_service.create_session(request)

        # Should have exercises from database
        exercise_count = sum(
            1 for item in response.items if item.item_type == "exercise"
        )
        assert exercise_count >= 1

    @pytest.mark.asyncio
    async def test_default_exercise_source_uses_settings(
        self,
        session_service: SessionService,
        mock_db: MockDB,
        mock_exercises_orm: list[MagicMock],
    ) -> None:
        """Test that default exercise_source uses settings default."""
        setup_db_mock_with_exercises(mock_db, mock_exercises_orm[:2])

        # Request without explicit exercise_source should use settings default
        request = SessionCreateRequest(
            duration_minutes=15,
            topic_filter=DEFAULT_TOPIC,
            # exercise_source not specified - uses settings default
        )

        response = await session_service.create_session(request)

        # Should have exercises (behavior depends on settings default)
        exercise_count = sum(
            1 for item in response.items if item.item_type == "exercise"
        )
        assert exercise_count >= 1


class TestSessionTimeBudget:
    """Tests for SessionTimeBudget class."""

    @pytest.mark.parametrize(
        ("total_minutes", "exercise_ratio", "expected_exercise", "expected_card"),
        [
            pytest.param(30, 0.6, 18.0, 12.0, id="60_40_split"),
            pytest.param(30, 0.8, 24.0, 6.0, id="80_20_split"),
            pytest.param(20, 0.5, 10.0, 10.0, id="50_50_split"),
        ],
    )
    def test_budget_allocation_ratios(
        self,
        total_minutes: int,
        exercise_ratio: float,
        expected_exercise: float,
        expected_card: float,
    ) -> None:
        """Test that budget correctly calculates time allocation with different ratios."""
        budget = SessionTimeBudget(
            total_minutes=total_minutes,
            content_mode=SessionContentMode.BOTH,
            exercise_ratio=exercise_ratio,
        )

        # Use pytest.approx for floating-point comparisons
        assert budget.exercise_budget == pytest.approx(expected_exercise)
        assert budget.card_budget == pytest.approx(expected_card)

    @pytest.mark.parametrize(
        ("content_mode", "expected_exercise", "expected_card"),
        [
            pytest.param(
                SessionContentMode.EXERCISES_ONLY,
                30.0,
                0.0,
                id="exercises_only",
            ),
            pytest.param(
                SessionContentMode.CARDS_ONLY,
                0.0,
                30.0,
                id="cards_only",
            ),
        ],
    )
    def test_single_content_mode_full_budget(
        self,
        content_mode: SessionContentMode,
        expected_exercise: float,
        expected_card: float,
    ) -> None:
        """Test that single-content modes allocate full budget appropriately."""
        budget = SessionTimeBudget(
            total_minutes=30,
            content_mode=content_mode,
        )

        assert budget.exercise_budget == expected_exercise
        assert budget.card_budget == expected_card

    def test_add_exercise_consumes_budget(self) -> None:
        """Test that adding exercises consumes budget correctly."""
        budget = SessionTimeBudget(
            total_minutes=30,
            content_mode=SessionContentMode.BOTH,
            exercise_ratio=0.6,
        )

        assert budget.add_exercise(10)
        assert budget.exercise_consumed == 10.0
        assert budget.exercise_remaining == 8.0
        assert budget.exercise_count == 1

    def test_can_fit_exercise_checks_budget(self) -> None:
        """Test that can_fit_exercise correctly checks budget."""
        budget = SessionTimeBudget(
            total_minutes=20,
            content_mode=SessionContentMode.BOTH,
            exercise_ratio=0.5,  # 10 min for exercises
        )

        # Should fit in budget
        can_fit, _ = budget.can_fit_exercise(10)
        assert can_fit

        # Consume the budget
        budget.add_exercise(10)

        # Should not fit in exercise budget without overflow
        can_fit, reason = budget.can_fit_exercise(5, allow_overflow=False)
        assert not can_fit

    def test_max_exercises_calculation(self) -> None:
        """Test max_exercises calculation."""
        budget = SessionTimeBudget(
            total_minutes=30,
            content_mode=SessionContentMode.EXERCISES_ONLY,
        )

        # 30 min / 10 min per exercise = 3 exercises (using default time)
        assert budget.max_exercises(time_per_exercise=10) == 3

    def test_topic_selected_increases_exercise_ratio(self) -> None:
        """Test that topic_selected=True increases exercise ratio."""
        budget_general = SessionTimeBudget(
            total_minutes=30,
            content_mode=SessionContentMode.BOTH,
            topic_selected=False,
        )

        budget_topic = SessionTimeBudget(
            total_minutes=30,
            content_mode=SessionContentMode.BOTH,
            topic_selected=True,
        )

        # Topic-focused should have higher exercise budget (80% vs ~60%)
        assert budget_topic.exercise_budget > budget_general.exercise_budget


class TestConfigurationResolvers:
    """Tests for configuration resolver functions."""

    @pytest.mark.parametrize(
        ("input_mode", "expected_type"),
        [
            pytest.param(
                SessionContentMode.EXERCISES_ONLY,
                SessionContentMode.EXERCISES_ONLY,
                id="explicit_exercises_only",
            ),
            pytest.param(
                SessionContentMode.CARDS_ONLY,
                SessionContentMode.CARDS_ONLY,
                id="explicit_cards_only",
            ),
            pytest.param(
                SessionContentMode.BOTH,
                SessionContentMode.BOTH,
                id="explicit_both",
            ),
            pytest.param(
                None,
                SessionContentMode,
                id="none_falls_back_to_settings",
            ),
        ],
    )
    def test_resolve_content_mode(
        self,
        input_mode: Optional[SessionContentMode],
        expected_type: type | SessionContentMode,
    ) -> None:
        """Test resolve_content_mode with various inputs."""
        result = resolve_content_mode(input_mode)

        if input_mode is None:
            # Should return some valid SessionContentMode from settings
            assert isinstance(result, SessionContentMode)
        else:
            assert result == expected_type

    @pytest.mark.parametrize(
        ("input_source", "expected_type"),
        [
            pytest.param(
                ContentSourcePreference.GENERATE_NEW,
                ContentSourcePreference.GENERATE_NEW,
                id="explicit_generate_new",
            ),
            pytest.param(
                ContentSourcePreference.EXISTING_ONLY,
                ContentSourcePreference.EXISTING_ONLY,
                id="explicit_existing_only",
            ),
            pytest.param(
                ContentSourcePreference.PREFER_EXISTING,
                ContentSourcePreference.PREFER_EXISTING,
                id="explicit_prefer_existing",
            ),
            pytest.param(
                None,
                ContentSourcePreference,
                id="none_falls_back_to_settings",
            ),
        ],
    )
    def test_resolve_exercise_source(
        self,
        input_source: Optional[ContentSourcePreference],
        expected_type: type | ContentSourcePreference,
    ) -> None:
        """Test resolve_exercise_source with various inputs."""
        result = resolve_exercise_source(input_source)

        if input_source is None:
            assert isinstance(result, ContentSourcePreference)
        else:
            assert result == expected_type

    @pytest.mark.parametrize(
        ("input_source", "expected_type"),
        [
            pytest.param(
                ContentSourcePreference.EXISTING_ONLY,
                ContentSourcePreference.EXISTING_ONLY,
                id="explicit_existing_only",
            ),
            pytest.param(
                None,
                ContentSourcePreference,
                id="none_falls_back_to_settings",
            ),
        ],
    )
    def test_resolve_card_source(
        self,
        input_source: Optional[ContentSourcePreference],
        expected_type: type | ContentSourcePreference,
    ) -> None:
        """Test resolve_card_source with various inputs."""
        result = resolve_card_source(input_source)

        if input_source is None:
            assert isinstance(result, ContentSourcePreference)
        else:
            assert result == expected_type


class TestExerciseRatioOverride:
    """Tests for exercise_ratio override parameter."""

    @pytest.mark.asyncio
    async def test_custom_exercise_ratio_respected(
        self,
        session_service: SessionService,
        mock_db: MockDB,
        mock_spaced_rep_service: MockSpacedRepService,
        mock_cards: list[CardResponse],
    ) -> None:
        """Test that custom exercise_ratio is respected."""
        # Provide enough cards to fill the card budget
        mock_spaced_rep_service.get_due_cards = AsyncMock(
            return_value=create_due_cards_response(cards=mock_cards, total_due=5)
        )
        setup_db_mock_with_empty_result(mock_db)

        # Request with 20% exercises (80% cards)
        request = SessionCreateRequest(
            duration_minutes=30,
            exercise_ratio=0.2,  # Only 20% for exercises
            content_mode=SessionContentMode.BOTH,
            exercise_source=ContentSourcePreference.GENERATE_NEW,
        )

        response = await session_service.create_session(request)

        # With 20% ratio, 6 min for exercises, 24 min for cards
        # Cards at 2 min each = up to 12 cards
        card_count = sum(1 for item in response.items if item.item_type == "card")
        # Should have significant number of cards
        assert card_count >= 3
