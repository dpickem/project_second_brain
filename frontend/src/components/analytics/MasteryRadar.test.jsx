/**
 * MasteryRadar Component Tests
 */

import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '../../test/test-utils'
import { MasteryRadar, MasteryRadarMini } from './MasteryRadar'

// Mock recharts components
vi.mock('recharts', () => ({
  ResponsiveContainer: ({ children, width, height }) => (
    <div data-testid="responsive-container" style={{ width, height }}>
      {children}
    </div>
  ),
  RadarChart: ({ children, data }) => (
    <div data-testid="radar-chart" data-length={data?.length}>
      {children}
    </div>
  ),
  PolarGrid: ({ stroke }) => <div data-testid="polar-grid" data-stroke={stroke} />,
  PolarAngleAxis: ({ dataKey }) => <div data-testid="polar-angle-axis" data-key={dataKey} />,
  PolarRadiusAxis: ({ domain, angle }) => (
    <div data-testid="polar-radius-axis" data-domain={domain?.join(',')} data-angle={angle} />
  ),
  Radar: ({ dataKey, name, fill }) => (
    <div data-testid="radar" data-key={dataKey} data-name={name} data-fill={fill} />
  ),
  Tooltip: () => <div data-testid="tooltip" />,
}))

// Mock framer-motion
vi.mock('framer-motion', () => ({
  motion: {
    div: ({ children, className, ...props }) => (
      <div className={className} {...props}>
        {children}
      </div>
    ),
  },
}))

describe('MasteryRadar', () => {
  const mockData = [
    { topic: 'JavaScript', mastery: 80, cardCount: 50 },
    { topic: 'React', mastery: 70, cardCount: 30 },
    { topic: 'TypeScript', mastery: 60, cardCount: 25 },
    { topic: 'Node.js', mastery: 50, cardCount: 20 },
  ]

  it('renders with default props', () => {
    render(<MasteryRadar />)
    expect(screen.getByTestId('responsive-container')).toBeInTheDocument()
    expect(screen.getByTestId('radar-chart')).toBeInTheDocument()
  })

  it('renders radar chart with provided data', () => {
    render(<MasteryRadar data={mockData} />)
    expect(screen.getByTestId('radar-chart')).toHaveAttribute('data-length', '4')
  })

  it('provides fallback data when less than 3 data points', () => {
    const shortData = [{ topic: 'JS', mastery: 80 }]
    render(<MasteryRadar data={shortData} />)
    // Should use fallback data with 3 points
    expect(screen.getByTestId('radar-chart')).toHaveAttribute('data-length', '3')
  })

  it('renders polar grid', () => {
    render(<MasteryRadar data={mockData} />)
    expect(screen.getByTestId('polar-grid')).toBeInTheDocument()
  })

  it('renders polar angle axis with topic dataKey', () => {
    render(<MasteryRadar data={mockData} />)
    expect(screen.getByTestId('polar-angle-axis')).toHaveAttribute('data-key', 'topic')
  })

  it('renders polar radius axis with 0-100 domain', () => {
    render(<MasteryRadar data={mockData} />)
    expect(screen.getByTestId('polar-radius-axis')).toHaveAttribute('data-domain', '0,100')
  })

  it('renders radar with mastery dataKey', () => {
    render(<MasteryRadar data={mockData} />)
    const radar = screen.getByTestId('radar')
    expect(radar).toHaveAttribute('data-key', 'mastery')
    expect(radar).toHaveAttribute('data-name', 'Mastery')
  })

  it('renders tooltip', () => {
    render(<MasteryRadar data={mockData} />)
    expect(screen.getByTestId('tooltip')).toBeInTheDocument()
  })

  it('applies custom className', () => {
    const { container } = render(<MasteryRadar data={mockData} className="custom-radar" />)
    expect(container.querySelector('.custom-radar')).toBeInTheDocument()
  })

  it('handles empty data array', () => {
    render(<MasteryRadar data={[]} />)
    // Should use fallback data
    expect(screen.getByTestId('radar-chart')).toHaveAttribute('data-length', '3')
  })

  it('uses data when exactly 3 points provided', () => {
    const threePoints = [
      { topic: 'A', mastery: 50 },
      { topic: 'B', mastery: 60 },
      { topic: 'C', mastery: 70 },
    ]
    render(<MasteryRadar data={threePoints} />)
    expect(screen.getByTestId('radar-chart')).toHaveAttribute('data-length', '3')
  })
})

describe('MasteryRadarMini', () => {
  const mockData = [
    { topic: 'A', mastery: 80 },
    { topic: 'B', mastery: 60 },
    { topic: 'C', mastery: 70 },
  ]

  it('renders with default props', () => {
    render(<MasteryRadarMini />)
    expect(screen.getByTestId('responsive-container')).toBeInTheDocument()
  })

  it('renders radar chart', () => {
    render(<MasteryRadarMini data={mockData} />)
    expect(screen.getByTestId('radar-chart')).toBeInTheDocument()
  })

  it('renders with custom size', () => {
    const { container } = render(<MasteryRadarMini data={mockData} size={200} />)
    const wrapper = container.querySelector('.relative')
    expect(wrapper).toHaveStyle({ width: '200px', height: '200px' })
  })

  it('renders with default size of 120', () => {
    const { container } = render(<MasteryRadarMini data={mockData} />)
    const wrapper = container.querySelector('.relative')
    expect(wrapper).toHaveStyle({ width: '120px', height: '120px' })
  })

  it('applies custom className', () => {
    const { container } = render(<MasteryRadarMini data={mockData} className="mini-radar" />)
    expect(container.querySelector('.mini-radar')).toBeInTheDocument()
  })

  it('renders polar grid', () => {
    render(<MasteryRadarMini data={mockData} />)
    expect(screen.getByTestId('polar-grid')).toBeInTheDocument()
  })

  it('renders radar with mastery dataKey', () => {
    render(<MasteryRadarMini data={mockData} />)
    expect(screen.getByTestId('radar')).toHaveAttribute('data-key', 'mastery')
  })

  it('handles empty data', () => {
    render(<MasteryRadarMini data={[]} />)
    expect(screen.getByTestId('radar-chart')).toHaveAttribute('data-length', '0')
  })
})
