# Frontend Application Implementation Plan

> **Document Status**: Implementation Plan  
> **Created**: January 2025  
> **Target Phases**: Phase 9 (Weeks 30-38)  
> **Design Docs**: `design_docs/07_frontend_application.md`, `design_docs/05_learning_system.md`  
> **Backend Dependencies**: Learning system API (Phases 6-8 backend complete)

---

## 1. Executive Summary

This document provides a detailed implementation plan for the **complete Frontend Application**, including all learning system UI components. It consolidates all frontend work into a single Phase 9, covering foundation components, the Dashboard, Knowledge Explorer, Practice Session, Review Queue, Analytics Dashboard, and Assistant.

### Current State Assessment

The frontend currently has:

| Component | Status | Notes |
|-----------|--------|-------|
| Navigation | ✅ Implemented | Vertical sidebar with Home, Vault, Graph, Settings |
| Knowledge Graph Page | ✅ Implemented | Force-directed graph with D3, filtering, controls |
| Vault Page | ✅ Implemented | Note browser |
| Home Page | ⚠️ Basic | Quick capture only, needs Dashboard upgrade |
| Tailwind + Dark Theme | ✅ Implemented | Slate/indigo color scheme |
| React Query | ✅ Available | Dependency installed, not widely used yet |
| Zustand | ✅ Available | Dependency installed, no stores created |
| Framer Motion | ✅ Available | Dependency installed, minimal usage |

### What This Plan Covers

| In Scope | Out of Scope |
|----------|--------------|
| Foundation components (Button, Card, Modal, etc.) | Mobile PWA (see Phase 10 / 08_mobile_capture) |
| Dashboard page upgrade | Backend API development |
| Knowledge Explorer enhancements | Database schema changes |
| **Practice Session UI** (exercises, feedback, code editor) | |
| **Review Queue UI** (flashcards, FSRS ratings) | |
| **Analytics Dashboard** (charts, mastery, weak spots) | |
| Assistant/Chat interface | |
| Global state stores | |
| Custom hooks | |
| Design system & styling | |
| API client layer (all endpoints) | |

### Architecture Overview

