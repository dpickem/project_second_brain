/**
 * PracticeSession Page
 * 
 * Main practice session interface with exercises and feedback.
 * Requires topic selection to generate targeted exercises.
 * 
 * EXERCISES vs SPACED REPETITION CARDS:
 * 
 * This page handles Exercises, which are different from Flashcards:
 * 
 * EXERCISES (this page - /practice):
 * - Rich, structured problems with detailed prompts
 * - Includes worked examples, code challenges, explain-why questions
 * - LLM-evaluated with personalized feedback on what you got right/wrong
 * - Exercise TYPE adapts to your mastery level (novice → advanced)
 * - Best for: Deep understanding and skill application
 * 
 * SPACED REP CARDS (Review page - /review):
 * - Simple front/back flashcards
 * - Self-rated (Again/Hard/Good/Easy)
 * - FSRS algorithm optimizes review timing
 * - Best for: Long-term memory retention of facts
 */

import { useState, useMemo, useEffect, useRef } from 'react'
import { useParams, useNavigate, useSearchParams } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { useMutation, useQuery } from '@tanstack/react-query'
import { clsx } from 'clsx'
import toast from 'react-hot-toast'
import { MagnifyingGlassIcon, ChevronRightIcon, ArrowsUpDownIcon } from '@heroicons/react/24/outline'
import { 
  ExerciseCard, 
  ResponseInput, 
  FeedbackDisplay, 
  SessionProgress,
  SessionComplete,
} from '../components/practice'
import { Card, Button, PageLoader, EmptyState, Skeleton } from '../components/common'
import { practiceApi } from '../api/practice'
import { knowledgeApi } from '../api/knowledge'
import { usePracticeStore, useSettingsStore } from '../stores'
import { fadeInUp, staggerContainer } from '../utils/animations'
import { isCodeExercise } from '../constants/enums.generated'

