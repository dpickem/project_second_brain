"""
Unit Tests for Frontmatter Utilities

Tests for FrontmatterBuilder class and parsing/update functions.
"""

from __future__ import annotations

from datetime import datetime, date
from pathlib import Path

import pytest

from app.services.obsidian.frontmatter import (
    FrontmatterBuilder,
    parse_frontmatter,
    parse_frontmatter_file,
    update_frontmatter,
    frontmatter_to_string,
)


# ============================================================================
# FrontmatterBuilder Tests
# ============================================================================


class TestFrontmatterBuilder:
    """Tests for the FrontmatterBuilder class."""

    def test_empty_builder(self):
        """Empty builder returns empty dict."""
        builder = FrontmatterBuilder()
        assert builder.build() == {}

    def test_set_basic_field(self):
        """set() stores a field."""
        builder = FrontmatterBuilder()
        result = builder.set("key", "value")

        assert result is builder  # Returns self for chaining
        assert builder.build() == {"key": "value"}

    def test_set_ignores_none(self):
        """set() ignores None values."""
        builder = FrontmatterBuilder()
        builder.set("key", None)
        assert builder.build() == {}

    def test_set_type(self):
        """set_type() stores the type field."""
        builder = FrontmatterBuilder()
        builder.set_type("paper")
        assert builder.build() == {"type": "paper"}

    def test_set_title(self):
        """set_title() stores the title field."""
        builder = FrontmatterBuilder()
        builder.set_title("My Paper Title")
        assert builder.build() == {"title": "My Paper Title"}

    def test_set_authors_with_list(self):
        """set_authors() stores authors list."""
        builder = FrontmatterBuilder()
        builder.set_authors(["Alice", "Bob"])
        assert builder.build() == {"authors": ["Alice", "Bob"]}

    def test_set_authors_empty_list(self):
        """set_authors() ignores empty list."""
        builder = FrontmatterBuilder()
        builder.set_authors([])
        assert builder.build() == {}

    def test_set_tags_with_list(self):
        """set_tags() stores tags list."""
        builder = FrontmatterBuilder()
        builder.set_tags(["ai", "ml"])
        assert builder.build() == {"tags": ["ai", "ml"]}

    def test_set_tags_empty_list(self):
        """set_tags() ignores empty list."""
        builder = FrontmatterBuilder()
        builder.set_tags([])
        assert builder.build() == {}

    def test_set_date_with_datetime(self):
        """set_date() formats datetime as YYYY-MM-DD."""
        builder = FrontmatterBuilder()
        dt = datetime(2025, 1, 15, 10, 30, 0)
        builder.set_date("published", dt)
        assert builder.build() == {"published": "2025-01-15"}

    def test_set_date_with_date(self):
        """set_date() formats date as YYYY-MM-DD."""
        builder = FrontmatterBuilder()
        d = date(2025, 6, 20)
        builder.set_date("published", d)
        assert builder.build() == {"published": "2025-06-20"}

    def test_set_date_with_string(self):
        """set_date() passes through string values."""
        builder = FrontmatterBuilder()
        builder.set_date("published", "2025-01-01")
        assert builder.build() == {"published": "2025-01-01"}

    def test_set_date_with_none(self):
        """set_date() ignores None."""
        builder = FrontmatterBuilder()
        builder.set_date("published", None)
        assert builder.build() == {}

    def test_set_created_with_datetime(self):
        """set_created() stores formatted date."""
        builder = FrontmatterBuilder()
        dt = datetime(2025, 3, 10)
        builder.set_created(dt)
        assert builder.build() == {"created": "2025-03-10"}

    def test_set_created_defaults_to_now(self):
        """set_created() defaults to today's date."""
        builder = FrontmatterBuilder()
        builder.set_created()
        result = builder.build()
        assert "created" in result
        # Verify it's today's date
        assert result["created"] == datetime.now().strftime("%Y-%m-%d")

    def test_set_processed_with_datetime(self):
        """set_processed() stores formatted date."""
        builder = FrontmatterBuilder()
        dt = datetime(2025, 4, 5)
        builder.set_processed(dt)
        assert builder.build() == {"processed": "2025-04-05"}

    def test_set_processed_defaults_to_now(self):
        """set_processed() defaults to today's date."""
        builder = FrontmatterBuilder()
        builder.set_processed()
        result = builder.build()
        assert "processed" in result
        assert result["processed"] == datetime.now().strftime("%Y-%m-%d")

    def test_set_status_valid(self):
        """set_status() stores valid status values."""
        valid_statuses = [
            "unread",
            "reading",
            "read",
            "reviewed",
            "archived",
            "processed",
        ]
        for status in valid_statuses:
            builder = FrontmatterBuilder()
            builder.set_status(status)
            assert builder.build() == {"status": status}

    def test_set_status_invalid_defaults_to_unread(self):
        """set_status() defaults invalid status to 'unread'."""
        builder = FrontmatterBuilder()
        builder.set_status("invalid_status")
        assert builder.build() == {"status": "unread"}

    def test_set_source_url_only(self):
        """set_source() stores URL."""
        builder = FrontmatterBuilder()
        builder.set_source(url="https://example.com")
        assert builder.build() == {"source": "https://example.com"}

    def test_set_source_doi_only(self):
        """set_source() stores DOI."""
        builder = FrontmatterBuilder()
        builder.set_source(doi="10.1234/example")
        assert builder.build() == {"doi": "10.1234/example"}

    def test_set_source_isbn_only(self):
        """set_source() stores ISBN."""
        builder = FrontmatterBuilder()
        builder.set_source(isbn="978-3-16-148410-0")
        assert builder.build() == {"isbn": "978-3-16-148410-0"}

    def test_set_source_all_fields(self):
        """set_source() stores all source fields."""
        builder = FrontmatterBuilder()
        builder.set_source(
            url="https://example.com",
            doi="10.1234/example",
            isbn="978-3-16-148410-0",
        )
        assert builder.build() == {
            "source": "https://example.com",
            "doi": "10.1234/example",
            "isbn": "978-3-16-148410-0",
        }

    def test_set_source_none_values_ignored(self):
        """set_source() ignores None values."""
        builder = FrontmatterBuilder()
        builder.set_source(url=None, doi=None, isbn=None)
        assert builder.build() == {}

    def test_set_domain(self):
        """set_domain() stores domain field."""
        builder = FrontmatterBuilder()
        builder.set_domain("machine-learning")
        assert builder.build() == {"domain": "machine-learning"}

    def test_set_complexity_valid(self):
        """set_complexity() stores valid complexity levels."""
        valid_levels = ["foundational", "intermediate", "advanced"]
        for level in valid_levels:
            builder = FrontmatterBuilder()
            builder.set_complexity(level)
            assert builder.build() == {"complexity": level}

    def test_set_complexity_invalid_ignored(self):
        """set_complexity() ignores invalid values."""
        builder = FrontmatterBuilder()
        builder.set_complexity("expert")  # Not valid
        assert builder.build() == {}

    def test_set_custom_single_field(self):
        """set_custom() stores custom fields."""
        builder = FrontmatterBuilder()
        builder.set_custom(rating=5)
        assert builder.build() == {"rating": 5}

    def test_set_custom_multiple_fields(self):
        """set_custom() stores multiple custom fields."""
        builder = FrontmatterBuilder()
        builder.set_custom(rating=5, priority="high", reviewed=True)
        assert builder.build() == {"rating": 5, "priority": "high", "reviewed": True}

    def test_set_custom_ignores_none(self):
        """set_custom() ignores None values."""
        builder = FrontmatterBuilder()
        builder.set_custom(rating=5, priority=None)
        assert builder.build() == {"rating": 5}

    def test_method_chaining(self):
        """Builder supports method chaining."""
        builder = FrontmatterBuilder()
        result = (
            builder.set_type("paper")
            .set_title("Test Paper")
            .set_tags(["ai", "ml"])
            .set_status("unread")
            .set_domain("machine-learning")
            .set_complexity("advanced")
        )

        assert result is builder
        assert builder.build() == {
            "type": "paper",
            "title": "Test Paper",
            "tags": ["ai", "ml"],
            "status": "unread",
            "domain": "machine-learning",
            "complexity": "advanced",
        }

    def test_build_returns_copy(self):
        """build() returns a copy, not the internal dict."""
        builder = FrontmatterBuilder()
        builder.set("key", "value")
        result1 = builder.build()
        result2 = builder.build()

        # Modifying result1 shouldn't affect result2 or builder
        result1["key"] = "modified"
        assert result2["key"] == "value"
        assert builder.build()["key"] == "value"

    def test_to_yaml(self):
        """to_yaml() produces valid YAML string."""
        builder = FrontmatterBuilder()
        builder.set_type("paper").set_title("Test")
        yaml_str = builder.to_yaml()

        assert "type: paper" in yaml_str
        assert "title: Test" in yaml_str

    def test_to_frontmatter(self):
        """to_frontmatter() produces complete frontmatter block."""
        builder = FrontmatterBuilder()
        builder.set_type("paper").set_title("Test")
        fm = builder.to_frontmatter()

        assert fm.startswith("---\n")
        assert fm.endswith("---\n")
        assert "type: paper" in fm
        assert "title: Test" in fm

    def test_to_frontmatter_empty(self):
        """to_frontmatter() returns empty string for empty builder."""
        builder = FrontmatterBuilder()
        assert builder.to_frontmatter() == ""


