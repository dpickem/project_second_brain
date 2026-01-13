/**
 * Screenshot Generator Script
 * 
 * Takes screenshots of all pages in the Second Brain application.
 * Run with: npx playwright test screenshots.spec.js
 * 
 * Screenshots are saved to: docs/screenshots/
 */

import { test, expect } from '@playwright/test'
import path from 'path'
import { fileURLToPath } from 'url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)
const screenshotDir = path.join(__dirname, '../..', 'docs', 'screenshots')

// Page configurations with descriptions
const pages = [
  {
    name: 'dashboard',
    path: '/',
    title: 'Dashboard',
    waitFor: 'main',
    waitTime: 1500,
  },
  {
    name: 'practice',
    path: '/practice',
    title: 'Practice Session',
    waitFor: 'main',
    waitTime: 1500,
  },
  {
    name: 'exercises',
    path: '/exercises',
    title: 'Exercises Catalogue',
    waitFor: 'main',
    waitTime: 1500,
  },
  {
    name: 'review',
    path: '/review',
    title: 'Review Queue',
    waitFor: 'main',
    waitTime: 1500,
  },
  {
    name: 'knowledge',
    path: '/knowledge',
    title: 'Knowledge Explorer',
    waitFor: 'main',
    waitTime: 1500,
  },
  {
    name: 'graph',
    path: '/graph',
    title: 'Knowledge Graph',
    waitFor: 'main',
    waitTime: 3000, // Graph needs more time to render
  },
  {
    name: 'analytics',
    path: '/analytics',
    title: 'Analytics Dashboard',
    waitFor: 'main',
    waitTime: 1500,
  },
  {
    name: 'assistant',
    path: '/assistant',
    title: 'Learning Assistant',
    waitFor: 'main',
    waitTime: 1500,
  },
  {
    name: 'settings',
    path: '/settings',
    title: 'Settings',
    waitFor: 'main',
    waitTime: 1500,
  },
]

test.describe('Screenshot Generator', () => {
  test.describe.configure({ mode: 'serial' })

  for (const page of pages) {
    test(`should capture ${page.title} page screenshot`, async ({ page: browserPage }) => {
      // Set viewport for consistent screenshots
      await browserPage.setViewportSize({ width: 1440, height: 900 })
      
      // Navigate to page
      await browserPage.goto(page.path)
      
      // Wait for the main content to load
      if (page.waitFor) {
        await browserPage.waitForSelector(page.waitFor, { state: 'visible', timeout: 10000 })
      }
      
      // Wait for animations and data to load
      await browserPage.waitForTimeout(page.waitTime)
      
      // Wait for any loading indicators to disappear
      await browserPage.waitForFunction(() => {
        const loaders = document.querySelectorAll('[data-testid="loading"], .animate-pulse, [role="status"]')
        return loaders.length === 0 || Array.from(loaders).every(el => el.offsetParent === null)
      }, { timeout: 15000 }).catch(() => {
        // Ignore timeout - page might not have loading indicators
      })
      
      // Additional wait for stability
      await browserPage.waitForTimeout(500)
      
      // Take screenshot
      const screenshotPath = path.join(screenshotDir, `${page.name}.png`)
      await browserPage.screenshot({
        path: screenshotPath,
        fullPage: false,
      })
      
      console.log(`✅ Captured: ${page.title} -> ${screenshotPath}`)
    })
  }
})
