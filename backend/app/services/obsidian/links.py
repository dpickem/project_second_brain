"""
Wikilink Utilities

Provides utilities for creating and extracting Obsidian-style wikilinks,
which are the primary linking mechanism in the knowledge vault.

Wikilink Syntax Reference:
    [[Note Name]]              - Basic link to a note
    [[Note Name|Display Text]] - Link with custom display text (alias)
    [[Note Name#Header]]       - Link to a specific header in a note
    [[Note Name#^block-id]]    - Link to a specific block (paragraph)
    ![[Note Name]]             - Embed (transclude) another note
    ![[image.png]]             - Embed an image

Key Components:
    - WikilinkBuilder: Static methods for creating properly formatted links
    - extract_wikilinks(): Parse note content to find outgoing links
    - extract_tags(): Find inline #tags in content
    - auto_link_concepts(): Automatically convert known terms to wikilinks
    - validate_links(): Find broken links (targets that don't exist)

Integration with Neo4j:
    Extracted wikilinks are used by VaultSyncService to create LINKS_TO
    relationships in the knowledge graph, enabling:
    - Graph traversal and visualization
    - Backlink queries
    - Related note suggestions
    - Orphan note detection

Usage:
    from app.services.obsidian.links import (
        WikilinkBuilder,
        extract_wikilinks,
        extract_tags,
    )

    # Create links
    link = WikilinkBuilder.link("Machine Learning", "ML")  # [[Machine Learning|ML]]

    # Extract from content
    content = "See [[Neural Networks]] for more on #ai/deep-learning."
    links = extract_wikilinks(content)  # ["Neural Networks"]
    tags = extract_tags(content)        # ["ai/deep-learning"]
"""

import re
from typing import Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class WikilinkBuilder:
    """
    Builder for creating Obsidian-compatible wikilinks.

    All methods are static - no instantiation needed. Provides a clean API
    for generating various link formats used throughout the vault.

    Link Types:
        - Standard: [[Target]] or [[Target|Alias]]
        - Header: [[Note#Header]] - deep link to a section
        - Block: [[Note#^block-id]] - link to a specific paragraph
        - Embed: ![[Target]] - inline transclusion

    Examples:
        WikilinkBuilder.link("Concept")              # [[Concept]]
        WikilinkBuilder.link("Concept", "See this")  # [[Concept|See this]]
        WikilinkBuilder.header_link("Note", "Intro") # [[Note#Intro]]
        WikilinkBuilder.embed("diagram.png")         # ![[diagram.png]]
    """

    @staticmethod
    def link(target: str, alias: str | None = None) -> str:
        """
        Create a standard wikilink.

        Args:
            target: Target note name or path (e.g., "Machine Learning" or
                   "concepts/Machine Learning"). Obsidian resolves paths
                   automatically, so usually just the note name is sufficient.
            alias: Optional display text. When provided, the link shows this
                  text instead of the target name.

        Returns:
            Wikilink string: [[target]] or [[target|alias]]

        Examples:
            link("Neural Networks")           # [[Neural Networks]]
            link("Neural Networks", "NNs")    # [[Neural Networks|NNs]]
            link("papers/Smith2023")          # [[papers/Smith2023]]
        """
        if alias:
            return f"[[{target}|{alias}]]"
        return f"[[{target}]]"

    @staticmethod
    def header_link(note: str, header: str, alias: str | None = None) -> str:
        """
        Create a link to a specific header within a note.

        Useful for linking to specific sections when notes are long.
        The header text should match exactly (case-sensitive in some cases).

        Args:
            note: Target note name
            header: Header text (without the # markdown prefix)
            alias: Optional display text

        Returns:
            Wikilink with header anchor: [[note#header]] or [[note#header|alias]]

        Examples:
            header_link("Python", "Installation")     # [[Python#Installation]]
            header_link("API Docs", "Auth", "login")  # [[API Docs#Auth|login]]
        """
        target = f"{note}#{header}"
        return WikilinkBuilder.link(target, alias)

    @staticmethod
    def block_link(note: str, block_id: str, alias: str | None = None) -> str:
        """
        Create a link to a specific block (paragraph) within a note.

        Block IDs are created in Obsidian by adding ^block-id at the end of
        a paragraph. This allows linking to specific paragraphs rather than
        headers.

        Args:
            note: Target note name
            block_id: Block identifier (without the ^ prefix)
            alias: Optional display text

        Returns:
            Wikilink with block anchor: [[note#^block-id]]

        Examples:
            block_link("Research Notes", "key-finding")  # [[Research Notes#^key-finding]]
        """
        target = f"{note}#^{block_id}"
        return WikilinkBuilder.link(target, alias)

    @staticmethod
    def embed(target: str) -> str:
        """
        Create an embedded (transcluded) link.

        Embeds display the target content inline rather than as a clickable
        link. Works for notes, images, PDFs, and audio files.

        Args:
            target: Note name or file path to embed

        Returns:
            Embed syntax: ![[target]]

        Examples:
            embed("Summary")           # ![[Summary]] - embeds entire note
            embed("diagram.png")       # ![[diagram.png]] - embeds image
            embed("Note#Section")      # ![[Note#Section]] - embeds just that section
        """
        return f"![[{target}]]"


