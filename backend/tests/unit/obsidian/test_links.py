"""
Unit Tests for Wikilink Utilities

Tests for WikilinkBuilder, link extraction, tag extraction,
auto-linking, and validation functions.
"""

from __future__ import annotations

import pytest

from app.services.obsidian.links import (
    WikilinkBuilder,
    extract_wikilinks,
    extract_tags,
    generate_connection_section,
    auto_link_concepts,
    validate_links,
    create_backlink_section,
)


# ============================================================================
# WikilinkBuilder Tests
# ============================================================================


class TestWikilinkBuilder:
    """Tests for WikilinkBuilder static methods."""

    def test_link_basic(self):
        """Create a basic wikilink."""
        result = WikilinkBuilder.link("Machine Learning")
        assert result == "[[Machine Learning]]"

    def test_link_with_alias(self):
        """Create a wikilink with alias."""
        result = WikilinkBuilder.link("Machine Learning", "ML")
        assert result == "[[Machine Learning|ML]]"

    def test_link_empty_alias_ignored(self):
        """Empty alias string is treated as no alias (falsy value)."""
        result = WikilinkBuilder.link("Note", "")
        assert result == "[[Note]]"  # Empty string is falsy, so no alias

    def test_link_none_alias_ignored(self):
        """None alias creates basic link."""
        result = WikilinkBuilder.link("Note", None)
        assert result == "[[Note]]"

    def test_link_with_path(self):
        """Create a wikilink with folder path."""
        result = WikilinkBuilder.link("sources/papers/Smith2023")
        assert result == "[[sources/papers/Smith2023]]"

    def test_header_link_basic(self):
        """Create a header link."""
        result = WikilinkBuilder.header_link("Python", "Installation")
        assert result == "[[Python#Installation]]"

    def test_header_link_with_alias(self):
        """Create a header link with alias."""
        result = WikilinkBuilder.header_link("API Docs", "Auth", "login")
        assert result == "[[API Docs#Auth|login]]"

    def test_block_link_basic(self):
        """Create a block link."""
        result = WikilinkBuilder.block_link("Research Notes", "key-finding")
        assert result == "[[Research Notes#^key-finding]]"

    def test_block_link_with_alias(self):
        """Create a block link with alias."""
        result = WikilinkBuilder.block_link("Notes", "abc123", "see here")
        assert result == "[[Notes#^abc123|see here]]"

    def test_embed_note(self):
        """Create an embedded note link."""
        result = WikilinkBuilder.embed("Summary")
        assert result == "![[Summary]]"

    def test_embed_image(self):
        """Create an embedded image link."""
        result = WikilinkBuilder.embed("diagram.png")
        assert result == "![[diagram.png]]"

    def test_embed_section(self):
        """Create an embedded section link."""
        result = WikilinkBuilder.embed("Note#Section")
        assert result == "![[Note#Section]]"


# ============================================================================
# Extract Wikilinks Tests
# ============================================================================


class TestExtractWikilinks:
    """Tests for extract_wikilinks function."""

    def test_extract_single_link(self):
        """Extract a single wikilink."""
        content = "See [[Machine Learning]] for details."
        result = extract_wikilinks(content)
        assert result == ["Machine Learning"]

    def test_extract_multiple_links(self):
        """Extract multiple wikilinks."""
        content = "Check [[Python]] and [[JavaScript]] examples."
        result = extract_wikilinks(content)
        assert result == ["Python", "JavaScript"]

    def test_extract_aliased_link(self):
        """Extract target from aliased link."""
        content = "See [[Machine Learning|ML]] for details."
        result = extract_wikilinks(content)
        assert result == ["Machine Learning"]

    def test_extract_header_link(self):
        """Extract base note from header link."""
        content = "See [[Paper#Methods]] for methodology."
        result = extract_wikilinks(content)
        assert result == ["Paper"]

    def test_extract_block_link(self):
        """Extract base note from block link."""
        content = "Check [[Notes#^abc123]] for the quote."
        result = extract_wikilinks(content)
        assert result == ["Notes"]

    def test_extract_removes_duplicates(self):
        """Duplicates are removed, order preserved."""
        content = "See [[ML]] here and [[ML]] there."
        result = extract_wikilinks(content)
        assert result == ["ML"]

    def test_extract_preserves_order(self):
        """Links returned in order of first appearance."""
        content = "First [[A]], then [[B]], back to [[A]]."
        result = extract_wikilinks(content)
        assert result == ["A", "B"]

    def test_extract_from_embed(self):
        """Extract note from embed syntax."""
        content = "![[Summary]] is embedded here."
        result = extract_wikilinks(content)
        assert result == ["Summary"]

    def test_extract_empty_content(self):
        """Empty content returns empty list."""
        result = extract_wikilinks("")
        assert result == []

    def test_extract_no_links(self):
        """Content without links returns empty list."""
        result = extract_wikilinks("Just plain text here.")
        assert result == []

    def test_extract_multiline(self):
        """Extract links from multiline content."""
        content = """# Title
        
See [[First Note]] for background.

Then check [[Second Note]] for details.
"""
        result = extract_wikilinks(content)
        assert result == ["First Note", "Second Note"]


