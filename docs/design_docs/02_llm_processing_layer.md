# LLM Processing Layer Design

> **Document Status**: Design Specification  
> **Last Updated**: December 2025  
> **Related Docs**: `01_ingestion_layer.md`, `05_learning_system.md`

---

## 1. Overview

The LLM Processing Layer transforms raw ingested content into structured, connected knowledge. It leverages multiple LLM providers via a unified interface to perform summarization, extraction, classification, and connection discovery.

### Design Goals

1. **Provider Agnostic**: Switch LLM providers without code changes
2. **Quality Over Speed**: Prioritize accurate processing over throughput
3. **Modular Pipeline**: Each processing step is independent and retryable
4. **Cost Efficient**: Use appropriate model sizes for each task
5. **Explainable Outputs**: All LLM decisions include reasoning

---

## 2. Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        UNIFIED CONTENT (from Ingestion)                      │
└─────────────────────────────────────┬───────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         LLM PROCESSING PIPELINE                              │
│                                                                              │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐   │
│  │ 1. Content  │───▶│ 2. Summary  │───▶│ 3. Concept  │───▶│ 4. Tagging  │   │
│  │   Analysis  │    │  Generation │    │  Extraction │    │   & Topics  │   │
│  └─────────────┘    └─────────────┘    └─────────────┘    └──────┬──────┘   │
│                                                                   │          │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐           │          │
│  │ 7. Mastery  │◀───│ 6. Follow-up│◀───│ 5. Connect- │◀──────────┘          │
│  │  Questions  │    │    Tasks    │    │     ions    │                       │
│  └─────────────┘    └─────────────┘    └─────────────┘                       │
│                                                                              │
└─────────────────────────────────────┬───────────────────────────────────────┘
                                      │
                    ┌─────────────────┼─────────────────┐
                    ▼                 ▼                 ▼
            ┌─────────────┐   ┌─────────────┐   ┌─────────────┐
            │  Obsidian   │   │   Neo4j     │   │ PostgreSQL  │
            │   Note      │   │   Nodes     │   │  Records    │
            └─────────────┘   └─────────────┘   └─────────────┘
```

---

## 3. LLM Client Configuration

### 3.1 Unified Client (aisuite)

```python
# backend/app/services/llm_client.py

import aisuite as ai
from typing import Optional
import os

class LLMClient:
    """Unified LLM client supporting multiple providers."""
    
    # Model mapping by task
    MODELS = {
        "summarization": "anthropic:claude-3-5-sonnet-20241022",
        "extraction": "openai:gpt-4o",
        "classification": "openai:gpt-4o-mini",  # Cost-efficient for simple tasks
        "connection_discovery": "anthropic:claude-3-5-sonnet-20241022",
        "question_generation": "openai:gpt-4o",
        "vision_ocr": "google:gemini-2.0-flash",
        "embeddings": "openai:text-embedding-3-small",
    }
    
    # Fallback models
    FALLBACKS = {
        "anthropic:claude-3-5-sonnet-20241022": "openai:gpt-4o",
        "openai:gpt-4o": "anthropic:claude-3-5-sonnet-20241022",
        "google:gemini-2.0-flash": "openai:gpt-4o",
    }
    
    def __init__(self):
        self.client = ai.Client()
        
        # Verify API keys are set
        required_keys = ["OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GOOGLE_API_KEY"]
        missing = [k for k in required_keys if not os.getenv(k)]
        if missing:
            raise ValueError(f"Missing API keys: {missing}")
    
    async def complete(
        self,
        task: str,
        messages: list[dict],
        temperature: float = 0.3,
        max_tokens: int = 4096,
        response_format: Optional[dict] = None,
        retry_with_fallback: bool = True
    ) -> str:
        """Generate a completion using the appropriate model for the task."""
        
        model = self.MODELS.get(task, "openai:gpt-4o")
        
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                response_format=response_format
            )
            return response.choices[0].message.content
            
        except Exception as e:
            if retry_with_fallback and model in self.FALLBACKS:
                fallback = self.FALLBACKS[model]
                response = self.client.chat.completions.create(
                    model=fallback,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens
                )
                return response.choices[0].message.content
            raise
    
    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for a list of texts."""
        from openai import OpenAI
        
        client = OpenAI()
        response = client.embeddings.create(
            model="text-embedding-3-small",
            input=texts
        )
        return [item.embedding for item in response.data]

# Singleton instance
_client: Optional[LLMClient] = None

def get_llm_client() -> LLMClient:
    global _client
    if _client is None:
        _client = LLMClient()
    return _client
```

### 3.2 Provider Comparison

| Provider | Best For | Strengths | Considerations |
|----------|----------|-----------|----------------|
| **Anthropic Claude** | Complex reasoning, summarization | Nuanced understanding, long context | Higher latency |
| **OpenAI GPT-4o** | Balanced tasks, extraction | Fast, reliable, structured outputs | Cost for high volume |
| **OpenAI GPT-4o-mini** | Classification, simple tasks | Cost-efficient | Less nuanced |
| **Google Gemini** | Vision tasks, OCR | Excellent multimodal | Rate limits |

---

## 4. Processing Pipeline Stages

### 4.1 Content Analysis

First pass analysis to understand content type and structure.

```python
# backend/app/services/processing/content_analysis.py

from pydantic import BaseModel

class ContentAnalysis(BaseModel):
    content_type: str           # paper, article, book, code, idea
    domain: str                 # ml, systems, leadership, etc.
    complexity: str             # foundational, intermediate, advanced
    estimated_length: str       # short, medium, long
    has_code: bool
    has_math: bool
    has_diagrams: bool
    key_topics: list[str]
    language: str

ANALYSIS_PROMPT = """Analyze this content and provide structured metadata.

