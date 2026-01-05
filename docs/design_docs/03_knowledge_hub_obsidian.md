# Knowledge Hub (Obsidian) Design

> **Document Status**: Design Specification  
> **Last Updated**: December 2025  
> **Related Docs**: `02_llm_processing_layer.md`, `04_knowledge_graph_neo4j.md`

---

## 1. Overview

Obsidian serves as the primary knowledge storage and human interface. All processed content ultimately becomes Markdown notes in the vault, enabling local-first ownership, powerful search, and extensive plugin ecosystem.

### Design Goals

1. **Local-First**: All data stored as plain Markdown files
2. **Human-Readable**: Notes make sense without the system
3. **Linked Knowledge**: Extensive use of bidirectional links
4. **Consistent Structure**: Templates enforce uniformity
5. **Plugin-Enhanced**: Leverage ecosystem for features

---

## 2. Vault Structure

> **EXTENSIBILITY**: The vault structure is defined in `config/default.yaml` and can be extended without code changes. See Section 9 for details on adding new content types.

```
vault/
├── .obsidian/                    # Obsidian configuration (auto-managed)
│   ├── plugins/                  # Installed plugins
│   ├── themes/                   # Custom themes
│   └── workspace.json            # Layout state
│
├── sources/                      # PRIMARY: Ingested content by type
│   │                             # (extensible via config/default.yaml)
│   │
│   │   # --- TECHNICAL CONTENT ---
│   ├── papers/                   # Academic papers, research
│   │   ├── 2024/                 # Organized by year
│   │   └── _index.md             # Auto-generated index
│   ├── articles/                 # Blog posts, news, essays
│   ├── books/                    # Book notes and highlights
│   ├── code/                     # Repository analyses
│   ├── ideas/                    # Fleeting notes, quick captures
│   │
│   │   # --- WORK & CAREER ---
│   ├── work/                     # Work-specific content
│   │   ├── meetings/
│   │   ├── proposals/
│   │   └── projects/
│   ├── career/                   # Career development
│   │   ├── goals/
│   │   ├── interviews/
│   │   ├── networking/
│   │   └── skills/
│   │
│   │   # --- PERSONAL DEVELOPMENT ---
│   ├── personal/                 # Personal development
│   │   ├── goals/
│   │   ├── reflections/
│   │   ├── habits/
│   │   └── wellbeing/
│   ├── projects/                 # Personal projects
│   │   ├── active/
│   │   ├── ideas/
│   │   └── archive/
│   │
│   │   # --- NON-TECHNICAL ---
│   └── non-tech/                 # Non-technical learning
│       ├── finance/
│       ├── hobbies/
│       ├── philosophy/
│       └── misc/
│
├── topics/                       # Topic-based index notes (auto-generated)
│   ├── ml/
│   │   ├── _index.md             # ML overview + links
│   │   ├── transformers.md       # Topic note for transformers
│   │   └── reinforcement-learning.md
│   ├── systems/
│   │   ├── distributed.md
│   │   └── databases.md
│   └── ...
│
├── concepts/                     # Standalone concept definitions
│   ├── attention-mechanism.md
│   ├── raft-consensus.md
│   └── ...
│
├── exercises/                    # Generated practice problems
│   ├── by-topic/
│   │   ├── ml-transformers/
│   │   └── systems-distributed/
│   └── daily/                    # Daily practice sets
│
├── reviews/                      # Spaced repetition queue
│   ├── due/                      # Cards due for review
│   ├── archive/                  # Completed review sessions
│   └── _queue.md                 # Review dashboard
│
├── daily/                        # Daily notes
│   ├── 2024-12-20.md
│   └── ...
│
├── templates/                    # Note templates (one per content type)
│   ├── paper.md
│   ├── article.md
│   ├── book.md
│   ├── code.md
│   ├── concept.md
│   ├── idea.md
│   ├── career.md                 # Career development template
│   ├── personal.md               # Personal development template
│   ├── project.md                # Personal project template
│   ├── reflection.md             # Reflection/retrospective template
│   ├── daily.md
│   └── exercise.md
│
└── meta/                         # System configuration
    ├── tag-taxonomy.md           # AUTO-GENERATED from config/tag-taxonomy.yaml (do not edit)
    ├── workflows.md              # Process documentation
    └── dashboard.md              # Main system dashboard
```

