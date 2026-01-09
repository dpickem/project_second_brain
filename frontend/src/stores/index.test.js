/**
 * Stores Index Tests
 * 
 * Tests for the barrel export file to ensure all stores are properly exported.
 */

import { describe, it, expect } from 'vitest'
import * as stores from './index'
import { useSettingsStore } from './settingsStore'
import { useUiStore } from './uiStore'
import { usePracticeStore } from './practiceStore'
import { useReviewStore } from './reviewStore'

describe('stores index', () => {
  describe('exports', () => {
    it('should export useSettingsStore', () => {
      expect(stores.useSettingsStore).toBeDefined()
      expect(stores.useSettingsStore).toBe(useSettingsStore)
    })

    it('should export useUiStore', () => {
      expect(stores.useUiStore).toBeDefined()
      expect(stores.useUiStore).toBe(useUiStore)
    })

    it('should export usePracticeStore', () => {
      expect(stores.usePracticeStore).toBeDefined()
      expect(stores.usePracticeStore).toBe(usePracticeStore)
    })

    it('should export useReviewStore', () => {
      expect(stores.useReviewStore).toBeDefined()
      expect(stores.useReviewStore).toBe(useReviewStore)
    })
  })

  describe('store functionality via barrel export', () => {
    it('should be able to access useSettingsStore state', () => {
      const state = stores.useSettingsStore.getState()
      expect(state).toHaveProperty('theme')
    })

    it('should be able to access useUiStore state', () => {
      const state = stores.useUiStore.getState()
      expect(state).toHaveProperty('activeModal')
    })

    it('should be able to access usePracticeStore state', () => {
      const state = stores.usePracticeStore.getState()
      expect(state).toHaveProperty('session')
    })

    it('should be able to access useReviewStore state', () => {
      const state = stores.useReviewStore.getState()
      expect(state).toHaveProperty('cards')
    })
  })
})
