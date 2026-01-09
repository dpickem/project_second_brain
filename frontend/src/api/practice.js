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

import { apiClient } from './client'

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
    apiClient.post('/api/practice/session', {
      topic_filter: params.topicFilter,
      duration_minutes: params.durationMinutes || 15,
      exercise_types: params.exerciseTypes,
      difficulty: params.difficulty,
    }).then(r => r.data),

  /**
   * Get an existing practice session by ID
   * @param {string} sessionId - Unique session identifier
   * @returns {Promise<{session_id: string, status: 'active'|'completed'|'abandoned', exercises: Array, current_index: number, started_at: string, progress: number}>} Session details with current state
   */
  getSession: (sessionId) => 
    apiClient.get(`/api/practice/session/${sessionId}`).then(r => r.data),

  /**
   * Submit an attempt for an exercise
   * @param {Object} data - Attempt data
   * @param {string} data.exerciseId - Exercise identifier
   * @param {string} data.response - User's response to the exercise
   * @param {number} data.timeSpentSeconds - Time spent on the exercise in seconds
   * @returns {Promise<{attempt_id: string, correct: boolean, correct_answer?: string, explanation?: string, points_earned: number, feedback: string}>} Attempt result with feedback
   */
  submitAttempt: ({ exerciseId, response, timeSpentSeconds }) => 
    apiClient.post('/api/practice/submit', {
      exercise_id: exerciseId,
      response,
      time_spent_seconds: timeSpentSeconds,
    }).then(r => r.data),

  /**
   * Update confidence rating for an attempt after seeing the answer
   * @param {string} attemptId - Attempt identifier
   * @param {number} confidenceAfter - Confidence rating from 1 (not confident) to 5 (very confident)
   * @returns {Promise<{attempt_id: string, confidence_after: number, updated_at: string}>} Updated attempt confirmation
   */
  updateConfidence: (attemptId, confidenceAfter) => 
    apiClient.patch(`/api/practice/attempt/${attemptId}/confidence`, {
      confidence_after: confidenceAfter,
    }).then(r => r.data),

  /**
   * Generate a new exercise on demand
   * @param {Object} params - Exercise parameters
   * @param {string} params.topicId - Topic ID to generate exercise for
   * @param {string} params.exerciseType - Type of exercise to generate
   * @param {string} [params.difficulty] - Difficulty level ('easy', 'medium', 'hard')
   * @returns {Promise<{id: string, type: string, question: string, options?: Array<string>, topic_id: string, difficulty: string}>} Generated exercise
   */
  generateExercise: (params) => 
    apiClient.post('/api/practice/generate', {
      topic_id: params.topicId,
      exercise_type: params.exerciseType,
      difficulty: params.difficulty,
    }).then(r => r.data),

  /**
   * Get summary statistics for a completed session
   * @param {string} sessionId - Unique session identifier
   * @returns {Promise<{session_id: string, total_exercises: number, correct_count: number, accuracy: number, time_spent_seconds: number, points_earned: number, topics_practiced: Array<{id: string, name: string, accuracy: number}>}>} Session summary statistics
   */
  getSessionSummary: (sessionId) => 
    apiClient.get(`/api/practice/session/${sessionId}/summary`).then(r => r.data),

  /**
   * End a session early before completing all exercises
   * @param {string} sessionId - Unique session identifier
   * @returns {Promise<{session_id: string, status: 'completed', ended_at: string, exercises_completed: number}>} Session end confirmation
   */
  endSession: (sessionId) => 
    apiClient.post(`/api/practice/session/${sessionId}/end`).then(r => r.data),

  /**
   * Get list of available exercise types with descriptions
   * @returns {Promise<{types: Array<{id: string, name: string, description: string, supported_content_types: Array<string>}>}>} Available exercise types
   */
  getExerciseTypes: () => 
    apiClient.get('/api/practice/exercise-types').then(r => r.data),

  /**
   * Get paginated practice session history
   * @param {Object} [options] - Query options
   * @param {number} [options.limit=10] - Maximum number of sessions to return
   * @param {number} [options.offset=0] - Number of sessions to skip for pagination
   * @returns {Promise<{sessions: Array<{id: string, date: string, duration_minutes: number, exercises_completed: number, accuracy: number}>, total: number}>} Practice history
   */
  getHistory: ({ limit = 10, offset = 0 } = {}) => 
    apiClient.get('/api/practice/history', { 
      params: { limit, offset } 
    }).then(r => r.data),

  /**
   * Get personalized topic recommendations for practice
   * @returns {Promise<{recommendations: Array<{topic_id: string, topic_name: string, reason: string, priority: 'high'|'medium'|'low', estimated_minutes: number}>}>} Recommended practice topics
   */
  getRecommendations: () => 
    apiClient.get('/api/practice/recommendations').then(r => r.data),

  /**
   * Skip an exercise without submitting an answer
   * @param {string} exerciseId - Exercise identifier to skip
   * @returns {Promise<{exercise_id: string, skipped: boolean, correct_answer?: string}>} Skip confirmation with optional answer reveal
   */
  skipExercise: (exerciseId) => 
    apiClient.post(`/api/practice/exercise/${exerciseId}/skip`).then(r => r.data),

  /**
   * Get progressive hints for an exercise
   * @param {string} exerciseId - Exercise identifier
   * @returns {Promise<{exercise_id: string, hints: Array<{level: number, text: string}>, hints_used: number}>} Available hints for the exercise
   */
  getHints: (exerciseId) => 
    apiClient.get(`/api/practice/exercise/${exerciseId}/hints`).then(r => r.data),
}

export default practiceApi
