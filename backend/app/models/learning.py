"""
Learning System API Models (Pydantic)

Request/response schemas for the Learning System API including:
- Spaced repetition cards with FSRS
- Exercises and attempts
- Practice sessions
- Mastery tracking and analytics

ARCHITECTURE NOTE:
    This file contains PYDANTIC models for API validation.
    There is a corresponding SQLAlchemy file: app/db/models_learning.py

    Data flows: API Request → Pydantic → Service → SQLAlchemy → Database

API Contract:
    Request models use StrictRequest (extra="forbid") to reject unknown fields.
    This catches frontend/backend mismatches early with clear 422 errors.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional, TYPE_CHECKING

from pydantic import AwareDatetime, BaseModel, Field

from app.models.base import StrictRequest, StrictResponse
from app.enums.learning import (
    CardState,
    Rating,
    ExerciseType,
    ExerciseDifficulty,
    MasteryTrend,
    SessionType,
    SessionContentMode,
    ContentSourcePreference,
)

if TYPE_CHECKING:
    from app.db.models_learning import (
        SpacedRepCard,
        Exercise,
        PracticeSession,
        ExerciseAttempt,
    )


# ===========================================
# Spaced Repetition Card Models
# ===========================================


class CardBase(BaseModel):
    """
    Base fields for spaced repetition cards.

    Contains the core content fields shared across card creation and response models.
    Cards support multiple types including concept, fact, application, cloze deletion,
    and code exercises, each with optional progressive hints for scaffolded learning.
    """

    card_type: str = Field(
        ..., description="Card type: concept, fact, application, cloze, code"
    )
    front: str = Field(..., description="Front side (question/prompt)")
    back: str = Field(..., description="Back side (answer)")
    hints: list[str] = Field(default_factory=list, description="Progressive hints")
    tags: list[str] = Field(default_factory=list, description="Topic tags")


class CardCreate(CardBase):
    """
    Request to create a new spaced repetition card.

    Extends CardBase with optional source linking to content and Neo4j concepts.
    For code cards, includes language, starter template, solution, and test cases
    that enable automated evaluation in the code sandbox.
    """

    # NOTE: In this project, `content_id` refers to the Content UUID string (not an integer PK).
    # The DB model `SpacedRepCard.content_id` is stored as String(36).
    content_id: Optional[str] = Field(None, description="Source content UUID")
    concept_id: Optional[str] = Field(None, description="Related concept ID in Neo4j")
    # Code-specific fields
    language: Optional[str] = Field(None, description="Programming language")
    starter_code: Optional[str] = Field(None, description="Initial code template")
    solution_code: Optional[str] = Field(None, description="Reference solution")
    test_cases: Optional[list[dict]] = Field(
        None, description="Test cases for code cards"
    )


class CardResponse(CardBase):
    """
    Card response with FSRS state.

    Includes the full FSRS scheduling state: stability (memory strength in days),
    difficulty (0-1 scale), and current learning state. The due_date indicates when
    the card should next be reviewed based on the FSRS-4.5 optimal retention algorithm.
    """

    id: int
    # NOTE: In this project, `content_id` refers to the Content UUID string (not an integer PK).
    content_id: Optional[str] = None
    concept_id: Optional[str] = None

    # FSRS state
    state: CardState = CardState.NEW
    stability: float = Field(0.0, description="Memory stability in days")
    difficulty: float = Field(
        0.3, ge=0.0, description="FSRS card difficulty (can exceed 1.0 after reviews)"
    )
    due_date: datetime
    last_reviewed: Optional[datetime] = None

    # Stats
    repetitions: int = 0
    lapses: int = 0
    total_reviews: int = 0
    correct_reviews: int = 0

    # Code fields (if applicable)
    language: Optional[str] = None

    class Config:
        from_attributes = True

    @classmethod
    def from_db_record(cls, record: SpacedRepCard) -> CardResponse:
        """
        Create a CardResponse from a database SpacedRepCard record.

        Factory method for converting SQLAlchemy models to Pydantic models
        when loading cards from the database.

        Args:
            record: SQLAlchemy SpacedRepCard record from the database

        Returns:
            CardResponse instance with data from the database record

        Example:
            >>> card = CardResponse.from_db_record(db_card)
        """
        return cls(
            id=record.id,
            card_type=record.card_type,
            front=record.front,
            back=record.back,
            hints=record.hints or [],
            tags=record.tags or [],
            content_id=record.content_id,
            concept_id=record.concept_id,
            state=CardState(record.state),
            stability=record.stability,
            difficulty=record.difficulty,
            due_date=record.due_date,
            last_reviewed=record.last_reviewed,
            repetitions=record.repetitions,
            lapses=record.lapses,
            total_reviews=record.total_reviews,
            correct_reviews=record.correct_reviews,
            language=record.language,
        )


class CardReviewRequest(StrictRequest):
    """
    Request to submit a card review rating.

    The rating follows FSRS conventions: Again (1) for forgotten, Hard (2) for difficult
    recall, Good (3) for successful recall with effort, Easy (4) for effortless recall.
    Time spent is tracked for analytics and can inform future difficulty adjustments.

    Note: Uses StrictRequest - unknown fields will be rejected with 422.
    """

    card_id: int = Field(..., description="Card ID to review")
    rating: Rating = Field(..., description="Self-assessment rating (1-4)")
    response: Optional[str] = Field(None, description="Optional response text")
    time_spent_seconds: Optional[int] = Field(
        None, ge=0, description="Time spent on review"
    )


class CardReviewResponse(BaseModel):
    """
    Response after submitting a card review.

    Contains the updated FSRS state after processing the review. The scheduled_days
    field shows when the card will next be due, which can range from minutes (for
    Again ratings) to months (for well-learned Easy cards with high stability).
    """

    card_id: int
    new_state: CardState
    new_stability: float
    new_difficulty: float
    next_due_date: datetime
    scheduled_days: int = Field(description="Days until next review")
    was_correct: bool = Field(description="Whether rating indicates success")


class ReviewForecast(BaseModel):
    """
    Forecast of upcoming reviews.

    Provides a breakdown of review workload to help users plan their study sessions.
    Overdue cards should be prioritized, while the weekly forecast helps set
    expectations for sustained learning commitment.
    """

    overdue: int = 0
    today: int = 0
    tomorrow: int = 0
    this_week: int = 0
    later: int = 0


class DueCardsResponse(BaseModel):
    """
    Response with due cards and forecast.

    Returns cards ordered by due date (oldest first) along with the total count
    of due cards and a forecast of upcoming reviews. The forecast helps users
    understand their review backlog and plan study sessions accordingly.
    """

    cards: list[CardResponse]
    total_due: int
    review_forecast: ReviewForecast


# ===========================================
# Exercise Models
# ===========================================


class ExerciseBase(BaseModel):
    """
    Base fields for exercises.

    Exercises are active learning activities generated by the LLM based on ingested
    content. Types include free recall, self-explanation, worked examples, code
    implementation, and debugging. Difficulty adapts to the learner's mastery level.
    """

    exercise_type: ExerciseType
    topic: str = Field(..., description="Topic path (e.g., ml/transformers)")
    difficulty: ExerciseDifficulty = ExerciseDifficulty.INTERMEDIATE
    prompt: str = Field(..., description="Main exercise prompt")
    hints: list[str] = Field(default_factory=list, description="Progressive hints")
    expected_key_points: list[str] = Field(
        default_factory=list, description="Key points for a good answer"
    )


class ExerciseCreate(ExerciseBase):
    """
    Request to create an exercise.

    Extends ExerciseBase with type-specific fields: worked examples include step-by-step
    solutions and follow-up problems, code exercises have starter/solution code with
    test cases, and debug exercises contain intentionally buggy code to fix.
    """

    worked_example: Optional[str] = Field(
        None, description="Step-by-step solution (for worked_example type)"
    )
    follow_up_problem: Optional[str] = Field(
        None, description="Follow-up problem after worked example"
    )
    # Code-specific
    language: Optional[str] = None
    starter_code: Optional[str] = None
    solution_code: Optional[str] = None
    test_cases: Optional[list[dict]] = None
    buggy_code: Optional[str] = Field(
        None, description="Code with bugs (for debug exercises)"
    )
    source_content_ids: list[str] = Field(
        default_factory=list, description="Content IDs used to generate"
    )
    estimated_time_minutes: int = Field(10, ge=1, le=120)
    tags: list[str] = Field(default_factory=list)


class ExerciseResponse(ExerciseBase):
    """
    Exercise response (hides solution until attempted).

    Returns the exercise prompt and any scaffolding (hints, starter code, buggy code)
    but withholds the solution until after the learner submits an attempt. This
    prevents premature exposure to answers and encourages genuine retrieval practice.
    """

    id: int
    exercise_uuid: str
    worked_example: Optional[str] = None  # Included for worked_example type
    follow_up_problem: Optional[str] = None
    language: Optional[str] = None
    starter_code: Optional[str] = None
    buggy_code: Optional[str] = None  # Included for debug type
    estimated_time_minutes: int = 10
    tags: list[str] = Field(default_factory=list)

    class Config:
        from_attributes = True

    @classmethod
    def from_db_record(cls, record: Exercise) -> ExerciseResponse:
        """
        Create an ExerciseResponse from a database Exercise record.

        Factory method for converting SQLAlchemy models to Pydantic models
        when loading exercises from the database. Note: Solution is not
        included to hide it until after an attempt.

        Args:
            record: SQLAlchemy Exercise record from the database

        Returns:
            ExerciseResponse instance with data from the database record

        Example:
            >>> exercise = ExerciseResponse.from_db_record(db_exercise)
        """
        return cls(
            id=record.id,
            exercise_uuid=record.exercise_uuid,
            exercise_type=ExerciseType(record.exercise_type),
            topic=record.topic,
            difficulty=ExerciseDifficulty(record.difficulty),
            prompt=record.prompt,
            hints=record.hints or [],
            expected_key_points=record.expected_key_points or [],
            worked_example=record.worked_example,
            follow_up_problem=record.follow_up_problem,
            language=record.language,
            starter_code=record.starter_code,
            buggy_code=record.buggy_code,
            estimated_time_minutes=record.estimated_time_minutes,
            tags=record.tags or [],
        )


class ExerciseWithSolution(ExerciseResponse):
    """
    Exercise with solution revealed (after attempt).

    Extends ExerciseResponse to include the reference solution and test cases.
    Only returned after the learner submits an attempt, enabling comparison
    between their response and the expected answer for self-assessment.
    """

    solution_code: Optional[str] = None
    test_cases: Optional[list[dict]] = None


class ExerciseGenerateRequest(StrictRequest):
    """
    Request to generate an exercise.

    The LLM exercise generator uses the topic and optional source content to create
    a contextually relevant exercise. If type/difficulty are not specified, they are
    automatically selected based on the learner's current mastery level for the topic.

    Note: Uses StrictRequest - unknown fields will be rejected with 422.
    """

    topic: str = Field(..., description="Topic to generate exercise for")
    exercise_type: Optional[ExerciseType] = Field(
        None, description="Specific type, or auto-select based on mastery"
    )
    difficulty: Optional[ExerciseDifficulty] = Field(
        None, description="Specific difficulty, or auto-select based on mastery"
    )
    language: Optional[str] = Field(
        None, description="Programming language for code exercises"
    )
    source_content_ids: list[str] = Field(
        default_factory=list, description="Optional content IDs to base exercise on"
    )


class ContentExerciseGenerateRequest(StrictRequest):
    """
    Request to generate exercises for a specific content item.

    Generates exercises based on the content's extracted concepts and/or
    full summary. This is typically triggered from the Knowledge page UI
    when a user wants exercises for a specific piece of content.

    Note: Uses StrictRequest - unknown fields will be rejected with 422.
    """

    generate_from_concepts: bool = Field(
        True, description="Generate exercises from extracted concepts"
    )
    generate_from_content: bool = Field(
        True, description="Generate exercises from content summary"
    )
    max_from_concepts: Optional[int] = Field(
        None, description="Max exercises from concepts (uses default if not set)"
    )
    max_from_content: Optional[int] = Field(
        None, description="Max exercises from content (uses default if not set)"
    )


class ContentExerciseStatus(StrictResponse):
    """
    Status of exercises for a content item.

    Used to check if a content item already has exercises before generating new ones.
    Helps prevent duplicate generation.
    """

    content_uuid: str
    content_title: Optional[str] = None
    has_exercises: bool
    total_exercises: int
    exercises_from_concepts: int
    exercises_from_content: int
    concept_names: list[str] = Field(
        default_factory=list, description="Concepts that have exercises"
    )


class ContentExerciseGenerateResponse(StrictResponse):
    """
    Response from content exercise generation.

    Returns both the status (including any pre-existing exercises) and
    the newly generated exercises. Includes a warning if exercises
    already existed for this content.
    """

    content_uuid: str
    warning: Optional[str] = Field(
        None, description="Warning if exercises already existed"
    )
    existing_exercise_count: int = 0
    generated_exercises: list[ExerciseResponse] = Field(default_factory=list)
    total_exercises: int = 0


# ===========================================
# Exercise Attempt Models
# ===========================================


class CodeExecutionResult(BaseModel):
    """
    Result of a single test case execution.

    Captures the outcome of running learner code against a test case in the sandbox.
    Includes input/expected/actual values for debugging failed tests, and any
    execution errors (syntax errors, exceptions, timeouts) that occurred.

    Note: Named CodeExecutionResult (not TestResult) to avoid pytest collection warnings.
    """

    test_index: int
    passed: bool
    input_value: Optional[str] = None
    expected: Optional[str] = None
    actual: Optional[str] = None
    error: Optional[str] = None


class AttemptSubmitRequest(StrictRequest):
    """
    Request to submit an exercise attempt.

    Supports both text responses (for conceptual exercises) and code responses
    (for programming exercises). The confidence_before field captures the learner's
    self-assessment prior to receiving feedback, enabling calibration tracking.

    Note: Uses StrictRequest - unknown fields will be rejected with 422.
    """

    exercise_id: int = Field(..., description="Exercise ID")
    response: Optional[str] = Field(None, description="Text response")
    response_code: Optional[str] = Field(None, description="Code response")
    confidence_before: Optional[int] = Field(
        None, ge=1, le=5, description="Self-reported confidence before (1-5)"
    )
    time_spent_seconds: Optional[int] = Field(None, ge=0)


class AttemptEvaluationResponse(BaseModel):
    """
    Evaluation result for an exercise attempt.

    Contains LLM-generated feedback analyzing the response against expected key points.
    Identifies covered points, missing concepts, and any misconceptions detected.
    For code exercises, includes detailed test results from sandbox execution.
    """

    attempt_id: int
    attempt_uuid: str
    score: float = Field(ge=0.0, le=1.0, description="Normalized score")
    is_correct: bool
    feedback: str = Field(..., description="LLM-generated feedback")

    # Detailed evaluation
    covered_points: list[str] = Field(
        default_factory=list, description="Key points addressed"
    )
    missing_points: list[str] = Field(
        default_factory=list, description="Key points missed"
    )
    misconceptions: list[str] = Field(
        default_factory=list, description="Identified misconceptions"
    )

    # Code-specific
    tests_passed: Optional[int] = None
    tests_total: Optional[int] = None
    test_results: Optional[list[CodeExecutionResult]] = None
    execution_error: Optional[str] = None

    # Solution reveal
    exercise_with_solution: Optional[ExerciseWithSolution] = None


class AttemptConfidenceUpdate(StrictRequest):
    """
    Update confidence after viewing feedback.

    Captures the learner's revised self-assessment after seeing the evaluation.
    Comparing confidence_before and confidence_after reveals calibration accuracy—
    well-calibrated learners show smaller deltas between pre and post confidence.

    Note: Uses StrictRequest - unknown fields will be rejected with 422.
    """

    confidence_after: int = Field(ge=1, le=5)


# ===========================================
# Practice Session Models
# ===========================================


class SessionItem(BaseModel):
    """
    Single item in a practice session (card or exercise).

    Wraps either a spaced repetition card or an exercise with timing metadata.
    The session service interleaves these items for optimal learning, placing
    worked examples first (scaffolding) then shuffling remaining items (interleaving).
    """

    item_type: str = Field(description="'card' or 'exercise'")
    card: Optional[CardResponse] = None
    exercise: Optional[ExerciseResponse] = None
    estimated_minutes: float = 2.0


class SessionCreateRequest(StrictRequest):
    """
    Request to create a practice session with configurable content mix.

    Session composition is controlled by:
    - content_mode: What to include (exercises, cards, or both)
    - exercise_source: How to source exercises (existing, generate, or both)
    - card_source: How to source cards (due cards, generate new, or both)
    - Time allocation ratios for exercises vs cards

    Defaults are configured in settings but can be overridden per-request.
    The topic_filter focuses the session on a specific area.

    Note: Uses StrictRequest - unknown fields will be rejected with 422.
    """

    duration_minutes: int = Field(15, ge=5, le=120, description="Target duration")
    topic_filter: Optional[str] = Field(None, description="Optional topic to focus on")
    session_type: SessionType = SessionType.PRACTICE

    # Content mode: what types of items to include
    content_mode: Optional[SessionContentMode] = Field(
        None,
        description="What to include: 'both', 'exercises_only', 'cards_only'. "
        "Uses SESSION_DEFAULT_CONTENT_MODE if not specified.",
    )

    # Source preferences: how to get content
    exercise_source: Optional[ContentSourcePreference] = Field(
        None,
        description="How to source exercises: 'prefer_existing', 'generate_new', 'existing_only'. "
        "Uses SESSION_DEFAULT_EXERCISE_SOURCE if not specified.",
    )
    card_source: Optional[ContentSourcePreference] = Field(
        None,
        description="How to source cards: 'prefer_existing', 'generate_new', 'existing_only'. "
        "Uses SESSION_DEFAULT_CARD_SOURCE if not specified.",
    )

    # Time allocation overrides (0-1 ratios, must sum to 1 if both provided)
    exercise_ratio: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Ratio of time for exercises (0-1). Card ratio is 1 - this value. "
        "Uses settings defaults if not specified.",
    )


class SessionResponse(BaseModel):
    """
    Practice session with items.

    Contains the ordered list of items to complete during the session. Items are
    interleaved for optimal learning with worked examples placed first. The
    estimated duration helps users plan their available study time.
    """

    session_id: int
    items: list[SessionItem]
    estimated_duration_minutes: float
    topics_covered: list[str]
    session_type: SessionType


class SessionSummary(BaseModel):
    """
    Summary after completing a session.

    Provides performance metrics and mastery changes from the session. The
    mastery_changes dict shows how each practiced topic's mastery score changed,
    helping learners see the impact of their study session.
    """

    session_id: int
    duration_minutes: float
    cards_reviewed: int
    exercises_completed: int
    correct_count: int
    total_count: int
    average_score: float
    mastery_changes: dict[str, float] = Field(
        default_factory=dict, description="Topic -> mastery delta"
    )

    @classmethod
    def from_db_record(
        cls,
        record: PracticeSession,
        mastery_changes: dict[str, float] | None = None,
    ) -> SessionSummary:
        """
        Create a SessionSummary from a database PracticeSession record.

        Factory method for converting SQLAlchemy models to Pydantic models
        when loading session data from the database.

        Args:
            record: SQLAlchemy PracticeSession record from the database
            mastery_changes: Optional dict of topic mastery changes

        Returns:
            SessionSummary instance with data from the database record

        Example:
            >>> summary = SessionSummary.from_db_record(db_session)
        """
        return cls(
            session_id=record.id,
            duration_minutes=record.duration_minutes or 0,
            cards_reviewed=record.total_cards,
            exercises_completed=record.exercise_count or 0,
            correct_count=record.correct_count,
            total_count=record.total_cards + (record.exercise_count or 0),
            average_score=record.average_score or 0.0,
            mastery_changes=mastery_changes or {},
        )


# ===========================================
# Mastery & Analytics Models
# ===========================================


class MasteryState(BaseModel):
    """
    Mastery state for a topic.

    Combines card-based metrics (stability, success rate) with practice history
    to estimate topic mastery. The retention_estimate predicts current recall
    probability based on time since last review and card stability.
    
    Now includes separate card and exercise mastery for filtered views.
    """

    topic_path: str
    mastery_score: float = Field(ge=0.0, le=1.0, description="Combined mastery score")
    # Separate mastery scores for cards vs exercises
    card_mastery_score: Optional[float] = Field(
        None, ge=0.0, le=1.0, description="Card-based mastery score"
    )
    exercise_mastery_score: Optional[float] = Field(
        None, ge=0.0, le=1.0, description="Exercise-based mastery score"
    )
    card_count: int = Field(0, description="Number of cards for this topic")
    exercise_count: int = Field(0, description="Number of exercises for this topic")
    confidence_avg: Optional[float] = None
    practice_count: int = 0
    success_rate: Optional[float] = None
    trend: MasteryTrend = MasteryTrend.STABLE
    last_practiced: Optional[datetime] = None
    retention_estimate: Optional[float] = None
    days_since_review: Optional[int] = None


class WeakSpot(BaseModel):
    """
    Topic identified as needing attention.

    Flagged when mastery score falls below threshold or shows declining trend.
    Includes actionable recommendations and suggested exercise types tailored
    to the learner's current level (e.g., worked examples for novices).
    """

    topic: str
    mastery_score: float
    success_rate: Optional[float] = None
    trend: MasteryTrend
    recommendation: str = Field(description="Suggested action")
    suggested_exercise_types: list[ExerciseType] = Field(default_factory=list)


class WeakSpotsResponse(BaseModel):
    """
    Response with weak spots.

    Returns topics sorted by priority: declining trends first, then lowest mastery.
    The threshold (default 0.6) determines what qualifies as a weak spot, helping
    learners focus their limited study time on areas that need the most work.
    """

    weak_spots: list[WeakSpot]
    total_topics: int
    weak_spot_threshold: float = 0.6


class MasteryOverview(BaseModel):
    """
    Overall mastery statistics.

    Provides a dashboard view of learning progress across all topics. Card counts
    show distribution across learning states (new, learning, mastered). The streak
    counter motivates consistent daily practice through gamification.

    Includes separate stats for spaced repetition cards and exercises to give
    users clear visibility into both learning modalities.
    """

    overall_mastery: float = Field(ge=0.0, le=1.0)
    topics: list[MasteryState]

    # Spaced repetition card stats
    spaced_rep_cards_total: int = Field(0, description="Total spaced repetition cards")
    spaced_rep_cards_mastered: int = Field(
        0, description="Cards with stability >= 21 days"
    )
    spaced_rep_cards_learning: int = Field(
        0, description="Cards in learning/relearning/review state"
    )
    spaced_rep_cards_new: int = Field(0, description="Cards never reviewed")
    spaced_rep_reviews_total: int = Field(0, description="Total card reviews completed")

    # Exercise stats
    exercises_total: int = Field(0, description="Total exercises available")
    exercises_completed: int = Field(
        0, description="Exercises with at least one attempt"
    )
    exercises_mastered: int = Field(0, description="Exercises with avg score >= 80%")
    exercises_attempts_total: int = Field(0, description="Total exercise attempts")
    exercises_avg_score: float = Field(
        0.0, description="Average score across all attempts"
    )

    streak_days: int = Field(0, description="Consecutive practice days")
    total_practice_time_hours: float = 0.0


class LearningCurveDataPoint(BaseModel):
    """
    Single data point for learning curve.

    Represents a daily snapshot of mastery metrics for time-series visualization.
    The retention_estimate shows predicted recall probability, while cards_reviewed
    indicates study activity level for that day.

    Now includes exercise activity for comprehensive progress tracking.
    """

    date: datetime
    mastery_score: float
    retention_estimate: Optional[float] = None
    # Card activity
    cards_reviewed: int = Field(0, description="Number of cards reviewed on this day")
    card_time_minutes: int = Field(0, description="Time spent on card reviews in minutes")
    # Exercise activity
    exercises_attempted: int = Field(
        0, description="Number of exercise attempts on this day"
    )
    exercise_score: Optional[float] = Field(
        None, description="Average exercise score for this day (0-100)"
    )
    exercise_time_minutes: int = Field(
        0, description="Time spent on exercises in minutes"
    )
    # Time tracking (total = card_time + exercise_time)
    time_minutes: int = Field(0, description="Total practice time in minutes")


class LearningCurveResponse(BaseModel):
    """
    Learning curve data for visualization.

    Contains historical mastery data points for charting progress over time.
    The trend indicator and 30-day projection help learners understand their
    trajectory and estimate when they'll reach mastery milestones.
    """

    topic: Optional[str] = Field(None, description="Topic or None for overall")
    data_points: list[LearningCurveDataPoint]
    trend: MasteryTrend
    projected_mastery_30d: Optional[float] = None


# ===========================================
# Card Statistics
# ===========================================


class CardStats(BaseModel):
    """
    Statistics about cards in the system.

    Provides aggregate metrics for the card collection including state distribution,
    average stability/difficulty, and review workload. Useful for understanding
    overall system health and planning study capacity.
    """

    total_cards: int
    cards_by_state: dict[str, int] = Field(
        default_factory=dict, description="Count per CardState"
    )
    avg_stability: float = 0.0
    avg_difficulty: float = 0.0
    due_today: int = 0
    overdue: int = 0


class CardGenerationRequest(StrictRequest):
    """
    Request to generate cards for a topic.

    Uses existing content and LLM to generate flashcards for the specified topic.
    The difficulty parameter controls the mix of generated cards, while count
    determines how many cards to create in a single generation batch.

    Note: Uses StrictRequest - unknown fields will be rejected with 422.
    """

    topic: str = Field(..., description="Topic path (e.g., 'ml/transformers')")
    count: int = Field(10, ge=1, le=50, description="Number of cards to generate")
    difficulty: str = Field(
        "mixed", description="Difficulty: easy, medium, hard, mixed"
    )


class CardGenerationResponse(BaseModel):
    """
    Response from card generation.

    Returns the number of cards generated along with the total card count for the
    topic after generation. Useful for understanding how many new cards were added
    and the current size of the topic's card pool.
    """

    generated_count: int
    total_cards: int
    topic: str


class CardEvaluateRequest(StrictRequest):
    """
    Request to evaluate a typed answer for a card.

    Enables "active recall" mode where users type their answer instead of just
    flipping the card. The LLM evaluates the answer semantically and returns
    an appropriate FSRS rating based on answer quality.

    Note: Uses StrictRequest - unknown fields will be rejected with 422.
    """

    card_id: int = Field(..., description="Card ID")
    user_answer: str = Field(..., description="User's typed answer")


class CardEvaluateResponse(BaseModel):
    """
    Response from card answer evaluation.

    Contains the LLM's assessment of the user's typed answer including an FSRS
    rating (1-4), detailed feedback explaining what was correct/incorrect, and
    lists of key points covered and missed. The expected_answer is included for
    comparison to help the learner understand the gap between their response
    and the ideal answer.
    """

    card_id: int
    rating: int = Field(..., ge=1, le=4, description="FSRS rating (1-4)")
    is_correct: bool = Field(
        ..., description="Whether the answer is considered correct"
    )
    feedback: str = Field(..., description="Explanation for the learner")
    key_points_covered: list[str] = Field(default_factory=list)
    key_points_missed: list[str] = Field(default_factory=list)
    expected_answer: str = Field(..., description="The correct answer for comparison")


# ===========================================
# Time Investment Models
# ===========================================


class TimeInvestmentPeriod(BaseModel):
    """
    Time investment for a specific period.

    Represents aggregated learning time within a time window, broken down by topic
    and activity type. Used for building time-series visualizations of study habits.
    """

    period_start: AwareDatetime
    period_end: AwareDatetime
    total_minutes: float
    by_topic: dict[str, float] = Field(default_factory=dict)  # topic -> minutes
    by_activity: dict[str, float] = Field(
        default_factory=dict
    )  # activity_type -> minutes


class TimeInvestmentResponse(BaseModel):
    """
    Time investment summary response.

    Provides comprehensive time tracking data including period breakdowns, top topics
    by time spent, daily average, and trend analysis. Powers the time investment
    dashboard for understanding study patterns and consistency.
    """

    total_minutes: float
    periods: list[TimeInvestmentPeriod]
    top_topics: list[tuple[str, float]] = Field(
        default_factory=list
    )  # (topic, minutes)
    daily_average: float
    trend: str  # "increasing", "decreasing", "stable"


# ===========================================
# Streak Models
# ===========================================


class StreakData(BaseModel):
    """
    Practice streak information.

    Tracks consecutive days of practice to motivate consistent learning habits.
    Includes current and longest streaks, milestone tracking, and weekly/monthly
    activity counts. Gamification element that encourages daily engagement.
    """

    current_streak: int  # Days
    longest_streak: int
    streak_start: Optional[date] = None
    last_practice: Optional[date] = None
    is_active_today: bool
    days_this_week: int
    days_this_month: int
    # Milestones
    milestones_reached: list[int] = Field(default_factory=list)  # e.g., [7, 30, 100]
    next_milestone: Optional[int] = None


# ===========================================
# Time Logging Models
# ===========================================


class LogTimeRequest(StrictRequest):
    """
    Request to log learning time.

    Captures time spent on learning activities for analytics. Supports various
    activity types (review, practice, reading, exercise) and can be linked to
    specific content, topics, or practice sessions for detailed tracking.

    Note: Uses StrictRequest - unknown fields will be rejected with 422.
    """

    activity_type: str = Field(
        ..., description="Type: review, practice, reading, exercise"
    )
    started_at: AwareDatetime
    ended_at: AwareDatetime
    topic: Optional[str] = None
    content_id: Optional[int] = None
    session_id: Optional[int] = None
    items_completed: int = Field(default=0, ge=0)


class LogTimeResponse(BaseModel):
    """
    Response after logging time.

    Confirms the time log was recorded and returns the calculated duration.
    The human-readable message provides quick feedback to the user about
    how much time was logged.
    """

    id: int
    duration_seconds: int
    message: str


# ===========================================
# Dashboard & Daily Stats Models
# ===========================================


class DailyStatsResponse(BaseModel):
    """
    Daily statistics for the dashboard.

    Provides a quick overview of today's learning status including due cards,
    streak information, and recent activity. Used by the frontend dashboard
    to show the user's current learning status at a glance.
    """

    # Streak info
    streak_days: int = Field(0, description="Current consecutive practice days")
    streak_at_risk: bool = Field(False, description="True if no practice today yet")

    # Cards
    due_cards_count: int = Field(0, description="Cards due for review today")
    total_cards: int = Field(0, description="Total cards in the system")
    cards_reviewed_today: int = Field(0, description="Cards reviewed so far today")

    # Progress
    overall_mastery: float = Field(
        0.0, ge=0.0, le=1.0, description="Overall mastery score"
    )
    practice_time_today_minutes: int = Field(
        0, description="Practice time today in minutes"
    )

    # Greeting context
    last_practice_date: Optional[date] = Field(
        None, description="Date of last practice"
    )


class PracticeHistoryDay(BaseModel):
    """
    Single day of practice history for activity heatmap.

    Contains practice activity metrics for one day, used to render
    GitHub-style activity heatmaps on the dashboard.
    """

    date: date
    count: int = Field(0, description="Number of practice items completed")
    minutes: int = Field(0, description="Total practice minutes")
    level: int = Field(
        0, ge=0, le=4, description="Activity level 0-4 for heatmap coloring"
    )


class PracticeHistoryResponse(BaseModel):
    """
    Practice history for activity heatmap visualization.

    Returns daily practice activity over a configurable time range,
    typically 26 or 52 weeks. Used to render a contribution-style
    heatmap showing practice consistency over time.
    """

    days: list[PracticeHistoryDay] = Field(default_factory=list)
    total_practice_days: int = Field(0, description="Days with at least one practice")
    total_items: int = Field(0, description="Total items practiced")
    max_daily_count: int = Field(0, description="Maximum items in a single day")