# ============================================================================
# Parse Frontmatter Tests
# ============================================================================


class TestParseFrontmatter:
    """Tests for parse_frontmatter function."""

    @pytest.mark.asyncio
    async def test_parse_basic_frontmatter(self):
        """Parses basic YAML frontmatter."""
        content = """---
type: paper
title: Test Paper
---

# Content here
"""
        metadata, body = await parse_frontmatter(content)

        assert metadata == {"type": "paper", "title": "Test Paper"}
        assert "# Content here" in body

    @pytest.mark.asyncio
    async def test_parse_frontmatter_with_lists(self):
        """Parses frontmatter containing lists."""
        content = """---
tags:
  - ai
  - ml
authors:
  - Alice
  - Bob
---

Body content
"""
        metadata, body = await parse_frontmatter(content)

        assert metadata["tags"] == ["ai", "ml"]
        assert metadata["authors"] == ["Alice", "Bob"]
        assert "Body content" in body

    @pytest.mark.asyncio
    async def test_parse_frontmatter_empty_metadata(self):
        """Handles content without frontmatter."""
        content = """# Just a heading

Some content without frontmatter.
"""
        metadata, body = await parse_frontmatter(content)

        assert metadata == {}
        assert "# Just a heading" in body

    @pytest.mark.asyncio
    async def test_parse_frontmatter_complex_values(self):
        """Parses frontmatter with complex/nested values."""
        content = """---
type: paper
rating: 5
verified: true
metadata:
  source: arxiv
  id: "12345"
---

Content
"""
        metadata, body = await parse_frontmatter(content)

        assert metadata["type"] == "paper"
        assert metadata["rating"] == 5
        assert metadata["verified"] is True
        assert metadata["metadata"] == {"source": "arxiv", "id": "12345"}


