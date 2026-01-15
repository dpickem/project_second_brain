/**
 * QuickCapture Component
 * 
 * Inline text capture with success feedback and optional learning material generation.
 */

import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { clsx } from 'clsx'
import { useMutation } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { Card, Button, Textarea, Checkbox } from '../common'
import { captureApi } from '../../api/capture'
import { scaleIn } from '../../utils/animations'

export function QuickCapture({
  onSuccess,
  placeholder = 'Capture a thought, idea, or note...',
  className,
}) {
  const [text, setText] = useState('')
  const [showSuccess, setShowSuccess] = useState(false)
  const [createCards, setCreateCards] = useState(false)
  const [createExercises, setCreateExercises] = useState(false)

  const captureMutation = useMutation({
    mutationFn: captureApi.captureText,
    onSuccess: (data) => {
      setText('')
      setShowSuccess(true)
      setTimeout(() => setShowSuccess(false), 2000)
      toast.success('Captured successfully!')
      onSuccess?.(data)
    },
    onError: (error) => {
      toast.error(error.response?.data?.detail || 'Failed to capture')
    },
  })

  const handleSubmit = (e) => {
    e?.preventDefault()
    if (!text.trim()) return
    captureMutation.mutate({ 
      text: text.trim(),
      createCards,
      createExercises,
    })
  }

  const handleKeyDown = (e) => {
    if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
      handleSubmit()
    }
  }

  return (
    <Card className={clsx('relative overflow-hidden', className)}>
      {/* Header */}
      <div className="flex items-center gap-2 mb-4">
        <span className="w-8 h-8 bg-indigo-600/20 rounded-lg flex items-center justify-center">
          ⚡
        </span>
        <h3 className="text-lg font-semibold text-text-primary font-heading">
          Quick Capture
        </h3>
      </div>

      {/* Form */}
      <form onSubmit={handleSubmit}>
        <Textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          rows={4}
          disabled={captureMutation.isPending}
          className="resize-none"
        />

        {/* Learning material toggles */}
        <div className="flex items-center gap-6 mt-3 pt-3 border-t border-border-primary">
          <Checkbox
            id="create-cards"
            checked={createCards}
            onChange={(e) => setCreateCards(e.target.checked)}
            label="Create Cards"
          />
          <Checkbox
            id="create-exercises"
            checked={createExercises}
            onChange={(e) => setCreateExercises(e.target.checked)}
            label="Create Exercises"
          />
        </div>

        <div className="flex items-center justify-between mt-4">
          {/* Keyboard shortcut hint */}
          <p className="text-xs text-text-muted">
            <kbd className="px-1.5 py-0.5 bg-slate-700 rounded text-slate-400">⌘</kbd>
            {' + '}
            <kbd className="px-1.5 py-0.5 bg-slate-700 rounded text-slate-400">Enter</kbd>
            {' to capture'}
          </p>

          {/* Submit button */}
          <Button
            type="submit"
            loading={captureMutation.isPending}
            disabled={!text.trim()}
          >
            Capture
          </Button>
        </div>
      </form>

      {/* Success overlay */}
      <AnimatePresence>
        {showSuccess && (
          <motion.div
            variants={scaleIn}
            initial="hidden"
            animate="show"
            exit="exit"
            className={clsx(
              'absolute inset-0 flex items-center justify-center',
              'bg-bg-elevated/95 backdrop-blur-sm'
            )}
          >
            <div className="text-center">
              <motion.div
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                transition={{ type: 'spring', stiffness: 300, damping: 20 }}
                className="w-16 h-16 bg-emerald-500/20 rounded-full flex items-center justify-center mx-auto mb-3"
              >
                <span className="text-3xl">✓</span>
              </motion.div>
              <p className="text-lg font-medium text-text-primary">Captured!</p>
              <p className="text-sm text-text-secondary mt-1">Your note has been saved</p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </Card>
  )
}

// Minimal inline capture variant
export function InlineCapture({ onSuccess, className }) {
  const [text, setText] = useState('')
  const [isFocused, setIsFocused] = useState(false)

  const captureMutation = useMutation({
    mutationFn: captureApi.captureText,
    onSuccess: (data) => {
      setText('')
      setIsFocused(false)
      toast.success('Captured!')
      onSuccess?.(data)
    },
  })

  return (
    <motion.div
      className={clsx('relative', className)}
      animate={{ height: isFocused ? 'auto' : '48px' }}
    >
      <div className={clsx(
        'flex items-center gap-2 rounded-xl border transition-all',
        isFocused 
          ? 'bg-bg-elevated border-border-focus ring-2 ring-indigo-500/20' 
          : 'bg-bg-tertiary border-border-primary'
      )}>
        <input
          type="text"
          value={text}
          onChange={(e) => setText(e.target.value)}
          onFocus={() => setIsFocused(true)}
          onBlur={() => !text && setIsFocused(false)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && text.trim()) {
              captureMutation.mutate({ text: text.trim() })
            }
          }}
          placeholder="Quick capture..."
          className="flex-1 bg-transparent px-4 py-3 text-text-primary placeholder-text-muted focus:outline-none"
        />
        
        <AnimatePresence>
          {text.trim() && (
            <motion.div
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.8 }}
              className="pr-2"
            >
              <Button
                size="sm"
                loading={captureMutation.isPending}
                onClick={() => captureMutation.mutate({ text: text.trim() })}
              >
                Capture
              </Button>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </motion.div>
  )
}

export default QuickCapture
