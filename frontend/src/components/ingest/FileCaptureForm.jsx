/**
 * FileCaptureForm Component
 *
 * Drag-and-drop file upload form for PDFs, images, and voice memos.
 * Detects file type and shows relevant options.
 */

import { useState, useCallback, useRef } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import PropTypes from 'prop-types'
import { motion, AnimatePresence } from 'framer-motion'
import {
  ArrowUpTrayIcon,
  DocumentIcon,
  PhotoIcon,
  MicrophoneIcon,
  XMarkIcon,
} from '@heroicons/react/24/outline'
import { Button, Input } from '../common'
import { captureApi } from '../../api/capture'
import { API_URL } from '../../api/client'
import { fadeInUp } from '../../utils/animations'

const ACCEPTED_TYPES = {
  'application/pdf': { icon: DocumentIcon, label: 'PDF', endpoint: 'pdf' },
  'image/jpeg': { icon: PhotoIcon, label: 'Photo', endpoint: 'photo' },
  'image/png': { icon: PhotoIcon, label: 'Photo', endpoint: 'photo' },
  'image/heic': { icon: PhotoIcon, label: 'Photo', endpoint: 'photo' },
  'image/heif': { icon: PhotoIcon, label: 'Photo', endpoint: 'photo' },
  'audio/mp4': { icon: MicrophoneIcon, label: 'Voice', endpoint: 'voice' },
  'audio/x-m4a': { icon: MicrophoneIcon, label: 'Voice', endpoint: 'voice' },
  'audio/mpeg': { icon: MicrophoneIcon, label: 'Voice', endpoint: 'voice' },
  'audio/wav': { icon: MicrophoneIcon, label: 'Voice', endpoint: 'voice' },
}

const ACCEPT_STRING = Object.keys(ACCEPTED_TYPES).join(',') + ',.pdf,.jpg,.jpeg,.png,.heic,.m4a,.mp3,.wav'

function getFileType(file) {
  // Check MIME type first
  if (ACCEPTED_TYPES[file.type]) {
    return ACCEPTED_TYPES[file.type]
  }
  // Fallback to extension
  const ext = file.name.split('.').pop()?.toLowerCase()
  const extMap = {
    pdf: ACCEPTED_TYPES['application/pdf'],
    jpg: ACCEPTED_TYPES['image/jpeg'],
    jpeg: ACCEPTED_TYPES['image/jpeg'],
    png: ACCEPTED_TYPES['image/png'],
    heic: ACCEPTED_TYPES['image/heic'],
    m4a: ACCEPTED_TYPES['audio/mp4'],
    mp3: ACCEPTED_TYPES['audio/mpeg'],
    wav: ACCEPTED_TYPES['audio/wav'],
  }
  return extMap[ext] || { icon: DocumentIcon, label: 'File', endpoint: 'file' }
}