---

## 3. Note Templates

### 3.1 Paper Template

```markdown
---
type: paper
title: "{{title}}"
authors: [{{authors}}]
year: {{year}}
venue: "{{venue}}"
doi: "{{doi}}"
tags: [{{tags}}]
status: unread | reading | read | reviewed
has_handwritten_notes: false
created: {{date}}
processed: {{processed_date}}
---

## Summary
{{llm_generated_summary}}

## Key Findings
- {{finding_1}}
- {{finding_2}}

## Core Concepts
- **{{concept_1}}**: {{definition}}
- **{{concept_2}}**: {{definition}}

## My Highlights
> {{highlight_1}}
> — Page {{page}}

> {{highlight_2}}

## My Handwritten Notes
> [!note] Page {{page}}
> {{transcription}}
> *Context: "{{surrounding_text}}"*

## Mastery Questions
- [ ] {{question_1}}
- [ ] {{question_2}}

## Follow-up Tasks
- [ ] {{task_1}} `research` `30min`
- [ ] {{task_2}} `practice` `1hr`

## Connections
- [[related_note_1]] — {{relationship_explanation}}
- [[related_note_2]] — {{relationship_explanation}}

---

## Detailed Notes
{{detailed_content}}
```

### 3.2 Article Template

```markdown
---
type: article
title: "{{title}}"
source: "{{url}}"
author: "{{author}}"
published: {{date}}
tags: [{{tags}}]
created: {{date}}
processed: {{processed_date}}
---

## Summary
{{llm_generated_summary}}

## Key Takeaways
1. {{takeaway_1}}
2. {{takeaway_2}}

## Highlights
> {{highlight}}

## My Notes
{{personal_notes}}

## Action Items
- [ ] {{action}}

## Related
- [[related_note]]
```

### 3.3 Book Template

```markdown
---
type: book
title: "{{title}}"
author: "{{author}}"
isbn: "{{isbn}}"
tags: [{{tags}}]
status: reading | read
started: {{date}}
finished: {{date}}
rating: {{1-5}}
---

## Overview
{{book_summary}}

## Key Themes
### {{theme_1}}
{{theme_notes}}

### {{theme_2}}
{{theme_notes}}

## Highlights by Chapter

### Chapter {{n}}: {{chapter_title}}
> {{highlight}}
> — Page {{page}}

{{my_thoughts}}

## Favorite Quotes
> "{{quote}}"
> — {{author}}, p. {{page}}

## How This Changed My Thinking
{{reflection}}

## Action Items
- [ ] {{action}}

## Related Books
- [[other_book]]
```

### 3.4 Code Repository Template

```markdown
---
type: code
repo: "{{full_name}}"
url: "{{github_url}}"
language: "{{primary_language}}"
stars: {{stars}}
tags: [{{tags}}]
created: {{date}}
---

## Purpose
{{what_it_does}}

## Why I Saved This
{{personal_reason}}

## Architecture Overview
{{architecture_summary}}

## Tech Stack
- **Language**: {{language}}
- **Framework**: {{framework}}
- **Dependencies**: {{key_deps}}

## Notable Patterns
### {{pattern_name}}
{{pattern_description}}

## Key Learnings
1. {{learning_1}}
2. {{learning_2}}

## Ideas to Apply
- [ ] {{idea}}

## Related
- [[related_repo]]
```

### 3.5 Concept Template

