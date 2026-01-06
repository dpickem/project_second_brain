/**
 * Graph Legend Component
 *
 * Displays color legend for different node types.
 */

import { motion } from 'framer-motion'

const NODE_TYPES = [
  { type: 'Content', color: '#818cf8', icon: '📄' },
  { type: 'Concept', color: '#34d399', icon: '💡' },
  { type: 'Note', color: '#fbbf24', icon: '📝' },
]

const CONTENT_TYPES = [
  { type: 'paper', color: '#a78bfa', icon: '📑' },
  { type: 'article', color: '#60a5fa', icon: '📰' },
  { type: 'book', color: '#f472b6', icon: '📚' },
  { type: 'code', color: '#2dd4bf', icon: '💻' },
  { type: 'idea', color: '#fb923c', icon: '💭' },
]

export function GraphLegend({ showContentTypes = false }) {
  return (
    <motion.div
      initial={{ opacity: 0, x: -20 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: 0.3 }}
      className="absolute bottom-4 left-4 bg-slate-900/90 backdrop-blur-sm rounded-lg p-3 border border-slate-700/50 shadow-xl"
    >
      <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
        Node Types
      </h3>
      <div className="space-y-1.5">
        {NODE_TYPES.map(({ type, color, icon }) => (
          <div key={type} className="flex items-center gap-2">
            <div
              className="w-3 h-3 rounded-full shadow-lg"
              style={{
                backgroundColor: color,
                boxShadow: `0 0 8px ${color}66`,
              }}
            />
            <span className="text-sm text-slate-300">
              {icon} {type}
            </span>
          </div>
        ))}
      </div>

      {showContentTypes && (
        <>
          <div className="border-t border-slate-700/50 my-2" />
          <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
            Content Types
          </h3>
          <div className="space-y-1.5">
            {CONTENT_TYPES.map(({ type, color, icon }) => (
              <div key={type} className="flex items-center gap-2">
                <div
                  className="w-2.5 h-2.5 rounded-full"
                  style={{ backgroundColor: color }}
                />
                <span className="text-xs text-slate-400">
                  {icon} {type}
                </span>
              </div>
            ))}
          </div>
        </>
      )}
    </motion.div>
  )
}

export default GraphLegend