function formatFileSize(bytes) {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

export function FileCaptureForm({ onSuccess }) {
  const [file, setFile] = useState(null)
  const [isDragOver, setIsDragOver] = useState(false)
  const [tags, setTags] = useState('')
  const [contentTypeHint, setContentTypeHint] = useState('')
  const [showOptions, setShowOptions] = useState(false)
  const fileInputRef = useRef(null)

  const queryClient = useQueryClient()

  const fileType = file ? getFileType(file) : null

  const mutation = useMutation({
    mutationFn: async ({ file, tags, contentTypeHint }) => {
      const formData = new FormData()
      formData.append('file', file)
      if (tags) formData.append('tags', tags)
      if (contentTypeHint) formData.append('content_type', contentTypeHint)

      const endpoint = fileType?.endpoint || 'file'
      const response = await fetch(`${API_URL}/api/capture/${endpoint}`, {
        method: 'POST',
        body: formData,
      })
      if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: response.statusText }))
        throw new Error(error.detail || `Upload failed: ${response.statusText}`)
      }
      return response.json()
    },
    onSuccess: (data) => {
      setFile(null)
      setTags('')
      setContentTypeHint('')
      toast.success(`${fileType?.label || 'File'} uploaded successfully!`)
      queryClient.invalidateQueries({ queryKey: ['ingestion-queue'] })
      onSuccess?.(data)
    },
    onError: (error) => {
      toast.error(error.message || 'Upload failed')
    },
  })

  const handleDrop = useCallback((e) => {
    e.preventDefault()
    setIsDragOver(false)
    const droppedFile = e.dataTransfer.files[0]
    if (droppedFile) setFile(droppedFile)
  }, [])

  const handleDragOver = useCallback((e) => {
    e.preventDefault()
    setIsDragOver(true)
  }, [])

  const handleDragLeave = useCallback(() => {
    setIsDragOver(false)
  }, [])

  const handleFileSelect = useCallback((e) => {
    const selectedFile = e.target.files[0]
    if (selectedFile) setFile(selectedFile)
  }, [])

  const handleSubmit = useCallback(
    (e) => {
      e?.preventDefault()
      if (!file) return
      mutation.mutate({
        file,
        tags: tags
          .split(',')
          .map((t) => t.trim())
          .filter(Boolean)
          .join(','),
        contentTypeHint: contentTypeHint || undefined,
      })
    },
    [file, tags, contentTypeHint, mutation]
  )

  const FileIcon = fileType?.icon || DocumentIcon

  return (
    <motion.form
      variants={fadeInUp}
      initial="hidden"
      animate="show"
      onSubmit={handleSubmit}
      className="space-y-4"
    >
      <div className="flex items-center gap-2 mb-2">
        <ArrowUpTrayIcon className="w-5 h-5 text-indigo-400" />
        <h3 className="text-sm font-semibold text-text-primary">
          Upload File
        </h3>
      </div>

      {/* Drop zone */}
      <div
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onClick={() => fileInputRef.current?.click()}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') fileInputRef.current?.click()
        }}
        className={`
          relative flex flex-col items-center justify-center p-6 rounded-xl border-2 border-dashed
          cursor-pointer transition-all duration-200
          ${
            isDragOver
              ? 'border-indigo-500 bg-indigo-500/10'
              : file
              ? 'border-emerald-500/50 bg-emerald-500/5'
              : 'border-border-primary hover:border-border-focus hover:bg-bg-hover'
          }
        `}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept={ACCEPT_STRING}
          onChange={handleFileSelect}
          className="hidden"
          aria-label="Upload file"
        />

        <AnimatePresence mode="wait">
          {file ? (
            <motion.div
              key="file-info"
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.9 }}
              className="flex items-center gap-3 w-full"
            >
              <FileIcon className="w-8 h-8 text-emerald-400 flex-shrink-0" />
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-text-primary truncate">
                  {file.name}
                </p>
                <p className="text-xs text-text-muted">
                  {formatFileSize(file.size)} &middot; {fileType?.label}
                </p>
              </div>
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation()
                  setFile(null)
                }}
                className="p-1 text-text-muted hover:text-text-primary transition-colors"
                aria-label="Remove file"
              >
                <XMarkIcon className="w-4 h-4" />
              </button>
            </motion.div>
          ) : (
            <motion.div
              key="drop-hint"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="text-center"
            >
              <ArrowUpTrayIcon className="w-8 h-8 text-text-muted mx-auto mb-2" />
              <p className="text-sm text-text-secondary">
                Drop a file here or click to browse
              </p>
              <p className="text-xs text-text-muted mt-1">
                PDF, images (JPG, PNG, HEIC), audio (M4A, MP3, WAV)
              </p>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Collapsible options */}
      {file && (
        <>
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
                value={contentTypeHint}
                onChange={(e) => setContentTypeHint(e.target.value)}
                placeholder="Content type hint (e.g., article, paper, book)"
                disabled={mutation.isPending}
              />
              <Input
                value={tags}
                onChange={(e) => setTags(e.target.value)}
                placeholder="Tags (comma separated)"
                disabled={mutation.isPending}
              />
            </motion.div>
          )}
        </>
      )}

      <div className="flex justify-end pt-2">
        <Button
          type="submit"
          loading={mutation.isPending}
          disabled={!file}
          size="sm"
        >
          Upload
        </Button>
      </div>
    </motion.form>
  )
}

FileCaptureForm.propTypes = {
  onSuccess: PropTypes.func,
}

export default FileCaptureForm
