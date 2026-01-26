# Mobile Capture Design

> **Document Status**: Design Specification  
> **Last Updated**: December 2025  
> **Related Docs**: `01_ingestion_layer.md`, `07_frontend_application.md`

---

## 1. Overview

The Mobile Capture system provides low-friction knowledge capture for on-the-go use. Built as a Progressive Web App (PWA), it enables photo capture, voice memos, and quick notes with offline support.

### Design Goals

1. **< 3 Seconds to Capture**: Minimize time from idea to saved
2. **Offline-First**: Queue captures for later sync
3. **Minimal UI**: Large touch targets, few steps
4. **Reliable**: Never lose a capture
5. **Cross-Platform**: iOS Safari, Android Chrome

---

## 2. Architecture

```
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
│                             └────────┬────────┘                              │
│                                      │                                       │
│                    ┌─────────────────┴─────────────────┐                     │
│                    │          Service Worker           │                     │
│                    │   • Offline queue (IndexedDB)     │                     │
│                    │   • Background sync               │                     │
│                    │   • Push notifications            │                     │
│                    └─────────────────┬─────────────────┘                     │
│                                      │                                       │
└──────────────────────────────────────┼───────────────────────────────────────┘
                                       │
                                       │ Upload when online
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              BACKEND                                         │
├─────────────────────────────────────────────────────────────────────────────┤
│   /api/capture/photo   →   Vision OCR   →   Inbox                           │
│   /api/capture/voice   →   Whisper      →   Inbox                           │
│   /api/capture/text    →   Save         →   Inbox                           │
│   /api/capture/url     →   Fetch        →   Inbox                           │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. PWA Configuration

### 3.1 Manifest

A **Progressive Web App (PWA) manifest** is a JSON file that tells the browser how to treat your web app when a user "installs" it to their home screen. Without this file, your web app is just a browser bookmark; with it, the app can behave like a native mobile app.

Key properties in this manifest:
- **`name` / `short_name`**: The app's display name. `short_name` is used when space is limited (e.g., under the home screen icon).
- **`display: "standalone"`**: This removes the browser's URL bar and navigation buttons, making the app feel native rather than like a website.
- **`start_url`**: The page that opens when the user taps the app icon.
- **`theme_color` / `background_color`**: Control the status bar color and splash screen background on mobile devices.
- **`icons`**: Different sizes for various contexts (home screen, app switcher, splash screen). 192px and 512px are the minimum required sizes.
- **`share_target`**: This PWA feature registers your app as a "share destination" in the operating system. When a user is in another app (like Chrome or Twitter) and taps "Share," your PWA will appear as an option. The `params` define what data your app can receive (title, text, URL, or files like images/audio). **Important**: This feature only works on Android (Chrome). iOS Safari does not support the Web Share Target API ([WebKit Bug 194593](https://bugs.webkit.org/show_bug.cgi?id=194593)).

```json
// public/manifest.json
{
  "name": "Second Brain Capture",
  "short_name": "Capture",
  "description": "Quick knowledge capture",
  "start_url": "/capture",
  "display": "standalone",
  "background_color": "#111827",
  "theme_color": "#4f46e5",
  "icons": [
    {
      "src": "/icons/icon-192.png",
      "sizes": "192x192",
      "type": "image/png"
    },
    {
      "src": "/icons/icon-512.png",
      "sizes": "512x512",
      "type": "image/png"
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
  }
}
```

### 3.2 Service Worker

A **Service Worker** is a JavaScript file that runs in the background, separate from your web page. Think of it as a programmable proxy server that sits between your app and the network. This is what enables offline functionality—something traditional websites cannot do.

**How it works:**
1. **Installation (`install` event)**: When the service worker first loads, it pre-caches essential files (HTML, CSS, JS, icons) so they're available even without internet.

2. **Fetch interception (`fetch` event)**: Every network request your app makes passes through the service worker first. It can:
   - Return cached files immediately (fast, works offline)
   - Fetch from the network and cache the response
   - Queue requests for later if offline

3. **Background Sync (`sync` event)**: When the user captures something while offline, we can't send it to the server. Instead, we store it in **IndexedDB** (a browser database that persists data locally). The service worker registers for "background sync," which means the browser will wake up the service worker when connectivity returns—even if the user has closed the app—and retry the uploads.

**IndexedDB** is used here because it can store large binary data (photos, audio files) that `localStorage` cannot handle. The code creates a database called `CaptureDB` with an object store (like a table) called `capture-queue` where pending uploads wait.

This architecture ensures **zero data loss**—captures are never lost even if the user is on a plane, in a subway, or has spotty connectivity.

```javascript
// public/sw.js

const CACHE_NAME = 'capture-v1';
const OFFLINE_QUEUE_NAME = 'capture-queue';

// Cache static assets
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll([
        '/capture',
        '/capture/index.html',
        '/capture/styles.css',
        '/capture/app.js',
        '/icons/icon-192.png',
      ]);
    })
  );
});

