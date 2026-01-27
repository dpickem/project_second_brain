/**
 * Typed API Client (OpenAPI-backed)
 * 
 * This module provides a type-safe API client that is generated from the backend's
 * OpenAPI schema. It catches endpoint typos and parameter mismatches at development
 * time instead of runtime.
 * 
 * ## How It Works
 * 
 * 1. `npm run generate:api-types` fetches the OpenAPI schema from the backend
 * 2. It generates TypeScript types in `src/api/schema.ts`
 * 3. This client uses `openapi-fetch` to provide typed HTTP methods
 * 
 * ## Why Use This Instead of Axios?
 * 
 * With axios, typos like `/api/itmes` or `{ qty: 5 }` instead of `{ quantity: 5 }`
 * only fail at runtime. With the typed client, TypeScript catches these errors
 * during development.
 * 
 * ## Usage
 * 
 * ```js
 * import { typedApi } from './typed-client'
 * 
 * // GET request - types for params and response are inferred
 * const { data, error } = await typedApi.GET('/api/knowledge/graph', {
 *   params: { query: { limit: 50, depth: 2 } }
 * })
 * 
 * // POST request - types for body and response are inferred
 * const { data, error } = await typedApi.POST('/api/knowledge/search', {
 *   body: { query: 'transformers', limit: 20 }
 * })
 * ```
 * 
 * ## When to Use
 * 
 * Use `typedApi` for:
 * - New code that benefits from type safety
 * - Critical paths where correctness matters
 * - Complex request bodies
 * 
 * The existing `apiClient` (axios) still works and is fine for simple cases
 * or where you need axios-specific features (interceptors, etc.).
 * 
 * ## Type Generation
 * 
 * Run `npm run generate:api-types` whenever the backend API changes.
 * In CI, use `npm run api:check` to fail if the schema has changed unexpectedly.
 * 
 * @module api/typed-client
 */

import createClient from 'openapi-fetch'
import { API_URL } from './client'

// Types generated from OpenAPI schema - run `npm run generate:api-types` to update
// @ts-ignore - JSDoc types work in JS files even without explicit import
/** @typedef {import('./schema').paths} paths */

/**
 * Typed API client created from OpenAPI schema.
 * 
 * Provides type-safe HTTP methods:
 * - `typedApi.GET(path, options)` - GET request
 * - `typedApi.POST(path, options)` - POST request
 * - `typedApi.PUT(path, options)` - PUT request
 * - `typedApi.PATCH(path, options)` - PATCH request
 * - `typedApi.DELETE(path, options)` - DELETE request
 * 
 * Each method returns `{ data, error, response }` where:
 * - `data`: The typed response body (if successful)
 * - `error`: The error body (if request failed)
 * - `response`: The raw Response object
 * 
 * @example
 * // Search knowledge with type-safe parameters
 * const { data, error } = await typedApi.POST('/api/knowledge/search', {
 *   body: {
 *     query: 'transformers',      // Must be string
 *     limit: 20,                   // Must be number
 *     node_types: ['Content'],     // Must be string array
 *   }
 * })
 * 
 * if (data) {
 *   // data.results is typed as SearchResult[]
 *   data.results.forEach(r => console.log(r.title))
 * }
 * 
 * @example
 * // Get graph with query parameters
 * const { data } = await typedApi.GET('/api/knowledge/graph', {
 *   params: {
 *     query: {
 *       limit: 100,
 *       depth: 2,
 *       node_types: 'Content,Concept'
 *     }
 *   }
 * })
 * 
 * @type {import('openapi-fetch').Client<import('./schema').paths>}
 */
