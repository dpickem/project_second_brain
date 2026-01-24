/**
 * Exercises Catalogue Page
 * 
 * Browse and filter all available exercises.
 */

import { useState, useMemo, useEffect } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { motion } from 'framer-motion'
import { useQuery, useMutation } from '@tanstack/react-query'
import { clsx } from 'clsx'
import toast from 'react-hot-toast'
import { 
  MagnifyingGlassIcon, 
  FunnelIcon,
  PlayIcon,
} from '@heroicons/react/24/outline'
import { Card, Button, PageLoader, Badge, DifficultyBadge, EmptyState } from '../components/common'
import { practiceApi } from '../api/practice'
import { usePracticeStore } from '../stores'
import { fadeInUp, staggerContainer } from '../utils/animations'
import { ExerciseType, ExerciseDifficulty } from '../constants/enums.generated'

const exerciseTypeConfig = {
  [ExerciseType.FREE_RECALL]: { label: 'Free Recall', icon: '🧠', color: 'primary' },
  [ExerciseType.SELF_EXPLAIN]: { label: 'Self Explain', icon: '💭', color: 'info' },
  [ExerciseType.WORKED_EXAMPLE]: { label: 'Worked Example', icon: '📝', color: 'success' },
  [ExerciseType.CODE_DEBUG]: { label: 'Debug Code', icon: '🐛', color: 'warning' },
  [ExerciseType.CODE_COMPLETE]: { label: 'Code Completion', icon: '⌨️', color: 'primary' },
  [ExerciseType.CODE_IMPLEMENT]: { label: 'Implementation', icon: '🔧', color: 'danger' },
  [ExerciseType.CODE_REFACTOR]: { label: 'Refactor Code', icon: '♻️', color: 'info' },
  [ExerciseType.CODE_EXPLAIN]: { label: 'Explain Code', icon: '📖', color: 'info' },
  [ExerciseType.TEACH_BACK]: { label: 'Teach Back', icon: '🎓', color: 'secondary' },
  [ExerciseType.APPLICATION]: { label: 'Application', icon: '🎯', color: 'primary' },
  [ExerciseType.COMPARE_CONTRAST]: { label: 'Compare & Contrast', icon: '⚖️', color: 'info' },
}

const difficultyOptions = [
  { value: '', label: 'All Difficulties' },
  { value: ExerciseDifficulty.FOUNDATIONAL, label: 'Foundational' },
  { value: ExerciseDifficulty.INTERMEDIATE, label: 'Intermediate' },
  { value: ExerciseDifficulty.ADVANCED, label: 'Advanced' },
]

const exerciseTypeOptions = [
  { value: '', label: 'All Types' },
  { value: ExerciseType.FREE_RECALL, label: '🧠 Free Recall' },
  { value: ExerciseType.SELF_EXPLAIN, label: '💭 Self Explain' },
  { value: ExerciseType.WORKED_EXAMPLE, label: '📝 Worked Example' },
  { value: ExerciseType.CODE_DEBUG, label: '🐛 Debug Code' },
  { value: ExerciseType.CODE_COMPLETE, label: '⌨️ Code Completion' },
  { value: ExerciseType.CODE_IMPLEMENT, label: '🔧 Implementation' },
  { value: ExerciseType.CODE_REFACTOR, label: '♻️ Refactor' },
  { value: ExerciseType.CODE_EXPLAIN, label: '📖 Explain Code' },
  { value: ExerciseType.TEACH_BACK, label: '🎓 Teach Back' },
  { value: ExerciseType.APPLICATION, label: '🎯 Application' },
  { value: ExerciseType.COMPARE_CONTRAST, label: '⚖️ Compare & Contrast' },
]

