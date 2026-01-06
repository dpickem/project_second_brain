/**
 * Vault Page
 * 
 * Browse and view notes in the Obsidian vault.
 */

import { useState, useCallback, useMemo, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useSearchParams } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import rehypeHighlight from 'rehype-highlight'
import 'highlight.js/styles/github-dark.css'
import { fetchNotes, fetchNoteContent, fetchFolders, fetchVaultStatus } from '../api/vault'

// Content type icons
const TYPE_ICONS = {
  paper: '📄',
  article: '📰',
  book: '📚',
  code: '💻',
  idea: '💡',
  voice_memo: '🎙️',
  note: '📝',
}

// Format file size
function formatSize(bytes) {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

// Format date
function formatDate(dateStr) {
  const date = new Date(dateStr)
  const now = new Date()
  const diff = now - date
  
  if (diff < 60000) return 'Just now'
  if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`
  if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`
  if (diff < 604800000) return `${Math.floor(diff / 86400000)}d ago`
  
  return date.toLocaleDateString()
}

// Sidebar with folders
function Sidebar({ folders, selectedFolder, onSelectFolder, status }) {
  return (
    <aside className="w-64 bg-slate-900 border-r border-slate-800 flex flex-col h-full">
      {/* Status */}
      <div className="p-4 border-b border-slate-800">
        <div className="flex items-center gap-2">
          <div className={`w-2 h-2 rounded-full ${status?.status === 'healthy' ? 'bg-emerald-400' : 'bg-amber-400'}`} />
          <span className="text-sm text-slate-400">
            {status?.total_files || 0} files
          </span>
        </div>
      </div>

      {/* Folders */}
      <nav className="flex-1 overflow-y-auto p-2">
        <button
          onClick={() => onSelectFolder(null)}
          className={`w-full text-left px-3 py-2 rounded-lg text-sm transition-colors ${
            selectedFolder === null
              ? 'bg-indigo-600/20 text-indigo-300'
              : 'text-slate-400 hover:text-white hover:bg-slate-800'
          }`}
        >
          📁 All Notes
        </button>
        
        {folders?.folders?.map((folder) => (
          <button
            key={folder.folder}
            onClick={() => onSelectFolder(folder.folder)}
            className={`w-full text-left px-3 py-2 rounded-lg text-sm transition-colors ${
              selectedFolder === folder.folder
                ? 'bg-indigo-600/20 text-indigo-300'
                : 'text-slate-400 hover:text-white hover:bg-slate-800'
            }`}
          >
            {folder.icon} {folder.folder}
          </button>
        ))}
      </nav>
    </aside>
  )
}

// Note list item
function NoteItem({ note, isSelected, onClick }) {
  return (
    <motion.button
      layout
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      onClick={onClick}
      className={`w-full text-left p-4 border-b border-slate-800/50 transition-colors ${
        isSelected ? 'bg-slate-800/80' : 'hover:bg-slate-800/50'
      }`}
    >
      <div className="flex items-start gap-3">
        <span className="text-xl mt-0.5">
          {TYPE_ICONS[note.content_type] || '📝'}
        </span>
        <div className="flex-1 min-w-0">
          <h3 className="text-white font-medium truncate">
            {note.title || note.name}
          </h3>
          <p className="text-sm text-slate-500 truncate">{note.folder || '/'}</p>
          <div className="flex items-center gap-3 mt-2 text-xs text-slate-500">
            <span>{formatDate(note.modified)}</span>
            <span>{formatSize(note.size)}</span>
          </div>
          {note.tags?.length > 0 && (
            <div className="flex flex-wrap gap-1 mt-2">
              {note.tags.slice(0, 3).map((tag) => (
                <span
                  key={tag}
                  className="px-1.5 py-0.5 text-xs bg-slate-700 text-slate-300 rounded"
                >
                  {tag}
                </span>
              ))}
              {note.tags.length > 3 && (
                <span className="text-xs text-slate-500">+{note.tags.length - 3}</span>
              )}
            </div>
          )}
        </div>
      </div>
    </motion.button>
  )
}

// Note viewer
function NoteViewer({ notePath, onClose }) {
  const { data: note, isLoading, error } = useQuery({
    queryKey: ['note', notePath],
    queryFn: () => fetchNoteContent(notePath),
    enabled: !!notePath,
  })

  if (!notePath) {
    return (
      <div className="flex-1 flex items-center justify-center text-slate-500">
        <div className="text-center">
          <span className="text-6xl mb-4 block">📖</span>
          <p>Select a note to view</p>
        </div>
      </div>
    )
  }

  if (isLoading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="animate-spin w-8 h-8 border-2 border-indigo-500 border-t-transparent rounded-full" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex-1 flex items-center justify-center text-red-400">
        <div className="text-center">
          <span className="text-4xl mb-2 block">⚠️</span>
          <p>Failed to load note</p>
          <p className="text-sm text-slate-500 mt-1">{error.message}</p>
        </div>
      </div>
    )
  }

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      {/* Header */}
      <header className="p-4 border-b border-slate-800 flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold text-white">
            {note.frontmatter?.title || note.name}
          </h2>
          <p className="text-sm text-slate-500 mt-1">{note.path}</p>
        </div>
        <button
          onClick={onClose}
          className="p-2 text-slate-400 hover:text-white hover:bg-slate-800 rounded-lg transition-colors"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </header>

      {/* Frontmatter badges */}
      {Object.keys(note.frontmatter || {}).length > 0 && (
        <div className="px-4 py-2 border-b border-slate-800/50 flex flex-wrap gap-2">
          {note.frontmatter.type && (
            <span className="px-2 py-1 text-xs bg-indigo-600/20 text-indigo-300 rounded">
              {TYPE_ICONS[note.frontmatter.type]} {note.frontmatter.type}
            </span>
          )}
          {note.frontmatter.tags?.map((tag) => (
            <span key={tag} className="px-2 py-1 text-xs bg-slate-700 text-slate-300 rounded">
              #{tag}
            </span>
          ))}
        </div>
      )}

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6">
        <article className="prose prose-invert max-w-none">
          <MarkdownContent content={note.content} />
        </article>
      </div>
    </div>
  )
}

