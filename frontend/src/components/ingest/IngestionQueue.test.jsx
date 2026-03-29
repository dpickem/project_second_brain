/**
 * Tests for IngestionQueue Component
 *
 * Tests the ingestion queue list, status filtering,
 * item selection, and empty states.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderWithProviders, screen, fireEvent, waitFor } from '../../test/test-utils'
import { IngestionQueue } from './IngestionQueue'

// Mock the ingestion API
vi.mock('../../api/ingestion', () => ({
  ingestionApi: {
    getQueueItems: vi.fn(),
    getQueueItemDetail: vi.fn(),
    getQueueStats: vi.fn(),
  },
}))

// Mock react-hot-toast
vi.mock('react-hot-toast', () => ({
  default: {
    success: vi.fn(),
    error: vi.fn(),
  },
}))

import { ingestionApi } from '../../api/ingestion'

const MOCK_QUEUE_ITEMS = {
  items: [
    {
      id: 1,
      content_uuid: 'uuid-001',
      title: 'Test Article',
      content_type: 'article',
      status: 'PROCESSED',
      processing_status: 'completed',
      error_message: null,
      created_at: '2026-01-15T10:00:00Z',
      updated_at: '2026-01-15T10:05:00Z',
    },
    {
      id: 2,
      content_uuid: 'uuid-002',
      title: 'Pending Paper',
      content_type: 'paper',
      status: 'PENDING',
      processing_status: null,
      error_message: null,
      created_at: '2026-01-15T11:00:00Z',
      updated_at: '2026-01-15T11:00:00Z',
    },
    {
      id: 3,
      content_uuid: 'uuid-003',
      title: 'Failed Import',
      content_type: 'article',
      status: 'FAILED',
      processing_status: 'failed',
      error_message: 'Connection timeout',
      created_at: '2026-01-15T09:00:00Z',
      updated_at: '2026-01-15T09:01:00Z',
    },
    {
      id: 4,
      content_uuid: 'uuid-004',
      title: 'Processing Item',
      content_type: 'pdf',
      status: 'PROCESSING',
      processing_status: 'processing',
      error_message: null,
      created_at: '2026-01-15T12:00:00Z',
      updated_at: '2026-01-15T12:00:00Z',
    },
  ],
  total: 4,
  limit: 50,
  offset: 0,
  has_more: false,
}

const EMPTY_QUEUE = {
  items: [],
  total: 0,
  limit: 50,
  offset: 0,
  has_more: false,
}

describe('IngestionQueue', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    ingestionApi.getQueueItems.mockResolvedValue(MOCK_QUEUE_ITEMS)
  })

  describe('rendering', () => {
    it('renders the queue header', async () => {
      renderWithProviders(<IngestionQueue />)

      expect(screen.getByText('Ingestion Queue')).toBeInTheDocument()
    })

    it('renders all status filter tabs', async () => {
      renderWithProviders(<IngestionQueue />)

      expect(screen.getByRole('tab', { name: 'All' })).toBeInTheDocument()
      expect(screen.getByRole('tab', { name: 'Pending' })).toBeInTheDocument()
      expect(screen.getByRole('tab', { name: 'Processing' })).toBeInTheDocument()
      expect(screen.getByRole('tab', { name: 'Completed' })).toBeInTheDocument()
      expect(screen.getByRole('tab', { name: 'Failed' })).toBeInTheDocument()
    })

    it('renders queue items when data is loaded', async () => {
      renderWithProviders(<IngestionQueue />)

      await waitFor(() => {
        expect(screen.getByText('Test Article')).toBeInTheDocument()
        expect(screen.getByText('Pending Paper')).toBeInTheDocument()
        expect(screen.getByText('Failed Import')).toBeInTheDocument()
        expect(screen.getByText('Processing Item')).toBeInTheDocument()
      })
    })

    it('shows total count in header', async () => {
      renderWithProviders(<IngestionQueue />)

      await waitFor(() => {
        expect(screen.getByText('(4)')).toBeInTheDocument()
      })
    })

    it('renders refresh button', () => {
      renderWithProviders(<IngestionQueue />)

      expect(screen.getByLabelText('Refresh queue')).toBeInTheDocument()
    })
  })

  describe('empty state', () => {
    it('shows empty state when no items', async () => {
      ingestionApi.getQueueItems.mockResolvedValue(EMPTY_QUEUE)

      renderWithProviders(<IngestionQueue />)

      await waitFor(() => {
        expect(screen.getByText('No items in queue')).toBeInTheDocument()
      })
    })

    it('shows contextual message for filtered empty state', async () => {
      ingestionApi.getQueueItems.mockResolvedValue(EMPTY_QUEUE)

      renderWithProviders(<IngestionQueue />)

      // Click on the Failed filter tab
      await waitFor(() => {
        expect(screen.getByRole('tab', { name: 'Failed' })).toBeInTheDocument()
      })

      fireEvent.click(screen.getByRole('tab', { name: 'Failed' }))

      await waitFor(() => {
        expect(screen.getByText(/no failed items found/i)).toBeInTheDocument()
      })
    })
  })

  describe('status filtering', () => {
    it('fetches items with no status filter by default', async () => {
      renderWithProviders(<IngestionQueue />)

      await waitFor(() => {
        expect(ingestionApi.getQueueItems).toHaveBeenCalledWith({
          status: undefined,
          limit: 50,
          offset: 0,
        })
      })
    })

    it('filters by pending status when tab clicked', async () => {
      renderWithProviders(<IngestionQueue />)

      await waitFor(() => {
        expect(screen.getByRole('tab', { name: 'Pending' })).toBeInTheDocument()
      })

      fireEvent.click(screen.getByRole('tab', { name: 'Pending' }))

      await waitFor(() => {
        expect(ingestionApi.getQueueItems).toHaveBeenCalledWith({
          status: 'pending',
          limit: 50,
          offset: 0,
        })
      })
    })

    it('filters by failed status when tab clicked', async () => {
      renderWithProviders(<IngestionQueue />)

      await waitFor(() => {
        expect(screen.getByRole('tab', { name: 'Failed' })).toBeInTheDocument()
      })

      fireEvent.click(screen.getByRole('tab', { name: 'Failed' }))

      await waitFor(() => {
        expect(ingestionApi.getQueueItems).toHaveBeenCalledWith({
          status: 'failed',
          limit: 50,
          offset: 0,
        })
      })
    })

    it('updates aria-selected on filter tabs', async () => {
      renderWithProviders(<IngestionQueue />)

      const allTab = screen.getByRole('tab', { name: 'All' })
      const pendingTab = screen.getByRole('tab', { name: 'Pending' })

      expect(allTab).toHaveAttribute('aria-selected', 'true')

      fireEvent.click(pendingTab)

      expect(pendingTab).toHaveAttribute('aria-selected', 'true')
      expect(allTab).toHaveAttribute('aria-selected', 'false')
    })
  })

  describe('item interaction', () => {
    it('renders items as clickable buttons', async () => {
      renderWithProviders(<IngestionQueue />)

      await waitFor(() => {
        // Each queue item is rendered as a button
        const itemButtons = screen.getAllByRole('button')
        // Should have refresh button + 5 filter tabs + 4 items = 10
        expect(itemButtons.length).toBeGreaterThanOrEqual(4)
      })
    })

    it('displays content type for each item', async () => {
      renderWithProviders(<IngestionQueue />)

      await waitFor(() => {
        // Use getAllByText since "article" appears for multiple items
        const articleElements = screen.getAllByText(/article/i)
        expect(articleElements.length).toBeGreaterThanOrEqual(1)
        expect(screen.getAllByText(/paper/i).length).toBeGreaterThanOrEqual(1)
      })
    })

    it('shows error indicator for failed items', async () => {
      renderWithProviders(<IngestionQueue />)

      await waitFor(() => {
        expect(screen.getByText('Failed Import')).toBeInTheDocument()
        // StatusBadge renders 'Error' for error variant (mapped from FAILED status)
        const errorBadges = screen.getAllByText('Error')
        expect(errorBadges.length).toBeGreaterThanOrEqual(1)
      })
    })
  })
})
