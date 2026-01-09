/**
 * UI Store Tests
 */

import { describe, it, expect, beforeEach } from 'vitest'
import { useUiStore } from './uiStore'

describe('uiStore', () => {
  beforeEach(() => {
    // Reset store to initial state
    useUiStore.setState({
      activeModal: null,
      modalProps: {},
      commandPaletteOpen: false,
      mobileMenuOpen: false,
      noteViewerOpen: false,
      selectedNoteId: null,
      globalLoading: false,
      globalLoadingMessage: '',
      pendingToasts: [],
      globalSearchQuery: '',
      searchFocused: false,
    })
  })

  describe('Modal Actions', () => {
    it('should open modal with props', () => {
      useUiStore.getState().openModal('capture', { title: 'Test' })
      
      const state = useUiStore.getState()
      expect(state.activeModal).toBe('capture')
      expect(state.modalProps).toEqual({ title: 'Test' })
    })

    it('should close modal and clear props', () => {
      useUiStore.setState({ activeModal: 'capture', modalProps: { title: 'Test' } })
      
      useUiStore.getState().closeModal()
      
      const state = useUiStore.getState()
      expect(state.activeModal).toBeNull()
      expect(state.modalProps).toEqual({})
    })

    it('should update modal props', () => {
      useUiStore.setState({ modalProps: { title: 'Test' } })
      
      useUiStore.getState().updateModalProps({ subtitle: 'Updated' })
      
      expect(useUiStore.getState().modalProps).toEqual({ title: 'Test', subtitle: 'Updated' })
    })
  })

  describe('Command Palette Actions', () => {
    it('should open command palette', () => {
      useUiStore.getState().openCommandPalette()
      
      expect(useUiStore.getState().commandPaletteOpen).toBe(true)
    })

    it('should close command palette', () => {
      useUiStore.setState({ commandPaletteOpen: true })
      
      useUiStore.getState().closeCommandPalette()
      
      expect(useUiStore.getState().commandPaletteOpen).toBe(false)
    })

    it('should toggle command palette', () => {
      const initial = useUiStore.getState().commandPaletteOpen
      
      useUiStore.getState().toggleCommandPalette()
      
      expect(useUiStore.getState().commandPaletteOpen).toBe(!initial)
    })
  })

  describe('Mobile Menu Actions', () => {
    it('should toggle mobile menu', () => {
      const initial = useUiStore.getState().mobileMenuOpen
      
      useUiStore.getState().toggleMobileMenu()
      
      expect(useUiStore.getState().mobileMenuOpen).toBe(!initial)
    })

    it('should close mobile menu', () => {
      useUiStore.setState({ mobileMenuOpen: true })
      
      useUiStore.getState().closeMobileMenu()
      
      expect(useUiStore.getState().mobileMenuOpen).toBe(false)
    })
  })

  describe('Note Viewer Actions', () => {
    it('should open note viewer with note id', () => {
      useUiStore.getState().openNoteViewer('note-123')
      
      const state = useUiStore.getState()
      expect(state.noteViewerOpen).toBe(true)
      expect(state.selectedNoteId).toBe('note-123')
    })

    it('should close note viewer and clear selection', () => {
      useUiStore.setState({ noteViewerOpen: true, selectedNoteId: 'note-123' })
      
      useUiStore.getState().closeNoteViewer()
      
      const state = useUiStore.getState()
      expect(state.noteViewerOpen).toBe(false)
      expect(state.selectedNoteId).toBeNull()
    })

    it('should set selected note', () => {
      useUiStore.getState().setSelectedNote('note-456')
      
      expect(useUiStore.getState().selectedNoteId).toBe('note-456')
    })
  })

  describe('Loading Actions', () => {
    it('should set global loading with message', () => {
      useUiStore.getState().setGlobalLoading(true, 'Loading...')
      
      const state = useUiStore.getState()
      expect(state.globalLoading).toBe(true)
      expect(state.globalLoadingMessage).toBe('Loading...')
    })

    it('should clear global loading', () => {
      useUiStore.setState({ globalLoading: true, globalLoadingMessage: 'Loading...' })
      
      useUiStore.getState().setGlobalLoading(false)
      
      const state = useUiStore.getState()
      expect(state.globalLoading).toBe(false)
      expect(state.globalLoadingMessage).toBe('')
    })
  })

  describe('Search Actions', () => {
    it('should set global search query', () => {
      useUiStore.getState().setGlobalSearchQuery('test query')
      
      expect(useUiStore.getState().globalSearchQuery).toBe('test query')
    })

    it('should set search focused', () => {
      useUiStore.getState().setSearchFocused(true)
      
      expect(useUiStore.getState().searchFocused).toBe(true)
    })

    it('should clear search', () => {
      useUiStore.setState({ globalSearchQuery: 'test', searchFocused: true })
      
      useUiStore.getState().clearSearch()
      
      const state = useUiStore.getState()
      expect(state.globalSearchQuery).toBe('')
      expect(state.searchFocused).toBe(false)
    })
  })

  describe('Toast Actions', () => {
    it('should queue toast', () => {
      useUiStore.getState().queueToast({ message: 'Test', type: 'success' })
      
      expect(useUiStore.getState().pendingToasts).toHaveLength(1)
      expect(useUiStore.getState().pendingToasts[0]).toEqual({ message: 'Test', type: 'success' })
    })

    it('should dequeue toast', () => {
      useUiStore.setState({ pendingToasts: [{ message: 'First' }, { message: 'Second' }] })
      
      useUiStore.getState().dequeueToast()
      
      expect(useUiStore.getState().pendingToasts).toHaveLength(1)
      expect(useUiStore.getState().pendingToasts[0]).toEqual({ message: 'Second' })
    })

    it('should clear all toasts', () => {
      useUiStore.setState({ pendingToasts: [{ message: 'First' }, { message: 'Second' }] })
      
      useUiStore.getState().clearToasts()
      
      expect(useUiStore.getState().pendingToasts).toHaveLength(0)
    })
  })

  describe('Selectors', () => {
    it('should check if modal is open', () => {
      useUiStore.setState({ activeModal: 'capture' })
      
      expect(useUiStore.getState().isModalOpen('capture')).toBe(true)
      expect(useUiStore.getState().isModalOpen('settings')).toBe(false)
    })

    it('should check if any overlay is open', () => {
      expect(useUiStore.getState().hasOpenOverlay()).toBe(false)
      
      useUiStore.setState({ activeModal: 'capture' })
      expect(useUiStore.getState().hasOpenOverlay()).toBe(true)
      
      useUiStore.setState({ activeModal: null, commandPaletteOpen: true })
      expect(useUiStore.getState().hasOpenOverlay()).toBe(true)
    })
  })

  describe('Bulk Actions', () => {
    it('should close all overlays', () => {
      useUiStore.setState({
        activeModal: 'capture',
        modalProps: { title: 'Test' },
        commandPaletteOpen: true,
        mobileMenuOpen: true,
        noteViewerOpen: true,
        selectedNoteId: 'note-123',
      })
      
      useUiStore.getState().closeAllOverlays()
      
      const state = useUiStore.getState()
      expect(state.activeModal).toBeNull()
      expect(state.modalProps).toEqual({})
      expect(state.commandPaletteOpen).toBe(false)
      expect(state.mobileMenuOpen).toBe(false)
      expect(state.noteViewerOpen).toBe(false)
      expect(state.selectedNoteId).toBeNull()
    })
  })
})
