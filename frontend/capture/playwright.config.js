/**
 * Playwright Configuration for PWA Capture App
 * 
 * E2E tests for the Mobile Capture PWA.
 * Run with: npm run test:e2e:capture (from frontend directory)
 * Or directly: npx playwright test --config=capture/playwright.config.js
 */

import { defineConfig, devices } from '@playwright/test'

export default defineConfig({
  // Test directory
  testDir: './e2e',
  
  // Test file pattern
  testMatch: '**/*.spec.js',
  
  // Run tests in serial mode for screenshots
  fullyParallel: false,
  
  // Fail the build on CI if you accidentally left test.only in the source code
  forbidOnly: !!process.env.CI,
  
  // Retry on CI only
  retries: process.env.CI ? 2 : 0,
  
  // Single worker for consistent screenshots
  workers: 1,
  
  // Reporter
  reporter: [
    ['html', { open: 'never' }],
    ['list'],
  ],
  
  // Shared settings for all projects
  use: {
    // Base URL for the PWA capture app (port 5174)
    baseURL: 'http://localhost:5174',
    
    // Collect trace when retrying the failed test
    trace: 'on-first-retry',
    
    // Screenshot on failure
    screenshot: 'only-on-failure',
    
    // Video on failure
    video: 'retain-on-failure',
  },

  // Configure projects for major browsers
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
    // Mobile viewport for realistic PWA screenshots
    {
      name: 'mobile-chrome',
      use: { ...devices['Pixel 5'] },
    },
  ],

  // Reuse existing dev server (capture app should already be running)
  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:5174/capture/',
    reuseExistingServer: true,
    timeout: 120 * 1000,
    cwd: '.',
  },
})
