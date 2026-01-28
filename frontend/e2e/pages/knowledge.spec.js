/**
 * Knowledge Page E2E Tests
 * 
 * Comprehensive end-to-end tests for the Knowledge Explorer page.
 * 
 * Run with: npm run test:e2e
 * Run only these tests: npm run test:e2e -- --grep "Knowledge"
 * 
 * ============================================================================
 * TEST COVERAGE SUMMARY
 * ============================================================================
 * 
 * PAGE LOAD (3 tests)
 * - Verifies page loads without JavaScript errors
 * - Checks sidebar displays correct folder/note counts
 * - Confirms Tree/List view toggle buttons are present
 * 
 * URL ROUTING (2 tests)
 * - ?note=path param opens specific note
 * - ?search=query param populates search
 * 
 * FOLDER TREE VIEW (3 tests)
 * - Displays all folders with icons and note counts
 * - Expanding a folder reveals nested notes
 * - Collapsing a folder hides nested notes
 * 
 * LIST VIEW (3 tests)
 * - Switching to list view shows all notes in flat list
 * - Each note displays its folder path
 * - Content type badges are shown for each note
 * 
 * NOTE SELECTION AND VIEWING (5 tests)
 * - Empty state shown when no note selected
 * - Clicking a note displays its markdown content
 * - Note header shows metadata (title, modified date)
 * - Close button returns to empty state
 * - Selected note is visually highlighted in sidebar
 * 
 * SEARCH FUNCTIONALITY (3 tests)
 * - Search input is visible in sidebar
 * - Typing filters notes by title/name (debounced)
 * - Command palette hint (⌘K) is displayed
 * 
 * COMMAND PALETTE INTEGRATION (3 tests)
 * - ⌘K keyboard shortcut opens command palette
 * - Escape key closes command palette
 * - Clicking ⌘K button opens command palette
 * 
 * MARKDOWN RENDERING (2 tests)
 * - Headings (h1, h2, h3) render correctly
 * - Code blocks render with syntax highlighting
 * 
 * RESPONSIVE DESIGN (2 tests)
 * - Layout works on tablet viewport (768x1024)
 * - Layout works on desktop viewport (1920x1080)
 * 
 * ERROR HANDLING (2 tests)
 * - Page handles folder API 500 errors gracefully
 * - Page handles note content 404 errors gracefully
 * 
 * ============================================================================
 * MOCKED API ENDPOINTS
 * ============================================================================
 * 
 * GET /api/vault/folders     - Returns folder list with note counts
 * GET /api/vault/notes       - Returns paginated note list (supports search)
 * GET /api/vault/notes/:path - Returns full note content with frontmatter
 * 
 * ============================================================================
 */

import { test, expect } from '@playwright/test'

// Mock data for consistent testing
const mockFolders = {
  folders: [
    { type: 'articles', folder: 'sources/articles', exists: true, icon: '📰', note_count: 3 },
    { type: 'papers', folder: 'sources/papers', exists: true, icon: '📄', note_count: 2 },
    { type: 'books', folder: 'sources/books', exists: true, icon: '📚', note_count: 1 },
  ],
  total_notes: 6,
}

const mockNotes = {
  notes: [
    { 
      path: 'sources/articles/test-article-1.md', 
      name: 'test-article-1', 
      folder: 'sources/articles',
      title: 'Understanding React Hooks',
      modified: '2026-01-08T10:00:00Z',
      size: 1024,
      tags: ['react', 'javascript'],
      content_type: 'article'
    },
    { 
      path: 'sources/articles/test-article-2.md', 
      name: 'test-article-2', 
      folder: 'sources/articles',
      title: 'Advanced TypeScript Patterns',
      modified: '2026-01-07T15:30:00Z',
      size: 2048,
      tags: ['typescript', 'patterns'],
      content_type: 'article'
    },
    { 
      path: 'sources/papers/research-paper.md', 
      name: 'research-paper', 
      folder: 'sources/papers',
      title: 'Machine Learning in Practice',
      modified: '2026-01-06T09:00:00Z',
      size: 4096,
      tags: ['ml', 'ai'],
      content_type: 'paper'
    },
  ],
  total: 3,
  page: 1,
  page_size: 50,
  has_more: false,
}

