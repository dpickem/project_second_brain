# Frontend Application Design

> **Document Status**: Design Specification  
> **Last Updated**: December 2025  
> **Related Docs**: `06_backend_api.md`, `05_learning_system.md`

---

## 1. Overview

The React frontend provides the user interface for knowledge exploration, active learning, and progress tracking. It emphasizes clean design, responsive interactions, and seamless integration with the learning system.

### Design Goals

1. **Learning-Focused**: UI optimized for active practice, not passive consumption
2. **Responsive**: Works on desktop and tablet
3. **Accessible**: Keyboard navigation, screen reader support
4. **Fast**: Optimistic updates, efficient data fetching
5. **Delightful**: Smooth animations, clear feedback

---

## 2. Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           FRONTEND APPLICATION                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                              PAGES                                    │   │
│  │  Dashboard │ Knowledge │ Practice │ Review │ Analytics │ Assistant   │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                      │                                       │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                           COMPONENTS                                  │   │
│  │  Graph │ Cards │ Exercises │ Charts │ Navigation │ Forms │ Feedback  │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                      │                                       │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                         STATE & DATA                                  │   │
│  │       Zustand Stores       │       React Query       │    Context    │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                      │                                       │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                            SERVICES                                   │   │
│  │                    API Client (fetch/axios)                          │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Project Structure

```
frontend/
├── src/
│   ├── main.jsx                # Entry point
│   ├── App.jsx                 # Root component, routing
│   │
│   ├── pages/                  # Page components
│   │   ├── Dashboard.jsx
│   │   ├── KnowledgeExplorer.jsx
│   │   ├── PracticeSession.jsx
│   │   ├── ReviewQueue.jsx
│   │   ├── Analytics.jsx
│   │   └── Assistant.jsx
│   │
│   ├── components/             # Reusable components
│   │   ├── common/             # Generic UI components
│   │   │   ├── Button.jsx
│   │   │   ├── Card.jsx
│   │   │   ├── Modal.jsx
│   │   │   └── Loading.jsx
│   │   │
│   │   ├── knowledge/          # Knowledge explorer
│   │   │   ├── GraphVisualization.jsx
│   │   │   ├── TopicTree.jsx
│   │   │   ├── SearchBar.jsx
│   │   │   └── NoteViewer.jsx
│   │   │
│   │   ├── practice/           # Practice session
│   │   │   ├── ExerciseCard.jsx
│   │   │   ├── FreeRecallPrompt.jsx
│   │   │   ├── SelfExplainBox.jsx
│   │   │   ├── WorkedExample.jsx
│   │   │   ├── ConfidenceSlider.jsx
│   │   │   └── FeedbackPanel.jsx
│   │   │
│   │   ├── review/             # Spaced repetition
│   │   │   ├── ReviewCard.jsx
│   │   │   ├── RatingButtons.jsx
│   │   │   └── SessionProgress.jsx
│   │   │
│   │   ├── analytics/          # Analytics dashboard
│   │   │   ├── MasteryHeatmap.jsx
│   │   │   ├── LearningCurve.jsx
│   │   │   ├── WeakSpotsList.jsx
│   │   │   ├── StreakCalendar.jsx
│   │   │   └── TimeChart.jsx
│   │   │
│   │   └── assistant/          # Chat assistant
│   │       ├── ChatInterface.jsx
│   │       ├── MessageBubble.jsx
│   │       └── SuggestionCards.jsx
│   │
│   ├── hooks/                  # Custom hooks
│   │   ├── useApi.js
│   │   ├── usePracticeSession.js
│   │   ├── useReviewQueue.js
│   │   └── useKeyboardShortcuts.js
│   │
│   ├── stores/                 # Zustand stores
│   │   ├── practiceStore.js
│   │   ├── reviewStore.js
│   │   └── settingsStore.js
│   │
│   ├── services/               # API services
│   │   ├── api.js              # Base API client
│   │   ├── knowledgeApi.js
│   │   ├── practiceApi.js
│   │   └── analyticsApi.js
│   │
│   ├── styles/                 # Global styles
│   │   ├── globals.css
│   │   ├── variables.css
│   │   └── animations.css
│   │
│   └── utils/                  # Utilities
│       ├── formatters.js
│       └── helpers.js
│
├── index.html
├── package.json
├── vite.config.js
├── tailwind.config.js
└── Dockerfile
```

