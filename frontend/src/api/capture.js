/**
 * Capture API Client
 * 
 * Functions for quick capture of content into the knowledge system.
 * This is the primary entry point for adding new content to be processed.
 * 
 * ## Use Cases
 * - **Text Capture**: Quick notes, ideas, quotes, or any text content
 * - **URL Capture**: Articles, blog posts, and web pages for extraction and processing
 * - **File Upload**: PDFs, images, audio files for OCR/transcription and processing
 * - **Capture History**: View and track all captured content and processing status
 * 
 * ## Processing Pipeline
 * Captured content flows through the following stages:
 * 
 * ```
 * Capture → Queue → LLM Processing → Obsidian Note → Neo4j Sync
 *    ↓
 * Status: pending → processing → completed/failed
 * ```
 * 
 * ## Supported File Types
 * - Documents: PDF, DOCX, TXT, MD
 * - Images: PNG, JPG, HEIC (OCR extraction)
 * - Audio: M4A, MP3, WAV (transcription)
 * 
 * ## Related APIs
 * - After processing, content appears in `vaultApi` as notes
 * - Processed content is synced to `knowledgeApi` graph
 * - Learning cards may be generated and accessible via `reviewApi`
 * 
 * @see vaultApi - To browse processed notes
 * @see knowledgeApi - To explore knowledge graph connections
 */

import { typedApi } from './typed-client'

export const captureApi = {
  /**
   * Capture text content for processing and storage
   * @param {Object} data - Capture data
   * @param {string} data.text - Text content to capture
   * @param {string[]} [data.tags] - Optional tags to associate with the capture
   * @param {string} [data.contentType] - Content type hint (e.g., 'note', 'idea', 'quote')
   * @returns {Promise<{id: string, status: 'pending'|'processing'|'completed', created_at: string, content_type: string}>} Capture confirmation with processing status
   */
  captureText: ({ text, tags, contentType }) => 
    typedApi.POST('/api/capture/text', { 
      body: { 
        content: text,  // Backend expects 'content' not 'text'
        tags, 
        content_type: contentType 
      }
    }).then(r => r.data),

  /**
   * Capture a URL for content extraction and processing
   * @param {Object} data - Capture data
   * @param {string} data.url - URL to capture and process
   * @param {string[]} [data.tags] - Optional tags to associate with the capture
   * @returns {Promise<{id: string, url: string, status: 'pending'|'processing'|'completed', title?: string, created_at: string}>} Capture confirmation with extracted metadata
   */
  captureUrl: ({ url, tags }) => 
    typedApi.POST('/api/capture/url', { 
      body: { url, tags } 
    }).then(r => r.data),

  /**
   * Upload and capture a file for processing
   * Note: File uploads require FormData and cannot use the typed client directly.
   * This method falls back to using fetch with FormData.
   * @param {File} file - File object to upload (PDF, image, audio, etc.)
   * @param {Object} [options] - Upload options
   * @param {string[]} [options.tags] - Optional tags to associate with the file
   * @param {string} [options.contentType] - Content type hint for processing
   * @returns {Promise<{id: string, filename: string, size_bytes: number, status: 'pending'|'processing'|'completed', mime_type: string, created_at: string}>} Upload confirmation with file metadata
   */
  captureFile: async (file, options = {}) => {
    const formData = new FormData()
    formData.append('file', file)
    if (options.tags) formData.append('tags', JSON.stringify(options.tags))
    if (options.contentType) formData.append('content_type', options.contentType)
    
    const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'
    const response = await fetch(`${API_URL}/api/capture/file`, {
      method: 'POST',
      body: formData,
    })
    if (!response.ok) {
      throw new Error(`Upload failed: ${response.statusText}`)
    }
    return response.json()
  },

  /**
   * Get paginated capture history with optional filtering
   * @param {Object} [options] - Query options
   * @param {number} [options.limit] - Maximum number of items to return
   * @param {number} [options.offset] - Number of items to skip for pagination
   * @param {string} [options.status] - Filter by status ('pending', 'processing', 'completed', 'failed')
   * @param {string} [options.type] - Filter by capture type ('text', 'url', 'file')
   * @returns {Promise<{captures: Array<{id: string, type: string, status: string, created_at: string, title?: string}>, total: number}>} Paginated capture history
   */
  getHistory: (options = {}) => 
    typedApi.GET('/api/capture/history', { 
      params: { query: options } 
    }).then(r => r.data),

  /**
   * Get most recent captures for quick access
   * @param {number} [limit=10] - Maximum number of recent captures to return
   * @returns {Promise<{captures: Array<{id: string, type: string, title?: string, status: string, created_at: string}>}>} List of recent captures
   */
  getRecent: (limit = 10) => 
    typedApi.GET('/api/capture/recent', { 
      params: { query: { limit } } 
    }).then(r => r.data),
}

export default captureApi
