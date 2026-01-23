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
const CustomTooltip = ({ active, payload }) => {
  if (!active || !payload?.length) return null

  const data = payload[0]?.payload
  if (!data) return null

  return (
    <div className="bg-bg-elevated border border-border-primary rounded-lg shadow-lg p-3">
      <p className="text-sm text-text-primary font-medium mb-1">{data.topic}</p>
      <p className="text-xs text-text-secondary">
        Mastery: <span className="text-indigo-400 font-medium">{data.mastery}%</span>
      </p>
      {data.cardCount !== undefined && (
        <p className="text-xs text-text-muted">{data.cardCount} cards</p>
      )}
    </div>
  )
}

export function MasteryRadar({
  data = [],
  height = 300,
  showLabels: _showLabels = true,
  className,
}) {
  const hasData = data.length > 0 && data.some(d => d.mastery > 0)
  
  // Ensure we have at least 3 data points for radar to look good
  const chartData = data.length >= 3 ? data : [
    { topic: 'Topic 1', mastery: 0 },
    { topic: 'Topic 2', mastery: 0 },
    { topic: 'Topic 3', mastery: 0 },
  ]

  return (
    <motion.div variants={fadeInUp} className={clsx('w-full', className)}>
      {/* Explanatory subtitle */}
      <p className="text-xs text-text-muted mb-2 px-2">
        Based on spaced repetition card performance (success rate + stability). Showing top {Math.min(data.length, 8)} topics.
      </p>
      
      {!hasData ? (
        <div className="flex flex-col items-center justify-center py-12 text-center">
          <span className="text-4xl mb-3">📊</span>
          <p className="text-sm text-text-secondary mb-1">No mastery data yet</p>
          <p className="text-xs text-text-muted max-w-[250px]">
            Review cards to build mastery scores. Mastery is calculated from your card review performance and memory stability.
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
            
            <Tooltip content={<CustomTooltip />} />
            
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
