/**
 * LLM Usage Page
 * 
 * Dashboard for monitoring LLM API usage and costs.
 * Shows budget status, spending trends, and breakdowns by model/pipeline.
 */

import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { useQuery } from '@tanstack/react-query'
import { clsx } from 'clsx'
import { Card, Button, PageLoader, Badge } from '../components/common'
import { llmUsageApi } from '../api/llmUsage'
import { fadeInUp, staggerContainer } from '../utils/animations'

const timeRanges = [
  { value: 7, label: '7 Days' },
  { value: 30, label: '30 Days' },
  { value: 90, label: '90 Days' },
]

// Format currency with proper decimals
function formatCurrency(amount, decimals = 2) {
  if (amount == null) return '$0.00'
  return `$${amount.toFixed(decimals)}`
}

// Format large numbers with K/M suffixes
function formatNumber(num) {
  if (num == null) return '0'
  if (num >= 1000000) return `${(num / 1000000).toFixed(1)}M`
  if (num >= 1000) return `${(num / 1000).toFixed(1)}K`
  return num.toLocaleString()
}

// Budget progress bar component
function BudgetProgress({ current, limit, alertThreshold, isOverBudget }) {
  const percentage = limit > 0 ? Math.min((current / limit) * 100, 100) : 0
  const isAlert = percentage >= alertThreshold

  return (
    <div className="space-y-2">
      <div className="flex justify-between text-sm">
        <span className="text-text-secondary">
          {formatCurrency(current)} of {formatCurrency(limit)}
        </span>
        <span className={clsx(
          'font-medium',
          isOverBudget ? 'text-red-400' : isAlert ? 'text-amber-400' : 'text-text-primary'
        )}>
          {percentage.toFixed(1)}%
        </span>
      </div>
      <div className="h-3 bg-bg-tertiary rounded-full overflow-hidden">
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${percentage}%` }}
          transition={{ duration: 0.5, ease: 'easeOut' }}
          className={clsx(
            'h-full rounded-full',
            isOverBudget 
              ? 'bg-gradient-to-r from-red-500 to-red-400' 
              : isAlert 
                ? 'bg-gradient-to-r from-amber-500 to-amber-400'
                : 'bg-gradient-to-r from-emerald-500 to-emerald-400'
          )}
        />
      </div>
      {/* Alert threshold marker */}
      <div className="relative h-1">
        <div 
          className="absolute w-0.5 h-3 bg-amber-500/50 -top-4"
          style={{ left: `${alertThreshold}%` }}
        />
      </div>
    </div>
  )
}

// Stats card component
function StatCard({ title, value, subValue, icon, trend, color = 'indigo' }) {
  const colorClasses = {
    indigo: 'text-indigo-400',
    emerald: 'text-emerald-400',
    amber: 'text-amber-400',
    red: 'text-red-400',
    purple: 'text-purple-400',
  }

  return (
    <div className="p-4 bg-bg-tertiary rounded-xl">
      <div className="flex items-center gap-2 mb-2">
        <span className="text-lg">{icon}</span>
        <h3 className="text-sm font-medium text-text-secondary">{title}</h3>
      </div>
      <p className={clsx('text-2xl font-bold font-heading', colorClasses[color])}>
        {value}
      </p>
      {subValue && (
        <p className="text-xs text-text-muted mt-1 flex items-center gap-1">
          {trend && (
            <span className={clsx(
              trend === 'up' ? 'text-red-400' : trend === 'down' ? 'text-emerald-400' : 'text-text-muted'
            )}>
              {trend === 'up' ? '↑' : trend === 'down' ? '↓' : '→'}
            </span>
          )}
          {subValue}
        </p>
      )}
    </div>
  )
}

// Usage chart (simple bar visualization)
function UsageChart({ data, height = 200 }) {
  if (!data || data.length === 0) {
    return (
      <div className="flex items-center justify-center h-48 text-text-muted">
        No usage data available
      </div>
    )
  }

  const maxCost = Math.max(...data.map(d => d.cost_usd || 0), 0.01)

  return (
    <div className="flex items-end gap-1 h-48" style={{ height }}>
      {data.map((point, i) => {
        const barHeight = maxCost > 0 ? ((point.cost_usd || 0) / maxCost) * 100 : 0
        const isToday = i === data.length - 1

        return (
          <motion.div
            key={point.date}
            initial={{ height: 0 }}
            animate={{ height: `${Math.max(barHeight, 2)}%` }}
            transition={{ duration: 0.3, delay: i * 0.02 }}
            className={clsx(
              'flex-1 rounded-t-sm cursor-pointer transition-colors group relative',
              isToday 
                ? 'bg-indigo-500 hover:bg-indigo-400' 
                : 'bg-indigo-500/40 hover:bg-indigo-500/60'
            )}
            title={`${point.date}: ${formatCurrency(point.cost_usd, 4)}`}
          >
            {/* Tooltip on hover */}
            <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-10">
              <div className="bg-bg-elevated px-2 py-1 rounded text-xs whitespace-nowrap shadow-lg border border-border-primary">
                <div className="font-medium">{point.date}</div>
                <div className="text-indigo-400">{formatCurrency(point.cost_usd, 4)}</div>
                <div className="text-text-muted">{formatNumber(point.tokens)} tokens</div>
              </div>
            </div>
          </motion.div>
        )
      })}
    </div>
  )
}

// Breakdown list component
function BreakdownList({ title, data, keyField, valueField, showTokens = false }) {
  if (!data || data.length === 0) {
    return (
      <div className="text-text-muted text-sm py-4 text-center">
        No data available
      </div>
    )
  }

  const total = data.reduce((sum, item) => sum + (item[valueField] || 0), 0)

  return (
    <div className="space-y-3">
      {data.map((item, i) => {
        const value = item[valueField] || 0
        const percentage = total > 0 ? (value / total) * 100 : 0

        return (
          <div key={item[keyField] || i} className="space-y-1">
            <div className="flex justify-between text-sm">
              <span className="text-text-primary font-medium truncate max-w-[60%]">
                {item[keyField]}
              </span>
              <span className="text-text-secondary">
                {formatCurrency(value, 4)}
                {showTokens && item.tokens && (
                  <span className="text-text-muted ml-2">
                    ({formatNumber(item.tokens)} tokens)
                  </span>
                )}
              </span>
            </div>
            <div className="h-1.5 bg-bg-tertiary rounded-full overflow-hidden">
              <motion.div
                initial={{ width: 0 }}
                animate={{ width: `${percentage}%` }}
                transition={{ duration: 0.3, delay: i * 0.05 }}
                className="h-full bg-indigo-500/60 rounded-full"
              />
            </div>
          </div>
        )
      })}
    </div>
  )
}

export function LLMUsage() {
  const navigate = useNavigate()
  const [historyDays, setHistoryDays] = useState(30)

  // Fetch all data
  const { data: budgetData, isLoading: budgetLoading } = useQuery({
    queryKey: ['llm-usage', 'budget'],
    queryFn: () => llmUsageApi.getBudgetStatus('monthly'),
  })

  const { data: dailyData, isLoading: dailyLoading } = useQuery({
    queryKey: ['llm-usage', 'daily'],
    queryFn: () => llmUsageApi.getDailyUsage(),
  })

  const { data: monthlyData, isLoading: monthlyLoading } = useQuery({
    queryKey: ['llm-usage', 'monthly'],
    queryFn: () => llmUsageApi.getMonthlyUsage(),
  })

  const { data: historyData, isLoading: historyLoading, isFetching: historyFetching } = useQuery({
    queryKey: ['llm-usage', 'history', historyDays],
    queryFn: () => llmUsageApi.getUsageHistory({ days: historyDays }),
  })

  const { data: topConsumersData, isLoading: consumersLoading } = useQuery({
    queryKey: ['llm-usage', 'top-consumers', historyDays],
    queryFn: () => llmUsageApi.getTopConsumers({ days: historyDays }),
  })

  const isInitialLoading = budgetLoading || dailyLoading || monthlyLoading

  if (isInitialLoading) {
    return <PageLoader message="Loading LLM usage data..." />
  }

  // Transform model breakdown from object to array for display
  const modelBreakdown = topConsumersData?.by_model || []
  const pipelineBreakdown = topConsumersData?.by_pipeline || []
  const operationBreakdown = topConsumersData?.by_operation || []

  return (
    <div className="min-h-screen bg-bg-primary p-6 lg:p-8">
      <motion.div
        variants={staggerContainer}
        initial="hidden"
        animate="show"
        className="max-w-7xl mx-auto space-y-8"
      >
        {/* Header */}
        <motion.div variants={fadeInUp} className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-text-primary font-heading">
              💰 LLM Usage & Costs
            </h1>
            <p className="text-text-secondary mt-1">
              Monitor API spending and optimize resource usage
            </p>
          </div>
          <Button variant="secondary" onClick={() => navigate('/')}>
            ← Dashboard
          </Button>
        </motion.div>

        {/* Budget Status */}
        <motion.div variants={fadeInUp}>
          <Card variant={budgetData?.is_over_budget ? 'danger' : budgetData?.is_alert_triggered ? 'warning' : 'default'}>
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-3">
                <span className="text-2xl">
                  {budgetData?.is_over_budget ? '🚨' : budgetData?.is_alert_triggered ? '⚠️' : '📊'}
                </span>
                <div>
                  <h2 className="text-xl font-semibold text-text-primary font-heading">
                    Monthly Budget
                  </h2>
                  <p className="text-xs text-text-muted">
                    Alert threshold: {budgetData?.alert_threshold || 80}%
                  </p>
                </div>
              </div>
              {budgetData?.is_over_budget && (
                <Badge variant="danger">Over Budget</Badge>
              )}
              {!budgetData?.is_over_budget && budgetData?.is_alert_triggered && (
                <Badge variant="warning">Alert</Badge>
              )}
            </div>
            <BudgetProgress
              current={budgetData?.current_spend_usd || 0}
              limit={budgetData?.limit_usd || 100}
              alertThreshold={budgetData?.alert_threshold || 80}
              isOverBudget={budgetData?.is_over_budget || false}
            />
            <div className="mt-4 flex gap-4 text-sm">
              <div>
                <span className="text-text-muted">Remaining: </span>
                <span className="text-emerald-400 font-medium">
                  {formatCurrency(budgetData?.remaining_usd || 0)}
                </span>
              </div>
              <div>
                <span className="text-text-muted">Avg daily: </span>
                <span className="text-text-primary font-medium">
                  {formatCurrency(historyData?.avg_daily_cost || 0, 4)}
                </span>
              </div>
              <div>
                <span className="text-text-muted">Projected: </span>
                <span className={clsx(
                  'font-medium',
                  (historyData?.avg_daily_cost || 0) * 30 > (budgetData?.limit_usd || 100)
                    ? 'text-red-400'
                    : 'text-text-primary'
                )}>
                  {formatCurrency((historyData?.avg_daily_cost || 0) * 30)}
                </span>
              </div>
            </div>
          </Card>
        </motion.div>

        {/* Stats Grid */}
        <motion.div variants={fadeInUp}>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <StatCard
              title="Today's Cost"
              value={formatCurrency(dailyData?.total_cost_usd || 0, 4)}
              subValue={`${formatNumber(dailyData?.request_count || 0)} requests`}
              icon="📈"
              color="indigo"
            />
            <StatCard
              title="Monthly Cost"
              value={formatCurrency(monthlyData?.total_cost_usd || 0)}
              subValue={`${formatNumber(monthlyData?.request_count || 0)} requests`}
              icon="📆"
              color="purple"
            />
            <StatCard
              title="Total Tokens"
              value={formatNumber(monthlyData?.total_tokens || 0)}
              subValue="this month"
              icon="🔤"
              color="emerald"
            />
            <StatCard
              title="Trend"
              value={
                historyData?.trend_direction === 'up' ? '↗️ Increasing' :
                historyData?.trend_direction === 'down' ? '↘️ Decreasing' :
                '→ Stable'
              }
              subValue="vs previous period"
              icon="📊"
              trend={historyData?.trend_direction}
              color={
                historyData?.trend_direction === 'up' ? 'red' :
                historyData?.trend_direction === 'down' ? 'emerald' :
                'amber'
              }
            />
          </div>
        </motion.div>

        {/* Usage History Chart */}
        <motion.div variants={fadeInUp}>
          <Card>
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-semibold text-text-primary font-heading">
                📈 Usage History
              </h2>
              
              {/* Time range selector */}
              <div className="flex items-center gap-1 bg-bg-tertiary rounded-lg p-1">
                {timeRanges.map((range) => (
                  <button
                    type="button"
                    key={range.value}
                    onClick={() => setHistoryDays(range.value)}
                    disabled={historyFetching}
                    className={clsx(
                      'px-3 py-1.5 text-sm rounded-md transition-colors',
                      historyDays === range.value
                        ? 'bg-indigo-600 text-white'
                        : 'text-text-secondary hover:text-text-primary',
                      historyFetching && 'opacity-50 cursor-not-allowed'
                    )}
                  >
                    {range.label}
                  </button>
                ))}
              </div>
            </div>
            
            <div className="relative">
              {historyFetching && (
                <div className="absolute inset-0 bg-bg-primary/50 backdrop-blur-sm flex items-center justify-center z-10 rounded-lg">
                  <div className="flex items-center gap-2 text-text-secondary">
                    <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                    </svg>
                    <span className="text-sm">Loading...</span>
                  </div>
                </div>
              )}
              <UsageChart data={historyData?.daily_data || []} />
            </div>
            
            {/* Summary stats */}
            <div className="mt-4 pt-4 border-t border-border-primary grid grid-cols-3 gap-4 text-center">
              <div>
                <p className="text-xs text-text-muted">Total Cost</p>
                <p className="text-lg font-semibold text-indigo-400">
                  {formatCurrency(historyData?.total_cost_usd || 0)}
                </p>
              </div>
              <div>
                <p className="text-xs text-text-muted">Total Requests</p>
                <p className="text-lg font-semibold text-text-primary">
                  {formatNumber(historyData?.total_requests || 0)}
                </p>
              </div>
              <div>
                <p className="text-xs text-text-muted">Total Tokens</p>
                <p className="text-lg font-semibold text-emerald-400">
                  {formatNumber(historyData?.total_tokens || 0)}
                </p>
              </div>
            </div>
          </Card>
        </motion.div>

        {/* Breakdowns */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* By Model */}
          <motion.div variants={fadeInUp}>
            <Card className="h-full">
              <div className="flex items-center gap-2 mb-4">
                <span className="text-lg">🤖</span>
                <h2 className="text-lg font-semibold text-text-primary font-heading">
                  By Model
                </h2>
              </div>
              <BreakdownList
                data={modelBreakdown}
                keyField="model"
                valueField="cost_usd"
                showTokens
              />
            </Card>
          </motion.div>

          {/* By Pipeline */}
          <motion.div variants={fadeInUp}>
            <Card className="h-full">
              <div className="flex items-center gap-2 mb-4">
                <span className="text-lg">⚙️</span>
                <h2 className="text-lg font-semibold text-text-primary font-heading">
                  By Pipeline
                </h2>
              </div>
              <BreakdownList
                data={pipelineBreakdown}
                keyField="pipeline"
                valueField="cost_usd"
              />
            </Card>
          </motion.div>

          {/* By Operation */}
          <motion.div variants={fadeInUp}>
            <Card className="h-full">
              <div className="flex items-center gap-2 mb-4">
                <span className="text-lg">🔧</span>
                <h2 className="text-lg font-semibold text-text-primary font-heading">
                  By Operation
                </h2>
              </div>
              <BreakdownList
                data={operationBreakdown}
                keyField="operation"
                valueField="cost_usd"
                showTokens
              />
            </Card>
          </motion.div>
        </div>

        {/* Daily Breakdown (from monthly data) */}
        {monthlyData?.by_day && monthlyData.by_day.length > 0 && (
          <motion.div variants={fadeInUp}>
            <Card>
              <h2 className="text-xl font-semibold text-text-primary font-heading mb-4">
                📅 Daily Breakdown (This Month)
              </h2>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-text-muted text-left border-b border-border-primary">
                      <th className="pb-2 font-medium">Date</th>
                      <th className="pb-2 font-medium text-right">Cost</th>
                      <th className="pb-2 font-medium text-right">Requests</th>
                    </tr>
                  </thead>
                  <tbody>
                    {monthlyData.by_day.slice(-14).reverse().map((day) => (
                      <tr key={day.date} className="border-b border-border-primary/50">
                        <td className="py-2 text-text-primary">{day.date}</td>
                        <td className="py-2 text-right text-indigo-400">
                          {formatCurrency(day.cost, 4)}
                        </td>
                        <td className="py-2 text-right text-text-secondary">
                          {formatNumber(day.count)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>
          </motion.div>
        )}

        {/* Tips Card */}
        <motion.div variants={fadeInUp}>
          <Card variant="elevated">
            <div className="flex items-center gap-3 mb-4">
              <span className="text-2xl">💡</span>
              <h2 className="text-xl font-semibold text-text-primary font-heading">
                Cost Optimization Tips
              </h2>
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              <div className="p-4 bg-bg-tertiary rounded-xl">
                <h3 className="text-sm font-medium text-text-primary mb-1">
                  Use Smaller Models
                </h3>
                <p className="text-xs text-text-muted">
                  For simple tasks, use cost-efficient models like Gemini Flash.
                </p>
              </div>
              
              <div className="p-4 bg-bg-tertiary rounded-xl">
                <h3 className="text-sm font-medium text-text-primary mb-1">
                  Batch Requests
                </h3>
                <p className="text-xs text-text-muted">
                  Combine multiple small requests into larger batches to reduce overhead.
                </p>
              </div>
              
              <div className="p-4 bg-bg-tertiary rounded-xl">
                <h3 className="text-sm font-medium text-text-primary mb-1">
                  Cache Responses
                </h3>
                <p className="text-xs text-text-muted">
                  Cache common queries to avoid repeated API calls for the same content.
                </p>
              </div>
              
              <div className="p-4 bg-bg-tertiary rounded-xl">
                <h3 className="text-sm font-medium text-text-primary mb-1">
                  Monitor Trends
                </h3>
                <p className="text-xs text-text-muted">
                  Watch for spending spikes and investigate high-cost operations.
                </p>
              </div>
            </div>
          </Card>
        </motion.div>
      </motion.div>
    </div>
  )
}

export default LLMUsage
