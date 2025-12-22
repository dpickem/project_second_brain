# Implementation Roadmap

> **Document Status**: Master Implementation Plan  
> **Last Updated**: December 2025  
> **Related Docs**: `design_docs/00_system_overview.md`, Individual implementation plans in this folder

---

## Overview

This document provides the high-level implementation roadmap for the Second Brain system. Each phase has a corresponding detailed implementation plan in this folder.

| Phase | Focus | Weeks | Detailed Plan |
|-------|-------|-------|---------------|
| 1 | Foundation | 1-2 | `00_foundation_implementation.md` |
| 2 | Ingestion Pipelines | 3-6 | `01_ingestion_layer_implementation.md` |
| 3 | LLM Processing | 7-10 | `02_llm_processing_implementation.md` (planned) |
| 4 | Knowledge Explorer UI | 11-13 | `03_knowledge_explorer_implementation.md` (planned) |
| 5 | Practice Session UI | 14-17 | `04_practice_session_implementation.md` (planned) |
| 6 | Spaced Repetition | 18-20 | `05_spaced_repetition_implementation.md` (planned) |
| 7 | Analytics Dashboard | 21-23 | `06_analytics_implementation.md` (planned) |
| 8 | Learning Assistant | 24-26 | `07_learning_assistant_implementation.md` (planned) |
| 9 | Polish & Production | Ongoing | `08_production_readiness.md` (planned) |

---

## Phase 1: Foundation (Weeks 1-2)

> 📋 **Detailed Plan**: See [`00_foundation_implementation.md`](./00_foundation_implementation.md)

### Knowledge Hub Setup
- [ ] Set up Obsidian vault with folder structure
- [ ] Configure essential plugins (Dataview, Templater, Tasks)
- [ ] Create note templates for each content type
- [ ] Establish tagging taxonomy

### Infrastructure ✅ (Partially Complete)
- [x] Docker Compose configuration
- [x] FastAPI backend skeleton
- [x] React/Vite frontend skeleton
- [x] Neo4j integration
- [ ] Add PostgreSQL for learning records
- [ ] Add Redis for session caching
- [ ] Set up database migrations (Alembic)

---

## Phase 2: Ingestion Pipelines (Weeks 3-6)

> 📋 **Detailed Plan**: See [`01_ingestion_layer_implementation.md`](./01_ingestion_layer_implementation.md)

### Backend API
- [ ] `/api/ingest/pdf` — PDF processing with highlight extraction
- [ ] `/api/ingest/raindrop` — Raindrop.io sync endpoint
- [ ] `/api/ingest/ocr` — Book photo OCR pipeline
- [ ] `/api/ingest/github` — GitHub starred repos importer
- [ ] Handwriting recognition integration (Vision LLM)

### Pipeline Scripts
- [ ] Build Raindrop → Obsidian sync script
- [ ] Implement PDF ingestion with highlight extraction
- [ ] Create OCR pipeline for book photos
- [ ] GitHub starred repos importer

---

## Phase 3: LLM Processing (Weeks 7-10)

