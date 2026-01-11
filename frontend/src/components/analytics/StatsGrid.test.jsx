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

// Mock framer-motion
vi.mock('framer-motion', () => ({
  motion: {
    div: ({ children, className, ...props }) => (
      <div className={className} {...props}>
        {children}
      </div>
    ),
    span: ({ children, ...props }) => <span {...props}>{children}</span>,
    button: ({ children, className, ...props }) => (
      <button className={className} {...props}>
        {children}
      </button>
    ),
  },
}))

describe('StatsGrid', () => {
  const mockStats = {
    totalCards: 1500,
    masteredCards: 300,
    totalReviews: 5000,
    learningTime: 120, // 120 minutes = 2 hours
    streak: 14,
    avgRetention: 85,
  }

  it('renders with default empty stats', () => {
    render(<StatsGrid />)
    // Default values should be 0 - multiple stat items show 0
    // Check that the component renders and has zeros
    expect(screen.getByText('0%')).toBeInTheDocument() // retention
    expect(screen.getByText('0d')).toBeInTheDocument() // streak
    expect(screen.getByText('0h')).toBeInTheDocument() // learning time
  })

  it('renders all stat items', () => {
    render(<StatsGrid stats={mockStats} />)
    
    expect(screen.getByText('Total Cards')).toBeInTheDocument()
    expect(screen.getByText('Mastered')).toBeInTheDocument()
    expect(screen.getByText('Reviews')).toBeInTheDocument()
    expect(screen.getByText('Learning Time')).toBeInTheDocument()
    expect(screen.getByText('Streak')).toBeInTheDocument()
    expect(screen.getByText('Retention')).toBeInTheDocument()
  })

  it('displays formatted total cards value', () => {
    render(<StatsGrid stats={mockStats} />)
    expect(screen.getByText('1,500')).toBeInTheDocument()
  })

  it('displays formatted mastered cards value', () => {
    render(<StatsGrid stats={mockStats} />)
    expect(screen.getByText('300')).toBeInTheDocument()
  })

  it('displays formatted total reviews value', () => {
    render(<StatsGrid stats={mockStats} />)
    expect(screen.getByText('5,000')).toBeInTheDocument()
  })

  it('displays learning time in hours', () => {
    render(<StatsGrid stats={mockStats} />)
    expect(screen.getByText('2h')).toBeInTheDocument()
  })

  it('displays streak with day suffix', () => {
    render(<StatsGrid stats={mockStats} />)
    expect(screen.getByText('14d')).toBeInTheDocument()
  })

  it('displays retention percentage', () => {
    render(<StatsGrid stats={mockStats} />)
    expect(screen.getByText('85%')).toBeInTheDocument()
  })

  it('calculates mastered percentage correctly', () => {
    render(<StatsGrid stats={mockStats} />)
    // 300/1500 = 20%
    expect(screen.getByText('20% of total')).toBeInTheDocument()
  })

  it('shows 0% when totalCards is 0', () => {
    render(<StatsGrid stats={{ ...mockStats, totalCards: 0 }} />)
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
    expect(screen.getByText('In your library')).toBeInTheDocument()
    // "All time" appears twice (for Reviews and Learning Time)
    expect(screen.getAllByText('All time')).toHaveLength(2)
    expect(screen.getByText('Keep it going!')).toBeInTheDocument()
    expect(screen.getByText('Average recall')).toBeInTheDocument()
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
    render(<StatsGrid stats={{ ...mockStats, streak: 5 }} />)
    expect(screen.queryByText('🎉')).not.toBeInTheDocument()
  })
})

describe('StatCard', () => {
  it('renders with basic props', () => {
    render(<StatCard label="Test Stat" value="100" />)
    expect(screen.getByText('Test Stat')).toBeInTheDocument()
    expect(screen.getByText('100')).toBeInTheDocument()
  })

  it('renders icon when provided', () => {
    render(<StatCard label="Test" value="50" icon="📊" />)
    expect(screen.getByText('📊')).toBeInTheDocument()
  })

  it('displays positive change with + prefix', () => {
    render(<StatCard label="Test" value="100" change={15} />)
    expect(screen.getByText('+15%')).toBeInTheDocument()
  })

  it('displays negative change', () => {
    render(<StatCard label="Test" value="100" change={-10} />)
    expect(screen.getByText('-10%')).toBeInTheDocument()
  })

  it('displays zero change', () => {
    render(<StatCard label="Test" value="100" change={0} />)
    expect(screen.getByText('0%')).toBeInTheDocument()
  })

  it('renders change label when provided', () => {
    render(<StatCard label="Test" value="100" change={5} changeLabel="vs last week" />)
    expect(screen.getByText('vs last week')).toBeInTheDocument()
  })

  it('applies green color for positive change', () => {
    render(<StatCard label="Test" value="100" change={10} />)
    const changeElement = screen.getByText('+10%')
    expect(changeElement).toHaveClass('text-emerald-400')
  })

  it('applies red color for negative change', () => {
    render(<StatCard label="Test" value="100" change={-10} />)
    const changeElement = screen.getByText('-10%')
    expect(changeElement).toHaveClass('text-red-400')
  })

  it('applies muted color for zero change', () => {
    render(<StatCard label="Test" value="100" change={0} />)
    const changeElement = screen.getByText('0%')
    expect(changeElement).toHaveClass('text-text-muted')
  })

  it('renders sparkline when data provided', () => {
    const sparklineData = [{ value: 10 }, { value: 20 }, { value: 15 }]
    render(<StatCard label="Test" value="100" sparklineData={sparklineData} />)
    expect(screen.getByTestId('responsive-container')).toBeInTheDocument()
  })

  it('does not render sparkline when no data', () => {
    render(<StatCard label="Test" value="100" />)
    expect(screen.queryByTestId('responsive-container')).not.toBeInTheDocument()
  })

  it('applies custom className', () => {
    const { container } = render(<StatCard label="Test" value="100" className="custom-stat" />)
    expect(container.querySelector('.custom-stat')).toBeInTheDocument()
  })

  it('renders without change when undefined', () => {
    render(<StatCard label="Test" value="100" />)
    expect(screen.queryByText('%')).not.toBeInTheDocument()
  })
})
