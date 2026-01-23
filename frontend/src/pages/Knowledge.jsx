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
import { ChevronRightIcon, XMarkIcon, TagIcon, CalendarIcon, FolderIcon, SparklesIcon } from '@heroicons/react/24/outline'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import rehypeHighlight from 'rehype-highlight'
import { Link } from 'react-router-dom'
import { format } from 'date-fns'
import toast from 'react-hot-toast'
import { Input, Badge, PageLoader, EmptyState, Skeleton, IconButton, TagBadge, Button } from '../components/common'
import { vaultApi } from '../api/vault'
import { reviewApi } from '../api/review'
import { practiceApi } from '../api/practice'
import { useUiStore } from '../stores'
import { useDebounce } from '../hooks/useDebouncedSearch'
import { fadeInUp, staggerContainer } from '../utils/animations'

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
  
  const { data: note, isLoading, error } = useQuery({
    queryKey: ['note-content', notePath],
    queryFn: () => vaultApi.getNoteContent(notePath),
    enabled: !!notePath,
  })

  // Extract topic from note folder or path for generation
  const getTopic = () => {
    if (!note) return null
    // Use folder as topic, or extract from path
    if (note.folder) return note.folder
    // Fallback: use path without filename
    const parts = notePath.split('/')
    return parts.slice(0, -1).join('/') || 'general'
  }

  // Generate cards mutation
  const generateCardsMutation = useMutation({
    mutationFn: ({ topic }) => reviewApi.generateCards({ topic, count: 10, difficulty: 'mixed' }),
    onSuccess: (data) => {
      toast.success(`Generated ${data.generated_count} cards for "${data.topic}"`)
      queryClient.invalidateQueries({ queryKey: ['cards'] })
    },
    onError: (error) => {
      const message = error.response?.data?.detail || error.message || 'Failed to generate cards'
      toast.error(message)
    },
  })

  // Generate exercises mutation
  const generateExercisesMutation = useMutation({
    mutationFn: ({ topic }) => practiceApi.generateExercise({ topicId: topic, exerciseType: 'free_recall' }),
    onSuccess: () => {
      toast.success('Generated exercise successfully!')
      queryClient.invalidateQueries({ queryKey: ['exercises'] })
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
    generateCardsMutation.mutate({ topic })
  }

  const handleGenerateExercises = () => {
    const topic = getTopic()
    if (!topic) {
      toast.error('Could not determine topic for this note')
      return
    }
    generateExercisesMutation.mutate({ topic })
  }

  const isGenerating = generateCardsMutation.isPending || generateExercisesMutation.isPending

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
          {note?.modified && (
            <p className="text-sm text-text-muted mt-1 flex items-center gap-2">
              <CalendarIcon className="w-4 h-4" />
              Modified {format(new Date(note.modified), 'MMM d, yyyy')}
            </p>
          )}
        </div>

        <div className="flex items-center gap-2">
          {/* Generation buttons */}
          <Button
            variant="secondary"
            size="sm"
            onClick={handleGenerateCards}
            loading={generateCardsMutation.isPending}
            disabled={isGenerating}
            icon={<SparklesIcon className="w-4 h-4" />}
          >
            Generate Cards
          </Button>
          <Button
            variant="secondary"
            size="sm"
            onClick={handleGenerateExercises}
            loading={generateExercisesMutation.isPending}
            disabled={isGenerating}
            icon={<SparklesIcon className="w-4 h-4" />}
          >
            Generate Exercises
          </Button>
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
          {note.frontmatter?.type && (
            <Badge variant="primary" size="xs">
              {note.frontmatter.type}
            </Badge>
          )}
        </div>
      )}

      {/* Content */}
      <div className="flex-1 overflow-y-auto">
        <div className="max-w-4xl mx-auto px-8 py-8">
          {note?.content ? (
            <article className="prose prose-invert prose-lg max-w-none">
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                rehypePlugins={[rehypeHighlight]}
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
                }}
              >
                {note.content}
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
              className={clsx(
                'w-full flex items-center gap-2 py-2 px-2 rounded-lg text-left',
                'hover:bg-bg-hover transition-colors',
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
                >
                  <div className="pl-8 space-y-0.5">
                    {folderNotes.map((note) => (
                      <button
                        key={note.path}
                        onClick={() => onNoteSelect(note.path)}
                        className={clsx(
                          'w-full text-left py-1.5 px-2 rounded text-sm',
                          'transition-colors truncate',
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
      const pageSize = 200 // Fetch in reasonable chunks
      
      while (hasMore) {
        const response = await vaultApi.getNotes({ 
          search: debouncedSearch || undefined, 
          page,
          pageSize 
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
              className="absolute right-2 top-1/2 -translate-y-1/2 px-2 py-0.5 text-xs bg-bg-tertiary text-text-muted rounded hover:bg-bg-hover"
            >
              ⌘K
            </button>
          </div>
        </motion.div>

        {/* View toggle */}
        <motion.div variants={fadeInUp} className="p-3 border-b border-border-primary">
          <div className="flex items-center gap-1 bg-bg-tertiary rounded-lg p-1">
            <button
              onClick={() => setViewMode('tree')}
              className={clsx(
                'flex-1 py-1.5 text-sm rounded-md transition-colors',
                viewMode === 'tree'
                  ? 'bg-bg-elevated text-text-primary'
                  : 'text-text-muted hover:text-text-secondary'
              )}
            >
              🌲 Tree
            </button>
            <button
              onClick={() => setViewMode('list')}
              className={clsx(
                'flex-1 py-1.5 text-sm rounded-md transition-colors',
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
        <motion.div variants={fadeInUp} className="flex-1 overflow-y-auto p-3">
          {viewMode === 'tree' ? (
            <FolderTree
              folders={sortedTopics}
              notesByFolder={notesByTopic}
              selectedNote={selectedNote}
              onNoteSelect={handleNoteSelect}
            />
          ) : (
            <div className="space-y-2">
              {sortedNotes.map((note) => (
                <motion.button
                  key={note.path}
                  whileHover={{ x: 4 }}
                  onClick={() => handleNoteSelect(note.path)}
                  className={clsx(
                    'w-full text-left p-3 rounded-lg transition-colors',
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