# ============================================================================
# Parse Frontmatter File Tests
# ============================================================================


class TestParseFrontmatterFile:
    """Tests for parse_frontmatter_file function."""

    @pytest.mark.asyncio
    async def test_parse_file(self, tmp_path: Path):
        """Parses frontmatter from a file."""
        file_path = tmp_path / "test.md"
        file_path.write_text(
            """---
type: article
title: Test Article
---

Article content here.
"""
        )

        metadata, body = await parse_frontmatter_file(file_path)

        assert metadata == {"type": "article", "title": "Test Article"}
        assert "Article content here." in body

    @pytest.mark.asyncio
    async def test_parse_file_utf8(self, tmp_path: Path):
        """Parses frontmatter with UTF-8 characters."""
        file_path = tmp_path / "test.md"
        file_path.write_text(
            """---
type: paper
title: "Análisis de datos con émojis 🎉"
---

Content with unicode: café, naïve, 日本語
""",
            encoding="utf-8",
        )

        metadata, body = await parse_frontmatter_file(file_path)

        assert metadata["title"] == "Análisis de datos con émojis 🎉"
        assert "café" in body


# ============================================================================
# Update Frontmatter Tests
# ============================================================================


class TestUpdateFrontmatter:
    """Tests for update_frontmatter function."""

    @pytest.mark.asyncio
    async def test_update_existing_field(self, tmp_path: Path):
        """Updates an existing field."""
        file_path = tmp_path / "test.md"
        file_path.write_text(
            """---
type: paper
status: unread
---

Content
"""
        )

        await update_frontmatter(file_path, {"status": "read"})

        metadata, _ = await parse_frontmatter_file(file_path)
        assert metadata["status"] == "read"
        assert metadata["type"] == "paper"  # Unchanged

    @pytest.mark.asyncio
    async def test_add_new_field(self, tmp_path: Path):
        """Adds a new field to frontmatter."""
        file_path = tmp_path / "test.md"
        file_path.write_text(
            """---
type: paper
---

Content
"""
        )

        await update_frontmatter(file_path, {"rating": 5})

        metadata, _ = await parse_frontmatter_file(file_path)
        assert metadata["rating"] == 5
        assert metadata["type"] == "paper"

    @pytest.mark.asyncio
    async def test_remove_field(self, tmp_path: Path):
        """Removes specified fields from frontmatter."""
        file_path = tmp_path / "test.md"
        file_path.write_text(
            """---
type: paper
status: unread
temp_field: to_remove
---

Content
"""
        )

        await update_frontmatter(file_path, {}, remove_keys=["temp_field"])

        metadata, _ = await parse_frontmatter_file(file_path)
        assert "temp_field" not in metadata
        assert metadata["type"] == "paper"
        assert metadata["status"] == "unread"

    @pytest.mark.asyncio
    async def test_update_and_remove(self, tmp_path: Path):
        """Updates and removes fields in one call."""
        file_path = tmp_path / "test.md"
        file_path.write_text(
            """---
type: paper
status: unread
temp: remove_me
---

Content
"""
        )

        await update_frontmatter(
            file_path, {"status": "read", "rating": 5}, remove_keys=["temp"]
        )

        metadata, _ = await parse_frontmatter_file(file_path)
        assert metadata["status"] == "read"
        assert metadata["rating"] == 5
        assert "temp" not in metadata

    @pytest.mark.asyncio
    async def test_update_preserves_body(self, tmp_path: Path):
        """Body content is preserved when updating frontmatter."""
        file_path = tmp_path / "test.md"
        original_body = """# Important Content

This should not change!

- Item 1
- Item 2
"""
        file_path.write_text(
            f"""---
type: paper
---
{original_body}"""
        )

        await update_frontmatter(file_path, {"status": "read"})

        _, body = await parse_frontmatter_file(file_path)
        assert "# Important Content" in body
        assert "This should not change!" in body
        assert "- Item 1" in body

    @pytest.mark.asyncio
    async def test_update_ignores_none_values(self, tmp_path: Path):
        """None values in updates dict are ignored."""
        file_path = tmp_path / "test.md"
        file_path.write_text(
            """---
type: paper
status: unread
---

Content
"""
        )

        await update_frontmatter(file_path, {"status": "read", "rating": None})

        metadata, _ = await parse_frontmatter_file(file_path)
        assert metadata["status"] == "read"
        assert "rating" not in metadata


