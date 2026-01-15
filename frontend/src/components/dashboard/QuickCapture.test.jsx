/**
 * Tests for QuickCapture Component
 * 
 * Tests the Quick Capture widget including the toggles for
 * creating cards and exercises.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderWithProviders, screen, fireEvent, waitFor } from '../../test/test-utils'
import { QuickCapture } from './QuickCapture'

// Mock the capture API
vi.mock('../../api/capture', () => ({
  captureApi: {
    captureText: vi.fn(),
  },
}))

// Mock react-hot-toast
vi.mock('react-hot-toast', () => ({
  default: {
    success: vi.fn(),
    error: vi.fn(),
  },
}))

import { captureApi } from '../../api/capture'
import toast from 'react-hot-toast'

describe('QuickCapture', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    captureApi.captureText.mockResolvedValue({
      status: 'captured',
      id: 'test-id-123',
      title: 'Test Capture',
      message: 'Content captured and queued for processing',
    })
  })

  // Helper to get checkboxes by their id
  const getCardsCheckbox = () => document.getElementById('create-cards')
  const getExercisesCheckbox = () => document.getElementById('create-exercises')

  describe('rendering', () => {
    it('renders the quick capture form', () => {
      renderWithProviders(<QuickCapture />)

      expect(screen.getByText('Quick Capture')).toBeInTheDocument()
      expect(screen.getByPlaceholderText(/capture a thought/i)).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /capture/i })).toBeInTheDocument()
    })

    it('renders the create cards checkbox', () => {
      renderWithProviders(<QuickCapture />)

      expect(screen.getByText('Create Cards')).toBeInTheDocument()
      expect(getCardsCheckbox()).toBeInTheDocument()
    })

    it('renders the create exercises checkbox', () => {
      renderWithProviders(<QuickCapture />)

      expect(screen.getByText('Create Exercises')).toBeInTheDocument()
      expect(getExercisesCheckbox()).toBeInTheDocument()
    })

    it('has checkboxes unchecked by default', () => {
      renderWithProviders(<QuickCapture />)

      expect(getCardsCheckbox()).not.toBeChecked()
      expect(getExercisesCheckbox()).not.toBeChecked()
    })
  })

  describe('interaction', () => {
    it('allows toggling create cards checkbox', async () => {
      renderWithProviders(<QuickCapture />)

      const cardsCheckbox = getCardsCheckbox()
      
      expect(cardsCheckbox).not.toBeChecked()
      
      fireEvent.click(cardsCheckbox)
      
      expect(cardsCheckbox).toBeChecked()
      
      fireEvent.click(cardsCheckbox)
      
      expect(cardsCheckbox).not.toBeChecked()
    })

    it('allows toggling create exercises checkbox', async () => {
      renderWithProviders(<QuickCapture />)

      const exercisesCheckbox = getExercisesCheckbox()
      
      expect(exercisesCheckbox).not.toBeChecked()
      
      fireEvent.click(exercisesCheckbox)
      
      expect(exercisesCheckbox).toBeChecked()
    })

    it('allows typing in the textarea', () => {
      renderWithProviders(<QuickCapture />)

      const textarea = screen.getByPlaceholderText(/capture a thought/i)
      
      fireEvent.change(textarea, { target: { value: 'Test idea content' } })
      
      expect(textarea).toHaveValue('Test idea content')
    })

    it('disables capture button when textarea is empty', () => {
      renderWithProviders(<QuickCapture />)

      const button = screen.getByRole('button', { name: /capture/i })
      
      expect(button).toBeDisabled()
    })

    it('enables capture button when textarea has content', () => {
      renderWithProviders(<QuickCapture />)

      const textarea = screen.getByPlaceholderText(/capture a thought/i)
      const button = screen.getByRole('button', { name: /capture/i })
      
      fireEvent.change(textarea, { target: { value: 'Test idea' } })
      
      expect(button).not.toBeDisabled()
    })
  })

  describe('submission', () => {
    it('submits with default false flags when checkboxes unchecked', async () => {
      renderWithProviders(<QuickCapture />)

      const textarea = screen.getByPlaceholderText(/capture a thought/i)
      const button = screen.getByRole('button', { name: /capture/i })

      fireEvent.change(textarea, { target: { value: 'Test idea content' } })
      fireEvent.click(button)

      await waitFor(() => {
        expect(captureApi.captureText).toHaveBeenCalled()
        const callArgs = captureApi.captureText.mock.calls[0][0]
        expect(callArgs.text).toBe('Test idea content')
        expect(callArgs.createCards).toBe(false)
        expect(callArgs.createExercises).toBe(false)
      })
    })

    it('submits with createCards=true when checkbox is checked', async () => {
      renderWithProviders(<QuickCapture />)

      const textarea = screen.getByPlaceholderText(/capture a thought/i)
      const button = screen.getByRole('button', { name: /capture/i })

      fireEvent.change(textarea, { target: { value: 'Test idea' } })
      fireEvent.click(getCardsCheckbox())
      fireEvent.click(button)

      await waitFor(() => {
        expect(captureApi.captureText).toHaveBeenCalled()
        const callArgs = captureApi.captureText.mock.calls[0][0]
        expect(callArgs.text).toBe('Test idea')
        expect(callArgs.createCards).toBe(true)
        expect(callArgs.createExercises).toBe(false)
      })
    })

    it('submits with createExercises=true when checkbox is checked', async () => {
      renderWithProviders(<QuickCapture />)

      const textarea = screen.getByPlaceholderText(/capture a thought/i)
      const button = screen.getByRole('button', { name: /capture/i })

      fireEvent.change(textarea, { target: { value: 'Test idea' } })
      fireEvent.click(getExercisesCheckbox())
      fireEvent.click(button)

      await waitFor(() => {
        expect(captureApi.captureText).toHaveBeenCalled()
        const callArgs = captureApi.captureText.mock.calls[0][0]
        expect(callArgs.text).toBe('Test idea')
        expect(callArgs.createCards).toBe(false)
        expect(callArgs.createExercises).toBe(true)
      })
    })

    it('submits with both flags true when both checkboxes are checked', async () => {
      renderWithProviders(<QuickCapture />)

      const textarea = screen.getByPlaceholderText(/capture a thought/i)
      const button = screen.getByRole('button', { name: /capture/i })

      fireEvent.change(textarea, { target: { value: 'Test idea' } })
      fireEvent.click(getCardsCheckbox())
      fireEvent.click(getExercisesCheckbox())
      fireEvent.click(button)

      await waitFor(() => {
        expect(captureApi.captureText).toHaveBeenCalled()
        const callArgs = captureApi.captureText.mock.calls[0][0]
        expect(callArgs.text).toBe('Test idea')
        expect(callArgs.createCards).toBe(true)
        expect(callArgs.createExercises).toBe(true)
      })
    })

    it('clears textarea after successful submission', async () => {
      renderWithProviders(<QuickCapture />)

      const textarea = screen.getByPlaceholderText(/capture a thought/i)
      const button = screen.getByRole('button', { name: /capture/i })

      fireEvent.change(textarea, { target: { value: 'Test idea' } })
      fireEvent.click(button)

      await waitFor(() => {
        expect(textarea).toHaveValue('')
      })
    })

    it('shows success toast after successful submission', async () => {
      renderWithProviders(<QuickCapture />)

      const textarea = screen.getByPlaceholderText(/capture a thought/i)
      const button = screen.getByRole('button', { name: /capture/i })

      fireEvent.change(textarea, { target: { value: 'Test idea' } })
      fireEvent.click(button)

      await waitFor(() => {
        expect(toast.success).toHaveBeenCalledWith('Captured successfully!')
      })
    })

    it('shows error toast on submission failure', async () => {
      captureApi.captureText.mockRejectedValueOnce(new Error('Network error'))

      renderWithProviders(<QuickCapture />)

      const textarea = screen.getByPlaceholderText(/capture a thought/i)
      const button = screen.getByRole('button', { name: /capture/i })

      fireEvent.change(textarea, { target: { value: 'Test idea' } })
      fireEvent.click(button)

      await waitFor(() => {
        expect(toast.error).toHaveBeenCalled()
      })
    })

    it('calls onSuccess callback after successful submission', async () => {
      const onSuccess = vi.fn()
      renderWithProviders(<QuickCapture onSuccess={onSuccess} />)

      const textarea = screen.getByPlaceholderText(/capture a thought/i)
      const button = screen.getByRole('button', { name: /capture/i })

      fireEvent.change(textarea, { target: { value: 'Test idea' } })
      fireEvent.click(button)

      await waitFor(() => {
        expect(onSuccess).toHaveBeenCalledWith({
          status: 'captured',
          id: 'test-id-123',
          title: 'Test Capture',
          message: 'Content captured and queued for processing',
        })
      })
    })
  })

  describe('keyboard shortcuts', () => {
    it('submits on Cmd+Enter', async () => {
      renderWithProviders(<QuickCapture />)

      const textarea = screen.getByPlaceholderText(/capture a thought/i)

      fireEvent.change(textarea, { target: { value: 'Test idea' } })
      fireEvent.keyDown(textarea, { key: 'Enter', metaKey: true })

      await waitFor(() => {
        expect(captureApi.captureText).toHaveBeenCalled()
      })
    })

    it('submits on Ctrl+Enter', async () => {
      renderWithProviders(<QuickCapture />)

      const textarea = screen.getByPlaceholderText(/capture a thought/i)

      fireEvent.change(textarea, { target: { value: 'Test idea' } })
      fireEvent.keyDown(textarea, { key: 'Enter', ctrlKey: true })

      await waitFor(() => {
        expect(captureApi.captureText).toHaveBeenCalled()
      })
    })

    it('does not submit on plain Enter', async () => {
      renderWithProviders(<QuickCapture />)

      const textarea = screen.getByPlaceholderText(/capture a thought/i)

      fireEvent.change(textarea, { target: { value: 'Test idea' } })
      fireEvent.keyDown(textarea, { key: 'Enter' })

      expect(captureApi.captureText).not.toHaveBeenCalled()
    })
  })
})
