/**
 * QueueItem Component
 *
 * Single row in the ingestion queue showing content type icon,
 * title, status badge, and timestamp.
 */

import { memo } from 'react'
import { motion } from 'framer-motion'
import { clsx } from 'clsx'
import PropTypes from 'prop-types'
import { format, formatDistanceToNow } from 'date-fns'
import {
  DocumentTextIcon,
  LinkIcon,
  DocumentIcon,
  PhotoIcon,
  MicrophoneIcon,
  BeakerIcon,
  ExclamationTriangleIcon,
} from '@heroicons/react/24/outline'
import { StatusBadge } from '../common'

const TYPE_ICONS = {
  article: LinkIcon,
  paper: DocumentIcon,
  book: DocumentIcon,
  code: BeakerIcon,
  idea: DocumentTextIcon,
  text: DocumentTextIcon,
  photo: PhotoIcon,
  voice: MicrophoneIcon,
  pdf: DocumentIcon,
}

const STATUS_VARIANTS = {
  PENDING: 'warning',
  PROCESSING: 'info',
  PROCESSED: 'success',
  FAILED: 'error',
}

function QueueItemInner({ item, isSelected, onClick }) {
  const Icon = TYPE_ICONS[item.content_type] || DocumentIcon
  const statusVariant = STATUS_VARIANTS[item.status] || 'default'
  const hasError = item.error_message || item.status === 'FAILED'

  const timeAgo = item.created_at
    ? formatDistanceToNow(new Date(item.created_at), { addSuffix: true })
    : ''

  return (
    <motion.button
      whileHover={{ x: 2 }}
      onClick={() => onClick(item)}
      className={clsx(
        'w-full flex items-center gap-3 p-3 rounded-lg text-left transition-all',
        'focus:outline-none focus:ring-2 focus:ring-accent-primary/50',
        isSelected
          ? 'bg-indigo-500/15 border border-indigo-500/30'
          : 'hover:bg-bg-hover border border-transparent'
      )}
    >
      {/* Type icon */}
      <div
        className={clsx(
          'w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0',
          hasError ? 'bg-red-500/15' : 'bg-bg-tertiary'
        )}
      >
        {hasError ? (
          <ExclamationTriangleIcon className="w-4 h-4 text-red-400" />
        ) : (
          <Icon className="w-4 h-4 text-text-muted" />
        )}
      </div>

      {/* Title and metadata */}
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-text-primary truncate">
          {item.title || 'Untitled'}
        </p>
        <p className="text-xs text-text-muted truncate">
          {item.content_type} &middot; {timeAgo}
        </p>
      </div>

      {/* Status badge */}
      <StatusBadge status={statusVariant} className="flex-shrink-0">
        {item.status}
      </StatusBadge>
    </motion.button>
  )
}

QueueItemInner.propTypes = {
  item: PropTypes.shape({
    id: PropTypes.number.isRequired,
    content_uuid: PropTypes.string.isRequired,
    title: PropTypes.string,
    content_type: PropTypes.string,
    status: PropTypes.string.isRequired,
    error_message: PropTypes.string,
    created_at: PropTypes.string,
  }).isRequired,
  isSelected: PropTypes.bool,
  onClick: PropTypes.func.isRequired,
}

export const QueueItem = memo(QueueItemInner)
export default QueueItem
