/**
 * RatingButtons Component
 * 
 * FSRS rating buttons (Again/Hard/Good/Easy) with interval preview.
 */

import { motion } from 'framer-motion'
import { clsx } from 'clsx'
import { staggerContainer, listItem } from '../../utils/animations'

const ratings = [
  { 
    value: 1, 
    label: 'Again', 
    shortcut: '1',
    color: 'red',
    description: 'Forgot completely',
  },
  { 
    value: 2, 
    label: 'Hard', 
    shortcut: '2',
    color: 'amber',
    description: 'Difficult to recall',
  },
  { 
    value: 3, 
    label: 'Good', 
    shortcut: '3',
    color: 'indigo',
    description: 'Recalled with effort',
  },
  { 
    value: 4, 
    label: 'Easy', 
    shortcut: '4',
    color: 'emerald',
    description: 'Recalled easily',
  },
]

const colorClasses = {
  red: {
    base: 'bg-red-500/10 border-red-500/30 hover:bg-red-500/20',
    active: 'bg-red-500 border-red-500 text-white',
    text: 'text-red-400',
  },
  amber: {
    base: 'bg-amber-500/10 border-amber-500/30 hover:bg-amber-500/20',
    active: 'bg-amber-500 border-amber-500 text-white',
    text: 'text-amber-400',
  },
  indigo: {
    base: 'bg-indigo-500/10 border-indigo-500/30 hover:bg-indigo-500/20',
    active: 'bg-indigo-500 border-indigo-500 text-white',
    text: 'text-indigo-400',
  },
  emerald: {
    base: 'bg-emerald-500/10 border-emerald-500/30 hover:bg-emerald-500/20',
    active: 'bg-emerald-500 border-emerald-500 text-white',
    text: 'text-emerald-400',
  },
}

export function RatingButtons({
  onRate,
  predictedIntervals = {},
  suggestedRating = null,
  isLoading = false,
  disabled = false,
  showShortcuts = true,
  className,
}) {
  // Format interval for display
  const formatInterval = (days) => {
    if (days === undefined || days === null) return ''
    if (days < 1) return '<1d'
    if (days < 30) return `${Math.round(days)}d`
    if (days < 365) return `${Math.round(days / 30)}mo`
    return `${(days / 365).toFixed(1)}y`
  }

  return (
    <motion.div
      variants={staggerContainer}
      initial="hidden"
      animate="show"
      className={clsx('space-y-4', className)}
    >
      {/* Label */}
      {!suggestedRating && (
        <p className="text-sm text-text-secondary text-center">
          How well did you remember?
        </p>
      )}

      {/* Rating buttons */}
      <div className="grid grid-cols-4 gap-3">
        {ratings.map((rating, index) => {
          const colors = colorClasses[rating.color]
          const interval = predictedIntervals[rating.value]
          const isSuggested = suggestedRating === rating.value

          return (
            <motion.button
              key={rating.value}
              variants={listItem}
              custom={index}
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={() => onRate?.(rating.value)}
              disabled={disabled || isLoading}
              className={clsx(
                'relative flex flex-col items-center p-4 rounded-xl border transition-all',
                'focus:outline-none focus-visible:ring-2 focus-visible:ring-offset-2',
                'focus-visible:ring-offset-bg-primary',
                disabled ? 'opacity-50 cursor-not-allowed' : colors.base,
                rating.color === 'red' && 'focus-visible:ring-red-500',
                rating.color === 'amber' && 'focus-visible:ring-amber-500',
                rating.color === 'indigo' && 'focus-visible:ring-indigo-500',
                rating.color === 'emerald' && 'focus-visible:ring-emerald-500',
                // Highlight suggested rating
                isSuggested && 'ring-2 ring-offset-2 ring-offset-bg-primary',
                isSuggested && rating.color === 'red' && 'ring-red-500',
                isSuggested && rating.color === 'amber' && 'ring-amber-500',
                isSuggested && rating.color === 'indigo' && 'ring-indigo-500',
                isSuggested && rating.color === 'emerald' && 'ring-emerald-500',
              )}
            >
              {/* Suggested badge */}
              {isSuggested && (
                <span className="absolute -top-2 -right-2 px-2 py-0.5 text-[10px] font-medium bg-accent-primary text-white rounded-full">
                  AI
                </span>
              )}
              
              {/* Label */}
              <span className={clsx('text-sm font-medium', colors.text)}>
                {rating.label}
              </span>

              {/* Predicted interval */}
              {interval !== undefined && (
                <span className="text-xs text-text-muted mt-1">
                  {formatInterval(interval)}
                </span>
              )}

              {/* Keyboard shortcut */}
              {showShortcuts && (
                <kbd className="mt-2 px-1.5 py-0.5 text-xs bg-slate-700 text-slate-400 rounded">
                  {rating.shortcut}
                </kbd>
              )}
            </motion.button>
          )
        })}
      </div>

      {/* Help text */}
      <p className="text-xs text-text-muted text-center">
        Press <kbd className="px-1 bg-slate-700 rounded">1</kbd>-<kbd className="px-1 bg-slate-700 rounded">4</kbd> to rate
        {suggestedRating && ' • You can override the AI suggestion'}
      </p>
    </motion.div>
  )
}

// Compact horizontal variant
export function RatingButtonsCompact({ onRate, disabled, className }) {
  return (
    <div className={clsx('flex items-center gap-2', className)}>
      {ratings.map((rating) => {
        const colors = colorClasses[rating.color]
        
        return (
          <button
            key={rating.value}
            onClick={() => onRate?.(rating.value)}
            disabled={disabled}
            className={clsx(
              'px-4 py-2 rounded-lg border text-sm font-medium transition-all',
              disabled ? 'opacity-50 cursor-not-allowed' : colors.base,
              colors.text,
            )}
          >
            {rating.label}
          </button>
        )
      })}
    </div>
  )
}

export default RatingButtons
