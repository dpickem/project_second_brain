/**
 * StatsGrid Component
 * 
 * Grid of key learning statistics with separate breakdowns for
 * spaced repetition cards and exercises.
 */

import { useState } from 'react'
import { motion } from 'framer-motion'
import { clsx } from 'clsx'
import { Card } from '../common'
import { LearningSparkline } from './LearningChart'
import { staggerContainer, fadeInUp, scaleIn } from '../../utils/animations'

export function StatsGrid({
  stats = {},
  viewMode = 'combined', // 'combined', 'cards', 'exercises'
  onViewModeChange,
  className,
}) {
  // Use controlled mode if onViewModeChange is provided, otherwise manage locally
  const [localViewMode, setLocalViewMode] = useState('combined')
  const currentViewMode = onViewModeChange ? viewMode : localViewMode
  const handleViewModeChange = onViewModeChange || setLocalViewMode
  
  const {
    // General stats
    learningTime = 0,
    streak = 0,
    avgRetention = 0,
    // Spaced rep card stats
    spacedRepCardsTotal = 0,
    spacedRepCardsMastered = 0,
    spacedRepCardsLearning = 0,
    spacedRepCardsNew = 0,
    spacedRepReviewsTotal = 0,
    // Exercise stats
    exercisesTotal = 0,
    exercisesCompleted = 0,
    exercisesMastered = 0,
    exercisesAttemptsTotal = 0,
    exercisesAvgScore = 0,
  } = stats
  
  // Compute combined totals for combined view
  const totalItems = spacedRepCardsTotal + exercisesTotal
  const totalMastered = spacedRepCardsMastered + exercisesMastered

  // Build stats based on view mode
  const getStatItems = () => {
    if (currentViewMode === 'cards') {
      return [
        {
          label: 'Flashcards',
          value: spacedRepCardsTotal.toLocaleString(),
          icon: '🃏',
          color: 'indigo',
          description: 'Spaced repetition cards',
        },
        {
          label: 'Mastered',
          value: spacedRepCardsMastered.toLocaleString(),
          icon: '🎯',
          color: 'emerald',
          description: `${spacedRepCardsTotal > 0 ? Math.round((spacedRepCardsMastered / spacedRepCardsTotal) * 100) : 0}% of cards`,
        },
        {
          label: 'Learning',
          value: spacedRepCardsLearning.toLocaleString(),
          icon: '📖',
          color: 'amber',
          description: 'In progress',
        },
        {
          label: 'New',
          value: spacedRepCardsNew.toLocaleString(),
          icon: '✨',
          color: 'purple',
          description: 'Ready to learn',
        },
        {
          label: 'Reviews',
          value: spacedRepReviewsTotal.toLocaleString(),
          icon: '✅',
          color: 'teal',
          description: 'Total reviews',
        },
        {
          label: 'Streak',
          value: `${streak}d`,
          icon: '🔥',
          color: 'orange',
          description: 'Keep it going!',
          highlight: streak >= 7,
        },
      ]
    }
    
    if (currentViewMode === 'exercises') {
      return [
        {
          label: 'Exercises',
          value: exercisesTotal.toLocaleString(),
          icon: '🏋️',
          color: 'indigo',
          description: 'Active learning tasks',
        },
        {
          label: 'Completed',
          value: exercisesCompleted.toLocaleString(),
          icon: '✅',
          color: 'emerald',
          description: `${exercisesTotal > 0 ? Math.round((exercisesCompleted / exercisesTotal) * 100) : 0}% tried`,
        },
        {
          label: 'Mastered',
          value: exercisesMastered.toLocaleString(),
          icon: '🎯',
          color: 'teal',
          description: 'Score ≥ 80%',
        },
        {
          label: 'Attempts',
          value: exercisesAttemptsTotal.toLocaleString(),
          icon: '🔄',
          color: 'purple',
          description: 'Total attempts',
        },
        {
          label: 'Avg Score',
          value: `${Math.round(exercisesAvgScore * 100)}%`,
          icon: '📊',
          color: exercisesAvgScore >= 0.8 ? 'emerald' : exercisesAvgScore >= 0.6 ? 'amber' : 'red',
          description: 'Across all attempts',
        },
        {
          label: 'Streak',
          value: `${streak}d`,
          icon: '🔥',
          color: 'orange',
          description: 'Keep it going!',
          highlight: streak >= 7,
        },
      ]
    }
    
    // Combined view (default)
    return [
      {
        label: 'Total Items',
        value: totalItems.toLocaleString(),
        icon: '📚',
        color: 'indigo',
        description: `${spacedRepCardsTotal} cards + ${exercisesTotal} exercises`,
      },
      {
        label: 'Mastered',
        value: totalMastered.toLocaleString(),
        icon: '🎯',
        color: 'emerald',
        description: `${totalItems > 0 ? Math.round((totalMastered / totalItems) * 100) : 0}% of total`,
      },
      {
        label: 'Reviews',
        value: spacedRepReviewsTotal.toLocaleString(),
        icon: '✅',
        color: 'purple',
        description: 'Card reviews',
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
  }

  const statItems = getStatItems()

  const colorClasses = {
    indigo: 'from-indigo-500/20 to-indigo-500/5 border-indigo-500/30',
    emerald: 'from-emerald-500/20 to-emerald-500/5 border-emerald-500/30',
    purple: 'from-purple-500/20 to-purple-500/5 border-purple-500/30',
    amber: 'from-amber-500/20 to-amber-500/5 border-amber-500/30',
    orange: 'from-orange-500/20 to-orange-500/5 border-orange-500/30',
    teal: 'from-teal-500/20 to-teal-500/5 border-teal-500/30',
    red: 'from-red-500/20 to-red-500/5 border-red-500/30',
  }

  const viewModes = [
    { value: 'combined', label: 'All', icon: '📊' },
    { value: 'cards', label: 'Cards', icon: '🃏' },
    { value: 'exercises', label: 'Exercises', icon: '🏋️' },
  ]

  return (
    <div className={className}>
      {/* View mode toggle */}
      <div className="flex items-center justify-end mb-4 gap-1 bg-bg-tertiary rounded-lg p-1 w-fit ml-auto">
        {viewModes.map((mode) => (
          <button
            key={mode.value}
            type="button"
            onClick={() => handleViewModeChange(mode.value)}
            className={clsx(
              'px-3 py-1.5 text-sm rounded-md transition-colors flex items-center gap-1.5',
              currentViewMode === mode.value
                ? 'bg-indigo-600 text-white'
                : 'text-text-secondary hover:text-text-primary'
            )}
          >
            <span>{mode.icon}</span>
            <span>{mode.label}</span>
          </button>
        ))}
      </div>
      
      <motion.div
        key={currentViewMode} // Re-animate when view mode changes
        variants={staggerContainer}
        initial="hidden"
        animate="show"
        className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4"
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
    </div>
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
