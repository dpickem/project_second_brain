/**
 * Analytics API Client
 * 
 * Functions for fetching learning analytics, mastery tracking, and progress data.
 * Provides insights into learning effectiveness and knowledge retention.
 * 
 * ## Use Cases
 * - **Dashboard Stats**: Overview metrics for the main dashboard
 * - **Mastery Tracking**: Per-topic mastery levels and progress over time
 * - **Weak Spot Detection**: Identify topics needing additional review
 * - **Learning Curves**: Visualize progress and retention over time
 * - **Practice History**: Activity heatmaps and streak tracking
 * - **Retention Analysis**: Understand how well knowledge is retained
 * 
 * ## Key Metrics
 * - **Mastery Score**: 0-100% representing knowledge confidence per topic
 * - **Retention Rate**: How well knowledge is retained over time
 * - **Streak Days**: Consecutive days of practice
 * - **Learning Curve**: Historical mastery progression
 * 
 * ## Data Breakdown
 * Analytics now include separate stats for:
 * - **Spaced Repetition Cards**: Flashcard-style recall practice with FSRS scheduling
 * - **Exercises**: Active learning activities (free recall, worked examples, code, etc.)
 * 
 * ## Data Sources
 * Analytics are computed from:
 * - Review session results (via `reviewApi`)
 * - Practice session performance (via `practiceApi`)
 * - Card scheduling metadata (FSRS algorithm data)
 * - Exercise attempts and scores
 * 
 * ## Related APIs
 * - `reviewApi` - Spaced repetition reviews that feed analytics
 * - `practiceApi` - Practice sessions that contribute to mastery
 * - `knowledgeApi` - Topic hierarchy for mastery aggregation
 * 
 * @see reviewApi - For reviewing cards and generating analytics data
 * @see practiceApi - For practice sessions that contribute to stats
 */

import { typedApi } from './typed-client'

