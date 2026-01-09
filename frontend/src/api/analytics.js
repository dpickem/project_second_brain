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
 * ## Data Sources
 * Analytics are computed from:
 * - Review session results (via `reviewApi`)
 * - Practice session performance (via `practiceApi`)
 * - Card scheduling metadata (SM-2 algorithm data)
 * 
 * ## Related APIs
 * - `reviewApi` - Spaced repetition reviews that feed analytics
 * - `practiceApi` - Practice sessions that contribute to mastery
 * - `knowledgeApi` - Topic hierarchy for mastery aggregation
 * 
 * @see reviewApi - For reviewing cards and generating analytics data
 * @see practiceApi - For practice sessions that contribute to stats
 */

import { apiClient } from './client'

export const analyticsApi = {
  /**
   * Get overall analytics overview including summary statistics
   * @returns {Promise<{total_cards: number, total_reviews: number, avg_mastery: number, cards_due_today: number, streak_days: number}>} Overview statistics
   */
  getOverview: () => 
    apiClient.get('/api/analytics/overview').then(r => r.data),

  /**
   * Get daily stats for dashboard display
   * @returns {Promise<{date: string, reviews_completed: number, cards_learned: number, time_spent_minutes: number, accuracy: number}>} Daily statistics
   */
  getDailyStats: () => 
    apiClient.get('/api/analytics/daily').then(r => r.data),

  /**
   * Get mastery data for all topics
   * @returns {Promise<{topics: Array<{id: string, name: string, mastery: number, card_count: number, last_reviewed?: string}>}>} Mastery data for all topics
   */
  getMastery: () => 
    apiClient.get('/api/analytics/mastery').then(r => r.data),

  /**
   * Get mastery for a specific topic
   * @param {string} topicId - Topic identifier
   * @returns {Promise<{id: string, name: string, mastery: number, card_count: number, mastered_count: number, learning_count: number, new_count: number}>} Topic mastery details
   */
  getTopicMastery: (topicId) => 
    apiClient.get(`/api/analytics/mastery/${topicId}`).then(r => r.data),

  /**
   * Get weak spots (topics below mastery threshold)
   * @param {Object} [options] - Query options
   * @param {number} [options.limit=5] - Maximum number of weak spots to return
   * @param {number} [options.threshold=0.6] - Mastery threshold (0-1) below which topics are considered weak
   * @returns {Promise<{weak_spots: Array<{topic_id: string, topic_name: string, mastery: number, card_count: number, suggested_action: string}>}>} List of weak topics
   */
  getWeakSpots: ({ limit = 5, threshold = 0.6 } = {}) => 
    apiClient.get('/api/analytics/weak-spots', { 
      params: { limit, threshold } 
    }).then(r => r.data),

  /**
   * Get learning curve data over time
   * @param {string} [topicId] - Optional topic ID for specific topic curve (omit for global)
   * @param {Object} [options] - Query options
   * @param {number} [options.days=30] - Number of days of history to include
   * @returns {Promise<{data_points: Array<{date: string, mastery: number, reviews: number, accuracy: number}>}>} Learning curve data points
   */
  getLearningCurve: (topicId, { days = 30 } = {}) => {
    const path = topicId 
      ? `/api/analytics/learning-curve/${topicId}` 
      : '/api/analytics/learning-curve'
    return apiClient.get(path, { params: { days } }).then(r => r.data)
  },

  /**
   * Get practice history for activity heatmap visualization
   * @param {Object} [options] - Query options
   * @param {number} [options.weeks=52] - Number of weeks of history to return
   * @returns {Promise<{history: Array<{date: string, count: number, minutes: number}>}>} Daily practice activity data
   */
  getPracticeHistory: ({ weeks = 52 } = {}) => 
    apiClient.get('/api/analytics/practice-history', { 
      params: { weeks } 
    }).then(r => r.data),

  /**
   * Get current streak information
   * @returns {Promise<{current_streak: number, longest_streak: number, last_practice_date: string, streak_start_date?: string}>} Streak statistics
   */
  getStreak: () => 
    apiClient.get('/api/analytics/streak').then(r => r.data),

  /**
   * Get user's comprehensive learning statistics
   * @returns {Promise<{total_cards: number, total_reviews: number, total_time_minutes: number, avg_session_length: number, favorite_topics: Array<string>}>} User statistics
   */
  getStats: () => 
    apiClient.get('/api/analytics/stats').then(r => r.data),

  /**
   * Get topic hierarchy tree with mastery data at each level
   * @returns {Promise<{tree: Array<{id: string, name: string, mastery: number, children?: Array}>}>} Hierarchical topic tree
   */
  getTopicTree: () => 
    apiClient.get('/api/analytics/topic-tree').then(r => r.data),

  /**
   * Get retention metrics showing how well knowledge is retained over time
   * @returns {Promise<{overall_retention: number, retention_by_interval: Array<{interval_days: number, retention_rate: number}>, forgetting_curve: Array<{days: number, predicted_retention: number}>}>} Retention analytics
   */
  getRetention: () => 
    apiClient.get('/api/analytics/retention').then(r => r.data),
}

export default analyticsApi
