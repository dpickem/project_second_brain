/**
 * Review API Client
 * 
 * Functions for spaced repetition review using the SM-2 algorithm.
 * This API manages flashcard scheduling, rating, and progress tracking.
 * 
 * ## Use Cases
 * - **Daily Reviews**: Get cards due for review and rate them
 * - **Progress Tracking**: Monitor card states, intervals, and ease factors
 * - **Card Management**: Suspend, reset, or get details for specific cards
 * - **Statistics**: View review performance metrics
 * 
 * ## SM-2 Algorithm
 * The SuperMemo 2 algorithm schedules cards based on recall quality:
 * 
 * | Rating | Quality    | Effect on Interval                    |
 * |--------|------------|---------------------------------------|
 * | 1      | Again      | Reset to learning phase               |
 * | 2      | Hard       | Small increase, decrease ease factor  |
 * | 3      | Good       | Normal increase based on ease factor  |
 * | 4      | Easy       | Larger increase, boost ease factor    |
 * 
 * ## Card States
 * - **New**: Never reviewed, awaiting first exposure
 * - **Learning**: Recently introduced, short intervals
 * - **Review**: Graduated, following SM-2 scheduling
 * - **Suspended**: Temporarily removed from review queue
 * 
 * ## Review vs Practice
 * Use `reviewApi` for:
 * - Flashcard-style recall with front/back cards
 * - SM-2 spaced repetition scheduling
 * - Long-term retention optimization
 * 
 * Use `practiceApi` for:
 * - Interactive exercises (fill-blank, multiple choice)
 * - Topic-focused practice sessions
 * - Immediate comprehension testing
 * 
 * @see practiceApi - For interactive practice exercises
 * @see analyticsApi - For learning analytics computed from reviews
 */

import { typedApi } from './typed-client'

