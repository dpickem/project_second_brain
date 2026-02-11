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
    name: 'cards',
    path: '/cards',
    title: 'Card Catalogue',
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
    // Custom action to select a note from sources/articles to show markdown rendering
    customAction: async (page) => {
      // Wait for folders to load
      await page.waitForTimeout(1000)
      
      // Try to find and expand sources/articles folder specifically
      // Folder buttons have aria-label like "{folder} folder, {count} notes, expand/collapse"
      const folderButtons = page.locator('button[aria-label*="folder"]')
      const folderCount = await folderButtons.count()
      
      // Priority list of folders to try (sources/articles preferred)
      const preferredFolders = ['sources/articles', 'sources/papers', 'sources/books', 'sources']
      let folderFound = false
      
      for (const targetFolder of preferredFolders) {
        if (folderFound) break
        
        for (let i = 0; i < folderCount; i++) {
          const folder = folderButtons.nth(i)
          const ariaLabel = await folder.getAttribute('aria-label')
          
          if (ariaLabel && ariaLabel.toLowerCase().includes(targetFolder)) {
            const isExpanded = await folder.getAttribute('aria-expanded')
            if (isExpanded !== 'true') {
              await folder.click()
              await page.waitForTimeout(500)
            }
            folderFound = true
            break
          }
        }
      }
      
      // If no preferred folder found, just expand the first folder
      if (!folderFound && folderCount > 0) {
        const firstFolder = folderButtons.first()
        const isExpanded = await firstFolder.getAttribute('aria-expanded')
        if (isExpanded !== 'true') {
          await firstFolder.click()
          await page.waitForTimeout(500)
        }
      }
      
      // Look for a note button inside the expanded folder
      const noteButtons = page.locator('div[role="group"] button')
      const noteCount = await noteButtons.count()
      
      if (noteCount > 0) {
        // Click the first note to show its content
        await noteButtons.first().click()
        await page.waitForTimeout(1500) // Wait for note content to load and render
      }
    },
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
    name: 'tasks',
    path: '/tasks',
    title: 'Follow-up Tasks',
    waitFor: 'main',
    waitTime: 1500,
  },
  {
    name: 'llm-usage',
    path: '/llm-usage',
    title: 'LLM Usage',
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
      
      // Execute custom action if defined (e.g., selecting a note)
      if (page.customAction) {
        await page.customAction(browserPage)
      }
      
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