---

## 4. Key Pages

### 4.1 Dashboard

The main entry point showing daily learning status.

**Purpose**: The Dashboard serves as the user's home screen—a personalized command center that answers "What should I do today?" at a glance. It aggregates key metrics (streak, due cards) and surfaces actionable next steps.

**Key Design Decisions**:
- **React Query for data fetching**: Uses `useQuery` hooks to fetch stats and due cards with automatic caching, background refetching, and loading states. This keeps the UI responsive while ensuring data freshness.
- **Grid layout**: Organizes content into logical sections (quick actions, due preview, weak spots, streak calendar) that can be scanned quickly.
- **Action-oriented**: The "Continue Learning" section prominently displays the two primary actions (practice and review) with contextual sublabels showing recommended time or card counts.
- **Progressive disclosure**: Shows just enough information (e.g., 3 weak spots, 5 due cards) to guide decisions without overwhelming the user.

```jsx
// src/pages/Dashboard.jsx

import { useQuery } from '@tanstack/react-query';
import { StreakCalendar } from '../components/analytics/StreakCalendar';
import { DueCardsPreview } from '../components/review/DueCardsPreview';
import { WeakSpotsList } from '../components/analytics/WeakSpotsList';

export function Dashboard() {
  const { data: stats } = useQuery(['dailyStats'], fetchDailyStats);
  const { data: dueCards } = useQuery(['dueCards'], () => fetchDueCards(5));
  
  return (
    <div className="dashboard">
      <header className="dashboard-header">
        <h1>Good morning!</h1>
        <p className="text-muted">
          {stats?.streak} day streak • {stats?.dueToday} cards due
        </p>
      </header>
      
      <div className="dashboard-grid">
        {/* Quick Actions */}
        <section className="quick-actions">
          <h2>Continue Learning</h2>
          <div className="action-buttons">
            <ActionButton 
              to="/practice" 
              icon="🎯" 
              label="Practice Session"
              sublabel={`${stats?.practiceMinutes || 15} min recommended`}
            />
            <ActionButton 
              to="/review" 
              icon="📚" 
              label="Review Cards"
              sublabel={`${dueCards?.length || 0} due today`}
              highlight={dueCards?.length > 10}
            />
          </div>
        </section>
        
        {/* Due Cards Preview */}
        <section className="due-preview">
          <h2>Due for Review</h2>
          <DueCardsPreview cards={dueCards} />
        </section>
        
        {/* Weak Spots */}
        <section className="weak-spots">
          <h2>Focus Areas</h2>
          <WeakSpotsList limit={3} />
        </section>
        
        {/* Streak Calendar */}
        <section className="streak-section">
          <StreakCalendar />
        </section>
      </div>
    </div>
  );
}
```

### 4.2 Practice Session Page

**Purpose**: This page orchestrates an active learning session where users engage with exercises generated from their knowledge base. It manages the flow of presenting exercises, collecting responses, showing feedback, and tracking progress.

**Key Design Decisions**:
- **Custom hook abstraction** (`usePracticeSession`): Encapsulates all session logic (fetching items, submitting responses, navigation) in a reusable hook, keeping the component focused on rendering.
- **State machine pattern**: The component manages a clear flow: *exercise → response → submit → feedback → next*. Local state (`showFeedback`, `response`, `feedback`) tracks which phase the user is in.
- **Disabled state during feedback**: Once submitted, the exercise input is disabled to prevent edits while the user reviews feedback—reinforcing the "commit to an answer" learning principle.
- **Session completion handling**: When `currentItem` is null but `progress.completed > 0`, the session is complete, triggering a summary view.

