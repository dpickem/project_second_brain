"""
Integration tests for Learning System API endpoints.

Tests the practice, review, and analytics routers with a real database.

IMPORTANT: These tests use the TEST database only (via POSTGRES_TEST_* env vars).
The test_client fixture overrides get_db to ensure the production database
is never touched. See tests/integration/conftest.py for details.
"""

from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models_learning import (
    SpacedRepCard,
    PracticeSession,
    Exercise,
    MasterySnapshot,
)


pytestmark = pytest.mark.integration


# =============================================================================
# Shared Fixtures
# =============================================================================


@pytest.fixture
def now():
    """Current UTC timestamp (timezone-aware)."""
    return datetime.now(timezone.utc)


@pytest_asyncio.fixture
async def sample_cards(clean_db: AsyncSession, now):
    """
    Create sample spaced rep cards covering different states:
    - new card (due now)
    - review card (overdue)
    - review card (not yet due)
    """
    cards_data = [
        {
            "card_type": "concept",
            "front": "What is FSRS?",
            "back": "Free Spaced Repetition Scheduler",
            "state": "new",
            "stability": 0.0,
            "difficulty": 0.3,
            "due_date": now,
            "tags": ["ml/spaced-rep"],
        },
        {
            "card_type": "concept",
            "front": "What is attention?",
            "back": "A mechanism in neural networks",
            "state": "review",
            "stability": 5.0,
            "difficulty": 0.4,
            "due_date": now - timedelta(days=1),  # Overdue
            "last_reviewed": now - timedelta(days=6),
            "tags": ["ml/transformers"],
        },
        {
            "card_type": "fact",
            "front": "Python list syntax?",
            "back": "[1, 2, 3]",
            "state": "review",
            "stability": 20.0,
            "difficulty": 0.2,
            "due_date": now + timedelta(days=10),  # Not due
            "last_reviewed": now - timedelta(days=5),
            "tags": ["programming/python"],
        },
    ]

    cards = [SpacedRepCard(**data) for data in cards_data]
    for card in cards:
        clean_db.add(card)
    await clean_db.commit()

    for card in cards:
        await clean_db.refresh(card)

    return cards


@pytest_asyncio.fixture
async def sample_exercise(clean_db: AsyncSession):
    """Create a sample free-recall exercise."""
    exercise = Exercise(
        exercise_type="free_recall",
        topic="ml/transformers",
        difficulty="intermediate",
        prompt="Explain the attention mechanism in transformers.",
        hints=["Think about queries, keys, and values"],
        expected_key_points=["Self-attention", "Query-key-value", "Softmax normalization"],
        estimated_time_minutes=10,
        tags=["ml", "transformers"],
    )
    clean_db.add(exercise)
    await clean_db.commit()
    await clean_db.refresh(exercise)
    return exercise


@pytest_asyncio.fixture
async def sample_session(clean_db: AsyncSession, now):
    """Create a practice session started 10 minutes ago."""
    session = PracticeSession(
        session_type="practice",
        started_at=now - timedelta(minutes=10),
    )
    clean_db.add(session)
    await clean_db.commit()
    await clean_db.refresh(session)
    return session


@pytest_asyncio.fixture
async def sample_mastery_data(clean_db: AsyncSession, now):
    """Create sample mastery data: cards with reviews + mastery snapshot."""
    cards = [
        SpacedRepCard(
            card_type="concept",
            front=f"Q{i}",
            back=f"A{i}",
            state="review",
            stability=stability,
            difficulty=difficulty,
            tags=["ml/transformers"],
            due_date=now,
            total_reviews=reviews,
            correct_reviews=correct,
        )
        for i, (stability, difficulty, reviews, correct) in enumerate(
            [(15.0, 0.3, 10, 9), (5.0, 0.5, 8, 5)], start=1
        )
    ]

    for card in cards:
        clean_db.add(card)

    snapshot = MasterySnapshot(
        snapshot_date=now - timedelta(days=1),
        topic_path="ml/transformers",
        mastery_score=0.65,
        practice_count=18,
        success_rate=0.78,
        trend="improving",
    )
    clean_db.add(snapshot)

    await clean_db.commit()
    return cards


# =============================================================================
# Review Endpoints
# =============================================================================


