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
const CustomTooltip = ({ active, payload, viewMode }) => {
  if (!active || !payload?.length) return null

  const data = payload[0]?.payload
  if (!data) return null

  const itemLabel = viewMode === 'exercises' ? 'exercises' : viewMode === 'cards' ? 'cards' : 'items'

  return (
    <div className="bg-bg-elevated border border-border-primary rounded-lg shadow-lg p-3">
      <p className="text-sm text-text-primary font-medium mb-1">{data.topic}</p>
      <div className="space-y-1 text-xs">
        <p className="text-text-secondary">
          Mastery: <span className="text-indigo-400 font-medium">{data.mastery}%</span>
        </p>
        {data.cardCount !== undefined && (
          <p className="text-text-muted">{data.cardCount} {itemLabel}</p>
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
  viewMode = 'combined', // 'combined', 'cards', 'exercises'
  className,
}) {
  const sortedData = [...data].sort((a, b) => b.mastery - a.mastery)
  // Show data if there are topics with mastery > 0 OR topics with items (cards/exercises)
  const hasData = data.length > 0 && data.some(d => d.mastery > 0 || d.cardCount > 0)

  // Dynamic labels based on view mode
  const itemLabel = viewMode === 'exercises' ? 'exercises' : viewMode === 'cards' ? 'cards' : 'items'
  
  const getSubtitle = () => {
    if (viewMode === 'exercises') {
      return 'Based on exercise scores per topic. Higher mastery = better exercise performance.'
    } else if (viewMode === 'cards') {
      return 'Based on card review performance per topic. Higher mastery = better recall + longer retention.'
    }
    return 'Combined card & exercise performance. Higher scores = better mastery.'
  }

  const getEmptyMessage = () => {
    if (viewMode === 'exercises') {
      return 'Complete exercises with topic tags to see your progress by topic. Each topic\'s mastery is based on your exercise scores.'
    } else if (viewMode === 'cards') {
      return 'Review cards with topic tags to see your progress by topic. Each topic\'s mastery is based on your review success rate and card stability.'
    }
    return 'Review cards or complete exercises to see your progress by topic.'
  }

  // Empty state for no data
  if (!hasData) {
    return (
      <div className={clsx('flex flex-col', className)}>
        {/* Explanatory subtitle */}
        <p className="text-xs text-text-muted mb-2">
          {getSubtitle()}
        </p>
        <div className="flex flex-col items-center justify-center py-12 text-center">
          <span className="text-4xl mb-3">📈</span>
          <p className="text-sm text-text-secondary mb-1">No progress data yet</p>
          <p className="text-xs text-text-muted max-w-[250px]">
            {getEmptyMessage()}
          </p>
        </div>
      </div>
    )
  }

  if (type === 'list') {
    return (
      <motion.div
        variants={staggerContainer}
        initial="hidden"
        animate="show"
        className={clsx('space-y-3', className)}
      >
        {/* Explanatory subtitle */}
        <p className="text-xs text-text-muted mb-2">
          {getSubtitle()}
        </p>
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
              <p className="text-xs text-text-muted">{topic.cardCount} {itemLabel}</p>
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
      {/* Explanatory subtitle for chart view */}
      <p className="text-xs text-text-muted mb-2">
        {getSubtitle()}
      </p>
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
          
          <Tooltip content={<CustomTooltip viewMode={viewMode} />} cursor={{ fill: 'rgba(99, 102, 241, 0.1)' }} />
          
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