```jsx
// src/pages/PracticeSession.jsx

import { useState } from 'react';
import { usePracticeSession } from '../hooks/usePracticeSession';
import { ExerciseCard } from '../components/practice/ExerciseCard';
import { FeedbackPanel } from '../components/practice/FeedbackPanel';
import { SessionProgress } from '../components/practice/SessionProgress';

export function PracticeSession() {
  const { 
    session, 
    currentItem, 
    submitResponse, 
    nextItem,
    progress,
    isLoading 
  } = usePracticeSession();
  
  const [response, setResponse] = useState('');
  const [showFeedback, setShowFeedback] = useState(false);
  const [feedback, setFeedback] = useState(null);
  
  const handleSubmit = async () => {
    const result = await submitResponse(currentItem.id, response);
    setFeedback(result);
    setShowFeedback(true);
  };
  
  const handleNext = () => {
    setShowFeedback(false);
    setResponse('');
    setFeedback(null);
    nextItem();
  };
  
  if (isLoading) return <Loading />;
  
  return (
    <div className="practice-session">
      <SessionProgress 
        completed={progress.completed}
        total={progress.total}
        timeElapsed={progress.timeElapsed}
      />
      
      <main className="practice-main">
        {currentItem && (
          <>
            <ExerciseCard 
              exercise={currentItem}
              response={response}
              onResponseChange={setResponse}
              onSubmit={handleSubmit}
              disabled={showFeedback}
            />
            
            {showFeedback && (
              <FeedbackPanel 
                feedback={feedback}
                onContinue={handleNext}
              />
            )}
          </>
        )}
        
        {!currentItem && progress.completed > 0 && (
          <SessionComplete session={session} />
        )}
      </main>
    </div>
  );
}
```

---

## 5. Key Components

### 5.1 Free Recall Prompt

**Purpose**: Implements the "free recall" learning technique—users must explain a concept from memory without looking at notes. This is one of the most effective evidence-based learning strategies, as it forces retrieval which strengthens memory.

**Key Design Decisions**:
- **Auto-focus on mount**: The `useEffect` + `useRef` pattern immediately focuses the textarea, reducing friction and signaling "start typing."
- **Progressive hint system**: Rather than showing all hints at once (which defeats the purpose), hints are revealed one at a time via `revealedHints` state. This maintains the challenge while providing scaffolding when truly stuck.
- **Timer component**: Visible timing creates gentle pressure that mimics test conditions—research shows this improves transfer to real-world recall.
- **Submission gating**: The submit button is disabled until there's actual content (`!response.trim()`), preventing empty submissions.
- **Clear visual hierarchy**: The "exercise type" badge, prompt text, instructions, and actions are visually distinct to guide the user's eye.

```jsx
// src/components/practice/FreeRecallPrompt.jsx

import { useState, useRef, useEffect } from 'react';
import { Timer } from '../common/Timer';
import { HintReveal } from './HintReveal';

export function FreeRecallPrompt({ 
  prompt, 
  hints = [], 
  onSubmit,
  disabled 
}) {
  const [response, setResponse] = useState('');
  const [revealedHints, setRevealedHints] = useState(0);
  const textareaRef = useRef(null);
  
  useEffect(() => {
    textareaRef.current?.focus();
  }, []);
  
  const revealNextHint = () => {
    if (revealedHints < hints.length) {
      setRevealedHints(prev => prev + 1);
    }
  };
  
  return (
    <div className="free-recall-prompt">
      <div className="prompt-header">
        <span className="exercise-type">Free Recall</span>
        <Timer />
      </div>
      
      <div className="prompt-content">
        <p className="prompt-text">{prompt}</p>
        
        <p className="instruction">
          Explain from memory — don't look at your notes!
        </p>
      </div>
      
      <textarea
        ref={textareaRef}
        className="response-textarea"
        value={response}
        onChange={(e) => setResponse(e.target.value)}
        placeholder="Type your explanation here..."
        disabled={disabled}
        rows={8}
      />
      
      <div className="prompt-actions">
        {hints.length > 0 && revealedHints < hints.length && (
          <button 
            className="btn-hint"
            onClick={revealNextHint}
          >
            Need a hint? ({hints.length - revealedHints} remaining)
          </button>
        )}
        
        <button
          className="btn-submit"
          onClick={() => onSubmit(response)}
          disabled={!response.trim() || disabled}
        >
          Check My Answer
        </button>
      </div>
      
      {revealedHints > 0 && (
        <HintReveal hints={hints.slice(0, revealedHints)} />
      )}
    </div>
  );
}
```