// Handle fetch with offline support
self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);
  
  // Capture API calls - queue if offline
  if (url.pathname.startsWith('/api/capture/')) {
    event.respondWith(handleCaptureRequest(event.request));
    return;
  }
  
  // Cache-first for static assets
  event.respondWith(
    caches.match(event.request).then((cached) => {
      return cached || fetch(event.request);
    })
  );
});

async function handleCaptureRequest(request) {
  try {
    // Try to send immediately
    const response = await fetch(request.clone());
    return response;
  } catch (error) {
    // Network failed - queue for later
    await queueCapture(request);
    return new Response(
      JSON.stringify({ status: 'queued', message: 'Saved offline' }),
      { status: 202, headers: { 'Content-Type': 'application/json' } }
    );
  }
}

async function queueCapture(request) {
  const db = await openCaptureDB();
  const formData = await request.formData();
  
  const captureData = {
    id: crypto.randomUUID(),
    url: request.url,
    method: request.method,
    timestamp: Date.now(),
    data: Object.fromEntries(formData),
  };
  
  // Store file data as ArrayBuffer
  for (const [key, value] of formData.entries()) {
    if (value instanceof File) {
      captureData.data[key] = {
        name: value.name,
        type: value.type,
        data: await value.arrayBuffer(),
      };
    }
  }
  
  const tx = db.transaction(OFFLINE_QUEUE_NAME, 'readwrite');
  await tx.objectStore(OFFLINE_QUEUE_NAME).add(captureData);
  
  // Register for background sync
  if ('sync' in self.registration) {
    await self.registration.sync.register('capture-sync');
  }
}

// Background sync handler
self.addEventListener('sync', (event) => {
  if (event.tag === 'capture-sync') {
    event.waitUntil(syncQueuedCaptures());
  }
});

async function syncQueuedCaptures() {
  const db = await openCaptureDB();
  const tx = db.transaction(OFFLINE_QUEUE_NAME, 'readwrite');
  const store = tx.objectStore(OFFLINE_QUEUE_NAME);
  const queued = await store.getAll();
  
  for (const capture of queued) {
    try {
      const formData = new FormData();
      
      for (const [key, value] of Object.entries(capture.data)) {
        if (value.data instanceof ArrayBuffer) {
          const blob = new Blob([value.data], { type: value.type });
          formData.append(key, blob, value.name);
        } else {
          formData.append(key, value);
        }
      }
      
      await fetch(capture.url, {
        method: capture.method,
        body: formData,
      });
      
      // Remove from queue on success
      await store.delete(capture.id);
      
    } catch (error) {
      console.error('Sync failed for capture:', capture.id, error);
    }
  }
}

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
```

---

## 4. Capture UI Components

### 4.1 Main Capture Screen

This is the landing page users see when they open the capture app. The design philosophy is **"speed to capture"**—the fewer taps and decisions required, the more likely users will actually capture fleeting ideas.

**Component breakdown:**
- **`useOnlineStatus()`**: A custom React hook that monitors `navigator.onLine` and listens for `online`/`offline` browser events. Returns `true` or `false` so we can show the offline banner.
- **`usePendingCaptures()`**: Queries IndexedDB to count how many captures are waiting to sync. This reassures users their offline captures weren't lost.
- **`useState(activeCapture)`**: Tracks which capture modal (photo/voice/text/url) is currently open. When `null`, no modal is shown.

**Why four separate capture types instead of one generic form?**
Each type has different UX needs: photos need camera access and preview, voice needs a recording interface with duration feedback, text is just a textarea, and URLs need validation. Separate flows let us optimize each experience.

**The `CaptureButton` component** is designed with large touch targets (see styles section) because thumbs are imprecise. Small buttons lead to frustration and mis-taps on mobile devices.

```jsx
// src/pages/MobileCapture.jsx

