/**
 * Follow-up Tasks API Client
 * 
 * Functions for interacting with follow-up tasks generated during content processing.
 * Follow-up tasks are actionable items that help users engage more deeply with content.
 * 
 * ## Use Cases
 * - **Task Listing**: View all pending or completed follow-up tasks
 * - **Task Management**: Mark tasks as completed or uncompleted
 * - **Filtering**: Filter tasks by priority, type, content, or status
 * 
 * ## Task Types
 * - `research`: Further investigation tasks
 * - `practice`: Hands-on practice tasks
 * - `connect`: Tasks to relate to other knowledge
 * - `apply`: Application of learned concepts
 * - `review`: Review and reinforcement tasks
 * 
 * ## Priority Levels
 * - `high`: Fundamental to understanding, should do soon
 * - `medium`: Would deepen understanding
 * - `low`: Nice to have, optional enrichment
 * 
 * @module api/followups
 */

import { apiClient } from './client'

export const followupsApi = {
  /**
   * List follow-up tasks with optional filtering
   * @param {Object} [options] - Query options
   * @param {number} [options.contentId] - Filter by specific content ID
   * @param {boolean} [options.completed] - Filter by completion status
   * @param {string} [options.priority] - Filter by priority: 'high', 'medium', 'low'
   * @param {string} [options.taskType] - Filter by task type: 'research', 'practice', 'connect', 'apply', 'review'
   * @param {number} [options.limit=100] - Maximum number of tasks to return
   * @param {number} [options.offset=0] - Offset for pagination
   * @returns {Promise<{total: number, tasks: Array}>} List of follow-up tasks
   */
  list: ({ contentId, completed, priority, taskType, limit = 100, offset = 0 } = {}) => {
    const params = new URLSearchParams()
    if (contentId !== undefined) params.set('content_id', contentId)
    if (completed !== undefined) params.set('completed', completed)
    if (priority) params.set('priority', priority)
    if (taskType) params.set('task_type', taskType)
    params.set('limit', limit)
    params.set('offset', offset)
    
    return apiClient.get(`/api/processing/followups?${params.toString()}`).then(r => r.data)
  },

  /**
   * Get pending (uncompleted) follow-up tasks
   * @param {Object} [options] - Query options
   * @param {number} [options.contentId] - Filter by specific content ID
   * @param {string} [options.priority] - Filter by priority
   * @param {number} [options.limit=100] - Maximum number of tasks
   * @returns {Promise<{total: number, tasks: Array}>} List of pending tasks
   */
  getPending: ({ contentId, priority, limit = 100 } = {}) => 
    followupsApi.list({ contentId, completed: false, priority, limit }),

  /**
   * Get completed follow-up tasks
   * @param {Object} [options] - Query options
   * @param {number} [options.contentId] - Filter by specific content ID
   * @param {number} [options.limit=100] - Maximum number of tasks
   * @returns {Promise<{total: number, tasks: Array}>} List of completed tasks
   */
  getCompleted: ({ contentId, limit = 100 } = {}) =>
    followupsApi.list({ contentId, completed: true, limit }),

  /**
   * Mark a follow-up task as completed
   * @param {string} taskId - UUID of the follow-up task
   * @returns {Promise<{id: string, completed: boolean, completed_at: string|null, message: string}>}
   */
  complete: (taskId) =>
    apiClient.patch(`/api/processing/followups/${taskId}`, { completed: true }).then(r => r.data),

  /**
   * Mark a follow-up task as uncompleted (reopen)
   * @param {string} taskId - UUID of the follow-up task
   * @returns {Promise<{id: string, completed: boolean, completed_at: string|null, message: string}>}
   */
  uncomplete: (taskId) =>
    apiClient.patch(`/api/processing/followups/${taskId}`, { completed: false }).then(r => r.data),

  /**
   * Toggle the completion status of a follow-up task
   * @param {string} taskId - UUID of the follow-up task
   * @param {boolean} completed - New completion status
   * @returns {Promise<{id: string, completed: boolean, completed_at: string|null, message: string}>}
   */
  setCompleted: (taskId, completed) =>
    apiClient.patch(`/api/processing/followups/${taskId}`, { completed }).then(r => r.data),
}

export default followupsApi
