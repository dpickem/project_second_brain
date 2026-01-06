/**
 * Knowledge Graph API Client
 *
 * Functions for fetching graph data and statistics from the backend.
 */

import axios from 'axios'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

/**
 * Fetch graph data for visualization
 *
 * @param {Object} options - Query options
 * @param {string} [options.centerId] - Center graph on this node ID
 * @param {string} [options.nodeTypes] - Comma-separated node types
 * @param {number} [options.depth] - Traversal depth from center
 * @param {number} [options.limit] - Max nodes to return
 * @returns {Promise<{nodes: Array, edges: Array, total_nodes: number, total_edges: number}>}
 */
export async function fetchGraph({ centerId, nodeTypes, depth, limit } = {}) {
  const params = new URLSearchParams()
  if (centerId) params.set('center_id', centerId)
  if (nodeTypes) params.set('node_types', nodeTypes)
  if (depth) params.set('depth', depth)
  if (limit) params.set('limit', limit)

  const url = `${API_URL}/api/knowledge/graph${params.toString() ? '?' + params : ''}`
  const response = await axios.get(url)
  return response.data
}

/**
 * Fetch graph statistics
 *
 * @returns {Promise<{total_content: number, total_concepts: number, total_notes: number, total_relationships: number, content_by_type: Object}>}
 */
export async function fetchGraphStats() {
  const response = await axios.get(`${API_URL}/api/knowledge/stats`)
  return response.data
}

/**
 * Fetch details for a specific node
 *
 * @param {string} nodeId - The node's unique identifier
 * @returns {Promise<{id: string, label: string, type: string, content_type?: string, summary?: string, tags: string[], connections: number}>}
 */
export async function fetchNodeDetails(nodeId) {
  const response = await axios.get(`${API_URL}/api/knowledge/node/${nodeId}`)
  return response.data
}

/**
 * Check knowledge graph health
 *
 * @returns {Promise<{status: string, neo4j_connected: boolean}>}
 */
export async function checkKnowledgeHealth() {
  const response = await axios.get(`${API_URL}/api/knowledge/health`)
  return response.data
}

