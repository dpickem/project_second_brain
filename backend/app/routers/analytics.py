"""
Analytics API Router

Endpoints for mastery tracking and learning analytics.

Endpoints:
- GET /api/analytics/overview - Get overall mastery overview
- GET /api/analytics/mastery/{topic} - Get mastery for a specific topic
- GET /api/analytics/weak-spots - Get topics needing attention
- GET /api/analytics/learning-curve - Get learning curve data
"""

from typing import Optional
import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.base import get_db
from app.models.learning import (
    MasteryState,
    MasteryOverview,
    WeakSpotsResponse,
    LearningCurveResponse,
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

        # Get total topic count for context
        # Note: This is a simplified count
        overview = await service.get_overview()
        total_topics = len(overview.topics)

        return WeakSpotsResponse(
            weak_spots=weak_spots,
            total_topics=total_topics,
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
