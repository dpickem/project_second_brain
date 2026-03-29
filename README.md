<div align="center">
  <img src="docs/image/logo.png" alt="Second Brain Logo" width="200" />
  <h1>Second Brain</h1>
  <p><strong>Personal Knowledge Management & Learning System</strong></p>

  > *"Tell me and I forget, teach me and I may remember, involve me and I learn."*
  > — Benjamin Franklin

  <p>A comprehensive system for ingesting, organizing, connecting, and actively learning from personal and professional knowledge sources—powered by LLMs and graph-based knowledge representation.</p>
</div>

---

## 📑 Table of Contents

- [Vision](#-vision)
- [Core Philosophy](#-core-philosophy)
  - [The Two-Fold Challenge](#the-two-fold-challenge)
  - [Key Insight](#key-insight)
- [System Architecture](#-system-architecture)
- [Ingestion Pipelines](#-ingestion-pipelines)
  - [Academic Papers (PDF)](#1-academic-papers-pdf)
  - [Web Content](#2-web-content-articles-blog-posts)
  - [Physical Books](#3-physical-books)
  - [Code & Repositories](#4-code--repositories)
  - [Ideas & Fleeting Notes](#5-ideas--fleeting-notes)
- [Organization Strategy](#️-organization-strategy)
- [Learning & Deliberate Practice](#-learning--deliberate-practice-system)
  - [Learning Science Foundation](#learning-science-foundation)
  - [Core Principles](#core-principles)
  - [Exercise Types](#exercise-types)
  - [Spaced Repetition Integration](#spaced-repetition-integration)
- [Technical Stack](#️-technical-stack)
- [Web Application](#️-web-application)
  - [Architecture](#architecture)
  - [Screenshots](#screenshots)
- [Mobile Capture (PWA)](#-mobile-capture-pwa)
- [Getting Started](#-getting-started)
  - [Prerequisites](#prerequisites)
  - [Quick Start](#quick-start)
  - [Setup Options](#setup-options)
  - [Access Points](#access-points)
- [Implementation Status](#-implementation-status)
- [Documentation](#-documentation)
  - [Design Documents](#design-documents)
  - [Implementation Plans](#implementation-plans)
- [Open Research Questions](#-open-research-questions)
- [Future Extensions](#-future-extensions)
  - [Tool Calling for Learning Assistant](#tool-calling-for-learning-assistant)
  - [MCP Integration](#mcp-integration-model-context-protocol)
- [Production Deployment](#-production-deployment)
- [Contributing](#-contributing)
- [Security](#-security)
- [License](#-license)
- [References](#-references)

---

## 🎯 Vision

Transform passive information consumption into **active knowledge acquisition** through:
1. **Automated ingestion** of diverse data sources
2. **Intelligent summarization** and connection discovery
3. **Deliberate practice** via AI-generated exercises and spaced repetition

---

## 🧠 Core Philosophy

### The Two-Fold Challenge

| Challenge | Focus | Solution Approach |
|-----------|-------|-------------------|
| **Extraction & Summarization** | LLM-powered | Automated pipelines that distill raw sources into structured, interconnected notes |
| **Learning & Retention** | Human-centered | Active exercises, spaced repetition, and deliberate practice systems |

### Key Insight
These challenges can be addressed independently, but solving extraction *in service of* learning maximizes value. Every piece of ingested content should feed into the learning loop.

---

## 📊 System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              DATA SOURCES                                    │
├─────────────┬─────────────┬─────────────┬─────────────┬─────────────────────┤
│   Papers    │  Articles   │   Books     │    Code     │   Ideas & Notes     │
│  (Books.app)│ (Raindrop)  │ (Physical)  │ (Git repos) │   (Manual input)    │
└──────┬──────┴──────┬──────┴──────┬──────┴──────┬──────┴──────────┬──────────┘
       │             │             │             │                 │
       ▼             ▼             ▼             ▼                 ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         INGESTION LAYER                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│  • PDF Parser + Highlight Extractor + Handwriting OCR (Vision LLM)           │
│  • Raindrop API Client                                                       │
│  • Book Photo OCR Pipeline (Mistral Vision API)                              │
│  • Git/GitHub API Integration                                                │
│  • Manual/CLI Entry Tools                                                    │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                       PROCESSING LAYER (LLM-Powered)                         │
├─────────────────────────────────────────────────────────────────────────────┤
│  • Summarization Engine                                                      │
│  • Key Concept Extraction                                                    │
│  • Tag & Topic Classification                                                │
│  • Connection Discovery (semantic similarity)                                │
│  • Follow-up Task Generation                                                 │
│  • Exercise & Quiz Generation                                                │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         KNOWLEDGE HUB (Obsidian)                             │
├─────────────────────────────────────────────────────────────────────────────┤
│  📁 vault/                                                                   │
│  ├── 📁 sources/           # Raw ingested content organized by type          │
│  │   ├── 📁 papers/                                                          │
│  │   ├── 📁 articles/                                                        │
│  │   ├── 📁 books/                                                           │
│  │   ├── 📁 code/                                                            │
│  │   └── 📁 ideas/                                                           │
│  ├── 📁 topics/            # Topic-based index notes (auto-generated)        │
│  ├── 📁 projects/          # Active learning projects                        │
│  ├── 📁 exercises/         # Generated practice problems                     │
│  ├── 📁 reviews/           # Spaced repetition queue                         │
│  └── 📁 meta/              # System config, templates, scripts               │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         KNOWLEDGE GRAPH (Neo4j)                              │
├─────────────────────────────────────────────────────────────────────────────┤
│  Nodes: Concepts, Sources, Topics, Authors, Tags                             │
│  Edges: RELATES_TO, CITES, CONTRADICTS, EXTENDS, PREREQUISITE_FOR           │
│  Queries: "What do I know about X?", "What connects A to B?"                 │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┴───────────────┐
                    ▼                               ▼
┌──────────────────────────────────┐  ┌──────────────────────────────────────┐
│     LEARNING SYSTEM (FSRS)       │  │       AI ASSISTANT (LLM Agent)       │
├──────────────────────────────────┤  ├──────────────────────────────────────┤
│  • Spaced repetition scheduling  │  │  • Natural language chat interface   │
│  • Flashcard management          │  │  • RAG over vault & knowledge graph  │
│  • Mastery tracking              │  │  • Streaming responses with citations│
│  • Practice session orchestration│  │  • Context-aware follow-up questions │
│  • Weak-spot identification      │  │  • Configurable LLM model selection  │
└──────────────────────────────────┘  │  • Conversation history & sessions   │
                                      │  • Source linking to original notes  │
                                      └──────────────────────────────────────┘
```

---

## 📥 Ingestion Pipelines

### 1. Academic Papers (PDF)
**Source**: MacOS Books app, Zotero, direct PDF uploads

The PDF pipeline uses a hybrid approach:
- **Mistral OCR** – Single API call that extracts full document text (markdown-formatted with tables & figures) AND detects handwritten notes/diagrams via image annotations
- **PyMuPDF** – Separate pass to extract PDF annotation objects (highlights, underlines, comments, sticky notes) from the PDF structure

```
┌─────────────────────────────────────────────────────────────────┐
│                         PDF INPUT                                │
└─────────────────────────────┬───────────────────────────────────┘
                              │
           ┌──────────────────┴──────────────────┐
           ▼                                     ▼
┌─────────────────────────┐           ┌─────────────────────────┐
│      Mistral OCR        │           │       PyMuPDF           │
│   (single API call)     │           │  (PDF structure parse)  │
├─────────────────────────┤           └────────────┬────────────┘
│ • Full text (markdown)  │                        │
│ • Tables & figures      │                        ▼
│ • Handwritten notes     │           ┌─────────────────────────┐
│   (via image analysis)  │           │   Digital Annotations   │
│ • Diagrams detected     │           │  • Highlights           │
└────────────┬────────────┘           │  • Underlines           │
             │                        │  • Comments/sticky notes│
             │                        └────────────┬────────────┘
             │                                     │
             └──────────────────┬──────────────────┘
                              ▼
              ┌───────────────────────────────┐
              │     Unified Content Merge      │
              │  (associate annotations with   │
              │   their context in the paper)  │
              └───────────────┬───────────────┘
                              │
                              ▼
              ┌───────────────────────────────┐
              │      LLM Summarization         │
              └───────────────┬───────────────┘
                              │
                              ▼
              ┌───────────────────────────────┐
              │       Markdown Note            │
              └───────────────────────────────┘
```

**Output**: Structured markdown with summary, key findings, highlights, handwritten notes with context, and auto-generated follow-up questions.

### 2. Web Content (Articles, Blog Posts)
**Source**: Raindrop.io API

```
Raindrop Collection → API fetch → Content extraction →
LLM Summarization → Markdown note with highlights preserved
```

**Integration Points**:
- Scheduled sync (daily/hourly)
- Preserve Raindrop collections as Obsidian folders or tags
- Extract user highlights as blockquotes
- Archive original content (avoid link rot)

### 3. Physical Books
**Source**: Photos of highlighted pages

```
Photo → Mistral Vision OCR → Highlight extraction →
Text cleanup → LLM processing → Structured book notes
```

**Workflow**:
1. Photograph highlighted pages with consistent lighting
2. Batch process through OCR pipeline
3. AI identifies highlighted vs. non-highlighted text
4. Aggregate into chapter-based or theme-based notes
5. Store original images in separate media vault

### 4. Code & Repositories
**Source**: GitHub starred repos, personal projects

```
Git repo → Structure analysis → README parsing →
Key file identification → LLM code summarization →
Markdown note with architecture overview, key patterns, learnings
```

**Captured Elements**:
- Repository purpose and architecture
- Notable design patterns
- Dependencies and technology stack
- Personal notes on why it was saved
- Code snippets worth remembering

### 5. Ideas & Fleeting Notes
**Source**: CLI tool, mobile app, voice memos

```
Quick capture → Inbox folder → Daily processing →
Elaboration or linking to existing notes
```

Quick capture sends items to an inbox folder for daily processing, elaboration, and linking to existing notes.

---

## 🏷️ Organization Strategy

### Primary: Content Type Hierarchy
```
sources/
├── papers/      # Academic papers, research
├── articles/    # Blog posts, news, essays
├── books/       # Book notes and highlights
├── code/        # Repository analyses
├── ideas/       # Fleeting notes, thoughts
└── work/        # Meetings, proposals, slack
```

### Secondary: Semantic Tags
Hierarchical topic tags (`ml/transformers`, `systems/distributed`) and meta tags (`status/actionable`, `quality/foundational`).

### Tertiary: Bidirectional Links
Leverage Obsidian's `[[wikilinks]]` extensively:
- Every note should link to related concepts
- Use block references for granular connections
- Auto-generate backlink summaries

---

## 🎓 Learning & Deliberate Practice System

> 📖 **Full details**: See **[LEARNING_THEORY.md](./LEARNING_THEORY.md)** for research foundations and citations.

### Learning Science Foundation

This system is grounded in research on human memory and learning. Key insights:

| Research | Key Finding | System Implementation |
|----------|-------------|----------------------|
| **Ericsson (2008)** — Deliberate Practice | Expertise requires structured practice with feedback, not just experience | Adaptive difficulty + immediate LLM feedback |
| **Bjork & Bjork (2011)** — Desirable Difficulties | Spacing, interleaving, and generation enhance long-term retention | Spaced repetition + varied exercises |
| **Dunlosky et al. (2013)** — Learning Techniques | Practice testing and distributed practice are highest utility; highlighting/rereading are lowest | Retrieval-based exercises, avoid recognition tasks |
| **Van Gog et al. (2011)** — Cognitive Load | Worked examples before problems for novices | Adaptive: examples → testing as mastery increases |
| **Chi et al. (1994)** — Self-Explanation | Prompting self-explanation builds correct mental models | Self-explanation prompts in exercises |

### Core Principles

1. **Learning ≠ Performance**: Easy recall during study (retrieval strength) doesn't guarantee long-term retention (storage strength)
2. **Generation over Recognition**: Producing answers from memory beats re-reading or highlighting
3. **Desirable Difficulties**: Spacing, interleaving, testing, and variation slow immediate performance but enhance retention
4. **Adaptive Scaffolding**: Novices get worked examples; intermediates get retrieval practice

### Exercise Types

```
              ┌─────────────────────────────┐
              │    1. INGEST NEW CONTENT    │
              │   (automated pipelines)     │
              └─────────────┬───────────────┘
                            │
                            ▼
              ┌─────────────────────────────┐
              │   2. UNDERSTAND & CONNECT   │
              │   (summarization, linking)  │
              └─────────────┬───────────────┘
                            │
                            ▼
              ┌─────────────────────────────┐
              │    3. ACTIVE PRACTICE       │◄────────┐
              │  (generation, not review)   │         │
              └─────────────┬───────────────┘         │
                            │                         │
                            ▼                         │
              ┌─────────────────────────────┐         │
              │   4. SPACED RETRIEVAL       │         │
              │  (testing > restudying)     │─────────┘
              └─────────────────────────────┘
```

### Exercise Generation

| Content Type | Exercise Types | Desirable Difficulty Applied |
|--------------|----------------|------------------------------|
| **Conceptual** | Explain-in-own-words, compare/contrast, teach-back | Generation effect (no notes allowed) |
| **Technical** | Implement from scratch, debug code, extend functionality | Generation + Variation |
| **Procedural** | Reconstruct steps from memory, adapt to new scenario | Retrieval practice + Interleaving |
| **Analytical** | Case study analysis, predict outcomes, critique approaches | Generation + Spacing |

### Spaced Repetition Integration

- Generate Anki-compatible flashcards from key concepts
- Schedule review sessions based on forgetting curves (FSRS algorithm)
- Track confidence levels per concept
- Surface weak areas for targeted practice


## 🛠️ Technical Stack

<table>
  <tr>
    <td align="center" width="96">
      <a href="https://www.python.org/">
        <img src="https://skillicons.dev/icons?i=python" width="48" height="48" alt="Python" />
      </a>
      <br>Python 3.11+
    </td>
    <td align="center" width="96">
      <a href="https://fastapi.tiangolo.com/">
        <img src="https://skillicons.dev/icons?i=fastapi" width="48" height="48" alt="FastAPI" />
      </a>
      <br>FastAPI
    </td>
    <td align="center" width="96">
      <a href="https://react.dev/">
        <img src="https://skillicons.dev/icons?i=react" width="48" height="48" alt="React" />
      </a>
      <br>React 18
    </td>
    <td align="center" width="96">
      <a href="https://vitejs.dev/">
        <img src="https://skillicons.dev/icons?i=vite" width="48" height="48" alt="Vite" />
      </a>
      <br>Vite
    </td>
    <td align="center" width="96">
      <a href="https://tailwindcss.com/">
        <img src="https://skillicons.dev/icons?i=tailwind" width="48" height="48" alt="TailwindCSS" />
      </a>
      <br>TailwindCSS
    </td>
    <td align="center" width="96">
      <a href="https://www.postgresql.org/">
        <img src="https://skillicons.dev/icons?i=postgres" width="48" height="48" alt="PostgreSQL" />
      </a>
      <br>PostgreSQL
    </td>
  </tr>
  <tr>
    <td align="center" width="96">
      <a href="https://neo4j.com/">
        <img src="https://cdn.simpleicons.org/neo4j/4581C3" width="48" height="48" alt="Neo4j" />
      </a>
      <br>Neo4j
    </td>
    <td align="center" width="96">
      <a href="https://redis.io/">
        <img src="https://skillicons.dev/icons?i=redis" width="48" height="48" alt="Redis" />
      </a>
      <br>Redis
    </td>
    <td align="center" width="96">
      <a href="https://www.docker.com/">
        <img src="https://skillicons.dev/icons?i=docker" width="48" height="48" alt="Docker" />
      </a>
      <br>Docker
    </td>
    <td align="center" width="96">
      <a href="https://obsidian.md/">
        <img src="https://cdn.simpleicons.org/obsidian/7C3AED" width="48" height="48" alt="Obsidian" />
      </a>
      <br>Obsidian
    </td>
    <td align="center" width="96">
      <a href="https://www.litellm.ai/">
        <img src="https://avatars.githubusercontent.com/u/139385568" width="48" height="48" alt="LiteLLM" style="border-radius: 8px;" />
      </a>
      <br>LiteLLM
    </td>
    <td align="center" width="96">
      <a href="https://docs.celeryq.dev/">
        <img src="https://cdn.simpleicons.org/celery/37814A" width="48" height="48" alt="Celery" />
      </a>
      <br>Celery
    </td>
  </tr>
  <tr>
    <td align="center" width="96">
      <a href="https://mistral.ai/">
        <img src="https://avatars.githubusercontent.com/u/132372032" width="48" height="48" alt="Mistral" style="border-radius: 8px;" />
      </a>
      <br>Mistral OCR
    </td>
    <td align="center" width="96">
      <a href="https://deepmind.google/technologies/gemini/">
        <img src="https://cdn.simpleicons.org/googlegemini/8E75B2" width="48" height="48" alt="Gemini" />
      </a>
      <br>Gemini
    </td>
    <td align="center" width="96">
      <a href="https://www.anthropic.com/">
        <img src="https://cdn.simpleicons.org/anthropic/D97757" width="48" height="48" alt="Anthropic" />
      </a>
      <br>Anthropic
    </td>
    <td align="center" width="96">
      <a href="https://openai.com/">
        <img src="https://avatars.githubusercontent.com/u/14957082" width="48" height="48" alt="OpenAI" style="border-radius: 8px;" />
      </a>
      <br>OpenAI
    </td>
    <td align="center" width="96">
      <a href="https://raindrop.io/">
        <img src="docs/image/raindrop.png" width="48" height="48" alt="Raindrop" />
      </a>
      <br>Raindrop.io
    </td>
    <td align="center" width="96">
      <a href="https://github.com/">
        <img src="https://skillicons.dev/icons?i=github" width="48" height="48" alt="GitHub" />
      </a>
      <br>GitHub API
    </td>
  </tr>
</table>

### Core Technologies

| Component | Technology | Rationale |
|-----------|------------|-----------|
| **Frontend** | React + Vite + TailwindCSS | Modern, fast, great DX |
| **Backend** | FastAPI + Python | Async, type-safe, OpenAPI docs |
| **Knowledge Hub** | Obsidian | Markdown-based, local-first, extensible |
| **Graph Database** | Neo4j | Native graph storage, Cypher queries |
| **Relational DB** | PostgreSQL | Learning records, user data |
| **Cache** | Redis | Session state, rate limiting |
| **Task Queue** | Celery | Async background job processing |
| **LLM Backbone** | [LiteLLM](https://www.litellm.ai/) ([GitHub](https://github.com/BerriAI/litellm)) | Unified interface to 100+ LLMs (OpenAI, Anthropic, Gemini, Mistral) |
| **Vision/OCR** | Mistral OCR (default for PDFs), Gemini 3 Flash | Document processing, handwriting recognition |

### APIs & Services

| Service | Purpose |
|---------|---------|
| Raindrop.io | Web bookmark sync |
| GitHub | Repository analysis |
| Mistral | Primary OCR for PDF/document processing |
| Google (Gemini) | Default text LLM for summarization, exercises |

---

## 🖥️ Web Application

The Second Brain web application provides a full-featured interface for knowledge management, spaced repetition learning, and analytics.

### Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│    Frontend     │────▶│     Backend     │────▶│   Data Layer    │
│  (React/Vite)   │     │   (FastAPI)     │     │ Neo4j/PG/Redis  │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

**Frontend Pages**: Dashboard, Practice Session, Exercises Catalogue, Card Catalogue, Review Queue, Knowledge Explorer, Knowledge Graph, Analytics, Follow-up Tasks, LLM Usage, Learning Assistant, Settings

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                           FRONTEND (React)                                    │
├──────────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │   Practice  │  │   Review    │  │  Analytics  │  │   Knowledge         │  │
│  │   Session   │  │   Queue     │  │  Dashboard  │  │   Explorer          │  │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────────────┘  │
│         │               │                │                    │              │
│  • Free recall    • Spaced cards   • Learning curves    • Graph viz         │
│  • Self-explain   • Due items      • Topic mastery      • Note browser      │
│  • Worked examples• Confidence     • Time invested      • Connection map    │
│  • Interleaved Qs   ratings        • Weak spots         • Search            │
└──────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                           BACKEND (FastAPI)                                   │
├──────────────────────────────────────────────────────────────────────────────┤
│  /api/practice/*        /api/review/*         /api/analytics/*               │
│  ├── generate-exercise  ├── due-items         ├── learning-curve            │
│  ├── submit-response    ├── update-card       ├── topic-mastery             │
│  ├── get-feedback       ├── schedule          ├── session-history           │
│  └── self-explain       └── confidence        └── weak-spots                │
│                                                                              │
│  /api/knowledge/*       /api/ingest/*         /api/assistant/*              │
│  ├── graph              ├── pdf               ├── chat                      │
│  ├── search             ├── raindrop          ├── generate-questions        │
│  ├── connections        ├── ocr               └── explain-connection        │
│  └── topics             └── github                                          │
│                                                                              │
│  /api/capture/*                                                             │
│  ├── text, url, photo, voice, pdf, book                                     │
└──────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                              DATA LAYER                                       │
├─────────────────────────┬─────────────────────────┬──────────────────────────┤
│        Neo4j            │       PostgreSQL        │        Redis             │
│   Knowledge Graph       │    Learning Records     │    Session Cache         │
├─────────────────────────┼─────────────────────────┼──────────────────────────┤
│ • Concepts & relations  │ • Practice attempts     │ • Active sessions        │
│ • Source documents      │ • Confidence ratings    │ • Temp exercise state    │
│ • Topic hierarchies     │ • Spaced rep schedule   │ • Rate limiting          │
│ • Semantic embeddings   │ • Time tracking         │                          │
└─────────────────────────┴─────────────────────────┴──────────────────────────┘
```
**Backend APIs**: `/api/practice/*`, `/api/review/*`, `/api/analytics/*`, `/api/knowledge/*`, `/api/ingest/*`, `/api/assistant/*`, `/api/capture/*`

### Screenshots

The application features a modern, dark-themed interface optimized for focused learning and knowledge management.

#### Dashboard
![Dashboard](docs/screenshots/dashboard.png)

The Dashboard serves as your home screen, answering "What should I do today?" at a glance. It displays a stats header showing your current streak, due review cards, and daily progress toward your learning goals. Quick action cards provide one-click access to practice sessions and review queues. The page also surfaces due cards for immediate review, identifies weak spots requiring attention, shows a streak calendar for motivation, and includes a quick capture input for rapidly saving ideas or URLs.

#### Practice Session
![Practice Session](docs/screenshots/practice.png)

The Practice Session page enables deep learning through structured exercises grounded in cognitive science. You can select topics hierarchically with visual mastery indicators showing your current level, configure session duration (5-30 minutes), and choose whether to reuse existing exercises or generate new AI-powered ones. Exercise types include free recall (retrieve from memory), self-explanation (explain concepts in your own words), worked examples (study solutions before attempting), code debugging, and teach-back prompts—all with immediate LLM-powered feedback on your responses.

#### Exercises Catalogue
![Exercises Catalogue](docs/screenshots/exercises.png)

The Exercises Catalogue provides a comprehensive browsing interface for all available exercises in the system. You can search exercises with full-text search, filter by exercise type (recall, explain, apply, code) and difficulty level, group by topic, and jump directly into practice mode. Each exercise card shows its type, difficulty, associated topic, and when it was last practiced, helping you identify fresh material or areas needing review.

#### Card Catalogue
![Card Catalogue](docs/screenshots/cards.png)

The Card Catalogue lets you browse and manage all spaced repetition flashcards in your knowledge base. Cards are organized by topic and state (new, learning, review, mastered), with filters for card type (definition, comparison, application, example, concept). You can search cards, view their front/back content, see scheduling information, and track mastery progress. This page complements the Review Queue by providing a library view of all your cards rather than just those currently due.

#### Review Queue (Spaced Repetition)
![Review Queue](docs/screenshots/review.png)

The Review Queue implements evidence-based spaced repetition using the FSRS (Free Spaced Repetition Scheduler) algorithm. Cards due for review are presented one at a time with active recall—you type your answer before seeing the correct response, which is more effective than simple recognition. The LLM evaluates your answers for semantic correctness, allowing for variations in wording. You then rate your confidence (Again/Hard/Good/Easy) to adjust scheduling. The page also supports AI-powered card generation from your notes.

#### Knowledge Explorer
![Knowledge Explorer](docs/screenshots/knowledge.png)

The Knowledge Explorer provides a unified interface for browsing your entire knowledge base stored in Obsidian. Toggle between tree view (folder hierarchy) and list view (flat listing), use real-time search to find notes instantly, and access the command palette with `⌘K` for quick navigation. Selected notes render inline with full markdown support including syntax highlighting for code blocks, LaTeX math, and wiki-link navigation. Deep linking support means you can share URLs to specific notes.

#### Knowledge Graph
![Knowledge Graph](docs/screenshots/graph.png)

The Knowledge Graph offers an interactive D3.js force-directed visualization of your Neo4j knowledge graph. Different node types (Content, Concepts, Notes) are color-coded, with edges representing relationships like RELATES_TO, CITES, EXTENDS, and PREREQUISITE_FOR. Click nodes to view details, drag to rearrange the layout, and scroll to zoom in/out. A statistics sidebar shows content breakdown by type. This visualization helps discover unexpected connections between ideas and identify knowledge clusters.

#### Analytics Dashboard
![Analytics Dashboard](docs/screenshots/analytics.png)

The Analytics Dashboard provides comprehensive insights into your learning journey. The stats grid displays total time invested, current streak, and overall mastery percentage. Activity charts show practice sessions and review activity over configurable time periods (7/30/90 days). A topic mastery radar visualizes your proficiency across different knowledge areas. Progress breakdowns show completion by topic, while weak spots analysis identifies topics with declining retention and provides "Practice Now" buttons for targeted improvement. Calculated insights surface trends and recommendations.

#### Follow-up Tasks
![Follow-up Tasks](docs/screenshots/tasks.png)

The Follow-up Tasks page displays actionable items generated automatically during content processing. When you ingest a paper, article, or book, the LLM identifies potential follow-up actions: research topics to explore, concepts to practice, connections to make with other notes, and applications to try. Tasks are categorized by type (research, practice, connect, apply, review) and priority (high, medium, low), with estimated time requirements. You can filter, search, and mark tasks complete as you work through them, turning passive reading into active engagement.

#### Ingest
![Ingest](docs/screenshots/ingest.png)

The Ingest page provides a unified interface for capturing new content directly from the desktop web UI and monitoring the entire ingestion pipeline. The top panel offers tabbed capture for text notes, URLs, and file uploads (PDFs, images, audio) with expandable options for tagging, title, and learning material generation (cards/exercises). The bottom panel displays a live, auto-refreshing ingestion queue showing all content items across every status (Pending, Processing, Completed, Failed). Click any item to expand a detail panel with full processing stage progress, error messages, cost/token stats, and a direct link to the generated note in the Knowledge Explorer.

#### LLM Usage
![LLM Usage](docs/screenshots/llm-usage.png)

The LLM Usage page provides a dashboard for monitoring your AI API usage and costs. It displays budget status with visual progress bars, spending trends over time, and breakdowns by model (GPT-4, Claude, Gemini, Mistral) and pipeline (ingestion, processing, exercises, assistant). This transparency helps you understand where AI costs go and optimize your usage. You can set monthly budgets and receive alerts when approaching limits.

#### Learning Assistant
![Learning Assistant](docs/screenshots/assistant.png)

The Learning Assistant is an AI-powered chat interface for exploring your knowledge base conversationally. Ask natural language questions like "What do I know about attention mechanisms?" or "How does paper X relate to paper Y?" The assistant searches your vault and knowledge graph, synthesizes information, and provides source citations linking back to your notes. You can configure which LLM model to use, and responses stream in real-time with full markdown rendering. This turns your knowledge base into an interactive, queryable resource.

#### Settings
![Settings](docs/screenshots/settings.png)

The Settings page lets you customize the application to your preferences. Appearance settings include compact mode for denser information display and animation toggles for reduced motion. Learning preferences let you set default session lengths and daily practice goals. Keyboard shortcuts are configurable, with defaults like `⌘K` for command palette and `⌘1-6` for page navigation. You can also manage notification preferences, configure LLM model defaults, and export your data for backup or migration purposes.

---

## 📱 Mobile Capture (PWA)

A critical bottleneck in knowledge management is **capture friction** — the effort required to get information into the system. The companion Progressive Web App provides a mobile-optimized interface for on-the-go capture with offline support.

### Capture Types

| Scenario | Capture Method | Processing |
|----------|----------------|------------|
| Physical book highlight | Photo of page | Vision OCR → highlight extraction → ingest |
| Fleeting idea | Voice memo or text | Transcription → LLM expansion → inbox |
| Interesting article | Share sheet / URL | Content fetch → summarize → save |
| Whiteboard / diagram | Photo | Vision LLM → describe → save with image |
| PDF document | File upload | Mistral OCR → full processing pipeline |

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     MOBILE DEVICE                                │
├─────────────────────────────────────────────────────────────────┤
│   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│   │   📷 Camera   │  │   🎤 Voice   │  │   📎 Share   │          │
│   │  (book pages, │  │   (ideas,    │  │   (URLs,     │          │
│   │  whiteboards) │  │   memos)     │  │   articles)  │          │
│   └──────┬───────┘  └──────┬───────┘  └──────┬───────┘          │
│          └─────────────────┼─────────────────┘                   │
│                   ┌────────▼────────┐                            │
│                   │   PWA / Mobile   │                            │
│                   │   Quick Capture  │                            │
│                   └────────┬────────┘                            │
└────────────────────────────┼─────────────────────────────────────┘
                             │ Upload (queue if offline)
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                      BACKEND                                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   /api/capture/photo     → Vision OCR → Text extraction          │
│   /api/capture/voice     → Whisper transcription → LLM expand    │
│   /api/capture/url       → Content fetch → Summarize             │
│   /api/capture/text      → Save to inbox → Tag suggestion        │
│   /api/capture/pdf       → Mistral OCR → Full pipeline           │
│   /api/capture/book      → Batch page OCR → Book notes           │
│                                                                  │
│                   ┌────────────────────┐                         │
│                   │   Inbox Processing  │                         │
│                   │  (async via Celery) │                         │
│                   └─────────┬──────────┘                         │
│                             │                                    │
│              ┌──────────────┼──────────────┐                     │
│              ▼              ▼              ▼                     │
│         Neo4j          Obsidian        PostgreSQL                │
│      (concepts)         (notes)       (metadata)                 │
└─────────────────────────────────────────────────────────────────┘
```

### Key Features

| Feature | Details |
|---------|---------|
| **Installable** | "Add to Home Screen" — launches like a native app |
| **Offline capable** | Service worker caches assets and queues captures in IndexedDB |
| **Background sync** | Automatically uploads queued captures when connection is restored |
| **Share target** | Receive shared URLs, text, and images from other apps (Android) |
| **< 3 second capture** | Minimal UI with large touch targets optimized for speed |

The PWA runs as a separate lightweight frontend (`localhost:5174`) and communicates with the same backend API. All captures are processed asynchronously via Celery and flow into the standard ingestion pipeline.

See [08_mobile_capture.md](docs/design_docs/08_mobile_capture.md) for full design details.

### Screenshots

<p align="center">
  <img src="docs/screenshots/capture-home.png" alt="Capture Home" width="250" />
  &nbsp;&nbsp;&nbsp;
  <img src="docs/screenshots/capture-text.png" alt="Text Capture" width="250" />
  &nbsp;&nbsp;&nbsp;
  <img src="docs/screenshots/capture-url.png" alt="URL Capture" width="250" />
</p>

*Left to right: Main capture screen with all capture types, Quick Note text capture, URL capture for saving links*

---

## 🚀 Getting Started

### Prerequisites

- Python 3.11+
- Docker Desktop installed and running
- At least one LLM API key (Gemini, Mistral, OpenAI, or Anthropic)

### Quick Start

```bash
# Clone the repository
git clone https://github.com/<your-username>/second-brain.git
cd second-brain

# Run the interactive setup script
python scripts/setup_project.py
```

The setup script guides you through:
1. **Environment configuration** — API keys, database credentials, data directory
2. **Vault setup** — Obsidian folder structure, templates, meta notes
3. **Docker services** — Start PostgreSQL, Neo4j, Redis, backend, frontend
4. **Database migrations** — Initialize schema

### Setup Options

```bash
python scripts/setup_project.py                    # Full interactive setup
python scripts/setup_project.py --non-interactive # Use defaults
python scripts/setup_project.py --env-only        # Only configure .env
python scripts/setup_project.py --help-only       # Show all available commands
python scripts/setup_project.py --help-env        # Show env variable reference
```

### Access Points

| Service | URL | Description |
|---------|-----|-------------|
| **Frontend** | http://localhost:3000 | Main web application |
| **Knowledge Graph** | http://localhost:3000/graph | Interactive graph visualization |
| **Mobile Capture PWA** | http://localhost:5174 | Mobile-optimized capture app |
| **Backend API** | http://localhost:8000 | REST API endpoints |
| **API Documentation** | http://localhost:8000/docs | Swagger/OpenAPI docs |
| **Neo4j Browser** | http://localhost:7474 | Graph database UI |

### Local Development (without Docker)

**Backend**: `cd backend && pip install -r requirements.txt && uvicorn app.main:app --reload`

**Frontend**: `cd frontend && npm install && npm run dev`

### Platform-Specific Setup

<details>
<summary><strong>macOS</strong></summary>

**Prerequisites:**

```bash
# Install Homebrew (if not installed)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install Python 3.11+
brew install python@3.11

# Install Docker Desktop
# Download from: https://www.docker.com/products/docker-desktop/
# Or via Homebrew:
brew install --cask docker

# Verify installations
python3 --version    # Should be 3.11+
docker --version     # Should show Docker version
docker compose version
```

**Notes:**
- Docker Desktop must be running before `docker compose` commands
- On Apple Silicon (M1/M2/M3), Docker automatically handles ARM64 architecture
- The `~` tilde expands correctly on macOS for local development

</details>

<details>
<summary><strong>Linux (Ubuntu/Debian)</strong></summary>

**Prerequisites:**

```bash
# Update package list
sudo apt update

# Install Python 3.11+
sudo apt install python3.11 python3.11-venv python3-pip

# Install Docker (official method)
# Remove old versions
sudo apt remove docker docker-engine docker.io containerd runc

# Install prerequisites
sudo apt install ca-certificates curl gnupg lsb-release

# Add Docker's official GPG key
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

# Set up repository
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker
sudo apt update
sudo apt install docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Add your user to the docker group (to run without sudo)
sudo usermod -aG docker $USER
newgrp docker

# Verify installations
python3 --version
docker --version
docker compose version
```

**Notes:**
- Log out and back in for docker group changes to take effect
- For systemd services, use absolute paths (tilde `~` won't expand)
- If running in WSL2, see Windows section for additional notes

</details>

<details>
<summary><strong>Windows (with WSL2)</strong></summary>

**Prerequisites:**

1. **Install WSL2:**
   ```powershell
   # Run in PowerShell as Administrator
   wsl --install
   # Restart your computer
   ```

2. **Install Docker Desktop:**
   - Download from: https://www.docker.com/products/docker-desktop/
   - During installation, enable "Use WSL 2 based engine"
   - After installation, open Docker Desktop Settings → Resources → WSL Integration
   - Enable integration with your WSL distribution

3. **In WSL2 terminal (Ubuntu):**
   ```bash
   # Install Python
   sudo apt update
   sudo apt install python3.11 python3.11-venv python3-pip

   # Verify Docker (provided by Docker Desktop)
   docker --version
   docker compose version
   ```

**Notes:**
- Run all commands from within WSL2, not PowerShell
- Store your project in the WSL filesystem (`/home/user/`) not `/mnt/c/` for better performance
- Use absolute paths in `.env` file (e.g., `/home/user/data` not `~/data`)
- Docker Desktop manages the Docker daemon; you don't need to start it manually

</details>

### Verifying Your Setup

After installation, verify everything is working:

```bash
# Check Python version (should be 3.11+)
python3 --version

# Check Docker is running
docker info

# Check Docker Compose
docker compose version

# Test Docker can run containers
docker run hello-world

# Verify GPU support (optional, for local LLM inference)
docker run --rm --gpus all nvidia/cuda:11.8.0-base-ubuntu22.04 nvidia-smi
```

### Troubleshooting Common Issues

<details>
<summary><strong>Docker daemon not running</strong></summary>

**macOS/Windows:** Start Docker Desktop application.

**Linux:**
```bash
sudo systemctl start docker
sudo systemctl enable docker  # Start on boot
```

</details>

<details>
<summary><strong>Permission denied when running docker</strong></summary>

**Linux:**
```bash
sudo usermod -aG docker $USER
# Log out and back in, or run:
newgrp docker
```

</details>

<details>
<summary><strong>Port already in use</strong></summary>

Check what's using the port:
```bash
# macOS/Linux
lsof -i :8000  # Backend
lsof -i :3000  # Frontend
lsof -i :5432  # PostgreSQL

# Stop the process or use different ports in docker-compose.yml
```

</details>

<details>
<summary><strong>Database connection refused</strong></summary>

1. Check if containers are running: `docker compose ps`
2. Check container logs: `docker compose logs postgres`
3. Verify `.env` file has correct credentials
4. Wait for healthcheck to pass (can take 30 seconds)

</details>

<details>
<summary><strong>Neo4j won't start / Out of memory</strong></summary>

Neo4j requires significant memory. Ensure Docker Desktop has at least 4GB RAM allocated:
- **Docker Desktop:** Settings → Resources → Memory → Set to 4GB+
- **Linux:** Check available memory with `free -h`

</details>

### Useful Commands

| Command | Purpose |
|---------|---------|
| `python scripts/pipelines/run_pipeline.py article <URL>` | Import web article |
| `python scripts/pipelines/run_pipeline.py pdf <file>` | Process PDF document |
| `python scripts/pipelines/run_pipeline.py book <file>` | OCR book photos |
| `python scripts/run_processing.py process-pending` | Process all pending content |
| `python scripts/run_all_tests.py` | Run all tests |
| `docker compose logs -f backend` | View backend logs |
| `docker compose down -v` | Stop and remove all data |

---

## 📋 Implementation Status

> 📁 **Full Details**: See [`implementation_plan/OVERVIEW.md`](docs/implementation_plan/OVERVIEW.md) for the complete implementation roadmap with task checklists.

| Phase | Focus | Status |
|-------|-------|--------|
| 1 | Foundation & Infrastructure | ✅ Complete |
| 2 | Ingestion Pipelines | ✅ Complete |
| 3 | LLM Processing | ✅ Complete |
| 4 | Knowledge Graph (Neo4j) | ✅ Complete |
| 5 | Backend API | ✅ Complete |
| 6 | Frontend Application | ✅ Complete |
| 7 | Learning System (Exercises + FSRS) | ✅ Complete |
| 8 | Analytics Dashboard | ✅ Complete |
| 9 | Mobile Capture (PWA) | ✅ Complete |
| 10 | Assistant Tool Calling | ⬜ Not Started |
| 11 | MCP Integration | ⬜ Not Started |
| 12 | Polish & Production | 🟡 In Progress |

---

## 📚 Documentation

### Design Documents

Detailed technical specifications for each system component:

| Document | Description |
|----------|-------------|
| [00_system_overview.md](docs/design_docs/00_system_overview.md) | High-level architecture and component interactions |
| [01_ingestion_layer.md](docs/design_docs/01_ingestion_layer.md) | Content ingestion pipelines and formats |
| [02_llm_processing_layer.md](docs/design_docs/02_llm_processing_layer.md) | LLM integration, prompts, and processing stages |
| [03_knowledge_hub_obsidian.md](docs/design_docs/03_knowledge_hub_obsidian.md) | Obsidian vault structure and templates |
| [04_knowledge_graph_neo4j.md](docs/design_docs/04_knowledge_graph_neo4j.md) | Neo4j schema, queries, and graph operations |
| [05_learning_system.md](docs/design_docs/05_learning_system.md) | Exercises, FSRS algorithm, mastery tracking |
| [06_backend_api.md](docs/design_docs/06_backend_api.md) | FastAPI endpoints and data models |
| [07_frontend_application.md](docs/design_docs/07_frontend_application.md) | React components and state management |
| [08_mobile_capture.md](docs/design_docs/08_mobile_capture.md) | PWA mobile capture workflow |
| [09_assistant_tool_calling.md](docs/design_docs/09_assistant_tool_calling.md) | LLM agent with tool calling |
| [10_observability.md](docs/design_docs/10_observability.md) | Logging, metrics, and monitoring |

### Implementation Plans

Step-by-step implementation guides with task checklists:

| Document | Description |
|----------|-------------|
| [OVERVIEW.md](docs/implementation_plan/OVERVIEW.md) | Master roadmap with all phases |
| [00_foundation_implementation.md](docs/implementation_plan/00_foundation_implementation.md) | Infrastructure setup |
| [01_ingestion_layer_implementation.md](docs/implementation_plan/01_ingestion_layer_implementation.md) | Content ingestion |
| [02_llm_processing_implementation.md](docs/implementation_plan/02_llm_processing_implementation.md) | LLM processing stages |
| [03_knowledge_hub_obsidian_implementation.md](docs/implementation_plan/03_knowledge_hub_obsidian_implementation.md) | Obsidian integration |
| [04_knowledge_graph_neo4j_implementation.md](docs/implementation_plan/04_knowledge_graph_neo4j_implementation.md) | Neo4j setup and queries |
| [05_learning_system_implementation.md](docs/implementation_plan/05_learning_system_implementation.md) | Learning system |
| [06_backend_api_implementation.md](docs/implementation_plan/06_backend_api_implementation.md) | API development |
| [07_frontend_application_implementation.md](docs/implementation_plan/07_frontend_application_implementation.md) | Frontend development |
| [08_mobile_capture_implementation.md](docs/implementation_plan/08_mobile_capture_implementation.md) | Mobile PWA |
| [09_assistant_tool_calling_implementation.md](docs/implementation_plan/09_assistant_tool_calling_implementation.md) | Assistant tool calling |
| [tech_debt.md](docs/implementation_plan/tech_debt.md) | Technical debt tracking |

### Other Documentation

| Document | Description |
|----------|-------------|
| [LEARNING_THEORY.md](LEARNING_THEORY.md) | Learning science research foundations |
| [TESTING.md](TESTING.md) | Testing guide and best practices |

---

## 🔬 Open Research Questions

1. **Human vs. Machine Connection-Making**: To what extent should we outsource relationship discovery to AI vs. keeping it as a human cognitive exercise?

2. **Information Overload**: How do we prevent the knowledge base from becoming overwhelming? What pruning and archival strategies work best?

3. **Exercise Quality**: Can current LLMs generate exercises that genuinely challenge and teach, or do they tend toward superficial quizzes?

---

## 🔮 Future Extensions

### Tool Calling for Learning Assistant

Enable the Learning Assistant to take actions through natural language requests, turning it from a Q&A interface into an interactive agent:

```
User: "Generate an exercise about attention mechanisms"
      → Assistant calls generate_exercise tool
      → Returns interactive exercise card inline in chat
```

**Planned Tools:**
| Tool | Description |
|------|-------------|
| `generate_exercise` | Generate adaptive exercise for a topic based on current mastery |
| `create_flashcard` | Create a spaced repetition card from conversation context |
| `search_knowledge` | Search the knowledge graph with natural language |
| `get_mastery` | Retrieve mastery state and learning history for a topic |
| `get_weak_spots` | Identify topics with declining retention needing review |

The design uses an LLM tool-calling loop: the model decides when to invoke tools, results are fed back for a synthesized response. See [09_assistant_tool_calling.md](docs/design_docs/09_assistant_tool_calling.md) for the full design.

### MCP Integration (Model Context Protocol)

Expose the knowledge base as [MCP servers](https://modelcontextprotocol.io/) so any MCP-compatible LLM client (Claude Desktop, Cursor, etc.) can directly query your Second Brain:

```
User (in Claude Desktop): "What do I know about distributed consensus?"
      → LLM queries Second Brain MCP server
      → Server searches Obsidian vault + Neo4j graph
      → Returns relevant notes with citations
```

**Planned MCP Servers:**
| Server | Capabilities |
|--------|-------------|
| **Vault server** | Read/search/write Obsidian notes, list by topic |
| **Knowledge graph server** | Cypher queries, concept lookup, relationship traversal |
| **Learning server** | Exercise generation, spaced rep scheduling, mastery queries |

---

## 🚢 Production Deployment

For production deployments, see the comprehensive guides in `docs/deployment/`:

| Document | Description |
|----------|-------------|
| [production.md](docs/deployment/production.md) | Full production deployment guide |
| [security.md](docs/deployment/security.md) | Security hardening and best practices |

**Key Production Steps:**

1. **Configure environment** — Set production values in `.env` (disable debug mode, set real secrets)
2. **SSL/TLS** — Use Let's Encrypt with Certbot for HTTPS certificates
3. **Reverse proxy** — Configure Nginx for rate limiting, security headers, and proxying
4. **CORS** — Restrict `CORS_ORIGINS` to your production domains
5. **Database security** — Strong passwords, network isolation, regular backups
6. **Container security** — Run as non-root, set resource limits, use read-only filesystems where possible

**Quick Production Checklist:**

```bash
# Required environment changes for production
DEBUG=false
SECRET_KEY=<generate-secure-random-key>
CORS_ORIGINS=https://yourdomain.com
POSTGRES_PASSWORD=<strong-password>
NEO4J_PASSWORD=<strong-password>
```

See [production.md](docs/deployment/production.md) for complete instructions including Docker configuration, Nginx setup, backup procedures, and monitoring.

---

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details on:

- Development environment setup
- Code style guidelines (Python and JavaScript/React)
- Commit message conventions
- Pull request process
- Testing requirements

**Quick Start for Contributors:**

```bash
# Fork and clone the repository
git clone https://github.com/<your-username>/second-brain.git
cd second-brain

# Run the setup script
python scripts/setup_project.py

# Create a feature branch
git checkout -b feature/your-feature-name

# Make changes, then submit a PR
```

---

## 🔒 Security

For security-related concerns, please review:

- **[Security Hardening Guide](docs/deployment/security.md)** — Production security best practices
- **Vulnerability Reporting** — If you discover a security vulnerability, please report it responsibly by emailing the maintainers directly rather than opening a public issue

**Security Features:**

- Configurable CORS origins (not wildcard in production)
- Environment-based secrets management
- Database credential isolation
- Rate limiting support
- Security headers via reverse proxy

---

## 📄 License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.

The MIT License is a permissive license that allows:
- ✅ Commercial use
- ✅ Modification
- ✅ Distribution
- ✅ Private use

With the only requirement being to include the license and copyright notice in copies.

---

## 📚 References

### Learning Science
> 📖 See **[LEARNING_THEORY.md](./LEARNING_THEORY.md)** for detailed research summaries.

Key sources: Ericsson (2008) on Deliberate Practice, Bjork & Bjork (2011) on Desirable Difficulties, Dunlosky et al. (2013) on Effective Learning Techniques.

### Knowledge Management
- [How to Take Smart Notes](https://takesmartnotes.com/) – Sönke Ahrens (Zettelkasten method)

### AI-Assisted Learning
- [ChatGPT Study Mode](https://openai.com/index/chatgpt-study-mode/)
- [Gemini Guided Learning](https://blog.google/outreach-initiatives/education/guided-learning/)

### Tools & Plugins
- [Google Code Wiki](https://developers.googleblog.com/introducing-code-wiki-accelerating-your-code-understanding/)
- [Obsidian Neo4j Graph View](https://www.obsidianstats.com/plugins/neo4j-graph-view)

---

*This is a living document. As the system evolves, so will this design.*
