/**
 * Vault/Knowledge Explorer Page
 * 
 * Unified page for browsing and exploring the knowledge base.
 * Available at the /knowledge route.
 * 
 * Features:
 * - Tree view with collapsible folders
 * - List view with note cards
 * - Full-width inline note viewer
 * - Search with debouncing
 * - URL params for deep linking (?note=path/to/note.md)
 * - Command palette integration (⌘K)
 */

import { useState, useMemo, useEffect, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useSearchParams } from 'react-router-dom'
import { clsx } from 'clsx'
import { 
  ChevronRightIcon, 
  XMarkIcon, 
  TagIcon, 
  CalendarIcon, 
  FolderIcon, 
  SparklesIcon,
  AdjustmentsHorizontalIcon,
  DocumentArrowDownIcon,
  EyeIcon,
  EyeSlashIcon,
} from '@heroicons/react/24/outline'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import rehypeRaw from 'rehype-raw'
import rehypeHighlight from 'rehype-highlight'
import { Link } from 'react-router-dom'
import { format } from 'date-fns'
import toast from 'react-hot-toast'
import { Input, Badge, PageLoader, EmptyState, Skeleton, IconButton, TagBadge, Button } from '../components/common'
import { vaultApi } from '../api/vault'
import { reviewApi } from '../api/review'
import { practiceApi } from '../api/practice'
import { useUiStore, useSettingsStore } from '../stores'
import { useDebounce } from '../hooks/useDebouncedSearch'
import { fadeInUp, staggerContainer } from '../utils/animations'
import { VAULT_PAGE_SIZE } from '../constants'
import { API_URL } from '../api/client'

// Helper to convert vault-relative image paths to API URLs
const convertImagePathToApiUrl = (src) => {
  if (!src) return src
  
  // Already an absolute URL
  if (src.startsWith('http://') || src.startsWith('https://')) {
    return src
  }
  
  // Already an API URL (relative) - prepend API_URL
  if (src.startsWith('/api/')) {
    return `${API_URL}${src}`
  }
  
  // Vault-relative path (e.g., "assets/images/content_id/page_1_img_0.png")
  if (src.startsWith('assets/')) {
    return `${API_URL}/api/vault/${src}`
  }
  
  // Handle paths that might have leading slash
  if (src.startsWith('/assets/')) {
    return `${API_URL}/api/vault${src}`
  }
  
  // Default: assume it's a vault-relative path
  return `${API_URL}/api/vault/assets/${src}`
}

// Helper to process wiki-links [[title]] and image embeds ![[path]] in text content
// The showImages parameter controls whether images are rendered or hidden
const processWikiLinks = (text, onLinkClick, showImages = true) => {
  if (typeof text !== 'string') return text
  
  // Match ![[image]] for image embeds (must be checked first)
  // and [[link]] or [[link|display text]] for links
  const combinedRegex = /!\[\[([^\]]+)\]\]|\[\[([^\]|]+)(?:\|([^\]]+))?\]\]/g
  const parts = []
  let lastIndex = 0
  let match

  while ((match = combinedRegex.exec(text)) !== null) {
    // Add text before the match
    if (match.index > lastIndex) {
      parts.push(text.slice(lastIndex, match.index))
    }
    
    if (match[1]) {
      // Image embed: ![[path]]
      // Only render if showImages is true
      if (showImages) {
        const imagePath = match[1]
        const imageUrl = convertImagePathToApiUrl(imagePath)
        parts.push(
          <img
            key={match.index}
            src={imageUrl}
            alt={imagePath.split('/').pop() || 'Embedded image'}
            className="max-w-full h-auto rounded-lg shadow-lg my-4 border border-slate-700"
            loading="lazy"
            onError={(e) => {
              e.target.style.display = 'none'
              console.warn(`Failed to load image: ${imageUrl}`)
            }}
          />
        )
      }
      // If showImages is false, we skip adding the image (effectively hiding it)
    } else {
      // Wiki-link: [[link]] or [[link|display text]]
      const linkTarget = match[2] // The actual link target
      const displayText = match[3] || match[2] // Display text (or same as target)
      
      // Create a clickable link that searches for the note
      parts.push(
        <Link
          key={match.index}
          to={`/knowledge?search=${encodeURIComponent(linkTarget)}`}
          className="text-indigo-400 hover:text-indigo-300 underline decoration-indigo-400/50 hover:decoration-indigo-300 transition-colors"
          title={`Open: ${linkTarget}`}
        >
          {displayText}
        </Link>
      )
    }
    
    lastIndex = match.index + match[0].length
  }
  
  // Add remaining text
  if (lastIndex < text.length) {
    parts.push(text.slice(lastIndex))
  }
  
  return parts.length > 0 ? parts : text
}

// Helper to detect and parse dict-like task strings from old template format
// Pattern: {'task': '...', 'task_type': '...', 'priority': '...', 'estimated_time': '...'}
// Handles both single and double quotes, and task text that contains apostrophes
const parseFollowupTaskDict = (text) => {
  if (typeof text !== 'string') return null
  
  // Check if this looks like a Python dict with task fields
  if (!text.includes("'task':") || !text.includes("'task_type':")) {
    return null
  }
  
  // Extract each field using specific patterns that handle both quote types
  // For task field (may contain apostrophes, so Python uses double quotes)
  let taskMatch = text.match(/'task':\s*"([^"]+)"/) || text.match(/'task':\s*'([^']+)'/)
  // For task_type
  let typeMatch = text.match(/'task_type':\s*'([^']+)'/) || text.match(/'task_type':\s*"([^"]+)"/)
  // For priority
  let priorityMatch = text.match(/'priority':\s*'([^']+)'/) || text.match(/'priority':\s*"([^"]+)"/)
  // For estimated_time
  let timeMatch = text.match(/'estimated_time':\s*'([^']+)'/) || text.match(/'estimated_time':\s*"([^"]+)"/)
  
  // All fields must be present
  if (taskMatch && typeMatch && priorityMatch && timeMatch) {
    return {
      task: taskMatch[1],
      taskType: typeMatch[1],
      priority: priorityMatch[1],
      estimatedTime: timeMatch[1],
    }
  }
  return null
}

