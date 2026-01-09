/**
 * Button Component
 * 
 * A versatile button with multiple variants, sizes, loading state, and icon support.
 */

import { forwardRef } from 'react'
import { clsx } from 'clsx'
import { motion } from 'framer-motion'
import { buttonTap } from '../../utils/animations'

const variants = {
  primary: 'bg-gradient-to-r from-indigo-600 to-purple-600 text-white hover:from-indigo-500 hover:to-purple-500 shadow-lg shadow-indigo-600/25 border-transparent',
  secondary: 'bg-slate-700 text-white hover:bg-slate-600 border-slate-600',
  ghost: 'bg-transparent text-slate-300 hover:bg-slate-800 hover:text-white border-transparent',
  outline: 'bg-transparent text-indigo-400 border-indigo-500/50 hover:bg-indigo-500/10 hover:border-indigo-400',
  danger: 'bg-red-600 text-white hover:bg-red-500 border-transparent shadow-lg shadow-red-600/25',
  success: 'bg-emerald-600 text-white hover:bg-emerald-500 border-transparent shadow-lg shadow-emerald-600/25',
}

const sizes = {
  xs: 'px-2.5 py-1 text-xs gap-1',
  sm: 'px-3 py-1.5 text-sm gap-1.5',
  md: 'px-4 py-2 text-sm gap-2',
  lg: 'px-6 py-3 text-base gap-2',
  xl: 'px-8 py-4 text-lg gap-3',
}

const iconSizes = {
  xs: 'w-3 h-3',
  sm: 'w-4 h-4',
  md: 'w-4 h-4',
  lg: 'w-5 h-5',
  xl: 'w-6 h-6',
}

function Spinner({ size = 'md', className }) {
  return (
    <svg
      className={clsx('animate-spin', iconSizes[size], className)}
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

export const Button = forwardRef(function Button(
  {
    variant = 'primary',
    size = 'md',
    loading = false,
    disabled = false,
    icon,
    iconPosition = 'left',
    fullWidth = false,
    as,
    children,
    className,
    ...props
  },
  ref
) {
  // Determine if we should use motion or the `as` component
  const Component = as || motion.button
  const isMotionComponent = !as

  const baseClasses = clsx(
    'inline-flex items-center justify-center font-medium rounded-lg transition-colors duration-150 border',
    'focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-900',
    'disabled:opacity-50 disabled:cursor-not-allowed disabled:pointer-events-none',
    variants[variant],
    sizes[size],
    fullWidth && 'w-full',
    className
  )

  const iconElement = icon && (
    <span className={clsx(iconSizes[size], 'flex-shrink-0')}>
      {icon}
    </span>
  )

  const content = (
    <>
      {loading ? (
        <Spinner size={size} />
      ) : (
        iconPosition === 'left' && iconElement
      )}
      {children && <span>{children}</span>}
      {!loading && iconPosition === 'right' && iconElement}
    </>
  )

  if (isMotionComponent) {
    return (
      <motion.button
        ref={ref}
        variants={buttonTap}
        initial="rest"
        whileHover={!disabled && !loading ? "hover" : undefined}
        whileTap={!disabled && !loading ? "tap" : undefined}
        className={baseClasses}
        disabled={disabled || loading}
        {...props}
      >
        {content}
      </motion.button>
    )
  }

  return (
    <Component
      ref={ref}
      className={baseClasses}
      disabled={disabled || loading}
      {...props}
    >
      {content}
    </Component>
  )
})

// Icon-only button variant
export const IconButton = forwardRef(function IconButton(
  {
    variant = 'ghost',
    size = 'md',
    loading = false,
    disabled = false,
    icon,
    label,
    className,
    ...props
  },
  ref
) {
  const iconOnlySizes = {
    xs: 'w-6 h-6',
    sm: 'w-8 h-8',
    md: 'w-10 h-10',
    lg: 'w-12 h-12',
    xl: 'w-14 h-14',
  }

  return (
    <motion.button
      ref={ref}
      variants={buttonTap}
      initial="rest"
      whileHover={!disabled && !loading ? "hover" : undefined}
      whileTap={!disabled && !loading ? "tap" : undefined}
      className={clsx(
        'inline-flex items-center justify-center rounded-lg transition-colors duration-150 border',
        'focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-900',
        'disabled:opacity-50 disabled:cursor-not-allowed',
        variants[variant],
        iconOnlySizes[size],
        className
      )}
      disabled={disabled || loading}
      aria-label={label}
      title={label}
      {...props}
    >
      {loading ? (
        <Spinner size={size} />
      ) : (
        <span className={iconSizes[size]}>{icon}</span>
      )}
    </motion.button>
  )
})

export default Button
