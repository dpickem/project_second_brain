import { useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { CaptureButton } from '../components/CaptureButton';
import { TextCapture } from '../components/TextCapture';
import { UrlCapture } from '../components/UrlCapture';
import { PhotoCapture } from '../components/PhotoCapture';
import { VoiceCapture } from '../components/VoiceCapture';
import { PdfCapture } from '../components/PdfCapture';
import { OfflineBanner } from '../components/OfflineBanner';
import { RecentCaptures } from '../components/RecentCaptures';
import { useOnlineStatus } from '../hooks/useOnlineStatus';
import { usePendingCaptures } from '../hooks/usePendingCaptures';
import { syncPendingCaptures } from '../api/capture';

const CAPTURE_TYPES = {
  text: { icon: '✏️', label: 'Note', component: TextCapture },
  url: { icon: '🔗', label: 'URL', component: UrlCapture },
  photo: { icon: '📷', label: 'Photo', component: PhotoCapture },
  voice: { icon: '🎤', label: 'Voice', component: VoiceCapture },
  pdf: { icon: '📑', label: 'PDF', component: PdfCapture },
};

export function MobileCapture() {
  const [activeCapture, setActiveCapture] = useState(null);
  const [syncing, setSyncing] = useState(false);
  const [syncResult, setSyncResult] = useState(null);
  const isOnline = useOnlineStatus();
  const { pendingCount, pending, refresh } = usePendingCaptures();

  const handleCaptureComplete = () => {
    setActiveCapture(null);
  };

  const handleSync = useCallback(async () => {
    if (syncing || !isOnline || pendingCount === 0) return;
    
    setSyncing(true);
    setSyncResult(null);
    
    try {
      const result = await syncPendingCaptures();
      
      setSyncResult(result);
      refresh(); // Refresh the pending list
      
      // Clear result after 3 seconds
      setTimeout(() => setSyncResult(null), 3000);
    } catch (error) {
      setSyncResult({ error: error.message });
    } finally {
      setSyncing(false);
    }
  }, [syncing, isOnline, pendingCount, refresh]);

  const ActiveComponent = activeCapture ? CAPTURE_TYPES[activeCapture]?.component : null;

  return (
    <div className="capture-container">
      {/* Offline Banner */}
      <OfflineBanner isOnline={isOnline} pendingCount={pendingCount} />

      {/* Header */}
      <header className="capture-header">
        <h1>Capture</h1>
        <div className="header-actions">
          {pendingCount > 0 && (
            <>
              <span className="pending-badge">{pendingCount} pending</span>
              <button 
                className={`sync-button ${syncing ? 'syncing' : ''}`}
                onClick={handleSync}
                disabled={syncing || !isOnline}
                title={!isOnline ? 'Offline - cannot sync' : 'Sync pending captures'}
              >
                {syncing ? '⟳' : '↻'} Sync
              </button>
            </>
          )}
        </div>
      </header>
      
      {/* Sync Result Toast */}
      <AnimatePresence>
        {syncResult && (
          <motion.div 
            className={`sync-toast ${syncResult.error ? 'error' : syncResult.failed > 0 ? 'warning' : 'success'}`}
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
          >
            {syncResult.error ? (
              `Sync failed: ${syncResult.error}`
            ) : syncResult.failed > 0 && syncResult.synced === 0 ? (
              <div>
                <div>All {syncResult.failed} captures failed</div>
                <div className="sync-toast-detail">
                  {syncResult.results?.find(r => r.error)?.error || 'Check console for details'}
                </div>
              </div>
            ) : (
              `Synced ${syncResult.synced} capture${syncResult.synced !== 1 ? 's' : ''}${syncResult.failed > 0 ? `, ${syncResult.failed} failed` : ''}`
            )}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Main Capture Buttons */}
      <AnimatePresence mode="wait">
        {!activeCapture ? (
          <motion.div
            key="buttons"
            className="capture-buttons"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
          >
            {Object.entries(CAPTURE_TYPES).map(([type, { icon, label }]) => (
              <CaptureButton
                key={type}
                icon={icon}
                label={label}
                onClick={() => setActiveCapture(type)}
              />
            ))}
          </motion.div>
        ) : (
          <motion.div
            key="form"
            className="capture-form-container"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
          >
            <button 
              className="back-button"
              onClick={() => setActiveCapture(null)}
            >
              ← Back
            </button>
            {ActiveComponent && (
              <ActiveComponent 
                onComplete={handleCaptureComplete}
                isOnline={isOnline}
              />
            )}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Recent Captures */}
      {!activeCapture && (
        <RecentCaptures pending={pending} onClear={refresh} />
      )}
    </div>
  );
}

export default MobileCapture;
