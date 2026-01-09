/**
 * Animation Utilities
 * 
 * Reusable Framer Motion animation presets for consistent, delightful micro-interactions.
 */

// Stagger container - staggers children animations
export const staggerContainer = {
  hidden: {},
  show: {
    transition: {
      staggerChildren: 0.1,
      delayChildren: 0.1,
    },
  },
}

// Stagger container variants (configurable)
export const createStaggerContainer = (staggerDelay = 0.1, initialDelay = 0.1) => ({
  hidden: {},
  show: {
    transition: {
      staggerChildren: staggerDelay,
      delayChildren: initialDelay,
    },
  },
})

// Fade in from bottom
export const fadeInUp = {
  hidden: { opacity: 0, y: 20 },
  show: { 
    opacity: 1, 
    y: 0,
    transition: { duration: 0.4, ease: 'easeOut' }
  },
  exit: {
    opacity: 0,
    y: -10,
    transition: { duration: 0.2, ease: 'easeIn' }
  }
}

// Fade in only (no movement)
export const fadeIn = {
  hidden: { opacity: 0 },
  show: { 
    opacity: 1,
    transition: { duration: 0.3, ease: 'easeOut' }
  },
  exit: {
    opacity: 0,
    transition: { duration: 0.2, ease: 'easeIn' }
  }
}

// Scale in from slightly smaller
export const scaleIn = {
  hidden: { opacity: 0, scale: 0.95 },
  show: { 
    opacity: 1, 
    scale: 1,
    transition: { duration: 0.3, ease: 'easeOut' }
  },
  exit: {
    opacity: 0,
    scale: 0.95,
    transition: { duration: 0.2, ease: 'easeIn' }
  }
}

// Scale in with bounce (for modals, popovers)
export const scaleInBounce = {
  hidden: { opacity: 0, scale: 0.9 },
  show: { 
    opacity: 1, 
    scale: 1,
    transition: { 
      duration: 0.35, 
      ease: [0.175, 0.885, 0.32, 1.275] // Bounce easing
    }
  },
  exit: {
    opacity: 0,
    scale: 0.95,
    transition: { duration: 0.2, ease: 'easeIn' }
  }
}

// Slide in from right
export const slideInRight = {
  hidden: { opacity: 0, x: 20 },
  show: { 
    opacity: 1, 
    x: 0,
    transition: { duration: 0.3, ease: 'easeOut' }
  },
  exit: {
    opacity: 0,
    x: 20,
    transition: { duration: 0.2, ease: 'easeIn' }
  }
}

// Slide in from left
export const slideInLeft = {
  hidden: { opacity: 0, x: -20 },
  show: { 
    opacity: 1, 
    x: 0,
    transition: { duration: 0.3, ease: 'easeOut' }
  },
  exit: {
    opacity: 0,
    x: -20,
    transition: { duration: 0.2, ease: 'easeIn' }
  }
}

// Slide in from bottom (for bottom sheets, toasts)
export const slideInBottom = {
  hidden: { opacity: 0, y: 30 },
  show: { 
    opacity: 1, 
    y: 0,
    transition: { duration: 0.3, ease: 'easeOut' }
  },
  exit: {
    opacity: 0,
    y: 30,
    transition: { duration: 0.2, ease: 'easeIn' }
  }
}

// Page transition (for route changes)
export const pageTransition = {
  initial: { opacity: 0, y: 10 },
  animate: { 
    opacity: 1, 
    y: 0,
    transition: { duration: 0.2, ease: 'easeOut' }
  },
  exit: { 
    opacity: 0, 
    y: -10,
    transition: { duration: 0.15, ease: 'easeIn' }
  },
}

// Card hover effect
export const cardHover = {
  rest: { 
    scale: 1, 
    y: 0,
    transition: { duration: 0.2, ease: 'easeOut' }
  },
  hover: { 
    scale: 1.02, 
    y: -2,
    transition: { duration: 0.2, ease: 'easeOut' }
  },
  tap: { 
    scale: 0.98,
    transition: { duration: 0.1 }
  }
}

// Button tap effect
export const buttonTap = {
  rest: { scale: 1 },
  hover: { scale: 1.02 },
  tap: { scale: 0.98 }
}

// List item animation (for virtualized lists)
export const listItem = {
  hidden: { opacity: 0, y: 10 },
  show: (custom = 0) => ({
    opacity: 1,
    y: 0,
    transition: {
      delay: custom * 0.05,
      duration: 0.3,
      ease: 'easeOut'
    }
  }),
  exit: {
    opacity: 0,
    y: -10,
    transition: { duration: 0.2 }
  }
}

// Skeleton pulse animation
export const skeletonPulse = {
  animate: {
    opacity: [0.5, 1, 0.5],
    transition: {
      duration: 1.5,
      repeat: Infinity,
      ease: 'easeInOut'
    }
  }
}

// Backdrop fade
export const backdropFade = {
  hidden: { opacity: 0 },
  show: { 
    opacity: 1,
    transition: { duration: 0.2 }
  },
  exit: { 
    opacity: 0,
    transition: { duration: 0.15 }
  }
}

// Flip animation (for flashcards)
export const cardFlip = {
  front: {
    rotateY: 0,
    transition: { duration: 0.4, ease: 'easeOut' }
  },
  back: {
    rotateY: 180,
    transition: { duration: 0.4, ease: 'easeOut' }
  }
}

// Progress bar fill
export const progressFill = {
  initial: { scaleX: 0 },
  animate: (progress) => ({
    scaleX: progress,
    transition: { duration: 0.5, ease: 'easeOut' }
  })
}

// Success checkmark (for completion states)
export const checkmark = {
  hidden: { pathLength: 0, opacity: 0 },
  show: {
    pathLength: 1,
    opacity: 1,
    transition: {
      pathLength: { duration: 0.5, ease: 'easeOut' },
      opacity: { duration: 0.2 }
    }
  }
}

// Spring configurations for more natural motion
export const springConfig = {
  gentle: { type: 'spring', stiffness: 100, damping: 15 },
  snappy: { type: 'spring', stiffness: 300, damping: 30 },
  bouncy: { type: 'spring', stiffness: 200, damping: 10 },
}

// Easing presets
export const easings = {
  easeOut: [0.0, 0.0, 0.2, 1],
  easeIn: [0.4, 0.0, 1, 1],
  easeInOut: [0.4, 0.0, 0.2, 1],
  bounce: [0.175, 0.885, 0.32, 1.275],
  sharp: [0.4, 0.0, 0.6, 1],
}
