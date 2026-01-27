/**
 * Input Component
 * 
 * Form input with label, error states, and icon support.
 */

import { forwardRef, useState } from 'react'
import { clsx } from 'clsx'
import { EyeIcon, EyeSlashIcon } from '@heroicons/react/24/outline'
import PropTypes from 'prop-types'

const sizes = {
  sm: 'px-3 py-1.5 text-sm',
  md: 'px-4 py-2.5 text-sm',
  lg: 'px-5 py-3 text-base',
}

export const Input = forwardRef(function Input(
  {
    label,
    error,
    hint,
    icon,
    iconPosition = 'left',
    size = 'md',
    type = 'text',
    className,
    wrapperClassName,
    ...props
  },
  ref
) {
  const [showPassword, setShowPassword] = useState(false)
  const isPassword = type === 'password'
  const inputType = isPassword ? (showPassword ? 'text' : 'password') : type

  const hasLeftIcon = icon && iconPosition === 'left'
  const hasRightIcon = (icon && iconPosition === 'right') || isPassword

  return (
    <div className={clsx('w-full', wrapperClassName)}>
      {label && (
        <label className="block text-sm font-medium text-text-primary mb-1.5">
          {label}
        </label>
      )}
      
      <div className="relative">
        {hasLeftIcon && (
          <div className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted pointer-events-none">
            <span className="w-5 h-5 block">{icon}</span>
          </div>
        )}

        <input
          ref={ref}
          type={inputType}
          className={clsx(
            'w-full rounded-lg border bg-bg-tertiary text-text-primary placeholder-text-muted',
            'transition-all duration-150',
            'focus:outline-none focus:ring-2 focus:ring-offset-0',
            'disabled:opacity-50 disabled:cursor-not-allowed',
            error
              ? 'border-accent-danger focus:border-accent-danger focus:ring-accent-danger/20'
              : 'border-border-primary focus:border-accent-primary focus:ring-accent-primary/20',
            sizes[size],
            hasLeftIcon && 'pl-10',
            hasRightIcon && 'pr-10',
            className
          )}
          {...props}
        />

        {isPassword && (
          <button
            type="button"
            onClick={() => setShowPassword(!showPassword)}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-text-muted hover:text-text-secondary transition-colors"
          >
            {showPassword ? (
              <EyeSlashIcon className="w-5 h-5" />
            ) : (
              <EyeIcon className="w-5 h-5" />
            )}
          </button>
        )}

        {!isPassword && hasRightIcon && (
          <div className="absolute right-3 top-1/2 -translate-y-1/2 text-text-muted pointer-events-none">
            <span className="w-5 h-5 block">{icon}</span>
          </div>
        )}
      </div>

      {(error || hint) && (
        <p className={clsx(
          'mt-1.5 text-sm',
          error ? 'text-accent-danger' : 'text-text-muted'
        )}>
          {error || hint}
        </p>
      )}
    </div>
  )
})

Input.propTypes = {
  label: PropTypes.string,
  error: PropTypes.string,
  hint: PropTypes.string,
  icon: PropTypes.node,
  iconPosition: PropTypes.oneOf(['left', 'right']),
  size: PropTypes.oneOf(['sm', 'md', 'lg']),
  type: PropTypes.string,
  className: PropTypes.string,
  wrapperClassName: PropTypes.string,
}

// Textarea variant
export const Textarea = forwardRef(function Textarea(
  {
    label,
    error,
    hint,
    size = 'md',
    rows = 4,
    className,
    wrapperClassName,
    ...props
  },
  ref
) {
  return (
    <div className={clsx('w-full', wrapperClassName)}>
      {label && (
        <label className="block text-sm font-medium text-text-primary mb-1.5">
          {label}
        </label>
      )}
      
      <textarea
        ref={ref}
        rows={rows}
        className={clsx(
          'w-full rounded-lg border bg-bg-tertiary text-text-primary placeholder-text-muted resize-none',
          'transition-all duration-150',
          'focus:outline-none focus:ring-2 focus:ring-offset-0',
          'disabled:opacity-50 disabled:cursor-not-allowed',
          error
            ? 'border-accent-danger focus:border-accent-danger focus:ring-accent-danger/20'
            : 'border-border-primary focus:border-accent-primary focus:ring-accent-primary/20',
          sizes[size],
          className
        )}
        {...props}
      />

      {(error || hint) && (
        <p className={clsx(
          'mt-1.5 text-sm',
          error ? 'text-accent-danger' : 'text-text-muted'
        )}>
          {error || hint}
        </p>
      )}
    </div>
  )
})

