/**
 * ExerciseCard Component
 * 
 * Displays an exercise with type badge, difficulty, prompt, context, and hints.
 */

import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { clsx } from 'clsx'
import ReactMarkdown from 'react-markdown'
import { ChevronDownIcon, LightBulbIcon } from '@heroicons/react/24/outline'
import { Badge, DifficultyBadge, Card } from '../common'
import { fadeInUp } from '../../utils/animations'

const exerciseTypeConfig = {
  free_recall: { label: 'Free Recall', icon: '🧠', color: 'primary' },
  self_explain: { label: 'Self Explain', icon: '💭', color: 'info' },
  worked_example: { label: 'Worked Example', icon: '📝', color: 'success' },
  debugging: { label: 'Debugging', icon: '🐛', color: 'warning' },
  code_completion: { label: 'Code Completion', icon: '⌨️', color: 'primary' },
  implementation: { label: 'Implementation', icon: '🔧', color: 'danger' },
  teach_back: { label: 'Teach Back', icon: '🎓', color: 'secondary' },
}

export function ExerciseCard({
  exercise,
  showHints = true,
  onHintUsed,
  className,
}) {
  const [showContext, setShowContext] = useState(false)
  const [hintsRevealed, setHintsRevealed] = useState(0)

  const typeConfig = exerciseTypeConfig[exercise.exercise_type] || {
    label: exercise.exercise_type,
    icon: '📋',
    color: 'default',
  }

  const hasContext = exercise.context || exercise.code_snippet
  const hasHints = showHints && exercise.hints && exercise.hints.length > 0

  const revealHint = () => {
    if (hintsRevealed < exercise.hints.length) {
      setHintsRevealed(hintsRevealed + 1)
      onHintUsed?.()
    }
  }

  return (
    <motion.div
      variants={fadeInUp}
      initial="hidden"
      animate="show"
      className={className}
    >
      <Card variant="elevated" padding="lg" className="space-y-6">
        {/* Header */}
        <div className="flex items-start justify-between gap-4">
          <div className="flex items-center gap-3">
            <span className="text-2xl">{typeConfig.icon}</span>
            <div>
              <Badge variant={typeConfig.color} size="sm">
                {typeConfig.label}
              </Badge>
              {exercise.topic_path && (
                <p className="text-xs text-text-muted mt-1">
                  {exercise.topic_path}
                </p>
              )}
            </div>
          </div>
          
          {exercise.difficulty && (
            <DifficultyBadge level={exercise.difficulty} />
          )}
        </div>

        {/* Prompt */}
        <div className="prose prose-invert prose-sm max-w-none">
          <ReactMarkdown>{exercise.prompt}</ReactMarkdown>
        </div>

        {/* Context/Code Snippet */}
        {hasContext && (
          <div>
            <button
              onClick={() => setShowContext(!showContext)}
              className={clsx(
                'flex items-center gap-2 text-sm font-medium',
                'text-text-secondary hover:text-text-primary transition-colors'
              )}
            >
              <ChevronDownIcon className={clsx(
                'w-4 h-4 transition-transform',
                showContext && 'rotate-180'
              )} />
              {showContext ? 'Hide Context' : 'Show Context'}
            </button>

            <AnimatePresence>
              {showContext && (
                <motion.div
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: 'auto', opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  transition={{ duration: 0.2 }}
                  className="overflow-hidden"
                >
                  <div className="mt-3 p-4 bg-bg-tertiary rounded-lg">
                    {exercise.context && (
                      <div className="prose prose-invert prose-sm max-w-none mb-4">
                        <ReactMarkdown>{exercise.context}</ReactMarkdown>
                      </div>
                    )}
                    
                    {exercise.code_snippet && (
                      <div className="relative">
                        {exercise.language && (
                          <span className="absolute top-2 right-2 text-xs text-text-muted bg-slate-700 px-2 py-1 rounded">
                            {exercise.language}
                          </span>
                        )}
                        <pre className="bg-slate-800/80 rounded-lg p-4 overflow-x-auto text-sm">
                          <code className="text-slate-300 font-mono">
                            {exercise.code_snippet}
                          </code>
                        </pre>
                      </div>
                    )}
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        )}

        {/* Hints */}
        {hasHints && (
          <div className="border-t border-border-primary pt-4">
            <div className="flex items-center justify-between mb-3">
              <span className="text-sm text-text-muted flex items-center gap-2">
                <LightBulbIcon className="w-4 h-4" />
                Hints ({hintsRevealed}/{exercise.hints.length})
              </span>
              
              {hintsRevealed < exercise.hints.length && (
                <button
                  onClick={revealHint}
                  className={clsx(
                    'text-sm font-medium text-accent-secondary',
                    'hover:text-accent-tertiary transition-colors'
                  )}
                >
                  Reveal Hint
                </button>
              )}
            </div>

            {hintsRevealed > 0 && (
              <div className="space-y-2">
                {exercise.hints.slice(0, hintsRevealed).map((hint, index) => (
                  <motion.div
                    key={index}
                    initial={{ opacity: 0, y: -10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="p-3 bg-amber-500/10 border border-amber-500/20 rounded-lg text-sm text-amber-200"
                  >
                    <span className="font-medium text-amber-400">Hint {index + 1}:</span>{' '}
                    {hint}
                  </motion.div>
                ))}
              </div>
            )}
          </div>
        )}
      </Card>
    </motion.div>
  )
}

export default ExerciseCard
