/**
 * Review Store
 * 
 * Zustand store for spaced repetition review queue state.
 */

import { create } from 'zustand'

export const useReviewStore = create((set, get) => ({
  // =====================
  // State
  // =====================
  
  // Cards queue
  cards: [],
  currentIndex: 0,
  
  // Session stats
  reviewedCount: 0,
  totalDueToday: 0,
  sessionStartTime: null,
  
  // Card state
  showAnswer: false,
  answerShownTime: null,
  
  // Ratings history (for undo)
  ratingsHistory: [],
  
  // Filters
  topicFilter: null,
  cardTypeFilter: null,
  
  // =====================
  // Queue Actions
  // =====================
  
  setCards: (cards, totalDue = 0) => set({
    cards,
    currentIndex: 0,
    reviewedCount: 0,
    totalDueToday: totalDue || cards.length,
    sessionStartTime: Date.now(),
    showAnswer: false,
    answerShownTime: null,
  }),
  
  addCards: (newCards) => set((state) => ({
    cards: [...state.cards, ...newCards],
    totalDueToday: state.totalDueToday + newCards.length,
  })),
  
  removeCard: (cardId) => set((state) => ({
    cards: state.cards.filter((c) => c.id !== cardId),
  })),
  
  // =====================
  // Card Actions
  // =====================
  
  showAnswerAction: () => set({
    showAnswer: true,
    answerShownTime: Date.now(),
  }),
  
  hideAnswer: () => set({
    showAnswer: false,
    answerShownTime: null,
  }),
  
  nextCard: () => set((state) => ({
    currentIndex: state.currentIndex + 1,
    reviewedCount: state.reviewedCount + 1,
    showAnswer: false,
    answerShownTime: null,
  })),
  
  previousCard: () => set((state) => ({
    currentIndex: Math.max(0, state.currentIndex - 1),
    showAnswer: false,
    answerShownTime: null,
  })),
  
  recordRating: (cardId, rating, newInterval) => set((state) => ({
    ratingsHistory: [
      ...state.ratingsHistory,
      {
        cardId,
        rating,
        newInterval,
        timestamp: Date.now(),
        responseTime: state.answerShownTime 
          ? Date.now() - state.answerShownTime 
          : 0,
      },
    ],
  })),
  
  // =====================
  // Filter Actions
  // =====================
  
  setTopicFilter: (topic) => set({ topicFilter: topic }),
  
  setCardTypeFilter: (type) => set({ cardTypeFilter: type }),
  
  clearFilters: () => set({
    topicFilter: null,
    cardTypeFilter: null,
  }),
  
  // =====================
  // Selectors
  // =====================
  
  getCurrentCard: () => {
    const { cards, currentIndex } = get()
    return cards[currentIndex] || null
  },
  
  getRemainingCount: () => {
    const { cards, currentIndex } = get()
    return Math.max(0, cards.length - currentIndex)
  },
  
  isQueueEmpty: () => {
    const { cards, currentIndex } = get()
    return currentIndex >= cards.length
  },
  
  getSessionStats: () => {
    const { reviewedCount, totalDueToday, sessionStartTime, ratingsHistory } = get()
    
    const sessionDuration = sessionStartTime 
      ? Date.now() - sessionStartTime 
      : 0
    
    // Calculate rating distribution
    const ratingCounts = { 1: 0, 2: 0, 3: 0, 4: 0 }
    ratingsHistory.forEach((r) => {
      if (ratingCounts[r.rating] !== undefined) {
        ratingCounts[r.rating]++
      }
    })
    
    // Calculate average response time
    const totalResponseTime = ratingsHistory.reduce(
      (sum, r) => sum + (r.responseTime || 0), 
      0
    )
    const avgResponseTime = ratingsHistory.length > 0 
      ? Math.round(totalResponseTime / ratingsHistory.length / 1000) 
      : 0
    
    return {
      reviewed: reviewedCount,
      totalDue: totalDueToday,
      remaining: totalDueToday - reviewedCount,
      percentComplete: totalDueToday > 0 
        ? Math.round((reviewedCount / totalDueToday) * 100) 
        : 0,
      sessionDuration,
      sessionDurationFormatted: formatDuration(sessionDuration),
      avgResponseTime, // seconds
      ratingDistribution: ratingCounts,
      // Quality metrics
      againCount: ratingCounts[1],
      hardCount: ratingCounts[2],
      goodCount: ratingCounts[3],
      easyCount: ratingCounts[4],
    }
  },
  
  getTimeSpentOnCurrentCard: () => {
    const { answerShownTime } = get()
    if (!answerShownTime) return 0
    return Math.round((Date.now() - answerShownTime) / 1000)
  },
  
  // Undo last rating
  undoLastRating: () => {
    const { ratingsHistory, currentIndex } = get()
    if (ratingsHistory.length === 0 || currentIndex === 0) return false
    
    set((state) => ({
      ratingsHistory: state.ratingsHistory.slice(0, -1),
      currentIndex: state.currentIndex - 1,
      reviewedCount: state.reviewedCount - 1,
      showAnswer: true,
      answerShownTime: Date.now(),
    }))
    
    return true
  },
  
  // =====================
  // Reset
  // =====================
  
  reset: () => set({
    cards: [],
    currentIndex: 0,
    reviewedCount: 0,
    totalDueToday: 0,
    sessionStartTime: null,
    showAnswer: false,
    answerShownTime: null,
    ratingsHistory: [],
    topicFilter: null,
    cardTypeFilter: null,
  }),
}))

// Helper function to format duration
function formatDuration(ms) {
  const seconds = Math.floor(ms / 1000)
  const minutes = Math.floor(seconds / 60)
  const hours = Math.floor(minutes / 60)
  
  if (hours > 0) {
    return `${hours}h ${minutes % 60}m`
  }
  if (minutes > 0) {
    return `${minutes}m ${seconds % 60}s`
  }
  return `${seconds}s`
}

export default useReviewStore
