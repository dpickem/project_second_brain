/**
 * TextCaptureForm Component
 *
 * Form for capturing quick text notes/ideas into the knowledge system.
 * Mirrors the PWA TextCapture but styled for the desktop web UI.
 */

import { useState, useCallback } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import PropTypes from 'prop-types'
import { motion } from 'framer-motion'
import { DocumentTextIcon } from '@heroicons/react/24/outline'
import { Button, Input, Textarea, Checkbox } from '../common'
import { captureApi } from '../../api/capture'
import { fadeInUp } from '../../utils/animations'

export function TextCaptureForm({ onSuccess }) {
  const [text, setText] = useState('')
  const [title, setTitle] = useState('')
  const [tags, setTags] = useState('')
  const [createCards, setCreateCards] = useState(false)
  const [createExercises, setCreateExercises] = useState(false)
  const [showOptions, setShowOptions] = useState(false)

  const queryClient = useQueryClient()

  const mutation = useMutation({
    mutationFn: captureApi.captureText,
    onSuccess: (data) => {
      setText('')
      setTitle('')
      setTags('')
      setCreateCards(false)
      setCreateExercises(false)
      toast.success('Text captured successfully!')
      queryClient.invalidateQueries({ queryKey: ['ingestion-queue'] })
      onSuccess?.(data)
    },
    onError: (error) => {
      toast.error(error.message || 'Failed to capture text')
    },
  })

  const handleSubmit = useCallback(
    (e) => {
      e?.preventDefault()
      if (!text.trim()) return
      mutation.mutate({
        text: text.trim(),
        title: title.trim() || undefined,
        tags: tags
          .split(',')
          .map((t) => t.trim())
          .filter(Boolean),
        createCards,
        createExercises,
      })
    },
    [text, title, tags, createCards, createExercises, mutation]
  )

  const handleKeyDown = useCallback(
    (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
        handleSubmit()
      }
    },
    [handleSubmit]
  )

  return (
    <motion.form
      variants={fadeInUp}
      initial="hidden"
      animate="show"
      onSubmit={handleSubmit}
      className="space-y-4"
    >
      <div className="flex items-center gap-2 mb-2">
        <DocumentTextIcon className="w-5 h-5 text-indigo-400" />
        <h3 className="text-sm font-semibold text-text-primary">Quick Note</h3>
      </div>

      <Textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="What's on your mind?"
        rows={5}
        disabled={mutation.isPending}
        className="resize-none"
      />

      {/* Collapsible options */}
      <button
        type="button"
        onClick={() => setShowOptions(!showOptions)}
        className="flex items-center gap-1 text-xs text-text-muted hover:text-text-secondary transition-colors"
      >
        <span>{showOptions ? '▾' : '▸'}</span>
        <span>Options</span>
      </button>

      {showOptions && (
        <motion.div
          initial={{ height: 0, opacity: 0 }}
          animate={{ height: 'auto', opacity: 1 }}
          className="space-y-3 overflow-hidden"
        >
          <Input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Title (optional)"
            disabled={mutation.isPending}
          />
          <Input
            value={tags}
            onChange={(e) => setTags(e.target.value)}
            placeholder="Tags (comma separated)"
            disabled={mutation.isPending}
          />
          <div className="flex items-center gap-6">
            <Checkbox
              id="text-create-cards"
              checked={createCards}
              onChange={(e) => setCreateCards(e.target.checked)}
              label="Create Cards"
            />
            <Checkbox
              id="text-create-exercises"
              checked={createExercises}
              onChange={(e) => setCreateExercises(e.target.checked)}
              label="Create Exercises"
            />
          </div>
        </motion.div>
      )}

      <div className="flex items-center justify-between pt-2">
        <p className="text-xs text-text-muted">
          <kbd className="px-1.5 py-0.5 bg-slate-700 rounded text-slate-400">
            ⌘
          </kbd>{' '}
          +{' '}
          <kbd className="px-1.5 py-0.5 bg-slate-700 rounded text-slate-400">
            Enter
          </kbd>{' '}
          to capture
        </p>
        <Button
          type="submit"
          loading={mutation.isPending}
          disabled={!text.trim()}
          size="sm"
        >
          Capture
        </Button>
      </div>
    </motion.form>
  )
}

TextCaptureForm.propTypes = {
  onSuccess: PropTypes.func,
}

export default TextCaptureForm
