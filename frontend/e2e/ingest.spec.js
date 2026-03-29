/**
 * Ingest Page E2E Tests
 *
 * Tests the Ingest page including capture forms, ingestion queue,
 * and status filtering.
 *
 * Run with: npx playwright test ingest.spec.js
 */

import { test, expect } from '@playwright/test'

// Mock queue items for API mocking
const MOCK_QUEUE_RESPONSE = {
  items: [
    {
      id: 1,
      content_uuid: 'uuid-001',
      title: 'Introduction to Machine Learning',
      content_type: 'article',
      source_url: 'https://example.com/ml-intro',
      status: 'PROCESSED',
      processing_status: 'completed',
      error_message: null,
      vault_path: 'sources/articles/ml-intro.md',
      created_at: '2026-01-15T10:00:00Z',
      updated_at: '2026-01-15T10:05:00Z',
    },
    {
      id: 2,
      content_uuid: 'uuid-002',
      title: 'Deep Learning Paper',
      content_type: 'paper',
      source_url: null,
      status: 'PENDING',
      processing_status: null,
      error_message: null,
      vault_path: null,
      created_at: '2026-01-15T11:00:00Z',
      updated_at: '2026-01-15T11:00:00Z',
    },
    {
      id: 3,
      content_uuid: 'uuid-003',
      title: 'Broken Article Import',
      content_type: 'article',
      source_url: 'https://example.com/broken',
      status: 'FAILED',
      processing_status: 'failed',
      error_message: 'Connection timeout after 30s',
      vault_path: null,
      created_at: '2026-01-15T09:00:00Z',
      updated_at: '2026-01-15T09:01:00Z',
    },
    {
      id: 4,
      content_uuid: 'uuid-004',
      title: 'Voice Memo - Project Ideas',
      content_type: 'voice',
      source_url: null,
      status: 'PROCESSING',
      processing_status: 'processing',
      error_message: null,
      vault_path: null,
      created_at: '2026-01-15T12:00:00Z',
      updated_at: '2026-01-15T12:00:00Z',
    },
  ],
  total: 4,
  limit: 50,
  offset: 0,
  has_more: false,
}

const MOCK_DETAIL_RESPONSE = {
  id: 3,
  content_uuid: 'uuid-003',
  title: 'Broken Article Import',
  content_type: 'article',
  source_url: 'https://example.com/broken',
  source_path: null,
  vault_path: null,
  status: 'FAILED',
  summary: null,
  metadata: {},
  created_at: '2026-01-15T09:00:00Z',
  processed_at: null,
  updated_at: '2026-01-15T09:01:00Z',
  ingestion_error: null,
  processing: {
    status: 'failed',
    started_at: '2026-01-15T09:00:30Z',
    completed_at: null,
    processing_time_seconds: null,
    estimated_cost_usd: null,
    error_message: 'Connection timeout after 30s',
    stages_completed: ['content_analysis'],
    models_used: null,
    total_tokens: null,
  },
  processing_runs_count: 1,
}

/**
 * Setup API route mocking for the ingest page.
 */
async function setupMockRoutes(page) {
  // Mock the queue items endpoint
  await page.route('**/api/ingestion/queue/combined**', (route) => {
    const url = new URL(route.request().url())
    const status = url.searchParams.get('status')

    if (status) {
      const filtered = {
        ...MOCK_QUEUE_RESPONSE,
        items: MOCK_QUEUE_RESPONSE.items.filter(
          (item) => item.status.toLowerCase() === status
        ),
      }
      filtered.total = filtered.items.length
      route.fulfill({ json: filtered })
    } else {
      route.fulfill({ json: MOCK_QUEUE_RESPONSE })
    }
  })

  // Mock the detail endpoint
  await page.route('**/api/ingestion/queue/*/detail', (route) => {
    route.fulfill({ json: MOCK_DETAIL_RESPONSE })
  })

  // Mock the capture endpoints
  await page.route('**/api/capture/text', (route) => {
    route.fulfill({
      json: {
        status: 'captured',
        content_id: 'new-uuid-001',
        title: 'Test capture',
        message: 'Content captured and queued',
      },
    })
  })

  await page.route('**/api/capture/url', (route) => {
    route.fulfill({
      json: {
        status: 'captured',
        content_id: 'new-uuid-002',
        title: 'Example Article',
        url: 'https://example.com',
        message: 'URL captured and queued',
      },
    })
  })
}

