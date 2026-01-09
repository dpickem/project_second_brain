/**
 * Tooltip Component Tests
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Tooltip, KeyboardShortcut, TooltipWithShortcut } from './Tooltip'

// Mock framer-motion to avoid animation issues in tests
vi.mock('framer-motion', () => ({
  motion: {
    div: ({ children, ...props }) => <div {...props}>{children}</div>,
  },
  AnimatePresence: ({ children }) => <>{children}</>,
}))

describe('Tooltip', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  describe('Basic Rendering', () => {
    it('renders children without tooltip when no content', () => {
      render(
        <Tooltip content="">
          <button>Hover me</button>
        </Tooltip>
      )

      expect(screen.getByRole('button', { name: 'Hover me' })).toBeInTheDocument()
      expect(screen.queryByRole('tooltip')).not.toBeInTheDocument()
    })

    it('renders children with tooltip trigger', () => {
      render(
        <Tooltip content="Tooltip text">
          <button>Hover me</button>
        </Tooltip>
      )

      expect(screen.getByRole('button', { name: 'Hover me' })).toBeInTheDocument()
    })

    it('does not show tooltip initially', () => {
      render(
        <Tooltip content="Tooltip text">
          <button>Hover me</button>
        </Tooltip>
      )

      expect(screen.queryByRole('tooltip')).not.toBeInTheDocument()
    })
  })

  describe('Mouse Interactions', () => {
    it('shows tooltip on mouse enter after delay', async () => {
      render(
        <Tooltip content="Tooltip text" delay={300}>
          <button>Hover me</button>
        </Tooltip>
      )

      const trigger = screen.getByRole('button', { name: 'Hover me' })
      fireEvent.mouseEnter(trigger)

      // Should not show immediately
      expect(screen.queryByRole('tooltip')).not.toBeInTheDocument()

      // Advance timers past the delay
      act(() => {
        vi.advanceTimersByTime(300)
      })

      // Now tooltip should be visible
      expect(screen.getByRole('tooltip')).toBeInTheDocument()
      expect(screen.getByText('Tooltip text')).toBeInTheDocument()
    })

    it('hides tooltip on mouse leave', async () => {
      render(
        <Tooltip content="Tooltip text" delay={100}>
          <button>Hover me</button>
        </Tooltip>
      )

      const trigger = screen.getByRole('button', { name: 'Hover me' })
      
      // Show tooltip
      fireEvent.mouseEnter(trigger)
      act(() => {
        vi.advanceTimersByTime(100)
      })
      expect(screen.getByRole('tooltip')).toBeInTheDocument()

      // Hide tooltip
      fireEvent.mouseLeave(trigger)
      expect(screen.queryByRole('tooltip')).not.toBeInTheDocument()
    })

    it('cancels tooltip if mouse leaves before delay', () => {
      render(
        <Tooltip content="Tooltip text" delay={500}>
          <button>Hover me</button>
        </Tooltip>
      )

      const trigger = screen.getByRole('button', { name: 'Hover me' })
      
      fireEvent.mouseEnter(trigger)
      
      // Leave before delay completes
      act(() => {
        vi.advanceTimersByTime(200)
      })
      fireEvent.mouseLeave(trigger)
      
      // Finish the original delay time
      act(() => {
        vi.advanceTimersByTime(300)
      })

      // Tooltip should never have appeared
      expect(screen.queryByRole('tooltip')).not.toBeInTheDocument()
    })
  })

  describe('Focus Interactions', () => {
    it('shows tooltip on focus', () => {
      render(
        <Tooltip content="Tooltip text" delay={100}>
          <button>Focus me</button>
        </Tooltip>
      )

      const trigger = screen.getByRole('button', { name: 'Focus me' })
      fireEvent.focus(trigger)

      act(() => {
        vi.advanceTimersByTime(100)
      })

      expect(screen.getByRole('tooltip')).toBeInTheDocument()
    })

    it('hides tooltip on blur', () => {
      render(
        <Tooltip content="Tooltip text" delay={100}>
          <button>Focus me</button>
        </Tooltip>
      )

      const trigger = screen.getByRole('button', { name: 'Focus me' })
      
      // Show tooltip
      fireEvent.focus(trigger)
      act(() => {
        vi.advanceTimersByTime(100)
      })
      expect(screen.getByRole('tooltip')).toBeInTheDocument()

      // Hide tooltip
      fireEvent.blur(trigger)
      expect(screen.queryByRole('tooltip')).not.toBeInTheDocument()
    })
  })

  describe('Disabled State', () => {
    it('does not show tooltip when disabled', () => {
      render(
        <Tooltip content="Tooltip text" delay={100} disabled>
          <button>Hover me</button>
        </Tooltip>
      )

      const trigger = screen.getByRole('button', { name: 'Hover me' })
      fireEvent.mouseEnter(trigger)

      act(() => {
        vi.advanceTimersByTime(100)
      })

      expect(screen.queryByRole('tooltip')).not.toBeInTheDocument()
    })
  })

  describe('Positioning', () => {
    it('applies top position classes by default', () => {
      render(
        <Tooltip content="Tooltip text" delay={0}>
          <button>Hover me</button>
        </Tooltip>
      )

      const trigger = screen.getByRole('button', { name: 'Hover me' })
      fireEvent.mouseEnter(trigger)
      act(() => {
        vi.advanceTimersByTime(0)
      })

      const tooltip = screen.getByRole('tooltip')
      expect(tooltip).toHaveClass('bottom-full')
    })

    it('applies bottom position classes', () => {
      render(
        <Tooltip content="Tooltip text" side="bottom" delay={0}>
          <button>Hover me</button>
        </Tooltip>
      )

      const trigger = screen.getByRole('button', { name: 'Hover me' })
      fireEvent.mouseEnter(trigger)
      act(() => {
        vi.advanceTimersByTime(0)
      })

      const tooltip = screen.getByRole('tooltip')
      expect(tooltip).toHaveClass('top-full')
    })

    it('applies left position classes', () => {
      render(
        <Tooltip content="Tooltip text" side="left" delay={0}>
          <button>Hover me</button>
        </Tooltip>
      )

      const trigger = screen.getByRole('button', { name: 'Hover me' })
      fireEvent.mouseEnter(trigger)
      act(() => {
        vi.advanceTimersByTime(0)
      })

      const tooltip = screen.getByRole('tooltip')
      expect(tooltip).toHaveClass('right-full')
    })

    it('applies right position classes', () => {
      render(
        <Tooltip content="Tooltip text" side="right" delay={0}>
          <button>Hover me</button>
        </Tooltip>
      )

      const trigger = screen.getByRole('button', { name: 'Hover me' })
      fireEvent.mouseEnter(trigger)
      act(() => {
        vi.advanceTimersByTime(0)
      })

      const tooltip = screen.getByRole('tooltip')
      expect(tooltip).toHaveClass('left-full')
    })
  })

  describe('Custom className', () => {
    it('applies custom className to tooltip', () => {
      render(
        <Tooltip content="Tooltip text" className="custom-class" delay={0}>
          <button>Hover me</button>
        </Tooltip>
      )

      const trigger = screen.getByRole('button', { name: 'Hover me' })
      fireEvent.mouseEnter(trigger)
      act(() => {
        vi.advanceTimersByTime(0)
      })

      const tooltip = screen.getByRole('tooltip')
      expect(tooltip).toHaveClass('custom-class')
    })
  })

  describe('Cleanup', () => {
    it('clears timeout on unmount', () => {
      const clearTimeoutSpy = vi.spyOn(global, 'clearTimeout')
      
      const { unmount } = render(
        <Tooltip content="Tooltip text" delay={1000}>
          <button>Hover me</button>
        </Tooltip>
      )

      const trigger = screen.getByRole('button', { name: 'Hover me' })
      fireEvent.mouseEnter(trigger)

      unmount()

      expect(clearTimeoutSpy).toHaveBeenCalled()
      clearTimeoutSpy.mockRestore()
    })
  })
})

describe('KeyboardShortcut', () => {
  it('renders single key shortcut', () => {
    render(<KeyboardShortcut shortcut="K" />)
    
    expect(screen.getByText('K')).toBeInTheDocument()
  })

  it('renders multi-key shortcut', () => {
    render(<KeyboardShortcut shortcut="Ctrl+Shift+P" />)
    
    expect(screen.getByText('Ctrl')).toBeInTheDocument()
    expect(screen.getByText('Shift')).toBeInTheDocument()
    expect(screen.getByText('P')).toBeInTheDocument()
  })

  it('renders each key in a kbd element', () => {
    render(<KeyboardShortcut shortcut="Ctrl+K" />)
    
    const kbdElements = screen.getAllByText(/Ctrl|K/)
    kbdElements.forEach(el => {
      expect(el.tagName).toBe('KBD')
    })
  })

  it('applies custom className', () => {
    const { container } = render(
      <KeyboardShortcut shortcut="K" className="custom-class" />
    )
    
    expect(container.firstChild).toHaveClass('custom-class')
  })
})

describe('TooltipWithShortcut', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('renders label and shortcut in tooltip', () => {
    render(
      <TooltipWithShortcut label="Search" shortcut="⌘K" delay={0}>
        <button>Search</button>
      </TooltipWithShortcut>
    )

    const trigger = screen.getByRole('button', { name: 'Search' })
    fireEvent.mouseEnter(trigger)
    act(() => {
      vi.advanceTimersByTime(0)
    })

    expect(screen.getByText('Search', { selector: 'span > *:first-child, span' })).toBeInTheDocument()
    expect(screen.getByText('⌘K')).toBeInTheDocument()
  })

  it('passes through additional props to Tooltip', () => {
    render(
      <TooltipWithShortcut label="Help" shortcut="?" side="bottom" delay={0}>
        <button>Help</button>
      </TooltipWithShortcut>
    )

    const trigger = screen.getByRole('button', { name: 'Help' })
    fireEvent.mouseEnter(trigger)
    act(() => {
      vi.advanceTimersByTime(0)
    })

    const tooltip = screen.getByRole('tooltip')
    expect(tooltip).toHaveClass('top-full')
  })
})
