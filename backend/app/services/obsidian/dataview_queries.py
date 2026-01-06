"""
Dataview Query Library

Collection of pre-built Dataview queries for Obsidian notes.
These queries power dynamic dashboards and help users
get immediate value from their vault.
"""


class DataviewLibrary:
    """Collection of useful Dataview queries."""

    @staticmethod
    def recent_notes(folder: str = "sources", limit: int = 10) -> str:
        """Query for recent notes in a folder."""
        return f'''```dataview
TABLE title as "Title", tags as "Tags", processed as "Processed"
FROM "{folder}"
WHERE processed
SORT processed DESC
LIMIT {limit}
```'''

    @staticmethod
    def unread_by_type(content_type: str) -> str:
        """Query for unread notes of a specific type."""
        return f'''```dataview
LIST
FROM "sources"
WHERE type = "{content_type}" AND (status = "unread" OR !status)
SORT created DESC
```'''

    @staticmethod
    def open_tasks() -> str:
        """Query for all incomplete tasks across vault."""
        return '''```dataview
TASK
FROM "sources" OR "concepts"
WHERE !completed
GROUP BY file.link
LIMIT 50
```'''

    @staticmethod
    def knowledge_stats() -> str:
        """Query for note counts by type."""
        return '''```dataview
TABLE WITHOUT ID
  type as "Type",
  length(rows) as "Count"
FROM "sources"
GROUP BY type
SORT length(rows) DESC
```'''

    @staticmethod
    def notes_by_domain(domain: str) -> str:
        """Query for notes in a specific domain."""
        return f'''```dataview
TABLE title as "Title", complexity as "Level", processed as "Date"
FROM "sources"
WHERE domain = "{domain}"
SORT processed DESC
```'''

    @staticmethod
    def mastery_questions() -> str:
        """Query for notes with mastery questions."""
        return '''```dataview
LIST
FROM "sources"
WHERE contains(file.content, "## Mastery Questions")
SORT processed DESC
LIMIT 20
```'''

    @staticmethod
    def concepts_index() -> str:
        """Query for all concept notes."""
        return '''```dataview
TABLE WITHOUT ID
  file.link as "Concept",
  domain as "Domain",
  complexity as "Level"
FROM "concepts"
SORT file.name ASC
```'''

    @staticmethod
    def due_for_review() -> str:
        """Query for notes due for spaced repetition review."""
        return '''```dataview
TABLE title as "Title", type as "Type", last_reviewed as "Last Reviewed"
FROM "sources" OR "concepts"
WHERE next_review <= date(today)
SORT next_review ASC
LIMIT 20
```'''

    @staticmethod
    def recently_created(days: int = 7) -> str:
        """Query for recently created notes."""
        return f'''```dataview
TABLE title as "Title", type as "Type", created as "Created"
FROM "sources"
WHERE created >= date(today) - dur({days} days)
SORT created DESC
```'''

    @staticmethod
    def notes_with_follow_ups() -> str:
        """Query for notes that have follow-up tasks."""
        return '''```dataview
LIST
FROM "sources"
WHERE contains(file.content, "## Follow-up Tasks")
SORT processed DESC
LIMIT 20
```'''


def generate_dashboard_queries() -> dict[str, str]:
    """Generate all queries needed for the main dashboard."""
    return {
        "recent": DataviewLibrary.recent_notes(limit=10),
        "unread_papers": DataviewLibrary.unread_by_type("paper"),
        "unread_articles": DataviewLibrary.unread_by_type("article"),
        "tasks": DataviewLibrary.open_tasks(),
        "stats": DataviewLibrary.knowledge_stats(),
        "concepts": DataviewLibrary.concepts_index(),
        "due_review": DataviewLibrary.due_for_review(),
        "follow_ups": DataviewLibrary.notes_with_follow_ups(),
    }

