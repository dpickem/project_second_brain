/**
 * EmptyState Component Tests
 */

import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '../../test/test-utils'
import {
  EmptyState,
  SearchEmptyState,
  ErrorEmptyState,
  NoDataEmptyState,
  ComingSoonEmptyState,
  NoNotesEmptyState,
  NoDueCardsEmptyState,
  NoExercisesEmptyState,
  NoConnectionsEmptyState,
} from './EmptyState'

// Mock framer-motion
vi.mock('framer-motion', async () => {
  const actual = await vi.importActual('framer-motion')
  return {
    ...actual,
    motion: {
      div: ({ children, variants, initial, animate, ...props }) => (
        <div {...props}>{children}</div>
      ),
      button: ({ children, ...props }) => <button {...props}>{children}</button>,
    },
  }
})

describe('EmptyState', () => {
  describe('Rendering', () => {
    it('should render title', () => {
      render(<EmptyState title="No items found" />)
      
      expect(screen.getByText('No items found')).toBeInTheDocument()
    })

    it('should render description', () => {
      render(<EmptyState description="Add some items to get started" />)
      
      expect(screen.getByText('Add some items to get started')).toBeInTheDocument()
    })

    it('should render emoji icon', () => {
      render(<EmptyState icon="📭" />)
      
      expect(screen.getByText('📭')).toBeInTheDocument()
    })

    it('should render custom icon element', () => {
      const CustomIcon = () => <svg data-testid="custom-icon" />
      render(<EmptyState icon={<CustomIcon />} />)
      
      expect(screen.getByTestId('custom-icon')).toBeInTheDocument()
    })
  })

  describe('Actions', () => {
    it('should render action button', () => {
      const handleAction = vi.fn()
      render(
        <EmptyState
          title="No items"
          onAction={handleAction}
          actionLabel="Add Item"
        />
      )
      
      expect(screen.getByRole('button', { name: 'Add Item' })).toBeInTheDocument()
    })

    it('should call onAction when button clicked', () => {
      const handleAction = vi.fn()
      render(
        <EmptyState
          title="No items"
          onAction={handleAction}
          actionLabel="Add Item"
        />
      )
      
      fireEvent.click(screen.getByRole('button', { name: 'Add Item' }))
      
      expect(handleAction).toHaveBeenCalled()
    })

    it('should render secondary action button', () => {
      const handleSecondary = vi.fn()
      render(
        <EmptyState
          title="No items"
          onAction={() => {}}
          actionLabel="Primary"
          onSecondaryAction={handleSecondary}
          secondaryActionLabel="Secondary"
        />
      )
      
      expect(screen.getByRole('button', { name: 'Secondary' })).toBeInTheDocument()
    })

    it('should use default labels when not provided', () => {
      render(
        <EmptyState
          title="No items"
          onAction={() => {}}
          onSecondaryAction={() => {}}
        />
      )
      
      expect(screen.getByRole('button', { name: 'Take Action' })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: 'Learn More' })).toBeInTheDocument()
    })
  })

  describe('Variants', () => {
    it('should apply card variant styles', () => {
      const { container } = render(<EmptyState variant="card" title="Card" />)
      
      expect(container.querySelector('.bg-bg-elevated')).toBeInTheDocument()
    })

    it('should apply default variant styles', () => {
      const { container } = render(<EmptyState variant="default" title="Default" />)
      
      expect(container.querySelector('.bg-transparent')).toBeInTheDocument()
    })

    it('should apply minimal variant styles', () => {
      const { container } = render(<EmptyState variant="minimal" title="Minimal" />)
      
      expect(container.querySelector('.py-4')).toBeInTheDocument()
    })
  })

  describe('Sizes', () => {
    it('should apply sm size', () => {
      render(<EmptyState size="sm" title="Small" />)
      
      expect(screen.getByText('Small')).toHaveClass('text-lg')
    })

    it('should apply md size', () => {
      render(<EmptyState size="md" title="Medium" />)
      
      expect(screen.getByText('Medium')).toHaveClass('text-xl')
    })

    it('should apply lg size', () => {
      render(<EmptyState size="lg" title="Large" />)
      
      expect(screen.getByText('Large')).toHaveClass('text-2xl')
    })
  })
})