### Backend Services
- [ ] `llm_client.py` — Unified LLM interface via [aisuite](https://github.com/andrewyng/aisuite)
- [ ] Summarization prompts and chains
- [ ] Tag suggestion system
- [ ] Connection discovery via embeddings
- [ ] Mastery question generation (2-3 per section)

### Knowledge Graph
- [ ] Define node/edge schema (Concepts, Sources, Topics)
- [ ] Build query interfaces
- [ ] Semantic similarity search

---

## Phase 4: Frontend — Knowledge Explorer (Weeks 11-13)

### Components
- [ ] `<KnowledgeExplorer />` — Main navigation view
- [ ] `<GraphVisualization />` — D3-force graph rendering
- [ ] `<TopicTree />` — Hierarchical topic browser
- [ ] `<SearchBar />` — Semantic search interface
- [ ] `<NoteViewer />` — Markdown note display

### Backend API
- [ ] `/api/knowledge/graph` — Full graph data
- [ ] `/api/knowledge/search` — Semantic search
- [ ] `/api/knowledge/connections` — Related concepts
- [ ] `/api/knowledge/topics` — Topic hierarchy

---

## Phase 5: Frontend — Practice Session (Weeks 14-17)

### Components (Research-Backed)
- [ ] `<PracticeSession />` — Main practice container
- [ ] `<FreeRecallPrompt />` — Generation effect (Bjork)
- [ ] `<SelfExplainBox />` — Self-explanation prompts (Chi)
- [ ] `<WorkedExampleViewer />` — For novice topics (Van Gog)
- [ ] `<InterleavedQuestionSet />` — Mixed topic practice (Dunlosky)
- [ ] `<ConfidenceSlider />` — Metacognition rating
- [ ] `<FeedbackPanel />` — LLM-generated feedback

### Backend API
- [ ] `/api/practice/generate` — Exercise generation with difficulty adaptation
- [ ] `/api/practice/submit` — Response evaluation
- [ ] `/api/practice/feedback` — LLM feedback generation
- [ ] `/api/practice/self-explain` — Store and analyze explanations

### Backend Services
- [ ] `exercise_generator.py` — LLM-based exercise creation
- [ ] `mastery_tracker.py` — Track expertise per topic
- [ ] Adaptive difficulty based on mastery level

---

## Phase 6: Frontend — Spaced Repetition (Weeks 18-20)

### Components
- [ ] `<ReviewQueue />` — Due items list
- [ ] `<ReviewCard />` — Flashcard interface
- [ ] `<RatingButtons />` — Again/Hard/Good/Easy
- [ ] `<SessionProgress />` — Cards completed, streak display

### Backend API & Services
- [ ] `/api/review/due` — Get due items (FSRS algorithm)
- [ ] `/api/review/update` — Update card after review
- [ ] `spaced_rep.py` — FSRS scheduling algorithm
- [ ] Card generation from ingested content

---

## Phase 7: Frontend — Analytics Dashboard (Weeks 21-23)

### Components
- [ ] `<AnalyticsDashboard />` — Main analytics view
- [ ] `<MasteryHeatmap />` — Topic mastery treemap
- [ ] `<LearningCurve />` — Time-series accuracy chart
- [ ] `<WeakSpotsList />` — Low mastery topics with action buttons
- [ ] `<StreakCalendar />` — GitHub-style contribution calendar
- [ ] `<TimeInvestmentChart />` — Where time is spent

### Backend API
- [ ] `/api/analytics/mastery` — Mastery scores per topic
- [ ] `/api/analytics/weak-spots` — Identify struggling areas
- [ ] `/api/analytics/learning-curve` — Historical performance
- [ ] `/api/analytics/time-spent` — Time tracking by activity

### Database
- [ ] `practice_attempts` table — Full attempt history
- [ ] `mastery_snapshots` table — Daily mastery snapshots
- [ ] Analytics queries and aggregations

---

## Phase 8: Learning Assistant Chat (Weeks 24-26)

### Components
- [ ] `<AssistantChat />` — Chat interface
- [ ] `<ConnectionSuggestions />` — "Have you considered X relates to Y?"
- [ ] `<StudyPlanGenerator />` — Personalized study recommendations

### Backend API & Services
- [ ] `/api/assistant/chat` — Conversational interface
- [ ] `/api/assistant/suggest-connections` — Graph-based suggestions
- [ ] `/api/assistant/study-plan` — Generate personalized plans
- [ ] RAG pipeline over knowledge graph

---

## Phase 9: Polish & Production (Ongoing)

### Automation
- [ ] Scheduled pipeline runs (cron/Celery)
- [ ] Daily sync scripts
- [ ] Weekly review reminders

### Quality
- [ ] Error handling and monitoring (Sentry)
- [ ] Performance optimization
- [ ] Test coverage (pytest, React Testing Library)
- [ ] CI/CD pipeline

### Mobile & UX
- [ ] Responsive design for all components
- [ ] Mobile capture workflow (see `design_docs/08_mobile_capture.md`)
- [ ] PWA (Progressive Web App) support for offline access
- [ ] Keyboard shortcuts for power users

---

## Progress Tracking

Use this section to track overall progress:

| Phase | Status | Start Date | Completion Date | Notes |
|-------|--------|------------|-----------------|-------|
| 1 - Foundation | 🟡 In Progress | — | — | Docker/FastAPI/React done |
| 2 - Ingestion | ⬜ Not Started | — | — | Plan ready |
| 3 - LLM Processing | ⬜ Not Started | — | — | — |
| 4 - Knowledge Explorer | ⬜ Not Started | — | — | — |
| 5 - Practice Session | ⬜ Not Started | — | — | — |
| 6 - Spaced Repetition | ⬜ Not Started | — | — | — |
| 7 - Analytics | ⬜ Not Started | — | — | — |
| 8 - Learning Assistant | ⬜ Not Started | — | — | — |
| 9 - Production | ⬜ Not Started | — | — | — |

**Legend**: ⬜ Not Started | 🟡 In Progress | ✅ Complete

---

## Related Documents

- `../design_docs/00_system_overview.md` — High-level system architecture
- `../README.md` — Project overview and vision
- `../LEARNING_THEORY.md` — Research foundations for learning system

