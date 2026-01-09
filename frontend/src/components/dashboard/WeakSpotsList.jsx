/**
 * WeakSpotsList Component
 * 
 * Topics below mastery threshold with trend indicators.
 */

import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { clsx } from 'clsx'
import { Card, Skeleton, EmptyState } from '../common'
import { staggerContainer, listItem } from '../../utils/animations'

function getMasteryColor(mastery) {
  if (mastery >= 0.8) return 'emerald'
  if (mastery >= 0.6) return 'indigo'
  if (mastery >= 0.4) return 'amber'
  return 'red'
}

function getTrendIcon(trend) {
  switch (trend) {
    case 'improving': return '↑'
    case 'declining': return '↓'
    default: return '→'
  }
}

function getTrendColor(trend) {
  switch (trend) {
    case 'improving': return 'text-emerald-400'
    case 'declining': return 'text-red-400'
    default: return 'text-slate-400'
  }
}

function WeakSpotItem({ topic, index }) {
  const color = getMasteryColor(topic.mastery_score)
  const percent = Math.round(topic.mastery_score * 100)
  
  return (
    <motion.div
      variants={listItem}
      custom={index}
      className={clsx(
        'flex items-center gap-3 p-3 rounded-lg',
        'hover:bg-slate-800/50 transition-colors'
      )}
    >
      {/* Status icon */}
      <div className={clsx(
        'w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 text-sm',
        color === 'red' && 'bg-red-500/20',
        color === 'amber' && 'bg-amber-500/20',
        color === 'indigo' && 'bg-indigo-500/20',
        color === 'emerald' && 'bg-emerald-500/20',
      )}>
        {color === 'red' && '⚠️'}
        {color === 'amber' && 'ℹ️'}
        {color === 'indigo' && '📊'}
        {color === 'emerald' && '✓'}
      </div>

      {/* Topic info */}
      <div className="flex-1 min-w-0">
        <p className="text-text-primary text-sm font-medium truncate">
          {topic.topic_name || topic.topic_path}
        </p>
        <div className="flex items-center gap-2 mt-1">
          {/* Progress bar */}
          <div className="flex-1 h-1.5 bg-slate-700 rounded-full overflow-hidden max-w-[100px]">
            <motion.div
              className={clsx(
                'h-full rounded-full',
                color === 'red' && 'bg-red-500',
                color === 'amber' && 'bg-amber-500',
                color === 'indigo' && 'bg-indigo-500',
                color === 'emerald' && 'bg-emerald-500',
              )}
              initial={{ width: 0 }}
              animate={{ width: `${percent}%` }}
              transition={{ duration: 0.8, ease: 'easeOut', delay: index * 0.1 }}
            />
          </div>
          <span className="text-xs text-text-muted">{percent}%</span>
          
          {/* Trend */}
          {topic.trend && (
            <span className={clsx('text-sm', getTrendColor(topic.trend))}>
              {getTrendIcon(topic.trend)}
            </span>
          )}
        </div>
      </div>

      {/* Practice button */}
      <Link
        to={`/practice/${topic.topic_id || topic.topic_path}`}
        className={clsx(
          'px-3 py-1.5 rounded-lg text-xs font-medium',
          'bg-slate-700 text-slate-300 hover:bg-slate-600 hover:text-white',
          'transition-colors'
        )}
      >
        Practice
      </Link>
    </motion.div>
  )
}

export function WeakSpotsList({
  topics = [],
  isLoading = false,
  showAll = false,
  maxItems = 5,
  className,
}) {
  const displayedTopics = showAll ? topics : topics.slice(0, maxItems)
  const hasMore = topics.length > maxItems && !showAll

  if (isLoading) {
    return (
      <Card className={className}>
        <div className="flex items-center justify-between mb-4">
          <Skeleton className="h-5 w-32" />
        </div>
        <div className="space-y-2">
          {[1, 2, 3].map((i) => (
            <div key={i} className="flex items-center gap-3 p-3">
              <Skeleton className="w-8 h-8 rounded-lg" />
              <div className="flex-1">
                <Skeleton className="h-4 w-1/2 mb-1" />
                <Skeleton className="h-2 w-3/4" />
              </div>
              <Skeleton className="w-16 h-7 rounded-lg" />
            </div>
          ))}
        </div>
      </Card>
    )
  }

  return (
    <Card className={className}>
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-text-primary font-heading flex items-center gap-2">
          <span>🎯</span> Focus Areas
        </h3>
        {topics.length > 0 && (
          <span className="text-sm text-text-muted">
            {topics.length} topics need attention
          </span>
        )}
      </div>

      {/* Topics list */}
      {displayedTopics.length > 0 ? (
        <motion.div
          variants={staggerContainer}
          initial="hidden"
          animate="show"
          className="space-y-1"
        >
          {displayedTopics.map((topic, index) => (
            <WeakSpotItem 
              key={topic.topic_id || topic.topic_path} 
              topic={topic} 
              index={index} 
            />
          ))}

          {/* Show more link */}
          {hasMore && (
            <Link
              to="/analytics"
              className="block text-center py-3 text-sm text-accent-secondary hover:text-accent-tertiary transition-colors"
            >
              View all {topics.length} topics →
            </Link>
          )}
        </motion.div>
      ) : (
        <EmptyState
          icon="🌟"
          title="Great progress!"
          description="All your topics are above the mastery threshold."
          size="sm"
          variant="minimal"
        />
      )}

      {/* Footer tip */}
      {displayedTopics.length > 0 && (
        <div className="mt-4 p-3 bg-slate-800/50 rounded-lg">
          <p className="text-xs text-text-muted">
            💡 <span className="text-text-secondary">Tip:</span> Focus on topics with ⚠️ icons first. 
            Consistent practice helps build lasting knowledge.
          </p>
        </div>
      )}
    </Card>
  )
}

export default WeakSpotsList
