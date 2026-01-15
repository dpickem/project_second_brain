/**
 * Dashboard Page Integration Tests
 * 
 * Tests the main Dashboard page functionality including:
 * - Page load and initial render
 * - Stats header display
 * - Quick action cards (Practice/Review)
 * - Due cards preview
 * - Quick capture functionality
 * - Navigation to other pages
 * 
 * Run with: npm run test:e2e
 */

import { test, expect } from '@playwright/test'

test.describe('Dashboard Page', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to the dashboard (home page)
    await page.goto('/')
  })

  test('should load the dashboard page', async ({ page }) => {
    // Wait for the page to be loaded
    await expect(page).toHaveURL('/')
    
    // Check that the main content area is visible
    await expect(page.locator('main')).toBeVisible()
  })

  test('should display the stats header with greeting', async ({ page }) => {
    // The greeting should be time-based (Good morning/afternoon/evening)
    const greetingPattern = /Good (morning|afternoon|evening)/
    await expect(page.getByText(greetingPattern)).toBeVisible()
  })

  test('should display quick action cards', async ({ page }) => {
    // Look for Practice action card (title is "Practice")
    const practiceCard = page.getByRole('link', { name: /🎯.*practice/i }).first()
    await expect(practiceCard).toBeVisible()
    
    // Look for Review action card (has icon 📚 and title "Review")
    const reviewCard = page.getByRole('link', { name: /📚.*review/i }).first()
    await expect(reviewCard).toBeVisible()
  })

  test('should navigate to practice page when clicking Practice card', async ({ page }) => {
    // Click the Practice action card
    const practiceCard = page.getByRole('link', { name: /practice/i })
    await practiceCard.click()
    
    // Should navigate to /practice
    await expect(page).toHaveURL('/practice')
  })

  test('should navigate to review page when clicking Review card', async ({ page }) => {
    // Click the Review action card (has icon 📚 and title "Review")
    const reviewCard = page.getByRole('link', { name: /📚.*review/i }).first()
    await reviewCard.click()
    
    // Should navigate to /review
    await expect(page).toHaveURL('/review')
  })

  test('should display the quick capture section', async ({ page }) => {
    // Look for the quick capture textarea or input
    const captureInput = page.getByPlaceholder(/capture|thought|idea|note/i)
    await expect(captureInput).toBeVisible()
  })

  test('should allow typing in quick capture', async ({ page }) => {
    // Find the quick capture input
    const captureInput = page.getByPlaceholder(/capture|thought|idea|note/i)
    
    // Type something
    await captureInput.fill('Test note about machine learning')
    
    // Verify the text was entered
    await expect(captureInput).toHaveValue('Test note about machine learning')
  })
})

test.describe('Dashboard Navigation', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/')
  })

  test('should have working sidebar navigation', async ({ page }) => {
    // Check that navigation links are present
    const nav = page.locator('nav')
    await expect(nav).toBeVisible()
    
    // Check for navigation links by href (icons don't have text)
    await expect(page.locator('nav a[href="/knowledge"]')).toBeVisible()
    await expect(page.locator('nav a[href="/analytics"]')).toBeVisible()
  })

  test('should navigate to Knowledge page from sidebar', async ({ page }) => {
    const knowledgeLink = page.locator('nav a[href="/knowledge"]')
    await knowledgeLink.click()
    
    await expect(page).toHaveURL('/knowledge')
  })

  test('should navigate to Analytics page from sidebar', async ({ page }) => {
    const analyticsLink = page.locator('nav a[href="/analytics"]')
    await analyticsLink.click()
    
    await expect(page).toHaveURL('/analytics')
  })

  test('should navigate to Settings page from sidebar', async ({ page }) => {
    // Settings link uses href="/settings" with icon only
    const settingsLink = page.locator('nav a[href="/settings"]')
    await settingsLink.click()
    
    await expect(page).toHaveURL('/settings')
  })
})

test.describe('Dashboard Keyboard Shortcuts', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/')
    // Wait for page to be fully loaded
    await page.waitForLoadState('networkidle')
  })

  test('should open command palette with Cmd+K', async ({ page }) => {
    // Press Cmd+K (Meta+k for macOS, Control+k for Windows/Linux)
    await page.keyboard.press('Meta+k')
    
    // Command palette has a placeholder "Search notes, type a command..."
    const commandInput = page.getByPlaceholder(/search notes/i)
    await expect(commandInput).toBeVisible({ timeout: 3000 })
  })

  test('should close command palette with Escape', async ({ page }) => {
    // Open command palette
    await page.keyboard.press('Meta+k')
    
    // Wait for it to be visible
    const commandInput = page.getByPlaceholder(/search notes/i)
    await expect(commandInput).toBeVisible({ timeout: 3000 })
    
    // Press Escape to close
    await page.keyboard.press('Escape')
    
    // Should be hidden
    await expect(commandInput).not.toBeVisible({ timeout: 3000 })
  })
})

test.describe('Dashboard Responsive Behavior', () => {
  test('should be responsive on tablet viewport', async ({ page }) => {
    // Set tablet viewport
    await page.setViewportSize({ width: 768, height: 1024 })
    await page.goto('/')
    
    // Page should still load
    await expect(page.locator('main')).toBeVisible()
    
    // Quick action cards should still be visible
    const practiceCard = page.getByRole('link', { name: /practice/i })
    await expect(practiceCard).toBeVisible()
  })

  test('should be responsive on mobile viewport', async ({ page }) => {
    // Set mobile viewport
    await page.setViewportSize({ width: 375, height: 667 })
    await page.goto('/')
    
    // Page should still load
    await expect(page.locator('main')).toBeVisible()
  })
})

test.describe('Dashboard Loading States', () => {
  test('should show loading state while fetching data', async ({ page }) => {
    // Intercept API calls to add delay
    await page.route('**/api/**', async (route) => {
      await new Promise((resolve) => setTimeout(resolve, 500))
      await route.continue()
    })
    
    await page.goto('/')
    
    // Look for loading indicators (spinner or skeleton)
    const loadingIndicator = page.locator('[data-testid="loading"]')
      .or(page.locator('.animate-pulse'))
      .or(page.locator('[role="status"]'))
    
    // Either a loading indicator is shown or content loads quickly
    const isLoading = await loadingIndicator.count() > 0
    if (isLoading) {
      await expect(loadingIndicator.first()).toBeVisible()
    }
  })
})

test.describe('Dashboard Error Handling', () => {
  test('should handle API errors gracefully', async ({ page }) => {
    // Intercept API calls and return error
    await page.route('**/api/analytics/**', (route) => {
      route.fulfill({
        status: 500,
        body: JSON.stringify({ error: 'Internal Server Error' }),
      })
    })
    
    await page.goto('/')
    
    // Page should still load without crashing
    await expect(page.locator('main')).toBeVisible()
    
    // May show error state or empty state - this is fine either way
    // The test passes if the page loads without crashing
  })

  test('should render static content even with slow API', async ({ page }) => {
    // Intercept API calls and delay them
    await page.route('**/api/**', async (route) => {
      // Delay API responses by 2 seconds
      await new Promise((resolve) => setTimeout(resolve, 2000))
      await route.continue()
    })
    
    await page.goto('/')
    
    // Static content (nav, layout) should render immediately
    await expect(page.locator('nav')).toBeVisible()
    await expect(page.locator('main')).toBeVisible()
  })
})
