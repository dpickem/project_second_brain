/**
 * API Client Foundation
 * 
 * This module provides a centralized HTTP client for all API communications using Axios.
 * 
 * ## What is Axios?
 * Axios is a promise-based HTTP client for JavaScript that works in both browser and Node.js.
 * Unlike the native `fetch` API, Axios provides:
 * - Automatic JSON transformation
 * - Request/response interceptors for global transformations
 * - Request cancellation
 * - Timeout handling
 * - Better error handling with response status codes
 * 
 * ## What is an Axios Client Instance?
 * `axios.create()` creates a new Axios instance with custom default configuration.
 * This allows us to:
 * - Set a base URL once, so all requests use relative paths
 * - Configure default headers (e.g., Content-Type, Authorization)
 * - Set timeouts globally
 * - Add interceptors that apply to all requests made with this instance
 * 
 * ## Architecture
 * This client serves as the single point of configuration for API calls:
 * 
 * ```
 * Component → API Module (capture.js, etc.) → apiClient → Backend API
 *                                                ↓
 *                                         Interceptors
 *                                    (auth, logging, errors)
 * ```
 * 
 * ## Usage Examples
 * 
 * Direct usage:
 * ```js
 * import { apiClient } from './client'
 * const response = await apiClient.get('/api/items')
 * const data = response.data
 * ```
 * 
 * Using helper functions:
 * ```js
 * import { createApiEndpoint } from './client'
 * const itemsApi = createApiEndpoint('/api/items')
 * const items = await itemsApi.get()  // data already extracted
 * ```
 * 
 * @module api/client
 */

import axios from 'axios'
import toast from 'react-hot-toast'

/**
 * Base URL for all API requests.
 * Configured via environment variable VITE_API_URL, defaults to localhost:8000 for development.
 * @constant {string}
 */
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

/**
 * Pre-configured Axios instance for making HTTP requests to the backend API.
 * 
 * Configuration:
 * - `baseURL`: All request paths are relative to this URL
 * - `timeout`: Requests will abort after 30 seconds
 * - `headers`: Default Content-Type is JSON
 * 
 * This instance has request and response interceptors attached for:
 * - Adding authentication tokens (future)
 * - Logging request durations in development
 * - Global error handling with user-friendly toast notifications
 * 
 * @type {import('axios').AxiosInstance}
 * 
 * @example
 * // GET request
 * const response = await apiClient.get('/api/items', { params: { limit: 10 } })
 * 
 * @example
 * // POST request
 * const response = await apiClient.post('/api/items', { name: 'New Item' })
 * 
 * @example
 * // With error handling
 * try {
 *   const response = await apiClient.get('/api/items')
 *   return response.data
 * } catch (error) {
 *   // Error already handled by interceptor (toast shown)
 *   console.error('Request failed:', error.message)
 * }
 */