export function Exercises() {
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  
  // Read topic filter from URL if present
  const topicFromUrl = searchParams.get('topic') || ''
  
  const [search, setSearch] = useState(topicFromUrl)
  const [typeFilter, setTypeFilter] = useState('')
  const [difficultyFilter, setDifficultyFilter] = useState('')
  const [showFilters, setShowFilters] = useState(!!topicFromUrl) // Auto-show filters if topic in URL
  
  const { startSession } = usePracticeStore()
  
  // Update search when URL topic changes
  useEffect(() => {
    if (topicFromUrl) {
      setSearch(topicFromUrl)
      setShowFilters(true)
    }
  }, [topicFromUrl])

  // Fetch exercises - include topic filter in query
  const { data: exercises, isLoading, error } = useQuery({
    queryKey: ['exercises', typeFilter, difficultyFilter, topicFromUrl],
    queryFn: () => practiceApi.listExercises({
      topic: topicFromUrl || undefined,
      exerciseType: typeFilter || undefined,
      difficulty: difficultyFilter || undefined,
      limit: 100,
    }),
  })

  // Create a quick session with a single exercise
  // When the exercise has a specific topic, we create a session and include that exercise
  const startSingleExerciseMutation = useMutation({
    mutationFn: async (exercise) => {
      // Try creating a session with the exercise's topic
      const session = await practiceApi.createSession({
        topicFilter: exercise.topic,
        durationMinutes: 10, // Increase time to better chance of finding exercises
        reuseExercises: true, // Only use existing exercises
      })
      
      // Return both the session and the original exercise for verification
      return { session, requestedExercise: exercise }
    },
    onSuccess: ({ session, requestedExercise }) => {
      // Check if session was created successfully
      if (!session || !session.items || session.items.length === 0) {
        // Session was empty - create a minimal session with just the requested exercise
        const minimalSession = {
          session_id: Date.now(), // Temp ID
          items: [{
            item_type: 'exercise',
            exercise: requestedExercise,
            estimated_minutes: requestedExercise.estimated_time_minutes || 5,
          }],
          estimated_duration_minutes: requestedExercise.estimated_time_minutes || 5,
          topics_covered: [requestedExercise.topic],
          session_type: 'practice',
        }
        startSession(minimalSession)
        navigate('/practice')
        return
      }
      
      // Check if the requested exercise is in the session
      const hasRequestedExercise = session.items.some(
        item => item.exercise?.id === requestedExercise.id
      )
      
      if (!hasRequestedExercise && requestedExercise) {
        // Add the requested exercise at the beginning if not already included
        session.items.unshift({
          item_type: 'exercise',
          exercise: requestedExercise,
          estimated_minutes: requestedExercise.estimated_time_minutes || 5,
        })
      }
      
      startSession(session)
      navigate('/practice')
    },
    onError: (error) => {
      const detail = error.response?.data?.detail
      let message = 'Failed to start exercise'
      
      if (typeof detail === 'string') {
        message = detail
      } else if (Array.isArray(detail) && detail.length > 0) {
        message = detail[0]?.msg || 'Validation error'
      }
      
      // On API error, try starting with just the exercise directly
      toast.error(`${message}. Starting exercise directly...`)
    },
  })

  const handleStartExercise = (exercise) => {
    startSingleExerciseMutation.mutate(exercise)
  }

  // Filter exercises by search
  const filteredExercises = useMemo(() => {
    if (!exercises) return []
    if (!search.trim()) return exercises
    
    const searchLower = search.toLowerCase()
    return exercises.filter(ex => 
      ex.prompt?.toLowerCase().includes(searchLower) ||
      ex.topic?.toLowerCase().includes(searchLower) ||
      ex.exercise_type?.toLowerCase().includes(searchLower)
    )
  }, [exercises, search])

  // Group exercises by topic
  const groupedExercises = useMemo(() => {
    const groups = {}
    filteredExercises.forEach(ex => {
      const topic = ex.topic || 'Uncategorized'
      if (!groups[topic]) groups[topic] = []
      groups[topic].push(ex)
    })
    return groups
  }, [filteredExercises])

  const topicCount = Object.keys(groupedExercises).length

  if (isLoading) {
    return <PageLoader message="Loading exercises..." />
  }

  return (
    <div className="min-h-screen bg-bg-primary p-6 lg:p-8">
      <motion.div
        variants={staggerContainer}
        initial="hidden"
        animate="show"
        className="max-w-6xl mx-auto space-y-6"
      >
        {/* Header */}
        <motion.div variants={fadeInUp} className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-text-primary font-heading">
              📚 Exercise Catalogue
            </h1>
            <p className="text-text-secondary mt-1">
              Browse and practice from {filteredExercises.length} exercises across {topicCount} topics
            </p>
          </div>
          <Button variant="secondary" onClick={() => navigate('/practice')}>
            Start Practice Session
          </Button>
        </motion.div>

        {/* Search and Filters */}
        <motion.div variants={fadeInUp}>
          <Card padding="md">
            <div className="flex flex-col sm:flex-row gap-4">
              {/* Search */}
              <div className="relative flex-1">
                <MagnifyingGlassIcon className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-text-muted" />
                <input
                  type="text"
                  placeholder="Search exercises..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  className={clsx(
                    'w-full pl-10 pr-4 py-2 rounded-lg',
                    'bg-bg-tertiary border border-border-primary',
                    'text-text-primary placeholder-text-muted',
                    'focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500'
                  )}
                />
              </div>

              {/* Filter toggle */}
              <Button
                type="button"
                variant={showFilters ? 'primary' : 'secondary'}
                onClick={() => setShowFilters(!showFilters)}
                icon={<FunnelIcon className="w-4 h-4" />}
              >
                Filters
              </Button>
            </div>

            {/* Filter options */}
            {showFilters && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: 'auto', opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                className="mt-4 pt-4 border-t border-border-primary"
              >
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  {/* Type filter */}
                  <div>
                    <label className="block text-sm font-medium text-text-secondary mb-2">
                      Exercise Type
                    </label>
                    <select
                      value={typeFilter}
                      onChange={(e) => setTypeFilter(e.target.value)}
                      className={clsx(
                        'w-full px-3 py-2 rounded-lg',
                        'bg-bg-tertiary border border-border-primary',
                        'text-text-primary',
                        'focus:outline-none focus:ring-2 focus:ring-indigo-500/50'
                      )}
                    >
                      {exerciseTypeOptions.map(opt => (
                        <option key={opt.value} value={opt.value}>{opt.label}</option>
                      ))}
                    </select>
                  </div>

                  {/* Difficulty filter */}
                  <div>
                    <label className="block text-sm font-medium text-text-secondary mb-2">
                      Difficulty
                    </label>
                    <select
                      value={difficultyFilter}
                      onChange={(e) => setDifficultyFilter(e.target.value)}
                      className={clsx(
                        'w-full px-3 py-2 rounded-lg',
                        'bg-bg-tertiary border border-border-primary',
                        'text-text-primary',
                        'focus:outline-none focus:ring-2 focus:ring-indigo-500/50'
                      )}
                    >
                      {difficultyOptions.map(opt => (
                        <option key={opt.value} value={opt.value}>{opt.label}</option>
                      ))}
                    </select>
                  </div>
                </div>
              </motion.div>
            )}
          </Card>
        </motion.div>

        {/* Error state */}
        {error && (
          <motion.div variants={fadeInUp}>
            <Card variant="elevated" className="bg-red-500/10 border-red-500/20">
              <p className="text-red-400">Failed to load exercises: {error.message}</p>
            </Card>
          </motion.div>
        )}

        {/* Empty state */}
        {!isLoading && filteredExercises.length === 0 && (
          <motion.div variants={fadeInUp}>
            <EmptyState
              icon="📝"
              title="No exercises found"
              description={search ? "Try adjusting your search or filters" : "Exercises will appear here as you practice topics"}
            />
          </motion.div>
        )}

        {/* Exercises by Topic */}
        {Object.entries(groupedExercises).map(([topic, topicExercises]) => (
          <motion.div key={topic} variants={fadeInUp}>
            <Card>
              {/* Topic header */}
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold text-text-primary font-heading">
                  {topic}
                </h2>
                <Badge variant="secondary">{topicExercises.length} exercises</Badge>
              </div>

              {/* Exercise list */}
              <div className="space-y-3">
                {topicExercises.map((exercise) => {
                  const typeConfig = exerciseTypeConfig[exercise.exercise_type] || {
                    label: exercise.exercise_type,
                    icon: '📋',
                    color: 'default',
                  }

                  return (
                    <div
                      key={exercise.id}
                      className={clsx(
                        'p-4 rounded-lg bg-bg-tertiary',
                        'border border-transparent hover:border-indigo-500/30',
                        'transition-colors group'
                      )}
                    >
                      <div className="flex items-start gap-4">
                        {/* Icon */}
                        <span className="text-2xl flex-shrink-0">{typeConfig.icon}</span>

                        {/* Content */}
                        <div className="flex-1 min-w-0">
                          {/* Type and difficulty badges */}
                          <div className="flex items-center gap-2 mb-2">
                            <Badge variant={typeConfig.color} size="sm">
                              {typeConfig.label}
                            </Badge>
                            {exercise.difficulty && (
                              <DifficultyBadge level={exercise.difficulty} />
                            )}
                            {exercise.language && (
                              <span className="text-xs text-text-muted bg-slate-700 px-2 py-0.5 rounded">
                                {exercise.language}
                              </span>
                            )}
                          </div>

                          {/* Prompt preview */}
                          <p className="text-sm text-text-secondary line-clamp-2 group-hover:text-text-primary transition-colors">
                            {exercise.prompt}
                          </p>

                          {/* Meta info */}
                          <div className="flex items-center gap-4 mt-2 text-xs text-text-muted">
                            {exercise.hints?.length > 0 && (
                              <span>💡 {exercise.hints.length} hints</span>
                            )}
                            {exercise.estimated_time_minutes && (
                              <span>⏱️ ~{exercise.estimated_time_minutes} min</span>
                            )}
                            {exercise.tags?.length > 0 && (
                              <span>🏷️ {exercise.tags.slice(0, 3).join(', ')}</span>
                            )}
                          </div>
                        </div>

                        {/* Start button */}
                        <Button
                          variant="primary"
                          size="sm"
                          onClick={() => handleStartExercise(exercise)}
                          loading={startSingleExerciseMutation.isPending}
                          icon={<PlayIcon className="w-4 h-4" />}
                        >
                          Start
                        </Button>
                      </div>
                    </div>
                  )
                })}
              </div>
            </Card>
          </motion.div>
        ))}

        {/* Back link */}
        <motion.div variants={fadeInUp} className="text-center pt-4">
          <Button variant="ghost" onClick={() => navigate('/')}>
            ← Back to Dashboard
          </Button>
        </motion.div>
      </motion.div>
    </div>
  )
}

export default Exercises