import { useState } from 'react';
import { CaptureButton } from '../components/capture/CaptureButton';
import { RecentCaptures } from '../components/capture/RecentCaptures';
import { OfflineBanner } from '../components/capture/OfflineBanner';
import { useOnlineStatus } from '../hooks/useOnlineStatus';
import { usePendingCaptures } from '../hooks/usePendingCaptures';

export function MobileCapture() {
  const isOnline = useOnlineStatus();
  const { pendingCount } = usePendingCaptures();
  const [activeCapture, setActiveCapture] = useState(null);
  
  return (
    <div className="capture-screen">
      {!isOnline && (
        <OfflineBanner pendingCount={pendingCount} />
      )}
      
      <header className="capture-header">
        <h1>Quick Capture</h1>
      </header>
      
      <main className="capture-buttons">
        <CaptureButton
          icon="📷"
          label="Photo"
          sublabel="Book page, whiteboard"
          onClick={() => setActiveCapture('photo')}
        />
        
        <CaptureButton
          icon="🎤"
          label="Voice"
          sublabel="Speak your idea"
          onClick={() => setActiveCapture('voice')}
        />
        
        <CaptureButton
          icon="✏️"
          label="Note"
          sublabel="Quick text"
          onClick={() => setActiveCapture('text')}
        />
        
        <CaptureButton
          icon="🔗"
          label="URL"
          sublabel="Save a link"
          onClick={() => setActiveCapture('url')}
        />
      </main>
      
      <section className="recent-captures">
        <h2>Recent</h2>
        <RecentCaptures limit={5} />
      </section>
      
      {/* Capture modals */}
      {activeCapture === 'photo' && (
        <PhotoCapture onClose={() => setActiveCapture(null)} />
      )}
      {activeCapture === 'voice' && (
        <VoiceCapture onClose={() => setActiveCapture(null)} />
      )}
      {activeCapture === 'text' && (
        <TextCapture onClose={() => setActiveCapture(null)} />
      )}
      {activeCapture === 'url' && (
        <UrlCapture onClose={() => setActiveCapture(null)} />
      )}
    </div>
  );
}
```

### 4.2 Photo Capture

This component handles photographing physical content like book pages, whiteboards, or handwritten notes. The captured image is sent to the backend for OCR (Optical Character Recognition) to extract the text.

**Key implementation details:**

- **`capture="environment"`**: This HTML attribute on the file input tells mobile browsers to open the rear-facing camera directly instead of showing a file picker. `"environment"` = back camera, `"user"` = front/selfie camera.

- **`accept="image/*"`**: Restricts the file picker to images only.

- **Capture type selector (`book_page`, `whiteboard`, `general`)**: Different source types benefit from different image preprocessing:
  - *Book pages*: Deskewing, shadow removal, contrast enhancement
  - *Whiteboards*: Color correction (whiteboards often photograph with a blue/gray tint), marker color enhancement
  - *General*: Minimal processing
  
  The backend uses this hint to apply appropriate filters before OCR.

- **`URL.createObjectURL(file)`**: Creates a temporary local URL for the captured image so we can show a preview without uploading first. This URL is only valid during the browser session.

- **Preview before submit**: Users can review and retake the photo before committing. This prevents wasted uploads of blurry or poorly-framed shots.

- **Error handling for offline**: If the upload fails due to network issues, the service worker will have queued it (see Section 3.2). We detect this via the `'queued'` error message and show appropriate feedback ("Saved offline" instead of "Failed").

```jsx
// src/components/capture/PhotoCapture.jsx

import { useRef, useState } from 'react';
import { captureApi } from '../../services/captureApi';

