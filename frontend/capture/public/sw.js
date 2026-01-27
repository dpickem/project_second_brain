/**
 * Service Worker for Second Brain Capture PWA
 * 
 * Features:
 * - Static asset caching for offline access
 * - Offline capture queue in IndexedDB
 * - Background sync for queued captures
 */

// Set to true for development debugging (logs to console)
const DEBUG = false;

const CACHE_NAME = 'capture-v2';
const OFFLINE_QUEUE_NAME = 'capture-queue';
const DB_NAME = 'capture-offline-db';
const DB_VERSION = 1;

/**
 * Generate a UUID, with fallback for environments without crypto.randomUUID
 */
function generateUUID() {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID();
  }
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === 'x' ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

// Assets to cache on install
const PRECACHE_ASSETS = [
  '/capture/',
  '/capture/index.html',
  '/capture/manifest.json',
];

// ============================================================================
// Install Event - Cache static assets
// ============================================================================

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(PRECACHE_ASSETS);
    })
  );
  // Activate immediately
  self.skipWaiting();
});

// ============================================================================
// Activate Event - Clean old caches
// ============================================================================

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys
          .filter((key) => key.startsWith('capture-') && key !== CACHE_NAME)
          .map((key) => caches.delete(key))
      );
    })
  );
  // Claim all clients
  self.clients.claim();
});

// ============================================================================
// Fetch Event - Handle requests with caching
// ============================================================================

self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);
  
  // Handle share target requests (GET for URLs from iOS/Android share sheet)
  // Note: We use GET for better iOS Safari compatibility with Web Share Target API
  if (url.pathname === '/capture/share') {
    // For GET requests, just let it pass through to the app router
    // The ShareTarget component will parse the query params
    if (event.request.method === 'GET') {
      // Fall through to normal fetch handling for navigation
      return;
    }
    // For POST requests (legacy/file shares), use special handler
    if (event.request.method === 'POST') {
      event.respondWith(handleShareTarget(event.request));
      return;
    }
  }
  
  // Capture API calls - queue if offline
  if (url.pathname.startsWith('/api/capture/')) {
    event.respondWith(handleCaptureRequest(event.request));
    return;
  }
  
  // Other API calls - network first
  if (url.pathname.startsWith('/api/')) {
    event.respondWith(
      fetch(event.request).catch(() => {
        return new Response(
          JSON.stringify({ error: 'offline', message: 'No network connection' }),
          { status: 503, headers: { 'Content-Type': 'application/json' } }
        );
      })
    );
    return;
  }
  
  // Static assets - cache first, then network
  event.respondWith(
    caches.match(event.request).then((cached) => {
      if (cached) {
        return cached;
      }
      return fetch(event.request).then((response) => {
        // Cache successful GET requests for static assets
        if (
          event.request.method === 'GET' && 
          response.status === 200 &&
          url.pathname.startsWith('/capture/')
        ) {
          const responseClone = response.clone();
          caches.open(CACHE_NAME).then((cache) => {
            cache.put(event.request, responseClone);
          });
        }
        return response;
      }).catch(() => {
        // Return cached index.html for navigation requests (SPA)
        if (event.request.mode === 'navigate') {
          return caches.match('/capture/index.html');
        }
        return new Response('Offline', { status: 503 });
      });
    })
  );
});

// ============================================================================
// Handle Share Target Requests (file shares from iOS/Android)
// ============================================================================

async function handleShareTarget(request) {
  try {
    const formData = await request.formData();
    
    // Extract shared data
    const title = formData.get('title') || '';
    const text = formData.get('text') || '';
    const url = formData.get('url') || '';
    const mediaFiles = formData.getAll('media');
    
    // If there are files, cache them for the ShareTarget page to retrieve
    if (mediaFiles && mediaFiles.length > 0) {
      const cache = await caches.open('share-target-files');
      
      // Clear any existing shared files first
      const existingKeys = await cache.keys();
      for (const key of existingKeys) {
        await cache.delete(key);
      }
      
      // Cache each shared file
      for (let i = 0; i < mediaFiles.length; i++) {
        const file = mediaFiles[i];
        if (file instanceof File) {
          const cacheKey = `/capture/shared-file-${i}?filename=${encodeURIComponent(file.name)}`;
          const response = new Response(file, {
            headers: { 'Content-Type': file.type || 'application/octet-stream' }
          });
          await cache.put(cacheKey, response);
        }
      }
    }
    
    // Build redirect URL with query params
    const redirectUrl = new URL('/capture/share', self.location.origin);
    if (title) redirectUrl.searchParams.set('title', title);
    if (text) redirectUrl.searchParams.set('text', text);
    if (url) redirectUrl.searchParams.set('url', url);
    if (mediaFiles.length > 0) redirectUrl.searchParams.set('hasFiles', 'true');
    
    // Redirect to the share target page
    return Response.redirect(redirectUrl.toString(), 303);
    
  } catch {
    // Redirect to home on error
    return Response.redirect('/capture/', 303);
  }
}