```text
FRONTEND ARCHITECTURE
=====================

┌─────────────────────────────────────────────────────────────────────────────┐
│                              PAGES (React Router)                            │
├─────────────────────────────────────────────────────────────────────────────┤
│  Dashboard │ Knowledge │ Practice │ Review │ Analytics │ Assistant │ Settings │
│  (upgrade) │ Explorer  │  (new)   │ (new)  │   (new)   │   (new)   │  (new)   │
└─────────────────────────────────────────────────────────────────────────────┘
                                     │
┌─────────────────────────────────────────────────────────────────────────────┐
│                              COMPONENTS                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│  Common:    Button │ Card │ Modal │ Loading │ Badge │ Input │ Tooltip      │
│  Dashboard: StatsCard │ ActionCard │ StreakCalendar │ DuePreview           │
│  Knowledge: GraphVisualization (exists) │ TopicTree │ SearchBar │ NoteViewer│
│  Practice:  ExerciseCard │ ResponseInput │ FeedbackDisplay │ SessionProgress│
│  Review:    FlashCard │ RatingButtons │ ReviewStats │ ReviewComplete        │
│  Analytics: MasteryOverview │ WeakSpotsPanel │ LearningCurve │ StatsCards  │
│  Assistant: ChatInterface │ MessageBubble │ SuggestionCards                │
└─────────────────────────────────────────────────────────────────────────────┘
                                     │
┌─────────────────────────────────────────────────────────────────────────────┐
│                           STATE & DATA                                       │
├─────────────────────────────────────────────────────────────────────────────┤
│  Zustand Stores          │  React Query Hooks      │  Context               │
│  - settingsStore         │  - useQuery/useMutation │  - ThemeContext        │
│  - uiStore (modals)      │  - Caching, refetch     │  - ToastContext        │
│  - practiceStore         │                         │                         │
│  - reviewStore           │                         │                         │
└─────────────────────────────────────────────────────────────────────────────┘
                                     │
┌─────────────────────────────────────────────────────────────────────────────┐
│                              SERVICES                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│  api/                                                                        │
│  ├── client.js          # Base axios instance + interceptors                │
│  ├── knowledge.js       # (exists) Graph, nodes, stats                      │
│  ├── vault.js           # (exists) Notes, search                            │
│  ├── capture.js         # Quick capture endpoint                            │
│  ├── assistant.js       # Chat/assistant API                                │
│  ├── practice.js        # Practice session API                              │
│  ├── review.js          # Spaced rep API                                    │
│  └── analytics.js       # Analytics/mastery API                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Prerequisites

### 2.1 Prior Work Required

| Phase | Component | Why Required |
|-------|-----------|--------------|
| **Phase 1** | Backend API running | Frontend needs endpoints |
| **Phase 4** | Knowledge Graph (Neo4j) | For Knowledge Explorer |
| **Phase 6A** | Learning system schema | For due cards, analytics |
| **Phase 7A-8A** | Learning system API | Practice, review, analytics endpoints |

### 2.2 New Dependencies

```bash
# Add to frontend/package.json
npm install @monaco-editor/react  # Code editor for exercises
npm install recharts              # Charts for analytics
npm install react-hot-toast       # Toast notifications
npm install cmdk                  # Command palette (⌘K)
npm install react-intersection-observer  # Lazy loading
```

**Why These Packages:**

| Package | Purpose | Alternative Considered |
|---------|---------|------------------------|
| `@monaco-editor/react` | Code editing in exercises | CodeMirror (heavier), textarea (too basic) |
| `recharts` | Analytics charts | Victory (larger), Chart.js (less React-native) |
| `react-hot-toast` | Non-blocking notifications | react-toastify (more opinionated) |
| `cmdk` | Command palette UX | Custom (more work), kbar (less polished) |

### 2.3 Already Available (no changes)

```json
{
  "react": "^18.2.0",
  "react-router-dom": "^6.22.0",
  "@tanstack/react-query": "^5.20.0",
  "zustand": "^4.5.0",
  "framer-motion": "^11.0.3",
  "d3": "^7.8.5",
  "axios": "^1.6.7",
  "date-fns": "^3.3.1",
  "clsx": "^2.1.0",
  "@headlessui/react": "^1.7.18",
  "@heroicons/react": "^2.1.1"
}
```

---

## 3. Implementation Phases

### Phase 9A: Foundation & Design System (Days 1-5)

This phase establishes the core building blocks used across all pages.

#### Task 9A.1: Design Token System

**Purpose**: Create a cohesive design system with CSS custom properties that go beyond the current Tailwind defaults. Addresses the "AI slop aesthetic" concern by choosing distinctive typography and colors.

**Typography Upgrade**: Replace Inter (overused) with a more distinctive pairing:

| Role | Font | Why |
|------|------|-----|
| Headings | **"Space Grotesk"** or **"Outfit"** | Modern geometric sans, distinctive character |
| Body | **"IBM Plex Sans"** | Excellent readability, technical feel |
| Code | **"JetBrains Mono"** | (already configured) ligatures, great for code |

**Files to Create/Modify:**

**`frontend/src/styles/variables.css`**
```css
:root {
  /* Typography */
  --font-heading: 'Outfit', 'Space Grotesk', system-ui, sans-serif;
  --font-body: 'IBM Plex Sans', 'Inter', system-ui, sans-serif;
  --font-mono: 'JetBrains Mono', 'Fira Code', monospace;

  /* Color Palette - Refined dark theme with warmer accents */
  --color-bg-primary: #0a0f1a;      /* Deeper than slate-950 */
  --color-bg-secondary: #111827;
  --color-bg-tertiary: #1e293b;
  --color-bg-elevated: #1a2234;

  --color-text-primary: #f1f5f9;
  --color-text-secondary: #94a3b8;
  --color-text-muted: #64748b;

  /* Accent colors - warmer, more distinctive than pure indigo */
  --color-accent-primary: #6366f1;    /* Indigo-500 */
  --color-accent-secondary: #818cf8;  /* Indigo-400 */
  --color-accent-warm: #f472b6;       /* Pink-400 - for highlights */
  --color-accent-success: #34d399;    /* Emerald-400 */
  --color-accent-warning: #fbbf24;    /* Amber-400 */
  --color-accent-danger: #f87171;     /* Red-400 */

  /* Gradients */
  --gradient-accent: linear-gradient(135deg, #6366f1 0%, #a855f7 50%, #ec4899 100%);
  --gradient-subtle: linear-gradient(135deg, rgba(99,102,241,0.1) 0%, rgba(168,85,247,0.05) 100%);

  /* Spacing Scale */
  --space-1: 0.25rem;
  --space-2: 0.5rem;
  --space-3: 0.75rem;
  --space-4: 1rem;
  --space-6: 1.5rem;
  --space-8: 2rem;
  --space-12: 3rem;

  /* Border Radius */
  --radius-sm: 0.375rem;
  --radius-md: 0.5rem;
  --radius-lg: 0.75rem;
  --radius-xl: 1rem;
  --radius-2xl: 1.5rem;

  /* Shadows */
  --shadow-sm: 0 1px 2px rgba(0,0,0,0.3);
  --shadow-md: 0 4px 6px rgba(0,0,0,0.4);
  --shadow-lg: 0 10px 15px rgba(0,0,0,0.5);
  --shadow-glow: 0 0 20px rgba(99,102,241,0.3);

  /* Transitions */
  --transition-fast: 150ms ease;
  --transition-normal: 250ms ease;
  --transition-slow: 400ms ease;
}
```

**Update `frontend/src/index.css`:**
```css
@import './styles/variables.css';
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700&family=IBM+Plex+Sans:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap');

/* Update base styles to use variables */
@layer base {
  html {
    font-family: var(--font-body);
  }
  
  h1, h2, h3, h4, h5, h6 {
    font-family: var(--font-heading);
  }
  
  code, pre {
    font-family: var(--font-mono);
  }
}
```

**Deliverables:**
- [ ] `frontend/src/styles/variables.css` — Design tokens
- [ ] Updated `index.css` with new fonts
- [ ] Updated `tailwind.config.js` to reference CSS variables

**Estimated Time:** 3 hours

---

#### Task 9A.2: Common UI Components

**Purpose**: Create a set of reusable, accessible UI primitives that enforce design consistency.

**Directory:** `frontend/src/components/common/`

| Component | Props | Features |
|-----------|-------|----------|
| `Button` | `variant`, `size`, `loading`, `icon`, `disabled` | Primary/secondary/ghost variants, loading spinner, icon support |
| `Card` | `variant`, `padding`, `hover`, `onClick` | Elevated/flat variants, hover effects, clickable |
| `Modal` | `isOpen`, `onClose`, `title`, `size` | Headless UI Dialog wrapper, focus trap, escape to close |
| `Input` | `label`, `error`, `icon`, `type` | Form input with label, validation styling |
| `Badge` | `variant`, `size` | Status badges (success/warning/info/danger) |
| `Tooltip` | `content`, `side`, `delay` | Accessible tooltip with portal |
| `Loading` | `size`, `variant` | Spinner and skeleton loaders |
| `EmptyState` | `icon`, `title`, `description`, `action` | Consistent empty state pattern |

**Button Component Example:**

```jsx
// frontend/src/components/common/Button.jsx
import { forwardRef } from 'react'
import { clsx } from 'clsx'
import { motion } from 'framer-motion'

const variants = {
  primary: 'bg-gradient-to-r from-indigo-600 to-purple-600 text-white hover:from-indigo-500 hover:to-purple-500 shadow-lg shadow-indigo-600/25',
  secondary: 'bg-slate-700 text-white hover:bg-slate-600',
  ghost: 'bg-transparent text-slate-300 hover:bg-slate-800 hover:text-white',
  danger: 'bg-red-600 text-white hover:bg-red-500',
}

const sizes = {
  sm: 'px-3 py-1.5 text-sm',
  md: 'px-4 py-2 text-sm',
  lg: 'px-6 py-3 text-base',
}

export const Button = forwardRef(function Button(
  { variant = 'primary', size = 'md', loading, icon, children, className, ...props },
  ref
) {
  return (
    <motion.button
      ref={ref}
      whileHover={{ scale: 1.02 }}
      whileTap={{ scale: 0.98 }}
      className={clsx(
        'inline-flex items-center justify-center gap-2 font-medium rounded-lg transition-colors duration-150 disabled:opacity-50 disabled:cursor-not-allowed',
        variants[variant],
        sizes[size],
        className
      )}
      disabled={loading || props.disabled}
      {...props}
    >
      {loading ? <Spinner size={size} /> : icon}
      {children}
    </motion.button>
  )
})
```

**Deliverables:**
- [ ] `Button.jsx` with variants, sizes, loading state
- [ ] `Card.jsx` with hover effects
- [ ] `Modal.jsx` wrapping Headless UI Dialog
- [ ] `Input.jsx` with label and error states
- [ ] `Badge.jsx` for status indicators
- [ ] `Tooltip.jsx` accessible tooltip
- [ ] `Loading.jsx` spinner and skeletons
- [ ] `EmptyState.jsx` consistent empty pattern
- [ ] `index.js` barrel export

**Estimated Time:** 8 hours

---

#### Task 9A.3: Animation Utilities

**Purpose**: Create reusable Framer Motion animation presets for consistent, delightful micro-interactions.

**File:** `frontend/src/utils/animations.js`

```javascript
// Stagger children animations
export const staggerContainer = {
  hidden: {},
  show: {
    transition: {
      staggerChildren: 0.1,
      delayChildren: 0.1,
    },
  },
}

export const fadeInUp = {
  hidden: { opacity: 0, y: 20 },
  show: { 
    opacity: 1, 
    y: 0,
    transition: { duration: 0.4, ease: 'easeOut' }
  },
}

export const scaleIn = {
  hidden: { opacity: 0, scale: 0.95 },
  show: { 
    opacity: 1, 
    scale: 1,
    transition: { duration: 0.3, ease: 'easeOut' }
  },
}

export const slideInRight = {
  hidden: { opacity: 0, x: 20 },
  show: { 
    opacity: 1, 
    x: 0,
    transition: { duration: 0.3, ease: 'easeOut' }
  },
}

// Page transition
export const pageTransition = {
  initial: { opacity: 0, y: 10 },
  animate: { opacity: 1, y: 0 },
  exit: { opacity: 0, y: -10 },
  transition: { duration: 0.2 },
}
```

**Deliverables:**
- [ ] `frontend/src/utils/animations.js` — Animation presets
- [ ] Update App.jsx to use AnimatePresence for page transitions

**Estimated Time:** 2 hours

---

#### Task 9A.4: API Client Foundation

**Purpose**: Create a robust base API client with error handling, interceptors, and request/response typing.

**File:** `frontend/src/api/client.js`

```javascript
import axios from 'axios'
import toast from 'react-hot-toast'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export const apiClient = axios.create({
  baseURL: API_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor - add auth token when available
apiClient.interceptors.request.use((config) => {
  // Future: Add auth token
  // const token = useAuthStore.getState().token
  // if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// Response interceptor - handle errors globally
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    const message = error.response?.data?.detail || error.message || 'An error occurred'
    
    // Don't toast on 401 (will redirect to login)
    if (error.response?.status !== 401) {
      toast.error(message)
    }
    
    return Promise.reject(error)
  }
)

// Helper for typed API calls
export function createApiEndpoint(path) {
  return {
    get: (params) => apiClient.get(path, { params }).then(r => r.data),
    post: (data) => apiClient.post(path, data).then(r => r.data),
    put: (data) => apiClient.put(path, data).then(r => r.data),
    patch: (data) => apiClient.patch(path, data).then(r => r.data),
    delete: () => apiClient.delete(path).then(r => r.data),
  }
}
```

**Migrate existing API files to use base client:**

```javascript
// frontend/src/api/knowledge.js (updated)
import { apiClient } from './client'

export const knowledgeApi = {
  getGraph: (params) => apiClient.get('/api/knowledge/graph', { params }).then(r => r.data),
  getStats: () => apiClient.get('/api/knowledge/stats').then(r => r.data),
  getNode: (nodeId) => apiClient.get(`/api/knowledge/node/${nodeId}`).then(r => r.data),
}
```

**Deliverables:**
- [ ] `frontend/src/api/client.js` — Base axios client
- [ ] Update `knowledge.js` to use base client
- [ ] Update `vault.js` to use base client
- [ ] Create `capture.js` for quick capture endpoint

**Estimated Time:** 3 hours

---

#### Task 9A.5: Global State Stores

**Purpose**: Create Zustand stores for UI state and user settings that persist across sessions.

**Directory:** `frontend/src/stores/`

| Store | State | Actions | Persistence |
|-------|-------|---------|-------------|
| `settingsStore` | theme, sidebarCollapsed, preferredSessionLength | setTheme, toggleSidebar, updateSettings | localStorage |
| `uiStore` | activeModal, commandPaletteOpen, toasts | openModal, closeModal, toggleCommandPalette | none |

**`frontend/src/stores/settingsStore.js`**
```javascript
import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export const useSettingsStore = create(
  persist(
    (set) => ({
      // State
      theme: 'dark',
      sidebarCollapsed: false,
      preferredSessionLength: 15, // minutes
      keyboardShortcutsEnabled: true,
      
      // Actions
      setTheme: (theme) => set({ theme }),
      toggleSidebar: () => set((s) => ({ sidebarCollapsed: !s.sidebarCollapsed })),
      updateSettings: (updates) => set((s) => ({ ...s, ...updates })),
    }),
    {
      name: 'second-brain-settings',
    }
  )
)
```

**`frontend/src/stores/uiStore.js`**
```javascript
import { create } from 'zustand'

export const useUIStore = create((set) => ({
  // Modal state
  activeModal: null, // 'capture' | 'settings' | 'confirm' | null
  modalProps: {},
  
  // Command palette
  commandPaletteOpen: false,
  
  // Actions
  openModal: (modal, props = {}) => set({ activeModal: modal, modalProps: props }),
  closeModal: () => set({ activeModal: null, modalProps: {} }),
  toggleCommandPalette: () => set((s) => ({ commandPaletteOpen: !s.commandPaletteOpen })),
}))
```

**Deliverables:**
- [ ] `frontend/src/stores/settingsStore.js` — User preferences with localStorage
- [ ] `frontend/src/stores/uiStore.js` — Modal and UI state
- [ ] `frontend/src/stores/index.js` — Barrel export

**Estimated Time:** 3 hours

---

### Phase 9B: Dashboard Upgrade (Days 6-10)

Transform the basic HomePage into a comprehensive learning command center.

#### Task 9B.1: Dashboard Page

**Purpose**: The Dashboard is the user's home screen—answering "What should I do today?" at a glance with actionable quick links, due cards preview, and learning stats.

**File:** `frontend/src/pages/Dashboard.jsx`

**Layout:**
```text
┌─────────────────────────────────────────────────────────────────────────┐
│  Good morning, User! 🌅                          15-day streak 🔥        │
│  You have 23 cards due today                                             │
├───────────────────────────────┬─────────────────────────────────────────┤
│  CONTINUE LEARNING            │  DUE FOR REVIEW                          │
│  ┌─────────┐ ┌─────────┐     │  Card 1: What is...?    [Source]         │
│  │ Practice │ │ Review  │     │  Card 2: Explain...     [Source]         │
│  │   🎯     │ │   📚    │     │  Card 3: How does...?   [Source]         │
│  │ 15 min  │ │ 23 due  │     │  ... and 20 more                         │
│  └─────────┘ └─────────┘     │                                          │
├───────────────────────────────┼─────────────────────────────────────────┤
│  FOCUS AREAS                  │  QUICK CAPTURE                           │
│  ⚠️ Machine Learning (42%)    │  ┌───────────────────────────────────┐  │
│  ⚠️ System Design (58%)       │  │ Capture a thought...              │  │
│  ℹ️ Databases (65%)           │  └───────────────────────────────────┘  │
│                               │  [ Capture ]                            │
├───────────────────────────────┴─────────────────────────────────────────┤
│  ACTIVITY                                                                │
│  [  ████  ████  ████  ██    ████  ████  ██  ]  Streak Calendar         │
└─────────────────────────────────────────────────────────────────────────┘
```

**Data Fetching:**
```javascript
// Queries needed
const { data: stats } = useQuery({
  queryKey: ['dailyStats'],
  queryFn: () => analyticsApi.getDailyStats(),
})

const { data: dueCards } = useQuery({
  queryKey: ['dueCards', { limit: 5 }],
  queryFn: () => reviewApi.getDueCards({ limit: 5 }),
})

const { data: weakSpots } = useQuery({
  queryKey: ['weakSpots', { limit: 3 }],
  queryFn: () => analyticsApi.getWeakSpots({ limit: 3 }),
})
```

**Components Used:**
- `StatsHeader` — Greeting, streak, due count
- `ActionCard` — Practice/Review quick actions
- `DueCardsPreview` — List of upcoming cards
- `WeakSpotsList` — Focus areas with mastery %
- `QuickCapture` — Inline text capture
- `StreakCalendar` — GitHub-style activity heatmap

**Deliverables:**
- [ ] `frontend/src/pages/Dashboard.jsx` — Main dashboard page
- [ ] Replace current HomePage with Dashboard

**Estimated Time:** 6 hours

---

#### Task 9B.2: Dashboard Components

**Directory:** `frontend/src/components/dashboard/`

| Component | Purpose |
|-----------|---------|
| `StatsHeader` | Personalized greeting (time-based), streak badge, due count |
| `ActionCard` | Large clickable cards for Practice/Review with icon, title, sublabel |
| `DueCardsPreview` | Compact list of 5 due cards with source badges |
| `WeakSpotsList` | Topics below threshold with mastery %, trend indicator |
| `QuickCapture` | Textarea + capture button, inline success feedback |
| `StreakCalendar` | 52-week activity heatmap showing practice days |

**ActionCard Component:**
```jsx
// frontend/src/components/dashboard/ActionCard.jsx
import { motion } from 'framer-motion'
import { Link } from 'react-router-dom'

export function ActionCard({ to, icon, title, sublabel, highlight }) {
  return (
    <Link to={to}>
      <motion.div
        whileHover={{ scale: 1.02, y: -2 }}
        whileTap={{ scale: 0.98 }}
        className={clsx(
          'p-6 rounded-2xl border transition-all duration-200',
          highlight
            ? 'bg-gradient-to-br from-indigo-600/20 to-purple-600/20 border-indigo-500/50 shadow-lg shadow-indigo-600/10'
            : 'bg-slate-800/50 border-slate-700 hover:border-slate-600'
        )}
      >
        <span className="text-4xl mb-4 block">{icon}</span>
        <h3 className="text-xl font-semibold text-white">{title}</h3>
        <p className="text-slate-400 mt-1">{sublabel}</p>
      </motion.div>
    </Link>
  )
}
```

**StreakCalendar Component:**
Uses a grid of 52 columns × 7 rows, colored by activity level (0-4).

**Deliverables:**
- [ ] `StatsHeader.jsx`
- [ ] `ActionCard.jsx`
- [ ] `DueCardsPreview.jsx`
- [ ] `WeakSpotsList.jsx`
- [ ] `QuickCapture.jsx`
- [ ] `StreakCalendar.jsx`
- [ ] `index.js` barrel export

**Estimated Time:** 8 hours

---

### Phase 9C: Knowledge Explorer Enhancements (Days 11-15)

Upgrade the existing Knowledge Graph page with topic tree, search, and note viewing.

#### Task 9C.1: Topic Tree Sidebar

**Purpose**: Provide hierarchical navigation of topics as an alternative to the graph view.

**File:** `frontend/src/components/knowledge/TopicTree.jsx`

**Features:**
- Tree structure with expand/collapse
- Topic count badges
- Mastery indicator (color-coded)
- Click to filter graph to topic
- Drag to reorder (future)

**Data Structure:**
```javascript
// Topic hierarchy from API
const topics = [
  {
    id: 'ml',
    name: 'Machine Learning',
    mastery: 0.42,
    count: 15,
    children: [
      { id: 'ml-supervised', name: 'Supervised Learning', mastery: 0.55, count: 8 },
      { id: 'ml-unsupervised', name: 'Unsupervised Learning', mastery: 0.30, count: 7 },
    ]
  },
  // ...
]
```

**Deliverables:**
- [ ] `TopicTree.jsx` — Hierarchical topic browser
- [ ] Tree expand/collapse with animation
- [ ] Mastery color coding

**Estimated Time:** 5 hours

---

#### Task 9C.2: Global Search Bar

**Purpose**: Command palette style search (⌘K) for finding notes, concepts, and topics across the knowledge base.

**File:** `frontend/src/components/common/CommandPalette.jsx`

**Features:**
- ⌘K / Ctrl+K keyboard shortcut
- Search across notes, concepts, tags
- Recent searches
- Quick actions (New note, Start practice, etc.)
- Keyboard navigation (↑↓ to select, Enter to open)

**Implementation:** Uses `cmdk` library for accessible command menu.

```jsx
import { Command } from 'cmdk'

export function CommandPalette() {
  const [open, setOpen] = useState(false)
  const [search, setSearch] = useState('')
  
  // ⌘K shortcut
  useEffect(() => {
    const down = (e) => {
      if (e.key === 'k' && (e.metaKey || e.ctrlKey)) {
        e.preventDefault()
        setOpen((open) => !open)
      }
    }
    document.addEventListener('keydown', down)
    return () => document.removeEventListener('keydown', down)
  }, [])
  
  return (
    <Command.Dialog open={open} onOpenChange={setOpen}>
      <Command.Input 
        value={search}
        onValueChange={setSearch}
        placeholder="Search notes, concepts, or type a command..."
      />
      <Command.List>
        <Command.Group heading="Notes">
          {/* Search results */}
        </Command.Group>
        <Command.Group heading="Actions">
          <Command.Item onSelect={() => navigate('/practice')}>
            Start Practice Session
          </Command.Item>
          {/* ... */}
        </Command.Group>
      </Command.List>
    </Command.Dialog>
  )
}
```

**Deliverables:**
- [ ] `CommandPalette.jsx` — Global search/command menu
- [ ] `useKeyboardShortcuts.js` — Hook for ⌘K and other shortcuts
- [ ] Add to App.jsx as global component

**Estimated Time:** 6 hours

---

#### Task 9C.3: Note Viewer Panel

**Purpose**: Side panel for viewing note content without leaving the graph/explorer view.

**File:** `frontend/src/components/knowledge/NoteViewer.jsx`

**Features:**
- Slide-in panel from right
- Markdown rendering with syntax highlighting
- Metadata (source, tags, created date)
- "Open in Vault" button
- Related concepts list

**Deliverables:**
- [ ] `NoteViewer.jsx` — Slide-in note viewer
- [ ] Markdown rendering with `react-markdown`
- [ ] Code syntax highlighting with `highlight.js`

**Estimated Time:** 4 hours

---

### Phase 9D: Assistant Chat Interface (Days 16-20)

Build the AI assistant interface for knowledge Q&A and learning guidance.

#### Task 9D.1: Chat Interface Page

**Purpose**: Conversational interface for asking questions about your knowledge base, getting study recommendations, and exploring topics.

**File:** `frontend/src/pages/Assistant.jsx`

**Layout:**
```text
┌─────────────────────────────────────────────────────────────────────────┐
│  Assistant                                            [New Chat] [...]   │
├───────────────────────────────┬─────────────────────────────────────────┤
│  CONVERSATIONS                │  CHAT                                    │
│  ─────────────────            │                                          │
│  ◉ Understanding FSRS...      │  🤖 Hi! I can help you explore your      │
│    Today                      │     knowledge base. Ask me anything!     │
│                               │                                          │
│  ○ Machine Learning basics    │  👤 What are the key concepts in         │
│    Yesterday                  │     machine learning I should review?    │
│                               │                                          │
│  ○ System design patterns     │  🤖 Based on your notes, here are the    │
│    3 days ago                 │     key ML concepts you've captured:     │
│                               │     • Supervised vs Unsupervised         │
│                               │     • Feature Engineering                │
│                               │     • Model Evaluation Metrics           │
│                               │                                          │
│                               │     📝 Want me to create a practice      │
│                               │        session on these topics?          │
│                               │                                          │
├───────────────────────────────┼─────────────────────────────────────────┤
│  SUGGESTIONS                  │  ┌───────────────────────────────────┐  │
│  "Explain [topic] to me"      │  │ Ask a question...                 │  │
│  "Quiz me on [topic]"         │  └───────────────────────────────────┘  │
│  "What should I study today?" │                              [Send 📤]  │
└───────────────────────────────┴─────────────────────────────────────────┘
```

**API Integration:**
```javascript
// frontend/src/api/assistant.js
export const assistantApi = {
  // Send message and get streaming response
  sendMessage: async (conversationId, message) => {
    const response = await apiClient.post('/api/assistant/chat', {
      conversation_id: conversationId,
      message,
    })
    return response.data
  },
  
  // Get conversation history
  getConversations: () => apiClient.get('/api/assistant/conversations').then(r => r.data),
  
  // Get single conversation with messages
  getConversation: (id) => apiClient.get(`/api/assistant/conversations/${id}`).then(r => r.data),
}
```

**Deliverables:**
- [ ] `frontend/src/pages/Assistant.jsx` — Main assistant page
- [ ] Add `/assistant` route

**Estimated Time:** 6 hours

---

#### Task 9D.2: Chat Components

**Directory:** `frontend/src/components/assistant/`

| Component | Props | Purpose |
|-----------|-------|---------|
| `ChatInterface` | `conversationId` | Main chat container, manages message state |
| `MessageBubble` | `message`, `isUser` | Individual message with avatar, timestamp |
| `MessageInput` | `onSend`, `loading` | Text input with send button, multiline |
| `SuggestionCards` | `suggestions`, `onSelect` | Quick action suggestions |
| `ConversationList` | `conversations`, `onSelect`, `active` | Sidebar conversation history |
| `SourceCitation` | `sources` | Shows which notes were used for answer |

**MessageBubble with Markdown:**
```jsx
import ReactMarkdown from 'react-markdown'
import { motion } from 'framer-motion'

export function MessageBubble({ message, isUser }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className={clsx(
        'flex gap-3',
        isUser ? 'flex-row-reverse' : 'flex-row'
      )}
    >
      <div className={clsx(
        'w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0',
        isUser ? 'bg-indigo-600' : 'bg-slate-700'
      )}>
        {isUser ? '👤' : '🤖'}
      </div>
      
      <div className={clsx(
        'max-w-[80%] rounded-2xl px-4 py-3',
        isUser 
          ? 'bg-indigo-600 text-white' 
          : 'bg-slate-800 text-slate-100'
      )}>
        <ReactMarkdown className="prose prose-sm prose-invert">
          {message.content}
        </ReactMarkdown>
        
        {message.sources && (
          <SourceCitation sources={message.sources} />
        )}
      </div>
    </motion.div>
  )
}
```

**Deliverables:**
- [ ] `ChatInterface.jsx` — Main chat container
- [ ] `MessageBubble.jsx` — Individual messages with markdown
- [ ] `MessageInput.jsx` — Multiline input with send
- [ ] `SuggestionCards.jsx` — Quick actions
- [ ] `ConversationList.jsx` — Conversation history sidebar
- [ ] `SourceCitation.jsx` — Reference display

**Estimated Time:** 10 hours

---

### Phase 9E: Custom Hooks (Days 21-23)

Create reusable hooks for common patterns.

#### Task 9E.1: Data Fetching Hooks

**Directory:** `frontend/src/hooks/`

| Hook | Purpose | Dependencies |
|------|---------|--------------|
| `useApi` | Generic API hook with loading/error states | React Query |
| `useDebouncedSearch` | Debounced search input | useState, useEffect |
| `useLocalStorage` | Persist state to localStorage | useState, useEffect |
| `useKeyboardShortcuts` | Register keyboard shortcuts | useEffect |

**`useKeyboardShortcuts.js`:**
```javascript
import { useEffect } from 'react'

const shortcuts = {
  'Meta+k': 'openSearch',
  'Meta+n': 'newCapture',
  'Meta+p': 'startPractice',
  'Escape': 'closeModal',
}

export function useKeyboardShortcuts(handlers) {
  useEffect(() => {
    const handleKeyDown = (e) => {
      const key = [
        e.metaKey && 'Meta',
        e.ctrlKey && 'Ctrl',
        e.shiftKey && 'Shift',
        e.key,
      ].filter(Boolean).join('+')
      
      const action = shortcuts[key]
      if (action && handlers[action]) {
        e.preventDefault()
        handlers[action]()
      }
    }
    
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [handlers])
}
```

**Deliverables:**
- [ ] `useApi.js` — Generic API wrapper
- [ ] `useDebouncedSearch.js` — Debounced input
- [ ] `useLocalStorage.js` — Persistent state
- [ ] `useKeyboardShortcuts.js` — Keyboard shortcuts

**Estimated Time:** 4 hours

---

#### Task 9E.2: Learning System Hooks

**Note**: These hooks work with the Zustand stores defined in Task 9J.3 and the API clients in Task 9J.2.

| Hook | Purpose | Implementation |
|------|---------|----------------|
| `usePracticeSession` | Session state, submit, navigation | Wraps practiceStore + React Query |
| `useReviewQueue` | Due cards, rating submission | Wraps reviewStore + React Query |
| `useMastery` | Topic mastery data | React Query for analytics endpoints |

```javascript
// frontend/src/hooks/usePracticeSession.js
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { usePracticeStore } from '../stores/practiceStore'
import { practiceApi } from '../api/practice'

export function usePracticeSession(topicId, duration = 15) {
  const queryClient = useQueryClient()
  const store = usePracticeStore()
  
  const sessionQuery = useQuery({
    queryKey: ['practice-session', topicId, duration],
    queryFn: () => practiceApi.createSession({ topic_filter: topicId, duration_minutes: duration }),
    enabled: !store.session,
    onSuccess: (data) => store.startSession(data),
  })
  
  const submitMutation = useMutation({
    mutationFn: ({ exerciseId, response }) => practiceApi.submitAttempt(exerciseId, response),
    onSuccess: (data, { exerciseId, response }) => {
      store.submitResponse(exerciseId, response, data)
    },
  })
  
  return {
    session: store.session,
    currentItem: store.getCurrentItem(),
    progress: store.getProgress(),
    isLoading: sessionQuery.isLoading,
    submitResponse: submitMutation.mutate,
    nextItem: store.nextItem,
  }
}
```

---

### Phase 9F: Navigation & Routing (Days 24-25)

Finalize routing structure and navigation updates.

#### Task 9F.1: Route Configuration

**File:** `frontend/src/App.jsx` (update)

```jsx
import { lazy, Suspense } from 'react'
import { Routes, Route } from 'react-router-dom'
import { AnimatePresence } from 'framer-motion'

// Lazy load pages for code splitting
const Dashboard = lazy(() => import('./pages/Dashboard'))
const KnowledgeExplorer = lazy(() => import('./pages/KnowledgeGraph'))
const PracticeSession = lazy(() => import('./pages/PracticeSession'))
const ReviewQueue = lazy(() => import('./pages/ReviewQueue'))
const Analytics = lazy(() => import('./pages/Analytics'))
const Assistant = lazy(() => import('./pages/Assistant'))
const Vault = lazy(() => import('./pages/Vault'))
const Settings = lazy(() => import('./pages/Settings'))

function App() {
  return (
    <div className="flex">
      <Navigation />
      <main className="flex-1 ml-16">
        <Suspense fallback={<PageLoader />}>
          <AnimatePresence mode="wait">
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/knowledge" element={<KnowledgeExplorer />} />
              <Route path="/practice" element={<PracticeSession />} />
              <Route path="/practice/:topicId" element={<PracticeSession />} />
              <Route path="/review" element={<ReviewQueue />} />
              <Route path="/analytics" element={<Analytics />} />
              <Route path="/analytics/:topicId" element={<Analytics />} />
              <Route path="/assistant" element={<Assistant />} />
              <Route path="/vault" element={<Vault />} />
              <Route path="/settings" element={<Settings />} />
            </Routes>
          </AnimatePresence>
        </Suspense>
      </main>
      
      {/* Global components */}
      <CommandPalette />
      <Toaster />
    </div>
  )
}
```

#### Task 9F.2: Navigation Updates

**Update Navigation Component:**
- Add Practice, Review, Analytics, Assistant links
- Active state indicators
- Keyboard shortcuts hints
- Collapsible sidebar option

**New Nav Items:**
```jsx
const navItems = [
  { to: '/', icon: <HomeIcon />, title: 'Dashboard', shortcut: '⌘1' },
  { to: '/practice', icon: <PracticeIcon />, title: 'Practice', shortcut: '⌘2' },
  { to: '/review', icon: <ReviewIcon />, title: 'Review', shortcut: '⌘3' },
  { to: '/knowledge', icon: <GraphIcon />, title: 'Knowledge', shortcut: '⌘4' },
  { to: '/analytics', icon: <AnalyticsIcon />, title: 'Analytics', shortcut: '⌘5' },
  { to: '/assistant', icon: <AssistantIcon />, title: 'Assistant', shortcut: '⌘6' },
]
```

**Deliverables:**
- [ ] Updated route configuration with lazy loading
- [ ] Navigation component with all pages
- [ ] Page transition animations
- [ ] Keyboard navigation shortcuts

**Estimated Time:** 4 hours

---

### Phase 9G: Settings Page (Days 26-27)

#### Task 9G.1: Settings Page

**File:** `frontend/src/pages/Settings.jsx`

**Sections:**
- **Appearance**: Theme (dark only for now), sidebar collapsed default
- **Learning**: Default session length, daily review goal
- **Keyboard Shortcuts**: View/customize shortcuts
- **Account**: (Future) Profile, data export

**Deliverables:**
- [ ] `Settings.jsx` — Settings page
- [ ] Settings sections with form inputs
- [ ] Persistence via settingsStore

**Estimated Time:** 4 hours

---

## 4. Learning System Frontend

### Phase 9H: Practice Session UI (Days 28-35)

The Practice Session UI is the primary interface for active learning—where users engage with exercises, submit responses, and receive immediate feedback.

#### Task 9H.1: Practice Session Core Components

**Directory:** `frontend/src/components/practice/`

| Component | Props | Purpose |
|-----------|-------|---------|
| `PracticeSession` | `topicId?`, `sessionLength`, `onComplete` | Main orchestrator - manages session state, current exercise index, feedback display |
| `ExerciseCard` | `exercise` | Displays exercise with type badge, difficulty, prompt, context, code snippet, hints |
| `SessionProgress` | `current`, `total`, `correctCount` | Progress bar and statistics |
| `SessionComplete` | `sessionId`, `onComplete` | Summary view after session ends |

**State Management:**
- Use TanStack Query for session creation (`useQuery` with `staleTime: Infinity`)
- Use `useMutation` for submit attempts
- Local state: `currentIndex`, `showFeedback`, `lastEvaluation`

**UX Flow:**
1. Create session on mount → fetch exercises
2. Show ExerciseCard + ResponseInput
3. On submit → show FeedbackDisplay with evaluation
4. User rates confidence → advance to next exercise
5. When complete → show SessionComplete summary

**Deliverables:**
- [ ] `PracticeSession.jsx` — Main session orchestrator
- [ ] `ExerciseCard.jsx` — Exercise display with type-specific rendering
- [ ] `SessionProgress.jsx` — Progress bar and stats
- [ ] `SessionComplete.jsx` — Session summary and next actions

**Estimated Time:** 10 hours

---

#### Task 9H.2: Response Input Components

**File:** `frontend/src/components/practice/ResponseInput.jsx`

| Exercise Type | Input Component | Features |
|---------------|-----------------|----------|
| Text exercises (free_recall, self_explain, teach_back) | `Textarea` | Placeholder per type, character count |
| Code exercises (debugging, code_completion, implementation) | Monaco `CodeEditor` | Syntax highlighting, line numbers, language detection |

**Behavior:**
- Cmd/Ctrl+Enter to submit
- Clear button for code editor
- Loading state during submission
- Exercise-type-specific placeholders

**Deliverables:**
- [ ] `ResponseInput.jsx` — Adaptive input based on exercise type
- [ ] Monaco editor integration with `@monaco-editor/react`
- [ ] Keyboard shortcuts

**Estimated Time:** 6 hours

---

#### Task 9H.3: Feedback Display Components

**File:** `frontend/src/components/practice/FeedbackDisplay.jsx`

| Section | Content |
|---------|---------|
| Result Header | Correct/incorrect icon, score percentage |
| Detailed Feedback | LLM feedback markdown, specific feedback points with icons |
| Model Answer | Revealed if incorrect (code diff for code exercises) |
| Confidence Rating | 4 buttons: "Still confused" → "Easy!" (1-4 scale) |

**Deliverables:**
- [ ] `FeedbackDisplay.jsx` — Evaluation results display
- [ ] `CodeDiff.jsx` — Side-by-side code comparison
- [ ] Confidence rating buttons

**Estimated Time:** 6 hours

---

### Phase 9I: Review Queue UI (Days 36-40)

The Review Queue UI handles spaced repetition card review—showing due cards and collecting user ratings.

#### Task 9I.1: Review Queue Components

**Directory:** `frontend/src/components/review/`

| Component | Props | Purpose |
|-----------|-------|---------|
| `ReviewQueue` | - | Main container - fetches due cards, manages review flow |
| `FlashCard` | `card`, `showAnswer`, `onShowAnswer` | Flip card with front/back, tap to reveal |
| `RatingButtons` | `onRate`, `isLoading`, `card` | FSRS rating buttons (Again/Hard/Good/Easy) with interval preview |
| `ReviewStats` | `remaining`, `reviewed`, `dueToday` | Session statistics |
| `ReviewComplete` | `reviewedCount`, `nextDueDate` | Completion screen |

**State Management:**
- `useQuery(['due-cards'])` - fetch due cards (staleTime: 5 min)
- `useMutation` for rating - invalidates due-cards query on success
- Local state: `showAnswer`, `reviewedCount`, `showAnswerTime` (for response timing)

**FlashCard Component:**
- Shows card front (question) with type badge, streak indicator, interval
- "Show Answer" button reveals back with animation
- Supports code blocks for both front and back
- Optional explanation section

**RatingButtons Component:**
- 4 buttons: Again (red), Hard (orange), Good (green), Easy (blue)
- Shows predicted next interval for each rating
- Keyboard shortcuts: 1-4

```jsx
// frontend/src/components/review/RatingButtons.jsx
const ratings = [
  { value: 1, label: 'Again', color: 'red', shortcut: '1' },
  { value: 2, label: 'Hard', color: 'orange', shortcut: '2' },
  { value: 3, label: 'Good', color: 'green', shortcut: '3' },
  { value: 4, label: 'Easy', color: 'blue', shortcut: '4' },
]
```

**Deliverables:**
- [ ] `ReviewQueue.jsx` — Due card queue management
- [ ] `FlashCard.jsx` — Card display with flip animation
- [ ] `RatingButtons.jsx` — FSRS rating interface
- [ ] `ReviewStats.jsx` — Session statistics
- [ ] `ReviewComplete.jsx` — Completion screen with next due info

**Estimated Time:** 10 hours

---

### Phase 9J: Analytics Dashboard (Days 41-45)

The Analytics Dashboard provides visual insight into learning progress, mastery levels, and areas needing attention.

#### Task 9J.1: Analytics Overview Components

**Directory:** `frontend/src/components/analytics/`

| Component | Purpose | Key Features |
|-----------|---------|--------------|
| `AnalyticsDashboard` | Main container | Fetches overview data, responsive grid layout |
| `StatsCards` | Key metrics | Total cards, cards reviewed today, streak, avg retention |
| `MasteryOverview` | Topic mastery | Progress bars per topic, trend indicators, overall % |
| `WeakSpotsPanel` | Areas needing attention | Topics below threshold, "Practice now" buttons |
| `LearningCurve` | Progress over time | Recharts line chart (mastery, retention, cards reviewed) |
| `PracticeHeatmap` | Activity visualization | GitHub-style heatmap of practice days |
| `TopicMasteryTree` | Hierarchical view | Tree visualization of topic→subtopic mastery |

**Layout:**
```text
┌─────────────────────────────────────────────┐
│  Learning Analytics                          │
├─────────────────────────────────────────────┤
│  [StatsCards - 4 columns]                   │
├──────────────────────┬──────────────────────┤
│  MasteryOverview     │  WeakSpotsPanel      │
├──────────────────────┴──────────────────────┤
│  LearningCurve (full width)                 │
├──────────────────────┬──────────────────────┤
│  PracticeHeatmap     │  TopicMasteryTree    │
└──────────────────────┴──────────────────────┘
```

**MasteryOverview Features:**
- Sort topics by mastery score
- Progress bar with color coding (green ≥80%, yellow ≥60%, orange ≥40%, red <40%)
- Trend indicators (↑ improving, ↓ declining, — stable)
- "View all N topics" link

**WeakSpotsPanel Features:**
- Query topics where mastery < 0.6
- Show recommendation per topic
- "Practice Now" button → navigates to /practice/{topicId}

**LearningCurve Component:**
- Uses Recharts `LineChart` with two lines: mastery (primary), retention (secondary)
- Query last 30 days of data
- X-axis: dates, Y-axis: 0-100%

**Deliverables:**
- [ ] `AnalyticsDashboard.jsx` — Main dashboard layout
- [ ] `MasteryOverview.jsx` — Topic mastery progress bars
- [ ] `WeakSpotsPanel.jsx` — Areas needing attention
- [ ] `LearningCurve.jsx` — Progress over time chart (Recharts)
- [ ] `PracticeHeatmap.jsx` — Activity calendar heatmap
- [ ] `TopicMasteryTree.jsx` — Hierarchical topic visualization
- [ ] `StatsCards.jsx` — Key metrics (streak, cards reviewed, etc.)

**Estimated Time:** 12 hours

---

#### Task 9J.2: Learning System API Client

**Directory:** `frontend/src/api/`

| File | Methods |
|------|---------|
| `practice.js` | `createSession`, `submitAttempt`, `updateConfidence`, `generateExercise`, `getSessionSummary` |
| `review.js` | `getDueCards`, `rateCard`, `getCard`, `getCardsByTopic` |
| `analytics.js` | `getOverview`, `getMastery`, `getWeakSpots`, `getLearningCurve`, `getPracticeHistory` |

```javascript
// frontend/src/api/practice.js
import { apiClient } from './client'

export const practiceApi = {
  createSession: (params) => 
    apiClient.post('/api/practice/session', params).then(r => r.data),
  
  submitAttempt: (exerciseId, response) =>
    apiClient.post(`/api/practice/submit`, { exercise_id: exerciseId, ...response }).then(r => r.data),
  
  updateConfidence: (attemptId, confidence) =>
    apiClient.patch(`/api/practice/attempt/${attemptId}/confidence`, { confidence_after: confidence }).then(r => r.data),
}

// frontend/src/api/review.js
export const reviewApi = {
  getDueCards: (params) =>
    apiClient.get('/api/review/due', { params }).then(r => r.data),
  
  rateCard: (cardId, rating, timeSpent) =>
    apiClient.post('/api/review/rate', { card_id: cardId, rating, time_spent_seconds: timeSpent }).then(r => r.data),
}

// frontend/src/api/analytics.js
export const analyticsApi = {
  getOverview: () =>
    apiClient.get('/api/analytics/mastery').then(r => r.data),
  
  getWeakSpots: (params) =>
    apiClient.get('/api/analytics/weak-spots', { params }).then(r => r.data),
  
  getLearningCurve: (topic) =>
    apiClient.get(`/api/analytics/learning-curve${topic ? `/${topic}` : ''}`).then(r => r.data),
}
```

**TypeScript Types (`frontend/src/types/learning.ts`):**

| Type | Fields |
|------|--------|
| `ExerciseType` | Union: free_recall, self_explain, worked_example, debugging, code_completion, implementation, teach_back |
| `CardType` | Union: concept, fact, application, cloze, code |
| `Rating` | Union: again, hard, good, easy (1-4) |
| `Trend` | Union: improving, stable, declining |
| `Exercise` | id, exercise_type, prompt, context?, code_snippet?, language?, difficulty, topic_path?, hints? |
| `AttemptEvaluation` | is_correct, score, feedback, model_answer?, specific_feedback[] |
| `SpacedRepCard` | id, front, back, card_type, code_front?, code_back?, due_date, stability, difficulty, interval_days |
| `MasteryState` | topic_path, mastery_score, success_rate, practice_count, trend |

**Deliverables:**
- [ ] `frontend/src/api/practice.js` — Practice API client
- [ ] `frontend/src/api/review.js` — Review API client
- [ ] `frontend/src/api/analytics.js` — Analytics API client
- [ ] `frontend/src/types/learning.ts` — TypeScript type definitions

**Estimated Time:** 6 hours

---

#### Task 9J.3: Learning System State Stores

**Directory:** `frontend/src/stores/`

**`frontend/src/stores/practiceStore.js`**
```javascript
import { create } from 'zustand'

export const usePracticeStore = create((set, get) => ({
  // State
  session: null,
  currentItemIndex: 0,
  responses: [],
  startTime: null,
  
  // Actions
  startSession: (session) => set({
    session,
    currentItemIndex: 0,
    responses: [],
    startTime: Date.now(),
  }),
  
  submitResponse: (itemId, response, feedback) => set((state) => ({
    responses: [...state.responses, { itemId, response, feedback }],
  })),
  
  nextItem: () => set((state) => ({
    currentItemIndex: state.currentItemIndex + 1,
  })),
  
  getCurrentItem: () => {
    const { session, currentItemIndex } = get()
    return session?.items?.[currentItemIndex] || null
  },
  
  getProgress: () => {
    const { session, currentItemIndex, startTime } = get()
    return {
      completed: currentItemIndex,
      total: session?.items?.length || 0,
      timeElapsed: startTime ? Date.now() - startTime : 0,
    }
  },
  
  reset: () => set({
    session: null,
    currentItemIndex: 0,
    responses: [],
    startTime: null,
  }),
}))
```

**`frontend/src/stores/reviewStore.js`**
```javascript
import { create } from 'zustand'

export const useReviewStore = create((set, get) => ({
  // State
  cards: [],
  currentIndex: 0,
  reviewedCount: 0,
  showAnswer: false,
  
  // Actions
  setCards: (cards) => set({ cards, currentIndex: 0, reviewedCount: 0 }),
  
  showAnswerAction: () => set({ showAnswer: true }),
  
  nextCard: () => set((state) => ({
    currentIndex: state.currentIndex + 1,
    reviewedCount: state.reviewedCount + 1,
    showAnswer: false,
  })),
  
  getCurrentCard: () => {
    const { cards, currentIndex } = get()
    return cards[currentIndex] || null
  },
  
  reset: () => set({ cards: [], currentIndex: 0, reviewedCount: 0, showAnswer: false }),
}))
```

**Deliverables:**
- [ ] `frontend/src/stores/practiceStore.js` — Practice session state
- [ ] `frontend/src/stores/reviewStore.js` — Review queue state

**Estimated Time:** 3 hours

---

**Learning System Frontend Total:** 53 hours

---

## 5. Timeline Summary

### Phase 9: Complete Frontend Implementation (Days 1-45)

| Phase | Days | Tasks | Deliverables | Hours |
|-------|------|-------|--------------|-------|
| 9A | 1-5 | Foundation & Design System | Tokens, components, animations, API client, stores | 19 |
| 9B | 6-10 | Dashboard Upgrade | Dashboard page, dashboard components | 14 |
| 9C | 11-15 | Knowledge Explorer | TopicTree, CommandPalette, NoteViewer | 15 |
| 9D | 16-20 | Assistant Chat | Assistant page, chat components | 16 |
| 9E | 21-23 | Custom Hooks | Data fetching, keyboard shortcuts | 4 |
| 9F | 24-25 | Navigation & Routing | Routes, navigation, page transitions | 4 |
| 9G | 26-27 | Settings Page | Settings page with preferences | 4 |
| 9H | 28-35 | **Practice Session UI** | ExerciseCard, ResponseInput, FeedbackDisplay, stores | 22 |
| 9I | 36-40 | **Review Queue UI** | FlashCard, RatingButtons, ReviewStats, ReviewComplete | 10 |
| 9J | 41-45 | **Analytics Dashboard** | MasteryOverview, LearningCurve, WeakSpots, API clients | 21 |
| **Total** | | | | **129** |

### Gantt View

```text
Days:     1----5----10---15---20---25---30---35---40---45
          [==9A==][==9B==][==9C==][==9D==][9E][9F][9G][====9H====][=9I=][==9J==]
          Foundation│Dashboard│Knowledge│Assistant│Hooks│Nav│Set│ Practice │Review│Analytics
```

**Sequencing Notes:**
- Phase 9A (Foundation) must complete first — provides design tokens and common components
- Phases 9B-9D can proceed in parallel with backend learning system work (Phase 6-8)
- Phase 9H (Practice) requires backend practice API endpoints (Phase 7A)
- Phase 9I (Review) requires backend review API endpoints (Phase 7A)
- Phase 9J (Analytics) requires backend analytics API endpoints (Phase 8A)

---

## 6. Testing Strategy

### 6.1 Component Testing

**Tool:** Vitest + React Testing Library

| Test File | Coverage |
|-----------|----------|
| `Button.test.jsx` | Variants, loading state, disabled state |
| `Modal.test.jsx` | Open/close, focus trap, escape key |
| `Dashboard.test.jsx` | Data fetching, empty states, navigation |
| `CommandPalette.test.jsx` | Search, keyboard navigation, actions |

### 6.2 Integration Testing

**Tool:** Playwright

| Test | Scenario |
|------|----------|
| `dashboard.spec.ts` | Load dashboard, see stats, navigate to practice |
| `practice-flow.spec.ts` | Create session, submit response, see feedback |
| `review-flow.spec.ts` | Load due cards, rate card, see next card |
| `search.spec.ts` | Open ⌘K, search, navigate to result |

---

## 7. Success Criteria

### Functional Requirements
- [ ] Dashboard shows accurate due count and streak
- [ ] ⌘K opens command palette and search works
- [ ] Navigation highlights current page
- [ ] All pages load within 2 seconds
- [ ] Assistant can query knowledge base

### Quality Requirements
- [ ] Lighthouse score > 90 (Performance, Accessibility)
- [ ] No FOUC (flash of unstyled content)
- [ ] Responsive on desktop and tablet
- [ ] Keyboard navigable (WCAG 2.1 AA)

### Design Requirements
- [ ] Consistent use of design tokens
- [ ] Smooth page transitions (< 300ms)
- [ ] Loading states for all async operations
- [ ] Empty states for all list views

---

## 8. Risk Assessment

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| API contract changes | Medium | Medium | Use TypeScript types, mock APIs during dev |
| Performance with large graphs | High | Low | Virtualization, pagination, WebGL renderer |
| State management complexity | Medium | Medium | Keep stores minimal, use React Query for server state |
| Accessibility gaps | Medium | Medium | Regular a11y audits, use semantic HTML |

---

## 9. Related Documents

| Document | Purpose |
|----------|---------|
| `design_docs/07_frontend_application.md` | Design specification |
| `design_docs/05_learning_system.md` | Learning system design (exercises, FSRS, mastery) |
| `05_learning_system_implementation.md` | Backend learning system implementation |
| `design_docs/06_backend_api.md` | API contract reference |
| `design_docs/08_mobile_capture.md` | PWA considerations (Phase 10) |

