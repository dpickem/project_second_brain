/**
 * useDebouncedSearch Hook
 * 
 * Debounced search input with loading states.
 */

import { useState, useEffect, useMemo, useCallback } from 'react'

/**
 * Hook for debounced search functionality
 * @param {string} initialValue - Initial search value
 * @param {number} delay - Debounce delay in milliseconds
 */
export function useDebouncedSearch(initialValue = '', delay = 300) {
  const [value, setValue] = useState(initialValue)
  const [debouncedValue, setDebouncedValue] = useState(initialValue)
  const [isDebouncing, setIsDebouncing] = useState(false)

  // Update debounced value after delay
  useEffect(() => {
    setIsDebouncing(true)
    
    const timer = setTimeout(() => {
      setDebouncedValue(value)
      setIsDebouncing(false)
    }, delay)

    return () => {
      clearTimeout(timer)
    }
  }, [value, delay])

  // Clear search
  const clear = useCallback(() => {
    setValue('')
    setDebouncedValue('')
    setIsDebouncing(false)
  }, [])

  // Check if there's a pending search
  const isPending = value !== debouncedValue

  return {
    value,
    debouncedValue,
    setValue,
    clear,
    isDebouncing,
    isPending,
  }
}

/**
 * Hook for debounced value only (simpler version)
 * @param {*} value - Value to debounce
 * @param {number} delay - Delay in milliseconds
 */
export function useDebounce(value, delay = 300) {
  const [debouncedValue, setDebouncedValue] = useState(value)

  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedValue(value)
    }, delay)

    return () => {
      clearTimeout(timer)
    }
  }, [value, delay])

  return debouncedValue
}

/**
 * Hook for debounced callback
 * @param {Function} callback - Function to debounce
 * @param {number} delay - Delay in milliseconds
 * @param {Array} deps - Dependencies
 */
export function useDebouncedCallback(callback, delay = 300) {
  const memoizedCallback = useCallback(callback, [callback])

  const debouncedFn = useMemo(() => {
    let timeoutId = null

    const debouncedFunction = (...args) => {
      if (timeoutId) {
        clearTimeout(timeoutId)
      }

      timeoutId = setTimeout(() => {
        memoizedCallback(...args)
      }, delay)
    }

    debouncedFunction.cancel = () => {
      if (timeoutId) {
        clearTimeout(timeoutId)
      }
    }

    debouncedFunction.flush = (...args) => {
      if (timeoutId) {
        clearTimeout(timeoutId)
      }
      memoizedCallback(...args)
    }

    return debouncedFunction
  }, [memoizedCallback, delay])

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      debouncedFn.cancel()
    }
  }, [debouncedFn])

  return debouncedFn
}

/**
 * Hook for throttled value
 * @param {*} value - Value to throttle
 * @param {number} limit - Throttle limit in milliseconds
 */
export function useThrottle(value, limit = 300) {
  const [throttledValue, setThrottledValue] = useState(value)
  const [lastRan, setLastRan] = useState(Date.now())

  useEffect(() => {
    const now = Date.now()
    
    if (now - lastRan >= limit) {
      setThrottledValue(value)
      setLastRan(now)
    } else {
      const timer = setTimeout(() => {
        setThrottledValue(value)
        setLastRan(Date.now())
      }, limit - (now - lastRan))

      return () => clearTimeout(timer)
    }
  }, [value, limit, lastRan])

  return throttledValue
}

export default useDebouncedSearch
