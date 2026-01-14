/**
 * ReviewQueue Page
 * 
 * Spaced repetition review interface with FSRS ratings.
 * 
 * SPACED REPETITION CARDS vs EXERCISES:
 * 
 * This page handles Spaced Repetition Cards, which are different from Exercises:
 * 
 * SPACED REP CARDS (this page - /review):
 * - Simple front/back flashcards for memory retention
 * - Self-rated (Again/Hard/Good/Easy)
 * - FSRS algorithm optimizes when you review each card
 * - Best for: Remembering facts, definitions, concepts
 * 
 * EXERCISES (Practice page - /practice):
 * - Rich, structured problems with detailed prompts
 * - LLM-evaluated with personalized feedback
 * - Adapts exercise TYPE based on your mastery level
 * - Best for: Practicing application and deep understanding
 */

import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import {
  FlashCard,
  RatingButtons,
  ReviewStats,
  ReviewComplete,
} from '../components/review'
import { Button, PageLoader, EmptyState, Card } from '../components/common'
import { reviewApi } from '../api/review'
import { knowledgeApi } from '../api/knowledge'
import { useReviewStore, useSettingsStore } from '../stores'
import { useKeyboardShortcuts } from '../hooks'


// Info component explaining cards vs exercises
function LearningModeInfo() {
  const [isExpanded, setIsExpanded] = useState(false)
  
  return (
    <div className="mb-6 p-4 bg-indigo-500/10 border border-indigo-500/20 rounded-lg">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center justify-between text-left"
      >
        <div className="flex items-center gap-2">
          <span className="text-indigo-400">💡</span>
          <span className="text-sm font-medium text-indigo-300">
            What are flashcards vs exercises?
          </span>
        </div>
        <span className="text-indigo-400 text-xs">
          {isExpanded ? '▲ Hide' : '▼ Show'}
        </span>
      </button>
      
      {isExpanded && (
        <div className="mt-4 text-sm text-text-secondary space-y-4">
          <div className="p-3 bg-bg-secondary rounded-lg">
            <div className="flex items-center gap-2 mb-2">
              <span>📚</span>
              <span className="font-medium text-emerald-400">Flashcards (This Page)</span>
            </div>
            <ul className="list-disc list-inside space-y-1 text-xs">
              <li>Simple question → answer format</li>
              <li>Self-rate how well you remembered</li>
              <li>Optimized for <span className="text-emerald-300">long-term memory</span></li>
              <li>Best for facts, definitions, terminology</li>
            </ul>
          </div>
          
          <div className="p-3 bg-bg-secondary rounded-lg">
            <div className="flex items-center gap-2 mb-2">
              <span>🎯</span>
              <span className="font-medium text-amber-400">Exercises (Practice Page)</span>
            </div>
            <ul className="list-disc list-inside space-y-1 text-xs">
              <li>Detailed prompts requiring written responses</li>
              <li>AI evaluates and gives feedback</li>
              <li>Adapts difficulty to your skill level</li>
              <li>Best for <span className="text-amber-300">applying knowledge</span></li>
            </ul>
          </div>
          
          <p className="text-xs text-text-muted italic">
            💡 Tip: Use both! Flashcards help you remember, exercises help you understand deeply.
          </p>
        </div>
      )}
    </div>
  )
}

