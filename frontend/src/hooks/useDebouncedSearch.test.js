/**
 * useDebouncedSearch Hook Tests
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { 
  useDebouncedSearch, 
  useDebounce, 
  useDebouncedCallback 
} from './useDebouncedSearch'

describe('useDebounce', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('should return initial value immediately', () => {
    const { result } = renderHook(() => useDebounce('initial', 300))
    
    expect(result.current).toBe('initial')
  })

  it('should debounce value changes', () => {
    const { result, rerender } = renderHook(
      ({ value }) => useDebounce(value, 300),
      { initialProps: { value: 'initial' } }
    )
    
    // Change value
    rerender({ value: 'changed' })
    
    // Should still be initial immediately
    expect(result.current).toBe('initial')
    
    // Fast-forward time
    act(() => {
      vi.advanceTimersByTime(300)
    })
    
    // Now should be changed
    expect(result.current).toBe('changed')
  })

  it('should cancel previous debounce on new value', () => {
    const { result, rerender } = renderHook(
      ({ value }) => useDebounce(value, 300),
      { initialProps: { value: 'first' } }
    )
    
    // Change value twice quickly
    rerender({ value: 'second' })
    act(() => {
      vi.advanceTimersByTime(100)
    })
    
    rerender({ value: 'third' })
    act(() => {
      vi.advanceTimersByTime(300)
    })
    
    // Should be 'third', not 'second'
    expect(result.current).toBe('third')
  })
})

describe('useDebouncedSearch', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('should return initial state', () => {
    const { result } = renderHook(() => useDebouncedSearch('test', 300))
    
    expect(result.current.value).toBe('test')
    expect(result.current.debouncedValue).toBe('test')
    // isDebouncing starts as true because useEffect sets it immediately
    expect(result.current.isDebouncing).toBe(true)
    
    // After timer completes, isDebouncing should be false
    act(() => {
      vi.advanceTimersByTime(300)
    })
    expect(result.current.isDebouncing).toBe(false)
  })

  it('should debounce search value changes', () => {
    const { result } = renderHook(() => useDebouncedSearch('', 300))
    
    // Change value
    act(() => {
      result.current.setValue('search')
    })
    
    // Value should update immediately
    expect(result.current.value).toBe('search')
    // Debounced value should still be empty
    expect(result.current.debouncedValue).toBe('')
    expect(result.current.isDebouncing).toBe(true)
    expect(result.current.isPending).toBe(true)
    
    // Fast-forward time
    act(() => {
      vi.advanceTimersByTime(300)
    })
    
    // Now debounced value should be updated
    expect(result.current.debouncedValue).toBe('search')
    expect(result.current.isDebouncing).toBe(false)
    expect(result.current.isPending).toBe(false)
  })

  it('should clear search', () => {
    const { result } = renderHook(() => useDebouncedSearch('initial', 300))
    
    // Wait for initial timer
    act(() => {
      vi.advanceTimersByTime(300)
    })
    
    // Set some value
    act(() => {
      result.current.setValue('search')
    })
    
    act(() => {
      vi.advanceTimersByTime(300)
    })
    
    // Clear - this sets isDebouncing to false directly
    act(() => {
      result.current.clear()
    })
    
    expect(result.current.value).toBe('')
    expect(result.current.debouncedValue).toBe('')
    // After clear, useEffect runs and sets isDebouncing to true again momentarily
    // We need to advance timers to see the final state
    act(() => {
      vi.advanceTimersByTime(300)
    })
    expect(result.current.isDebouncing).toBe(false)
  })
})

describe('useDebouncedCallback', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('should debounce callback execution', () => {
    const callback = vi.fn()
    const { result } = renderHook(() => useDebouncedCallback(callback, 300))
    
    act(() => {
      result.current('arg1')
      result.current('arg2')
      result.current('arg3')
    })
    
    // Callback should not be called yet
    expect(callback).not.toHaveBeenCalled()
    
    // Fast-forward
    act(() => {
      vi.advanceTimersByTime(300)
    })
    
    // Should only be called once with last args
    expect(callback).toHaveBeenCalledTimes(1)
    expect(callback).toHaveBeenCalledWith('arg3')
  })

  it('should return cancel function', () => {
    const callback = vi.fn()
    const { result } = renderHook(() => useDebouncedCallback(callback, 300))
    
    act(() => {
      result.current('test')
    })
    
    // Cancel before debounce completes
    act(() => {
      result.current.cancel()
      vi.advanceTimersByTime(300)
    })
    
    expect(callback).not.toHaveBeenCalled()
  })

  it('should provide flush function', () => {
    const callback = vi.fn()
    const { result } = renderHook(() => useDebouncedCallback(callback, 300))
    
    act(() => {
      result.current('test')
      result.current.flush('immediate')
    })
    
    // Flush should call immediately with provided args
    expect(callback).toHaveBeenCalledWith('immediate')
  })
})