// ============================================================================
// Handle Capture Requests
// ============================================================================

async function handleCaptureRequest(request) {
  try {
    const response = await fetch(request.clone());
    return response;
  } catch {
    // Network failed - queue for later
    await queueCapture(request);
    return new Response(
      JSON.stringify({ 
        status: 'queued', 
        message: 'Saved offline. Will sync when connected.',
        queued_at: new Date().toISOString()
      }),
      { 
        status: 202, 
        headers: { 'Content-Type': 'application/json' } 
      }
    );
  }
}

// ============================================================================
// IndexedDB Operations
// ============================================================================

function openDB() {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, DB_VERSION);
    
    request.onerror = () => reject(request.error);
    request.onsuccess = () => resolve(request.result);
    
    request.onupgradeneeded = (event) => {
      const db = event.target.result;
      if (!db.objectStoreNames.contains(OFFLINE_QUEUE_NAME)) {
        const store = db.createObjectStore(OFFLINE_QUEUE_NAME, { keyPath: 'id' });
        store.createIndex('timestamp', 'timestamp', { unique: false });
      }
    };
  });
}

async function queueCapture(request) {
  const db = await openDB();
  const formData = await request.formData();
  
  const captureData = {
    id: generateUUID(),
    url: request.url,
    method: request.method,
    timestamp: Date.now(),
    retryCount: 0,
    data: {},
  };
  
  // Serialize form data (including files as ArrayBuffer)
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
  
  return new Promise((resolve, reject) => {
    const tx = db.transaction(OFFLINE_QUEUE_NAME, 'readwrite');
    const store = tx.objectStore(OFFLINE_QUEUE_NAME);
    const request = store.add(captureData);
    
    request.onsuccess = () => {
      // Register for background sync
      if ('sync' in self.registration) {
        self.registration.sync.register('capture-sync');
      }
      
      // Notify any open clients
      notifyClients({
        type: 'CAPTURE_QUEUED',
        capture: { id: captureData.id, timestamp: captureData.timestamp }
      });
      
      resolve();
    };
    
    request.onerror = () => reject(request.error);
  });
}

async function getAllQueued() {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(OFFLINE_QUEUE_NAME, 'readonly');
    const store = tx.objectStore(OFFLINE_QUEUE_NAME);
    const request = store.getAll();
    
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

async function deleteQueued(id) {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(OFFLINE_QUEUE_NAME, 'readwrite');
    const store = tx.objectStore(OFFLINE_QUEUE_NAME);
    const request = store.delete(id);
    
    request.onsuccess = () => resolve();
    request.onerror = () => reject(request.error);
  });
}

async function updateQueued(capture) {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(OFFLINE_QUEUE_NAME, 'readwrite');
    const store = tx.objectStore(OFFLINE_QUEUE_NAME);
    const request = store.put(capture);
    
    request.onsuccess = () => resolve();
    request.onerror = () => reject(request.error);
  });
}

// ============================================================================
// Background Sync
// ============================================================================

self.addEventListener('sync', (event) => {
  if (event.tag === 'capture-sync') {
    event.waitUntil(syncQueuedCaptures());
  }
});

async function syncQueuedCaptures() {
  const queued = await getAllQueued();
  
  for (const capture of queued) {
    try {
      // Rebuild FormData from stored data
      const formData = new FormData();
      
      for (const [key, value] of Object.entries(capture.data)) {
        if (value.type === 'file') {
          const blob = new Blob([value.data], { type: value.mimeType });
          const file = new File([blob], value.name, { type: value.mimeType });
          formData.append(key, file);
        } else {
          formData.append(key, value.value);
        }
      }
      
      // Build headers with API key if available
      const headers = {};
      if (capture.apiKey) {
        headers['X-API-Key'] = capture.apiKey;
      }
      
      // Retry the request
      const response = await fetch(capture.url, {
        method: capture.method,
        headers,
        body: formData,
      });
      
      if (response.ok) {
        // Success - remove from queue
        await deleteQueued(capture.id);
        
        // Notify clients
        notifyClients({
          type: 'CAPTURE_SYNCED',
          capture: { id: capture.id }
        });
      } else {
        // Server error - increment retry count
        capture.retryCount++;
        if (capture.retryCount < 5) {
          await updateQueued(capture);
        } else {
          // Too many retries - give up
          await deleteQueued(capture.id);
        }
      }
    } catch {
      // Network still down - will retry on next sync
    }
  }
}

// ============================================================================
// Client Notifications
// ============================================================================

async function notifyClients(message) {
  const clients = await self.clients.matchAll();
  clients.forEach((client) => {
    client.postMessage(message);
  });
}

// ============================================================================
// Periodic Background Sync (for browsers that support it)
// ============================================================================

self.addEventListener('periodicsync', (event) => {
  if (event.tag === 'capture-periodic-sync') {
    event.waitUntil(syncQueuedCaptures());
  }
});
