import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import './styles/capture.css';

// Register service worker for PWA functionality
if ('serviceWorker' in navigator) {
  window.addEventListener('load', async () => {
    try {
      const registration = await navigator.serviceWorker.register('/capture/sw.js', {
        scope: '/capture/',
      });
      console.log('[PWA] Service Worker registered:', registration.scope);
      
      // Listen for updates
      registration.addEventListener('updatefound', () => {
        const newWorker = registration.installing;
        newWorker.addEventListener('statechange', () => {
          if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
            // New version available
            console.log('[PWA] New version available');
          }
        });
      });
    } catch (error) {
      console.error('[PWA] Service Worker registration failed:', error);
    }
  });
  
  // Listen for messages from service worker
  navigator.serviceWorker.addEventListener('message', (event) => {
    const { type, capture } = event.data;
    if (type === 'CAPTURE_QUEUED') {
      console.log('[PWA] Capture queued offline:', capture);
      window.dispatchEvent(new CustomEvent('captureQueued', { detail: capture }));
    } else if (type === 'CAPTURE_SYNCED') {
      console.log('[PWA] Capture synced:', capture);
      window.dispatchEvent(new CustomEvent('captureSynced', { detail: capture }));
    }
  });
}

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
