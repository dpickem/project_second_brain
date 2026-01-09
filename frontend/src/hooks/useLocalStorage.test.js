/**
 * useLocalStorage Hook Tests
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useLocalStorage } from './useLocalStorage'

describe('useLocalStorage', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.clearAllMocks()
  })

  it('should return initial value when localStorage is empty', () => {
    localStorage.getItem.mockReturnValue(null)
    
    const { result } = renderHook(() => useLocalStorage('test-key', 'initial'))
    
    expect(result.current[0]).toBe('initial')
  })

  it('should return stored value from localStorage', () => {
    localStorage.getItem.mockReturnValue(JSON.stringify('stored-value'))
    
    const { result } = renderHook(() => useLocalStorage('test-key', 'initial'))
    
    expect(result.current[0]).toBe('stored-value')
  })

  it('should update localStorage when setValue is called', () => {
    localStorage.getItem.mockReturnValue(null)
    
    const { result } = renderHook(() => useLocalStorage('test-key', 'initial'))
    
    act(() => {
      result.current[1]('new-value')
    })
    
    expect(localStorage.setItem).toHaveBeenCalledWith('test-key', JSON.stringify('new-value'))
    expect(result.current[0]).toBe('new-value')
  })

  it('should handle objects as values', () => {
    localStorage.getItem.mockReturnValue(null)
    
    const { result } = renderHook(() => useLocalStorage('test-key', { name: 'test' }))
    
    act(() => {
      result.current[1]({ name: 'updated', count: 5 })
    })
    
    expect(localStorage.setItem).toHaveBeenCalledWith(
      'test-key', 
      JSON.stringify({ name: 'updated', count: 5 })
    )
    expect(result.current[0]).toEqual({ name: 'updated', count: 5 })
  })

  it('should handle function updates', () => {
    localStorage.getItem.mockReturnValue(JSON.stringify(5))
    
    const { result } = renderHook(() => useLocalStorage('test-key', 0))
    
    act(() => {
      result.current[1]((prev) => prev + 1)
    })
    
    expect(result.current[0]).toBe(6)
  })

  it('should remove item when setValue receives undefined', () => {
    localStorage.getItem.mockReturnValue(JSON.stringify('value'))
    
    const { result } = renderHook(() => useLocalStorage('test-key', 'initial'))
    
    act(() => {
      result.current[2]() // remove function
    })
    
    expect(localStorage.removeItem).toHaveBeenCalledWith('test-key')
  })

  it('should handle JSON parse errors gracefully', () => {
    localStorage.getItem.mockReturnValue('invalid-json{')
    
    const { result } = renderHook(() => useLocalStorage('test-key', 'default'))
    
    expect(result.current[0]).toBe('default')
  })
})
