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
"""

from datetime import date, datetime
from typing import Optional

from pydantic import AwareDatetime, BaseModel, Field

from app.enums.learning import (
    CardState,
    Rating,
    ExerciseType,
    ExerciseDifficulty,
    MasteryTrend,
    SessionType,
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

    content_id: Optional[int] = Field(None, description="Source content ID")
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
    content_id: Optional[int] = None
    concept_id: Optional[str] = None

    # FSRS state
    state: CardState = CardState.NEW
    stability: float = Field(0.0, description="Memory stability in days")
    difficulty: float = Field(0.3, ge=0.0, le=1.0, description="Card difficulty")
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


class CardReviewRequest(BaseModel):
    """
    Request to submit a card review rating.
    
    The rating follows FSRS conventions: Again (1) for forgotten, Hard (2) for difficult
    recall, Good (3) for successful recall with effort, Easy (4) for effortless recall.
    Time spent is tracked for analytics and can inform future difficulty adjustments.
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


class ExerciseWithSolution(ExerciseResponse):
    """
    Exercise with solution revealed (after attempt).
    
    Extends ExerciseResponse to include the reference solution and test cases.
    Only returned after the learner submits an attempt, enabling comparison
    between their response and the expected answer for self-assessment.
    """

    solution_code: Optional[str] = None
    test_cases: Optional[list[dict]] = None


class ExerciseGenerateRequest(BaseModel):
    """
    Request to generate an exercise.
    
    The LLM exercise generator uses the topic and optional source content to create
    a contextually relevant exercise. If type/difficulty are not specified, they are
    automatically selected based on the learner's current mastery level for the topic.
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


class AttemptSubmitRequest(BaseModel):
    """
    Request to submit an exercise attempt.
    
    Supports both text responses (for conceptual exercises) and code responses
    (for programming exercises). The confidence_before field captures the learner's
    self-assessment prior to receiving feedback, enabling calibration tracking.
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


class AttemptConfidenceUpdate(BaseModel):
    """
    Update confidence after viewing feedback.
    
    Captures the learner's revised self-assessment after seeing the evaluation.
    Comparing confidence_before and confidence_after reveals calibration accuracy—
    well-calibrated learners show smaller deltas between pre and post confidence.
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


class SessionCreateRequest(BaseModel):
    """
    Request to create a practice session.
    
    Creates a balanced session mixing due spaced rep cards (40%), weak spot exercises
    (30%), and new content (30%). The topic_filter focuses the session on a specific
    area, otherwise content is drawn from across all learned topics.
    """

    duration_minutes: int = Field(15, ge=5, le=120, description="Target duration")
    topic_filter: Optional[str] = Field(None, description="Optional topic to focus on")
    session_type: SessionType = SessionType.PRACTICE


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


# ===========================================
# Mastery & Analytics Models
# ===========================================


class MasteryState(BaseModel):
    """
    Mastery state for a topic.
    
    Combines card-based metrics (stability, success rate) with practice history
    to estimate topic mastery. The retention_estimate predicts current recall
    probability based on time since last review and card stability.
    """

    topic_path: str
    mastery_score: float = Field(ge=0.0, le=1.0)
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
    """

    overall_mastery: float = Field(ge=0.0, le=1.0)
    topics: list[MasteryState]
    total_cards: int
    cards_mastered: int = Field(description="Cards with stability >= 21 days")
    cards_learning: int
    cards_new: int
    streak_days: int = Field(0, description="Consecutive practice days")
    total_practice_time_hours: float = 0.0


class LearningCurveDataPoint(BaseModel):
    """
    Single data point for learning curve.
    
    Represents a daily snapshot of mastery metrics for time-series visualization.
    The retention_estimate shows predicted recall probability, while cards_reviewed
    indicates study activity level for that day.
    """

    date: datetime
    mastery_score: float
    retention_estimate: Optional[float] = None
    cards_reviewed: int = 0


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
    by_activity: dict[str, float] = Field(default_factory=dict)  # activity_type -> minutes


class TimeInvestmentResponse(BaseModel):
    """
    Time investment summary response.
    
    Provides comprehensive time tracking data including period breakdowns, top topics
    by time spent, daily average, and trend analysis. Powers the time investment
    dashboard for understanding study patterns and consistency.
    """

    total_minutes: float
    periods: list[TimeInvestmentPeriod]
    top_topics: list[tuple[str, float]] = Field(default_factory=list)  # (topic, minutes)
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


class LogTimeRequest(BaseModel):
    """
    Request to log learning time.
    
    Captures time spent on learning activities for analytics. Supports various
    activity types (review, practice, reading, exercise) and can be linked to
    specific content, topics, or practice sessions for detailed tracking.
    """

    activity_type: str = Field(..., description="Type: review, practice, reading, exercise")
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
    overall_mastery: float = Field(0.0, ge=0.0, le=1.0, description="Overall mastery score")
    practice_time_today_minutes: int = Field(0, description="Practice time today in minutes")
    
    # Greeting context
    last_practice_date: Optional[date] = Field(None, description="Date of last practice")


class PracticeHistoryDay(BaseModel):
    """
    Single day of practice history for activity heatmap.
    
    Contains practice activity metrics for one day, used to render
    GitHub-style activity heatmaps on the dashboard.
    """

    date: date
    count: int = Field(0, description="Number of practice items completed")
    minutes: int = Field(0, description="Total practice minutes")
    level: int = Field(0, ge=0, le=4, description="Activity level 0-4 for heatmap coloring")


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