// Component for when there are no cards
function NoCardsState({ onNavigate, onRefresh }) {
  const [isGenerating, setIsGenerating] = useState(false)
  const [selectedTopic, setSelectedTopic] = useState('')

  // Fetch available topics
  const { data: topicsData, isLoading: topicsLoading } = useQuery({
    queryKey: ['topics-hierarchy'],
    queryFn: knowledgeApi.getTopics,
    staleTime: 5 * 60 * 1000,
  })

  // Flatten topics for selection
  const flattenedTopics = topicsData?.roots?.flatMap(function flatten(node) {
    const current = { id: node.path, name: node.name }
    const children = (node.children || []).flatMap(flatten)
    return [current, ...children]
  }) || []

  const handleGenerateCards = async () => {
    if (!selectedTopic) {
      toast.error('Please select a topic first')
      return
    }
    
    setIsGenerating(true)
    try {
      const result = await reviewApi.generateCards({
        topic: selectedTopic,
        count: 10,
        difficulty: 'mixed',
      })
      
      toast.success(`Generated ${result.generated_count} new cards!`)
      onRefresh()
    } catch (error) {
      toast.error('Failed to generate cards: ' + (error.response?.data?.detail || error.message))
    } finally {
      setIsGenerating(false)
    }
  }

  return (
    <Card className="max-w-lg text-center">
      <span className="text-6xl mb-4 block">📚</span>
      <h2 className="text-2xl font-bold text-text-primary mb-2">No Cards to Review</h2>
      <p className="text-text-secondary mb-4">
        You don&apos;t have any flashcards yet. Generate some cards to start your spaced repetition journey!
      </p>
      
      {/* Info about cards vs exercises */}
      <LearningModeInfo />
      
      {/* Topic Selection */}
      <div className="mb-6">
        <label className="block text-sm font-medium text-text-secondary mb-2 text-left">
          Select a Topic
        </label>
        {topicsLoading ? (
          <div className="animate-pulse bg-bg-tertiary h-10 rounded-lg" />
        ) : (
          <select
            value={selectedTopic}
            onChange={(e) => setSelectedTopic(e.target.value)}
            className="w-full px-4 py-2.5 rounded-lg bg-bg-tertiary border border-border-primary text-text-primary focus:outline-none focus:border-accent-primary"
          >
            <option value="">Choose a topic...</option>
            {flattenedTopics.map((topic) => (
              <option key={topic.id} value={topic.id}>
                {topic.name}
              </option>
            ))}
          </select>
        )}
      </div>

      {/* Actions */}
      <div className="flex flex-col gap-3">
        <Button
          onClick={handleGenerateCards}
          loading={isGenerating}
          disabled={!selectedTopic || isGenerating}
          className="w-full"
        >
          {isGenerating ? 'Generating Cards...' : '✨ Generate Cards'}
        </Button>
        
        <Button variant="secondary" onClick={onNavigate} className="w-full">
          ← Back to Dashboard
        </Button>
      </div>
      
      <p className="text-xs text-text-muted mt-4">
        Cards will be generated using AI based on your knowledge base content.
      </p>
    </Card>
  )
}

