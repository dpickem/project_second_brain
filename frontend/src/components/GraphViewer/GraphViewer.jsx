/**
 * Graph Viewer Component
 *
 * Simple, stable force-directed graph visualization.
 * Prioritizes usability over fancy effects.
 * Supports node dragging with position persistence.
 */

import { useCallback, useRef, useState, useEffect, useMemo } from 'react'
import ForceGraph2D from 'react-force-graph-2d'
import * as d3 from 'd3'
import { useGraphData } from './useGraphData'
import { GraphLegend } from './GraphLegend'
import {
  DEFAULT_GRAPH_WIDTH,
  DEFAULT_GRAPH_HEIGHT,
  GRAPH_CHARGE_STRENGTH,
  GRAPH_CHARGE_DISTANCE_MAX,
  GRAPH_LINK_DISTANCE,
} from '../../constants'

// Node colors by type - single unified color scheme
const NODE_COLORS = {
  Content: '#818cf8', // Indigo - processed content (papers, articles, books, etc.)
  Concept: '#34d399', // Emerald - extracted concepts
  Note: '#fbbf24',    // Amber - vault notes
}

function GraphSkeleton() {
  return (
    <div className="absolute inset-0 flex items-center justify-center bg-slate-900">
      <div className="text-center">
        <div className="w-12 h-12 border-4 border-indigo-500/30 border-t-indigo-500 rounded-full animate-spin mx-auto mb-4" />
        <p className="text-slate-400">Loading graph...</p>
      </div>
    </div>
  )
}

function GraphError({ error, onRetry }) {
  return (
    <div className="absolute inset-0 flex items-center justify-center bg-slate-900">
      <div className="text-center">
        <p className="text-red-400 mb-4">{error?.message || 'Failed to load graph'}</p>
        <button
          onClick={onRetry}
          className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg"
        >
          Retry
        </button>
      </div>
    </div>
  )
}

function EmptyGraph({ message = 'No nodes in the graph yet' }) {
  return (
    <div className="absolute inset-0 flex items-center justify-center bg-slate-900">
      <div className="text-center">
        <p className="text-slate-400">{message}</p>
      </div>
    </div>
  )
}