### 5.2 Confidence Slider

**Purpose**: Captures the user's metacognitive judgment—how confident they feel about their answer *before* seeing feedback. This serves two purposes: (1) calibrates the learning system (confident-but-wrong answers indicate misconceptions needing attention), and (2) trains users to better estimate their own knowledge.

**Key Design Decisions**:
- **Discrete buttons vs. slider**: Uses 5 distinct buttons rather than a continuous slider. Discrete options are faster to select, reduce decision paralysis, and map cleanly to backend scoring.
- **Emoji + text labels**: Combines emotional cues (emojis) with descriptive text for accessibility and faster visual scanning. Users can respond to either modality.
- **Controlled component pattern**: Value is passed in and changes are emitted via `onChange`, making it easy to integrate with any parent form.
- **5-point scale**: Matches common Likert scales used in educational research, enabling meaningful statistical analysis of calibration accuracy.

```jsx
// src/components/practice/ConfidenceSlider.jsx

export function ConfidenceSlider({ 
  value, 
  onChange,
  label = "How confident are you?" 
}) {
  const levels = [
    { value: 1, label: 'Not at all', emoji: '😰' },
    { value: 2, label: 'Slightly', emoji: '🤔' },
    { value: 3, label: 'Somewhat', emoji: '😐' },
    { value: 4, label: 'Fairly', emoji: '🙂' },
    { value: 5, label: 'Very', emoji: '😊' },
  ];
  
  return (
    <div className="confidence-slider">
      <label className="slider-label">{label}</label>
      
      <div className="slider-options">
        {levels.map((level) => (
          <button
            key={level.value}
            className={`confidence-option ${value === level.value ? 'selected' : ''}`}
            onClick={() => onChange(level.value)}
          >
            <span className="emoji">{level.emoji}</span>
            <span className="label">{level.label}</span>
          </button>
        ))}
      </div>
    </div>
  );
}
```

### 5.3 Review Card

**Purpose**: The core UI for spaced repetition review—presents a flashcard front, reveals the answer on demand, and collects a quality rating. This is the atomic unit of the SRS (Spaced Repetition System) workflow.

**Key Design Decisions**:
- **Two-phase reveal**: Users see the question first, must consciously click "Show Answer," then rate. This enforces active recall rather than passive recognition.
- **Framer Motion animations**: The `AnimatePresence` and `motion` components provide smooth transitions when revealing the answer. The subtle `whileHover` and `whileTap` effects on the reveal button add tactile feedback.
- **4-point rating scale**: Follows the Anki/SM-2 convention (Again/Hard/Good/Easy). Each rating maps to different scheduling intervals in the backend algorithm.
- **Keyboard shortcuts**: The `RatingButtons` component displays shortcut hints (`1`, `2`, `3`, `4`), enabling power users to rapidly process their review queue. These are handled by a keyboard hook at the page level.
- **Color-coded ratings**: Red → orange → green → blue provides instant visual mapping from "failed" to "mastered."

```jsx
// src/components/review/ReviewCard.jsx

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

export function ReviewCard({ card, onRate }) {
  const [isRevealed, setIsRevealed] = useState(false);
  
  return (
    <div className="review-card">
      <div className="card-front">
        <p className="card-question">{card.front}</p>
      </div>
      
      <AnimatePresence>
        {!isRevealed ? (
          <motion.button
            className="reveal-button"
            onClick={() => setIsRevealed(true)}
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
          >
            Show Answer
          </motion.button>
        ) : (
          <motion.div
            className="card-back"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3 }}
          >
            <p className="card-answer">{card.back}</p>
            
            <RatingButtons onRate={onRate} />
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

function RatingButtons({ onRate }) {
  const ratings = [
    { value: 1, label: 'Again', color: 'red', shortcut: '1' },
    { value: 2, label: 'Hard', color: 'orange', shortcut: '2' },
    { value: 3, label: 'Good', color: 'green', shortcut: '3' },
    { value: 4, label: 'Easy', color: 'blue', shortcut: '4' },
  ];
  
  return (
    <div className="rating-buttons">
      {ratings.map((rating) => (
        <button
          key={rating.value}
          className={`rating-btn rating-${rating.color}`}
          onClick={() => onRate(rating.value)}
        >
          <span className="rating-label">{rating.label}</span>
          <kbd className="shortcut">{rating.shortcut}</kbd>
        </button>
      ))}
    </div>
  );
}
```

