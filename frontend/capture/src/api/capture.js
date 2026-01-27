/**
 * Capture API Client with Offline Support
 * 
 * This module handles all capture API calls and provides offline support
 * through IndexedDB for queueing requests when offline.
 * 
 * Authentication:
 *   All requests include the X-API-Key header with VITE_CAPTURE_API_KEY.
 *   If no key is configured, requests are sent without authentication (dev mode).
 */

// Determine API URL - use same host as PWA but port 8000 for backend
function getApiUrl() {
  const envUrl = import.meta.env.VITE_API_URL;
  
  // If explicitly set and not localhost, use it
  if (envUrl && !envUrl.includes('localhost')) {
    return envUrl;
  }
  
  // If we're on localhost, use localhost
  if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
    return envUrl || 'http://localhost:8000';
  }
  
  // Otherwise, use the same host as the PWA but with backend port
  // This handles accessing from mobile devices on the same network
  return `http://${window.location.hostname}:8000`;
}

const API_URL = getApiUrl();
const CAPTURE_API_KEY = import.meta.env.VITE_CAPTURE_API_KEY || '';

/**
 * Generate a UUID, with fallback for non-secure contexts (HTTP)
 */
function generateUUID() {
  // Use crypto.randomUUID if available (secure contexts only)
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID();
  }
  
  // Fallback: generate a v4-like UUID using Math.random
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === 'x' ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

// IndexedDB configuration
const DB_NAME = 'capture-offline-db';
const DB_VERSION = 1;
export const OFFLINE_QUEUE_NAME = 'capture-queue';

/**
 * Open (or create) the IndexedDB for offline capture storage
 */
export async function openCaptureDB() {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, DB_VERSION);
    
    request.onerror = () => reject(request.error);
    request.onsuccess = () => resolve(request.result);
    
    request.onupgradeneeded = (event) => {
      const db = event.target.result;
      
      // Create offline queue store if it doesn't exist
      if (!db.objectStoreNames.contains(OFFLINE_QUEUE_NAME)) {
        const store = db.createObjectStore(OFFLINE_QUEUE_NAME, { keyPath: 'id' });
        store.createIndex('timestamp', 'timestamp', { unique: false });
      }
    };
  });
}

/**
 * Get all pending captures from IndexedDB
 */
export async function getPendingCaptures() {
  const db = await openCaptureDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(OFFLINE_QUEUE_NAME, 'readonly');
    const store = tx.objectStore(OFFLINE_QUEUE_NAME);
    const request = store.getAll();
    
    request.onsuccess = () => resolve(request.result || []);
    request.onerror = () => reject(request.error);
  });
}

/**
 * Queue a capture for later sync when offline
 */
async function queueOfflineCapture(endpoint, formData, type) {
  const db = await openCaptureDB();
  
  const captureData = {
    id: generateUUID(),
    endpoint,
    type,
    timestamp: Date.now(),
    retryCount: 0,
    apiKey: CAPTURE_API_KEY, // Store API key for later sync
    data: {},
  };
  
  // Serialize form data
  for (const [key, value] of formData.entries()) {
    if (value instanceof File) {
      captureData.data[key] = {
        type: 'file',
        name: value.name,
        mimeType: value.type,
        data: await value.arrayBuffer(),
      };
    } else {
      captureData.data[key] = {
        type: 'string',
        value: value,
      };
    }
  }
  
  await new Promise((resolve, reject) => {
    const tx = db.transaction(OFFLINE_QUEUE_NAME, 'readwrite');
    const store = tx.objectStore(OFFLINE_QUEUE_NAME);
    const request = store.add(captureData);
    
    request.onsuccess = () => resolve();
    request.onerror = () => reject(request.error);
  });
  
  // Dispatch event for UI update
  window.dispatchEvent(new CustomEvent('captureQueued', { 
    detail: { id: captureData.id, type, timestamp: captureData.timestamp } 
  }));
  
  // Register for background sync if available
  if ('serviceWorker' in navigator && 'sync' in window.registration) {
    try {
      await navigator.serviceWorker.ready;
      await navigator.serviceWorker.registration.sync.register('capture-sync');
    } catch {
      // Background sync not supported or failed - capture will sync manually
    }
  }
  
  return {
    status: 'queued',
    id: captureData.id,
    message: 'Saved offline. Will sync when connected.',
  };
}

/**
 * Get headers for API requests including authentication
 */
