/**
 * SessionComplete Component
 * 
 * Summary view after practice session ends.
 */

import { motion } from 'framer-motion'
import { Link } from 'react-router-dom'
import { clsx } from 'clsx'
import { Card, Button } from '../common'
import { fadeInUp, scaleInBounce, staggerContainer } from '../../utils/animations'

export function SessionComplete({
  summary,
  onStartNew,
  onViewAnalytics: _onViewAnalytics,
  className,
}) {
  const {
    totalItems = 0,
    completedItems = 0,
    correctItems = 0,
    accuracy = 0,
    totalTimeFormatted = '0:00',
    averageTimePerItem = 0,
  } = summary || {}

  // Determine performance level
  const getPerformanceLevel = (acc) => {
    if (acc >= 90) return { label: 'Excellent!', emoji: '🌟', color: 'emerald' }
    if (acc >= 75) return { label: 'Great job!', emoji: '🎉', color: 'indigo' }
    if (acc >= 60) return { label: 'Good progress!', emoji: '👍', color: 'amber' }
    return { label: 'Keep practicing!', emoji: '💪', color: 'red' }
  }

  const performance = getPerformanceLevel(accuracy)

  return (
    <motion.div
      variants={staggerContainer}
      initial="hidden"
      animate="show"
      className={clsx('max-w-2xl mx-auto', className)}
    >
      {/* Header */}
      <motion.div 
        variants={scaleInBounce}
        className="text-center mb-8"
      >
        <motion.span
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          transition={{ type: 'spring', stiffness: 200, delay: 0.2 }}
          className="text-7xl block mb-4"
        >
          {performance.emoji}
        </motion.span>
        <h1 className="text-3xl font-bold text-text-primary font-heading mb-2">
          Session Complete
        </h1>
        <p className={clsx(
          'text-xl font-medium',
          performance.color === 'emerald' && 'text-emerald-400',
          performance.color === 'indigo' && 'text-indigo-400',
          performance.color === 'amber' && 'text-amber-400',
          performance.color === 'red' && 'text-red-400',
        )}>
          {performance.label}
        </p>
      </motion.div>

      {/* Stats Grid */}
      <motion.div variants={fadeInUp}>
        <Card variant="elevated" padding="lg">
          <div className="grid grid-cols-2 gap-6">
            {/* Accuracy */}
            <div className="text-center p-4 bg-bg-tertiary rounded-xl">
              <div className={clsx(
                'text-4xl font-bold font-heading mb-1',
                accuracy >= 75 ? 'text-emerald-400' : 
                accuracy >= 50 ? 'text-amber-400' : 'text-red-400'
              )}>
                {accuracy}%
              </div>
              <p className="text-sm text-text-secondary">Accuracy</p>
            </div>

            {/* Exercises */}
            <div className="text-center p-4 bg-bg-tertiary rounded-xl">
              <div className="text-4xl font-bold font-heading text-text-primary mb-1">
                {completedItems}/{totalItems}
              </div>
              <p className="text-sm text-text-secondary">Completed</p>
            </div>

            {/* Time */}
            <div className="text-center p-4 bg-bg-tertiary rounded-xl">
              <div className="text-4xl font-bold font-heading text-text-primary mb-1">
                {totalTimeFormatted}
              </div>
              <p className="text-sm text-text-secondary">Total Time</p>
            </div>

            {/* Avg Time */}
            <div className="text-center p-4 bg-bg-tertiary rounded-xl">
              <div className="text-4xl font-bold font-heading text-text-primary mb-1">
                {averageTimePerItem}s
              </div>
              <p className="text-sm text-text-secondary">Avg per Item</p>
            </div>
          </div>

          {/* Correct/Incorrect breakdown */}
          <div className="mt-6 flex items-center justify-center gap-8">
            <div className="flex items-center gap-2">
              <span className="w-3 h-3 bg-emerald-500 rounded-full" />
              <span className="text-sm text-text-secondary">
                {correctItems} correct
              </span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-3 h-3 bg-red-500 rounded-full" />
              <span className="text-sm text-text-secondary">
                {completedItems - correctItems} incorrect
              </span>
            </div>
          </div>
        </Card>
      </motion.div>

      {/* Recommendations */}
      {accuracy < 80 && (
        <motion.div variants={fadeInUp} className="mt-6">
          <Card variant="ghost" className="bg-amber-500/10 border border-amber-500/20">
            <div className="flex items-start gap-3">
              <span className="text-xl">💡</span>
              <div>
                <p className="text-sm font-medium text-amber-300">Tip for Improvement</p>
                <p className="text-sm text-amber-200/70 mt-1">
                  Consider reviewing the topics you struggled with. Spaced repetition helps build long-term memory.
                </p>
              </div>
            </div>
          </Card>
        </motion.div>
      )}

      {/* Actions */}
      <motion.div 
        variants={fadeInUp}
        className="mt-8 flex flex-col sm:flex-row items-center justify-center gap-4"
      >
        <Button onClick={onStartNew} size="lg">
          Start New Session
        </Button>
        <Link to="/analytics">
          <Button variant="secondary" size="lg">
            View Analytics
          </Button>
        </Link>
        <Link to="/">
          <Button variant="ghost" size="lg">
            Back to Dashboard
          </Button>
        </Link>
      </motion.div>
    </motion.div>
  )
}

export default SessionComplete
