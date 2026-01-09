/**
 * Hooks Barrel Export
 * 
 * Central export for all custom React hooks used throughout the application.
 * Import hooks from this file for cleaner imports:
 * 
 * @example
 * import { useDebounce, useLocalStorage, useKeyboardShortcut } from '../hooks'
 * 
 * 
 * ## Available Hooks
 * 
 * ### Keyboard Shortcuts
 * - `useKeyboardShortcuts` - Global keyboard shortcuts with default navigation bindings
 * - `useKeyboardShortcut` - Register a single keyboard shortcut
 * 
 * ### Local Storage
 * - `useLocalStorage` - Persist any value to localStorage with JSON serialization
 * - `useLocalStorageString` - Persist string values without serialization
 * - `useLocalStorageBoolean` - Persist boolean values efficiently
 * 
 * ### Debounce & Throttle
 * - `useDebouncedSearch` - Full-featured search input with debouncing and loading states
 * - `useDebounce` - Simple value debouncing
 * - `useDebouncedCallback` - Debounce function calls with cancel/flush support
 * - `useThrottle` - Throttle rapidly changing values
 */

// ============================================================================
// Keyboard Shortcuts
// ============================================================================

/**
 * useKeyboardShortcuts - Global keyboard shortcut handler
 * 
 * Registers app-wide keyboard shortcuts with default navigation bindings.
 * Respects user's keyboard shortcuts enabled setting.
 * 
 * Default shortcuts:
 * - ⌘K / Ctrl+K: Toggle command palette
 * - ⌘N / Ctrl+N: Open quick capture
 * - ⌘1-6: Navigate to Dashboard, Practice, Review, Knowledge, Analytics, Assistant
 * - Escape: Close overlays
 * 
 * @example
 * // Use with default shortcuts
 * useKeyboardShortcuts()
 * 
 * @example
 * // Add custom handlers
 * useKeyboardShortcuts({
 *   customAction: () => console.log('Custom!'),
 * })
 * 
 * @example
 * // Temporarily disable
 * useKeyboardShortcuts({}, { enabled: !isModalOpen })
 */

/**
 * useKeyboardShortcut - Single keyboard shortcut
 * 
 * Register a single keyboard shortcut with fine-grained control.
 * 
 * @example
 * // Save on Cmd+S
 * useKeyboardShortcut('Meta+s', handleSave)
 * 
 * @example
 * // Allow in input fields
 * useKeyboardShortcut('Escape', handleClose, { allowInInput: true })
 * 
 * @example
 * // Don't prevent default browser behavior
 * useKeyboardShortcut('Meta+p', handlePrint, { preventDefault: false })
 */
export { 
  useKeyboardShortcuts, 
  useKeyboardShortcut 
} from './useKeyboardShortcuts'

// ============================================================================
// Local Storage Persistence
// ============================================================================

/**
 * useLocalStorage - Persist state to localStorage
 * 
 * Syncs React state with localStorage, with automatic JSON serialization
 * and optional cross-tab synchronization.
 * 
 * @example
 * // Basic usage
 * const [user, setUser, removeUser] = useLocalStorage('user', null)
 * 
 * @example
 * // With functional updates
 * const [count, setCount] = useLocalStorage('count', 0)
 * setCount(prev => prev + 1)
 * 
 * @example
 * // Disable cross-tab sync
 * const [value, setValue] = useLocalStorage('key', 'default', {
 *   syncAcrossTabs: false
 * })
 */

/**
 * useLocalStorageString - String storage without serialization
 * 
 * Optimized for string values - avoids JSON.stringify/parse overhead.
 * 
 * @example
 * const [theme, setTheme] = useLocalStorageString('theme', 'dark')
 */

/**
 * useLocalStorageBoolean - Boolean storage
 * 
 * Efficient storage for boolean flags using '1'/'0' strings.
 * 
 * @example
 * const [isDismissed, setIsDismissed] = useLocalStorageBoolean('banner-dismissed', false)
 */
export { 
  useLocalStorage, 
  useLocalStorageString, 
  useLocalStorageBoolean 
} from './useLocalStorage'

// ============================================================================
// Debounce & Throttle Utilities
// ============================================================================

/**
 * useDebouncedSearch - Full-featured search debouncing
 * 
 * Provides both immediate and debounced values plus loading states.
 * Ideal for search inputs with API calls.
 * 
 * @example
 * const { value, debouncedValue, setValue, clear, isDebouncing } = useDebouncedSearch('', 300)
 * 
 * // Use `value` for input display (immediate)
 * // Use `debouncedValue` for API calls (debounced)
 * <input value={value} onChange={(e) => setValue(e.target.value)} />
 * {isDebouncing && <Spinner />}
 */

/**
 * useDebounce - Simple value debouncing
 * 
 * Returns a debounced version of the provided value.
 * Simpler alternative when you don't need loading states.
 * 
 * @example
 * const [searchTerm, setSearchTerm] = useState('')
 * const debouncedSearch = useDebounce(searchTerm, 300)
 * 
 * useEffect(() => {
 *   fetchResults(debouncedSearch)
 * }, [debouncedSearch])
 */

/**
 * useDebouncedCallback - Debounce function calls
 * 
 * Returns a debounced version of a callback function.
 * Includes `.cancel()` and `.flush()` methods for fine control.
 * 
 * @example
 * const debouncedSave = useDebouncedCallback((data) => {
 *   api.save(data)
 * }, 500)
 * 
 * // Call debounced function
 * debouncedSave(formData)
 * 
 * // Cancel pending call
 * debouncedSave.cancel()
 * 
 * // Execute immediately
 * debouncedSave.flush(formData)
 */

/**
 * useThrottle - Throttle rapidly changing values
 * 
 * Limits how often a value updates, useful for scroll/resize handlers.
 * Unlike debounce, throttle ensures regular updates during continuous changes.
 * 
 * @example
 * const [scrollY, setScrollY] = useState(0)
 * const throttledScrollY = useThrottle(scrollY, 100)
 * 
 * // Updates at most every 100ms during scroll
 */
export { 
  useDebouncedSearch, 
  useDebounce, 
  useDebouncedCallback,
  useThrottle,
} from './useDebouncedSearch'