# ============================================================================
# Extract Tags Tests
# ============================================================================


class TestExtractTags:
    """Tests for extract_tags function."""

    def test_extract_single_tag(self):
        """Extract a single inline tag."""
        content = "This is about #machinelearning"
        result = extract_tags(content)
        assert result == ["machinelearning"]

    def test_extract_multiple_tags(self):
        """Extract multiple tags."""
        content = "Topics: #ai and #ml"
        result = extract_tags(content)
        assert set(result) == {"ai", "ml"}

    def test_extract_hierarchical_tag(self):
        """Extract hierarchical tags."""
        content = "Related to #ai/deep-learning/transformers"
        result = extract_tags(content)
        assert result == ["ai/deep-learning/transformers"]

    def test_extract_tag_with_hyphen(self):
        """Tags can contain hyphens."""
        content = "Using #machine-learning techniques"
        result = extract_tags(content)
        assert result == ["machine-learning"]

    def test_extract_ignores_headers(self):
        """Markdown headers (##) are not tags."""
        content = "## This is a header"
        result = extract_tags(content)
        assert result == []

    def test_extract_tag_after_header(self):
        """Tag after header marker is extracted."""
        content = "## Header with #tag"
        result = extract_tags(content)
        assert result == ["tag"]

    def test_extract_removes_duplicates(self):
        """Duplicate tags are removed."""
        content = "See #ai here and #ai there."
        result = extract_tags(content)
        assert result == ["ai"]

    def test_extract_tag_must_start_with_letter(self):
        """Tags must start with a letter."""
        content = "#123 is not a tag"
        result = extract_tags(content)
        assert result == []

    def test_extract_empty_content(self):
        """Empty content returns empty list."""
        result = extract_tags("")
        assert result == []

    def test_extract_no_tags(self):
        """Content without tags returns empty list."""
        result = extract_tags("Just plain text.")
        assert result == []

    def test_extract_multiline(self):
        """Extract tags from multiline content."""
        content = """# Notes
        
Learning about #ai

Specifically #deep-learning
"""
        result = extract_tags(content)
        assert set(result) == {"ai", "deep-learning"}


# ============================================================================
# Generate Connection Section Tests
# ============================================================================


class TestGenerateConnectionSection:
    """Tests for generate_connection_section function."""

    def test_generate_empty_connections(self):
        """Empty connections returns placeholder."""
        result = generate_connection_section([])
        assert result == "*No connections found*"

    def test_generate_single_connection(self):
        """Generate section with one connection."""
        connections = [{"target_title": "Machine Learning"}]
        result = generate_connection_section(connections)
        assert "[[Machine Learning]]" in result
        assert "RELATES_TO" in result

    def test_generate_with_explanation(self):
        """Connection with explanation uses em-dash format."""
        connections = [
            {
                "target_title": "Neural Networks",
                "explanation": "Foundational concepts for this paper",
            }
        ]
        result = generate_connection_section(connections)
        assert "[[Neural Networks]]" in result
        assert "Foundational concepts" in result
        assert "—" in result  # Em-dash

    def test_generate_with_relationship_type(self):
        """Connection without explanation shows relationship type."""
        connections = [
            {
                "target_title": "Python",
                "relationship_type": "EXTENDS",
            }
        ]
        result = generate_connection_section(connections)
        assert "[[Python]]" in result
        assert "(EXTENDS)" in result

    def test_generate_multiple_connections(self):
        """Generate section with multiple connections."""
        connections = [
            {"target_title": "A", "explanation": "First link"},
            {"target_title": "B", "relationship_type": "EXTENDS"},
            {"target_title": "C"},
        ]
        result = generate_connection_section(connections)
        lines = result.split("\n")
        assert len(lines) == 3
        assert "[[A]]" in lines[0]
        assert "[[B]]" in lines[1]
        assert "[[C]]" in lines[2]


# ============================================================================
# Auto Link Concepts Tests
# ============================================================================


