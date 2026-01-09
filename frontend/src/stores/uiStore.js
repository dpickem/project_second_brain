/**
 * UI Store
 * 
 * Zustand store for transient UI state (modals, command palette, etc.)
 */

import { create } from 'zustand'

export const useUiStore = create((set, get) => ({
  // =====================
  // State
  // =====================
  
  // Modal state
  activeModal: null, // 'capture' | 'settings' | 'confirm' | 'noteViewer' | null
  modalProps: {},
  
  // Command palette
  commandPaletteOpen: false,
  
  // Sidebar/navigation
  mobileMenuOpen: false,
  
  // Note viewer panel
  noteViewerOpen: false,
  selectedNoteId: null,
  
  // Global loading state
  globalLoading: false,
  globalLoadingMessage: '',
  
  // Toast/notification queue (managed by react-hot-toast, this is for programmatic control)
  pendingToasts: [],
  
  // Search state
  globalSearchQuery: '',
  searchFocused: false,
  
  // =====================
  // Modal Actions
  // =====================
  
  openModal: (modal, props = {}) => set({
    activeModal: modal,
    modalProps: props,
  }),
  
  closeModal: () => set({
    activeModal: null,
    modalProps: {},
  }),
  
  updateModalProps: (props) => set((state) => ({
    modalProps: { ...state.modalProps, ...props },
  })),
  
  // =====================
  // Command Palette Actions
  // =====================
  
  toggleCommandPalette: () => set((state) => ({
    commandPaletteOpen: !state.commandPaletteOpen,
  })),
  
  openCommandPalette: () => set({ commandPaletteOpen: true }),
  
  closeCommandPalette: () => set({ commandPaletteOpen: false }),
  
  // =====================
  // Mobile Menu Actions
  // =====================
  
  toggleMobileMenu: () => set((state) => ({
    mobileMenuOpen: !state.mobileMenuOpen,
  })),
  
  closeMobileMenu: () => set({ mobileMenuOpen: false }),
  
  // =====================
  // Note Viewer Actions
  // =====================
  
  openNoteViewer: (noteId) => set({
    noteViewerOpen: true,
    selectedNoteId: noteId,
  }),
  
  closeNoteViewer: () => set({
    noteViewerOpen: false,
    selectedNoteId: null,
  }),
  
  setSelectedNote: (noteId) => set({ selectedNoteId: noteId }),
  
  // =====================
  // Loading Actions
  // =====================
  
  setGlobalLoading: (loading, message = '') => set({
    globalLoading: loading,
    globalLoadingMessage: message,
  }),
  
  // =====================
  // Search Actions
  // =====================
  
  setGlobalSearchQuery: (query) => set({ globalSearchQuery: query }),
  
  setSearchFocused: (focused) => set({ searchFocused: focused }),
  
  clearSearch: () => set({
    globalSearchQuery: '',
    searchFocused: false,
  }),
  
  // =====================
  // Toast Actions
  // =====================
  
  queueToast: (toast) => set((state) => ({
    pendingToasts: [...state.pendingToasts, toast],
  })),
  
  dequeueToast: () => set((state) => ({
    pendingToasts: state.pendingToasts.slice(1),
  })),
  
  clearToasts: () => set({ pendingToasts: [] }),
  
  // =====================
  // Selectors
  // =====================
  
  isModalOpen: (modalName) => get().activeModal === modalName,
  
  hasOpenOverlay: () => {
    const state = get()
    return state.activeModal !== null || 
           state.commandPaletteOpen || 
           state.mobileMenuOpen ||
           state.noteViewerOpen
  },
  
  // =====================
  // Bulk Actions
  // =====================
  
  closeAllOverlays: () => set({
    activeModal: null,
    modalProps: {},
    commandPaletteOpen: false,
    mobileMenuOpen: false,
    noteViewerOpen: false,
    selectedNoteId: null,
  }),
}))

export default useUiStore
