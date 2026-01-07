"""
Review API Router

Endpoints for spaced repetition card management and review.

Endpoints:
- GET /api/review/due - Get cards due for review
- POST /api/review/rate - Submit a card review rating
- POST /api/review/cards - Create a new card
- GET /api/review/cards/{id} - Get a card by ID
- GET /api/review/stats - Get card statistics
"""

from typing import Optional
import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_db
from app.models.learning import (
    CardCreate,
    CardResponse,
    CardReviewRequest,
    CardReviewResponse,
    DueCardsResponse,
    CardStats,
)
from app.services.learning import SpacedRepService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/review", tags=["review"])


# ===========================================
# Dependency Injection
# ===========================================


async def get_spaced_rep_service(
    db: AsyncSession = Depends(get_db),
) -> SpacedRepService:
    """Get spaced repetition service."""
    return SpacedRepService(db)


# ===========================================
# Card Management Endpoints
# ===========================================


@router.post("/cards", response_model=CardResponse)
async def create_card(
    card_data: CardCreate,
    service: SpacedRepService = Depends(get_spaced_rep_service),
) -> CardResponse:
    """
    Create a new spaced repetition card.

    Card is created in NEW state with FSRS initial parameters.
    """
    try:
        return await service.create_card(card_data)
    except Exception as e:
        logger.error(f"Failed to create card: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cards/{card_id}", response_model=CardResponse)
async def get_card(
    card_id: int,
    service: SpacedRepService = Depends(get_spaced_rep_service),
) -> CardResponse:
    """Get a card by ID."""
    card = await service.get_card(card_id)

    if card is None:
        raise HTTPException(status_code=404, detail="Card not found")

    return card


# ===========================================
# Review Endpoints
# ===========================================


@router.get("/due", response_model=DueCardsResponse)
async def get_due_cards(
    limit: int = Query(50, ge=1, le=200, description="Maximum cards to return"),
    topic: Optional[str] = Query(None, description="Filter by topic tag"),
    service: SpacedRepService = Depends(get_spaced_rep_service),
) -> DueCardsResponse:
    """
    Get cards due for review.

    Returns cards ordered by due date (oldest first) with a review forecast.
    """
    try:
        return await service.get_due_cards(
            limit=limit,
            topic_filter=topic,
        )
    except Exception as e:
        logger.error(f"Failed to get due cards: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/rate", response_model=CardReviewResponse)
async def rate_card(
    request: CardReviewRequest,
    service: SpacedRepService = Depends(get_spaced_rep_service),
) -> CardReviewResponse:
    """
    Submit a review rating for a card.

    FSRS ratings:
    - AGAIN (1): Complete failure, reset to learning
    - HARD (2): Significant difficulty, shorter interval
    - GOOD (3): Correct with effort, normal interval
    - EASY (4): Too easy, longer interval

    Returns the new scheduling information.
    """
    try:
        return await service.review_card(request)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to rate card: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ===========================================
# Statistics Endpoints
# ===========================================


@router.get("/stats", response_model=CardStats)
async def get_card_stats(
    topic: Optional[str] = Query(None, description="Filter by topic tag"),
    service: SpacedRepService = Depends(get_spaced_rep_service),
) -> CardStats:
    """
    Get card statistics.

    Returns counts by state, average stability/difficulty, and due counts.
    """
    try:
        return await service.get_card_stats(topic_filter=topic)
    except Exception as e:
        logger.error(f"Failed to get card stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))
