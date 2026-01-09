/**
 * API Client Tests
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { 
  apiClient, 
  createApiEndpoint, 
  createDynamicEndpoint, 
  buildQueryParams,
  retryConfig 
} from './client'

// Mock axios
vi.mock('axios', () => ({
  default: {
    create: vi.fn(() => ({
      interceptors: {
        request: { use: vi.fn() },
        response: { use: vi.fn() },
      },
      get: vi.fn(),
      post: vi.fn(),
      put: vi.fn(),
      patch: vi.fn(),
      delete: vi.fn(),
    })),
  },
}))

// Mock react-hot-toast
vi.mock('react-hot-toast', () => ({
  default: {
    error: vi.fn(),
    success: vi.fn(),
  },
}))

describe('apiClient', () => {
  it('should be defined', () => {
    expect(apiClient).toBeDefined()
  })

  it('should have request interceptor configured', () => {
    expect(apiClient.interceptors.request.use).toBeDefined()
  })

  it('should have response interceptor configured', () => {
    expect(apiClient.interceptors.response.use).toBeDefined()
  })
})

describe('createApiEndpoint', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('should create endpoint with get method', () => {
    const endpoint = createApiEndpoint('/api/test')
    
    expect(endpoint.get).toBeDefined()
    expect(typeof endpoint.get).toBe('function')
  })

  it('should create endpoint with post method', () => {
    const endpoint = createApiEndpoint('/api/test')
    
    expect(endpoint.post).toBeDefined()
    expect(typeof endpoint.post).toBe('function')
  })

  it('should create endpoint with put method', () => {
    const endpoint = createApiEndpoint('/api/test')
    
    expect(endpoint.put).toBeDefined()
    expect(typeof endpoint.put).toBe('function')
  })

  it('should create endpoint with patch method', () => {
    const endpoint = createApiEndpoint('/api/test')
    
    expect(endpoint.patch).toBeDefined()
    expect(typeof endpoint.patch).toBe('function')
  })

  it('should create endpoint with delete method', () => {
    const endpoint = createApiEndpoint('/api/test')
    
    expect(endpoint.delete).toBeDefined()
    expect(typeof endpoint.delete).toBe('function')
  })
})

describe('createDynamicEndpoint', () => {
  it('should create dynamic endpoint with get method', () => {
    const endpoint = createDynamicEndpoint((id) => `/api/items/${id}`)
    
    expect(endpoint.get).toBeDefined()
    expect(typeof endpoint.get).toBe('function')
  })

  it('should create dynamic endpoint with post method', () => {
    const endpoint = createDynamicEndpoint((id) => `/api/items/${id}`)
    
    expect(endpoint.post).toBeDefined()
    expect(typeof endpoint.post).toBe('function')
  })

  it('should create dynamic endpoint with put method', () => {
    const endpoint = createDynamicEndpoint((id) => `/api/items/${id}`)
    
    expect(endpoint.put).toBeDefined()
    expect(typeof endpoint.put).toBe('function')
  })

  it('should create dynamic endpoint with patch method', () => {
    const endpoint = createDynamicEndpoint((id) => `/api/items/${id}`)
    
    expect(endpoint.patch).toBeDefined()
    expect(typeof endpoint.patch).toBe('function')
  })

  it('should create dynamic endpoint with delete method', () => {
    const endpoint = createDynamicEndpoint((id) => `/api/items/${id}`)
    
    expect(endpoint.delete).toBeDefined()
    expect(typeof endpoint.delete).toBe('function')
  })
})

describe('buildQueryParams', () => {
  it('should build query params from object', () => {
    const params = buildQueryParams({ page: 1, limit: 10 })
    
    expect(params.get('page')).toBe('1')
    expect(params.get('limit')).toBe('10')
  })

  it('should filter out undefined values', () => {
    const params = buildQueryParams({ page: 1, search: undefined })
    
    expect(params.get('page')).toBe('1')
    expect(params.get('search')).toBeNull()
  })

  it('should filter out null values', () => {
    const params = buildQueryParams({ page: 1, filter: null })
    
    expect(params.get('page')).toBe('1')
    expect(params.get('filter')).toBeNull()
  })

  it('should filter out empty string values', () => {
    const params = buildQueryParams({ page: 1, query: '' })
    
    expect(params.get('page')).toBe('1')
    expect(params.get('query')).toBeNull()
  })

  it('should keep falsy but valid values like 0', () => {
    const params = buildQueryParams({ page: 0, active: false })
    
    expect(params.get('page')).toBe('0')
    expect(params.get('active')).toBe('false')
  })

  it('should return empty URLSearchParams for empty object', () => {
    const params = buildQueryParams({})
    
    expect(params.toString()).toBe('')
  })
})

describe('retryConfig', () => {
  it('should have retries configured', () => {
    expect(retryConfig.retries).toBe(3)
  })

  it('should have retryDelay function', () => {
    expect(typeof retryConfig.retryDelay).toBe('function')
  })

  it('should calculate exponential backoff delay', () => {
    expect(retryConfig.retryDelay(0)).toBe(1000)
    expect(retryConfig.retryDelay(1)).toBe(2000)
    expect(retryConfig.retryDelay(2)).toBe(4000)
    expect(retryConfig.retryDelay(3)).toBe(8000)
  })

  it('should cap delay at 10 seconds', () => {
    expect(retryConfig.retryDelay(10)).toBe(10000)
  })

  it('should have retryCondition function', () => {
    expect(typeof retryConfig.retryCondition).toBe('function')
  })

  it('should retry on network error (no response)', () => {
    const error = { message: 'Network Error' }
    expect(retryConfig.retryCondition(error)).toBe(true)
  })

  it('should retry on 500 error', () => {
    const error = { response: { status: 500 } }
    expect(retryConfig.retryCondition(error)).toBe(true)
  })

  it('should retry on 503 error', () => {
    const error = { response: { status: 503 } }
    expect(retryConfig.retryCondition(error)).toBe(true)
  })

  it('should not retry on 400 error', () => {
    const error = { response: { status: 400 } }
    expect(retryConfig.retryCondition(error)).toBe(false)
  })

  it('should not retry on 404 error', () => {
    const error = { response: { status: 404 } }
    expect(retryConfig.retryCondition(error)).toBe(false)
  })

  it('should not retry on 401 error', () => {
    const error = { response: { status: 401 } }
    expect(retryConfig.retryCondition(error)).toBe(false)
  })
})
