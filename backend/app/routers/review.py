"""
Review API Router

Endpoints for spaced repetition card management and review.

Endpoints:
- GET /api/review/due - Get cards due for review
- POST /api/review/rate - Submit a card review rating
- POST /api/review/evaluate - Evaluate typed answer and get rating (active recall)
- POST /api/review/cards - Create a new card
- POST /api/review/generate - Generate cards for a topic on-demand
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
    CardGenerationRequest,
    CardGenerationResponse,
    CardEvaluateRequest,
    CardEvaluateResponse,
)
from app.services.cost_tracking import CostTracker
from app.services.learning import SpacedRepService
from app.services.learning.card_generator import CardGeneratorService
from app.services.learning.card_evaluator import CardAnswerEvaluator
from app.services.llm.client import get_llm_client

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


async def get_card_generator(
    db: AsyncSession = Depends(get_db),
) -> CardGeneratorService:
    """Get card generator service."""
    return CardGeneratorService(db)


async def get_card_evaluator() -> CardAnswerEvaluator:
    """Get card answer evaluator service."""
    return CardAnswerEvaluator(llm_client=get_llm_client())


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


@router.get("/cards", response_model=list[CardResponse])
async def list_cards(
    topic: Optional[str] = Query(None, description="Filter by topic tag"),
    card_type: Optional[str] = Query(None, description="Filter by card type"),
    state: Optional[str] = Query(None, description="Filter by card state (new, learning, review, mastered)"),
    limit: int = Query(100, ge=1, le=500, description="Maximum cards to return"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    service: SpacedRepService = Depends(get_spaced_rep_service),
) -> list[CardResponse]:
    """
    List all cards with optional filters.
    
    Browse the entire card catalogue with filtering by topic, type, or state.
    """
    try:
        return await service.list_cards(
            topic_filter=topic,
            card_type=card_type,
            state_filter=state,
            limit=limit,
            offset=offset,
        )
    except Exception as e:
        logger.error(f"Failed to list cards: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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


@router.post("/evaluate", response_model=CardEvaluateResponse)
async def evaluate_card_answer(
    request: CardEvaluateRequest,
    service: SpacedRepService = Depends(get_spaced_rep_service),
    evaluator: CardAnswerEvaluator = Depends(get_card_evaluator),
) -> CardEvaluateResponse:
    """
    Evaluate a typed answer for a card using LLM.

    This enables "active recall" mode where users type their answer
    instead of just flipping the card. The LLM evaluates the answer
    semantically and returns an appropriate FSRS rating.

    Use the returned rating with the /rate endpoint to save the review.

    Returns:
    - rating: FSRS rating (1-4) based on answer quality
    - is_correct: True if rating >= 3 (Good or Easy)
    - feedback: Explanation of what was correct/incorrect
    - expected_answer: The correct answer for comparison
    """
    # Get the card first
    card = await service.get_card(request.card_id)
    if card is None:
        raise HTTPException(status_code=404, detail="Card not found")

    try:
        # Evaluate the user's answer against the expected answer
        result = await evaluator.evaluate_answer(
            question=card.front,
            expected_answer=card.back,
            user_answer=request.user_answer,
        )

        return CardEvaluateResponse(
            card_id=request.card_id,
            rating=result["rating"],
            is_correct=result["is_correct"],
            feedback=result["feedback"],
            key_points_covered=result["key_points_covered"],
            key_points_missed=result["key_points_missed"],
            expected_answer=card.back,
        )
    except Exception as e:
        logger.error(f"Failed to evaluate card answer: {e}")
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


# ===========================================
# Card Generation Endpoints
# ===========================================


@router.post("/generate", response_model=CardGenerationResponse)
async def generate_cards(
    request: CardGenerationRequest,
    generator: CardGeneratorService = Depends(get_card_generator),
) -> CardGenerationResponse:
    """
    Generate spaced repetition cards for a topic on-demand.

    Uses existing content and LLM to generate flashcards for the specified topic.
    Useful when starting a review session for a topic with few or no cards.
    """
    try:
        cards, usages = await generator.generate_for_topic(
            topic=request.topic,
            count=request.count,
            difficulty=request.difficulty,
        )
        # Track LLM usage for cost monitoring
        if usages:
            await CostTracker.log_usages_batch(usages)

        # Get total card count for topic
        total, more_usages = await generator.ensure_minimum_cards(request.topic, minimum=0)
        if more_usages:
            await CostTracker.log_usages_batch(more_usages)

        return CardGenerationResponse(
            generated_count=len(cards),
            total_cards=total,
            topic=request.topic,
        )
    except Exception as e:
        logger.error(f"Failed to generate cards: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ensure-cards", response_model=CardGenerationResponse)
async def ensure_cards_for_topic(
    topic: str = Query(..., description="Topic path"),
    minimum: int = Query(5, ge=1, le=50, description="Minimum cards required"),
    generator: CardGeneratorService = Depends(get_card_generator),
) -> CardGenerationResponse:
    """
    Ensure a minimum number of cards exist for a topic.

    If fewer than `minimum` cards exist, generates more using LLM.
    Returns immediately if enough cards already exist.
    """
    try:
        total, usages = await generator.ensure_minimum_cards(
            topic=topic,
            minimum=minimum,
        )
        # Track LLM usage for cost monitoring
        if usages:
            await CostTracker.log_usages_batch(usages)

        return CardGenerationResponse(
            generated_count=max(0, total - minimum) if total >= minimum else total,
            total_cards=total,
            topic=topic,
        )
    except Exception as e:
        logger.error(f"Failed to ensure cards: {e}")
        raise HTTPException(status_code=500, detail=str(e))
