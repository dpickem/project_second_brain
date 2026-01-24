/**
 * FlashCard Component
 * 
 * Active recall card with text input for typed answers.
 * Supports both "active recall" mode (type answer → LLM evaluation)
 * and traditional "flip card" mode.
 */

import { useState, useRef, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { clsx } from 'clsx'
import ReactMarkdown from 'react-markdown'
import { BookOpenIcon } from '@heroicons/react/24/outline'
import { Badge, ContentTypeBadge, Button, Spinner } from '../common'

/**
 * Active Recall Card - User types answer, LLM evaluates
 */
export function FlashCard({
  card,
  showFeedback = false,
  evaluation = null,
  onSubmitAnswer,
  isEvaluating = false,
  className,
}) {
  const [userAnswer, setUserAnswer] = useState('')
  const textareaRef = useRef(null)

  // Focus textarea on mount
  useEffect(() => {
    if (textareaRef.current && !showFeedback) {
      textareaRef.current.focus()
    }
  }, [card?.id, showFeedback])

  // Reset answer when card changes
  useEffect(() => {
    setUserAnswer('')
  }, [card?.id])

  const handleSubmit = (e) => {
    e?.preventDefault()
    if (userAnswer.trim() && !isEvaluating) {
      onSubmitAnswer?.(userAnswer.trim())
    }
  }

  const handleKeyDown = (e) => {
    // Submit on Ctrl+Enter or Cmd+Enter
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
      handleSubmit()
    }
  }

  return (
    <div className={clsx('w-full', className)}>
      <motion.div
        className={clsx(
          'p-8 rounded-2xl shadow-xl',
          'bg-bg-elevated border border-border-primary',
          'flex flex-col min-h-[450px]'
        )}
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
        <div className="mb-6">
          <div className="prose prose-invert prose-lg max-w-none">
            <ReactMarkdown>{card.front}</ReactMarkdown>
          </div>
          
          {card.code_front && (
            <pre className="mt-4 p-4 bg-slate-800/80 rounded-lg overflow-x-auto text-sm">
              <code className="text-slate-300 font-mono">{card.code_front}</code>
            </pre>
          )}
        </div>

        {/* Answer Input or Feedback */}
        <AnimatePresence mode="wait">
          {!showFeedback ? (
            <motion.form
              key="input"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              onSubmit={handleSubmit}
              className="flex-1 flex flex-col"
            >
              <label className="text-sm font-medium text-text-secondary mb-2">
                Type your answer:
              </label>
              <textarea
                ref={textareaRef}
                value={userAnswer}
                onChange={(e) => setUserAnswer(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Type your answer here..."
                disabled={isEvaluating}
                className={clsx(
                  'flex-1 min-h-[150px] p-4 rounded-xl',
                  'bg-bg-tertiary border border-border-primary',
                  'text-text-primary placeholder-text-muted',
                  'focus:outline-none focus:border-accent-primary focus:ring-1 focus:ring-accent-primary',
                  'resize-none transition-colors',
                  isEvaluating && 'opacity-50 cursor-not-allowed'
                )}
              />
              <div className="flex items-center justify-between mt-4">
                <p className="text-xs text-text-muted">
                  Press <kbd className="px-1 bg-slate-700 rounded">⌘+Enter</kbd> to submit
                </p>
                <Button
                  type="submit"
                  disabled={!userAnswer.trim() || isEvaluating}
                  loading={isEvaluating}
                >
                  {isEvaluating ? 'Evaluating...' : 'Check Answer'}
                </Button>
              </div>
            </motion.form>
          ) : (
            <motion.div
              key="feedback"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className="flex-1 flex flex-col"
            >
              <EvaluationFeedback 
                evaluation={evaluation} 
                expectedAnswer={card.back}
                contentId={card.content_id}
                tags={card.tags}
              />
            </motion.div>
          )}
        </AnimatePresence>
      </motion.div>
    </div>
  )
}

/**
 * Evaluation Feedback Display
 */
function EvaluationFeedback({ evaluation, expectedAnswer, contentId, tags }) {
  if (!evaluation) return null

  const ratingLabels = {
    1: { label: 'Again', color: 'text-red-400', bg: 'bg-red-500/20', emoji: '❌' },
    2: { label: 'Hard', color: 'text-amber-400', bg: 'bg-amber-500/20', emoji: '😐' },
    3: { label: 'Good', color: 'text-indigo-400', bg: 'bg-indigo-500/20', emoji: '✓' },
    4: { label: 'Easy', color: 'text-emerald-400', bg: 'bg-emerald-500/20', emoji: '🌟' },
  }

  const ratingInfo = ratingLabels[evaluation.rating] || ratingLabels[2]
  const primaryTopic = tags?.[0]

  return (
    <div className="space-y-4">
      {/* Rating Badge */}
      <div className={clsx(
        'flex items-center gap-3 p-4 rounded-xl',
        ratingInfo.bg
      )}>
        <span className="text-2xl">{ratingInfo.emoji}</span>
        <div>
          <span className={clsx('font-bold text-lg', ratingInfo.color)}>
            {ratingInfo.label}
          </span>
          <span className="text-text-secondary ml-2">
            {evaluation.is_correct ? 'Correct!' : 'Needs improvement'}
          </span>
        </div>
      </div>

      {/* Study Source Link - Show when answer needs improvement */}
      {!evaluation.is_correct && (contentId || primaryTopic) && (
        <div className="p-4 bg-amber-500/10 border border-amber-500/20 rounded-xl">
          <h4 className="text-sm font-medium text-amber-400 mb-2 flex items-center gap-2">
            <BookOpenIcon className="w-4 h-4" />
            Review the Source Material
          </h4>
          <p className="text-sm text-text-secondary mb-3">
            It looks like you need to brush up on this topic. Check out the original content to reinforce your understanding.
          </p>
          <div className="flex flex-wrap gap-2">
            {contentId && (
              <Link
                to={`/knowledge?content=${contentId}`}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm bg-amber-500/20 text-amber-300 hover:bg-amber-500/30 rounded-lg transition-colors"
              >
                <BookOpenIcon className="w-4 h-4" />
                View Source Note
              </Link>
            )}
            {primaryTopic && (
              <Link
                to={`/knowledge?topic=${encodeURIComponent(primaryTopic)}`}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm bg-indigo-500/20 text-indigo-300 hover:bg-indigo-500/30 rounded-lg transition-colors"
              >
                Browse Topic: {primaryTopic}
              </Link>
            )}
          </div>
        </div>
      )}

      {/* Feedback */}
      <div className="p-4 bg-bg-tertiary rounded-xl">
        <h4 className="text-sm font-medium text-text-primary mb-2">Feedback</h4>
        <p className="text-text-secondary">{evaluation.feedback}</p>
      </div>

      {/* Key Points */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {evaluation.key_points_covered?.length > 0 && (
          <div className="p-4 bg-emerald-500/10 border border-emerald-500/20 rounded-xl">
            <h4 className="text-sm font-medium text-emerald-400 mb-2">✓ Covered</h4>
            <ul className="space-y-1">
              {evaluation.key_points_covered.map((point, i) => (
                <li key={i} className="text-sm text-text-secondary">• {point}</li>
              ))}
            </ul>
          </div>
        )}
        
        {evaluation.key_points_missed?.length > 0 && (
          <div className="p-4 bg-red-500/10 border border-red-500/20 rounded-xl">
            <h4 className="text-sm font-medium text-red-400 mb-2">✗ Missed</h4>
            <ul className="space-y-1">
              {evaluation.key_points_missed.map((point, i) => (
                <li key={i} className="text-sm text-text-secondary">• {point}</li>
              ))}
            </ul>
          </div>
        )}
      </div>

      {/* Expected Answer */}
      <div className="p-4 bg-indigo-500/10 border border-indigo-500/20 rounded-xl">
        <h4 className="text-sm font-medium text-indigo-300 mb-2">Expected Answer</h4>
        <div className="prose prose-invert prose-sm max-w-none">
          <ReactMarkdown>{expectedAnswer}</ReactMarkdown>
        </div>
      </div>
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
