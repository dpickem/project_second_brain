"""
Learning System Enums

Defines enums for the FSRS spaced repetition algorithm, exercise types,
and mastery tracking.
"""

from enum import Enum


class CardState(str, Enum):
    """
    FSRS card states in the learning state machine.

    State transitions:
    - NEW → LEARNING (first review)
    - LEARNING → REVIEW (graduated) or LEARNING (still learning)
    - REVIEW → REVIEW (success) or RELEARNING (lapse)
    - RELEARNING → REVIEW (recovered) or RELEARNING (still struggling)
    """

    NEW = "new"  # Never reviewed, initial state
    LEARNING = "learning"  # Being learned, short intervals
    REVIEW = "review"  # Graduated, normal spaced intervals
    RELEARNING = "relearning"  # Lapsed and being relearned


class Rating(int, Enum):
    """
    FSRS review ratings.

    User self-assessment after reviewing a card or completing an exercise.
    Maps to FSRS algorithm parameters for scheduling.
    """

    AGAIN = 1  # Complete failure, reset learning
    HARD = 2  # Significant difficulty, shorter interval
    GOOD = 3  # Correct with reasonable effort, normal interval
    EASY = 4  # Too easy, longer interval


class ExerciseType(str, Enum):
    """
    Types of exercises for active learning.

    Text-based exercises:
    - FREE_RECALL: Explain concept from memory
    - SELF_EXPLAIN: Explain why/how something works
    - WORKED_EXAMPLE: Step-by-step solution followed by similar problem
    - APPLICATION: Apply concept to novel situation
    - COMPARE_CONTRAST: Compare two concepts or approaches
    - TEACH_BACK: Explain as if teaching someone (Feynman technique)

    Code-based exercises:
    - CODE_IMPLEMENT: Write code from scratch
    - CODE_COMPLETE: Fill in blanks in code
    - CODE_DEBUG: Find and fix bugs
    - CODE_REFACTOR: Improve existing code
    - CODE_EXPLAIN: Explain what code does
    """

    # Text exercises
    FREE_RECALL = "free_recall"
    SELF_EXPLAIN = "self_explain"
    WORKED_EXAMPLE = "worked_example"
    APPLICATION = "application"
    COMPARE_CONTRAST = "compare_contrast"
    TEACH_BACK = "teach_back"

    # Code exercises
    CODE_IMPLEMENT = "code_implement"
    CODE_COMPLETE = "code_complete"
    CODE_DEBUG = "code_debug"
    CODE_REFACTOR = "code_refactor"
    CODE_EXPLAIN = "code_explain"


class ExerciseDifficulty(str, Enum):
    """
    Difficulty levels aligned with mastery progression.

    Difficulty selection is adaptive based on learner mastery:
    - mastery < 0.3: FOUNDATIONAL (worked examples, completions)
    - mastery 0.3-0.7: INTERMEDIATE (free recall, implementations)
    - mastery > 0.7: ADVANCED (applications, refactoring)
    """

    FOUNDATIONAL = "foundational"  # Basic understanding, scaffolded
    INTERMEDIATE = "intermediate"  # Solid understanding, independent work
    ADVANCED = "advanced"  # Deep understanding, novel applications


class MasteryTrend(str, Enum):
    """
    Trend direction for mastery tracking.

    Calculated by comparing current mastery to previous snapshot:
    - delta > 0.05: IMPROVING
    - delta < -0.05: DECLINING
    - else: STABLE
    """

    IMPROVING = "improving"
    STABLE = "stable"
    DECLINING = "declining"


class SessionType(str, Enum):
    """
    Types of practice sessions.
    """

    REVIEW = "review"  # Spaced repetition review
    PRACTICE = "practice"  # Mixed exercises and cards
    FOCUSED = "focused"  # Focus on specific topic
    WEAK_SPOTS = "weak_spots"  # Target weak areas


class SessionContentMode(str, Enum):
    """
    What types of content to include in a session.

    Controls whether sessions contain exercises, spaced rep cards, or both.
    Used to customize the learning experience based on user preference.
    """

    BOTH = "both"  # Include both exercises and cards (default)
    EXERCISES_ONLY = "exercises_only"  # Only exercises, no spaced rep cards
    CARDS_ONLY = "cards_only"  # Only spaced rep cards, no exercises


class ContentSourcePreference(str, Enum):
    """
    How to source content (exercises or cards) for a session.

    Controls whether to use existing content from the database,
    generate new content via LLM, or a combination.
    """

    PREFER_EXISTING = "prefer_existing"  # Use existing, generate if needed (default)
    GENERATE_NEW = "generate_new"  # Always generate new content (more LLM cost)
    EXISTING_ONLY = "existing_only"  # Only use existing (no LLM cost, may be empty)


class CodeLanguage(str, Enum):
    """
    Supported programming languages for code exercises.
    """

    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    # PyTorch/ML exercises use Python image with torch
    PYTORCH = "pytorch"


class TimePeriod(str, Enum):
    """
    Time periods for analytics queries.

    Used by time investment and other analytics endpoints to specify
    the date range for data aggregation.
    """

    WEEK = "7d"
    MONTH = "30d"
    QUARTER = "90d"
    YEAR = "1y"
    ALL = "all"


class GroupBy(str, Enum):
    """
    Grouping strategy for time-series analytics data.

    Determines how time investment and other metrics are bucketed
    for visualization and trend analysis.
    """

    DAY = "day"
    WEEK = "week"
    MONTH = "month"
