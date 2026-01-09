/**
 * Input Component Tests
 */

import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '../../test/test-utils'
import { Input, Textarea, SearchInput, Select, Checkbox } from './Input'

describe('Input', () => {
  describe('Rendering', () => {
    it('should render an input element', () => {
      render(<Input placeholder="Enter text" />)
      
      expect(screen.getByPlaceholderText('Enter text')).toBeInTheDocument()
    })

    it('should render with label', () => {
      render(<Input label="Username" />)
      
      expect(screen.getByText('Username')).toBeInTheDocument()
    })

    it('should render with hint text', () => {
      render(<Input hint="Enter your email address" />)
      
      expect(screen.getByText('Enter your email address')).toBeInTheDocument()
    })
  })

  describe('Sizes', () => {
    it('should apply sm size', () => {
      render(<Input size="sm" placeholder="Small" />)
      
      expect(screen.getByPlaceholderText('Small')).toHaveClass('px-3', 'py-1.5', 'text-sm')
    })

    it('should apply md size', () => {
      render(<Input size="md" placeholder="Medium" />)
      
      expect(screen.getByPlaceholderText('Medium')).toHaveClass('px-4', 'py-2.5')
    })

    it('should apply lg size', () => {
      render(<Input size="lg" placeholder="Large" />)
      
      expect(screen.getByPlaceholderText('Large')).toHaveClass('px-5', 'py-3', 'text-base')
    })
  })

  describe('Error state', () => {
    it('should show error message', () => {
      render(<Input error="This field is required" />)
      
      expect(screen.getByText('This field is required')).toBeInTheDocument()
    })

    it('should apply error styles', () => {
      render(<Input error="Error" placeholder="Input" />)
      
      expect(screen.getByPlaceholderText('Input')).toHaveClass('border-accent-danger')
    })

    it('should show error over hint when both provided', () => {
      render(<Input error="Error message" hint="Hint message" />)
      
      expect(screen.getByText('Error message')).toBeInTheDocument()
      expect(screen.queryByText('Hint message')).not.toBeInTheDocument()
    })
  })

  describe('Icon support', () => {
    const MockIcon = () => <svg data-testid="input-icon" />

    it('should render icon on the left by default', () => {
      render(<Input icon={<MockIcon />} placeholder="With icon" />)
      
      expect(screen.getByTestId('input-icon')).toBeInTheDocument()
      expect(screen.getByPlaceholderText('With icon')).toHaveClass('pl-10')
    })

    it('should render icon on the right when specified', () => {
      render(<Input icon={<MockIcon />} iconPosition="right" placeholder="Right icon" />)
      
      expect(screen.getByTestId('input-icon')).toBeInTheDocument()
      expect(screen.getByPlaceholderText('Right icon')).toHaveClass('pr-10')
    })
  })

  describe('Password type', () => {
    it('should render password input with type password', () => {
      render(<Input type="password" placeholder="Password" />)
      
      expect(screen.getByPlaceholderText('Password')).toHaveAttribute('type', 'password')
    })

    it('should toggle password visibility', () => {
      render(<Input type="password" placeholder="Password" />)
      
      const input = screen.getByPlaceholderText('Password')
      expect(input).toHaveAttribute('type', 'password')
      
      // Click toggle button
      fireEvent.click(screen.getByRole('button'))
      expect(input).toHaveAttribute('type', 'text')
      
      // Click again to hide
      fireEvent.click(screen.getByRole('button'))
      expect(input).toHaveAttribute('type', 'password')
    })
  })

  describe('Events', () => {
    it('should call onChange when value changes', () => {
      const handleChange = vi.fn()
      render(<Input onChange={handleChange} placeholder="Input" />)
      
      fireEvent.change(screen.getByPlaceholderText('Input'), { target: { value: 'test' } })
      
      expect(handleChange).toHaveBeenCalled()
    })
  })

  describe('Disabled state', () => {
    it('should be disabled when disabled prop is true', () => {
      render(<Input disabled placeholder="Disabled" />)
      
      expect(screen.getByPlaceholderText('Disabled')).toBeDisabled()
    })
  })
})

