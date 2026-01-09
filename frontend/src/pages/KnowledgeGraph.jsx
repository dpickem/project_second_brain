/**
 * Knowledge Graph Page
 *
 * Full-page graph visualization with stats sidebar and node details panel.
 */

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { GraphViewer } from '../components/GraphViewer'
import { fetchGraphStats, fetchNodeDetails } from '../api/knowledge'

// Stat item component
function StatItem({ icon, label, value, color = 'text-white' }) {
  return (
    <div className="flex items-center justify-between">
      <span className="flex items-center gap-2 text-slate-400">
        <span>{icon}</span>
        {label}
      </span>
      <span className={`font-semibold ${color}`}>{value}</span>
    </div>
  )
}

// Node details panel
function NodeDetailsPanel({ nodeId, onClose, onViewInVault }) {
  const { data: node, isLoading } = useQuery({
    queryKey: ['node-details', nodeId],
    queryFn: () => fetchNodeDetails(nodeId),
    enabled: !!nodeId,
  })

  if (!nodeId) return null

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: 20 }}
      className="absolute bottom-4 left-1/2 -translate-x-1/2 bg-slate-800/95 backdrop-blur-md rounded-xl border border-slate-700/50 shadow-2xl max-w-2xl w-full mx-4"
    >
      <div className="p-4">
        {isLoading ? (
          <div className="flex items-center gap-3">
            <div className="w-5 h-5 border-2 border-indigo-500/30 border-t-indigo-500 rounded-full animate-spin" />
            <span className="text-slate-400">Loading...</span>
          </div>
        ) : node ? (
          <div className="flex items-start gap-4">
            {/* Icon */}
            <div
              className="w-12 h-12 rounded-lg flex items-center justify-center text-2xl"
              style={{
                backgroundColor:
                  node.type === 'Content'
                    ? '#818cf820'
                    : node.type === 'Concept'
                    ? '#34d39920'
                    : '#fbbf2420',
              }}
            >
              {node.type === 'Content' && '📄'}
              {node.type === 'Concept' && '💡'}
              {node.type === 'Note' && '📝'}
            </div>

            {/* Content */}
            <div className="flex-1 min-w-0">
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0 flex-1">
                  <h3 className="text-lg font-semibold text-white leading-tight">
                    {node.label}
                  </h3>
                  <p className="text-sm text-slate-400">
                    {node.type}
                    {node.content_type && ` · ${node.content_type}`}
                    {node.connections > 0 && ` · ${node.connections} connections`}
                  </p>
                </div>
                <button
                  onClick={onClose}
                  className="flex-shrink-0 p-1.5 text-slate-400 hover:text-white hover:bg-slate-700 rounded-lg transition-colors"
                >
                  <svg
                    className="w-5 h-5"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M6 18L18 6M6 6l12 12"
                    />
                  </svg>
                </button>
              </div>

              {/* Summary */}
              {node.summary && (
                <p className="mt-2 text-sm text-slate-300 line-clamp-2">
                  {node.summary}
                </p>
              )}

              {/* Tags */}
              {node.tags?.length > 0 && (
                <div className="flex flex-wrap gap-1.5 mt-3">
                  {node.tags.map((tag) => (
                    <span
                      key={tag}
                      className="px-2 py-0.5 text-xs bg-slate-700 text-slate-300 rounded-full"
                    >
                      {tag}
                    </span>
                  ))}
                </div>
              )}

              {/* Actions */}
              <div className="flex gap-2 mt-3 pt-3 border-t border-slate-700/50">
                {node.source_url && (
                  <a
                    href={node.source_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="px-3 py-1.5 text-sm bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg transition-colors"
                  >
                    Open Source
                  </a>
                )}
                <button
                  onClick={() => onViewInVault(node)}
                  className="px-3 py-1.5 text-sm bg-slate-700 hover:bg-slate-600 text-white rounded-lg transition-colors"
                >
                  View Note
                </button>
              </div>
            </div>
          </div>
        ) : (
          <p className="text-slate-400">Node not found</p>
        )}
      </div>
    </motion.div>
  )
}

