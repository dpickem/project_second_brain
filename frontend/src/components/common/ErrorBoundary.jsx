/**
 * Error Boundary Component
 * 
 * Catches JavaScript errors in child component tree and displays a fallback UI.
 * Error boundaries must be class components (lifecycle methods not available in hooks).
 */

import { Component } from 'react'
import PropTypes from 'prop-types'
import { Button } from './Button'

/**
 * Error boundary that catches errors in its child component tree.
 * 
 * Usage:
 * ```jsx
 * <ErrorBoundary fallback={<p>Something went wrong</p>}>
 *   <MyComponent />
 * </ErrorBoundary>
 * ```
 * 
 * Or with a render function for access to error details:
 * ```jsx
 * <ErrorBoundary fallback={(error, reset) => (
 *   <div>
 *     <p>Error: {error.message}</p>
 *     <button onClick={reset}>Try Again</button>
 *   </div>
 * )}>
 *   <MyComponent />
 * </ErrorBoundary>
 * ```
 */
class ErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error) {
    // Update state so next render shows fallback UI
    return { hasError: true, error }
  }

  componentDidCatch(error, errorInfo) {
    // Log error to console in development
    if (import.meta.env.DEV) {
      // eslint-disable-next-line no-console
      console.error('ErrorBoundary caught an error:', error, errorInfo)
    }
    
    // Call optional onError callback
    if (this.props.onError) {
      this.props.onError(error, errorInfo)
    }
  }

  resetErrorBoundary = () => {
    this.setState({ hasError: false, error: null })
  }

  render() {
    if (this.state.hasError) {
      // If fallback is a function, call it with error and reset function
      if (typeof this.props.fallback === 'function') {
        return this.props.fallback(this.state.error, this.resetErrorBoundary)
      }
      
      // If fallback is provided as element, use it
      if (this.props.fallback) {
        return this.props.fallback
      }

      // Default fallback UI
      return (
        <DefaultErrorFallback 
          error={this.state.error} 
          resetErrorBoundary={this.resetErrorBoundary}
          title={this.props.errorTitle}
        />
      )
    }

    return this.props.children
  }
}

ErrorBoundary.propTypes = {
  children: PropTypes.node.isRequired,
  fallback: PropTypes.oneOfType([PropTypes.node, PropTypes.func]),
  onError: PropTypes.func,
  errorTitle: PropTypes.string,
}

/**
 * Default error fallback UI component
 */
function DefaultErrorFallback({ error, resetErrorBoundary, title }) {
  return (
    <div className="flex items-center justify-center min-h-[400px] p-8">
      <div className="text-center max-w-md">
        {/* Error Icon */}
        <div className="w-16 h-16 mx-auto mb-6 rounded-full bg-red-500/10 flex items-center justify-center">
          <svg 
            className="w-8 h-8 text-red-500" 
            fill="none" 
            stroke="currentColor" 
            viewBox="0 0 24 24"
          >
            <path 
              strokeLinecap="round" 
              strokeLinejoin="round" 
              strokeWidth={2} 
              d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" 
            />
          </svg>
        </div>
        
        {/* Error Message */}
        <h2 className="text-xl font-semibold text-text-primary mb-2">
          {title || 'Something went wrong'}
        </h2>
        <p className="text-text-secondary mb-6">
          An unexpected error occurred. Please try again or refresh the page.
        </p>
        
        {/* Error Details (dev only) */}
        {import.meta.env.DEV && error && (
          <details className="mb-6 text-left bg-bg-secondary rounded-lg p-4 border border-border-primary">
            <summary className="cursor-pointer text-sm text-text-muted hover:text-text-secondary">
              Error details
            </summary>
            <pre className="mt-2 text-xs text-red-400 overflow-auto max-h-32">
              {error.message}
              {error.stack && '\n\n' + error.stack}
            </pre>
          </details>
        )}
        
        {/* Action Buttons */}
        <div className="flex gap-3 justify-center">
          <Button 
            variant="secondary" 
            onClick={() => window.location.reload()}
          >
            Refresh Page
          </Button>
          <Button 
            variant="primary" 
            onClick={resetErrorBoundary}
          >
            Try Again
          </Button>
        </div>
      </div>
    </div>
  )
}

DefaultErrorFallback.propTypes = {
  error: PropTypes.object,
  resetErrorBoundary: PropTypes.func.isRequired,
  title: PropTypes.string,
}

/**
 * Page-level error boundary with navigation-aware reset.
 * Resets automatically when the route changes.
 */
class PageErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false, error: null, errorKey: props.resetKey }
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error }
  }

  static getDerivedStateFromProps(props, state) {
    // Reset error state when resetKey changes (e.g., route change)
    if (props.resetKey !== state.errorKey) {
      return { hasError: false, error: null, errorKey: props.resetKey }
    }
    return null
  }

  componentDidCatch(error, errorInfo) {
    if (import.meta.env.DEV) {
      // eslint-disable-next-line no-console
      console.error('PageErrorBoundary caught an error:', error, errorInfo)
    }
    
    if (this.props.onError) {
      this.props.onError(error, errorInfo)
    }
  }

  resetErrorBoundary = () => {
    this.setState({ hasError: false, error: null })
  }

  render() {
    if (this.state.hasError) {
      return (
        <DefaultErrorFallback 
          error={this.state.error} 
          resetErrorBoundary={this.resetErrorBoundary}
          title="Page Error"
        />
      )
    }

    return this.props.children
  }
}

PageErrorBoundary.propTypes = {
  children: PropTypes.node.isRequired,
  resetKey: PropTypes.string,
  onError: PropTypes.func,
}

export { ErrorBoundary, PageErrorBoundary, DefaultErrorFallback }
