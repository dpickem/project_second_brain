"""
Unit tests for Learning System Pydantic models.

Tests the request/response models for validation and serialization.
"""

from datetime import datetime, timedelta

import pytest
from pydantic import ValidationError

from app.enums.learning import (
    CardState,
    Rating,
    ExerciseType,
    ExerciseDifficulty,
    MasteryTrend,
    SessionType,
)
from app.models.learning import (
    # Card models
    CardBase,
    CardCreate,
    CardResponse,
    CardReviewRequest,
    CardReviewResponse,
    ReviewForecast,
    DueCardsResponse,
    # Exercise models
    ExerciseBase,
    ExerciseCreate,
    ExerciseResponse,
    ExerciseWithSolution,
    ExerciseGenerateRequest,
    # Attempt models
    CodeExecutionResult,
    AttemptSubmitRequest,
    AttemptEvaluationResponse,
    AttemptConfidenceUpdate,
    # Session models
    SessionItem,
    SessionCreateRequest,
    SessionResponse,
    SessionSummary,
    # Mastery models
    MasteryState,
    WeakSpot,
    WeakSpotsResponse,
    MasteryOverview,
    LearningCurveDataPoint,
    LearningCurveResponse,
    CardStats,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def now():
    """Current timestamp for tests."""
    return datetime.utcnow()


@pytest.fixture
def card_response(now):
    """Basic CardResponse fixture."""
    return CardResponse(
        id=1,
        card_type="concept",
        front="Q",
        back="A",
        due_date=now,
    )


@pytest.fixture
def exercise_response():
    """Basic ExerciseResponse fixture."""
    return ExerciseResponse(
        id=1,
        exercise_uuid="abc-123",
        exercise_type=ExerciseType.FREE_RECALL,
        topic="test",
        prompt="Explain X",
    )


# =============================================================================
# Card Models
# =============================================================================


class TestCardModels:
    """Tests for spaced repetition card models."""

    def test_card_base_defaults(self):
        """Test CardBase with required fields only."""
        card = CardBase(card_type="concept", front="Q?", back="A")
        assert card.hints == []
        assert card.tags == []

    @pytest.mark.parametrize(
        "hints,tags",
        [
            (["Hint 1"], ["tag1"]),
            (["Hint 1", "Hint 2"], ["ml/transformers", "attention"]),
            ([], ["single-tag"]),
        ],
    )
    def test_card_base_optional_fields(self, hints, tags):
        """Test CardBase with various hints and tags."""
        card = CardBase(card_type="fact", front="Q", back="A", hints=hints, tags=tags)
        assert card.hints == hints
        assert card.tags == tags

    def test_card_create_code_card(self):
        """Test CardCreate for code cards with all fields."""
        card = CardCreate(
            card_type="code",
            front="Implement binary search",
            back="def binary_search(arr, x): ...",
            language="python",
            starter_code="def binary_search(arr, x):\n    pass",
            solution_code="def binary_search(arr, x):\n    ...",
            test_cases=[{"input": "[1,2,3,4,5], 3", "expected": "2"}],
            content_id=1,
            concept_id="algo/search/binary",
        )
        assert card.language == "python"
        assert card.starter_code is not None
        assert len(card.test_cases) == 1

    def test_card_response_fsrs_state(self, now):
        """Test CardResponse includes FSRS fields."""
        card = CardResponse(
            id=1,
            card_type="concept",
            front="Q",
            back="A",
            state=CardState.REVIEW,
            stability=15.5,
            difficulty=0.4,
            due_date=now + timedelta(days=7),
            last_reviewed=now,
            repetitions=5,
            lapses=1,
            total_reviews=10,
            correct_reviews=9,
        )
        assert card.state == CardState.REVIEW
        assert card.stability == 15.5
        assert card.difficulty == 0.4

    @pytest.mark.parametrize(
        "rating,time_spent",
        [
            (Rating.AGAIN, 10),
            (Rating.HARD, 20),
            (Rating.GOOD, 30),
            (Rating.EASY, 5),
        ],
    )
    def test_card_review_request_ratings(self, rating, time_spent):
        """Test CardReviewRequest with various ratings."""
        request = CardReviewRequest(
            card_id=1, rating=rating, time_spent_seconds=time_spent
        )
        assert request.rating == rating
        assert request.time_spent_seconds == time_spent

    @pytest.mark.parametrize("invalid_time", [-1, -100])
    def test_card_review_request_rejects_negative_time(self, invalid_time):
        """Test CardReviewRequest rejects negative time."""
        with pytest.raises(ValidationError):
            CardReviewRequest(card_id=1, rating=Rating.GOOD, time_spent_seconds=invalid_time)

    def test_card_review_response(self, now):
        """Test CardReviewResponse structure."""
        response = CardReviewResponse(
            card_id=1,
            new_state=CardState.REVIEW,
            new_stability=10.0,
            new_difficulty=0.3,
            next_due_date=now + timedelta(days=10),
            scheduled_days=10,
            was_correct=True,
        )
        assert response.scheduled_days == 10
        assert response.was_correct is True

    def test_review_forecast(self):
        """Test ReviewForecast structure."""
        forecast = ReviewForecast(overdue=5, today=10, tomorrow=8, this_week=20, later=100)
        assert (forecast.overdue, forecast.today) == (5, 10)

    def test_due_cards_response(self, card_response):
        """Test DueCardsResponse structure."""
        response = DueCardsResponse(
            cards=[card_response],
            total_due=50,
            review_forecast=ReviewForecast(),
        )
        assert len(response.cards) == 1
        assert response.total_due == 50


# =============================================================================
# Exercise Models
# =============================================================================


class TestExerciseModels:
    """Tests for exercise models."""

    def test_exercise_base_defaults(self):
        """Test ExerciseBase default difficulty."""
        exercise = ExerciseBase(
            exercise_type=ExerciseType.FREE_RECALL,
            topic="ml/transformers",
            prompt="Explain attention.",
        )
        assert exercise.difficulty == ExerciseDifficulty.INTERMEDIATE

    @pytest.mark.parametrize(
        "exercise_type,extra_fields",
        [
            (
                ExerciseType.WORKED_EXAMPLE,
                {
                    "worked_example": "Step 1: Forward pass...",
                    "follow_up_problem": "Now compute gradients",
                },
            ),
            (
                ExerciseType.CODE_IMPLEMENT,
                {
                    "language": "python",
                    "starter_code": "def solution():\n    pass",
                    "solution_code": "def solution():\n    return 42",
                    "test_cases": [{"input": "[]", "expected": "42"}],
                },
            ),
        ],
    )
    def test_exercise_create_types(self, exercise_type, extra_fields):
        """Test ExerciseCreate for different exercise types."""
        exercise = ExerciseCreate(
            exercise_type=exercise_type,
            topic="test",
            prompt="Do the thing",
            **extra_fields,
        )
        assert exercise.exercise_type == exercise_type
        for key, value in extra_fields.items():
            assert getattr(exercise, key) == value

    def test_exercise_with_solution_includes_solution(self):
        """Test ExerciseWithSolution includes solution fields."""
        exercise = ExerciseWithSolution(
            id=1,
            exercise_uuid="abc-123",
            exercise_type=ExerciseType.CODE_IMPLEMENT,
            topic="test",
            prompt="Implement X",
            solution_code="def solution():\n    return 42",
            test_cases=[{"input": "", "expected": "42"}],
        )
        assert exercise.solution_code is not None

    def test_exercise_generate_request(self):
        """Test ExerciseGenerateRequest."""
        request = ExerciseGenerateRequest(
            topic="ml/neural-networks",
            exercise_type=ExerciseType.APPLICATION,
            difficulty=ExerciseDifficulty.ADVANCED,
            language="python",
        )
        assert request.topic == "ml/neural-networks"
        assert request.exercise_type == ExerciseType.APPLICATION


# =============================================================================
# Attempt Models
# =============================================================================


class TestAttemptModels:
    """Tests for exercise attempt models."""

    @pytest.mark.parametrize(
        "passed,error",
        [
            (True, None),
            (False, "Assertion failed"),
            (False, "Timeout"),
        ],
    )
    def test_test_result(self, passed, error):
        """Test CodeExecutionResult for passed/failed cases."""
        result = CodeExecutionResult(
            test_index=0,
            passed=passed,
            input_value="[1,2,3]",
            expected="6",
            actual="6" if passed else "5",
            error=error,
        )
        assert result.passed == passed
        assert result.error == error

    @pytest.mark.parametrize(
        "response,response_code",
        [
            ("My explanation...", None),
            (None, "def solution():\n    return 42"),
        ],
    )
    def test_attempt_submit_request_types(self, response, response_code):
        """Test AttemptSubmitRequest with text or code response."""
        request = AttemptSubmitRequest(
            exercise_id=1,
            response=response,
            response_code=response_code,
            time_spent_seconds=120,
        )
        assert request.response == response
        assert request.response_code == response_code

    @pytest.mark.parametrize("invalid_confidence", [0, 6, -1, 10])
    def test_attempt_confidence_bounds(self, invalid_confidence):
        """Test confidence must be 1-5."""
        with pytest.raises(ValidationError):
            AttemptSubmitRequest(exercise_id=1, confidence_before=invalid_confidence)

    @pytest.mark.parametrize("valid_confidence", [1, 2, 3, 4, 5])
    def test_attempt_confidence_valid(self, valid_confidence):
        """Test valid confidence values."""
        request = AttemptSubmitRequest(exercise_id=1, confidence_before=valid_confidence)
        assert request.confidence_before == valid_confidence

    def test_attempt_evaluation_response_text(self):
        """Test AttemptEvaluationResponse for text exercise."""
        response = AttemptEvaluationResponse(
            attempt_id=1,
            attempt_uuid="abc-123",
            score=0.85,
            is_correct=True,
            feedback="Great explanation!",
            covered_points=["point1", "point2"],
            missing_points=["point3"],
            misconceptions=[],
        )
        assert response.score == 0.85
        assert response.is_correct is True
        assert len(response.covered_points) == 2

    def test_attempt_evaluation_response_code(self):
        """Test AttemptEvaluationResponse for code exercise."""
        response = AttemptEvaluationResponse(
            attempt_id=1,
            attempt_uuid="abc-123",
            score=0.75,
            is_correct=False,
            feedback="3 of 4 tests passed.",
            tests_passed=3,
            tests_total=4,
            test_results=[
                CodeExecutionResult(test_index=i, passed=(i < 3), error="Timeout" if i == 3 else None)
                for i in range(4)
            ],
        )
        assert response.tests_passed == 3
        assert len(response.test_results) == 4

    @pytest.mark.parametrize("confidence", [1, 3, 5])
    def test_attempt_confidence_update(self, confidence):
        """Test AttemptConfidenceUpdate."""
        update = AttemptConfidenceUpdate(confidence_after=confidence)
        assert update.confidence_after == confidence


# =============================================================================
# Session Models
# =============================================================================


class TestSessionModels:
    """Tests for practice session models."""

    def test_session_item_card(self, card_response):
        """Test SessionItem with card."""
        item = SessionItem(item_type="card", card=card_response, estimated_minutes=2.0)
        assert item.item_type == "card"
        assert item.card is not None
        assert item.exercise is None

    def test_session_item_exercise(self, exercise_response):
        """Test SessionItem with exercise."""
        item = SessionItem(
            item_type="exercise", exercise=exercise_response, estimated_minutes=7.0
        )
        assert item.item_type == "exercise"
        assert item.exercise is not None

    @pytest.mark.parametrize(
        "duration,topic,session_type",
        [
            (15, None, SessionType.PRACTICE),
            (30, "ml/transformers", SessionType.PRACTICE),
            (60, "algorithms", SessionType.REVIEW),
        ],
    )
    def test_session_create_request(self, duration, topic, session_type):
        """Test SessionCreateRequest variations."""
        request = SessionCreateRequest(
            duration_minutes=duration,
            topic_filter=topic,
            session_type=session_type,
        )
        assert request.duration_minutes == duration
        assert request.topic_filter == topic
        assert request.session_type == session_type

    @pytest.mark.parametrize("invalid_duration", [4, 121, 0, -10])
    def test_session_create_request_duration_bounds(self, invalid_duration):
        """Test duration must be 5-120 minutes."""
        with pytest.raises(ValidationError):
            SessionCreateRequest(duration_minutes=invalid_duration)

    def test_session_response(self):
        """Test SessionResponse."""
        response = SessionResponse(
            session_id=1,
            items=[],
            estimated_duration_minutes=15.0,
            topics_covered=["ml/transformers"],
            session_type=SessionType.PRACTICE,
        )
        assert response.session_id == 1

    def test_session_summary(self):
        """Test SessionSummary."""
        summary = SessionSummary(
            session_id=1,
            duration_minutes=25.5,
            cards_reviewed=10,
            exercises_completed=2,
            correct_count=9,
            total_count=12,
            average_score=0.82,
            mastery_changes={"ml/transformers": 0.05},
        )
        assert summary.cards_reviewed == 10
        assert summary.average_score == 0.82


# =============================================================================
# Mastery Models
# =============================================================================


class TestMasteryModels:
    """Tests for mastery tracking models."""

    @pytest.mark.parametrize(
        "score,trend",
        [
            (0.75, MasteryTrend.IMPROVING),
            (0.5, MasteryTrend.STABLE),
            (0.25, MasteryTrend.DECLINING),
        ],
    )
    def test_mastery_state(self, score, trend):
        """Test MasteryState with various scores and trends."""
        state = MasteryState(
            topic_path="ml/transformers",
            mastery_score=score,
            practice_count=20,
            success_rate=0.85,
            trend=trend,
            days_since_review=3,
        )
        assert state.mastery_score == score
        assert state.trend == trend

    @pytest.mark.parametrize("invalid_score", [-0.1, 1.1, 1.5, -1])
    def test_mastery_score_bounds(self, invalid_score):
        """Test mastery score must be 0-1."""
        with pytest.raises(ValidationError):
            MasteryState(topic_path="test", mastery_score=invalid_score)

    def test_weak_spot(self):
        """Test WeakSpot."""
        spot = WeakSpot(
            topic="ml/backprop",
            mastery_score=0.35,
            success_rate=0.45,
            trend=MasteryTrend.DECLINING,
            recommendation="Practice more backpropagation exercises",
            suggested_exercise_types=[ExerciseType.WORKED_EXAMPLE, ExerciseType.FREE_RECALL],
        )
        assert spot.mastery_score == 0.35
        assert len(spot.suggested_exercise_types) == 2

    def test_weak_spots_response(self):
        """Test WeakSpotsResponse."""
        response = WeakSpotsResponse(
            weak_spots=[
                WeakSpot(
                    topic="test",
                    mastery_score=0.4,
                    trend=MasteryTrend.DECLINING,
                    recommendation="Practice more",
                )
            ],
            total_topics=10,
            weak_spot_threshold=0.6,
        )
        assert len(response.weak_spots) == 1

    def test_mastery_overview(self):
        """Test MasteryOverview."""
        overview = MasteryOverview(
            overall_mastery=0.72,
            topics=[],
            total_cards=100,
            cards_mastered=50,
            cards_learning=30,
            cards_new=20,
            streak_days=5,
        )
        assert overview.overall_mastery == 0.72
        assert overview.total_cards == 100

    def test_learning_curve_data_point(self, now):
        """Test LearningCurveDataPoint."""
        point = LearningCurveDataPoint(
            date=now,
            mastery_score=0.65,
            retention_estimate=0.85,
            cards_reviewed=15,
        )
        assert point.mastery_score == 0.65

    def test_learning_curve_response(self):
        """Test LearningCurveResponse."""
        response = LearningCurveResponse(
            topic="ml/transformers",
            data_points=[],
            trend=MasteryTrend.IMPROVING,
            projected_mastery_30d=0.85,
        )
        assert response.trend == MasteryTrend.IMPROVING

    def test_card_stats(self):
        """Test CardStats."""
        stats = CardStats(
            total_cards=200,
            cards_by_state={"new": 50, "learning": 30, "review": 120},
            avg_stability=12.5,
            avg_difficulty=0.35,
            due_today=15,
            overdue=5,
        )
        assert stats.total_cards == 200
        assert stats.due_today == 15
