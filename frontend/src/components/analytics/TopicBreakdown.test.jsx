/**
 * TopicBreakdown Component Tests
 */

import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '../../test/test-utils'
import { TopicBreakdown } from './TopicBreakdown'

// Mock recharts components
vi.mock('recharts', () => ({
  ResponsiveContainer: ({ children }) => <div data-testid="responsive-container">{children}</div>,
  BarChart: ({ children, data, layout }) => (
    <div data-testid="bar-chart" data-length={data?.length} data-layout={layout}>
      {children}
    </div>
  ),
  Bar: ({ dataKey, children }) => (
    <div data-testid="bar" data-key={dataKey}>
      {children}
    </div>
  ),
  XAxis: ({ type, domain }) => (
    <div data-testid="x-axis" data-type={type} data-domain={domain?.join(',')} />
  ),
  YAxis: ({ type, dataKey }) => (
    <div data-testid="y-axis" data-type={type} data-key={dataKey} />
  ),
  CartesianGrid: () => <div data-testid="cartesian-grid" />,
  Tooltip: () => <div data-testid="tooltip" />,
  Cell: ({ fill }) => <div data-testid="cell" data-fill={fill} />,
}))

// Note: framer-motion is globally mocked in src/test/setup.js

describe('TopicBreakdown', () => {
  const mockData = [
    { topic: 'JavaScript', mastery: 85, cardCount: 50, dueCount: 5 },
    { topic: 'React', mastery: 70, cardCount: 30, dueCount: 3 },
    { topic: 'CSS', mastery: 55, cardCount: 25, dueCount: 8 },
    { topic: 'Node.js', mastery: 35, cardCount: 15, dueCount: 2 },
  ]

  describe('Chart Type', () => {
    it('renders bar chart by default', () => {
      render(<TopicBreakdown data={mockData} />)
      expect(screen.getByTestId('bar-chart')).toBeInTheDocument()
    })

    it('renders bar chart when type is "chart"', () => {
      render(<TopicBreakdown data={mockData} type="chart" />)
      expect(screen.getByTestId('bar-chart')).toBeInTheDocument()
    })

    it('renders vertical bar chart (horizontal bars)', () => {
      render(<TopicBreakdown data={mockData} />)
      expect(screen.getByTestId('bar-chart')).toHaveAttribute('data-layout', 'vertical')
    })

    it('renders list view when type is "list"', () => {
      render(<TopicBreakdown data={mockData} type="list" />)
      expect(screen.queryByTestId('bar-chart')).not.toBeInTheDocument()
    })
  })

  describe('Chart View', () => {
    it('renders responsive container', () => {
      render(<TopicBreakdown data={mockData} />)
      expect(screen.getByTestId('responsive-container')).toBeInTheDocument()
    })

    it('renders with correct data length', () => {
      render(<TopicBreakdown data={mockData} />)
      expect(screen.getByTestId('bar-chart')).toHaveAttribute('data-length', '4')
    })

    it('renders x-axis with number type and 0-100 domain', () => {
      render(<TopicBreakdown data={mockData} />)
      const xAxis = screen.getByTestId('x-axis')
      expect(xAxis).toHaveAttribute('data-type', 'number')
      expect(xAxis).toHaveAttribute('data-domain', '0,100')
    })

    it('renders y-axis with category type and topic dataKey', () => {
      render(<TopicBreakdown data={mockData} />)
      const yAxis = screen.getByTestId('y-axis')
      expect(yAxis).toHaveAttribute('data-type', 'category')
      expect(yAxis).toHaveAttribute('data-key', 'topic')
    })

    it('renders bar with mastery dataKey', () => {
      render(<TopicBreakdown data={mockData} />)
      expect(screen.getByTestId('bar')).toHaveAttribute('data-key', 'mastery')
    })

    it('renders cells for each data point', () => {
      render(<TopicBreakdown data={mockData} />)
      const cells = screen.getAllByTestId('cell')
      expect(cells).toHaveLength(4)
    })

    it('renders tooltip', () => {
      render(<TopicBreakdown data={mockData} />)
      expect(screen.getByTestId('tooltip')).toBeInTheDocument()
    })

    it('renders cartesian grid', () => {
      render(<TopicBreakdown data={mockData} />)
      expect(screen.getByTestId('cartesian-grid')).toBeInTheDocument()
    })
  })

  describe('List View', () => {
    it('renders all topics', () => {
      render(<TopicBreakdown data={mockData} type="list" />)
      expect(screen.getByText('JavaScript')).toBeInTheDocument()
      expect(screen.getByText('React')).toBeInTheDocument()
      expect(screen.getByText('CSS')).toBeInTheDocument()
      expect(screen.getByText('Node.js')).toBeInTheDocument()
    })

    it('displays item count for each topic', () => {
      // Default viewMode is 'combined', which shows "items" instead of "cards"
      render(<TopicBreakdown data={mockData} type="list" />)
      expect(screen.getByText('50 items')).toBeInTheDocument()
      expect(screen.getByText('30 items')).toBeInTheDocument()
      expect(screen.getByText('25 items')).toBeInTheDocument()
      expect(screen.getByText('15 items')).toBeInTheDocument()
    })

    it('displays mastery percentage for each topic', () => {
      render(<TopicBreakdown data={mockData} type="list" />)
      expect(screen.getByText('85%')).toBeInTheDocument()
      expect(screen.getByText('70%')).toBeInTheDocument()
      expect(screen.getByText('55%')).toBeInTheDocument()
      expect(screen.getByText('35%')).toBeInTheDocument()
    })

    it('displays due badges for topics with due cards', () => {
      render(<TopicBreakdown data={mockData} type="list" />)
      // Due badges show dueCount
      expect(screen.getByText('5')).toBeInTheDocument()
      expect(screen.getByText('3')).toBeInTheDocument()
      expect(screen.getByText('8')).toBeInTheDocument()
      expect(screen.getByText('2')).toBeInTheDocument()
    })

    it('does not show badge when dueCount is 0', () => {
      const dataWithNoDue = [
        { topic: 'Test', mastery: 80, cardCount: 10, dueCount: 0 },
      ]
      render(<TopicBreakdown data={dataWithNoDue} type="list" />)
      // Badge shouldn't appear for 0 due
      expect(screen.queryByText('0')).not.toBeInTheDocument()
    })

    it('sorts topics by mastery in descending order', () => {
      render(<TopicBreakdown data={mockData} type="list" />)
      const topics = screen.getAllByText(/JavaScript|React|CSS|Node\.js/)
      // JavaScript (85%) should be first, Node.js (35%) should be last
      expect(topics[0]).toHaveTextContent('JavaScript')
      expect(topics[topics.length - 1]).toHaveTextContent('Node.js')
    })
  })

  describe('Empty State', () => {
    it('shows empty state message for chart when no data', () => {
      // Component shows empty state instead of chart when data is empty
      render(<TopicBreakdown data={[]} />)
      expect(screen.getByText('No progress data yet')).toBeInTheDocument()
      expect(screen.getByText('📈')).toBeInTheDocument()
    })

    it('shows empty state message for list when no data', () => {
      // Component shows empty state instead of list when data is empty
      render(<TopicBreakdown data={[]} type="list" />)
      expect(screen.getByText('No progress data yet')).toBeInTheDocument()
    })
  })

  describe('Styling', () => {
    it('applies custom className', () => {
      const { container } = render(
        <TopicBreakdown data={mockData} className="custom-breakdown" />
      )
      expect(container.querySelector('.custom-breakdown')).toBeInTheDocument()
    })

    it('applies custom className in list view', () => {
      const { container } = render(
        <TopicBreakdown data={mockData} type="list" className="custom-list" />
      )
      expect(container.querySelector('.custom-list')).toBeInTheDocument()
    })
  })
})