Content:
{content}

Provide analysis in JSON format:
{{
  "content_type": "paper|article|book|code|idea",
  "domain": "primary domain (e.g., ml, systems, leadership, productivity)",
  "complexity": "foundational|intermediate|advanced",
  "estimated_length": "short|medium|long",
  "has_code": true|false,
  "has_math": true|false,
  "has_diagrams": true|false,
  "key_topics": ["topic1", "topic2", ...],
  "language": "en|de|fr|..."
}}
"""

async def analyze_content(content: UnifiedContent, llm_client: LLMClient) -> ContentAnalysis:
    """Perform initial content analysis."""
    
    # Use first ~8000 chars for analysis
    text_sample = content.full_text[:8000]
    
    response = await llm_client.complete(
        task="classification",
        messages=[{
            "role": "user",
            "content": ANALYSIS_PROMPT.format(content=text_sample)
        }],
        response_format={"type": "json_object"}
    )
    
    return ContentAnalysis.model_validate_json(response)
```

### 4.2 Summary Generation

Generate multi-level summaries based on content type.

```python
# backend/app/services/processing/summarization.py

from enum import Enum

class SummaryLevel(str, Enum):
    BRIEF = "brief"      # 1-2 sentences
    STANDARD = "standard"  # 1-2 paragraphs
    DETAILED = "detailed"  # Full summary with sections

SUMMARY_PROMPTS = {
    "paper": """Summarize this academic paper at {level} level.

Paper content:
{content}

For {level} summary, include:
- BRIEF: Core contribution in 1-2 sentences
- STANDARD: Problem, approach, key findings, implications
- DETAILED: Full structured summary with methodology, results, limitations

Annotations/highlights from the reader:
{annotations}

Use the annotations to understand what the reader found important.
""",
    
    "article": """Summarize this article at {level} level.

Article:
{content}

Highlights:
{annotations}

Focus on practical takeaways and actionable insights.
""",
    
    "book": """Summarize these book highlights/notes at {level} level.

Content:
{content}

The reader highlighted these passages as important - use them to inform the summary.
""",
    
    "code": """Summarize this code repository analysis at {level} level.

Analysis:
{content}

Focus on:
- What the code does
- Key architectural decisions
- Notable patterns or techniques
- Potential learnings
"""
}

async def generate_summary(
    content: UnifiedContent,
    analysis: ContentAnalysis,
    level: SummaryLevel,
    llm_client: LLMClient
) -> str:
    """Generate a summary at the specified level."""
    
    prompt_template = SUMMARY_PROMPTS.get(
        analysis.content_type, 
        SUMMARY_PROMPTS["article"]
    )
    
    # Format annotations
    annotations_text = "\n".join([
        f"- [{a.type}] {a.content}" 
        for a in content.annotations[:20]  # Limit to prevent token overflow
    ])
    
    prompt = prompt_template.format(
        content=content.full_text[:30000],  # Limit content length
        level=level.value,
        annotations=annotations_text or "None provided"
    )
    
    return await llm_client.complete(
        task="summarization",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3
    )
```

### 4.3 Concept Extraction

Extract key concepts, definitions, and terminology.

```python
# backend/app/services/processing/extraction.py

from pydantic import BaseModel

class Concept(BaseModel):
    name: str
    definition: str
    context: str  # How it's used in this content
    importance: str  # core, supporting, tangential
    related_concepts: list[str]

class ExtractionResult(BaseModel):
    concepts: list[Concept]
    key_findings: list[str]
    methodologies: list[str]
    tools_mentioned: list[str]
    people_mentioned: list[str]

EXTRACTION_PROMPT = """Extract structured information from this content.

