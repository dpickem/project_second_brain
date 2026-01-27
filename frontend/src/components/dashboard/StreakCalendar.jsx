/**
 * StreakCalendar Component
 * 
 * GitHub-style activity heatmap showing practice days.
 */

import { useMemo, useRef, useEffect } from 'react'
import { motion } from 'framer-motion'
import { clsx } from 'clsx'
import { format, subDays, addDays, startOfWeek, endOfWeek, eachDayOfInterval, parseISO, isSameDay } from 'date-fns'
import { Card, Skeleton, Tooltip } from '../common'

const WEEKS_BEFORE = 13 // ~3 months before today
const WEEKS_AFTER = 13  // ~3 months after today

function getActivityLevel(count) {
  if (count === 0) return 0
  if (count <= 2) return 1
  if (count <= 5) return 2
  if (count <= 10) return 3
  return 4
}

const levelColors = {
  0: 'bg-slate-800',
  1: 'bg-emerald-900',
  2: 'bg-emerald-700',
  3: 'bg-emerald-500',
  4: 'bg-emerald-400',
}

function DayCell({ date, count, level, isToday, isFuture }) {
  const formattedDate = format(date, 'MMM d, yyyy')
  const tooltipContent = isFuture
    ? `${formattedDate} (upcoming)`
    : count > 0 
      ? `${count} review${count === 1 ? '' : 's'} on ${formattedDate}`
      : `No activity on ${formattedDate}`

  return (
    <Tooltip content={tooltipContent} side="top">
      <motion.div
        initial={{ scale: 0, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        transition={{ duration: 0.2 }}
        className={clsx(
          'w-3 h-3 rounded-sm cursor-pointer',
          'hover:ring-1 hover:ring-white/30 transition-all',
          isFuture ? 'bg-slate-800/50' : levelColors[level],
          isToday && 'ring-2 ring-amber-400'
        )}
      />
    </Tooltip>
  )
}

export function StreakCalendar({
  activityData = [], // Array of { date: string, count: number }
  isLoading = false,
  className,
}) {
  // Ref for auto-scrolling to current date
  const scrollContainerRef = useRef(null)

  // Generate calendar grid with past and future dates
  const { calendar, todayWeekIndex } = useMemo(() => {
    const today = new Date()
    const startDate = startOfWeek(subDays(today, WEEKS_BEFORE * 7))
    const endDate = endOfWeek(addDays(today, WEEKS_AFTER * 7))
    const allDays = eachDayOfInterval({ start: startDate, end: endDate })
    
    // Create a map for quick lookup
    const activityMap = new Map()
    activityData.forEach(({ date, count }) => {
      const d = typeof date === 'string' ? parseISO(date) : date
      const key = format(d, 'yyyy-MM-dd')
      activityMap.set(key, count)
    })

    // Group by weeks and track which week contains today
    const weeks = []
    let currentWeek = []
    let todayIdx = 0
    
    allDays.forEach((day, index) => {
      const dayOfWeek = day.getDay()
      const count = activityMap.get(format(day, 'yyyy-MM-dd')) || 0
      const isToday = isSameDay(day, today)
      const isFuture = day > today
      
      currentWeek.push({
        date: day,
        count,
        level: getActivityLevel(count),
        isToday,
        isFuture,
      })
      
      if (dayOfWeek === 6 || index === allDays.length - 1) {
        // Check if this week contains today
        if (currentWeek.some(d => d.isToday)) {
          todayIdx = weeks.length
        }
        weeks.push(currentWeek)
        currentWeek = []
      }
    })

    return { calendar: weeks, todayWeekIndex: todayIdx }
  }, [activityData])

  // Auto-scroll to center on today's week
  useEffect(() => {
    const scrollToToday = () => {
      if (scrollContainerRef.current) {
        const container = scrollContainerRef.current
        const weekWidth = 16 // 12px cell + 4px gap
        const todayPosition = todayWeekIndex * weekWidth
        const containerWidth = container.clientWidth
        // Center today in the view
        container.scrollLeft = todayPosition - (containerWidth / 2) + (weekWidth / 2)
      }
    }
    // Double RAF ensures layout is complete
    requestAnimationFrame(() => {
      requestAnimationFrame(scrollToToday)
    })
  }, [calendar, todayWeekIndex])

  // Calculate stats
  const stats = useMemo(() => {
    const total = activityData.reduce((sum, d) => sum + (d.count || 0), 0)
    const activeDays = activityData.filter(d => d.count > 0).length
    const average = activeDays > 0 ? Math.round(total / activeDays) : 0
    
    // Calculate current streak
    let streak = 0
    const today = new Date()
    for (let i = 0; i < 365; i++) {
      const checkDate = format(subDays(today, i), 'yyyy-MM-dd')
      const dayData = activityData.find(d => {
        const d2 = typeof d.date === 'string' ? d.date : format(d.date, 'yyyy-MM-dd')
        return d2 === checkDate
      })
      if (dayData && dayData.count > 0) {
        streak++
      } else if (i > 0) { // Allow today to be unfinished
        break
      }
    }

    return { total, activeDays, average, streak }
  }, [activityData])

  if (isLoading) {
    return (
      <Card className={className}>
        <div className="flex items-center justify-between mb-4">
          <Skeleton className="h-5 w-32" />
          <Skeleton className="h-4 w-24" />
        </div>
        <Skeleton className="h-24 w-full" />
      </Card>
    )
  }

  return (
    <Card className={clsx('overflow-visible', className)}>
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-text-primary font-heading flex items-center gap-2">
          <span>📊</span> Activity
        </h3>
        <div className="flex items-center gap-4 text-sm">
          <span className="text-text-muted">
            {stats.total} reviews
          </span>
          <span className="text-text-muted">
            {stats.activeDays} active days
          </span>
        </div>
      </div>

      {/* Calendar grid with sticky day labels */}
      <div className="relative flex">
        {/* Sticky day labels */}
        <div className="sticky left-0 z-10 flex flex-col gap-1 mr-2 text-xs text-text-muted bg-bg-elevated pr-2">
          <span className="h-3">Mon</span>
          <span className="h-3"></span>
          <span className="h-3">Wed</span>
          <span className="h-3"></span>
          <span className="h-3">Fri</span>
          <span className="h-3"></span>
          <span className="h-3">Sun</span>
        </div>

        {/* Scrollable weeks container */}
        <div ref={scrollContainerRef} className="overflow-x-auto overflow-y-visible pb-2 flex-1">
          <div className="flex gap-1">
            {/* Weeks */}
            {calendar.map((week, weekIndex) => (
              <div key={weekIndex} className="flex flex-col gap-1">
                {/* Fill empty days at start of first week */}
                {weekIndex === 0 && week[0]?.date.getDay() > 0 && (
                  Array.from({ length: week[0].date.getDay() }).map((_, i) => (
                    <div key={`empty-${i}`} className="w-3 h-3" />
                  ))
                )}
                {week.map((day) => (
                  <DayCell 
                    key={day.date.toISOString()}
                    {...day}
                  />
                ))}
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Legend */}
      <div className="flex items-center justify-between mt-4 pt-4 border-t border-border-primary">
        <div className="flex items-center gap-2">
          <span className="text-xs text-text-muted">Less</span>
          {[0, 1, 2, 3, 4].map((level) => (
            <div
              key={level}
              className={clsx('w-3 h-3 rounded-sm', levelColors[level])}
            />
          ))}
          <span className="text-xs text-text-muted">More</span>
        </div>

        {stats.streak > 0 && (
          <motion.div
            initial={{ opacity: 0, x: 10 }}
            animate={{ opacity: 1, x: 0 }}
            className="flex items-center gap-2 px-3 py-1 bg-amber-500/10 rounded-full"
          >
            <span className="text-amber-400">🔥</span>
            <span className="text-sm text-amber-300 font-medium">
              {stats.streak} day streak
            </span>
          </motion.div>
        )}
      </div>
    </Card>
  )
}

// Compact variant for smaller spaces
export function MiniStreakCalendar({ activityData = [], className }) {
  const recentDays = useMemo(() => {
    const today = new Date()
    const days = []
    
    const activityMap = new Map()
    activityData.forEach(({ date, count }) => {
      const d = typeof date === 'string' ? parseISO(date) : date
      activityMap.set(format(d, 'yyyy-MM-dd'), count)
    })

    for (let i = 13; i >= 0; i--) {
      const date = subDays(today, i)
      const count = activityMap.get(format(date, 'yyyy-MM-dd')) || 0
      days.push({
        date,
        count,
        level: getActivityLevel(count),
      })
    }

    return days
  }, [activityData])

  return (
    <div className={clsx('flex items-center gap-1', className)}>
      {recentDays.map((day) => (
        <Tooltip
          key={day.date.toISOString()}
          content={`${day.count} reviews - ${format(day.date, 'MMM d')}`}
          side="bottom"
        >
          <div
            className={clsx(
              'w-2 h-4 rounded-sm',
              levelColors[day.level]
            )}
          />
        </Tooltip>
      ))}
    </div>
  )
}

export default StreakCalendar