export default function KnowledgeGraphPage() {
  const navigate = useNavigate()
  const [selectedNode, setSelectedNode] = useState(null)
  const [centerId, setCenterId] = useState(null)

  const { data: stats, isLoading: statsLoading } = useQuery({
    queryKey: ['graph-stats'],
    queryFn: fetchGraphStats,
    staleTime: 60_000, // Cache for 1 minute
  })

  const handleNodeClick = (node) => {
    setSelectedNode(node)
  }

  const handleCenterOnNode = () => {
    if (selectedNode) {
      setCenterId(selectedNode.id)
    }
  }

  const handleResetCenter = () => {
    setCenterId(null)
  }

  const handleViewInVault = (node) => {
    // For any node with a file_path, navigate directly to the note
    if (node.file_path) {
      const notePath = node.file_path.endsWith('.md') ? node.file_path : `${node.file_path}.md`
      navigate(`/knowledge?note=${encodeURIComponent(notePath)}`)
    } else {
      // Fallback: search by label for nodes without file_path
      const searchTerm = node.label || node.name || node.id
      navigate(`/knowledge?search=${encodeURIComponent(searchTerm)}`)
    }
  }

  return (
    <div className="h-screen flex flex-col bg-slate-950">
      {/* Header */}
      <header className="flex-shrink-0 px-6 py-4 bg-slate-900/80 backdrop-blur-sm border-b border-slate-800">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <h1 className="text-2xl font-bold text-white flex items-center gap-3">
              <span className="w-10 h-10 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-lg flex items-center justify-center">
                <svg
                  className="w-6 h-6 text-white"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  {/* Network/graph nodes */}
                  <circle cx="5" cy="6" r="2" strokeWidth={2} />
                  <circle cx="12" cy="4" r="2" strokeWidth={2} />
                  <circle cx="19" cy="8" r="2" strokeWidth={2} />
                  <circle cx="6" cy="18" r="2" strokeWidth={2} />
                  <circle cx="18" cy="18" r="2" strokeWidth={2} />
                  <circle cx="12" cy="12" r="2.5" strokeWidth={2} />
                  {/* Connections */}
                  <path strokeLinecap="round" strokeWidth={1.5} d="M7 7l3.5 3.5M14.5 10l3-1M9.5 12.5l-2 4M14.5 13.5l2 3" />
                </svg>
              </span>
              Knowledge Graph
            </h1>
            {centerId && (
              <button
                onClick={handleResetCenter}
                className="flex items-center gap-1.5 px-3 py-1.5 text-sm bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg transition-colors"
              >
                <svg
                  className="w-4 h-4"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M6 18L18 6M6 6l12 12"
                  />
                </svg>
                Clear Focus
              </button>
            )}
          </div>
          <div className="flex items-center gap-3">
            {selectedNode && (
              <button
                onClick={handleCenterOnNode}
                className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg transition-colors flex items-center gap-2"
              >
                <svg
                  className="w-4 h-4"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
                  />
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"
                  />
                </svg>
                Focus on Node
              </button>
            )}
          </div>
        </div>
      </header>

      {/* Main Content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Graph Area - uses absolute positioning for full size */}
        <main className="flex-1 relative min-w-0">
          <GraphViewer
            onNodeClick={handleNodeClick}
            limit={200}
          />

          {/* Selected Node Details */}
          <AnimatePresence>
            {selectedNode && (
              <NodeDetailsPanel
                nodeId={selectedNode.id}
                onClose={() => setSelectedNode(null)}
                onViewInVault={handleViewInVault}
              />
            )}
          </AnimatePresence>
        </main>

        {/* Stats Sidebar */}
        <aside className="w-72 flex-shrink-0 bg-slate-900 border-l border-slate-800 p-5 overflow-y-auto">
          <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
            <svg
              className="w-5 h-5 text-indigo-400"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
              />
            </svg>
            Statistics
          </h2>

          {statsLoading ? (
            <div className="space-y-3">
              {[1, 2, 3, 4].map((i) => (
                <div
                  key={i}
                  className="h-6 bg-slate-800 rounded animate-pulse"
                />
              ))}
            </div>
          ) : stats ? (
            <div className="space-y-4">
              <div className="space-y-2.5">
                <StatItem
                  icon="📄"
                  label="Content"
                  value={stats.total_content}
                  color="text-indigo-400"
                />
                <StatItem
                  icon="💡"
                  label="Concepts"
                  value={stats.total_concepts}
                  color="text-emerald-400"
                />
                <StatItem
                  icon="📝"
                  label="Notes"
                  value={stats.total_notes}
                  color="text-amber-400"
                />
                <StatItem
                  icon="🔗"
                  label="Relationships"
                  value={stats.total_relationships}
                  color="text-slate-300"
                />
              </div>

              {Object.keys(stats.content_by_type).length > 0 && (
                <>
                  <hr className="border-slate-800" />
                  <div>
                    <h3 className="text-sm font-medium text-slate-400 mb-2.5">
                      Content by Type
                    </h3>
                    <div className="space-y-2">
                      {Object.entries(stats.content_by_type)
                        .sort((a, b) => b[1] - a[1])
                        .map(([type, count]) => (
                          <div
                            key={type}
                            className="flex justify-between text-sm"
                          >
                            <span className="text-slate-400 capitalize">
                              {type}
                            </span>
                            <span className="text-slate-300">{count}</span>
                          </div>
                        ))}
                    </div>
                  </div>
                </>
              )}

              <hr className="border-slate-800" />

              {/* Quick tips */}
              <div className="bg-slate-800/50 rounded-lg p-3">
                <h3 className="text-sm font-medium text-slate-300 mb-2">
                  💡 Quick Tips
                </h3>
                <ul className="text-xs text-slate-400 space-y-1.5">
                  <li>• Drag nodes to rearrange</li>
                  <li>• Scroll to zoom in/out</li>
                  <li>• Click a node for details</li>
                  <li>• Use &quot;Focus on Node&quot; to explore connections</li>
                </ul>
              </div>
            </div>
          ) : (
            <p className="text-slate-400 text-sm">Failed to load statistics</p>
          )}
        </aside>
      </div>
    </div>
  )
}

