/**
 * TopicBreakdown Component
 * 
 * Horizontal bar chart or list showing mastery by topic.
 */

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts'
import { motion } from 'framer-motion'
import { clsx } from 'clsx'
import { Badge } from '../common'
import { staggerContainer, listItem } from '../../utils/animations'

// Color based on mastery level
const getMasteryColor = (mastery) => {
  if (mastery >= 80) return '#34d399' // emerald
  if (mastery >= 60) return '#6366f1' // indigo
  if (mastery >= 40) return '#fbbf24' // amber
  return '#f87171' // red
}

// Custom tooltip
const CustomTooltip = ({ active, payload }) => {
  if (!active || !payload?.length) return null

  const data = payload[0]?.payload
  if (!data) return null

  return (
    <div className="bg-bg-elevated border border-border-primary rounded-lg shadow-lg p-3">
      <p className="text-sm text-text-primary font-medium mb-1">{data.topic}</p>
      <div className="space-y-1 text-xs">
        <p className="text-text-secondary">
          Mastery: <span className="text-indigo-400 font-medium">{data.mastery}%</span>
        </p>
        {data.cardCount !== undefined && (
          <p className="text-text-muted">{data.cardCount} cards</p>
        )}
        {data.dueCount !== undefined && data.dueCount > 0 && (
          <p className="text-amber-400">{data.dueCount} due</p>
        )}
      </div>
    </div>
  )
}

export function TopicBreakdown({
  data = [],
  type = 'chart', // 'chart' | 'list'
  height = 300,
  showValues: _showValues = true,
  className,
}) {
  const sortedData = [...data].sort((a, b) => b.mastery - a.mastery)

  if (type === 'list') {
    return (
      <motion.div
        variants={staggerContainer}
        initial="hidden"
        animate="show"
        className={clsx('space-y-3', className)}
      >
        {sortedData.map((topic, index) => (
          <motion.div
            key={topic.topic}
            variants={listItem}
            custom={index}
            className="flex items-center gap-3"
          >
            {/* Topic name */}
            <div className="flex-1 min-w-0">
              <p className="text-sm text-text-primary font-medium truncate">
                {topic.topic}
              </p>
              <p className="text-xs text-text-muted">{topic.cardCount} cards</p>
            </div>

            {/* Progress bar */}
            <div className="w-32 h-2 bg-slate-700 rounded-full overflow-hidden">
              <motion.div
                className="h-full rounded-full"
                style={{ backgroundColor: getMasteryColor(topic.mastery) }}
                initial={{ width: 0 }}
                animate={{ width: `${topic.mastery}%` }}
                transition={{ duration: 0.5, delay: index * 0.05 }}
              />
            </div>

            {/* Value */}
            <span 
              className="text-sm font-medium w-12 text-right"
              style={{ color: getMasteryColor(topic.mastery) }}
            >
              {topic.mastery}%
            </span>

            {/* Due badge */}
            {topic.dueCount > 0 && (
              <Badge variant="warning" size="xs">{topic.dueCount}</Badge>
            )}
          </motion.div>
        ))}
      </motion.div>
    )
  }

  return (
    <motion.div variants={listItem} className={clsx('w-full', className)}>
      <ResponsiveContainer width="100%" height={height}>
        <BarChart
          data={sortedData}
          layout="vertical"
          margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
        >
          <CartesianGrid 
            strokeDasharray="3 3" 
            stroke="rgba(148, 163, 184, 0.1)"
            horizontal={false}
          />
          
          <XAxis 
            type="number" 
            domain={[0, 100]}
            stroke="#64748b"
            fontSize={12}
            tickLine={false}
            axisLine={false}
          />
          
          <YAxis
            type="category"
            dataKey="topic"
            stroke="#64748b"
            fontSize={12}
            tickLine={false}
            axisLine={false}
            width={100}
            tick={{ fill: '#94a3b8' }}
          />
          
          <Tooltip content={<CustomTooltip />} cursor={{ fill: 'rgba(99, 102, 241, 0.1)' }} />
          
          <Bar 
            dataKey="mastery" 
            radius={[0, 4, 4, 0]}
            maxBarSize={24}
          >
            {sortedData.map((entry, index) => (
              <Cell 
                key={`cell-${index}`} 
                fill={getMasteryColor(entry.mastery)}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </motion.div>
  )
}

export default TopicBreakdown