Content:
{content}

Extract:
1. **Concepts**: Key ideas, terms, frameworks mentioned
   - Name, definition, importance level (core/supporting/tangential)
   - Related concepts within this content

2. **Key Findings**: Main insights, conclusions, or claims

3. **Methodologies**: Approaches, techniques, or processes described

4. **Tools**: Software, frameworks, or technologies mentioned

5. **People**: Authors, researchers, or practitioners referenced

Return as JSON:
{{
  "concepts": [
    {{
      "name": "concept name",
      "definition": "brief definition",
      "context": "how it's used here",
      "importance": "core|supporting|tangential",
      "related_concepts": ["related1", "related2"]
    }}
  ],
  "key_findings": ["finding1", "finding2"],
  "methodologies": ["method1", "method2"],
  "tools_mentioned": ["tool1", "tool2"],
  "people_mentioned": ["person1", "person2"]
}}
"""

async def extract_concepts(
    content: UnifiedContent,
    llm_client: LLMClient
) -> ExtractionResult:
    """Extract structured concepts and information."""
    
    response = await llm_client.complete(
        task="extraction",
        messages=[{
            "role": "user",
            "content": EXTRACTION_PROMPT.format(content=content.full_text[:20000])
        }],
        response_format={"type": "json_object"}
    )
    
    return ExtractionResult.model_validate_json(response)
```

### 4.4 Tagging & Classification

Assign hierarchical tags and topics.

```python
# backend/app/services/processing/tagging.py

# Controlled vocabulary for consistent tagging
TAG_TAXONOMY = {
    "domains": [
        "ml/deep-learning", "ml/nlp", "ml/computer-vision", "ml/reinforcement-learning",
        "systems/distributed", "systems/databases", "systems/performance",
        "engineering/architecture", "engineering/testing", "engineering/devops",
        "leadership/management", "leadership/communication", "leadership/strategy",
        "productivity/habits", "productivity/tools", "productivity/learning"
    ],
    "meta": [
        "status/actionable", "status/reference", "status/archive",
        "quality/foundational", "quality/deep-dive", "quality/overview"
    ]
}

TAGGING_PROMPT = """Assign tags to this content from the provided taxonomy.

Content Analysis:
- Type: {content_type}
- Domain: {domain}
- Complexity: {complexity}
- Key Topics: {key_topics}

Summary:
{summary}

Available Tags (select from these):
Domains: {domain_tags}
Meta: {meta_tags}

Rules:
1. Assign 1-3 domain tags (most specific that applies)
2. Assign 1-2 meta tags
3. Only use tags from the provided taxonomy
4. If no exact match, use closest parent category