function getHeaders() {
  const headers = {};
  if (CAPTURE_API_KEY) {
    headers['X-API-Key'] = CAPTURE_API_KEY;
  }
  return headers;
}

/**
 * Make a capture API request with offline fallback
 */
async function captureRequest(endpoint, formData, type) {
  // Check if online
  if (!navigator.onLine) {
    return queueOfflineCapture(endpoint, formData, type);
  }
  
  try {
    const response = await fetch(`${API_URL}${endpoint}`, {
      method: 'POST',
      headers: getHeaders(),
      body: formData,
    });
    
    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: response.statusText }));
      throw new Error(error.detail || 'Capture failed');
    }
    
    return response.json();
  } catch (error) {
    // Network error - queue for offline
    if (error.name === 'TypeError' || error.message.includes('fetch')) {
      return queueOfflineCapture(endpoint, formData, type);
    }
    throw error;
  }
}

/**
 * Capture API methods
 */
export const captureApi = {
  /**
   * Capture text content
   */
  captureText: async ({ text, title, tags, createCards = true, createExercises = true }) => {
    const formData = new FormData();
    formData.append('content', text);
    if (title) formData.append('title', title);
    if (tags && tags.length > 0) formData.append('tags', tags.join(','));
    formData.append('create_cards', createCards.toString());
    formData.append('create_exercises', createExercises.toString());
    
    return captureRequest('/api/capture/text', formData, 'text');
  },

  /**
   * Capture a URL
   */
  captureUrl: async ({ url, notes, tags, createCards = true, createExercises = true }) => {
    const formData = new FormData();
    formData.append('url', url);
    if (notes) formData.append('notes', notes);
    if (tags && tags.length > 0) formData.append('tags', tags.join(','));
    formData.append('create_cards', createCards.toString());
    formData.append('create_exercises', createExercises.toString());
    
    return captureRequest('/api/capture/url', formData, 'url');
  },

  /**
   * Capture a photo
   */
  capturePhoto: async ({ file, captureType, notes, bookTitle, createCards = true, createExercises = true }) => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('capture_type', captureType || 'general');
    if (notes) formData.append('notes', notes);
    if (bookTitle) formData.append('book_title', bookTitle);
    formData.append('create_cards', createCards.toString());
    formData.append('create_exercises', createExercises.toString());
    
    return captureRequest('/api/capture/photo', formData, 'photo');
  },

  /**
   * Capture a voice memo
   */
  captureVoice: async ({ file, expand = true, createCards = true, createExercises = true }) => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('expand', expand.toString());
    formData.append('create_cards', createCards.toString());
    formData.append('create_exercises', createExercises.toString());
    
    return captureRequest('/api/capture/voice', formData, 'voice');
  },

/**
 * Capture a PDF
 */
capturePdf: async ({ file, contentTypeHint, detectHandwriting = true, createCards = true, createExercises = true }) => {
  const formData = new FormData();
  formData.append('file', file);
  if (contentTypeHint) formData.append('content_type_hint', contentTypeHint);
  formData.append('detect_handwriting', detectHandwriting.toString());
  formData.append('create_cards', createCards.toString());
  formData.append('create_exercises', createExercises.toString());
  
  return captureRequest('/api/capture/pdf', formData, 'pdf');
},

/**
 * Capture multiple book pages as a single book
 */
captureBook: async ({ files, title, authors, isbn, notes, createCards = true, createExercises = true }) => {
  const formData = new FormData();
  // Append each file with the same field name (FastAPI expects list)
  files.forEach(file => {
    formData.append('files', file);
  });
  if (title) formData.append('title', title);
  if (authors) formData.append('authors', authors);
  if (isbn) formData.append('isbn', isbn);
  if (notes) formData.append('notes', notes);
  formData.append('create_cards', createCards.toString());
  formData.append('create_exercises', createExercises.toString());
  
  return captureRequest('/api/capture/book', formData, 'book');
},
};

/**
 * Sync all pending captures from IndexedDB to the server
 * Returns an object with success/failure counts and details
 */
