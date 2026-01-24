/**
 * Practice API Client
 * 
 * Functions for interactive practice sessions with generated exercises.
 * Unlike flashcard reviews, practice sessions offer diverse question types
 * for active learning and comprehension testing.
 * 
 * ## Use Cases
 * - **Practice Sessions**: Timed sessions with mixed exercise types
 * - **Exercise Generation**: On-demand questions for specific topics
 * - **Progress Tracking**: Session history, accuracy, and recommendations
 * - **Adaptive Difficulty**: Exercises adjust to your skill level
 * 
 * ## Exercise Types
 * - **Fill in the Blank**: Complete sentences with missing terms
 * - **Multiple Choice**: Select the correct answer from options
 * - **Free Response**: Open-ended answers evaluated by AI
 * - **Concept Matching**: Connect related ideas
 * - **True/False**: Evaluate statement accuracy
 * 
 * ## Session Flow
 * ```
 * Create Session → Get Exercises → Submit Attempts → Get Summary
 *       ↓              ↓                ↓               ↓
 * Set parameters  Work through     Get feedback    View results
 * ```
 * 
 * ## Practice vs Review
 * Use `practiceApi` for:
 * - Interactive exercises (fill-blank, multiple choice)
 * - Topic-focused practice sessions
 * - Immediate comprehension testing
 * - Hints and explanations
 * 
 * Use `reviewApi` for:
 * - Flashcard-style recall with front/back cards
 * - SM-2 spaced repetition scheduling
 * - Long-term retention optimization
 * 
 * @see reviewApi - For flashcard-based spaced repetition
 * @see analyticsApi - For practice statistics and progress
 * @see assistantApi - For AI-generated quizzes
 */

import { typedApi } from './typed-client'