export function ReviewQueue() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  
  const showKeyboardHints = useSettingsStore((s) => s.showKeyboardHints)
  
  const {
    cards,
    currentIndex,
    setCards,
    nextCard,
    recordRating,
    getCurrentCard,
    getSessionStats,
    isQueueEmpty,
  } = useReviewStore()

  const [sessionStartTime] = useState(() => Date.now())
  const [cardStartTime, setCardStartTime] = useState(Date.now())
  
  // Active recall state
  const [evaluation, setEvaluation] = useState(null)
  const [showFeedback, setShowFeedback] = useState(false)

  // Fetch due cards
  const { data: dueCards, isLoading, error } = useQuery({
    queryKey: ['review', 'due'],
    queryFn: reviewApi.getDueCards,
    staleTime: 60000,
  })

  // Evaluate answer mutation (active recall)
  const evaluateMutation = useMutation({
    mutationFn: reviewApi.evaluateAnswer,
    onSuccess: (data) => {
      setEvaluation(data)
      setShowFeedback(true)
    },
    onError: (err) => {
      toast.error('Failed to evaluate answer: ' + (err.response?.data?.detail || err.message))
    },
  })

  // Rate card mutation
  const rateMutation = useMutation({
    mutationFn: reviewApi.rateCard,
    onSuccess: (data, variables) => {
      // Record the rating (from request variables) and move to next card
      recordRating(variables.cardId, variables.rating, data.scheduled_days)
      // Reset for next card
      setEvaluation(null)
      setShowFeedback(false)
      nextCard()
    },
    onError: () => {
      toast.error('Failed to save rating')
    },
  })

  // Initialize queue when cards load
  useEffect(() => {
    if (dueCards?.cards && cards.length === 0) {
      setCards(dueCards.cards, dueCards.total_due)
    }
  }, [dueCards, cards.length, setCards])

  // Reset card timer and state when card changes
  useEffect(() => {
    setCardStartTime(Date.now())
    setEvaluation(null)
    setShowFeedback(false)
  }, [currentIndex])

  const currentCard = getCurrentCard()
  const stats = getSessionStats()
  const isComplete = isQueueEmpty()
  
  // Compute progress
  const progress = {
    reviewed: stats.reviewed,
    remaining: stats.remaining,
    total: stats.totalDue,
  }

  // Handle answer submission for LLM evaluation
  const handleSubmitAnswer = useCallback((userAnswer) => {
    if (!currentCard) return
    
    evaluateMutation.mutate({
      cardId: currentCard.id,
      userAnswer,
    })
  }, [currentCard, evaluateMutation])

  // Handle confirming the rating after seeing evaluation
  const handleConfirmRating = useCallback((rating) => {
    if (!currentCard) return
    
    const timeSpentSeconds = Math.round((Date.now() - cardStartTime) / 1000)
    
    rateMutation.mutate({
      cardId: currentCard.id,
      rating,
      timeSpentSeconds,
    })
  }, [currentCard, cardStartTime, rateMutation])

  // Keyboard shortcuts for rating confirmation (after evaluation)
  useKeyboardShortcuts({
    '1': () => showFeedback && handleConfirmRating(1),
    '2': () => showFeedback && handleConfirmRating(2),
    '3': () => showFeedback && handleConfirmRating(3),
    '4': () => showFeedback && handleConfirmRating(4),
  }, { enabled: !isComplete && showFeedback })

  // Reset function to clear the store
  const handleReset = useCallback(() => {
    setCards([], 0)
  }, [setCards])

  // Determine content based on state
  const renderContent = () => {
    // Loading state
    if (isLoading) {
      return (
        <div className="flex-1 flex items-center justify-center">
          <PageLoader message="Loading review queue..." />
        </div>
      )
    }

    // Error state
    if (error) {
      return (
        <div className="flex-1 flex items-center justify-center p-6">
          <EmptyState
            icon="⚠️"
            title="Failed to load review queue"
            description={error.message}
            onAction={() => queryClient.invalidateQueries(['review', 'due'])}
            actionLabel="Try Again"
          />
        </div>
      )
    }

    // No cards due - offer to generate cards
    if (!dueCards?.cards?.length && cards.length === 0) {
      return (
        <div className="flex-1 flex items-center justify-center p-6">
          <NoCardsState 
            onNavigate={() => navigate('/')}
            onRefresh={() => queryClient.invalidateQueries(['review', 'due'])}
          />
        </div>
      )
    }

    // Session complete
    if (isComplete) {
      const sessionDuration = Math.round((Date.now() - sessionStartTime) / 1000)
      const sessionMinutes = Math.floor(sessionDuration / 60)
      const sessionSeconds = sessionDuration % 60

      return (
        <div className="p-6 lg:p-8">
          <ReviewComplete
            stats={{
              ...stats,
              sessionDuration,
              sessionDurationFormatted: `${sessionMinutes}:${sessionSeconds.toString().padStart(2, '0')}`,
              avgResponseTime: stats.reviewed > 0 
                ? Math.round(sessionDuration / stats.reviewed) 
                : 0,
            }}
            nextDueDate={dueCards?.nextDueDate}
            onReviewMore={() => {
              handleReset()
              queryClient.invalidateQueries(['review', 'due'])
            }}
          />
        </div>
      )
    }

    // Active review
    return (
      <div className="p-6 lg:p-8">
        <div className="max-w-3xl mx-auto">
          {/* Header */}
          <div className="flex items-center justify-between mb-6">
            <Button 
              variant="ghost" 
              onClick={() => {
                if (confirm('End review session? Your progress has been saved.')) {
                  handleReset()
                  navigate('/')
                }
              }}
            >
              ← Exit Review
            </Button>
            
            <ReviewStats
              remaining={progress.remaining}
              reviewed={progress.reviewed}
              dueToday={progress.total}
              avgResponseTime={stats.reviewed > 0 
                ? Math.round((Date.now() - sessionStartTime) / 1000 / stats.reviewed)
                : undefined}
            />
          </div>

          {/* Active Recall Card */}
          <AnimatePresence mode="wait">
            {currentCard && (
              <motion.div
                key={currentCard.id}
                initial={{ opacity: 0, x: 50 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -50 }}
                transition={{ duration: 0.3 }}
                className="space-y-6"
              >
                <FlashCard
                  card={currentCard}
                  showFeedback={showFeedback}
                  evaluation={evaluation}
                  onSubmitAnswer={handleSubmitAnswer}
                  isEvaluating={evaluateMutation.isPending}
                />

                {/* Rating Buttons (shown after evaluation) */}
                <AnimatePresence mode="wait">
                  {showFeedback && evaluation && (
                    <motion.div
                      key="rating"
                      initial={{ opacity: 0, y: 20 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: -20 }}
                    >
                      <div className="p-4 bg-bg-elevated rounded-xl border border-border-primary">
                        <p className="text-sm text-text-secondary mb-3 text-center">
                          {evaluation.is_correct 
                            ? 'Great job! How confident did you feel?'
                            : 'Keep practicing! How would you rate this attempt?'
                          }
                        </p>
                        <RatingButtons
                          onRate={handleConfirmRating}
                          suggestedRating={evaluation.rating}
                          isLoading={rateMutation.isPending}
                          showShortcuts={showKeyboardHints}
                        />
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    )
  }

  return (
    <main className="flex-1 ml-16 min-h-screen bg-bg-primary flex flex-col">
      {renderContent()}
    </main>
  )
}

export default ReviewQueue