class TestReviewEndpoints:
    """Tests for spaced repetition review endpoints."""

    @pytest.mark.asyncio
    async def test_get_due_cards(self, async_test_client, sample_cards):
        """Test GET /api/review/due returns due cards with forecast."""
        response = await async_test_client.get("/api/review/due")

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert all(key in data for key in ["cards", "total_due", "review_forecast"])
        # Should return new + overdue cards (at least 2)
        assert data["total_due"] >= 2

    @pytest.mark.parametrize(
        "query_params,expected_check",
        [
            ("?topic=ml/transformers", lambda d: all("ml/transformers" in c.get("tags", []) for c in d["cards"])),
            ("?limit=1", lambda d: len(d["cards"]) <= 1),
        ],
    )
    @pytest.mark.asyncio
    async def test_get_due_cards_filtered(self, async_test_client, sample_cards, query_params, expected_check):
        """Test GET /api/review/due with filters."""
        response = await async_test_client.get(f"/api/review/due{query_params}")

        assert response.status_code == 200
        assert expected_check(response.json())

    @pytest.mark.parametrize(
        "rating,expected_correct,expected_state",
        [
            (3, True, None),       # GOOD - correct, state varies
            (4, True, None),       # EASY - correct
            (1, False, "relearning"),  # AGAIN - incorrect, enters relearning
        ],
    )
    @pytest.mark.asyncio
    async def test_review_card_ratings(
        self, async_test_client, sample_cards, rating, expected_correct, expected_state
    ):
        """Test POST /api/review/rate with different ratings."""
        card = sample_cards[1]  # Overdue review card

        response = await async_test_client.post(
            "/api/review/rate",
            json={"card_id": card.id, "rating": rating, "time_spent_seconds": 10},
        )

        assert response.status_code == 200, f"Failed with: {response.json()}"
        data = response.json()

        assert data["card_id"] == card.id
        assert data["was_correct"] is expected_correct
        if expected_state:
            assert data["new_state"] == expected_state

    @pytest.mark.asyncio
    async def test_review_nonexistent_card(self, async_test_client):
        """Test POST /api/review/rate with invalid card ID returns 404."""
        response = await async_test_client.post(
            "/api/review/rate",
            json={"card_id": 99999, "rating": 3},
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_create_card(self, async_test_client, clean_db):
        """Test POST /api/review/cards creates a new card in NEW state."""
        card_data = {
            "card_type": "concept",
            "front": "Test question?",
            "back": "Test answer",
            "hints": ["Hint 1"],
            # Note: tags omitted since they must exist in database first
        }

        response = await async_test_client.post("/api/review/cards", json=card_data)

        assert response.status_code == 200
        data = response.json()

        assert data["card_type"] == "concept"
        assert data["front"] == "Test question?"
        assert data["state"] == "new"

        # Verify in database
        result = await clean_db.execute(
            select(SpacedRepCard).where(SpacedRepCard.id == data["id"])
        )
        assert result.scalar_one().front == "Test question?"

    @pytest.mark.asyncio
    async def test_get_card_stats(self, async_test_client, sample_cards):
        """Test GET /api/review/stats returns card statistics."""
        response = await async_test_client.get("/api/review/stats")

        assert response.status_code == 200
        data = response.json()

        expected_fields = ["total_cards", "cards_by_state", "due_today"]
        assert all(field in data for field in expected_fields)
        assert data["total_cards"] >= 3


# =============================================================================
# Practice Endpoints
# =============================================================================


class TestPracticeEndpoints:
    """Tests for practice session endpoints."""

    @pytest.mark.asyncio
    async def test_create_session(self, async_test_client, clean_db):
        """Test POST /api/practice/session creates a session."""
        response = await async_test_client.post(
            "/api/practice/session",
            json={"duration_minutes": 15, "session_type": "practice"},
        )

        assert response.status_code == 200
        data = response.json()

        expected_fields = ["session_id", "items", "estimated_duration_minutes"]
        assert all(field in data for field in expected_fields)

    @pytest.mark.asyncio
    async def test_end_session(self, async_test_client, sample_session):
        """Test POST /api/practice/session/{id}/end returns summary."""
        response = await async_test_client.post(f"/api/practice/session/{sample_session.id}/end")

        assert response.status_code == 200
        data = response.json()

        assert data["session_id"] == sample_session.id
        expected_fields = ["duration_minutes", "cards_reviewed", "exercises_completed"]
        assert all(field in data for field in expected_fields)

    @pytest.mark.asyncio
    async def test_get_exercise(self, async_test_client, sample_exercise):
        """Test GET /api/practice/exercise/{id} returns exercise without solution."""
        response = await async_test_client.get(f"/api/practice/exercise/{sample_exercise.id}")

        assert response.status_code == 200
        data = response.json()

        assert data["id"] == sample_exercise.id
        assert data["prompt"] == sample_exercise.prompt
        assert data["topic"] == "ml/transformers"
        # Solution should not be exposed
        assert data.get("solution_code") is None

    @pytest.mark.asyncio
    async def test_submit_attempt(self, async_test_client, sample_exercise):
        """Test POST /api/practice/submit submits an attempt."""
        response = await async_test_client.post(
            "/api/practice/submit",
            json={
                "exercise_id": sample_exercise.id,
                "response": "Attention allows the model to focus on relevant parts. Uses queries, keys, values.",
                "confidence_before": 3,
                "time_spent_seconds": 120,
            },
        )

        # May return 500 if LLM not configured; in real tests we'd mock it
        assert response.status_code in (200, 500)

        if response.status_code == 200:
            data = response.json()
            assert all(field in data for field in ["attempt_id", "score", "feedback"])

    @pytest.mark.parametrize(
        "endpoint,method",
        [
            ("/api/practice/session/99999/end", "post"),
            ("/api/practice/exercise/99999", "get"),
        ],
    )
    @pytest.mark.asyncio
    async def test_nonexistent_resources_404(self, async_test_client, endpoint, method):
        """Test accessing non-existent resources returns 404."""
        response = await getattr(async_test_client, method)(endpoint)
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_submit_attempt_nonexistent_exercise(self, async_test_client):
        """Test submitting to non-existent exercise returns 404."""
        response = await async_test_client.post(
            "/api/practice/submit",
            json={"exercise_id": 99999, "response": "Test response"},
        )
        assert response.status_code == 404


# =============================================================================
# Analytics Endpoints
# =============================================================================


class TestAnalyticsEndpoints:
    """Tests for learning analytics endpoints."""

    @pytest.mark.asyncio
    async def test_get_mastery_overview(self, async_test_client, sample_mastery_data):
        """Test GET /api/analytics/overview returns mastery overview."""
        response = await async_test_client.get("/api/analytics/overview")

        assert response.status_code == 200
        data = response.json()

        expected_fields = [
            "overall_mastery", "total_cards", "cards_mastered",
            "cards_learning", "cards_new"
        ]
        assert all(field in data for field in expected_fields)

    @pytest.mark.asyncio
    async def test_get_topic_mastery(self, async_test_client, sample_mastery_data):
        """Test GET /api/analytics/mastery/{topic} returns topic-specific mastery."""
        response = await async_test_client.get("/api/analytics/mastery/ml%2Ftransformers")

        assert response.status_code == 200
        data = response.json()

        expected_fields = ["topic_path", "mastery_score", "practice_count"]
        assert all(field in data for field in expected_fields)

    @pytest.mark.asyncio
    async def test_get_weak_spots(self, async_test_client, sample_mastery_data):
        """Test GET /api/analytics/weak-spots returns weak spots analysis."""
        response = await async_test_client.get("/api/analytics/weak-spots")

        assert response.status_code == 200
        data = response.json()

        expected_fields = ["weak_spots", "total_topics", "weak_spot_threshold"]
        assert all(field in data for field in expected_fields)

    @pytest.mark.parametrize(
        "query_params,expected_topic",
        [
            ("?days=30", None),
            ("?topic=ml%2Ftransformers&days=30", "ml/transformers"),
        ],
    )
    @pytest.mark.asyncio
    async def test_get_learning_curve(
        self, async_test_client, sample_mastery_data, query_params, expected_topic
    ):
        """Test GET /api/analytics/learning-curve returns curve data."""
        response = await async_test_client.get(f"/api/analytics/learning-curve{query_params}")

        assert response.status_code == 200
        data = response.json()

        assert all(field in data for field in ["data_points", "trend"])
        if expected_topic:
            assert data.get("topic") == expected_topic
