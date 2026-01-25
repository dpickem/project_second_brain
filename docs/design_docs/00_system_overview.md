# System Overview: Second Brain Architecture

> **Document Status**: Design Specification  
> **Last Updated**: December 2025  
> **Related Docs**: All component design documents

---

## 1. Executive Summary

The Second Brain system transforms passive information consumption into active knowledge acquisition through automated ingestion, intelligent processing, and research-backed learning techniques. This document provides a high-level architectural overview of the entire system.

---

## 2. System Goals

### Primary Objectives

| Goal | Description | Success Metrics |
|------|-------------|-----------------|
| **Automated Ingestion** | Capture knowledge from diverse sources with minimal friction | < 3 seconds to capture; 95%+ ingestion success rate |
| **Intelligent Processing** | Distill raw content into structured, interconnected notes | Accurate summaries; relevant tags; discovered connections |
| **Active Learning** | Enable deliberate practice via spaced repetition and generation | Measurable retention improvement; consistent practice habits |
| **Knowledge Discovery** | Surface connections and insights across the knowledge base | Users discover non-obvious relationships |

### Design Principles

1. **Local-First**: Data ownership remains with the user (Obsidian vault, local Neo4j)
2. **Desirable Difficulties**: Learning features prioritize generation over recognition
3. **Minimal Friction**: Capture should be effortless; processing should be automated
4. **Interoperability**: Standard formats (Markdown, JSON) enable tool flexibility
5. **Progressive Enhancement**: System works without AI; AI enhances capabilities

---

## 3. High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              DATA SOURCES                                    │
├─────────────┬─────────────┬─────────────┬─────────────┬─────────────────────┤
│   Papers    │  Articles   │   Books     │    Code     │   Ideas & Notes     │
│  (PDFs)     │ (Raindrop)  │ (Photos)    │ (Git repos) │   (Mobile/CLI)      │
└──────┬──────┴──────┬──────┴──────┬──────┴──────┬──────┴──────────┬──────────┘
       │             │             │             │                 │
       ▼             ▼             ▼             ▼                 ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         INGESTION LAYER                                      │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────────────────┐│
│  │PDF Processor│ │Raindrop Sync│ │ Vision OCR  │ │   Quick Capture API     ││
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────────────────┘│
└─────────────────────────────────────┬───────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    PROCESSING LAYER (LLM-Powered)                            │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────────────────┐│
│  │Summarization│ │ Extraction  │ │  Tagging    │ │  Connection Discovery   ││
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────────────────┘│
└─────────────────────────────────────┬───────────────────────────────────────┘
                                      │
                    ┌─────────────────┼─────────────────┐
                    ▼                 ▼                 ▼
