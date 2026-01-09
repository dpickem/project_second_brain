/**
 * TopicTree Component
 * 
 * Hierarchical navigation of topics with mastery indicators.
 */

import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { clsx } from 'clsx'
import { ChevronRightIcon } from '@heroicons/react/24/outline'
import { Skeleton } from '../common'

function getMasteryColor(mastery) {
  if (mastery >= 0.8) return 'emerald'
  if (mastery >= 0.6) return 'indigo'
  if (mastery >= 0.4) return 'amber'
  return 'red'
}

function TopicNode({ topic, level = 0, onSelect, selectedId }) {
  const [isExpanded, setIsExpanded] = useState(level < 2)
  const hasChildren = topic.children && topic.children.length > 0
  const isSelected = selectedId === topic.id
  const masteryColor = getMasteryColor(topic.mastery || 0)
  const masteryPercent = Math.round((topic.mastery || 0) * 100)

  return (
    <div>
      <motion.div
        initial={{ opacity: 0, x: -10 }}
        animate={{ opacity: 1, x: 0 }}
        className={clsx(
          'flex items-center gap-2 py-1.5 px-2 rounded-lg cursor-pointer group transition-colors',
          isSelected 
            ? 'bg-accent-primary/20 text-accent-secondary' 
            : 'hover:bg-bg-hover text-text-secondary hover:text-text-primary'
        )}
        style={{ paddingLeft: `${level * 16 + 8}px` }}
        onClick={() => {
          if (hasChildren) {
            setIsExpanded(!isExpanded)
          }
          onSelect?.(topic)
        }}
      >
        {/* Expand/collapse icon */}
        {hasChildren ? (
          <motion.span
            animate={{ rotate: isExpanded ? 90 : 0 }}
            transition={{ duration: 0.15 }}
            className="w-4 h-4 text-text-muted"
          >
            <ChevronRightIcon className="w-4 h-4" />
          </motion.span>
        ) : (
          <span className="w-4 h-4" />
        )}

        {/* Mastery indicator dot */}
        <span className={clsx(
          'w-2 h-2 rounded-full flex-shrink-0',
          masteryColor === 'emerald' && 'bg-emerald-500',
          masteryColor === 'indigo' && 'bg-indigo-500',
          masteryColor === 'amber' && 'bg-amber-500',
          masteryColor === 'red' && 'bg-red-500',
        )} />

        {/* Topic name */}
        <span className="flex-1 truncate text-sm font-medium">
          {topic.name}
        </span>

        {/* Count badge */}
        {topic.count !== undefined && (
          <span className="text-xs text-text-muted opacity-0 group-hover:opacity-100 transition-opacity">
            {topic.count}
          </span>
        )}

        {/* Mastery percentage */}
        <span className={clsx(
          'text-xs font-medium',
          masteryColor === 'emerald' && 'text-emerald-400',
          masteryColor === 'indigo' && 'text-indigo-400',
          masteryColor === 'amber' && 'text-amber-400',
          masteryColor === 'red' && 'text-red-400',
        )}>
          {masteryPercent}%
        </span>
      </motion.div>

      {/* Children */}
      <AnimatePresence initial={false}>
        {isExpanded && hasChildren && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            {topic.children.map((child) => (
              <TopicNode
                key={child.id}
                topic={child}
                level={level + 1}
                onSelect={onSelect}
                selectedId={selectedId}
              />
            ))}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

export function TopicTree({
  topics = [],
  selectedId,
  onSelect,
  isLoading = false,
  showHeader = true,
  className,
}) {
  if (isLoading) {
    return (
      <div className={clsx('space-y-2 p-2', className)}>
        {showHeader && <Skeleton className="h-5 w-24 mb-4" />}
        {[1, 2, 3, 4, 5].map((i) => (
          <div key={i} className="flex items-center gap-2 py-1.5 px-2">
            <Skeleton className="w-4 h-4 rounded" />
            <Skeleton className="w-2 h-2 rounded-full" />
            <Skeleton className="h-4 flex-1" />
            <Skeleton className="w-8 h-4" />
          </div>
        ))}
      </div>
    )
  }

  if (topics.length === 0) {
    return (
      <div className={clsx('p-4 text-center text-text-muted text-sm', className)}>
        No topics found. Add some content to build your knowledge tree.
      </div>
    )
  }

  return (
    <div className={className}>
      {showHeader && (
        <div className="flex items-center justify-between px-2 mb-2">
          <h3 className="text-sm font-semibold text-text-primary">Topics</h3>
          <span className="text-xs text-text-muted">{topics.length} topics</span>
        </div>
      )}
      
      <div className="space-y-0.5">
        {topics.map((topic) => (
          <TopicNode
            key={topic.id}
            topic={topic}
            onSelect={onSelect}
            selectedId={selectedId}
          />
        ))}
      </div>
    </div>
  )
}

// Compact variant for sidebars
export function TopicTreeCompact({ topics, onSelect, selectedId, className }) {
  return (
    <TopicTree
      topics={topics}
      onSelect={onSelect}
      selectedId={selectedId}
      showHeader={false}
      className={className}
    />
  )
}

// With practice buttons
export function TopicTreeWithActions({ topics, onPractice, onSelect, selectedId: _selectedId, className }) {
  return (
    <div className={className}>
      {topics.map((topic) => (
        <div 
          key={topic.id}
          className={clsx(
            'flex items-center gap-2 py-2 px-3 rounded-lg',
            'hover:bg-bg-hover transition-colors group'
          )}
        >
          {/* Mastery indicator */}
          <div className={clsx(
            'w-8 h-8 rounded-lg flex items-center justify-center text-xs font-medium',
            getMasteryColor(topic.mastery) === 'emerald' && 'bg-emerald-500/20 text-emerald-400',
            getMasteryColor(topic.mastery) === 'indigo' && 'bg-indigo-500/20 text-indigo-400',
            getMasteryColor(topic.mastery) === 'amber' && 'bg-amber-500/20 text-amber-400',
            getMasteryColor(topic.mastery) === 'red' && 'bg-red-500/20 text-red-400',
          )}>
            {Math.round((topic.mastery || 0) * 100)}%
          </div>

          {/* Topic info */}
          <div 
            className="flex-1 min-w-0 cursor-pointer"
            onClick={() => onSelect?.(topic)}
          >
            <p className="text-sm font-medium text-text-primary truncate">
              {topic.name}
            </p>
            {topic.count !== undefined && (
              <p className="text-xs text-text-muted">
                {topic.count} items
              </p>
            )}
          </div>

          {/* Practice button */}
          <button
            onClick={() => onPractice?.(topic)}
            className={clsx(
              'px-3 py-1.5 rounded-lg text-xs font-medium',
              'bg-slate-700 text-slate-300 hover:bg-slate-600 hover:text-white',
              'opacity-0 group-hover:opacity-100 transition-all'
            )}
          >
            Practice
          </button>
        </div>
      ))}
    </div>
  )
}

export default TopicTree