export const typedApi = createClient({
  baseUrl: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

/**
 * Helper to check if request was successful.
 * 
 * @example
 * const result = await typedApi.GET('/api/knowledge/stats')
 * if (isOk(result)) {
 *   console.log(result.data.total_content)
 * } else {
 *   console.error('Failed:', result.error)
 * }
 */
export function isOk(result) {
  return result.data !== undefined && result.error === undefined
}

/**
 * Helper to extract data or throw error.
 * Useful when you want to use try/catch instead of checking result.
 * 
 * @example
 * try {
 *   const stats = await unwrap(typedApi.GET('/api/knowledge/stats'))
 *   console.log(stats.total_content)
 * } catch (error) {
 *   console.error('Request failed:', error)
 * }
 */
export async function unwrap(resultPromise) {
  const result = await resultPromise
  if (result.error) {
    const error = new Error(result.error.message || 'API request failed')
    error.status = result.response?.status
    error.body = result.error
    throw error
  }
  return result.data
}

/**
 * Type-safe wrapper for common API patterns.
 * 
 * These helpers combine the typed client with common error handling patterns.
 */
export const api = {
  /**
   * Knowledge graph operations
   */
  knowledge: {
    /**
     * Get graph data for visualization.
     * @param {Object} params - Query parameters
     * @param {number} [params.limit] - Max nodes to return
     * @param {number} [params.depth] - Traversal depth
     * @param {string} [params.center_id] - Center graph on this node
     * @param {string} [params.node_types] - Comma-separated node types
     */
    getGraph: (params = {}) =>
      typedApi.GET('/api/knowledge/graph', { params: { query: params } }),
    
    /**
     * Get graph statistics.
     */
    getStats: () =>
      typedApi.GET('/api/knowledge/stats'),
    
    /**
     * Semantic search across knowledge base.
     * @param {Object} body - Search parameters
     * @param {string} body.query - Search query text
     * @param {number} [body.limit] - Max results
     * @param {string[]} [body.node_types] - Node types to search
     * @param {number} [body.min_score] - Minimum relevance score
     * @param {boolean} [body.use_vector] - Use vector search
     */
    search: (body) =>
      typedApi.POST('/api/knowledge/search', { body }),
    
    /**
     * Get node details by ID.
     * @param {string} nodeId - Node identifier
     */
    getNode: (nodeId) =>
      typedApi.GET('/api/knowledge/node/{node_id}', {
        params: { path: { node_id: nodeId } }
      }),
    
    /**
     * Get connections for a node.
     * @param {string} nodeId - Node identifier
     * @param {Object} [params] - Query parameters
     * @param {string} [params.direction] - 'incoming', 'outgoing', or 'both'
     * @param {number} [params.limit] - Max connections per direction
     */
    getConnections: (nodeId, params = {}) =>
      typedApi.GET('/api/knowledge/connections/{node_id}', {
        params: { path: { node_id: nodeId }, query: params }
      }),
    
    /**
     * Get topic hierarchy.
     * @param {Object} [params] - Query parameters
     * @param {number} [params.min_content] - Min content count to include
     */
    getTopics: (params = {}) =>
      typedApi.GET('/api/knowledge/topics', { params: { query: params } }),
    
    /**
     * Check knowledge graph health.
     */
    checkHealth: () =>
      typedApi.GET('/api/knowledge/health'),
  },
  
  /**
   * Assistant/chat operations
   */
  assistant: {
    /**
     * Send a message to the assistant.
     * @param {Object} body - Message data
     * @param {string} body.message - User message
     * @param {string} [body.conversation_id] - Existing conversation ID
     */
    chat: (body) =>
      typedApi.POST('/api/assistant/chat', { body }),
    
    /**
     * List conversations.
     * @param {Object} [params] - Query parameters
     * @param {number} [params.limit] - Max conversations
     * @param {number} [params.offset] - Pagination offset
     */
    listConversations: (params = {}) =>
      typedApi.GET('/api/assistant/conversations', { params: { query: params } }),
    
    /**
     * Get conversation details.
     * @param {string} conversationId - Conversation ID
     */
    getConversation: (conversationId) =>
      typedApi.GET('/api/assistant/conversations/{conversation_id}', {
        params: { path: { conversation_id: conversationId } }
      }),
  },
  
  /**
   * Health check
   */
  health: {
    /**
     * Check API health.
     */
    check: () =>
      typedApi.GET('/api/health'),
  },
}

export default typedApi
