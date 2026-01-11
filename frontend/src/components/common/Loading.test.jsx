/**
 * Loading Components Tests
 */

import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '../../test/test-utils'
import {
  Spinner,
  DotsLoader,
  Skeleton,
  SkeletonText,
  SkeletonCard,
  SkeletonList,
  SkeletonAvatar,
  PageLoader,
  InlineLoader,
  SkeletonTable,
} from './Loading'

// Mock framer-motion
vi.mock('framer-motion', async () => {
  const actual = await vi.importActual('framer-motion')
  return {
    ...actual,
    motion: {
      div: ({ children, ...props }) => <div {...props}>{children}</div>,
    },
  }
})

describe('Spinner', () => {
  it('should render an SVG spinner', () => {
    const { container } = render(<Spinner />)
    
    expect(container.querySelector('svg')).toBeInTheDocument()
  })

  it('should have animate-spin class', () => {
    const { container } = render(<Spinner />)
    
    expect(container.querySelector('svg')).toHaveClass('animate-spin')
  })

  describe('Sizes', () => {
    it('should apply xs size', () => {
      const { container } = render(<Spinner size="xs" />)
      
      expect(container.querySelector('svg')).toHaveClass('w-3', 'h-3')
    })

    it('should apply sm size', () => {
      const { container } = render(<Spinner size="sm" />)
      
      expect(container.querySelector('svg')).toHaveClass('w-4', 'h-4')
    })

    it('should apply md size', () => {
      const { container } = render(<Spinner size="md" />)
      
      expect(container.querySelector('svg')).toHaveClass('w-6', 'h-6')
    })

    it('should apply lg size', () => {
      const { container } = render(<Spinner size="lg" />)
      
      expect(container.querySelector('svg')).toHaveClass('w-8', 'h-8')
    })

    it('should apply xl size', () => {
      const { container } = render(<Spinner size="xl" />)
      
      expect(container.querySelector('svg')).toHaveClass('w-12', 'h-12')
    })
  })

  it('should apply custom className', () => {
    const { container } = render(<Spinner className="text-indigo-500" />)
    
    expect(container.querySelector('svg')).toHaveClass('text-indigo-500')
  })
})

describe('DotsLoader', () => {
  it('should render three dots', () => {
    const { container } = render(<DotsLoader />)
    
    const dots = container.querySelectorAll('.rounded-full')
    expect(dots).toHaveLength(3)
  })

  it('should apply size class to dots', () => {
    const { container } = render(<DotsLoader size="lg" />)
    
    const dots = container.querySelectorAll('.rounded-full')
    dots.forEach(dot => {
      expect(dot).toHaveClass('w-3', 'h-3')
    })
  })
})

describe('Skeleton', () => {
  it('should render a skeleton div', () => {
    const { container } = render(<Skeleton />)
    
    const skeleton = container.querySelector('.rounded-lg')
    expect(skeleton).toBeInTheDocument()
    expect(skeleton).toHaveClass('bg-slate-700/50')
  })

  it('should apply custom className', () => {
    const { container } = render(<Skeleton className="h-4 w-full" />)
    
    expect(container.querySelector('.rounded-lg')).toHaveClass('h-4', 'w-full')
  })
})

describe('SkeletonText', () => {
  it('should render default 3 lines', () => {
    const { container } = render(<SkeletonText />)
    
    const skeletons = container.querySelectorAll('.rounded-lg')
    expect(skeletons).toHaveLength(3)
  })

  it('should render custom number of lines', () => {
    const { container } = render(<SkeletonText lines={5} />)
    
    const skeletons = container.querySelectorAll('.rounded-lg')
    expect(skeletons).toHaveLength(5)
  })

  it('should make last line shorter', () => {
    const { container } = render(<SkeletonText lines={3} />)
    
    const skeletons = container.querySelectorAll('.rounded-lg')
    expect(skeletons[2]).toHaveClass('w-3/4')
  })
})

