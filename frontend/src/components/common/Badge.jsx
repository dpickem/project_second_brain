/**
 * Badge Component
 * 
 * Status badges and tags with multiple variants and sizes.
 */

import { clsx } from 'clsx'

const variants = {
  default: 'bg-slate-700 text-slate-200 border-slate-600',
  primary: 'bg-indigo-500/20 text-indigo-300 border-indigo-500/30',
  secondary: 'bg-slate-600/50 text-slate-300 border-slate-500/50',
  success: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30',
  warning: 'bg-amber-500/20 text-amber-300 border-amber-500/30',
  danger: 'bg-red-500/20 text-red-300 border-red-500/30',
  info: 'bg-sky-500/20 text-sky-300 border-sky-500/30',
  // Solid variants
  'solid-primary': 'bg-indigo-600 text-white border-indigo-600',
  'solid-success': 'bg-emerald-600 text-white border-emerald-600',
  'solid-warning': 'bg-amber-600 text-white border-amber-600',
  'solid-danger': 'bg-red-600 text-white border-red-600',
  // Outline variants
  'outline-primary': 'bg-transparent text-indigo-400 border-indigo-500',
  'outline-success': 'bg-transparent text-emerald-400 border-emerald-500',
  'outline-warning': 'bg-transparent text-amber-400 border-amber-500',
  'outline-danger': 'bg-transparent text-red-400 border-red-500',
}

const sizes = {
  xs: 'px-1.5 py-0.5 text-xs',
  sm: 'px-2 py-0.5 text-xs',
  md: 'px-2.5 py-1 text-sm',
  lg: 'px-3 py-1.5 text-sm',
}

export function Badge({
  variant = 'default',
  size = 'sm',
  dot = false,
  icon,
  removable = false,
  onRemove,
  children,
  className,
  ...props
}) {
  return (
    <span
      className={clsx(
        'inline-flex items-center font-medium rounded-full border',
        variants[variant],
        sizes[size],
        className
      )}
      {...props}
    >
      {dot && (
        <span className={clsx(
          'w-1.5 h-1.5 rounded-full mr-1.5',
          variant.includes('success') && 'bg-emerald-400',
          variant.includes('warning') && 'bg-amber-400',
          variant.includes('danger') && 'bg-red-400',
          variant.includes('primary') && 'bg-indigo-400',
          variant.includes('info') && 'bg-sky-400',
          variant === 'default' && 'bg-slate-400',
          variant === 'secondary' && 'bg-slate-400',
        )} />
      )}
      
      {icon && (
        <span className="w-3.5 h-3.5 mr-1 -ml-0.5">{icon}</span>
      )}
      
      {children}
      
      {removable && (
        <button
          type="button"
          onClick={onRemove}
          className="ml-1 -mr-0.5 w-3.5 h-3.5 rounded-full hover:bg-white/20 transition-colors flex items-center justify-center"
        >
          <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      )}
    </span>
  )
}

// Status Badge - specialized for status indicators
export function StatusBadge({ status, size = 'sm', className }) {
  const statusConfig = {
    active: { variant: 'success', label: 'Active', dot: true },
    inactive: { variant: 'default', label: 'Inactive', dot: true },
    pending: { variant: 'warning', label: 'Pending', dot: true },
    error: { variant: 'danger', label: 'Error', dot: true },
    completed: { variant: 'success', label: 'Completed', dot: false },
    processing: { variant: 'info', label: 'Processing', dot: true },
    draft: { variant: 'secondary', label: 'Draft', dot: false },
  }

  const config = statusConfig[status] || statusConfig.inactive

  return (
    <Badge 
      variant={config.variant} 
      size={size} 
      dot={config.dot}
      className={className}
    >
      {config.label}
    </Badge>
  )
}

// Content Type Badge - for content types
export function ContentTypeBadge({ type, size = 'sm', className }) {
  const typeConfig = {
    article: { variant: 'primary', icon: '📄' },
    book: { variant: 'info', icon: '📚' },
    paper: { variant: 'success', icon: '📑' },
    video: { variant: 'danger', icon: '🎬' },
    podcast: { variant: 'warning', icon: '🎙️' },
    code: { variant: 'default', icon: '💻' },
    note: { variant: 'secondary', icon: '📝' },
    concept: { variant: 'primary', icon: '💡' },
  }

  const config = typeConfig[type] || { variant: 'default', icon: '📄' }

  return (
    <Badge variant={config.variant} size={size} className={className}>
      <span className="mr-1">{config.icon}</span>
      {type}
    </Badge>
  )
}

// Difficulty Badge - for exercise difficulty
export function DifficultyBadge({ level, size = 'sm', className }) {
  const levelConfig = {
    beginner: { variant: 'success', label: 'Beginner' },
    easy: { variant: 'success', label: 'Easy' },
    intermediate: { variant: 'warning', label: 'Intermediate' },
    medium: { variant: 'warning', label: 'Medium' },
    advanced: { variant: 'danger', label: 'Advanced' },
    hard: { variant: 'danger', label: 'Hard' },
    expert: { variant: 'outline-danger', label: 'Expert' },
  }

  const config = levelConfig[level] || levelConfig.intermediate

  return (
    <Badge variant={config.variant} size={size} className={className}>
      {config.label}
    </Badge>
  )
}

// Tag Badge - for clickable tags
export function TagBadge({ tag, onClick, removable, onRemove, size = 'sm', className }) {
  if (onClick) {
    return (
      <button
        type="button"
        onClick={() => onClick(tag)}
        className={clsx(
          'inline-flex items-center font-medium rounded-full border',
          'bg-slate-700/50 text-slate-300 border-slate-600/50',
          'hover:bg-slate-600/50 hover:border-slate-500/50 transition-colors',
          sizes[size],
          className
        )}
      >
        <span className="text-text-muted mr-1">#</span>
        {tag}
        {removable && (
          <span
            role="button"
            onClick={(e) => {
              e.stopPropagation()
              onRemove?.(tag)
            }}
            className="ml-1 -mr-0.5 w-3.5 h-3.5 rounded-full hover:bg-white/20 transition-colors flex items-center justify-center"
          >
            <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </span>
        )}
      </button>
    )
  }

  return (
    <Badge variant="secondary" size={size} removable={removable} onRemove={() => onRemove?.(tag)} className={className}>
      <span className="text-text-muted mr-1">#</span>
      {tag}
    </Badge>
  )
}

// Mastery Badge - for mastery levels
export function MasteryBadge({ mastery, size = 'sm', showPercent = true, className }) {
  const percent = Math.round(mastery * 100)
  let variant = 'danger'
  let label = 'Novice'

  if (percent >= 80) {
    variant = 'success'
    label = 'Mastered'
  } else if (percent >= 60) {
    variant = 'primary'
    label = 'Proficient'
  } else if (percent >= 40) {
    variant = 'warning'
    label = 'Learning'
  }

  return (
    <Badge variant={variant} size={size} className={className}>
      {label}
      {showPercent && <span className="ml-1 opacity-75">{percent}%</span>}
    </Badge>
  )
}

export default Badge
