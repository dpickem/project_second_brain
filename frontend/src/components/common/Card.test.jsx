/**
 * Card Component Tests
 */

import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '../../test/test-utils'
import { 
  Card, 
  CardHeader, 
  CardTitle, 
  CardDescription, 
  CardContent, 
  CardFooter, 
  StatsCard 
} from './Card'

// Disable framer-motion for testing
vi.mock('framer-motion', async () => {
  const actual = await vi.importActual('framer-motion')
  return {
    ...actual,
    motion: {
      button: ({ children, className, ...props }) => (
        <button className={className} {...props}>{children}</button>
      ),
      div: ({ children, className, ...props }) => (
        <div className={className} {...props}>{children}</div>
      ),
    },
  }
})

describe('Card', () => {
  describe('Rendering', () => {
    it('should render with children', () => {
      render(<Card>Card content</Card>)
      
      expect(screen.getByText('Card content')).toBeInTheDocument()
    })
  })

  describe('Interactive', () => {
    it('should handle onClick', () => {
      const handleClick = vi.fn()
      render(<Card onClick={handleClick}>Clickable</Card>)
      
      // With onClick, the card becomes a button
      fireEvent.click(screen.getByRole('button'))
      
      expect(handleClick).toHaveBeenCalledTimes(1)
    })
  })

  describe('Custom class', () => {
    it('should apply custom className', () => {
      const { container } = render(<Card className="custom-card">Custom</Card>)
      
      expect(container.querySelector('.custom-card')).toBeInTheDocument()
    })
  })
})

describe('CardHeader', () => {
  it('should render with children', () => {
    render(<CardHeader>Header content</CardHeader>)
    
    expect(screen.getByText('Header content')).toBeInTheDocument()
  })

  it('should apply flex styles', () => {
    render(<CardHeader>Header</CardHeader>)
    
    expect(screen.getByText('Header')).toHaveClass('flex', 'items-center', 'justify-between')
  })

  it('should apply custom className', () => {
    render(<CardHeader className="custom-header">Header</CardHeader>)
    
    expect(screen.getByText('Header')).toHaveClass('custom-header')
  })
})

describe('CardTitle', () => {
  it('should render as h3 by default', () => {
    render(<CardTitle>Title</CardTitle>)
    
    expect(screen.getByRole('heading', { level: 3 })).toHaveTextContent('Title')
  })

  it('should render as custom element', () => {
    render(<CardTitle as="h2">Title</CardTitle>)
    
    expect(screen.getByRole('heading', { level: 2 })).toHaveTextContent('Title')
  })

  it('should apply title styles', () => {
    render(<CardTitle>Title</CardTitle>)
    
    expect(screen.getByText('Title')).toHaveClass('text-lg', 'font-semibold')
  })
})

describe('CardDescription', () => {
  it('should render description text', () => {
    render(<CardDescription>Description text</CardDescription>)
    
    expect(screen.getByText('Description text')).toBeInTheDocument()
  })

  it('should apply description styles', () => {
    render(<CardDescription>Description</CardDescription>)
    
    expect(screen.getByText('Description')).toHaveClass('text-sm', 'text-text-secondary')
  })
})

describe('CardContent', () => {
  it('should render children', () => {
    render(<CardContent>Content</CardContent>)
    
    expect(screen.getByText('Content')).toBeInTheDocument()
  })

  it('should apply custom className', () => {
    render(<CardContent className="custom-content">Content</CardContent>)
    
    expect(screen.getByText('Content')).toHaveClass('custom-content')
  })
})

describe('CardFooter', () => {
  it('should render children', () => {
    render(<CardFooter>Footer</CardFooter>)
    
    expect(screen.getByText('Footer')).toBeInTheDocument()
  })

  it('should apply footer styles', () => {
    render(<CardFooter>Footer</CardFooter>)
    
    expect(screen.getByText('Footer')).toHaveClass('flex', 'items-center', 'gap-3', 'mt-4', 'pt-4', 'border-t')
  })
})

describe('StatsCard', () => {
  it('should render value and label', () => {
    render(<StatsCard value="42" label="Total items" />)
    
    expect(screen.getByText('42')).toBeInTheDocument()
    expect(screen.getByText('Total items')).toBeInTheDocument()
  })

  it('should render icon when provided', () => {
    const icon = <svg data-testid="stats-icon" />
    render(<StatsCard value="10" label="Count" icon={icon} />)
    
    expect(screen.getByTestId('stats-icon')).toBeInTheDocument()
  })

  it('should render upward trend', () => {
    const { container } = render(<StatsCard value="100" label="Users" trend="up" trendLabel="+10%" />)
    
    // Text is split across child nodes, check the container
    const trendSpan = container.querySelector('.text-accent-success')
    expect(trendSpan).toBeInTheDocument()
    expect(trendSpan.textContent).toContain('+10%')
    expect(trendSpan.textContent).toContain('↑')
  })

  it('should render downward trend', () => {
    const { container } = render(<StatsCard value="50" label="Sales" trend="down" trendLabel="-5%" />)
    
    const trendSpan = container.querySelector('.text-accent-danger')
    expect(trendSpan).toBeInTheDocument()
    expect(trendSpan.textContent).toContain('-5%')
    expect(trendSpan.textContent).toContain('↓')
  })

  it('should render neutral trend', () => {
    const { container } = render(<StatsCard value="75" label="Average" trend="neutral" trendLabel="0%" />)
    
    const trendSpan = container.querySelector('.text-text-muted')
    expect(trendSpan).toBeInTheDocument()
    expect(trendSpan.textContent).toContain('0%')
    expect(trendSpan.textContent).toContain('→')
  })
})
