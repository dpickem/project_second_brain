/**
 * Analytics Page
 * 
 * Comprehensive learning analytics dashboard.
 */

import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { useQuery } from '@tanstack/react-query'
import { clsx } from 'clsx'
import {
  LearningChart,
  MasteryRadar,
  TopicBreakdown,
  StatsGrid,
  WeakSpotsAnalysis,
} from '../components/analytics'
import { Card, Button, PageLoader, Badge } from '../components/common'
import { analyticsApi } from '../api/analytics'
import { fadeInUp, staggerContainer } from '../utils/animations'

const timeRanges = [
  { value: '7d', label: 'Week' },
  { value: '30d', label: 'Month' },
  { value: '90d', label: '3 Months' },
  { value: '365d', label: 'Year' },
]

export function Analytics() {
  const navigate = useNavigate()
  const [timeRange, setTimeRange] = useState('30d')

  // Fetch analytics data
  const { data: overviewData, isLoading: overviewLoading } = useQuery({
    queryKey: ['analytics', 'overview'],
    queryFn: analyticsApi.getOverview,
  })

  const { data: chartData, isLoading: chartLoading } = useQuery({
    queryKey: ['analytics', 'activity', timeRange],
    queryFn: () => analyticsApi.getActivityData(timeRange),
  })

  const { data: masteryData, isLoading: masteryLoading } = useQuery({
    queryKey: ['analytics', 'mastery'],
    queryFn: analyticsApi.getMasteryByTopic,
  })

  const { data: weakSpotsData } = useQuery({
    queryKey: ['analytics', 'weak-spots'],
    queryFn: analyticsApi.getWeakSpots,
  })

  const isLoading = overviewLoading || chartLoading || masteryLoading

  // Handle practice navigation
  const handlePracticeTopic = (topic) => {
    navigate(`/practice?topic=${encodeURIComponent(topic)}`)
  }

  if (isLoading) {
    return <PageLoader message="Loading analytics..." />
  }

  // Use API data with empty defaults
  const overview = overviewData || {
    totalCards: 0,
    masteredCards: 0,
    totalReviews: 0,
    learningTime: 0,
    streak: 0,
    avgRetention: 0,
  }

  const activityData = chartData?.data || []
  const mastery = masteryData?.topics || []
  const weakSpots = weakSpotsData?.spots || []

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
              📊 Learning Analytics
            </h1>
            <p className="text-text-secondary mt-1">
              Track your progress and identify areas for improvement
            </p>
          </div>
          <Button variant="secondary" onClick={() => navigate('/')}>
            ← Dashboard
          </Button>
        </motion.div>

        {/* Stats Grid */}
        <motion.div variants={fadeInUp}>
          <StatsGrid stats={overview} />
        </motion.div>

        {/* Activity Chart */}
        <motion.div variants={fadeInUp}>
          <Card>
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-semibold text-text-primary font-heading">
                Learning Activity
              </h2>
              
              {/* Time range selector */}
              <div className="flex items-center gap-1 bg-bg-tertiary rounded-lg p-1">
                {timeRanges.map((range) => (
                  <button
                    key={range.value}
                    onClick={() => setTimeRange(range.value)}
                    className={clsx(
                      'px-3 py-1.5 text-sm rounded-md transition-colors',
                      timeRange === range.value
                        ? 'bg-indigo-600 text-white'
                        : 'text-text-secondary hover:text-text-primary'
                    )}
                  >
                    {range.label}
                  </button>
                ))}
              </div>
            </div>
            
            <LearningChart
              data={activityData}
              type="area"
              metrics={['cardsReviewed', 'practiceTime']}
              height={350}
            />
          </Card>
        </motion.div>

        {/* Mastery & Breakdown */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Mastery Radar */}
          <motion.div variants={fadeInUp}>
            <Card>
              <h2 className="text-xl font-semibold text-text-primary font-heading mb-6">
                Topic Mastery
              </h2>
              <MasteryRadar
                data={mastery.slice(0, 8)}
                height={350}
              />
            </Card>
          </motion.div>

          {/* Topic Breakdown */}
          <motion.div variants={fadeInUp}>
            <Card>
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-xl font-semibold text-text-primary font-heading">
                  Progress by Topic
                </h2>
                <Badge>{mastery.length} topics</Badge>
              </div>
              <TopicBreakdown
                data={mastery}
                type="list"
                height={350}
              />
            </Card>
          </motion.div>
        </div>

        {/* Weak Spots */}
        <motion.div variants={fadeInUp}>
          <Card>
            <WeakSpotsAnalysis
              weakSpots={weakSpots}
              onPractice={handlePracticeTopic}
            />
          </Card>
        </motion.div>

        {/* Additional Insights */}
        <motion.div variants={fadeInUp}>
          <Card variant="elevated">
            <div className="flex items-center gap-3 mb-4">
              <span className="text-2xl">💡</span>
              <h2 className="text-xl font-semibold text-text-primary font-heading">
                Insights
              </h2>
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {/* Optimal review time */}
              <div className="p-4 bg-bg-tertiary rounded-xl">
                <h3 className="text-sm font-medium text-text-primary mb-1">
                  Best Study Time
                </h3>
                <p className="text-2xl font-bold text-indigo-400 font-heading">
                  9-11 AM
                </p>
                <p className="text-xs text-text-muted mt-1">
                  Based on your review patterns
                </p>
              </div>
              
              {/* Predicted mastery */}
              <div className="p-4 bg-bg-tertiary rounded-xl">
                <h3 className="text-sm font-medium text-text-primary mb-1">
                  Predicted Mastery
                </h3>
                <p className="text-2xl font-bold text-emerald-400 font-heading">
                  +15% this month
                </p>
                <p className="text-xs text-text-muted mt-1">
                  If you maintain current pace
                </p>
              </div>
              
              {/* Review efficiency */}
              <div className="p-4 bg-bg-tertiary rounded-xl">
                <h3 className="text-sm font-medium text-text-primary mb-1">
                  Review Efficiency
                </h3>
                <p className="text-2xl font-bold text-amber-400 font-heading">
                  {overview.avgRetention}%
                </p>
                <p className="text-xs text-text-muted mt-1">
                  {overview.avgRetention >= 80 ? 'Excellent!' : 'Room for improvement'}
                </p>
              </div>
            </div>
          </Card>
        </motion.div>
      </motion.div>
    </div>
  )
}

export default Analytics
