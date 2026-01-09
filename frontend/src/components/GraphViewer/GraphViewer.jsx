/**
 * Graph Viewer Component
 *
 * Simple, stable force-directed graph visualization.
 * Prioritizes usability over fancy effects.
 */

import { useCallback, useRef, useState, useEffect, useMemo } from 'react'
import ForceGraph2D from 'react-force-graph-2d'
import * as d3 from 'd3'
import { useGraphData } from './useGraphData'
import { GraphLegend } from './GraphLegend'

// Node colors by type
const NODE_COLORS = {
  Content: '#818cf8',
  Concept: '#34d399',
  Note: '#fbbf24',
}

// Content type specific colors
const CONTENT_TYPE_COLORS = {
  paper: '#a78bfa',
  article: '#60a5fa',
  book: '#f472b6',
  code: '#2dd4bf',
  idea: '#fb923c',
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

function EmptyGraph() {
  return (
    <div className="absolute inset-0 flex items-center justify-center bg-slate-900">
      <div className="text-center">
        <p className="text-slate-400">No nodes in the graph yet</p>
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
}) {
  const graphRef = useRef()
  const containerRef = useRef()
  const dimensionsRef = useRef({ width: 800, height: 600 })
  const [dimensions, setDimensions] = useState({ width: 800, height: 600 })
  const dataIdRef = useRef(null) // Track which data we've initialized
  const simulationFrozenRef = useRef(false)

  const { data: rawData, isLoading, error, refetch } = useGraphData(centerId, {
    nodeTypes,
    limit,
  })
  
  // Memoize graph data to prevent unnecessary re-renders
  const data = useMemo(() => {
    if (!rawData) return null
    return rawData
  }, [rawData])

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
    fg.d3Force('charge')?.strength(-300)?.distanceMax(400)
    fg.d3Force('link')?.distance(100)
    fg.d3Force('center')?.strength(0.03)
    
    // Add collision force to prevent overlap - larger radius for labels
    fg.d3Force('collision', d3.forceCollide().radius(40).strength(1.0))
  }, [data])

  // Fit to view once when simulation ends, then FREEZE the simulation completely
  const handleEngineStop = useCallback(() => {
    if (graphRef.current && !simulationFrozenRef.current) {
      simulationFrozenRef.current = true
      
      const fg = graphRef.current
      
      // Completely stop the simulation - no more force calculations
      if (fg.d3Force) {
        fg.d3Force('charge', null)
        fg.d3Force('link', null)
        fg.d3Force('center', null)
        fg.d3Force('collision', null)
      }
      
      // Fit to view after a brief delay
      setTimeout(() => {
        fg.zoomToFit(300, 60)
      }, 100)
    }
  }, [])

  // Reset view handler
  const handleResetView = useCallback(() => {
    if (graphRef.current) {
      graphRef.current.zoomToFit(300, 50)
    }
  }, [])

  // Get node color
  const getNodeColor = useCallback((node) => {
    if (node.content_type && CONTENT_TYPE_COLORS[node.content_type]) {
      return CONTENT_TYPE_COLORS[node.content_type]
    }
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
    const radius = 6

    // Draw node
    ctx.beginPath()
    ctx.arc(node.x, node.y, radius, 0, 2 * Math.PI)
    ctx.fillStyle = color
    ctx.fill()

    // Draw label if zoomed in enough
    if (globalScale > 0.5) {
      const label = node.label || node.id || ''
      const fontSize = Math.min(Math.max(9 / globalScale, 3), 9)
      const maxWidth = 70 // pixels for text wrapping
      
      ctx.font = `${fontSize}px sans-serif`
      ctx.textAlign = 'center'
      ctx.fillStyle = '#e2e8f0'
      
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
    }
  }, [getNodeColor, wrapText])

  // Handle click
  const handleClick = useCallback((node) => {
    if (onNodeClick) {
      onNodeClick(node)
    }
  }, [onNodeClick])

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
        linkColor={() => '#475569'}
        linkWidth={1}
        onNodeClick={handleClick}
        onEngineStop={handleEngineStop}
        // Simulation settings - run once then freeze
        cooldownTicks={100}
        cooldownTime={1500}
        warmupTicks={50}
        d3AlphaMin={0.001}
        // Completely disable interaction features that cause movement
        enableNodeDrag={false}
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
      {showLegend && <GraphLegend showContentTypes />}

      {/* Node count */}
      <div className="absolute top-4 left-4 bg-slate-900/90 rounded-lg px-3 py-1.5 border border-slate-700/50">
        <span className="text-sm text-slate-400">
          {data.nodes.length} nodes · {data.links.length} connections
        </span>
      </div>

      {/* Controls */}
      <div className="absolute top-4 right-4 flex flex-col gap-2">
        <button
          onClick={handleResetView}
          className="w-8 h-8 bg-slate-800 hover:bg-slate-700 rounded-lg flex items-center justify-center text-slate-400 hover:text-white border border-slate-700"
          title="Reset view"
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
