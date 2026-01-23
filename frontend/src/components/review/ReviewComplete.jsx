/**
 * ReviewComplete Component
 * 
 * Completion screen with stats and next due info.
 */

import { motion } from 'framer-motion'
import { Link } from 'react-router-dom'
import { clsx } from 'clsx'
import { format } from 'date-fns'
import { Card, Button } from '../common'
import { fadeInUp, scaleInBounce, staggerContainer } from '../../utils/animations'

export function ReviewComplete({
  stats,
  nextDueDate,
  onReviewMore,
  className,
}) {
  const {
    reviewed = 0,
    skipped = 0,
    sessionDurationFormatted = '0:00',
    avgResponseTime = 0,
    againCount = 0,
    hardCount = 0,
    goodCount = 0,
    easyCount = 0,
  } = stats || {}

  // Calculate retention (percentage of cards rated Good or Easy)
  const retention = reviewed > 0 
    ? Math.round(((goodCount + easyCount) / reviewed) * 100) 
    : 0

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
          🎉
        </motion.span>
        <h1 className="text-3xl font-bold text-text-primary font-heading mb-2">
          Review Complete!
        </h1>
        <p className="text-text-secondary">
          Great job staying on top of your learning
        </p>
      </motion.div>

      {/* Stats */}
      <motion.div variants={fadeInUp}>
        <Card variant="elevated" padding="lg">
          <div className="grid grid-cols-2 gap-6">
            {/* Cards Reviewed */}
            <div className="text-center p-4 bg-bg-tertiary rounded-xl">
              <div className="text-4xl font-bold font-heading text-text-primary mb-1">
                {reviewed}
              </div>
              <p className="text-sm text-text-secondary">Cards Reviewed</p>
            </div>

            {/* Retention */}
            <div className="text-center p-4 bg-bg-tertiary rounded-xl">
              <div className={clsx(
                'text-4xl font-bold font-heading mb-1',
                retention >= 80 ? 'text-emerald-400' : 
                retention >= 60 ? 'text-indigo-400' : 'text-amber-400'
              )}>
                {retention}%
              </div>
              <p className="text-sm text-text-secondary">Retention</p>
            </div>

            {/* Session Time */}
            <div className="text-center p-4 bg-bg-tertiary rounded-xl">
              <div className="text-4xl font-bold font-heading text-text-primary mb-1">
                {sessionDurationFormatted}
              </div>
              <p className="text-sm text-text-secondary">Session Time</p>
            </div>

            {/* Avg Response */}
            <div className="text-center p-4 bg-bg-tertiary rounded-xl">
              <div className="text-4xl font-bold font-heading text-text-primary mb-1">
                {avgResponseTime}s
              </div>
              <p className="text-sm text-text-secondary">Avg Response</p>
            </div>
          </div>

          {/* Skipped cards (if any) */}
          {skipped > 0 && (
            <div className="mt-4 text-center p-3 bg-slate-700/30 rounded-lg">
              <span className="text-sm text-text-muted">
                {skipped} card{skipped !== 1 ? 's' : ''} skipped
              </span>
            </div>
          )}

          {/* Rating Distribution */}
          <div className="mt-6 pt-6 border-t border-border-primary">
            <h4 className="text-sm font-medium text-text-primary mb-4">
              Rating Distribution
            </h4>
            <div className="flex items-center gap-2">
              {[
                { label: 'Again', count: againCount, color: 'bg-red-500' },
                { label: 'Hard', count: hardCount, color: 'bg-amber-500' },
                { label: 'Good', count: goodCount, color: 'bg-indigo-500' },
                { label: 'Easy', count: easyCount, color: 'bg-emerald-500' },
              ].map(({ label, count, color }) => (
                <div key={label} className="flex-1">
                  <div className="flex items-center justify-center gap-1 mb-1">
                    <span className={clsx('w-2 h-2 rounded-full', color)} />
                    <span className="text-sm text-text-secondary">{count}</span>
                  </div>
                  <div className="text-xs text-text-muted text-center">{label}</div>
                </div>
              ))}
            </div>
          </div>
        </Card>
      </motion.div>

      {/* Next Due */}
      {nextDueDate && (
        <motion.div variants={fadeInUp} className="mt-6">
          <Card variant="ghost" className="text-center">
            <p className="text-sm text-text-secondary">
              Next cards due: {' '}
              <span className="text-text-primary font-medium">
                {format(new Date(nextDueDate), 'EEEE, MMM d')}
              </span>
            </p>
          </Card>
        </motion.div>
      )}

      {/* Actions */}
      <motion.div 
        variants={fadeInUp}
        className="mt-8 flex flex-col sm:flex-row items-center justify-center gap-4"
      >
        {onReviewMore && (
          <Button onClick={onReviewMore} size="lg">
            Review More Cards
          </Button>
        )}
        <Link to="/practice">
          <Button variant="secondary" size="lg">
            Start Practice
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

export default ReviewComplete
