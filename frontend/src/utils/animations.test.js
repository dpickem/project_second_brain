/**
 * Animation Utilities Tests
 */

import { describe, it, expect } from 'vitest'
import {
  staggerContainer,
  createStaggerContainer,
  fadeInUp,
  fadeIn,
  scaleIn,
  scaleInBounce,
  slideInRight,
  slideInLeft,
  slideInBottom,
  pageTransition,
  cardHover,
  buttonTap,
  listItem,
  skeletonPulse,
  backdropFade,
  cardFlip,
  progressFill,
  checkmark,
  springConfig,
  easings,
} from './animations'

describe('staggerContainer', () => {
  it('should have hidden state', () => {
    expect(staggerContainer.hidden).toBeDefined()
  })

  it('should have show variant with staggerChildren', () => {
    expect(staggerContainer.show.transition.staggerChildren).toBeDefined()
    expect(staggerContainer.show.transition.delayChildren).toBeDefined()
  })
})

describe('createStaggerContainer', () => {
  it('should create stagger container with default values', () => {
    const container = createStaggerContainer()
    expect(container.show.transition.staggerChildren).toBe(0.1)
    expect(container.show.transition.delayChildren).toBe(0.1)
  })

  it('should create stagger container with custom values', () => {
    const container = createStaggerContainer(0.2, 0.5)
    expect(container.show.transition.staggerChildren).toBe(0.2)
    expect(container.show.transition.delayChildren).toBe(0.5)
  })
})

describe('fadeInUp', () => {
  it('should have correct hidden state', () => {
    expect(fadeInUp.hidden.opacity).toBe(0)
    expect(fadeInUp.hidden.y).toBe(20)
  })

  it('should have correct show state', () => {
    expect(fadeInUp.show.opacity).toBe(1)
    expect(fadeInUp.show.y).toBe(0)
    expect(fadeInUp.show.transition).toBeDefined()
  })

  it('should have exit state', () => {
    expect(fadeInUp.exit).toBeDefined()
    expect(fadeInUp.exit.opacity).toBe(0)
    expect(fadeInUp.exit.y).toBe(-10)
  })
})

describe('fadeIn', () => {
  it('should transition opacity only', () => {
    expect(fadeIn.hidden.opacity).toBe(0)
    expect(fadeIn.show.opacity).toBe(1)
    expect(fadeIn.hidden.y).toBeUndefined()
  })
})

describe('scaleIn', () => {
  it('should have correct hidden state', () => {
    expect(scaleIn.hidden.opacity).toBe(0)
    expect(scaleIn.hidden.scale).toBe(0.95)
  })

  it('should have correct show state', () => {
    expect(scaleIn.show.opacity).toBe(1)
    expect(scaleIn.show.scale).toBe(1)
  })
})

describe('scaleInBounce', () => {
  it('should have smaller initial scale for bounce effect', () => {
    expect(scaleInBounce.hidden.scale).toBe(0.9)
  })

  it('should have bounce easing', () => {
    expect(scaleInBounce.show.transition.ease).toBeDefined()
    expect(Array.isArray(scaleInBounce.show.transition.ease)).toBe(true)
  })
})

describe('slideInRight', () => {
  it('should slide in from right', () => {
    expect(slideInRight.hidden.x).toBe(20)
    expect(slideInRight.show.x).toBe(0)
  })
})

describe('slideInLeft', () => {
  it('should slide in from left', () => {
    expect(slideInLeft.hidden.x).toBe(-20)
    expect(slideInLeft.show.x).toBe(0)
  })
})

describe('slideInBottom', () => {
  it('should slide in from bottom', () => {
    expect(slideInBottom.hidden.y).toBe(30)
    expect(slideInBottom.show.y).toBe(0)
  })
})

describe('pageTransition', () => {
  it('should have initial, animate, and exit states', () => {
    expect(pageTransition.initial).toBeDefined()
    expect(pageTransition.animate).toBeDefined()
    expect(pageTransition.exit).toBeDefined()
  })

  it('should have correct initial state', () => {
    expect(pageTransition.initial.opacity).toBe(0)
    expect(pageTransition.initial.y).toBe(10)
  })

  it('should have correct animate state', () => {
    expect(pageTransition.animate.opacity).toBe(1)
    expect(pageTransition.animate.y).toBe(0)
  })

  it('should have correct exit state', () => {
    expect(pageTransition.exit.opacity).toBe(0)
    expect(pageTransition.exit.y).toBe(-10)
  })
})

