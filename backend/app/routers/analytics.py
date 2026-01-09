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

from typing import Optional
import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.base import get_db
from app.enums.learning import TimePeriod, GroupBy
from app.models.learning import (
    MasteryState,
    MasteryOverview,
    WeakSpotsResponse,
    LearningCurveResponse,
    TimeInvestmentResponse,
    StreakData,
    LogTimeRequest,
    LogTimeResponse,
    DailyStatsResponse,
    PracticeHistoryResponse,
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
    try:
        return await service.get_overview()
    except Exception as e:
        logger.error(f"Failed to get mastery overview: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/daily", response_model=DailyStatsResponse)
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
    try:
        return await service.get_daily_stats()
    except Exception as e:
        logger.error(f"Failed to get daily stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/practice-history", response_model=PracticeHistoryResponse)
async def get_practice_history(
    weeks: int = Query(52, ge=1, le=104, description="Number of weeks of history"),
    service: MasteryService = Depends(get_mastery_service),
) -> PracticeHistoryResponse:
    """
    Get practice history for activity heatmap.

    Returns daily practice activity for the specified number of weeks,
    suitable for rendering a GitHub-style contribution heatmap.
    """
    try:
        return await service.get_practice_history(weeks=weeks)
    except Exception as e:
        logger.error(f"Failed to get practice history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/mastery/{topic:path}", response_model=MasteryState)
async def get_topic_mastery(
    topic: str,
    service: MasteryService = Depends(get_mastery_service),
) -> MasteryState:
    """
    Get mastery state for a specific topic.

    Topic paths use slashes (e.g., "ml/transformers/attention").
    """
    try:
        return await service.get_mastery_state(topic)
    except Exception as e:
        logger.error(f"Failed to get topic mastery: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/weak-spots", response_model=WeakSpotsResponse)
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
    try:
        weak_spots = await service.get_weak_spots(limit=limit)
        overview = await service.get_overview()

        return WeakSpotsResponse(
            weak_spots=weak_spots,
            total_topics=len(overview.topics),
            weak_spot_threshold=settings.MASTERY_WEAK_SPOT_THRESHOLD,
        )
    except Exception as e:
        logger.error(f"Failed to get weak spots: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/learning-curve", response_model=LearningCurveResponse)
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
    try:
        return await service.get_learning_curve(topic=topic, days=days)
    except Exception as e:
        logger.error(f"Failed to get learning curve: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ===========================================
# Snapshot Management (Admin)
# ===========================================


@router.post("/snapshot", response_model=dict)
async def take_mastery_snapshot(
    service: MasteryService = Depends(get_mastery_service),
) -> dict:
    """
    Manually trigger a mastery snapshot.

    This is normally done by a scheduled job at midnight,
    but can be triggered manually for testing.
    """
    try:
        count = await service.take_daily_snapshot()
        return {"status": "success", "snapshots_created": count}
    except Exception as e:
        logger.error(f"Failed to take snapshot: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ===========================================
# Time Investment Endpoints
# ===========================================


@router.get("/time-investment", response_model=TimeInvestmentResponse)
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
    try:
        return await service.get_time_investment(period=period, group_by=group_by)
    except Exception as e:
        logger.error(f"Failed to get time investment: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ===========================================
# Streak Endpoints
# ===========================================


@router.get("/streak", response_model=StreakData)
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
    try:
        return await service.get_streak_data()
    except Exception as e:
        logger.error(f"Failed to get streak data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ===========================================
# Time Logging Endpoint
# ===========================================


@router.post("/time-log", response_model=LogTimeResponse)
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
    try:
        return await service.log_learning_time(request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to log time: {e}")
        raise HTTPException(status_code=500, detail=str(e))