describe('SearchEmptyState', () => {
  it('should show search query in title', () => {
    render(<SearchEmptyState query="test search" />)
    
    expect(screen.getByText('No results for "test search"')).toBeInTheDocument()
  })

  it('should show clear button when onClear provided', () => {
    const handleClear = vi.fn()
    render(<SearchEmptyState query="test" onClear={handleClear} />)
    
    expect(screen.getByRole('button', { name: 'Clear Search' })).toBeInTheDocument()
  })

  it('should call onClear when clear button clicked', () => {
    const handleClear = vi.fn()
    render(<SearchEmptyState query="test" onClear={handleClear} />)
    
    fireEvent.click(screen.getByRole('button', { name: 'Clear Search' }))
    
    expect(handleClear).toHaveBeenCalled()
  })
})

describe('ErrorEmptyState', () => {
  it('should show default error title', () => {
    render(<ErrorEmptyState />)
    
    expect(screen.getByText('Something went wrong')).toBeInTheDocument()
  })

  it('should show custom error title', () => {
    render(<ErrorEmptyState title="Connection failed" />)
    
    expect(screen.getByText('Connection failed')).toBeInTheDocument()
  })

  it('should show retry button', () => {
    render(<ErrorEmptyState onRetry={() => {}} />)
    
    expect(screen.getByRole('button', { name: 'Try Again' })).toBeInTheDocument()
  })

  it('should call onRetry when retry button clicked', () => {
    const handleRetry = vi.fn()
    render(<ErrorEmptyState onRetry={handleRetry} />)
    
    fireEvent.click(screen.getByRole('button', { name: 'Try Again' }))
    
    expect(handleRetry).toHaveBeenCalled()
  })
})

describe('NoDataEmptyState', () => {
  it('should show default title and description', () => {
    render(<NoDataEmptyState />)
    
    expect(screen.getByText('No data yet')).toBeInTheDocument()
    expect(screen.getByText('Start adding content to see it appear here.')).toBeInTheDocument()
  })

  it('should show custom title', () => {
    render(<NoDataEmptyState title="Empty collection" />)
    
    expect(screen.getByText('Empty collection')).toBeInTheDocument()
  })

  it('should show action button', () => {
    render(<NoDataEmptyState onAction={() => {}} />)
    
    expect(screen.getByRole('button', { name: 'Get Started' })).toBeInTheDocument()
  })
})

describe('ComingSoonEmptyState', () => {
  it('should show coming soon title', () => {
    render(<ComingSoonEmptyState />)
    
    expect(screen.getByText('Coming Soon')).toBeInTheDocument()
  })

  it('should show feature name in description', () => {
    render(<ComingSoonEmptyState feature="Dark mode" />)
    
    expect(screen.getByText('Dark mode is currently under development. Check back soon!')).toBeInTheDocument()
  })
})

describe('NoNotesEmptyState', () => {
  it('should show no notes message', () => {
    render(<NoNotesEmptyState />)
    
    expect(screen.getByText('No notes yet')).toBeInTheDocument()
  })

  it('should show capture button', () => {
    render(<NoNotesEmptyState onCapture={() => {}} />)
    
    expect(screen.getByRole('button', { name: 'Capture Note' })).toBeInTheDocument()
  })
})

describe('NoDueCardsEmptyState', () => {
  it('should show all caught up message', () => {
    render(<NoDueCardsEmptyState />)
    
    expect(screen.getByText('All caught up!')).toBeInTheDocument()
  })

  it('should show practice button', () => {
    render(<NoDueCardsEmptyState onPractice={() => {}} />)
    
    expect(screen.getByRole('button', { name: 'Start Practice Session' })).toBeInTheDocument()
  })
})

describe('NoExercisesEmptyState', () => {
  it('should show no exercises message', () => {
    render(<NoExercisesEmptyState />)
    
    expect(screen.getByText('No exercises available')).toBeInTheDocument()
  })
})

describe('NoConnectionsEmptyState', () => {
  it('should show no connections message', () => {
    render(<NoConnectionsEmptyState />)
    
    expect(screen.getByText('No connections yet')).toBeInTheDocument()
  })
})