class TestAutoLinkConcepts:
    """Tests for auto_link_concepts function."""

    def test_auto_link_single_concept(self):
        """Single concept is linked."""
        content = "Machine learning is useful."
        concepts = ["Machine learning"]
        result = auto_link_concepts(content, concepts)
        assert result == "[[Machine learning]] is useful."

    def test_auto_link_case_insensitive(self):
        """Linking is case-insensitive."""
        content = "MACHINE LEARNING is useful."
        concepts = ["Machine Learning"]
        result = auto_link_concepts(content, concepts)
        assert "[[MACHINE LEARNING]]" in result

    def test_auto_link_multiple_concepts(self):
        """Multiple concepts are linked."""
        content = "Neural networks use backpropagation."
        concepts = ["Neural networks", "Backpropagation"]
        result = auto_link_concepts(content, concepts)
        assert "[[Neural networks]]" in result
        assert "[[backpropagation]]" in result.lower()

    def test_auto_link_longest_first(self):
        """Longer concepts matched first to prevent partial matches."""
        content = "Machine learning algorithms"
        concepts = ["Machine", "Machine learning"]
        result = auto_link_concepts(content, concepts)
        assert "[[Machine learning]]" in result
        # "Machine" alone should not be linked separately
        assert result.count("[[") == 1

    def test_auto_link_word_boundaries(self):
        """Only whole words are matched."""
        content = "Unlearning is different from learning."
        concepts = ["learning"]
        result = auto_link_concepts(content, concepts)
        assert "[[learning]]" in result
        assert "Unlearning" in result  # Not [[Un]][[learning]]

    def test_auto_link_skip_already_linked(self):
        """Already linked text is not re-linked."""
        content = "See [[Machine Learning]] for more."
        concepts = ["Machine Learning"]
        result = auto_link_concepts(content, concepts)
        # Should remain as is, not double-linked
        assert result.count("[[Machine Learning]]") == 1

    def test_auto_link_empty_concepts(self):
        """Empty concept list returns unchanged content."""
        content = "Some content here."
        result = auto_link_concepts(content, [])
        assert result == content

    def test_auto_link_handles_empty_concept(self):
        """Empty string in concepts is skipped."""
        content = "Some content here."
        concepts = ["", "content"]
        result = auto_link_concepts(content, concepts)
        assert "[[content]]" in result

    def test_auto_link_preserves_formatting(self):
        """Preserves markdown formatting."""
        content = "# Header\n\nMachine learning is *important*."
        concepts = ["Machine learning"]
        result = auto_link_concepts(content, concepts)
        assert "# Header" in result
        assert "*important*" in result


# ============================================================================
# Validate Links Tests
# ============================================================================


class TestValidateLinks:
    """Tests for validate_links function."""

    def test_validate_no_broken_links(self):
        """All links exist - no broken links."""
        content = "See [[Python]] and [[JavaScript]]."
        vault_notes = {"Python", "JavaScript"}
        result = validate_links(content, vault_notes)
        assert result == []

    def test_validate_finds_broken_link(self):
        """Missing link is identified."""
        content = "See [[Python]] and [[Rust]]."
        vault_notes = {"Python"}
        result = validate_links(content, vault_notes)
        assert result == ["Rust"]

    def test_validate_multiple_broken_links(self):
        """Multiple missing links are identified."""
        content = "See [[A]], [[B]], and [[C]]."
        vault_notes = {"B"}
        result = validate_links(content, vault_notes)
        assert set(result) == {"A", "C"}

    def test_validate_empty_content(self):
        """Empty content has no broken links."""
        result = validate_links("", {"Python"})
        assert result == []

    def test_validate_no_links(self):
        """Content without links has no broken links."""
        result = validate_links("Plain text.", {"Python"})
        assert result == []

    def test_validate_empty_vault(self):
        """All links broken if vault is empty."""
        content = "See [[Python]]."
        result = validate_links(content, set())
        assert result == ["Python"]


# ============================================================================
# Create Backlink Section Tests
# ============================================================================


class TestCreateBacklinkSection:
    """Tests for create_backlink_section function."""

    def test_create_empty_backlinks(self):
        """Empty backlinks returns placeholder."""
        result = create_backlink_section([])
        assert result == "*No backlinks found*"

    def test_create_single_backlink(self):
        """Generate section with one backlink."""
        backlinks = [{"title": "Machine Learning"}]
        result = create_backlink_section(backlinks)
        assert "[[Machine Learning]]" in result

    def test_create_backlink_with_context(self):
        """Backlink with context includes quote."""
        backlinks = [
            {
                "title": "ML Guide",
                "context": "References this concept in the intro",
            }
        ]
        result = create_backlink_section(backlinks)
        assert "[[ML Guide]]" in result
        assert "References this concept" in result

    def test_create_multiple_backlinks(self):
        """Generate section with multiple backlinks."""
        backlinks = [
            {"title": "Note A"},
            {"title": "Note B", "context": "Some context"},
            {"title": "Note C"},
        ]
        result = create_backlink_section(backlinks)
        lines = result.split("\n")
        assert len(lines) == 3
        assert "[[Note A]]" in lines[0]
        assert "[[Note B]]" in lines[1]
        assert "Some context" in lines[1]
        assert "[[Note C]]" in lines[2]
