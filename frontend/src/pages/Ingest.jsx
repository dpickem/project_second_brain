/**
 * Ingest Page
 *
 * Unified page for content capture and ingestion queue monitoring.
 * Available at the /ingest route.
 *
 * Features:
 * - Tabbed capture panel: Text, URL, File Upload
 * - Live ingestion queue with status filtering
 * - Auto-refreshing queue (10s polling)
 * - Click-to-expand item detail with processing stages and errors
 * - Link to Knowledge Explorer for processed items
 */

import { motion } from 'framer-motion'
import { CapturePanel, IngestionQueue } from '../components/ingest'
import { staggerContainer, fadeInUp } from '../utils/animations'

export function Ingest() {
  return (
    <motion.div
      variants={staggerContainer}
      initial="hidden"
      animate="show"
      className="space-y-6"
    >
      {/* Page header */}
      <motion.div variants={fadeInUp}>
        <h1 className="text-2xl font-bold text-text-primary font-heading">
          Ingest
        </h1>
        <p className="text-sm text-text-secondary mt-1">
          Capture new content and monitor the ingestion pipeline.
        </p>
      </motion.div>

      {/* Capture panel */}
      <motion.div variants={fadeInUp}>
        <CapturePanel />
      </motion.div>

      {/* Ingestion queue */}
      <motion.div variants={fadeInUp} className="min-h-[400px]">
        <IngestionQueue />
      </motion.div>
    </motion.div>
  )
}

export default Ingest
