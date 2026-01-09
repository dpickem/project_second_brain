/**
 * EmptyState Component
 * 
 * Consistent empty state pattern for lists, searches, and missing data.
 */

import { motion } from 'framer-motion'
import { clsx } from 'clsx'
import { fadeInUp } from '../../utils/animations'
import { Button } from './Button'

const variants = {
  default: 'bg-transparent',
  card: 'bg-bg-elevated border border-border-primary rounded-2xl p-8',
  minimal: 'bg-transparent py-4',
}

const sizes = {
  sm: {
    icon: 'w-12 h-12',
    title: 'text-lg',
    description: 'text-sm',
    gap: 'gap-3',
  },
  md: {
    icon: 'w-16 h-16',
    title: 'text-xl',
    description: 'text-base',
    gap: 'gap-4',
  },
  lg: {
    icon: 'w-20 h-20',
    title: 'text-2xl',
    description: 'text-base',
    gap: 'gap-5',
  },
}

export function EmptyState({
  icon,
  title,
  description,
  action,
  actionLabel,
  onAction,
  secondaryAction,
  secondaryActionLabel,
  onSecondaryAction,
  variant = 'default',
  size = 'md',
  className,
}) {
  const sizeConfig = sizes[size]

  return (
    <motion.div
      variants={fadeInUp}
      initial="hidden"
      animate="show"
      className={clsx(
        'flex flex-col items-center justify-center text-center',
        variants[variant],
        sizeConfig.gap,
        className
      )}
    >
      {icon && (
        <div className={clsx(
          'flex items-center justify-center rounded-2xl bg-slate-800/50 text-text-muted',
          sizeConfig.icon
        )}>
          {typeof icon === 'string' ? (
            <span className="text-3xl">{icon}</span>
          ) : (
            <span className="w-8 h-8">{icon}</span>
          )}
        </div>
      )}

      {title && (
        <h3 className={clsx(
          'font-semibold text-text-primary font-heading',
          sizeConfig.title
        )}>
          {title}
        </h3>
      )}

      {description && (
        <p className={clsx(
          'text-text-secondary max-w-sm',
          sizeConfig.description
        )}>
          {description}
        </p>
      )}

      {(action || onAction || secondaryAction || onSecondaryAction) && (
        <div className="flex items-center gap-3 mt-2">
          {(action || onAction) && (
            action || (
              <Button onClick={onAction} size={size === 'sm' ? 'sm' : 'md'}>
                {actionLabel || 'Take Action'}
              </Button>
            )
          )}
          
          {(secondaryAction || onSecondaryAction) && (
            secondaryAction || (
              <Button
                variant="ghost"
                onClick={onSecondaryAction}
                size={size === 'sm' ? 'sm' : 'md'}
              >
                {secondaryActionLabel || 'Learn More'}
              </Button>
            )
          )}
        </div>
      )}
    </motion.div>
  )
}

// Search Empty State
export function SearchEmptyState({
  query,
  onClear,
  suggestions,
  className,
}) {
  return (
    <EmptyState
      icon="🔍"
      title={`No results for "${query}"`}
      description="Try adjusting your search terms or filters"
      action={
        onClear && (
          <Button variant="secondary" onClick={onClear}>
            Clear Search
          </Button>
        )
      }
      variant="default"
      className={className}
    >
      {suggestions && suggestions.length > 0 && (
        <div className="mt-4 text-left w-full max-w-sm">
          <p className="text-sm text-text-muted mb-2">Suggestions:</p>
          <ul className="space-y-1">
            {suggestions.map((suggestion, index) => (
              <li key={index} className="text-sm text-text-secondary">
                • {suggestion}
              </li>
            ))}
          </ul>
        </div>
      )}
    </EmptyState>
  )
}

// Error Empty State
export function ErrorEmptyState({
  title = 'Something went wrong',
  description = 'An error occurred while loading this content.',
  onRetry,
  retryLabel = 'Try Again',
  className,
}) {
  return (
    <EmptyState
      icon="⚠️"
      title={title}
      description={description}
      onAction={onRetry}
      actionLabel={retryLabel}
      variant="card"
      className={className}
    />
  )
}

// No Data Empty State
export function NoDataEmptyState({
  title = 'No data yet',
  description = 'Start adding content to see it appear here.',
  onAction,
  actionLabel = 'Get Started',
  icon = '📭',
  className,
}) {
  return (
    <EmptyState
      icon={icon}
      title={title}
      description={description}
      onAction={onAction}
      actionLabel={actionLabel}
      variant="default"
      className={className}
    />
  )
}

// Coming Soon Empty State
export function ComingSoonEmptyState({
  feature = 'This feature',
  className,
}) {
  return (
    <EmptyState
      icon="🚧"
      title="Coming Soon"
      description={`${feature} is currently under development. Check back soon!`}
      variant="card"
      className={className}
    />
  )
}

// Specific empty states for different contexts

export function NoNotesEmptyState({ onCapture, className }) {
  return (
    <EmptyState
      icon="📝"
      title="No notes yet"
      description="Capture your first thought or idea to get started building your second brain."
      onAction={onCapture}
      actionLabel="Capture Note"
      variant="default"
      className={className}
    />
  )
}

export function NoDueCardsEmptyState({ onPractice, className }) {
  return (
    <EmptyState
      icon="🎉"
      title="All caught up!"
      description="You have no cards due for review. Great job staying on top of your learning!"
      onAction={onPractice}
      actionLabel="Start Practice Session"
      variant="card"
      className={className}
    />
  )
}

export function NoExercisesEmptyState({ className }) {
  return (
    <EmptyState
      icon="📚"
      title="No exercises available"
      description="Exercises will be generated as you add more content to your knowledge base."
      variant="default"
      className={className}
    />
  )
}

export function NoConnectionsEmptyState({ className }) {
  return (
    <EmptyState
      icon="🕸️"
      title="No connections yet"
      description="As you add more content, connections between concepts will appear here."
      variant="default"
      size="sm"
      className={className}
    />
  )
}

export default EmptyState