test.describe('Ingest Page', () => {
  test.beforeEach(async ({ page }) => {
    await setupMockRoutes(page)
  })

  test('should load the ingest page', async ({ page }) => {
    await page.goto('/ingest')
    await page.waitForLoadState('domcontentloaded')

    // Page header should be visible
    await expect(page.locator('h1:text("Ingest")')).toBeVisible()

    // Capture panel should be visible
    await expect(page.locator('text=Capture Content')).toBeVisible()

    // Queue should be visible
    await expect(page.locator('text=Ingestion Queue')).toBeVisible()
  })

  test('should show capture tabs', async ({ page }) => {
    await page.goto('/ingest')
    await page.waitForLoadState('domcontentloaded')

    await expect(page.locator('role=tab[name="Text"]')).toBeVisible()
    await expect(page.locator('role=tab[name="URL"]')).toBeVisible()
    await expect(page.locator('role=tab[name="File"]')).toBeVisible()
  })

  test('should show text capture form by default', async ({ page }) => {
    await page.goto('/ingest')
    await page.waitForLoadState('domcontentloaded')

    await expect(page.locator('text=Quick Note')).toBeVisible()
    await expect(
      page.locator('textarea[placeholder="What\'s on your mind?"]')
    ).toBeVisible()
  })

  test('should switch to URL capture form', async ({ page }) => {
    await page.goto('/ingest')
    await page.waitForLoadState('domcontentloaded')

    await page.click('role=tab[name="URL"]')

    await expect(page.locator('text=Save URL')).toBeVisible()
    await expect(page.locator('input[placeholder="https://..."]')).toBeVisible()
  })

  test('should switch to file upload form', async ({ page }) => {
    await page.goto('/ingest')
    await page.waitForLoadState('domcontentloaded')

    await page.click('role=tab[name="File"]')

    await expect(page.locator('text=Upload File')).toBeVisible()
    await expect(page.locator('text=Drop a file here')).toBeVisible()
  })

  test('should submit text capture successfully', async ({ page }) => {
    await page.goto('/ingest')
    await page.waitForLoadState('domcontentloaded')

    // Type text
    await page.fill(
      'textarea[placeholder="What\'s on your mind?"]',
      'My test idea for the knowledge base'
    )

    // Click capture button
    await page.click('button:text("Capture")')

    // Textarea should clear after success
    await expect(
      page.locator('textarea[placeholder="What\'s on your mind?"]')
    ).toHaveValue('')
  })

  test('should submit URL capture successfully', async ({ page }) => {
    await page.goto('/ingest')
    await page.waitForLoadState('domcontentloaded')

    // Switch to URL tab
    await page.click('role=tab[name="URL"]')

    // Enter URL
    await page.fill('input[placeholder="https://..."]', 'https://example.com/article')

    // Click capture button
    await page.click('button:text("Capture")')

    // Input should clear after success
    await expect(page.locator('input[placeholder="https://..."]')).toHaveValue(
      ''
    )
  })

  test('should show queue items with statuses', async ({ page }) => {
    await page.goto('/ingest')
    await page.waitForTimeout(1500)

    // Items should be visible
    await expect(
      page.locator('text=Introduction to Machine Learning')
    ).toBeVisible()
    await expect(page.locator('text=Deep Learning Paper')).toBeVisible()
    await expect(page.locator('text=Broken Article Import')).toBeVisible()
    await expect(
      page.locator('text=Voice Memo - Project Ideas')
    ).toBeVisible()

    // Status badges should be visible
    await expect(page.locator('text=PROCESSED')).toBeVisible()
    await expect(page.locator('text=PENDING')).toBeVisible()
    await expect(page.locator('text=FAILED')).toBeVisible()
    await expect(page.locator('text=PROCESSING')).toBeVisible()
  })

  test('should filter queue by status', async ({ page }) => {
    await page.goto('/ingest')
    await page.waitForTimeout(1500)

    // Click Failed filter
    await page.click('role=tab[name="Failed"]')
    await page.waitForTimeout(500)

    // Should show only failed items
    await expect(page.locator('text=Broken Article Import')).toBeVisible()
  })

  test('should show detail panel when clicking an item', async ({ page }) => {
    await page.goto('/ingest')
    await page.waitForTimeout(1500)

    // Click on a queue item
    await page.click('text=Broken Article Import')
    await page.waitForTimeout(500)

    // Detail panel should show processing error
    await expect(page.locator('text=Error Details')).toBeVisible()
    await expect(
      page.locator('text=Connection timeout after 30s')
    ).toBeVisible()
  })

  test('should show status filter tabs with correct aria-selected', async ({
    page,
  }) => {
    await page.goto('/ingest')
    await page.waitForLoadState('domcontentloaded')

    // All tab should be selected by default
    const allTab = page.locator('role=tab[name="All"]')
    await expect(allTab).toHaveAttribute('aria-selected', 'true')

    // Click Pending tab
    const pendingTab = page.locator('role=tab[name="Pending"]')
    await pendingTab.click()
    await expect(pendingTab).toHaveAttribute('aria-selected', 'true')
    await expect(allTab).toHaveAttribute('aria-selected', 'false')
  })

  test('should be accessible via sidebar navigation', async ({ page }) => {
    await page.goto('/')
    await page.waitForLoadState('domcontentloaded')

    // Click the ingest nav link
    await page.click('nav a[href="/ingest"]')
    await expect(page).toHaveURL('/ingest')

    // Page should render
    await expect(page.locator('h1:text("Ingest")')).toBeVisible()
  })
})
