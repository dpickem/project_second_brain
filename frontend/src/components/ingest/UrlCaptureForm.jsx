/**
 * UrlCaptureForm Component
 *
 * Form for capturing URLs (articles, blog posts) for extraction and processing.
 */

import { useState, useCallback } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import PropTypes from 'prop-types'
import { motion } from 'framer-motion'
import { LinkIcon } from '@heroicons/react/24/outline'
import { Button, Input, Textarea } from '../common'
import { captureApi } from '../../api/capture'
import { fadeInUp } from '../../utils/animations'

const URL_REGEX = /^https?:\/\/.+/i

export function UrlCaptureForm({ onSuccess }) {
  const [url, setUrl] = useState('')
  const [notes, setNotes] = useState('')
  const [tags, setTags] = useState('')
  const [showOptions, setShowOptions] = useState(false)

  const queryClient = useQueryClient()

  const isValidUrl = URL_REGEX.test(url.trim())

  const mutation = useMutation({
    mutationFn: captureApi.captureUrl,
    onSuccess: (data) => {
      setUrl('')
      setNotes('')
      setTags('')
      toast.success('URL captured successfully!')
      queryClient.invalidateQueries({ queryKey: ['ingestion-queue'] })
      onSuccess?.(data)
    },
    onError: (error) => {
      toast.error(error.message || 'Failed to capture URL')
    },
  })

  const handleSubmit = useCallback(
    (e) => {
      e?.preventDefault()
      if (!isValidUrl) return
      mutation.mutate({
        url: url.trim(),
        notes: notes.trim() || undefined,
        tags: tags
          .split(',')
          .map((t) => t.trim())
          .filter(Boolean),
      })
    },
    [url, notes, tags, isValidUrl, mutation]
  )

  const handlePaste = useCallback(async () => {
    try {
      const text = await navigator.clipboard.readText()
      if (URL_REGEX.test(text.trim())) {
        setUrl(text.trim())
      }
    } catch {
      // Clipboard access denied - ignore
    }
  }, [])

  return (
    <motion.form
      variants={fadeInUp}
      initial="hidden"
      animate="show"
      onSubmit={handleSubmit}
      className="space-y-4"
    >
      <div className="flex items-center gap-2 mb-2">
        <LinkIcon className="w-5 h-5 text-indigo-400" />
        <h3 className="text-sm font-semibold text-text-primary">Save URL</h3>
      </div>

      <div className="relative">
        <Input
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="https://..."
          type="url"
          disabled={mutation.isPending}
        />
        {!url && (
          <button
            type="button"
            onClick={handlePaste}
            className="absolute right-2 top-1/2 -translate-y-1/2 text-xs text-indigo-400 hover:text-indigo-300 transition-colors"
          >
            Paste
          </button>
        )}
      </div>

      {url && !isValidUrl && (
        <p className="text-xs text-red-400">Please enter a valid URL starting with http:// or https://</p>
      )}

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
          <Textarea
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="Notes about this URL (optional)"
            rows={2}
            disabled={mutation.isPending}
            className="resize-none"
          />
          <Input
            value={tags}
            onChange={(e) => setTags(e.target.value)}
            placeholder="Tags (comma separated)"
            disabled={mutation.isPending}
          />
        </motion.div>
      )}

      <div className="flex justify-end pt-2">
        <Button
          type="submit"
          loading={mutation.isPending}
          disabled={!isValidUrl}
          size="sm"
        >
          Capture
        </Button>
      </div>
    </motion.form>
  )
}

UrlCaptureForm.propTypes = {
  onSuccess: PropTypes.func,
}

export default UrlCaptureForm
