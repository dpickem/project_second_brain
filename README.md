# Second Brain: Personal Knowledge Management & Learning System

> *"Tell me and I forget, teach me and I may remember, involve me and I learn."*
> Benjamin Franklin

A comprehensive system for ingesting, organizing, connecting, and actively learning from personal and professional knowledge sources—powered by LLMs and graph-based knowledge representation.

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
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                       LEARNING ASSISTANT (LLM Agent)                         │
├─────────────────────────────────────────────────────────────────────────────┤
│  • Conversational knowledge retrieval                                        │
│  • Guided learning sessions                                                  │
│  • Adaptive exercise generation                                              │
│  • Progress tracking & weak-spot identification                              │
│  • Connection suggestions ("Have you considered how X relates to Y?")        │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 📥 Ingestion Pipelines

### 1. Academic Papers (PDF)
**Source**: MacOS Books app, Zotero, direct PDF uploads

Papers may contain two types of annotations that need extraction:
1. **Digital annotations** – Highlights and typed notes added via PDF readers
2. **Handwritten annotations** – Margin notes, drawings, diagrams written on printed/tablet PDFs

```
┌─────────────────────────────────────────────────────────────────┐
│                         PDF INPUT                                │
└─────────────────────────────┬───────────────────────────────────┘
                              │
                              ▼
              ┌───────────────────────────────┐
              │      Annotation Detection      │
              │   (analyze each page/region)   │
              └───────────────┬───────────────┘
                              │
            ┌─────────────────┼─────────────────┐
            ▼                 ▼                 ▼
   ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
   │  Printed Text   │ │    Digital      │ │   Handwritten   │
   │  (PyMuPDF)      │ │   Highlights    │ │   Annotations   │
   │                 │ │  (pdfplumber)   │ │  (Vision LLM)   │
   └────────┬────────┘ └────────┬────────┘ └────────┬────────┘
            │                   │                   │
            │                   │                   ▼
            │                   │          ┌─────────────────┐
            │                   │          │  Mistral/GPT-4  │
            │                   │          │  Vision OCR     │
            │                   │          │  + Handwriting  │
            │                   │          │  Recognition    │
            │                   │          └────────┬────────┘
            │                   │                   │
            └───────────────────┴───────────────────┘
                              │
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

**Handwritten Annotation Handling**:
- Render each PDF page as an image (300+ DPI for clarity)
- Use vision model to detect regions containing handwriting
- Extract and transcribe handwritten text, including:
  - Margin notes and comments
  - Underlines with associated text
  - Arrows/connections between concepts
  - Mathematical notation and diagrams (describe semantically)
- Associate handwritten notes with nearby printed content for context
- Preserve original page images in `assets/` folder for reference

**Output Template**:
```markdown
---
type: paper
title: "{{title}}"
authors: [{{authors}}]
year: {{year}}
venue: "{{venue}}"
doi: "{{doi}}"
tags: [{{auto_generated_tags}}]
has_handwritten_notes: true | false
status: unread | reading | read | reviewed
created: {{date}}
---

## Summary
{{llm_generated_summary}}

## Key Findings
{{extracted_key_points}}

## My Highlights (Digital)
{{digital_highlights_and_annotations}}

## My Handwritten Notes
> [!note] Page {{page_num}}
> {{transcribed_handwritten_note}}
> *Context: "{{surrounding_printed_text}}"*

