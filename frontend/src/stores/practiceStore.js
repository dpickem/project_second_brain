/**
 * Practice Store
 * 
 * Zustand store for practice session state management.
 */

import { create } from 'zustand'

export const usePracticeStore = create((set, get) => ({
  // =====================
  // State
  // =====================
  
  // Session data
  session: null,
  sessionId: null,
  
  // Current progress
  currentItemIndex: 0,
  responses: [],
  
  // Timing
  startTime: null,
  itemStartTime: null,
  
  // UI state
  showFeedback: false,
  lastEvaluation: null,
  
  // Session configuration
  topicFilter: null,
  sessionLength: 15, // minutes
  
  // =====================
  // Session Actions
  // =====================
  
  startSession: (session) => set({
    session,
    sessionId: session.id,
    currentItemIndex: 0,
    responses: [],
    startTime: Date.now(),
    itemStartTime: Date.now(),
    showFeedback: false,
    lastEvaluation: null,
  }),
  
  endSession: () => set({
    session: null,
    sessionId: null,
    currentItemIndex: 0,
    responses: [],
    startTime: null,
    itemStartTime: null,
    showFeedback: false,
    lastEvaluation: null,
    topicFilter: null,
  }),
  
  setSessionConfig: (config) => set({
    topicFilter: config.topicFilter ?? null,
    sessionLength: config.sessionLength ?? 15,
  }),
  
  // =====================
  // Item Actions
  // =====================
  
  submitResponse: (itemId, response, evaluation) => set((state) => {
    const timeSpent = state.itemStartTime 
      ? Math.round((Date.now() - state.itemStartTime) / 1000)
      : 0
      
    return {
      responses: [
        ...state.responses,
        {
          itemId,
          response,
          evaluation,
          timeSpent,
          timestamp: Date.now(),
        },
      ],
      showFeedback: true,
      lastEvaluation: evaluation,
    }
  }),
  
  nextItem: () => set((state) => ({
    currentItemIndex: state.currentItemIndex + 1,
    showFeedback: false,
    lastEvaluation: null,
    itemStartTime: Date.now(),
  })),
  
  previousItem: () => set((state) => ({
    currentItemIndex: Math.max(0, state.currentItemIndex - 1),
    showFeedback: false,
    lastEvaluation: null,
    itemStartTime: Date.now(),
  })),
  
  setConfidence: (itemId, confidence) => set((state) => ({
    responses: state.responses.map((r) =>
      r.itemId === itemId ? { ...r, confidence } : r
    ),
  })),
  
  hideFeedback: () => set({
    showFeedback: false,
  }),
  
  // =====================
  // Selectors
  // =====================
  
  getCurrentItem: () => {
    const { session, currentItemIndex } = get()
    return session?.items?.[currentItemIndex] || null
  },
  
  getProgress: () => {
    const { session, currentItemIndex, responses, startTime } = get()
    const total = session?.items?.length || 0
    const completed = currentItemIndex
    const correct = responses.filter((r) => r.evaluation?.is_correct).length
    const timeElapsed = startTime ? Date.now() - startTime : 0
    
    return {
      completed,
      total,
      correct,
      percentage: total > 0 ? Math.round((completed / total) * 100) : 0,
      accuracy: completed > 0 ? Math.round((correct / completed) * 100) : 0,
      timeElapsed,
      timeElapsedFormatted: formatDuration(timeElapsed),
    }
  },
  
  isSessionComplete: () => {
    const { session, currentItemIndex } = get()
    return session && currentItemIndex >= (session?.items?.length || 0)
  },
  
  getSessionSummary: () => {
    const { session, responses, startTime } = get()
    if (!session) return null
    
    const totalTime = startTime ? Date.now() - startTime : 0
    const correct = responses.filter((r) => r.evaluation?.is_correct).length
    const total = responses.length
    
    return {
      sessionId: session.id,
      totalItems: session.items?.length || 0,
      completedItems: total,
      correctItems: correct,
      accuracy: total > 0 ? Math.round((correct / total) * 100) : 0,
      totalTime,
      totalTimeFormatted: formatDuration(totalTime),
      averageTimePerItem: total > 0 ? Math.round(totalTime / total / 1000) : 0,
      responses,
    }
  },
  
  getResponseForItem: (itemId) => {
    const { responses } = get()
    return responses.find((r) => r.itemId === itemId)
  },
  
  // =====================
  // Reset
  // =====================
  
  reset: () => set({
    session: null,
    sessionId: null,
    currentItemIndex: 0,
    responses: [],
    startTime: null,
    itemStartTime: null,
    showFeedback: false,
    lastEvaluation: null,
    topicFilter: null,
    sessionLength: 15,
  }),
}))

// Helper function to format duration
function formatDuration(ms) {
  const seconds = Math.floor(ms / 1000)
  const minutes = Math.floor(seconds / 60)
  const remainingSeconds = seconds % 60
  
  if (minutes === 0) {
    return `${seconds}s`
  }
  
  return `${minutes}m ${remainingSeconds}s`
}

export default usePracticeStore
