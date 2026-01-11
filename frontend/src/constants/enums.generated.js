/**
 * AUTO-GENERATED FILE - DO NOT EDIT MANUALLY
 * 
 * Generated from Python enums in backend/app/enums/
 * Run: python scripts/generate_enums.py
 * Generated at: 2026-01-10T23:59:04.648036
 * 
 * This file ensures frontend and backend use the same enum values.
 */


/**
 * Types of exercises for active learning.
 * 
 *     Text-based exercises:
 *     - FREE_RECALL: Explain concept from memory
 *     - SELF_EXPLAIN: Explain why/how something works
 *     - WORKED_EXAMPLE: Step-by-step solution followed by similar problem
 *     - APPLICATION: Apply concept to novel situation
 *     - COMPARE_CONTRAST: Compare two concepts or approaches
 *     - TEACH_BACK: Explain as if teaching someone (Feynman technique)
 * 
 *     Code-based exercises:
 *     - CODE_IMPLEMENT: Write code from scratch
 *     - CODE_COMPLETE: Fill in blanks in code
 *     - CODE_DEBUG: Find and fix bugs
 *     - CODE_REFACTOR: Improve existing code
 *     - CODE_EXPLAIN: Explain what code does
 */
export const ExerciseType = Object.freeze({
  FREE_RECALL: 'free_recall',
  SELF_EXPLAIN: 'self_explain',
  WORKED_EXAMPLE: 'worked_example',
  APPLICATION: 'application',
  COMPARE_CONTRAST: 'compare_contrast',
  TEACH_BACK: 'teach_back',
  CODE_IMPLEMENT: 'code_implement',
  CODE_COMPLETE: 'code_complete',
  CODE_DEBUG: 'code_debug',
  CODE_REFACTOR: 'code_refactor',
  CODE_EXPLAIN: 'code_explain'
})

/**
 * Difficulty levels aligned with mastery progression.
 * 
 *     Difficulty selection is adaptive based on learner mastery:
 *     - mastery < 0.3: FOUNDATIONAL (worked examples, completions)
 *     - mastery 0.3-0.7: INTERMEDIATE (free recall, implementations)
 *     - mastery > 0.7: ADVANCED (applications, refactoring)
 */
export const ExerciseDifficulty = Object.freeze({
  FOUNDATIONAL: 'foundational',
  INTERMEDIATE: 'intermediate',
  ADVANCED: 'advanced'
})

/**
 * FSRS card states in the learning state machine.
 * 
 *     State transitions:
 *     - NEW → LEARNING (first review)
 *     - LEARNING → REVIEW (graduated) or LEARNING (still learning)
 *     - REVIEW → REVIEW (success) or RELEARNING (lapse)
 *     - RELEARNING → REVIEW (recovered) or RELEARNING (still struggling)
 */
export const CardState = Object.freeze({
  NEW: 'new',
  LEARNING: 'learning',
  REVIEW: 'review',
  RELEARNING: 'relearning'
})

/**
 * FSRS review ratings.
 * 
 *     User self-assessment after reviewing a card or completing an exercise.
 *     Maps to FSRS algorithm parameters for scheduling.
 */
export const Rating = Object.freeze({
  AGAIN: '1',
  HARD: '2',
  GOOD: '3',
  EASY: '4'
})

/**
 * Trend direction for mastery tracking.
 * 
 *     Calculated by comparing current mastery to previous snapshot:
 *     - delta > 0.05: IMPROVING
 *     - delta < -0.05: DECLINING
 *     - else: STABLE
 */
export const MasteryTrend = Object.freeze({
  IMPROVING: 'improving',
  STABLE: 'stable',
  DECLINING: 'declining'
})

/**
 * Types of practice sessions.
 */
export const SessionType = Object.freeze({
  REVIEW: 'review',
  PRACTICE: 'practice',
  FOCUSED: 'focused',
  WEAK_SPOTS: 'weak_spots'
})

/**
 * Supported programming languages for code exercises.
 */
