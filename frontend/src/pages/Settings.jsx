/**
 * Settings Page
 * 
 * User preferences and application settings.
 */

import { motion } from 'framer-motion'
import { clsx } from 'clsx'
import { 
  Card, 
  CardHeader, 
  CardTitle, 
  CardDescription, 
  CardContent,
  Button,
  Select,
} from '../components/common'
import { useSettingsStore } from '../stores'
import { fadeInUp, staggerContainer } from '../utils/animations'

export function Settings() {
  const {
    sidebarCollapsed,
    preferredSessionLength,
    dailyReviewGoal,
    keyboardShortcutsEnabled,
    notificationsEnabled,
    soundEnabled,
    compactMode,
    showHints,
    animationsEnabled,
    setPreferredSessionLength,
    setDailyReviewGoal,
    toggleKeyboardShortcuts,
    toggleNotifications,
    toggleSound,
    toggleCompactMode,
    toggleHints,
    toggleAnimations,
    toggleSidebar,
    resetSettings,
    getSessionLengthOptions,
    getReviewGoalOptions,
  } = useSettingsStore()

  const sessionLengthOptions = getSessionLengthOptions().map(v => ({
    value: v.toString(),
    label: `${v} minutes`,
  }))

  const reviewGoalOptions = getReviewGoalOptions().map(v => ({
    value: v.toString(),
    label: `${v} cards`,
  }))

  return (
    <div className="min-h-screen bg-bg-primary p-6 lg:p-8">
      <div className="max-w-3xl mx-auto">
        <motion.div
          variants={staggerContainer}
          initial="hidden"
          animate="show"
          className="space-y-8"
        >
          {/* Header */}
          <motion.div variants={fadeInUp}>
            <h1 className="text-3xl font-bold text-text-primary font-heading mb-2">
              Settings
            </h1>
            <p className="text-text-secondary">
              Customize your learning experience
            </p>
          </motion.div>

          {/* Appearance */}
          <motion.div variants={fadeInUp}>
            <Card>
              <CardHeader>
                <CardTitle>🎨 Appearance</CardTitle>
                <CardDescription>Customize how the app looks</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <SettingRow
                  label="Dark Theme"
                  description="Currently the only available theme"
                >
                  <span className="text-sm text-text-muted">Active</span>
                </SettingRow>

                <SettingRow
                  label="Compact Mode"
                  description="Show more content with less spacing"
                >
                  <Toggle checked={compactMode} onChange={toggleCompactMode} />
                </SettingRow>

                <SettingRow
                  label="Animations"
                  description="Enable smooth transitions and effects"
                >
                  <Toggle checked={animationsEnabled} onChange={toggleAnimations} />
                </SettingRow>

                <SettingRow
                  label="Collapsed Sidebar"
                  description="Start with sidebar minimized"
                >
                  <Toggle checked={sidebarCollapsed} onChange={toggleSidebar} />
                </SettingRow>
              </CardContent>
            </Card>
          </motion.div>

          {/* Learning */}
          <motion.div variants={fadeInUp}>
            <Card>
              <CardHeader>
                <CardTitle>📚 Learning</CardTitle>
                <CardDescription>Configure your learning preferences</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <SettingRow
                  label="Default Session Length"
                  description="Duration for practice sessions"
                >
                  <Select
                    options={sessionLengthOptions}
                    value={preferredSessionLength.toString()}
                    onChange={(e) => setPreferredSessionLength(parseInt(e.target.value))}
                    className="w-32"
                  />
                </SettingRow>

                <SettingRow
                  label="Daily Review Goal"
                  description="Target cards to review each day"
                >
                  <Select
                    options={reviewGoalOptions}
                    value={dailyReviewGoal.toString()}
                    onChange={(e) => setDailyReviewGoal(parseInt(e.target.value))}
                    className="w-32"
                  />
                </SettingRow>

                <SettingRow
                  label="Show Hints"
                  description="Display helpful tips during practice"
                >
                  <Toggle checked={showHints} onChange={toggleHints} />
                </SettingRow>
              </CardContent>
            </Card>
          </motion.div>

          {/* Keyboard Shortcuts */}
          <motion.div variants={fadeInUp}>
            <Card>
              <CardHeader>
                <CardTitle>⌨️ Keyboard Shortcuts</CardTitle>
                <CardDescription>Quick access to common actions</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <SettingRow
                  label="Enable Shortcuts"
                  description="Use keyboard shortcuts for navigation"
                >
                  <Toggle checked={keyboardShortcutsEnabled} onChange={toggleKeyboardShortcuts} />
                </SettingRow>

                {keyboardShortcutsEnabled && (
                  <div className="mt-4 p-4 bg-bg-tertiary rounded-lg">
                    <h4 className="text-sm font-medium text-text-primary mb-3">Available Shortcuts</h4>
                    <div className="grid grid-cols-2 gap-2 text-sm">
                      <ShortcutRow keys="⌘K" description="Command Palette" />
                      <ShortcutRow keys="⌘N" description="Quick Capture" />
                      <ShortcutRow keys="⌘1" description="Dashboard" />
                      <ShortcutRow keys="⌘2" description="Practice" />
                      <ShortcutRow keys="⌘3" description="Review" />
                      <ShortcutRow keys="⌘4" description="Knowledge" />
                      <ShortcutRow keys="⌘5" description="Analytics" />
                      <ShortcutRow keys="⌘6" description="Vault" />
                      <ShortcutRow keys="Esc" description="Close Overlays" />
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          </motion.div>

          {/* Notifications */}
          <motion.div variants={fadeInUp}>
            <Card>
              <CardHeader>
                <CardTitle>🔔 Notifications</CardTitle>
                <CardDescription>Control alerts and reminders</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <SettingRow
                  label="Enable Notifications"
                  description="Receive reminders and updates"
                >
                  <Toggle checked={notificationsEnabled} onChange={toggleNotifications} />
                </SettingRow>

                <SettingRow
                  label="Sound Effects"
                  description="Play sounds for actions"
                >
                  <Toggle checked={soundEnabled} onChange={toggleSound} />
                </SettingRow>
              </CardContent>
            </Card>
          </motion.div>

          {/* Data & Privacy */}
          <motion.div variants={fadeInUp}>
            <Card>
              <CardHeader>
                <CardTitle>🔒 Data & Privacy</CardTitle>
                <CardDescription>Manage your data</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <SettingRow
                  label="Export Data"
                  description="Download all your notes and progress"
                >
                  <Button variant="secondary" size="sm" disabled>
                    Coming Soon
                  </Button>
                </SettingRow>

                <SettingRow
                  label="Reset Settings"
                  description="Restore all settings to defaults"
                >
                  <Button 
                    variant="danger" 
                    size="sm"
                    onClick={() => {
                      if (confirm('Reset all settings to defaults?')) {
                        resetSettings()
                      }
                    }}
                  >
                    Reset
                  </Button>
                </SettingRow>
              </CardContent>
            </Card>
          </motion.div>

          {/* About */}
          <motion.div variants={fadeInUp}>
            <Card variant="ghost" className="text-center py-8">
              <div className="w-16 h-16 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-2xl flex items-center justify-center mx-auto mb-4 shadow-lg shadow-indigo-600/20">
                <svg
                  className="w-10 h-10 text-white"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"
                  />
                </svg>
              </div>
              <h3 className="text-xl font-semibold text-text-primary font-heading mb-1">
                Second Brain
              </h3>
              <p className="text-text-muted text-sm">
                Version 0.1.0 • Built with ❤️
              </p>
            </Card>
          </motion.div>
        </motion.div>
      </div>
    </div>
  )
}

// Setting row component
function SettingRow({ label, description, children }) {
  return (
    <div className="flex items-center justify-between py-2">
      <div>
        <p className="text-sm font-medium text-text-primary">{label}</p>
        <p className="text-xs text-text-muted">{description}</p>
      </div>
      {children}
    </div>
  )
}

// Toggle switch component
function Toggle({ checked, onChange }) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      onClick={onChange}
      className={clsx(
        'relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent',
        'transition-colors duration-200 ease-in-out',
        'focus:outline-none focus-visible:ring-2 focus-visible:ring-accent-primary focus-visible:ring-offset-2 focus-visible:ring-offset-bg-primary',
        checked ? 'bg-accent-primary' : 'bg-slate-600'
      )}
    >
      <span
        className={clsx(
          'pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0',
          'transition duration-200 ease-in-out',
          checked ? 'translate-x-5' : 'translate-x-0'
        )}
      />
    </button>
  )
}

// Shortcut row component
function ShortcutRow({ keys, description }) {
  return (
    <div className="flex items-center justify-between py-1">
      <span className="text-text-secondary">{description}</span>
      <kbd className="px-2 py-1 bg-slate-700 text-slate-300 rounded text-xs font-mono">
        {keys}
      </kbd>
    </div>
  )
}

export default Settings
