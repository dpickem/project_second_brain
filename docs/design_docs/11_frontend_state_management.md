# State Management Guidelines

This document describes the state management patterns used in the Second Brain frontend and when to use each approach.

## Overview

The frontend uses three complementary state management patterns:

| Pattern | Use Case | Persistence | Scope |
|---------|----------|-------------|-------|
| **Zustand Stores** | Client-only state shared across components | In-memory or localStorage | Global |
| **React Query** | Server state (API data) | Cache with refetch | Global |
| **Local useState** | Component-specific UI state | None | Component |

## Decision Tree

```
Is the state from the server (API data)?
├─ YES → Use React Query
└─ NO → Is the state needed by multiple components?
         ├─ YES → Does it need to persist across page refreshes?
         │        ├─ YES → Use Zustand with persist middleware
         │        └─ NO → Use Zustand (no persist)
         └─ NO → Use local useState
```

---

## 1. Zustand Stores

Located in `frontend/src/stores/`. Use for **client-side global state** that multiple components need to access or modify.

### Available Stores

#### `useSettingsStore` - User Preferences
**Purpose**: Persisted user preferences (theme, goals, display options).

**Persistence**: localStorage via `zustand/middleware/persist`

**Example usage**:
```jsx
import { useSettingsStore } from '@/stores'

function Settings() {
  const { theme, setTheme, dailyReviewGoal } = useSettingsStore()
  
  return (
    <select value={theme} onChange={(e) => setTheme(e.target.value)}>
      <option value="dark">Dark</option>
      <option value="light">Light</option>
    </select>
  )
}
```

#### `useUiStore` - Transient UI State
**Purpose**: Modal visibility, command palette, mobile menu, note viewer panel.

**Persistence**: None (resets on page refresh)

**Example usage**:
```jsx
import { useUiStore } from '@/stores'

function Header() {
  const { openModal, toggleCommandPalette } = useUiStore()
  
  return (
    <>
      <button onClick={() => openModal('capture')}>New Capture</button>
      <button onClick={toggleCommandPalette}>⌘K</button>
    </>
  )
}
```

#### `usePracticeStore` - Practice Session State
**Purpose**: Active practice session progress, responses, timing.

**Persistence**: None (session is ephemeral)

**Example usage**:
```jsx
import { usePracticeStore } from '@/stores'

function PracticeSession() {
  const { session, currentItemIndex, submitResponse, nextItem } = usePracticeStore()
  const currentItem = usePracticeStore((s) => s.getCurrentItem())
  
  const handleAnswer = (response) => {
    submitResponse(currentItem.id, response, evaluation)
    nextItem()
  }
}
```

#### `useReviewStore` - Spaced Repetition Queue
**Purpose**: Review queue cards, progress, rating history.

**Persistence**: None (queue fetched fresh each session)

**Example usage**:
```jsx
import { useReviewStore } from '@/stores'

function ReviewQueue() {
  const { setCards, showAnswerAction, nextCard, recordRating } = useReviewStore()
  const currentCard = useReviewStore((s) => s.getCurrentCard())
  const stats = useReviewStore((s) => s.getSessionStats())
}
```

### Store Design Conventions

1. **Structure**: Each store follows this pattern:
   ```javascript
   export const useMyStore = create((set, get) => ({
     // =====================
     // State
     // =====================
     myValue: initialValue,
     
     // =====================
     // Actions
     // =====================
     setMyValue: (value) => set({ myValue: value }),
     
     // =====================
     // Selectors (for derived state)
     // =====================
     getComputedValue: () => {
       const { myValue } = get()
       return myValue * 2
     },
     
     // =====================
     // Reset
     // =====================
     reset: () => set({ myValue: initialValue }),
   }))
   ```

2. **Naming**: 
   - Stores: `use<Domain>Store` (e.g., `useSettingsStore`)
   - Actions: verb + noun (e.g., `setTheme`, `openModal`, `nextCard`)
   - Selectors: `get<Thing>` (e.g., `getCurrentCard`, `getSessionStats`)

3. **Selectors**: Use selectors for derived/computed state to avoid recalculation:
   ```jsx
   // Good - only re-renders when currentCard changes
   const currentCard = useReviewStore((s) => s.getCurrentCard())
   
   // Avoid - re-renders on any store change
   const { cards, currentIndex } = useReviewStore()
   const currentCard = cards[currentIndex]
   ```

---

## 2. React Query (TanStack Query)

Use for **server state** - data that lives on the backend and needs to be fetched, cached, and synchronized.

### When to Use React Query

- Fetching data from API endpoints
- Caching responses to avoid redundant requests
- Background refetching for fresh data
- Optimistic updates for mutations
- Loading/error states for async operations

### Patterns

#### Fetching Data
```jsx
import { useQuery } from '@tanstack/react-query'
import { knowledgeApi } from '@/api'

function Knowledge() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['knowledge', 'list'],
    queryFn: () => knowledgeApi.list(),
  })
  
  if (isLoading) return <Spinner />
  if (error) return <ErrorMessage error={error} />
  
  return <KnowledgeList items={data} />
}
```