describe('SkeletonCard', () => {
  it('should render card skeleton', () => {
    const { container } = render(<SkeletonCard />)
    
    expect(container.querySelector('.rounded-xl')).toBeInTheDocument()
  })

  it('should render multiple skeleton elements', () => {
    const { container } = render(<SkeletonCard />)
    
    const skeletons = container.querySelectorAll('.rounded-lg')
    expect(skeletons.length).toBeGreaterThan(1)
  })
})

describe('SkeletonList', () => {
  it('should render default 5 items', () => {
    const { container } = render(<SkeletonList />)
    
    const items = container.querySelectorAll('.flex.items-center.gap-3')
    expect(items).toHaveLength(5)
  })

  it('should render custom number of items', () => {
    const { container } = render(<SkeletonList items={3} />)
    
    const items = container.querySelectorAll('.flex.items-center.gap-3')
    expect(items).toHaveLength(3)
  })
})

describe('SkeletonAvatar', () => {
  it('should render avatar skeleton', () => {
    const { container } = render(<SkeletonAvatar />)
    
    expect(container.querySelector('.rounded-full')).toBeInTheDocument()
  })

  describe('Sizes', () => {
    it('should apply sm size', () => {
      const { container } = render(<SkeletonAvatar size="sm" />)
      
      expect(container.querySelector('.rounded-full')).toHaveClass('w-8', 'h-8')
    })

    it('should apply md size', () => {
      const { container } = render(<SkeletonAvatar size="md" />)
      
      expect(container.querySelector('.rounded-full')).toHaveClass('w-10', 'h-10')
    })

    it('should apply lg size', () => {
      const { container } = render(<SkeletonAvatar size="lg" />)
      
      expect(container.querySelector('.rounded-full')).toHaveClass('w-12', 'h-12')
    })

    it('should apply xl size', () => {
      const { container } = render(<SkeletonAvatar size="xl" />)
      
      expect(container.querySelector('.rounded-full')).toHaveClass('w-16', 'h-16')
    })
  })
})

describe('PageLoader', () => {
  it('should render loading message', () => {
    render(<PageLoader />)
    
    expect(screen.getByText('Loading...')).toBeInTheDocument()
  })

  it('should render custom message', () => {
    render(<PageLoader message="Please wait..." />)
    
    expect(screen.getByText('Please wait...')).toBeInTheDocument()
  })

  it('should render spinner', () => {
    const { container } = render(<PageLoader />)
    
    expect(container.querySelector('.animate-spin')).toBeInTheDocument()
  })
})

describe('InlineLoader', () => {
  it('should render default text', () => {
    render(<InlineLoader />)
    
    expect(screen.getByText('Loading')).toBeInTheDocument()
  })

  it('should render custom text', () => {
    render(<InlineLoader text="Saving..." />)
    
    expect(screen.getByText('Saving...')).toBeInTheDocument()
  })

  it('should render spinner', () => {
    const { container } = render(<InlineLoader />)
    
    expect(container.querySelector('.animate-spin')).toBeInTheDocument()
  })
})

describe('SkeletonTable', () => {
  it('should render header row', () => {
    const { container } = render(<SkeletonTable />)
    
    const header = container.querySelector('.border-b')
    expect(header).toBeInTheDocument()
  })

  it('should render default 5 rows', () => {
    const { container } = render(<SkeletonTable />)
    
    const rows = container.querySelectorAll('.py-2')
    expect(rows).toHaveLength(5)
  })

  it('should render custom number of rows', () => {
    const { container } = render(<SkeletonTable rows={3} />)
    
    const rows = container.querySelectorAll('.py-2')
    expect(rows).toHaveLength(3)
  })

  it('should render custom number of columns', () => {
    const { container } = render(<SkeletonTable columns={6} rows={1} />)
    
    // Header has columns + data rows have columns
    const headerSkeletons = container.querySelector('.border-b').querySelectorAll('.rounded-lg')
    expect(headerSkeletons).toHaveLength(6)
  })
})
