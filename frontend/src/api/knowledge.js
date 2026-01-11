/**
 * Knowledge Graph API Client
 *
 * Functions for interacting with the Neo4j knowledge graph database.
 * This API provides access to the graph structure, relationships, and analytics.
 * 
 * ## Use Cases
 * - **Graph Visualization**: Fetch nodes and edges for rendering interactive graph views
 * - **Relationship Exploration**: Navigate connections between concepts, topics, and notes
 * - **Semantic Search**: Search across the graph for related concepts
 * - **Topic Hierarchy**: Access hierarchical topic structures for navigation
 * - **Mastery Analytics**: Track learning progress and mastery levels per topic
 * 
 * ## When to Use This vs vaultApi
 * Use `knowledgeApi` when you need:
 * - Graph-based queries (nodes, edges, relationships)
 * - Cross-note connections and link traversal
 * - Topic-level aggregations and statistics
 * - Mastery/learning progress data
 * 
 * Use `vaultApi` instead when you need:
 * - Direct file access to markdown notes
 * - Note content browsing and editing
 * - Folder structure and file metadata
 * - Vault sync operations
 * 
 * @see vaultApi - For direct Obsidian vault file operations
 */

import { typedApi } from './typed-client'

export const knowledgeApi = {
  /**
   * Fetch graph data for visualization
   * @param {Object} params - Query parameters
   * @param {string} [params.center_id] - Center graph on this node ID
   * @param {string} [params.node_types] - Comma-separated node types to include
   * @param {number} [params.depth] - Traversal depth from center node (default: 2)
   * @param {number} [params.limit] - Maximum number of nodes to return
   * @returns {Promise<{nodes: Array<{id: string, label: string, type: string}>, edges: Array<{source: string, target: string, type: string}>}>} Graph data with nodes and edges
   */
  getGraph: (params) => 
    typedApi.GET('/api/knowledge/graph', { params: { query: params } }).then(r => r.data),

  /**
   * Fetch graph statistics
   * @returns {Promise<{node_count: number, edge_count: number, node_types: Object<string, number>, edge_types: Object<string, number>}>} Statistics about the knowledge graph
   */
  getStats: () => 
    typedApi.GET('/api/knowledge/stats').then(r => r.data),

  /**
   * Fetch details for a specific node
   * @param {string} nodeId - The node's unique identifier
   * @returns {Promise<{id: string, label: string, type: string, properties: Object, connections: Array}>} Node details with properties and connections
   */
  getNode: (nodeId) => 
    typedApi.GET('/api/knowledge/node/{node_id}', { 
      params: { path: { node_id: nodeId } } 
    }).then(r => r.data),

  /**
   * Check knowledge graph health
   * @returns {Promise<{status: string, connected: boolean, message?: string}>} Health status of the knowledge graph service
   */
  checkHealth: () => 
    typedApi.GET('/api/knowledge/health').then(r => r.data),

  /**
   * Search nodes by query (semantic search)
   * @param {Object} body - Search parameters
   * @param {string} body.query - Search query string
   * @param {number} [body.limit] - Maximum number of results to return
   * @param {string[]} [body.node_types] - Node types to search
   * @param {number} [body.min_score] - Minimum relevance score
   * @param {boolean} [body.use_vector] - Use vector search
   * @returns {Promise<{results: Array<{id: string, label: string, type: string, score: number}>}>} Search results with relevance scores
   */
  search: (body) => 
    typedApi.POST('/api/knowledge/search', { body }).then(r => r.data),

  /**
   * Get related concepts for a node
   * @param {string} nodeId - The node's unique identifier
   * @param {number} [limit=10] - Maximum number of related nodes to return
   * @returns {Promise<{related: Array<{id: string, label: string, type: string, relationship: string}>}>} Related nodes with relationship types
   */
  getRelated: (nodeId, limit = 10) => 
    typedApi.GET('/api/knowledge/node/{node_id}/related', { 
      params: { path: { node_id: nodeId }, query: { limit } } 
    }).then(r => r.data),

  /**
   * Get connections for a node
   * @param {string} nodeId - The node's unique identifier
   * @param {Object} [params] - Query parameters
   * @param {string} [params.direction] - 'incoming', 'outgoing', or 'both'
   * @param {number} [params.limit] - Maximum connections per direction
   * @returns {Promise<{incoming: Array, outgoing: Array, total: number}>} Node connections
   */
  getConnections: (nodeId, params = {}) =>
    typedApi.GET('/api/knowledge/connections/{node_id}', {
      params: { path: { node_id: nodeId }, query: params }
    }).then(r => r.data),

  /**
   * Get topic hierarchy
   * @param {Object} [params] - Query parameters
   * @param {number} [params.min_content] - Min content count to include
   * @returns {Promise<{topics: Array<{id: string, name: string, parent_id?: string, children?: Array}>}>} Hierarchical topic structure
   */
  getTopics: (params = {}) => 
    typedApi.GET('/api/knowledge/topics', { params: { query: params } }).then(r => r.data),

  /**
   * Get mastery data for topics
   * @param {string} [topicId] - Optional topic ID for specific topic mastery data
   * @returns {Promise<{mastery: number, total_cards: number, mastered_cards: number, topics?: Array<{id: string, name: string, mastery: number}>}>} Mastery statistics for topic(s)
   */
  getMastery: (topicId) => {
    if (topicId) {
      return typedApi.GET('/api/knowledge/mastery/{topic_id}', {
        params: { path: { topic_id: topicId } }
      }).then(r => r.data)
    }
    return typedApi.GET('/api/knowledge/mastery').then(r => r.data)
  },
}

/**
 * Fetch graph data for visualization (legacy export)
 * @param {Object} [options] - Query options
 * @param {string} [options.centerId] - Center graph on this node ID
 * @param {string} [options.nodeTypes] - Comma-separated node types to include
 * @param {number} [options.depth] - Traversal depth from center node
 * @param {number} [options.limit] - Maximum number of nodes to return
 * @returns {Promise<{nodes: Array, edges: Array}>} Graph data with nodes and edges
 */
export async function fetchGraph(options) {
  const params = {}
  if (options?.centerId) params.center_id = options.centerId
  if (options?.nodeTypes) params.node_types = options.nodeTypes
  if (options?.depth) params.depth = options.depth
  if (options?.limit) params.limit = options.limit
  
  return knowledgeApi.getGraph(params)
}

/**
 * Fetch graph statistics (legacy export)
 * @returns {Promise<{node_count: number, edge_count: number, node_types: Object, edge_types: Object}>} Statistics about the knowledge graph
 */
export async function fetchGraphStats() {
  return knowledgeApi.getStats()
}

/**
 * Fetch details for a specific node (legacy export)
 * @param {string} nodeId - The node's unique identifier
 * @returns {Promise<{id: string, label: string, type: string, properties: Object, connections: Array}>} Node details
 */
export async function fetchNodeDetails(nodeId) {
  return knowledgeApi.getNode(nodeId)
}

/**
 * Check knowledge graph health (legacy export)
 * @returns {Promise<{status: string, connected: boolean, message?: string}>} Health status
 */
export async function checkKnowledgeHealth() {
  return knowledgeApi.checkHealth()
}

export default knowledgeApi
