/**
 * ReviewQueue Page
 * 
 * Spaced repetition review interface with FSRS ratings.
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
import { Button, PageLoader, EmptyState } from '../components/common'
import { reviewApi } from '../api/review'
import { useReviewStore, useSettingsStore } from '../stores'
import { useKeyboardShortcuts } from '../hooks'

export function ReviewQueue() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  
  const showKeyboardHints = useSettingsStore((s) => s.showKeyboardHints)
  
  const {
    cards,
    currentIndex,
    showAnswer,
    setCards,
    showAnswerAction,
    nextCard,
    recordRating,
    getCurrentCard,
    getSessionStats,
    isQueueEmpty,
  } = useReviewStore()

  const [sessionStartTime] = useState(() => Date.now())
  const [cardStartTime, setCardStartTime] = useState(Date.now())

  // Fetch due cards
  const { data: dueCards, isLoading, error } = useQuery({
    queryKey: ['review', 'due'],
    queryFn: reviewApi.getDueCards,
    staleTime: 60000,
  })

  // Rate card mutation
  const rateMutation = useMutation({
    mutationFn: ({ cardId, rating, responseTime }) =>
      reviewApi.rateCard(cardId, rating, responseTime),
    onSuccess: (data, { cardId }) => {
      // Record the rating and move to next card
      recordRating(cardId, data.rating, data.newInterval)
      nextCard()
    },
    onError: () => {
      toast.error('Failed to save rating')
    },
  })

  // Initialize queue when cards load
  useEffect(() => {
    if (dueCards?.cards && cards.length === 0) {
      setCards(dueCards.cards, dueCards.totalDue)
    }
  }, [dueCards, cards.length, setCards])

  // Reset card timer when card changes
  useEffect(() => {
    setCardStartTime(Date.now())
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

  // Handle rating
  const handleRate = useCallback((rating) => {
    if (!currentCard) return
    
    const responseTime = Math.round((Date.now() - cardStartTime) / 1000)
    
    rateMutation.mutate({
      cardId: currentCard.id,
      rating,
      responseTime,
    })
  }, [currentCard, cardStartTime, rateMutation])

  // Handle reveal
  const handleReveal = useCallback(() => {
    if (!showAnswer) {
      showAnswerAction()
    }
  }, [showAnswer, showAnswerAction])

  // Keyboard shortcuts
  useKeyboardShortcuts({
    'Space': handleReveal,
    '1': () => showAnswer && handleRate(1),
    '2': () => showAnswer && handleRate(2),
    '3': () => showAnswer && handleRate(3),
    '4': () => showAnswer && handleRate(4),
  }, { enabled: !isComplete })

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

    // No cards due
    if (!dueCards?.cards?.length && cards.length === 0) {
      return (
        <div className="flex-1 flex items-center justify-center p-6">
          <EmptyState
            icon="✨"
            title="All caught up!"
            description="You have no cards due for review right now. Great job staying on top of your learning!"
            onAction={() => navigate('/')}
            actionLabel="Back to Dashboard"
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

          {/* Card */}
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
                  showAnswer={showAnswer}
                  onShowAnswer={handleReveal}
                />

                {/* Rating or Reveal */}
                <AnimatePresence mode="wait">
                  {showAnswer ? (
                    <motion.div
                      key="rating"
                      initial={{ opacity: 0, y: 20 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: -20 }}
                    >
                      <RatingButtons
                        onRate={handleRate}
                        predictedIntervals={currentCard.predictedIntervals}
                        isLoading={rateMutation.isPending}
                        showShortcuts={showKeyboardHints}
                      />
                    </motion.div>
                  ) : (
                    <motion.div
                      key="reveal"
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      exit={{ opacity: 0 }}
                      className="text-center"
                    >
                      <Button
                        size="lg"
                        onClick={handleReveal}
                        className="px-16"
                      >
                        Show Answer
                      </Button>
                      <p className="text-xs text-text-muted mt-2">
                        Press <kbd className="px-1 bg-slate-700 rounded">Space</kbd> to reveal
                      </p>
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