export function PhotoCapture({ onClose }) {
  const [captureType, setCaptureType] = useState('book_page');
  const [isCapturing, setIsCapturing] = useState(false);
  const [preview, setPreview] = useState(null);
  const inputRef = useRef(null);
  
  const handleFileSelect = (event) => {
    const file = event.target.files[0];
    if (file) {
      setPreview(URL.createObjectURL(file));
    }
  };
  
  const handleSubmit = async () => {
    const file = inputRef.current.files[0];
    if (!file) return;
    
    setIsCapturing(true);
    
    try {
      await captureApi.photo(file, captureType);
      
      // Show success feedback
      showToast('Captured! Processing...', 'success');
      onClose();
      
    } catch (error) {
      if (error.message === 'queued') {
        showToast('Saved offline', 'info');
        onClose();
      } else {
        showToast('Capture failed', 'error');
      }
    } finally {
      setIsCapturing(false);
    }
  };
  
  return (
    <div className="capture-modal">
      <header>
        <button className="btn-close" onClick={onClose}>×</button>
        <h2>Photo Capture</h2>
      </header>
      
      <main>
        {/* Capture type selector */}
        <div className="type-selector">
          <TypeButton 
            active={captureType === 'book_page'}
            onClick={() => setCaptureType('book_page')}
            icon="📖"
            label="Book Page"
          />
          <TypeButton 
            active={captureType === 'whiteboard'}
            onClick={() => setCaptureType('whiteboard')}
            icon="🖼️"
            label="Whiteboard"
          />
          <TypeButton 
            active={captureType === 'general'}
            onClick={() => setCaptureType('general')}
            icon="📝"
            label="General"
          />
        </div>
        
        {/* Camera/file input */}
        <div className="photo-input">
          {preview ? (
            <div className="preview">
              <img src={preview} alt="Preview" />
              <button 
                className="btn-retake"
                onClick={() => {
                  setPreview(null);
                  inputRef.current.value = '';
                }}
              >
                Retake
              </button>
            </div>
          ) : (
            <label className="camera-button">
              <input
                ref={inputRef}
                type="file"
                accept="image/*"
                capture="environment"
                onChange={handleFileSelect}
              />
              <span className="icon">📷</span>
              <span>Tap to capture</span>
            </label>
          )}
        </div>
      </main>
      
      <footer>
        <button
          className="btn-submit"
          onClick={handleSubmit}
          disabled={!preview || isCapturing}
        >
          {isCapturing ? 'Processing...' : 'Save Capture'}
        </button>
      </footer>
    </div>
  );
}
```

### 4.3 Voice Capture

Voice memos let users quickly dictate ideas without typing on a small keyboard. The audio is recorded locally, then sent to the backend where OpenAI's Whisper model transcribes it to text.

**Key browser APIs used:**

- **`navigator.mediaDevices.getUserMedia({ audio: true })`**: Requests microphone access from the user. The browser will show a permission prompt on first use. Returns a `MediaStream` object containing the audio data.

- **`MediaRecorder`**: A browser API that records media streams. We configure it to output WebM format (good compression, widely supported). Key events:
  - `ondataavailable`: Called periodically with chunks of recorded audio data
  - `onstop`: Called when recording ends, where we combine all chunks into a single file

- **`Blob`**: A "Binary Large Object"—raw binary data that represents the audio file. We create it by combining all the recorded chunks: `new Blob(chunks, { type: 'audio/webm' })`.

**UI/UX considerations:**

- **Large circular record button**: Mimics familiar voice recorder apps. The pulsing animation (CSS keyframes) provides constant visual feedback that recording is active.

- **Duration timer**: Users need to know how long they've been recording. We use `setInterval` to increment a counter every second. The `formatDuration` helper converts seconds to `M:SS` format.

- **Playback before submit**: The `<audio controls>` element lets users listen to their recording before saving. This catches issues like background noise or accidentally recording silence.

- **Cleanup**: When recording stops, we call `stream.getTracks().forEach(track => track.stop())` to release the microphone. Without this, the browser would keep showing the "recording" indicator and the mic would stay active.

**Why WebM format?** It's natively supported by Chrome and Firefox's MediaRecorder without any encoding libraries. Safari has historically been problematic (preferring MP4/AAC), which is a known cross-browser challenge for voice recording PWAs.

```jsx
// src/components/capture/VoiceCapture.jsx

