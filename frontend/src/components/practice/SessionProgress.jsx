/**
 * SessionProgress Component
 * 
 * Progress bar and statistics for practice session.
 */

import { motion } from 'framer-motion'
import { clsx } from 'clsx'
import { ClockIcon, CheckCircleIcon } from '@heroicons/react/24/outline'

export function SessionProgress({
  current,
  total,
  correctCount = 0,
  timeElapsed = 0,
  className,
}) {
  const progress = total > 0 ? (current / total) * 100 : 0
  const accuracy = current > 0 ? Math.round((correctCount / current) * 100) : 0
  
  // Format time
  const formatTime = (ms) => {
    const seconds = Math.floor(ms / 1000)
    const minutes = Math.floor(seconds / 60)
    const remainingSeconds = seconds % 60
    return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`
  }

  return (
    <div className={clsx('space-y-3', className)}>
      {/* Progress bar */}
      <div className="relative h-2 bg-slate-700 rounded-full overflow-hidden">
        <motion.div
          className="absolute inset-y-0 left-0 bg-gradient-to-r from-indigo-500 to-purple-500 rounded-full"
          initial={{ width: 0 }}
          animate={{ width: `${progress}%` }}
          transition={{ duration: 0.5, ease: 'easeOut' }}
        />
      </div>

      {/* Stats */}
      <div className="flex items-center justify-between text-sm">
        {/* Progress count */}
        <span className="text-text-primary font-medium">
          {current} / {total}
        </span>

        {/* Stats badges */}
        <div className="flex items-center gap-4">
          {/* Accuracy */}
          <div className="flex items-center gap-1.5 text-text-secondary">
            <CheckCircleIcon className="w-4 h-4 text-emerald-400" />
            <span>{accuracy}%</span>
          </div>

          {/* Correct/Incorrect */}
          <div className="flex items-center gap-2 text-text-muted">
            <span className="text-emerald-400">{correctCount}</span>
            <span>/</span>
            <span className="text-red-400">{current - correctCount}</span>
          </div>

          {/* Time */}
          <div className="flex items-center gap-1.5 text-text-secondary">
            <ClockIcon className="w-4 h-4" />
            <span>{formatTime(timeElapsed)}</span>
          </div>
        </div>
      </div>
    </div>
  )
}

// Compact version for header
export function SessionProgressCompact({ current, total, className }) {
  const progress = total > 0 ? (current / total) * 100 : 0

  return (
    <div className={clsx('flex items-center gap-3', className)}>
      <span className="text-sm text-text-muted">
        {current}/{total}
      </span>
      <div className="flex-1 h-1.5 bg-slate-700 rounded-full overflow-hidden min-w-[100px]">
        <motion.div
          className="h-full bg-indigo-500 rounded-full"
          initial={{ width: 0 }}
          animate={{ width: `${progress}%` }}
          transition={{ duration: 0.3 }}
        />
      </div>
      <span className="text-sm text-text-muted">
        {Math.round(progress)}%
      </span>
    </div>
  )
}

export default SessionProgress