Return as JSON:
{{
  "domain_tags": ["tag1", "tag2"],
  "meta_tags": ["tag1"],
  "suggested_new_tags": ["tag that should exist but doesn't"],
  "reasoning": "brief explanation of tag choices"
}}
"""

async def assign_tags(
    content: UnifiedContent,
    analysis: ContentAnalysis,
    summary: str,
    llm_client: LLMClient
) -> dict:
    """Assign tags from controlled vocabulary."""
    
    prompt = TAGGING_PROMPT.format(
        content_type=analysis.content_type,
        domain=analysis.domain,
        complexity=analysis.complexity,
        key_topics=", ".join(analysis.key_topics),
        summary=summary[:2000],
        domain_tags=", ".join(TAG_TAXONOMY["domains"]),
        meta_tags=", ".join(TAG_TAXONOMY["meta"])
    )
    
    response = await llm_client.complete(
        task="classification",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"}
    )
    
    return json.loads(response)
```

### 4.5 Connection Discovery

Find relationships to existing knowledge.

```python
# backend/app/services/processing/connections.py

from typing import Optional

class Connection(BaseModel):
    target_id: str
    target_title: str
    relationship_type: str  # RELATES_TO, EXTENDS, CONTRADICTS, PREREQUISITE_FOR
    strength: float  # 0.0 - 1.0
    explanation: str

async def discover_connections(
    content: UnifiedContent,
    concepts: ExtractionResult,
    llm_client: LLMClient,
    neo4j_client,
    top_k: int = 10
) -> list[Connection]:
    """Discover connections to existing knowledge."""
    
    # Step 1: Generate embedding for new content
    embedding = (await llm_client.embed([content.full_text[:8000]]))[0]
    
    # Step 2: Find similar content via embedding search
    similar_nodes = await neo4j_client.vector_search(
        embedding=embedding,
        top_k=top_k * 2  # Get more candidates for filtering
    )
    
    if not similar_nodes:
        return []
    
    # Step 3: Use LLM to evaluate and explain connections
    connections = await _evaluate_connections(
        content=content,
        candidates=similar_nodes,
        llm_client=llm_client
    )
    
    return connections[:top_k]

CONNECTION_EVALUATION_PROMPT = """Evaluate the relationship between a new piece of content and potential connections.

New Content:
Title: {new_title}
Summary: {new_summary}
Key Concepts: {new_concepts}

Potential Connection:
Title: {candidate_title}
Summary: {candidate_summary}

Evaluate:
1. Is there a meaningful connection? (yes/no)
2. If yes, what type?
   - RELATES_TO: General topical relationship
   - EXTENDS: New content builds on existing
   - CONTRADICTS: New content challenges existing
   - PREREQUISITE_FOR: Existing is foundational for new
3. How strong is the connection? (0.0-1.0)
4. Explain the connection in 1-2 sentences

Return JSON:
{{
  "has_connection": true|false,
  "relationship_type": "RELATES_TO|EXTENDS|CONTRADICTS|PREREQUISITE_FOR",
  "strength": 0.0-1.0,
  "explanation": "explanation of the connection"
}}
"""

async def _evaluate_connections(
    content: UnifiedContent,
    candidates: list[dict],
    llm_client: LLMClient
) -> list[Connection]:
    """Use LLM to evaluate potential connections."""
    
    connections = []
    
    for candidate in candidates:
        prompt = CONNECTION_EVALUATION_PROMPT.format(
            new_title=content.title,
            new_summary=content.full_text[:1500],
            new_concepts="...",
            candidate_title=candidate["title"],
            candidate_summary=candidate.get("summary", "")[:1000]
        )
        
        response = await llm_client.complete(
            task="connection_discovery",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        
        result = json.loads(response)
        
        if result.get("has_connection") and result.get("strength", 0) > 0.3:
            connections.append(Connection(
                target_id=candidate["id"],
                target_title=candidate["title"],
                relationship_type=result["relationship_type"],
                strength=result["strength"],
                explanation=result["explanation"]
            ))
    
    # Sort by strength
    connections.sort(key=lambda c: c.strength, reverse=True)
    
    return connections
```

### 4.6 Follow-up Task Generation

Generate actionable tasks for deeper engagement.

```python
# backend/app/services/processing/followups.py

FOLLOWUP_PROMPT = """Based on this content, generate follow-up tasks that would help deepen understanding.

Content:
Title: {title}
Type: {content_type}
Summary: {summary}
Key Concepts: {concepts}

Reader's Highlights/Annotations:
{annotations}

Generate 3-5 follow-up tasks that are:
1. Actionable (can be completed in a single session)
2. Deepening (go beyond surface understanding)
3. Connected (relate to other knowledge areas)

Task types to consider:
- Research: "Look up X to understand Y better"
- Practice: "Try implementing X"
- Connect: "Explore how this relates to Z"
- Apply: "Use this technique on project W"
- Review: "Revisit X after applying this"