// Render a parsed follow-up task with nice formatting
const renderFollowupTask = (taskData, key) => {
  const priorityColors = {
    HIGH: 'bg-red-500/20 text-red-400 border-red-500/30',
    MEDIUM: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
    LOW: 'bg-green-500/20 text-green-400 border-green-500/30',
  }
  const typeColors = {
    RESEARCH: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
    PRACTICE: 'bg-green-500/20 text-green-400 border-green-500/30',
    CONNECT: 'bg-purple-500/20 text-purple-400 border-purple-500/30',
    APPLY: 'bg-orange-500/20 text-orange-400 border-orange-500/30',
    REVIEW: 'bg-cyan-500/20 text-cyan-400 border-cyan-500/30',
  }
  const timeDisplay = {
    '15MIN': '15 min',
    '30MIN': '30 min',
    '1HR': '1 hour',
    '2HR_PLUS': '2+ hours',
  }

  const priorityClass = priorityColors[taskData.priority?.toUpperCase()] || priorityColors.MEDIUM
  const typeClass = typeColors[taskData.taskType?.toUpperCase()] || 'bg-slate-500/20 text-slate-400 border-slate-500/30'
  const time = timeDisplay[taskData.estimatedTime?.toUpperCase()] || taskData.estimatedTime

  return (
    <span key={key} className="block">
      <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border mr-2 ${typeClass}`}>
        {taskData.taskType}
      </span>
      <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border mr-2 ${priorityClass}`}>
        {taskData.priority}
      </span>
      <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-slate-700/50 text-slate-300 mr-2">
        ~{time}
      </span>
      <span className="text-text-primary">{taskData.task}</span>
    </span>
  )
}

// Process text to handle dict-like task strings
const processFollowupTasks = (text) => {
  if (typeof text !== 'string') return text
  
  const taskData = parseFollowupTaskDict(text)
  if (taskData) {
    return renderFollowupTask(taskData, 'task')
  }
  return text
}

// Recursively process children to find and convert wiki-links
// The showImages parameter controls whether images are rendered or hidden
const processChildrenForWikiLinks = (children, showImages = true) => {
  if (!children) return children
  
  if (typeof children === 'string') {
    // First check if it's a dict-like task string
    const taskData = parseFollowupTaskDict(children)
    if (taskData) {
      return renderFollowupTask(taskData, 'task')
    }
    return processWikiLinks(children, null, showImages)
  }
  
  if (Array.isArray(children)) {
    return children.map((child, index) => {
      if (typeof child === 'string') {
        // First check if it's a dict-like task string
        const taskData = parseFollowupTaskDict(child)
        if (taskData) {
          return renderFollowupTask(taskData, index)
        }
        const processed = processWikiLinks(child, null, showImages)
        // If it's still a string (no wiki-links found), return as-is
        if (typeof processed === 'string') return processed
        // Otherwise wrap the array of parts in a fragment
        return <span key={index}>{processed}</span>
      }
      return child
    })
  }
  
  return children
}

// Section visibility configuration
// Note: 'images' has heading: null because images are handled specially in the renderer
const TOGGLEABLE_SECTIONS = {
  summary: { label: 'Summary', heading: '## Summary', default: true },
  keyFindings: { label: 'Key Findings', heading: '## Key Findings', default: true },
  concepts: { label: 'Core Concepts', heading: '## Core Concepts', default: true },
  highlights: { label: 'My Highlights', heading: '## My Highlights', default: true },
  handwrittenNotes: { label: 'Handwritten Notes', heading: '## My Handwritten Notes', default: true },
  masteryQuestions: { label: 'Mastery Questions', heading: '## Mastery Questions', default: true },
  followupTasks: { label: 'Follow-up Tasks', heading: '## Follow-up Tasks', default: true },
  connections: { label: 'Connections', heading: '## Connections', default: true },
  detailedNotes: { label: 'Detailed Notes', heading: '## Detailed Notes', default: true },
  images: { label: 'Images', heading: null, default: true },
}

// Default visibility state is now in useSettingsStore.knowledgeSectionVisibility

// Filter markdown content based on visible sections
const filterMarkdownSections = (content, visibility) => {
  if (!content) return content
  
  // Get list of sections to hide
  const sectionsToHide = Object.entries(visibility)
    .filter(([_, visible]) => !visible)
    .map(([key]) => TOGGLEABLE_SECTIONS[key]?.heading)
    .filter(Boolean)
  
  if (sectionsToHide.length === 0) return content
  
  // Split content into lines and process
  const lines = content.split('\n')
  const result = []
  let skipUntilNextH2 = false
  
  for (const line of lines) {
    // Check if this is a heading we should skip
    if (line.startsWith('## ')) {
      if (sectionsToHide.some(heading => line.startsWith(heading))) {
        skipUntilNextH2 = true
        continue
      } else {
        skipUntilNextH2 = false
      }
    }
    
    if (!skipUntilNextH2) {
      result.push(line)
    }
  }
  
  return result.join('\n')
}

