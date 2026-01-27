import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

/**
 * Collapsible learning options section for capture forms.
 * Allows users to configure card and exercise generation.
 */
export function LearningOptions({ 
  createCards, 
  setCreateCards, 
  createExercises, 
  setCreateExercises,
  defaultExpanded = false,
}) {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);

  return (
    <div className="learning-options">
      <button
        type="button"
        className="learning-options-toggle"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <span className="learning-options-icon">📚</span>
        <span>Learning Options</span>
        <span className="toggle-arrow">{isExpanded ? '▼' : '▶'}</span>
      </button>
      
      <AnimatePresence>
        {isExpanded && (
          <motion.div
            className="learning-options-content"
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
          >
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

export default LearningOptions;
