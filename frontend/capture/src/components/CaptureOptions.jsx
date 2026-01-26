import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

/**
 * Collapsible options section for capture forms.
 * Includes learning options (cards/exercises) and can accept additional custom options.
 */
export function CaptureOptions({ 
  createCards, 
  setCreateCards, 
  createExercises, 
  setCreateExercises,
  // Optional: additional options passed as children or specific props
  detectHandwriting,
  setDetectHandwriting,
  expandTranscript,
  setExpandTranscript,
  // Text/URL-specific options
  title,
  setTitle,
  notes,
  setNotes,
  notesPlaceholder = "Notes (optional)",
  tags,
  setTags,
  // Photo/Book-specific options
  bookTitle,
  setBookTitle,
  defaultExpanded = false,
}) {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);

  return (
    <div className="capture-options">
      <button
        type="button"
        className="capture-options-toggle"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <span className="capture-options-icon">⚙️</span>
        <span>Options</span>
        <span className="toggle-arrow">{isExpanded ? '▼' : '▶'}</span>
      </button>
      
      <AnimatePresence>
        {isExpanded && (
          <motion.div
            className="capture-options-content"
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
          >
            {/* Title field (Text-specific) */}
            {setTitle && (
              <div className="option-field">
                <input
                  type="text"
                  className="capture-input"
                  placeholder="Title (optional)"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                />
              </div>
            )}

            {/* Book title field (Photo/Book-specific) */}
            {setBookTitle && (
              <div className="option-field">
                <input
                  type="text"
                  className="capture-input"
                  placeholder="Book title (optional)"
                  value={bookTitle}
                  onChange={(e) => setBookTitle(e.target.value)}
                />
              </div>
            )}

            {/* Notes field */}
            {setNotes && (
              <div className="option-field">
                <textarea
                  className="capture-textarea capture-textarea-small"
                  placeholder={notesPlaceholder}
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  rows={2}
                />
              </div>
            )}

            {/* Tags field (URL-specific) */}
            {setTags && (
              <div className="option-field">
                <input
                  type="text"
                  className="capture-input"
                  placeholder="Tags (comma-separated)"
                  value={tags}
                  onChange={(e) => setTags(e.target.value)}
                />
              </div>
            )}

            {/* Expand transcript option (Voice-specific) */}
            {setExpandTranscript && (
              <>
                <label className="checkbox-label">
                  <input
                    type="checkbox"
                    checked={expandTranscript}
                    onChange={(e) => setExpandTranscript(e.target.checked)}
                  />
                  <span>Expand into structured note</span>
                </label>
                <p className="hint-text checkbox-hint">
                  {expandTranscript 
                    ? 'Transcription will be expanded into a well-formatted note.'
                    : 'Transcription will be kept as-is.'}
                </p>
              </>
            )}

            {/* Handwriting detection option (PDF-specific) */}
            {setDetectHandwriting && (
              <>
                <label className="checkbox-label">
                  <input
                    type="checkbox"
                    checked={detectHandwriting}
                    onChange={(e) => setDetectHandwriting(e.target.checked)}
                  />
                  <span>Detect handwritten annotations</span>
                </label>
                <p className="hint-text checkbox-hint">
                  {detectHandwriting 
                    ? 'Will use Vision AI to extract handwritten margin notes.'
                    : 'Only digital text and highlights will be extracted.'}
                </p>
              </>
            )}

            {/* Learning options */}
            <label className="checkbox-label">
              <input
                type="checkbox"
                checked={createCards}
                onChange={(e) => setCreateCards(e.target.checked)}
              />
              <span>Generate flashcards</span>
            </label>
            <p className="hint-text checkbox-hint">
              Create spaced repetition cards for review
            </p>
            
            <label className="checkbox-label">
              <input
                type="checkbox"
                checked={createExercises}
                onChange={(e) => setCreateExercises(e.target.checked)}
              />
              <span>Generate exercises</span>
            </label>
            <p className="hint-text checkbox-hint">
              Create practice exercises to test understanding
            </p>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export default CaptureOptions;
