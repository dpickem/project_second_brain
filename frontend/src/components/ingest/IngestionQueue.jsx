/**
 * IngestionQueue Component
 *
 * Shows a filterable, auto-refreshing list of content items
 * in the ingestion/processing pipeline.
 */

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { motion, AnimatePresence } from 'framer-motion'
import { clsx } from 'clsx'
import PropTypes from 'prop-types'
import {
  QueueListIcon,
  ArrowPathIcon,
} from '@heroicons/react/24/outline'
import { Card, EmptyState, Spinner } from '../common'
import { ingestionApi } from '../../api/ingestion'
import { QueueItem } from './QueueItem'
import { QueueItemDetail } from './QueueItemDetail'
import { staggerContainer, fadeInUp } from '../../utils/animations'

const STATUS_FILTERS = [
  { id: null, label: 'All' },
  { id: 'pending', label: 'Pending' },
  { id: 'processing', label: 'Processing' },
  { id: 'processed', label: 'Completed' },
  { id: 'failed', label: 'Failed' },
]

const POLL_INTERVAL_MS = 10000

export function IngestionQueue({ className }) {
  const [statusFilter, setStatusFilter] = useState(null)
  const [selectedUuid, setSelectedUuid] = useState(null)

  const {
    data: queueData,
    isLoading,
    isRefetching,
    refetch,
  } = useQuery({
    queryKey: ['ingestion-queue', statusFilter],
    queryFn: () =>
      ingestionApi.getQueueItems({
        status: statusFilter || undefined,
        limit: 50,
        offset: 0,
      }),
    refetchInterval: POLL_INTERVAL_MS,
  })

  const items = queueData?.items || []
  const total = queueData?.total || 0

  const handleItemClick = (item) => {
    setSelectedUuid(
      selectedUuid === item.content_uuid ? null : item.content_uuid
    )
  }

  return (
    <div className={clsx('flex gap-4', className)}>
      {/* Queue list */}
      <Card className="flex-1 flex flex-col min-h-0">
        {/* Header */}
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <span className="w-8 h-8 bg-indigo-600/20 rounded-lg flex items-center justify-center">
              <QueueListIcon className="w-4 h-4 text-indigo-400" />
            </span>
            <h2 className="text-lg font-semibold text-text-primary font-heading">
              Ingestion Queue
            </h2>
            <span className="text-sm text-text-muted">({total})</span>
          </div>
          <button
            onClick={() => refetch()}
            disabled={isRefetching}
            className={clsx(
              'p-2 rounded-lg text-text-muted hover:text-text-primary hover:bg-bg-hover transition-all',
              isRefetching && 'animate-spin'
            )}
            aria-label="Refresh queue"
          >
            <ArrowPathIcon className="w-4 h-4" />
          </button>
        </div>

        {/* Status filter tabs */}
        <div
          className="flex gap-1 mb-4 p-1 bg-bg-tertiary rounded-lg overflow-x-auto"
          role="tablist"
          aria-label="Filter by status"
        >
          {STATUS_FILTERS.map((filter) => (
            <button
              key={filter.id || 'all'}
              role="tab"
              aria-selected={statusFilter === filter.id}
              onClick={() => {
                setStatusFilter(filter.id)
                setSelectedUuid(null)
              }}
              className={clsx(
                'px-3 py-1.5 rounded-md text-xs font-medium whitespace-nowrap',
                'transition-all duration-200',
                statusFilter === filter.id
                  ? 'bg-bg-elevated text-text-primary shadow-sm'
                  : 'text-text-muted hover:text-text-secondary'
              )}
            >
              {filter.label}
            </button>
          ))}
        </div>

        {/* Queue items list */}
        <div className="flex-1 overflow-y-auto min-h-0">
          {isLoading ? (
            <div className="flex items-center justify-center py-12">
              <Spinner />
            </div>
          ) : items.length === 0 ? (
            <EmptyState
              icon={<QueueListIcon className="w-12 h-12" />}
              title="No items in queue"
              description={
                statusFilter
                  ? `No ${statusFilter} items found. Try a different filter.`
                  : 'Capture some content above to get started!'
              }
            />
          ) : (
            <motion.div
              variants={staggerContainer}
              initial="hidden"
              animate="show"
              className="space-y-1"
            >
              {items.map((item) => (
                <motion.div key={item.content_uuid} variants={fadeInUp}>
                  <QueueItem
                    item={item}
                    isSelected={selectedUuid === item.content_uuid}
                    onClick={handleItemClick}
                  />
                </motion.div>
              ))}
            </motion.div>
          )}
        </div>
      </Card>

      {/* Detail panel */}
      <AnimatePresence>
        {selectedUuid && (
          <motion.div
            initial={{ width: 0, opacity: 0 }}
            animate={{ width: 400, opacity: 1 }}
            exit={{ width: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="flex-shrink-0 overflow-hidden"
          >
            <QueueItemDetail
              contentUuid={selectedUuid}
              onClose={() => setSelectedUuid(null)}
            />
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

IngestionQueue.propTypes = {
  className: PropTypes.string,
}

export default IngestionQueue
