/**
 * PracticeSession Page
 * 
 * Main practice session interface with exercises and feedback.
 */

import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { useMutation } from '@tanstack/react-query'
import { clsx } from 'clsx'
import toast from 'react-hot-toast'
import { 
  ExerciseCard, 
  ResponseInput, 
  FeedbackDisplay, 
  SessionProgress,
  SessionComplete,
} from '../components/practice'
import { Card, Button, PageLoader, EmptyState } from '../components/common'
import { practiceApi } from '../api/practice'
import { usePracticeStore, useSettingsStore } from '../stores'
import { fadeInUp, staggerContainer } from '../utils/animations'

export function PracticeSession() {
  const { topicId } = useParams()
  const navigate = useNavigate()
  
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
    topic: topicId || '',
  })

  // Create session mutation
  const createSessionMutation = useMutation({
    mutationFn: practiceApi.createSession,
    onSuccess: (data) => {
      startSession(data)
      setIsConfiguring(false)
    },
    onError: (error) => {
      toast.error(error.response?.data?.detail || 'Failed to create session')
    },
  })

  // Submit attempt mutation
  const submitMutation = useMutation({
    mutationFn: practiceApi.submitAttempt,
    onSuccess: (evaluation, { exerciseId }) => {
      submitResponse(exerciseId, null, evaluation)
    },
    onError: () => {
      toast.error('Failed to submit response')
    },
  })

  // Update confidence mutation
  const confidenceMutation = useMutation({
    mutationFn: ({ attemptId, confidence }) => 
      practiceApi.updateConfidence(attemptId, confidence),
  })

  const currentExercise = getCurrentItem()
  const progress = getProgress()
  const isComplete = isSessionComplete()

  // Start new session
  const handleStartSession = () => {
    createSessionMutation.mutate({
      topicFilter: sessionConfig.topic || undefined,
      durationMinutes: sessionConfig.duration,
    })
  }

  // Submit response
  const handleSubmit = (response) => {
    if (!currentExercise) return
    
    submitMutation.mutate({
      exerciseId: currentExercise.id,
      response,
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
    reset()
    setIsConfiguring(true)
  }

  // Session configuration screen
  if (isConfiguring) {
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
                Configure your practice session settings
              </p>
            </motion.div>

            {/* Configuration */}
            <motion.div variants={fadeInUp}>
              <Card>
                <div className="space-y-6">
                  {/* Duration */}
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

                  {/* Topic filter */}
                  {topicId && (
                    <div>
                      <label className="block text-sm font-medium text-text-primary mb-2">
                        Focus Topic
                      </label>
                      <div className="p-3 bg-indigo-500/10 border border-indigo-500/20 rounded-lg">
                        <span className="text-sm text-indigo-300">{topicId}</span>
                      </div>
                    </div>
                  )}
                </div>

                {/* Start button */}
                <div className="mt-8 flex justify-center">
                  <Button
                    size="lg"
                    onClick={handleStartSession}
                    loading={createSessionMutation.isPending}
                    className="px-12"
                  >
                    Start Practice
                  </Button>
                </div>
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
              key={`exercise-${currentExercise.id}`}
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