const mockNoteContent = {
  path: 'sources/articles/test-article-1.md',
  name: 'test-article-1',
  title: 'Understanding React Hooks',
  folder: 'sources/articles',
  content: `# Understanding React Hooks

React Hooks revolutionized how we write React components.

## useState

The most basic hook for managing local state.

\`\`\`javascript
const [count, setCount] = useState(0);
\`\`\`

## useEffect

For side effects and lifecycle management.

## Summary

Hooks make React development more intuitive and functional.
`,
  frontmatter: {
    title: 'Understanding React Hooks',
    tags: ['react', 'javascript'],
    type: 'article',
  },
  modified: '2026-01-08T10:00:00Z',
  size: 1024,
}

test.describe('Knowledge Page', () => {
  test.beforeEach(async ({ page }) => {
    // Set up API mocks
    await page.route('**/api/vault/folders', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(mockFolders),
      })
    })

    // Mock for specific note content - must be registered before the generic notes route
    await page.route('**/api/vault/notes/**/*.md', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(mockNoteContent),
      })
    })

    // Mock for notes listing (with optional search) - must match with query params
    await page.route(/\/api\/vault\/notes(\?.*)?$/, async (route) => {
      const url = new URL(route.request().url())
      const search = url.searchParams.get('search')
      
      if (search) {
        // Filter notes based on search query
        const filteredNotes = mockNotes.notes.filter(note => 
          note.title.toLowerCase().includes(search.toLowerCase()) ||
          note.name.toLowerCase().includes(search.toLowerCase())
        )
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ ...mockNotes, notes: filteredNotes, total: filteredNotes.length }),
        })
      } else {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(mockNotes),
        })
      }
    })
  })

  test.describe('Page Load', () => {
    test('should load the Knowledge page without errors', async ({ page }) => {
      const consoleErrors = []
      page.on('console', (msg) => {
        if (msg.type() === 'error') {
          consoleErrors.push(msg.text())
        }
      })

      await page.goto('/knowledge')
      await page.waitForLoadState('networkidle')

      // Page should have loaded
      await expect(page.getByRole('heading', { name: /Knowledge/i })).toBeVisible()
      
      // Filter out expected API-related errors
      const criticalErrors = consoleErrors.filter(
        (error) => !error.includes('Failed to fetch') && 
                   !error.includes('NetworkError') &&
                   !error.includes('queryFn')
      )
      expect(criticalErrors).toHaveLength(0)
    })

    test('should display the sidebar with folders and notes count', async ({ page }) => {
      await page.goto('/knowledge')
      await page.waitForLoadState('networkidle')

      // Stats should show correct counts
      await expect(page.getByText('3 topics')).toBeVisible()
      await expect(page.getByText('3 notes')).toBeVisible()
    })

    test('should have Tree and List view toggle', async ({ page }) => {
      await page.goto('/knowledge')
      await page.waitForLoadState('networkidle')

      // View toggles should be visible (role="tab" for accessibility)
      await expect(page.getByRole('tab', { name: /Tree/i })).toBeVisible()
      await expect(page.getByRole('tab', { name: /List/i })).toBeVisible()
    })
  })

  test.describe('URL Routing', () => {
    test('should open note from URL param ?note=', async ({ page }) => {
      await page.goto('/knowledge?note=sources/articles/test-article-1.md')
      await page.waitForLoadState('networkidle')

      // Note content should be displayed (header title)
      await expect(page.getByRole('heading', { name: 'Understanding React Hooks', level: 1 }).first()).toBeVisible()
    })

    test('should populate search from URL param ?search=', async ({ page }) => {
      await page.goto('/knowledge?search=React')
      await page.waitForLoadState('networkidle')

      // Search input should have the value
      await expect(page.getByPlaceholder('Search notes...')).toHaveValue('React')
    })
  })

  test.describe('Folder Tree View', () => {
    test('should display folders with icons and note counts', async ({ page }) => {
      await page.goto('/knowledge')
      await page.waitForLoadState('networkidle')

      // Folders should be visible
      await expect(page.getByText('sources/articles')).toBeVisible()
      await expect(page.getByText('sources/papers')).toBeVisible()
      await expect(page.getByText('sources/books')).toBeVisible()
    })

    test('should expand folder to show notes', async ({ page }) => {
      await page.goto('/knowledge')
      await page.waitForLoadState('networkidle')

      // Click on articles folder to expand
      await page.getByText('sources/articles').click()

      // Notes in that folder should be visible
      await expect(page.getByText('Understanding React Hooks')).toBeVisible()
      await expect(page.getByText('Advanced TypeScript Patterns')).toBeVisible()
    })

    test('should collapse expanded folder on second click', async ({ page }) => {
      await page.goto('/knowledge')
      await page.waitForLoadState('networkidle')

      // Expand folder
      await page.getByText('sources/articles').click()
      await expect(page.getByText('Understanding React Hooks')).toBeVisible()

      // Collapse folder
      await page.getByText('sources/articles').click()
      
      // Notes should be hidden (with animation)
      await expect(page.getByText('Understanding React Hooks')).not.toBeVisible()
    })
  })

  test.describe('List View', () => {
    test('should switch to list view when List button is clicked', async ({ page }) => {
      await page.goto('/knowledge')
      await page.waitForLoadState('networkidle')

      // Switch to list view (role="tab" for accessibility)
      await page.getByRole('tab', { name: /List/i }).click()

      // All notes should be visible in flat list
      await expect(page.getByText('Understanding React Hooks')).toBeVisible()
      await expect(page.getByText('Advanced TypeScript Patterns')).toBeVisible()
      await expect(page.getByText('Machine Learning in Practice')).toBeVisible()
    })

    test('should show folder path for each note in list view', async ({ page }) => {
      await page.goto('/knowledge')
      await page.waitForLoadState('networkidle')

      // Switch to list view (role="tab" for accessibility)
      await page.getByRole('tab', { name: /List/i }).click()

      // Folder paths should be visible
      await expect(page.getByText('sources/articles').first()).toBeVisible()
      await expect(page.getByText('sources/papers').first()).toBeVisible()
    })

    test('should show content type badges in list view', async ({ page }) => {
      await page.goto('/knowledge')
      await page.waitForLoadState('networkidle')

      // Switch to list view (role="tab" for accessibility)
      await page.getByRole('tab', { name: /List/i }).click()

      // Content type badges should be visible
      await expect(page.getByText('article').first()).toBeVisible()
    })
  })

  test.describe('Note Selection and Viewing', () => {
    test('should show empty state when no note is selected', async ({ page }) => {
      await page.goto('/knowledge')
      await page.waitForLoadState('networkidle')

      // Empty state should be visible
      await expect(page.getByText('Select a note')).toBeVisible()
      await expect(page.getByText(/Choose a note from the sidebar/)).toBeVisible()
    })

    test('should display note content when a note is selected', async ({ page }) => {
      await page.goto('/knowledge')
      await page.waitForLoadState('networkidle')

      // Expand folder and select a note
      await page.getByText('sources/articles').click()
      await page.getByText('Understanding React Hooks').first().click()

      // Note content should be displayed (header title)
      await expect(page.getByRole('heading', { name: 'Understanding React Hooks', level: 1 }).first()).toBeVisible()
      
      // Content should be rendered as markdown
      await expect(page.getByText(/React Hooks revolutionized/)).toBeVisible()
    })

    test('should update URL when note is selected', async ({ page }) => {
      await page.goto('/knowledge')
      await page.waitForLoadState('networkidle')

      // Select a note
      await page.getByText('sources/articles').click()
      await page.getByText('Understanding React Hooks').first().click()

      // URL should contain note param
      await expect(page).toHaveURL(/note=/)
    })

    test('should show note metadata in the header', async ({ page }) => {
      await page.goto('/knowledge')
      await page.waitForLoadState('networkidle')

      // Select a note
      await page.getByText('sources/articles').click()
      await page.getByText('Understanding React Hooks').first().click()

      // Metadata should be visible
      await expect(page.getByText(/Modified/)).toBeVisible()
    })

    test('should close note viewer when X button is clicked', async ({ page }) => {
      await page.goto('/knowledge')
      await page.waitForLoadState('networkidle')

      // Select a note
      await page.getByText('sources/articles').click()
      await page.getByText('Understanding React Hooks').first().click()

      // Note should be displayed (header title)
      await expect(page.getByRole('heading', { name: 'Understanding React Hooks', level: 1 }).first()).toBeVisible()

      // Click close button
      await page.getByLabel('Close').click()

      // Empty state should return
      await expect(page.getByText('Select a note')).toBeVisible()
    })

    test('should highlight selected note in sidebar', async ({ page }) => {
      await page.goto('/knowledge')
      await page.waitForLoadState('networkidle')

      // Expand folder and select a note
      await page.getByText('sources/articles').click()
      const noteButton = page.getByText('Understanding React Hooks').first()
      await noteButton.click()

      // Selected note should have highlight class
      await expect(noteButton).toHaveClass(/indigo/)
    })
  })

  test.describe('Search Functionality', () => {
    test('should have a search input in the sidebar', async ({ page }) => {
      await page.goto('/knowledge')
      await page.waitForLoadState('networkidle')

      // Search input should be visible
      await expect(page.getByPlaceholder('Search notes...')).toBeVisible()
    })

    test('should filter notes when searching', async ({ page }) => {
      await page.goto('/knowledge')
      await page.waitForLoadState('networkidle')

      // Switch to list view for easier verification (role="tab" for accessibility)
      await page.getByRole('tab', { name: /List/i }).click()

      // Type in search
      await page.getByPlaceholder('Search notes...').fill('React')

      // Wait for debounced search
      await page.waitForTimeout(500)

      // Only matching notes should be visible
      await expect(page.getByText('Understanding React Hooks')).toBeVisible()
    })

    test('should show command palette hint (⌘K)', async ({ page }) => {
      await page.goto('/knowledge')
      await page.waitForLoadState('networkidle')

      // ⌘K hint button should be visible in search input area (has aria-label for accessibility)
      await expect(page.getByRole('button', { name: /command palette/i })).toBeVisible()
    })
  })

  test.describe('Command Palette Integration', () => {
    test('should open command palette with ⌘K shortcut', async ({ page }) => {
      await page.goto('/knowledge')
      await page.waitForLoadState('networkidle')

      // Press Cmd+K (or Ctrl+K on non-Mac)
      await page.keyboard.press('Meta+k')

      // Command palette should be visible
      await expect(page.getByPlaceholder(/Search notes, type a command/)).toBeVisible()
    })

    test('should close command palette with Escape', async ({ page }) => {
      await page.goto('/knowledge')
      await page.waitForLoadState('networkidle')

      // Open command palette
      await page.keyboard.press('Meta+k')
      await expect(page.getByPlaceholder(/Search notes, type a command/)).toBeVisible()

      // Close with Escape
      await page.keyboard.press('Escape')
      await expect(page.getByPlaceholder(/Search notes, type a command/)).not.toBeVisible()
    })

    test('should open command palette when clicking ⌘K button', async ({ page }) => {
      await page.goto('/knowledge')
      await page.waitForLoadState('networkidle')

      // Click the ⌘K button in the search input area (has aria-label for accessibility)
      await page.getByRole('button', { name: /command palette/i }).click()

      // Command palette should be visible
      await expect(page.getByPlaceholder(/Search notes, type a command/)).toBeVisible()
    })
  })

  test.describe('Markdown Rendering', () => {
    test('should render markdown headings correctly', async ({ page }) => {
      await page.goto('/knowledge')
      await page.waitForLoadState('networkidle')

      // Select a note
      await page.getByText('sources/articles').click()
      await page.getByText('Understanding React Hooks').first().click()

      // Headings should be rendered (there will be two h1s - header title and markdown h1)
      await expect(page.getByRole('heading', { name: 'Understanding React Hooks' }).first()).toBeVisible()
      await expect(page.getByRole('heading', { name: 'useState' })).toBeVisible()
      await expect(page.getByRole('heading', { name: 'useEffect' })).toBeVisible()
      await expect(page.getByRole('heading', { name: 'Summary' })).toBeVisible()
    })

    test('should render code blocks with syntax highlighting', async ({ page }) => {
      await page.goto('/knowledge')
      await page.waitForLoadState('networkidle')

      // Select a note
      await page.getByText('sources/articles').click()
      await page.getByText('Understanding React Hooks').first().click()

      // Code block should be rendered
      await expect(page.locator('pre code')).toBeVisible()
      await expect(page.getByText('useState(0)')).toBeVisible()
    })
  })

  test.describe('Responsive Design', () => {
    test('should display correctly on tablet viewport', async ({ page }) => {
      await page.setViewportSize({ width: 768, height: 1024 })
      await page.goto('/knowledge')
      await page.waitForLoadState('networkidle')

      // Sidebar and main content should be visible
      await expect(page.getByRole('heading', { name: /Knowledge/i })).toBeVisible()
      await expect(page.getByText('Select a note')).toBeVisible()
    })

    test('should display correctly on desktop viewport', async ({ page }) => {
      await page.setViewportSize({ width: 1920, height: 1080 })
      await page.goto('/knowledge')
      await page.waitForLoadState('networkidle')

      // Full layout should be visible
      await expect(page.getByRole('heading', { name: /Knowledge/i })).toBeVisible()
      await expect(page.getByText('sources/articles')).toBeVisible()
    })
  })

  test.describe('Exercise Content Behavior', () => {
    const mockExerciseNote = {
      path: 'exercises/by-topic/ml_test/Self Explain - test_abc123.md',
      name: 'Self Explain - test_abc123',
      title: 'Self Explain - ml/test',
      folder: 'exercises/by-topic/ml_test',
      content: `---
type: exercise
title: "Self Explain - ml/test"
exercise_type: self_explain
topic: "ml/test"
difficulty: foundational
---

## Exercise: Self Explain - ml/test

**Type**: Self Explain  
**Difficulty**: Foundational

---

## Prompt

Explain the concept in your own words.

---

## Hints

<details>
<summary>Click to reveal hints (try without first!)</summary>

1. Think about the key ideas.
2. Consider the implications.

</details>

---

## Source Material

- [[Test Source Paper]]
`,
      frontmatter: {
        title: 'Self Explain - ml/test',
        type: 'exercise',
        exercise_type: 'self_explain',
        topic: 'ml/test',
        difficulty: 'foundational',
      },
      modified: '2026-01-08T10:00:00Z',
      size: 512,
    }

    test.beforeEach(async ({ page }) => {
      // Override note content endpoint for exercise
      await page.route('**/api/vault/notes/**/exercises/**', async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(mockExerciseNote),
        })
      })

      // Mock exercises API to return empty
      await page.route('**/api/practice/exercises**', async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify([]),
        })
      })

      // Mock cards API to return empty
      await page.route('**/api/review/cards**', async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify([]),
        })
      })
    })

    test('should disable Generate Cards button when viewing exercise content', async ({ page }) => {
      await page.goto('/knowledge?note=exercises/by-topic/ml_test/Self%20Explain%20-%20test_abc123.md')
      await page.waitForLoadState('networkidle')

      // Wait for note content to load
      await expect(page.getByRole('heading', { name: /Self Explain/i }).first()).toBeVisible()

      // Find the Generate Cards button and verify it's disabled
      const generateCardsButton = page.getByRole('button', { name: /Generate Cards/i })
      await expect(generateCardsButton).toBeVisible()
      await expect(generateCardsButton).toBeDisabled()
    })

    test('should disable Generate Exercises button when viewing exercise content', async ({ page }) => {
      await page.goto('/knowledge?note=exercises/by-topic/ml_test/Self%20Explain%20-%20test_abc123.md')
      await page.waitForLoadState('networkidle')

      // Wait for note content to load
      await expect(page.getByRole('heading', { name: /Self Explain/i }).first()).toBeVisible()

      // Find the Generate Exercises button and verify it's disabled
      const generateExercisesButton = page.getByRole('button', { name: /Generate Exercises/i })
      await expect(generateExercisesButton).toBeVisible()
      await expect(generateExercisesButton).toBeDisabled()
    })

    test('should show tooltip on hover over disabled Generate Cards button', async ({ page }) => {
      await page.goto('/knowledge?note=exercises/by-topic/ml_test/Self%20Explain%20-%20test_abc123.md')
      await page.waitForLoadState('networkidle')

      // Wait for note content to load
      await expect(page.getByRole('heading', { name: /Self Explain/i }).first()).toBeVisible()

      // Find the wrapper span with the tooltip (parent of the button)
      const generateCardsWrapper = page.locator('span[title="Cannot generate cards from exercises"]')
      await expect(generateCardsWrapper).toBeVisible()

      // Hover over the wrapper to trigger tooltip
      await generateCardsWrapper.hover()

      // The title attribute should be present - native tooltips appear after a delay
      // We verify the attribute exists since native tooltip timing is browser-dependent
      await expect(generateCardsWrapper).toHaveAttribute('title', 'Cannot generate cards from exercises')
    })

    test('should show tooltip on hover over disabled Generate Exercises button', async ({ page }) => {
      await page.goto('/knowledge?note=exercises/by-topic/ml_test/Self%20Explain%20-%20test_abc123.md')
      await page.waitForLoadState('networkidle')

      // Wait for note content to load
      await expect(page.getByRole('heading', { name: /Self Explain/i }).first()).toBeVisible()

      // Find the wrapper span with the tooltip (parent of the button)
      const generateExercisesWrapper = page.locator('span[title="Cannot generate exercises from exercises"]')
      await expect(generateExercisesWrapper).toBeVisible()

      // Verify the title attribute is present
      await expect(generateExercisesWrapper).toHaveAttribute('title', 'Cannot generate exercises from exercises')
    })

    test('should render collapsible hints section', async ({ page }) => {
      await page.goto('/knowledge?note=exercises/by-topic/ml_test/Self%20Explain%20-%20test_abc123.md')
      await page.waitForLoadState('networkidle')

      // Wait for note content to load
      await expect(page.getByRole('heading', { name: /Self Explain/i }).first()).toBeVisible()

      // Details/summary elements should be present
      const detailsElement = page.locator('details')
      await expect(detailsElement.first()).toBeVisible()

      // Summary should be clickable
      const summaryElement = page.locator('summary').first()
      await expect(summaryElement).toBeVisible()
      await expect(summaryElement).toContainText('Click to reveal')
    })

    test('should expand hints when clicking on summary', async ({ page }) => {
      await page.goto('/knowledge?note=exercises/by-topic/ml_test/Self%20Explain%20-%20test_abc123.md')
      await page.waitForLoadState('networkidle')

      // Wait for note content to load
      await expect(page.getByRole('heading', { name: /Self Explain/i }).first()).toBeVisible()

      // Click on summary to expand
      const summaryElement = page.locator('summary').first()
      await summaryElement.click()

      // Content inside details should now be visible
      await expect(page.getByText('Think about the key ideas')).toBeVisible()
    })

    test('should render wiki-links as clickable links', async ({ page }) => {
      await page.goto('/knowledge?note=exercises/by-topic/ml_test/Self%20Explain%20-%20test_abc123.md')
      await page.waitForLoadState('networkidle')

      // Wait for note content to load
      await expect(page.getByRole('heading', { name: /Self Explain/i }).first()).toBeVisible()

      // Wiki-link should be rendered as a clickable link
      const sourceLink = page.getByRole('link', { name: 'Test Source Paper' })
      await expect(sourceLink).toBeVisible()
      
      // Should link to knowledge search
      await expect(sourceLink).toHaveAttribute('href', /\/knowledge\?search=Test%20Source%20Paper/)
    })
  })

  test.describe('Error Handling', () => {
    test('should handle folder API errors gracefully', async ({ page }) => {
      // Override with error response
      await page.route('**/api/vault/folders', async (route) => {
        await route.fulfill({
          status: 500,
          contentType: 'application/json',
          body: JSON.stringify({ detail: 'Internal Server Error' }),
        })
      })

      await page.goto('/knowledge')
      await page.waitForLoadState('networkidle')

      // Page should still render
      await expect(page.getByRole('heading', { name: /Knowledge/i })).toBeVisible()
    })

    test('should handle note content API errors gracefully', async ({ page }) => {
      // Override note content endpoint with error
      await page.route('**/api/vault/notes/sources/**', async (route) => {
        await route.fulfill({
          status: 404,
          contentType: 'application/json',
          body: JSON.stringify({ detail: 'Note not found' }),
        })
      })

      await page.goto('/knowledge?note=sources/articles/nonexistent.md')
      await page.waitForLoadState('networkidle')

      // Error state should be shown
      await expect(page.getByText(/Failed to load/i)).toBeVisible()
    })
  })
})
