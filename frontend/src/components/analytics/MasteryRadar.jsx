/**
 * MasteryRadar Component
 * 
 * Radar chart showing mastery levels across topics.
 */

import {
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
  ResponsiveContainer,
  Tooltip,
} from 'recharts'
import { motion } from 'framer-motion'
import { clsx } from 'clsx'
import { fadeInUp } from '../../utils/animations'

// Custom tooltip
const CustomTooltip = ({ active, payload, viewMode }) => {
  if (!active || !payload?.length) return null

  const data = payload[0]?.payload
  if (!data) return null

  const itemLabel = viewMode === 'exercises' ? 'exercises' : viewMode === 'cards' ? 'cards' : 'items'

  return (
    <div className="bg-bg-elevated border border-border-primary rounded-lg shadow-lg p-3">
      <p className="text-sm text-text-primary font-medium mb-1">{data.topic}</p>
      <p className="text-xs text-text-secondary">
        Mastery: <span className="text-indigo-400 font-medium">{data.mastery}%</span>
      </p>
      {data.cardCount !== undefined && (
        <p className="text-xs text-text-muted">{data.cardCount} {itemLabel}</p>
      )}
    </div>
  )
}

export function MasteryRadar({
  data = [],
  height = 300,
  showLabels: _showLabels = true,
  viewMode = 'combined', // 'combined', 'cards', 'exercises'
  className,
}) {
  // Show data if there are topics with mastery > 0 OR topics with items (cards/exercises)
  const hasData = data.length > 0 && data.some(d => d.mastery > 0 || d.cardCount > 0)
  
  // For radar chart, we need at least 3 points. If we have fewer, pad with actual topics at 0
  // but use meaningful names from the data we have
  let chartData = data
  if (data.length > 0 && data.length < 3) {
    // Pad with placeholder points based on existing data
    chartData = [...data]
    while (chartData.length < 3) {
      chartData.push({ topic: `—`, mastery: 0 })
    }
  } else if (data.length === 0) {
    chartData = [
      { topic: '—', mastery: 0 },
      { topic: '—', mastery: 0 },
      { topic: '—', mastery: 0 },
    ]
  }

  // Dynamic text based on view mode
  const getSubtitle = () => {
    if (viewMode === 'exercises') {
      return `Based on exercise scores. Showing ${Math.min(data.length, 8)} topics with exercises.`
    } else if (viewMode === 'cards') {
      return `Based on spaced repetition card performance. Showing ${Math.min(data.length, 8)} topics.`
    }
    return `Combined card & exercise performance. Showing top ${Math.min(data.length, 8)} topics.`
  }

  const getEmptyMessage = () => {
    if (viewMode === 'exercises') {
      return 'Complete exercises to build mastery scores. Mastery is calculated from your exercise performance.'
    } else if (viewMode === 'cards') {
      return 'Review cards to build mastery scores. Mastery is calculated from your card review performance and memory stability.'
    }
    return 'Review cards or complete exercises to build mastery scores.'
  }

  return (
    <motion.div variants={fadeInUp} className={clsx('w-full', className)}>
      {/* Explanatory subtitle */}
      <p className="text-xs text-text-muted mb-2 px-2">
        {getSubtitle()}
      </p>
      
      {!hasData ? (
        <div className="flex flex-col items-center justify-center py-12 text-center">
          <span className="text-4xl mb-3">📊</span>
          <p className="text-sm text-text-secondary mb-1">No mastery data yet</p>
          <p className="text-xs text-text-muted max-w-[250px]">
            {getEmptyMessage()}
          </p>
        </div>
      ) : (
        <ResponsiveContainer width="100%" height={height}>
          <RadarChart data={chartData} margin={{ top: 20, right: 30, bottom: 20, left: 30 }}>
            <PolarGrid 
              stroke="rgba(148, 163, 184, 0.2)"
              strokeDasharray="3 3"
            />
            
            <PolarAngleAxis
              dataKey="topic"
              tick={{ fill: '#94a3b8', fontSize: 11 }}
              tickLine={false}
            />
            
            <PolarRadiusAxis
              angle={90}
              domain={[0, 100]}
              tick={{ fill: '#64748b', fontSize: 10 }}
              tickCount={5}
              stroke="rgba(148, 163, 184, 0.1)"
            />
            
            <Tooltip content={<CustomTooltip viewMode={viewMode} />} />
            
            <Radar
              name="Mastery"
              dataKey="mastery"
              stroke="#6366f1"
              strokeWidth={2}
              fill="#6366f1"
              fillOpacity={0.3}
            />
          </RadarChart>
        </ResponsiveContainer>
      )}
    </motion.div>
  )
}

// Mini radar for compact display
export function MasteryRadarMini({ data = [], size = 120, className }) {
  return (
    <div className={clsx('relative', className)} style={{ width: size, height: size }}>
      <ResponsiveContainer width="100%" height="100%">
        <RadarChart data={data} margin={{ top: 5, right: 5, bottom: 5, left: 5 }}>
          <PolarGrid stroke="rgba(148, 163, 184, 0.15)" />
          <Radar
            dataKey="mastery"
            stroke="#6366f1"
            strokeWidth={1.5}
            fill="#6366f1"
            fillOpacity={0.2}
          />
        </RadarChart>
      </ResponsiveContainer>
    </div>
  )
}

export default MasteryRadar