```markdown
---
type: concept
name: "{{concept_name}}"
domain: "{{domain}}"
complexity: foundational | intermediate | advanced
tags: [{{tags}}]
created: {{date}}
---

## Definition
{{clear_definition}}

## Why It Matters
{{importance_explanation}}

## Key Properties
- {{property_1}}
- {{property_2}}

## Examples
### Example 1: {{example_name}}
{{example_description}}

## Common Misconceptions
- ❌ {{misconception}}
- ✅ {{correction}}

## Prerequisites
- [[prerequisite_concept_1]]
- [[prerequisite_concept_2]]

## Related Concepts
- [[related_1]] — {{relationship}}
- [[related_2]] — {{relationship}}

## Sources
- [[source_paper_1]]
- [[source_article_1]]
```

---

## 4. Tagging System

> **EXTENSIBILITY**: The tag taxonomy is defined in `config/tag-taxonomy.yaml` (single source of truth) and can be extended by adding new domains/categories. The `meta/tag-taxonomy.md` file in the vault is **auto-generated** from the YAML config—do not edit it directly.

### 4.1 Tag Taxonomy

```yaml
# config/tag-taxonomy.yaml (single source of truth)
# Tag Hierarchy: domain/category/topic (3 levels)

# TECHNICAL DOMAIN TAGS (hierarchical)
domains:
  ml:
    - ml/architecture/transformers
    - ml/architecture/llms
    - ml/architecture/diffusion
    - ml/technique/fine-tuning
    - ml/technique/rlhf
    - ml/application/agents
    - ml/application/rag
  systems:
    - systems/distributed/consensus
    - systems/distributed/replication
    - systems/storage/databases
    - systems/storage/caching
  engineering:
    - engineering/design/architecture
    - engineering/design/api
    - engineering/practices/testing
    - engineering/practices/devops

  # CAREER & PERSONAL DOMAIN TAGS
  career:
    - career/growth/goals
    - career/growth/strategy
    - career/skills/technical
    - career/skills/soft
    - career/networking/mentorship
    - career/job-search/interviews
  personal:
    - personal/goals/life
    - personal/goals/annual
    - personal/growth/mindset
    - personal/growth/habits
    - personal/wellbeing/physical
    - personal/wellbeing/mental
    - personal/relationships/family
  projects:
    - projects/active/side-project
    - projects/active/learning
    - projects/planning/ideas
    - projects/planning/roadmap

  # NON-TECHNICAL DOMAIN TAGS
  non-tech:
    - non-tech/finance/investing
    - non-tech/finance/budgeting
    - non-tech/philosophy/mental-models
    - non-tech/hobbies/reading
    - non-tech/learning/history

  # LEADERSHIP & PRODUCTIVITY (existing)
  leadership:
    - leadership/management/teams
    - leadership/management/hiring
    - leadership/skills/communication
    - leadership/skills/strategy
  productivity:
    - productivity/learning/techniques
    - productivity/systems/habits
    - productivity/systems/time

# Status Tags (flat)
status:
  - status/actionable     # Has pending tasks
  - status/reference      # Useful for lookup
  - status/archive        # Historical interest only
  - status/review         # Needs review/update
  - status/processing     # Being processed

# Quality Tags (flat)
quality:
  - quality/foundational  # Must-know content
  - quality/deep-dive     # Comprehensive treatment
  - quality/overview      # Surface-level introduction
  - quality/practical     # Hands-on, applied

# NOTE: Source tags (source/paper, source/article) are NOT used.
# The folder structure already encodes source type.
# Use domain tags and status tags instead.
```

### 4.2 Tag Usage Rules

1. **1-3 domain tags** per note (most specific that applies)
2. **1 status tag** (required)
3. **1 quality tag** (optional but recommended)
4. **Source tag auto-applied** based on content type
5. Prefer existing tags over new ones
6. Review suggested new tags monthly

---

## 5. Linking Strategy

### 5.1 Link Types

| Link Type | Syntax | Purpose |
|-----------|--------|---------|
| **Standard** | `[[Note Name]]` | General reference |
| **Aliased** | `[[Note Name\|display text]]` | Custom display text |
| **Header** | `[[Note#Section]]` | Link to specific section |
| **Block** | `[[Note#^block-id]]` | Link to specific paragraph |
| **Embed** | `![[Note]]` | Embed note content |

