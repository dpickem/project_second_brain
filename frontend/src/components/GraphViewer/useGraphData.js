/**
 * Graph Data Fetching Hook
 *
 * React Query hook for fetching and caching graph data.
 */

import { useQuery } from '@tanstack/react-query'
import { fetchGraph } from '../../api/knowledge'

/**
 * Hook for fetching graph data with React Query
 *
 * @param {string|null} centerId - Optional node ID to center the graph on
 * @param {Object} options - Additional query options
 * @param {string} [options.nodeTypes] - Comma-separated node types
 * @param {number} [options.depth] - Traversal depth from center
 * @param {number} [options.limit] - Max nodes to return
 * @returns {Object} React Query result with graph data
 */
export function useGraphData(centerId = null, options = {}) {
  return useQuery({
    queryKey: ['graph', centerId, options],
    queryFn: () => fetchGraph({ centerId, ...options }),
    staleTime: 30_000, // Cache for 30 seconds
    refetchOnWindowFocus: false,
    select: (data) => ({
      nodes: data.nodes || [],
      links: (data.edges || []).map((e) => ({
        source: e.source,
        target: e.target,
        type: e.type,
        strength: e.strength,
      })),
      totalNodes: data.total_nodes,
      totalEdges: data.total_edges,
    }),
  })
}

export default useGraphData

