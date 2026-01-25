import { useEffect, useState } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import toast from 'react-hot-toast';
import { captureApi } from '../api/capture';
import { PdfCapture } from '../components/PdfCapture';

/**
 * ShareTarget handles content shared from other apps via the Web Share Target API.
 * 
 * When users share a URL, text, or files to this PWA, they're directed here.
 * The component parses the shared data and captures it appropriately.
 * 
 * For files (PDFs, images, audio), the service worker caches them and we
 * retrieve them here for user confirmation before upload.
 */
export function ShareTarget() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [status, setStatus] = useState('processing');
  const [error, setError] = useState(null);
  const [sharedFile, setSharedFile] = useState(null);
  const [fileType, setFileType] = useState(null);

  useEffect(() => {
    const handleShare = async () => {
      try {
        const title = searchParams.get('title') || '';
        const text = searchParams.get('text') || '';
        const url = searchParams.get('url') || '';

        // Check if there are shared files in the cache (set by service worker)
        const sharedFiles = await getSharedFiles();
        
        if (sharedFiles && sharedFiles.length > 0) {
          const file = sharedFiles[0];
          
          // Determine file type and show appropriate UI
          if (file.type === 'application/pdf' || file.name?.endsWith('.pdf')) {
            setSharedFile(file);
            setFileType('pdf');
            setStatus('file-preview');
            return;
          } else if (file.type?.startsWith('image/')) {
            // Handle image - auto-capture as photo
            await captureApi.capturePhoto({
              file,
              captureType: 'general',
            });
            toast.success('Photo captured!');
            setStatus('success');
            setTimeout(() => navigate('/'), 1500);
            return;
          } else if (file.type?.startsWith('audio/')) {
            // Handle audio - auto-capture as voice memo
            await captureApi.captureVoice({ file });
            toast.success('Voice memo captured!');
            setStatus('success');
            setTimeout(() => navigate('/'), 1500);
            return;
          }
        }

        // Extract URL from text if not provided directly
        let captureUrl = url;
        if (!captureUrl && text) {
          const urlMatch = text.match(/https?:\/\/[^\s]+/);
          if (urlMatch) {
            captureUrl = urlMatch[0];
          }
        }

        if (captureUrl) {
          // Capture as URL
          await captureApi.captureUrl({
            url: captureUrl,
            notes: text !== captureUrl ? text : undefined,
          });
          toast.success('URL captured!');
        } else if (text || title) {
          // Capture as text
          await captureApi.captureText({
            text: text || title,
            title: title || undefined,
          });
          toast.success('Note captured!');
        } else {
          throw new Error('No content to capture');
        }

        setStatus('success');
        
        // Navigate to home after a brief delay
        setTimeout(() => navigate('/'), 1500);
      } catch (err) {
        console.error('Share capture failed:', err);
        setError(err.message);
        setStatus('error');
      }
    };

    handleShare();
  }, [searchParams, navigate]);

  // Handle PDF capture completion
  const handlePdfComplete = () => {
    clearSharedFiles();
    navigate('/');
  };

  // Show PDF capture form if a PDF was shared
  if (status === 'file-preview' && fileType === 'pdf') {
    return (
      <div className="capture-container">
        <header className="capture-header">
          <h1>Shared PDF</h1>
        </header>
        <PdfCapture 
          onComplete={handlePdfComplete}
          isOnline={navigator.onLine}
          initialFile={sharedFile}
        />
      </div>
    );
  }

  return (
    <div className="capture-container share-target">
      <motion.div
        className="share-status"
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
      >
        {status === 'processing' && (
          <>
            <div className="spinner" />
            <p>Capturing...</p>
          </>
        )}
        {status === 'success' && (
          <>
            <div className="success-icon">✓</div>
            <p>Captured!</p>
          </>
        )}
        {status === 'error' && (
          <>
            <div className="error-icon">✗</div>
            <p>{error || 'Failed to capture'}</p>
            <button 
              className="retry-button"
              onClick={() => navigate('/')}
            >
              Go Home
            </button>
          </>
        )}
      </motion.div>
    </div>
  );
}

export default ShareTarget;

/**
 * Get shared files from the service worker's cache.
 * The service worker stores files when receiving share target POST requests.
 */
async function getSharedFiles() {
  try {
    // Check if files were stored in the share-target-files cache
    const cache = await caches.open('share-target-files');
    const keys = await cache.keys();
    
    if (keys.length === 0) return null;
    
    const files = [];
    for (const key of keys) {
      const response = await cache.match(key);
      if (response) {
        const blob = await response.blob();
        const url = new URL(key.url);
        const filename = url.searchParams.get('filename') || 'shared-file';
        const file = new File([blob], filename, { type: blob.type });
        files.push(file);
      }
    }
    
    return files;
  } catch (err) {
    console.error('Failed to get shared files:', err);
    return null;
  }
}

/**
 * Clear shared files from the cache after processing.
 */
async function clearSharedFiles() {
  try {
    await caches.delete('share-target-files');
  } catch (err) {
    console.error('Failed to clear shared files:', err);
  }
}
