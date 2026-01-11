/**
 * Analytics Page
 * 
 * Comprehensive learning analytics dashboard.
 */

import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { useQuery, keepPreviousData } from '@tanstack/react-query'
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
  const [viewMode, setViewMode] = useState('combined') // 'combined', 'cards', 'exercises'

  // Fetch analytics data
  const { data: overviewData, isLoading: overviewLoading } = useQuery({
    queryKey: ['analytics', 'overview'],
    queryFn: analyticsApi.getOverview,
  })

  const { data: chartData, isLoading: chartLoading, isFetching: chartFetching } = useQuery({
    queryKey: ['analytics', 'activity', timeRange],
    queryFn: () => analyticsApi.getActivityData(timeRange),
    placeholderData: keepPreviousData,
  })

  // Note: Mastery data comes from overview endpoint - no separate mastery query needed
  // The overview includes topic mastery states

  const { data: weakSpotsData } = useQuery({
    queryKey: ['analytics', 'weak-spots'],
    queryFn: analyticsApi.getWeakSpots,
  })

  // Only show full page loader on initial load, not when chart time range changes
  const isInitialLoading = overviewLoading || (chartLoading && !chartData)

  // Handle practice navigation
  const handlePracticeTopic = (topic) => {
    navigate(`/practice?topic=${encodeURIComponent(topic)}`)
  }

  if (isInitialLoading) {
    return <PageLoader message="Loading analytics..." />
  }

  // Transform API data to component format (snake_case to camelCase)
  const overview = overviewData ? {
    // General stats
    learningTime: (overviewData.total_practice_time_hours || 0) * 60, // Convert hours to minutes
    streak: overviewData.streak_days || 0,
    avgRetention: Math.round((overviewData.overall_mastery || 0) * 100),
    // Spaced repetition card stats
    spacedRepCardsTotal: overviewData.spaced_rep_cards_total || 0,
    spacedRepCardsMastered: overviewData.spaced_rep_cards_mastered || 0,
    spacedRepCardsLearning: overviewData.spaced_rep_cards_learning || 0,
    spacedRepCardsNew: overviewData.spaced_rep_cards_new || 0,
    spacedRepReviewsTotal: overviewData.spaced_rep_reviews_total || 0,
    // Exercise stats
    exercisesTotal: overviewData.exercises_total || 0,
    exercisesCompleted: overviewData.exercises_completed || 0,
    exercisesMastered: overviewData.exercises_mastered || 0,
    exercisesAttemptsTotal: overviewData.exercises_attempts_total || 0,
    exercisesAvgScore: overviewData.exercises_avg_score || 0,
  } : {
    learningTime: 0,
    streak: 0,
    avgRetention: 0,
    spacedRepCardsTotal: 0,
    spacedRepCardsMastered: 0,
    spacedRepCardsLearning: 0,
    spacedRepCardsNew: 0,
    spacedRepReviewsTotal: 0,
    exercisesTotal: 0,
    exercisesCompleted: 0,
    exercisesMastered: 0,
    exercisesAttemptsTotal: 0,
    exercisesAvgScore: 0,
  }

  const activityData = chartData?.data || []
  // Get mastery data from overview endpoint (topics array contains MasteryState objects)
  // TopicBreakdown expects: topic (name), mastery (0-100%), cardCount
  const mastery = (overviewData?.topics || []).map(t => ({
    id: t.topic_path,
    topic: t.topic_path.split('/').pop(), // TopicBreakdown expects 'topic' not 'name'
    mastery: Math.round((t.mastery_score || 0) * 100), // Convert 0-1 to percentage
    cardCount: t.practice_count || 0, // Use practice_count as proxy for activity
    practice_count: t.practice_count || 0,
    last_practiced: t.last_practiced,
  }))
  const weakSpots = weakSpotsData?.weak_spots || []

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
          <StatsGrid 
            stats={overview} 
            viewMode={viewMode}
            onViewModeChange={setViewMode}
          />
        </motion.div>

        {/* Activity Chart */}
        <motion.div variants={fadeInUp}>
          <Card>
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-semibold text-text-primary font-heading">
                {viewMode === 'cards' ? '🃏 Card Activity' : 
                 viewMode === 'exercises' ? '🏋️ Exercise Activity' : 
                 '📊 Learning Activity'}
              </h2>
              
              {/* Time range selector */}
              <div className="flex items-center gap-1 bg-bg-tertiary rounded-lg p-1">
                {timeRanges.map((range) => (
                  <button
                    type="button"
                    key={range.value}
                    onClick={() => setTimeRange(range.value)}
                    disabled={chartFetching}
                    className={clsx(
                      'px-3 py-1.5 text-sm rounded-md transition-colors',
                      timeRange === range.value
                        ? 'bg-indigo-600 text-white'
                        : 'text-text-secondary hover:text-text-primary',
                      chartFetching && 'opacity-50 cursor-not-allowed'
                    )}
                  >
                    {range.label}
                  </button>
                ))}
              </div>
            </div>
            
            <div className="relative">
              {chartFetching && (
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
              <LearningChart
                data={activityData}
                type="area"
                metrics={
                  viewMode === 'cards' 
                    ? ['cardsReviewed', 'practiceTime'] 
                    : viewMode === 'exercises'
                    ? ['exercisesAttempted', 'exerciseTime']
                    : ['cardsReviewed', 'exercisesAttempted', 'practiceTime']
                }
                height={350}
              />
            </div>
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
            
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              {/* Card mastery progress */}
              <div className="p-4 bg-bg-tertiary rounded-xl">
                <h3 className="text-sm font-medium text-text-primary mb-1">
                  Card Progress
                </h3>
                <p className="text-2xl font-bold text-indigo-400 font-heading">
                  {overview.spacedRepCardsTotal > 0 
                    ? Math.round((overview.spacedRepCardsMastered / overview.spacedRepCardsTotal) * 100) 
                    : 0}%
                </p>
                <p className="text-xs text-text-muted mt-1">
                  {overview.spacedRepCardsMastered} of {overview.spacedRepCardsTotal} cards mastered
                </p>
              </div>
              
              {/* Exercise mastery progress */}
              <div className="p-4 bg-bg-tertiary rounded-xl">
                <h3 className="text-sm font-medium text-text-primary mb-1">
                  Exercise Progress
                </h3>
                <p className="text-2xl font-bold text-teal-400 font-heading">
                  {overview.exercisesTotal > 0 
                    ? Math.round((overview.exercisesMastered / overview.exercisesTotal) * 100) 
                    : 0}%
                </p>
                <p className="text-xs text-text-muted mt-1">
                  {overview.exercisesMastered} of {overview.exercisesTotal} exercises mastered
                </p>
              </div>
              
              {/* Exercise average score */}
              <div className="p-4 bg-bg-tertiary rounded-xl">
                <h3 className="text-sm font-medium text-text-primary mb-1">
                  Avg Exercise Score
                </h3>
                <p className={`text-2xl font-bold font-heading ${
                  overview.exercisesAvgScore >= 0.8 ? 'text-emerald-400' : 
                  overview.exercisesAvgScore >= 0.6 ? 'text-amber-400' : 'text-red-400'
                }`}>
                  {Math.round(overview.exercisesAvgScore * 100)}%
                </p>
                <p className="text-xs text-text-muted mt-1">
                  {overview.exercisesAvgScore >= 0.8 ? 'Excellent!' : 
                   overview.exercisesAvgScore >= 0.6 ? 'Good progress' : 'Keep practicing'}
                </p>
              </div>
              
              {/* Overall retention */}
              <div className="p-4 bg-bg-tertiary rounded-xl">
                <h3 className="text-sm font-medium text-text-primary mb-1">
                  Overall Mastery
                </h3>
                <p className={`text-2xl font-bold font-heading ${
                  overview.avgRetention >= 80 ? 'text-emerald-400' : 
                  overview.avgRetention >= 60 ? 'text-indigo-400' : 'text-amber-400'
                }`}>
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
