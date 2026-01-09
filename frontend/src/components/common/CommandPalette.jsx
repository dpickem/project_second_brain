/**
 * CommandPalette Component
 * 
 * Global command palette (⌘K) for search and quick actions.
 */

import { useState, useEffect, useCallback, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { Command } from 'cmdk'
import { motion, AnimatePresence } from 'framer-motion'
import { useQuery } from '@tanstack/react-query'
import { clsx } from 'clsx'
import { useUiStore, useSettingsStore } from '../../stores'
import { vaultApi } from '../../api/vault'
import { useDebounce } from '../../hooks/useDebouncedSearch'

// Icons
const icons = {
  search: (
    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
    </svg>
  ),
  home: (
    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
    </svg>
  ),
  practice: (
    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
  ),
  review: (
    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
    </svg>
  ),
  graph: (
    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <circle cx="5" cy="6" r="2" strokeWidth={2} />
      <circle cx="12" cy="4" r="2" strokeWidth={2} />
      <circle cx="19" cy="8" r="2" strokeWidth={2} />
      <circle cx="12" cy="12" r="2.5" strokeWidth={2} />
    </svg>
  ),
  analytics: (
    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
    </svg>
  ),
  vault: (
    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 8h14M5 8a2 2 0 110-4h14a2 2 0 110 4M5 8v10a2 2 0 002 2h10a2 2 0 002-2V8m-9 4h4" />
    </svg>
  ),
  settings: (
    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
    </svg>
  ),
  note: (
    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
    </svg>
  ),
  capture: (
    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
    </svg>
  ),
}

export function CommandPalette() {
  const navigate = useNavigate()
  const [search, setSearch] = useState('')
  const inputRef = useRef(null)
  const { commandPaletteOpen, closeCommandPalette, openModal } = useUiStore()
  const keyboardShortcutsEnabled = useSettingsStore((s) => s.keyboardShortcutsEnabled)

  // Debounce the search to avoid too many API calls
  const debouncedSearch = useDebounce(search, 200)

  // Reset search when closing the palette
  useEffect(() => {
    if (!commandPaletteOpen) {
      setSearch('')
    }
  }, [commandPaletteOpen])

  // Auto-focus input when palette opens
  useEffect(() => {
    if (commandPaletteOpen && inputRef.current) {
      // Small delay to ensure the DOM is ready
      setTimeout(() => {
        inputRef.current?.focus()
      }, 50)
    }
  }, [commandPaletteOpen])

  // Search notes when typing
  const { data: searchResults, isLoading } = useQuery({
    queryKey: ['command-search', debouncedSearch],
    queryFn: () => vaultApi.search(debouncedSearch, { limit: 5 }),
    enabled: debouncedSearch.length > 2,
    staleTime: 10 * 1000, // Shorter stale time for fresher results
  })

  // Keyboard shortcut to open
  useEffect(() => {
    if (!keyboardShortcutsEnabled) return

    const handleKeyDown = (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault()
        if (commandPaletteOpen) {
          closeCommandPalette()
        } else {
          useUiStore.getState().openCommandPalette()
        }
      }
      // Escape to close
      if (e.key === 'Escape' && commandPaletteOpen) {
        closeCommandPalette()
      }
    }

    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [commandPaletteOpen, closeCommandPalette, keyboardShortcutsEnabled])

  const runCommand = useCallback((command) => {
    closeCommandPalette()
    command()
  }, [closeCommandPalette])

  const navigateTo = useCallback((path) => {
    runCommand(() => navigate(path))
  }, [navigate, runCommand])

  return (
    <AnimatePresence>
      {commandPaletteOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={closeCommandPalette}
            className="fixed inset-0 bg-black/60 backdrop-blur-sm z-command"
          />

          {/* Command Dialog */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: -20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: -20 }}
            transition={{ duration: 0.15 }}
            className="fixed inset-x-4 top-[15vh] mx-auto max-w-xl z-command"
          >
            <Command
              className={clsx(
                'rounded-2xl overflow-hidden',
                'bg-bg-elevated border border-border-primary shadow-2xl'
              )}
              loop
            >
              {/* Input */}
              <div className="flex items-center gap-3 px-4 border-b border-border-primary">
                <span className="text-text-muted">{icons.search}</span>
                <Command.Input
                  ref={inputRef}
                  value={search}
                  onValueChange={setSearch}
                  placeholder="Search notes, type a command..."
                  autoFocus
                  className={clsx(
                    'flex-1 py-4 bg-transparent text-text-primary placeholder-text-muted',
                    'text-base focus:outline-none'
                  )}
                />
                <kbd className="px-2 py-1 text-xs bg-slate-700 text-slate-400 rounded">
                  ESC
                </kbd>
              </div>

              {/* Results */}
              <Command.List className="max-h-[50vh] overflow-y-auto p-2">
                <Command.Empty className="py-8 text-center text-text-muted">
                  {isLoading ? 'Searching...' : 'No results found.'}
                </Command.Empty>

                {/* Search Results */}
                {searchResults?.results?.length > 0 && (
                  <Command.Group heading="Notes">
                    {searchResults.results.map((note) => (
                      <CommandItem
                        key={note.path}
                        icon={icons.note}
                        onSelect={() => navigateTo(`/knowledge?note=${encodeURIComponent(note.path)}`)}
                      >
                        <span>{note.title || note.path}</span>
                        {note.folder && (
                          <span className="ml-2 text-xs text-text-muted">{note.folder}</span>
                        )}
                      </CommandItem>
                    ))}
                  </Command.Group>
                )}

                {/* Pages */}
                <Command.Group heading="Pages">
                  <CommandItem icon={icons.home} onSelect={() => navigateTo('/')}>
                    Dashboard
                  </CommandItem>
                  <CommandItem icon={icons.practice} onSelect={() => navigateTo('/practice')}>
                    Practice Session
                  </CommandItem>
                  <CommandItem icon={icons.review} onSelect={() => navigateTo('/review')}>
                    Review Queue
                  </CommandItem>
                  <CommandItem icon={icons.graph} onSelect={() => navigateTo('/knowledge')}>
                    Knowledge Graph
                  </CommandItem>
                  <CommandItem icon={icons.analytics} onSelect={() => navigateTo('/analytics')}>
                    Analytics
                  </CommandItem>
                  <CommandItem icon={icons.vault} onSelect={() => navigateTo('/knowledge')}>
                    Knowledge
                  </CommandItem>
                  <CommandItem icon={icons.settings} onSelect={() => navigateTo('/settings')}>
                    Settings
                  </CommandItem>
                </Command.Group>

                {/* Actions */}
                <Command.Group heading="Actions">
                  <CommandItem
                    icon={icons.capture}
                    onSelect={() => runCommand(() => openModal('capture'))}
                  >
                    Quick Capture
                    <span className="ml-auto text-xs text-text-muted">⌘N</span>
                  </CommandItem>
                  <CommandItem
                    icon={icons.practice}
                    onSelect={() => navigateTo('/practice')}
                  >
                    Start Practice Session
                    <span className="ml-auto text-xs text-text-muted">⌘P</span>
                  </CommandItem>
                </Command.Group>
              </Command.List>

              {/* Footer */}
              <div className="flex items-center justify-between px-4 py-2 border-t border-border-primary text-xs text-text-muted">
                <div className="flex items-center gap-4">
                  <span className="flex items-center gap-1">
                    <kbd className="px-1.5 py-0.5 bg-slate-700 rounded">↑↓</kbd>
                    navigate
                  </span>
                  <span className="flex items-center gap-1">
                    <kbd className="px-1.5 py-0.5 bg-slate-700 rounded">↵</kbd>
                    select
                  </span>
                </div>
                <span className="flex items-center gap-1">
                  <kbd className="px-1.5 py-0.5 bg-slate-700 rounded">⌘K</kbd>
                  to toggle
                </span>
              </div>
            </Command>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  )
}

function CommandItem({ icon, onSelect, children }) {
  return (
    <Command.Item
      onSelect={onSelect}
      className={clsx(
        'flex items-center gap-3 px-3 py-2.5 rounded-lg cursor-pointer',
        'text-text-secondary data-[selected=true]:bg-accent-primary data-[selected=true]:text-white',
        'transition-colors'
      )}
    >
      <span className="text-text-muted data-[selected=true]:text-white/70">
        {icon}
      </span>
      <span className="flex-1 flex items-center">{children}</span>
    </Command.Item>
  )
}

export default CommandPalette
