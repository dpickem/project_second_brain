# Mobile Capture PWA Implementation Plan

> **Document Status**: Implementation Plan  
> **Created**: January 2026  
> **Target Phase**: Phase 10 (Weeks 39-42)  
> **Design Doc**: `design_docs/08_mobile_capture.md`  
> **Dependencies**: `01_ingestion_layer_implementation.md`, `07_frontend_application_implementation.md`

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
   - [Design Goals](#design-goals)
   - [Current State Assessment](#current-state-assessment)
   - [What This Plan Covers](#what-this-plan-covers)
   - [Architecture Overview](#architecture-overview)
   - [Directory Structure](#directory-structure)
2. [Prerequisites](#2-prerequisites)
   - [2.1 Prior Work Required](#21-prior-work-required)
   - [2.2 New Backend Endpoints Needed](#22-new-backend-endpoints-needed)
   - [2.3 Frontend Dependencies](#23-frontend-dependencies)
   - [2.4 Browser Compatibility Requirements](#24-browser-compatibility-requirements)
3. [Implementation Phases](#3-implementation-phases)
   - [Phase 10A: PWA Foundation (Days 1-3)](#phase-10a-pwa-foundation-days-1-3)
     - [Task 10A.1: PWA Manifest Configuration](#task-10a1-pwa-manifest-configuration)
     - [Task 10A.2: Vite Configuration for Capture PWA](#task-10a2-vite-configuration-for-capture-pwa)
     - [Task 10A.3: Service Worker Implementation](#task-10a3-service-worker-implementation)
     - [Task 10A.4: Offline Support Hooks](#task-10a4-offline-support-hooks)
   - [Phase 10B: Capture UI Components (Days 4-8)](#phase-10b-capture-ui-components-days-4-8)
     - [Task 10B.1: Main Capture Screen](#task-10b1-main-capture-screen)
     - [Task 10B.2: Capture Button Component](#task-10b2-capture-button-component)
     - [Task 10B.3: Photo Capture Component](#task-10b3-photo-capture-component)
     - [Task 10B.4: Voice Capture Component](#task-10b4-voice-capture-component)
     - [Task 10B.5: Text Capture Component](#task-10b5-text-capture-component)
     - [Task 10B.6: URL Capture Component](#task-10b6-url-capture-component)
     - [Task 10B.7: Supporting Components](#task-10b7-supporting-components)
   - [Phase 10C: API Client & Share Target (Days 9-11)](#phase-10c-api-client--share-target-days-9-11)
     - [Task 10C.1: Capture API Client](#task-10c1-capture-api-client)
     - [Task 10C.2: Share Target Handler](#task-10c2-share-target-handler)
     - [Task 10C.3: File Share Handler](#task-10c3-file-share-handler)
   - [Phase 10D: Mobile-Optimized Styles (Days 12-14)](#phase-10d-mobile-optimized-styles-days-12-14)
     - [Task 10D.1: Mobile CSS Foundation](#task-10d1-mobile-css-foundation)
4. [Backend Additions](#4-backend-additions)
   - [Task 10E.1: Additional Capture Endpoints](#task-10e1-additional-capture-endpoints)
5. [Timeline Summary](#5-timeline-summary)
   - [Phase 10: Mobile Capture PWA (Days 1-14)](#phase-10-mobile-capture-pwa-days-1-14)
   - [Gantt View](#gantt-view)
6. [Testing Strategy](#6-testing-strategy)
   - [6.1 Unit Tests](#61-unit-tests)
   - [6.2 Integration Tests (Playwright)](#62-integration-tests-playwright)
   - [6.3 Manual Testing Checklist](#63-manual-testing-checklist)
7. [Success Criteria](#7-success-criteria)
   - [Functional Requirements](#functional-requirements)
   - [Performance Requirements](#performance-requirements)
   - [Quality Requirements](#quality-requirements)
8. [Risk Assessment](#8-risk-assessment)
9. [Deployment to Mobile Devices](#9-deployment-to-mobile-devices)
   - [9.1 iOS Deployment (Safari)](#91-ios-deployment-safari)
   - [9.2 Android Deployment (Chrome)](#92-android-deployment-chrome)
   - [9.3 Deployment Checklist](#93-deployment-checklist)
10. [Related Documents](#10-related-documents)

---

## 1. Executive Summary

This document provides a detailed implementation plan for the Mobile Capture Progressive Web App (PWA). The PWA enables low-friction knowledge capture on mobile devices with offline support, camera access, voice recording, and share target integration.

### Design Goals

1. **< 3 Seconds to Capture**: Minimize time from idea to saved
2. **Offline-First**: Queue captures for later sync
3. **Minimal UI**: Large touch targets, few steps
4. **Reliable**: Never lose a capture
5. **Cross-Platform**: iOS Safari, Android Chrome

### Current State Assessment

The backend already supports capture endpoints (from Phase 2 Ingestion):

| Component | Status | Notes |
|-----------|--------|-------|
| `/api/capture/pdf` | ✅ Implemented | PDF processing with highlights |
| `/api/capture/book` | ✅ Implemented | Book photo OCR pipeline |
| `/api/capture/voice` | ✅ Implemented | Voice transcription endpoint |
| `/api/capture/url` | ⬜ Needs Addition | URL capture endpoint |
| `/api/capture/text` | ⬜ Needs Addition | Quick text capture endpoint |
| Frontend PWA | ⬜ Not Started | This plan |

### What This Plan Covers

| In Scope | Out of Scope |
|----------|--------------|
| PWA manifest and configuration | Backend capture endpoints (existing) |
| Service Worker with offline queue | LLM processing (already implemented) |
| IndexedDB for offline storage | Desktop frontend (separate plan) |
| Camera capture UI | Authentication (future) |
| Voice recording UI | Push notifications (v2 feature) |
| Text and URL capture UI | |
| Share Target integration | |
| Mobile-optimized styles | |
| Offline support hooks | |

### Architecture Overview

```text
MOBILE CAPTURE PWA ARCHITECTURE
===============================

┌─────────────────────────────────────────────────────────────────────────────┐
│                          MOBILE DEVICE                                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│   │   📷 Photo   │  │   🎤 Voice   │  │   ✏️ Note    │  │   🔗 URL     │    │
│   └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘    │
│          │                 │                 │                 │             │
│          └─────────────────┴─────────────────┴─────────────────┘             │
│                                      │                                       │
│                             ┌────────▼────────┐                              │
│                             │   Capture UI    │                              │
│                             │  (React/Vite)   │                              │
│                             └────────┬────────┘                              │
│                                      │                                       │
│                    ┌─────────────────┴─────────────────┐                     │
│                    │          Service Worker           │                     │
│                    │   • Offline queue (IndexedDB)     │                     │
│                    │   • Background sync               │                     │
│                    │   • Static asset caching          │                     │
│                    └─────────────────┬─────────────────┘                     │
│                                      │                                       │
└──────────────────────────────────────┼───────────────────────────────────────┘
                                       │
                                       │ Upload when online
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              BACKEND (Existing)                              │
├─────────────────────────────────────────────────────────────────────────────┤
│   /api/capture/photo   →   Vision OCR   →   Inbox                           │
│   /api/capture/voice   →   Whisper      →   Inbox                           │
│   /api/capture/text    →   Save         →   Inbox   (NEW)                   │
│   /api/capture/url     →   Fetch        →   Inbox   (NEW)                   │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Directory Structure

The Mobile Capture PWA lives in a **dedicated `capture/` directory** separate from the main browser frontend. This keeps the mobile-specific code isolated and allows for independent builds and deployments.

```text
frontend/
├── src/                          # Main browser frontend (existing)
│   ├── api/
│   ├── components/
│   ├── pages/
│   ├── App.jsx
│   └── main.jsx
│
├── capture/                      # ★ Mobile Capture PWA (NEW)
│   ├── public/
│   │   ├── manifest.json         # PWA manifest
│   │   ├── sw.js                 # Service Worker
│   │   ├── icons/                # App icons (192, 512, maskable)
│   │   └── screenshots/          # Install screenshots
│   │
│   ├── src/
│   │   ├── api/
│   │   │   └── capture.js        # Capture API client
│   │   │
│   │   ├── components/
│   │   │   ├── CaptureButton.jsx
│   │   │   ├── CaptureModal.jsx
│   │   │   ├── PhotoCapture.jsx
│   │   │   ├── VoiceCapture.jsx
│   │   │   ├── TextCapture.jsx
│   │   │   ├── UrlCapture.jsx
│   │   │   ├── OfflineBanner.jsx
│   │   │   ├── RecentCaptures.jsx
│   │   │   └── index.js
│   │   │
│   │   ├── hooks/
│   │   │   ├── useOnlineStatus.js
│   │   │   ├── usePendingCaptures.js
│   │   │   ├── useMediaRecorder.js
│   │   │   ├── useToast.js
│   │   │   └── index.js
│   │   │
│   │   ├── pages/
│   │   │   ├── MobileCapture.jsx
│   │   │   ├── ShareTarget.jsx
│   │   │   └── ShareTargetFiles.jsx
│   │   │
│   │   ├── styles/
│   │   │   ├── variables.css     # Can import shared tokens from ../../../src/styles/
│   │   │   └── capture.css
│   │   │
│   │   ├── App.jsx               # Capture app root
│   │   └── main.jsx              # Capture app entry point
│   │
│   ├── index.html                # PWA HTML entry
│   ├── vite.config.js            # Separate Vite config for PWA build
│   └── package.json              # Optional: PWA-specific deps (or use root)
│
├── package.json                  # Shared dependencies
├── vite.config.js                # Main frontend config
└── tailwind.config.js            # Shared Tailwind config
```

**Why Separate?**
1. **Independent builds**: Can build/deploy PWA without rebuilding full frontend
2. **Smaller bundle**: PWA only includes capture-specific code (~50KB vs ~500KB)
3. **Different entry points**: PWA starts at `/capture`, main app at `/`
4. **Easier testing**: Can test PWA in isolation
5. **Clear ownership**: Mobile-specific code is easy to find

**Shared Code**: The capture app can import shared utilities from the main frontend:
```javascript
// Import shared API client base
import { apiClient } from '../../src/api/client';

// Import shared design tokens (CSS variables)
@import '../../src/styles/variables.css';
```

---

## 2. Prerequisites

### 2.1 Prior Work Required

| Phase | Component | Why Required |
|-------|-----------|--------------|
| **Phase 2** | Ingestion pipelines | `/api/capture/*` endpoints |
| **Phase 3** | LLM processing | OCR and transcription |
| **Phase 9A** | Design system | Shared tokens and components |

### 2.2 New Backend Endpoints Needed

Before PWA implementation, add these capture endpoints:

```python
# backend/app/routers/capture.py (additions)

@router.post("/text")
async def capture_text(
    text: str = Form(...),
    title: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
) -> CaptureResponse:
    """Quick text capture from mobile."""
    # Save to inbox with minimal processing
    ...

@router.post("/url")
async def capture_url(
    url: str = Form(...),
    notes: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
) -> CaptureResponse:
    """Save URL for later processing."""
    # Validate URL, save to inbox, queue for web_article pipeline
    ...
```

**Estimated Backend Work**: 4 hours

### 2.3 Frontend Dependencies

```bash
# Already available in frontend/
react           # ^18.2.0
react-router-dom # ^6.22.0
framer-motion   # ^11.0.3
clsx            # ^2.1.0

# PWA-specific (no new npm packages needed)
# Service Worker: Native browser API
# IndexedDB: Native browser API (idb wrapper optional)
# MediaRecorder: Native browser API
```

### 2.4 Browser Compatibility Requirements

**Target Versions**: Chrome Android 90+, iOS 16+ (Safari 16+)

| Feature | Chrome Android | Safari iOS | Chrome iOS | Notes |
|---------|----------------|------------|------------|-------|
| PWA Install | ✅ Native | ✅ "Add to Home Screen" | ❌ Not supported | Chrome iOS uses WebKit; must use Safari to install |
| Service Worker | ✅ Full | ✅ Full | ✅ Full | Chrome iOS uses Safari's SW implementation |
| Background Sync | ✅ Full | ✅ Full (iOS 16+) | ✅ Full (iOS 16+) | Reliable on iOS 16+ with Push Notifications |
| IndexedDB | ✅ Full | ✅ Full | ✅ Full | |
| MediaRecorder | ✅ WebM | ✅ WebM (iOS 16+) | ✅ WebM (iOS 16+) | iOS 16+ added WebM support |
| Share Target | ✅ Full | ✅ Full (iOS 16.4+) | ❌ Not supported | Only Safari can register as share target on iOS |
| getUserMedia | ✅ Full | ✅ Full | ✅ Full | Requires HTTPS |
| Push Notifications | ✅ Full | ✅ Full (iOS 16.4+) | ✅ Full (iOS 16.4+) | Web Push added in iOS 16.4 |
| Badging API | ✅ Full | ✅ Full (iOS 16.4+) | ❌ Not supported | App icon badge updates |

> **Note**: All browsers on iOS (Chrome, Firefox, Edge, etc.) use Apple's WebKit engine due to App Store requirements. This means they inherit Safari's PWA limitations. Users must use Safari to install PWAs on iOS. With iOS 16+, most PWA features work reliably.

---

## 3. Implementation Phases

### Phase 10A: PWA Foundation (Days 1-3)

This phase establishes the PWA infrastructure: manifest, service worker, and offline storage.

#### Task 10A.1: PWA Manifest Configuration

**Purpose**: Configure the PWA manifest to enable installation and define app identity.

**File**: `frontend/capture/public/manifest.json`

```json
{
  "name": "Second Brain Capture",
  "short_name": "Capture",
  "description": "Quick knowledge capture for your Second Brain",
  "start_url": "/capture",
  "display": "standalone",
  "orientation": "portrait",
  "background_color": "#0a0f1a",
  "theme_color": "#6366f1",
  "icons": [
    {
      "src": "/icons/capture-192.png",
      "sizes": "192x192",
      "type": "image/png",
      "purpose": "any maskable"
    },
    {
      "src": "/icons/capture-512.png",
      "sizes": "512x512",
      "type": "image/png",
      "purpose": "any maskable"
    }
  ],
  "share_target": {
    "action": "/capture/share",
    "method": "POST",
    "enctype": "multipart/form-data",
    "params": {
      "title": "title",
      "text": "text",
      "url": "url",
      "files": [
        {
          "name": "media",
          "accept": ["image/*", "audio/*"]
        }
      ]
    }
  },
  "categories": ["productivity", "utilities"],
  "screenshots": [
    {
      "src": "/screenshots/capture-main.png",
      "sizes": "390x844",
      "type": "image/png",
      "label": "Capture screen showing photo, voice, note, and URL options"
    }
  ]
}
```

**Link in HTML**: `frontend/capture/index.html`

```html
<head>
  <!-- PWA Meta Tags -->
  <link rel="manifest" href="/manifest.json">
  <meta name="theme-color" content="#6366f1">
  <meta name="apple-mobile-web-app-capable" content="yes">
  <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
  <meta name="apple-mobile-web-app-title" content="Capture">
  
  <!-- iOS Icons -->
  <link rel="apple-touch-icon" href="/icons/capture-192.png">
  
  <!-- Viewport for mobile -->
  <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no, viewport-fit=cover">
</head>
```

**App Icons Required**:

| File | Size | Purpose |
|------|------|---------|
| `capture-192.png` | 192×192 | Android home screen, iOS |
| `capture-512.png` | 512×512 | Android splash, Play Store |
| `capture-maskable.png` | 512×512 | Android adaptive icons (with safe zone) |

**Deliverables**:
- [ ] `frontend/capture/public/manifest.json` — PWA manifest
- [ ] `frontend/capture/index.html` — PWA HTML with meta tags
- [ ] `frontend/capture/public/icons/` — App icons (192, 512, maskable)
- [ ] `frontend/capture/public/screenshots/` — Install screenshots

**Estimated Time**: 3 hours

---

#### Task 10A.2: Vite Configuration for Capture PWA

**Purpose**: Set up separate Vite build configuration for the capture PWA.

**File**: `frontend/capture/vite.config.js`

```javascript
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { resolve } from 'path';

export default defineConfig({
  plugins: [react()],
  
  // Root directory for the capture app
  root: resolve(__dirname),
  
  // Public directory for static assets (manifest, sw, icons)
  publicDir: resolve(__dirname, 'public'),
  
  // Build configuration
  build: {
    outDir: resolve(__dirname, '../dist/capture'),
    emptyOutDir: true,
    rollupOptions: {
      input: resolve(__dirname, 'index.html'),
    },
  },
  
  // Dev server configuration
  server: {
    port: 5174, // Different port from main frontend (5173)
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  
  // Resolve aliases for shared code
  resolve: {
    alias: {
      '@shared': resolve(__dirname, '../src'),
      '@capture': resolve(__dirname, 'src'),
    },
  },
});
```

**File**: `frontend/capture/src/App.jsx`

```jsx
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Toaster } from 'react-hot-toast';

import { MobileCapture } from './pages/MobileCapture';
import { ShareTarget } from './pages/ShareTarget';
import { ShareTargetFiles } from './pages/ShareTargetFiles';

import './styles/capture.css';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30000,
      retry: 1,
    },
  },
});

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter basename="/capture">
        <Routes>
          <Route path="/" element={<MobileCapture />} />
          <Route path="/share" element={<ShareTarget />} />
          <Route path="/share-files" element={<ShareTargetFiles />} />
        </Routes>
        <Toaster 
          position="bottom-center"
          toastOptions={{
            style: {
              background: 'var(--color-bg-secondary)',
              color: 'var(--color-text-primary)',
            },
          }}
        />
      </BrowserRouter>
    </QueryClientProvider>
  );
}

export default App;
```

**Add Scripts to `package.json`**:

```json
{
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "dev:capture": "vite --config capture/vite.config.js",
    "build:capture": "vite build --config capture/vite.config.js",
    "preview:capture": "vite preview --config capture/vite.config.js"
  }
}
```

**Deliverables**:
- [ ] `frontend/capture/vite.config.js` — Separate Vite config for PWA
- [ ] `frontend/capture/src/App.jsx` — Capture app root component
- [ ] `frontend/capture/src/main.jsx` — Entry point with SW registration
- [ ] Update `frontend/package.json` with capture scripts

**Estimated Time**: 2 hours

---

#### Task 10A.3: Service Worker Implementation

**Purpose**: Enable offline functionality through caching and request queuing.

**File**: `frontend/capture/public/sw.js`

```javascript
// Service Worker for Second Brain Capture PWA
const CACHE_NAME = 'capture-v1';
const OFFLINE_QUEUE_NAME = 'capture-queue';

// Assets to cache on install
const PRECACHE_ASSETS = [
  '/capture',
  '/capture/index.html',
  '/assets/capture.css',
  '/assets/capture.js',
  '/icons/capture-192.png',
  '/icons/capture-512.png',
];

// Cache static assets on install
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      console.log('[SW] Precaching assets');
      return cache.addAll(PRECACHE_ASSETS);
    })
  );
  // Activate immediately
  self.skipWaiting();
});

// Clean old caches on activate
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys
          .filter((key) => key !== CACHE_NAME)
          .map((key) => caches.delete(key))
      );
    })
  );
  // Claim all clients
  self.clients.claim();
});

// Fetch handler with offline support
self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);
  
  // Capture API calls - queue if offline
  if (url.pathname.startsWith('/api/capture/')) {
    event.respondWith(handleCaptureRequest(event.request));
    return;
  }
  
  // Network-first for API calls
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
  
  // Cache-first for static assets
  event.respondWith(
    caches.match(event.request).then((cached) => {
      if (cached) {
        return cached;
      }
      return fetch(event.request).then((response) => {
        // Cache successful GET requests
        if (event.request.method === 'GET' && response.status === 200) {
          const responseClone = response.clone();
          caches.open(CACHE_NAME).then((cache) => {
            cache.put(event.request, responseClone);
          });
        }
        return response;
      });
    })
  );
});

// Handle capture requests with offline fallback
async function handleCaptureRequest(request) {
  try {
    const response = await fetch(request.clone());
    return response;
  } catch (error) {
    // Network failed - queue for later
    console.log('[SW] Network failed, queuing capture');
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

// Queue capture in IndexedDB
async function queueCapture(request) {
  const db = await openCaptureDB();
  const formData = await request.formData();
  
  const captureData = {
    id: crypto.randomUUID(),
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
  
  const tx = db.transaction(OFFLINE_QUEUE_NAME, 'readwrite');
  await tx.objectStore(OFFLINE_QUEUE_NAME).add(captureData);
  await tx.done;
  
  // Register for background sync
  if ('sync' in self.registration) {
    await self.registration.sync.register('capture-sync');
  }
  
  // Notify any open clients
  const clients = await self.clients.matchAll();
  clients.forEach((client) => {
    client.postMessage({
      type: 'CAPTURE_QUEUED',
      capture: { id: captureData.id, timestamp: captureData.timestamp }
    });
  });
}

// Background sync handler
self.addEventListener('sync', (event) => {
  if (event.tag === 'capture-sync') {
    event.waitUntil(syncQueuedCaptures());
  }
});

// Sync all queued captures
async function syncQueuedCaptures() {
  const db = await openCaptureDB();
  const tx = db.transaction(OFFLINE_QUEUE_NAME, 'readwrite');
  const store = tx.objectStore(OFFLINE_QUEUE_NAME);
  const queued = await store.getAll();
  
  console.log(`[SW] Syncing ${queued.length} queued captures`);
  
  for (const capture of queued) {
    try {
      const formData = new FormData();
      
      // Reconstruct form data
      for (const [key, value] of Object.entries(capture.data)) {
        if (value.type === 'file') {
          const blob = new Blob([value.data], { type: value.mimeType });
          formData.append(key, blob, value.name);
        } else {
          formData.append(key, value.value);
        }
      }
      
      const response = await fetch(capture.url, {
        method: capture.method,
        body: formData,
      });
      
      if (response.ok) {
        // Success - remove from queue
        await store.delete(capture.id);
        console.log(`[SW] Synced capture ${capture.id}`);
        
        // Notify clients
        const clients = await self.clients.matchAll();
        clients.forEach((client) => {
          client.postMessage({
            type: 'CAPTURE_SYNCED',
            capture: { id: capture.id }
          });
        });
      } else if (response.status >= 400 && response.status < 500) {
        // Client error - don't retry, remove
        await store.delete(capture.id);
        console.error(`[SW] Capture ${capture.id} failed with ${response.status}, removing`);
      } else {
        // Server error - increment retry count
        capture.retryCount++;
        if (capture.retryCount >= 5) {
          await store.delete(capture.id);
          console.error(`[SW] Capture ${capture.id} failed after 5 retries, removing`);
        } else {
          await store.put(capture);
        }
      }
    } catch (error) {
      console.error(`[SW] Sync failed for capture ${capture.id}:`, error);
      capture.retryCount++;
      if (capture.retryCount < 5) {
        await store.put(capture);
      }
    }
  }
}

// IndexedDB helper
function openCaptureDB() {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open('CaptureDB', 1);
    
    request.onupgradeneeded = (event) => {
      const db = event.target.result;
      if (!db.objectStoreNames.contains(OFFLINE_QUEUE_NAME)) {
        db.createObjectStore(OFFLINE_QUEUE_NAME, { keyPath: 'id' });
      }
    };
    
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

// Handle messages from clients
self.addEventListener('message', (event) => {
  if (event.data.type === 'FORCE_SYNC') {
    syncQueuedCaptures();
  }
  
  if (event.data.type === 'GET_QUEUE_COUNT') {
    openCaptureDB().then(async (db) => {
      const tx = db.transaction(OFFLINE_QUEUE_NAME, 'readonly');
      const count = await tx.objectStore(OFFLINE_QUEUE_NAME).count();
      event.ports[0].postMessage({ count });
    });
  }
});
```

**Register Service Worker**: `frontend/capture/src/main.jsx`

```javascript
// Register service worker for PWA
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js')
      .then((registration) => {
        console.log('SW registered:', registration.scope);
      })
      .catch((error) => {
        console.error('SW registration failed:', error);
      });
  });
}
```

**Deliverables**:
- [ ] `frontend/capture/public/sw.js` — Service Worker with offline queue
- [ ] `frontend/capture/src/main.jsx` — App entry with SW registration
- [ ] IndexedDB schema for capture queue

**Estimated Time**: 8 hours

---

#### Task 10A.4: Offline Support Hooks

**Purpose**: Create React hooks to monitor connectivity and queue status.

##### Enhanced `useOnlineStatus` Hook

The hook provides comprehensive connectivity status beyond just `navigator.onLine`:

| Return Value | Type | Description |
|--------------|------|-------------|
| `isOnline` | `boolean` | **Combined status** - `true` only if browser online AND server reachable |
| `isBrowserOnline` | `boolean` | Raw `navigator.onLine` status |
| `isServerReachable` | `boolean` | Whether `/api/health` endpoint responds (2xx) |
| `isChecking` | `boolean` | Currently performing health check |
| `lastChecked` | `Date \| null` | Timestamp of last successful check |
| `checkNow()` | `function` | Manual retry function to trigger immediate check |

**Key Features:**
- **Health Check Endpoint**: Pings `/api/health` with 5-second timeout
- **Periodic Checks**: Every 30 seconds when browser reports online
- **Event-Triggered Checks**: On browser `online` event, tab visibility change (user returns to app)
- **Abort Handling**: Cancels in-flight requests when new check starts or component unmounts
- **Optimistic Default**: Assumes server reachable initially to avoid flash of offline UI

**Why Not Just `navigator.onLine`?**
- Returns `true` behind captive portals (hotel WiFi login pages)
- Returns `true` when server is down but internet works
- Returns `true` with DNS issues for specific domains
- Doesn't detect server maintenance or API outages

**File**: `frontend/capture/src/hooks/useOnlineStatus.js`

```javascript
import { useState, useEffect, useCallback, useRef } from 'react';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const HEALTH_CHECK_INTERVAL = 30000; // 30 seconds
const HEALTH_CHECK_TIMEOUT = 5000;   // 5 second timeout

/**
 * Comprehensive online status hook.
 * 
 * Goes beyond navigator.onLine to verify actual server connectivity:
 * 1. Browser online/offline events (quick detection)
 * 2. Periodic health check to Second Brain API
 * 3. Server reachability verification on network change
 * 
 * Returns:
 * - isOnline: true only if browser is online AND server is reachable
 * - isBrowserOnline: raw navigator.onLine status
 * - isServerReachable: whether the API health endpoint responds
 * - lastChecked: timestamp of last successful health check
 * - checkNow: function to trigger immediate health check
 */
export function useOnlineStatus() {
  const [isBrowserOnline, setIsBrowserOnline] = useState(navigator.onLine);
  const [isServerReachable, setIsServerReachable] = useState(true); // Optimistic default
  const [lastChecked, setLastChecked] = useState(null);
  const [isChecking, setIsChecking] = useState(false);
  
  const intervalRef = useRef(null);
  const abortControllerRef = useRef(null);
  
  /**
   * Check if the Second Brain API is reachable.
   * Uses the health endpoint with a timeout.
   */
  const checkServerHealth = useCallback(async () => {
    // Don't check if browser is offline
    if (!navigator.onLine) {
      setIsServerReachable(false);
      return false;
    }
    
    // Abort any in-flight request
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    
    abortControllerRef.current = new AbortController();
    setIsChecking(true);
    
    try {
      const response = await fetch(`${API_URL}/api/health`, {
        method: 'GET',
        signal: abortControllerRef.current.signal,
        // Short timeout for health checks
        headers: { 'Cache-Control': 'no-cache' },
      });
      
      // Consider any 2xx response as success
      const isHealthy = response.ok;
      setIsServerReachable(isHealthy);
      
      if (isHealthy) {
        setLastChecked(new Date());
        
        // Trigger sync when server becomes reachable
        if ('serviceWorker' in navigator) {
          navigator.serviceWorker.ready.then((registration) => {
            registration.active?.postMessage({ type: 'FORCE_SYNC' });
          });
        }
      }
      
      return isHealthy;
      
    } catch (error) {
      // Network error, timeout, or aborted
      if (error.name !== 'AbortError') {
        console.warn('[useOnlineStatus] Server health check failed:', error.message);
        setIsServerReachable(false);
      }
      return false;
      
    } finally {
      setIsChecking(false);
    }
  }, []);
  
  /**
   * Check server with timeout wrapper.
   */
  const checkWithTimeout = useCallback(async () => {
    const timeoutPromise = new Promise((_, reject) => {
      setTimeout(() => reject(new Error('Health check timeout')), HEALTH_CHECK_TIMEOUT);
    });
    
    try {
      await Promise.race([checkServerHealth(), timeoutPromise]);
    } catch (error) {
      console.warn('[useOnlineStatus] Health check timed out');
      setIsServerReachable(false);
    }
  }, [checkServerHealth]);
  
  // Handle browser online/offline events
  useEffect(() => {
    const handleOnline = () => {
      console.log('[useOnlineStatus] Browser online event');
      setIsBrowserOnline(true);
      // Verify server is actually reachable
      checkWithTimeout();
    };
    
    const handleOffline = () => {
      console.log('[useOnlineStatus] Browser offline event');
      setIsBrowserOnline(false);
      setIsServerReachable(false);
    };
    
    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);
    
    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, [checkWithTimeout]);
  
  // Periodic health checks when browser is online
  useEffect(() => {
    // Initial check on mount
    if (navigator.onLine) {
      checkWithTimeout();
    }
    
    // Set up periodic checks
    intervalRef.current = setInterval(() => {
      if (navigator.onLine) {
        checkWithTimeout();
      }
    }, HEALTH_CHECK_INTERVAL);
    
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, [checkWithTimeout]);
  
  // Also check on visibility change (user returns to app)
  useEffect(() => {
    const handleVisibilityChange = () => {
      if (document.visibilityState === 'visible' && navigator.onLine) {
        checkWithTimeout();
      }
    };
    
    document.addEventListener('visibilitychange', handleVisibilityChange);
    return () => document.removeEventListener('visibilitychange', handleVisibilityChange);
  }, [checkWithTimeout]);
  
  // Combined status: only "online" if both browser and server are reachable
  const isOnline = isBrowserOnline && isServerReachable;
  
  return {
    isOnline,              // Combined status (use this in most cases)
    isBrowserOnline,       // Raw browser status
    isServerReachable,     // API server status
    isChecking,            // Currently checking
    lastChecked,           // Last successful check timestamp
    checkNow: checkWithTimeout,  // Manual check trigger
  };
}

/**
 * Simplified hook that just returns boolean online status.
 * Use this for simpler components that don't need detailed status.
 */
export function useIsOnline() {
  const { isOnline } = useOnlineStatus();
  return isOnline;
}
```

**File**: `frontend/capture/src/hooks/usePendingCaptures.js`

```javascript
import { useState, useEffect, useCallback } from 'react';

/**
 * Hook to track pending captures in the offline queue.
 */
export function usePendingCaptures() {
  const [pendingCount, setPendingCount] = useState(0);
  const [pendingCaptures, setPendingCaptures] = useState([]);
  
  const refreshQueue = useCallback(async () => {
    if (!('serviceWorker' in navigator)) return;
    
    const registration = await navigator.serviceWorker.ready;
    const messageChannel = new MessageChannel();
    
    messageChannel.port1.onmessage = (event) => {
      setPendingCount(event.data.count);
    };
    
    registration.active?.postMessage(
      { type: 'GET_QUEUE_COUNT' },
      [messageChannel.port2]
    );
  }, []);
  
  useEffect(() => {
    refreshQueue();
    
    // Listen for SW messages about queue changes
    const handleMessage = (event) => {
      if (event.data.type === 'CAPTURE_QUEUED') {
        refreshQueue();
      }
      if (event.data.type === 'CAPTURE_SYNCED') {
        refreshQueue();
      }
    };
    
    navigator.serviceWorker?.addEventListener('message', handleMessage);
    
    // Also refresh when coming online
    window.addEventListener('online', refreshQueue);
    
    return () => {
      navigator.serviceWorker?.removeEventListener('message', handleMessage);
      window.removeEventListener('online', refreshQueue);
    };
  }, [refreshQueue]);
  
  return { pendingCount, pendingCaptures, refreshQueue };
}
```

**File**: `frontend/capture/src/hooks/useMediaRecorder.js`

```javascript
import { useState, useRef, useCallback } from 'react';

/**
 * Hook to handle audio recording with cross-browser support.
 * 
 * Safari requires MP4/AAC, Chrome/Firefox prefer WebM.
 * This hook detects the best format automatically.
 */
export function useMediaRecorder() {
  const [isRecording, setIsRecording] = useState(false);
  const [audioBlob, setAudioBlob] = useState(null);
  const [error, setError] = useState(null);
  const [duration, setDuration] = useState(0);
  
  const mediaRecorderRef = useRef(null);
  const chunksRef = useRef([]);
  const streamRef = useRef(null);
  const timerRef = useRef(null);
  
  // Detect best supported mime type
  const getMimeType = () => {
    if (MediaRecorder.isTypeSupported('audio/webm;codecs=opus')) {
      return 'audio/webm;codecs=opus';
    }
    if (MediaRecorder.isTypeSupported('audio/webm')) {
      return 'audio/webm';
    }
    if (MediaRecorder.isTypeSupported('audio/mp4')) {
      return 'audio/mp4';
    }
    return 'audio/wav';
  };
  
  const startRecording = useCallback(async () => {
    try {
      setError(null);
      const stream = await navigator.mediaDevices.getUserMedia({ 
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        }
      });
      streamRef.current = stream;
      
      const mimeType = getMimeType();
      const mediaRecorder = new MediaRecorder(stream, { mimeType });
      mediaRecorderRef.current = mediaRecorder;
      chunksRef.current = [];
      
      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) {
          chunksRef.current.push(e.data);
        }
      };
      
      mediaRecorder.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: mimeType });
        setAudioBlob(blob);
        
        // Clean up stream
        streamRef.current?.getTracks().forEach(track => track.stop());
        streamRef.current = null;
      };
      
      mediaRecorder.start(1000); // Chunk every second
      setIsRecording(true);
      setDuration(0);
      
      // Start timer
      timerRef.current = setInterval(() => {
        setDuration(d => d + 1);
      }, 1000);
      
    } catch (err) {
      setError(err.message || 'Microphone access denied');
    }
  }, []);
  
  const stopRecording = useCallback(() => {
    mediaRecorderRef.current?.stop();
    setIsRecording(false);
    clearInterval(timerRef.current);
  }, []);
  
  const clearRecording = useCallback(() => {
    setAudioBlob(null);
    setDuration(0);
  }, []);
  
  return {
    isRecording,
    audioBlob,
    duration,
    error,
    startRecording,
    stopRecording,
    clearRecording,
  };
}
```

**Deliverables**:
- [ ] `frontend/capture/src/hooks/useOnlineStatus.js` — Comprehensive connectivity tracking (browser + server health)
- [ ] `frontend/capture/src/hooks/usePendingCaptures.js` — Queue status
- [ ] `frontend/capture/src/hooks/useMediaRecorder.js` — Audio recording with format detection
- [ ] `frontend/capture/src/hooks/index.js` — Barrel export for capture hooks

**Estimated Time**: 6 hours

---

### Phase 10B: Capture UI Components (Days 4-8)

Build the main capture interface with four capture types.

#### Task 10B.1: Main Capture Screen

**Purpose**: Landing screen with large, accessible capture buttons.

**File**: `frontend/capture/src/pages/MobileCapture.jsx`

```jsx
import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useOnlineStatus } from '../hooks/useOnlineStatus';
import { usePendingCaptures } from '../hooks/usePendingCaptures';
import { CaptureButton } from '../components/CaptureButton';
import { RecentCaptures } from '../components/RecentCaptures';
import { OfflineBanner } from '../components/OfflineBanner';
import { PhotoCapture } from '../components/PhotoCapture';
import { VoiceCapture } from '../components/VoiceCapture';
import { TextCapture } from '../components/TextCapture';
import { UrlCapture } from '../components/UrlCapture';

export function MobileCapture() {
  // Comprehensive online status with server reachability
  const { 
    isOnline,           // Combined: browser online AND server reachable
    isBrowserOnline, 
    isServerReachable,
    isChecking,
    checkNow 
  } = useOnlineStatus();
  
  const { pendingCount } = usePendingCaptures();
  const [activeCapture, setActiveCapture] = useState(null);
  
  const captureTypes = [
    {
      id: 'photo',
      icon: '📷',
      label: 'Photo',
      sublabel: 'Book page, whiteboard',
      component: PhotoCapture,
    },
    {
      id: 'voice',
      icon: '🎤',
      label: 'Voice',
      sublabel: 'Speak your idea',
      component: VoiceCapture,
    },
    {
      id: 'text',
      icon: '✏️',
      label: 'Note',
      sublabel: 'Quick text',
      component: TextCapture,
    },
    {
      id: 'url',
      icon: '🔗',
      label: 'URL',
      sublabel: 'Save a link',
      component: UrlCapture,
    },
  ];
  
  const ActiveComponent = captureTypes.find(t => t.id === activeCapture)?.component;
  
  // Show banner if offline OR if server is unreachable
  const showOfflineBanner = !isBrowserOnline || !isServerReachable;
  
  return (
    <div className="capture-screen">
      {/* Offline/Server Status Banner */}
      <AnimatePresence>
        {showOfflineBanner && (
          <OfflineBanner 
            isBrowserOnline={isBrowserOnline}
            isServerReachable={isServerReachable}
            pendingCount={pendingCount}
            onRetry={checkNow}
          />
        )}
      </AnimatePresence>
      
      {/* Header */}
      <header className="capture-header">
        <h1 className="capture-title">Quick Capture</h1>
        {pendingCount > 0 && isOnline && (
          <span className="sync-indicator">
            {isChecking ? 'Checking...' : `Syncing ${pendingCount}...`}
          </span>
        )}
      </header>
      
      {/* Capture Buttons Grid */}
      <main className="capture-buttons">
        {captureTypes.map((type, index) => (
          <motion.div
            key={type.id}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.1 }}
          >
            <CaptureButton
              icon={type.icon}
              label={type.label}
              sublabel={type.sublabel}
              onClick={() => setActiveCapture(type.id)}
            />
          </motion.div>
        ))}
      </main>
      
      {/* Recent Captures */}
      <section className="recent-section">
        <h2 className="section-title">Recent</h2>
        <RecentCaptures limit={5} />
      </section>
      
      {/* Capture Modals */}
      <AnimatePresence>
        {ActiveComponent && (
          <ActiveComponent 
            onClose={() => setActiveCapture(null)} 
          />
        )}
      </AnimatePresence>
    </div>
  );
}

export default MobileCapture;
```

**Deliverables**:
- [ ] `frontend/capture/src/pages/MobileCapture.jsx` — Main capture screen
- [ ] `frontend/capture/src/App.jsx` — Capture app with routes

**Estimated Time**: 4 hours

---

#### Task 10B.2: Capture Button Component

**Purpose**: Large, accessible touch targets for capture types.

**File**: `frontend/capture/src/components/CaptureButton.jsx`

```jsx
import { motion } from 'framer-motion';
import clsx from 'clsx';

export function CaptureButton({ icon, label, sublabel, onClick, disabled }) {
  return (
    <motion.button
      whileHover={{ scale: 1.02 }}
      whileTap={{ scale: 0.98 }}
      className={clsx(
        'capture-button',
        disabled && 'capture-button--disabled'
      )}
      onClick={onClick}
      disabled={disabled}
    >
      <span className="capture-button__icon">{icon}</span>
      <span className="capture-button__label">{label}</span>
      <span className="capture-button__sublabel">{sublabel}</span>
    </motion.button>
  );
}
```

**Deliverables**:
- [ ] `frontend/capture/src/components/CaptureButton.jsx`

**Estimated Time**: 1 hour

---

#### Task 10B.3: Photo Capture Component

**Purpose**: Camera capture for book pages, whiteboards, and general photos.

**File**: `frontend/capture/src/components/PhotoCapture.jsx`

```jsx
import { useRef, useState } from 'react';
import { motion } from 'framer-motion';
import { captureApi } from '../api/capture';
import { useToast } from '../hooks/useToast';
import { CaptureModal } from './CaptureModal';

const CAPTURE_TYPES = [
  { id: 'book_page', icon: '📖', label: 'Book Page' },
  { id: 'whiteboard', icon: '🖼️', label: 'Whiteboard' },
  { id: 'general', icon: '📝', label: 'General' },
];

export function PhotoCapture({ onClose }) {
  const [captureType, setCaptureType] = useState('book_page');
  const [preview, setPreview] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const inputRef = useRef(null);
  const { showToast } = useToast();
  
  const handleFileSelect = (event) => {
    const file = event.target.files[0];
    if (file) {
      // Validate file
      if (!file.type.startsWith('image/')) {
        showToast('Please select an image file', 'error');
        return;
      }
      
      // Check size (max 10MB)
      if (file.size > 10 * 1024 * 1024) {
        showToast('Image must be under 10MB', 'error');
        return;
      }
      
      setPreview({
        url: URL.createObjectURL(file),
        file: file,
      });
    }
  };
  
  const handleSubmit = async () => {
    if (!preview?.file) return;
    
    setIsSubmitting(true);
    
    try {
      const result = await captureApi.photo(preview.file, captureType);
      
      if (result.status === 'queued') {
        showToast('Saved offline. Will sync when connected.', 'info');
      } else {
        showToast('Captured! Processing...', 'success');
      }
      
      // Clean up preview URL
      URL.revokeObjectURL(preview.url);
      onClose();
      
    } catch (error) {
      showToast(error.message || 'Capture failed', 'error');
    } finally {
      setIsSubmitting(false);
    }
  };
  
  const handleRetake = () => {
    if (preview?.url) {
      URL.revokeObjectURL(preview.url);
    }
    setPreview(null);
    inputRef.current.value = '';
  };
  
  return (
    <CaptureModal title="Photo Capture" onClose={onClose}>
      {/* Type Selector */}
      <div className="type-selector">
        {CAPTURE_TYPES.map((type) => (
          <button
            key={type.id}
            className={`type-button ${captureType === type.id ? 'type-button--active' : ''}`}
            onClick={() => setCaptureType(type.id)}
          >
            <span className="type-button__icon">{type.icon}</span>
            <span className="type-button__label">{type.label}</span>
          </button>
        ))}
      </div>
      
      {/* Camera Input / Preview */}
      <div className="photo-capture-area">
        {preview ? (
          <div className="photo-preview">
            <img src={preview.url} alt="Capture preview" />
            <button 
              className="btn-retake"
              onClick={handleRetake}
            >
              Retake
            </button>
          </div>
        ) : (
          <label className="camera-input">
            <input
              ref={inputRef}
              type="file"
              accept="image/*"
              capture="environment"
              onChange={handleFileSelect}
            />
            <span className="camera-input__icon">📷</span>
            <span className="camera-input__text">Tap to capture</span>
          </label>
        )}
      </div>
      
      {/* Submit Button */}
      {preview && (
        <motion.button
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="btn-submit"
          onClick={handleSubmit}
          disabled={isSubmitting}
        >
          {isSubmitting ? 'Processing...' : 'Save Capture'}
        </motion.button>
      )}
    </CaptureModal>
  );
}
```

**Deliverables**:
- [ ] `frontend/capture/src/components/PhotoCapture.jsx`

**Estimated Time**: 4 hours

---

#### Task 10B.4: Voice Capture Component

**Purpose**: Voice memo recording with cross-browser MediaRecorder support.

**File**: `frontend/capture/src/components/VoiceCapture.jsx`

```jsx
import { useState } from 'react';
import { motion } from 'framer-motion';
import { useMediaRecorder } from '../hooks/useMediaRecorder';
import { captureApi } from '../api/capture';
import { useToast } from '../hooks/useToast';
import { CaptureModal } from './CaptureModal';

export function VoiceCapture({ onClose }) {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const { showToast } = useToast();
  
  const {
    isRecording,
    audioBlob,
    duration,
    error,
    startRecording,
    stopRecording,
    clearRecording,
  } = useMediaRecorder();
  
  const formatDuration = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };
  
  const handleSubmit = async () => {
    if (!audioBlob) return;
    
    setIsSubmitting(true);
    
    try {
      const result = await captureApi.voice(audioBlob);
      
      if (result.status === 'queued') {
        showToast('Saved offline. Will sync when connected.', 'info');
      } else {
        showToast('Voice memo saved!', 'success');
      }
      
      onClose();
      
    } catch (error) {
      showToast(error.message || 'Capture failed', 'error');
    } finally {
      setIsSubmitting(false);
    }
  };
  
  return (
    <CaptureModal title="Voice Memo" onClose={onClose}>
      {/* Error Display */}
      {error && (
        <div className="error-banner">
          <span>⚠️</span>
          <span>{error}</span>
        </div>
      )}
      
      {/* Recording Indicator */}
      <div className="recording-area">
        {isRecording ? (
          <>
            <motion.div
              className="pulse-ring"
              animate={{ scale: [1, 1.2, 1] }}
              transition={{ repeat: Infinity, duration: 1 }}
            />
            <span className="duration">{formatDuration(duration)}</span>
            <span className="recording-label">Recording...</span>
          </>
        ) : audioBlob ? (
          <div className="playback-area">
            <audio 
              src={URL.createObjectURL(audioBlob)} 
              controls 
              className="audio-player"
            />
            <span className="duration-label">
              {formatDuration(duration)} recorded
            </span>
          </div>
        ) : (
          <span className="instruction">Tap to start recording</span>
        )}
      </div>
      
      {/* Record Button */}
      <button
        className={`record-button ${isRecording ? 'record-button--recording' : ''}`}
        onClick={isRecording ? stopRecording : startRecording}
        disabled={error}
      >
        {isRecording ? '⏹️ Stop' : '🎤 Record'}
      </button>
      
      {/* Action Buttons */}
      {audioBlob && !isRecording && (
        <div className="action-buttons">
          <button 
            className="btn-discard"
            onClick={clearRecording}
          >
            Discard
          </button>
          <button 
            className="btn-submit"
            onClick={handleSubmit}
            disabled={isSubmitting}
          >
            {isSubmitting ? 'Saving...' : 'Save'}
          </button>
        </div>
      )}
    </CaptureModal>
  );
}
```

**Deliverables**:
- [ ] `frontend/capture/src/components/VoiceCapture.jsx`

**Estimated Time**: 4 hours

---

#### Task 10B.5: Text Capture Component

**Purpose**: Quick text notes with minimal friction.

**File**: `frontend/capture/src/components/TextCapture.jsx`

```jsx
import { useState, useRef, useEffect } from 'react';
import { captureApi } from '../api/capture';
import { useToast } from '../hooks/useToast';
import { CaptureModal } from './CaptureModal';

export function TextCapture({ onClose }) {
  const [text, setText] = useState('');
  const [title, setTitle] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const textareaRef = useRef(null);
  const { showToast } = useToast();
  
  // Auto-focus on mount
  useEffect(() => {
    textareaRef.current?.focus();
  }, []);
  
  const handleSubmit = async () => {
    if (!text.trim()) {
      showToast('Please enter some text', 'error');
      return;
    }
    
    setIsSubmitting(true);
    
    try {
      const result = await captureApi.text(text, title || undefined);
      
      if (result.status === 'queued') {
        showToast('Saved offline. Will sync when connected.', 'info');
      } else {
        showToast('Note captured!', 'success');
      }
      
      onClose();
      
    } catch (error) {
      showToast(error.message || 'Capture failed', 'error');
    } finally {
      setIsSubmitting(false);
    }
  };
  
  // Submit on Cmd/Ctrl + Enter
  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
      e.preventDefault();
      handleSubmit();
    }
  };
  
  return (
    <CaptureModal title="Quick Note" onClose={onClose}>
      {/* Optional Title */}
      <input
        type="text"
        className="title-input"
        placeholder="Title (optional)"
        value={title}
        onChange={(e) => setTitle(e.target.value)}
      />
      
      {/* Text Area */}
      <textarea
        ref={textareaRef}
        className="text-input"
        placeholder="Capture your thought..."
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={handleKeyDown}
        rows={6}
      />
      
      {/* Character Count */}
      <div className="char-count">
        {text.length} characters
        <span className="hint"> • ⌘Enter to save</span>
      </div>
      
      {/* Submit Button */}
      <button
        className="btn-submit"
        onClick={handleSubmit}
        disabled={!text.trim() || isSubmitting}
      >
        {isSubmitting ? 'Saving...' : 'Save Note'}
      </button>
    </CaptureModal>
  );
}
```

**Deliverables**:
- [ ] `frontend/capture/src/components/TextCapture.jsx`

**Estimated Time**: 2 hours

---

#### Task 10B.6: URL Capture Component

**Purpose**: Save links for later processing.

**File**: `frontend/capture/src/components/UrlCapture.jsx`

```jsx
import { useState, useRef, useEffect } from 'react';
import { captureApi } from '../api/capture';
import { useToast } from '../hooks/useToast';
import { CaptureModal } from './CaptureModal';

// Simple URL validation
const isValidUrl = (string) => {
  try {
    const url = new URL(string);
    return url.protocol === 'http:' || url.protocol === 'https:';
  } catch {
    return false;
  }
};

export function UrlCapture({ onClose }) {
  const [url, setUrl] = useState('');
  const [notes, setNotes] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [urlError, setUrlError] = useState(null);
  const inputRef = useRef(null);
  const { showToast } = useToast();
  
  // Auto-focus and check clipboard
  useEffect(() => {
    inputRef.current?.focus();
    
    // Try to read URL from clipboard
    navigator.clipboard?.readText().then((text) => {
      if (isValidUrl(text)) {
        setUrl(text);
      }
    }).catch(() => {
      // Clipboard access denied - ignore
    });
  }, []);
  
  const handleUrlChange = (e) => {
    const value = e.target.value;
    setUrl(value);
    
    if (value && !isValidUrl(value)) {
      setUrlError('Please enter a valid URL');
    } else {
      setUrlError(null);
    }
  };
  
  const handleSubmit = async () => {
    if (!url.trim() || !isValidUrl(url)) {
      showToast('Please enter a valid URL', 'error');
      return;
    }
    
    setIsSubmitting(true);
    
    try {
      const result = await captureApi.url(url, notes || undefined);
      
      if (result.status === 'queued') {
        showToast('Saved offline. Will sync when connected.', 'info');
      } else {
        showToast('URL saved!', 'success');
      }
      
      onClose();
      
    } catch (error) {
      showToast(error.message || 'Capture failed', 'error');
    } finally {
      setIsSubmitting(false);
    }
  };
  
  return (
    <CaptureModal title="Save URL" onClose={onClose}>
      {/* URL Input */}
      <div className="input-group">
        <input
          ref={inputRef}
          type="url"
          className={`url-input ${urlError ? 'url-input--error' : ''}`}
          placeholder="https://example.com/article"
          value={url}
          onChange={handleUrlChange}
        />
        {urlError && (
          <span className="input-error">{urlError}</span>
        )}
      </div>
      
      {/* Optional Notes */}
      <textarea
        className="notes-input"
        placeholder="Notes (optional) - Why save this?"
        value={notes}
        onChange={(e) => setNotes(e.target.value)}
        rows={3}
      />
      
      {/* Submit Button */}
      <button
        className="btn-submit"
        onClick={handleSubmit}
        disabled={!url.trim() || urlError || isSubmitting}
      >
        {isSubmitting ? 'Saving...' : 'Save URL'}
      </button>
    </CaptureModal>
  );
}
```

**Deliverables**:
- [ ] `frontend/capture/src/components/UrlCapture.jsx`

**Estimated Time**: 2 hours

---

#### Task 10B.7: Supporting Components

**Purpose**: Shared components used across capture modals.

**File**: `frontend/capture/src/components/CaptureModal.jsx`

```jsx
import { motion } from 'framer-motion';

export function CaptureModal({ title, onClose, children }) {
  return (
    <motion.div
      className="capture-modal"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
    >
      <motion.div
        className="capture-modal__content"
        initial={{ y: '100%' }}
        animate={{ y: 0 }}
        exit={{ y: '100%' }}
        transition={{ type: 'spring', damping: 25, stiffness: 300 }}
      >
        <header className="capture-modal__header">
          <button 
            className="btn-close" 
            onClick={onClose}
            aria-label="Close"
          >
            ✕
          </button>
          <h2 className="capture-modal__title">{title}</h2>
        </header>
        
        <main className="capture-modal__body">
          {children}
        </main>
      </motion.div>
    </motion.div>
  );
}
```

**File**: `frontend/capture/src/components/OfflineBanner.jsx`

```jsx
import { motion } from 'framer-motion';

/**
 * Banner showing offline/connectivity status.
 * 
 * Shows different messages based on:
 * - Browser offline (no network)
 * - Server unreachable (network ok, but API down)
 * - Pending captures waiting to sync
 */
export function OfflineBanner({ 
  isBrowserOnline, 
  isServerReachable, 
  pendingCount,
  onRetry 
}) {
  // Determine banner variant
  const variant = !isBrowserOnline 
    ? 'offline' 
    : !isServerReachable 
      ? 'server-down' 
      : 'syncing';
  
  const config = {
    offline: {
      icon: '📴',
      message: "You're offline",
      color: 'var(--color-accent-warning)',
    },
    'server-down': {
      icon: '🔌',
      message: 'Server unavailable',
      color: 'var(--color-accent-danger)',
    },
    syncing: {
      icon: '🔄',
      message: 'Syncing...',
      color: 'var(--color-accent-primary)',
    },
  };
  
  const { icon, message, color } = config[variant];
  
  return (
    <motion.div
      className="offline-banner"
      style={{ backgroundColor: color }}
      initial={{ height: 0, opacity: 0 }}
      animate={{ height: 'auto', opacity: 1 }}
      exit={{ height: 0, opacity: 0 }}
    >
      <span className="offline-banner__icon">{icon}</span>
      <span className="offline-banner__text">
        {message}
        {pendingCount > 0 && (
          <> • {pendingCount} capture{pendingCount > 1 ? 's' : ''} waiting</>
        )}
      </span>
      
      {/* Retry button when server is down but browser is online */}
      {isBrowserOnline && !isServerReachable && onRetry && (
        <button 
          className="offline-banner__retry"
          onClick={onRetry}
          aria-label="Retry connection"
        >
          Retry
        </button>
      )}
    </motion.div>
  );
}
```

**File**: `frontend/capture/src/components/RecentCaptures.jsx`

```jsx
import { useQuery } from '@tanstack/react-query';
import { captureApi } from '../api/capture';
import { formatDistanceToNow } from 'date-fns';

export function RecentCaptures({ limit = 5 }) {
  const { data: captures, isLoading } = useQuery({
    queryKey: ['recentCaptures', limit],
    queryFn: () => captureApi.getRecent(limit),
    staleTime: 30000, // 30 seconds
  });
  
  if (isLoading) {
    return <div className="recent-captures--loading">Loading...</div>;
  }
  
  if (!captures?.length) {
    return (
      <div className="recent-captures--empty">
        <span className="empty-icon">📭</span>
        <span>No captures yet</span>
      </div>
    );
  }
  
  const typeIcons = {
    photo: '📷',
    voice: '🎤',
    text: '✏️',
    url: '🔗',
  };
  
  return (
    <ul className="recent-captures">
      {captures.map((capture) => (
        <li key={capture.id} className="recent-capture">
          <span className="recent-capture__icon">
            {typeIcons[capture.type] || '📄'}
          </span>
          <div className="recent-capture__info">
            <span className="recent-capture__title">
              {capture.title || capture.type}
            </span>
            <span className="recent-capture__time">
              {formatDistanceToNow(new Date(capture.created_at), { addSuffix: true })}
            </span>
          </div>
          <span className={`recent-capture__status recent-capture__status--${capture.status}`}>
            {capture.status === 'processing' ? '⏳' : '✓'}
          </span>
        </li>
      ))}
    </ul>
  );
}
```

**Deliverables**:
- [ ] `frontend/capture/src/components/CaptureModal.jsx` — Modal wrapper
- [ ] `frontend/capture/src/components/OfflineBanner.jsx` — Offline/server status indicator
- [ ] `frontend/capture/src/components/RecentCaptures.jsx` — Recent captures list
- [ ] `frontend/capture/src/components/index.js` — Barrel export

**Estimated Time**: 4 hours

---

### Phase 10C: API Client & Share Target (Days 9-11)

#### Task 10C.1: Capture API Client

**Purpose**: API client with offline-aware responses.

**File**: `frontend/capture/src/api/capture.js`

```javascript
import { apiClient } from './client';

/**
 * Capture API client.
 * 
 * All capture methods handle both online and offline scenarios.
 * When offline, the service worker queues requests and returns
 * { status: 'queued' } responses.
 */
export const captureApi = {
  /**
   * Capture a photo (book page, whiteboard, etc.)
   * @param {File} file - Image file
   * @param {string} captureType - 'book_page' | 'whiteboard' | 'general'
   */
  photo: async (file, captureType = 'general') => {
    const formData = new FormData();
    formData.append('image', file);
    formData.append('capture_type', captureType);
    
    const response = await apiClient.post('/api/capture/photo', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  },
  
  /**
   * Capture a voice memo
   * @param {Blob} audioBlob - Audio recording
   */
  voice: async (audioBlob) => {
    const formData = new FormData();
    
    // Detect format from blob type
    const extension = audioBlob.type.includes('webm') ? 'webm' : 'm4a';
    formData.append('audio', audioBlob, `recording.${extension}`);
    
    const response = await apiClient.post('/api/capture/voice', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  },
  
  /**
   * Capture a text note
   * @param {string} text - Note content
   * @param {string} title - Optional title
   */
  text: async (text, title) => {
    const formData = new FormData();
    formData.append('text', text);
    if (title) formData.append('title', title);
    
    const response = await apiClient.post('/api/capture/text', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  },
  
  /**
   * Capture a URL
   * @param {string} url - URL to save
   * @param {string} notes - Optional notes
   */
  url: async (url, notes) => {
    const formData = new FormData();
    formData.append('url', url);
    if (notes) formData.append('notes', notes);
    
    const response = await apiClient.post('/api/capture/url', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  },
  
  /**
   * Get recent captures
   * @param {number} limit - Max results
   */
  getRecent: async (limit = 10) => {
    const response = await apiClient.get('/api/capture/recent', {
      params: { limit },
    });
    return response.data;
  },
};
```

**Deliverables**:
- [ ] `frontend/capture/src/api/capture.js` — Capture API client

**Estimated Time**: 2 hours

---

#### Task 10C.2: Share Target Handler

**Purpose**: Handle content shared from other apps.

**File**: `frontend/capture/src/pages/ShareTarget.jsx`

```jsx
import { useEffect, useState } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { captureApi } from '../api/capture';

/**
 * Share Target handler page.
 * 
 * Receives content shared from other apps via the Web Share Target API.
 * Processes the shared data and redirects to the main capture screen.
 */
export function ShareTarget() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [status, setStatus] = useState('processing');
  const [message, setMessage] = useState('Saving...');
  
  useEffect(() => {
    handleSharedContent();
  }, []);
  
  const handleSharedContent = async () => {
    try {
      const title = searchParams.get('title');
      const text = searchParams.get('text');
      const url = searchParams.get('url');
      
      // Determine what was shared
      if (url) {
        // Shared URL (most common from browsers)
        setMessage('Saving link...');
        await captureApi.url(url, text || title);
        setStatus('success');
        setMessage('Link saved!');
        
      } else if (text) {
        // Shared text
        setMessage('Saving note...');
        
        // Check if text contains a URL
        const urlMatch = text.match(/https?:\/\/[^\s]+/);
        if (urlMatch) {
          await captureApi.url(urlMatch[0], text);
        } else {
          await captureApi.text(text, title);
        }
        
        setStatus('success');
        setMessage('Saved!');
        
      } else {
        // Nothing useful shared
        setStatus('error');
        setMessage('Nothing to save');
      }
      
    } catch (error) {
      if (error.response?.data?.status === 'queued') {
        setStatus('queued');
        setMessage('Saved offline');
      } else {
        setStatus('error');
        setMessage(error.message || 'Failed to save');
      }
    }
    
    // Redirect after delay
    setTimeout(() => {
      navigate('/capture', { replace: true });
    }, 1500);
  };
  
  const statusConfig = {
    processing: { icon: '⏳', color: 'text-slate-400' },
    success: { icon: '✓', color: 'text-emerald-400' },
    queued: { icon: '📴', color: 'text-amber-400' },
    error: { icon: '✗', color: 'text-red-400' },
  };
  
  const config = statusConfig[status];
  
  return (
    <div className="share-target-screen">
      <motion.div
        className="share-target-status"
        initial={{ scale: 0.9, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
      >
        <motion.span
          className={`status-icon ${config.color}`}
          animate={status === 'processing' ? { rotate: 360 } : {}}
          transition={status === 'processing' ? { repeat: Infinity, duration: 1 } : {}}
        >
          {config.icon}
        </motion.span>
        <span className="status-message">{message}</span>
      </motion.div>
    </div>
  );
}

export default ShareTarget;
```

**Routes**: Defined in `frontend/capture/src/App.jsx`

```jsx
// Routes in capture App.jsx
<Routes>
  <Route path="/" element={<MobileCapture />} />
  <Route path="/share" element={<ShareTarget />} />
  <Route path="/share-files" element={<ShareTargetFiles />} />
</Routes>
```

**Deliverables**:
- [ ] `frontend/capture/src/pages/ShareTarget.jsx` — Share target handler

**Estimated Time**: 3 hours

---

#### Task 10C.3: File Share Handler

**Purpose**: Handle files (images, audio) shared from other apps.

The Share Target API can receive files via POST multipart/form-data. This requires a special handler since React Router doesn't natively handle POST requests.

**File**: `frontend/capture/src/pages/ShareTargetFiles.jsx`

```jsx
import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { captureApi } from '../api/capture';

/**
 * File share target handler.
 * 
 * Handles POST requests from the Share Target API with file data.
 * The service worker intercepts the POST and stores files in IndexedDB,
 * then this component retrieves and processes them.
 */
export function ShareTargetFiles() {
  const navigate = useNavigate();
  const [status, setStatus] = useState('processing');
  const [message, setMessage] = useState('Processing shared files...');
  
  useEffect(() => {
    handleSharedFiles();
  }, []);
  
  const handleSharedFiles = async () => {
    try {
      // Get files from service worker
      const response = await fetch('/api/share-target/files');
      
      if (!response.ok) {
        throw new Error('No files found');
      }
      
      const data = await response.json();
      const { files, text, title } = data;
      
      if (files?.length) {
        for (const fileData of files) {
          const file = new File([fileData.data], fileData.name, { 
            type: fileData.type 
          });
          
          if (fileData.type.startsWith('image/')) {
            await captureApi.photo(file, 'general');
          } else if (fileData.type.startsWith('audio/')) {
            await captureApi.voice(file);
          }
        }
        
        setStatus('success');
        setMessage(`${files.length} file(s) saved!`);
      } else {
        throw new Error('No supported files');
      }
      
    } catch (error) {
      setStatus('error');
      setMessage(error.message);
    }
    
    setTimeout(() => {
      navigate('/capture', { replace: true });
    }, 1500);
  };
  
  // ... similar UI to ShareTarget
}
```

**Service Worker Addition**: Handle file shares

```javascript
// Add to sw.js

// Handle share target POST with files
self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);
  
  if (url.pathname === '/capture/share' && event.request.method === 'POST') {
    event.respondWith(handleShareTargetPost(event.request));
  }
  
  // ... rest of fetch handler
});

async function handleShareTargetPost(request) {
  const formData = await request.formData();
  
  // Store in IndexedDB for later retrieval
  const db = await openShareDB();
  const shareData = {
    id: 'current',
    timestamp: Date.now(),
    files: [],
    text: formData.get('text'),
    title: formData.get('title'),
    url: formData.get('url'),
  };
  
  // Process files
  const mediaFiles = formData.getAll('media');
  for (const file of mediaFiles) {
    if (file instanceof File) {
      shareData.files.push({
        name: file.name,
        type: file.type,
        data: await file.arrayBuffer(),
      });
    }
  }
  
  const tx = db.transaction('shares', 'readwrite');
  await tx.objectStore('shares').put(shareData);
  
  // Redirect to handler page
  return Response.redirect('/capture/share-files', 303);
}
```

**Deliverables**:
- [ ] `frontend/capture/src/pages/ShareTargetFiles.jsx` — File share handler
- [ ] Update `frontend/capture/public/sw.js` with file share handling

**Estimated Time**: 4 hours

---

### Phase 10D: Mobile-Optimized Styles (Days 12-14)

#### Task 10D.1: Mobile CSS Foundation

**Purpose**: Create mobile-optimized styles with safe areas, touch targets, and dark theme.

**File**: `frontend/capture/src/styles/capture.css`

```css
/* Mobile Capture Styles */

/* ============================================
   CSS Variables (extend from design system)
   ============================================ */
:root {
  /* Mobile-specific */
  --touch-target-min: 44px;
  --touch-target-large: 80px;
  --safe-area-top: env(safe-area-inset-top, 0px);
  --safe-area-bottom: env(safe-area-inset-bottom, 0px);
  --safe-area-left: env(safe-area-inset-left, 0px);
  --safe-area-right: env(safe-area-inset-right, 0px);
}

/* ============================================
   Capture Screen
   ============================================ */
.capture-screen {
  min-height: 100vh;
  min-height: 100dvh; /* Dynamic viewport height (iOS Safari) */
  background: var(--color-bg-primary);
  color: var(--color-text-primary);
  padding-top: var(--safe-area-top);
  padding-bottom: var(--safe-area-bottom);
  padding-left: var(--safe-area-left);
  padding-right: var(--safe-area-right);
  display: flex;
  flex-direction: column;
}

.capture-header {
  padding: var(--space-4) var(--space-4);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.capture-title {
  font-family: var(--font-heading);
  font-size: 1.5rem;
  font-weight: 600;
  color: var(--color-text-primary);
}

.sync-indicator {
  font-size: 0.875rem;
  color: var(--color-accent-primary);
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

/* ============================================
   Capture Buttons Grid
   ============================================ */
.capture-buttons {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--space-4);
  padding: var(--space-4);
  flex: 1;
  align-content: start;
}

.capture-button {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--space-6) var(--space-4);
  background: var(--color-bg-secondary);
  border-radius: var(--radius-xl);
  border: 1px solid var(--color-bg-tertiary);
  
  /* Large touch target */
  min-height: 120px;
  
  /* Remove default button styles */
  -webkit-appearance: none;
  appearance: none;
  
  /* Prevent text selection */
  -webkit-user-select: none;
  user-select: none;
  
  /* Remove tap highlight */
  -webkit-tap-highlight-color: transparent;
  
  /* Touch feedback via :active */
  transition: transform 0.1s ease, background 0.15s ease;
}

.capture-button:active {
  transform: scale(0.98);
  background: var(--color-bg-tertiary);
}

.capture-button--disabled {
  opacity: 0.5;
  pointer-events: none;
}

.capture-button__icon {
  font-size: 2.5rem;
  margin-bottom: var(--space-2);
}

.capture-button__label {
  font-family: var(--font-heading);
  font-size: 1.125rem;
  font-weight: 600;
  color: var(--color-text-primary);
}

.capture-button__sublabel {
  font-size: 0.875rem;
  color: var(--color-text-muted);
  margin-top: var(--space-1);
}

/* ============================================
   Capture Modal
   ============================================ */
.capture-modal {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.8);
  z-index: 100;
  display: flex;
  flex-direction: column;
  justify-content: flex-end;
}

.capture-modal__content {
  background: var(--color-bg-primary);
  border-radius: var(--radius-2xl) var(--radius-2xl) 0 0;
  max-height: 90vh;
  overflow-y: auto;
  padding-bottom: var(--safe-area-bottom);
}

.capture-modal__header {
  display: flex;
  align-items: center;
  padding: var(--space-4);
  border-bottom: 1px solid var(--color-bg-tertiary);
  position: sticky;
  top: 0;
  background: var(--color-bg-primary);
}

.capture-modal__title {
  flex: 1;
  text-align: center;
  font-family: var(--font-heading);
  font-size: 1.125rem;
  font-weight: 600;
}

.capture-modal__body {
  padding: var(--space-4);
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.btn-close {
  width: var(--touch-target-min);
  height: var(--touch-target-min);
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: none;
  color: var(--color-text-secondary);
  font-size: 1.25rem;
  -webkit-tap-highlight-color: transparent;
}

/* ============================================
   Type Selector
   ============================================ */
.type-selector {
  display: flex;
  gap: var(--space-2);
}

.type-button {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: var(--space-3);
  background: var(--color-bg-secondary);
  border: 2px solid transparent;
  border-radius: var(--radius-lg);
  -webkit-tap-highlight-color: transparent;
  transition: border-color 0.15s ease;
}

.type-button--active {
  border-color: var(--color-accent-primary);
  background: rgba(99, 102, 241, 0.1);
}

.type-button__icon {
  font-size: 1.5rem;
  margin-bottom: var(--space-1);
}

.type-button__label {
  font-size: 0.75rem;
  color: var(--color-text-secondary);
}

/* ============================================
   Photo Capture
   ============================================ */
.photo-capture-area {
  aspect-ratio: 4 / 3;
  background: var(--color-bg-secondary);
  border-radius: var(--radius-lg);
  overflow: hidden;
}

.camera-input {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  cursor: pointer;
}

.camera-input input {
  display: none;
}

.camera-input__icon {
  font-size: 4rem;
  margin-bottom: var(--space-2);
}

.camera-input__text {
  color: var(--color-text-muted);
}

.photo-preview {
  position: relative;
  width: 100%;
  height: 100%;
}

.photo-preview img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.btn-retake {
  position: absolute;
  bottom: var(--space-2);
  right: var(--space-2);
  padding: var(--space-2) var(--space-4);
  background: rgba(0, 0, 0, 0.7);
  color: white;
  border: none;
  border-radius: var(--radius-md);
  font-size: 0.875rem;
}

/* ============================================
   Voice Capture
   ============================================ */
.recording-area {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 150px;
  gap: var(--space-3);
}

.pulse-ring {
  width: 80px;
  height: 80px;
  border-radius: 50%;
  background: var(--color-accent-danger);
  opacity: 0.3;
}

.duration {
  font-family: var(--font-mono);
  font-size: 2rem;
  font-weight: 500;
}

.recording-label {
  color: var(--color-accent-danger);
  font-size: 0.875rem;
}

.instruction {
  color: var(--color-text-muted);
}

.record-button {
  width: var(--touch-target-large);
  height: var(--touch-target-large);
  border-radius: 50%;
  background: var(--color-accent-danger);
  border: 4px solid white;
  font-size: 1.5rem;
  display: flex;
  align-items: center;
  justify-content: center;
  -webkit-tap-highlight-color: transparent;
  transition: transform 0.1s ease;
}

.record-button:active {
  transform: scale(0.95);
}

.record-button--recording {
  animation: pulse 1s infinite;
}

@keyframes pulse {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.05); }
}

.playback-area {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-2);
}

.audio-player {
  width: 100%;
  max-width: 280px;
}

.duration-label {
  font-size: 0.875rem;
  color: var(--color-text-muted);
}

/* ============================================
   Text/URL Capture
   ============================================ */
.title-input,
.url-input,
.notes-input {
  width: 100%;
  padding: var(--space-3) var(--space-4);
  background: var(--color-bg-secondary);
  border: 1px solid var(--color-bg-tertiary);
  border-radius: var(--radius-lg);
  color: var(--color-text-primary);
  font-size: 1rem;
  -webkit-appearance: none;
}

.title-input:focus,
.url-input:focus,
.notes-input:focus,
.text-input:focus {
  outline: none;
  border-color: var(--color-accent-primary);
}

.url-input--error {
  border-color: var(--color-accent-danger);
}

.text-input {
  width: 100%;
  min-height: 150px;
  padding: var(--space-3) var(--space-4);
  background: var(--color-bg-secondary);
  border: 1px solid var(--color-bg-tertiary);
  border-radius: var(--radius-lg);
  color: var(--color-text-primary);
  font-size: 1rem;
  resize: vertical;
  -webkit-appearance: none;
}

.input-error {
  font-size: 0.75rem;
  color: var(--color-accent-danger);
  margin-top: var(--space-1);
}

.char-count {
  font-size: 0.75rem;
  color: var(--color-text-muted);
  text-align: right;
}

.hint {
  color: var(--color-text-muted);
}

/* ============================================
   Action Buttons
   ============================================ */
.btn-submit {
  width: 100%;
  padding: var(--space-4);
  background: var(--gradient-accent);
  color: white;
  border: none;
  border-radius: var(--radius-lg);
  font-family: var(--font-heading);
  font-size: 1rem;
  font-weight: 600;
  min-height: var(--touch-target-min);
  -webkit-tap-highlight-color: transparent;
  transition: opacity 0.15s ease;
}

.btn-submit:disabled {
  opacity: 0.5;
}

.btn-submit:active:not(:disabled) {
  opacity: 0.9;
}

.action-buttons {
  display: flex;
  gap: var(--space-3);
}

.btn-discard {
  flex: 1;
  padding: var(--space-4);
  background: var(--color-bg-tertiary);
  color: var(--color-text-secondary);
  border: none;
  border-radius: var(--radius-lg);
  font-size: 1rem;
  min-height: var(--touch-target-min);
}

/* ============================================
   Offline Banner
   ============================================ */
.offline-banner {
  background: var(--color-accent-warning);
  color: #000;
  padding: var(--space-2) var(--space-4);
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  font-size: 0.875rem;
}

.offline-banner__icon {
  font-size: 1rem;
}

.offline-banner__retry {
  padding: var(--space-1) var(--space-3);
  background: rgba(255, 255, 255, 0.2);
  border: 1px solid rgba(255, 255, 255, 0.3);
  border-radius: var(--radius-md);
  color: inherit;
  font-size: 0.75rem;
  font-weight: 600;
  margin-left: auto;
  -webkit-tap-highlight-color: transparent;
}

.offline-banner__retry:active {
  background: rgba(255, 255, 255, 0.3);
}

/* ============================================
   Recent Captures
   ============================================ */
.recent-section {
  padding: var(--space-4);
  border-top: 1px solid var(--color-bg-tertiary);
}

.section-title {
  font-family: var(--font-heading);
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--color-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: var(--space-3);
}

.recent-captures {
  list-style: none;
  padding: 0;
  margin: 0;
}

.recent-capture {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-3) 0;
  border-bottom: 1px solid var(--color-bg-tertiary);
}

.recent-capture:last-child {
  border-bottom: none;
}

.recent-capture__icon {
  font-size: 1.25rem;
}

.recent-capture__info {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.recent-capture__title {
  font-size: 0.875rem;
  color: var(--color-text-primary);
}

.recent-capture__time {
  font-size: 0.75rem;
  color: var(--color-text-muted);
}

.recent-capture__status {
  font-size: 1rem;
}

.recent-capture__status--processing {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.recent-captures--empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-6);
  color: var(--color-text-muted);
}

.empty-icon {
  font-size: 2rem;
}

/* ============================================
   Share Target Screen
   ============================================ */
.share-target-screen {
  min-height: 100vh;
  min-height: 100dvh;
  background: var(--color-bg-primary);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--space-4);
}

.share-target-status {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-4);
}

.status-icon {
  font-size: 3rem;
}

.status-message {
  font-size: 1.125rem;
  color: var(--color-text-primary);
}

/* ============================================
   Error States
   ============================================ */
.error-banner {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-3);
  background: rgba(248, 113, 113, 0.1);
  border: 1px solid var(--color-accent-danger);
  border-radius: var(--radius-lg);
  color: var(--color-accent-danger);
  font-size: 0.875rem;
}
```

**Deliverables**:
- [ ] `frontend/capture/src/styles/capture.css` — Complete mobile capture styles
- [ ] `frontend/capture/src/styles/variables.css` — CSS variables (imports shared tokens)

**Estimated Time**: 6 hours

---

## 4. Backend Additions

### Task 10E.1: Additional Capture Endpoints

**Purpose**: Add missing text and URL capture endpoints.

**File**: `backend/app/routers/capture.py` (additions)

```python
from fastapi import APIRouter, Depends, Form, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from datetime import datetime, timezone

from app.db.base import get_db
from app.db.models import Content
from app.models.content import CaptureResponse
from app.services.queue import queue_processing

router = APIRouter(prefix="/api/capture", tags=["capture"])


@router.post("/text", response_model=CaptureResponse)
async def capture_text(
    text: str = Form(..., min_length=1, max_length=50000),
    title: Optional[str] = Form(None, max_length=500),
    tags: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
) -> CaptureResponse:
    """
    Quick text capture from mobile.
    
    Creates an inbox item with the text content.
    Queues for LLM processing (summarization, tagging).
    """
    # Create content record
    content = Content(
        source_type="capture_text",
        title=title or f"Quick note - {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')}",
        raw_content=text,
        status="pending",
        captured_at=datetime.now(timezone.utc),
        metadata={
            "capture_type": "text",
            "tags": tags.split(",") if tags else [],
        }
    )
    
    db.add(content)
    await db.commit()
    await db.refresh(content)
    
    # Queue for processing
    await queue_processing(content.id, priority="low")
    
    return CaptureResponse(
        id=content.id,
        status="captured",
        message="Text captured and queued for processing",
    )


@router.post("/url", response_model=CaptureResponse)
async def capture_url(
    url: str = Form(...),
    notes: Optional[str] = Form(None, max_length=5000),
    db: AsyncSession = Depends(get_db),
) -> CaptureResponse:
    """
    Save URL for later processing.
    
    Validates URL, creates inbox item, queues for
    web article pipeline (fetch, extract, summarize).
    """
    # Validate URL
    from urllib.parse import urlparse
    parsed = urlparse(url)
    if parsed.scheme not in ('http', 'https'):
        raise HTTPException(400, "Invalid URL: must be http or https")
    
    # Create content record
    content = Content(
        source_type="capture_url",
        title=f"Link: {parsed.netloc}",
        source_url=url,
        raw_content=notes or "",
        status="pending",
        captured_at=datetime.now(timezone.utc),
        metadata={
            "capture_type": "url",
            "notes": notes,
        }
    )
    
    db.add(content)
    await db.commit()
    await db.refresh(content)
    
    # Queue for web article processing
    await queue_processing(content.id, pipeline="web_article", priority="normal")
    
    return CaptureResponse(
        id=content.id,
        status="captured",
        message="URL saved and queued for processing",
    )


@router.get("/recent")
async def get_recent_captures(
    limit: int = 10,
    db: AsyncSession = Depends(get_db),
):
    """Get recent captures for mobile UI."""
    from sqlalchemy import select
    
    query = (
        select(Content)
        .where(Content.source_type.in_(['capture_text', 'capture_url', 'capture_photo', 'capture_voice']))
        .order_by(Content.captured_at.desc())
        .limit(limit)
    )
    
    result = await db.execute(query)
    captures = result.scalars().all()
    
    return [
        {
            "id": c.id,
            "type": c.source_type.replace("capture_", ""),
            "title": c.title,
            "status": c.status,
            "created_at": c.captured_at.isoformat(),
        }
        for c in captures
    ]
```

**Deliverables**:
- [ ] Add `/api/capture/text` endpoint
- [ ] Add `/api/capture/url` endpoint
- [ ] Add `/api/capture/recent` endpoint
- [ ] Unit tests for new endpoints

**Estimated Time**: 4 hours

---

## 5. Timeline Summary

### Phase 10: Mobile Capture PWA (Days 1-14)

| Phase | Days | Tasks | Deliverables | Hours |
|-------|------|-------|--------------|-------|
| 10A | 1-3 | PWA Foundation | Vite config, Manifest, Service Worker, offline hooks | 19 |
| 10B | 4-8 | Capture UI Components | Main screen, 4 capture modals, supporting components | 21 |
| 10C | 9-11 | API Client & Share Target | Capture API, share target handler | 9 |
| 10D | 12-14 | Mobile Styles | Complete mobile CSS | 6 |
| 10E | — | Backend Additions | Text/URL endpoints (can parallel) | 4 |
| **Total** | | | | **59** |

### Gantt View

```text
Days:     1----3----5----7----9----11---13---14
Phase:    [==10A==][======10B======][==10C==][10D]
Backend:  [====10E====] (parallel)
```

---

## 6. Testing Strategy

### 6.1 Unit Tests

| Test File | Coverage |
|-----------|----------|
| `useOnlineStatus.test.js` | Browser online/offline events, server health checks, timeout handling, visibility change triggers |
| `usePendingCaptures.test.js` | Queue count, refresh on sync |
| `useMediaRecorder.test.js` | Recording start/stop, format detection |
| `PhotoCapture.test.jsx` | File selection, type selector, submit |
| `VoiceCapture.test.jsx` | Record flow, playback, submit |
| `OfflineBanner.test.jsx` | Different states (offline, server-down, syncing), retry button |

**Example: `useOnlineStatus.test.js`**

```javascript
import { renderHook, act, waitFor } from '@testing-library/react';
import { useOnlineStatus } from './useOnlineStatus';

// Mock fetch for health checks
global.fetch = jest.fn();

describe('useOnlineStatus', () => {
  beforeEach(() => {
    jest.useFakeTimers();
    fetch.mockClear();
    
    // Default: browser online, server healthy
    Object.defineProperty(navigator, 'onLine', { value: true, writable: true });
    fetch.mockResolvedValue({ ok: true });
  });
  
  afterEach(() => {
    jest.useRealTimers();
  });
  
  it('returns online when browser and server are both available', async () => {
    const { result } = renderHook(() => useOnlineStatus());
    
    await waitFor(() => {
      expect(result.current.isOnline).toBe(true);
      expect(result.current.isBrowserOnline).toBe(true);
      expect(result.current.isServerReachable).toBe(true);
    });
  });
  
  it('returns offline when browser is offline', async () => {
    Object.defineProperty(navigator, 'onLine', { value: false });
    
    const { result } = renderHook(() => useOnlineStatus());
    
    expect(result.current.isOnline).toBe(false);
    expect(result.current.isBrowserOnline).toBe(false);
  });
  
  it('returns offline when server health check fails', async () => {
    fetch.mockRejectedValue(new Error('Network error'));
    
    const { result } = renderHook(() => useOnlineStatus());
    
    await waitFor(() => {
      expect(result.current.isOnline).toBe(false);
      expect(result.current.isBrowserOnline).toBe(true);
      expect(result.current.isServerReachable).toBe(false);
    });
  });
  
  it('handles server returning non-ok status', async () => {
    fetch.mockResolvedValue({ ok: false, status: 503 });
    
    const { result } = renderHook(() => useOnlineStatus());
    
    await waitFor(() => {
      expect(result.current.isServerReachable).toBe(false);
    });
  });
  
  it('performs periodic health checks', async () => {
    const { result } = renderHook(() => useOnlineStatus());
    
    // Initial check
    await waitFor(() => expect(fetch).toHaveBeenCalledTimes(1));
    
    // Fast-forward 30 seconds
    act(() => {
      jest.advanceTimersByTime(30000);
    });
    
    await waitFor(() => expect(fetch).toHaveBeenCalledTimes(2));
  });
  
  it('checks server when visibility changes to visible', async () => {
    const { result } = renderHook(() => useOnlineStatus());
    
    await waitFor(() => expect(fetch).toHaveBeenCalledTimes(1));
    
    // Simulate tab becoming visible
    Object.defineProperty(document, 'visibilityState', { value: 'visible' });
    document.dispatchEvent(new Event('visibilitychange'));
    
    await waitFor(() => expect(fetch).toHaveBeenCalledTimes(2));
  });
  
  it('allows manual retry via checkNow', async () => {
    fetch.mockRejectedValueOnce(new Error('First fail'));
    fetch.mockResolvedValueOnce({ ok: true });
    
    const { result } = renderHook(() => useOnlineStatus());
    
    await waitFor(() => {
      expect(result.current.isServerReachable).toBe(false);
    });
    
    // Manual retry
    await act(async () => {
      await result.current.checkNow();
    });
    
    expect(result.current.isServerReachable).toBe(true);
  });
});
```

### 6.2 Integration Tests (Playwright)

| Test | Scenario |
|------|----------|
| `capture-photo.spec.ts` | Select type, take photo, submit, see confirmation |
| `capture-voice.spec.ts` | Start recording, stop, playback, submit |
| `capture-text.spec.ts` | Enter text, submit with ⌘Enter |
| `capture-offline.spec.ts` | Capture while offline, see queued, sync when online |
| `share-target.spec.ts` | Share URL from "browser", see captured |

### 6.3 Manual Testing Checklist

- [ ] Install PWA on Android Chrome
- [ ] Install PWA on iOS Safari (Add to Home Screen)
- [ ] Photo capture opens camera
- [ ] Voice recording works on both platforms
- [ ] Offline capture queues correctly
- [ ] Background sync uploads when online
- [ ] Share Target appears in system share sheet
- [ ] Safe areas render correctly on notched devices

---

## 7. Success Criteria

### Functional Requirements
- [ ] PWA installable on Android and iOS
- [ ] All 4 capture types functional
- [ ] Offline captures sync automatically
- [ ] Share Target receives URLs and text
- [ ] Recent captures display correctly

### Performance Requirements
- [ ] Time to interactive < 2 seconds
- [ ] Capture to confirmation < 3 seconds (online)
- [ ] Service Worker caches all static assets
- [ ] Works on 3G connection

### Quality Requirements
- [ ] Touch targets >= 44px
- [ ] Safe area insets handled
- [ ] No FOUC on load
- [ ] Lighthouse PWA score >= 90

---

## 8. Risk Assessment

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Safari MediaRecorder limitations | High | Medium | Format detection, fallback to MP4 |
| Background sync unreliable on iOS | Medium | High | Manual sync button, clear queue status |
| Share Target not supported on older iOS | Medium | Medium | Graceful degradation, copy-paste fallback |
| Large file uploads fail offline | High | Low | Compress images before queuing, size limits |
| IndexedDB quota exceeded | Medium | Low | Monitor storage, prune old entries |
| Captive portal false positive | Medium | Medium | Server health check validates actual connectivity |
| Server down while browser online | Medium | Low | Distinct "server unavailable" banner with retry button |
| Health check performance overhead | Low | Low | 30s interval, 5s timeout, abort on navigation |

---

## 9. Deployment to Mobile Devices

### 9.1 iOS Deployment (Safari)

iOS requires using Safari to install PWAs. Other browsers (Chrome, Firefox) on iOS use WebKit and cannot install PWAs.

#### Prerequisites

1. **HTTPS Required**: PWAs must be served over HTTPS. iOS Safari blocks service workers on HTTP.
2. **Valid SSL Certificate**: Self-signed certs won't work. Use Let's Encrypt or similar.
3. **iOS 16+**: Target iOS 16+ for best PWA support (WebM, Background Sync, Share Target).

#### Development Setup for iOS Testing

**Option A: Local Network Testing (Recommended for Development)**

```bash
# 1. Find your Mac's local IP
ifconfig | grep "inet " | grep -v 127.0.0.1

# 2. Start the capture dev server (accessible on network)
cd frontend
npm run dev:capture -- --host 0.0.0.0

# 3. On iOS device, open Safari and navigate to:
# http://YOUR_MAC_IP:5174/capture

# Note: Service Worker won't work over HTTP, but you can test UI
```

**Option B: ngrok Tunnel (HTTPS for Full PWA Testing)**

```bash
# 1. Install ngrok (one-time)
brew install ngrok

# 2. Start the capture dev server
npm run dev:capture

# 3. In another terminal, start ngrok tunnel
ngrok http 5174

# 4. ngrok provides an HTTPS URL like:
# https://abc123.ngrok-free.app

# 5. Update VITE_API_URL to point to your backend
# (also needs to be accessible - either tunneled or deployed)

# 6. On iOS Safari, navigate to the ngrok URL
```

**Option C: Deploy to Staging Server**

```bash
# 1. Build the capture PWA
npm run build:capture

# 2. Deploy to your staging server (e.g., Vercel, Netlify, your VPS)
# Ensure it's served over HTTPS

# 3. Test on iOS Safari via the staging URL
```

#### Installing the PWA on iOS

1. **Open in Safari**: Navigate to `https://your-domain.com/capture` in Safari
2. **Tap Share Button**: Tap the share icon (box with arrow) in Safari's toolbar
3. **Select "Add to Home Screen"**: Scroll down and tap this option
4. **Name the App**: Confirm or edit the name (defaults to `short_name` from manifest)
5. **Tap "Add"**: The app icon appears on your home screen

```text
┌─────────────────────────────────────┐
│         Safari Share Sheet          │
├─────────────────────────────────────┤
│  Copy                               │
│  Add Bookmark                       │
│  Add to Reading List                │
│  Add to Favorites                   │
│  ★ Add to Home Screen ← Tap this   │
│  Find on Page                       │
│  ...                                │
└─────────────────────────────────────┘
```

#### iOS-Specific Configuration

**Apple Touch Icon**: iOS uses this for the home screen icon.

```html
<!-- In capture/index.html -->
<link rel="apple-touch-icon" href="/icons/capture-192.png">
<link rel="apple-touch-icon" sizes="180x180" href="/icons/capture-180.png">
```

**Status Bar Styling**:

```html
<!-- Black translucent status bar (content extends under it) -->
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">

<!-- Or use default (white) -->
<meta name="apple-mobile-web-app-status-bar-style" content="default">
```

**Splash Screen**: iOS generates splash screens from the icon and background color. For custom splash screens:

```html
<!-- iPhone 14 Pro Max (430x932) -->
<link rel="apple-touch-startup-image" 
      href="/splash/splash-1290x2796.png"
      media="(device-width: 430px) and (device-height: 932px) and (-webkit-device-pixel-ratio: 3)">

<!-- iPhone 14 Pro (393x852) -->
<link rel="apple-touch-startup-image"
      href="/splash/splash-1179x2556.png"  
      media="(device-width: 393px) and (device-height: 852px) and (-webkit-device-pixel-ratio: 3)">

<!-- Add more sizes as needed -->
```

#### iOS Debugging

**Safari Web Inspector (Remote Debugging)**:

1. **On iOS Device**: Settings → Safari → Advanced → Enable "Web Inspector"
2. **On Mac**: Safari → Settings → Advanced → Enable "Show Develop menu"
3. **Connect via USB**: Connect iOS device to Mac
4. **Open Inspector**: Safari → Develop → [Your iPhone] → [Your PWA]

**Console Logging**:
```javascript
// Logs visible in Safari Web Inspector console
console.log('[Capture]', 'Debug message');

// For production, use a logging service or localStorage
if (import.meta.env.DEV) {
  console.log('[Debug]', data);
}
```

**Service Worker Debugging**:
```javascript
// Check if SW is registered
navigator.serviceWorker.ready.then((registration) => {
  console.log('SW ready:', registration.scope);
});

// List all registrations
navigator.serviceWorker.getRegistrations().then((registrations) => {
  console.log('SW registrations:', registrations);
});
```

#### iOS Gotchas & Workarounds

| Issue | Workaround |
|-------|------------|
| **No install prompt** | iOS doesn't show install prompts. Educate users to use "Add to Home Screen" |
| **PWA closes on tab switch** | Normal behavior. State is preserved in IndexedDB |
| **Push notifications require user interaction** | Show in-app prompt before requesting permission |
| **Camera/mic permissions reset** | Permissions are per-origin; once granted, they persist |
| **50MB storage limit per origin** | Monitor storage usage; prune old cached data |
| **No badge updates in background** | Badge API works but only updates when app is open |

#### Updating the PWA on iOS

When you deploy updates:

1. **Service Worker handles updates**: New SW installs in background
2. **User sees update on next launch**: After closing and reopening the app
3. **Force update prompt** (optional):

```javascript
// In main.jsx, prompt user when update available
navigator.serviceWorker.ready.then((registration) => {
  registration.addEventListener('updatefound', () => {
    const newWorker = registration.installing;
    newWorker.addEventListener('statechange', () => {
      if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
        // New content available, prompt user
        if (confirm('New version available! Reload to update?')) {
          window.location.reload();
        }
      }
    });
  });
});
```

### 9.2 Android Deployment (Chrome)

Android provides better PWA support with native install prompts.

#### Installing on Android

1. **Open in Chrome**: Navigate to `https://your-domain.com/capture`
2. **Install Banner**: Chrome shows an install banner automatically (if criteria met)
3. **Or use Menu**: Tap ⋮ menu → "Install app" or "Add to Home screen"

#### PWA Install Criteria (Chrome)

Chrome shows the install prompt when:
- [x] Served over HTTPS
- [x] Has a valid `manifest.json` with required fields
- [x] Has a registered service worker with fetch handler
- [x] User has interacted with the domain (engagement heuristic)

#### Triggering Install Prompt Programmatically

```javascript
// Store the deferred prompt
let deferredPrompt;

window.addEventListener('beforeinstallprompt', (e) => {
  e.preventDefault();
  deferredPrompt = e;
  
  // Show your custom install button
  showInstallButton();
});

// When user clicks your install button
async function handleInstallClick() {
  if (!deferredPrompt) return;
  
  deferredPrompt.prompt();
  const { outcome } = await deferredPrompt.userChoice;
  
  console.log('Install outcome:', outcome);
  deferredPrompt = null;
}
```

### 9.3 Deployment Checklist

#### Before Deploying to Production

- [ ] **HTTPS configured** with valid certificate
- [ ] **manifest.json** has all required fields (name, icons, start_url, display)
- [ ] **Service Worker** registered and caching assets
- [ ] **Icons** available in required sizes (192x192, 512x512, maskable)
- [ ] **Offline page** works when network is unavailable
- [ ] **API URL** points to production backend
- [ ] **CORS** configured on backend for PWA domain

#### Testing Checklist

- [ ] Install PWA on iOS Safari
- [ ] Install PWA on Android Chrome  
- [ ] Test all 4 capture types (photo, voice, text, URL)
- [ ] Test offline capture and sync
- [ ] Test Share Target (share URL from browser to PWA)
- [ ] Test camera permission flow
- [ ] Test microphone permission flow
- [ ] Verify safe area insets on notched devices
- [ ] Test update flow (deploy change, verify update)

#### Lighthouse PWA Audit

```bash
# Run Lighthouse PWA audit
npx lighthouse https://your-domain.com/capture --view --preset=desktop

# Or use Chrome DevTools:
# 1. Open DevTools (F12)
# 2. Go to Lighthouse tab
# 3. Select "Progressive Web App" category
# 4. Generate report
```

**Target Scores:**
- Performance: > 90
- Accessibility: > 90
- Best Practices: > 90
- PWA: > 90 (all checks pass)

---

## 10. Related Documents

| Document | Purpose |
|----------|---------|
| `design_docs/08_mobile_capture.md` | Design specification |
| `01_ingestion_layer_implementation.md` | Existing capture endpoints |
| `07_frontend_application_implementation.md` | Frontend design system |
| `06_backend_api_implementation.md` | Backend API patterns |

