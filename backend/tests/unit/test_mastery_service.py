"""
Unit tests for MasteryService.

Tests the mastery tracking and analytics service including:
- Mastery score calculation
- Weak spot detection
- Daily snapshots
- Learning curve data
"""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pandas as pd
import pytest

from app.config import settings
from app.enums.learning import MasteryTrend, ExerciseType, CardState
from app.models.learning import MasteryState
from app.services.learning.mastery_service import (
    MasteryService,
    _calculate_trend,
)


# ============================================================================
# Shared Fixtures
# ============================================================================


@pytest.fixture
def mock_db():
    """Create a mock database session."""
    mock = MagicMock()
    mock.execute = AsyncMock()
    mock.add = MagicMock()
    mock.commit = AsyncMock()
    return mock


@pytest.fixture
def service(mock_db):
    """Create a MasteryService instance with mock db."""
    return MasteryService(mock_db)


@pytest.fixture
def sample_cards_df():
    """Create a sample cards DataFrame for testing."""
    return pd.DataFrame([
        {
            "id": 1,
            "tags": ["ml", "python"],
            "state": CardState.REVIEW,
            "stability": 15.0,
            "total_reviews": 10,
            "correct_reviews": 8,
            "last_reviewed": datetime.utcnow() - timedelta(days=3),
        },
        {
            "id": 2,
            "tags": ["ml"],
            "state": CardState.REVIEW,
            "stability": 20.0,
            "total_reviews": 15,
            "correct_reviews": 14,
            "last_reviewed": datetime.utcnow() - timedelta(days=1),
        },
        {
            "id": 3,
            "tags": ["python"],
            "state": CardState.LEARNING,
            "stability": 1.0,
            "total_reviews": 2,
            "correct_reviews": 2,
            "last_reviewed": datetime.utcnow(),
        },
    ])


# ============================================================================
# Test _calculate_trend helper function
# ============================================================================


class TestCalculateTrend:
    """Tests for the _calculate_trend helper function."""

    @pytest.mark.parametrize(
        "current,previous,expected",
        [
            (0.8, 0.5, MasteryTrend.IMPROVING),  # Large increase
            (0.3, 0.7, MasteryTrend.DECLINING),  # Large decrease
            (0.52, 0.50, MasteryTrend.STABLE),   # Small increase
            (0.48, 0.50, MasteryTrend.STABLE),   # Small decrease
            (0.5, 0.5, MasteryTrend.STABLE),     # No change
        ],
        ids=["improving", "declining", "small_increase", "small_decrease", "no_change"],
    )
    def test_trend_calculation(self, current, previous, expected):
        """Test trend is calculated correctly for various score deltas."""
        assert _calculate_trend(current, previous) == expected

    def test_threshold_boundary(self):
        """Test behavior at threshold boundary."""
        threshold = settings.MASTERY_TREND_THRESHOLD
        # Just above threshold = IMPROVING
        assert _calculate_trend(0.5 + threshold + 0.001, 0.5) == MasteryTrend.IMPROVING
        # Just below threshold = STABLE
        assert _calculate_trend(0.5 + threshold - 0.001, 0.5) == MasteryTrend.STABLE


# ============================================================================
# Test MasteryService Initialization
# ============================================================================


class TestMasteryServiceInitialization:
    """Tests for MasteryService initialization."""

    def test_initialization(self, mock_db):
        """Test service initializes with database session."""
        service = MasteryService(mock_db)
        assert service.db == mock_db


# ============================================================================
# Test get_mastery_state
# ============================================================================