### 5.4 Graph Visualization

**Purpose**: Renders the knowledge graph as an interactive force-directed network, allowing users to visually explore relationships between sources, concepts, and topics. This makes the abstract knowledge structure tangible and navigable.

**Key Design Decisions**:
- **D3.js force simulation**: Uses D3's physics-based layout where nodes repel each other (`forceManyBody`), links pull connected nodes together (`forceLink`), and everything gravitates toward center (`forceCenter`). This creates organic, readable layouts automatically.
- **Imperative D3 inside declarative React**: The `useEffect` + `useRef` pattern gives D3 direct DOM control inside the SVG element. The effect cleans up the previous simulation before creating a new one when `data` changes.
- **Visual encoding**:
  - *Color* distinguishes node types (Sources=indigo, Concepts=green, Topics=amber)
  - *Size* encodes importance via connection count (more connections = larger node)
  - *Edge thickness* encodes relationship strength/weight
- **Interactive dragging**: The `drag` function implements D3's drag behavior, letting users reposition nodes. Dragging "heats up" the simulation (`alphaTarget(0.3)`) so other nodes respond, then "cools down" when released.
- **Click handling**: `onNodeClick` callback enables parent components to respond to selections (e.g., showing a detail panel).

```jsx
// src/components/knowledge/GraphVisualization.jsx

import { useRef, useEffect } from 'react';
import * as d3 from 'd3';

export function GraphVisualization({ 
  data, 
  onNodeClick,
  colorBy = 'type',
  width = 800,
  height = 600 
}) {
  const svgRef = useRef(null);
  
  useEffect(() => {
    if (!data || !svgRef.current) return;
    
    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();
    
    // Color scale
    const colorScale = d3.scaleOrdinal()
      .domain(['Source', 'Concept', 'Topic'])
      .range(['#4f46e5', '#10b981', '#f59e0b']);
    
    // Create simulation
    const simulation = d3.forceSimulation(data.nodes)
      .force('link', d3.forceLink(data.edges)
        .id(d => d.id)
        .distance(100))
      .force('charge', d3.forceManyBody().strength(-300))
      .force('center', d3.forceCenter(width / 2, height / 2))
      .force('collision', d3.forceCollide().radius(30));
    
    // Draw edges
    const links = svg.append('g')
      .selectAll('line')
      .data(data.edges)
      .enter()
      .append('line')
      .attr('stroke', '#ddd')
      .attr('stroke-width', d => Math.sqrt(d.weight || 1));
    
    // Draw nodes
    const nodes = svg.append('g')
      .selectAll('circle')
      .data(data.nodes)
      .enter()
      .append('circle')
      .attr('r', d => getNodeSize(d))
      .attr('fill', d => colorScale(d.type))
      .attr('cursor', 'pointer')
      .call(drag(simulation))
      .on('click', (event, d) => onNodeClick?.(d));
    
    // Node labels
    const labels = svg.append('g')
      .selectAll('text')
      .data(data.nodes)
      .enter()
      .append('text')
      .text(d => truncate(d.label, 20))
      .attr('font-size', '12px')
      .attr('dx', 15)
      .attr('dy', 4);
    
    // Update positions on tick
    simulation.on('tick', () => {
      links
        .attr('x1', d => d.source.x)
        .attr('y1', d => d.source.y)
        .attr('x2', d => d.target.x)
        .attr('y2', d => d.target.y);
      
      nodes
        .attr('cx', d => d.x)
        .attr('cy', d => d.y);
      
      labels
        .attr('x', d => d.x)
        .attr('y', d => d.y);
    });
    
    return () => simulation.stop();
  }, [data, width, height]);
  
  return (
    <svg 
      ref={svgRef} 
      width={width} 
      height={height}
      className="graph-visualization"
    />
  );
}

function getNodeSize(node) {
  const baseSize = 8;
  const connectionBonus = Math.min(node.connectionCount || 0, 10) * 0.5;
  return baseSize + connectionBonus;
}

function drag(simulation) {
  return d3.drag()
    .on('start', (event, d) => {
      if (!event.active) simulation.alphaTarget(0.3).restart();
      d.fx = d.x;
      d.fy = d.y;
    })
    .on('drag', (event, d) => {
      d.fx = event.x;
      d.fy = event.y;
    })
    .on('end', (event, d) => {
      if (!event.active) simulation.alphaTarget(0);
      d.fx = null;
      d.fy = null;
    });
}
```