export function PracticeSession() {
  const { topicId } = useParams()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  
  // Get topic from URL query param (e.g., /practice?topic=ml/agents) or path param
  const topicFromUrl = searchParams.get('topic') || topicId || ''
  
  const preferredSessionLength = useSettingsStore((s) => s.preferredSessionLength)
  
  const {
    session,
    showFeedback,
    lastEvaluation,
    startSession,
    submitResponse,
    setConfidence,
    nextItem,
    getProgress,
    getCurrentItem,
    isSessionComplete,
    getSessionSummary,
    reset,
  } = usePracticeStore()

  // Session configuration state
  const [isConfiguring, setIsConfiguring] = useState(!session)
  const [sessionConfig, setSessionConfig] = useState({
    duration: preferredSessionLength,
    topic: topicFromUrl,
    topicName: '',
    reuseExercises: true, // Default to reusing existing exercises (faster, no API cost)
  })
  const [topicSearch, setTopicSearch] = useState('')
  const [topicSort, setTopicSort] = useState('alphabetical') // 'alphabetical' | 'mastery-asc' | 'mastery-desc'

  // Fetch available topics for selection
  const { data: topicsData, isLoading: topicsLoading } = useQuery({
    queryKey: ['topics-hierarchy'],
    queryFn: knowledgeApi.getTopics,
    staleTime: 5 * 60 * 1000, // 5 minutes
  })

  // Flatten topic hierarchy for easier searching/selection
  const flattenedTopics = useMemo(() => {
    const flatten = (nodes) => {
      if (!nodes) return []
      return nodes.flatMap(node => {
        const current = {
          id: node.path, // Use path as the unique ID (e.g., "ml/deep-learning")
          name: node.name,
          path: node.path,
          mastery: node.mastery_score || 0,
          count: node.content_count || 0,
          depth: node.depth || 0,
        }
        const children = flatten(node.children || [])
        return [current, ...children]
      })
    }
    return flatten(topicsData?.roots || [])
  }, [topicsData])
  
  // Update topic when URL changes (after flattenedTopics is defined)
  useEffect(() => {
    if (topicFromUrl && flattenedTopics.length > 0) {
      // Find the topic name from the topics list
      const topic = flattenedTopics.find(t => t.path === topicFromUrl || t.id === topicFromUrl)
      if (topic || topicFromUrl) {
        setSessionConfig(prev => ({
          ...prev,
          topic: topicFromUrl,
          topicName: topic?.name || topicFromUrl,
        }))
      }
    }
  }, [topicFromUrl, flattenedTopics])

  // Filter and sort topics
  const filteredTopics = useMemo(() => {
    let result = flattenedTopics
    
    // Apply search filter
    if (topicSearch.trim()) {
      const search = topicSearch.toLowerCase()
      result = result.filter(t => 
        t.name.toLowerCase().includes(search) || 
        t.path.toLowerCase().includes(search)
      )
    }
    
    // Apply sorting
    result = [...result].sort((a, b) => {
      switch (topicSort) {
        case 'mastery-asc':
          return a.mastery - b.mastery // Lowest mastery first (needs practice)
        case 'mastery-desc':
          return b.mastery - a.mastery // Highest mastery first
        case 'alphabetical':
        default:
          return a.name.localeCompare(b.name)
      }
    })
    
    return result
  }, [flattenedTopics, topicSearch, topicSort])

  // Create session mutation
  const [sessionError, setSessionError] = useState(null)
  
  const createSessionMutation = useMutation({
    mutationFn: practiceApi.createSession,
    onSuccess: (data) => {
      setSessionError(null)
      startSession(data)
      setIsConfiguring(false)
    },
    onError: (error) => {
      // Handle Pydantic validation errors (array of {type, loc, msg, input})
      const detail = error.response?.data?.detail
      let errorMessage = 'Failed to create session'
      
      if (typeof detail === 'string') {
        errorMessage = detail
      } else if (Array.isArray(detail) && detail.length > 0) {
        // Extract message from first validation error
        errorMessage = detail[0]?.msg || detail[0]?.message || JSON.stringify(detail[0])
      } else if (detail && typeof detail === 'object') {
        errorMessage = detail.msg || detail.message || JSON.stringify(detail)
      }
      
      setSessionError(errorMessage)
      toast.error(errorMessage)
    },
  })

  // Submit attempt mutation
  const submitMutation = useMutation({
    mutationFn: practiceApi.submitAttempt,
    onSuccess: (evaluation, { exerciseId }) => {
      submitResponse(exerciseId, null, evaluation)
    },
    onError: (error) => {
      // Handle Pydantic validation errors (array of {type, loc, msg, input})
      const detail = error.response?.data?.detail
      let errorMessage = 'Failed to submit response'
      
      if (typeof detail === 'string') {
        errorMessage = detail
      } else if (Array.isArray(detail) && detail.length > 0) {
        errorMessage = detail[0]?.msg || detail[0]?.message || 'Validation error'
      } else if (detail && typeof detail === 'object') {
        errorMessage = detail.msg || detail.message || 'Validation error'
      }
      
      toast.error(errorMessage)
    },
  })

  // Update confidence mutation
  const confidenceMutation = useMutation({
    mutationFn: ({ attemptId, confidence }) => 
      practiceApi.updateConfidence(attemptId, confidence),
  })

  // End session mutation
  const endSessionMutation = useMutation({
    mutationFn: (sessionId) => practiceApi.endSession(sessionId),
    // Session end is best-effort - no user feedback needed
  })

  // Track if we've already ended the session to prevent duplicate calls
  const sessionEndedRef = useRef(false)

  const currentItem = getCurrentItem()
  // Extract exercise from session item - items have { item_type, exercise, card } structure
  const currentExercise = currentItem?.exercise || currentItem?.card || currentItem
  const progress = getProgress()
  const isComplete = isSessionComplete()

  // End session in backend when session completes
  useEffect(() => {
    const sessionId = session?.session_id
    if (isComplete && sessionId && !sessionEndedRef.current) {
      sessionEndedRef.current = true
      endSessionMutation.mutate(sessionId)
    }
  }, [isComplete, session?.session_id, endSessionMutation])

  // Reset the ref when starting a new session
  useEffect(() => {
    if (!session) {
      sessionEndedRef.current = false
    }
  }, [session])

  // Select a topic
  const handleTopicSelect = (topic) => {
    setSessionConfig({ 
      ...sessionConfig, 
      topic: topic.id,
      topicName: topic.name,
    })
    setTopicSearch('')
  }

  // Start new session (requires topic selection)
  const handleStartSession = () => {
    if (!sessionConfig.topic) {
      toast.error('Please select a topic to practice')
      return
    }
    createSessionMutation.mutate({
      topicFilter: sessionConfig.topic,
      durationMinutes: sessionConfig.duration,
      reuseExercises: sessionConfig.reuseExercises,
    })
  }

  // Submit response
  const handleSubmit = (response) => {
    if (!currentExercise) return
    
    // Determine if this is a code exercise using generated enum constants
    const isCode = isCodeExercise(currentExercise.exercise_type)
    
    submitMutation.mutate({
      exerciseId: currentExercise.id,
      // Send as response_code for code exercises, response for others
      response: isCode ? null : response,
      responseCode: isCode ? response : null,
      timeSpentSeconds: Math.round((Date.now() - (usePracticeStore.getState().itemStartTime || Date.now())) / 1000),
    })
  }

  // Handle confidence rating
  const handleConfidenceSelect = (confidence) => {
    if (lastEvaluation?.attempt_id) {
      confidenceMutation.mutate({
        attemptId: lastEvaluation.attempt_id,
        confidence,
      })
    }
    setConfidence(currentExercise?.id, confidence)
  }

  // Continue to next exercise
  const handleContinue = () => {
    nextItem()
  }

  // Start new session after completion
  const handleStartNew = () => {
    // Session should already be ended via useEffect, but ensure it's done
    if (session?.session_id && !sessionEndedRef.current) {
      sessionEndedRef.current = true
      endSessionMutation.mutate(session.session_id)
    }
    reset()
    setIsConfiguring(true)
  }

  // Helper to get mastery color
  const getMasteryColor = (mastery) => {
    if (mastery >= 0.8) return 'emerald'
    if (mastery >= 0.6) return 'indigo'
    if (mastery >= 0.4) return 'amber'
    return 'red'
  }

  // Info component explaining exercises vs cards
  const PracticeModeInfo = () => {
    const [isExpanded, setIsExpanded] = useState(false)
    
    return (
      <div className="p-4 bg-amber-500/10 border border-amber-500/20 rounded-lg">
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="w-full flex items-center justify-between text-left"
        >
          <div className="flex items-center gap-2">
            <span className="text-amber-400">💡</span>
            <span className="text-sm font-medium text-amber-300">
              What happens in a Practice Session?
            </span>
          </div>
          <span className="text-amber-400 text-xs">
            {isExpanded ? '▲ Hide' : '▼ Show'}
          </span>
        </button>
        
        {isExpanded && (
          <div className="mt-4 text-sm text-text-secondary space-y-4">
            <div className="p-3 bg-bg-secondary rounded-lg">
              <div className="flex items-center gap-2 mb-2">
                <span>🎯</span>
                <span className="font-medium text-amber-400">Exercises (This Page)</span>
              </div>
              <ul className="list-disc list-inside space-y-1 text-xs">
                <li>Detailed prompts that test understanding</li>
                <li>AI evaluates your response with feedback</li>
                <li>Exercise type adapts to your skill level</li>
                <li>Novices: worked examples, code completion</li>
                <li>Experts: teach-back, refactoring challenges</li>
              </ul>
            </div>
            
            <div className="p-3 bg-bg-secondary rounded-lg">
              <div className="flex items-center gap-2 mb-2">
                <span>📚</span>
                <span className="font-medium text-emerald-400">Flashcards (Review Page)</span>
              </div>
              <ul className="list-disc list-inside space-y-1 text-xs">
                <li>Simple question → answer cards</li>
                <li>Self-rate your recall (Again/Good/Easy)</li>
                <li>Spaced repetition for memory retention</li>
                <li>Best for definitions and terminology</li>
              </ul>
            </div>
            
            <p className="text-xs text-text-muted italic">
              💡 Use exercises to <span className="text-amber-300">practice deeply</span>, 
              then flashcards to <span className="text-emerald-300">remember long-term</span>.
            </p>
          </div>
        )}
      </div>
    )
  }

  // Session configuration screen
  if (isConfiguring) {
    const canStart = !!sessionConfig.topic
    const hasNoTopics = !topicsLoading && flattenedTopics.length === 0

    return (
      <div className="min-h-screen bg-bg-primary p-6 lg:p-8">
        <div className="max-w-2xl mx-auto">
          <motion.div
            variants={staggerContainer}
            initial="hidden"
            animate="show"
            className="space-y-8"
          >
            {/* Header */}
            <motion.div variants={fadeInUp} className="text-center">
              <span className="text-6xl mb-4 block">🎯</span>
              <h1 className="text-3xl font-bold text-text-primary font-heading mb-2">
                Start Practice Session
              </h1>
              <p className="text-text-secondary">
                Select a topic and duration to begin practicing
              </p>
            </motion.div>

            {/* Info about exercises vs flashcards */}
            <motion.div variants={fadeInUp}>
              <PracticeModeInfo />
            </motion.div>

            {/* Configuration */}
            <motion.div variants={fadeInUp}>
              <Card>
                <div className="space-y-6">
                  {/* Topic Selection - Required */}
                  <div>
                    <label className="block text-sm font-medium text-text-primary mb-2">
                      Topic to Practice <span className="text-red-400">*</span>
                    </label>
                    
                    {/* Selected topic display */}
                    {sessionConfig.topic && (
                      <div className="mb-3 p-3 bg-indigo-500/10 border border-indigo-500/20 rounded-lg flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <span className="text-indigo-400">✓</span>
                          <span className="text-sm font-medium text-indigo-300">
                            {sessionConfig.topicName || sessionConfig.topic}
                          </span>
                        </div>
                        <button
                          onClick={() => setSessionConfig({ ...sessionConfig, topic: '', topicName: '' })}
                          className="text-xs text-text-muted hover:text-text-secondary"
                        >
                          Change
                        </button>
                      </div>
                    )}

                    {/* Topic search and list */}
                    {!sessionConfig.topic && (
                      <>
                        {/* Search and sort controls */}
                        <div className="flex gap-2 mb-3">
                          {/* Search input */}
                          <div className="relative flex-1">
                            <MagnifyingGlassIcon className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-muted" />
                            <input
                              type="text"
                              placeholder="Search topics..."
                              value={topicSearch}
                              onChange={(e) => setTopicSearch(e.target.value)}
                              className={clsx(
                                'w-full pl-9 pr-4 py-2.5 rounded-lg text-sm',
                                'bg-bg-tertiary border border-border-primary',
                                'text-text-primary placeholder-text-muted',
                                'focus:outline-none focus:border-accent-primary focus:ring-1 focus:ring-accent-primary'
                              )}
                            />
                          </div>
                          
                          {/* Sort dropdown */}
                          <div className="relative">
                            <select
                              value={topicSort}
                              onChange={(e) => setTopicSort(e.target.value)}
                              className={clsx(
                                'appearance-none pl-9 pr-8 py-2.5 rounded-lg text-sm cursor-pointer',
                                'bg-bg-tertiary border border-border-primary',
                                'text-text-primary',
                                'focus:outline-none focus:border-accent-primary focus:ring-1 focus:ring-accent-primary'
                              )}
                            >
                              <option value="alphabetical">A-Z</option>
                              <option value="mastery-asc">Mastery ↑</option>
                              <option value="mastery-desc">Mastery ↓</option>
                            </select>
                            <ArrowsUpDownIcon className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-muted pointer-events-none" />
                            <ChevronRightIcon className="absolute right-2 top-1/2 -translate-y-1/2 w-4 h-4 text-text-muted pointer-events-none rotate-90" />
                          </div>
                        </div>

                        {/* Topics list */}
                        <div className="max-h-64 overflow-y-auto rounded-lg border border-border-primary bg-bg-secondary">
                          {topicsLoading ? (
                            <div className="p-4 space-y-2">
                              {[1, 2, 3, 4, 5].map((i) => (
                                <div key={i} className="flex items-center gap-3 py-2">
                                  <Skeleton className="w-2 h-2 rounded-full" />
                                  <Skeleton className="h-4 flex-1" />
                                  <Skeleton className="w-8 h-4" />
                                </div>
                              ))}
                            </div>
                          ) : hasNoTopics ? (
                            <div className="p-6 text-center">
                              <span className="text-4xl mb-3 block">📚</span>
                              <p className="text-sm text-text-secondary mb-2">
                                No topics available yet
                              </p>
                              <p className="text-xs text-text-muted">
                                Add some content to your knowledge base first, then come back to practice!
                              </p>
                            </div>
                          ) : filteredTopics.length === 0 ? (
                            <div className="p-4 text-center text-sm text-text-muted">
                              No topics match &ldquo;{topicSearch}&rdquo;
                            </div>
                          ) : (
                            <div className="divide-y divide-border-primary">
                              {filteredTopics.map((topic) => {
                                const masteryColor = getMasteryColor(topic.mastery)
                                const masteryPercent = Math.round(topic.mastery * 100)
                                
                                return (
                                  <button
                                    key={topic.id}
                                    onClick={() => handleTopicSelect(topic)}
                                    className={clsx(
                                      'w-full flex items-center gap-3 px-4 py-3 text-left',
                                      'hover:bg-bg-hover transition-colors group'
                                    )}
                                    style={{ paddingLeft: `${topic.depth * 12 + 16}px` }}
                                  >
                                    {/* Mastery indicator */}
                                    <span className={clsx(
                                      'w-2 h-2 rounded-full flex-shrink-0',
                                      masteryColor === 'emerald' && 'bg-emerald-500',
                                      masteryColor === 'indigo' && 'bg-indigo-500',
                                      masteryColor === 'amber' && 'bg-amber-500',
                                      masteryColor === 'red' && 'bg-red-500',
                                    )} />
                                    
                                    {/* Topic name */}
                                    <span className="flex-1 text-sm text-text-secondary group-hover:text-text-primary truncate">
                                      {topic.name}
                                    </span>
                                    
                                    {/* Item count */}
                                    {topic.count > 0 && (
                                      <span className="text-xs text-text-muted">
                                        {topic.count} items
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
                                    
                                    {/* Arrow */}
                                    <ChevronRightIcon className="w-4 h-4 text-text-muted opacity-0 group-hover:opacity-100 transition-opacity" />
                                  </button>
                                )
                              })}
                            </div>
                          )}
                        </div>
                      </>
                    )}
                  </div>

                  {/* Duration Selection */}
                  <div>
                    <label className="block text-sm font-medium text-text-primary mb-2">
                      Session Duration
                    </label>
                    <div className="grid grid-cols-4 gap-2">
                      {[5, 10, 15, 30].map((duration) => (
                        <button
                          key={duration}
                          onClick={() => setSessionConfig({ ...sessionConfig, duration })}
                          className={clsx(
                            'py-3 rounded-lg text-sm font-medium transition-all',
                            sessionConfig.duration === duration
                              ? 'bg-indigo-600 text-white'
                              : 'bg-bg-tertiary text-text-secondary hover:bg-bg-hover'
                          )}
                        >
                          {duration} min
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* Exercise Source Toggle */}
                  <div>
                    <label className="block text-sm font-medium text-text-primary mb-2">
                      Exercise Source
                    </label>
                    <div className="grid grid-cols-2 gap-2">
                      <button
                        onClick={() => setSessionConfig({ ...sessionConfig, reuseExercises: true })}
                        className={clsx(
                          'py-3 px-4 rounded-lg text-sm font-medium transition-all text-left',
                          sessionConfig.reuseExercises
                            ? 'bg-indigo-600 text-white'
                            : 'bg-bg-tertiary text-text-secondary hover:bg-bg-hover'
                        )}
                      >
                        <div className="flex items-center gap-2">
                          <span>♻️</span>
                          <div>
                            <div className="font-medium">Reuse Existing</div>
                            <div className={clsx(
                              'text-xs mt-0.5',
                              sessionConfig.reuseExercises ? 'text-indigo-200' : 'text-text-muted'
                            )}>
                              Fast, uses saved exercises
                            </div>
                          </div>
                        </div>
                      </button>
                      <button
                        onClick={() => setSessionConfig({ ...sessionConfig, reuseExercises: false })}
                        className={clsx(
                          'py-3 px-4 rounded-lg text-sm font-medium transition-all text-left',
                          !sessionConfig.reuseExercises
                            ? 'bg-indigo-600 text-white'
                            : 'bg-bg-tertiary text-text-secondary hover:bg-bg-hover'
                        )}
                      >
                        <div className="flex items-center gap-2">
                          <span>✨</span>
                          <div>
                            <div className="font-medium">Generate New</div>
                            <div className={clsx(
                              'text-xs mt-0.5',
                              !sessionConfig.reuseExercises ? 'text-indigo-200' : 'text-text-muted'
                            )}>
                              Fresh exercises via AI
                            </div>
                          </div>
                        </div>
                      </button>
                    </div>
                  </div>
                </div>

                {/* Error display */}
                {sessionError && (
                  <div className="mt-6 p-4 bg-red-500/10 border border-red-500/20 rounded-lg">
                    <div className="flex items-start gap-3">
                      <span className="text-red-400 text-lg">⚠️</span>
                      <div className="flex-1">
                        <p className="text-sm font-medium text-red-400 mb-1">
                          Exercise Generation Failed
                        </p>
                        <p className="text-xs text-red-300/80">
                          {sessionError}
                        </p>
                        <p className="text-xs text-text-muted mt-2">
                          This may be due to a temporary issue with the AI service. Please try again or select a different topic.
                        </p>
                      </div>
                      <button
                        onClick={() => setSessionError(null)}
                        className="text-red-400/60 hover:text-red-400 text-sm"
                      >
                        ✕
                      </button>
                    </div>
                  </div>
                )}

                {/* Start button */}
                <div className="mt-8 flex flex-col items-center gap-3">
                  <Button
                    size="lg"
                    onClick={handleStartSession}
                    loading={createSessionMutation.isPending}
                    disabled={!canStart || hasNoTopics}
                    className="px-12"
                  >
                    {createSessionMutation.isPending 
                      ? 'Generating Exercises...' 
                      : hasNoTopics 
                        ? 'No Topics Available' 
                        : canStart 
                          ? 'Start Practice' 
                          : 'Select a Topic'}
                  </Button>
                  
                  {/* Loading message */}
                  {createSessionMutation.isPending && (
                    <motion.p
                      initial={{ opacity: 0, y: -10 }}
                      animate={{ opacity: 1, y: 0 }}
                      className="text-sm text-text-secondary text-center"
                    >
                      Creating personalized exercises for <span className="text-indigo-400 font-medium">{sessionConfig.topicName || sessionConfig.topic}</span>...
                      <br />
                      <span className="text-xs text-text-muted">This may take a few seconds</span>
                    </motion.p>
                  )}
                </div>

                {/* Hint text */}
                {!canStart && !hasNoTopics && !sessionError && !createSessionMutation.isPending && (
                  <p className="mt-4 text-center text-xs text-text-muted">
                    Select a topic from the list above to begin your practice session
                  </p>
                )}
              </Card>
            </motion.div>

            {/* Back link */}
            <motion.div variants={fadeInUp} className="text-center">
              <Button variant="ghost" onClick={() => navigate('/')}>
                ← Back to Dashboard
              </Button>
            </motion.div>
          </motion.div>
        </div>
      </div>
    )
  }

  // Loading state
  if (createSessionMutation.isPending) {
    return <PageLoader message="Creating practice session..." />
  }

  // No exercises
  if (session && (!session.items || session.items.length === 0)) {
    return (
      <div className="min-h-screen bg-bg-primary flex items-center justify-center p-6">
        <EmptyState
          icon="📚"
          title="No exercises available"
          description="There are no exercises available for this topic. Try adding more content or selecting a different topic."
          onAction={() => navigate('/')}
          actionLabel="Back to Dashboard"
        />
      </div>
    )
  }

  // Session complete
  if (isComplete) {
    return (
      <div className="min-h-screen bg-bg-primary p-6 lg:p-8">
        <SessionComplete
          summary={getSessionSummary()}
          onStartNew={handleStartNew}
        />
      </div>
    )
  }

  // Active session
  return (
    <div className="min-h-screen bg-bg-primary p-6 lg:p-8">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <Button variant="ghost" onClick={() => {
            if (confirm('End session? Your progress will be saved.')) {
              // End session in backend before resetting local state
              if (session?.session_id && !sessionEndedRef.current) {
                sessionEndedRef.current = true
                endSessionMutation.mutate(session.session_id)
              }
              reset()
              navigate('/')
            }
          }}>
            ← Exit Session
          </Button>
          
          <SessionProgress
            current={progress.completed}
            total={progress.total}
            correctCount={progress.correct}
            timeElapsed={progress.timeElapsed}
            className="flex-1 mx-8"
          />
        </div>

        {/* Exercise/Feedback */}
        <AnimatePresence mode="wait">
          {showFeedback && lastEvaluation ? (
            <FeedbackDisplay
              key="feedback"
              evaluation={lastEvaluation}
              onConfidenceSelect={handleConfidenceSelect}
              onContinue={handleContinue}
            />
          ) : currentExercise ? (
            <motion.div
              key={`exercise-${currentExercise.id || currentExercise.exercise_uuid || progress.completed}`}
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
              className="space-y-6"
            >
              <ExerciseCard exercise={currentExercise} />
              
              <ResponseInput
                exerciseType={currentExercise.exercise_type}
                language={currentExercise.language}
                initialCode={currentExercise.starter_code}
                onSubmit={handleSubmit}
                isSubmitting={submitMutation.isPending}
              />
            </motion.div>
          ) : null}
        </AnimatePresence>
      </div>
    </div>
  )
}

export default PracticeSession
