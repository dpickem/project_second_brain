/**
 * FlashCard Component
 * 
 * Flip card with front/back for spaced repetition review.
 */

import { motion } from 'framer-motion'
import { clsx } from 'clsx'
import ReactMarkdown from 'react-markdown'
import { Badge, ContentTypeBadge } from '../common'

export function FlashCard({
  card,
  showAnswer = false,
  onShowAnswer,
  className,
}) {
  return (
    <div className={clsx('perspective-1000', className)}>
      <motion.div
        className="relative w-full min-h-[400px] cursor-pointer"
        onClick={() => !showAnswer && onShowAnswer?.()}
        style={{ transformStyle: 'preserve-3d' }}
      >
        {/* Front */}
        <motion.div
          className={clsx(
            'absolute inset-0 p-8 rounded-2xl backface-hidden',
            'bg-bg-elevated border border-border-primary shadow-xl',
            'flex flex-col'
          )}
          animate={{ rotateY: showAnswer ? 180 : 0 }}
          transition={{ duration: 0.4, ease: 'easeOut' }}
          style={{ backfaceVisibility: 'hidden' }}
        >
          {/* Card metadata */}
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-2">
              <ContentTypeBadge type={card.card_type} size="sm" />
              {card.streak > 0 && (
                <Badge variant="success" size="xs">
                  🔥 {card.streak}
                </Badge>
              )}
            </div>
            {card.interval_days !== undefined && (
              <span className="text-xs text-text-muted">
                {card.interval_days === 0 ? 'New' : `${card.interval_days}d interval`}
              </span>
            )}
          </div>

          {/* Question */}
          <div className="flex-1 flex flex-col justify-center">
            <div className="prose prose-invert prose-lg max-w-none text-center">
              <ReactMarkdown>{card.front}</ReactMarkdown>
            </div>
            
            {card.code_front && (
              <pre className="mt-6 p-4 bg-slate-800/80 rounded-lg overflow-x-auto text-sm">
                <code className="text-slate-300 font-mono">{card.code_front}</code>
              </pre>
            )}
          </div>

          {/* Tap hint */}
          {!showAnswer && (
            <motion.p 
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.5 }}
              className="text-center text-sm text-text-muted mt-4"
            >
              Tap to reveal answer
            </motion.p>
          )}
        </motion.div>

        {/* Back */}
        <motion.div
          className={clsx(
            'absolute inset-0 p-8 rounded-2xl backface-hidden',
            'bg-gradient-to-br from-indigo-900/50 to-purple-900/50',
            'border border-indigo-500/30 shadow-xl',
            'flex flex-col'
          )}
          initial={{ rotateY: -180 }}
          animate={{ rotateY: showAnswer ? 0 : -180 }}
          transition={{ duration: 0.4, ease: 'easeOut' }}
          style={{ backfaceVisibility: 'hidden' }}
        >
          {/* Answer header */}
          <div className="flex items-center justify-between mb-6">
            <span className="text-sm font-medium text-indigo-300">Answer</span>
            {card.source && (
              <span className="text-xs text-text-muted truncate max-w-[200px]">
                {card.source}
              </span>
            )}
          </div>

          {/* Answer */}
          <div className="flex-1 flex flex-col justify-center overflow-y-auto">
            <div className="prose prose-invert prose-lg max-w-none">
              <ReactMarkdown>{card.back}</ReactMarkdown>
            </div>
            
            {card.code_back && (
              <pre className="mt-6 p-4 bg-slate-800/80 rounded-lg overflow-x-auto text-sm">
                <code className="text-slate-300 font-mono">{card.code_back}</code>
              </pre>
            )}

            {/* Explanation */}
            {card.explanation && (
              <div className="mt-6 p-4 bg-slate-800/50 rounded-lg">
                <p className="text-sm text-text-secondary">
                  <span className="font-medium text-text-primary">💡 </span>
                  {card.explanation}
                </p>
              </div>
            )}
          </div>
        </motion.div>
      </motion.div>
    </div>
  )
}

// Compact card for lists
export function FlashCardCompact({ card, onClick, className }) {
  return (
    <motion.div
      whileHover={{ scale: 1.01 }}
      whileTap={{ scale: 0.99 }}
      onClick={onClick}
      className={clsx(
        'p-4 rounded-xl bg-bg-elevated border border-border-primary',
        'hover:border-border-secondary cursor-pointer transition-colors',
        className
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <p className="text-text-primary font-medium line-clamp-2">{card.front}</p>
          <div className="flex items-center gap-2 mt-2">
            <ContentTypeBadge type={card.card_type} size="xs" />
            {card.interval_days !== undefined && (
              <span className="text-xs text-text-muted">
                {card.interval_days}d
              </span>
            )}
          </div>
        </div>
        
        {card.due_date && new Date(card.due_date) < new Date() && (
          <Badge variant="danger" size="xs">Overdue</Badge>
        )}
      </div>
    </motion.div>
  )
}

export default FlashCard
