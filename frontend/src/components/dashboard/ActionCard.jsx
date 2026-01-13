/**
 * ActionCard Component
 * 
 * Large clickable cards for primary actions (Practice, Review).
 */

import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { clsx } from 'clsx'
import { cardHover } from '../../utils/animations'

export function ActionCard({
  to,
  icon,
  title,
  sublabel,
  highlight = false,
  badge,
  disabled = false,
  className,
  onClick,
}) {
  const content = (
    <motion.div
      variants={cardHover}
      initial="rest"
      whileHover={!disabled ? "hover" : undefined}
      whileTap={!disabled ? "tap" : undefined}
      className={clsx(
        'relative p-6 rounded-2xl border transition-all duration-200 overflow-hidden',
        'flex flex-col h-full min-h-[160px]',
        highlight
          ? 'bg-gradient-to-br from-indigo-600/20 to-purple-600/20 border-indigo-500/50 shadow-lg shadow-indigo-600/10'
          : 'bg-slate-800/50 border-slate-700 hover:border-slate-600',
        disabled && 'opacity-50 cursor-not-allowed',
        className
      )}
    >
      {/* Background decoration */}
      {highlight && (
        <div className="absolute top-0 right-0 w-32 h-32 bg-gradient-to-br from-indigo-500/10 to-purple-500/10 rounded-full blur-2xl -translate-y-8 translate-x-8" />
      )}
      
      {/* Badge */}
      {badge && (
        <div className="absolute top-4 right-4">
          <span className={clsx(
            'px-2 py-1 text-xs font-medium rounded-full',
            'bg-indigo-500/20 text-indigo-300 border border-indigo-500/30'
          )}>
            {badge}
          </span>
        </div>
      )}

      {/* Icon */}
      <span className="text-4xl mb-4 block">{icon}</span>
      
      {/* Title */}
      <h3 className={clsx(
        'text-xl font-semibold text-white font-heading',
        !disabled && 'group-hover:text-indigo-300'
      )}>
        {title}
      </h3>
      
      {/* Sublabel */}
      <p className="text-slate-400 mt-1">{sublabel}</p>

      {/* Arrow indicator */}
      {!disabled && (
        <div className="mt-auto pt-4">
          <motion.span 
            className="text-slate-500 text-lg"
            initial={{ x: 0 }}
            whileHover={{ x: 4 }}
          >
            →
          </motion.span>
        </div>
      )}
    </motion.div>
  )

  if (disabled) {
    return content
  }

  if (onClick) {
    return (
      <button 
        onClick={onClick}
        className="w-full h-full text-left group"
      >
        {content}
      </button>
    )
  }

  return (
    <Link to={to} className="group block h-full">
      {content}
    </Link>
  )
}

// Pre-configured action cards

export function PracticeActionCard({ exerciseCount, topicName, ...props }) {
  return (
    <ActionCard
      to="/practice"
      icon="🎯"
      title="Practice"
      sublabel={topicName 
        ? `Continue ${topicName}` 
        : exerciseCount 
          ? `${exerciseCount} exercises ready` 
          : 'Start a practice session'
      }
      highlight
      {...props}
    />
  )
}

export function ReviewActionCard({ dueCount, ...props }) {
  return (
    <ActionCard
      to="/review"
      icon="📚"
      title="Review"
      sublabel={dueCount > 0 
        ? `${dueCount} cards due` 
        : 'All caught up!'
      }
      badge={dueCount > 0 ? `${dueCount} due` : undefined}
      highlight={dueCount > 0}
      {...props}
    />
  )
}

export function ExploreActionCard({ ...props }) {
  return (
    <ActionCard
      to="/knowledge"
      icon="🕸️"
      title="Explore"
      sublabel="Browse your knowledge graph"
      {...props}
    />
  )
}

export function CaptureActionCard({ onClick, ...props }) {
  return (
    <ActionCard
      icon="⚡"
      title="Quick Capture"
      sublabel="Capture a thought or idea"
      onClick={onClick}
      {...props}
    />
  )
}

export default ActionCard