describe('cardHover', () => {
  it('should have rest state', () => {
    expect(cardHover.rest).toBeDefined()
    expect(cardHover.rest.scale).toBe(1)
    expect(cardHover.rest.y).toBe(0)
  })

  it('should have hover state with scale and y offset', () => {
    expect(cardHover.hover).toBeDefined()
    expect(cardHover.hover.y).toBe(-2)
    expect(cardHover.hover.scale).toBe(1.02)
  })

  it('should have tap state', () => {
    expect(cardHover.tap).toBeDefined()
    expect(cardHover.tap.scale).toBe(0.98)
  })
})

describe('buttonTap', () => {
  it('should have rest state', () => {
    expect(buttonTap.rest.scale).toBe(1)
  })

  it('should have hover state', () => {
    expect(buttonTap.hover.scale).toBe(1.02)
  })

  it('should have tap state with scale', () => {
    expect(buttonTap.tap.scale).toBe(0.98)
  })
})

describe('listItem', () => {
  it('should have hidden state', () => {
    expect(listItem.hidden.opacity).toBe(0)
    expect(listItem.hidden.y).toBe(10)
  })

  it('should have show as function for custom delay', () => {
    expect(typeof listItem.show).toBe('function')
    
    const showState = listItem.show(2)
    expect(showState.opacity).toBe(1)
    expect(showState.y).toBe(0)
    expect(showState.transition.delay).toBe(0.1) // 2 * 0.05
  })

  it('should have exit state', () => {
    expect(listItem.exit).toBeDefined()
    expect(listItem.exit.opacity).toBe(0)
  })
})

describe('skeletonPulse', () => {
  it('should have animate with opacity array', () => {
    expect(skeletonPulse.animate).toBeDefined()
    expect(skeletonPulse.animate.opacity).toBeDefined()
    expect(Array.isArray(skeletonPulse.animate.opacity)).toBe(true)
  })

  it('should have infinite repeat', () => {
    expect(skeletonPulse.animate.transition.repeat).toBe(Infinity)
  })
})

describe('backdropFade', () => {
  it('should fade backdrop', () => {
    expect(backdropFade.hidden.opacity).toBe(0)
    expect(backdropFade.show.opacity).toBe(1)
    expect(backdropFade.exit.opacity).toBe(0)
  })
})

describe('cardFlip', () => {
  it('should have front state with no rotation', () => {
    expect(cardFlip.front.rotateY).toBe(0)
  })

  it('should have back state with 180 degree rotation', () => {
    expect(cardFlip.back.rotateY).toBe(180)
  })
})

describe('progressFill', () => {
  it('should have initial scaleX of 0', () => {
    expect(progressFill.initial.scaleX).toBe(0)
  })

  it('should have animate as function for progress', () => {
    expect(typeof progressFill.animate).toBe('function')
    
    const animateState = progressFill.animate(0.5)
    expect(animateState.scaleX).toBe(0.5)
  })
})

describe('checkmark', () => {
  it('should have hidden state with 0 path length', () => {
    expect(checkmark.hidden.pathLength).toBe(0)
    expect(checkmark.hidden.opacity).toBe(0)
  })

  it('should have show state with full path', () => {
    expect(checkmark.show.pathLength).toBe(1)
    expect(checkmark.show.opacity).toBe(1)
  })
})

describe('springConfig', () => {
  it('should have gentle config', () => {
    expect(springConfig.gentle.type).toBe('spring')
    expect(springConfig.gentle.stiffness).toBeDefined()
    expect(springConfig.gentle.damping).toBeDefined()
  })

  it('should have snappy config', () => {
    expect(springConfig.snappy.type).toBe('spring')
    expect(springConfig.snappy.stiffness).toBeGreaterThan(springConfig.gentle.stiffness)
  })

  it('should have bouncy config', () => {
    expect(springConfig.bouncy.type).toBe('spring')
    expect(springConfig.bouncy.damping).toBeLessThan(springConfig.gentle.damping)
  })
})

describe('easings', () => {
  it('should have easeOut easing', () => {
    expect(easings.easeOut).toBeDefined()
    expect(Array.isArray(easings.easeOut)).toBe(true)
  })

  it('should have easeIn easing', () => {
    expect(easings.easeIn).toBeDefined()
    expect(Array.isArray(easings.easeIn)).toBe(true)
  })

  it('should have easeInOut easing', () => {
    expect(easings.easeInOut).toBeDefined()
    expect(Array.isArray(easings.easeInOut)).toBe(true)
  })

  it('should have bounce easing', () => {
    expect(easings.bounce).toBeDefined()
    expect(Array.isArray(easings.bounce)).toBe(true)
  })

  it('should have sharp easing', () => {
    expect(easings.sharp).toBeDefined()
    expect(Array.isArray(easings.sharp)).toBe(true)
  })
})