### 5.5 Mastery Heatmap

**Purpose**: Provides a bird's-eye view of mastery across all topics using a treemap visualization. Each rectangle represents a topic, sized by content volume and colored by mastery level—instantly revealing where the user is strong vs. struggling.

**Key Design Decisions**:
- **Treemap layout**: Recharts' `Treemap` component uses a space-filling algorithm where rectangle size encodes `noteCount` (more content = larger area). This gives proportional visual weight to major vs. minor topics.
- **5-tier color scale**: The `getColor` function maps mastery percentages to a traffic-light-inspired palette (red → orange → amber → lime → green). The thresholds (0.2, 0.4, 0.6, 0.8) create actionable bands.
- **Custom cell renderer**: The `CustomCell` component replaces the default Recharts treemap cell to show both the topic name and mastery percentage. Small cells (< 50px wide or < 30px tall) render nothing to avoid visual clutter.
- **ResponsiveContainer**: Wraps the chart to automatically resize with its parent, ensuring the visualization works across screen sizes.
- **Legend**: The color legend below the chart provides a key for interpreting the heatmap without hovering on individual cells.

```jsx
// src/components/analytics/MasteryHeatmap.jsx

import { Treemap, ResponsiveContainer } from 'recharts';

export function MasteryHeatmap({ data }) {
  const getColor = (mastery) => {
    if (mastery >= 0.8) return '#10b981';  // Green
    if (mastery >= 0.6) return '#84cc16';  // Lime
    if (mastery >= 0.4) return '#f59e0b';  // Amber
    if (mastery >= 0.2) return '#f97316';  // Orange
    return '#ef4444';                       // Red
  };
  
  const treeData = data.map(topic => ({
    name: topic.name,
    size: topic.noteCount || 1,
    mastery: topic.mastery,
    fill: getColor(topic.mastery),
  }));
  
  return (
    <div className="mastery-heatmap">
      <ResponsiveContainer width="100%" height={400}>
        <Treemap
          data={treeData}
          dataKey="size"
          stroke="#fff"
          content={<CustomCell />}
        />
      </ResponsiveContainer>
      
      <div className="legend">
        <span className="legend-item">
          <span className="dot" style={{ background: '#ef4444' }} /> 0-20%
        </span>
        <span className="legend-item">
          <span className="dot" style={{ background: '#f59e0b' }} /> 40-60%
        </span>
        <span className="legend-item">
          <span className="dot" style={{ background: '#10b981' }} /> 80-100%
        </span>
      </div>
    </div>
  );
}

function CustomCell({ x, y, width, height, name, fill, mastery }) {
  if (width < 50 || height < 30) return null;
  
  return (
    <g>
      <rect
        x={x}
        y={y}
        width={width}
        height={height}
        fill={fill}
        stroke="#fff"
        strokeWidth={2}
        rx={4}
      />
      <text
        x={x + width / 2}
        y={y + height / 2}
        textAnchor="middle"
        fill="#fff"
        fontSize={12}
        fontWeight="bold"
      >
        {name}
      </text>
      <text
        x={x + width / 2}
        y={y + height / 2 + 14}
        textAnchor="middle"
        fill="#fff"
        fontSize={10}
      >
        {Math.round(mastery * 100)}%
      </text>
    </g>
  );
}
```