class TestGetMasteryState:
    """Tests for get_mastery_state method."""

    @pytest.mark.asyncio
    async def test_returns_cached_snapshot_if_recent(self, service):
        """Test that recent snapshot is returned instead of recalculating."""
        mock_snapshot = MagicMock(
            topic_path="ml/transformers",
            mastery_score=0.75,
            practice_count=10,
            success_rate=0.8,
            trend="stable",
            last_practiced=datetime.utcnow(),
            retention_estimate=0.9,
            days_since_review=2,
        )

        with patch.object(service, "_get_recent_snapshot", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_snapshot
            result = await service.get_mastery_state("ml/transformers")

            assert result.topic_path == "ml/transformers"
            assert result.mastery_score == 0.75
            mock_get.assert_called_once_with("ml/transformers")

    @pytest.mark.asyncio
    async def test_calculates_fresh_when_no_snapshot(self, service):
        """Test that mastery is calculated when no snapshot exists."""
        expected_state = MasteryState(
            topic_path="ml/transformers", mastery_score=0.6, practice_count=5
        )

        with patch.object(service, "_get_recent_snapshot", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = None
            with patch.object(service, "_calculate_mastery", new_callable=AsyncMock) as mock_calc:
                mock_calc.return_value = expected_state
                result = await service.get_mastery_state("ml/transformers")

                assert result == expected_state
                mock_calc.assert_called_once_with("ml/transformers")


# ============================================================================
# Test get_weak_spots
# ============================================================================


class TestGetWeakSpots:
    """Tests for get_weak_spots method."""

    @pytest.fixture
    def weak_spot_states(self):
        """Create test states with weak and strong topics."""
        return [
            MasteryState(
                topic_path="weak/topic1", mastery_score=0.3,
                practice_count=10, trend=MasteryTrend.DECLINING,
            ),
            MasteryState(
                topic_path="strong/topic", mastery_score=0.9,
                practice_count=20, trend=MasteryTrend.STABLE,
            ),
            MasteryState(
                topic_path="new/topic", mastery_score=0.2,
                practice_count=1, trend=MasteryTrend.STABLE,  # Below min attempts
            ),
            MasteryState(
                topic_path="weak/topic2", mastery_score=0.4,
                practice_count=15, trend=MasteryTrend.STABLE,
            ),
        ]

    @pytest.mark.asyncio
    async def test_filters_by_threshold_and_attempts(self, service, weak_spot_states):
        """Test weak spots are filtered by threshold and min attempts."""
        with patch.object(service, "_get_all_topics", new_callable=AsyncMock) as mock_topics:
            mock_topics.return_value = [s.topic_path for s in weak_spot_states]
            with patch.object(service, "_calculate_mastery_batch", new_callable=AsyncMock) as mock_batch:
                mock_batch.return_value = weak_spot_states

                result = await service.get_weak_spots(limit=10)

                topics = [ws.topic for ws in result]
                assert len(result) == 2
                assert "weak/topic1" in topics
                assert "weak/topic2" in topics
                assert "strong/topic" not in topics
                assert "new/topic" not in topics

    @pytest.mark.asyncio
    async def test_sorts_declining_first(self, service):
        """Test that declining trends are sorted first."""
        test_states = [
            MasteryState(
                topic_path="stable/weak", mastery_score=0.3,
                practice_count=10, trend=MasteryTrend.STABLE,
            ),
            MasteryState(
                topic_path="declining/weak", mastery_score=0.35,
                practice_count=10, trend=MasteryTrend.DECLINING,
            ),
        ]

        with patch.object(service, "_get_all_topics", new_callable=AsyncMock) as mock_topics:
            mock_topics.return_value = [s.topic_path for s in test_states]
            with patch.object(service, "_calculate_mastery_batch", new_callable=AsyncMock) as mock_batch:
                mock_batch.return_value = test_states
                result = await service.get_weak_spots(limit=10)

                assert result[0].topic == "declining/weak"
                assert result[1].topic == "stable/weak"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("limit", [1, 5, 10])
    async def test_respects_limit(self, service, limit):
        """Test that limit parameter is respected."""
        test_states = [
            MasteryState(
                topic_path=f"weak/topic{i}", mastery_score=0.3,
                practice_count=10, trend=MasteryTrend.STABLE,
            )
            for i in range(20)
        ]

        with patch.object(service, "_get_all_topics", new_callable=AsyncMock) as mock_topics:
            mock_topics.return_value = [s.topic_path for s in test_states]
            with patch.object(service, "_calculate_mastery_batch", new_callable=AsyncMock) as mock_batch:
                mock_batch.return_value = test_states
                result = await service.get_weak_spots(limit=limit)

                assert len(result) == limit


# ============================================================================
# Test get_overview
# ============================================================================


class TestGetOverview:
    """Tests for get_overview method."""

    @pytest.fixture
    def mock_db_with_counts(self):
        """Create mock db that returns card counts."""
        mock = MagicMock()
        counts = iter([100, 30, 50, 20])  # total, mastered, learning, new

        def execute_side_effect(query):
            result = MagicMock()
            result.scalar.return_value = next(counts, 0)
            return result

        mock.execute = AsyncMock(side_effect=execute_side_effect)
        return mock

    @pytest.mark.asyncio
    async def test_aggregates_card_counts(self, mock_db_with_counts):
        """Test that card counts are aggregated correctly."""
        service = MasteryService(mock_db_with_counts)

        with patch.object(service, "_get_all_topics", new_callable=AsyncMock) as mock_topics:
            mock_topics.return_value = ["topic1", "topic2"]
            with patch.object(service, "_calculate_mastery_batch", new_callable=AsyncMock) as mock_batch:
                mock_batch.return_value = [
                    MasteryState(topic_path="topic1", mastery_score=0.7, practice_count=10),
                    MasteryState(topic_path="topic2", mastery_score=0.5, practice_count=5),
                ]
                with patch.object(service, "_calculate_streak", new_callable=AsyncMock) as mock_streak:
                    mock_streak.return_value = 5
                    result = await service.get_overview()

                    assert result.total_cards == 100
                    assert result.cards_mastered == 30
                    assert result.cards_learning == 50
                    assert result.cards_new == 20
                    assert result.streak_days == 5

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "scores,expected_avg",
        [
            ([0.8, 0.6], 0.7),
            ([0.5, 0.5], 0.5),
            ([1.0, 0.0], 0.5),
            ([0.9, 0.8, 0.7], 0.8),
        ],
        ids=["basic", "same", "extremes", "three_topics"],
    )
    async def test_calculates_overall_mastery(self, mock_db_with_counts, scores, expected_avg):
        """Test overall mastery is average of topic scores."""
        service = MasteryService(mock_db_with_counts)
        topics = [f"topic{i}" for i in range(len(scores))]
        states = [
            MasteryState(topic_path=t, mastery_score=s, practice_count=10)
            for t, s in zip(topics, scores)
        ]

        with patch.object(service, "_get_all_topics", new_callable=AsyncMock) as mock_topics:
            mock_topics.return_value = topics
            with patch.object(service, "_calculate_mastery_batch", new_callable=AsyncMock) as mock_batch:
                mock_batch.return_value = states
                with patch.object(service, "_calculate_streak", new_callable=AsyncMock) as mock_streak:
                    mock_streak.return_value = 0
                    result = await service.get_overview()

                    assert abs(result.overall_mastery - expected_avg) < 0.01


# ============================================================================
# Test _fetch_cards_dataframe
# ============================================================================


class TestFetchCardsDataframe:
    """Tests for _fetch_cards_dataframe method."""

    @pytest.mark.asyncio
    async def test_returns_empty_dataframe_when_no_cards(self, mock_db, service):
        """Test empty DataFrame is returned when no cards exist."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await service._fetch_cards_dataframe()

        assert isinstance(result, pd.DataFrame)
        assert result.empty
        assert all(col in result.columns for col in ["id", "tags", "state"])

    @pytest.mark.asyncio
    async def test_converts_cards_to_dataframe(self, mock_db, service):
        """Test cards are converted to DataFrame correctly."""
        mock_cards = [
            MagicMock(id=1, tags=["ml"], state=CardState.REVIEW, stability=10.0,
                      total_reviews=5, correct_reviews=4, last_reviewed=datetime.utcnow()),
            MagicMock(id=2, tags=["python"], state=CardState.LEARNING, stability=2.0,
                      total_reviews=2, correct_reviews=2, last_reviewed=datetime.utcnow()),
        ]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_cards
        mock_db.execute = AsyncMock(return_value=mock_result)

        result = await service._fetch_cards_dataframe()

        assert len(result) == 2
        assert result.iloc[0]["id"] == 1
        assert result.iloc[1]["id"] == 2


# ============================================================================
# Test _compute_mastery_dataframe
# ============================================================================


class TestComputeMasteryDataframe:
    """Tests for _compute_mastery_dataframe method."""

    def test_groups_by_topic(self, service, sample_cards_df):
        """Test that cards are grouped by topic."""
        result = service._compute_mastery_dataframe(sample_cards_df, ["ml", "python"])
        assert "ml" in result.index
        assert "python" in result.index

    @pytest.mark.parametrize(
        "topic,expected_reviews,expected_correct",
        [
            ("ml", 25, 22),      # Cards 1 + 2: 10+15=25 reviews, 8+14=22 correct
            ("python", 12, 10),  # Cards 1 + 3: 10+2=12 reviews, 8+2=10 correct
        ],
    )
    def test_aggregates_reviews(self, service, sample_cards_df, topic, expected_reviews, expected_correct):
        """Test review counts are aggregated correctly per topic."""
        result = service._compute_mastery_dataframe(sample_cards_df, [topic])
        assert result.loc[topic]["total_reviews"] == expected_reviews
        assert result.loc[topic]["correct_reviews"] == expected_correct

    def test_calculates_success_rate(self, service, sample_cards_df):
        """Test success rate calculation."""
        result = service._compute_mastery_dataframe(sample_cards_df, ["ml"])
        expected_success_rate = 22 / 25
        assert abs(result.loc["ml"]["success_rate"] - expected_success_rate) < 0.01

    def test_mastery_score_bounds(self, service, sample_cards_df):
        """Test mastery score is between 0 and 1."""
        result = service._compute_mastery_dataframe(sample_cards_df, ["ml"])
        assert 0 <= result.loc["ml"]["mastery_score"] <= 1

    def test_returns_empty_for_nonexistent_topic(self, service, sample_cards_df):
        """Test empty DataFrame for topics with no cards."""
        result = service._compute_mastery_dataframe(sample_cards_df, ["nonexistent"])
        assert result.empty

    def test_handles_zero_reviews(self, service):
        """Test handling of topics with zero reviews."""
        cards_df = pd.DataFrame([{
            "id": 1, "tags": ["new_topic"], "state": CardState.NEW,
            "stability": 0.0, "total_reviews": 0, "correct_reviews": 0, "last_reviewed": None,
        }])
        result = service._compute_mastery_dataframe(cards_df, ["new_topic"])

        assert result.loc["new_topic"]["success_rate"] is None
        assert result.loc["new_topic"]["mastery_score"] == 0.0


# ============================================================================
# Test _calculate_mastery_batch
# ============================================================================


class TestCalculateMasteryBatch:
    """Tests for _calculate_mastery_batch method."""

    @pytest.mark.asyncio
    async def test_returns_empty_for_empty_topics(self, service):
        """Test empty list is returned for empty topics."""
        result = await service._calculate_mastery_batch([])
        assert result == []

    @pytest.mark.asyncio
    async def test_returns_empty_states_when_no_cards(self, service):
        """Test empty states are returned when no cards exist."""
        with patch.object(service, "_fetch_cards_dataframe", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = pd.DataFrame()
            with patch.object(service, "_get_recent_snapshots_batch", new_callable=AsyncMock) as mock_snap:
                mock_snap.return_value = {}
                result = await service._calculate_mastery_batch(["topic1", "topic2"])

                assert len(result) == 2
                assert all(s.mastery_score == 0.0 for s in result)
                assert all(s.practice_count == 0 for s in result)

    @pytest.mark.asyncio
    async def test_calculates_mastery_for_multiple_topics(self, service):
        """Test mastery is calculated for all topics."""
        cards_df = pd.DataFrame([
            {"id": 1, "tags": ["topic1"], "state": CardState.REVIEW, "stability": 15.0,
             "total_reviews": 10, "correct_reviews": 8, "last_reviewed": datetime.utcnow()},
            {"id": 2, "tags": ["topic2"], "state": CardState.REVIEW, "stability": 20.0,
             "total_reviews": 20, "correct_reviews": 18, "last_reviewed": datetime.utcnow()},
        ])

        with patch.object(service, "_fetch_cards_dataframe", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = cards_df
            with patch.object(service, "_get_recent_snapshots_batch", new_callable=AsyncMock) as mock_snap:
                mock_snap.return_value = {}
                result = await service._calculate_mastery_batch(["topic1", "topic2"])

                assert len(result) == 2
                assert result[0].topic_path == "topic1"
                assert result[1].topic_path == "topic2"
                assert all(s.mastery_score > 0 for s in result)


# ============================================================================
# Test _generate_recommendation
# ============================================================================


class TestGenerateRecommendation:
    """Tests for _generate_recommendation method."""

    @pytest.mark.parametrize(
        "state_kwargs,expected_text",
        [
            (
                {"trend": MasteryTrend.DECLINING, "mastery_score": 0.5, "practice_count": 10},
                "declining",
            ),
            (
                {"success_rate": 0.4, "trend": MasteryTrend.STABLE, "mastery_score": 0.5, "practice_count": 10},
                "success rate",
            ),
            (
                {"days_since_review": 30, "trend": MasteryTrend.STABLE, "mastery_score": 0.5, "practice_count": 10},
                "30 days",
            ),
            (
                {"success_rate": 0.8, "days_since_review": 3, "trend": MasteryTrend.STABLE,
                 "mastery_score": 0.7, "practice_count": 10},
                "continue practicing",
            ),
        ],
        ids=["declining", "low_success_rate", "stale_review", "default"],
    )
    def test_recommendations(self, state_kwargs, expected_text):
        """Test recommendation generation for different states."""
        state = MasteryState(topic_path="ml/transformers", **state_kwargs)
        result = MasteryService._generate_recommendation(state)
        assert expected_text in result.lower()


# ============================================================================
# Test _suggest_exercise_types
# ============================================================================


class TestSuggestExerciseTypes:
    """Tests for _suggest_exercise_types method."""

    @pytest.mark.parametrize("mastery_score", [0.2, 0.5, 0.8])
    def test_returns_exercise_types(self, mastery_score):
        """Test that exercise types are returned for various mastery levels."""
        state = MasteryState(topic_path="ml/transformers", mastery_score=mastery_score, practice_count=10)
        result = MasteryService._suggest_exercise_types(state)

        assert isinstance(result, list)
        assert len(result) > 0
        assert all(isinstance(t, ExerciseType) for t in result)


# ============================================================================
# Test take_daily_snapshot
# ============================================================================


class TestTakeDailySnapshot:
    """Tests for take_daily_snapshot method."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("num_topics", [0, 1, 3, 5])
    async def test_creates_correct_number_of_snapshots(self, mock_db, num_topics):
        """Test correct number of snapshots are created."""
        service = MasteryService(mock_db)
        topics = [f"topic{i}" for i in range(num_topics)]
        states = [
            MasteryState(topic_path=t, mastery_score=0.5, practice_count=10)
            for t in topics
        ]

        with patch.object(service, "_get_all_topics", new_callable=AsyncMock) as mock_topics:
            mock_topics.return_value = topics
            with patch.object(service, "_calculate_mastery_batch", new_callable=AsyncMock) as mock_batch:
                mock_batch.return_value = states
                with patch.object(service, "_get_recent_snapshots_batch", new_callable=AsyncMock) as mock_snap:
                    mock_snap.return_value = {}

                    count = await service.take_daily_snapshot()

                    assert count == num_topics
                    assert mock_db.add.call_count == num_topics


# ============================================================================
# Test _calculate_streak
# ============================================================================


class TestCalculateStreak:
    """Tests for _calculate_streak method."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "days_reviewed,expected_streak",
        [
            ([], 0),                      # No reviews
            ([0], 1),                     # Just today
            ([0, 1, 2], 3),              # 3 consecutive days
            ([0, 1, 2, 4], 3),           # Gap on day 3
            ([0, 1, 2, 3, 4, 5, 6], 7),  # Full week
        ],
        ids=["no_reviews", "today_only", "three_days", "with_gap", "full_week"],
    )
    async def test_streak_calculation(self, mock_db, days_reviewed, expected_streak):
        """Test streak counting for various review patterns."""
        today = datetime.utcnow().date()
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [(today - timedelta(days=d),) for d in days_reviewed]
        mock_db.execute = AsyncMock(return_value=mock_result)

        service = MasteryService(mock_db)
        result = await service._calculate_streak()

        assert result == expected_streak


# ============================================================================
# Test _snapshot_to_state
# ============================================================================


class TestSnapshotToState:
    """Tests for _snapshot_to_state method."""

    @pytest.mark.parametrize(
        "snapshot_data,expected_values",
        [
            (
                {"topic_path": "ml/transformers", "mastery_score": 0.75, "practice_count": 20,
                 "success_rate": 0.85, "trend": "improving", "last_practiced": datetime.utcnow(),
                 "retention_estimate": 0.92, "days_since_review": 3},
                {"topic_path": "ml/transformers", "mastery_score": 0.75, "practice_count": 20,
                 "success_rate": 0.85, "trend": MasteryTrend.IMPROVING},
            ),
            (
                {"topic_path": None, "mastery_score": None, "practice_count": None,
                 "success_rate": None, "trend": None, "last_practiced": None,
                 "retention_estimate": None, "days_since_review": None},
                {"topic_path": "", "mastery_score": 0.0, "practice_count": 0,
                 "trend": MasteryTrend.STABLE},
            ),
        ],
        ids=["valid_snapshot", "none_values"],
    )
    def test_snapshot_conversion(self, service, snapshot_data, expected_values):
        """Test snapshot is converted to MasteryState correctly."""
        mock_snapshot = MagicMock(**snapshot_data)
        result = service._snapshot_to_state(mock_snapshot)

        for key, expected in expected_values.items():
            assert getattr(result, key) == expected