export const CodeLanguage = Object.freeze({
  PYTHON: 'python',
  JAVASCRIPT: 'javascript',
  TYPESCRIPT: 'typescript',
  PYTORCH: 'pytorch'
})

/**
 * Time periods for analytics queries.
 * 
 *     Used by time investment and other analytics endpoints to specify
 *     the date range for data aggregation.
 */
export const TimePeriod = Object.freeze({
  WEEK: '7d',
  MONTH: '30d',
  QUARTER: '90d',
  YEAR: '1y',
  ALL: 'all'
})

/**
 * Grouping strategy for time-series analytics data.
 * 
 *     Determines how time investment and other metrics are bucketed
 *     for visualization and trend analysis.
 */
export const GroupBy = Object.freeze({
  DAY: 'day',
  WEEK: 'week',
  MONTH: 'month'
})

/**
 * Built-in content types for the ingestion system.
 * 
 *     This enum should stay in sync with config/default.yaml content_types section.
 *     The enum provides compile-time type safety in Python code, while the YAML
 *     config defines runtime behavior (folders, templates, icons).
 * 
 *     TO ADD A NEW CONTENT TYPE:
 *     1. Add to config/default.yaml content_types section (defines folder, template, etc.)
 *     2. Add to this enum (e.g., PODCAST = "PODCAST") for type safety
 *     3. Create Obsidian template in vault's templates/ folder
 *     4. Create Jinja2 template in config/templates/
 *     5. Run `python scripts/setup/setup_vault.py` to create folders
 * 
 *     See config/default.yaml for the full content type registry with all configuration.
 */
export const ContentType = Object.freeze({
  PAPER: 'PAPER',
  ARTICLE: 'ARTICLE',
  BOOK: 'BOOK',
  CODE: 'CODE',
  IDEA: 'IDEA',
  VOICE_MEMO: 'VOICE_MEMO',
  CAREER: 'CAREER',
  PERSONAL: 'PERSONAL',
  PROJECT: 'PROJECT',
  REFLECTION: 'REFLECTION',
  NON_TECH: 'NON_TECH',
  DAILY: 'DAILY',
  CONCEPT: 'CONCEPT',
  EXERCISE: 'EXERCISE'
})

/**
 * Processing status for content items.
 * 
 *     Values must match the PostgreSQL contentstatus enum (uppercase).
 */
export const ProcessingStatus = Object.freeze({
  PENDING: 'PENDING',
  PROCESSING: 'PROCESSING',
  PROCESSED: 'PROCESSED',
  FAILED: 'FAILED'
})


/**
 * Set of code-based exercise types.
 * Use: CODE_EXERCISE_TYPES.has(exerciseType)
 */
export const CODE_EXERCISE_TYPES = new Set([
  ExerciseType.CODE_IMPLEMENT,
  ExerciseType.CODE_COMPLETE,
  ExerciseType.CODE_DEBUG,
  ExerciseType.CODE_REFACTOR,
  ExerciseType.CODE_EXPLAIN
])

/**
 * Set of text-based exercise types.
 * Use: TEXT_EXERCISE_TYPES.has(exerciseType)
 */
export const TEXT_EXERCISE_TYPES = new Set([
  ExerciseType.FREE_RECALL,
  ExerciseType.SELF_EXPLAIN,
  ExerciseType.WORKED_EXAMPLE,
  ExerciseType.APPLICATION,
  ExerciseType.COMPARE_CONTRAST,
  ExerciseType.TEACH_BACK
])

/**
 * Check if an exercise type is a code exercise.
 * @param {string} exerciseType - The exercise type value
 * @returns {boolean}
 */
export function isCodeExercise(exerciseType) {
  return CODE_EXERCISE_TYPES.has(exerciseType)
}

/**
 * Check if an exercise type is a text exercise.
 * @param {string} exerciseType - The exercise type value
 * @returns {boolean}
 */
export function isTextExercise(exerciseType) {
  return TEXT_EXERCISE_TYPES.has(exerciseType)
}