┌───────────────────────┐ ┌───────────────────┐ ┌─────────────────────────────┐
│   KNOWLEDGE HUB       │ │  KNOWLEDGE GRAPH  │ │     LEARNING RECORDS        │
│   (Obsidian Vault)    │ │     (Neo4j)       │ │     (PostgreSQL)            │
│                       │ │                   │ │                             │
│ • Markdown notes      │ │ • Concepts        │ │ • Practice attempts         │
│ • Folder hierarchy    │ │ • Relationships   │ │ • Spaced rep schedules      │
│ • Templates           │ │ • Embeddings      │ │ • Mastery scores            │
└───────────┬───────────┘ └─────────┬─────────┘ └──────────────┬──────────────┘
            │                       │                          │
            └───────────────────────┼──────────────────────────┘
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         WEB APPLICATION                                      │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │                         BACKEND (FastAPI)                               ││
│  │  /api/ingest/*  /api/knowledge/*  /api/practice/*  /api/assistant/*     ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │                        FRONTEND (React/Vite)                            ││
│  │  Knowledge Explorer │ Practice Session │ Review Queue │ Analytics       ││
│  └─────────────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      MOBILE CAPTURE (PWA)                                    │
│         📷 Camera  │  🎤 Voice  │  ✏️ Note  │  🔗 URL                        │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Component Summary

| Component | Technology | Purpose | Design Doc |
|-----------|------------|---------|------------|
| **Ingestion Layer** | Python pipelines | Capture and normalize content from diverse sources | `01_ingestion_layer.md` |
| **LLM Processing** | aisuite + multiple providers | Summarize, tag, extract, and connect content | `02_llm_processing_layer.md` |
| **Knowledge Hub** | Obsidian | Store and organize notes in Markdown format | `03_knowledge_hub_obsidian.md` |
| **Knowledge Graph** | Neo4j | Store relationships and enable graph queries | `04_knowledge_graph_neo4j.md` |
| **Learning System** | FSRS + exercises | Implement spaced repetition and active practice | `05_learning_system.md` |
| **Backend API** | FastAPI | REST API for all system operations | `06_backend_api.md` |
| **Frontend App** | React + Vite | User interface for learning and exploration | `07_frontend_application.md` |
| **Mobile Capture** | PWA | Low-friction mobile knowledge capture | `08_mobile_capture.md` |
---

> **Note**: FSRS stands for **Free Spaced Repetition Scheduler**, an open-source algorithm that outperforms the traditional SM-2 algorithm used by Anki. FSRS uses a more sophisticated model of memory to optimally schedule review intervals based on desired retention rates.

## 5. Data Flow Patterns

### 5.1 Content Ingestion Flow

```
Source → Ingestion Pipeline → Raw Content
                                  │
                                  ▼
                         LLM Processing
                                  │
                    ┌─────────────┼─────────────┐
                    ▼             ▼             ▼
              Obsidian Note  Neo4j Nodes    PostgreSQL
              (Markdown)     (Graph)        (Metadata)
```

### 5.2 Learning Flow

```
User selects topic → Backend generates exercise
                              │
                              ▼
                     User provides response
                              │
                              ▼
                     LLM evaluates + feedback
                              │
                    ┌─────────┴─────────┐
                    ▼                   ▼
            Update mastery        Schedule review
            (PostgreSQL)           (FSRS algorithm)
```

### 5.3 Query Flow

```
User query → Semantic search (embeddings)
                    │
                    ├── Neo4j graph traversal
                    │
                    ├── Full-text search
                    │
                    └── LLM synthesis
                              │
                              ▼
                    Unified response + sources
```

---

## 6. Technology Stack

### Core Infrastructure

| Layer | Technology | Rationale |
|-------|------------|-----------|
| **Container Orchestration** | Docker Compose | Simple local development; production-ready |
| **Backend Framework** | FastAPI | Async, type-safe, automatic OpenAPI docs |
| **Frontend Framework** | React + Vite | Fast development, component ecosystem |
| **Primary Database** | PostgreSQL | Reliable, supports complex queries |
| **Graph Database** | Neo4j | Native graph storage, Cypher queries |
| **Cache** | Redis | Session state, rate limiting |

### AI/ML Stack

| Component | Technology | Rationale |
|-----------|------------|-----------|
| **LLM Interface** | aisuite | Provider-agnostic, tool calling support |
| **Vision/OCR** | GPT-4V / Gemini Vision | Handwriting recognition, diagram understanding |
| **Embeddings** | OpenAI text-embedding-3-small | Semantic search, connection discovery |
| **Transcription** | Whisper API | Voice memo processing |

### External Services

| Service | Purpose |
|---------|---------|
| Raindrop.io | Web bookmark synchronization |
| GitHub API | Repository analysis |
| OpenAI API | Summarization, exercises |
| Anthropic API | Alternative LLM provider |
| Google AI | Gemini Vision for diagrams |

---

## 7. Security Considerations

### Data Privacy

- **Local-First**: Primary data storage is local (Obsidian vault, local databases)
- **API Key Management**: All keys stored in environment variables or secrets manager
- **No Cloud Sync Required**: System functions fully offline after initial setup

### Authentication

- **Single-User System**: Initial design is single-user (personal knowledge base)
- **Future Multi-User**: OAuth2 + JWT tokens planned for shared deployments

### API Security

- Rate limiting via Redis
- Input validation via Pydantic
- CORS configuration for frontend

---

## 8. Deployment Architecture

### Development Environment

```yaml
# docker-compose.yml
services:
  backend:
    build: ./backend
    ports: ["8000:8000"]
    depends_on: [neo4j, postgres, redis]
    
  frontend:
    build: ./frontend
    ports: ["3000:3000"]
    
  neo4j:
    image: neo4j:5
    ports: ["7474:7474", "7687:7687"]
    
  postgres:
    image: postgres:16
    ports: ["5432:5432"]
    
  redis:
    image: redis:7
    ports: ["6379:6379"]
```

### Production Considerations

- **Nginx** reverse proxy with SSL termination
- **Database backups** via pg_dump and Neo4j dump
- **Obsidian vault backup** via git or rsync
- **Monitoring** via Prometheus + Grafana (optional)

---

## 9. Integration Points

### Obsidian Vault

```
vault/
├── .obsidian/          # Plugin configs (auto-managed)
├── sources/            # Ingested content
├── topics/             # Auto-generated topic indices
├── exercises/          # Generated practice problems
├── reviews/            # Spaced repetition queue
└── meta/               # Templates, scripts
```

### Neo4j Graph

- Bi-directional sync with Obsidian via Neo4j Graph View plugin
- Backend queries for connection discovery
- Embedding storage for semantic search

### External APIs

```python
# Unified interface via aisuite
import aisuite as ai
client = ai.Client()

# All providers use same interface
response = client.chat.completions.create(
    model="anthropic/claude-4-5-sonnet-202509",
    messages=[...]
)
```

---

## 10. Success Metrics

### System Health

| Metric | Target | Measurement |
|--------|--------|-------------|
| Ingestion success rate | > 95% | Successful / attempted ingestions |
| API response time (p95) | < 500ms | Backend latency monitoring |
| LLM quality score | > 4/5 | User ratings on summaries |

### Learning Effectiveness

| Metric | Target | Measurement |
|--------|--------|-------------|
| Daily practice streak | > 80% days | Active practice sessions |
| Retention rate | > 70% at 30 days | Spaced rep success rate |
| Mastery progression | Positive trend | Average mastery score over time |

### User Engagement

| Metric | Target | Measurement |
|--------|--------|-------------|
| Content captured weekly | > 10 items | Ingestion count |
| Practice sessions weekly | > 5 sessions | Session count |
| Connections discovered | > 3 per week | New links created |

---

## 11. Development Roadmap

See `README.md` Implementation Roadmap for detailed phased plan.

### Phase Summary

| Phase | Focus | Duration |
|-------|-------|----------|
| 1 | Foundation & Infrastructure | Weeks 1-2 |
| 2 | Ingestion Pipelines | Weeks 3-6 |
| 3 | LLM Processing | Weeks 7-10 |
| 4 | Knowledge Explorer UI | Weeks 11-13 |
| 5 | Practice Session UI | Weeks 14-17 |
| 6 | Spaced Repetition | Weeks 18-20 |
| 7 | Analytics Dashboard | Weeks 21-23 |
| 8 | Learning Assistant | Weeks 24-26 |
| 9 | Polish & Production | Ongoing |

---

## 12. Related Documents

- `01_ingestion_layer.md` — Content ingestion pipelines
- `02_llm_processing_layer.md` — AI-powered processing
- `03_knowledge_hub_obsidian.md` — Obsidian vault structure
- `04_knowledge_graph_neo4j.md` — Neo4j schema and queries
- `05_learning_system.md` — Learning science and spaced repetition
- `06_backend_api.md` — FastAPI backend design
- `07_frontend_application.md` — React frontend design
- `08_mobile_capture.md` — Mobile PWA design

