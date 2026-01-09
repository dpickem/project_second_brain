/**
 * StatsHeader Component
 * 
 * Personalized greeting with streak badge and due count.
 */

import { motion } from 'framer-motion'
import { clsx } from 'clsx'
import { fadeInUp } from '../../utils/animations'

function getGreeting() {
  const hour = new Date().getHours()
  if (hour < 12) return 'Good morning'
  if (hour < 17) return 'Good afternoon'
  return 'Good evening'
}

function getGreetingEmoji() {
  const hour = new Date().getHours()
  if (hour < 12) return '🌅'
  if (hour < 17) return '☀️'
  return '🌙'
}

export function StatsHeader({ 
  userName = 'there',
  streak = 0,
  dueCount = 0,
  todayReviewed = 0,
  dailyGoal = 20,
  className,
}) {
  const greeting = getGreeting()
  const emoji = getGreetingEmoji()
  const hasStreak = streak > 0
  const goalProgress = dailyGoal > 0 ? Math.min(100, Math.round((todayReviewed / dailyGoal) * 100)) : 0
  const goalComplete = goalProgress >= 100

  return (
    <motion.div
      variants={fadeInUp}
      initial="hidden"
      animate="show"
      className={clsx(
        'flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4',
        className
      )}
    >
      {/* Greeting */}
      <div>
        <h1 className="text-2xl sm:text-3xl font-bold text-text-primary font-heading">
          {greeting}, {userName}! {emoji}
        </h1>
        <p className="text-text-secondary mt-1">
          {dueCount > 0 ? (
            <>You have <span className="text-accent-primary font-medium">{dueCount} cards</span> due today</>
          ) : (
            <>All caught up! Great job staying on top of your learning.</>
          )}
        </p>
      </div>

      {/* Stats Badges */}
      <div className="flex items-center gap-3 flex-wrap">
        {/* Streak Badge */}
        {hasStreak && (
          <motion.div
            initial={{ scale: 0.8, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ delay: 0.2, type: 'spring', stiffness: 200 }}
          >
            <div className={clsx(
              'flex items-center gap-2 px-4 py-2 rounded-xl',
              'bg-gradient-to-r from-amber-500/20 to-orange-500/20',
              'border border-amber-500/30'
            )}>
              <span className="text-xl">🔥</span>
              <div>
                <p className="text-sm font-semibold text-amber-300">{streak}-day streak</p>
                <p className="text-xs text-amber-400/70">Keep it up!</p>
              </div>
            </div>
          </motion.div>
        )}

        {/* Daily Goal Progress */}
        <motion.div
          initial={{ scale: 0.8, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ delay: 0.3, type: 'spring', stiffness: 200 }}
        >
          <div className={clsx(
            'flex items-center gap-3 px-4 py-2 rounded-xl',
            goalComplete
              ? 'bg-emerald-500/20 border border-emerald-500/30'
              : 'bg-slate-800/50 border border-slate-700'
          )}>
            <div className="relative w-10 h-10">
              {/* Circular progress */}
              <svg className="w-10 h-10 transform -rotate-90">
                <circle
                  cx="20"
                  cy="20"
                  r="16"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="3"
                  className="text-slate-700"
                />
                <motion.circle
                  cx="20"
                  cy="20"
                  r="16"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="3"
                  strokeLinecap="round"
                  className={goalComplete ? 'text-emerald-400' : 'text-indigo-400'}
                  strokeDasharray={`${2 * Math.PI * 16}`}
                  initial={{ strokeDashoffset: 2 * Math.PI * 16 }}
                  animate={{ 
                    strokeDashoffset: 2 * Math.PI * 16 * (1 - goalProgress / 100) 
                  }}
                  transition={{ duration: 1, ease: 'easeOut', delay: 0.5 }}
                />
              </svg>
              {/* Center icon/text */}
              <div className="absolute inset-0 flex items-center justify-center">
                {goalComplete ? (
                  <span className="text-sm">✓</span>
                ) : (
                  <span className="text-xs font-medium text-text-secondary">{goalProgress}%</span>
                )}
              </div>
            </div>
            <div>
              <p className={clsx(
                'text-sm font-semibold',
                goalComplete ? 'text-emerald-300' : 'text-text-primary'
              )}>
                {todayReviewed}/{dailyGoal}
              </p>
              <p className={clsx(
                'text-xs',
                goalComplete ? 'text-emerald-400/70' : 'text-text-muted'
              )}>
                {goalComplete ? 'Goal reached!' : 'Daily goal'}
              </p>
            </div>
          </div>
        </motion.div>
      </div>
    </motion.div>
  )
}

export default StatsHeader
