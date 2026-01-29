/**
 * Follow-up Tasks Page
 * 
 * Browse, filter, and manage follow-up tasks generated during content processing.
 * Follow-up tasks are actionable items that help users engage more deeply with content.
 */

import { useState, useMemo } from 'react'
import { useSearchParams, Link } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { clsx } from 'clsx'
import { format, formatDistanceToNow } from 'date-fns'
import toast from 'react-hot-toast'
import { 
  MagnifyingGlassIcon, 
  FunnelIcon,
  CheckIcon,
  ArrowPathIcon,
  ClockIcon,
  FlagIcon,
  DocumentTextIcon,
  ChevronDownIcon,
} from '@heroicons/react/24/outline'
import { CheckCircleIcon } from '@heroicons/react/24/solid'
import { Card, Button, PageLoader, Badge, EmptyState, Input } from '../components/common'
import { followupsApi } from '../api/followups'
import { fadeInUp, staggerContainer } from '../utils/animations'

// Task type configuration
const taskTypeConfig = {
  research: { label: 'Research', icon: '🔍', color: 'bg-blue-500/20 text-blue-400 border-blue-500/30' },
  practice: { label: 'Practice', icon: '💪', color: 'bg-green-500/20 text-green-400 border-green-500/30' },
  connect: { label: 'Connect', icon: '🔗', color: 'bg-purple-500/20 text-purple-400 border-purple-500/30' },
  apply: { label: 'Apply', icon: '🎯', color: 'bg-orange-500/20 text-orange-400 border-orange-500/30' },
  review: { label: 'Review', icon: '📖', color: 'bg-cyan-500/20 text-cyan-400 border-cyan-500/30' },
}

// Priority configuration
const priorityConfig = {
  high: { label: 'High', color: 'text-red-400', bgColor: 'bg-red-500/20 border-red-500/30', icon: '🔴' },
  medium: { label: 'Medium', color: 'text-yellow-400', bgColor: 'bg-yellow-500/20 border-yellow-500/30', icon: '🟡' },
  low: { label: 'Low', color: 'text-green-400', bgColor: 'bg-green-500/20 border-green-500/30', icon: '🟢' },
}

// Time estimate display
const timeEstimateDisplay = {
  '15min': '15 min',
  '30min': '30 min',
  '1hr': '1 hour',
  '2hr+': '2+ hours',
  '15MIN': '15 min',
  '30MIN': '30 min',
  '1HR': '1 hour',
  '2HR_PLUS': '2+ hours',
}

// Filter options
const statusOptions = [
  { value: '', label: 'All Tasks' },
  { value: 'pending', label: 'Pending' },
  { value: 'completed', label: 'Completed' },
]

const priorityOptions = [
  { value: '', label: 'All Priorities' },
  { value: 'high', label: '🔴 High' },
  { value: 'medium', label: '🟡 Medium' },
  { value: 'low', label: '🟢 Low' },
]

const typeOptions = [
  { value: '', label: 'All Types' },
  { value: 'research', label: '🔍 Research' },
  { value: 'practice', label: '💪 Practice' },
  { value: 'connect', label: '🔗 Connect' },
  { value: 'apply', label: '🎯 Apply' },
  { value: 'review', label: '📖 Review' },
]