---

## 6. State Management

> **What is Zustand?**  
> Zustand is a lightweight state management library for React. Unlike Redux, it requires minimal boilerplate—no reducers, action types, or dispatch calls. Stores are consumed as React hooks (e.g., `usePracticeStore()`), and unlike Context, no providers are needed. It's ideal for client-side state that doesn't come from the server.

**Purpose**: The practice store manages all client-side state for an active practice session—the current session data, which item the user is on, their responses, and timing. This state is *not* server-derived (that's React Query's job) but rather ephemeral UI state that lives only during a session.

**Key Design Decisions**:
- **Zustand over Redux**: The store is a single function call (`create`) returning a hook. No action types, no reducers, no Provider wrappers. State and actions coexist in one object.
- **`set` for state updates**: Each action calls `set()` with either a new state object or a function receiving current state. Zustand handles immutability internally.
- **`get` for derived data**: Methods like `getCurrentItem()` and `getProgress()` use `get()` to read current state and compute derived values on demand—avoiding stale closures.
- **Session lifecycle**: 
  - `startSession()` initializes everything including `startTime` for timing
  - `submitResponse()` appends to the responses array (immutable push)
  - `nextItem()` increments the index
  - `reset()` clears everything when leaving or restarting
- **Colocation of state + actions**: Unlike Redux where actions and reducers are separate files, Zustand keeps everything together, making the store self-documenting.

```javascript
// src/stores/practiceStore.js

import { create } from 'zustand';

export const usePracticeStore = create((set, get) => ({
  // State
  session: null,
  currentItemIndex: 0,
  responses: [],
  startTime: null,
  
  // Actions
  startSession: (session) => set({
    session,
    currentItemIndex: 0,
    responses: [],
    startTime: Date.now(),
  }),
  
  submitResponse: (itemId, response, feedback) => set((state) => ({
    responses: [...state.responses, { itemId, response, feedback }],
  })),
  
  nextItem: () => set((state) => ({
    currentItemIndex: state.currentItemIndex + 1,
  })),
  
  getCurrentItem: () => {
    const { session, currentItemIndex } = get();
    return session?.items?.[currentItemIndex] || null;
  },
  
  getProgress: () => {
    const { session, currentItemIndex, startTime } = get();
    return {
      completed: currentItemIndex,
      total: session?.items?.length || 0,
      timeElapsed: startTime ? Date.now() - startTime : 0,
    };
  },
  
  reset: () => set({
    session: null,
    currentItemIndex: 0,
    responses: [],
    startTime: null,
  }),
}));
```

---

## 7. API Client

**Purpose**: Provides a thin abstraction layer over `fetch` for communicating with the backend API. The base `ApiClient` class handles common concerns (base URL, headers, error handling), while domain-specific modules (`practiceApi`, etc.) expose semantic methods for each endpoint.

**Key Design Decisions**:
- **Environment-based URL**: `API_BASE` reads from Vite's environment variables (`import.meta.env.VITE_API_URL`), falling back to `localhost:8000` for local development. This enables the same code to work across dev, staging, and production.
- **Centralized error handling**: The `request()` method checks `response.ok`, extracts error details from the JSON body, and throws a consistent `Error`. Consumers don't need to handle HTTP status codes individually.
- **JSON by default**: Sets `Content-Type: application/json` header automatically and calls `response.json()` on success. The vast majority of API calls are JSON-based.
- **GET with query params**: The `get()` method accepts a `params` object and serializes it via `URLSearchParams`, avoiding manual string concatenation.
- **Domain-specific API modules**: `practiceApi.js` (and similar) import the base `api` client and expose named functions like `createSession()` and `submitResponse()`. This provides:
  - Type-like documentation of available endpoints
  - A place to add request/response transformations
  - Easier mocking in tests