describe('Textarea', () => {
  it('should render a textarea element', () => {
    render(<Textarea placeholder="Enter text" />)
    
    expect(screen.getByPlaceholderText('Enter text').tagName).toBe('TEXTAREA')
  })

  it('should render with label', () => {
    render(<Textarea label="Description" />)
    
    expect(screen.getByText('Description')).toBeInTheDocument()
  })

  it('should apply custom rows', () => {
    render(<Textarea rows={6} placeholder="Textarea" />)
    
    expect(screen.getByPlaceholderText('Textarea')).toHaveAttribute('rows', '6')
  })

  it('should show error message', () => {
    render(<Textarea error="Required field" />)
    
    expect(screen.getByText('Required field')).toBeInTheDocument()
  })
})

describe('SearchInput', () => {
  it('should render with default placeholder', () => {
    render(<SearchInput />)
    
    expect(screen.getByPlaceholderText('Search...')).toBeInTheDocument()
  })

  it('should render with custom placeholder', () => {
    render(<SearchInput placeholder="Find something..." />)
    
    expect(screen.getByPlaceholderText('Find something...')).toBeInTheDocument()
  })

  it('should show clear button when value exists', () => {
    const handleClear = vi.fn()
    render(<SearchInput value="test" onClear={handleClear} onChange={() => {}} />)
    
    fireEvent.click(screen.getByRole('button'))
    
    expect(handleClear).toHaveBeenCalled()
  })

  it('should not show clear button when value is empty', () => {
    render(<SearchInput value="" onClear={() => {}} onChange={() => {}} />)
    
    expect(screen.queryByRole('button')).not.toBeInTheDocument()
  })
})

describe('Select', () => {
  const options = [
    { value: 'opt1', label: 'Option 1' },
    { value: 'opt2', label: 'Option 2' },
    { value: 'opt3', label: 'Option 3', disabled: true },
  ]

  it('should render a select element', () => {
    render(<Select options={options} />)
    
    expect(screen.getByRole('combobox')).toBeInTheDocument()
  })

  it('should render with label', () => {
    render(<Select label="Choose option" options={options} />)
    
    expect(screen.getByText('Choose option')).toBeInTheDocument()
  })

  it('should render placeholder option', () => {
    render(<Select options={options} placeholder="Select one..." />)
    
    expect(screen.getByText('Select one...')).toBeInTheDocument()
  })

  it('should render all options', () => {
    render(<Select options={options} />)
    
    expect(screen.getByText('Option 1')).toBeInTheDocument()
    expect(screen.getByText('Option 2')).toBeInTheDocument()
    expect(screen.getByText('Option 3')).toBeInTheDocument()
  })

  it('should disable option when option.disabled is true', () => {
    render(<Select options={options} />)
    
    const option3 = screen.getByText('Option 3')
    expect(option3).toBeDisabled()
  })

  it('should show error message', () => {
    render(<Select options={options} error="Please select an option" />)
    
    expect(screen.getByText('Please select an option')).toBeInTheDocument()
  })
})

describe('Checkbox', () => {
  it('should render a checkbox input', () => {
    render(<Checkbox />)
    
    expect(screen.getByRole('checkbox')).toBeInTheDocument()
  })

  it('should render with label', () => {
    render(<Checkbox label="Accept terms" />)
    
    expect(screen.getByText('Accept terms')).toBeInTheDocument()
  })

  it('should render with description', () => {
    render(<Checkbox label="Newsletter" description="Receive weekly updates" />)
    
    expect(screen.getByText('Newsletter')).toBeInTheDocument()
    expect(screen.getByText('Receive weekly updates')).toBeInTheDocument()
  })

  it('should toggle checked state', () => {
    const handleChange = vi.fn()
    render(<Checkbox onChange={handleChange} />)
    
    const checkbox = screen.getByRole('checkbox')
    fireEvent.click(checkbox)
    
    expect(handleChange).toHaveBeenCalled()
  })

  it('should apply error styles', () => {
    render(<Checkbox error="Must accept terms" />)
    
    expect(screen.getByRole('checkbox')).toHaveClass('border-accent-danger')
  })
})