function getNoteDisplayTitle(note) {
  return (
    note?.title ||
    note?.frontmatter?.title ||
    note?.frontmatter?.name ||
    note?.name ||
    ''
  )
}

function getFolderDisplayName(folder) {
  return folder?.folder || ''
}

// Inline note content component that fills available space
function InlineNoteContent({ notePath, onClose }) {
  const queryClient = useQueryClient()
  const [showSettingsPanel, setShowSettingsPanel] = useState(false)
  
  // Use settings store for section visibility (persisted via Zustand)
  const sectionVisibility = useSettingsStore((s) => s.knowledgeSectionVisibility)
  const toggleKnowledgeSection = useSettingsStore((s) => s.toggleKnowledgeSection)
  const setKnowledgeSectionVisibility = useSettingsStore((s) => s.setKnowledgeSectionVisibility)
  
  const { data: note, isLoading, error } = useQuery({
    queryKey: ['note-content', notePath],
    queryFn: () => vaultApi.getNoteContent(notePath),
    enabled: !!notePath,
  })
  
  // Get the topic for the note (using title for better matching)
  const topic = note?.title || note?.frontmatter?.title || note?.name || ''
  
  // Get source URL from frontmatter
  const sourceUrl = note?.frontmatter?.source_url || note?.frontmatter?.url || note?.frontmatter?.doi
  const sourcePath = note?.frontmatter?.source_path
  
  // Fetch existing exercises for this topic
  const { data: exercisesData } = useQuery({
    queryKey: ['exercises', 'topic', topic],
    queryFn: () => practiceApi.listExercises({ topic, limit: 100 }),
    enabled: !!topic,
  })
  
  // Fetch existing cards for this topic
  const { data: cardsData } = useQuery({
    queryKey: ['cards', 'topic', topic],
    queryFn: () => reviewApi.getCardsByTopic(topic, { limit: 100, includeNotDue: true }),
    enabled: !!topic,
  })
  
  const exerciseCount = exercisesData?.length || 0
  const cardCount = cardsData?.cards?.length || cardsData?.total || 0
  
  // Toggle section visibility (using settings store)
  const toggleSection = (sectionKey) => {
    toggleKnowledgeSection(sectionKey)
  }
  
  // Toggle all sections (using settings store)
  const toggleAllSections = (visible) => {
    const newState = Object.fromEntries(
      Object.keys(TOGGLEABLE_SECTIONS).map(key => [key, visible])
    )
    setKnowledgeSectionVisibility(newState)
  }
  
  // Filter content based on visibility
  const filteredContent = useMemo(() => {
    return filterMarkdownSections(note?.content, sectionVisibility)
  }, [note?.content, sectionVisibility])
  
  // Count visible sections
  const visibleCount = Object.values(sectionVisibility).filter(Boolean).length
  const totalSections = Object.keys(TOGGLEABLE_SECTIONS).length

  // Extract topic from note - use title for better context matching
  const getTopic = () => {
    if (!note) return null
    // Use note title as the primary topic for better context matching
    // The card generator searches for content by title/summary keywords
    const title = note.title || note.frontmatter?.title || note.name
    if (title) return title
    // Fallback to folder if no title
    if (note.folder) return note.folder
    // Last resort: use path without filename
    const parts = notePath.split('/')
    return parts.slice(0, -1).join('/') || 'general'
  }

  // Get display name for the note
  const getNoteDisplayName = () => {
    return note?.title || note?.frontmatter?.title || note?.name || notePath
  }

  // Generate cards mutation
  const generateCardsMutation = useMutation({
    mutationFn: ({ topic }) => reviewApi.generateCards({ topic, count: 10, difficulty: 'mixed' }),
    onSuccess: (data) => {
      if (data.generated_count > 0) {
        toast.success(
          <div>
            <strong>Generated {data.generated_count} cards</strong>
            <p className="text-sm opacity-80">Topic: {data.topic}</p>
            <p className="text-sm opacity-80">Total cards for topic: {data.total_cards}</p>
          </div>,
          { duration: 5000 }
        )
      } else {
        toast.error(
          <div>
            <strong>No cards generated</strong>
            <p className="text-sm opacity-80">No matching content found for &quot;{data.topic}&quot;</p>
            <p className="text-sm opacity-80">Try processing this content first via ingestion.</p>
          </div>,
          { duration: 6000 }
        )
      }
      queryClient.invalidateQueries({ queryKey: ['cards'] })
    },
    onError: (error) => {
      const message = error.response?.data?.detail || error.message || 'Failed to generate cards'
      toast.error(message)
    },
  })

  // Human-readable exercise type labels
  const exerciseTypeLabels = {
    free_recall: 'Free Recall',
    self_explain: 'Self Explain',
    worked_example: 'Worked Example',
    code_debug: 'Debug Code',
    code_complete: 'Code Completion',
    code_implement: 'Implementation',
    code_refactor: 'Refactor Code',
    code_explain: 'Explain Code',
    teach_back: 'Teach Back',
    application: 'Application',
    compare_contrast: 'Compare & Contrast',
  }

  // Generate exercises mutation
  const generateExercisesMutation = useMutation({
    mutationFn: ({ topic }) => practiceApi.generateExercise({ topicId: topic, exerciseType: 'free_recall' }),
    onSuccess: (data) => {
      const exerciseType = data?.exercise_type || 'free_recall'
      const typeLabel = exerciseTypeLabels[exerciseType] || exerciseType
      const prompt = data?.prompt?.substring(0, 80) || ''
      const exerciseTopic = data?.topic || getTopic()
      
      toast.success(
        <div className="space-y-2">
          <strong>Generated {typeLabel} Exercise</strong>
          {prompt && (
            <p className="text-sm opacity-90 line-clamp-2">&quot;{prompt}...&quot;</p>
          )}
          <p className="text-xs opacity-70">Topic: {exerciseTopic}</p>
          <Link 
            to={`/exercises?topic=${encodeURIComponent(exerciseTopic)}`}
            className="inline-block text-xs text-indigo-300 hover:text-indigo-200 underline mt-1"
          >
            View in Exercise Catalogue →
          </Link>
        </div>,
        { duration: 6000 }
      )
      queryClient.invalidateQueries({ queryKey: ['exercises'] })
      queryClient.invalidateQueries({ queryKey: ['exercises', 'topic'] })
    },
    onError: (error) => {
      const message = error.response?.data?.detail || error.message || 'Failed to generate exercise'
      toast.error(message)
    },
  })

  const handleGenerateCards = () => {
    const topic = getTopic()
    if (!topic) {
      toast.error('Could not determine topic for this note')
      return
    }
    toast.loading(`Generating cards for "${getNoteDisplayName()}"...`, { id: 'generate-cards' })
    generateCardsMutation.mutate({ topic }, {
      onSettled: () => toast.dismiss('generate-cards')
    })
  }

  const handleGenerateExercises = () => {
    const topic = getTopic()
    if (!topic) {
      toast.error('Could not determine topic for this note')
      return
    }
    toast.loading(`Generating exercise for "${getNoteDisplayName()}"...`, { id: 'generate-exercise' })
    generateExercisesMutation.mutate({ topic }, {
      onSettled: () => toast.dismiss('generate-exercise')
    })
  }

  const isGenerating = generateCardsMutation.isPending || generateExercisesMutation.isPending
  
  // Disable generation buttons for exercise content type (to avoid recursive generation)
  const isExerciseContent = note?.frontmatter?.type === 'exercise'

  if (isLoading) {
    return (
      <div className="flex-1 p-8">
        <div className="max-w-4xl mx-auto space-y-4">
          <Skeleton className="h-8 w-2/3" />
          <Skeleton className="h-4 w-1/3" />
          <div className="mt-8 space-y-3">
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-3/4" />
            <Skeleton className="h-32 w-full mt-4" />
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-5/6" />
          </div>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex-1 flex items-center justify-center p-8">
        <div className="text-center">
          <span className="text-4xl mb-4 block">⚠️</span>
          <p className="text-text-secondary">Failed to load note content</p>
          <p className="text-sm text-text-muted mt-2">{error.message}</p>
        </div>
      </div>
    )
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0 }}
      className="flex-1 flex flex-col overflow-hidden"
    >
      {/* Header */}
      <div className="flex items-center justify-between px-8 py-4 border-b border-border-primary bg-bg-secondary">
        <div className="flex-1 min-w-0 pr-4">
          <h1 className="text-2xl font-bold text-text-primary font-heading truncate">
            {getNoteDisplayTitle(note) || 'Untitled'}
          </h1>
          <div className="flex items-center gap-4 mt-1">
            {note?.modified && (
              <p className="text-sm text-text-muted flex items-center gap-2">
                <CalendarIcon className="w-4 h-4" />
                Modified {format(new Date(note.modified), 'MMM d, yyyy')}
              </p>
            )}
            {/* Source link */}
            {(sourceUrl || sourcePath) && (
              <a
                href={sourceUrl || `file://${sourcePath}`}
                target="_blank"
                rel="noopener noreferrer"
                className="text-sm text-indigo-400 hover:text-indigo-300 flex items-center gap-1.5 transition-colors"
              >
                <DocumentArrowDownIcon className="w-4 h-4" />
                {sourceUrl ? 'View Original Source' : 'Open Source File'}
              </a>
            )}
          </div>
        </div>

        <div className="flex items-center gap-2">
          {/* Section visibility settings */}
          <div className="relative">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setShowSettingsPanel(!showSettingsPanel)}
              icon={<AdjustmentsHorizontalIcon className="w-4 h-4" />}
              className={clsx(showSettingsPanel && 'bg-bg-hover')}
            >
              Sections ({visibleCount}/{totalSections})
            </Button>
            
            {/* Settings panel dropdown */}
            <AnimatePresence>
              {showSettingsPanel && (
                <motion.div
                  initial={{ opacity: 0, y: -10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -10 }}
                  className="absolute right-0 top-full mt-2 w-64 bg-bg-elevated border border-border-primary rounded-lg shadow-xl z-50"
                >
                  <div className="p-3 border-b border-border-primary">
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium text-text-primary">Show Sections</span>
                      <div className="flex gap-1">
                        <button
                          onClick={() => toggleAllSections(true)}
                          aria-label="Show all sections"
                          className="text-xs text-indigo-400 hover:text-indigo-300 focus:outline-none focus:underline"
                        >
                          All
                        </button>
                        <span className="text-text-muted" aria-hidden="true">|</span>
                        <button
                          onClick={() => toggleAllSections(false)}
                          aria-label="Hide all sections"
                          className="text-xs text-indigo-400 hover:text-indigo-300 focus:outline-none focus:underline"
                        >
                          None
                        </button>
                      </div>
                    </div>
                  </div>
                  <div className="p-2 max-h-80 overflow-y-auto" role="group" aria-label="Toggle sections visibility">
                    {Object.entries(TOGGLEABLE_SECTIONS).map(([key, config]) => (
                      <button
                        key={key}
                        onClick={() => toggleSection(key)}
                        aria-pressed={sectionVisibility[key]}
                        aria-label={`${sectionVisibility[key] ? 'Hide' : 'Show'} ${config.label} section`}
                        className="w-full flex items-center justify-between px-3 py-2 rounded-md hover:bg-bg-hover transition-colors focus:outline-none focus:ring-2 focus:ring-accent-primary/50"
                      >
                        <span className="text-sm text-text-secondary">{config.label}</span>
                        {sectionVisibility[key] ? (
                          <EyeIcon className="w-4 h-4 text-emerald-400" aria-hidden="true" />
                        ) : (
                          <EyeSlashIcon className="w-4 h-4 text-text-muted" aria-hidden="true" />
                        )}
                      </button>
                    ))}
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
          
          {/* Generation buttons - disabled for exercise content to avoid recursive generation */}
          <span title={isExerciseContent ? 'Cannot generate cards from exercises' : undefined}>
            <Button
              variant="secondary"
              size="sm"
              onClick={handleGenerateCards}
              loading={generateCardsMutation.isPending}
              disabled={isGenerating || isExerciseContent}
              icon={<SparklesIcon className="w-4 h-4" />}
            >
              Generate Cards
            </Button>
          </span>
          <span title={isExerciseContent ? 'Cannot generate exercises from exercises' : undefined}>
            <Button
              variant="secondary"
              size="sm"
              onClick={handleGenerateExercises}
              loading={generateExercisesMutation.isPending}
              disabled={isGenerating || isExerciseContent}
              icon={<SparklesIcon className="w-4 h-4" />}
            >
              Generate Exercises
            </Button>
          </span>
          <IconButton
            icon={<XMarkIcon className="w-5 h-5" />}
            label="Close"
            variant="ghost"
            size="sm"
            onClick={onClose}
          />
        </div>
      </div>

      {/* Metadata bar */}
      {note && (
        <div className="px-8 py-3 border-b border-border-primary bg-bg-primary/50 flex items-center gap-4 flex-wrap">
          {note.folder && (
            <div className="flex items-center gap-2 text-sm text-text-secondary">
              <FolderIcon className="w-4 h-4 text-text-muted" />
              <span>{note.folder}</span>
            </div>
          )}
          {note.frontmatter?.tags && note.frontmatter.tags.length > 0 && (
            <div className="flex items-center gap-2 flex-wrap">
              <TagIcon className="w-4 h-4 text-text-muted" />
              {note.frontmatter.tags.map((tag) => (
                <TagBadge key={tag} tag={tag} size="xs" />
              ))}
            </div>
          )}
          {/* Learning content stats */}
          <div className="flex items-center gap-3 text-sm">
            <span className="text-text-muted">|</span>
            <span className="text-text-secondary">
              <span className="text-indigo-400">{cardCount}</span> cards
            </span>
            <span className="text-text-secondary">
              <span className="text-emerald-400">{exerciseCount}</span> exercises
            </span>
          </div>
          {note.frontmatter?.type && (
            <Badge variant="primary" size="xs">
              {note.frontmatter.type}
            </Badge>
          )}
        </div>
      )}

      {/* Content */}
      <div className="flex-1 overflow-y-auto" onClick={() => setShowSettingsPanel(false)}>
        <div className="max-w-4xl mx-auto px-8 py-8">
          {filteredContent ? (
            <article className="prose prose-invert prose-lg max-w-none">
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                rehypePlugins={[rehypeRaw, rehypeHighlight]}
                components={{
                  a: ({ href, children }) => {
                    const isInternal = href?.startsWith('/') || href?.startsWith('#')
                    if (isInternal) {
                      return (
                        <Link to={href} className="text-accent-secondary hover:text-accent-tertiary">
                          {children}
                        </Link>
                      )
                    }
                    return (
                      <a 
                        href={href} 
                        target="_blank" 
                        rel="noopener noreferrer"
                        className="text-accent-secondary hover:text-accent-tertiary"
                      >
                        {children}
                      </a>
                    )
                  },
                  code: ({ inline, className, children, ...props }) => {
                    if (inline) {
                      return (
                        <code 
                          className="px-1.5 py-0.5 bg-slate-800 rounded text-accent-success text-sm font-mono"
                          {...props}
                        >
                          {children}
                        </code>
                      )
                    }
                    return (
                      <code className={className} {...props}>
                        {children}
                      </code>
                    )
                  },
                  pre: ({ children }) => (
                    <pre className="bg-slate-800/80 rounded-lg p-4 overflow-x-auto">
                      {children}
                    </pre>
                  ),
                  // Support for collapsible sections (details/summary HTML tags)
                  details: ({ children, ...props }) => (
                    <details 
                      className="my-4 p-4 bg-slate-800/50 border border-slate-700 rounded-lg group"
                      {...props}
                    >
                      {children}
                    </details>
                  ),
                  summary: ({ children, ...props }) => (
                    <summary 
                      className="cursor-pointer font-medium text-indigo-400 hover:text-indigo-300 transition-colors select-none list-none flex items-center gap-2"
                      {...props}
                    >
                      <ChevronRightIcon className="w-4 h-4 transition-transform group-open:rotate-90" />
                      {children}
                    </summary>
                  ),
                  // Process wiki-links [[title]] and image embeds ![[path]] in paragraphs and list items
                  // Pass showImages setting to control image visibility
                  p: ({ children, ...props }) => (
                    <p {...props}>{processChildrenForWikiLinks(children, sectionVisibility.images)}</p>
                  ),
                  li: ({ children, ...props }) => (
                    <li {...props}>{processChildrenForWikiLinks(children, sectionVisibility.images)}</li>
                  ),
                  // Handle standard markdown images ![alt](src)
                  // Respect the images visibility setting
                  img: ({ src, alt, ...props }) => {
                    // If images are hidden, don't render
                    if (!sectionVisibility.images) {
                      return null
                    }
                    const imageUrl = convertImagePathToApiUrl(src)
                    return (
                      <img
                        src={imageUrl}
                        alt={alt || 'Image'}
                        className="max-w-full h-auto rounded-lg shadow-lg my-4 border border-slate-700"
                        loading="lazy"
                        onError={(e) => {
                          // Show a placeholder on error
                          e.target.onerror = null
                          e.target.src = 'data:image/svg+xml,' + encodeURIComponent(
                            '<svg xmlns="http://www.w3.org/2000/svg" width="200" height="150" viewBox="0 0 200 150">' +
                            '<rect fill="#1e293b" width="200" height="150"/>' +
                            '<text fill="#64748b" font-family="sans-serif" font-size="14" x="50%" y="50%" text-anchor="middle" dy=".3em">Image not found</text>' +
                            '</svg>'
                          )
                        }}
                        {...props}
                      />
                    )
                  },
                }}
              >
                {filteredContent}
              </ReactMarkdown>
            </article>
          ) : (
            <div className="text-center py-12">
              <span className="text-4xl mb-4 block">📄</span>
              <p className="text-text-secondary">No content available</p>
            </div>
          )}
        </div>
      </div>
    </motion.div>
  )
}

