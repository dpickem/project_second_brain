/**
 * QueueItemDetail Component
 *
 * Expanded detail panel showing full metadata, processing stages,
 * error messages, and link to the note in Knowledge Explorer.
 */

import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { clsx } from 'clsx'
import PropTypes from 'prop-types'
import { Link } from 'react-router-dom'
import { format } from 'date-fns'
import {
  XMarkIcon,
  ArrowTopRightOnSquareIcon,
  CheckCircleIcon,
  ExclamationCircleIcon,
  ClockIcon,
} from '@heroicons/react/24/outline'
import { Card, StatusBadge, Spinner } from '../common'
import { ingestionApi } from '../../api/ingestion'
import { fadeInUp } from '../../utils/animations'

const STAGE_LABELS = {
  content_analysis: 'Content Analysis',
  summarization: 'Summarization',
  extraction: 'Extraction',
  tagging: 'Tagging',
  obsidian_sync: 'Obsidian Note',
  neo4j_sync: 'Knowledge Graph',
}

const ALL_STAGES = Object.keys(STAGE_LABELS)

export function QueueItemDetail({ contentUuid, onClose }) {
  const { data: detail, isLoading, error } = useQuery({
    queryKey: ['ingestion-detail', contentUuid],
    queryFn: () => ingestionApi.getQueueItemDetail(contentUuid),
    enabled: !!contentUuid,
    refetchInterval: (query) => {
      // Auto-refresh if item is still processing
      const status = query.state.data?.status
      if (status === 'PENDING' || status === 'PROCESSING') return 5000
      return false
    },
  })

  if (!contentUuid) return null

  return (
    <motion.div
      variants={fadeInUp}
      initial="hidden"
      animate="show"
      className="h-full"
    >
      <Card className="h-full flex flex-col">
        {/* Header */}
        <div className="flex items-start justify-between mb-4">
          <div className="flex-1 min-w-0">
            <h3 className="text-lg font-semibold text-text-primary truncate">
              {detail?.title || 'Loading...'}
            </h3>
            {detail && (
              <p className="text-xs text-text-muted mt-1">
                {detail.content_type} &middot;{' '}
                {detail.created_at
                  ? format(new Date(detail.created_at), 'PPp')
                  : 'Unknown date'}
              </p>
            )}
          </div>
          <button
            onClick={onClose}
            className="p-1 text-text-muted hover:text-text-primary transition-colors flex-shrink-0"
            aria-label="Close detail panel"
          >
            <XMarkIcon className="w-5 h-5" />
          </button>
        </div>

        {/* Loading state */}
        {isLoading && (
          <div className="flex-1 flex items-center justify-center">
            <Spinner />
          </div>
        )}

        {/* Error state */}
        {error && (
          <div className="p-4 rounded-lg bg-red-500/10 border border-red-500/20">
            <p className="text-sm text-red-400">
              Failed to load details: {error.message}
            </p>
          </div>
        )}

        {/* Detail content */}
        {detail && (
          <div className="flex-1 overflow-y-auto space-y-4">
            {/* Status row */}
            <div className="flex items-center gap-3">
              <span className="text-sm text-text-muted">Status:</span>
              <StatusBadge
                status={
                  detail.status === 'PROCESSED'
                    ? 'success'
                    : detail.status === 'FAILED'
                    ? 'error'
                    : detail.status === 'PROCESSING'
                    ? 'info'
                    : 'warning'
                }
              >
                {detail.status}
              </StatusBadge>
            </div>

            {/* Source URL */}
            {detail.source_url && (
              <div>
                <span className="text-xs font-medium text-text-muted uppercase tracking-wider">
                  Source
                </span>
                <a
                  href={detail.source_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="block text-sm text-indigo-400 hover:text-indigo-300 truncate mt-1"
                >
                  {detail.source_url}
                </a>
              </div>
            )}

            {/* Summary preview */}
            {detail.summary && (
              <div>
                <span className="text-xs font-medium text-text-muted uppercase tracking-wider">
                  Summary
                </span>
                <p className="text-sm text-text-secondary mt-1 line-clamp-4">
                  {detail.summary}
                </p>
              </div>
            )}

            {/* Processing stages */}
            {detail.processing && (
              <div>
                <span className="text-xs font-medium text-text-muted uppercase tracking-wider">
                  Processing Stages
                </span>
                <div className="mt-2 space-y-1.5">
                  {ALL_STAGES.map((stage) => {
                    const completed =
                      detail.processing.stages_completed?.includes(stage)
                    return (
                      <div
                        key={stage}
                        className="flex items-center gap-2 text-sm"
                      >
                        {completed ? (
                          <CheckCircleIcon className="w-4 h-4 text-emerald-400" />
                        ) : (
                          <div className="w-4 h-4 rounded-full border border-border-primary" />
                        )}
                        <span
                          className={
                            completed
                              ? 'text-text-primary'
                              : 'text-text-muted'
                          }
                        >
                          {STAGE_LABELS[stage]}
                        </span>
                      </div>
                    )
                  })}
                </div>
              </div>
            )}

            {/* Processing stats */}
            {detail.processing?.processing_time_seconds != null && (
              <div className="flex items-center gap-4 text-xs text-text-muted">
                <span className="flex items-center gap-1">
                  <ClockIcon className="w-3.5 h-3.5" />
                  {detail.processing.processing_time_seconds.toFixed(1)}s
                </span>
                {detail.processing.estimated_cost_usd != null && (
                  <span>
                    ${detail.processing.estimated_cost_usd.toFixed(4)}
                  </span>
                )}
                {detail.processing.total_tokens != null && (
                  <span>{detail.processing.total_tokens.toLocaleString()} tokens</span>
                )}
              </div>
            )}

            {/* Error messages */}
            {(detail.ingestion_error || detail.processing?.error_message) && (
              <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/20">
                <div className="flex items-center gap-2 mb-2">
                  <ExclamationCircleIcon className="w-4 h-4 text-red-400" />
                  <span className="text-sm font-medium text-red-400">
                    Error Details
                  </span>
                </div>
                {detail.ingestion_error && (
                  <div className="mb-2">
                    <span className="text-xs text-red-400/70 font-medium">
                      Ingestion:
                    </span>
                    <pre className="text-xs text-red-300 mt-1 whitespace-pre-wrap break-words font-mono">
                      {detail.ingestion_error}
                    </pre>
                  </div>
                )}
                {detail.processing?.error_message && (
                  <div>
                    <span className="text-xs text-red-400/70 font-medium">
                      Processing:
                    </span>
                    <pre className="text-xs text-red-300 mt-1 whitespace-pre-wrap break-words font-mono">
                      {detail.processing.error_message}
                    </pre>
                  </div>
                )}
              </div>
            )}

            {/* Metadata */}
            {detail.metadata &&
              Object.keys(detail.metadata).length > 0 && (
                <div>
                  <span className="text-xs font-medium text-text-muted uppercase tracking-wider">
                    Metadata
                  </span>
                  <div className="mt-2 space-y-1">
                    {Object.entries(detail.metadata).map(([key, value]) => (
                      <div key={key} className="flex gap-2 text-xs">
                        <span className="text-text-muted font-medium min-w-[100px]">
                          {key}:
                        </span>
                        <span className="text-text-secondary truncate">
                          {typeof value === 'object'
                            ? JSON.stringify(value)
                            : String(value)}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

            {/* Link to note in Knowledge Explorer */}
            {detail.vault_path && (
              <Link
                to={`/knowledge?note=${encodeURIComponent(detail.vault_path)}`}
                className={clsx(
                  'flex items-center gap-2 p-3 rounded-lg',
                  'bg-indigo-500/10 border border-indigo-500/20',
                  'text-sm text-indigo-400 hover:text-indigo-300 transition-colors'
                )}
              >
                <ArrowTopRightOnSquareIcon className="w-4 h-4" />
                <span>Open in Knowledge Explorer</span>
              </Link>
            )}
          </div>
        )}
      </Card>
    </motion.div>
  )
}

QueueItemDetail.propTypes = {
  contentUuid: PropTypes.string,
  onClose: PropTypes.func.isRequired,
}

export default QueueItemDetail