import { useState, useRef, useEffect } from 'react';
import { captureApi } from '../../services/captureApi';

export function VoiceCapture({ onClose }) {
  const [isRecording, setIsRecording] = useState(false);
  const [audioBlob, setAudioBlob] = useState(null);
  const [duration, setDuration] = useState(0);
  const mediaRecorderRef = useRef(null);
  const chunksRef = useRef([]);
  const timerRef = useRef(null);
  
  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;
      chunksRef.current = [];
      
      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) {
          chunksRef.current.push(e.data);
        }
      };
      
      mediaRecorder.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: 'audio/webm' });
        setAudioBlob(blob);
        stream.getTracks().forEach(track => track.stop());
      };
      
      mediaRecorder.start();
      setIsRecording(true);
      
      // Start timer
      timerRef.current = setInterval(() => {
        setDuration(d => d + 1);
      }, 1000);
      
    } catch (error) {
      showToast('Microphone access denied', 'error');
    }
  };
  
  const stopRecording = () => {
    mediaRecorderRef.current?.stop();
    setIsRecording(false);
    clearInterval(timerRef.current);
  };
  
  const handleSubmit = async () => {
    if (!audioBlob) return;
    
    try {
      await captureApi.voice(audioBlob);
      showToast('Voice memo saved!', 'success');
      onClose();
    } catch (error) {
      if (error.message === 'queued') {
        showToast('Saved offline', 'info');
        onClose();
      }
    }
  };
  
  const formatDuration = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };
  
  return (
    <div className="capture-modal voice-capture">
      <header>
        <button className="btn-close" onClick={onClose}>×</button>
        <h2>Voice Memo</h2>
      </header>
      
      <main>
        <div className="recording-indicator">
          {isRecording ? (
            <>
              <div className="pulse-ring" />
              <span className="duration">{formatDuration(duration)}</span>
            </>
          ) : audioBlob ? (
            <audio src={URL.createObjectURL(audioBlob)} controls />
          ) : (
            <span className="instruction">Tap to start recording</span>
          )}
        </div>
        
        <button
          className={`record-button ${isRecording ? 'recording' : ''}`}
          onClick={isRecording ? stopRecording : startRecording}
        >
          {isRecording ? '⏹️ Stop' : '🎤 Record'}
        </button>
      </main>
      
      {audioBlob && (
        <footer>
          <button className="btn-discard" onClick={() => setAudioBlob(null)}>
            Discard
          </button>
          <button className="btn-submit" onClick={handleSubmit}>
            Save
          </button>
        </footer>
      )}
    </div>
  );
}
```

---

## 5. Share Target Integration

> ⚠️ **iOS Limitation**: The Web Share Target API is **not supported on iOS Safari**. This means the Capture PWA will not appear in the iOS share sheet. This is a [known WebKit limitation](https://bugs.webkit.org/show_bug.cgi?id=194593) that has been open since 2019 with no implementation timeline.
>
> **Workarounds for iOS users:**
> 1. Open the PWA directly and manually copy/paste URLs or use the file picker
> 2. Create a native iOS app wrapper using [PWABuilder](https://www.pwabuilder.com/) with a Share Extension
>
> The Share Target functionality described below **works fully on Android** with Chrome.

### 5.1 Handle Shared Content (Android)

This page handles content shared *into* the app from other applications. For example, if a user is reading an article in Chrome on Android and taps Share → "Second Brain Capture," this component receives that URL.

**How the Share Target API works (Android only):**

1. The PWA manifest (Section 3.1) declares the app as a share target with `share_target` configuration.
2. When the user shares something, the OS launches the PWA at the specified `action` URL (`/capture/share`).
3. The shared data arrives as URL query parameters: `?title=...&text=...&url=...`

**React Router integration:**
- **`useSearchParams()`**: A React Router hook that parses the URL query string. We extract the `title`, `text`, and `url` parameters that the OS passed to us.
- **`useNavigate()`**: Programmatically redirects the user after processing. We send them back to `/capture` after a brief delay.

**Why the status states (`processing`, `success`, `queued`, `error`)?**
The share flow happens automatically without user input, so clear feedback is essential. Users need to know:
- Their share was received (not silently dropped)
- Whether it succeeded or was saved for later (offline)
- If something went wrong

**The 1.5-second delay before redirect** gives users time to read the status message. Immediate redirects feel jarring and leave users uncertain whether the action completed.

**`useEffect` with empty dependency array `[]`**: This React pattern runs the function once when the component mounts—perfect for processing the shared content immediately when the page loads.

```jsx
// src/pages/ShareTarget.jsx

