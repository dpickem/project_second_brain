/**
 * Loading Components
 * 
 * Spinner and skeleton loaders for loading states.
 */

import { motion } from 'framer-motion'
import { clsx } from 'clsx'
import { skeletonPulse } from '../../utils/animations'

const spinnerSizes = {
  xs: 'w-3 h-3',
  sm: 'w-4 h-4',
  md: 'w-6 h-6',
  lg: 'w-8 h-8',
  xl: 'w-12 h-12',
}

// Spinner Component
export function Spinner({ size = 'md', className }) {
  return (
    <svg
      className={clsx('animate-spin', spinnerSizes[size], className)}
      fill="none"
      viewBox="0 0 24 24"
    >
      <circle
        className="opacity-25"
        cx="12"
        cy="12"
        r="10"
        stroke="currentColor"
        strokeWidth="4"
      />
      <path
        className="opacity-75"
        fill="currentColor"
        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
      />
    </svg>
  )
}

// Pulsing dots loader
export function DotsLoader({ size = 'md', className }) {
  const dotSizes = {
    sm: 'w-1.5 h-1.5',
    md: 'w-2 h-2',
    lg: 'w-3 h-3',
  }

  return (
    <div className={clsx('flex items-center gap-1', className)}>
      {[0, 1, 2].map((i) => (
        <motion.div
          key={i}
          className={clsx('rounded-full bg-current', dotSizes[size])}
          animate={{
            scale: [1, 1.2, 1],
            opacity: [0.5, 1, 0.5],
          }}
          transition={{
            duration: 0.8,
            repeat: Infinity,
            delay: i * 0.15,
          }}
        />
      ))}
    </div>
  )
}

// Skeleton base component
export function Skeleton({ className, animate = true }) {
  return (
    <motion.div
      className={clsx(
        'rounded-lg bg-slate-700/50',
        className
      )}
      animate={animate ? skeletonPulse.animate : undefined}
    />
  )
}

// Skeleton Text - for text content
export function SkeletonText({ lines = 3, className }) {
  return (
    <div className={clsx('space-y-2', className)}>
      {Array.from({ length: lines }).map((_, i) => (
        <Skeleton
          key={i}
          className={clsx(
            'h-4',
            i === lines - 1 ? 'w-3/4' : 'w-full'
          )}
        />
      ))}
    </div>
  )
}

// Skeleton Card - for card loading states
export function SkeletonCard({ className }) {
  return (
    <div className={clsx(
      'p-6 rounded-xl bg-bg-elevated border border-border-primary',
      className
    )}>
      <div className="flex items-start gap-4">
        <Skeleton className="w-12 h-12 rounded-xl flex-shrink-0" />
        <div className="flex-1 space-y-2">
          <Skeleton className="h-5 w-1/2" />
          <Skeleton className="h-4 w-3/4" />
        </div>
      </div>
      <div className="mt-4 space-y-2">
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-4 w-2/3" />
      </div>
    </div>
  )
}

// Skeleton List - for list loading states
export function SkeletonList({ items = 5, className }) {
  return (
    <div className={clsx('space-y-3', className)}>
      {Array.from({ length: items }).map((_, i) => (
        <div key={i} className="flex items-center gap-3">
          <Skeleton className="w-10 h-10 rounded-lg flex-shrink-0" />
          <div className="flex-1">
            <Skeleton className="h-4 w-1/3 mb-1" />
            <Skeleton className="h-3 w-1/2" />
          </div>
        </div>
      ))}
    </div>
  )
}

// Skeleton Avatar
export function SkeletonAvatar({ size = 'md', className }) {
  const sizes = {
    sm: 'w-8 h-8',
    md: 'w-10 h-10',
    lg: 'w-12 h-12',
    xl: 'w-16 h-16',
  }

  return (
    <Skeleton className={clsx('rounded-full', sizes[size], className)} />
  )
}

// Full Page Loader
export function PageLoader({ message = 'Loading...' }) {
  return (
    <div className="fixed inset-0 bg-bg-primary flex flex-col items-center justify-center z-50">
      <motion.div
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        className="flex flex-col items-center gap-4"
      >
        {/* Logo */}
        <div className="w-16 h-16 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-2xl flex items-center justify-center animate-pulse-slow">
          <svg
            className="w-10 h-10 text-white"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"
            />
          </svg>
        </div>
        
        <Spinner size="lg" className="text-indigo-500" />
        
        <p className="text-text-secondary text-sm">{message}</p>
      </motion.div>
    </div>
  )
}

// Inline Loader - for loading within content
export function InlineLoader({ text = 'Loading', className }) {
  return (
    <div className={clsx('flex items-center gap-2 text-text-muted', className)}>
      <Spinner size="sm" />
      <span className="text-sm">{text}</span>
    </div>
  )
}

// Button Loading State (internal use)
export function ButtonSpinner({ size = 'md' }) {
  return <Spinner size={size} className="text-current" />
}

// Skeleton Table
export function SkeletonTable({ rows = 5, columns = 4, className }) {
  return (
    <div className={clsx('space-y-2', className)}>
      {/* Header */}
      <div className="flex gap-4 pb-2 border-b border-border-primary">
        {Array.from({ length: columns }).map((_, i) => (
          <Skeleton key={i} className="h-4 flex-1" />
        ))}
      </div>
      
      {/* Rows */}
      {Array.from({ length: rows }).map((_, rowIndex) => (
        <div key={rowIndex} className="flex gap-4 py-2">
          {Array.from({ length: columns }).map((_, colIndex) => (
            <Skeleton
              key={colIndex}
              className={clsx(
                'h-4 flex-1',
                colIndex === 0 && 'w-1/4',
                colIndex === columns - 1 && 'w-1/6'
              )}
            />
          ))}
        </div>
      ))}
    </div>
  )
}

export default {
  Spinner,
  DotsLoader,
  Skeleton,
  SkeletonText,
  SkeletonCard,
  SkeletonList,
  SkeletonAvatar,
  SkeletonTable,
  PageLoader,
  InlineLoader,
}
