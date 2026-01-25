import { motion } from 'framer-motion';

/**
 * Large, touch-friendly capture button for mobile.
 * Designed for quick one-handed access with 56px+ touch targets.
 */
export function CaptureButton({ icon, label, onClick, disabled = false }) {
  return (
    <motion.button
      className="capture-button"
      onClick={onClick}
      disabled={disabled}
      whileTap={{ scale: 0.95 }}
      whileHover={{ scale: 1.02 }}
    >
      <span className="capture-button-icon">{icon}</span>
      <span className="capture-button-label">{label}</span>
    </motion.button>
  );
}

export default CaptureButton;
