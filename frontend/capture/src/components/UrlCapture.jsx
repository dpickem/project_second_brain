import { useState, useRef, useEffect } from 'react';
import { motion } from 'framer-motion';
import toast from 'react-hot-toast';
import { captureApi } from '../api/capture';
import { CaptureOptions } from './CaptureOptions';

/**
 * URL capture component.
 * Captures URLs for later processing and content extraction.
 */
export function UrlCapture({ onComplete, isOnline }) {
  const [url, setUrl] = useState('');
  const [notes, setNotes] = useState('');
  const [tags, setTags] = useState('');
  const [createCards, setCreateCards] = useState(false);
  const [createExercises, setCreateExercises] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const inputRef = useRef(null);

  // Auto-focus and check clipboard for URL on mount
  useEffect(() => {
    inputRef.current?.focus();
    
    // Try to read URL from clipboard
    const checkClipboard = async () => {
      try {
        const clipboardText = await navigator.clipboard.readText();
        if (clipboardText && /^https?:\/\//.test(clipboardText)) {
          setUrl(clipboardText);
        }
      } catch {
        // Clipboard access denied - that's fine
      }
    };
    
    checkClipboard();
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    const trimmedUrl = url.trim();
    
    if (!trimmedUrl) {
      toast.error('Please enter a URL');
      return;
    }

    // Basic URL validation
    if (!/^https?:\/\/.+/.test(trimmedUrl)) {
      toast.error('Please enter a valid URL starting with http:// or https://');
      return;
    }

    setIsSubmitting(true);

    try {
      const tagList = tags
        .split(',')
        .map(t => t.trim())
        .filter(Boolean);

      await captureApi.captureUrl({
        url: trimmedUrl,
        notes: notes.trim() || undefined,
        tags: tagList.length > 0 ? tagList : undefined,
        createCards,
        createExercises,
      });

      toast.success(isOnline ? 'URL captured!' : 'Saved offline');
      onComplete();
    } catch (err) {
      toast.error(err.message || 'Capture failed');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <motion.form 
      className="capture-form"
      onSubmit={handleSubmit}
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
    >
      <div className="form-header">
        <span className="form-icon">🔗</span>
        <h2>Save URL</h2>
      </div>

      <input
        ref={inputRef}
        type="url"
        className="capture-input capture-input-large"
        placeholder="https://..."
        value={url}
        onChange={(e) => setUrl(e.target.value)}
        autoComplete="off"
        inputMode="url"
      />

      <CaptureOptions
        notes={notes}
        setNotes={setNotes}
        tags={tags}
        setTags={setTags}
        createCards={createCards}
        setCreateCards={setCreateCards}
        createExercises={createExercises}
        setCreateExercises={setCreateExercises}
      />

      <button 
        type="submit" 
        className="submit-button"
        disabled={isSubmitting || !url.trim()}
      >
        {isSubmitting ? 'Capturing...' : 'Capture'}
      </button>
    </motion.form>
  );
}

export default UrlCapture;