import { useEffect, useState } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { captureApi } from '../services/captureApi';

export function ShareTarget() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [status, setStatus] = useState('processing');
  
  useEffect(() => {
    handleSharedContent();
  }, []);
  
  const handleSharedContent = async () => {
    const title = searchParams.get('title');
    const text = searchParams.get('text');
    const url = searchParams.get('url');
    
    try {
      if (url) {
        // Shared URL
        await captureApi.url(url, text);
        setStatus('success');
      } else if (text) {
        // Shared text
        await captureApi.text(text, title);
        setStatus('success');
      } else {
        setStatus('error');
      }
      
      // Redirect after short delay
      setTimeout(() => navigate('/capture'), 1500);
      
    } catch (error) {
      if (error.message === 'queued') {
        setStatus('queued');
        setTimeout(() => navigate('/capture'), 1500);
      } else {
        setStatus('error');
      }
    }
  };
  
  return (
    <div className="share-target-screen">
      {status === 'processing' && (
        <div className="status processing">
          <div className="spinner" />
          <p>Saving...</p>
        </div>
      )}
      
      {status === 'success' && (
        <div className="status success">
          <span className="icon">✓</span>
          <p>Saved!</p>
        </div>
      )}
      
      {status === 'queued' && (
        <div className="status queued">
          <span className="icon">📴</span>
          <p>Saved offline</p>
        </div>
      )}
      
      {status === 'error' && (
        <div className="status error">
          <span className="icon">✗</span>
          <p>Failed to save</p>
        </div>
      )}
    </div>
  );
}
```

---

## 6. Offline Support Hooks

**Custom React Hooks** are reusable functions that encapsulate stateful logic. By convention, they start with `use`. These two hooks handle offline-related concerns so individual components don't need to duplicate this logic.

### `useOnlineStatus`

This hook tracks whether the device has network connectivity.

**How it works:**
- **`navigator.onLine`**: A browser property that returns `true` if the browser believes it has network access. Note: this isn't perfectly reliable (it might say "online" when behind a captive portal), but it's the best we have.
- **`useState(navigator.onLine)`**: Initialize React state with the current online status.
- **Event listeners**: The browser fires `online` and `offline` events on the `window` object when connectivity changes. We listen for these and update our state accordingly.
- **Cleanup function**: The `return () => { ... }` inside `useEffect` runs when the component unmounts, removing our event listeners to prevent memory leaks.

**Usage**: Any component can call `const isOnline = useOnlineStatus()` and react to connectivity changes.

### `usePendingCaptures`

This hook queries IndexedDB to count captures waiting in the offline queue.

**Why this matters for UX:** Users who captured content while offline might worry their data was lost. Showing "3 captures pending sync" reassures them and sets expectations about what will happen when connectivity returns.

**Implementation notes:**
- Opens the same `CaptureDB` database the service worker uses
- Uses a read-only transaction (we're just counting, not modifying)
- Re-checks when the device comes online (because background sync might have cleared the queue)

```javascript
// src/hooks/useOnlineStatus.js

import { useState, useEffect } from 'react';

export function useOnlineStatus() {
  const [isOnline, setIsOnline] = useState(navigator.onLine);
  
  useEffect(() => {
    const handleOnline = () => setIsOnline(true);
    const handleOffline = () => setIsOnline(false);
    
    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);
    
    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);
  
  return isOnline;
}

// src/hooks/usePendingCaptures.js

import { useState, useEffect } from 'react';

