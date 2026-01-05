#!/usr/bin/env python3
"""
Create Obsidian Templates

Creates all note templates in the Obsidian vault's templates folder.
Templates use Templater syntax for dynamic content.

Usage:
    python scripts/setup/create_templates.py
    python scripts/setup/create_templates.py --data-dir ~/my/data
"""

import argparse
from pathlib import Path
from typing import Any

from _common import add_common_args, resolve_paths


# Template definitions with Templater syntax
TEMPLATES: dict[str, str] = {
    "paper.md": """---
type: paper
title: "{{title}}"
authors: []
year: {{date:YYYY}}
venue: ""
doi: ""
tags: []
status: unread
has_handwritten_notes: false
created: {{date:YYYY-MM-DD}}
processed: 
---

## Summary
<!-- LLM-generated summary will be inserted here -->

## Key Findings
- 

## Core Concepts
- **Concept**: Definition

## My Highlights
> Highlight text
> — Page X

## My Handwritten Notes
> [!note] Page X
> Transcription
> *Context: "surrounding text"*

## Mastery Questions
- [ ] Question 1
- [ ] Question 2

## Follow-up Tasks
- [ ] Task #research

## Connections
- [[Related Note]] — Relationship explanation

---

## Detailed Notes
""",
    "article.md": """---
type: article
title: "{{title}}"
source: ""
author: ""
published: 
tags: []
status: unread
created: {{date:YYYY-MM-DD}}
processed:
---

## Summary
<!-- LLM-generated summary -->

## Key Takeaways
1. 
2. 

## Highlights
> Highlight text

## My Notes


## Action Items
- [ ] 

## Related
- [[Related Note]]
""",
    "book.md": """---
type: book
title: "{{title}}"
author: ""
isbn: ""
tags: []
status: reading
started: {{date:YYYY-MM-DD}}
finished: 
rating: 
---

## Overview


## Key Themes
### Theme 1


## Highlights by Chapter

### Chapter 1: Title
> Highlight
> — Page X


## Favorite Quotes
> "Quote"
> — Author, p. X

## How This Changed My Thinking


## Action Items
- [ ] 

## Related Books
- [[Other Book]]
""",
    "code.md": """---
type: code
repo: "{{title}}"
url: ""
language: ""
stars: 
tags: []
created: {{date:YYYY-MM-DD}}
---

## Purpose


## Why I Saved This


## Architecture Overview


## Tech Stack
- **Language**: 
- **Framework**: 
- **Dependencies**: 

## Notable Patterns
### Pattern Name


## Key Learnings
1. 
2. 

## Ideas to Apply
- [ ] 

## Related
- [[Related Repo]]
""",
    "concept.md": """---
type: concept
name: "{{title}}"
domain: ""
complexity: foundational
tags: []
created: {{date:YYYY-MM-DD}}
---

## Definition


## Why It Matters


## Key Properties
- 

## Examples
### Example 1


## Common Misconceptions
- ❌ Misconception
- ✅ Correction

## Prerequisites
- [[Prerequisite Concept]]

## Related Concepts
- [[Related]] — Relationship

## Sources
- [[Source Paper]]
""",
    "idea.md": """---
type: idea
title: "{{title}}"
tags: []
status: status/actionable
created: {{date:YYYY-MM-DD}}
---

## Idea


## Context


## Why It Matters


## Next Steps
- [ ] 

## Related
- [[Related Note]]
""",
    "daily.md": """---
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
""",
    "exercise.md": """---
type: exercise
topic: ""
difficulty: intermediate
exercise_type: free-recall
source_concept: ""
tags: []
created: {{date:YYYY-MM-DD}}
---

## Question


## Expected Answer


## Hints
1. 
2. 

## Related Concepts
- [[Concept]]

## Source Material
- [[Source Note]]
""",
    "career.md": """---
type: career
title: "{{title}}"
category: ""
tags: []
status: status/actionable
created: {{date:YYYY-MM-DD}}
---

## Overview


## Why This Matters


## Current State
<!-- Where am I now? -->


## Target State
<!-- Where do I want to be? -->


## Action Plan
- [ ] 

## Resources Needed
- 

## Timeline
| Milestone | Target Date | Status |
|-----------|-------------|--------|
|           |             |        |

## Progress Notes


## Related
- [[Related Note]]
""",
    "personal.md": """---
type: personal
title: "{{title}}"
area: ""
tags: []
status: status/actionable
created: {{date:YYYY-MM-DD}}
---

## Summary


## Why This Matters to Me


## Key Insights
1. 
2. 
3. 

## How This Applies to My Life


## Action Items
- [ ] 

## Reflections


## Related
- [[Related Note]]
""",
    "project.md": """---
type: project
title: "{{title}}"
status: planning
priority: medium
started: {{date:YYYY-MM-DD}}
target_completion: 
completed: 
tags: []
---

## Vision
<!-- What does success look like? -->


## Motivation
<!-- Why am I doing this? -->


## Goals
- [ ] Primary goal
- [ ] Secondary goal

## Scope
### In Scope
- 

### Out of Scope
- 

## Milestones
| Milestone | Target | Status |
|-----------|--------|--------|
|           |        |        |

## Tasks
### To Do
- [ ] 

### In Progress
- [ ] 

### Done
- [x] 

## Resources
- **Time**: 
- **Budget**: 
- **Tools**: 

## Progress Log
### {{date:YYYY-MM-DD}}
- 

## Lessons Learned


## Related
- [[Related Project]]
""",
    "reflection.md": """---
type: reflection
title: "{{title}}"
period: ""
tags: []
created: {{date:YYYY-MM-DD}}
---

## What Went Well
1. 
2. 
3. 

## What Could Be Better
1. 
2. 
3. 

## Key Learnings
- 

## Surprises
<!-- What unexpected things happened? -->


## Gratitude
<!-- What am I thankful for? -->
1. 
2. 
3. 

## Energy & Mood
<!-- How did I feel during this period? -->


## Priorities for Next Period
1. 
2. 
3. 

## Adjustments to Make
- [ ] 

## Questions to Explore
- 
""",
    "work.md": """---
type: work
title: "{{title}}"
category: ""
project: ""
tags: []
status: status/actionable
created: {{date:YYYY-MM-DD}}
---

## Summary


## Context


## Key Points
1. 
2. 
3. 

## Action Items
- [ ] 

## Decisions Made


## Follow-ups Needed
- [ ] 

## Related
- [[Related Note]]
""",
}


def create_templates(vault_path: Path, config: dict[str, Any]) -> None:
    """Create all templates in the vault's templates folder."""

    obsidian_config = config.get("obsidian", {})
    templates_config = obsidian_config.get("templates", {})
    templates_folder = templates_config.get("folder", "templates")

    templates_dir = vault_path / templates_folder
    templates_dir.mkdir(parents=True, exist_ok=True)

    print(f"📝 Creating Obsidian templates in {templates_folder}/:")

    for filename, content in TEMPLATES.items():
        template_path = templates_dir / filename

        with open(template_path, "w") as f:
            f.write(content)

        print(f"  ✅ {filename}")

    print(f"\n✅ Created {len(TEMPLATES)} templates")


def main() -> None:
    parser = argparse.ArgumentParser(description="Create Obsidian templates")
    add_common_args(parser)
    args = parser.parse_args()

    config, data_dir, vault_path = resolve_paths(args)

    print(f"🧠 Second Brain Template Creator")
    print(f"   Vault path: {vault_path}")
    print()

    create_templates(vault_path, config)


if __name__ == "__main__":
    main()
