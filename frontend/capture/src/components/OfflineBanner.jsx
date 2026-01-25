import { motion, AnimatePresence } from 'framer-motion';

/**
 * Banner that appears when the device is offline.
 * Shows pending capture count if any.
 */
export function OfflineBanner({ isOnline, pendingCount = 0 }) {
  return (
    <AnimatePresence>
      {!isOnline && (
        <motion.div
          className="offline-banner"
          initial={{ height: 0, opacity: 0 }}
          animate={{ height: 'auto', opacity: 1 }}
          exit={{ height: 0, opacity: 0 }}
        >
          <span className="offline-icon">📡</span>
          <span className="offline-text">
            Offline mode
            {pendingCount > 0 && ` • ${pendingCount} capture${pendingCount > 1 ? 's' : ''} pending`}
          </span>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

export default OfflineBanner;
