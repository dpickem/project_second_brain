/**
 * Card Component
 * 
 * A flexible card container with multiple variants, hover effects, and interactive states.
 */

import { forwardRef } from 'react'
import { clsx } from 'clsx'
import { motion } from 'framer-motion'
import { cardHover } from '../../utils/animations'

const variants = {
  elevated: 'bg-bg-elevated border border-border-primary shadow-card',
  flat: 'bg-bg-secondary border border-border-primary',
  ghost: 'bg-transparent border border-transparent hover:bg-bg-elevated/50',
  glass: 'glass-panel',
  gradient: 'bg-gradient-to-br from-slate-800/50 to-slate-900/50 border border-slate-700/50',
  outline: 'bg-transparent border border-border-primary',
}

const paddings = {
  none: '',
  sm: 'p-3',
  md: 'p-4',
  lg: 'p-6',
  xl: 'p-8',
}

const roundings = {
  sm: 'rounded-lg',
  md: 'rounded-xl',
  lg: 'rounded-2xl',
  full: 'rounded-3xl',
}

export const Card = forwardRef(function Card(
  {
    variant = 'elevated',
    padding = 'md',
    rounded = 'md',
    hover = false,
    interactive = false,
    as,
    onClick,
    children,
    className,
    ...props
  },
  ref
) {
  const isClickable = interactive || onClick
  const Component = as || (isClickable ? motion.button : motion.div)
  const shouldAnimate = hover || isClickable

  const baseClasses = clsx(
    'relative overflow-hidden',
    variants[variant],
    paddings[padding],
    roundings[rounded],
    isClickable && 'cursor-pointer text-left w-full',
    isClickable && 'focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-900',
    className
  )

  if (shouldAnimate) {
    return (
      <Component
        ref={ref}
        variants={cardHover}
        initial="rest"
        whileHover="hover"
        whileTap={isClickable ? "tap" : undefined}
        onClick={onClick}
        className={baseClasses}
        {...props}
      >
        {children}
      </Component>
    )
  }

  const StaticComponent = as || 'div'

  return (
    <StaticComponent
      ref={ref}
      onClick={onClick}
      className={baseClasses}
      {...props}
    >
      {children}
    </StaticComponent>
  )
})

// Card Header - for consistent header styling
export function CardHeader({ children, className, ...props }) {
  return (
    <div
      className={clsx(
        'flex items-center justify-between mb-4',
        className
      )}
      {...props}
    >
      {children}
    </div>
  )
}

// Card Title
export function CardTitle({ as: Component = 'h3', children, className, ...props }) {
  return (
    <Component
      className={clsx(
        'text-lg font-semibold text-text-primary font-heading',
        className
      )}
      {...props}
    >
      {children}
    </Component>
  )
}

// Card Description
export function CardDescription({ children, className, ...props }) {
  return (
    <p
      className={clsx(
        'text-sm text-text-secondary',
        className
      )}
      {...props}
    >
      {children}
    </p>
  )
}

// Card Content
export function CardContent({ children, className, ...props }) {
  return (
    <div className={clsx('', className)} {...props}>
      {children}
    </div>
  )
}

// Card Footer
export function CardFooter({ children, className, ...props }) {
  return (
    <div
      className={clsx(
        'flex items-center gap-3 mt-4 pt-4 border-t border-border-primary',
        className
      )}
      {...props}
    >
      {children}
    </div>
  )
}

// Stats Card - specialized for displaying metrics
export function StatsCard({
  icon,
  label,
  value,
  trend,
  trendLabel,
  className,
  ...props
}) {
  const trendColors = {
    up: 'text-accent-success',
    down: 'text-accent-danger',
    neutral: 'text-text-muted',
  }

  const trendIcons = {
    up: '↑',
    down: '↓',
    neutral: '→',
  }

  return (
    <Card className={clsx('', className)} {...props}>
      <div className="flex items-start justify-between">
        {icon && (
          <div className="w-10 h-10 rounded-xl bg-accent-primary/10 flex items-center justify-center text-accent-primary">
            {icon}
          </div>
        )}
        {trend && (
          <span className={clsx('text-sm font-medium flex items-center gap-1', trendColors[trend])}>
            {trendIcons[trend]} {trendLabel}
          </span>
        )}
      </div>
      <div className="mt-4">
        <p className="text-3xl font-bold text-text-primary font-heading">{value}</p>
        <p className="text-sm text-text-secondary mt-1">{label}</p>
      </div>
    </Card>
  )
}

export default Card
