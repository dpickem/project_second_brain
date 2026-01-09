/**
 * useKeyboardShortcuts Hook
 * 
 * Register and manage keyboard shortcuts.
 */

import { useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useSettingsStore, useUiStore } from '../stores'

// Default keyboard shortcuts
const defaultShortcuts = {
  'Meta+k': 'toggleCommandPalette',
  'Ctrl+k': 'toggleCommandPalette',
  'Meta+n': 'openCapture',
  'Ctrl+n': 'openCapture',
  'Meta+1': 'navigateDashboard',
  'Meta+2': 'navigatePractice',
  'Meta+3': 'navigateReview',
  'Meta+4': 'navigateKnowledge',
  'Meta+5': 'navigateAnalytics',
  'Meta+6': 'navigateAssistant',
  'Escape': 'closeOverlays',
}

/**
 * Hook for handling global keyboard shortcuts
 * @param {Object} customHandlers - Custom action handlers to merge with defaults
 * @param {Object} options - Options for the hook
 * @param {boolean} options.enabled - Whether shortcuts are enabled (default: true)
 */
export function useKeyboardShortcuts(customHandlers = {}, options = {}) {
  const { enabled = true } = options
  const navigate = useNavigate()
  const keyboardShortcutsEnabled = useSettingsStore((s) => s.keyboardShortcutsEnabled)
  const { 
    toggleCommandPalette, 
    openModal, 
    closeAllOverlays,
    hasOpenOverlay,
  } = useUiStore()

  // Default action handlers
  const defaultHandlers = useCallback(() => ({
    toggleCommandPalette,
    openCapture: () => openModal('capture'),
    closeOverlays: () => {
      if (hasOpenOverlay()) {
        closeAllOverlays()
      }
    },
    navigateDashboard: () => navigate('/'),
    navigatePractice: () => navigate('/practice'),
    navigateReview: () => navigate('/review'),
    navigateKnowledge: () => navigate('/knowledge'),
    navigateAnalytics: () => navigate('/analytics'),
    navigateAssistant: () => navigate('/assistant'),
  }), [navigate, toggleCommandPalette, openModal, closeAllOverlays, hasOpenOverlay])

  useEffect(() => {
    if (!keyboardShortcutsEnabled || !enabled) return

    const handlers = { ...defaultHandlers(), ...customHandlers }

    const handleKeyDown = (event) => {
      // Don't trigger shortcuts when typing in inputs
      const isTyping = ['INPUT', 'TEXTAREA', 'SELECT'].includes(
        document.activeElement?.tagName
      ) || document.activeElement?.isContentEditable

      // Allow Escape even when typing
      if (isTyping && event.key !== 'Escape') return

      // Build the key combo string
      const parts = []
      if (event.metaKey) parts.push('Meta')
      if (event.ctrlKey) parts.push('Ctrl')
      if (event.altKey) parts.push('Alt')
      if (event.shiftKey) parts.push('Shift')
      if (event.key !== 'Meta' && event.key !== 'Control' && 
          event.key !== 'Alt' && event.key !== 'Shift') {
        parts.push(event.key)
      }
      
      const keyCombo = parts.join('+')
      const action = defaultShortcuts[keyCombo]

      if (action && handlers[action]) {
        event.preventDefault()
        handlers[action](event)
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [keyboardShortcutsEnabled, enabled, defaultHandlers, customHandlers])
}

/**
 * Hook for registering a single keyboard shortcut
 * @param {string} key - Key combination (e.g., 'Meta+s', 'Escape')
 * @param {Function} handler - Handler function
 * @param {Object} options - Options
 */
export function useKeyboardShortcut(key, handler, options = {}) {
  const { 
    enabled = true, 
    allowInInput = false,
    preventDefault = true,
  } = options
  
  const keyboardShortcutsEnabled = useSettingsStore((s) => s.keyboardShortcutsEnabled)

  useEffect(() => {
    if (!enabled || !keyboardShortcutsEnabled) return

    const handleKeyDown = (event) => {
      // Check if typing in input
      const isTyping = ['INPUT', 'TEXTAREA', 'SELECT'].includes(
        document.activeElement?.tagName
      ) || document.activeElement?.isContentEditable

      if (isTyping && !allowInInput) return

      // Parse the key
      const keyParts = key.split('+')
      const mainKey = keyParts[keyParts.length - 1].toLowerCase()
      const needsMeta = keyParts.includes('Meta') || keyParts.includes('Cmd')
      const needsCtrl = keyParts.includes('Ctrl')
      const needsAlt = keyParts.includes('Alt')
      const needsShift = keyParts.includes('Shift')

      const matches = 
        event.key.toLowerCase() === mainKey &&
        event.metaKey === needsMeta &&
        event.ctrlKey === needsCtrl &&
        event.altKey === needsAlt &&
        event.shiftKey === needsShift

      if (matches) {
        if (preventDefault) {
          event.preventDefault()
        }
        handler(event)
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [key, handler, enabled, allowInInput, preventDefault, keyboardShortcutsEnabled])
}

export default useKeyboardShortcuts
