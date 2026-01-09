/**
 * Review Store Tests
 */

import { describe, it, expect, beforeEach } from 'vitest'
import { useReviewStore } from './reviewStore'

describe('reviewStore', () => {
  beforeEach(() => {
    // Reset store to initial state
    useReviewStore.getState().reset()
  })

  describe('initial state', () => {
    it('should have correct default values', () => {
      const state = useReviewStore.getState()
      
      expect(state.cards).toEqual([])
      expect(state.currentIndex).toBe(0)
      expect(state.reviewedCount).toBe(0)
      expect(state.showAnswer).toBe(false)
      expect(state.ratingsHistory).toEqual([])
    })
  })

  describe('setCards', () => {
    it('should initialize cards queue', () => {
      const cards = [
        { id: '1', front: 'Q1', back: 'A1' },
        { id: '2', front: 'Q2', back: 'A2' },
      ]
      
      useReviewStore.getState().setCards(cards)
      
      const state = useReviewStore.getState()
      expect(state.cards).toEqual(cards)
      expect(state.currentIndex).toBe(0)
      expect(state.reviewedCount).toBe(0)
      expect(state.totalDueToday).toBe(2)
      expect(state.sessionStartTime).toBeTruthy()
      expect(state.showAnswer).toBe(false)
    })

    it('should set custom total due count', () => {
      const cards = [{ id: '1' }]
      
      useReviewStore.getState().setCards(cards, 10)
      
      expect(useReviewStore.getState().totalDueToday).toBe(10)
    })
  })

  describe('addCards', () => {
    it('should add cards to queue', () => {
      useReviewStore.setState({ cards: [{ id: '1' }], totalDueToday: 1 })
      
      useReviewStore.getState().addCards([{ id: '2' }, { id: '3' }])
      
      const state = useReviewStore.getState()
      expect(state.cards).toHaveLength(3)
      expect(state.totalDueToday).toBe(3)
    })
  })

  describe('removeCard', () => {
    it('should remove card from queue', () => {
      useReviewStore.setState({ cards: [{ id: '1' }, { id: '2' }] })
      
      useReviewStore.getState().removeCard('1')
      
      const state = useReviewStore.getState()
      expect(state.cards).toHaveLength(1)
      expect(state.cards[0].id).toBe('2')
    })
  })

  describe('showAnswerAction', () => {
    it('should reveal the answer', () => {
      useReviewStore.getState().showAnswerAction()
      
      const state = useReviewStore.getState()
      expect(state.showAnswer).toBe(true)
      expect(state.answerShownTime).toBeTruthy()
    })
  })

  describe('hideAnswer', () => {
    it('should hide the answer', () => {
      useReviewStore.setState({ showAnswer: true, answerShownTime: Date.now() })
      
      useReviewStore.getState().hideAnswer()
      
      const state = useReviewStore.getState()
      expect(state.showAnswer).toBe(false)
      expect(state.answerShownTime).toBeNull()
    })
  })

  describe('nextCard', () => {
    it('should advance to next card', () => {
      useReviewStore.setState({
        cards: [{ id: '1' }, { id: '2' }],
        currentIndex: 0,
        reviewedCount: 0,
        showAnswer: true,
      })
      
      useReviewStore.getState().nextCard()
      
      const state = useReviewStore.getState()
      expect(state.currentIndex).toBe(1)
      expect(state.reviewedCount).toBe(1)
      expect(state.showAnswer).toBe(false)
    })
  })

  describe('previousCard', () => {
    it('should go back to previous card', () => {
      useReviewStore.setState({
        cards: [{ id: '1' }, { id: '2' }],
        currentIndex: 1,
        showAnswer: true,
      })
      
      useReviewStore.getState().previousCard()
      
      const state = useReviewStore.getState()
      expect(state.currentIndex).toBe(0)
      expect(state.showAnswer).toBe(false)
    })

    it('should not go below 0', () => {
      useReviewStore.setState({ currentIndex: 0 })
      
      useReviewStore.getState().previousCard()
      
      expect(useReviewStore.getState().currentIndex).toBe(0)
    })
  })

  describe('recordRating', () => {
    it('should record rating in history', () => {
      useReviewStore.setState({ answerShownTime: Date.now() - 1000 })
      
      useReviewStore.getState().recordRating('card-1', 3, 4)
      
      const state = useReviewStore.getState()
      expect(state.ratingsHistory).toHaveLength(1)
      expect(state.ratingsHistory[0].cardId).toBe('card-1')
      expect(state.ratingsHistory[0].rating).toBe(3)
      expect(state.ratingsHistory[0].newInterval).toBe(4)
      expect(state.ratingsHistory[0].timestamp).toBeTruthy()
    })
  })

  describe('filter actions', () => {
    it('should set topic filter', () => {
      useReviewStore.getState().setTopicFilter('javascript')
      
      expect(useReviewStore.getState().topicFilter).toBe('javascript')
    })

    it('should set card type filter', () => {
      useReviewStore.getState().setCardTypeFilter('flashcard')
      
      expect(useReviewStore.getState().cardTypeFilter).toBe('flashcard')
    })

    it('should clear filters', () => {
      useReviewStore.setState({ topicFilter: 'js', cardTypeFilter: 'flashcard' })
      
      useReviewStore.getState().clearFilters()
      
      const state = useReviewStore.getState()
      expect(state.topicFilter).toBeNull()
      expect(state.cardTypeFilter).toBeNull()
    })
  })

  describe('selectors', () => {
    describe('getCurrentCard', () => {
      it('should get current card', () => {
        const cards = [{ id: '1', front: 'Q1' }, { id: '2', front: 'Q2' }]
        useReviewStore.setState({ cards, currentIndex: 1 })
        
        const current = useReviewStore.getState().getCurrentCard()
        
        expect(current).toEqual({ id: '2', front: 'Q2' })
      })

      it('should return null when no cards', () => {
        expect(useReviewStore.getState().getCurrentCard()).toBeNull()
      })
    })

    describe('getRemainingCount', () => {
      it('should get remaining card count', () => {
        useReviewStore.setState({
          cards: [{ id: '1' }, { id: '2' }, { id: '3' }, { id: '4' }],
          currentIndex: 1,
        })
        
        expect(useReviewStore.getState().getRemainingCount()).toBe(3)
      })
    })

    describe('isQueueEmpty', () => {
      it('should return true when queue is complete', () => {
        useReviewStore.setState({
          cards: [{ id: '1' }, { id: '2' }],
          currentIndex: 2,
        })
        
        expect(useReviewStore.getState().isQueueEmpty()).toBe(true)
      })

      it('should return false when cards remain', () => {
        useReviewStore.setState({
          cards: [{ id: '1' }, { id: '2' }],
          currentIndex: 1,
        })
        
        expect(useReviewStore.getState().isQueueEmpty()).toBe(false)
      })
    })

    describe('getSessionStats', () => {
      it('should calculate session stats', () => {
        useReviewStore.setState({
          reviewedCount: 5,
          totalDueToday: 10,
          sessionStartTime: Date.now() - 60000, // 1 minute ago
          ratingsHistory: [
            { rating: 1 },
            { rating: 2 },
            { rating: 3 },
            { rating: 3 },
            { rating: 4 },
          ],
        })
        
        const stats = useReviewStore.getState().getSessionStats()
        
        expect(stats.reviewed).toBe(5)
        expect(stats.totalDue).toBe(10)
        expect(stats.remaining).toBe(5)
        expect(stats.percentComplete).toBe(50)
        expect(stats.againCount).toBe(1)
        expect(stats.hardCount).toBe(1)
        expect(stats.goodCount).toBe(2)
        expect(stats.easyCount).toBe(1)
      })

      it('should calculate average response time', () => {
        useReviewStore.setState({
          reviewedCount: 3,
          totalDueToday: 5,
          sessionStartTime: Date.now(),
          ratingsHistory: [
            { rating: 3, responseTime: 3000 },
            { rating: 4, responseTime: 2000 },
            { rating: 3, responseTime: 4000 },
          ],
        })
        
        const stats = useReviewStore.getState().getSessionStats()
        
        expect(stats.avgResponseTime).toBe(3) // 9000ms / 3 / 1000 = 3 seconds
      })

      it('should handle zero total due', () => {
        useReviewStore.setState({
          reviewedCount: 0,
          totalDueToday: 0,
          sessionStartTime: Date.now(),
          ratingsHistory: [],
        })
        
        const stats = useReviewStore.getState().getSessionStats()
        
        expect(stats.percentComplete).toBe(0)
        expect(stats.avgResponseTime).toBe(0)
      })

      it('should include session duration formatted', () => {
        useReviewStore.setState({
          reviewedCount: 1,
          totalDueToday: 5,
          sessionStartTime: Date.now() - 120000, // 2 minutes ago
          ratingsHistory: [],
        })
        
        const stats = useReviewStore.getState().getSessionStats()
        
        expect(stats.sessionDuration).toBeGreaterThanOrEqual(119000)
        expect(stats.sessionDurationFormatted).toContain('m')
      })

      it('should handle invalid ratings gracefully', () => {
        useReviewStore.setState({
          reviewedCount: 2,
          totalDueToday: 5,
          sessionStartTime: Date.now(),
          ratingsHistory: [
            { rating: 5 }, // Invalid rating
            { rating: 0 }, // Invalid rating
          ],
        })
        
        const stats = useReviewStore.getState().getSessionStats()
        
        // Invalid ratings should not be counted
        expect(stats.ratingDistribution[1]).toBe(0)
        expect(stats.ratingDistribution[2]).toBe(0)
        expect(stats.ratingDistribution[3]).toBe(0)
        expect(stats.ratingDistribution[4]).toBe(0)
      })
    })

    describe('getTimeSpentOnCurrentCard', () => {
      it('should return time spent since answer was shown', () => {
        const twoSecondsAgo = Date.now() - 2000
        useReviewStore.setState({ answerShownTime: twoSecondsAgo })
        
        const timeSpent = useReviewStore.getState().getTimeSpentOnCurrentCard()
        
        expect(timeSpent).toBeGreaterThanOrEqual(2)
        expect(timeSpent).toBeLessThan(5) // Allow some tolerance
      })

      it('should return 0 when answer not shown', () => {
        useReviewStore.setState({ answerShownTime: null })
        
        const timeSpent = useReviewStore.getState().getTimeSpentOnCurrentCard()
        
        expect(timeSpent).toBe(0)
      })

      it('should return 0 immediately after showing answer', () => {
        useReviewStore.setState({ answerShownTime: Date.now() })
        
        const timeSpent = useReviewStore.getState().getTimeSpentOnCurrentCard()
        
        expect(timeSpent).toBeLessThan(1)
      })
    })
  })

  describe('undoLastRating', () => {
    it('should undo last rating and go back', () => {
      useReviewStore.setState({
        cards: [{ id: '1' }, { id: '2' }],
        currentIndex: 2,
        reviewedCount: 2,
        ratingsHistory: [{ cardId: '1', rating: 3 }, { cardId: '2', rating: 4 }],
      })
      
      const result = useReviewStore.getState().undoLastRating()
      
      expect(result).toBe(true)
      const state = useReviewStore.getState()
      expect(state.currentIndex).toBe(1)
      expect(state.reviewedCount).toBe(1)
      expect(state.ratingsHistory).toHaveLength(1)
      expect(state.showAnswer).toBe(true)
    })

    it('should return false when no history', () => {
      useReviewStore.setState({ ratingsHistory: [], currentIndex: 0 })
      
      const result = useReviewStore.getState().undoLastRating()
      
      expect(result).toBe(false)
    })
  })

  describe('reset', () => {
    it('should reset to initial state', () => {
      useReviewStore.setState({
        cards: [{ id: '1' }],
        currentIndex: 1,
        reviewedCount: 1,
        showAnswer: true,
        ratingsHistory: [{ rating: 3 }],
      })
      
      useReviewStore.getState().reset()
      
      const state = useReviewStore.getState()
      expect(state.cards).toEqual([])
      expect(state.currentIndex).toBe(0)
      expect(state.reviewedCount).toBe(0)
      expect(state.showAnswer).toBe(false)
      expect(state.ratingsHistory).toEqual([])
    })
  })
})
