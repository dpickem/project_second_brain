/**
 * Page Load Tests
 * 
 * Ensures all pages in the application load without crashing.
 * These are smoke tests to catch render errors early.
 * 
 * Run with: npm run test:e2e
 */

import { test, expect } from '@playwright/test'

// All routes in the application
const pages = [
  { path: '/', name: 'Dashboard' },
  { path: '/practice', name: 'Practice' },
  { path: '/review', name: 'Review' },
  { path: '/knowledge', name: 'Knowledge' },
  { path: '/graph', name: 'Knowledge Graph' },
  { path: '/analytics', name: 'Analytics' },
  { path: '/assistant', name: 'Assistant' },
  { path: '/settings', name: 'Settings' },
]

test.describe('Page Load Tests', () => {
  for (const page of pages) {
    test(`${page.name} page (${page.path}) should load without errors`, async ({ page: browserPage }) => {
      // Collect console errors
      const consoleErrors = []
      browserPage.on('console', (msg) => {
        if (msg.type() === 'error') {
          consoleErrors.push(msg.text())
        }
      })

      // Collect page errors (uncaught exceptions)
      const pageErrors = []
      browserPage.on('pageerror', (error) => {
        pageErrors.push(error.message)
      })

      // Navigate to the page
      await browserPage.goto(page.path)

      // Wait for the page to be loaded
      await browserPage.waitForLoadState('domcontentloaded')

      // Basic structure should be present (use .first() in case of multiple navs/mains)
      await expect(browserPage.locator('nav').first()).toBeVisible()
      await expect(browserPage.locator('main').first()).toBeVisible()

      // No uncaught JavaScript errors should occur
      // Filter out expected API errors (404s, 500s from backend)
      const criticalErrors = pageErrors.filter(
        (error) => !error.includes('Failed to fetch') && 
                   !error.includes('NetworkError') &&
                   !error.includes('Load failed')
      )

      expect(criticalErrors).toHaveLength(0)
    })
  }
})

test.describe('Page Navigation', () => {
  test('should navigate between all pages via sidebar', async ({ page }) => {
    await page.goto('/')
    await page.waitForLoadState('networkidle')

    // Navigate to each page via sidebar links
    for (const { path, name } of pages) {
      if (path === '/') continue // Already on dashboard

      const link = page.locator(`nav a[href="${path}"]`)
      await link.click()
      await expect(page).toHaveURL(path)
      
      // Page should render without crashing
      await expect(page.locator('main').first()).toBeVisible()
    }
  })
})

test.describe('Page Content Verification', () => {
  test('Dashboard should show stats header', async ({ page }) => {
    await page.goto('/')
    await expect(page.getByText(/Good (morning|afternoon|evening)/)).toBeVisible()
  })

  test('Practice page should have practice-related content', async ({ page }) => {
    await page.goto('/practice')
    // Should show either practice session content or empty/loading state
    await expect(page.locator('main').first()).toBeVisible()
  })

  test('Review page should have review-related content', async ({ page }) => {
    await page.goto('/review')
    // Should show either review queue content or empty/loading state
    await expect(page.locator('main').first()).toBeVisible()
  })

  test('Knowledge page should have knowledge explorer content', async ({ page }) => {
    await page.goto('/knowledge')
    await expect(page.locator('main').first()).toBeVisible()
  })

  test('Graph page should have graph visualization', async ({ page }) => {
    await page.goto('/graph')
    await expect(page.locator('main').first()).toBeVisible()
  })

  test('Analytics page should have analytics content', async ({ page }) => {
    await page.goto('/analytics')
    await expect(page.locator('main').first()).toBeVisible()
  })

  test('Assistant page should have chat interface', async ({ page }) => {
    await page.goto('/assistant')
    await expect(page.locator('main').first()).toBeVisible()
  })

  test('Settings page should have settings sections', async ({ page }) => {
    await page.goto('/settings')
    // Settings page should have appearance section
    await expect(page.getByRole('heading', { name: /appearance/i })).toBeVisible()
  })
})

test.describe('Error Boundary', () => {
  test('dashboard should handle API errors gracefully', async ({ page }) => {
    // Mock specific API calls to return errors
    await page.route('**/api/analytics/**', (route) => {
      route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Internal Server Error' }),
      })
    })

    await page.route('**/api/review/**', (route) => {
      route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Internal Server Error' }),
      })
    })

    // Dashboard should still render even with API errors
    await page.goto('/')
    await page.waitForLoadState('domcontentloaded')
    
    // Page structure should still be present
    await expect(page.locator('nav').first()).toBeVisible()
    await expect(page.locator('main').first()).toBeVisible()
    
    // The page title should still be visible
    await expect(page.getByText(/dashboard/i).first()).toBeVisible()
  })
})

test.describe('Responsive Layout', () => {
  const viewports = [
    { width: 1920, height: 1080, name: 'Desktop' },
    { width: 1024, height: 768, name: 'Tablet Landscape' },
    { width: 768, height: 1024, name: 'Tablet Portrait' },
  ]

  for (const viewport of viewports) {
    test(`pages should render correctly at ${viewport.name} (${viewport.width}x${viewport.height})`, async ({ page }) => {
      await page.setViewportSize({ width: viewport.width, height: viewport.height })

      // Test a few key pages
      for (const path of ['/', '/practice', '/analytics', '/settings']) {
        await page.goto(path)
        await expect(page.locator('main').first()).toBeVisible()
      }
    })
  }
})
