# Implementation Roadmap

> **Document Status**: Master Implementation Plan  
> **Last Updated**: January 7, 2026  
> **Related Docs**: `design_docs/00_system_overview.md`, Individual implementation plans in this folder

---

## Overview

This document provides the high-level implementation roadmap for the Second Brain system. Each phase has a corresponding detailed implementation plan in this folder.

| Phase | Focus | Weeks | Detailed Plan | Status |
|-------|-------|-------|---------------|--------|
| 1 | Foundation | 1-2 | `00_foundation_implementation.md` | ✅ Complete |
| 2 | Ingestion Pipelines | 3-6 | `01_ingestion_layer_implementation.md` | ✅ Complete |
| 3 | LLM Processing | 7-10 | `02_llm_processing_implementation.md` | ✅ Complete |
| 3-4 | Knowledge Graph (Neo4j) | 7-14 | `04_knowledge_graph_neo4j_implementation.md` | ✅ Complete |
| 4 | Knowledge Hub (Obsidian) | 11-14 | `03_knowledge_hub_obsidian_implementation.md` | ✅ Complete |
| 5 | Knowledge Explorer UI | 15-17 | `07_frontend_application_implementation.md` | 🟡 Partial |
| 6-8 | **Learning System** | 18-29 | `05_learning_system_implementation.md` | ✅ Backend Complete |
| — | Backend API Completion | — | `06_backend_api_implementation.md` | ✅ ~98% Complete |
| 9 | **Frontend Application** | 30-38 | `07_frontend_application_implementation.md` | ⬜ Not Started |
| 10 | **Mobile Capture (PWA)** | 39-42 | `08_mobile_capture_implementation.md` | ⬜ Not Started |
| 11 | Learning Assistant | 43-46 | `11_learning_assistant_implementation.md` (planned) | ⬜ Not Started |
| 12 | Polish & Production | Ongoing | `12_production_readiness.md` (planned) | 🟡 Ongoing |

---

## Phase 1: Foundation (Weeks 1-2) ✅ COMPLETE

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

## Phase 2: Ingestion Pipelines (Weeks 3-6) ✅ COMPLETE

> 📋 **Detailed Plan**: See [`01_ingestion_layer_implementation.md`](./01_ingestion_layer_implementation.md)

### Backend API ✅
- [x] `/api/capture/pdf` — PDF processing with highlight extraction
- [x] `/api/ingest/raindrop/sync` — Raindrop.io sync endpoint
- [x] `/api/capture/book` — Book photo OCR pipeline
- [x] `/api/ingest/github/sync` — GitHub starred repos importer
- [x] Handwriting recognition integration (Vision LLM via Mistral)

### Pipeline Scripts ✅
- [x] Raindrop → Obsidian sync (`pipelines/raindrop_sync.py`)
- [x] PDF ingestion with processing (`pipelines/pdf_processor.py`)
- [x] OCR pipeline for book photos (`pipelines/book_ocr.py`)
- [x] GitHub starred repos importer (`pipelines/github_importer.py`)
- [x] Voice transcription (`pipelines/voice_transcribe.py`)
- [x] Web article processor (`pipelines/web_article.py`)

---

## Phase 3: LLM Processing (Weeks 7-10) ✅ COMPLETE

> 📋 **Detailed Plan**: See [`02_llm_processing_implementation.md`](./02_llm_processing_implementation.md)

### Backend Services ✅
- [x] `llm/client.py` — Unified LLM interface via LiteLLM
- [x] Summarization stage (`processing/stages/summarization.py`)
- [x] Tag suggestion system (`processing/stages/tagging.py`)
- [x] Connection discovery (`processing/stages/connections.py`)
- [x] Mastery question generation (`processing/stages/questions.py`)
- [x] Content analysis (`processing/stages/content_analysis.py`)
- [x] Concept extraction (`processing/stages/extraction.py`)
- [x] Follow-up task generation (`processing/stages/followups.py`)

### Processing Pipeline ✅
- [x] Multi-stage async pipeline (`processing/pipeline.py`)
- [x] Processing run tracking in PostgreSQL
- [x] Obsidian note generation (`processing/output/obsidian_generator.py`)
- [x] Neo4j node generation (`processing/output/neo4j_generator.py`)
- [x] Cost tracking service (`services/cost_tracking.py`)

---

## Phase 3-4: Knowledge Graph — Neo4j (Weeks 7-14) ✅ COMPLETE

