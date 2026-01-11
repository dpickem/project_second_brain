/**
 * LearningChart Component
 * 
 * Time-series chart for learning activity and progress.
 */

import {
  LineChart,
  Line,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts'
import { motion } from 'framer-motion'
import { clsx } from 'clsx'
import { format, parseISO } from 'date-fns'
import { fadeInUp } from '../../utils/animations'

// Custom tooltip
const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null

  return (
    <div className="bg-bg-elevated border border-border-primary rounded-lg shadow-lg p-3">
      <p className="text-sm text-text-primary font-medium mb-2">
        {format(parseISO(label), 'MMM d, yyyy')}
      </p>
      {payload.map((entry, index) => (
        <div key={index} className="flex items-center gap-2 text-xs">
          <span 
            className="w-2 h-2 rounded-full" 
            style={{ backgroundColor: entry.color }}
          />
          <span className="text-text-secondary">{entry.name}:</span>
          <span className="text-text-primary font-medium">{entry.value}</span>
        </div>
      ))}
    </div>
  )
}

export function LearningChart({
  data = [],
  type = 'area', // 'line' | 'area'
  metrics = ['cardsReviewed', 'practiceTime'],
  height = 300,
  showLegend = true,
  className,
}) {
  const metricConfig = {
    // Combined / Cards metrics
    cardsReviewed: {
      name: 'Cards Reviewed',
      color: '#6366f1',
      dataKey: 'cardsReviewed',
    },
    practiceTime: {
      name: 'Practice (min)',
      color: '#34d399',
      dataKey: 'practiceTime',
    },
    retention: {
      name: 'Retention %',
      color: '#f472b6',
      dataKey: 'retention',
    },
    newCards: {
      name: 'New Cards',
      color: '#fbbf24',
      dataKey: 'newCards',
    },
    // Exercise-specific metrics
    exercisesAttempted: {
      name: 'Exercises Attempted',
      color: '#14b8a6',
      dataKey: 'exercisesAttempted',
    },
    exerciseTime: {
      name: 'Exercise Time (min)',
      color: '#f97316',
      dataKey: 'exerciseTime',
    },
    exerciseScore: {
      name: 'Avg Score %',
      color: '#8b5cf6',
      dataKey: 'exerciseScore',
    },
  }

  const ChartComponent = type === 'area' ? AreaChart : LineChart

  return (
    <motion.div variants={fadeInUp} className={clsx('w-full', className)}>
      <ResponsiveContainer width="100%" height={height}>
        <ChartComponent
          data={data}
          margin={{ top: 10, right: 10, left: 0, bottom: 0 }}
        >
          <defs>
            {metrics.map((metric) => (
              <linearGradient 
                key={metric}
                id={`gradient-${metric}`} 
                x1="0" y1="0" x2="0" y2="1"
              >
                <stop 
                  offset="5%" 
                  stopColor={metricConfig[metric]?.color || '#6366f1'} 
                  stopOpacity={0.3}
                />
                <stop 
                  offset="95%" 
                  stopColor={metricConfig[metric]?.color || '#6366f1'} 
                  stopOpacity={0}
                />
              </linearGradient>
            ))}
          </defs>
          
          <CartesianGrid 
            strokeDasharray="3 3" 
            stroke="rgba(148, 163, 184, 0.1)"
            vertical={false}
          />
          
          <XAxis
            dataKey="date"
            tickFormatter={(date) => format(parseISO(date), 'MMM d')}
            stroke="#64748b"
            fontSize={12}
            tickLine={false}
            axisLine={false}
          />
          
          <YAxis
            stroke="#64748b"
            fontSize={12}
            tickLine={false}
            axisLine={false}
            width={40}
          />
          
          <Tooltip content={<CustomTooltip />} />
          
          {showLegend && (
            <Legend
              verticalAlign="top"
              height={36}
              iconType="circle"
              iconSize={8}
              formatter={(value) => (
                <span className="text-xs text-text-secondary">{value}</span>
              )}
            />
          )}

          {metrics.map((metric) => {
            const config = metricConfig[metric]
            if (!config) return null

            return type === 'area' ? (
              <Area
                key={metric}
                type="monotone"
                dataKey={config.dataKey}
                name={config.name}
                stroke={config.color}
                strokeWidth={2}
                fill={`url(#gradient-${metric})`}
              />
            ) : (
              <Line
                key={metric}
                type="monotone"
                dataKey={config.dataKey}
                name={config.name}
                stroke={config.color}
                strokeWidth={2}
                dot={false}
                activeDot={{ r: 4, strokeWidth: 0 }}
              />
            )
          })}
        </ChartComponent>
      </ResponsiveContainer>
    </motion.div>
  )
}

// Sparkline variant for compact display
export function LearningSparkline({
  data = [],
  dataKey = 'value',
  color = '#6366f1',
  height = 40,
  className,
}) {
  return (
    <div className={clsx('w-full', className)}>
      <ResponsiveContainer width="100%" height={height}>
        <AreaChart data={data} margin={{ top: 0, right: 0, left: 0, bottom: 0 }}>
          <defs>
            <linearGradient id={`spark-${dataKey}`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor={color} stopOpacity={0.3} />
              <stop offset="95%" stopColor={color} stopOpacity={0} />
            </linearGradient>
          </defs>
          <Area
            type="monotone"
            dataKey={dataKey}
            stroke={color}
            strokeWidth={1.5}
            fill={`url(#spark-${dataKey})`}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}

export default LearningChart
