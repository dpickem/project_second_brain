import { useState, useRef, useEffect } from 'react';
import { motion } from 'framer-motion';
import toast from 'react-hot-toast';
import { captureApi } from '../api/capture';
import { CaptureOptions } from './CaptureOptions';

/**
 * Quick text capture component.
 * Supports markdown, auto-title generation, and optional tags.
 */
export function TextCapture({ onComplete, isOnline }) {
  const [text, setText] = useState('');
  const [title, setTitle] = useState('');
  const [tags, setTags] = useState('');
  const [createCards, setCreateCards] = useState(false);
  const [createExercises, setCreateExercises] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const textareaRef = useRef(null);

  // Auto-focus textarea on mount
  useEffect(() => {
    textareaRef.current?.focus();
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!text.trim()) {
      toast.error('Please enter some text');
      return;
    }

    setIsSubmitting(true);

    try {
      const tagList = tags
        .split(',')
        .map(t => t.trim())
        .filter(Boolean);

      await captureApi.captureText({
        text: text.trim(),
        title: title.trim() || undefined,
        tags: tagList.length > 0 ? tagList : undefined,
        createCards,
        createExercises,
      });

      toast.success(isOnline ? 'Captured!' : 'Saved offline');
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
        <span className="form-icon">✏️</span>
        <h2>Quick Note</h2>
      </div>

      <textarea
        ref={textareaRef}
        className="capture-textarea"
        placeholder="What's on your mind?"
        value={text}
        onChange={(e) => setText(e.target.value)}
        rows={6}
        autoComplete="off"
        autoCorrect="on"
        spellCheck="true"
      />

      <CaptureOptions
        title={title}
        setTitle={setTitle}
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
        disabled={isSubmitting || !text.trim()}
      >
        {isSubmitting ? 'Capturing...' : 'Capture'}
      </button>
    </motion.form>
  );
}

export default TextCapture;
