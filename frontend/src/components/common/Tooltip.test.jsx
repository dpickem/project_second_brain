/**
 * Tooltip Component Tests
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, fireEvent, act } from '@testing-library/react'
import { Tooltip, KeyboardShortcut, TooltipWithShortcut } from './Tooltip'

// Note: framer-motion is globally mocked in src/test/setup.js

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
    // Note: After refactoring to use portals with fixed positioning,
    // the tooltip uses transform classes instead of positioning classes
    it('applies top position transform by default', () => {
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
      // Top position uses translateY(-100%) to move above
      expect(tooltip).toHaveClass('-translate-y-full')
      expect(tooltip).toHaveClass('-translate-x-1/2')
    })

    it('applies bottom position transform', () => {
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
      // Bottom position uses translateX(-50%) to center
      expect(tooltip).toHaveClass('-translate-x-1/2')
    })

    it('applies left position transform', () => {
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
      // Left position uses translateX(-100%) to move left
      expect(tooltip).toHaveClass('-translate-x-full')
      expect(tooltip).toHaveClass('-translate-y-1/2')
    })

    it('applies right position transform', () => {
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
      // Right position uses translateY(-50%) to center vertically
      expect(tooltip).toHaveClass('-translate-y-1/2')
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

  describe('Portal Rendering', () => {
    it('renders tooltip in document.body via portal', () => {
      render(
        <div style={{ overflow: 'hidden', position: 'relative' }}>
          <Tooltip content="Portal tooltip" delay={0}>
            <button>Hover me</button>
          </Tooltip>
        </div>
      )

      const trigger = screen.getByRole('button', { name: 'Hover me' })
      fireEvent.mouseEnter(trigger)
      act(() => {
        vi.advanceTimersByTime(0)
      })

      // Tooltip should exist
      const tooltip = screen.getByRole('tooltip')
      expect(tooltip).toBeInTheDocument()
      
      // Tooltip should be in body (not inside the overflow:hidden parent)
      // This tests that the portal works correctly
      expect(document.body.querySelector('[role="tooltip"]')).toBeInTheDocument()
    })

    it('tooltip not clipped by parent overflow hidden', () => {
      const { container } = render(
        <div style={{ overflow: 'hidden', width: '100px', height: '50px' }}>
          <Tooltip content="This is a longer tooltip that would be clipped" delay={0}>
            <button>Hover</button>
          </Tooltip>
        </div>
      )

      const trigger = screen.getByRole('button', { name: 'Hover' })
      fireEvent.mouseEnter(trigger)
      act(() => {
        vi.advanceTimersByTime(0)
      })

      const tooltip = screen.getByRole('tooltip')
      
      // Tooltip should NOT be a descendant of the overflow:hidden container
      // It should be rendered in the portal (document.body)
      expect(container.contains(tooltip)).toBe(false)
      expect(document.body.contains(tooltip)).toBe(true)
    })

    it('tooltip has fixed positioning for portal', () => {
      render(
        <Tooltip content="Fixed position tooltip" delay={0}>
          <button>Hover me</button>
        </Tooltip>
      )

      const trigger = screen.getByRole('button', { name: 'Hover me' })
      fireEvent.mouseEnter(trigger)
      act(() => {
        vi.advanceTimersByTime(0)
      })

      const tooltip = screen.getByRole('tooltip')
      expect(tooltip).toHaveClass('fixed')
    })

    it('tooltip has high z-index to render above other content', () => {
      render(
        <Tooltip content="High z-index tooltip" delay={0}>
          <button>Hover me</button>
        </Tooltip>
      )

      const trigger = screen.getByRole('button', { name: 'Hover me' })
      fireEvent.mouseEnter(trigger)
      act(() => {
        vi.advanceTimersByTime(0)
      })

      const tooltip = screen.getByRole('tooltip')
      // Check for z-index class (z-[9999])
      expect(tooltip.className).toMatch(/z-\[9999\]/)
    })
  })

  describe('Arrow Rendering', () => {
    it('renders arrow pointing to correct direction for top tooltip', () => {
      render(
        <Tooltip content="Top tooltip" side="top" delay={0}>
          <button>Hover me</button>
        </Tooltip>
      )

      const trigger = screen.getByRole('button', { name: 'Hover me' })
      fireEvent.mouseEnter(trigger)
      act(() => {
        vi.advanceTimersByTime(0)
      })

      // Arrow should be at bottom for top tooltip
      const arrow = document.querySelector('.border-t-slate-700')
      expect(arrow).toBeInTheDocument()
    })

    it('renders arrow pointing to correct direction for bottom tooltip', () => {
      render(
        <Tooltip content="Bottom tooltip" side="bottom" delay={0}>
          <button>Hover me</button>
        </Tooltip>
      )

      const trigger = screen.getByRole('button', { name: 'Hover me' })
      fireEvent.mouseEnter(trigger)
      act(() => {
        vi.advanceTimersByTime(0)
      })

      // Arrow should be at top for bottom tooltip
      const arrow = document.querySelector('.border-b-slate-700')
      expect(arrow).toBeInTheDocument()
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
    // Bottom side uses center transform
    expect(tooltip).toHaveClass('-translate-x-1/2')
    expect(tooltip).toHaveClass('fixed')
  })
})