> 📋 **Detailed Plan**: See [`04_knowledge_graph_neo4j_implementation.md`](./04_knowledge_graph_neo4j_implementation.md)

### Foundation ✅
- [x] Neo4j async client with connection pooling (`services/knowledge_graph/client.py`)
- [x] Pydantic models for nodes and relationships (`services/knowledge_graph/schemas.py`)
- [x] Query patterns (`services/knowledge_graph/queries.py`)

### Core Operations ✅
- [x] Graph visualization endpoint (`/api/knowledge/graph`)
- [x] Node details endpoint (`/api/knowledge/node/{id}`)
- [x] Graph statistics endpoint (`/api/knowledge/stats`)
- [x] Health check endpoint (`/api/knowledge/health`)

### Import & Sync ✅
- [x] Processing result import to Neo4j
- [x] Obsidian vault sync (`/api/vault/sync`)
- [x] File watcher for real-time updates

---

## Phase 4: Knowledge Hub — Obsidian (Weeks 11-14) ✅ COMPLETE

> 📋 **Detailed Plan**: See [`03_knowledge_hub_obsidian_implementation.md`](./03_knowledge_hub_obsidian_implementation.md)

### Vault Management ✅
- [x] Vault structure initialization (`services/obsidian/vault.py`)
- [x] Note templates via Jinja2 (`config/templates/*.j2`)
- [x] Frontmatter YAML generation (`services/obsidian/frontmatter.py`)
- [x] Wikilink handling and extraction (`services/obsidian/links.py`)

### Automation ✅
- [x] Folder index auto-generation (`services/obsidian/indexer.py`)
- [x] Daily note generation (`services/obsidian/daily.py`)
- [x] Dataview query templates (`services/obsidian/dataview_queries.py`)
- [x] Tag taxonomy enforcement (`services/tag_service.py`)

### Synchronization ✅
- [x] Vault file watcher (`services/obsidian/watcher.py`)
- [x] Vault → Neo4j sync (`services/obsidian/sync.py`)
- [x] Lifecycle management (`services/obsidian/lifecycle.py`)
- [x] Backend API for vault operations (`routers/vault.py`)

---

## Phase 5: Frontend — Knowledge Explorer (Weeks 15-17) 🟡 PARTIAL

> 📋 **Detailed Plan**: See [`07_frontend_application_implementation.md`](./07_frontend_application_implementation.md) (Phase 9C)

### Components
- [x] Basic `<GraphVisualization />` — D3-force graph rendering
- [ ] `<KnowledgeExplorer />` — Main navigation view
- [ ] `<TopicTree />` — Hierarchical topic browser (Phase 9C.1)
- [ ] `<CommandPalette />` — Global search with ⌘K (Phase 9C.2)
- [ ] `<NoteViewer />` — Markdown note display (Phase 9C.3)

### Backend API ✅ COMPLETE
- [x] `/api/knowledge/graph` — Graph data for visualization
- [x] `/api/knowledge/stats` — Graph statistics
- [x] `/api/knowledge/node/{id}` — Node details
- [x] `/api/knowledge/search` — Semantic search (keyword, full-text, vector, hybrid)
- [x] `/api/knowledge/connections/{id}` — Node connections with direction filtering
- [x] `/api/knowledge/topics` — Topic hierarchy tree

---

## Phases 6-8: Learning System (Weeks 18-29) ✅ BACKEND COMPLETE

> 📋 **Detailed Plan**: See [`05_learning_system_implementation.md`](./05_learning_system_implementation.md)

The Learning System backend is fully implemented with all core services.

### Phase 6: Backend Foundation ✅ COMPLETE
- [x] FSRS spaced repetition algorithm (`services/learning/fsrs.py`)
- [x] Exercise generation system (`services/learning/exercise_generator.py`)
- [x] Adaptive difficulty based on mastery level
- [x] Code evaluation sandbox (`services/learning/code_sandbox.py`)
- [x] LLM-powered response evaluation (`services/learning/evaluator.py`)

### Phase 7: Practice & Review Backend ✅ COMPLETE
- [x] Practice session API (`routers/practice.py`)
- [x] Session orchestration (`services/learning/session_service.py`)
- [x] Card management and FSRS scheduling (`services/learning/spaced_rep_service.py`)
- [x] Review API (`routers/review.py`)

