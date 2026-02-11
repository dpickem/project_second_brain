/**
 * PWA Capture App Screenshot Generator
 * 
 * Takes screenshots of the Mobile Capture PWA application.
 * Run with: npx playwright test --config=capture/playwright.config.js
 * 
 * Screenshots are saved to: docs/screenshots/
 */

import { test, expect } from '@playwright/test'
import path from 'path'
import { fileURLToPath } from 'url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)
const screenshotDir = path.join(__dirname, '../../..', 'docs', 'screenshots')

// PWA page configurations
const pages = [
  {
    name: 'capture-home',
    path: '/capture/',
    title: 'Capture Home',
    waitFor: '.capture-container',
    waitTime: 1000,
    description: 'Main capture screen with all capture type buttons',
  },
  {
    name: 'capture-text',
    path: '/capture/',
    title: 'Text Capture',
    waitFor: '.capture-container',
    waitTime: 1000,
    description: 'Text/Note capture form',
    // Click on the Note button to open the text capture form
    customAction: async (page) => {
      // Find and click the Note capture button
      const noteButton = page.locator('button:has-text("Note")').or(
        page.locator('.capture-button:has-text("Note")')
      )
      await noteButton.click()
      await page.waitForTimeout(500)
    },
  },
  {
    name: 'capture-url',
    path: '/capture/',
    title: 'URL Capture',
    waitFor: '.capture-container',
    waitTime: 1000,
    description: 'URL capture form for saving web links',
    // Click on the URL button to open the URL capture form
    customAction: async (page) => {
      // Find and click the URL capture button
      const urlButton = page.locator('button:has-text("URL")').or(
        page.locator('.capture-button:has-text("URL")')
      )
      await urlButton.click()
      await page.waitForTimeout(500)
    },
  },
]

test.describe('PWA Capture Screenshot Generator', () => {
  test.describe.configure({ mode: 'serial' })

  for (const pageConfig of pages) {
    test(`should capture ${pageConfig.title} screenshot`, async ({ page }) => {
      // Set viewport to simulate mobile device in browser
      // Using a wider viewport since this is for browser display, not actual mobile
      await page.setViewportSize({ width: 430, height: 932 }) // iPhone 14 Pro Max size
      
      // Navigate to page
      await page.goto(pageConfig.path)
      
      // Wait for the main content to load
      if (pageConfig.waitFor) {
        await page.waitForSelector(pageConfig.waitFor, { state: 'visible', timeout: 10000 })
      }
      
      // Wait for animations and data to load
      await page.waitForTimeout(pageConfig.waitTime)
      
      // Execute custom action if defined (e.g., clicking a button to open a form)
      if (pageConfig.customAction) {
        await pageConfig.customAction(page)
      }
      
      // Wait for any loading indicators to disappear
      await page.waitForFunction(() => {
        const loaders = document.querySelectorAll('[data-testid="loading"], .animate-pulse, [role="status"]')
        return loaders.length === 0 || Array.from(loaders).every(el => el.offsetParent === null)
      }, { timeout: 10000 }).catch(() => {
        // Ignore timeout - page might not have loading indicators
      })
      
      // Additional wait for stability
      await page.waitForTimeout(500)
      
      // Take screenshot
      const screenshotPath = path.join(screenshotDir, `${pageConfig.name}.png`)
      await page.screenshot({
        path: screenshotPath,
        fullPage: false,
      })
      
      console.log(`✅ Captured: ${pageConfig.title} -> ${screenshotPath}`)
    })
  }
})