export const analyticsApi = {
  /**
   * Get overall analytics overview including summary statistics
   * 
   * Returns comprehensive stats including separate breakdowns for:
   * - Spaced repetition cards (total, mastered, learning, new, reviews)
   * - Exercises (total, completed, mastered, attempts, avg score)
   * 
   * @returns {Promise<{
   *   overall_mastery: number,
   *   total_cards: number,
   *   cards_mastered: number,
   *   cards_learning: number,
   *   cards_new: number,
   *   spaced_rep_cards_total: number,
   *   spaced_rep_cards_mastered: number,
   *   spaced_rep_cards_learning: number,
   *   spaced_rep_cards_new: number,
   *   spaced_rep_reviews_total: number,
   *   exercises_total: number,
   *   exercises_completed: number,
   *   exercises_mastered: number,
   *   exercises_attempts_total: number,
   *   exercises_avg_score: number,
   *   streak_days: number,
   *   total_practice_time_hours: number,
   *   topics: Array<{topic_path: string, mastery_score: number, practice_count: number}>
   * }>} Overview statistics with separate card and exercise breakdowns
   */
  getOverview: () => 
    typedApi.GET('/api/analytics/overview').then(r => r.data),

  /**
   * Get daily stats for dashboard display
   * @returns {Promise<{date: string, reviews_completed: number, cards_learned: number, time_spent_minutes: number, accuracy: number}>} Daily statistics
   */
  getDailyStats: () => 
    typedApi.GET('/api/analytics/daily').then(r => r.data),

  /**
   * Get mastery data for all topics
   * @returns {Promise<{topics: Array<{id: string, name: string, mastery: number, card_count: number, last_reviewed?: string}>}>} Mastery data for all topics
   */
  getMastery: () => 
    typedApi.GET('/api/analytics/mastery').then(r => r.data),

  /**
   * Get mastery for a specific topic
   * @param {string} topicId - Topic identifier
   * @returns {Promise<{id: string, name: string, mastery: number, card_count: number, mastered_count: number, learning_count: number, new_count: number}>} Topic mastery details
   */
  getTopicMastery: (topicId) => 
    typedApi.GET('/api/analytics/mastery/{topic_id}', {
      params: { path: { topic_id: topicId } }
    }).then(r => r.data),

  /**
   * Get weak spots (topics below mastery threshold)
   * @param {Object} [options] - Query options
   * @param {number} [options.limit=5] - Maximum number of weak spots to return
   * @param {number} [options.threshold=0.6] - Mastery threshold (0-1) below which topics are considered weak
   * @returns {Promise<{weak_spots: Array<{topic_id: string, topic_name: string, mastery: number, card_count: number, suggested_action: string}>}>} List of weak topics
   */
  getWeakSpots: ({ limit = 5, threshold = 0.6 } = {}) => 
    typedApi.GET('/api/analytics/weak-spots', { 
      params: { query: { limit, threshold } } 
    }).then(r => r.data),

  /**
   * Get learning curve data over time
   * @param {string} [topicId] - Optional topic ID for specific topic curve (omit for global)
   * @param {Object} [options] - Query options
   * @param {number} [options.days=30] - Number of days of history to include
   * @returns {Promise<{data_points: Array<{date: string, mastery: number, reviews: number, accuracy: number}>}>} Learning curve data points
   */
  getLearningCurve: (topicId, { days = 30 } = {}) => {
    if (topicId) {
      return typedApi.GET('/api/analytics/learning-curve/{topic_id}', {
        params: { path: { topic_id: topicId }, query: { days } }
      }).then(r => r.data)
    }
    return typedApi.GET('/api/analytics/learning-curve', { 
      params: { query: { days } } 
    }).then(r => r.data)
  },

  /**
   * Get practice history for activity heatmap visualization
   * @param {Object} [options] - Query options
   * @param {number} [options.weeks=52] - Number of weeks of history to return
   * @returns {Promise<{history: Array<{date: string, count: number, minutes: number}>}>} Daily practice activity data
   */
  getPracticeHistory: ({ weeks = 52 } = {}) => 
    typedApi.GET('/api/analytics/practice-history', { 
      params: { query: { weeks } } 
    }).then(r => r.data),

  /**
   * Get current streak information
   * @returns {Promise<{current_streak: number, longest_streak: number, last_practice_date: string, streak_start_date?: string}>} Streak statistics
   */
  getStreak: () => 
    typedApi.GET('/api/analytics/streak').then(r => r.data),

  /**
   * Get user's comprehensive learning statistics
   * @returns {Promise<{total_cards: number, total_reviews: number, total_time_minutes: number, avg_session_length: number, favorite_topics: Array<string>}>} User statistics
   */
  getStats: () => 
    typedApi.GET('/api/analytics/stats').then(r => r.data),

  /**
   * Get topic hierarchy tree with mastery data at each level
   * @returns {Promise<{tree: Array<{id: string, name: string, mastery: number, children?: Array}>}>} Hierarchical topic tree
   */
  getTopicTree: () => 
    typedApi.GET('/api/analytics/topic-tree').then(r => r.data),

  /**
   * Get retention metrics showing how well knowledge is retained over time
   * @returns {Promise<{overall_retention: number, retention_by_interval: Array<{interval_days: number, retention_rate: number}>, forgetting_curve: Array<{days: number, predicted_retention: number}>}>} Retention analytics
   */
  getRetention: () => 
    typedApi.GET('/api/analytics/retention').then(r => r.data),

  /**
   * Get activity data for the learning chart
   * 
   * Returns daily activity data including:
   * - Card reviews (spaced repetition)
   * - Exercise attempts
   * - Practice time
   * - Average exercise scores
   * 
   * @param {string} timeRange - Time range string like '7d', '30d', '90d', '365d'
   * @returns {Promise<{data: Array<{
   *   date: string,
   *   cardsReviewed: number,
   *   exercisesAttempted: number,
   *   practiceTime: number,
   *   exerciseTime: number,
   *   exerciseScore: number|null
   * }>}>} Activity data with card and exercise metrics
   */
  getActivityData: (timeRange) => {
    // Parse days from timeRange string (e.g., '30d' -> 30)
    const days = parseInt(timeRange.replace('d', ''), 10) || 30
    return typedApi.GET('/api/analytics/learning-curve', { params: { query: { days } } })
      .then(r => ({
        data: (r.data?.data_points || []).map(point => ({
          date: point.date,
          // Card activity
          cardsReviewed: point.cards_reviewed || 0,
          cardTime: Math.round(point.card_time_minutes || 0),
          // Exercise activity
          exercisesAttempted: point.exercises_attempted || 0,
          exerciseScore: point.exercise_score != null ? Math.round(point.exercise_score) : null,
          exerciseTime: Math.round(point.exercise_time_minutes || 0),
          // Total time (sum of card + exercise time)
          practiceTime: Math.round(point.time_minutes || 0),
        }))
      }))
  },
}

export default analyticsApi
