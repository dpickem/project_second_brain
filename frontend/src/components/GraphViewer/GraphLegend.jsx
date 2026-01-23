/**
 * Graph Legend Component
 *
 * Displays color legend for node types.
 */

import { motion } from 'framer-motion'

const NODE_TYPES = [
  { type: 'Content', color: '#818cf8', icon: '📄', description: 'Processed content' },
  { type: 'Concept', color: '#34d399', icon: '💡', description: 'Extracted concepts' },
  { type: 'Note', color: '#fbbf24', icon: '📝', description: 'Vault notes' },
]

export function GraphLegend() {
  return (
    <motion.div
      initial={{ opacity: 0, x: -20 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: 0.3 }}
      className="absolute bottom-4 left-4 bg-slate-900/90 backdrop-blur-sm rounded-lg p-3 border border-slate-700/50 shadow-xl"
    >
      <div className="space-y-2">
        {NODE_TYPES.map(({ type, color, icon, description }) => (
          <div key={type} className="flex items-center gap-2.5">
            <div
              className="w-3.5 h-3.5 rounded-full shadow-lg flex-shrink-0"
              style={{
                backgroundColor: color,
                boxShadow: `0 0 8px ${color}66`,
              }}
            />
            <div className="flex items-center gap-1.5">
              <span className="text-base">{icon}</span>
              <span className="text-sm text-slate-300">{type}</span>
            </div>
          </div>
        ))}
      </div>
    </motion.div>
  )
}

export default GraphLegend