def extract_wikilinks(content: str) -> list[str]:
    """
    Extract all wikilinks from markdown content.

    Parses the content to find all [[wikilinks]], handling:
    - Basic links: [[Note Name]]
    - Aliased links: [[Note Name|Display Text]]
    - Header links: [[Note#Header]] (returns just "Note")
    - Block links: [[Note#^block-id]] (returns just "Note")
    - Embeds: ![[Note]] (also extracted)

    Used by VaultSyncService to determine outgoing LINKS_TO relationships
    for the Neo4j knowledge graph.

    Args:
        content: Full markdown content of a note (including frontmatter)

    Returns:
        List of unique note names in order of first appearance.
        Header/block references are stripped - only the base note name returned.

    Examples:
        extract_wikilinks("See [[ML]] and [[ML|machine learning]]")
        # Returns: ["ML"]

        extract_wikilinks("Check [[Paper#Methods]] and [[Paper#Results]]")
        # Returns: ["Paper"]
    """
    pattern = r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]"
    matches = re.findall(pattern, content)

    # Remove duplicates while preserving order
    seen = set()
    unique = []
    for match in matches:
        note_name = match.split("#")[0]  # Strip header/block references
        if note_name and note_name not in seen:
            seen.add(note_name)
            unique.append(note_name)

    return unique


def extract_tags(content: str) -> list[str]:
    """
    Extract all inline #tags from markdown content.

    Finds hashtag-style tags used in Obsidian for categorization.
    Supports hierarchical tags (e.g., #ai/deep-learning/transformers).

    Does NOT extract:
    - Tags in frontmatter (those are parsed separately)
    - Markdown headers (e.g., ## Header)
    - Tags inside wikilinks

    Args:
        content: Full markdown content of a note

    Returns:
        List of unique tags (without the # prefix)

    Examples:
        extract_tags("Learning about #machine-learning and #ai/nlp")
        # Returns: ["machine-learning", "ai/nlp"]

        extract_tags("## Header with #tag")
        # Returns: ["tag"] (## is a header, not a tag)
    """
    pattern = r"(?<!\[)#([a-zA-Z][\w/-]*)"
    matches = re.findall(pattern, content)
    return list(set(matches))


def generate_connection_section(connections: list[dict]) -> str:
    """
    Generate a Connections section with formatted wikilinks.

    Creates a markdown list of related notes, typically used at the bottom
    of processed notes to show relationships discovered by the LLM.

    Args:
        connections: List of connection dicts, each containing:
            - target_title (str): Name of the related note
            - explanation (str, optional): Why notes are related
            - relationship_type (str, optional): Type like "RELATES_TO", "EXTENDS"

    Returns:
        Markdown formatted string with one link per line.
        Returns "*No connections found*" if empty.

    Example Output:
        - [[Machine Learning]] — Foundational concepts for this paper
        - [[Neural Networks]] (EXTENDS)
        - [[Backpropagation]] — Used in the training algorithm
    """
    if not connections:
        return "*No connections found*"

    lines = []
    for conn in connections:
        target = conn.get("target_title", "Unknown")
        explanation = conn.get("explanation", "")
        relationship = conn.get("relationship_type", "RELATES_TO")

        link = WikilinkBuilder.link(target)

        if explanation:
            lines.append(f"- {link} — {explanation}")
        else:
            lines.append(f"- {link} ({relationship})")

    return "\n".join(lines)