### Phase 7-8: Learning System Frontend → See Phase 9
> **Note**: All Learning System frontend tasks have been consolidated into Phase 9 (Frontend Application).
> See [`07_frontend_application_implementation.md`](./07_frontend_application_implementation.md) Tasks 9H, 9I, 9J.

### Phase 8: Analytics Backend ✅ COMPLETE
- [x] Mastery tracking service (`services/learning/mastery_service.py`)
- [x] Weak spot detection
- [x] Analytics API (`routers/analytics.py`)
- [x] Learning curve data endpoint
- [x] Time investment tracking (`LearningTimeLog` model, migration 009)
- [x] Practice streak tracking with milestones

### Testing ✅ COMPLETE
- [x] Unit tests for FSRS algorithm
- [x] Unit tests for all learning services
- [x] Integration tests for learning API
- [x] Test database safety checks

---

## Phase 9: Frontend Application (Weeks 30-38) ⬜ NOT STARTED

> 📋 **Detailed Plan**: See [`07_frontend_application_implementation.md`](./07_frontend_application_implementation.md)

The comprehensive frontend application phase covering **all remaining frontend work** (~129 hours):

| Sub-Phase | Days | Focus |
|-----------|------|-------|
| 9A | 1-5 | Foundation & Design System (tokens, components) |
| 9B | 6-10 | Dashboard Upgrade (stats, actions, streak calendar) |
| 9C | 11-15 | Knowledge Explorer (TopicTree, CommandPalette, NoteViewer) |
| 9D | 16-20 | Assistant Chat Interface |
| 9E-9G | 21-27 | Custom Hooks, Navigation, Settings |
| **9H** | 28-35 | **Practice Session UI** (exercises, feedback, confidence) |
| **9I** | 36-40 | **Review Queue UI** (flashcards, FSRS ratings) |
| **9J** | 41-45 | **Analytics Dashboard** (charts, mastery, weak spots) |

---

## Phase 10: Mobile Capture — PWA (Weeks 39-42) ⬜ NOT STARTED

> 📋 **Detailed Plan**: See [`08_mobile_capture_implementation.md`](./08_mobile_capture_implementation.md)  
> 📋 **Design Spec**: See [`../design_docs/08_mobile_capture.md`](../design_docs/08_mobile_capture.md)

Progressive Web App for low-friction knowledge capture on mobile devices.

### PWA Foundation
- [ ] PWA manifest configuration (`public/manifest.json`)
- [ ] Service Worker with offline queue (`public/sw.js`)
- [ ] IndexedDB for offline capture storage
- [ ] Background sync for queued uploads

### Capture UI Components
- [ ] `<MobileCapture />` — Main capture screen with 4 capture types
- [ ] `<PhotoCapture />` — Camera capture for book pages, whiteboards
- [ ] `<VoiceCapture />` — Voice memo recording with MediaRecorder API
- [ ] `<TextCapture />` — Quick text notes
- [ ] `<UrlCapture />` — URL/link saving

### Share Target Integration
- [ ] Share Target API registration in manifest
- [ ] `<ShareTarget />` — Handle shared content from other apps
- [ ] Support for shared URLs, text, and images

### Offline Support
- [ ] `useOnlineStatus()` hook — Network connectivity tracking
- [ ] `usePendingCaptures()` hook — Offline queue status
- [ ] `<OfflineBanner />` — Visual offline indicator
- [ ] Automatic sync when connectivity restored

### Mobile-Optimized Styles
- [ ] Safe area insets for notched devices
- [ ] Large touch targets (120px minimum)
- [ ] Touch feedback animations
- [ ] Dark theme for OLED battery savings

---

## Phase 11: Learning Assistant Backend (Weeks 43-46) ⬜ NOT STARTED

### Backend API & Services
- [ ] `/api/assistant/chat` — Conversational interface with RAG
- [ ] `/api/assistant/suggest-connections` — Graph-based suggestions
- [ ] `/api/assistant/study-plan` — Generate personalized plans
- [ ] RAG pipeline over knowledge graph

---

## Phase 12: Polish & Production (Ongoing) 🟡 IN PROGRESS

### Automation
- [x] Scheduled pipeline runs (APScheduler)
- [x] Background task processing (Celery)
- [ ] Weekly review reminders

### Quality
- [x] Structured logging
- [x] LLM cost tracking
- [x] Test coverage (pytest)
- [x] Rate limiting middleware (SlowAPI with configurable limits per endpoint type)
- [x] Error handling middleware (correlation IDs, custom exceptions, sanitized responses)
- [ ] Error monitoring (Sentry integration)
- [ ] CI/CD pipeline

