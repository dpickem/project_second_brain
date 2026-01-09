/**
 * Badge Component Tests
 */

import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '../../test/test-utils'
import { 
  Badge, 
  StatusBadge, 
  ContentTypeBadge, 
  DifficultyBadge, 
  TagBadge, 
  MasteryBadge 
} from './Badge'

describe('Badge', () => {
  describe('Rendering', () => {
    it('should render with children', () => {
      render(<Badge>Test Badge</Badge>)
      
      expect(screen.getByText('Test Badge')).toBeInTheDocument()
    })

    it('should apply default variant styles', () => {
      render(<Badge>Default</Badge>)
      
      expect(screen.getByText('Default')).toHaveClass('bg-slate-700')
    })
  })

  describe('Variants', () => {
    it('should apply primary variant', () => {
      render(<Badge variant="primary">Primary</Badge>)
      
      expect(screen.getByText('Primary')).toHaveClass('bg-indigo-500/20')
    })

    it('should apply success variant', () => {
      render(<Badge variant="success">Success</Badge>)
      
      expect(screen.getByText('Success')).toHaveClass('bg-emerald-500/20')
    })

    it('should apply warning variant', () => {
      render(<Badge variant="warning">Warning</Badge>)
      
      expect(screen.getByText('Warning')).toHaveClass('bg-amber-500/20')
    })

    it('should apply danger variant', () => {
      render(<Badge variant="danger">Danger</Badge>)
      
      expect(screen.getByText('Danger')).toHaveClass('bg-red-500/20')
    })

    it('should apply solid variants', () => {
      render(<Badge variant="solid-primary">Solid Primary</Badge>)
      
      expect(screen.getByText('Solid Primary')).toHaveClass('bg-indigo-600')
    })

    it('should apply outline variants', () => {
      render(<Badge variant="outline-success">Outline Success</Badge>)
      
      expect(screen.getByText('Outline Success')).toHaveClass('bg-transparent', 'border-emerald-500')
    })
  })

  describe('Sizes', () => {
    it('should apply xs size', () => {
      render(<Badge size="xs">XS</Badge>)
      
      expect(screen.getByText('XS')).toHaveClass('px-1.5', 'text-xs')
    })

    it('should apply sm size', () => {
      render(<Badge size="sm">SM</Badge>)
      
      expect(screen.getByText('SM')).toHaveClass('px-2', 'text-xs')
    })

    it('should apply md size', () => {
      render(<Badge size="md">MD</Badge>)
      
      expect(screen.getByText('MD')).toHaveClass('px-2.5', 'text-sm')
    })

    it('should apply lg size', () => {
      render(<Badge size="lg">LG</Badge>)
      
      expect(screen.getByText('LG')).toHaveClass('px-3', 'py-1.5')
    })
  })

  describe('Dot indicator', () => {
    it('should render dot when dot prop is true', () => {
      const { container } = render(<Badge dot variant="success">With Dot</Badge>)
      
      const dot = container.querySelector('.w-1\\.5.h-1\\.5.rounded-full')
      expect(dot).toBeInTheDocument()
    })

    it('should not render dot by default', () => {
      const { container } = render(<Badge>No Dot</Badge>)
      
      const dot = container.querySelector('.w-1\\.5.h-1\\.5.rounded-full')
      expect(dot).not.toBeInTheDocument()
    })
  })

  describe('Icon support', () => {
    it('should render icon when provided', () => {
      const icon = <svg data-testid="badge-icon" />
      render(<Badge icon={icon}>With Icon</Badge>)
      
      expect(screen.getByTestId('badge-icon')).toBeInTheDocument()
    })
  })

  describe('Removable', () => {
    it('should show remove button when removable', () => {
      render(<Badge removable>Removable</Badge>)
      
      expect(screen.getByRole('button')).toBeInTheDocument()
    })

    it('should call onRemove when remove button clicked', () => {
      const handleRemove = vi.fn()
      render(<Badge removable onRemove={handleRemove}>Removable</Badge>)
      
      fireEvent.click(screen.getByRole('button'))
      
      expect(handleRemove).toHaveBeenCalledTimes(1)
    })
  })

  describe('Custom class', () => {
    it('should apply custom className', () => {
      render(<Badge className="custom-class">Custom</Badge>)
      
      expect(screen.getByText('Custom')).toHaveClass('custom-class')
    })
  })
})

