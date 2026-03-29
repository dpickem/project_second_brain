/**
 * Ingestion API Client
 *
 * Functions for browsing the ingestion queue, checking item status,
 * and fetching detailed processing information.
 *
 * ## Related APIs
 * - Use `captureApi` for submitting new content (text, URLs, files)
 * - This module is for monitoring and inspecting ingestion status
 *
 * @see captureApi - To submit new captures
 */

import { apiClient } from './client'

export const ingestionApi = {
  /**
   * List content items in the ingestion queue with filtering and pagination.
   * @param {Object} [options] - Query options
   * @param {string} [options.status] - Filter by status (pending, processing, processed, failed)
   * @param {string} [options.content_type] - Filter by content type
   * @param {number} [options.limit=50] - Maximum items to return
   * @param {number} [options.offset=0] - Pagination offset
   * @returns {Promise<{items: Array, total: number, limit: number, offset: number, has_more: boolean}>}
   */
  getQueueItems: (options = {}) =>
    apiClient
      .get('/api/ingestion/queue/combined', { params: options })
      .then((r) => r.data),

  /**
   * Get detailed status for a single content item.
   * @param {string} contentUuid - UUID of the content item
   * @returns {Promise<Object>} Full item details including processing stages and errors
   */
  getQueueItemDetail: (contentUuid) =>
    apiClient
      .get(`/api/ingestion/queue/${contentUuid}/detail`)
      .then((r) => r.data),

  /**
   * Get Celery queue statistics (active, queued, scheduled task counts).
   * @returns {Promise<Object>} Queue statistics
   */
  getQueueStats: () =>
    apiClient.get('/api/ingestion/queue/stats').then((r) => r.data),

  /**
   * Get ingestion status for a specific content item.
   * @param {string} contentId - UUID of the content item
   * @returns {Promise<Object>} Status information
   */
  getStatus: (contentId) =>
    apiClient.get(`/api/ingestion/status/${contentId}`).then((r) => r.data),

  /**
   * Trigger a Raindrop.io sync.
   * @param {Object} [options] - Sync options
   * @param {number} [options.since_days=1] - Sync items from last N days
   * @param {number} [options.limit] - Maximum items to sync
   * @returns {Promise<Object>} Sync status
   */
  triggerRaindropSync: (options = {}) =>
    apiClient
      .post('/api/ingestion/raindrop/sync', options)
      .then((r) => r.data),

  /**
   * Trigger a GitHub starred repos sync.
   * @param {Object} [options] - Sync options
   * @param {number} [options.limit=50] - Maximum repos to sync
   * @returns {Promise<Object>} Sync status
   */
  triggerGithubSync: (options = {}) =>
    apiClient.post('/api/ingestion/github/sync', options).then((r) => r.data),
}

export default ingestionApi
