/**
 * Tests for CapturePanel Component
 *
 * Tests the tabbed capture interface including tab switching
 * and form rendering for Text, URL, and File capture modes.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderWithProviders, screen, fireEvent, waitFor } from '../../test/test-utils'
import { CapturePanel } from './CapturePanel'

// Mock the capture API
vi.mock('../../api/capture', () => ({
  captureApi: {
    captureText: vi.fn(),
    captureUrl: vi.fn(),
    captureFile: vi.fn(),
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

describe('CapturePanel', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    captureApi.captureText.mockResolvedValue({
      status: 'captured',
      id: 'test-id-123',
      title: 'Test Capture',
      message: 'Content captured and queued for processing',
    })
    captureApi.captureUrl.mockResolvedValue({
      status: 'captured',
      id: 'test-id-456',
      title: 'Test URL',
      message: 'URL captured and queued for processing',
    })
  })

  describe('rendering', () => {
    it('renders the capture panel with header', () => {
      renderWithProviders(<CapturePanel />)

      expect(screen.getByText('Capture Content')).toBeInTheDocument()
    })

    it('renders all three capture tabs', () => {
      renderWithProviders(<CapturePanel />)

      expect(screen.getByRole('tab', { name: /text/i })).toBeInTheDocument()
      expect(screen.getByRole('tab', { name: /url/i })).toBeInTheDocument()
      expect(screen.getByRole('tab', { name: /file/i })).toBeInTheDocument()
    })

    it('shows the text capture form by default', () => {
      renderWithProviders(<CapturePanel />)

      expect(screen.getByText('Quick Note')).toBeInTheDocument()
      expect(screen.getByPlaceholderText(/what's on your mind/i)).toBeInTheDocument()
    })

    it('has text tab selected by default', () => {
      renderWithProviders(<CapturePanel />)

      const textTab = screen.getByRole('tab', { name: /text/i })
      expect(textTab).toHaveAttribute('aria-selected', 'true')
    })
  })

  describe('tab switching', () => {
    it('switches to URL form when URL tab is clicked', () => {
      renderWithProviders(<CapturePanel />)

      fireEvent.click(screen.getByRole('tab', { name: /url/i }))

      expect(screen.getByText('Save URL')).toBeInTheDocument()
      expect(screen.getByPlaceholderText('https://...')).toBeInTheDocument()
    })

    it('switches to File form when File tab is clicked', () => {
      renderWithProviders(<CapturePanel />)

      fireEvent.click(screen.getByRole('tab', { name: /file/i }))

      expect(screen.getByText('Upload File')).toBeInTheDocument()
      expect(screen.getByText(/drop a file here/i)).toBeInTheDocument()
    })

    it('switches back to Text form from URL tab', () => {
      renderWithProviders(<CapturePanel />)

      // Go to URL tab
      fireEvent.click(screen.getByRole('tab', { name: /url/i }))
      expect(screen.getByText('Save URL')).toBeInTheDocument()

      // Go back to Text tab
      fireEvent.click(screen.getByRole('tab', { name: /text/i }))
      expect(screen.getByText('Quick Note')).toBeInTheDocument()
    })

    it('updates aria-selected when switching tabs', () => {
      renderWithProviders(<CapturePanel />)

      const urlTab = screen.getByRole('tab', { name: /url/i })
      const textTab = screen.getByRole('tab', { name: /text/i })

      fireEvent.click(urlTab)

      expect(urlTab).toHaveAttribute('aria-selected', 'true')
      expect(textTab).toHaveAttribute('aria-selected', 'false')
    })
  })

  describe('text capture submission', () => {
    it('submits text content via the text form', async () => {
      renderWithProviders(<CapturePanel />)

      const textarea = screen.getByPlaceholderText(/what's on your mind/i)
      const captureButton = screen.getByRole('button', { name: /capture/i })

      fireEvent.change(textarea, { target: { value: 'My test idea' } })
      fireEvent.click(captureButton)

      await waitFor(() => {
        expect(captureApi.captureText).toHaveBeenCalled()
        const callArgs = captureApi.captureText.mock.calls[0][0]
        expect(callArgs.text).toBe('My test idea')
      })
    })

    it('disables capture button when text is empty', () => {
      renderWithProviders(<CapturePanel />)

      const captureButton = screen.getByRole('button', { name: /capture/i })
      expect(captureButton).toBeDisabled()
    })

    it('shows success toast on successful text capture', async () => {
      renderWithProviders(<CapturePanel />)

      const textarea = screen.getByPlaceholderText(/what's on your mind/i)
      const captureButton = screen.getByRole('button', { name: /capture/i })

      fireEvent.change(textarea, { target: { value: 'Test content' } })
      fireEvent.click(captureButton)

      await waitFor(() => {
        expect(toast.success).toHaveBeenCalledWith('Text captured successfully!')
      })
    })

    it('calls onCaptureSuccess callback on successful capture', async () => {
      const onSuccess = vi.fn()
      renderWithProviders(<CapturePanel onCaptureSuccess={onSuccess} />)

      const textarea = screen.getByPlaceholderText(/what's on your mind/i)
      const captureButton = screen.getByRole('button', { name: /capture/i })

      fireEvent.change(textarea, { target: { value: 'Test content' } })
      fireEvent.click(captureButton)

      await waitFor(() => {
        expect(onSuccess).toHaveBeenCalled()
      })
    })
  })

  describe('URL capture', () => {
    it('validates URL format', () => {
      renderWithProviders(<CapturePanel />)

      fireEvent.click(screen.getByRole('tab', { name: /url/i }))

      const input = screen.getByPlaceholderText('https://...')
      const captureButton = screen.getByRole('button', { name: /capture/i })

      // Invalid URL - button should be disabled
      fireEvent.change(input, { target: { value: 'not-a-url' } })
      expect(captureButton).toBeDisabled()

      // Valid URL - button should be enabled
      fireEvent.change(input, { target: { value: 'https://example.com' } })
      expect(captureButton).not.toBeDisabled()
    })

    it('shows validation message for invalid URLs', () => {
      renderWithProviders(<CapturePanel />)

      fireEvent.click(screen.getByRole('tab', { name: /url/i }))

      const input = screen.getByPlaceholderText('https://...')
      fireEvent.change(input, { target: { value: 'not-a-url' } })

      expect(screen.getByText(/please enter a valid url/i)).toBeInTheDocument()
    })
  })

  describe('file capture', () => {
    it('shows drop zone with supported file types', () => {
      renderWithProviders(<CapturePanel />)

      fireEvent.click(screen.getByRole('tab', { name: /file/i }))

      expect(screen.getByText(/drop a file here/i)).toBeInTheDocument()
      expect(screen.getByText(/pdf, images/i)).toBeInTheDocument()
    })

    it('has hidden file input element', () => {
      renderWithProviders(<CapturePanel />)

      fireEvent.click(screen.getByRole('tab', { name: /file/i }))

      const fileInput = document.querySelector('input[type="file"]')
      expect(fileInput).toBeInTheDocument()
    })
  })
})