export function usePendingCaptures() {
  const [pendingCount, setPendingCount] = useState(0);
  
  useEffect(() => {
    const checkPending = async () => {
      const db = await openCaptureDB();
      const tx = db.transaction('capture-queue', 'readonly');
      const count = await tx.objectStore('capture-queue').count();
      setPendingCount(count);
    };
    
    checkPending();
    
    // Recheck when coming online
    window.addEventListener('online', checkPending);
    return () => window.removeEventListener('online', checkPending);
  }, []);
  
  return { pendingCount };
}
```

---

## 7. Mobile-Optimized Styles

Mobile CSS requires different considerations than desktop. These styles are optimized for touch interaction, variable screen sizes, and mobile-specific hardware features.

**Key mobile CSS techniques used:**

### Safe Area Insets
```css
padding: env(safe-area-inset-top) env(safe-area-inset-right) ...
```
Modern phones have notches (iPhone) or camera cutouts (Android) that intrude into the screen. `env(safe-area-inset-*)` is a CSS function that returns the size of these obstructions, so content doesn't get hidden behind them. Without this, your UI might render under the notch.

### Touch Target Sizing
```css
min-height: 120px;
```
Apple's Human Interface Guidelines recommend touch targets of at least 44×44 points. We go larger (120px) because capture buttons are primary actions and users may be tapping quickly or one-handed. Small buttons cause frustration and errors.

### Preventing Unwanted Touch Behaviors
```css
-webkit-user-select: none;
user-select: none;
-webkit-tap-highlight-color: transparent;
```
- **`user-select: none`**: Prevents text selection when users tap buttons. Without this, long-pressing a button might select its text instead of activating it.
- **`-webkit-tap-highlight-color: transparent`**: iOS Safari adds a gray overlay when you tap elements. This removes it for cleaner visual feedback.

### Touch Feedback
```css
&:active { transform: scale(0.98); }
```
Unlike desktop hover states, mobile needs `:active` states for feedback. The subtle scale-down (98%) gives tactile feedback that the tap was registered.

### Aspect Ratio for Camera Preview
```css
aspect-ratio: 4/3;
```
Maintains a consistent preview shape regardless of screen width. 4:3 matches common camera sensor ratios.

### Dark Theme
The dark background (`--bg-dark: #111827`) isn't just aesthetic—on OLED screens (common on modern phones), dark pixels are literally turned off, significantly reducing battery consumption. This matters for a capture app users might keep open.

```css
/* src/styles/mobile-capture.css */

.capture-screen {
  min-height: 100vh;
  background: var(--bg-dark);
  color: white;
  padding: env(safe-area-inset-top) env(safe-area-inset-right) 
           env(safe-area-inset-bottom) env(safe-area-inset-left);
}

.capture-buttons {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 1rem;
  padding: 1rem;
}

.capture-button {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 2rem 1rem;
  background: var(--bg-secondary);
  border-radius: var(--radius-lg);
  border: none;
  
  /* Large touch target */
  min-height: 120px;
  
  /* Prevent text selection on touch */
  -webkit-user-select: none;
  user-select: none;
  
  /* Touch feedback */
  -webkit-tap-highlight-color: transparent;
  
  &:active {
    transform: scale(0.98);
    background: var(--bg-dark);
  }
}

.capture-button .icon {
  font-size: 2.5rem;
  margin-bottom: 0.5rem;
}

.capture-modal {
  position: fixed;
  inset: 0;
  background: var(--bg-dark);
  z-index: 100;
  display: flex;
  flex-direction: column;
}

.camera-button {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  width: 100%;
  aspect-ratio: 4/3;
  background: #222;
  border-radius: var(--radius-lg);
  cursor: pointer;
  
  input {
    display: none;
  }
  
  .icon {
    font-size: 4rem;
    margin-bottom: 1rem;
  }
}

.record-button {
  width: 80px;
  height: 80px;
  border-radius: 50%;
  background: var(--color-danger);
  border: 4px solid white;
  font-size: 1.5rem;
  
  &.recording {
    animation: pulse 1s infinite;
  }
}

@keyframes pulse {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.05); }
}

.offline-banner {
  background: var(--color-warning);
  color: black;
  padding: 0.5rem 1rem;
  text-align: center;
  font-size: 0.875rem;
}
```

---

## 8. Related Documents

- `01_ingestion_layer.md` — Backend capture endpoints
- `07_frontend_application.md` — Main web application
- `06_backend_api.md` — API specifications