### 5.2 Linking Guidelines

```markdown
## Good Linking Practices

1. **Link to concepts, not just sources**
   - ❌ "Transformers were introduced in [[Attention Is All You Need]]"
   - ✅ "[[Transformers]] were introduced in [[Attention Is All You Need]]"

2. **Create concept notes for recurring ideas**
   - If you mention "gradient descent" in 5+ notes, create [[Gradient Descent]]

3. **Use block references for specific claims**
   - "The authors found X [[Paper#^finding-1]]"

4. **Maintain bidirectional awareness**
   - When linking to X, consider: should X link back?

5. **Link follow-ups to sources**
   - "Based on [[Paper]], I should try [[Project Idea]]"
```

---

## 6. Plugin Configuration

### 6.1 Essential Plugins

| Plugin | Purpose | Configuration |
|--------|---------|---------------|
| **Dataview** | Query notes as database | See query examples below |
| **Templater** | Advanced templates | Auto-insert dates, prompts |
| **Tasks** | Track todos across vault | Global task queries |
| **Calendar** | Daily notes navigation | Link to daily/ folder |
| **Tag Wrangler** | Bulk tag management | Rename, merge tags |
| **Linter** | Enforce formatting | YAML frontmatter, headings |

### 6.2 Recommended Plugins

| Plugin | Purpose |
|--------|---------|
| **Smart Connections** | AI-powered related notes |
| **Graph Analysis** | Enhanced graph metrics |
| **Waypoint** | Auto-generate folder indices |
| **Periodic Notes** | Weekly/monthly reviews |
| **Kanban** | Visual project boards |

### 6.3 Dataview Queries

```markdown
## Dashboard Queries

### Recently Processed
```dataview
TABLE title, tags, processed
FROM "sources"
WHERE processed
SORT processed DESC
LIMIT 10
```

### Unread Papers
```dataview
LIST
FROM "sources/papers"
WHERE status = "unread"
SORT created DESC
```

### Actionable Items
```dataview
TASK
FROM "sources"
WHERE !completed
GROUP BY file.link
```

### Topics by Note Count
```dataview
TABLE length(rows) as "Notes"
FROM "sources"
GROUP BY tags
SORT length(rows) DESC
LIMIT 20
```

### Notes Needing Review
```dataview
LIST
FROM "sources"
WHERE status = "status/review"
SORT file.mtime ASC
```

---

## 7. Automation

### 7.1 Note Creation Workflow

```python
# scripts/create_obsidian_note.py

from pathlib import Path
import frontmatter
from datetime import datetime

def create_note(
    vault_path: Path,
    content_type: str,
    title: str,
    content: str,
    frontmatter_data: dict
) -> Path:
    """Create a new note in the appropriate location."""
    
    # Determine folder
    folder_map = {
        "paper": "sources/papers",
        "article": "sources/articles",
        "book": "sources/books",
        "code": "sources/code",
        "idea": "sources/ideas",
        "concept": "concepts"
    }
    
    folder = vault_path / folder_map.get(content_type, "sources/ideas")
    
    # Add year subfolder for papers
    if content_type == "paper":
        year = frontmatter_data.get("year", datetime.now().year)
        folder = folder / str(year)
    
    folder.mkdir(parents=True, exist_ok=True)
    
    # Create safe filename
    safe_title = sanitize_filename(title)
    filepath = folder / f"{safe_title}.md"
    
    # Handle duplicates
    counter = 1
    while filepath.exists():
        filepath = folder / f"{safe_title}-{counter}.md"
        counter += 1
    
    # Create note with frontmatter
    post = frontmatter.Post(content)
    post.metadata = frontmatter_data
    
    with open(filepath, 'w') as f:
        f.write(frontmatter.dumps(post))
    
    return filepath