export function GraphViewer({
  centerId = null,
  onNodeClick,
  nodeTypes = 'Content,Concept,Note',
  limit = 150,
  showLegend = true,
  highlightedNodeIds = null, // Set of node IDs to highlight from search
}) {
  const graphRef = useRef()
  const containerRef = useRef()
  const dimensionsRef = useRef({ width: DEFAULT_GRAPH_WIDTH, height: DEFAULT_GRAPH_HEIGHT })
  const [dimensions, setDimensions] = useState({ width: DEFAULT_GRAPH_WIDTH, height: DEFAULT_GRAPH_HEIGHT })
  const [selectedNodeId, setSelectedNodeId] = useState(null)
  const dataIdRef = useRef(null) // Track which data we've initialized
  const stableDataRef = useRef(null) // Store stable graph data reference
  const simulationFrozenRef = useRef(false)

  const { data: rawData, isLoading, error, refetch } = useGraphData(centerId, {
    nodeTypes,
    limit,
  })
  
  // Create a stable data reference that only updates when node IDs actually change
  // This prevents the graph from resetting when parent components re-render
  const data = useMemo(() => {
    if (!rawData) return stableDataRef.current
    
    // Generate a unique ID for this dataset
    const newDataId = rawData.nodes.map(n => n.id).sort().join(',')
    
    // If it's the same data, return the existing stable reference
    if (dataIdRef.current === newDataId && stableDataRef.current) {
      return stableDataRef.current
    }
    
    // New data - update the stable reference
    stableDataRef.current = rawData
    return rawData
  }, [rawData])

  // Compute connected nodes and links when a node is selected
  const { connectedNodeIds, connectedLinkIds } = useMemo(() => {
    if (!selectedNodeId || !data?.links) {
      return { connectedNodeIds: new Set(), connectedLinkIds: new Set() }
    }
    
    const nodeIds = new Set()
    const linkIds = new Set()
    
    data.links.forEach((link, index) => {
      const sourceId = typeof link.source === 'object' ? link.source.id : link.source
      const targetId = typeof link.target === 'object' ? link.target.id : link.target
      
      if (sourceId === selectedNodeId || targetId === selectedNodeId) {
        nodeIds.add(sourceId)
        nodeIds.add(targetId)
        linkIds.add(index)
      }
    })
    
    return { connectedNodeIds: nodeIds, connectedLinkIds: linkIds }
  }, [selectedNodeId, data?.links])

  // Measure container on mount only (not on every resize)
  useEffect(() => {
    const measure = () => {
      if (containerRef.current) {
        const rect = containerRef.current.getBoundingClientRect()
        // Only update if significantly different (avoid micro-adjustments)
        if (
          Math.abs(rect.width - dimensionsRef.current.width) > 50 ||
          Math.abs(rect.height - dimensionsRef.current.height) > 50
        ) {
          dimensionsRef.current = { width: rect.width, height: rect.height }
          setDimensions({ width: rect.width, height: rect.height })
        }
      }
    }

    // Initial measure
    setTimeout(measure, 50)
    
    // Only observe for major layout changes
    const observer = new ResizeObserver(measure)
    if (containerRef.current) {
      observer.observe(containerRef.current)
    }

    return () => observer.disconnect()
  }, [])

  // Configure d3 forces for good spread when data loads
  useEffect(() => {
    if (!graphRef.current || !data?.nodes?.length) return
    
    // Create a unique ID for this dataset
    const newDataId = data.nodes.map(n => n.id).sort().join(',')
    
    // Only configure if this is new data
    if (dataIdRef.current === newDataId) return
    dataIdRef.current = newDataId
    simulationFrozenRef.current = false
    
    const fg = graphRef.current
    
    // Configure forces for good spread
    fg.d3Force('charge')?.strength(GRAPH_CHARGE_STRENGTH)?.distanceMax(GRAPH_CHARGE_DISTANCE_MAX)
    fg.d3Force('link')?.distance(GRAPH_LINK_DISTANCE)
    fg.d3Force('center')?.strength(0.03)
    
    // Add collision force to prevent overlap - larger radius for labels
    fg.d3Force('collision', d3.forceCollide().radius(40).strength(1.0))
  }, [data])

  // Fit to view once when simulation ends, then reduce to link-only forces
  const handleEngineStop = useCallback(() => {
    if (graphRef.current && !simulationFrozenRef.current) {
      simulationFrozenRef.current = true
      
      const fg = graphRef.current
      
      // Disable charge force (causes phantom edges between unconnected nodes)
      // Keep link force so connected nodes follow when dragged, but very weak
      if (fg.d3Force) {
        fg.d3Force('charge', null)
        fg.d3Force('center', null)
        fg.d3Force('collision', null)
        // Very weak link force - just a gentle pull, not collapse
        fg.d3Force('link')?.strength(0.005)?.distance(100)
      }
    }
  }, [])
  
  // Handle node drag start - fix the node position during drag
  const handleNodeDragStart = useCallback((node) => {
    // Fix node position during drag
    node.fx = node.x
    node.fy = node.y
  }, [])
  
  // Handle node drag - update fixed position and reheat slightly
  const handleNodeDrag = useCallback((node, translate) => {
    node.fx = translate.x
    node.fy = translate.y
    // Continuous small reheat during drag so connected nodes follow
    if (graphRef.current) {
      graphRef.current.d3ReheatSimulation()
    }
  }, [])
  
  // Handle node drag end - keep position fixed
  const handleNodeDragEnd = useCallback((node) => {
    // Keep the node fixed at its new position
    node.fx = node.x
    node.fy = node.y
  }, [])

  // Unfreeze all nodes and reheat simulation for reorganization
  const handleUnfreezeNodes = useCallback(() => {
    if (!graphRef.current || !data?.nodes) return
    
    const fg = graphRef.current
    
    // Unfreeze all nodes
    data.nodes.forEach(node => {
      node.fx = undefined
      node.fy = undefined
    })
    
    // Restore forces for reorganization
    fg.d3Force('charge', d3.forceManyBody().strength(-300).distanceMax(400))
    fg.d3Force('link', d3.forceLink(data.links).id(d => d.id).distance(100).strength(0.5))
    fg.d3Force('center', d3.forceCenter(dimensions.width / 2, dimensions.height / 2).strength(0.03))
    fg.d3Force('collision', d3.forceCollide().radius(40).strength(1.0))
    
    // Reset the frozen flag so handleEngineStop will freeze again when done
    simulationFrozenRef.current = false
    
    // Reheat the simulation
    fg.d3ReheatSimulation()
  }, [data?.nodes, data?.links, dimensions.width, dimensions.height])

  // Get node color - simple lookup by node type
  const getNodeColor = useCallback((node) => {
    return NODE_COLORS[node.type] || '#94a3b8'
  }, [])

  // Helper to wrap text into lines that fit within maxWidth
  const wrapText = useCallback((ctx, text, maxWidth) => {
    const words = text.split(' ')
    const lines = []
    let currentLine = ''
    
    for (const word of words) {
      const testLine = currentLine ? `${currentLine} ${word}` : word
      if (ctx.measureText(testLine).width > maxWidth && currentLine) {
        lines.push(currentLine)
        currentLine = word
      } else {
        currentLine = testLine
      }
    }
    if (currentLine) lines.push(currentLine)
    
    // Limit to 2 lines max, truncate last line if needed
    if (lines.length > 2) {
      lines.length = 2
      lines[1] = lines[1].slice(0, -1) + '…'
    }
    
    return lines
  }, [])

  // Node rendering with wrapped text
  const nodeCanvasObject = useCallback((node, ctx, globalScale) => {
    if (!Number.isFinite(node.x) || !Number.isFinite(node.y)) return

    const color = getNodeColor(node)
    const isSelected = node.id === selectedNodeId
    const isConnected = connectedNodeIds.has(node.id)
    const isHighlighted = highlightedNodeIds?.has(node.id)
    const hasSelection = selectedNodeId !== null
    const hasHighlights = highlightedNodeIds !== null && highlightedNodeIds.size > 0
    
    // Determine opacity and size based on selection/highlight state
    // If there's a search (highlights), dim non-highlighted nodes
    // If there's a selection, dim non-connected nodes
    const isDimmed = (hasHighlights && !isHighlighted && !isSelected) ||
                     (hasSelection && !hasHighlights && !isSelected && !isConnected)
    const opacity = isDimmed ? 0.15 : 1
    const radius = isSelected ? 10 : isHighlighted ? 9 : isConnected ? 8 : 6

    // Draw glow for selected/connected/highlighted nodes
    if (isSelected || isConnected || isHighlighted) {
      ctx.beginPath()
      ctx.arc(node.x, node.y, radius + 4, 0, 2 * Math.PI)
      ctx.fillStyle = isSelected 
        ? `rgba(251, 191, 36, 0.3)` // golden glow for selected
        : isHighlighted
        ? `rgba(236, 72, 153, 0.35)` // pink glow for search matches
        : `rgba(129, 140, 248, 0.25)` // indigo glow for connected
      ctx.fill()
    }

    // Draw node
    ctx.beginPath()
    ctx.arc(node.x, node.y, radius, 0, 2 * Math.PI)
    ctx.globalAlpha = opacity
    ctx.fillStyle = isHighlighted ? '#ec4899' : color // Pink for highlighted nodes
    ctx.fill()
    
    // Add ring for selected or highlighted node
    if (isSelected) {
      ctx.strokeStyle = '#fbbf24'
      ctx.lineWidth = 2
      ctx.stroke()
    } else if (isHighlighted) {
      ctx.strokeStyle = '#f472b6'
      ctx.lineWidth = 2
      ctx.stroke()
    }
    
    ctx.globalAlpha = 1

    // Draw label if zoomed in enough or if node is highlighted
    if (globalScale > 0.5 || isHighlighted) {
      const label = node.label || node.id || ''
      const fontSize = isHighlighted 
        ? Math.min(Math.max(11 / globalScale, 4), 11) // Larger font for highlighted
        : Math.min(Math.max(9 / globalScale, 3), 9)
      const maxWidth = 70 // pixels for text wrapping
      
      ctx.font = isHighlighted ? `bold ${fontSize}px sans-serif` : `${fontSize}px sans-serif`
      ctx.textAlign = 'center'
      ctx.globalAlpha = isDimmed ? 0.2 : 1
      ctx.fillStyle = isSelected ? '#fbbf24' : isHighlighted ? '#f9a8d4' : '#e2e8f0'
      
      // Wrap text into lines
      const lines = wrapText(ctx, label, maxWidth)
      const lineHeight = fontSize * 1.2
      
      // Add text shadow for better readability
      ctx.shadowColor = 'rgba(0, 0, 0, 0.9)'
      ctx.shadowBlur = 3
      
      // Draw each line
      lines.forEach((line, i) => {
        const y = node.y + radius + fontSize + 2 + (i * lineHeight)
        ctx.fillText(line, node.x, y)
      })
      
      ctx.shadowBlur = 0
      ctx.globalAlpha = 1
    }
  }, [getNodeColor, wrapText, selectedNodeId, connectedNodeIds, highlightedNodeIds])

  // Handle click - toggle selection and notify parent
  const handleClick = useCallback((node) => {
    setSelectedNodeId(prev => prev === node.id ? null : node.id)
    if (onNodeClick) {
      onNodeClick(node)
    }
  }, [onNodeClick])

  // Handle background click to deselect
  const handleBackgroundClick = useCallback(() => {
    setSelectedNodeId(null)
  }, [])

  // Link color based on selection
  const getLinkColor = useCallback((link) => {
    if (!selectedNodeId) return '#475569'
    
    const sourceId = typeof link.source === 'object' ? link.source.id : link.source
    const targetId = typeof link.target === 'object' ? link.target.id : link.target
    
    if (sourceId === selectedNodeId || targetId === selectedNodeId) {
      return '#818cf8' // Bright indigo for connected links
    }
    return 'rgba(71, 85, 105, 0.15)' // Dimmed for non-connected
  }, [selectedNodeId])

  // Link width based on selection
  const getLinkWidth = useCallback((link) => {
    if (!selectedNodeId) return 1
    
    const sourceId = typeof link.source === 'object' ? link.source.id : link.source
    const targetId = typeof link.target === 'object' ? link.target.id : link.target
    
    if (sourceId === selectedNodeId || targetId === selectedNodeId) {
      return 2.5 // Thicker for connected links
    }
    return 0.5 // Thinner for non-connected
  }, [selectedNodeId])

  // Handle empty filter selection
  if (!nodeTypes) {
    return <div ref={containerRef} className="absolute inset-0"><EmptyGraph message="Select at least one node type to display" /></div>
  }
  if (isLoading) return <div ref={containerRef} className="absolute inset-0"><GraphSkeleton /></div>
  if (error) return <div ref={containerRef} className="absolute inset-0"><GraphError error={error} onRetry={refetch} /></div>
  if (!data?.nodes?.length) return <div ref={containerRef} className="absolute inset-0"><EmptyGraph /></div>

  return (
    <div 
      ref={containerRef} 
      className="absolute inset-0 bg-slate-900"
      style={{ background: 'radial-gradient(ellipse at center, #1e293b 0%, #0f172a 70%)' }}
    >
      <ForceGraph2D
        ref={graphRef}
        width={dimensions.width}
        height={dimensions.height}
        graphData={data}
        nodeCanvasObject={nodeCanvasObject}
        nodePointerAreaPaint={(node, color, ctx) => {
          if (!Number.isFinite(node.x) || !Number.isFinite(node.y)) return
          ctx.fillStyle = color
          ctx.beginPath()
          ctx.arc(node.x, node.y, 15, 0, 2 * Math.PI)
          ctx.fill()
        }}
        linkColor={getLinkColor}
        linkWidth={getLinkWidth}
        onNodeClick={handleClick}
        onBackgroundClick={handleBackgroundClick}
        onEngineStop={handleEngineStop}
        // Node dragging handlers
        onNodeDragStart={handleNodeDragStart}
        onNodeDrag={handleNodeDrag}
        onNodeDragEnd={handleNodeDragEnd}
        // Simulation settings - run once then settle
        cooldownTicks={100}
        cooldownTime={1500}
        warmupTicks={50}
        d3AlphaMin={0.001}
        d3AlphaDecay={0.05}
        d3VelocityDecay={0.4}
        // Enable node dragging for manual arrangement
        enableNodeDrag={true}
        enablePointerInteraction={true}
        enableZoomInteraction={true}
        enablePanInteraction={true}
        // Prevent any automatic zooming/centering
        autoPauseRedraw={false}
        minZoom={0.3}
        maxZoom={8}
        backgroundColor="transparent"
      />

      {/* Legend */}
      {showLegend && <GraphLegend />}

      {/* Node count */}
      <div className="absolute top-4 left-4 bg-slate-900/90 rounded-lg px-3 py-1.5 border border-slate-700/50">
        <span className="text-sm text-slate-400">
          {data.nodes.length} nodes · {data.links.length} connections
        </span>
      </div>

      {/* Controls */}
      <div className="absolute top-4 right-4 flex flex-col gap-2">
        <button
          onClick={handleUnfreezeNodes}
          className="w-8 h-8 bg-slate-800 hover:bg-slate-700 rounded-lg flex items-center justify-center text-slate-400 hover:text-white border border-slate-700"
          title="Reorganize layout (unfreeze all nodes)"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
        </button>
        <button
          onClick={() => graphRef.current?.zoomToFit(300, 50)}
          className="w-8 h-8 bg-slate-800 hover:bg-slate-700 rounded-lg flex items-center justify-center text-slate-400 hover:text-white border border-slate-700"
          title="Fit to view"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4" />
          </svg>
        </button>
        <button
          onClick={() => graphRef.current?.zoom(graphRef.current.zoom() * 1.5, 300)}
          className="w-8 h-8 bg-slate-800 hover:bg-slate-700 rounded-lg flex items-center justify-center text-slate-400 hover:text-white border border-slate-700"
          title="Zoom in"
        >
          +
        </button>
        <button
          onClick={() => graphRef.current?.zoom(graphRef.current.zoom() / 1.5, 300)}
          className="w-8 h-8 bg-slate-800 hover:bg-slate-700 rounded-lg flex items-center justify-center text-slate-400 hover:text-white border border-slate-700"
          title="Zoom out"
        >
          −
        </button>
      </div>
    </div>
  )
}

export default GraphViewer
