/**
 * Card Catalogue Page
 * 
 * Browse and filter all available spaced repetition cards.
 */

import { useState, useMemo, useEffect, useCallback } from 'react'
import { useNavigate, useSearchParams, Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { useInfiniteQuery } from '@tanstack/react-query'
import { clsx } from 'clsx'
import { 
  MagnifyingGlassIcon, 
  FunnelIcon,
  BookOpenIcon,
  TagIcon,
} from '@heroicons/react/24/outline'
import { Card, Button, PageLoader, Badge, EmptyState, Spinner } from '../components/common'
import { reviewApi } from '../api/review'
import { fadeInUp, staggerContainer } from '../utils/animations'

const PAGE_SIZE = 100

const cardTypeConfig = {
  definition: { label: 'Definition', icon: '📖', color: 'primary' },
  comparison: { label: 'Comparison', icon: '⚖️', color: 'info' },
  application: { label: 'Application', icon: '🎯', color: 'success' },
  example: { label: 'Example', icon: '💡', color: 'warning' },
  concept: { label: 'Concept', icon: '🧠', color: 'purple' },
  fact: { label: 'Fact', icon: '✅', color: 'emerald' },
  process: { label: 'Process', icon: '🔄', color: 'amber' },
  basic: { label: 'Basic', icon: '📝', color: 'secondary' },
}

const stateOptions = [
  { value: '', label: 'All States' },
  { value: 'new', label: '✨ New' },
  { value: 'learning', label: '📖 Learning' },
  { value: 'review', label: '🔄 Review' },
  { value: 'mastered', label: '🎯 Mastered' },
]

const cardTypeOptions = [
  { value: '', label: 'All Types' },
  { value: 'definition', label: '📖 Definition' },
  { value: 'comparison', label: '⚖️ Comparison' },
  { value: 'application', label: '🎯 Application' },
  { value: 'example', label: '💡 Example' },
  { value: 'concept', label: '🧠 Concept' },
  { value: 'fact', label: '✅ Fact' },
  { value: 'process', label: '🔄 Process' },
]

const stateColors = {
  new: 'text-purple-400 bg-purple-500/10',
  learning: 'text-amber-400 bg-amber-500/10',
  review: 'text-indigo-400 bg-indigo-500/10',
  mastered: 'text-emerald-400 bg-emerald-500/10',
}

export function CardCatalogue() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  
  // Read topic filter from URL if present
  const topicFromUrl = searchParams.get('topic') || ''
  
  const [search, setSearch] = useState(topicFromUrl)
  const [typeFilter, setTypeFilter] = useState('')
  const [stateFilter, setStateFilter] = useState('')
  const [showFilters, setShowFilters] = useState(!!topicFromUrl)
  
  // Update search when URL topic changes
  useEffect(() => {
    if (topicFromUrl) {
      setSearch(topicFromUrl)
      setShowFilters(true)
    }
  }, [topicFromUrl])

  // Fetch cards with pagination
  const {
    data,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
    isLoading,
    error,
  } = useInfiniteQuery({
    queryKey: ['cards-catalogue', typeFilter, stateFilter, topicFromUrl],
    queryFn: ({ pageParam = 0 }) => reviewApi.listCards({
      topic: topicFromUrl || undefined,
      cardType: typeFilter || undefined,
      state: stateFilter || undefined,
      limit: PAGE_SIZE,
      offset: pageParam,
    }),
    getNextPageParam: (lastPage, allPages) => {
      // If we got fewer than PAGE_SIZE cards, we've reached the end
      if (!lastPage || lastPage.length < PAGE_SIZE) {
        return undefined
      }
      // Return the offset for the next page
      return allPages.reduce((total, page) => total + page.length, 0)
    },
    initialPageParam: 0,
  })

  // Flatten all pages into a single cards array
  const cards = useMemo(() => {
    return data?.pages?.flat() || []
  }, [data])

  // Filter cards by search (client-side for front/back content)
  const filteredCards = useMemo(() => {
    if (!cards.length) return []
    if (!search.trim()) return cards
    
    const searchLower = search.toLowerCase()
    return cards.filter(card => 
      card.front?.toLowerCase().includes(searchLower) ||
      card.back?.toLowerCase().includes(searchLower) ||
      card.tags?.some(tag => tag.toLowerCase().includes(searchLower))
    )
  }, [cards, search])
  
  // Load more handler
  const handleLoadMore = useCallback(() => {
    if (hasNextPage && !isFetchingNextPage) {
      fetchNextPage()
    }
  }, [hasNextPage, isFetchingNextPage, fetchNextPage])
  
  // Load all cards handler - fetch all pages
  const handleLoadAll = useCallback(async () => {
    if (!hasNextPage || isFetchingNextPage) return
    
    // Keep fetching until no more pages
    let hasMore = hasNextPage
    while (hasMore) {
      const result = await fetchNextPage()
      // Check if there are more pages
      hasMore = result.hasNextPage
    }
  }, [hasNextPage, isFetchingNextPage, fetchNextPage])

  // Group cards by primary tag (first tag or 'Uncategorized')
  const groupedCards = useMemo(() => {
    const groups = {}
    filteredCards.forEach(card => {
      const topic = card.tags?.[0] || 'Uncategorized'
      if (!groups[topic]) groups[topic] = []
      groups[topic].push(card)
    })
    return groups
  }, [filteredCards])

  const topicCount = Object.keys(groupedCards).length

  if (isLoading) {
    return <PageLoader message="Loading cards..." />
  }

  return (
    <div className="min-h-screen bg-bg-primary p-6 lg:p-8">
      <motion.div
        variants={staggerContainer}
        initial="hidden"
        animate="show"
        className="max-w-6xl mx-auto space-y-6"
      >
        {/* Header */}
        <motion.div variants={fadeInUp} className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-text-primary font-heading">
              🃏 Card Catalogue
            </h1>
            <p className="text-text-secondary mt-1">
              Browse {filteredCards.length} cards across {topicCount} topics
              {hasNextPage && <span className="text-amber-400"> (more available)</span>}
            </p>
          </div>
          <div className="flex gap-2">
            {hasNextPage && (
              <Button 
                variant="secondary" 
                onClick={handleLoadAll}
                disabled={isFetchingNextPage}
              >
                {isFetchingNextPage ? 'Loading...' : 'Load All Cards'}
              </Button>
            )}
            <Button variant="secondary" onClick={() => navigate('/review')}>
              Start Review Session
            </Button>
          </div>
        </motion.div>

        {/* Search and Filters */}
        <motion.div variants={fadeInUp}>
          <Card padding="md">
            <div className="flex flex-col sm:flex-row gap-4">
              {/* Search */}
              <div className="relative flex-1">
                <MagnifyingGlassIcon className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-text-muted" />
                <input
                  type="text"
                  placeholder="Search cards..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  className={clsx(
                    'w-full pl-10 pr-4 py-2 rounded-lg',
                    'bg-bg-tertiary border border-border-primary',
                    'text-text-primary placeholder-text-muted',
                    'focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500'
                  )}
                />
              </div>

              {/* Filter toggle */}
              <Button
                type="button"
                variant={showFilters ? 'primary' : 'secondary'}
                onClick={() => setShowFilters(!showFilters)}
                icon={<FunnelIcon className="w-4 h-4" />}
              >
                Filters
              </Button>
            </div>

            {/* Filter options */}
            {showFilters && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: 'auto', opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                className="mt-4 pt-4 border-t border-border-primary"
              >
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  {/* Type filter */}
                  <div>
                    <label className="block text-sm font-medium text-text-secondary mb-2">
                      Card Type
                    </label>
                    <select
                      value={typeFilter}
                      onChange={(e) => setTypeFilter(e.target.value)}
                      className={clsx(
                        'w-full px-3 py-2 rounded-lg',
                        'bg-bg-tertiary border border-border-primary',
                        'text-text-primary',
                        'focus:outline-none focus:ring-2 focus:ring-indigo-500/50'
                      )}
                    >
                      {cardTypeOptions.map(opt => (
                        <option key={opt.value} value={opt.value}>{opt.label}</option>
                      ))}
                    </select>
                  </div>

                  {/* State filter */}
                  <div>
                    <label className="block text-sm font-medium text-text-secondary mb-2">
                      Card State
                    </label>
                    <select
                      value={stateFilter}
                      onChange={(e) => setStateFilter(e.target.value)}
                      className={clsx(
                        'w-full px-3 py-2 rounded-lg',
                        'bg-bg-tertiary border border-border-primary',
                        'text-text-primary',
                        'focus:outline-none focus:ring-2 focus:ring-indigo-500/50'
                      )}
                    >
                      {stateOptions.map(opt => (
                        <option key={opt.value} value={opt.value}>{opt.label}</option>
                      ))}
                    </select>
                  </div>
                </div>
              </motion.div>
            )}
          </Card>
        </motion.div>

        {/* Error state */}
        {error && (
          <motion.div variants={fadeInUp}>
            <Card variant="elevated" className="bg-red-500/10 border-red-500/20">
              <p className="text-red-400">Failed to load cards: {error.message}</p>
            </Card>
          </motion.div>
        )}

        {/* Empty state */}
        {!isLoading && filteredCards.length === 0 && (
          <motion.div variants={fadeInUp}>
            <EmptyState
              icon="🃏"
              title="No cards found"
              description={search ? "Try adjusting your search or filters" : "Cards will appear here as you generate them from the Knowledge page"}
            />
          </motion.div>
        )}

        {/* Cards by Topic */}
        {Object.entries(groupedCards).map(([topic, topicCards]) => (
          <motion.div key={topic} variants={fadeInUp}>
            <Card>
              {/* Topic header */}
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold text-text-primary font-heading flex items-center gap-2">
                  <TagIcon className="w-5 h-5 text-text-muted" />
                  {topic}
                </h2>
                <Badge variant="secondary">{topicCards.length} cards</Badge>
              </div>

              {/* Card list */}
              <div className="space-y-3">
                {topicCards.map((card) => {
                  const typeConfig = cardTypeConfig[card.card_type] || {
                    label: card.card_type || 'Basic',
                    icon: '📝',
                    color: 'default',
                  }

                  return (
                    <div
                      key={card.id}
                      className={clsx(
                        'p-4 rounded-lg bg-bg-tertiary',
                        'border border-transparent hover:border-indigo-500/30',
                        'transition-colors group'
                      )}
                    >
                      <div className="flex items-start gap-4">
                        {/* Icon */}
                        <span className="text-2xl flex-shrink-0">{typeConfig.icon}</span>

                        {/* Content */}
                        <div className="flex-1 min-w-0">
                          {/* Type and state badges */}
                          <div className="flex items-center gap-2 mb-2">
                            <Badge variant={typeConfig.color} size="sm">
                              {typeConfig.label}
                            </Badge>
                            {card.state && (
                              <span className={clsx(
                                'text-xs px-2 py-0.5 rounded',
                                stateColors[card.state] || 'text-text-muted bg-bg-secondary'
                              )}>
                                {card.state}
                              </span>
                            )}
                          </div>

                          {/* Front (question) */}
                          <p className="text-sm font-medium text-text-primary line-clamp-2 group-hover:text-indigo-300 transition-colors">
                            {card.front}
                          </p>

                          {/* Back (answer preview) */}
                          <p className="text-xs text-text-muted line-clamp-1 mt-1">
                            {card.back}
                          </p>

                          {/* Meta info */}
                          <div className="flex items-center gap-4 mt-2 text-xs text-text-muted">
                            {card.hints?.length > 0 && (
                              <span>💡 {card.hints.length} hints</span>
                            )}
                            {card.total_reviews > 0 && (
                              <span>📊 {card.total_reviews} reviews</span>
                            )}
                            {card.content_id && (
                              <Link 
                                to={`/knowledge?content=${card.content_id}`}
                                className="text-indigo-400 hover:text-indigo-300"
                              >
                                📄 View Source
                              </Link>
                            )}
                          </div>
                        </div>

                        {/* Review button - navigate to review with topic filter */}
                        <Button
                          variant="secondary"
                          size="sm"
                          onClick={() => {
                            // Use the card's primary tag as the topic filter
                            const cardTopic = card.tags?.[0]
                            if (cardTopic) {
                              navigate(`/review?topic=${encodeURIComponent(cardTopic)}`)
                            } else {
                              navigate('/review')
                            }
                          }}
                          icon={<BookOpenIcon className="w-4 h-4" />}
                        >
                          Review Topic
                        </Button>
                      </div>
                    </div>
                  )
                })}
              </div>
            </Card>
          </motion.div>
        ))}

        {/* Load More button */}
        {hasNextPage && (
          <motion.div variants={fadeInUp} className="text-center py-4">
            <Button
              variant="secondary"
              onClick={handleLoadMore}
              disabled={isFetchingNextPage}
            >
              {isFetchingNextPage ? (
                <span className="flex items-center gap-2">
                  <Spinner size="sm" /> Loading more...
                </span>
              ) : (
                `Load More Cards (${cards.length} loaded)`
              )}
            </Button>
          </motion.div>
        )}

        {/* Back link */}
        <motion.div variants={fadeInUp} className="text-center pt-4">
          <Button variant="ghost" onClick={() => navigate('/')}>
            ← Back to Dashboard
          </Button>
        </motion.div>
      </motion.div>
    </div>
  )
}

export default CardCatalogue
