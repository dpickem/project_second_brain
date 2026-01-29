/**
 * Main Application Component
 * 
 * Sets up routing, global providers, and layout.
 */

import { lazy, Suspense } from 'react'
import { Routes, Route, NavLink, useLocation } from 'react-router-dom'
import { AnimatePresence, motion } from 'framer-motion'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Toaster } from 'react-hot-toast'
import { clsx } from 'clsx'
import PropTypes from 'prop-types'
import { PageLoader, Tooltip, CommandPalette, PageErrorBoundary } from './components/common'
import { useSettingsStore } from './stores'
import { pageTransition } from './utils/animations'

// Lazy load pages for code splitting
const Dashboard = lazy(() => import('./pages/Dashboard'))
const Knowledge = lazy(() => import('./pages/Knowledge'))
const KnowledgeGraphPage = lazy(() => import('./pages/KnowledgeGraph'))
const PracticeSession = lazy(() => import('./pages/PracticeSession'))
const Exercises = lazy(() => import('./pages/Exercises'))
const CardCatalogue = lazy(() => import('./pages/CardCatalogue'))
const ReviewQueue = lazy(() => import('./pages/ReviewQueue'))
const Analytics = lazy(() => import('./pages/Analytics'))
const Assistant = lazy(() => import('./pages/Assistant'))
const LLMUsage = lazy(() => import('./pages/LLMUsage'))
const Tasks = lazy(() => import('./pages/Tasks'))
const Settings = lazy(() => import('./pages/Settings'))

// Create a query client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 60 * 1000, // 1 minute
      cacheTime: 5 * 60 * 1000, // 5 minutes
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
})

// Navigation component
function Navigation() {
  const sidebarCollapsed = useSettingsStore((s) => s.sidebarCollapsed)
  
  return (
    <nav className={clsx(
      'fixed top-0 left-0 h-full bg-bg-secondary border-r border-border-primary',
      'flex flex-col items-center py-4 z-sticky transition-all duration-300',
      sidebarCollapsed ? 'w-16' : 'w-16'
    )}>
      {/* Logo */}
      <div className="w-10 h-10 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-xl flex items-center justify-center mb-8 shadow-lg shadow-indigo-600/20">
        <svg
          className="w-6 h-6 text-white"
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

      {/* Main Nav Links */}
      <div className="flex flex-col gap-2">
        <NavItem to="/" icon={<HomeIcon />} title="Dashboard" shortcut="⌘1" />
        <NavItem to="/practice" icon={<PracticeIcon />} title="Practice" shortcut="⌘2" />
        <NavItem to="/exercises" icon={<ExercisesIcon />} title="Exercises" shortcut="⌘3" />
        <NavItem to="/cards" icon={<CardsIcon />} title="Cards" shortcut="⌘4" />
        <NavItem to="/review" icon={<ReviewIcon />} title="Review" shortcut="⌘5" />
        <NavItem to="/tasks" icon={<TasksIcon />} title="Tasks" shortcut="⌘6" />
        <NavItem to="/knowledge" icon={<KnowledgeIcon />} title="Knowledge" shortcut="⌘7" />
        <NavItem to="/graph" icon={<GraphIcon />} title="Graph" shortcut="⌘8" />
        <NavItem to="/analytics" icon={<AnalyticsIcon />} title="Analytics" shortcut="⌘9" />
        <NavItem to="/assistant" icon={<AssistantIcon />} title="Assistant" />
        <NavItem to="/llm-usage" icon={<CostIcon />} title="LLM Costs" />
      </div>

      {/* Spacer */}
      <div className="flex-1" />

      {/* Settings */}
      <NavItem to="/settings" icon={<SettingsIcon />} title="Settings" />
    </nav>
  )
}

function NavItem({ to, icon, title, shortcut }) {
  return (
    <Tooltip 
      content={
        <span className="flex items-center gap-2">
          {title}
          {shortcut && (
            <kbd className="px-1.5 py-0.5 text-xs bg-slate-600 rounded">{shortcut}</kbd>
          )}
        </span>
      } 
      side="right"
    >
      <NavLink
        to={to}
        className={({ isActive }) =>
          clsx(
            'w-10 h-10 rounded-xl flex items-center justify-center transition-all duration-200',
            isActive
              ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-600/30'
              : 'text-text-muted hover:text-text-primary hover:bg-bg-hover'
          )
        }
      >
        {icon}
      </NavLink>
    </Tooltip>
  )
}

NavItem.propTypes = {
  to: PropTypes.string.isRequired,
  icon: PropTypes.node.isRequired,
  title: PropTypes.string.isRequired,
  shortcut: PropTypes.string,
}

