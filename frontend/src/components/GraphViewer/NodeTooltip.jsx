/**
 * Node Tooltip Component
 *
 * Displays information about a node on hover.
 */

import { motion, AnimatePresence } from 'framer-motion'

export function NodeTooltip({ node, position }) {
  // Guard against invalid position values
  if (!node || !position || !Number.isFinite(position.x) || !Number.isFinite(position.y)) {
    return null
  }

  const tags = node.metadata?.tags || []

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.9 }}
        transition={{ duration: 0.15 }}
        className="fixed z-50 pointer-events-none"
        style={{
          left: position.x + 15,
          top: position.y - 10,
        }}
      >
        <div className="bg-slate-900/95 backdrop-blur-md rounded-lg p-3 border border-slate-700/50 shadow-2xl max-w-xs">
          {/* Header */}
          <div className="flex items-start gap-2 mb-2">
            <span className="text-lg">
              {node.type === 'Content' && '📄'}
              {node.type === 'Concept' && '💡'}
              {node.type === 'Note' && '📝'}
            </span>
            <div className="flex-1 min-w-0">
              <h4 className="font-medium text-white text-sm truncate">
                {node.label}
              </h4>
              <p className="text-xs text-slate-400">
                {node.type}
                {node.content_type && ` · ${node.content_type}`}
              </p>
            </div>
          </div>

          {/* Tags */}
          {tags.length > 0 && (
            <div className="flex flex-wrap gap-1 mt-2">
              {tags.slice(0, 3).map((tag) => (
                <span
                  key={tag}
                  className="px-1.5 py-0.5 text-xs bg-slate-800 text-slate-300 rounded"
                >
                  {tag}
                </span>
              ))}
              {tags.length > 3 && (
                <span className="text-xs text-slate-500">
                  +{tags.length - 3} more
                </span>
              )}
            </div>
          )}

          {/* Click hint */}
          <p className="text-xs text-slate-500 mt-2 pt-2 border-t border-slate-700/50">
            Click for details
          </p>
        </div>
      </motion.div>
    </AnimatePresence>
  )
}

export default NodeTooltip

