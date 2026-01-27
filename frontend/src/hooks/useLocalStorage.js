/**
 * useLocalStorage Hook
 * 
 * Persist state to localStorage with automatic serialization.
 */

import { useState, useEffect, useCallback } from 'react'

/**
 * Hook for persisting state to localStorage
 * @param {string} key - Storage key
 * @param {*} initialValue - Initial value if not in storage
 * @param {Object} options - Options
 */
export function useLocalStorage(key, initialValue, options = {}) {
  const { 
    serialize = JSON.stringify, 
    deserialize = JSON.parse,
    syncAcrossTabs = true,
  } = options

  // Get initial value from storage or use provided initial value
  const readValue = useCallback(() => {
    if (typeof window === 'undefined') {
      return initialValue
    }

    try {
      const item = window.localStorage.getItem(key)
      return item ? deserialize(item) : initialValue
    } catch {
      return initialValue
    }
  }, [key, initialValue, deserialize])

  const [storedValue, setStoredValue] = useState(readValue)

  // Update localStorage when state changes
  const setValue = useCallback((value) => {
    try {
      // Allow value to be a function (like useState)
      const valueToStore = value instanceof Function ? value(storedValue) : value
      
      setStoredValue(valueToStore)
      
      if (typeof window !== 'undefined') {
        window.localStorage.setItem(key, serialize(valueToStore))
        
        // Dispatch custom event for cross-tab sync
        if (syncAcrossTabs) {
          window.dispatchEvent(new StorageEvent('storage', {
            key,
            newValue: serialize(valueToStore),
          }))
        }
      }
    } catch {
      // localStorage write failed (e.g., quota exceeded, private mode)
    }
  }, [key, serialize, storedValue, syncAcrossTabs])

  // Remove from storage
  const removeValue = useCallback(() => {
    try {
      setStoredValue(initialValue)
      if (typeof window !== 'undefined') {
        window.localStorage.removeItem(key)
      }
    } catch {
      // localStorage remove failed
    }
  }, [key, initialValue])

  // Sync across tabs
  useEffect(() => {
    if (!syncAcrossTabs) return

    const handleStorageChange = (event) => {
      if (event.key === key && event.newValue !== null) {
        try {
          setStoredValue(deserialize(event.newValue))
        } catch {
          // Storage event parse failed - ignore malformed data
        }
      }
    }

    window.addEventListener('storage', handleStorageChange)
    return () => window.removeEventListener('storage', handleStorageChange)
  }, [key, deserialize, syncAcrossTabs])

  return [storedValue, setValue, removeValue]
}

/**
 * Hook for simple key-value storage (no serialization)
 * @param {string} key - Storage key
 * @param {string} initialValue - Initial value
 */
export function useLocalStorageString(key, initialValue = '') {
  return useLocalStorage(key, initialValue, {
    serialize: (v) => v,
    deserialize: (v) => v,
  })
}

/**
 * Hook for boolean storage
 * @param {string} key - Storage key
 * @param {boolean} initialValue - Initial value
 */
export function useLocalStorageBoolean(key, initialValue = false) {
  return useLocalStorage(key, initialValue, {
    serialize: (v) => v ? '1' : '0',
    deserialize: (v) => v === '1',
  })
}

export default useLocalStorage
