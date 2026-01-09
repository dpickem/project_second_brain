/**
 * Settings Store Tests
 */

import { describe, it, expect, beforeEach } from 'vitest'
import { useSettingsStore } from './settingsStore'

describe('settingsStore', () => {
  beforeEach(() => {
    // Reset store to initial state
    useSettingsStore.getState().resetSettings()
  })

  describe('initial state', () => {
    it('should have correct default values', () => {
      const state = useSettingsStore.getState()
      
      expect(state.theme).toBe('dark')
      expect(state.sidebarCollapsed).toBe(false)
      expect(state.preferredSessionLength).toBe(15)
      expect(state.dailyReviewGoal).toBe(20)
      expect(state.keyboardShortcutsEnabled).toBe(true)
      expect(state.animationsEnabled).toBe(true)
    })

    it('should have all expected settings properties', () => {
      const state = useSettingsStore.getState()
      
      // Appearance
      expect(state).toHaveProperty('theme')
      expect(state).toHaveProperty('sidebarCollapsed')
      
      // Learning preferences
      expect(state).toHaveProperty('preferredSessionLength')
      expect(state).toHaveProperty('dailyReviewGoal')
      expect(state).toHaveProperty('showStreakReminders')
      
      // Keyboard shortcuts
      expect(state).toHaveProperty('keyboardShortcutsEnabled')
      
      // Notifications
      expect(state).toHaveProperty('notificationsEnabled')
      expect(state).toHaveProperty('soundEnabled')
      
      // Display
      expect(state).toHaveProperty('compactMode')
      expect(state).toHaveProperty('showHints')
      expect(state).toHaveProperty('animationsEnabled')
    })

    it('should have default notification settings', () => {
      const state = useSettingsStore.getState()
      
      expect(state.notificationsEnabled).toBe(true)
      expect(state.soundEnabled).toBe(false)
      expect(state.showStreakReminders).toBe(true)
    })

    it('should have default display settings', () => {
      const state = useSettingsStore.getState()
      
      expect(state.compactMode).toBe(false)
      expect(state.showHints).toBe(true)
    })
  })

  describe('setPreferredSessionLength', () => {
    it('should update session length', () => {
      useSettingsStore.getState().setPreferredSessionLength(30)
      
      expect(useSettingsStore.getState().preferredSessionLength).toBe(30)
    })
  })

  describe('setDailyReviewGoal', () => {
    it('should update daily review goal', () => {
      useSettingsStore.getState().setDailyReviewGoal(50)
      
      expect(useSettingsStore.getState().dailyReviewGoal).toBe(50)
    })
  })

  describe('toggleKeyboardShortcuts', () => {
    it('should toggle keyboard shortcuts', () => {
      const initial = useSettingsStore.getState().keyboardShortcutsEnabled
      
      useSettingsStore.getState().toggleKeyboardShortcuts()
      
      expect(useSettingsStore.getState().keyboardShortcutsEnabled).toBe(!initial)
    })
  })

  describe('toggleAnimations', () => {
    it('should toggle animations', () => {
      const initial = useSettingsStore.getState().animationsEnabled
      
      useSettingsStore.getState().toggleAnimations()
      
      expect(useSettingsStore.getState().animationsEnabled).toBe(!initial)
    })
  })

  describe('toggleSidebar', () => {
    it('should toggle sidebar collapsed state', () => {
      const initial = useSettingsStore.getState().sidebarCollapsed
      
      useSettingsStore.getState().toggleSidebar()
      
      expect(useSettingsStore.getState().sidebarCollapsed).toBe(!initial)
    })

    it('should toggle back to original state', () => {
      const initial = useSettingsStore.getState().sidebarCollapsed
      
      useSettingsStore.getState().toggleSidebar()
      useSettingsStore.getState().toggleSidebar()
      
      expect(useSettingsStore.getState().sidebarCollapsed).toBe(initial)
    })
  })

  describe('setSidebarCollapsed', () => {
    it('should set sidebar to collapsed', () => {
      useSettingsStore.getState().setSidebarCollapsed(true)
      
      expect(useSettingsStore.getState().sidebarCollapsed).toBe(true)
    })

    it('should set sidebar to expanded', () => {
      useSettingsStore.setState({ sidebarCollapsed: true })
      
      useSettingsStore.getState().setSidebarCollapsed(false)
      
      expect(useSettingsStore.getState().sidebarCollapsed).toBe(false)
    })
  })

  describe('setTheme', () => {
    it('should update theme', () => {
      useSettingsStore.getState().setTheme('light')
      
      expect(useSettingsStore.getState().theme).toBe('light')
    })
  })

  describe('toggleNotifications', () => {
    it('should toggle notifications', () => {
      const initial = useSettingsStore.getState().notificationsEnabled
      
      useSettingsStore.getState().toggleNotifications()
      
      expect(useSettingsStore.getState().notificationsEnabled).toBe(!initial)
    })
  })

  describe('toggleSound', () => {
    it('should toggle sound', () => {
      const initial = useSettingsStore.getState().soundEnabled
      
      useSettingsStore.getState().toggleSound()
      
      expect(useSettingsStore.getState().soundEnabled).toBe(!initial)
    })
  })

  describe('toggleCompactMode', () => {
    it('should toggle compact mode', () => {
      const initial = useSettingsStore.getState().compactMode
      
      useSettingsStore.getState().toggleCompactMode()
      
      expect(useSettingsStore.getState().compactMode).toBe(!initial)
    })
  })

  describe('toggleHints', () => {
    it('should toggle hints', () => {
      const initial = useSettingsStore.getState().showHints
      
      useSettingsStore.getState().toggleHints()
      
      expect(useSettingsStore.getState().showHints).toBe(!initial)
    })
  })

  describe('updateSettings', () => {
    it('should bulk update settings', () => {
      useSettingsStore.getState().updateSettings({
        preferredSessionLength: 45,
        dailyReviewGoal: 100,
      })
      
      const state = useSettingsStore.getState()
      expect(state.preferredSessionLength).toBe(45)
      expect(state.dailyReviewGoal).toBe(100)
    })

    it('should preserve unchanged settings', () => {
      const originalTheme = useSettingsStore.getState().theme
      
      useSettingsStore.getState().updateSettings({
        preferredSessionLength: 30,
      })
      
      expect(useSettingsStore.getState().theme).toBe(originalTheme)
    })

    it('should update multiple categories at once', () => {
      useSettingsStore.getState().updateSettings({
        theme: 'light',
        preferredSessionLength: 30,
        notificationsEnabled: false,
        compactMode: true,
      })
      
      const state = useSettingsStore.getState()
      expect(state.theme).toBe('light')
      expect(state.preferredSessionLength).toBe(30)
      expect(state.notificationsEnabled).toBe(false)
      expect(state.compactMode).toBe(true)
    })
  })

  describe('resetSettings', () => {
    it('should reset to defaults', () => {
      // Change some settings
      useSettingsStore.getState().setPreferredSessionLength(60)
      useSettingsStore.getState().setDailyReviewGoal(100)
      
      useSettingsStore.getState().resetSettings()
      
      const state = useSettingsStore.getState()
      expect(state.preferredSessionLength).toBe(15)
      expect(state.dailyReviewGoal).toBe(20)
    })

    it('should reset all settings to defaults', () => {
      // Modify all settings
      useSettingsStore.getState().updateSettings({
        theme: 'light',
        sidebarCollapsed: true,
        preferredSessionLength: 60,
        dailyReviewGoal: 100,
        showStreakReminders: false,
        keyboardShortcutsEnabled: false,
        notificationsEnabled: false,
        soundEnabled: true,
        compactMode: true,
        showHints: false,
        animationsEnabled: false,
      })
      
      useSettingsStore.getState().resetSettings()
      
      const state = useSettingsStore.getState()
      expect(state.theme).toBe('dark')
      expect(state.sidebarCollapsed).toBe(false)
      expect(state.preferredSessionLength).toBe(15)
      expect(state.dailyReviewGoal).toBe(20)
      expect(state.showStreakReminders).toBe(true)
      expect(state.keyboardShortcutsEnabled).toBe(true)
      expect(state.notificationsEnabled).toBe(true)
      expect(state.soundEnabled).toBe(false)
      expect(state.compactMode).toBe(false)
      expect(state.showHints).toBe(true)
      expect(state.animationsEnabled).toBe(true)
    })
  })

  describe('selectors', () => {
    it('should get session length options', () => {
      const options = useSettingsStore.getState().getSessionLengthOptions()
      
      expect(Array.isArray(options)).toBe(true)
      expect(options).toContain(15)
      expect(options).toContain(30)
    })

    it('should get review goal options', () => {
      const options = useSettingsStore.getState().getReviewGoalOptions()
      
      expect(Array.isArray(options)).toBe(true)
      expect(options).toContain(20)
      expect(options).toContain(50)
    })
  })
})