def sanitize_filename(title: str) -> str:
    """Convert title to safe filename."""
    import re
    # Remove/replace unsafe characters
    safe = re.sub(r'[<>:"/\\|?*]', '', title)
    safe = safe.strip()[:100]  # Limit length
    return safe
```

### 7.2 Index Generation

```python
# scripts/generate_indices.py

async def generate_folder_index(folder_path: Path) -> str:
    """Generate an index note for a folder."""
    
    notes = list(folder_path.glob("*.md"))
    notes = [n for n in notes if n.name != "_index.md"]
    
    # Parse frontmatter for each note
    entries = []
    for note in notes:
        fm = frontmatter.load(note)
        entries.append({
            "title": fm.get("title", note.stem),
            "tags": fm.get("tags", []),
            "created": fm.get("created"),
            "link": f"[[{note.stem}]]"
        })
    
    # Sort by date
    entries.sort(key=lambda x: x.get("created", ""), reverse=True)
    
    # Generate markdown
    index_content = f"# {folder_path.name.title()}\n\n"
    index_content += f"*{len(entries)} notes*\n\n"
    
    # Group by tag or year
    index_content += "## Recent\n\n"
    for entry in entries[:10]:
        index_content += f"- {entry['link']}\n"
    
    index_content += "\n## All Notes\n\n"
    for entry in entries:
        tags_str = " ".join([f"`{t}`" for t in entry.get("tags", [])[:3]])
        index_content += f"- {entry['link']} {tags_str}\n"
    
    return index_content
```

### 7.3 Daily Note Template

```markdown
---
type: daily
date: {{date:YYYY-MM-DD}}
---

# {{date:dddd, MMMM D, YYYY}}

## 📥 Inbox
<!-- Quick captures, ideas, todos that need processing -->


## 📚 Learning
### Today's Practice
- [ ] Complete review queue ([[reviews/_queue]])

### Notes Processed
<!-- Links to notes processed today -->


## ✅ Tasks
### Must Do
- [ ] 

### Should Do
- [ ] 

### Could Do
- [ ] 

## 📝 Journal
<!-- Reflection, thoughts, learnings -->


## 🔗 Quick Links
- [[meta/dashboard|Dashboard]]
- [[reviews/_queue|Review Queue]]
```

---

## 8. Sync Strategy

### 8.1 With Neo4j

```python
# Bi-directional sync between Obsidian and Neo4j

async def sync_to_neo4j(note_path: Path, neo4j_client):
    """Push note to Neo4j graph."""
    
    fm = frontmatter.load(note_path)
    
    # Create or update node
    await neo4j_client.run("""
        MERGE (n:Note {path: $path})
        SET n.title = $title,
            n.type = $type,
            n.tags = $tags,
            n.updated = datetime()
        RETURN n
    """, {
        "path": str(note_path),
        "title": fm.get("title"),
        "type": fm.get("type"),
        "tags": fm.get("tags", [])
    })
    
    # Extract and create links
    content = note_path.read_text()
    links = extract_wikilinks(content)
    
    for link in links:
        await neo4j_client.run("""
            MATCH (source:Note {path: $source_path})
            MERGE (target:Note {title: $target_title})
            MERGE (source)-[:LINKS_TO]->(target)
        """, {
            "source_path": str(note_path),
            "target_title": link
        })

def extract_wikilinks(content: str) -> list[str]:
    """Extract [[wikilinks]] from content."""
    import re
    pattern = r'\[\[([^\]|]+)(?:\|[^\]]+)?\]\]'
    return re.findall(pattern, content)
```

### 8.2 With Backend

```python
# Watch for changes and sync

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class VaultWatcher(FileSystemEventHandler):
    def __init__(self, vault_path: Path, sync_callback):
        self.vault_path = vault_path
        self.sync_callback = sync_callback
    
    def on_modified(self, event):
        if event.src_path.endswith('.md'):
            asyncio.create_task(
                self.sync_callback(Path(event.src_path))
            )
    
    def on_created(self, event):
        if event.src_path.endswith('.md'):
            asyncio.create_task(
                self.sync_callback(Path(event.src_path))
            )