Return as JSON:
{{
  "tasks": [
    {{
      "task": "task description",
      "type": "research|practice|connect|apply|review",
      "priority": "high|medium|low",
      "estimated_time": "15min|30min|1hr|2hr+"
    }}
  ]
}}
"""

async def generate_followups(
    content: UnifiedContent,
    analysis: ContentAnalysis,
    summary: str,
    concepts: ExtractionResult,
    llm_client: LLMClient
) -> list[dict]:
    """Generate follow-up tasks."""
    
    annotations_text = "\n".join([
        f"- {a.content[:200]}" 
        for a in content.annotations[:10]
    ])
    
    prompt = FOLLOWUP_PROMPT.format(
        title=content.title,
        content_type=analysis.content_type,
        summary=summary[:2000],
        concepts=", ".join([c.name for c in concepts.concepts[:10]]),
        annotations=annotations_text or "None"
    )
    
    response = await llm_client.complete(
        task="question_generation",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"}
    )
    
    result = json.loads(response)
    return result.get("tasks", [])
```

### 4.7 Mastery Question Generation

Generate questions that, if answered, prove mastery.

```python
# backend/app/services/processing/questions.py

MASTERY_QUESTIONS_PROMPT = """Generate mastery questions for this content.

A mastery question is one where:
- If you can answer it from memory, you truly understand the material
- It tests understanding, not just recall of facts
- Answering requires integrating multiple concepts

Content:
Title: {title}
Summary: {summary}
Key Concepts: {concepts}
Complexity: {complexity}

Generate 3-5 mastery questions at appropriate difficulty level.

For {complexity} content:
- Foundational: Focus on "what" and "how" questions
- Intermediate: Focus on "why" and "when to use" questions  
- Advanced: Focus on "tradeoffs" and "edge cases" questions

Return as JSON:
{{
  "questions": [
    {{
      "question": "the question text",
      "type": "conceptual|application|analysis|synthesis",
      "difficulty": "foundational|intermediate|advanced",
      "hints": ["hint1", "hint2"],
      "key_points": ["point that should be in a good answer"]
    }}
  ]
}}
"""

async def generate_mastery_questions(
    content: UnifiedContent,
    analysis: ContentAnalysis,
    summary: str,
    concepts: ExtractionResult,
    llm_client: LLMClient
) -> list[dict]:
    """Generate questions that test true understanding."""
    
    prompt = MASTERY_QUESTIONS_PROMPT.format(
        title=content.title,
        summary=summary[:3000],
        concepts="\n".join([
            f"- {c.name}: {c.definition}"
            for c in concepts.concepts[:10]
        ]),
        complexity=analysis.complexity
    )
    
    response = await llm_client.complete(
        task="question_generation",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"}
    )
    
    result = json.loads(response)
    return result.get("questions", [])
```

---

## 5. Pipeline Orchestration

### 5.1 Main Processing Function

```python
# backend/app/services/processing/pipeline.py

from dataclasses import dataclass

@dataclass
class ProcessingResult:
    content_id: str
    analysis: ContentAnalysis
    summaries: dict[SummaryLevel, str]
    concepts: ExtractionResult
    tags: dict
    connections: list[Connection]
    followups: list[dict]
    mastery_questions: list[dict]
    obsidian_note: str
    neo4j_nodes: list[dict]

async def process_content(content: UnifiedContent) -> ProcessingResult:
    """Run full processing pipeline on ingested content."""
    
    llm_client = get_llm_client()
    neo4j_client = get_neo4j_client()
    
    # Stage 1: Content Analysis
    analysis = await analyze_content(content, llm_client)
    
    # Stage 2: Generate Summaries (parallel)
    summaries = {}
    for level in SummaryLevel:
        summaries[level] = await generate_summary(
            content, analysis, level, llm_client
        )
    
    # Stage 3: Extract Concepts
    concepts = await extract_concepts(content, llm_client)
    
    # Stage 4: Assign Tags
    tags = await assign_tags(content, analysis, summaries[SummaryLevel.STANDARD], llm_client)
    
    # Stage 5: Discover Connections
    connections = await discover_connections(
        content, concepts, llm_client, neo4j_client
    )
    
    # Stage 6: Generate Follow-ups
    followups = await generate_followups(
        content, analysis, summaries[SummaryLevel.STANDARD], concepts, llm_client
    )
    
    # Stage 7: Generate Mastery Questions
    questions = await generate_mastery_questions(
        content, analysis, summaries[SummaryLevel.DETAILED], concepts, llm_client
    )
    
    # Generate outputs
    obsidian_note = generate_obsidian_note(
        content, analysis, summaries, concepts, tags, connections, followups, questions
    )
    
    neo4j_nodes = generate_neo4j_nodes(
        content, analysis, concepts, tags, connections
    )
    
    return ProcessingResult(
        content_id=content.id,
        analysis=analysis,
        summaries=summaries,
        concepts=concepts,
        tags=tags,
        connections=connections,
        followups=followups,
        mastery_questions=questions,
        obsidian_note=obsidian_note,
        neo4j_nodes=neo4j_nodes
    )
```

### 5.2 Obsidian Note Generation

```python
# backend/app/services/processing/note_generator.py

TEMPLATES = {
    "paper": """---
