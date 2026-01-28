/**
 * UI Constants
 * 
 * Extracted magic numbers and configuration values for frontend components.
 */

// =============================================================================
// Dashboard
// =============================================================================

/** Default daily review goal (number of cards) */
export const DEFAULT_DAILY_GOAL = 20

// =============================================================================
// Vault / Knowledge
// =============================================================================

/** Page size for fetching vault notes (used in pagination) */
export const VAULT_PAGE_SIZE = 200

// =============================================================================
// Knowledge Graph
// =============================================================================

/** Default graph container dimensions (pixels) */
export const DEFAULT_GRAPH_WIDTH = 800
export const DEFAULT_GRAPH_HEIGHT = 600

/** Maximum number of nodes to fetch for graph display */
export const GRAPH_NODE_LIMIT = 200

/** D3 force simulation parameters */
export const GRAPH_CHARGE_STRENGTH = -300
export const GRAPH_CHARGE_DISTANCE_MAX = 400
export const GRAPH_LINK_DISTANCE = 100

// =============================================================================
// Z-Index Layers
// =============================================================================

/**
 * Z-index values for layered UI elements.
 * Using a scale to ensure consistent stacking order.
 */
export const Z_INDEX = {
  /** Base level for most content */
  BASE: 0,
  /** Dropdowns, popovers */
  DROPDOWN: 50,
  /** Fixed headers, footers */
  STICKY: 100,
  /** Modal backdrops */
  MODAL_BACKDROP: 1000,
  /** Modal content */
  MODAL: 1001,
  /** Tooltips - highest layer */
  TOOLTIP: 9999,
}
