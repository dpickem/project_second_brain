/**
 * Vault API Client
 * 
 * Functions for interacting with the Obsidian vault file system.
 * Provides direct access to markdown notes, folders, tags, and sync operations.
 * 
 * ## Use Cases
 * - **Note Browsing**: List and search notes with filtering by folder, tag, or content type
 * - **Note Content**: Fetch full markdown content with parsed frontmatter
 * - **Folder Navigation**: Browse the vault's folder structure
 * - **Tag Management**: Access all tags with usage counts
 * - **Vault Sync**: Trigger and monitor sync operations to Neo4j
 * 
 * ## When to Use This vs knowledgeApi
 * Use `vaultApi` when you need:
 * - Direct file access to markdown notes
 * - Note content for reading or display
 * - Folder structure and file metadata
 * - File-level search (by name, path, frontmatter)
 * - Vault sync operations
 * 
 * Use `knowledgeApi` instead when you need:
 * - Graph-based queries (nodes, edges, relationships)
 * - Cross-note connections and link traversal
 * - Topic-level aggregations and statistics
 * - Mastery/learning progress data
 * - Graph visualization data
 * 
 * ## Data Flow
 * Notes in the Obsidian vault are synced to Neo4j via `/api/vault/sync`.
 * After sync, the knowledge graph reflects the vault's content and relationships.
 * 
 * @see knowledgeApi - For graph-based queries and relationship exploration
 */

import { apiClient } from './client'

export const vaultApi = {
  /**
   * Get vault status and statistics
   * @returns {Promise<{status: 'healthy'|'unhealthy', note_count: number, folder_count: number, last_sync?: string, vault_path: string}>} Vault health status and statistics
   */
  getStatus: () => 
    apiClient.get('/api/vault/status').then(r => r.data),

  /**
   * List notes in the vault with filtering and pagination
   * @param {Object} [options] - Query options
   * @param {string} [options.folder] - Filter by folder path
   * @param {string} [options.search] - Search query to filter notes by title/content
   * @param {string} [options.tag] - Filter by tag
   * @param {string} [options.contentType] - Filter by content type (e.g., 'article', 'book', 'concept')
   * @param {number} [options.page=1] - Page number for pagination (1-indexed)
   * @param {number} [options.pageSize=50] - Number of notes per page
   * @param {string} [options.sortBy='modified'] - Sort field ('modified', 'created', 'title')
   * @param {boolean} [options.sortDesc=true] - Sort in descending order
   * @returns {Promise<{notes: Array<{path: string, title: string, folder: string, content_type: string, modified: string, created: string, tags: Array<string>}>, total: number, page: number, page_size: number, has_more: boolean}>} Paginated note list
   */
  getNotes: ({
    folder,
    search,
    tag,
    contentType,
    page = 1,
    pageSize = 50,
    sortBy = 'modified',
    sortDesc = true,
  } = {}) => {
    const params = {
      page,
      page_size: pageSize,
      sort_by: sortBy,
      sort_desc: sortDesc,
    }
    if (folder) params.folder = folder
    if (search) params.search = search
    if (tag) params.tag = tag
    if (contentType) params.content_type = contentType
    
    return apiClient.get('/api/vault/notes', { params }).then(r => r.data)
  },

  /**
   * Get the full content of a specific note
   * @param {string} notePath - Relative path to the note from vault root (e.g., 'sources/articles/my-note.md')
   * @returns {Promise<{path: string, title: string, content: string, frontmatter: Object, modified: string, created: string, tags: Array<string>, links: Array<{target: string, display?: string}>}>} Full note content with metadata
   */
  getNoteContent: (notePath) => 
    apiClient.get(`/api/vault/notes/${notePath}`).then(r => r.data),

  /**
   * List content type folders in the vault
   * @returns {Promise<{folders: Array<{type: string, folder: string, exists: boolean, icon: string, note_count: number}>}>} List of vault folders with metadata
   */
  getFolders: () => 
    apiClient.get('/api/vault/folders').then(r => r.data),

  /**
   * Trigger full vault sync to Neo4j knowledge graph
   * @returns {Promise<{status: 'started'|'already_running', job_id?: string, message: string}>} Sync job status
   */
  syncVault: () => 
    apiClient.post('/api/vault/sync').then(r => r.data),

  /**
   * Get current vault sync status
   * @returns {Promise<{status: 'idle'|'running'|'completed'|'failed', last_sync?: string, notes_synced?: number, errors?: Array<string>, progress?: number}>} Current sync status
   */
  getSyncStatus: () => 
    apiClient.get('/api/vault/sync/status').then(r => r.data),

  /**
   * Search notes by query (convenience wrapper around getNotes)
   * @param {string} query - Search query string
   * @param {Object} [options] - Search options
   * @param {number} [options.limit=10] - Maximum number of results to return
   * @returns {Promise<{results: Array<{path: string, title: string, folder: string, content_type: string, tags: Array<string>}>, total: number}>} Search results
   */
  search: (query, options = {}) => {
    const { limit = 10, ...rest } = options
    return apiClient.get('/api/vault/notes', { 
      params: { 
        search: query,
        page_size: limit,
        ...rest 
      } 
    }).then(r => ({
      // Transform response to match expected format
      results: r.data.notes || [],
      total: r.data.total || 0,
    }))
  },

  /**
   * Get all tags in the vault with usage counts
   * @returns {Promise<{tags: Array<{name: string, count: number}>}>} Tags with occurrence counts
   */
  getTags: () => 
    apiClient.get('/api/vault/tags').then(r => r.data),
}

/**
 * Fetch vault status (legacy export)
 * @returns {Promise<{status: string, note_count: number, folder_count: number}>} Vault status
 */
export async function fetchVaultStatus() {
  return vaultApi.getStatus()
}

/**
 * Fetch notes with filtering (legacy export)
 * @param {Object} [options] - Query options (see vaultApi.getNotes)
 * @returns {Promise<{notes: Array, total: number}>} Paginated notes
 */
export async function fetchNotes(options) {
  return vaultApi.getNotes(options)
}

/**
 * Fetch note content by path (legacy export)
 * @param {string} notePath - Path to the note
 * @returns {Promise<{path: string, title: string, content: string, frontmatter: Object}>} Note content
 */
export async function fetchNoteContent(notePath) {
  return vaultApi.getNoteContent(notePath)
}

/**
 * Fetch vault folders (legacy export)
 * @returns {Promise<{folders: Array}>} Vault folders
 */
export async function fetchFolders() {
  return vaultApi.getFolders()
}

/**
 * Trigger vault sync (legacy export)
 * @returns {Promise<{status: string}>} Sync status
 */
export async function syncVault() {
  return vaultApi.syncVault()
}

/**
 * Fetch sync status (legacy export)
 * @returns {Promise<{status: string}>} Current sync status
 */
export async function fetchSyncStatus() {
  return vaultApi.getSyncStatus()
}

export default vaultApi