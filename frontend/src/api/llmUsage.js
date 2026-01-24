/**
 * LLM Usage API Client
 * 
 * Functions for fetching LLM cost and usage data, providing visibility
 * into API spending and token consumption.
 * 
 * ## Use Cases
 * - **Cost Monitoring**: Track daily and monthly LLM spending
 * - **Budget Management**: Check budget status and receive alerts
 * - **Usage Analysis**: Identify top consumers by model, pipeline, operation
 * - **Trend Analysis**: View historical usage patterns
 * 
 * ## Key Metrics
 * - **Cost USD**: Total spending on LLM API calls
 * - **Token Count**: Total tokens consumed (prompt + completion)
 * - **Request Count**: Number of API calls made
 * - **Budget Status**: Remaining budget and alert thresholds
 * 
 * @module api/llmUsage
 */

import { typedApi } from './typed-client'
import { apiClient } from './client'

export const llmUsageApi = {
  /**
   * Get today's LLM usage summary
   * @param {string} [date] - Optional date in YYYY-MM-DD format (defaults to today)
   * @returns {Promise<{
   *   date: string,
   *   total_cost_usd: number,
   *   request_count: number,
   *   total_tokens: number,
   *   by_model: Object,
   *   by_pipeline: Object
   * }>} Daily usage summary
   */
  getDailyUsage: (date) => 
    apiClient.get('/api/llm-usage/daily', { params: date ? { date } : {} }).then(r => r.data),

  /**
   * Get monthly LLM usage summary
   * @param {Object} [options] - Query options
   * @param {number} [options.year] - Year (defaults to current year)
   * @param {number} [options.month] - Month 1-12 (defaults to current month)
   * @returns {Promise<{
   *   year: number,
   *   month: number,
   *   total_cost_usd: number,
   *   request_count: number,
   *   total_tokens: number,
   *   by_day: Array,
   *   by_model: Object
   * }>} Monthly usage summary
   */
  getMonthlyUsage: ({ year, month } = {}) => 
    apiClient.get('/api/llm-usage/monthly', { 
      params: { ...(year && { year }), ...(month && { month }) }
    }).then(r => r.data),

  /**
   * Get budget status and alerts
   * @param {string} [period='monthly'] - Budget period: 'daily' or 'monthly'
   * @returns {Promise<{
   *   period: string,
   *   current_spend_usd: number,
   *   limit_usd: number,
   *   remaining_usd: number,
   *   percentage_used: number,
   *   is_over_budget: boolean,
   *   alert_threshold: number,
   *   is_alert_triggered: boolean
   * }>} Budget status
   */
  getBudgetStatus: (period = 'monthly') => 
    apiClient.get('/api/llm-usage/budget', { params: { period } }).then(r => r.data),

  /**
   * Get historical usage data
   * @param {Object} [options] - Query options
   * @param {number} [options.days=30] - Number of days of history (1-365)
   * @returns {Promise<{
   *   period_days: number,
   *   total_cost_usd: number,
   *   total_requests: number,
   *   total_tokens: number,
   *   daily_data: Array<{date: string, cost_usd: number, request_count: number, tokens: number}>,
   *   avg_daily_cost: number,
   *   trend_direction: string
   * }>} Historical usage data
   */
  getUsageHistory: ({ days = 30 } = {}) => 
    apiClient.get('/api/llm-usage/history', { params: { days } }).then(r => r.data),

  /**
   * Get top consumers of LLM resources
   * @param {Object} [options] - Query options
   * @param {number} [options.days=30] - Number of days to analyze
   * @param {number} [options.limit=10] - Number of top items to return
   * @returns {Promise<{
   *   by_model: Array<{model: string, cost_usd: number, request_count: number, tokens: number}>,
   *   by_pipeline: Array<{pipeline: string, cost_usd: number, request_count: number}>,
   *   by_operation: Array<{operation: string, cost_usd: number, request_count: number, tokens: number}>
   * }>} Top consumers breakdown
   */
  getTopConsumers: ({ days = 30, limit = 10 } = {}) => 
    apiClient.get('/api/llm-usage/top-consumers', { params: { days, limit } }).then(r => r.data),
}

export default llmUsageApi
