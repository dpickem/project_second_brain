/**
 * Tooltip Component
 * 
 * Accessible tooltip with portal rendering and multiple positions.
 */

import { useState, useRef, useEffect } from 'react'
import { createPortal } from 'react-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { clsx } from 'clsx'
import { Z_INDEX } from '../../constants'

const positions = {
  top: {
    origin: 'bottom center',
    initial: { opacity: 0, y: 4, scale: 0.95 },
    animate: { opacity: 1, y: 0, scale: 1 },
    exit: { opacity: 0, y: 4, scale: 0.95 },
  },
  bottom: {
    origin: 'top center',
    initial: { opacity: 0, y: -4, scale: 0.95 },
    animate: { opacity: 1, y: 0, scale: 1 },
    exit: { opacity: 0, y: -4, scale: 0.95 },
  },
  left: {
    origin: 'right center',
    initial: { opacity: 0, x: 4, scale: 0.95 },
    animate: { opacity: 1, x: 0, scale: 1 },
    exit: { opacity: 0, x: 4, scale: 0.95 },
  },
  right: {
    origin: 'left center',
    initial: { opacity: 0, x: -4, scale: 0.95 },
    animate: { opacity: 1, x: 0, scale: 1 },
    exit: { opacity: 0, x: -4, scale: 0.95 },
  },
}

export function Tooltip({
  content,
  children,
  side = 'top',
  delay = 300,
  disabled = false,
  className,
}) {
  const [isVisible, setIsVisible] = useState(false)
  const [position, setPosition] = useState({ top: 0, left: 0 })
  const triggerRef = useRef(null)
  const timeoutRef = useRef(null)

  const updatePosition = () => {
    if (!triggerRef.current) return
    const rect = triggerRef.current.getBoundingClientRect()

    // For fixed positioning, use viewport-relative coordinates directly
    let top, left
    switch (side) {
      case 'top':
        top = rect.top - 8 // 8px gap above
        left = rect.left + rect.width / 2
        break
      case 'bottom':
        top = rect.bottom + 8
        left = rect.left + rect.width / 2
        break
      case 'left':
        top = rect.top + rect.height / 2
        left = rect.left - 8
        break
      case 'right':
        top = rect.top + rect.height / 2
        left = rect.right + 8
        break
      default:
        top = rect.top - 8
        left = rect.left + rect.width / 2
    }

    setPosition({ top, left })
  }

  const showTooltip = () => {
    if (disabled) return
    timeoutRef.current = setTimeout(() => {
      updatePosition()
      setIsVisible(true)
    }, delay)
  }

  const hideTooltip = () => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current)
    }
    setIsVisible(false)
  }

  useEffect(() => {
    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current)
      }
    }
  }, [])

  if (!content) {
    return children
  }

  const arrowStyles = {
    top: 'bottom-[-4px] left-1/2 -translate-x-1/2 border-l-transparent border-r-transparent border-b-transparent border-t-slate-700',
    bottom: 'top-[-4px] left-1/2 -translate-x-1/2 border-l-transparent border-r-transparent border-t-transparent border-b-slate-700',
    left: 'right-[-4px] top-1/2 -translate-y-1/2 border-t-transparent border-b-transparent border-r-transparent border-l-slate-700',
    right: 'left-[-4px] top-1/2 -translate-y-1/2 border-t-transparent border-b-transparent border-l-transparent border-r-slate-700',
  }

  const tooltipPositionStyles = {
    top: '-translate-x-1/2 -translate-y-full',
    bottom: '-translate-x-1/2',
    left: '-translate-x-full -translate-y-1/2',
    right: '-translate-y-1/2',
  }

  return (
    <>
      <div
        ref={triggerRef}
        onMouseEnter={showTooltip}
        onMouseLeave={hideTooltip}
        onFocus={showTooltip}
        onBlur={hideTooltip}
        className="inline-block"
      >
        {children}
      </div>

      {createPortal(
        <AnimatePresence>
          {isVisible && (
            <motion.div
              initial={positions[side].initial}
              animate={positions[side].animate}
              exit={positions[side].exit}
              transition={{ duration: 0.15 }}
              style={{ top: position.top, left: position.left, zIndex: Z_INDEX.TOOLTIP }}
              className={clsx(
                'fixed px-2 py-1 text-xs font-medium text-white bg-slate-700 rounded shadow-lg',
                'whitespace-nowrap pointer-events-none',
                tooltipPositionStyles[side],
                className
              )}
              role="tooltip"
            >
              {content}
              {/* Arrow */}
              <div
                className={clsx(
                  'absolute w-0 h-0 border-4',
                  arrowStyles[side]
                )}
              />
            </motion.div>
          )}
        </AnimatePresence>,
        document.body
      )}
    </>
  )
}

// Keyboard Shortcut Tooltip - shows a keyboard shortcut
export function KeyboardShortcut({ shortcut, className }) {
  // Parse shortcut like "⌘K" or "Ctrl+Shift+P"
  const parts = shortcut.split('+')

  return (
    <span className={clsx('inline-flex items-center gap-0.5', className)}>
      {parts.map((key, index) => (
        <kbd
          key={index}
          className="px-1.5 py-0.5 text-xs font-medium bg-slate-700 text-slate-300 rounded border border-slate-600"
        >
          {key}
        </kbd>
      ))}
    </span>
  )
}

// Combined tooltip with keyboard shortcut
export function TooltipWithShortcut({ label, shortcut, children, ...props }) {
  return (
    <Tooltip
      content={
        <span className="flex items-center gap-2">
          {label}
          <KeyboardShortcut shortcut={shortcut} />
        </span>
      }
      {...props}
    >
      {children}
    </Tooltip>
  )
}

export default Tooltip