type: paper
title: "{title}"
authors: [{authors}]
year: {year}
tags: [{tags}]
status: read
created: {created}
processed: {processed}
---

## Summary
{summary_standard}

## Key Findings
{key_findings}

## Core Concepts
{concepts}

## My Highlights
{highlights}

{handwritten_section}

## Mastery Questions
{questions}

## Follow-up Tasks
{followups}

## Connections
{connections}

---
### Detailed Summary
{summary_detailed}
""",

    "article": """---
type: article
title: "{title}"
source: "{source_url}"
author: "{author}"
tags: [{tags}]
created: {created}
processed: {processed}
---

## Summary
{summary_standard}

## Key Takeaways
{key_findings}

## Highlights
{highlights}

## Questions
{questions}

## Follow-ups
{followups}

## Related
{connections}
"""
}

def generate_obsidian_note(
    content: UnifiedContent,
    analysis: ContentAnalysis,
    summaries: dict,
    concepts: ExtractionResult,
    tags: dict,
    connections: list[Connection],
    followups: list[dict],
    questions: list[dict]
) -> str:
    """Generate a formatted Obsidian note."""
    
    template = TEMPLATES.get(analysis.content_type, TEMPLATES["article"])
    
    # Format sections
    all_tags = tags.get("domain_tags", []) + tags.get("meta_tags", [])
    
    highlights_text = "\n".join([
        f"> {a.content}\n> — Page {a.page_number}" if a.page_number else f"> {a.content}"
        for a in content.annotations
        if a.type == AnnotationType.DIGITAL_HIGHLIGHT
    ])
    
    handwritten_section = ""
    handwritten_notes = [a for a in content.annotations if a.type == AnnotationType.HANDWRITTEN_NOTE]
    if handwritten_notes:
        handwritten_section = "## My Handwritten Notes\n"
        for note in handwritten_notes:
            handwritten_section += f"> [!note] Page {note.page_number}\n"
            handwritten_section += f"> {note.content}\n"
            if note.context:
                handwritten_section += f"> *Context: \"{note.context}\"*\n"
            handwritten_section += "\n"
    
    concepts_text = "\n".join([
        f"- **{c.name}**: {c.definition}"
        for c in concepts.concepts
        if c.importance == "core"
    ])
    
    questions_text = "\n".join([
        f"- [ ] {q['question']}"
        for q in questions
    ])
    
    followups_text = "\n".join([
        f"- [ ] {f['task']} `{f['type']}` `{f['estimated_time']}`"
        for f in followups
    ])
    
    connections_text = "\n".join([
        f"- [[{c.target_title}]] — {c.explanation}"
        for c in connections
    ])
    
    key_findings_text = "\n".join([
        f"- {finding}"
        for finding in concepts.key_findings
    ])
    
    return template.format(
        title=content.title,
        authors=", ".join(content.authors),
        author=content.authors[0] if content.authors else "Unknown",
        year=content.created_at.year,
        tags=", ".join(all_tags),
        source_url=content.source_url or "",
        created=content.created_at.strftime("%Y-%m-%d"),
        processed=datetime.now().strftime("%Y-%m-%d"),
        summary_standard=summaries.get(SummaryLevel.STANDARD, ""),
        summary_detailed=summaries.get(SummaryLevel.DETAILED, ""),
        key_findings=key_findings_text,
        concepts=concepts_text,
        highlights=highlights_text or "*No highlights*",
        handwritten_section=handwritten_section,
        questions=questions_text,
        followups=followups_text,
        connections=connections_text or "*No connections found*"
    )
```

---

## 6. Quality Assurance

### 6.1 Output Validation

```python
# backend/app/services/processing/validation.py

async def validate_processing_result(result: ProcessingResult) -> list[str]:
    """Validate processing outputs for quality issues."""
    
    issues = []
    
    # Check summary quality
    if len(result.summaries[SummaryLevel.STANDARD]) < 100:
        issues.append("Summary too short")
    
    # Check concept extraction
    if not result.concepts.concepts:
        issues.append("No concepts extracted")
    
    core_concepts = [c for c in result.concepts.concepts if c.importance == "core"]
    if not core_concepts:
        issues.append("No core concepts identified")
    
    # Check tag assignment
    if not result.tags.get("domain_tags"):
        issues.append("No domain tags assigned")
    
    # Check question quality
    if len(result.mastery_questions) < 2:
        issues.append("Insufficient mastery questions")
    
    return issues
```

### 6.2 Feedback Loop

```python
# Allow users to rate and correct processing outputs
@router.post("/api/processing/{content_id}/feedback")
async def submit_feedback(
    content_id: str,
    feedback: ProcessingFeedback
):
    """Submit feedback on processing quality."""
    
    # Store feedback for analysis
    await store_feedback(content_id, feedback)
    
    # If corrections provided, update outputs
    if feedback.corrections:
        await apply_corrections(content_id, feedback.corrections)
    
    # Use feedback to improve prompts over time
    if feedback.rating < 3:
        await flag_for_review(content_id, feedback)
```

---

## 7. Cost Management

### 7.1 Token Estimation

```python
def estimate_tokens(text: str) -> int:
    """Rough token estimate (4 chars per token)."""
    return len(text) // 4

def estimate_pipeline_cost(content: UnifiedContent) -> dict:
    """Estimate API costs for processing."""
    
    text_length = len(content.full_text)
    input_tokens = estimate_tokens(content.full_text[:30000])
    
    # Rough estimates per stage
    costs = {
        "analysis": input_tokens * 0.5 / 1000 * 0.00015,  # GPT-4o-mini input
        "summarization": input_tokens * 3 / 1000 * 0.003,  # Claude input
        "extraction": input_tokens / 1000 * 0.0025,  # GPT-4o input
        "tagging": 2000 / 1000 * 0.00015,  # GPT-4o-mini
        "connections": 5000 / 1000 * 0.003,  # Claude
        "questions": 3000 / 1000 * 0.0025,  # GPT-4o
        "embedding": input_tokens / 1000 * 0.00002,
    }
    
    return {
        "estimated_input_tokens": input_tokens * 5,  # Rough multiplier
        "estimated_output_tokens": input_tokens,
        "estimated_cost_usd": sum(costs.values()),
        "breakdown": costs
    }
```

### 7.2 Caching Strategy

```python
# Cache expensive operations
from functools import lru_cache
import hashlib

def content_hash(content: str) -> str:
    return hashlib.sha256(content.encode()).hexdigest()[:16]

# Redis caching for embeddings
async def get_or_compute_embedding(text: str, llm_client: LLMClient) -> list[float]:
    cache_key = f"embedding:{content_hash(text)}"
    
    cached = await redis_client.get(cache_key)
    if cached:
        return json.loads(cached)
    
    embedding = (await llm_client.embed([text]))[0]
    await redis_client.set(cache_key, json.dumps(embedding), ex=86400 * 30)  # 30 days
    
    return embedding
```

---

## 8. Configuration

```yaml
# config/processing.yaml
processing:
  # Pipeline settings
  pipeline:
    parallel_stages: false  # Run stages sequentially for now
    max_retries: 3
    timeout_seconds: 300
    
  # Content limits
  limits:
    max_content_length: 100000
    max_annotations: 100
    truncate_for_summary: 30000
    truncate_for_extraction: 20000
    
  # Model selection
  models:
    summarization: "anthropic:claude-3-5-sonnet-20241022"
    extraction: "openai:gpt-4o"
    classification: "openai:gpt-4o-mini"
    connection_discovery: "anthropic:claude-3-5-sonnet-20241022"
    question_generation: "openai:gpt-4o"
    
  # Output settings
  output:
    obsidian_vault_path: "/path/to/vault"
    note_subfolder_by_type: true
    generate_neo4j_nodes: true
    
  # Quality settings
  quality:
    validate_outputs: true
    min_summary_length: 100
    min_concepts: 1
    min_questions: 2
```

---

## 9. Related Documents

- `01_ingestion_layer.md` — Source of content for processing
- `04_knowledge_graph_neo4j.md` — Neo4j node generation
- `05_learning_system.md` — How mastery questions are used
- `03_knowledge_hub_obsidian.md` — Obsidian note format

