/**
 * FeedbackDisplay Component
 * 
 * Shows evaluation results with detailed feedback and confidence rating.
 */

import { useState } from 'react'
import { motion } from 'framer-motion'
import { clsx } from 'clsx'
import ReactMarkdown from 'react-markdown'
import { CheckCircleIcon, XCircleIcon, ChevronDownIcon } from '@heroicons/react/24/outline'
import { Card, Button } from '../common'
import { fadeInUp, scaleInBounce } from '../../utils/animations'

const confidenceOptions = [
  { value: 1, label: 'Still confused', icon: '😕', color: 'red' },
  { value: 2, label: 'Needs review', icon: '🤔', color: 'amber' },
  { value: 3, label: 'Got it', icon: '😊', color: 'indigo' },
  { value: 4, label: 'Easy!', icon: '🎯', color: 'emerald' },
]

export function FeedbackDisplay({
  evaluation,
  onConfidenceSelect,
  onContinue,
  showModelAnswer = true,
  className,
}) {
  const [showAnswer, setShowAnswer] = useState(false)
  const [selectedConfidence, setSelectedConfidence] = useState(null)

  const isCorrect = evaluation?.is_correct
  const score = evaluation?.score ?? 0
  const scorePercent = Math.round(score * 100)

  const handleConfidenceSelect = (confidence) => {
    setSelectedConfidence(confidence)
    onConfidenceSelect?.(confidence)
  }

  return (
    <motion.div
      variants={fadeInUp}
      initial="hidden"
      animate="show"
      className={className}
    >
      <Card variant="elevated" padding="lg" className="space-y-6">
        {/* Result Header */}
        <motion.div
          variants={scaleInBounce}
          initial="hidden"
          animate="show"
          className="flex items-center justify-between"
        >
          <div className="flex items-center gap-4">
            {/* Result Icon */}
            <div className={clsx(
              'w-14 h-14 rounded-full flex items-center justify-center',
              isCorrect 
                ? 'bg-emerald-500/20 text-emerald-400' 
                : 'bg-red-500/20 text-red-400'
            )}>
              {isCorrect ? (
                <CheckCircleIcon className="w-8 h-8" />
              ) : (
                <XCircleIcon className="w-8 h-8" />
              )}
            </div>

            {/* Result Text */}
            <div>
              <h3 className={clsx(
                'text-xl font-semibold font-heading',
                isCorrect ? 'text-emerald-400' : 'text-red-400'
              )}>
                {isCorrect ? 'Correct!' : 'Not quite right'}
              </h3>
              <p className="text-text-secondary">
                Score: {scorePercent}%
              </p>
            </div>
          </div>

          {/* Score Badge */}
          <div className={clsx(
            'text-3xl font-bold font-heading',
            scorePercent >= 80 && 'text-emerald-400',
            scorePercent >= 60 && scorePercent < 80 && 'text-indigo-400',
            scorePercent >= 40 && scorePercent < 60 && 'text-amber-400',
            scorePercent < 40 && 'text-red-400',
          )}>
            {scorePercent}%
          </div>
        </motion.div>

        {/* Detailed Feedback */}
        {evaluation?.feedback && (
          <div className="p-4 bg-bg-tertiary rounded-lg">
            <h4 className="text-sm font-medium text-text-primary mb-2">Feedback</h4>
            <div className="prose prose-invert prose-sm max-w-none">
              <ReactMarkdown>{evaluation.feedback}</ReactMarkdown>
            </div>
          </div>
        )}

        {/* Specific Feedback Points */}
        {evaluation?.specific_feedback && evaluation.specific_feedback.length > 0 && (
          <div className="space-y-2">
            {evaluation.specific_feedback.map((item, index) => (
              <div 
                key={index}
                className={clsx(
                  'flex items-start gap-2 p-3 rounded-lg',
                  item.type === 'positive' && 'bg-emerald-500/10 border border-emerald-500/20',
                  item.type === 'improvement' && 'bg-amber-500/10 border border-amber-500/20',
                  item.type === 'error' && 'bg-red-500/10 border border-red-500/20',
                )}
              >
                <span className="text-sm">
                  {item.type === 'positive' && '✓'}
                  {item.type === 'improvement' && '💡'}
                  {item.type === 'error' && '✗'}
                </span>
                <span className="text-sm text-text-secondary">{item.message}</span>
              </div>
            ))}
          </div>
        )}

        {/* Model Answer */}
        {showModelAnswer && evaluation?.model_answer && (
          <div>
            <button
              onClick={() => setShowAnswer(!showAnswer)}
              className={clsx(
                'flex items-center gap-2 text-sm font-medium',
                'text-accent-secondary hover:text-accent-tertiary transition-colors'
              )}
            >
              <ChevronDownIcon className={clsx(
                'w-4 h-4 transition-transform',
                showAnswer && 'rotate-180'
              )} />
              {showAnswer ? 'Hide Model Answer' : 'Show Model Answer'}
            </button>

            {showAnswer && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: 'auto', opacity: 1 }}
                className="mt-3 p-4 bg-indigo-500/10 border border-indigo-500/20 rounded-lg"
              >
                <div className="prose prose-invert prose-sm max-w-none">
                  <ReactMarkdown>{evaluation.model_answer}</ReactMarkdown>
                </div>
              </motion.div>
            )}
          </div>
        )}

        {/* Confidence Rating */}
        <div className="border-t border-border-primary pt-6">
          <h4 className="text-sm font-medium text-text-primary mb-4">
            How confident do you feel about this topic?
          </h4>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {confidenceOptions.map((option) => (
              <motion.button
                key={option.value}
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                onClick={() => handleConfidenceSelect(option.value)}
                className={clsx(
                  'p-4 rounded-xl border transition-all text-center',
                  selectedConfidence === option.value
                    ? option.color === 'red' && 'bg-red-500/20 border-red-500/50 ring-2 ring-red-500/30'
                    : '',
                  selectedConfidence === option.value
                    ? option.color === 'amber' && 'bg-amber-500/20 border-amber-500/50 ring-2 ring-amber-500/30'
                    : '',
                  selectedConfidence === option.value
                    ? option.color === 'indigo' && 'bg-indigo-500/20 border-indigo-500/50 ring-2 ring-indigo-500/30'
                    : '',
                  selectedConfidence === option.value
                    ? option.color === 'emerald' && 'bg-emerald-500/20 border-emerald-500/50 ring-2 ring-emerald-500/30'
                    : '',
                  selectedConfidence !== option.value && 'bg-bg-tertiary border-border-primary hover:border-border-secondary'
                )}
              >
                <span className="text-2xl block mb-1">{option.icon}</span>
                <span className="text-xs text-text-secondary">{option.label}</span>
              </motion.button>
            ))}
          </div>
        </div>

        {/* Continue Button */}
        <div className="flex justify-end">
          <Button
            onClick={onContinue}
            disabled={!selectedConfidence}
          >
            Continue →
          </Button>
        </div>
      </Card>
    </motion.div>
  )
}

export default FeedbackDisplay
