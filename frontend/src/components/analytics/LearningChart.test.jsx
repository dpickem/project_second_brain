/**
 * LearningChart Component Tests
 */

import React from 'react'
import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '../../test/test-utils'
import { LearningChart, LearningSparkline } from './LearningChart'

// Mock recharts components since they require canvas/SVG rendering
// Note: We render children but filter out raw SVG elements like 'defs' that cause jsdom warnings
vi.mock('recharts', () => ({
  ResponsiveContainer: ({ children }) => <div data-testid="responsive-container">{children}</div>,
  LineChart: ({ children, data }) => {
    // Filter out raw string-type elements (like 'defs') that cause SVG warnings in jsdom
    const filteredChildren = React.Children.toArray(children).filter(
      child => child && typeof child.type !== 'string'
    )
    return (
      <div data-testid="line-chart" data-length={data?.length}>
        {filteredChildren}
      </div>
    )
  },
  AreaChart: ({ children, data }) => {
    // Filter out raw string-type elements (like 'defs') that cause SVG warnings in jsdom
    const filteredChildren = React.Children.toArray(children).filter(
      child => child && typeof child.type !== 'string'
    )
    return (
      <div data-testid="area-chart" data-length={data?.length}>
        {filteredChildren}
      </div>
    )
  },
  Line: ({ dataKey, name, stroke }) => (
    <div data-testid={`line-${dataKey}`} data-name={name} data-stroke={stroke} />
  ),
  Area: ({ dataKey, name, stroke }) => (
    <div data-testid={`area-${dataKey}`} data-name={name} data-stroke={stroke} />
  ),
  XAxis: ({ dataKey }) => <div data-testid="x-axis" data-key={dataKey} />,
  YAxis: () => <div data-testid="y-axis" />,
  CartesianGrid: () => <div data-testid="cartesian-grid" />,
  Tooltip: () => <div data-testid="tooltip" />,
  Legend: () => <div data-testid="legend" />,
}))

// Note: framer-motion is globally mocked in src/test/setup.js

describe('LearningChart', () => {
  const mockData = [
    { date: '2024-01-01', cardsReviewed: 10, practiceTime: 15 },
    { date: '2024-01-02', cardsReviewed: 15, practiceTime: 20 },
    { date: '2024-01-03', cardsReviewed: 8, practiceTime: 12 },
  ]

  it('renders with default props', () => {
    render(<LearningChart />)
    expect(screen.getByTestId('responsive-container')).toBeInTheDocument()
  })

  it('renders area chart by default', () => {
    render(<LearningChart data={mockData} />)
    expect(screen.getByTestId('area-chart')).toBeInTheDocument()
  })

  it('renders line chart when type is "line"', () => {
    render(<LearningChart data={mockData} type="line" />)
    expect(screen.getByTestId('line-chart')).toBeInTheDocument()
  })

  it('renders default metrics (cardsReviewed and practiceTime)', () => {
    render(<LearningChart data={mockData} />)
    expect(screen.getByTestId('area-cardsReviewed')).toBeInTheDocument()
    expect(screen.getByTestId('area-practiceTime')).toBeInTheDocument()
  })

  it('renders specified metrics', () => {
    render(<LearningChart data={mockData} metrics={['retention', 'newCards']} />)
    expect(screen.getByTestId('area-retention')).toBeInTheDocument()
    expect(screen.getByTestId('area-newCards')).toBeInTheDocument()
  })

  it('renders lines when type is "line"', () => {
    render(<LearningChart data={mockData} type="line" metrics={['cardsReviewed']} />)
    expect(screen.getByTestId('line-cardsReviewed')).toBeInTheDocument()
  })

  it('renders with custom height', () => {
    const { container } = render(<LearningChart data={mockData} height={500} />)
    expect(container.querySelector('.w-full')).toBeInTheDocument()
  })

  it('renders legend by default', () => {
    render(<LearningChart data={mockData} showLegend={true} />)
    expect(screen.getByTestId('legend')).toBeInTheDocument()
  })

  it('renders x-axis with date dataKey', () => {
    render(<LearningChart data={mockData} />)
    expect(screen.getByTestId('x-axis')).toHaveAttribute('data-key', 'date')
  })

  it('renders y-axis', () => {
    render(<LearningChart data={mockData} />)
    expect(screen.getByTestId('y-axis')).toBeInTheDocument()
  })

  it('renders tooltip', () => {
    render(<LearningChart data={mockData} />)
    expect(screen.getByTestId('tooltip')).toBeInTheDocument()
  })

  it('applies custom className', () => {
    const { container } = render(<LearningChart data={mockData} className="custom-class" />)
    expect(container.querySelector('.custom-class')).toBeInTheDocument()
  })

  it('handles empty data array', () => {
    render(<LearningChart data={[]} />)
    expect(screen.getByTestId('area-chart')).toHaveAttribute('data-length', '0')
  })

  it('ignores invalid metric keys', () => {
    render(<LearningChart data={mockData} metrics={['invalidMetric']} />)
    // Invalid metrics should not render anything
    expect(screen.queryByTestId('area-invalidMetric')).not.toBeInTheDocument()
  })
})

describe('LearningSparkline', () => {
  const mockData = [
    { value: 10 },
    { value: 15 },
    { value: 8 },
    { value: 20 },
  ]

  it('renders with default props', () => {
    render(<LearningSparkline />)
    expect(screen.getByTestId('responsive-container')).toBeInTheDocument()
  })

  it('renders area chart', () => {
    render(<LearningSparkline data={mockData} />)
    expect(screen.getByTestId('area-chart')).toBeInTheDocument()
  })

  it('renders with custom dataKey', () => {
    render(<LearningSparkline data={mockData} dataKey="customValue" />)
    expect(screen.getByTestId('area-customValue')).toBeInTheDocument()
  })

  it('renders with custom color', () => {
    render(<LearningSparkline data={mockData} color="#ff0000" />)
    expect(screen.getByTestId('area-value')).toHaveAttribute('data-stroke', '#ff0000')
  })

  it('applies custom className', () => {
    const { container } = render(<LearningSparkline data={mockData} className="sparkline-class" />)
    expect(container.querySelector('.sparkline-class')).toBeInTheDocument()
  })

  it('handles empty data', () => {
    render(<LearningSparkline data={[]} />)
    expect(screen.getByTestId('area-chart')).toHaveAttribute('data-length', '0')
  })
})