Textarea.propTypes = {
  label: PropTypes.string,
  error: PropTypes.string,
  hint: PropTypes.string,
  size: PropTypes.oneOf(['sm', 'md', 'lg']),
  rows: PropTypes.number,
  className: PropTypes.string,
  wrapperClassName: PropTypes.string,
}

// Search Input
export const SearchInput = forwardRef(function SearchInput(
  { placeholder = 'Search...', onClear, value, ...props },
  ref
) {
  return (
    <div className="relative">
      <div className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted pointer-events-none">
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
        </svg>
      </div>
      
      <input
        ref={ref}
        type="text"
        value={value}
        placeholder={placeholder}
        className={clsx(
          'w-full rounded-lg border border-border-primary bg-bg-tertiary text-text-primary placeholder-text-muted',
          'pl-10 pr-10 py-2.5 text-sm',
          'transition-all duration-150',
          'focus:outline-none focus:ring-2 focus:ring-accent-primary/20 focus:border-accent-primary'
        )}
        {...props}
      />

      {value && onClear && (
        <button
          type="button"
          onClick={onClear}
          className="absolute right-3 top-1/2 -translate-y-1/2 text-text-muted hover:text-text-secondary transition-colors"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      )}
    </div>
  )
})

SearchInput.propTypes = {
  placeholder: PropTypes.string,
  onClear: PropTypes.func,
  value: PropTypes.string,
}

// Select Input
export const Select = forwardRef(function Select(
  {
    label,
    error,
    hint,
    size = 'md',
    options = [],
    placeholder = 'Select...',
    className,
    wrapperClassName,
    ...props
  },
  ref
) {
  return (
    <div className={clsx('w-full', wrapperClassName)}>
      {label && (
        <label className="block text-sm font-medium text-text-primary mb-1.5">
          {label}
        </label>
      )}
      
      <div className="relative">
        <select
          ref={ref}
          className={clsx(
            'w-full rounded-lg border bg-bg-tertiary text-text-primary appearance-none cursor-pointer',
            'transition-all duration-150',
            'focus:outline-none focus:ring-2 focus:ring-offset-0',
            'disabled:opacity-50 disabled:cursor-not-allowed',
            error
              ? 'border-accent-danger focus:border-accent-danger focus:ring-accent-danger/20'
              : 'border-border-primary focus:border-accent-primary focus:ring-accent-primary/20',
            sizes[size],
            'pr-10',
            className
          )}
          {...props}
        >
          {placeholder && (
            <option value="" disabled>
              {placeholder}
            </option>
          )}
          {options.map((option) => (
            <option
              key={option.value}
              value={option.value}
              disabled={option.disabled}
            >
              {option.label}
            </option>
          ))}
        </select>

        {/* Chevron icon */}
        <div className="absolute right-3 top-1/2 -translate-y-1/2 text-text-muted pointer-events-none">
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </div>
      </div>

      {(error || hint) && (
        <p className={clsx(
          'mt-1.5 text-sm',
          error ? 'text-accent-danger' : 'text-text-muted'
        )}>
          {error || hint}
        </p>
      )}
    </div>
  )
})

Select.propTypes = {
  label: PropTypes.string,
  error: PropTypes.string,
  hint: PropTypes.string,
  size: PropTypes.oneOf(['sm', 'md', 'lg']),
  options: PropTypes.arrayOf(
    PropTypes.shape({
      value: PropTypes.oneOfType([PropTypes.string, PropTypes.number]).isRequired,
      label: PropTypes.string.isRequired,
      disabled: PropTypes.bool,
    })
  ),
  placeholder: PropTypes.string,
  className: PropTypes.string,
  wrapperClassName: PropTypes.string,
}

// Checkbox
export const Checkbox = forwardRef(function Checkbox(
  { label, description, error, className, ...props },
  ref
) {
  return (
    <div className={clsx('relative flex items-start', className)}>
      <div className="flex items-center h-5">
        <input
          ref={ref}
          type="checkbox"
          className={clsx(
            'w-4 h-4 rounded border bg-bg-tertiary cursor-pointer',
            'text-accent-primary focus:ring-accent-primary/20 focus:ring-offset-0',
            'transition-colors duration-150',
            error ? 'border-accent-danger' : 'border-border-primary'
          )}
          {...props}
        />
      </div>
      {(label || description) && (
        <div className="ml-3">
          {label && (
            <label className="text-sm font-medium text-text-primary cursor-pointer">
              {label}
            </label>
          )}
          {description && (
            <p className="text-sm text-text-muted">{description}</p>
          )}
        </div>
      )}
    </div>
  )
})

Checkbox.propTypes = {
  label: PropTypes.string,
  description: PropTypes.string,
  error: PropTypes.string,
  className: PropTypes.string,
}

export default Input