#### Mutations
```jsx
import { useMutation, useQueryClient } from '@tanstack/react-query'

function CaptureForm() {
  const queryClient = useQueryClient()
  
  const mutation = useMutation({
    mutationFn: (data) => captureApi.create(data),
    onSuccess: () => {
      // Invalidate and refetch
      queryClient.invalidateQueries({ queryKey: ['captures'] })
    },
  })
  
  return (
    <form onSubmit={(e) => mutation.mutate(formData)}>
      {mutation.isPending && <Spinner />}
      {mutation.isError && <Error message={mutation.error.message} />}
    </form>
  )
}
```

### Query Key Conventions

Use hierarchical keys for cache management:
```javascript
// List queries
['knowledge', 'list']
['knowledge', 'list', { topic: 'machine-learning' }]

// Detail queries
['knowledge', 'detail', contentId]

// Related data
['knowledge', contentId, 'cards']
['knowledge', contentId, 'concepts']
```

---

## 3. Local useState

Use for **component-specific state** that:
- Is only needed by one component (and maybe its direct children)
- Doesn't need to persist
- Doesn't need to be shared

### Examples

```jsx
function SearchInput() {
  // Local UI state
  const [inputValue, setInputValue] = useState('')
  const [isFocused, setIsFocused] = useState(false)
  
  return (
    <input
      value={inputValue}
      onChange={(e) => setInputValue(e.target.value)}
      onFocus={() => setIsFocused(true)}
      onBlur={() => setIsFocused(false)}
    />
  )
}
```

```jsx
function CollapsibleSection({ title, children }) {
  // Component-local toggle state
  const [isOpen, setIsOpen] = useState(true)
  
  return (
    <div>
      <button onClick={() => setIsOpen(!isOpen)}>{title}</button>
      {isOpen && children}
    </div>
  )
}
```

### When NOT to Use useState

- Form state across multiple steps → Consider `useReducer` or form library
- State needed by sibling components → Lift to Zustand
- Derived from server data → Use React Query's `select` option

---

## Custom Hooks

Located in `frontend/src/hooks/`. Use for **reusable stateful logic**.

### Available Hooks

| Hook | Purpose |
|------|---------|
| `useLocalStorage` | Persist state to localStorage with SSR safety |
| `useDebouncedSearch` | Debounced search input with loading state |
| `useKeyboardShortcuts` | Register keyboard shortcuts |

### Creating Custom Hooks

Good candidates for custom hooks:
- Encapsulating useState + useEffect patterns
- Abstracting browser APIs (localStorage, media queries)
- Combining multiple hooks for a specific feature

```jsx
// Example: Custom hook combining Zustand + React Query
function useReviewSession() {
  const store = useReviewStore()
  
  const { data: dueCards } = useQuery({
    queryKey: ['cards', 'due'],
    queryFn: () => reviewApi.getDueCards(),
  })
  
  useEffect(() => {
    if (dueCards) {
      store.setCards(dueCards)
    }
  }, [dueCards])
  
  return {
    ...store,
    isLoading: !dueCards,
  }
}
```

---

## Anti-Patterns to Avoid

### 1. Prop Drilling Through Many Levels
❌ **Bad**: Passing state through 4+ component levels
```jsx
<App theme={theme}>
  <Layout theme={theme}>
    <Sidebar theme={theme}>
      <NavItem theme={theme} />  // Too many levels!
```

✅ **Good**: Use Zustand for shared state
```jsx
// In NavItem.jsx
const { theme } = useSettingsStore()
```

### 2. Duplicating Server State
❌ **Bad**: Copying API data into Zustand
```jsx
// Don't do this
const [users, setUsers] = useState([])
useEffect(() => {
  fetchUsers().then(setUsers)
}, [])
```

✅ **Good**: Use React Query
```jsx
const { data: users } = useQuery({
  queryKey: ['users'],
  queryFn: fetchUsers,
})
```

### 3. Overusing Global State
❌ **Bad**: Putting form input values in Zustand
```jsx
// Don't do this for simple forms
const { searchQuery, setSearchQuery } = useSearchStore()
```

✅ **Good**: Use local state for component-specific values
```jsx
const [searchQuery, setSearchQuery] = useState('')
```

### 4. Not Using Selectors
❌ **Bad**: Subscribing to entire store
```jsx
const store = useReviewStore()  // Re-renders on ANY change
```

✅ **Good**: Subscribe to specific slices
```jsx
const currentCard = useReviewStore((s) => s.getCurrentCard())
const stats = useReviewStore((s) => s.getSessionStats())
```

---

## Summary Cheat Sheet

| I need to... | Use |
|--------------|-----|
| Fetch data from API | React Query `useQuery` |
| Create/update/delete via API | React Query `useMutation` |
| Share UI state (modals, menus) | `useUiStore` |
| Persist user preferences | `useSettingsStore` |
| Track review session progress | `useReviewStore` |
| Track practice session progress | `usePracticeStore` |
| Toggle within a single component | Local `useState` |
| Form input value | Local `useState` (or form library) |
| Debounced search | `useDebouncedSearch` hook |
| Keyboard shortcuts | `useKeyboardShortcuts` hook |
