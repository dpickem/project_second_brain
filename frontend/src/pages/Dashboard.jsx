/**
 * Dashboard Page
 * 
 * The user's home screen - answering "What should I do today?" at a glance.
 */

import { motion } from 'framer-motion'
import { useQuery } from '@tanstack/react-query'
import { clsx } from 'clsx'
import { 
  StatsHeader, 
  PracticeActionCard, 
  ReviewActionCard,
  DueCardsPreview,
  WeakSpotsList,
  QuickCapture,
  StreakCalendar,
} from '../components/dashboard'
import { PageLoader } from '../components/common'
import { analyticsApi } from '../api/analytics'
import { reviewApi } from '../api/review'
import { staggerContainer, fadeInUp } from '../utils/animations'

export function Dashboard() {
  // Fetch dashboard data
  const { data: dailyStats, isLoading: statsLoading } = useQuery({
    queryKey: ['daily-stats'],
    queryFn: analyticsApi.getDailyStats,
    staleTime: 60 * 1000, // 1 minute
  })

  const { data: dueCardsData, isLoading: dueLoading } = useQuery({
    queryKey: ['due-cards', { limit: 5 }],
    queryFn: () => reviewApi.getDueCards({ limit: 5 }),
    staleTime: 60 * 1000,
  })

  const { data: weakSpots, isLoading: weakSpotsLoading } = useQuery({
    queryKey: ['weak-spots', { limit: 5 }],
    queryFn: () => analyticsApi.getWeakSpots({ limit: 5 }),
    staleTime: 5 * 60 * 1000, // 5 minutes
  })

  const { data: activityData, isLoading: activityLoading } = useQuery({
    queryKey: ['practice-history', { weeks: 26 }],
    queryFn: () => analyticsApi.getPracticeHistory({ weeks: 26 }),
    staleTime: 10 * 60 * 1000, // 10 minutes
  })

  // Use API data with empty defaults
  const stats = dailyStats || {
    streak: 0,
    due_count: 0,
    today_reviewed: 0,
    daily_goal: 20,
  }

  const dueCards = dueCardsData?.cards || []
  const totalDue = dueCardsData?.total || stats.due_count || 0
  const topics = weakSpots?.topics || []
  const activity = activityData?.activity || []

  const isInitialLoading = statsLoading && dueLoading && weakSpotsLoading

  if (isInitialLoading) {
    return <PageLoader message="Loading your dashboard..." />
  }

  return (
    <div className="min-h-screen bg-bg-primary p-6 lg:p-8">
      <div className="max-w-7xl mx-auto">
        <motion.div
          variants={staggerContainer}
          initial="hidden"
          animate="show"
          className="space-y-8"
        >
          {/* Stats Header */}
          <motion.div variants={fadeInUp}>
            <StatsHeader
              streak={stats.streak}
              dueCount={totalDue}
              todayReviewed={stats.today_reviewed}
              dailyGoal={stats.daily_goal}
            />
          </motion.div>

          {/* Main Grid - Learning Section */}
          <motion.div variants={fadeInUp} className="space-y-4">
            <h2 className="text-sm font-medium text-text-muted uppercase tracking-wide">
              Continue Learning
            </h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
              {/* Practice Action */}
              <PracticeActionCard />

              {/* Due Cards Preview */}
              <DueCardsPreview
                cards={dueCards}
                totalDue={totalDue}
                isLoading={dueLoading}
              />

              {/* Focus Areas */}
              <WeakSpotsList
                topics={topics}
                isLoading={weakSpotsLoading}
              />
            </div>
          </motion.div>

          {/* Secondary Row */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
            {/* Review Action */}
            <motion.div variants={fadeInUp}>
              <ReviewActionCard dueCount={totalDue} />
            </motion.div>

            {/* Quick Capture */}
            <motion.div variants={fadeInUp}>
              <QuickCapture />
            </motion.div>

            {/* Activity Calendar */}
            <motion.div variants={fadeInUp}>
              <StreakCalendar
                activityData={activity}
                isLoading={activityLoading}
              />
            </motion.div>
          </div>

          {/* Quick Links */}
          <motion.div variants={fadeInUp}>
            <h2 className="text-sm font-medium text-text-muted uppercase tracking-wide mb-4">
              Quick Links
            </h2>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
              <QuickLink
                to="/knowledge"
                icon="🕸️"
                title="Knowledge Graph"
                description="Explore connections"
              />
              <QuickLink
                to="/knowledge"
                icon="📚"
                title="Vault"
                description="Browse notes"
              />
              <QuickLink
                to="/analytics"
                icon="📊"
                title="Analytics"
                description="Track progress"
              />
              <QuickLink
                to="/assistant"
                icon="🤖"
                title="Assistant"
                description="Ask questions"
              />
            </div>
          </motion.div>
        </motion.div>
      </div>
    </div>
  )
}

function QuickLink({ to, icon, title, description }) {
  return (
    <motion.a
      href={to}
      whileHover={{ scale: 1.02, y: -2 }}
      whileTap={{ scale: 0.98 }}
      className={clsx(
        'p-4 rounded-xl border border-border-primary',
        'bg-bg-secondary hover:bg-bg-elevated',
        'transition-colors group'
      )}
    >
      <span className="text-2xl mb-2 block">{icon}</span>
      <h3 className="font-medium text-text-primary group-hover:text-accent-secondary transition-colors">
        {title}
      </h3>
      <p className="text-xs text-text-muted mt-0.5">{description}</p>
    </motion.a>
  )
}

export default Dashboard
