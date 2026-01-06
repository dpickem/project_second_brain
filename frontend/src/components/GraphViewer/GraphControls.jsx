/**
 * Graph Controls Component
 *
 * Provides zoom, pan, and layout controls for the graph.
 */

import { motion } from 'framer-motion'

export function GraphControls({ graphRef, onReset }) {
  const handleZoomIn = () => {
    if (graphRef?.current) {
      const currentZoom = graphRef.current.zoom()
      graphRef.current.zoom(currentZoom * 1.3, 300)
    }
  }

  const handleZoomOut = () => {
    if (graphRef?.current) {
      const currentZoom = graphRef.current.zoom()
      graphRef.current.zoom(currentZoom / 1.3, 300)
    }
  }

  const handleZoomToFit = () => {
    if (graphRef?.current) {
      graphRef.current.zoomToFit(400, 50)
    }
  }

  const handleCenterGraph = () => {
    if (graphRef?.current) {
      graphRef.current.centerAt(0, 0, 300)
    }
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: -20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.2 }}
      className="absolute top-4 right-4 flex flex-col gap-1 bg-slate-900/90 backdrop-blur-sm rounded-lg p-1.5 border border-slate-700/50 shadow-xl"
    >
      <ControlButton
        onClick={handleZoomIn}
        title="Zoom In"
        icon={
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
              d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0zM10 7v6m3-3H7"
            />
          </svg>
        }
      />
      <ControlButton
        onClick={handleZoomOut}
        title="Zoom Out"
        icon={
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
              d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0zM13 10H7"
            />
          </svg>
        }
      />
      <div className="border-t border-slate-700/50 my-1" />
      <ControlButton
        onClick={handleZoomToFit}
        title="Fit to View"
        icon={
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
              d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4"
            />
          </svg>
        }
      />
      <ControlButton
        onClick={handleCenterGraph}
        title="Center"
        icon={
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
              d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
        }
      />
      {onReset && (
        <>
          <div className="border-t border-slate-700/50 my-1" />
          <ControlButton
            onClick={onReset}
            title="Reset View"
            icon={
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
                  d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
                />
              </svg>
            }
          />
        </>
      )}
    </motion.div>
  )
}

function ControlButton({ onClick, title, icon }) {
  return (
    <button
      onClick={onClick}
      title={title}
      className="p-2 text-slate-400 hover:text-white hover:bg-slate-700/50 rounded-md transition-colors duration-150"
    >
      {icon}
    </button>
  )
}

export default GraphControls