// Task card component
function TaskCard({ task, onToggleComplete }) {
  const typeConf = taskTypeConfig[task.task_type?.toLowerCase()] || taskTypeConfig.research
  const priorityConf = priorityConfig[task.priority?.toLowerCase()] || priorityConfig.medium
  const timeDisplay = timeEstimateDisplay[task.estimated_time] || task.estimated_time

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, scale: 0.95 }}
      className={clsx(
        'group relative p-4 rounded-xl border transition-all duration-200',
        task.completed 
          ? 'bg-bg-secondary/50 border-border-primary opacity-70' 
          : 'bg-bg-secondary border-border-primary hover:border-indigo-500/50 hover:shadow-lg hover:shadow-indigo-500/10'
      )}
    >
      {/* Checkbox and content */}
      <div className="flex gap-4">
        {/* Checkbox */}
        <button
          onClick={() => onToggleComplete(task)}
          className={clsx(
            'flex-shrink-0 w-6 h-6 rounded-full border-2 flex items-center justify-center transition-all duration-200',
            task.completed
              ? 'bg-emerald-500 border-emerald-500 text-white'
              : 'border-slate-500 hover:border-indigo-500 hover:bg-indigo-500/10'
          )}
          aria-label={task.completed ? 'Mark as incomplete' : 'Mark as complete'}
        >
          {task.completed && <CheckIcon className="w-4 h-4" />}
        </button>

        {/* Content */}
        <div className="flex-1 min-w-0">
          {/* Task text */}
          <p className={clsx(
            'text-sm leading-relaxed',
            task.completed ? 'text-text-muted line-through' : 'text-text-primary'
          )}>
            {task.task}
          </p>

          {/* Metadata row */}
          <div className="flex flex-wrap items-center gap-2 mt-3">
            {/* Type badge */}
            <span className={clsx(
              'inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium border',
              typeConf.color
            )}>
              <span>{typeConf.icon}</span>
              {typeConf.label}
            </span>

            {/* Priority badge */}
            <span className={clsx(
              'inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium border',
              priorityConf.bgColor, priorityConf.color
            )}>
              <FlagIcon className="w-3 h-3" />
              {priorityConf.label}
            </span>

            {/* Time estimate */}
            <span className="inline-flex items-center gap-1 text-xs text-text-muted">
              <ClockIcon className="w-3.5 h-3.5" />
              {timeDisplay}
            </span>

            {/* Source content link */}
            {task.content_title && (
              <Link
                to={`/knowledge?search=${encodeURIComponent(task.content_title)}`}
                className="inline-flex items-center gap-1 text-xs text-indigo-400 hover:text-indigo-300 transition-colors"
              >
                <DocumentTextIcon className="w-3.5 h-3.5" />
                <span className="max-w-[200px] truncate">{task.content_title}</span>
              </Link>
            )}
          </div>

          {/* Completion info */}
          {task.completed && task.completed_at && (
            <p className="mt-2 text-xs text-text-muted">
              Completed {formatDistanceToNow(new Date(task.completed_at), { addSuffix: true })}
            </p>
          )}
        </div>
      </div>
    </motion.div>
  )
}

// Stats summary component
function TaskStats({ tasks }) {
  const stats = useMemo(() => {
    const total = tasks.length
    const completed = tasks.filter(t => t.completed).length
    const pending = total - completed
    const highPriority = tasks.filter(t => !t.completed && t.priority?.toLowerCase() === 'high').length
    
    return { total, completed, pending, highPriority }
  }, [tasks])

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
      <Card className="p-4 bg-bg-secondary">
        <p className="text-2xl font-bold text-text-primary">{stats.total}</p>
        <p className="text-sm text-text-muted">Total Tasks</p>
      </Card>
      <Card className="p-4 bg-bg-secondary">
        <p className="text-2xl font-bold text-yellow-400">{stats.pending}</p>
        <p className="text-sm text-text-muted">Pending</p>
      </Card>
      <Card className="p-4 bg-bg-secondary">
        <p className="text-2xl font-bold text-emerald-400">{stats.completed}</p>
        <p className="text-sm text-text-muted">Completed</p>
      </Card>
      <Card className="p-4 bg-bg-secondary">
        <p className="text-2xl font-bold text-red-400">{stats.highPriority}</p>
        <p className="text-sm text-text-muted">High Priority</p>
      </Card>
    </div>
  )
}

