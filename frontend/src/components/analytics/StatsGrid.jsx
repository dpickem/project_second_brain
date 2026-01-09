/**
 * StatsGrid Component
 * 
 * Grid of key learning statistics.
 */

import { motion } from 'framer-motion'
import { clsx } from 'clsx'
import { Card } from '../common'
import { LearningSparkline } from './LearningChart'
import { staggerContainer, fadeInUp, scaleIn } from '../../utils/animations'

export function StatsGrid({
  stats = {},
  className,
}) {
  const {
    totalCards = 0,
    masteredCards = 0,
    totalReviews = 0,
    learningTime = 0,
    streak = 0,
    avgRetention = 0,
  } = stats

  const statItems = [
    {
      label: 'Total Cards',
      value: totalCards.toLocaleString(),
      icon: '📚',
      color: 'indigo',
      description: 'In your library',
    },
    {
      label: 'Mastered',
      value: masteredCards.toLocaleString(),
      icon: '🎯',
      color: 'emerald',
      description: `${totalCards > 0 ? Math.round((masteredCards / totalCards) * 100) : 0}% of total`,
    },
    {
      label: 'Reviews',
      value: totalReviews.toLocaleString(),
      icon: '✅',
      color: 'purple',
      description: 'All time',
    },
    {
      label: 'Learning Time',
      value: `${Math.round(learningTime / 60)}h`,
      icon: '⏱️',
      color: 'amber',
      description: 'All time',
    },
    {
      label: 'Streak',
      value: `${streak}d`,
      icon: '🔥',
      color: 'orange',
      description: 'Keep it going!',
      highlight: streak >= 7,
    },
    {
      label: 'Retention',
      value: `${avgRetention}%`,
      icon: '🧠',
      color: avgRetention >= 80 ? 'emerald' : avgRetention >= 60 ? 'indigo' : 'amber',
      description: 'Average recall',
    },
  ]

  const colorClasses = {
    indigo: 'from-indigo-500/20 to-indigo-500/5 border-indigo-500/30',
    emerald: 'from-emerald-500/20 to-emerald-500/5 border-emerald-500/30',
    purple: 'from-purple-500/20 to-purple-500/5 border-purple-500/30',
    amber: 'from-amber-500/20 to-amber-500/5 border-amber-500/30',
    orange: 'from-orange-500/20 to-orange-500/5 border-orange-500/30',
  }

  return (
    <motion.div
      variants={staggerContainer}
      initial="hidden"
      animate="show"
      className={clsx('grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4', className)}
    >
      {statItems.map((stat, index) => (
        <motion.div
          key={stat.label}
          variants={fadeInUp}
          custom={index}
        >
          <div
            className={clsx(
              'p-4 rounded-xl border bg-gradient-to-br transition-all',
              'hover:scale-[1.02] hover:shadow-lg',
              colorClasses[stat.color],
              stat.highlight && 'ring-2 ring-orange-500/50'
            )}
          >
            <div className="flex items-center justify-between mb-2">
              <span className="text-2xl">{stat.icon}</span>
              {stat.highlight && (
                <motion.span
                  animate={{ scale: [1, 1.2, 1] }}
                  transition={{ duration: 1, repeat: Infinity }}
                  className="text-xs"
                >
                  🎉
                </motion.span>
              )}
            </div>
            
            <motion.div
              variants={scaleIn}
              className="text-2xl font-bold text-text-primary font-heading"
            >
              {stat.value}
            </motion.div>
            
            <p className="text-sm text-text-secondary mt-1">{stat.label}</p>
            <p className="text-xs text-text-muted">{stat.description}</p>
          </div>
        </motion.div>
      ))}
    </motion.div>
  )
}

// Single stat card with sparkline
export function StatCard({
  label,
  value,
  change,
  changeLabel,
  sparklineData,
  icon,
  className,
}) {
  const isPositive = change > 0
  const isNegative = change < 0

  return (
    <Card className={clsx('relative overflow-hidden', className)}>
      <div className="flex items-start justify-between">
        <div>
          {icon && <span className="text-2xl mb-2 block">{icon}</span>}
          <p className="text-sm text-text-secondary">{label}</p>
          <p className="text-3xl font-bold text-text-primary font-heading mt-1">
            {value}
          </p>
          
          {change !== undefined && (
            <div className="flex items-center gap-1 mt-2">
              <span className={clsx(
                'text-sm font-medium',
                isPositive && 'text-emerald-400',
                isNegative && 'text-red-400',
                !isPositive && !isNegative && 'text-text-muted'
              )}>
                {isPositive && '+'}
                {change}%
              </span>
              {changeLabel && (
                <span className="text-xs text-text-muted">{changeLabel}</span>
              )}
            </div>
          )}
        </div>
        
        {sparklineData && (
          <div className="w-24">
            <LearningSparkline
              data={sparklineData}
              color={isPositive ? '#34d399' : isNegative ? '#f87171' : '#6366f1'}
            />
          </div>
        )}
      </div>
    </Card>
  )
}

export default StatsGrid
