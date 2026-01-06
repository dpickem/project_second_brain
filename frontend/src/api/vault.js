/**
 * Vault API client
 * 
 * Functions for interacting with the vault browsing API.
 */

import axios from 'axios'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

/**
 * Get vault status and statistics
 */
export async function fetchVaultStatus() {
  const response = await axios.get(`${API_URL}/api/vault/status`)
  return response.data
}

/**
 * List notes in the vault with filtering and pagination
 * 
 * @param {Object} options - Query options
 * @param {string} options.folder - Filter by folder path
 * @param {string} options.search - Search in file names
 * @param {string} options.tag - Filter by tag
 * @param {string} options.contentType - Filter by content type
 * @param {number} options.page - Page number (default: 1)
 * @param {number} options.pageSize - Notes per page (default: 50)
 * @param {string} options.sortBy - Sort by: modified, name, size
 * @param {boolean} options.sortDesc - Sort descending
 */
export async function fetchNotes({
  folder,
  search,
  tag,
  contentType,
  page = 1,
  pageSize = 50,
  sortBy = 'modified',
  sortDesc = true,
} = {}) {
  const params = new URLSearchParams()
  
  if (folder) params.set('folder', folder)
  if (search) params.set('search', search)
  if (tag) params.set('tag', tag)
  if (contentType) params.set('content_type', contentType)
  params.set('page', page)
  params.set('page_size', pageSize)
  params.set('sort_by', sortBy)
  params.set('sort_desc', sortDesc)
  
  const response = await axios.get(`${API_URL}/api/vault/notes?${params}`)
  return response.data
}

/**
 * Get the full content of a specific note
 * 
 * @param {string} notePath - Relative path to the note from vault root
 */
export async function fetchNoteContent(notePath) {
  // Don't encode slashes in path - the backend expects the full path
  const response = await axios.get(`${API_URL}/api/vault/notes/${notePath}`)
  return response.data
}

/**
 * List content type folders in the vault
 */
export async function fetchFolders() {
  const response = await axios.get(`${API_URL}/api/vault/folders`)
  return response.data
}

/**
 * Trigger full vault sync to Neo4j
 */
export async function syncVault() {
  const response = await axios.post(`${API_URL}/api/vault/sync`)
  return response.data
}

/**
 * Get vault sync status
 */
export async function fetchSyncStatus() {
  const response = await axios.get(`${API_URL}/api/vault/sync/status`)
  return response.data
}

