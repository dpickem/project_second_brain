/**
 * Tests for StreakCalendar Component
 * 
 * Tests the activity streak calendar including:
 * - Rendering and loading states
 * - Day cell rendering
 * - Activity level colors
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderWithProviders, screen } from '../../test/test-utils'
import { StreakCalendar } from './StreakCalendar'

// Mock date-fns to control "today"
const MOCK_TODAY = new Date(2026, 0, 15) // January 15, 2026

describe('StreakCalendar', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    vi.setSystemTime(MOCK_TODAY)
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  describe('rendering', () => {
    it('renders the calendar component', () => {
      renderWithProviders(<StreakCalendar activityData={[]} isLoading={false} />)

      // Should have day labels
      expect(screen.getByText('Mon')).toBeInTheDocument()
      expect(screen.getByText('Wed')).toBeInTheDocument()
      expect(screen.getByText('Fri')).toBeInTheDocument()
      expect(screen.getByText('Sun')).toBeInTheDocument()
    })

    it('renders without crashing when loading', () => {
      const { container } = renderWithProviders(
        <StreakCalendar activityData={[]} isLoading={true} />
      )

      // Component should still render something
      expect(container.firstChild).toBeInTheDocument()
    })

    it('renders header with activity info', () => {
      renderWithProviders(<StreakCalendar activityData={[]} isLoading={false} />)

      // Should show reviews and active days labels
      expect(screen.getByText(/reviews/i)).toBeInTheDocument()
      expect(screen.getByText(/active days/i)).toBeInTheDocument()
    })
  })

  describe('activity data', () => {
    it('renders day cells', () => {
      const { container } = renderWithProviders(
        <StreakCalendar activityData={[]} isLoading={false} />
      )

      // Should render many day cells (w-3 h-3 rounded-sm)
      const dayCells = container.querySelectorAll('.w-3.h-3.rounded-sm')
      expect(dayCells.length).toBeGreaterThan(0)
    })

    it('accepts activity data array', () => {
      const activityData = [
        { date: '2026-01-10', count: 5 },
        { date: '2026-01-11', count: 3 },
        { date: '2026-01-12', count: 7 },
      ]

      // Should not throw when passed activity data
      expect(() => {
        renderWithProviders(
          <StreakCalendar activityData={activityData} isLoading={false} />
        )
      }).not.toThrow()
    })

    it('handles empty activity data', () => {
      expect(() => {
        renderWithProviders(
          <StreakCalendar activityData={[]} isLoading={false} />
        )
      }).not.toThrow()
    })
  })

  describe('activity levels', () => {
    it('renders different colors based on activity level', () => {
      const activityData = [
        { date: '2026-01-10', count: 1 },  // level 1
        { date: '2026-01-11', count: 5 },  // level 2
        { date: '2026-01-12', count: 10 }, // level 3
        { date: '2026-01-13', count: 20 }, // level 4
      ]

      const { container } = renderWithProviders(
        <StreakCalendar activityData={activityData} isLoading={false} />
      )

      // Should render emerald color classes for active days
      const hasEmeraldCells = container.querySelector('[class*="emerald"]')
      expect(hasEmeraldCells).toBeTruthy()
    })
  })

  describe('scroll container', () => {
    it('has scrollable container', () => {
      const { container } = renderWithProviders(
        <StreakCalendar activityData={[]} isLoading={false} />
      )

      // Should have overflow-x-auto for horizontal scrolling
      const scrollContainer = container.querySelector('.overflow-x-auto')
      expect(scrollContainer).toBeInTheDocument()
    })
  })

  describe('sticky day labels', () => {
    it('has sticky day labels', () => {
      const { container } = renderWithProviders(
        <StreakCalendar activityData={[]} isLoading={false} />
      )

      // Should have sticky positioning
      const stickyElement = container.querySelector('.sticky')
      expect(stickyElement).toBeInTheDocument()
    })
  })

  describe('today highlighting', () => {
    it('highlights today with a ring', () => {
      const { container } = renderWithProviders(
        <StreakCalendar activityData={[]} isLoading={false} />
      )

      // Today should have ring-2 ring-amber-400
      const todayCell = container.querySelector('.ring-amber-400')
      expect(todayCell).toBeInTheDocument()
    })
  })
})
