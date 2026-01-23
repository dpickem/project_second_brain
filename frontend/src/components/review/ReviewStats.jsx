/**
 * ReviewStats Component
 * 
 * Session statistics for review queue.
 */

import { motion } from 'framer-motion'
import { clsx } from 'clsx'

export function ReviewStats({
  remaining,
  reviewed,
  skipped = 0,
  dueToday,
  avgResponseTime,
  className,
}) {
  const progress = dueToday > 0 ? Math.round(((reviewed + skipped) / dueToday) * 100) : 0

  return (
    <div className={clsx('flex items-center gap-6', className)}>
      {/* Progress */}
      <div className="flex items-center gap-3">
        <div className="relative w-12 h-12">
          {/* Circular progress */}
          <svg className="w-12 h-12 transform -rotate-90">
            <circle
              cx="24"
              cy="24"
              r="20"
              fill="none"
              stroke="currentColor"
              strokeWidth="4"
              className="text-slate-700"
            />
            <motion.circle
              cx="24"
              cy="24"
              r="20"
              fill="none"
              stroke="currentColor"
              strokeWidth="4"
              strokeLinecap="round"
              className="text-indigo-500"
              strokeDasharray={`${2 * Math.PI * 20}`}
              initial={{ strokeDashoffset: 2 * Math.PI * 20 }}
              animate={{ 
                strokeDashoffset: 2 * Math.PI * 20 * (1 - progress / 100) 
              }}
              transition={{ duration: 0.5, ease: 'easeOut' }}
            />
          </svg>
          {/* Center text */}
          <div className="absolute inset-0 flex items-center justify-center">
            <span className="text-sm font-medium text-text-primary">{progress}%</span>
          </div>
        </div>
        
        <div>
          <p className="text-sm font-medium text-text-primary">
            {reviewed}/{dueToday}
            {skipped > 0 && <span className="text-text-muted ml-1">({skipped} skipped)</span>}
          </p>
          <p className="text-xs text-text-muted">Completed</p>
        </div>
      </div>

      {/* Remaining */}
      <div className="text-center">
        <p className="text-2xl font-bold text-text-primary">{remaining}</p>
        <p className="text-xs text-text-muted">Remaining</p>
      </div>

      {/* Avg time */}
      {avgResponseTime !== undefined && (
        <div className="text-center">
          <p className="text-2xl font-bold text-text-primary">{avgResponseTime}s</p>
          <p className="text-xs text-text-muted">Avg time</p>
        </div>
      )}
    </div>
  )
}

// Compact stats bar
export function ReviewStatsBar({ reviewed, total, className }) {
  const progress = total > 0 ? (reviewed / total) * 100 : 0

  return (
    <div className={clsx('flex items-center gap-3', className)}>
      <span className="text-sm text-text-muted">{reviewed}/{total}</span>
      <div className="flex-1 h-1.5 bg-slate-700 rounded-full overflow-hidden min-w-[100px]">
        <motion.div
          className="h-full bg-indigo-500 rounded-full"
          initial={{ width: 0 }}
          animate={{ width: `${progress}%` }}
          transition={{ duration: 0.3 }}
        />
      </div>
    </div>
  )
}

export default ReviewStats