// Simple folder tree component that works with the vault API structure
function FolderTree({ folders, notesByFolder, selectedNote, onNoteSelect }) {
  const [expandedFolders, setExpandedFolders] = useState({})

  const toggleFolder = (folder) => {
    setExpandedFolders(prev => ({
      ...prev,
      [folder]: !prev[folder]
    }))
  }

  if (!folders || folders.length === 0) {
    return (
      <div className="text-center py-8 text-text-muted text-sm">
        No folders found
      </div>
    )
  }

  return (
    <div className="space-y-1">
      {folders.map((folder) => {
        const folderNotes = notesByFolder[folder.folder] || []
        const isExpanded = expandedFolders[folder.folder]
        
        return (
          <div key={folder.folder}>
            {/* Folder header */}
            <button
              onClick={() => toggleFolder(folder.folder)}
              aria-expanded={isExpanded}
              aria-controls={`folder-notes-${folder.folder.replace(/[^a-zA-Z0-9]/g, '-')}`}
              aria-label={`${folder.folder} folder, ${folder.note_count} notes, ${isExpanded ? 'collapse' : 'expand'}`}
              className={clsx(
                'w-full flex items-center gap-2 py-2 px-2 rounded-lg text-left',
                'hover:bg-bg-hover transition-colors',
                'focus:outline-none focus:ring-2 focus:ring-accent-primary/50',
                isExpanded && 'bg-bg-hover/50'
              )}
            >
              <motion.span
                animate={{ rotate: isExpanded ? 90 : 0 }}
                transition={{ duration: 0.15 }}
              >
                <ChevronRightIcon className="w-4 h-4 text-text-muted" />
              </motion.span>
              <span className="text-lg">{folder.icon || '📁'}</span>
              <span className="flex-1 text-sm font-medium text-text-primary truncate">
                {folder.folder}
              </span>
              <span className="text-xs text-text-muted">
                {folder.note_count}
              </span>
            </button>

            {/* Notes in folder */}
            <AnimatePresence>
              {isExpanded && folderNotes.length > 0 && (
                <motion.div
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: 'auto', opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  className="overflow-hidden"
                  id={`folder-notes-${folder.folder.replace(/[^a-zA-Z0-9]/g, '-')}`}
                  role="group"
                  aria-label={`Notes in ${folder.folder}`}
                >
                  <div className="pl-8 space-y-0.5">
                    {folderNotes.map((note) => (
                      <button
                        key={note.path}
                        onClick={() => onNoteSelect(note.path)}
                        aria-current={selectedNote === note.path ? 'page' : undefined}
                        className={clsx(
                          'w-full text-left py-1.5 px-2 rounded text-sm',
                          'transition-colors truncate',
                          'focus:outline-none focus:ring-2 focus:ring-accent-primary/50',
                          selectedNote === note.path
                            ? 'bg-indigo-500/20 text-indigo-300'
                            : 'text-text-secondary hover:text-text-primary hover:bg-bg-hover'
                        )}
                      >
                        {note.title || note.name}
                      </button>
                    ))}
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        )
      })}
    </div>
  )
}

export function Knowledge() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [selectedNote, setSelectedNote] = useState(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [viewMode, setViewMode] = useState('tree') // 'tree' | 'list'
  
  // Track the search term we're waiting to auto-select for (from URL navigation)
  const pendingAutoSelectSearchRef = useRef(null)
  
  const openCommandPalette = useUiStore((s) => s.openCommandPalette)
  
  // Debounce the search query to avoid too many API calls
  const debouncedSearch = useDebounce(searchQuery, 300)

  // Sync with URL params (supports ?note=path/to/note.md and ?search=query)
  // Only re-run when searchParams changes - NOT when selectedNote changes
  // to avoid infinite loops between this effect and the auto-select effect
  useEffect(() => {
    const noteParam = searchParams.get('note')
    const searchParam = searchParams.get('search')
    
    if (noteParam) {
      setSelectedNote(decodeURIComponent(noteParam))
      pendingAutoSelectSearchRef.current = null
    } else if (!noteParam) {
      // Clear selection if note param is removed from URL (e.g., browser back)
      // Use functional update to avoid needing selectedNote in deps
      setSelectedNote(prev => prev ? null : prev)
    }
    if (searchParam) {
      setSearchQuery(searchParam)
      // Store the search term we need to wait for before auto-selecting
      pendingAutoSelectSearchRef.current = searchParam
      // Switch to list view for better search UX
      setViewMode('list')
    }
  }, [searchParams]) // Only re-run when URL params change

  // Update URL when note selection changes
  const handleNoteSelect = (notePath) => {
    setSelectedNote(notePath)
    if (notePath) {
      setSearchParams({ note: notePath }, { replace: true })
    } else {
      setSearchParams({}, { replace: true })
    }
  }

  // Handle closing note (also clears URL param)
  const handleCloseNote = () => {
    setSelectedNote(null)
    setSearchParams({}, { replace: true })
  }

  // Fetch topics/folders
  const { data: topicsData, isLoading: topicsLoading } = useQuery({
    queryKey: ['vault', 'folders'],
    queryFn: vaultApi.getFolders,
  })

  // Fetch all notes with pagination - tree view needs the full list
  const { data: notesData, isLoading: notesLoading } = useQuery({
    queryKey: ['vault', 'notes', 'all', debouncedSearch],
    queryFn: async () => {
      const allNotes = []
      let page = 1
      let hasMore = true
      
      while (hasMore) {
        const response = await vaultApi.getNotes({ 
          search: debouncedSearch || undefined, 
          page,
          pageSize: VAULT_PAGE_SIZE 
        })
        allNotes.push(...(response.notes || []))
        hasMore = response.has_more
        page++
      }
      
      return { notes: allNotes, total: allNotes.length }
    },
  })

  const topics = topicsData?.folders || []
  const notes = useMemo(() => notesData?.notes || [], [notesData])

  const isLoading = topicsLoading || notesLoading

  const collator = useMemo(
    () => new Intl.Collator(undefined, { numeric: true, sensitivity: 'base' }),
    []
  )

  const sortedTopics = useMemo(() => {
    return [...topics].sort((a, b) =>
      collator.compare(getFolderDisplayName(a), getFolderDisplayName(b))
    )
  }, [topics, collator])

  const sortedNotes = useMemo(() => {
    return [...notes].sort((a, b) =>
      collator.compare(getNoteDisplayTitle(a), getNoteDisplayTitle(b))
    )
  }, [notes, collator])

  // Auto-select best matching note when coming from graph with search param
  useEffect(() => {
    // Only auto-select when:
    // 1. We have a pending search from URL navigation
    // 2. The debounced search has caught up (matches the pending search)
    // 3. Notes are loaded and we don't already have a selection
    const pendingSearch = pendingAutoSelectSearchRef.current
    if (
      pendingSearch && 
      debouncedSearch === pendingSearch && 
      notes.length > 0 && 
      !notesLoading && 
      !selectedNote
    ) {
      // Find the best matching note by comparing titles
      // Prefer exact title match, then closest match
      const searchLower = pendingSearch.toLowerCase()
      
      let bestMatch = notes[0]
      let bestScore = 0
      
      for (const note of notes) {
        const titleLower = (note.title || note.name || '').toLowerCase()
        
        // Exact match gets highest score
        if (titleLower === searchLower) {
          bestMatch = note
          break
        }
        
        // Check if title contains the search or vice versa
        if (titleLower.includes(searchLower) || searchLower.includes(titleLower)) {
          const score = Math.min(titleLower.length, searchLower.length) / 
                       Math.max(titleLower.length, searchLower.length)
          if (score > bestScore) {
            bestScore = score
            bestMatch = note
          }
        }
      }
      
      if (bestMatch?.path) {
        setSelectedNote(bestMatch.path)
        setSearchParams({ note: bestMatch.path }, { replace: true })
      }
      pendingAutoSelectSearchRef.current = null
    }
  }, [notes, notesLoading, selectedNote, setSearchParams, debouncedSearch])

  // Group notes by folder for tree view
  // Notes in subfolders (e.g., sources/articles/tech) should be grouped under
  // their parent content type folder (e.g., sources/articles)
  const notesByTopic = useMemo(() => {
    const grouped = {}
    const topicFolders = topics.map(t => t.folder)
    
    sortedNotes.forEach(note => {
      const noteFolder = note.folder || ''
      // Find the matching content type folder (note folder may be a subfolder)
      const matchingTopic = topicFolders.find(topicFolder => 
        noteFolder === topicFolder || noteFolder.startsWith(topicFolder + '/')
      )
      const groupKey = matchingTopic || noteFolder || 'Uncategorized'
      if (!grouped[groupKey]) grouped[groupKey] = []
      grouped[groupKey].push(note)
    })

    // Ensure notes are always alphabetically sorted within each folder
    for (const key of Object.keys(grouped)) {
      grouped[key].sort((a, b) =>
        collator.compare(getNoteDisplayTitle(a), getNoteDisplayTitle(b))
      )
    }

    return grouped
  }, [sortedNotes, topics, collator])

  if (isLoading) {
    return <PageLoader message="Loading knowledge base..." />
  }

  return (
    <div className="min-h-screen bg-bg-primary flex">
      {/* Sidebar */}
      <motion.div
        variants={staggerContainer}
        initial="hidden"
        animate="show"
        className="w-80 border-r border-border-primary bg-bg-secondary flex flex-col"
      >
        {/* Header */}
        <motion.div variants={fadeInUp} className="p-4 border-b border-border-primary">
          <h1 className="text-xl font-bold text-text-primary font-heading mb-4">
            📚 Knowledge
          </h1>
          
          {/* Search */}
          <div className="relative">
            <Input
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search notes..."
              className="pl-10"
            />
            <span className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted">
              🔍
            </span>
            {/* Keyboard hint */}
            <button
              onClick={openCommandPalette}
              aria-label="Open command palette (Command K)"
              className="absolute right-2 top-1/2 -translate-y-1/2 px-2 py-0.5 text-xs bg-bg-tertiary text-text-muted rounded hover:bg-bg-hover focus:outline-none focus:ring-2 focus:ring-accent-primary/50"
            >
              ⌘K
            </button>
          </div>
        </motion.div>

        {/* View toggle */}
        <motion.div variants={fadeInUp} className="p-3 border-b border-border-primary">
          <div className="flex items-center gap-1 bg-bg-tertiary rounded-lg p-1" role="tablist" aria-label="View mode">
            <button
              role="tab"
              aria-selected={viewMode === 'tree'}
              aria-controls="notes-panel"
              onClick={() => setViewMode('tree')}
              className={clsx(
                'flex-1 py-1.5 text-sm rounded-md transition-colors',
                'focus:outline-none focus:ring-2 focus:ring-accent-primary/50',
                viewMode === 'tree'
                  ? 'bg-bg-elevated text-text-primary'
                  : 'text-text-muted hover:text-text-secondary'
              )}
            >
              🌲 Tree
            </button>
            <button
              role="tab"
              aria-selected={viewMode === 'list'}
              aria-controls="notes-panel"
              onClick={() => setViewMode('list')}
              className={clsx(
                'flex-1 py-1.5 text-sm rounded-md transition-colors',
                'focus:outline-none focus:ring-2 focus:ring-accent-primary/50',
                viewMode === 'list'
                  ? 'bg-bg-elevated text-text-primary'
                  : 'text-text-muted hover:text-text-secondary'
              )}
            >
              📋 List
            </button>
          </div>
        </motion.div>

        {/* Content */}
        <motion.div variants={fadeInUp} className="flex-1 overflow-y-auto p-3" id="notes-panel" role="tabpanel" aria-label="Notes list">
          {viewMode === 'tree' ? (
            <FolderTree
              folders={sortedTopics}
              notesByFolder={notesByTopic}
              selectedNote={selectedNote}
              onNoteSelect={handleNoteSelect}
            />
          ) : (
            <div className="space-y-2" role="listbox" aria-label="Notes">
              {sortedNotes.map((note) => (
                <motion.button
                  key={note.path}
                  whileHover={{ x: 4 }}
                  onClick={() => handleNoteSelect(note.path)}
                  role="option"
                  aria-selected={selectedNote === note.path}
                  className={clsx(
                    'w-full text-left p-3 rounded-lg transition-colors',
                    'focus:outline-none focus:ring-2 focus:ring-accent-primary/50',
                    selectedNote === note.path
                      ? 'bg-indigo-500/20 border border-indigo-500/30'
                      : 'hover:bg-bg-hover'
                  )}
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0">
                      <p className="text-sm font-medium text-text-primary truncate">
                        {getNoteDisplayTitle(note)}
                      </p>
                      <p className="text-xs text-text-muted mt-0.5">
                        {note.folder || 'Uncategorized'}
                      </p>
                    </div>
                    {note.content_type && (
                      <Badge size="xs" variant="default">
                        {note.content_type}
                      </Badge>
                    )}
                  </div>
                </motion.button>
              ))}
              
              {notes.length === 0 && (
                <div className="text-center py-8">
                  <p className="text-sm text-text-muted">No notes found</p>
                </div>
              )}
            </div>
          )}
        </motion.div>

        {/* Stats */}
        <motion.div 
          variants={fadeInUp}
          className="p-4 border-t border-border-primary bg-bg-primary"
        >
          <div className="flex items-center justify-between text-xs text-text-muted">
            <span>{topics.length} topics</span>
            <span>{notes.length} notes</span>
          </div>
        </motion.div>
      </motion.div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col bg-bg-primary">
        <AnimatePresence mode="wait">
          {selectedNote ? (
            <InlineNoteContent
              key={selectedNote}
              notePath={selectedNote}
              onClose={handleCloseNote}
            />
          ) : (
            <motion.div
              key="empty"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="flex-1 flex items-center justify-center p-8"
            >
              <EmptyState
                icon="📖"
                title="Select a note"
                description="Choose a note from the sidebar to view its contents, or use the search to find specific topics."
                onAction={openCommandPalette}
                actionLabel="Search (⌘K)"
              />
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  )
}

export default Knowledge
