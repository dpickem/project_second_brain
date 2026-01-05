# Implementation Roadmap

> **Document Status**: Master Implementation Plan  
> **Last Updated**: December 2025  
> **Related Docs**: `design_docs/00_system_overview.md`, Individual implementation plans in this folder

---

## Overview

This document provides the high-level implementation roadmap for the Second Brain system. Each phase has a corresponding detailed implementation plan in this folder.

| Phase | Focus | Weeks | Detailed Plan | Status |
|-------|-------|-------|---------------|--------|
| 1 | Foundation | 1-2 | `00_foundation_implementation.md` | ✅ |
| 2 | Ingestion Pipelines | 3-6 | `01_ingestion_layer_implementation.md` | ⬜ |
| 3 | LLM Processing | 7-10 | `02_llm_processing_implementation.md` | ⬜ |
| 3-4 | Knowledge Graph (Neo4j) | 7-14 | `04_knowledge_graph_neo4j_implementation.md` | ⬜ |
| 4 | Knowledge Hub (Obsidian) | 11-14 | `03_knowledge_hub_obsidian_implementation.md` | ⬜ |
| 5 | Knowledge Explorer UI | 15-17 | `05_knowledge_explorer_implementation.md` (planned) | ⬜ |
| 6 | Practice Session UI | 18-21 | `06_practice_session_implementation.md` (planned) | ⬜ |
| 7 | Spaced Repetition | 22-24 | `07_spaced_repetition_implementation.md` (planned) | ⬜ |
| 8 | Analytics Dashboard | 25-27 | `08_analytics_implementation.md` (planned) | ⬜ |
| 9 | Learning Assistant | 28-30 | `09_learning_assistant_implementation.md` (planned) | ⬜ |
| 10 | Polish & Production | Ongoing | `10_production_readiness.md` (planned) | ⬜ |

---

## Phase 1: Foundation (Weeks 1-2) ✅

> 📋 **Detailed Plan**: See [`00_foundation_implementation.md`](./00_foundation_implementation.md)

### Knowledge Hub Setup ✅
- [x] Set up Obsidian vault with folder structure (`scripts/setup/setup_vault.py`)
- [x] Configure essential plugins (Daily Notes, Templates, core plugins)
- [x] Create note templates for each content type (`scripts/setup/create_templates.py` — 13 templates)
- [x] Establish tagging taxonomy (`config/tag-taxonomy.yaml`)

### Extensible Content Type System ✅
- [x] Implement Content Type Registry (`backend/app/content_types.py`)
- [x] Support for technical, career, personal, and non-tech content (14 content types in `config/default.yaml`)
- [x] Dynamic template loading from configuration (Templater + Jinja2 template paths)
- [x] Extensibility without code changes

### Infrastructure ✅
- [x] Docker Compose configuration (all services)
- [x] FastAPI backend skeleton
- [x] React/Vite frontend skeleton
- [x] Neo4j integration
- [x] PostgreSQL for learning records (`backend/app/db/models.py`)
- [x] Redis for session caching (`backend/app/db/redis.py`)
- [x] Database migrations setup (Alembic configured)
- [x] Jinja2 templates for backend note generation (`config/templates/*.j2` — 13 templates)

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

> 📋 **Detailed Plan**: See [`02_llm_processing_implementation.md`](./02_llm_processing_implementation.md)

### Backend Services
- [ ] `llm_client.py` — Unified LLM interface via [LiteLLM](https://docs.litellm.ai/)
- [ ] Summarization prompts and chains
- [ ] Tag suggestion system
- [ ] Connection discovery via embeddings
- [ ] Mastery question generation (2-3 per section)

### Knowledge Graph
- [ ] Define node/edge schema (Concepts, Sources, Topics)
- [ ] Build query interfaces
- [ ] Semantic similarity search

---

## Phase 3-4: Knowledge Graph — Neo4j (Weeks 7-14)

> 📋 **Detailed Plan**: See [`04_knowledge_graph_neo4j_implementation.md`](./04_knowledge_graph_neo4j_implementation.md)

*Runs in parallel with LLM Processing and Knowledge Hub phases*

### Foundation (Weeks 7-8)
- [ ] Neo4j async client with connection pooling
- [ ] Pydantic models for nodes and relationships
- [ ] Schema creation (constraints, indexes, vector indexes)

### Core Operations (Weeks 9-10)
- [ ] Node CRUD operations (Source, Concept, Topic, Person, Tag)
- [ ] Relationship operations
- [ ] Vector search service
- [ ] Common query patterns (path finding, prerequisites, learning paths)

### Import & Sync (Weeks 11-14)
- [ ] Processing result import service
- [ ] Obsidian vault sync (bi-directional)
- [ ] Knowledge API endpoints

---

## Phase 4: Knowledge Hub — Obsidian (Weeks 11-14)

> 📋 **Detailed Plan**: See [`03_knowledge_hub_obsidian_implementation.md`](./03_knowledge_hub_obsidian_implementation.md)

### Vault Management
- [ ] Vault structure initialization
- [ ] Note templates (Paper, Article, Book, Code, Concept)
- [ ] Frontmatter YAML generation
- [ ] Wikilink handling and extraction

### Automation
- [ ] Folder index auto-generation
- [ ] Daily note generation
- [ ] Dataview query templates
- [ ] Tag taxonomy enforcement

### Synchronization
- [ ] Vault file watcher
- [ ] Bi-directional Neo4j sync
- [ ] Backend API for vault operations

---

## Phase 5: Frontend — Knowledge Explorer (Weeks 15-17)

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

## Phase 6: Frontend — Practice Session (Weeks 18-21)

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

## Phase 7: Frontend — Spaced Repetition (Weeks 22-24)

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

## Phase 8: Frontend — Analytics Dashboard (Weeks 25-27)

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

## Phase 9: Learning Assistant Chat (Weeks 28-30)

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

## Phase 10: Polish & Production (Ongoing)

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
| 1 - Foundation | ✅ Complete | Dec 2024 | Dec 2024 | Infrastructure, content types, templates, taxonomy |
| 2 - Ingestion | ⬜ Not Started | — | — | Plan ready |
| 3 - LLM Processing | ⬜ Not Started | — | — | Plan ready |
| 3-4 - Knowledge Graph (Neo4j) | ⬜ Not Started | — | — | Plan ready |
| 4 - Knowledge Hub (Obsidian) | ⬜ Not Started | — | — | Plan ready |
| 5 - Knowledge Explorer | ⬜ Not Started | — | — | — |
| 6 - Practice Session | ⬜ Not Started | — | — | — |
| 7 - Spaced Repetition | ⬜ Not Started | — | — | — |
| 8 - Analytics | ⬜ Not Started | — | — | — |
| 9 - Learning Assistant | ⬜ Not Started | — | — | — |
| 10 - Production | ⬜ Not Started | — | — | — |

**Legend**: ⬜ Not Started | 🟡 In Progress | ✅ Complete

---

## Related Documents

- `../design_docs/00_system_overview.md` — High-level system architecture
- `../README.md` — Project overview and vision
- `../LEARNING_THEORY.md` — Research foundations for learning system

