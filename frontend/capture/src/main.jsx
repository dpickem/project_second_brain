import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import './styles/capture.css';

// Register service worker for PWA functionality
if ('serviceWorker' in navigator) {
  window.addEventListener('load', async () => {
    try {
      await navigator.serviceWorker.register('/capture/sw.js', {
        scope: '/capture/',
      });
    } catch {
      // Service worker registration failed - PWA features won't work
    }
  });
  
  // Listen for messages from service worker
  navigator.serviceWorker.addEventListener('message', (event) => {
    const { type, capture } = event.data;
    if (type === 'CAPTURE_QUEUED') {
      window.dispatchEvent(new CustomEvent('captureQueued', { detail: capture }));
    } else if (type === 'CAPTURE_SYNCED') {
      window.dispatchEvent(new CustomEvent('captureSynced', { detail: capture }));
    }
  });
}

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
