#!/usr/bin/env python3
"""
Create Meta Notes

Creates the system meta notes (dashboard, workflows, plugin setup)
in the Obsidian vault's meta folder.

Usage:
    python scripts/create_meta_notes.py
    python scripts/create_meta_notes.py --data-dir ~/my/data
"""

import argparse
from datetime import datetime
from pathlib import Path
from typing import Any

from _common import add_common_args, resolve_paths


META_NOTES: dict[str, str] = {
    "dashboard.md": """---
type: meta
title: "Second Brain Dashboard"
created: {date}
---

# 🧠 Second Brain Dashboard

## 📊 Quick Stats

```dataview
TABLE WITHOUT ID
  length(filter(rows, (r) => r.type = "paper")) as "📄 Papers",
  length(filter(rows, (r) => r.type = "article")) as "📰 Articles",
  length(filter(rows, (r) => r.type = "book")) as "📚 Books",
  length(filter(rows, (r) => r.type = "code")) as "💻 Code",
  length(filter(rows, (r) => r.type = "idea")) as "💡 Ideas"
FROM "sources"
FLATTEN type
GROUP BY true
```

---

## 📥 Inbox (Needs Processing)

```dataview
TABLE title as "Title", type as "Type", created as "Captured"
FROM "sources"
WHERE status = "processing" OR status = "unread"
SORT created DESC
LIMIT 10
```

---

## 📚 Currently Reading

```dataview
LIST
FROM "sources/books"
WHERE status = "reading"
SORT file.mtime DESC
```

---

## ✅ Open Tasks

```dataview
TASK
FROM "sources" OR "concepts"
WHERE !completed
LIMIT 15
```

---

## 🏷️ Top Topics

```dataview
TABLE length(rows) as "Notes"
FROM "sources"
FLATTEN tags
WHERE !startswith(tags, "status/") AND !startswith(tags, "quality/")
GROUP BY tags
SORT length(rows) DESC
LIMIT 10
```

---

## 🔗 Quick Links

- [[meta/tag-taxonomy|Tag Taxonomy]]
- [[meta/plugin-setup|Plugin Setup]]
- [[meta/workflows|Workflows]]
- [[reviews/_queue|Review Queue]]

---

## 📅 Recent Activity

```dataview
TABLE file.mtime as "Modified", type as "Type"
FROM "sources" OR "concepts"
SORT file.mtime DESC
LIMIT 10
```
""",
    "workflows.md": """---
type: meta
title: "Workflows"
created: {date}
---

# Workflows

## Daily Workflow

### Morning (5-10 min)
1. Open today's daily note
2. Review inbox items
3. Check [[reviews/_queue|review queue]]
4. Plan learning focus for the day

### Throughout Day
1. Capture ideas immediately (quick capture)
2. Tag with `status/actionable` if needs follow-up
3. Link to related notes when relevant

### Evening (5-10 min)
1. Process inbox items
2. Update task status
3. Journal reflection

---

## Content Processing Workflow

### 1. Capture
- Quick capture via API/CLI
- Auto-placed in `sources/ideas` or appropriate folder

### 2. Process
- LLM generates summary
- Extracts key concepts
- Suggests tags and connections

### 3. Review
- Verify accuracy of summary
- Add personal notes
- Create manual connections
- Update status tag

### 4. Learn
- Generate mastery questions
- Schedule for spaced repetition
- Practice via exercises

---

## Paper Processing

1. **Upload PDF** -> `/api/ingest/pdf`
2. **Extract text & highlights** -> Automated
3. **OCR handwritten notes** -> Vision LLM
4. **Generate summary** -> LLM
5. **Review & enhance** -> Manual
6. **Create concept notes** -> For key ideas
7. **Add to review queue** -> Mastery questions

---

## Weekly Review

Every Sunday:

- [ ] Process remaining inbox items
- [ ] Review notes marked `status/review`
- [ ] Check for orphan notes (no links)
- [ ] Update tag taxonomy if needed
- [ ] Archive completed items
- [ ] Plan next week's learning focus

---

## Monthly Review

First of each month:

- [ ] Review mastery progress
- [ ] Identify knowledge gaps
- [ ] Update learning goals
- [ ] Clean up unused tags
- [ ] Archive old content
""",
    "plugin-setup.md": """---
type: meta
title: "Plugin Setup Guide"
created: {date}
---

# Obsidian Plugin Setup

## Essential Plugins (Install First)

### 1. Dataview
**Purpose**: Query notes as a database

**Installation**: Community Plugins > Browse > "Dataview" > Install > Enable

**Settings**:
- Enable JavaScript Queries: ON
- Enable Inline Queries: ON

### 2. Templater
**Purpose**: Advanced templates with dynamic content

**Installation**: Community Plugins > Browse > "Templater" > Install > Enable

**Settings**:
- Template folder location: `templates`
- Enable Folder Templates: ON
- Add folder templates:
  - `sources/papers` -> `templates/paper.md`
  - `sources/articles` -> `templates/article.md`
  - `sources/books` -> `templates/book.md`
  - `sources/code` -> `templates/code.md`
  - `sources/ideas` -> `templates/idea.md`
  - `sources/career` -> `templates/career.md`
  - `sources/personal` -> `templates/personal.md`
  - `sources/personal/reflections` -> `templates/reflection.md`
  - `sources/projects` -> `templates/project.md`
  - `concepts` -> `templates/concept.md`
  - `daily` -> `templates/daily.md`

### 3. Tasks
**Purpose**: Track todos across the vault

**Installation**: Community Plugins > Browse > "Tasks" > Install > Enable

**Settings**:
- Global task filter: Leave empty (search all)
- Set done date on completion: ON

### 4. Tag Wrangler
**Purpose**: Bulk tag management

**Installation**: Community Plugins > Browse > "Tag Wrangler" > Install > Enable

### 5. Linter
**Purpose**: Enforce formatting consistency

**Installation**: Community Plugins > Browse > "Linter" > Install > Enable

**Settings**:
- YAML Title: ON
- YAML Sort: ON
- Heading blank lines: ON

---

## Recommended Plugins

### 6. Calendar
**Purpose**: Visual daily notes navigation

### 7. Periodic Notes
**Purpose**: Weekly/monthly review notes

### 8. Waypoint
**Purpose**: Auto-generate folder index notes

### 9. Kanban
**Purpose**: Visual project boards

---

## Dataview Query Examples

### Recently Processed Notes
```dataview
TABLE title as "Title", tags as "Tags", processed as "Processed"
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

### All Open Tasks
```dataview
TASK
FROM "sources" OR "concepts"
WHERE !completed
GROUP BY file.link
```

---

## Hotkeys to Configure

| Action | Suggested Hotkey |
|--------|------------------|
| Open daily note | Cmd/Ctrl + D |
| New note from template | Cmd/Ctrl + Shift + N |
| Search tags | Cmd/Ctrl + Shift + T |
| Toggle task complete | Cmd/Ctrl + Enter |
| Insert template | Alt + T |
""",
}