export const practiceApi = {
  /**
   * Create a new practice session with specified parameters
   * @param {Object} params - Session parameters
   * @param {string} [params.topicFilter] - Optional topic ID to focus the session on
   * @param {number} [params.durationMinutes=15] - Target session duration in minutes
   * @param {string[]} [params.exerciseTypes] - Types of exercises to include (e.g., ['fill_blank', 'multiple_choice'])
   * @param {string} [params.difficulty] - Difficulty level ('easy', 'medium', 'hard', 'adaptive')
   * @returns {Promise<{session_id: string, exercises: Array<{id: string, type: string, question: string, topic_id: string}>, total_exercises: number, estimated_minutes: number}>} Created session with exercises
   */
  createSession: (params) => 
    typedApi.POST('/api/practice/session', {
      body: {
        topic_filter: params.topicFilter,
        duration_minutes: params.durationMinutes || 15,
        // Practice page is for exercises only (cards are on /review page)
        content_mode: 'exercises_only',
        // Map reuseExercises boolean to exercise_source enum value
        // true = existing_only (no generation), false = generate_new
        exercise_source: params.reuseExercises === false ? 'generate_new' : 'existing_only',
      }
    }).then(r => r.data),

  /**
   * Get an existing practice session by ID
   * @param {string} sessionId - Unique session identifier
   * @returns {Promise<{session_id: string, status: 'active'|'completed'|'abandoned', exercises: Array, current_index: number, started_at: string, progress: number}>} Session details with current state
   */
  getSession: (sessionId) => 
    typedApi.GET('/api/practice/session/{session_id}', {
      params: { path: { session_id: sessionId } }
    }).then(r => r.data),

  /**
   * Submit an attempt for an exercise
   * @param {Object} data - Attempt data
   * @param {string} data.exerciseId - Exercise identifier
   * @param {string} data.response - User's response to the exercise
   * @param {number} data.timeSpentSeconds - Time spent on the exercise in seconds
   * @returns {Promise<{attempt_id: string, correct: boolean, correct_answer?: string, explanation?: string, points_earned: number, feedback: string}>} Attempt result with feedback
   */
  submitAttempt: ({ exerciseId, response, responseCode, timeSpentSeconds }) => 
    typedApi.POST('/api/practice/submit', {
      body: {
        exercise_id: exerciseId,
        response,
        response_code: responseCode,
        time_spent_seconds: timeSpentSeconds,
      }
    }).then(r => r.data),

  /**
   * Update confidence rating for an attempt after seeing the answer
   * @param {string} attemptId - Attempt identifier
   * @param {number} confidenceAfter - Confidence rating from 1 (not confident) to 5 (very confident)
   * @returns {Promise<{attempt_id: string, confidence_after: number, updated_at: string}>} Updated attempt confirmation
   */
  updateConfidence: (attemptId, confidenceAfter) => 
    typedApi.PATCH('/api/practice/attempt/{attempt_id}/confidence', {
      params: { path: { attempt_id: attemptId } },
      body: { confidence_after: confidenceAfter },
    }).then(r => r.data),

  /**
   * Generate a new exercise on demand
   * @param {Object} params - Exercise parameters
   * @param {string} params.topicId - Topic to generate exercise for
   * @param {string} params.exerciseType - Type of exercise to generate
   * @param {string} [params.difficulty] - Difficulty level ('foundational', 'intermediate', 'advanced')
   * @returns {Promise<{id: number, exercise_type: string, prompt: string, topic: string, difficulty: string}>} Generated exercise
   */
  generateExercise: (params) => 
    typedApi.POST('/api/practice/exercise/generate', {
      body: {
        topic: params.topicId, // Backend expects 'topic' not 'topic_id'
        exercise_type: params.exerciseType,
        difficulty: params.difficulty,
      }
    }).then(r => r.data),

  /**
   * List all exercises with optional filtering
   * @param {Object} [options] - Query options
   * @param {string} [options.topic] - Filter by topic path
   * @param {string} [options.exerciseType] - Filter by exercise type
   * @param {string} [options.difficulty] - Filter by difficulty
   * @param {number} [options.limit=50] - Maximum exercises to return
   * @param {number} [options.offset=0] - Offset for pagination
   * @returns {Promise<Array<{id: string, exercise_type: string, topic: string, difficulty: string, prompt: string}>>} List of exercises
   */
  listExercises: ({ topic, exerciseType, difficulty, limit = 50, offset = 0 } = {}) => 
    typedApi.GET('/api/practice/exercises', { 
      params: { 
        query: { 
          topic, 
          exercise_type: exerciseType, 
          difficulty,
          limit, 
          offset 
        } 
      } 
    }).then(r => r.data),

  /**
   * Get summary statistics for a completed session
   * @param {string} sessionId - Unique session identifier
   * @returns {Promise<{session_id: string, total_exercises: number, correct_count: number, accuracy: number, time_spent_seconds: number, points_earned: number, topics_practiced: Array<{id: string, name: string, accuracy: number}>}>} Session summary statistics
   */
  getSessionSummary: (sessionId) => 
    typedApi.GET('/api/practice/session/{session_id}/summary', {
      params: { path: { session_id: sessionId } }
    }).then(r => r.data),

  /**
   * End a session early before completing all exercises
   * @param {string} sessionId - Unique session identifier
   * @returns {Promise<{session_id: string, status: 'completed', ended_at: string, exercises_completed: number}>} Session end confirmation
   */
  endSession: (sessionId) => 
    typedApi.POST('/api/practice/session/{session_id}/end', {
      params: { path: { session_id: sessionId } }
    }).then(r => r.data),

  /**
   * Get list of available exercise types with descriptions
   * @returns {Promise<{types: Array<{id: string, name: string, description: string, supported_content_types: Array<string>}>}>} Available exercise types
   */
  getExerciseTypes: () => 
    typedApi.GET('/api/practice/exercise-types').then(r => r.data),

  /**
   * Get paginated practice session history
   * @param {Object} [options] - Query options
   * @param {number} [options.limit=10] - Maximum number of sessions to return
   * @param {number} [options.offset=0] - Number of sessions to skip for pagination
   * @returns {Promise<{sessions: Array<{id: string, date: string, duration_minutes: number, exercises_completed: number, accuracy: number}>, total: number}>} Practice history
   */
  getHistory: ({ limit = 10, offset = 0 } = {}) => 
    typedApi.GET('/api/practice/history', { 
      params: { query: { limit, offset } } 
    }).then(r => r.data),

  /**
   * Get personalized topic recommendations for practice
   * @returns {Promise<{recommendations: Array<{topic_id: string, topic_name: string, reason: string, priority: 'high'|'medium'|'low', estimated_minutes: number}>}>} Recommended practice topics
   */
  getRecommendations: () => 
    typedApi.GET('/api/practice/recommendations').then(r => r.data),

  /**
   * Skip an exercise without submitting an answer
   * @param {string} exerciseId - Exercise identifier to skip
   * @returns {Promise<{exercise_id: string, skipped: boolean, correct_answer?: string}>} Skip confirmation with optional answer reveal
   */
  skipExercise: (exerciseId) => 
    typedApi.POST('/api/practice/exercise/{exercise_id}/skip', {
      params: { path: { exercise_id: exerciseId } }
    }).then(r => r.data),

  /**
   * Get progressive hints for an exercise
   * @param {string} exerciseId - Exercise identifier
   * @returns {Promise<{exercise_id: string, hints: Array<{level: number, text: string}>, hints_used: number}>} Available hints for the exercise
   */
  getHints: (exerciseId) => 
    typedApi.GET('/api/practice/exercise/{exercise_id}/hints', {
      params: { path: { exercise_id: exerciseId } }
    }).then(r => r.data),
}

export default practiceApi
