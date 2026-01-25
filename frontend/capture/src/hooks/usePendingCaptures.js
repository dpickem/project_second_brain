import { useState, useEffect, useCallback } from 'react';
import { getPendingCaptures } from '../api/capture';

/**
 * Hook that tracks pending offline captures.
 * Listens for capture queued/synced events.
 */
export function usePendingCaptures() {
  const [pending, setPending] = useState([]);

  // Function to reload pending captures from IndexedDB
  const refresh = useCallback(async () => {
    try {
      const captures = await getPendingCaptures();
      setPending(captures);
    } catch (err) {
      console.error('Failed to load pending captures:', err);
    }
  }, []);

  // Load initial pending captures from IndexedDB
  useEffect(() => {
    refresh();
  }, [refresh]);

  // Listen for capture events
  useEffect(() => {
    const handleQueued = (event) => {
      const capture = event.detail;
      setPending((prev) => [...prev, capture]);
    };

    const handleSynced = (event) => {
      const { id } = event.detail;
      setPending((prev) => prev.filter((c) => c.id !== id));
    };

    const handleSyncComplete = () => {
      // Refresh from IndexedDB after sync completes
      refresh();
    };

    const handleQueueCleared = () => {
      setPending([]);
    };

    window.addEventListener('captureQueued', handleQueued);
    window.addEventListener('captureSynced', handleSynced);
    window.addEventListener('captureSyncComplete', handleSyncComplete);
    window.addEventListener('captureQueueCleared', handleQueueCleared);

    return () => {
      window.removeEventListener('captureQueued', handleQueued);
      window.removeEventListener('captureSynced', handleSynced);
      window.removeEventListener('captureSyncComplete', handleSyncComplete);
      window.removeEventListener('captureQueueCleared', handleQueueCleared);
    };
  }, [refresh]);

  return {
    pending,
    pendingCount: pending.length,
    refresh,
  };
}

export default usePendingCaptures;
