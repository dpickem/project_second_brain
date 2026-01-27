/**
 * StatsGrid Component Tests
 */

import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '../../test/test-utils'
import { StatsGrid, StatCard } from './StatsGrid'

// Mock recharts (used by LearningSparkline)
vi.mock('recharts', () => ({
  ResponsiveContainer: ({ children }) => <div data-testid="responsive-container">{children}</div>,
  AreaChart: ({ children }) => <div data-testid="area-chart">{children}</div>,
  Area: () => <div data-testid="area" />,
}))

// Note: framer-motion is globally mocked in src/test/setup.js

describe('StatsGrid', () => {
  // Mock stats now use the new property names
  const mockStats = {
    spacedRepCardsTotal: 1500,
    spacedRepCardsMastered: 300,
    spacedRepCardsLearning: 800,
    spacedRepCardsNew: 400,
    spacedRepReviewsTotal: 5000,
    exercisesTotal: 100,
    exercisesCompleted: 50,
    exercisesMastered: 25,
    exercisesAttemptsTotal: 200,
    exercisesAvgScore: 75,
    learningTime: 120, // 120 minutes = 2 hours
    streak: 14,
    avgRetention: 85,
  }

  it('renders with default empty stats', () => {
    render(<StatsGrid />)
    // Default values should be 0 - multiple stat items show 0
    expect(screen.getByText('0%')).toBeInTheDocument() // retention
    expect(screen.getByText('0d')).toBeInTheDocument() // streak
    expect(screen.getByText('0m')).toBeInTheDocument() // learning time (minutes, not hours when 0)
  })

  it('renders all stat items in combined view', () => {
    render(<StatsGrid stats={mockStats} />)
    
    // Combined view shows: Total Items, Mastered, Reviews, Learning Time, Streak, Retention
    expect(screen.getByText('Total Items')).toBeInTheDocument()
    expect(screen.getByText('Mastered')).toBeInTheDocument()
    expect(screen.getByText('Reviews')).toBeInTheDocument()
    expect(screen.getByText('Learning Time')).toBeInTheDocument()
    expect(screen.getByText('Streak')).toBeInTheDocument()
    expect(screen.getByText('Retention')).toBeInTheDocument()
  })

  it('displays formatted total items value (cards + exercises)', () => {
    render(<StatsGrid stats={mockStats} />)
    // Total items = spacedRepCardsTotal + exercisesTotal = 1500 + 100 = 1600
    expect(screen.getByText('1,600')).toBeInTheDocument()
  })

  it('displays formatted mastered value', () => {
    render(<StatsGrid stats={mockStats} />)
    // Mastered = spacedRepCardsMastered + exercisesMastered = 300 + 25 = 325
    expect(screen.getByText('325')).toBeInTheDocument()
  })

  it('displays formatted reviews value', () => {
    render(<StatsGrid stats={mockStats} />)
    expect(screen.getByText('5,000')).toBeInTheDocument()
  })

  it('displays learning time in hours', () => {
    render(<StatsGrid stats={mockStats} />)
    expect(screen.getByText('2h')).toBeInTheDocument()
  })

  it('displays streak in days', () => {
    render(<StatsGrid stats={mockStats} />)
    expect(screen.getByText('14d')).toBeInTheDocument()
  })

  it('displays retention percentage', () => {
    render(<StatsGrid stats={mockStats} />)
    expect(screen.getByText('85%')).toBeInTheDocument()
  })

  it('handles zero total cards for percentage calculation', () => {
    render(<StatsGrid stats={{ ...mockStats, spacedRepCardsTotal: 0, exercisesTotal: 0 }} />)
    expect(screen.getByText('0% of total')).toBeInTheDocument()
  })

  it('renders emojis for each stat', () => {
    render(<StatsGrid stats={mockStats} />)
    expect(screen.getByText('📚')).toBeInTheDocument()
    expect(screen.getByText('🎯')).toBeInTheDocument()
    expect(screen.getByText('✅')).toBeInTheDocument()
    expect(screen.getByText('⏱️')).toBeInTheDocument()
    expect(screen.getByText('🔥')).toBeInTheDocument()
    expect(screen.getByText('🧠')).toBeInTheDocument()
  })

  it('renders descriptions for each stat', () => {
    render(<StatsGrid stats={mockStats} />)
    // Combined mode descriptions (default viewMode)
    expect(screen.getByText('Keep it going!')).toBeInTheDocument() // Streak description
    expect(screen.getByText('Average recall')).toBeInTheDocument() // Retention description
    // Learning time shows specific description based on time
    expect(screen.getByText('120 min total')).toBeInTheDocument() // 2h = 120 min
  })

  it('applies custom className', () => {
    const { container } = render(<StatsGrid stats={mockStats} className="custom-grid" />)
    expect(container.querySelector('.custom-grid')).toBeInTheDocument()
  })

  it('renders grid layout', () => {
    const { container } = render(<StatsGrid stats={mockStats} />)
    expect(container.querySelector('.grid')).toBeInTheDocument()
  })

  it('highlights streak when >= 7 days', () => {
    render(<StatsGrid stats={{ ...mockStats, streak: 10 }} />)
    // Should have a celebration emoji
    expect(screen.getByText('🎉')).toBeInTheDocument()
  })

  it('does not highlight streak when < 7 days', () => {
    render(<StatsGrid stats={{ ...mockStats, streak: 3 }} />)
    // Should not have celebration emoji
    expect(screen.queryByText('🎉')).not.toBeInTheDocument()
  })
})

describe('StatCard', () => {
  it('renders stat card with all props', () => {
    render(
      <StatCard
        label="Test Stat"
        value="100"
        icon="📊"
        change={5}
        changeLabel="from last week"
      />
    )

    expect(screen.getByText('Test Stat')).toBeInTheDocument()
    expect(screen.getByText('100')).toBeInTheDocument()
    expect(screen.getByText('📊')).toBeInTheDocument()
  })

  it('displays positive change with icon', () => {
    render(
      <StatCard
        label="Reviews"
        value="500"
        icon="✅"
        change={10}
        changeLabel="from last week"
      />
    )

    expect(screen.getByText('+10%')).toBeInTheDocument()
    expect(screen.getByText('from last week')).toBeInTheDocument()
  })

  it('displays negative change with icon', () => {
    render(
      <StatCard
        label="Score"
        value="75%"
        icon="📊"
        change={-5}
        changeLabel="from last week"
      />
    )

    expect(screen.getByText('-5%')).toBeInTheDocument()
  })

  it('applies custom className', () => {
    const { container } = render(
      <StatCard
        label="Test"
        value="10"
        icon="📊"
        className="custom-card"
      />
    )

    expect(container.querySelector('.custom-card')).toBeInTheDocument()
  })

  it('handles missing optional props gracefully', () => {
    render(<StatCard label="Test" value="10" icon="📊" />)

    expect(screen.getByText('Test')).toBeInTheDocument()
    expect(screen.getByText('10')).toBeInTheDocument()
  })
})