export const reviewApi = {
  /**
   * Get cards due for review with optional filtering
   * @param {Object} [options] - Query options
   * @param {number} [options.limit=50] - Maximum number of cards to return
   * @param {string} [options.topic] - Filter by topic ID
   * @param {string} [options.cardType] - Filter by card type (e.g., 'basic', 'cloze', 'concept')
   * @returns {Promise<{cards: Array<{id: string, front: string, back: string, topic_id: string, card_type: string, interval_days: number, ease_factor: number, due_date: string}>, total_due: number}>} Due cards with scheduling metadata
   */
  getDueCards: ({ limit = 50, topic, cardType } = {}) => {
    const params = { limit }
    if (topic) params.topic = topic
    if (cardType) params.card_type = cardType
    
    return typedApi.GET('/api/review/due', { 
      params: { query: params } 
    }).then(r => r.data)
  },

  /**
   * Get count of cards due for review
   * @returns {Promise<{due_count: number, new_count: number, learning_count: number, review_count: number}>} Counts by card state
   */
  getDueCount: () => 
    typedApi.GET('/api/review/due/count').then(r => r.data),

  /**
   * Rate a card after review using SM-2 rating scale
   * @param {Object} data - Rating data
   * @param {string} data.cardId - Card identifier
   * @param {number} data.rating - Rating (1: Again, 2: Hard, 3: Good, 4: Easy)
   * @param {number} data.timeSpentSeconds - Time spent viewing the card in seconds
   * @returns {Promise<{card_id: string, next_due: string, new_interval_days: number, new_ease_factor: number, repetitions: number}>} Updated card scheduling
   */
  rateCard: ({ cardId, rating, timeSpentSeconds }) => 
    typedApi.POST('/api/review/rate', {
      body: {
        card_id: cardId,
        rating,
        time_spent_seconds: timeSpentSeconds,
      }
    }).then(r => r.data),

  /**
   * Evaluate a typed answer for a card using LLM (active recall mode)
   * @param {Object} data - Evaluation data
   * @param {string} data.cardId - Card identifier
   * @param {string} data.userAnswer - User's typed answer
   * @returns {Promise<{card_id: number, rating: number, is_correct: boolean, feedback: string, key_points_covered: string[], key_points_missed: string[], expected_answer: string}>} Evaluation result with suggested rating
   */
  evaluateAnswer: ({ cardId, userAnswer }) =>
    typedApi.POST('/api/review/evaluate', {
      body: {
        card_id: cardId,
        user_answer: userAnswer,
      }
    }).then(r => r.data),

  /**
   * Get a specific card by ID
   * @param {string} cardId - Card identifier
   * @returns {Promise<{id: string, front: string, back: string, topic_id: string, topic_name: string, card_type: string, tags: Array<string>, created_at: string, interval_days: number, ease_factor: number, due_date: string, review_count: number}>} Full card details
   */
  getCard: (cardId) => 
    typedApi.GET('/api/review/card/{card_id}', {
      params: { path: { card_id: cardId } }
    }).then(r => r.data),

  /**
   * Get all cards for a specific topic
   * @param {string} topicId - Topic identifier
   * @param {Object} [options] - Query options
   * @param {number} [options.limit=50] - Maximum number of cards to return
   * @param {boolean} [options.includeNotDue=false] - Include cards not yet due for review
   * @returns {Promise<{cards: Array<{id: string, front: string, back: string, due_date: string, is_due: boolean}>, total: number}>} Cards for the topic
   */
  getCardsByTopic: (topicId, { limit = 50, includeNotDue = false } = {}) => 
    typedApi.GET('/api/review/topic/{topic_id}', { 
      params: { 
        path: { topic_id: topicId },
        query: { limit, include_not_due: includeNotDue } 
      } 
    }).then(r => r.data),

  /**
   * Get comprehensive review statistics
   * @returns {Promise<{total_cards: number, total_reviews: number, avg_ease_factor: number, avg_interval: number, retention_rate: number, reviews_today: number, streak_days: number}>} Review statistics
   */
  getStats: () => 
    typedApi.GET('/api/review/stats').then(r => r.data),

  /**
   * Get predicted next intervals for each rating option
   * @param {string} cardId - Card identifier
   * @returns {Promise<{card_id: string, predictions: {again: {interval: string, ease: number}, hard: {interval: string, ease: number}, good: {interval: string, ease: number}, easy: {interval: string, ease: number}}}>} Predicted intervals for each rating
   */
  getPredictedIntervals: (cardId) => 
    typedApi.GET('/api/review/card/{card_id}/predict', {
      params: { path: { card_id: cardId } }
    }).then(r => r.data),

  /**
   * Bulk rate multiple cards at once
   * @param {Array<{cardId: string, rating: number, timeSpentSeconds: number}>} ratings - Array of rating objects
   * @returns {Promise<{rated_count: number, results: Array<{card_id: string, success: boolean, next_due?: string}>}>} Bulk rating results
   */
  bulkRate: (ratings) => 
    typedApi.POST('/api/review/rate/bulk', { 
      body: { ratings } 
    }).then(r => r.data),

  /**
   * Suspend a card to remove it from the review queue
   * @param {string} cardId - Card identifier
   * @returns {Promise<{card_id: string, suspended: boolean, suspended_at: string}>} Suspension confirmation
   */
  suspendCard: (cardId) => 
    typedApi.POST('/api/review/card/{card_id}/suspend', {
      params: { path: { card_id: cardId } }
    }).then(r => r.data),

  /**
   * Unsuspend a card to add it back to the review queue
   * @param {string} cardId - Card identifier
   * @returns {Promise<{card_id: string, suspended: boolean, due_date: string}>} Unsuspension confirmation with new due date
   */
  unsuspendCard: (cardId) => 
    typedApi.POST('/api/review/card/{card_id}/unsuspend', {
      params: { path: { card_id: cardId } }
    }).then(r => r.data),

  /**
   * Reset card progress to initial state (new card)
   * @param {string} cardId - Card identifier
   * @returns {Promise<{card_id: string, reset: boolean, new_interval: number, new_ease_factor: number, new_due_date: string}>} Reset confirmation
   */
  resetCard: (cardId) => 
    typedApi.POST('/api/review/card/{card_id}/reset', {
      params: { path: { card_id: cardId } }
    }).then(r => r.data),

  /**
   * Generate spaced repetition cards for a topic on-demand
   * @param {Object} params - Generation parameters
   * @param {string} params.topic - Topic path (e.g., 'ml/transformers')
   * @param {number} [params.count=10] - Number of cards to generate
   * @param {string} [params.difficulty='mixed'] - Difficulty: easy, medium, hard, mixed
   * @returns {Promise<{generated_count: number, total_cards: number, topic: string}>} Generation result
   */
  generateCards: ({ topic, count = 10, difficulty = 'mixed' }) =>
    typedApi.POST('/api/review/generate', { 
      body: { topic, count, difficulty } 
    }).then(r => r.data),

  /**
   * Ensure minimum cards exist for a topic, generating if needed
   * @param {string} topic - Topic path
   * @param {number} [minimum=5] - Minimum cards required
   * @returns {Promise<{generated_count: number, total_cards: number, topic: string}>} Ensured result
   */
  ensureCards: (topic, minimum = 5) =>
    typedApi.POST('/api/review/ensure-cards', { 
      params: { query: { topic, minimum } }
    }).then(r => r.data),
}

export default reviewApi
