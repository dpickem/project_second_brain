/**
 * DueCardsPreview Component
 * 
 * Compact list of upcoming due cards with source badges.
 */

import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { clsx } from 'clsx'
import { Card, Badge, Skeleton, EmptyState } from '../common'
import { staggerContainer, listItem } from '../../utils/animations'

function CardItem({ card, index }) {
  return (
    <motion.div
      variants={listItem}
      custom={index}
      className={clsx(
        'flex items-start gap-3 p-3 rounded-lg',
        'hover:bg-slate-800/50 transition-colors cursor-pointer'
      )}
    >
      {/* Type indicator */}
      <div className={clsx(
        'w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 text-sm',
        card.card_type === 'concept' && 'bg-indigo-500/20 text-indigo-400',
        card.card_type === 'fact' && 'bg-emerald-500/20 text-emerald-400',
        card.card_type === 'application' && 'bg-amber-500/20 text-amber-400',
        card.card_type === 'code' && 'bg-purple-500/20 text-purple-400',
        card.card_type === 'cloze' && 'bg-sky-500/20 text-sky-400',
      )}>
        {card.card_type === 'concept' && '💡'}
        {card.card_type === 'fact' && '📝'}
        {card.card_type === 'application' && '🔧'}
        {card.card_type === 'code' && '💻'}
        {card.card_type === 'cloze' && '📌'}
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        <p className="text-text-primary text-sm font-medium truncate">
          {card.front || card.question}
        </p>
        <div className="flex items-center gap-2 mt-1">
          {card.source && (
            <span className="text-xs text-text-muted truncate max-w-[120px]">
              {card.source}
            </span>
          )}
          {card.interval_days !== undefined && (
            <span className="text-xs text-text-muted">
              {card.interval_days === 0 ? 'New' : `${card.interval_days}d interval`}
            </span>
          )}
        </div>
      </div>

      {/* Due indicator */}
      <div className={clsx(
        'flex-shrink-0 w-2 h-2 rounded-full',
        card.overdue ? 'bg-red-400' : 'bg-indigo-400'
      )} />
    </motion.div>
  )
}

export function DueCardsPreview({
  cards = [],
  totalDue = 0,
  isLoading = false,
  className,
}) {
  const hasMore = totalDue > cards.length
  const remainingCount = totalDue - cards.length

  if (isLoading) {
    return (
      <Card className={className}>
        <div className="flex items-center justify-between mb-4">
          <Skeleton className="h-5 w-32" />
          <Skeleton className="h-4 w-16" />
        </div>
        <div className="space-y-2">
          {[1, 2, 3, 4, 5].map((i) => (
            <div key={i} className="flex items-start gap-3 p-3">
              <Skeleton className="w-8 h-8 rounded-lg" />
              <div className="flex-1">
                <Skeleton className="h-4 w-3/4 mb-1" />
                <Skeleton className="h-3 w-1/2" />
              </div>
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
          <span>📋</span> Due for Review
        </h3>
        {totalDue > 0 && (
          <Badge variant="primary" size="sm">
            {totalDue} total
          </Badge>
        )}
      </div>

      {/* Cards list */}
      {cards.length > 0 ? (
        <motion.div
          variants={staggerContainer}
          initial="hidden"
          animate="show"
          className="space-y-1"
        >
          {cards.map((card, index) => (
            <CardItem key={card.id} card={card} index={index} />
          ))}

          {/* More indicator */}
          {hasMore && (
            <Link 
              to="/review" 
              className="block text-center py-3 text-sm text-accent-secondary hover:text-accent-tertiary transition-colors"
            >
              ... and {remainingCount} more →
            </Link>
          )}
        </motion.div>
      ) : (
        <EmptyState
          icon="🎉"
          title="All caught up!"
          description="No cards due for review right now."
          size="sm"
          variant="minimal"
        />
      )}

      {/* Footer action */}
      {cards.length > 0 && (
        <div className="mt-4 pt-4 border-t border-border-primary">
          <Link
            to="/review"
            className={clsx(
              'flex items-center justify-center gap-2 w-full py-2.5 rounded-lg',
              'bg-indigo-600/20 text-indigo-300 hover:bg-indigo-600/30',
              'transition-colors font-medium text-sm'
            )}
          >
            Start Review Session
            <span>→</span>
          </Link>
        </div>
      )}
    </Card>
  )
}

export default DueCardsPreview
