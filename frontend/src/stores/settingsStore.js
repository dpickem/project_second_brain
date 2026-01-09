/**
 * Settings Store
 * 
 * Zustand store for user preferences with localStorage persistence.
 */

import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export const useSettingsStore = create(
  persist(
    (set) => ({
      // =====================
      // State
      // =====================
      
      // Appearance
      theme: 'dark', // 'dark' | 'light' (future)
      sidebarCollapsed: false,
      
      // Learning preferences
      preferredSessionLength: 15, // minutes
      dailyReviewGoal: 20, // cards per day
      showStreakReminders: true,
      
      // Keyboard shortcuts
      keyboardShortcutsEnabled: true,
      
      // Notifications
      notificationsEnabled: true,
      soundEnabled: false,
      
      // Display
      compactMode: false,
      showHints: true,
      animationsEnabled: true,
      
      // =====================
      // Actions
      // =====================
      
      setTheme: (theme) => set({ theme }),
      
      toggleSidebar: () => set((state) => ({ 
        sidebarCollapsed: !state.sidebarCollapsed 
      })),
      
      setSidebarCollapsed: (collapsed) => set({ 
        sidebarCollapsed: collapsed 
      }),
      
      setPreferredSessionLength: (minutes) => set({ 
        preferredSessionLength: minutes 
      }),
      
      setDailyReviewGoal: (cards) => set({ 
        dailyReviewGoal: cards 
      }),
      
      toggleKeyboardShortcuts: () => set((state) => ({
        keyboardShortcutsEnabled: !state.keyboardShortcutsEnabled
      })),
      
      toggleNotifications: () => set((state) => ({
        notificationsEnabled: !state.notificationsEnabled
      })),
      
      toggleSound: () => set((state) => ({
        soundEnabled: !state.soundEnabled
      })),
      
      toggleCompactMode: () => set((state) => ({
        compactMode: !state.compactMode
      })),
      
      toggleHints: () => set((state) => ({
        showHints: !state.showHints
      })),
      
      toggleAnimations: () => set((state) => ({
        animationsEnabled: !state.animationsEnabled
      })),
      
      // Bulk update settings
      updateSettings: (updates) => set((state) => ({
        ...state,
        ...updates,
      })),
      
      // Reset to defaults
      resetSettings: () => set({
        theme: 'dark',
        sidebarCollapsed: false,
        preferredSessionLength: 15,
        dailyReviewGoal: 20,
        showStreakReminders: true,
        keyboardShortcutsEnabled: true,
        notificationsEnabled: true,
        soundEnabled: false,
        compactMode: false,
        showHints: true,
        animationsEnabled: true,
      }),
      
      // =====================
      // Selectors
      // =====================
      
      getSessionLengthOptions: () => [5, 10, 15, 20, 30, 45, 60],
      getReviewGoalOptions: () => [5, 10, 15, 20, 30, 50, 100],
    }),
    {
      name: 'second-brain-settings',
      version: 1,
      // Only persist specific fields
      partialize: (state) => ({
        theme: state.theme,
        sidebarCollapsed: state.sidebarCollapsed,
        preferredSessionLength: state.preferredSessionLength,
        dailyReviewGoal: state.dailyReviewGoal,
        showStreakReminders: state.showStreakReminders,
        keyboardShortcutsEnabled: state.keyboardShortcutsEnabled,
        notificationsEnabled: state.notificationsEnabled,
        soundEnabled: state.soundEnabled,
        compactMode: state.compactMode,
        showHints: state.showHints,
        animationsEnabled: state.animationsEnabled,
      }),
    }
  )
)

export default useSettingsStore
