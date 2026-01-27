"""
Analytics API Router

Endpoints for mastery tracking and learning analytics.

Endpoints:
- GET /api/analytics/overview - Get overall mastery overview
- GET /api/analytics/mastery/{topic} - Get mastery for a specific topic
- GET /api/analytics/weak-spots - Get topics needing attention
- GET /api/analytics/learning-curve - Get learning curve data
- GET /api/analytics/time-investment - Get time investment breakdown
- GET /api/analytics/streak - Get practice streak information
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.base import get_db
from app.enums.learning import GroupBy, TimePeriod
from app.middleware.error_handling import handle_endpoint_errors
from app.models.learning import (
    DailyStatsResponse,
    LearningCurveResponse,
    LogTimeRequest,
    LogTimeResponse,
    MasteryOverview,
    MasteryState,
    PracticeHistoryResponse,
    StreakData,
    TimeInvestmentResponse,
    WeakSpotsResponse,
)
from app.services.learning import MasteryService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/analytics", tags=["analytics"])


# ===========================================
# Dependency Injection
# ===========================================


async def get_mastery_service(
    db: AsyncSession = Depends(get_db),
) -> MasteryService:
    """Get mastery service."""
    return MasteryService(db)


# ===========================================
# Mastery Endpoints
# ===========================================


@router.get("/overview", response_model=MasteryOverview)
@handle_endpoint_errors("Get mastery overview")
async def get_mastery_overview(
    service: MasteryService = Depends(get_mastery_service),
) -> MasteryOverview:
    """
    Get overall mastery statistics.

    Returns:
    - Overall mastery score
    - Card counts by state
    - Topic masteries
    - Practice streak
    """
    return await service.get_overview()


@router.get("/daily", response_model=DailyStatsResponse)
@handle_endpoint_errors("Get daily stats")
async def get_daily_stats(
    service: MasteryService = Depends(get_mastery_service),
) -> DailyStatsResponse:
    """
    Get daily statistics for the dashboard.

    Returns today's learning status including:
    - Current streak and risk status
    - Due cards count
    - Cards reviewed today
    - Overall mastery
    - Practice time today
    """
    return await service.get_daily_stats()


@router.get("/practice-history", response_model=PracticeHistoryResponse)
@handle_endpoint_errors("Get practice history")
async def get_practice_history(
    weeks: int = Query(52, ge=1, le=104, description="Number of weeks of history"),
    service: MasteryService = Depends(get_mastery_service),
) -> PracticeHistoryResponse:
    """
    Get practice history for activity heatmap.

    Returns daily practice activity for the specified number of weeks,
    suitable for rendering a GitHub-style contribution heatmap.
    """
    return await service.get_practice_history(weeks=weeks)


@router.get("/mastery/{topic:path}", response_model=MasteryState)
@handle_endpoint_errors("Get topic mastery")
async def get_topic_mastery(
    topic: str,
    service: MasteryService = Depends(get_mastery_service),
) -> MasteryState:
    """
    Get mastery state for a specific topic.

    Topic paths use slashes (e.g., "ml/transformers/attention").
    """
    return await service.get_mastery_state(topic)


@router.get("/weak-spots", response_model=WeakSpotsResponse)
@handle_endpoint_errors("Get weak spots")
async def get_weak_spots(
    limit: int = Query(10, ge=1, le=50, description="Maximum weak spots to return"),
    service: MasteryService = Depends(get_mastery_service),
) -> WeakSpotsResponse:
    """
    Get topics identified as weak spots.

    Weak spots are topics with:
    - Mastery score < 0.6
    - At least 3 practice attempts
    - Declining trends prioritized
    """
    weak_spots = await service.get_weak_spots(limit=limit)
    overview = await service.get_overview()

    return WeakSpotsResponse(
        weak_spots=weak_spots,
        total_topics=len(overview.topics),
        weak_spot_threshold=settings.MASTERY_WEAK_SPOT_THRESHOLD,
    )


@router.get("/learning-curve", response_model=LearningCurveResponse)
@handle_endpoint_errors("Get learning curve")
async def get_learning_curve(
    topic: Optional[str] = Query(
        None, description="Topic to get curve for (None for overall)"
    ),
    days: int = Query(30, ge=7, le=365, description="Number of days of history"),
    service: MasteryService = Depends(get_mastery_service),
) -> LearningCurveResponse:
    """
    Get learning curve data for visualization.

    Returns historical mastery data points for charting progress over time.
    """
    return await service.get_learning_curve(topic=topic, days=days)


# ===========================================
# Snapshot Management (Admin)
# ===========================================


@router.post("/snapshot", response_model=dict)
@handle_endpoint_errors("Take mastery snapshot")
async def take_mastery_snapshot(
    service: MasteryService = Depends(get_mastery_service),
) -> dict:
    """
    Manually trigger a mastery snapshot.

    This is normally done by a scheduled job at midnight,
    but can be triggered manually for testing.
    """
    count = await service.take_daily_snapshot()
    return {"status": "success", "snapshots_created": count}


# ===========================================
# Time Investment Endpoints
# ===========================================


@router.get("/time-investment", response_model=TimeInvestmentResponse)
@handle_endpoint_errors("Get time investment")
async def get_time_investment(
    period: TimePeriod = Query(TimePeriod.MONTH, description="Time period to analyze"),
    group_by: GroupBy = Query(GroupBy.DAY, description="How to group the data"),
    service: MasteryService = Depends(get_mastery_service),
) -> TimeInvestmentResponse:
    """
    Get time investment breakdown.

    Shows how much time has been spent learning,
    broken down by topic and activity type.

    Args:
        period: Time period to analyze (7d, 30d, 90d, 1y, all)
        group_by: How to group the data (day, week, month)

    Returns:
        Time investment summary with trends
    """
    return await service.get_time_investment(period=period, group_by=group_by)


# ===========================================
# Streak Endpoints
# ===========================================


@router.get("/streak", response_model=StreakData)
@handle_endpoint_errors("Get streak data")
async def get_streak_data(
    service: MasteryService = Depends(get_mastery_service),
) -> StreakData:
    """
    Get practice streak information.

    A streak is maintained by practicing at least once per day.
    Streaks reset if a day is missed.

    Returns:
        Current streak, history, and milestones
    """
    return await service.get_streak_data()


# ===========================================
# Time Logging Endpoint
# ===========================================


@router.post("/time-log", response_model=LogTimeResponse)
@handle_endpoint_errors("Log learning time")
async def log_learning_time(
    request: LogTimeRequest,
    service: MasteryService = Depends(get_mastery_service),
) -> LogTimeResponse:
    """
    Log time spent on a learning activity.

    Called by frontend to track time investment.
    Duration is calculated from started_at and ended_at.

    Args:
        request: Time log details

    Returns:
        Created time log record
    """
    return await service.log_learning_time(request)
