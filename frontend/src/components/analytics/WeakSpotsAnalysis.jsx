/**
 * WeakSpotsAnalysis Component
 * 
 * Identifies topics needing extra attention with recommendations.
 */

import { motion } from 'framer-motion'
import { Link } from 'react-router-dom'
import { clsx } from 'clsx'
import { Card, Badge, Button } from '../common'
import { staggerContainer, listItem } from '../../utils/animations'

export function WeakSpotsAnalysis({
  weakSpots = [],
  onPractice,
  className,
}) {
  if (weakSpots.length === 0) {
    return (
      <Card className={className}>
        <div className="text-center py-8">
          <span className="text-4xl mb-4 block">🌟</span>
          <h3 className="text-lg font-semibold text-text-primary mb-2">
            Great Progress!
          </h3>
          <p className="text-sm text-text-secondary">
            No weak spots identified. Keep up the excellent work!
          </p>
        </div>
      </Card>
    )
  }

  return (
    <motion.div
      variants={staggerContainer}
      initial="hidden"
      animate="show"
      className={clsx('space-y-4', className)}
    >
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold text-text-primary">
            🎯 Areas to Focus
          </h3>
          <p className="text-sm text-text-secondary">
            Topics that could use more practice
          </p>
        </div>
        <Badge variant="warning">{weakSpots.length} topics</Badge>
      </div>

      {/* Weak spots list */}
      <div className="space-y-3">
        {weakSpots.map((spot, index) => (
          <motion.div
            key={spot.topic}
            variants={listItem}
            custom={index}
          >
            <Card variant="ghost" padding="sm">
              <div className="flex items-center gap-4">
                {/* Icon/Indicator */}
                <div className={clsx(
                  'w-10 h-10 rounded-lg flex items-center justify-center',
                  spot.mastery < 30 ? 'bg-red-500/20' :
                  spot.mastery < 50 ? 'bg-amber-500/20' : 'bg-indigo-500/20'
                )}>
                  <span className="text-lg">
                    {spot.mastery < 30 ? '🔴' : spot.mastery < 50 ? '🟡' : '🔵'}
                  </span>
                </div>

                {/* Topic info */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <h4 className="text-sm font-medium text-text-primary truncate">
                      {spot.topic}
                    </h4>
                    <Badge 
                      variant={spot.mastery < 30 ? 'danger' : spot.mastery < 50 ? 'warning' : 'default'}
                      size="xs"
                    >
                      {spot.mastery}%
                    </Badge>
                  </div>
                  
                  <p className="text-xs text-text-muted mt-0.5">
                    {spot.cardCount} cards • {spot.dueCount || 0} due
                  </p>
                  
                  {/* Recommendation */}
                  {spot.recommendation && (
                    <p className="text-xs text-indigo-400 mt-1">
                      💡 {spot.recommendation}
                    </p>
                  )}
                </div>

                {/* Progress bar */}
                <div className="w-20 hidden sm:block">
                  <div className="h-1.5 bg-slate-700 rounded-full overflow-hidden">
                    <motion.div
                      className={clsx(
                        'h-full rounded-full',
                        spot.mastery < 30 ? 'bg-red-500' :
                        spot.mastery < 50 ? 'bg-amber-500' : 'bg-indigo-500'
                      )}
                      initial={{ width: 0 }}
                      animate={{ width: `${spot.mastery}%` }}
                      transition={{ duration: 0.5, delay: index * 0.1 }}
                    />
                  </div>
                </div>

                {/* Practice button */}
                <Button
                  size="sm"
                  variant="secondary"
                  onClick={() => onPractice?.(spot.topic)}
                >
                  Practice
                </Button>
              </div>
            </Card>
          </motion.div>
        ))}
      </div>

      {/* CTA */}
      <div className="pt-4 flex justify-center">
        <Link to="/practice">
          <Button>
            Start Focused Practice
          </Button>
        </Link>
      </div>
    </motion.div>
  )
}

export default WeakSpotsAnalysis
