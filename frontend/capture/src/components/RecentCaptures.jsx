import { useState } from 'react';
import { motion } from 'framer-motion';
import { clearPendingCaptures } from '../api/capture';

/**
 * Shows recent captures and pending offline captures.
 */
export function RecentCaptures({ pending, onClear }) {
  const [clearing, setClearing] = useState(false);
  
  // Ensure pending is always an array
  const pendingList = Array.isArray(pending) ? pending : [];
  
  if (pendingList.length === 0) {
    return null;
  }

  const formatTime = (timestamp) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    
    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    
    const diffHours = Math.floor(diffMins / 60);
    if (diffHours < 24) return `${diffHours}h ago`;
    
    return date.toLocaleDateString();
  };

  const handleClear = async () => {
    if (clearing) return;
    if (!window.confirm('Clear all pending captures? This cannot be undone.')) return;
    
    setClearing(true);
    try {
      await clearPendingCaptures();
      if (onClear) onClear();
    } catch {
      // Clear failed - ignore
    } finally {
      setClearing(false);
    }
  };

  return (
    <div className="recent-captures">
      <div className="recent-captures-header">
        <h3>Pending Sync</h3>
        <button 
          className="clear-pending-button"
          onClick={handleClear}
          disabled={clearing}
        >
          {clearing ? '...' : 'Clear All'}
        </button>
      </div>
      <ul className="pending-list">
        {pendingList.map((capture) => (
          <motion.li
            key={capture.id}
            className={`pending-item ${capture.retryCount > 0 ? 'has-errors' : ''}`}
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
          >
            <span className="pending-status">
              {capture.retryCount > 0 ? '⚠️' : '⏳'}
            </span>
            <span className="pending-info">
              <span className="pending-type">{capture.type || 'Capture'}</span>
              <span className="pending-time">
                {formatTime(capture.timestamp)}
                {capture.retryCount > 0 && ` · ${capture.retryCount} retries`}
              </span>
            </span>
          </motion.li>
        ))}
      </ul>
    </div>
  );
}

export default RecentCaptures;