// Icons
function HomeIcon() {
  return (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
    </svg>
  )
}

function PracticeIcon() {
  return (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
  )
}

function ExercisesIcon() {
  return (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01" />
    </svg>
  )
}

function CardsIcon() {
  return (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
    </svg>
  )
}

function ReviewIcon() {
  return (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
    </svg>
  )
}

function TasksIcon() {
  return (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
    </svg>
  )
}

function KnowledgeIcon() {
  return (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
    </svg>
  )
}

function GraphIcon() {
  return (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <circle cx="5" cy="6" r="2" strokeWidth={2} />
      <circle cx="12" cy="4" r="2" strokeWidth={2} />
      <circle cx="19" cy="8" r="2" strokeWidth={2} />
      <circle cx="6" cy="18" r="2" strokeWidth={2} />
      <circle cx="18" cy="18" r="2" strokeWidth={2} />
      <circle cx="12" cy="12" r="2.5" strokeWidth={2} />
      <path strokeLinecap="round" strokeWidth={1.5} d="M7 7l3.5 3.5M14.5 10l3-1M9.5 12.5l-2 4M14.5 13.5l2 3M12 14.5v0" />
    </svg>
  )
}

function AnalyticsIcon() {
  return (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
    </svg>
  )
}

function AssistantIcon() {
  return (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
    </svg>
  )
}

function CostIcon() {
  return (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
  )
}

function SettingsIcon() {
  return (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
    </svg>
  )
}

// Animated page wrapper
function AnimatedPage({ children }) {
  return (
    <motion.div
      initial={pageTransition.initial}
      animate={pageTransition.animate}
      exit={pageTransition.exit}
      transition={pageTransition.transition}
    >
      {children}
    </motion.div>
  )
}

AnimatedPage.propTypes = {
  children: PropTypes.node.isRequired,
}

function App() {
  const location = useLocation()

  return (
    <QueryClientProvider client={queryClient}>
      <div className="flex min-h-screen bg-bg-primary">
        <Navigation />
        
        <main className="flex-1 ml-16">
          <PageErrorBoundary resetKey={location.pathname}>
            <Suspense fallback={<PageLoader />}>
              <AnimatePresence mode="wait">
                <Routes location={location} key={location.pathname}>
                  <Route path="/" element={<AnimatedPage><Dashboard /></AnimatedPage>} />
                  <Route path="/practice" element={<AnimatedPage><PracticeSession /></AnimatedPage>} />
                  <Route path="/practice/:topicId" element={<AnimatedPage><PracticeSession /></AnimatedPage>} />
                  <Route path="/exercises" element={<AnimatedPage><Exercises /></AnimatedPage>} />
                  <Route path="/cards" element={<AnimatedPage><CardCatalogue /></AnimatedPage>} />
                  <Route path="/review" element={<AnimatedPage><ReviewQueue /></AnimatedPage>} />
                  <Route path="/knowledge" element={<AnimatedPage><Knowledge /></AnimatedPage>} />
                  <Route path="/graph" element={<AnimatedPage><KnowledgeGraphPage /></AnimatedPage>} />
                  <Route path="/analytics" element={<AnimatedPage><Analytics /></AnimatedPage>} />
                  <Route path="/analytics/:topicId" element={<AnimatedPage><Analytics /></AnimatedPage>} />
                  <Route path="/assistant" element={<AnimatedPage><Assistant /></AnimatedPage>} />
                  <Route path="/llm-usage" element={<AnimatedPage><LLMUsage /></AnimatedPage>} />
                  <Route path="/tasks" element={<AnimatedPage><Tasks /></AnimatedPage>} />
                  <Route path="/settings" element={<AnimatedPage><Settings /></AnimatedPage>} />
                </Routes>
              </AnimatePresence>
            </Suspense>
          </PageErrorBoundary>
        </main>

        {/* Command Palette */}
        <CommandPalette />

        {/* Toast notifications */}
        <Toaster
          position="bottom-right"
          toastOptions={{
            className: 'toast-custom',
            duration: 4000,
            style: {
              background: 'var(--color-bg-elevated)',
              color: 'var(--color-text-primary)',
              border: '1px solid var(--color-border-primary)',
              borderRadius: 'var(--radius-lg)',
            },
            success: {
              iconTheme: {
                primary: 'var(--color-accent-success)',
                secondary: 'white',
              },
            },
            error: {
              iconTheme: {
                primary: 'var(--color-accent-danger)',
                secondary: 'white',
              },
            },
          }}
        />
      </div>
    </QueryClientProvider>
  )
}

export default App