export function Tasks() {
  const queryClient = useQueryClient()
  const [searchParams, setSearchParams] = useSearchParams()
  
  // Filter state
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState(searchParams.get('status') || '')
  const [priorityFilter, setPriorityFilter] = useState(searchParams.get('priority') || '')
  const [typeFilter, setTypeFilter] = useState(searchParams.get('type') || '')
  const [showFilters, setShowFilters] = useState(false)

  // Fetch tasks
  const { data, isLoading, error } = useQuery({
    queryKey: ['followup-tasks', statusFilter, priorityFilter, typeFilter],
    queryFn: () => followupsApi.list({
      completed: statusFilter === 'completed' ? true : statusFilter === 'pending' ? false : undefined,
      priority: priorityFilter || undefined,
      taskType: typeFilter || undefined,
      limit: 500,
    }),
  })

  // Toggle completion mutation
  const toggleCompleteMutation = useMutation({
    mutationFn: (task) => followupsApi.setCompleted(task.id, !task.completed),
    onMutate: async (task) => {
      // Cancel outgoing refetches
      await queryClient.cancelQueries({ queryKey: ['followup-tasks'] })
      
      // Snapshot previous value
      const previousData = queryClient.getQueryData(['followup-tasks', statusFilter, priorityFilter, typeFilter])
      
      // Optimistically update
      queryClient.setQueryData(['followup-tasks', statusFilter, priorityFilter, typeFilter], (old) => {
        if (!old) return old
        return {
          ...old,
          tasks: old.tasks.map(t => 
            t.id === task.id 
              ? { ...t, completed: !t.completed, completed_at: !t.completed ? new Date().toISOString() : null }
              : t
          ),
        }
      })
      
      return { previousData }
    },
    onError: (err, task, context) => {
      // Rollback on error
      queryClient.setQueryData(
        ['followup-tasks', statusFilter, priorityFilter, typeFilter], 
        context.previousData
      )
      toast.error('Failed to update task')
    },
    onSuccess: (data, task) => {
      toast.success(task.completed ? 'Task reopened' : 'Task completed!')
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ['followup-tasks'] })
    },
  })

  // Filter tasks by search term
  const filteredTasks = useMemo(() => {
    if (!data?.tasks) return []
    if (!search) return data.tasks
    
    const searchLower = search.toLowerCase()
    return data.tasks.filter(task => 
      task.task?.toLowerCase().includes(searchLower) ||
      task.content_title?.toLowerCase().includes(searchLower)
    )
  }, [data?.tasks, search])

  // Group tasks by status for better organization
  const { pendingTasks, completedTasks } = useMemo(() => {
    const pending = filteredTasks.filter(t => !t.completed)
    const completed = filteredTasks.filter(t => t.completed)
    
    // Sort pending by priority (high first)
    const priorityOrder = { high: 0, medium: 1, low: 2 }
    pending.sort((a, b) => {
      const aPriority = priorityOrder[a.priority?.toLowerCase()] ?? 1
      const bPriority = priorityOrder[b.priority?.toLowerCase()] ?? 1
      return aPriority - bPriority
    })
    
    // Sort completed by completion date (most recent first)
    completed.sort((a, b) => {
      const aDate = a.completed_at ? new Date(a.completed_at) : new Date(0)
      const bDate = b.completed_at ? new Date(b.completed_at) : new Date(0)
      return bDate - aDate
    })
    
    return { pendingTasks: pending, completedTasks: completed }
  }, [filteredTasks])

  const handleToggleComplete = (task) => {
    toggleCompleteMutation.mutate(task)
  }

  if (isLoading) {
    return <PageLoader message="Loading tasks..." />
  }

  if (error) {
    return (
      <div className="min-h-screen bg-bg-primary p-8">
        <div className="max-w-4xl mx-auto">
          <EmptyState
            icon="⚠️"
            title="Failed to load tasks"
            description={error.message || "Something went wrong. Please try again."}
          />
        </div>
      </div>
    )
  }

  return (
    <motion.div
      variants={staggerContainer}
      initial="hidden"
      animate="show"
      className="min-h-screen bg-bg-primary p-8"
    >
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <motion.div variants={fadeInUp} className="mb-8">
          <h1 className="text-3xl font-bold text-text-primary font-heading mb-2">
            📋 Follow-up Tasks
          </h1>
          <p className="text-text-secondary">
            Actionable tasks generated from your knowledge base to deepen your understanding
          </p>
        </motion.div>

        {/* Stats */}
        {data?.tasks && data.tasks.length > 0 && (
          <motion.div variants={fadeInUp}>
            <TaskStats tasks={data.tasks} />
          </motion.div>
        )}

        {/* Search and filters */}
        <motion.div variants={fadeInUp} className="mb-6 space-y-4">
          <div className="flex gap-4">
            {/* Search */}
            <div className="relative flex-1">
              <MagnifyingGlassIcon className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-text-muted" />
              <Input
                type="text"
                placeholder="Search tasks..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="pl-10"
              />
            </div>
            
            {/* Filter toggle */}
            <Button
              variant="secondary"
              onClick={() => setShowFilters(!showFilters)}
              icon={<FunnelIcon className="w-4 h-4" />}
              className={clsx(showFilters && 'bg-indigo-500/20 border-indigo-500/50')}
            >
              Filters
              {(statusFilter || priorityFilter || typeFilter) && (
                <span className="ml-1.5 px-1.5 py-0.5 text-xs bg-indigo-500 rounded-full">
                  {[statusFilter, priorityFilter, typeFilter].filter(Boolean).length}
                </span>
              )}
            </Button>
          </div>

          {/* Filter dropdowns */}
          <AnimatePresence>
            {showFilters && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
                className="flex flex-wrap gap-4 overflow-hidden"
              >
                {/* Status filter */}
                <select
                  value={statusFilter}
                  onChange={(e) => setStatusFilter(e.target.value)}
                  className="px-3 py-2 bg-bg-tertiary border border-border-primary rounded-lg text-text-primary text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                >
                  {statusOptions.map(opt => (
                    <option key={opt.value} value={opt.value}>{opt.label}</option>
                  ))}
                </select>

                {/* Priority filter */}
                <select
                  value={priorityFilter}
                  onChange={(e) => setPriorityFilter(e.target.value)}
                  className="px-3 py-2 bg-bg-tertiary border border-border-primary rounded-lg text-text-primary text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                >
                  {priorityOptions.map(opt => (
                    <option key={opt.value} value={opt.value}>{opt.label}</option>
                  ))}
                </select>

                {/* Type filter */}
                <select
                  value={typeFilter}
                  onChange={(e) => setTypeFilter(e.target.value)}
                  className="px-3 py-2 bg-bg-tertiary border border-border-primary rounded-lg text-text-primary text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                >
                  {typeOptions.map(opt => (
                    <option key={opt.value} value={opt.value}>{opt.label}</option>
                  ))}
                </select>

                {/* Clear filters */}
                {(statusFilter || priorityFilter || typeFilter) && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => {
                      setStatusFilter('')
                      setPriorityFilter('')
                      setTypeFilter('')
                    }}
                  >
                    Clear filters
                  </Button>
                )}
              </motion.div>
            )}
          </AnimatePresence>
        </motion.div>

        {/* Task list */}
        {filteredTasks.length === 0 ? (
          <motion.div variants={fadeInUp}>
            <EmptyState
              icon="📋"
              title={search ? "No matching tasks" : "No tasks yet"}
              description={
                search 
                  ? "Try adjusting your search or filters" 
                  : "Follow-up tasks will appear here after processing content. Try ingesting some articles, papers, or books!"
              }
            />
          </motion.div>
        ) : (
          <motion.div variants={fadeInUp} className="space-y-8">
            {/* Pending tasks */}
            {pendingTasks.length > 0 && (
              <section>
                <h2 className="text-lg font-semibold text-text-primary mb-4 flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-yellow-400"></span>
                  Pending ({pendingTasks.length})
                </h2>
                <div className="space-y-3">
                  <AnimatePresence mode="popLayout">
                    {pendingTasks.map(task => (
                      <TaskCard
                        key={task.id}
                        task={task}
                        onToggleComplete={handleToggleComplete}
                      />
                    ))}
                  </AnimatePresence>
                </div>
              </section>
            )}

            {/* Completed tasks */}
            {completedTasks.length > 0 && (
              <section>
                <h2 className="text-lg font-semibold text-text-primary mb-4 flex items-center gap-2">
                  <CheckCircleIcon className="w-5 h-5 text-emerald-400" />
                  Completed ({completedTasks.length})
                </h2>
                <div className="space-y-3">
                  <AnimatePresence mode="popLayout">
                    {completedTasks.map(task => (
                      <TaskCard
                        key={task.id}
                        task={task}
                        onToggleComplete={handleToggleComplete}
                      />
                    ))}
                  </AnimatePresence>
                </div>
              </section>
            )}
          </motion.div>
        )}
      </div>
    </motion.div>
  )
}

export default Tasks