REVIEW_QUEUE: str = """---
type: meta
title: "Review Queue"
created: {date}
---

# 📋 Review Queue

## Due Today

```dataview
LIST
FROM "sources" OR "concepts"
WHERE due_date = date(today)
SORT file.mtime ASC
```

## Overdue

```dataview
LIST
FROM "sources" OR "concepts"
WHERE due_date < date(today)
SORT due_date ASC
```

## Coming Up (Next 7 Days)

```dataview
TABLE due_date as "Due", difficulty as "Difficulty"
FROM "sources" OR "concepts"
WHERE due_date > date(today) AND due_date <= date(today) + dur(7 days)
SORT due_date ASC
```

---

## Stats

- **Total cards**: `$= dv.pages('"sources" OR "concepts"').where(p => p.type == "concept").length`
- **Due today**: Count from query above
- **Streak**: Track manually or via backend

---

## Quick Actions

- Start Practice Session (via web app)
- Generate New Cards (via web app)
"""


def create_meta_notes(vault_path: Path, config: dict[str, Any]) -> None:
    """Create all meta notes in the vault's meta folder."""

    obsidian_config = config.get("obsidian", {})
    meta_config = obsidian_config.get("meta", {})
    meta_folder = meta_config.get("folder", "meta")

    # Get reviews folder from system_folders
    reviews_folder = "reviews"
    system_folders: list[str] = obsidian_config.get("system_folders", [])
    for folder in system_folders:
        if folder.startswith("reviews"):
            reviews_folder = folder.split("/")[0]
            break

    meta_dir = vault_path / meta_folder
    meta_dir.mkdir(parents=True, exist_ok=True)

    reviews_dir = vault_path / reviews_folder
    reviews_dir.mkdir(parents=True, exist_ok=True)

    today = datetime.now().strftime("%Y-%m-%d")

    print(f"📋 Creating meta notes in {meta_folder}/:")

    for filename, content in META_NOTES.items():
        note_path = meta_dir / filename

        with open(note_path, "w") as f:
            f.write(content.format(date=today))

        print(f"  ✅ {filename}")

    # Create review queue
    queue_path = reviews_dir / "_queue.md"
    with open(queue_path, "w") as f:
        f.write(REVIEW_QUEUE.format(date=today))
    print(f"  ✅ {reviews_folder}/_queue.md")

    print(f"\n✅ Created {len(META_NOTES) + 1} meta notes")


def main() -> None:
    parser = argparse.ArgumentParser(description="Create meta notes for the vault")
    add_common_args(parser)
    args = parser.parse_args()

    config, data_dir, vault_path = resolve_paths(args)

    print(f"🧠 Second Brain Meta Note Creator")
    print(f"   Vault path: {vault_path}")
    print()

    create_meta_notes(vault_path, config)


if __name__ == "__main__":
    main()