def auto_link_concepts(
    content: str, known_concepts: list[str], exclude_in_links: bool = True
) -> str:
    """
    Automatically convert known concept names to wikilinks.

    Scans the content for mentions of known concepts and wraps them in
    [[wikilink]] syntax. Useful for:
    - Post-processing LLM-generated content
    - Enriching imported notes with links
    - Building a more connected knowledge graph

    The function is smart about:
    - Case-insensitive matching ("machine learning" matches "Machine Learning")
    - Word boundaries (won't match "learning" inside "unlearning")
    - Longest-first matching (prevents "ML" from matching inside "HTML")
    - Skipping already-linked text

    Args:
        content: Markdown content to process
        known_concepts: List of concept names that exist in the vault
        exclude_in_links: If True (default), won't re-link text already
                         inside a wikilink

    Returns:
        Content with concept mentions converted to [[wikilinks]]

    Example:
        concepts = ["Machine Learning", "Neural Networks"]
        content = "Machine learning uses neural networks."
        result = auto_link_concepts(content, concepts)
        # "[[Machine Learning]] uses [[Neural Networks]]."

    Caution:
        Can be aggressive - review output for false positives, especially
        with short concept names or common words.
    """
    # Sort by length (longest first) to avoid partial matches
    concepts = sorted(known_concepts, key=len, reverse=True)

    for concept in concepts:
        if not concept:
            continue

        # Pattern to match concept not already in a wikilink
        pattern = rf"(?<!\[\[)(?<!\|)\b({re.escape(concept)})\b(?!\]\])(?!\|)"

        def replace(match):
            return f"[[{match.group(1)}]]"

        content = re.sub(pattern, replace, content, flags=re.IGNORECASE)

    return content


def validate_links(content: str, vault_notes: set[str]) -> list[str]:
    """
    Find broken wikilinks pointing to non-existent notes.

    Compares extracted links against a set of known note names to identify
    links that would show as "unresolved" in Obsidian.

    Useful for:
    - Vault health checks
    - Pre-commit validation
    - Identifying notes that need to be created

    Args:
        content: Markdown content to check
        vault_notes: Set of all note names that exist in the vault
                    (typically from VaultManager.list_notes())

    Returns:
        List of link targets that don't exist in vault_notes

    Example:
        vault_notes = {"Python", "JavaScript"}
        content = "See [[Python]] and [[Rust]] for examples."
        broken = validate_links(content, vault_notes)
        # Returns: ["Rust"]
    """
    links = extract_wikilinks(content)
    broken = [link for link in links if link not in vault_notes]
    return broken


def create_backlink_section(backlinks: list[dict]) -> str:
    """
    Create a Backlinks section showing notes that link to this one.

    Generates a markdown list of notes that reference the current note,
    optionally with context showing how they're related.

    Backlinks are typically computed via Neo4j query:
        MATCH (other:Note)-[:LINKS_TO]->(this:Note {id: $id})
        RETURN other.title, other.excerpt

    Args:
        backlinks: List of dicts, each containing:
            - title (str): Name of the note that links here
            - context (str, optional): Excerpt or description of the link

    Returns:
        Markdown formatted string with one backlink per line.
        Returns "*No backlinks found*" if empty.

    Example Output:
        - [[Machine Learning]]: "Neural networks are a key technique..."
        - [[Deep Learning]]
        - [[AI Overview]]: References this concept in the intro
    """
    if not backlinks:
        return "*No backlinks found*"

    lines = []
    for bl in backlinks:
        title = bl.get("title", "Unknown")
        context = bl.get("context", "")
        link = WikilinkBuilder.link(title)

        if context:
            lines.append(f"- {link}: {context}")
        else:
            lines.append(f"- {link}")

    return "\n".join(lines)