# ============================================================================
# Frontmatter to String Tests
# ============================================================================


class TestFrontmatterToString:
    """Tests for frontmatter_to_string function."""

    def test_basic_conversion(self):
        """Converts metadata and content to markdown string."""
        metadata = {"type": "paper", "title": "Test"}
        content = "# Body content\n\nParagraph here."

        result = frontmatter_to_string(metadata, content)

        assert "---" in result
        assert "type: paper" in result
        assert "title: Test" in result
        assert "# Body content" in result
        assert "Paragraph here." in result

    def test_empty_metadata(self):
        """Handles empty metadata."""
        result = frontmatter_to_string({}, "Just content")

        assert "---" in result
        assert "Just content" in result

    def test_complex_metadata(self):
        """Handles complex metadata values."""
        metadata = {
            "type": "paper",
            "tags": ["ai", "ml"],
            "authors": ["Alice", "Bob"],
        }
        content = "Content"

        result = frontmatter_to_string(metadata, content)

        assert "type: paper" in result
        assert "Content" in result


# ============================================================================
# Integration Tests
# ============================================================================


class TestFrontmatterIntegration:
    """Integration tests combining builder and parsing."""

    @pytest.mark.asyncio
    async def test_build_and_parse_roundtrip(self):
        """Built frontmatter can be parsed back correctly."""
        builder = FrontmatterBuilder()
        builder.set_type("paper").set_title("Roundtrip Test").set_tags(
            ["test", "roundtrip"]
        ).set_status("unread")

        frontmatter_block = builder.to_frontmatter()
        full_content = frontmatter_block + "\n# Content\n\nBody text here."

        metadata, body = await parse_frontmatter(full_content)

        assert metadata["type"] == "paper"
        assert metadata["title"] == "Roundtrip Test"
        assert metadata["tags"] == ["test", "roundtrip"]
        assert metadata["status"] == "unread"
        assert "# Content" in body

    @pytest.mark.asyncio
    async def test_full_workflow(self, tmp_path: Path):
        """Complete workflow: build, write, read, update, verify."""
        file_path = tmp_path / "workflow_test.md"

        # Build and write
        builder = FrontmatterBuilder()
        builder.set_type("article").set_title("Workflow Test").set_status("unread")

        content = builder.to_frontmatter() + "\n# Article\n\nGreat content."
        file_path.write_text(content)

        # Read and verify initial state
        metadata, body = await parse_frontmatter_file(file_path)
        assert metadata["status"] == "unread"

        # Update
        await update_frontmatter(file_path, {"status": "read", "rating": 5})

        # Verify final state
        metadata, body = await parse_frontmatter_file(file_path)
        assert metadata["status"] == "read"
        assert metadata["rating"] == 5
        assert metadata["type"] == "article"
        assert "# Article" in body