export const apiClient = axios.create({
  baseURL: API_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

/**
 * Request Interceptor
 * 
 * Interceptors are middleware functions that Axios calls before sending a request
 * or after receiving a response. They allow global transformation of all requests.
 * 
 * This request interceptor:
 * - Attaches metadata (start timestamp) for performance monitoring
 * - [Future] Will add Authorization header with JWT token for authenticated requests
 * 
 * @see https://axios-http.com/docs/interceptors
 */
apiClient.interceptors.request.use(
  (config) => {
    // Add request ID for tracking
    config.metadata = { startTime: Date.now() }

    // Future: Add auth token
    // const token = useAuthStore.getState().token
    // if (token) {
    //   config.headers.Authorization = `Bearer ${token}`
    // }

    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

/**
 * Response Interceptor
 * 
 * This interceptor processes all responses and errors before they reach the caller.
 * 
 * Success handling:
 * - Logs request duration in development mode for performance monitoring
 * 
 * Error handling by HTTP status:
 * - 401 Unauthorized: Silent (handled via redirect, no toast)
 * - 403 Forbidden: Toast notification about permissions
 * - 404 Not Found: Silent (let caller decide how to handle)
 * - 422 Validation Error: Show specific validation message
 * - 429 Rate Limited: Toast about rate limiting
 * - 500 Server Error: Generic server error toast
 * - Network Error: Connection failure toast
 * - Timeout: Request timeout toast
 * 
 * Note: Errors are still rejected (Promise.reject) so callers can add
 * additional handling if needed.
 */
apiClient.interceptors.response.use(
  (response) => {
    // Log response time in development
    if (import.meta.env.DEV && response.config.metadata) {
      const duration = Date.now() - response.config.metadata.startTime
      console.debug(`[API] ${response.config.method?.toUpperCase()} ${response.config.url} - ${duration}ms`)
    }
    return response
  },
  (error) => {
    const message = error.response?.data?.detail 
      || error.response?.data?.message 
      || error.message 
      || 'An unexpected error occurred'

    // Handle different error types
    if (error.response) {
      const { status } = error.response

      switch (status) {
        case 401:
          // Don't toast on auth errors - handle via redirect
          // Future: useAuthStore.getState().logout()
          break
        case 403:
          toast.error('You do not have permission to perform this action')
          break
        case 404:
          // Don't toast on 404 - let the caller handle it
          break
        case 422:
          // Validation error - show specific message
          toast.error(message)
          break
        case 429:
          toast.error('Too many requests. Please wait a moment.')
          break
        case 500:
          toast.error('Server error. Please try again later.')
          break
        default:
          toast.error(message)
      }
    } else if (error.code === 'ECONNABORTED') {
      toast.error('Request timed out. Please try again.')
    } else if (error.message === 'Network Error') {
      toast.error('Unable to connect to the server. Please check your connection.')
    }

    return Promise.reject(error)
  }
)

/**
 * Creates an API endpoint wrapper for a fixed path with automatic response data extraction.
 * 
 * This factory function simplifies API calls by:
 * - Eliminating the need to call `.then(r => r.data)` on every request
 * - Providing a consistent interface for CRUD operations
 * - Keeping API logic centralized and DRY
 * 
 * @param {string} path - The API endpoint path (e.g., '/api/items')
 * @returns {Object} Object with HTTP method functions (get, post, put, patch, delete)
 * 
 * @example
 * // Create an endpoint for items
 * const itemsApi = createApiEndpoint('/api/items')
 * 
 * // GET /api/items?status=active
 * const items = await itemsApi.get({ status: 'active' })
 * 
 * // POST /api/items with body { name: 'New Item' }
 * const newItem = await itemsApi.post({ name: 'New Item' })
 * 
 * // DELETE /api/items
 * await itemsApi.delete()
 */
export function createApiEndpoint(path) {
  return {
    /** GET request with optional query parameters */
    get: (params) => apiClient.get(path, { params }).then(r => r.data),
    /** POST request with request body */
    post: (data) => apiClient.post(path, data).then(r => r.data),
    /** PUT request with request body (full replacement) */
    put: (data) => apiClient.put(path, data).then(r => r.data),
    /** PATCH request with request body (partial update) */
    patch: (data) => apiClient.patch(path, data).then(r => r.data),
    /** DELETE request */
    delete: () => apiClient.delete(path).then(r => r.data),
  }
}

/**
 * Creates an API endpoint wrapper for dynamic paths (paths with variables).
 * 
 * Use this when the endpoint path includes IDs or other variable segments.
 * The path function receives arguments and constructs the final URL.
 * 
 * @param {Function} pathFn - Function that builds the path from provided arguments
 * @returns {Object} Object with HTTP method functions that accept path params + data
 * 
 * @example
 * // Create a dynamic endpoint for individual items
 * const itemApi = createDynamicEndpoint((id) => `/api/items/${id}`)
 * 
 * // GET /api/items/123
 * const item = await itemApi.get(123)
 * 
 * // GET /api/items/123?include=details
 * const itemWithDetails = await itemApi.get(123, { include: 'details' })
 * 
 * // PUT /api/items/123 with body { name: 'Updated' }
 * const updated = await itemApi.put(123, { name: 'Updated' })
 * 
 * // DELETE /api/items/123
 * await itemApi.delete(123)
 * 
 * @example
 * // Nested resource example
 * const commentApi = createDynamicEndpoint(
 *   (itemId, commentId) => `/api/items/${itemId}/comments/${commentId}`
 * )
 * 
 * // GET /api/items/123/comments/456
 * const comment = await commentApi.get(123, 456)
 * 
 * // POST /api/items/123/comments/456 with body
 * await commentApi.post(123, 456, { text: 'New comment' })
 */
export function createDynamicEndpoint(pathFn) {
  return {
    /**
     * GET request - path params followed by optional query params object
     * @example get(id) or get(id, { include: 'all' })
     */
    get: (...args) => {
      const [params, queryParams] = Array.isArray(args[args.length - 1]) || typeof args[args.length - 1] === 'object'
        ? [args.slice(0, -1), args[args.length - 1]]
        : [args, undefined]
      return apiClient.get(pathFn(...params), { params: queryParams }).then(r => r.data)
    },
    /**
     * POST request - path params followed by request body
     * @example post(id, { name: 'New' })
     */
    post: (...args) => {
      const path = pathFn(...args.slice(0, -1))
      const data = args[args.length - 1]
      return apiClient.post(path, data).then(r => r.data)
    },
    /**
     * PUT request - path params followed by request body (full replacement)
     * @example put(id, { name: 'Updated', status: 'active' })
     */
    put: (...args) => {
      const path = pathFn(...args.slice(0, -1))
      const data = args[args.length - 1]
      return apiClient.put(path, data).then(r => r.data)
    },
    /**
     * PATCH request - path params followed by request body (partial update)
     * @example patch(id, { status: 'inactive' })
     */
    patch: (...args) => {
      const path = pathFn(...args.slice(0, -1))
      const data = args[args.length - 1]
      return apiClient.patch(path, data).then(r => r.data)
    },
    /**
     * DELETE request - path params only
     * @example delete(id) or delete(itemId, commentId)
     */
    delete: (...args) => apiClient.delete(pathFn(...args)).then(r => r.data),
  }
}

/**
 * Builds a URLSearchParams object from a parameters object, filtering out empty values.
 * 
 * Useful when you need to construct query strings manually or append them to URLs.
 * Automatically removes null, undefined, and empty string values to keep URLs clean.
 * 
 * @param {Object} params - Object with key-value pairs for query parameters
 * @returns {URLSearchParams} URLSearchParams instance ready for use
 * 
 * @example
 * const params = buildQueryParams({
 *   search: 'hello',
 *   status: 'active',
 *   page: 1,
 *   empty: '',      // filtered out
 *   missing: null,  // filtered out
 * })
 * 
 * // Result: "search=hello&status=active&page=1"
 * const url = `/api/items?${params.toString()}`
 */
export function buildQueryParams(params) {
  const filtered = Object.entries(params)
    .filter(([, value]) => value !== undefined && value !== null && value !== '')
    .reduce((acc, [key, value]) => ({ ...acc, [key]: value }), {})
  
  return new URLSearchParams(filtered)
}

/**
 * Configuration object for implementing retry logic on failed requests.
 * 
 * This config is designed for use with axios-retry or similar retry middleware.
 * It implements exponential backoff to avoid overwhelming the server during outages.
 * 
 * Properties:
 * - `retries`: Maximum number of retry attempts (3)
 * - `retryDelay`: Exponential backoff function (1s, 2s, 4s... max 10s)
 * - `retryCondition`: Only retry on network errors or server errors (5xx)
 * 
 * @example
 * // Using with axios-retry library:
 * import axiosRetry from 'axios-retry'
 * import { apiClient, retryConfig } from './client'
 * 
 * axiosRetry(apiClient, retryConfig)
 * 
 * @example
 * // Manual retry implementation:
 * async function fetchWithRetry(url) {
 *   for (let attempt = 0; attempt <= retryConfig.retries; attempt++) {
 *     try {
 *       return await apiClient.get(url)
 *     } catch (error) {
 *       if (attempt === retryConfig.retries || !retryConfig.retryCondition(error)) {
 *         throw error
 *       }
 *       await new Promise(r => setTimeout(r, retryConfig.retryDelay(attempt)))
 *     }
 *   }
 * }
 * 
 * @type {{retries: number, retryDelay: Function, retryCondition: Function}}
 */
export const retryConfig = {
  /** Maximum number of retry attempts */
  retries: 3,
  /** 
   * Calculates delay between retries using exponential backoff
   * @param {number} attemptIndex - Zero-based attempt number
   * @returns {number} Delay in milliseconds (1000, 2000, 4000... max 10000)
   */
  retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 10000),
  /**
   * Determines if a failed request should be retried
   * @param {Error} error - Axios error object
   * @returns {boolean} True if the request should be retried
   */
  retryCondition: (error) => {
    // Retry on network errors or 5xx errors
    return !error.response || (error.response.status >= 500 && error.response.status <= 599)
  },
}

/**
 * Default export is the configured Axios client instance.
 * Prefer named import `apiClient` for clarity.
 */
export default apiClient