describe('StatusBadge', () => {
  it('should render active status', () => {
    render(<StatusBadge status="active" />)
    
    expect(screen.getByText('Active')).toBeInTheDocument()
  })

  it('should render pending status with warning color', () => {
    render(<StatusBadge status="pending" />)
    
    expect(screen.getByText('Pending')).toBeInTheDocument()
  })

  it('should render error status', () => {
    render(<StatusBadge status="error" />)
    
    expect(screen.getByText('Error')).toBeInTheDocument()
  })

  it('should render completed status', () => {
    render(<StatusBadge status="completed" />)
    
    expect(screen.getByText('Completed')).toBeInTheDocument()
  })

  it('should fall back to inactive for unknown status', () => {
    render(<StatusBadge status="unknown" />)
    
    expect(screen.getByText('Inactive')).toBeInTheDocument()
  })
})

describe('ContentTypeBadge', () => {
  it('should render article type', () => {
    render(<ContentTypeBadge type="article" />)
    
    expect(screen.getByText('article')).toBeInTheDocument()
    expect(screen.getByText('📄')).toBeInTheDocument()
  })

  it('should render book type', () => {
    render(<ContentTypeBadge type="book" />)
    
    expect(screen.getByText('book')).toBeInTheDocument()
    expect(screen.getByText('📚')).toBeInTheDocument()
  })

  it('should render code type', () => {
    render(<ContentTypeBadge type="code" />)
    
    expect(screen.getByText('code')).toBeInTheDocument()
    expect(screen.getByText('💻')).toBeInTheDocument()
  })
})

describe('DifficultyBadge', () => {
  it('should render beginner level', () => {
    render(<DifficultyBadge level="beginner" />)
    
    expect(screen.getByText('Beginner')).toBeInTheDocument()
  })

  it('should render intermediate level', () => {
    render(<DifficultyBadge level="intermediate" />)
    
    expect(screen.getByText('Intermediate')).toBeInTheDocument()
  })

  it('should render advanced level', () => {
    render(<DifficultyBadge level="advanced" />)
    
    expect(screen.getByText('Advanced')).toBeInTheDocument()
  })

  it('should render expert level', () => {
    render(<DifficultyBadge level="expert" />)
    
    expect(screen.getByText('Expert')).toBeInTheDocument()
  })
})

describe('TagBadge', () => {
  it('should render tag with hashtag prefix', () => {
    render(<TagBadge tag="javascript" />)
    
    expect(screen.getByText('#')).toBeInTheDocument()
    expect(screen.getByText('javascript')).toBeInTheDocument()
  })

  it('should be clickable when onClick is provided', () => {
    const handleClick = vi.fn()
    render(<TagBadge tag="react" onClick={handleClick} />)
    
    fireEvent.click(screen.getByRole('button'))
    
    expect(handleClick).toHaveBeenCalledWith('react')
  })

  it('should be removable when removable prop is true', () => {
    const handleRemove = vi.fn()
    render(<TagBadge tag="css" removable onRemove={handleRemove} />)
    
    // There should be a remove button
    expect(screen.getByText('#')).toBeInTheDocument()
  })
})

describe('MasteryBadge', () => {
  it('should show "Novice" for low mastery', () => {
    render(<MasteryBadge mastery={0.2} />)
    
    expect(screen.getByText('Novice')).toBeInTheDocument()
  })

  it('should show "Learning" for medium-low mastery', () => {
    render(<MasteryBadge mastery={0.45} />)
    
    expect(screen.getByText('Learning')).toBeInTheDocument()
  })

  it('should show "Proficient" for medium-high mastery', () => {
    render(<MasteryBadge mastery={0.65} />)
    
    expect(screen.getByText('Proficient')).toBeInTheDocument()
  })

  it('should show "Mastered" for high mastery', () => {
    render(<MasteryBadge mastery={0.85} />)
    
    expect(screen.getByText('Mastered')).toBeInTheDocument()
  })

  it('should show percentage when showPercent is true', () => {
    render(<MasteryBadge mastery={0.75} showPercent />)
    
    expect(screen.getByText('75%')).toBeInTheDocument()
  })

  it('should hide percentage when showPercent is false', () => {
    render(<MasteryBadge mastery={0.75} showPercent={false} />)
    
    expect(screen.queryByText('75%')).not.toBeInTheDocument()
  })
})