```javascript
// src/services/api.js

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

class ApiClient {
  async request(path, options = {}) {
    const url = `${API_BASE}${path}`;
    
    const response = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });
    
    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || 'API request failed');
    }
    
    return response.json();
  }
  
  get(path, params) {
    const searchParams = params 
      ? '?' + new URLSearchParams(params).toString()
      : '';
    return this.request(`${path}${searchParams}`);
  }
  
  post(path, data) {
    return this.request(path, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }
}

export const api = new ApiClient();

// src/services/practiceApi.js

import { api } from './api';

export const practiceApi = {
  createSession: (params) => 
    api.post('/api/practice/session', params),
  
  submitResponse: (exerciseId, response) =>
    api.post(`/api/practice/exercise/${exerciseId}/submit`, response),
  
  getDueCards: (limit = 20) =>
    api.get('/api/review/due', { limit }),
  
  rateCard: (cardId, rating) =>
    api.post(`/api/review/rate/${cardId}`, { rating }),
};
```

---

## 8. Styling

**Purpose**: Establishes a consistent design system through CSS custom properties (variables) and reusable animation classes. This approach enables global theming, easy maintenance, and smooth visual feedback throughout the app.

**Key Design Decisions**:
- **CSS Custom Properties**: All design tokens (colors, spacing, radii, shadows, transitions) are defined as `--var-name` properties on `:root`. Components reference these variables rather than hardcoded values, enabling:
  - Single source of truth for design tokens
  - Easy theme switching (just reassign variables)
  - Consistent spacing and timing across components
- **Semantic color naming**: Colors are named by *role* (`--color-primary`, `--color-success`) not *appearance* (`--color-blue`). This makes the system adaptable to different color schemes.
- **Three-tier background system**: `--bg-primary` (white), `--bg-secondary` (light gray), and `--bg-dark` (charcoal) provide layering options for cards, modals, and containers.
- **Consistent spacing scale**: Uses a modular scale (0.25rem, 0.5rem, 1rem, 1.5rem, 2rem) that creates visual rhythm. Components use `--spacing-md` instead of magic numbers.
- **Animation utilities**: The `@keyframes` definitions (`fadeIn`, `slideUp`) and utility classes (`.animate-fade-in`, `.animate-slide-up`) provide plug-and-play entrance animations. Timing uses the transition variables for consistency.
- **Transition standardization**: `--transition-fast` (150ms) and `--transition-normal` (250ms) ensure interactive elements feel cohesive—hover states, reveals, and micro-interactions all share the same timing.

```css
/* src/styles/variables.css */

:root {
  /* Colors */
  --color-primary: #4f46e5;
  --color-primary-dark: #4338ca;
  --color-success: #10b981;
  --color-warning: #f59e0b;
  --color-danger: #ef4444;
  
  /* Backgrounds */
  --bg-primary: #ffffff;
  --bg-secondary: #f9fafb;
  --bg-dark: #111827;
  
  /* Text */
  --text-primary: #111827;
  --text-secondary: #6b7280;
  --text-muted: #9ca3af;
  
  /* Spacing */
  --spacing-xs: 0.25rem;
  --spacing-sm: 0.5rem;
  --spacing-md: 1rem;
  --spacing-lg: 1.5rem;
  --spacing-xl: 2rem;
  
  /* Border radius */
  --radius-sm: 0.25rem;
  --radius-md: 0.5rem;
  --radius-lg: 1rem;
  
  /* Shadows */
  --shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.05);
  --shadow-md: 0 4px 6px rgba(0, 0, 0, 0.1);
  --shadow-lg: 0 10px 15px rgba(0, 0, 0, 0.1);
  
  /* Transitions */
  --transition-fast: 150ms ease;
  --transition-normal: 250ms ease;
}

/* src/styles/animations.css */

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

@keyframes slideUp {
  from { 
    opacity: 0; 
    transform: translateY(10px); 
  }
  to { 
    opacity: 1; 
    transform: translateY(0); 
  }
}

.animate-fade-in {
  animation: fadeIn var(--transition-normal) forwards;
}

.animate-slide-up {
  animation: slideUp var(--transition-normal) forwards;
}
```

---

## 9. Related Documents

- `06_backend_api.md` — API endpoints consumed
- `05_learning_system.md` — Practice and review logic
- `08_mobile_capture.md` — Mobile PWA components

