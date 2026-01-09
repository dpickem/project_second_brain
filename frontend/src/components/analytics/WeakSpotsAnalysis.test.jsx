/**
 * WeakSpotsAnalysis Component Tests
 */

import { describe, it, expect, vi } from 'vitest'
import { renderWithProviders, screen } from '../../test/test-utils'
import userEvent from '@testing-library/user-event'
import { WeakSpotsAnalysis } from './WeakSpotsAnalysis'

// Mock framer-motion
vi.mock('framer-motion', () => ({
  motion: {
    div: ({ children, className, initial, animate, transition, custom, variants, ...props }) => (
      <div className={className} {...props}>
        {children}
      </div>
    ),
    button: ({ children, className, variants, initial, whileHover, whileTap, ...props }) => (
      <button className={className} {...props}>
        {children}
      </button>
    ),
  },
}))

describe('WeakSpotsAnalysis', () => {
  const mockWeakSpots = [
    {
      topic: 'Advanced Algorithms',
      mastery: 25,
      cardCount: 30,
      dueCount: 12,
      recommendation: 'Focus on graph traversal algorithms',
    },
    {
      topic: 'System Design',
      mastery: 45,
      cardCount: 20,
      dueCount: 8,
      recommendation: 'Practice distributed systems concepts',
    },
    {
      topic: 'Database Optimization',
      mastery: 60,
      cardCount: 15,
      dueCount: 5,
      recommendation: 'Review indexing strategies',
    },
  ]

  describe('Empty State', () => {
    it('renders congratulation message when no weak spots', () => {
      renderWithProviders(<WeakSpotsAnalysis weakSpots={[]} />)
      expect(screen.getByText('Great Progress!')).toBeInTheDocument()
    })

    it('renders encouragement text when no weak spots', () => {
      renderWithProviders(<WeakSpotsAnalysis weakSpots={[]} />)
      expect(
        screen.getByText('No weak spots identified. Keep up the excellent work!')
      ).toBeInTheDocument()
    })

    it('renders star emoji when no weak spots', () => {
      renderWithProviders(<WeakSpotsAnalysis weakSpots={[]} />)
      expect(screen.getByText('🌟')).toBeInTheDocument()
    })

    it('renders empty state with default props', () => {
      renderWithProviders(<WeakSpotsAnalysis />)
      expect(screen.getByText('Great Progress!')).toBeInTheDocument()
    })
  })

  describe('Header', () => {
    it('renders header title', () => {
      renderWithProviders(<WeakSpotsAnalysis weakSpots={mockWeakSpots} />)
      expect(screen.getByText('🎯 Areas to Focus')).toBeInTheDocument()
    })

    it('renders header description', () => {
      renderWithProviders(<WeakSpotsAnalysis weakSpots={mockWeakSpots} />)
      expect(
        screen.getByText('Topics that could use more practice')
      ).toBeInTheDocument()
    })

    it('displays badge with topic count', () => {
      renderWithProviders(<WeakSpotsAnalysis weakSpots={mockWeakSpots} />)
      expect(screen.getByText('3 topics')).toBeInTheDocument()
    })
  })

  describe('Weak Spots List', () => {
    it('renders all weak spots', () => {
      renderWithProviders(<WeakSpotsAnalysis weakSpots={mockWeakSpots} />)
      expect(screen.getByText('Advanced Algorithms')).toBeInTheDocument()
      expect(screen.getByText('System Design')).toBeInTheDocument()
      expect(screen.getByText('Database Optimization')).toBeInTheDocument()
    })

    it('displays mastery percentage for each topic', () => {
      renderWithProviders(<WeakSpotsAnalysis weakSpots={mockWeakSpots} />)
      expect(screen.getByText('25%')).toBeInTheDocument()
      expect(screen.getByText('45%')).toBeInTheDocument()
      expect(screen.getByText('60%')).toBeInTheDocument()
    })

    it('displays card count and due count', () => {
      renderWithProviders(<WeakSpotsAnalysis weakSpots={mockWeakSpots} />)
      expect(screen.getByText('30 cards • 12 due')).toBeInTheDocument()
      expect(screen.getByText('20 cards • 8 due')).toBeInTheDocument()
      expect(screen.getByText('15 cards • 5 due')).toBeInTheDocument()
    })

    it('displays recommendations when available', () => {
      renderWithProviders(<WeakSpotsAnalysis weakSpots={mockWeakSpots} />)
      expect(
        screen.getByText('💡 Focus on graph traversal algorithms')
      ).toBeInTheDocument()
      expect(
        screen.getByText('💡 Practice distributed systems concepts')
      ).toBeInTheDocument()
      expect(
        screen.getByText('💡 Review indexing strategies')
      ).toBeInTheDocument()
    })

    it('handles spots without recommendations', () => {
      const spotsWithoutReco = [
        { topic: 'Test Topic', mastery: 40, cardCount: 10, dueCount: 5 },
      ]
      renderWithProviders(<WeakSpotsAnalysis weakSpots={spotsWithoutReco} />)
      expect(screen.getByText('Test Topic')).toBeInTheDocument()
      expect(screen.queryByText(/💡/)).not.toBeInTheDocument()
    })

    it('handles spots with zero due count', () => {
      const spotsNoDue = [
        { topic: 'No Due', mastery: 40, cardCount: 10, dueCount: 0 },
      ]
      renderWithProviders(<WeakSpotsAnalysis weakSpots={spotsNoDue} />)
      expect(screen.getByText('10 cards • 0 due')).toBeInTheDocument()
    })

    it('handles spots with undefined due count', () => {
      const spotsUndefinedDue = [
        { topic: 'Undefined Due', mastery: 40, cardCount: 10 },
      ]
      renderWithProviders(<WeakSpotsAnalysis weakSpots={spotsUndefinedDue} />)
      expect(screen.getByText('10 cards • 0 due')).toBeInTheDocument()
    })
  })

  describe('Visual Indicators', () => {
    it('renders red indicator for mastery < 30', () => {
      renderWithProviders(<WeakSpotsAnalysis weakSpots={mockWeakSpots} />)
      expect(screen.getByText('🔴')).toBeInTheDocument()
    })

    it('renders yellow indicator for mastery 30-49', () => {
      renderWithProviders(<WeakSpotsAnalysis weakSpots={mockWeakSpots} />)
      expect(screen.getByText('🟡')).toBeInTheDocument()
    })

    it('renders blue indicator for mastery >= 50', () => {
      renderWithProviders(<WeakSpotsAnalysis weakSpots={mockWeakSpots} />)
      expect(screen.getByText('🔵')).toBeInTheDocument()
    })
  })

  describe('Practice Buttons', () => {
    it('renders practice button for each weak spot', () => {
      renderWithProviders(<WeakSpotsAnalysis weakSpots={mockWeakSpots} />)
      const practiceButtons = screen.getAllByRole('button', { name: 'Practice' })
      expect(practiceButtons).toHaveLength(3)
    })

    it('calls onPractice with topic when practice button clicked', async () => {
      const user = userEvent.setup()
      const mockOnPractice = vi.fn()
      renderWithProviders(
        <WeakSpotsAnalysis weakSpots={mockWeakSpots} onPractice={mockOnPractice} />
      )

      const practiceButtons = screen.getAllByRole('button', { name: 'Practice' })
      await user.click(practiceButtons[0])

      expect(mockOnPractice).toHaveBeenCalledWith('Advanced Algorithms')
    })

    it('handles missing onPractice callback gracefully', async () => {
      const user = userEvent.setup()
      renderWithProviders(<WeakSpotsAnalysis weakSpots={mockWeakSpots} />)

      const practiceButtons = screen.getAllByRole('button', { name: 'Practice' })
      // Should not throw
      await user.click(practiceButtons[0])
    })
  })

  describe('CTA Button', () => {
    it('renders Start Focused Practice button', () => {
      renderWithProviders(<WeakSpotsAnalysis weakSpots={mockWeakSpots} />)
      expect(
        screen.getByRole('button', { name: 'Start Focused Practice' })
      ).toBeInTheDocument()
    })

    it('links to /practice page', () => {
      renderWithProviders(<WeakSpotsAnalysis weakSpots={mockWeakSpots} />)
      const link = screen.getByRole('link')
      expect(link).toHaveAttribute('href', '/practice')
    })

    it('does not render CTA when no weak spots', () => {
      renderWithProviders(<WeakSpotsAnalysis weakSpots={[]} />)
      expect(
        screen.queryByRole('button', { name: 'Start Focused Practice' })
      ).not.toBeInTheDocument()
    })
  })

  describe('Styling', () => {
    it('applies custom className', () => {
      const { container } = renderWithProviders(
        <WeakSpotsAnalysis weakSpots={mockWeakSpots} className="custom-analysis" />
      )
      expect(container.querySelector('.custom-analysis')).toBeInTheDocument()
    })

    it('applies custom className in empty state', () => {
      const { container } = renderWithProviders(
        <WeakSpotsAnalysis weakSpots={[]} className="empty-custom" />
      )
      expect(container.querySelector('.empty-custom')).toBeInTheDocument()
    })
  })

  describe('Badge Variants', () => {
    it('uses danger variant for mastery < 30', () => {
      const dangerSpot = [
        { topic: 'Critical', mastery: 20, cardCount: 10, dueCount: 5 },
      ]
      renderWithProviders(<WeakSpotsAnalysis weakSpots={dangerSpot} />)
      // Badge shows mastery
      expect(screen.getByText('20%')).toBeInTheDocument()
    })

    it('uses warning variant for mastery 30-49', () => {
      const warningSpot = [
        { topic: 'Warning', mastery: 40, cardCount: 10, dueCount: 5 },
      ]
      renderWithProviders(<WeakSpotsAnalysis weakSpots={warningSpot} />)
      expect(screen.getByText('40%')).toBeInTheDocument()
    })

    it('uses default variant for mastery >= 50', () => {
      const defaultSpot = [
        { topic: 'Default', mastery: 55, cardCount: 10, dueCount: 5 },
      ]
      renderWithProviders(<WeakSpotsAnalysis weakSpots={defaultSpot} />)
      expect(screen.getByText('55%')).toBeInTheDocument()
    })
  })
})