### Mobile & UX
- [ ] Responsive design for all components
- [ ] Mobile capture workflow (see Phase 10 and `design_docs/08_mobile_capture.md`)
- [ ] Keyboard shortcuts for power users

---

## Progress Tracking

| Phase | Status | Start Date | Completion Date | Notes |
|-------|--------|------------|-----------------|-------|
| 1 - Foundation | ✅ Complete | Dec 2024 | Dec 2024 | Infrastructure, content types, templates, taxonomy |
| 2 - Ingestion | ✅ Complete | Dec 2024 | Jan 2025 | All pipelines implemented |
| 3 - LLM Processing | ✅ Complete | Dec 2024 | Jan 2025 | Full pipeline with 7 stages |
| 3-4 - Knowledge Graph | ✅ Complete | Dec 2024 | Jan 2025 | Neo4j client, queries, sync |
| 4 - Knowledge Hub | ✅ Complete | Dec 2024 | Jan 2025 | Full Obsidian integration |
| 5 - Knowledge Explorer | 🟡 Partial | Jan 2025 | — | Backend API complete, frontend components pending |
| 6-8 - Learning System | ✅ Backend | Jan 2026 | Jan 2026 | Backend complete, frontend needed |
| Backend API | ✅ ~98% | Jan 2026 | Jan 2026 | Only Assistant Router (Phase 11) remaining |
| 9 - Frontend Application | ⬜ Not Started | — | — | See `07_frontend_application_implementation.md` |
| 10 - Mobile Capture (PWA) | ⬜ Not Started | — | — | See `08_mobile_capture_implementation.md` |
| 11 - Learning Assistant | ⬜ Not Started | — | — | — |
| 12 - Production | 🟡 In Progress | Ongoing | — | Rate limiting, error handling, logging done |

**Legend**: ⬜ Not Started | 🟡 In Progress | ✅ Complete

---

## Next Steps (Recommended Priority)

### 1. Frontend Application Implementation (High Priority)

> 📋 **Detailed Plan**: See [`07_frontend_application_implementation.md`](./07_frontend_application_implementation.md)

**The backend is ~98% complete** with all core APIs implemented:
- ✅ Knowledge graph (search, connections, topics, visualization)
- ✅ Learning system (practice, review, analytics, streaks)
- ✅ Production hardening (rate limiting, error handling)
- ⬜ Only Assistant Router remains (Phase 11)

The comprehensive frontend plan covers:

**Phase 9A-9G: Core Application** (Days 1-27, 76h)
- Foundation & Design System (tokens, components, animations)
- Dashboard upgrade (stats, actions, streak calendar)
- Knowledge Explorer (TopicTree, CommandPalette, NoteViewer)
- Assistant Chat Interface
- Custom hooks, navigation, settings

**Phase 9H-9J: Learning System Frontend** (Days 28-45, 53h)
- **Practice Session UI** — ExerciseCard, ResponseInput, FeedbackDisplay, Monaco editor
- **Review Queue UI** — FlashCard, RatingButtons, FSRS interval preview
- **Analytics Dashboard** — MasteryOverview, LearningCurve, WeakSpotsPanel

**Total Estimated:** 129 hours (45 days)

### 2. Mobile Capture PWA (Phase 10)

> 📋 **Detailed Plan**: See [`08_mobile_capture_implementation.md`](./08_mobile_capture_implementation.md)

- Progressive Web App for on-the-go capture
- Offline-first with background sync
- Share Target integration for seamless capture from other apps
- **Estimated**: 56 hours across 14 days

### 3. Learning Assistant Backend (Phase 11)
- Chat endpoint with RAG over knowledge graph
- Connection suggestions
- Study plan generation

### 4. Production Readiness (Ongoing)
- Error monitoring (Sentry)
- CI/CD pipeline

---

## Related Documents

- `../design_docs/00_system_overview.md` — High-level system architecture
- `../design_docs/06_backend_api.md` — Backend API design (updated with implementation status)
- `../design_docs/07_frontend_application.md` — Frontend application design specification
- `../design_docs/08_mobile_capture.md` — Mobile capture PWA design specification
- `07_frontend_application_implementation.md` — Comprehensive frontend implementation plan
- `08_mobile_capture_implementation.md` — Mobile capture PWA implementation plan
- `../README.md` — Project overview and vision
- `../LEARNING_THEORY.md` — Research foundations for learning system
