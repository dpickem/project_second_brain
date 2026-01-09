/**
 * Practice Store Tests
 */

import { describe, it, expect, beforeEach } from 'vitest'
import { usePracticeStore } from './practiceStore'

describe('practiceStore', () => {
  beforeEach(() => {
    // Reset store to initial state
    usePracticeStore.getState().reset()
  })

  describe('initial state', () => {
    it('should have correct default values', () => {
      const state = usePracticeStore.getState()
      
      expect(state.session).toBeNull()
      expect(state.sessionId).toBeNull()
      expect(state.currentItemIndex).toBe(0)
      expect(state.responses).toEqual([])
      expect(state.showFeedback).toBe(false)
      expect(state.lastEvaluation).toBeNull()
      expect(state.sessionLength).toBe(15)
    })
  })

  describe('startSession', () => {
    it('should initialize a new session', () => {
      const mockSession = {
        id: 'session-123',
        items: [
          { id: '1', question: 'Q1' },
          { id: '2', question: 'Q2' },
        ],
      }
      
      usePracticeStore.getState().startSession(mockSession)
      
      const state = usePracticeStore.getState()
      expect(state.session).toEqual(mockSession)
      expect(state.sessionId).toBe('session-123')
      expect(state.currentItemIndex).toBe(0)
      expect(state.responses).toEqual([])
      expect(state.startTime).toBeTruthy()
      expect(state.showFeedback).toBe(false)
    })
  })

  describe('endSession', () => {
    it('should end session and reset state', () => {
      // Start a session first
      const mockSession = { id: 'session-123', items: [{ id: '1' }] }
      usePracticeStore.getState().startSession(mockSession)
      
      usePracticeStore.getState().endSession()
      
      const state = usePracticeStore.getState()
      expect(state.session).toBeNull()
      expect(state.sessionId).toBeNull()
      expect(state.currentItemIndex).toBe(0)
      expect(state.responses).toEqual([])
      expect(state.showFeedback).toBe(false)
    })
  })

  describe('setSessionConfig', () => {
    it('should update session config', () => {
      usePracticeStore.getState().setSessionConfig({
        topicFilter: 'javascript',
        sessionLength: 30,
      })
      
      const state = usePracticeStore.getState()
      expect(state.topicFilter).toBe('javascript')
      expect(state.sessionLength).toBe(30)
    })
  })

  describe('submitResponse', () => {
    it('should record response with evaluation', () => {
      const mockSession = { id: 'session-123', items: [{ id: '1' }] }
      usePracticeStore.getState().startSession(mockSession)
      
      const evaluation = { is_correct: true, score: 1.0 }
      usePracticeStore.getState().submitResponse('item-1', 'my answer', evaluation)
      
      const state = usePracticeStore.getState()
      expect(state.responses).toHaveLength(1)
      expect(state.responses[0].itemId).toBe('item-1')
      expect(state.responses[0].response).toBe('my answer')
      expect(state.responses[0].evaluation).toEqual(evaluation)
      expect(state.showFeedback).toBe(true)
      expect(state.lastEvaluation).toEqual(evaluation)
    })

    it('should track time spent on item', () => {
      const mockSession = { id: 'session-123', items: [{ id: '1' }] }
      usePracticeStore.getState().startSession(mockSession)
      
      usePracticeStore.getState().submitResponse('item-1', 'answer', { is_correct: true })
      
      const state = usePracticeStore.getState()
      expect(state.responses[0].timeSpent).toBeGreaterThanOrEqual(0)
      expect(state.responses[0].timestamp).toBeTruthy()
    })

    it('should handle zero time spent when itemStartTime is null', () => {
      usePracticeStore.setState({ itemStartTime: null })
      
      usePracticeStore.getState().submitResponse('item-1', 'answer', { is_correct: true })
      
      const state = usePracticeStore.getState()
      expect(state.responses[0].timeSpent).toBe(0)
    })

    it('should append multiple responses', () => {
      const mockSession = { id: 'session-123', items: [{ id: '1' }, { id: '2' }] }
      usePracticeStore.getState().startSession(mockSession)
      
      usePracticeStore.getState().submitResponse('item-1', 'answer1', { is_correct: true })
      usePracticeStore.getState().submitResponse('item-2', 'answer2', { is_correct: false })
      
      const state = usePracticeStore.getState()
      expect(state.responses).toHaveLength(2)
      expect(state.responses[0].itemId).toBe('item-1')
      expect(state.responses[1].itemId).toBe('item-2')
    })
  })

  describe('nextItem', () => {
    it('should advance to next item', () => {
      const mockSession = { id: 'session-123', items: [{ id: '1' }, { id: '2' }] }
      usePracticeStore.getState().startSession(mockSession)
      
      usePracticeStore.getState().nextItem()
      
      const state = usePracticeStore.getState()
      expect(state.currentItemIndex).toBe(1)
      expect(state.showFeedback).toBe(false)
      expect(state.lastEvaluation).toBeNull()
    })
  })

  describe('previousItem', () => {
    it('should go back to previous item', () => {
      const mockSession = { id: 'session-123', items: [{ id: '1' }, { id: '2' }] }
      usePracticeStore.getState().startSession(mockSession)
      usePracticeStore.getState().nextItem()
      
      usePracticeStore.getState().previousItem()
      
      const state = usePracticeStore.getState()
      expect(state.currentItemIndex).toBe(0)
    })

    it('should not go below 0', () => {
      const mockSession = { id: 'session-123', items: [{ id: '1' }] }
      usePracticeStore.getState().startSession(mockSession)
      
      usePracticeStore.getState().previousItem()
      
      expect(usePracticeStore.getState().currentItemIndex).toBe(0)
    })
  })

  describe('setConfidence', () => {
    it('should set confidence for a specific response', () => {
      const mockSession = { id: 'session-123', items: [{ id: '1' }] }
      usePracticeStore.getState().startSession(mockSession)
      usePracticeStore.getState().submitResponse('item-1', 'answer', { is_correct: true })
      
      usePracticeStore.getState().setConfidence('item-1', 0.8)
      
      const state = usePracticeStore.getState()
      expect(state.responses[0].confidence).toBe(0.8)
    })

    it('should not modify other responses', () => {
      const mockSession = { id: 'session-123', items: [{ id: '1' }, { id: '2' }] }
      usePracticeStore.getState().startSession(mockSession)
      usePracticeStore.getState().submitResponse('item-1', 'answer1', { is_correct: true })
      usePracticeStore.getState().submitResponse('item-2', 'answer2', { is_correct: false })
      
      usePracticeStore.getState().setConfidence('item-1', 0.9)
      
      const state = usePracticeStore.getState()
      expect(state.responses[0].confidence).toBe(0.9)
      expect(state.responses[1].confidence).toBeUndefined()
    })

    it('should not add confidence to non-existent response', () => {
      const mockSession = { id: 'session-123', items: [{ id: '1' }] }
      usePracticeStore.getState().startSession(mockSession)
      usePracticeStore.getState().submitResponse('item-1', 'answer', { is_correct: true })
      
      usePracticeStore.getState().setConfidence('non-existent', 0.5)
      
      const state = usePracticeStore.getState()
      expect(state.responses[0].confidence).toBeUndefined()
    })
  })

  describe('hideFeedback', () => {
    it('should hide feedback', () => {
      usePracticeStore.setState({ showFeedback: true })
      
      usePracticeStore.getState().hideFeedback()
      
      expect(usePracticeStore.getState().showFeedback).toBe(false)
    })
  })

  describe('selectors', () => {
    describe('getCurrentItem', () => {
      it('should get current item', () => {
        const items = [{ id: '1', question: 'Q1' }, { id: '2', question: 'Q2' }]
        const mockSession = { id: 'session-123', items }
        usePracticeStore.getState().startSession(mockSession)
        usePracticeStore.getState().nextItem()
        
        const currentItem = usePracticeStore.getState().getCurrentItem()
        
        expect(currentItem).toEqual({ id: '2', question: 'Q2' })
      })

      it('should return null when no session', () => {
        expect(usePracticeStore.getState().getCurrentItem()).toBeNull()
      })
    })

    describe('getProgress', () => {
      it('should calculate progress', () => {
        const items = [{ id: '1' }, { id: '2' }, { id: '3' }, { id: '4' }]
        const mockSession = { id: 'session-123', items }
        usePracticeStore.getState().startSession(mockSession)
        usePracticeStore.getState().nextItem()
        usePracticeStore.getState().nextItem()
        
        const progress = usePracticeStore.getState().getProgress()
        
        expect(progress.completed).toBe(2)
        expect(progress.total).toBe(4)
        expect(progress.percentage).toBe(50)
      })

      it('should calculate accuracy with correct and incorrect responses', () => {
        const items = [{ id: '1' }, { id: '2' }, { id: '3' }, { id: '4' }]
        const mockSession = { id: 'session-123', items }
        usePracticeStore.getState().startSession(mockSession)
        
        // Submit 3 responses: 2 correct, 1 incorrect
        usePracticeStore.getState().submitResponse('1', 'a', { is_correct: true })
        usePracticeStore.getState().nextItem()
        usePracticeStore.getState().submitResponse('2', 'b', { is_correct: false })
        usePracticeStore.getState().nextItem()
        usePracticeStore.getState().submitResponse('3', 'c', { is_correct: true })
        usePracticeStore.getState().nextItem()
        
        const progress = usePracticeStore.getState().getProgress()
        
        expect(progress.completed).toBe(3)
        expect(progress.correct).toBe(2)
        expect(progress.accuracy).toBe(67) // 2/3 = 66.67% rounded to 67
      })

      it('should handle zero completed items', () => {
        const items = [{ id: '1' }, { id: '2' }]
        const mockSession = { id: 'session-123', items }
        usePracticeStore.getState().startSession(mockSession)
        
        const progress = usePracticeStore.getState().getProgress()
        
        expect(progress.completed).toBe(0)
        expect(progress.percentage).toBe(0)
        expect(progress.accuracy).toBe(0)
      })

      it('should return time elapsed', () => {
        const items = [{ id: '1' }]
        const mockSession = { id: 'session-123', items }
        usePracticeStore.getState().startSession(mockSession)
        
        const progress = usePracticeStore.getState().getProgress()
        
        expect(progress.timeElapsed).toBeGreaterThanOrEqual(0)
        expect(progress.timeElapsedFormatted).toBeTruthy()
      })

      it('should return zero total when no session', () => {
        const progress = usePracticeStore.getState().getProgress()
        
        expect(progress.total).toBe(0)
        expect(progress.completed).toBe(0)
        expect(progress.percentage).toBe(0)
      })
    })

    describe('isSessionComplete', () => {
      it('should return true when all items completed', () => {
        const items = [{ id: '1' }, { id: '2' }]
        const mockSession = { id: 'session-123', items }
        usePracticeStore.getState().startSession(mockSession)
        usePracticeStore.getState().nextItem()
        usePracticeStore.getState().nextItem()
        
        expect(usePracticeStore.getState().isSessionComplete()).toBe(true)
      })

      it('should return false when items remain', () => {
        const items = [{ id: '1' }, { id: '2' }]
        const mockSession = { id: 'session-123', items }
        usePracticeStore.getState().startSession(mockSession)
        
        expect(usePracticeStore.getState().isSessionComplete()).toBe(false)
      })
    })

    describe('getSessionSummary', () => {
      it('should return null when no session', () => {
        expect(usePracticeStore.getState().getSessionSummary()).toBeNull()
      })

      it('should return summary when session exists', () => {
        const items = [{ id: '1' }, { id: '2' }]
        const mockSession = { id: 'session-123', items }
        usePracticeStore.getState().startSession(mockSession)
        usePracticeStore.getState().submitResponse('1', 'answer', { is_correct: true })
        
        const summary = usePracticeStore.getState().getSessionSummary()
        
        expect(summary).not.toBeNull()
        expect(summary.sessionId).toBe('session-123')
        expect(summary.totalItems).toBe(2)
        expect(summary.completedItems).toBe(1)
        expect(summary.correctItems).toBe(1)
      })

      it('should calculate accuracy correctly', () => {
        const items = [{ id: '1' }, { id: '2' }, { id: '3' }, { id: '4' }]
        const mockSession = { id: 'session-123', items }
        usePracticeStore.getState().startSession(mockSession)
        usePracticeStore.getState().submitResponse('1', 'a', { is_correct: true })
        usePracticeStore.getState().submitResponse('2', 'b', { is_correct: true })
        usePracticeStore.getState().submitResponse('3', 'c', { is_correct: false })
        usePracticeStore.getState().submitResponse('4', 'd', { is_correct: true })
        
        const summary = usePracticeStore.getState().getSessionSummary()
        
        expect(summary.completedItems).toBe(4)
        expect(summary.correctItems).toBe(3)
        expect(summary.accuracy).toBe(75) // 3/4 = 75%
      })

      it('should include total time and formatted time', () => {
        const items = [{ id: '1' }]
        const mockSession = { id: 'session-123', items }
        usePracticeStore.getState().startSession(mockSession)
        usePracticeStore.getState().submitResponse('1', 'answer', { is_correct: true })
        
        const summary = usePracticeStore.getState().getSessionSummary()
        
        expect(summary.totalTime).toBeGreaterThanOrEqual(0)
        expect(summary.totalTimeFormatted).toBeTruthy()
        expect(summary.averageTimePerItem).toBeGreaterThanOrEqual(0)
      })

      it('should include responses array', () => {
        const items = [{ id: '1' }, { id: '2' }]
        const mockSession = { id: 'session-123', items }
        usePracticeStore.getState().startSession(mockSession)
        usePracticeStore.getState().submitResponse('1', 'answer1', { is_correct: true })
        usePracticeStore.getState().submitResponse('2', 'answer2', { is_correct: false })
        
        const summary = usePracticeStore.getState().getSessionSummary()
        
        expect(summary.responses).toHaveLength(2)
        expect(summary.responses[0].response).toBe('answer1')
        expect(summary.responses[1].response).toBe('answer2')
      })

      it('should handle empty responses', () => {
        const items = [{ id: '1' }, { id: '2' }]
        const mockSession = { id: 'session-123', items }
        usePracticeStore.getState().startSession(mockSession)
        
        const summary = usePracticeStore.getState().getSessionSummary()
        
        expect(summary.completedItems).toBe(0)
        expect(summary.correctItems).toBe(0)
        expect(summary.accuracy).toBe(0)
      })
    })

    describe('getResponseForItem', () => {
      it('should return response for specific item', () => {
        const mockSession = { id: 'session-123', items: [{ id: '1' }, { id: '2' }] }
        usePracticeStore.getState().startSession(mockSession)
        usePracticeStore.getState().submitResponse('item-1', 'answer1', { is_correct: true })
        usePracticeStore.getState().submitResponse('item-2', 'answer2', { is_correct: false })
        
        const response = usePracticeStore.getState().getResponseForItem('item-1')
        
        expect(response).toBeTruthy()
        expect(response.itemId).toBe('item-1')
        expect(response.response).toBe('answer1')
      })

      it('should return undefined for non-existent item', () => {
        const mockSession = { id: 'session-123', items: [{ id: '1' }] }
        usePracticeStore.getState().startSession(mockSession)
        usePracticeStore.getState().submitResponse('item-1', 'answer', { is_correct: true })
        
        const response = usePracticeStore.getState().getResponseForItem('non-existent')
        
        expect(response).toBeUndefined()
      })

      it('should return undefined when no responses exist', () => {
        const response = usePracticeStore.getState().getResponseForItem('item-1')
        
        expect(response).toBeUndefined()
      })
    })
  })

  describe('reset', () => {
    it('should reset to initial state', () => {
      // Set some state
      const mockSession = { id: 'session-123', items: [{ id: '1' }] }
      usePracticeStore.getState().startSession(mockSession)
      
      usePracticeStore.getState().reset()
      
      const state = usePracticeStore.getState()
      expect(state.session).toBeNull()
      expect(state.sessionId).toBeNull()
      expect(state.sessionLength).toBe(15)
    })
  })
})
