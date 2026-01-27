"""
Practice API Router

Endpoints for practice sessions, exercise generation, and attempt submission.

Endpoints:
- POST /api/practice/session - Create a practice session
- POST /api/practice/session/{id}/end - End a session and get summary
- POST /api/practice/exercise/generate - Generate an exercise
- POST /api/practice/submit - Submit an exercise attempt
- PATCH /api/practice/attempt/{id}/confidence - Update post-feedback confidence
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_db
from app.db.models_learning import Exercise
from app.enums.learning import ExerciseDifficulty, ExerciseType
from app.middleware.error_handling import handle_endpoint_errors
from app.models.learning import (
    AttemptConfidenceUpdate,
    AttemptEvaluationResponse,
    AttemptSubmitRequest,
    ExerciseGenerateRequest,
    ExerciseResponse,
    SessionCreateRequest,
    SessionResponse,
    SessionSummary,
)
from app.services.cost_tracking import CostTracker
from app.services.learning import (
    ExerciseGenerator,
    MasteryService,
    ResponseEvaluator,
    SessionService,
    SpacedRepService,
    get_code_sandbox,
)
from app.services.llm.client import get_llm_client

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/practice", tags=["practice"])


# ===========================================
# Dependency Injection
# ===========================================


async def get_spaced_rep_service(
    db: AsyncSession = Depends(get_db),
) -> SpacedRepService:
    """Get spaced repetition service."""
    return SpacedRepService(db)


async def get_exercise_generator(
    db: AsyncSession = Depends(get_db),
) -> ExerciseGenerator:
    """Get exercise generator service."""
    llm_client = get_llm_client()  # Synchronous - returns singleton
    return ExerciseGenerator(llm_client, db)


async def get_response_evaluator(
    db: AsyncSession = Depends(get_db),
) -> ResponseEvaluator:
    """Get response evaluator service."""
    llm_client = get_llm_client()  # Synchronous - returns singleton
    return ResponseEvaluator(llm_client, db)


async def get_mastery_service(
    db: AsyncSession = Depends(get_db),
) -> MasteryService:
    """Get mastery service."""
    return MasteryService(db)


async def get_session_service(
    db: AsyncSession = Depends(get_db),
    spaced_rep: SpacedRepService = Depends(get_spaced_rep_service),
    exercise_gen: ExerciseGenerator = Depends(get_exercise_generator),
    mastery: MasteryService = Depends(get_mastery_service),
) -> SessionService:
    """Get session service with dependencies."""
    return SessionService(db, spaced_rep, exercise_gen, mastery)


# ===========================================
# Session Endpoints
# ===========================================


@router.post("/session", response_model=SessionResponse)
@handle_endpoint_errors("Create session")
async def create_session(
    request: SessionCreateRequest,
    service: SessionService = Depends(get_session_service),
) -> SessionResponse:
    """
    Create a new practice session.

    Returns a balanced session with:
    - 40% due spaced rep cards
    - 30% weak spot exercises
    - 30% new/interleaved content
    """
    return await service.create_session(request)


@router.post("/session/{session_id}/end", response_model=SessionSummary)
@handle_endpoint_errors("End session")
async def end_session(
    session_id: int,
    service: SessionService = Depends(get_session_service),
) -> SessionSummary:
    """
    End a practice session and get summary statistics.
    """
    return await service.end_session(session_id)


# ===========================================
# Exercise Endpoints
# ===========================================


@router.post("/exercise/generate", response_model=ExerciseResponse)
@handle_endpoint_errors("Generate exercise")
async def generate_exercise(
    request: ExerciseGenerateRequest,
    mastery_level: float = Query(
        0.5, ge=0.0, le=1.0, description="Current mastery level"
    ),
    generator: ExerciseGenerator = Depends(get_exercise_generator),
) -> ExerciseResponse:
    """
    Generate an adaptive exercise for a topic.

    Exercise type and difficulty are selected based on mastery level:
    - < 0.3: Worked examples, code completions
    - 0.3-0.7: Free recall, implementations
    - > 0.7: Applications, teach-back
    """
    exercise, usages = await generator.generate_exercise(
        request=request,
        mastery_level=mastery_level,
    )
    # Track LLM usage for cost monitoring
    if usages:
        await CostTracker.log_usages_batch(usages)
    return exercise


@router.get("/exercises", response_model=list[ExerciseResponse])
@handle_endpoint_errors("List exercises")
async def list_exercises(
    topic: str | None = Query(None, description="Filter by topic path"),
    exercise_type: ExerciseType | None = Query(
        None, description="Filter by exercise type"
    ),
    difficulty: ExerciseDifficulty | None = Query(
        None, description="Filter by difficulty"
    ),
    limit: int = Query(50, ge=1, le=200, description="Maximum exercises to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    db: AsyncSession = Depends(get_db),
) -> list[ExerciseResponse]:
    """
    List all exercises with optional filtering.

    Returns exercises ordered by creation date (newest first).
    """
    query = select(Exercise).order_by(Exercise.created_at.desc())

    if topic:
        query = query.where(Exercise.topic.ilike(f"%{topic}%"))
    if exercise_type:
        query = query.where(Exercise.exercise_type == exercise_type.value)
    if difficulty:
        query = query.where(Exercise.difficulty == difficulty.value)

    query = query.offset(offset).limit(limit)
    result = await db.execute(query)
    exercises = result.scalars().all()

    return [
        ExerciseResponse(
            id=ex.id,
            exercise_uuid=ex.exercise_uuid,
            exercise_type=ExerciseType(ex.exercise_type),
            topic=ex.topic,
            difficulty=ExerciseDifficulty(ex.difficulty),
            prompt=ex.prompt,
            hints=ex.hints or [],
            expected_key_points=ex.expected_key_points or [],
            worked_example=ex.worked_example,
            follow_up_problem=ex.follow_up_problem,
            language=ex.language,
            starter_code=ex.starter_code,
            buggy_code=ex.buggy_code,
            estimated_time_minutes=ex.estimated_time_minutes or 10,
            tags=ex.tags or [],
        )
        for ex in exercises
    ]


@router.get("/exercise/{exercise_id}", response_model=ExerciseResponse)
@handle_endpoint_errors("Get exercise")
async def get_exercise(
    exercise_id: int,
    db: AsyncSession = Depends(get_db),
) -> ExerciseResponse:
    """Get an exercise by ID."""
    result = await db.execute(select(Exercise).where(Exercise.id == exercise_id))
    exercise = result.scalar_one_or_none()

    if exercise is None:
        raise HTTPException(status_code=404, detail="Exercise not found")

    return ExerciseResponse(
        id=exercise.id,
        exercise_uuid=exercise.exercise_uuid,
        exercise_type=ExerciseType(exercise.exercise_type),
        topic=exercise.topic,
        difficulty=ExerciseDifficulty(exercise.difficulty),
        prompt=exercise.prompt,
        hints=exercise.hints or [],
        expected_key_points=exercise.expected_key_points or [],
        worked_example=exercise.worked_example,
        follow_up_problem=exercise.follow_up_problem,
        language=exercise.language,
        starter_code=exercise.starter_code,
        buggy_code=exercise.buggy_code,
        estimated_time_minutes=exercise.estimated_time_minutes or 10,
        tags=exercise.tags or [],
    )


# ===========================================
# Attempt Endpoints
# ===========================================


@router.post("/submit", response_model=AttemptEvaluationResponse)
@handle_endpoint_errors("Submit attempt")
async def submit_attempt(
    request: AttemptSubmitRequest,
    db: AsyncSession = Depends(get_db),
    evaluator: ResponseEvaluator = Depends(get_response_evaluator),
) -> AttemptEvaluationResponse:
    """
    Submit an exercise attempt for evaluation.

    Returns detailed feedback including:
    - Score (0-1)
    - Covered and missing key points
    - Misconceptions identified
    - LLM-generated feedback
    - Solution reveal
    """
    # Load exercise
    result = await db.execute(
        select(Exercise).where(Exercise.id == request.exercise_id)
    )
    exercise = result.scalar_one_or_none()

    if exercise is None:
        raise HTTPException(status_code=404, detail="Exercise not found")

    # Run code tests if applicable
    test_results = None
    if request.response_code and exercise.test_cases:
        sandbox = get_code_sandbox()
        if sandbox.enabled:
            test_results = await sandbox.run_tests(
                code=request.response_code,
                test_cases=exercise.test_cases,
                language=exercise.language or "python",
            )

    return await evaluator.evaluate_response(
        exercise=exercise,
        request=request,
        code_test_results=test_results,
    )


@router.patch("/attempt/{attempt_id}/confidence")
@handle_endpoint_errors("Update confidence")
async def update_confidence(
    attempt_id: int,
    request: AttemptConfidenceUpdate,
    evaluator: ResponseEvaluator = Depends(get_response_evaluator),
) -> dict:
    """
    Update confidence rating after viewing feedback.
    """
    await evaluator.update_confidence(attempt_id, request.confidence_after)
    return {"status": "updated"}
