/**
 * Test Setup
 * 
 * Global test configuration and mocks.
 */

import '@testing-library/jest-dom'
import { vi } from 'vitest'
import React from 'react'

// Mock window.matchMedia
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation(query => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
})

// Mock ResizeObserver
global.ResizeObserver = vi.fn().mockImplementation(() => ({
  observe: vi.fn(),
  unobserve: vi.fn(),
  disconnect: vi.fn(),
}))

// Mock IntersectionObserver
global.IntersectionObserver = vi.fn().mockImplementation(() => ({
  observe: vi.fn(),
  unobserve: vi.fn(),
  disconnect: vi.fn(),
}))

// Mock localStorage
const localStorageMock = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn(),
}
Object.defineProperty(window, 'localStorage', { value: localStorageMock })

// Mock scrollIntoView
Element.prototype.scrollIntoView = vi.fn()

// Helper to filter out Framer Motion animation props that shouldn't be passed to DOM elements
const filterMotionProps = (props) => {
  const {
    // Animation props
    animate,
    initial,
    exit,
    variants,
    transition,
    whileHover,
    whileTap,
    whileFocus,
    whileDrag,
    whileInView,
    viewport,
    // Gesture props
    onAnimationStart,
    onAnimationComplete,
    onUpdate,
    onDragStart,
    onDrag,
    onDragEnd,
    // Layout props
    layout,
    layoutId,
    layoutDependency,
    layoutScroll,
    // Other motion-specific props
    drag,
    dragConstraints,
    dragElastic,
    dragMomentum,
    dragTransition,
    dragPropagation,
    dragControls,
    dragListener,
    dragSnapToOrigin,
    ...domProps
  } = props
  return domProps
}

// Global mock for framer-motion
vi.mock('framer-motion', async () => {
  const actual = await vi.importActual('framer-motion')
  
  // Create a motion component factory that filters animation props
  const createMotionComponent = (element) => {
    return React.forwardRef(({ children, ...props }, ref) => {
      const filteredProps = filterMotionProps(props)
      return React.createElement(element, { ...filteredProps, ref }, children)
    })
  }
  
  return {
    ...actual,
    motion: {
      div: createMotionComponent('div'),
      span: createMotionComponent('span'),
      button: createMotionComponent('button'),
      a: createMotionComponent('a'),
      ul: createMotionComponent('ul'),
      li: createMotionComponent('li'),
      p: createMotionComponent('p'),
      h1: createMotionComponent('h1'),
      h2: createMotionComponent('h2'),
      h3: createMotionComponent('h3'),
      h4: createMotionComponent('h4'),
      section: createMotionComponent('section'),
      article: createMotionComponent('article'),
      nav: createMotionComponent('nav'),
      aside: createMotionComponent('aside'),
      header: createMotionComponent('header'),
      footer: createMotionComponent('footer'),
      main: createMotionComponent('main'),
      form: createMotionComponent('form'),
      input: createMotionComponent('input'),
      textarea: createMotionComponent('textarea'),
      label: createMotionComponent('label'),
      img: createMotionComponent('img'),
      svg: createMotionComponent('svg'),
      path: createMotionComponent('path'),
    },
    AnimatePresence: ({ children }) => React.createElement(React.Fragment, null, children),
    useAnimation: () => ({
      start: vi.fn(),
      stop: vi.fn(),
      set: vi.fn(),
    }),
    useMotionValue: (initial) => ({
      get: () => initial,
      set: vi.fn(),
      onChange: vi.fn(),
    }),
    useSpring: (initial) => ({
      get: () => initial,
      set: vi.fn(),
    }),
    useTransform: () => ({
      get: () => 0,
      set: vi.fn(),
    }),
    useReducedMotion: () => false,
    useInView: () => true,
    useScroll: () => ({
      scrollX: { get: () => 0 },
      scrollY: { get: () => 0 },
      scrollXProgress: { get: () => 0 },
      scrollYProgress: { get: () => 0 },
    }),
  }
})

// Suppress console errors in tests (optional)
// vi.spyOn(console, 'error').mockImplementation(() => {})