export async function syncPendingCaptures(onProgress) {
  const pending = await getPendingCaptures();
  
  if (pending.length === 0) {
    return { synced: 0, failed: 0, remaining: 0, results: [] };
  }
  
  const results = [];
  let synced = 0;
  let failed = 0;
  
  for (const capture of pending) {
    try {
      // Validate capture has required fields
      if (!capture.endpoint) {
        throw new Error('Missing endpoint - capture is corrupted');
      }
      if (!capture.data || typeof capture.data !== 'object') {
        throw new Error('Missing or invalid data - capture is corrupted');
      }
      
      // Reconstruct FormData from stored data
      const formData = new FormData();
      for (const [key, value] of Object.entries(capture.data)) {
        if (!value || typeof value !== 'object') {
          // Skip invalid fields (corrupted data)
          continue;
        }
        if (value.type === 'file') {
          if (!value.data) {
            throw new Error(`Missing file data for field: ${key}`);
          }
          const blob = new Blob([value.data], { type: value.mimeType || 'application/octet-stream' });
          const file = new File([blob], value.name || 'file', { type: value.mimeType || 'application/octet-stream' });
          formData.append(key, file);
        } else if (value.type === 'string') {
          formData.append(key, value.value || '');
        } else {
          // Handle legacy format or unknown types
          formData.append(key, String(value.value || value));
        }
      }
      
      // Use stored API key or current one
      const headers = {};
      const apiKey = capture.apiKey || CAPTURE_API_KEY;
      if (apiKey) {
        headers['X-API-Key'] = apiKey;
      }
      
      // Make the API request
      const response = await fetch(`${API_URL}${capture.endpoint}`, {
        method: 'POST',
        headers,
        body: formData,
      });
      
      if (!response.ok) {
        const errorBody = await response.text();
        let errorDetail;
        try {
          const errorJson = JSON.parse(errorBody);
          errorDetail = errorJson.detail || errorJson.message || response.statusText;
        } catch {
          errorDetail = errorBody || response.statusText;
        }
        throw new Error(`${response.status}: ${errorDetail}`);
      }
      
      // Success - remove from queue
      await removePendingCapture(capture.id);
      synced++;
      results.push({ id: capture.id, status: 'synced', type: capture.type });
      
      // Report progress
      if (onProgress) {
        onProgress({ synced, failed, total: pending.length, current: capture });
      }
    } catch (error) {
      failed++;
      const errorMsg = error.message || 'Unknown error';
      results.push({ id: capture.id, status: 'failed', type: capture.type, error: errorMsg });
      
      // Update retry count (best-effort)
      try {
        await updateCaptureRetryCount(capture.id, (capture.retryCount || 0) + 1);
      } catch {
        // Ignore retry count update failures
      }
      
      if (onProgress) {
        onProgress({ synced, failed, total: pending.length, current: capture, error });
      }
    }
  }
  
  // Dispatch event for UI update
  window.dispatchEvent(new CustomEvent('captureSyncComplete', { 
    detail: { synced, failed, results } 
  }));
  
  return { synced, failed, remaining: failed, results };
}

/**
 * Remove a pending capture from IndexedDB
 */
async function removePendingCapture(id) {
  const db = await openCaptureDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(OFFLINE_QUEUE_NAME, 'readwrite');
    const store = tx.objectStore(OFFLINE_QUEUE_NAME);
    const request = store.delete(id);
    
    request.onsuccess = () => resolve();
    request.onerror = () => reject(request.error);
  });
}

/**
 * Update retry count for a pending capture
 */
async function updateCaptureRetryCount(id, retryCount) {
  const db = await openCaptureDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(OFFLINE_QUEUE_NAME, 'readwrite');
    const store = tx.objectStore(OFFLINE_QUEUE_NAME);
    const getRequest = store.get(id);
    
    getRequest.onsuccess = () => {
      const capture = getRequest.result;
      if (capture) {
        capture.retryCount = retryCount;
        capture.lastRetry = Date.now();
        const putRequest = store.put(capture);
        putRequest.onsuccess = () => resolve();
        putRequest.onerror = () => reject(putRequest.error);
      } else {
        resolve();
      }
    };
    getRequest.onerror = () => reject(getRequest.error);
  });
}

/**
 * Clear all pending captures (use with caution)
 */
export async function clearPendingCaptures() {
  const db = await openCaptureDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(OFFLINE_QUEUE_NAME, 'readwrite');
    const store = tx.objectStore(OFFLINE_QUEUE_NAME);
    const request = store.clear();
    
    request.onsuccess = () => {
      window.dispatchEvent(new CustomEvent('captureQueueCleared'));
      resolve();
    };
    request.onerror = () => reject(request.error);
  });
}

export default captureApi;