// Markdown renderer component
function MarkdownContent({ content }) {
  // Strip frontmatter from content before rendering
  const cleanContent = useMemo(() => {
    if (!content) return ''
    // Remove YAML frontmatter (--- ... ---)
    const frontmatterRegex = /^---\n[\s\S]*?\n---\n?/
    return content.replace(frontmatterRegex, '').trim()
  }, [content])

  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      rehypePlugins={[rehypeHighlight]}
    >
      {cleanContent}
    </ReactMarkdown>
  )
}

// Search bar
function SearchBar({ value, onChange }) {
  return (
    <div className="relative">
      <svg
        className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
        />
      </svg>
      <input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder="Search notes..."
        className="w-full pl-10 pr-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white placeholder-slate-500 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
      />
    </div>
  )
}

// Main page component
export default function VaultPage() {
  const [searchParams] = useSearchParams()
  const [selectedFolder, setSelectedFolder] = useState(null)
  const [selectedNote, setSelectedNote] = useState(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [page, setPage] = useState(1)

  // Initialize from URL params
  useEffect(() => {
    const urlSearch = searchParams.get('search')
    const urlNote = searchParams.get('note')
    
    if (urlNote) {
      // Direct note path - open this note
      setSelectedNote(urlNote)
      // Set folder to parent folder if path contains /
      const lastSlash = urlNote.lastIndexOf('/')
      if (lastSlash > 0) {
        setSelectedFolder(urlNote.substring(0, lastSlash))
      }
    } else if (urlSearch) {
      setSearchQuery(urlSearch)
    }
  }, [searchParams])

  // Fetch vault status
  const { data: status } = useQuery({
    queryKey: ['vault-status'],
    queryFn: fetchVaultStatus,
  })

  // Fetch folders
  const { data: folders } = useQuery({
    queryKey: ['vault-folders'],
    queryFn: fetchFolders,
  })

  // Fetch notes
  const { data: notesData, isLoading, error } = useQuery({
    queryKey: ['vault-notes', selectedFolder, searchQuery, page],
    queryFn: () => fetchNotes({
      folder: selectedFolder,
      search: searchQuery || undefined,
      page,
      pageSize: 50,
    }),
  })

  const handleSelectFolder = useCallback((folder) => {
    setSelectedFolder(folder)
    setSelectedNote(null)
    setPage(1)
  }, [])

  const handleSearch = useCallback((query) => {
    setSearchQuery(query)
    setPage(1)
  }, [])

  return (
    <div className="h-screen flex bg-slate-950">
      {/* Sidebar */}
      <Sidebar
        folders={folders}
        selectedFolder={selectedFolder}
        onSelectFolder={handleSelectFolder}
        status={status}
      />

      {/* Main content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Header */}
        <header className="p-4 border-b border-slate-800 flex items-center gap-4">
          <div className="flex-1 max-w-md">
            <SearchBar value={searchQuery} onChange={handleSearch} />
          </div>
          <div className="text-sm text-slate-500">
            {notesData?.total || 0} notes
          </div>
        </header>

        {/* Content area */}
        <div className="flex-1 flex overflow-hidden">
          {/* Notes list */}
          <div className="w-96 border-r border-slate-800 overflow-y-auto">
            {isLoading ? (
              <div className="flex items-center justify-center h-32">
                <div className="animate-spin w-6 h-6 border-2 border-indigo-500 border-t-transparent rounded-full" />
              </div>
            ) : error ? (
              <div className="p-4 text-red-400 text-center">
                <p>Failed to load notes</p>
                <p className="text-sm text-slate-500 mt-1">{error.message}</p>
              </div>
            ) : notesData?.notes?.length === 0 ? (
              <div className="p-8 text-center text-slate-500">
                <span className="text-4xl mb-2 block">📭</span>
                <p>No notes found</p>
              </div>
            ) : (
              <>
                <AnimatePresence>
                  {notesData?.notes?.map((note) => (
                    <NoteItem
                      key={note.path}
                      note={note}
                      isSelected={selectedNote === note.path}
                      onClick={() => setSelectedNote(note.path)}
                    />
                  ))}
                </AnimatePresence>
                
                {/* Pagination */}
                {notesData?.has_more && (
                  <div className="p-4 flex justify-center">
                    <button
                      onClick={() => setPage((p) => p + 1)}
                      className="px-4 py-2 text-sm text-indigo-400 hover:text-indigo-300 transition-colors"
                    >
                      Load more...
                    </button>
                  </div>
                )}
              </>
            )}
          </div>

          {/* Note viewer */}
          <NoteViewer
            notePath={selectedNote}
            onClose={() => setSelectedNote(null)}
          />
        </div>
      </div>
    </div>
  )
}