def start_vault_watcher(vault_path: Path, sync_callback):
    observer = Observer()
    observer.schedule(
        VaultWatcher(vault_path, sync_callback),
        str(vault_path),
        recursive=True
    )
    observer.start()
    return observer
```

---

## 9. Configuration

> **EXTENSIBILITY**: Configuration uses a Content Type Registry pattern. Adding new content types requires only YAML changes, no code modifications.

```yaml
# config/default.yaml
obsidian:
  vault_path: "/path/to/vault"
  
  folders:
    sources: "sources"
    topics: "topics"
    concepts: "concepts"
    exercises: "exercises"
    reviews: "reviews"
    daily: "daily"
    templates: "templates"

# CONTENT TYPE REGISTRY
# Single source of truth for all content types.
# To add a new type: add entry here + create template file.
content_types:
  # Technical content
  paper:
    folder: "sources/papers"
    template: "templates/paper.md"
    description: "Academic papers, research"
    icon: "📄"
  article:
    folder: "sources/articles"
    template: "templates/article.md"
    description: "Web articles, blog posts"
    icon: "📰"
  book:
    folder: "sources/books"
    template: "templates/book.md"
    description: "Book notes and highlights"
    icon: "📚"
  code:
    folder: "sources/code"
    template: "templates/code.md"
    description: "Repository analyses"
    icon: "💻"
  idea:
    folder: "sources/ideas"
    template: "templates/idea.md"
    description: "Quick captures, fleeting notes"
    icon: "💡"
    
  # Career & personal
  career:
    folder: "sources/career"
    template: "templates/career.md"
    description: "Career development"
    icon: "🎯"
    subfolders: [goals, interviews, networking, skills]
  personal:
    folder: "sources/personal"
    template: "templates/personal.md"
    description: "Personal development"
    icon: "🌱"
    subfolders: [goals, reflections, habits, wellbeing]
  project:
    folder: "sources/projects"
    template: "templates/project.md"
    description: "Personal projects"
    icon: "🚀"
    subfolders: [active, ideas, archive]
  
  # System types (hidden from user selection)
  concept:
    folder: "concepts"
    template: "templates/concept.md"
    system: true
  daily:
    folder: "daily"
    template: "templates/daily.md"
    system: true
    
  sync:
    neo4j_enabled: true
    watch_changes: true
    index_generation: true
    
  formatting:
    date_format: "YYYY-MM-DD"
    yaml_frontmatter: true
    auto_link_concepts: true
```

---

## 10. Extensibility

The vault system is designed to be extended without code changes.

### Adding a New Content Type

1. **Add to `config/default.yaml`**:
   ```yaml
   content_types:
     podcast:
       folder: "sources/podcasts"
       template: "templates/podcast.md"
       description: "Podcast notes"
       icon: "🎙️"
   ```

2. **Create template** (`templates/podcast.md`):
   ```markdown
   ---
   type: podcast
   title: "{{title}}"
   podcast_name: ""
   episode: ""
   tags: []
   status: unread
   ---
   
   ## Summary
   
   ## Key Takeaways
   ```

3. **Run vault setup**: `python scripts/setup/setup_vault.py`

The system will automatically:
- Create the `sources/podcasts/` folder
- Recognize "podcast" as a valid content type
- Use the template for new notes
- Include podcasts in Dataview queries

### Adding New Tag Domains

Edit `config/tag-taxonomy.yaml` (single source of truth):

```yaml
domains:
  new-domain:
    - new-domain/category/topic
```

### Template Requirements

All templates must have these frontmatter fields:
- `type: <content_type>` — For identification
- `tags: []` — For taxonomy queries
- `status: <status>` — For workflow tracking

---

## 11. Related Documents

- `02_llm_processing_layer.md` — Note content generation
- `04_knowledge_graph_neo4j.md` — Graph sync
- `05_learning_system.md` — Review and exercise integration
- `00_foundation_implementation.md` — Content type registry details

