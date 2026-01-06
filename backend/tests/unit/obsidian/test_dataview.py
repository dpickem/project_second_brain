"""
Unit Tests for Dataview Query Library

Tests for the DataviewLibrary class which provides pre-built
Dataview queries for Obsidian dashboards.
"""

from __future__ import annotations

import pytest

from app.services.obsidian.dataview_queries import (
    DataviewLibrary,
    generate_dashboard_queries,
)


# ============================================================================
# DataviewLibrary Tests
# ============================================================================


class TestDataviewLibraryRecentNotes:
    """Tests for recent_notes query."""

    def test_recent_notes_default(self):
        """recent_notes with defaults."""
        result = DataviewLibrary.recent_notes()
        assert "```dataview" in result
        assert 'FROM "sources"' in result
        assert "SORT processed DESC" in result
        assert "LIMIT 10" in result

    def test_recent_notes_custom_folder(self):
        """recent_notes with custom folder."""
        result = DataviewLibrary.recent_notes(folder="concepts")
        assert 'FROM "concepts"' in result

    def test_recent_notes_custom_limit(self):
        """recent_notes with custom limit."""
        result = DataviewLibrary.recent_notes(limit=25)
        assert "LIMIT 25" in result


class TestDataviewLibraryUnreadByType:
    """Tests for unread_by_type query."""

    def test_unread_by_type(self):
        """unread_by_type generates correct query."""
        result = DataviewLibrary.unread_by_type("paper")
        assert "```dataview" in result
        assert 'type = "paper"' in result
        assert 'status = "unread"' in result

    def test_unread_by_type_article(self):
        """unread_by_type for article type."""
        result = DataviewLibrary.unread_by_type("article")
        assert 'type = "article"' in result


class TestDataviewLibraryOpenTasks:
    """Tests for open_tasks query."""

    def test_open_tasks(self):
        """open_tasks generates correct query."""
        result = DataviewLibrary.open_tasks()
        assert "```dataview" in result
        assert "TASK" in result
        assert "!completed" in result
        assert "GROUP BY file.link" in result
        assert "LIMIT 50" in result


class TestDataviewLibraryKnowledgeStats:
    """Tests for knowledge_stats query."""

    def test_knowledge_stats(self):
        """knowledge_stats generates correct query."""
        result = DataviewLibrary.knowledge_stats()
        assert "```dataview" in result
        assert "TABLE WITHOUT ID" in result
        assert "GROUP BY type" in result
        assert "length(rows)" in result


class TestDataviewLibraryNotesByDomain:
    """Tests for notes_by_domain query."""

    def test_notes_by_domain(self):
        """notes_by_domain generates correct query."""
        result = DataviewLibrary.notes_by_domain("machine-learning")
        assert "```dataview" in result
        assert 'domain = "machine-learning"' in result
        assert "SORT processed DESC" in result


class TestDataviewLibraryMasteryQuestions:
    """Tests for mastery_questions query."""

    def test_mastery_questions(self):
        """mastery_questions generates correct query."""
        result = DataviewLibrary.mastery_questions()
        assert "```dataview" in result
        assert 'contains(file.content, "## Mastery Questions")' in result
        assert "LIMIT 20" in result


class TestDataviewLibraryConceptsIndex:
    """Tests for concepts_index query."""

    def test_concepts_index(self):
        """concepts_index generates correct query."""
        result = DataviewLibrary.concepts_index()
        assert "```dataview" in result
        assert 'FROM "concepts"' in result
        assert "file.link" in result
        assert "SORT file.name ASC" in result


class TestDataviewLibraryDueForReview:
    """Tests for due_for_review query."""

    def test_due_for_review(self):
        """due_for_review generates correct query."""
        result = DataviewLibrary.due_for_review()
        assert "```dataview" in result
        assert "next_review <= date(today)" in result
        assert "SORT next_review ASC" in result
        assert "LIMIT 20" in result


class TestDataviewLibraryRecentlyCreated:
    """Tests for recently_created query."""

    def test_recently_created_default(self):
        """recently_created with default 7 days."""
        result = DataviewLibrary.recently_created()
        assert "```dataview" in result
        assert "dur(7 days)" in result
        assert "SORT created DESC" in result

    def test_recently_created_custom_days(self):
        """recently_created with custom days."""
        result = DataviewLibrary.recently_created(days=30)
        assert "dur(30 days)" in result


class TestDataviewLibraryNotesWithFollowUps:
    """Tests for notes_with_follow_ups query."""

    def test_notes_with_follow_ups(self):
        """notes_with_follow_ups generates correct query."""
        result = DataviewLibrary.notes_with_follow_ups()
        assert "```dataview" in result
        assert 'contains(file.content, "## Follow-up Tasks")' in result
        assert "LIMIT 20" in result


# ============================================================================
# Generate Dashboard Queries Tests
# ============================================================================


class TestGenerateDashboardQueries:
    """Tests for generate_dashboard_queries function."""

    def test_returns_dict(self):
        """Returns a dictionary of queries."""
        result = generate_dashboard_queries()
        assert isinstance(result, dict)

    def test_contains_required_keys(self):
        """Contains all expected dashboard sections."""
        result = generate_dashboard_queries()
        expected_keys = [
            "recent",
            "unread_papers",
            "unread_articles",
            "tasks",
            "stats",
            "concepts",
            "due_review",
            "follow_ups",
        ]
        for key in expected_keys:
            assert key in result

    def test_all_values_are_dataview_queries(self):
        """All values are valid Dataview queries."""
        result = generate_dashboard_queries()
        for key, query in result.items():
            assert "```dataview" in query, f"{key} is not a dataview query"

    def test_queries_are_unique(self):
        """Queries are different from each other."""
        result = generate_dashboard_queries()
        queries = list(result.values())
        # Should have no duplicates
        assert len(queries) == len(set(queries))


# ============================================================================
# Query Syntax Tests
# ============================================================================


class TestQuerySyntax:
    """Tests for query syntax correctness."""

    def test_queries_properly_closed(self):
        """All queries have closing backticks."""
        queries = [
            DataviewLibrary.recent_notes(),
            DataviewLibrary.unread_by_type("paper"),
            DataviewLibrary.open_tasks(),
            DataviewLibrary.knowledge_stats(),
            DataviewLibrary.notes_by_domain("ai"),
            DataviewLibrary.mastery_questions(),
            DataviewLibrary.concepts_index(),
            DataviewLibrary.due_for_review(),
            DataviewLibrary.recently_created(),
            DataviewLibrary.notes_with_follow_ups(),
        ]
        for query in queries:
            assert (
                query.count("```") == 2
            ), f"Query has mismatched backticks: {query[:50]}"

    def test_queries_use_correct_list_or_table(self):
        """Queries use appropriate output format."""
        # TABLE queries
        table_queries = [
            DataviewLibrary.recent_notes(),
            DataviewLibrary.knowledge_stats(),
            DataviewLibrary.notes_by_domain("ai"),
            DataviewLibrary.concepts_index(),
            DataviewLibrary.due_for_review(),
            DataviewLibrary.recently_created(),
        ]
        for query in table_queries:
            assert "TABLE" in query

        # LIST queries
        list_queries = [
            DataviewLibrary.unread_by_type("paper"),
            DataviewLibrary.mastery_questions(),
            DataviewLibrary.notes_with_follow_ups(),
        ]
        for query in list_queries:
            assert "LIST" in query

        # TASK query
        assert "TASK" in DataviewLibrary.open_tasks()