{{#each handwritten_notes}}
> [!note] Page {{this.page}}
> {{this.transcription}}
> *Context: "{{this.context}}"*
{{/each}}

## Diagrams & Sketches
{{#if has_diagrams}}
![[{{paper_slug}}-diagram-{{n}}.png]]
*Description: {{diagram_description}}*
{{/if}}

## Questions & Follow-ups
- [ ] {{generated_question_1}}
- [ ] {{generated_question_2}}

## Connections
- [[related_note_1]]
- [[related_note_2]]
```

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

---

## 🏷️ Organization Strategy

### Primary Hierarchy: Content Type
Organize raw storage by the *nature* of the source:

```
sources/
├── papers/        # Academic papers, research
├── articles/      # Blog posts, news, essays
├── books/         # Book notes and highlights
├── code/          # Repository analyses
├── ideas/         # Fleeting notes, thoughts
└── work/          # Work-specific content
    ├── meetings/
    ├── proposals/
    └── slack/
```

### Secondary Organization: Semantic Tags
Use a controlled vocabulary of tags for cross-cutting concerns:

```yaml
# Topic Tags (hierarchical)
- ml/transformers
- ml/reinforcement-learning
- systems/distributed
- systems/databases
- leadership/management
- productivity/habits

# Meta Tags
- status/actionable
- status/reference
- status/archive
- quality/foundational
- quality/deep-dive
```

### Tertiary: Bidirectional Links
Leverage Obsidian's `[[wikilinks]]` extensively:
- Every note should link to related concepts
- Use block references for granular connections
- Auto-generate backlink summaries

---

## 🎓 Learning & Deliberate Practice System

> 📖 **Full details**: See **[LEARNING_THEORY.md](./LEARNING_THEORY.md)** for comprehensive research foundations and citations.

### Learning Science Foundation (Summary)

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

### The Learning Loop

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

---

## 🔌 Obsidian Plugin Stack

| Plugin | Purpose |
|--------|---------|
| **Neo4j Graph View** | Export knowledge graph to Neo4j for advanced querying |
| **Dataview** | SQL-like queries over notes for dynamic dashboards |
| **Smart Connections** | AI-powered related note suggestions |
| **Tag Wrangler** | Bulk tag management and refactoring |
| **Linter** | Enforce consistent formatting |
| **Waypoint / Folder Note** | Auto-generate folder index notes |
| **Templater** | Advanced templates for different note types |
| **Tasks** | Track follow-up tasks across all notes |
| **Periodic Notes** | Daily/weekly review automation |

---

## 🛠️ Technical Stack

### Core Technologies

| Component | Technology | Rationale |
|-----------|------------|-----------|
| **Knowledge Hub** | Obsidian | Markdown-based, local-first, extensive plugin ecosystem |
| **Graph Database** | Neo4j | Native graph storage, powerful Cypher queries |
| **LLM Backbone** | [aisuite](https://github.com/andrewyng/aisuite) | Unified interface to OpenAI, Anthropic, Gemini, etc. |
| **Vision / OCR** | GPT-4V / Gemini Vision / Mistral Vision | Handwriting recognition, diagram understanding, book photo OCR |
| **PDF Processing** | PyMuPDF + pdfplumber + pdf2image | Text extraction, highlight detection, page rendering for vision |
| **API Integrations** | Python + httpx | Raindrop, GitHub, various services |
| **Automation** | Python scripts + cron | Scheduled ingestion runs |

### APIs & Services

| Service | Purpose | API Docs |
|---------|---------|----------|
| Raindrop.io | Web bookmark sync | [raindrop.io/dev](https://developer.raindrop.io/) |
| GitHub | Repository analysis | [docs.github.com](https://docs.github.com/en/rest) |
| Mistral | Vision OCR, handwriting recognition | [docs.mistral.ai](https://docs.mistral.ai/) |
| OpenAI | Summarization, exercises, GPT-4V for handwriting | [platform.openai.com](https://platform.openai.com/docs) |
| Google | Gemini Vision for complex diagrams | [ai.google.dev](https://ai.google.dev/docs) |

---

## 🖥️ Web Application: Learning Interface

The existing frontend/backend provides a foundation for the **active learning** and **analytics** components of the system.

### Current Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│    Frontend     │────▶│     Backend     │────▶│      Neo4j      │
│  (React/Vite)   │     │    (FastAPI)    │     │  Knowledge Graph│
└─────────────────┘     └─────────────────┘     └─────────────────┘
                               │
                               ▼
                        ┌─────────────────┐
                        │     OpenAI      │
                        │   Embeddings    │
                        └─────────────────┘
```

### Extended Architecture for Learning System

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

### Frontend Components

#### 1. Practice Session View
The core learning interface, implementing research-backed techniques:

| Component | Learning Principle | Implementation |
|-----------|-------------------|----------------|
| **Free Recall Prompt** | Generation effect (Bjork) | "Explain [concept] without looking at notes" |
| **Self-Explanation Box** | Self-explanation (Chi) | "How does this connect to what you know?" |
| **Worked Example Viewer** | Cognitive load (Van Gog) | Step-by-step solutions for novice topics |
| **Interleaved Question Set** | Interleaving (Dunlosky) | Mix questions from different topics |
| **Confidence Slider** | Metacognition | Rate certainty after each response |

```jsx
// Example: Practice Session Flow
<PracticeSession>
  <QuestionCard 
    type="free-recall" 
    topic="distributed-systems/consensus"
    prompt="Explain the Raft consensus algorithm from memory"
  />
  <ResponseArea 
    onSubmit={checkAndProvideFeeback}
    timer={true}
  />
  <SelfExplainPrompt 
    questions={[
      "How does this relate to Paxos?",
      "When would you choose Raft over other algorithms?"
    ]}
  />
  <ConfidenceRating onRate={updateSpacedRepSchedule} />
  <FeedbackPanel showAfterSubmit={true} />
</PracticeSession>
```

#### 2. Review Queue (Spaced Repetition)
Implements distributed practice with SM-2 or FSRS algorithm:

```jsx
<ReviewQueue>
  <DueItemsList 
    sortBy="urgency" 
    showTopicDistribution={true}
  />
  <ReviewCard>
    <Question />
    <RevealButton />
    <RatingButtons values={["Again", "Hard", "Good", "Easy"]} />
  </ReviewCard>
  <SessionProgress 
    completed={15} 
    remaining={8} 
    streakDays={12}
  />
</ReviewQueue>
```

#### 3. Analytics Dashboard
Track learning progress and identify weak spots:

| Metric | Visualization | Purpose |
|--------|---------------|---------|
| **Learning Curve** | Line chart over time | Track knowledge retention |
| **Topic Mastery Heatmap** | Treemap by topic | Identify strong/weak areas |
| **Retrieval Success Rate** | Bar chart per topic | Measure testing effect |
| **Time Investment** | Stacked area chart | See where time goes |
| **Forgetting Curve** | Decay curves by topic | Predict review timing |
| **Connection Density** | Network metrics | Measure knowledge integration |

```jsx
<AnalyticsDashboard>
  <MasteryHeatmap topics={allTopics} />
  <LearningCurve 
    timeRange="30d" 
    metrics={["accuracy", "confidence", "speed"]}
  />
  <WeakSpotsList 
    criteria="low-confidence-high-importance"
    actionButton="Start Practice"
  />
  <StreakCalendar />
  <TimeInvestmentChart groupBy="topic" />
</AnalyticsDashboard>
```

#### 4. Knowledge Explorer
Visual navigation of the knowledge graph:

```jsx
<KnowledgeExplorer>
  <GraphVisualization 
    engine="d3-force" 
    nodeColor="by-mastery"
    edgeWidth="by-strength"
  />
  <TopicTree expandable={true} showMastery={true} />
  <SearchBar semantic={true} />
  <ConnectionSuggestions 
    prompt="Have you considered how X relates to Y?"
  />
</KnowledgeExplorer>
```

### LLM Client (aisuite)

The backend uses [aisuite](https://github.com/andrewyng/aisuite) for a unified interface to multiple LLM providers:

```python
# backend/app/services/llm_client.py
import aisuite as ai

client = ai.Client()

# Switch providers with a single string change
MODELS = {
    "summarization": "anthropic:claude-3-5-sonnet-20241022",
    "exercise_generation": "openai:gpt-4o",
    "vision_ocr": "google:gemini-2.0-flash",
    "embeddings": "openai:text-embedding-3-small",
}

async def generate_exercise(topic: str, difficulty: str, mastery_level: float):
    """Generate a practice exercise using the configured model."""
    response = client.chat.completions.create(
        model=MODELS["exercise_generation"],
        messages=[
            {"role": "system", "content": EXERCISE_SYSTEM_PROMPT},
            {"role": "user", "content": f"Generate a {difficulty} exercise for: {topic}"}
        ],
        temperature=0.7
    )
    return response.choices[0].message.content

async def summarize_content(text: str, content_type: str):
    """Summarize ingested content."""
    response = client.chat.completions.create(
        model=MODELS["summarization"],
        messages=[
            {"role": "system", "content": SUMMARIZATION_PROMPTS[content_type]},
            {"role": "user", "content": text}
        ]
    )
    return response.choices[0].message.content
```

**Tool Calling for Learning Assistant**:

```python
# Automatic tool execution for the learning assistant agent
def search_knowledge_graph(query: str) -> str:
    """Search the knowledge graph for relevant concepts."""
    # Neo4j query logic here
    return results

def get_related_concepts(concept_id: str) -> list:
    """Get concepts related to the given concept."""
    # Graph traversal logic
    return related

response = client.chat.completions.create(
    model="openai:gpt-4o",
    messages=[{"role": "user", "content": "How does Raft relate to Paxos?"}],
    tools=[search_knowledge_graph, get_related_concepts],
    max_turns=3  # Automatic tool execution
)
```

**MCP Integration** (for Obsidian vault access):

```python
from aisuite.mcp import MCPClient

# Connect to Obsidian vault via MCP filesystem server
obsidian_mcp = MCPClient(
    command="npx",
    args=["-y", "@modelcontextprotocol/server-filesystem", "/path/to/obsidian/vault"]
)

response = client.chat.completions.create(
    model="anthropic:claude-3-5-sonnet-20241022",
    messages=[{"role": "user", "content": "Find all notes about distributed systems"}],
    tools=obsidian_mcp.get_callable_tools(),
    max_turns=3
)
```

### Backend API Extensions

```python
# New endpoints for learning system

# Practice endpoints
@app.post("/api/practice/generate")
async def generate_exercise(topic: str, difficulty: str, type: ExerciseType):
    """Generate exercise using LLM based on topic mastery level"""
    
@app.post("/api/practice/submit")
async def submit_response(exercise_id: str, response: str, time_spent: int):
    """Evaluate response, provide feedback, update mastery"""

@app.post("/api/practice/self-explain")
async def record_self_explanation(exercise_id: str, explanation: str):
    """Store self-explanation, analyze for mental model quality"""

# Spaced repetition endpoints
@app.get("/api/review/due")
async def get_due_items(limit: int = 20):
    """Get items due for review based on FSRS algorithm"""

@app.post("/api/review/update")
async def update_review(item_id: str, rating: int, response_time: int):
    """Update spaced rep schedule based on rating"""

# Analytics endpoints
@app.get("/api/analytics/mastery")
async def get_mastery_by_topic():
    """Calculate mastery scores per topic from practice history"""

@app.get("/api/analytics/weak-spots")
async def get_weak_spots(threshold: float = 0.6):
    """Identify topics with low mastery or declining performance"""

@app.get("/api/analytics/learning-curve")
async def get_learning_curve(topic: str = None, days: int = 30):
    """Return time-series of accuracy/confidence metrics"""
```

### Database Schema Extensions

```sql
-- PostgreSQL schema for learning records

CREATE TABLE practice_sessions (
    id UUID PRIMARY KEY,
    user_id UUID,
    started_at TIMESTAMP,
    ended_at TIMESTAMP,
    topics JSONB,
    exercise_count INT
);

CREATE TABLE practice_attempts (
    id UUID PRIMARY KEY,
    session_id UUID REFERENCES practice_sessions(id),
    concept_id UUID,  -- links to Neo4j node
    exercise_type VARCHAR(50),  -- free-recall, self-explain, worked-example
    prompt TEXT,
    response TEXT,
    is_correct BOOLEAN,
    confidence_before FLOAT,
    confidence_after FLOAT,
    time_spent_seconds INT,
    feedback TEXT,
    created_at TIMESTAMP
);

CREATE TABLE spaced_rep_cards (
    id UUID PRIMARY KEY,
    concept_id UUID,
    front TEXT,
    back TEXT,
    -- FSRS algorithm fields
    difficulty FLOAT DEFAULT 0.3,
    stability FLOAT DEFAULT 1.0,
    due_date DATE,
    last_review TIMESTAMP,
    review_count INT DEFAULT 0,
    lapses INT DEFAULT 0
);

CREATE TABLE mastery_snapshots (
    id UUID PRIMARY KEY,
    concept_id UUID,
    topic_path VARCHAR(255),
    mastery_score FLOAT,
    confidence_avg FLOAT,
    practice_count INT,
    last_practiced TIMESTAMP,
    snapshot_date DATE
);
```

---

## 📁 Repository Structure

```
dpickem_project_second_brain/
├── README.md                    # This file
├── docker-compose.yml           # Container orchestration
│
├── backend/                     # FastAPI backend (existing)
│   ├── app/
│   │   ├── main.py              # API entry point
│   │   ├── routers/             # API route modules (to add)
│   │   │   ├── practice.py      # Practice session endpoints
│   │   │   ├── review.py        # Spaced repetition endpoints
│   │   │   ├── analytics.py     # Learning analytics endpoints
│   │   │   ├── knowledge.py     # Knowledge graph endpoints
│   │   │   └── ingest.py        # Content ingestion endpoints
│   │   ├── services/            # Business logic
│   │   │   ├── exercise_generator.py
│   │   │   ├── spaced_rep.py    # FSRS algorithm
│   │   │   ├── mastery_tracker.py
│   │   │   └── llm_client.py
│   │   ├── models/              # Pydantic models
│   │   └── db/                  # Database connections
│   ├── Dockerfile
│   └── requirements.txt
│
├── frontend/                    # React frontend (existing)
│   ├── src/
│   │   ├── App.jsx
│   │   ├── main.jsx
│   │   ├── components/          # UI components (to add)
│   │   │   ├── PracticeSession/
│   │   │   ├── ReviewQueue/
│   │   │   ├── AnalyticsDashboard/
│   │   │   └── KnowledgeExplorer/
│   │   ├── hooks/               # Custom React hooks
│   │   ├── services/            # API client
│   │   └── stores/              # State management
│   ├── index.html
│   ├── package.json
│   ├── vite.config.js
│   └── Dockerfile
│
├── pipelines/                   # Data ingestion pipelines (to add)
│   ├── raindrop.py
│   ├── pdf_processor.py
│   ├── handwriting_ocr.py
│   ├── book_ocr_pipeline.py
│   └── github_importer.py
│
├── templates/                   # Obsidian note templates
│   ├── paper.md
│   ├── article.md
│   ├── book.md
│   └── code.md
│
├── scripts/                     # Automation scripts
│   ├── daily_sync.py
│   └── weekly_review.py
│
├── config/                      # Configuration files
│   ├── config.yaml
│   └── prompts.yaml
│
└── tests/                       # Test suite
```

---

## 🔬 Open Research Questions

1. **Human vs. Machine Connection-Making**: To what extent should we outsource relationship discovery to AI vs. keeping it as a human cognitive exercise? *(Bjork's research suggests that effortful retrieval and generation by humans is crucial for storage strength—AI may help prompt connections, but the human must generate them.)*

2. ~~**Active Learning Optimization**: What does learning science research say about maximizing retention?~~ ✅ **Addressed** – See [LEARNING_THEORY.md](./LEARNING_THEORY.md). Key answer: Prioritize *desirable difficulties*—spacing, interleaving, generation, and testing over passive re-reading.

3. **Information Overload**: How do we prevent the knowledge base from becoming overwhelming? What pruning and archival strategies work best?

4. **Exercise Quality**: Can current LLMs generate exercises that genuinely challenge and teach, or do they tend toward superficial quizzes? *(Exercises should force generation/retrieval, not recognition. Need to validate LLM outputs against Bjork's criteria.)*

5. **Graph Utility**: Is a formal graph database necessary, or are Obsidian's native links sufficient for most connection discovery?

---

## 📚 References & Inspiration

### Learning Science
> 📖 See **[LEARNING_THEORY.md](./LEARNING_THEORY.md)** for detailed research summaries, findings, and system implications.

Key sources: Ericsson (2008) on Deliberate Practice, Bjork & Bjork (2011) on Desirable Difficulties, Dunlosky et al. (2013) on Effective Learning Techniques, Chi et al. (1994) on Self-Explanation, Van Gog et al. (2011) on Cognitive Load Theory.

### Knowledge Management
- [Building a Second Brain](https://www.buildingasecondbrain.com/) – Tiago Forte
- [How to Take Smart Notes](https://takesmartnotes.com/) – Sönke Ahrens (Zettelkasten method)

### AI-Assisted Learning
- [ChatGPT Study Mode](https://openai.com/index/chatgpt-study-mode/)
- [Gemini Guided Learning](https://blog.google/outreach-initiatives/education/guided-learning/)

### Tools & Plugins
- [Google Code Wiki](https://developers.googleblog.com/introducing-code-wiki-accelerating-your-code-understanding/)
- [Obsidian Neo4j Graph View](https://www.obsidianstats.com/plugins/neo4j-graph-view)

---

## 🚀 Getting Started

```bash
# Clone the repository
git clone https://github.com/dpickem/dpickem_project_second_brain.git
cd dpickem_project_second_brain

# Set up Python environment
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure API keys
cp config/config.example.yaml config/config.yaml
# Edit config.yaml with your API keys

# Run initial sync
python scripts/daily_sync.py
```

---

## 📋 Implementation Roadmap

### Phase 1: Foundation (Weeks 1-2)
**Knowledge Hub Setup**
- [ ] Set up Obsidian vault with folder structure
- [ ] Configure essential plugins (Dataview, Templater, Tasks)
- [ ] Create note templates for each content type
- [ ] Establish tagging taxonomy

**Infrastructure** ✅ (Partially Complete)
- [x] Docker Compose configuration
- [x] FastAPI backend skeleton
- [x] React/Vite frontend skeleton
- [x] Neo4j integration
- [ ] Add PostgreSQL for learning records
- [ ] Add Redis for session caching
- [ ] Set up database migrations (Alembic)

### Phase 2: Ingestion Pipelines (Weeks 3-6)
**Backend API**
- [ ] `/api/ingest/pdf` — PDF processing with highlight extraction
- [ ] `/api/ingest/raindrop` — Raindrop.io sync endpoint
- [ ] `/api/ingest/ocr` — Book photo OCR pipeline
- [ ] `/api/ingest/github` — GitHub starred repos importer
- [ ] Handwriting recognition integration (Vision LLM)

**Pipeline Scripts**
- [ ] Build Raindrop → Obsidian sync script
- [ ] Implement PDF ingestion with highlight extraction
- [ ] Create OCR pipeline for book photos
- [ ] GitHub starred repos importer

### Phase 3: LLM Processing (Weeks 7-10)
**Backend Services**
- [ ] `llm_client.py` — Unified LLM interface via [aisuite](https://github.com/andrewyng/aisuite)
- [ ] Summarization prompts and chains
- [ ] Tag suggestion system
- [ ] Connection discovery via embeddings
- [ ] Mastery question generation (2-3 per section)

**Knowledge Graph**
- [ ] Define node/edge schema (Concepts, Sources, Topics)
- [ ] Build query interfaces
- [ ] Semantic similarity search

### Phase 4: Frontend — Knowledge Explorer (Weeks 11-13)
**Components**
- [ ] `<KnowledgeExplorer />` — Main navigation view
- [ ] `<GraphVisualization />` — D3-force graph rendering
- [ ] `<TopicTree />` — Hierarchical topic browser
- [ ] `<SearchBar />` — Semantic search interface
- [ ] `<NoteViewer />` — Markdown note display

**Backend API**
- [ ] `/api/knowledge/graph` — Full graph data
- [ ] `/api/knowledge/search` — Semantic search
- [ ] `/api/knowledge/connections` — Related concepts
- [ ] `/api/knowledge/topics` — Topic hierarchy

### Phase 5: Frontend — Practice Session (Weeks 14-17)
**Components (Research-Backed)**
- [ ] `<PracticeSession />` — Main practice container
- [ ] `<FreeRecallPrompt />` — Generation effect (Bjork)
- [ ] `<SelfExplainBox />` — Self-explanation prompts (Chi)
- [ ] `<WorkedExampleViewer />` — For novice topics (Van Gog)
- [ ] `<InterleavedQuestionSet />` — Mixed topic practice (Dunlosky)
- [ ] `<ConfidenceSlider />` — Metacognition rating
- [ ] `<FeedbackPanel />` — LLM-generated feedback

**Backend API**
- [ ] `/api/practice/generate` — Exercise generation with difficulty adaptation
- [ ] `/api/practice/submit` — Response evaluation
- [ ] `/api/practice/feedback` — LLM feedback generation
- [ ] `/api/practice/self-explain` — Store and analyze explanations

**Backend Services**
- [ ] `exercise_generator.py` — LLM-based exercise creation
- [ ] `mastery_tracker.py` — Track expertise per topic
- [ ] Adaptive difficulty based on mastery level

### Phase 6: Frontend — Spaced Repetition (Weeks 18-20)
**Components**
- [ ] `<ReviewQueue />` — Due items list
- [ ] `<ReviewCard />` — Flashcard interface
- [ ] `<RatingButtons />` — Again/Hard/Good/Easy
- [ ] `<SessionProgress />` — Cards completed, streak display

**Backend API & Services**
- [ ] `/api/review/due` — Get due items (FSRS algorithm)
- [ ] `/api/review/update` — Update card after review
- [ ] `spaced_rep.py` — FSRS scheduling algorithm
- [ ] Card generation from ingested content

### Phase 7: Frontend — Analytics Dashboard (Weeks 21-23)
**Components**
- [ ] `<AnalyticsDashboard />` — Main analytics view
- [ ] `<MasteryHeatmap />` — Topic mastery treemap
- [ ] `<LearningCurve />` — Time-series accuracy chart
- [ ] `<WeakSpotsList />` — Low mastery topics with action buttons
- [ ] `<StreakCalendar />` — GitHub-style contribution calendar
- [ ] `<TimeInvestmentChart />` — Where time is spent

**Backend API**
- [ ] `/api/analytics/mastery` — Mastery scores per topic
- [ ] `/api/analytics/weak-spots` — Identify struggling areas
- [ ] `/api/analytics/learning-curve` — Historical performance
- [ ] `/api/analytics/time-spent` — Time tracking by activity

**Database**
- [ ] `practice_attempts` table — Full attempt history
- [ ] `mastery_snapshots` table — Daily mastery snapshots
- [ ] Analytics queries and aggregations

### Phase 8: Learning Assistant Chat (Weeks 24-26)
**Components**
- [ ] `<AssistantChat />` — Chat interface
- [ ] `<ConnectionSuggestions />` — "Have you considered X relates to Y?"
- [ ] `<StudyPlanGenerator />` — Personalized study recommendations

**Backend API & Services**
- [ ] `/api/assistant/chat` — Conversational interface
- [ ] `/api/assistant/suggest-connections` — Graph-based suggestions
- [ ] `/api/assistant/study-plan` — Generate personalized plans
- [ ] RAG pipeline over knowledge graph

### Phase 9: Polish & Production (Ongoing)
**Automation**
- [ ] Scheduled pipeline runs (cron/Celery)
- [ ] Daily sync scripts
- [ ] Weekly review reminders

**Quality**
- [ ] Error handling and monitoring (Sentry)
- [ ] Performance optimization
- [ ] Test coverage (pytest, React Testing Library)
- [ ] CI/CD pipeline

**Mobile & UX**
- [ ] Responsive design for all components
- [ ] Mobile capture workflow (see details below)
- [ ] PWA (Progressive Web App) support for offline access
- [ ] Keyboard shortcuts for power users

---

## 📱 Mobile Capture Workflow

A critical bottleneck in any knowledge management system is **capture friction**—the effort required to get information from the real world into the system. The mobile capture workflow minimizes this friction for on-the-go knowledge capture.

### Use Cases

| Scenario | Capture Method | Processing |
|----------|----------------|------------|
| **Physical book highlight** | Photo of page | Vision OCR → extract text → identify highlights → ingest |
| **Fleeting idea** | Voice memo or quick text | Transcription → LLM expansion → save to inbox |
| **Interesting article** | Share sheet / URL paste | Fetch content → summarize → save with tags |
| **Whiteboard / diagram** | Photo | Vision LLM → describe diagram → save with image |
| **Conference talk notes** | Voice recording | Transcribe → structure → extract key points |

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     MOBILE DEVICE                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│   │   📷 Camera   │  │   🎤 Voice   │  │   📎 Share   │          │
│   │  (book pages, │  │   (ideas,    │  │   (URLs,     │          │
│   │  whiteboards) │  │   memos)     │  │   articles)  │          │
│   └──────┬───────┘  └──────┬───────┘  └──────┬───────┘          │
│          │                 │                 │                   │
│          └─────────────────┼─────────────────┘                   │
│                            │                                     │
│                   ┌────────▼────────┐                            │
│                   │   PWA / Mobile   │                            │
│                   │   Quick Capture  │                            │
│                   │      UI          │                            │
│                   └────────┬────────┘                            │
│                            │                                     │
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
│                                                                  │
│                   ┌────────────────────┐                         │
│                   │   Inbox Processing  │                         │
│                   │  (async, batched)   │                         │
│                   └─────────┬──────────┘                         │
│                             │                                    │
│              ┌──────────────┼──────────────┐                     │
│              ▼              ▼              ▼                     │
│         Neo4j          Obsidian        PostgreSQL                │
│      (concepts)         (notes)       (metadata)                 │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Mobile UI Components

```jsx
// Quick capture modal - minimal friction, maximum speed
<QuickCapture>
  {/* Large touch targets for quick access */}
  <CaptureButton icon="📷" label="Photo" onPress={openCamera} />
  <CaptureButton icon="🎤" label="Voice" onPress={startRecording} />
  <CaptureButton icon="✏️" label="Note" onPress={openTextInput} />
  <CaptureButton icon="🔗" label="URL" onPress={pasteUrl} />
  
  {/* Recent captures for quick review */}
  <RecentCaptures limit={5} />
  
  {/* Offline indicator */}
  {isOffline && <OfflineBanner pendingCount={pendingUploads} />}
</QuickCapture>
```

### Backend Endpoints

```python
@app.post("/api/capture/photo")
async def capture_photo(
    file: UploadFile,
    capture_type: str = "book_page"  # book_page | whiteboard | diagram | handwritten
):
    """
    Process uploaded photo through vision pipeline.
    - Book pages: OCR + highlight detection
    - Whiteboards: OCR + structure extraction
    - Diagrams: Semantic description
    - Handwritten: Handwriting recognition
    """
    image_bytes = await file.read()
    
    if capture_type == "book_page":
        result = await vision_ocr_pipeline(image_bytes, detect_highlights=True)
    elif capture_type == "whiteboard":
        result = await vision_ocr_pipeline(image_bytes, extract_structure=True)
    else:
        result = await vision_describe(image_bytes)
    
    # Save to inbox for review
    await save_to_inbox(result, source="mobile_capture")
    return {"status": "queued", "preview": result.summary}


@app.post("/api/capture/voice")
async def capture_voice(file: UploadFile):
    """
    Transcribe voice memo and optionally expand with LLM.
    """
    audio_bytes = await file.read()
    
    # Whisper transcription
    transcript = await transcribe_audio(audio_bytes)
    
    # LLM expansion (turn fragments into coherent notes)
    expanded = await expand_fleeting_note(transcript)
    
    await save_to_inbox(expanded, source="voice_memo")
    return {"transcript": transcript, "expanded": expanded}


@app.post("/api/capture/url")
async def capture_url(url: str, highlights: list[str] = None):
    """
    Fetch URL content, extract main text, summarize.
    """
    content = await fetch_and_extract(url)
    summary = await summarize_content(content.text, content_type="article")
    
    await save_to_inbox({
        "url": url,
        "title": content.title,
        "summary": summary,
        "highlights": highlights,
        "full_text": content.text
    }, source="url_capture")
    
    return {"title": content.title, "summary": summary}
```

### Offline Support via PWA (Progressive Web App)

A **Progressive Web App (PWA)** is a web application that can be installed on a device and behaves like a native app. Key benefits for the Second Brain:

| PWA Feature | Benefit |
|-------------|---------|
| **Installable** | "Add to Home Screen" — launches like a native app |
| **Offline capable** | Service workers cache assets and queue API calls |
| **Background sync** | Uploads queued captures when connection restored |
| **Push notifications** | Remind user of spaced repetition reviews |
| **No app store** | Direct install from browser, instant updates |

This means the mobile capture interface works even without internet—captures are queued locally and synced when back online.

```javascript
// Service worker for offline queuing
self.addEventListener('fetch', (event) => {
  if (event.request.url.includes('/api/capture/')) {
    event.respondWith(
      fetch(event.request).catch(() => {
        // Queue for later sync when offline
        return saveToOfflineQueue(event.request);
      })
    );
  }
});

// Background sync when connection restored
self.addEventListener('sync', (event) => {
  if (event.tag === 'capture-sync') {
    event.waitUntil(uploadQueuedCaptures());
  }
});
```

### Integration with Existing Tools

| Tool | Integration Method |
|------|-------------------|
| **iOS Share Sheet** | PWA "Add to Home Screen" + Web Share Target API |
| **Android Share** | PWA manifest with share_target |
| **Raindrop.io** | Use mobile app → sync via API (already planned) |
| **Apple Notes** | Export + batch import |
| **Voice Memos** | Direct upload or watch folder sync |

### Key Design Principles

1. **< 3 seconds to capture** — Any longer and ideas are lost
2. **Offline-first** — Queue uploads, sync when connected
3. **Minimal categorization at capture** — Let LLM tag later
4. **Visual feedback** — Confirm capture succeeded immediately
5. **Inbox review** — All captures go to inbox for daily processing

---

*This is a living document. As the system evolves, so will this design.*

