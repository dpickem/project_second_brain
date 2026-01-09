/**
 * Button Component Tests
 */

import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '../../test/test-utils'
import { Button, IconButton } from './Button'

// Disable framer-motion for testing
vi.mock('framer-motion', async () => {
  const actual = await vi.importActual('framer-motion')
  return {
    ...actual,
    motion: {
      button: ({ children, whileHover, whileTap, variants, initial, ...props }) => (
        <button {...props}>{children}</button>
      ),
      div: ({ children, ...props }) => <div {...props}>{children}</div>,
    },
  }
})

describe('Button', () => {
  describe('Rendering', () => {
    it('should render with children', () => {
      render(<Button>Click me</Button>)
      
      expect(screen.getByRole('button')).toHaveTextContent('Click me')
    })

    it('should render with default variant and size', () => {
      render(<Button>Default</Button>)
      
      const button = screen.getByRole('button')
      expect(button).toHaveClass('bg-gradient-to-r') // primary gradient
      expect(button).toHaveClass('px-4', 'py-2') // md size
    })
  })

  describe('Variants', () => {
    it('should apply primary variant styles', () => {
      render(<Button variant="primary">Primary</Button>)
      
      expect(screen.getByRole('button')).toHaveClass('from-indigo-600')
    })

    it('should apply secondary variant styles', () => {
      render(<Button variant="secondary">Secondary</Button>)
      
      expect(screen.getByRole('button')).toHaveClass('bg-slate-700')
    })

    it('should apply ghost variant styles', () => {
      render(<Button variant="ghost">Ghost</Button>)
      
      expect(screen.getByRole('button')).toHaveClass('bg-transparent')
    })

    it('should apply outline variant styles', () => {
      render(<Button variant="outline">Outline</Button>)
      
      expect(screen.getByRole('button')).toHaveClass('border-indigo-500/50')
    })

    it('should apply danger variant styles', () => {
      render(<Button variant="danger">Danger</Button>)
      
      expect(screen.getByRole('button')).toHaveClass('bg-red-600')
    })

    it('should apply success variant styles', () => {
      render(<Button variant="success">Success</Button>)
      
      expect(screen.getByRole('button')).toHaveClass('bg-emerald-600')
    })
  })

  describe('Sizes', () => {
    it('should apply xs size', () => {
      render(<Button size="xs">Extra Small</Button>)
      
      expect(screen.getByRole('button')).toHaveClass('px-2.5', 'py-1', 'text-xs')
    })

    it('should apply sm size', () => {
      render(<Button size="sm">Small</Button>)
      
      expect(screen.getByRole('button')).toHaveClass('px-3', 'py-1.5', 'text-sm')
    })

    it('should apply md size', () => {
      render(<Button size="md">Medium</Button>)
      
      expect(screen.getByRole('button')).toHaveClass('px-4', 'py-2')
    })

    it('should apply lg size', () => {
      render(<Button size="lg">Large</Button>)
      
      expect(screen.getByRole('button')).toHaveClass('px-6', 'py-3', 'text-base')
    })

    it('should apply xl size', () => {
      render(<Button size="xl">Extra Large</Button>)
      
      expect(screen.getByRole('button')).toHaveClass('px-8', 'py-4', 'text-lg')
    })
  })

  describe('States', () => {
    it('should handle disabled state', () => {
      render(<Button disabled>Disabled</Button>)
      
      expect(screen.getByRole('button')).toBeDisabled()
    })

    it('should handle loading state', () => {
      render(<Button loading>Loading</Button>)
      
      const button = screen.getByRole('button')
      expect(button).toBeDisabled()
      expect(button.querySelector('.animate-spin')).toBeInTheDocument()
    })

    it('should apply full width class', () => {
      render(<Button fullWidth>Full Width</Button>)
      
      expect(screen.getByRole('button')).toHaveClass('w-full')
    })
  })

  describe('Icons', () => {
    const MockIcon = () => <svg data-testid="mock-icon" />

    it('should render icon on the left by default', () => {
      render(<Button icon={<MockIcon />}>With Icon</Button>)
      
      expect(screen.getByTestId('mock-icon')).toBeInTheDocument()
    })

    it('should render icon on the right when specified', () => {
      render(<Button icon={<MockIcon />} iconPosition="right">With Icon</Button>)
      
      expect(screen.getByTestId('mock-icon')).toBeInTheDocument()
    })

    it('should not show icon when loading', () => {
      render(<Button icon={<MockIcon />} loading>Loading</Button>)
      
      expect(screen.queryByTestId('mock-icon')).not.toBeInTheDocument()
      expect(screen.getByRole('button').querySelector('.animate-spin')).toBeInTheDocument()
    })
  })

  describe('Events', () => {
    it('should call onClick when clicked', () => {
      const handleClick = vi.fn()
      render(<Button onClick={handleClick}>Click me</Button>)
      
      fireEvent.click(screen.getByRole('button'))
      
      expect(handleClick).toHaveBeenCalledTimes(1)
    })

    it('should not call onClick when disabled', () => {
      const handleClick = vi.fn()
      render(<Button onClick={handleClick} disabled>Click me</Button>)
      
      fireEvent.click(screen.getByRole('button'))
      
      expect(handleClick).not.toHaveBeenCalled()
    })
  })

  describe('Custom class', () => {
    it('should apply custom className', () => {
      render(<Button className="custom-class">Custom</Button>)
      
      expect(screen.getByRole('button')).toHaveClass('custom-class')
    })
  })
})

describe('IconButton', () => {
  const MockIcon = () => <svg data-testid="mock-icon" />

  it('should render with icon', () => {
    render(<IconButton icon={<MockIcon />} label="Icon button" />)
    
    expect(screen.getByTestId('mock-icon')).toBeInTheDocument()
  })

  it('should have aria-label for accessibility', () => {
    render(<IconButton icon={<MockIcon />} label="Icon button" />)
    
    expect(screen.getByRole('button')).toHaveAttribute('aria-label', 'Icon button')
  })

  it('should have title attribute', () => {
    render(<IconButton icon={<MockIcon />} label="Icon button" />)
    
    expect(screen.getByRole('button')).toHaveAttribute('title', 'Icon button')
  })

  it('should show spinner when loading', () => {
    render(<IconButton icon={<MockIcon />} label="Loading" loading />)
    
    const button = screen.getByRole('button')
    expect(button).toBeDisabled()
    expect(button.querySelector('.animate-spin')).toBeInTheDocument()
    expect(screen.queryByTestId('mock-icon')).not.toBeInTheDocument()
  })

  it('should apply different sizes', () => {
    const { rerender } = render(<IconButton icon={<MockIcon />} label="Icon" size="sm" />)
    expect(screen.getByRole('button')).toHaveClass('w-8', 'h-8')

    rerender(<IconButton icon={<MockIcon />} label="Icon" size="lg" />)
    expect(screen.getByRole('button')).toHaveClass('w-12', 'h-12')
  })
})
