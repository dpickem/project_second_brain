"""
Concept Deduplication Service

Provides concept name normalization and deduplication to prevent duplicate
concepts like "Behavior Cloning (BC)" and "Behavior Cloning" from being
stored as separate entities.

Key Features:
- Name normalization (case-insensitive matching, alias extraction)
- Duplicate detection before concept creation
- Integration with existing cleanup service

Usage:
    from app.services.processing.concept_dedup import (
        normalize_concept_name,
        find_existing_concept,
        deduplicate_concepts,
    )

    # Normalize a concept name
    normalized = normalize_concept_name("Behavior Cloning (BC)")
    # Returns: {"normalized": "behavior cloning", "aliases": ["BC"]}

    # Find existing concept by normalized name
    existing = await find_existing_concept(
        normalized_name="behavior cloning",
        neo4j_client=neo4j_client,
    )

    # Deduplicate a list of extracted concepts
    unique_concepts = deduplicate_concepts(concepts)
"""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from app.models.processing import Concept
    from app.services.knowledge_graph.client import Neo4jClient

logger = logging.getLogger(__name__)

# Pattern to extract aliases from parentheses
# Matches: "Concept Name (ALIAS)" or "Concept Name (alias1, alias2)"
ALIAS_PATTERN = re.compile(r"\s*\(([^)]+)\)\s*$")

# Pattern to clean up whitespace
WHITESPACE_PATTERN = re.compile(r"\s+")


class NormalizedConcept:
    """
    A concept with its normalized name and extracted aliases.

    Attributes:
        original: Original concept name as extracted
        normalized: Lowercase, cleaned name for matching
        aliases: List of aliases extracted from parentheses
    """

    def __init__(self, original: str):
        self.original = original
        self.normalized, self.aliases = normalize_concept_name(original)

    def matches(self, other: NormalizedConcept) -> bool:
        """Check if this concept matches another by normalized name or aliases."""
        # Direct normalized name match
        if self.normalized == other.normalized:
            return True

        # Check if either's aliases match the other's normalized name
        if self.normalized in other.aliases or other.normalized in self.aliases:
            return True

        # Check alias overlap
        if self.aliases and other.aliases:
            if set(self.aliases) & set(other.aliases):
                return True

        return False


def normalize_concept_name(name: str) -> tuple[str, list[str]]:
    """
    Normalize a concept name for deduplication matching.

    Extracts aliases from parentheses and normalizes the base name.

    Args:
        name: Original concept name (e.g., "Behavior Cloning (BC)")

    Returns:
        Tuple of (normalized_name, aliases):
        - normalized_name: Lowercase, whitespace-normalized base name
        - aliases: List of extracted aliases (e.g., ["bc"])

    Examples:
        >>> normalize_concept_name("Behavior Cloning (BC)")
        ("behavior cloning", ["bc"])

        >>> normalize_concept_name("Natural Language Processing (NLP, NLU)")
        ("natural language processing", ["nlp", "nlu"])

        >>> normalize_concept_name("Simple Concept")
        ("simple concept", [])

        >>> normalize_concept_name("API")
        ("api", [])
    """
    if not name:
        return "", []

    # Extract aliases from parentheses at the end
    aliases = []
    match = ALIAS_PATTERN.search(name)
    if match:
        # Extract the content in parentheses
        alias_content = match.group(1)
        # Split by comma or semicolon
        raw_aliases = re.split(r"[,;]", alias_content)
        aliases = [a.strip().lower() for a in raw_aliases if a.strip()]
        # Remove the alias part from the name
        name = name[: match.start()]

    # Normalize the base name
    normalized = WHITESPACE_PATTERN.sub(" ", name).strip().lower()

    return normalized, aliases


def get_canonical_name(name: str) -> str:
    """
    Get the canonical (normalized) form of a concept name.

    This is used for Neo4j MERGE operations to ensure consistent matching.

    Args:
        name: Original concept name

    Returns:
        Canonical form for storage/matching

    Example:
        >>> get_canonical_name("Behavior Cloning (BC)")
        "Behavior Cloning"
    """
    # Remove alias parenthetical but preserve original casing
    match = ALIAS_PATTERN.search(name)
    if match:
        name = name[: match.start()].strip()
    return name


def extract_aliases(name: str) -> list[str]:
    """
    Extract aliases from a concept name.

    Args:
        name: Concept name potentially containing aliases

    Returns:
        List of extracted aliases (original case preserved)

    Example:
        >>> extract_aliases("Machine Learning (ML)")
        ["ML"]
    """
    match = ALIAS_PATTERN.search(name)
    if match:
        alias_content = match.group(1)
        raw_aliases = re.split(r"[,;]", alias_content)
        return [a.strip() for a in raw_aliases if a.strip()]
    return []


async def find_existing_concept(
    normalized_name: str,
    neo4j_client: Optional[Neo4jClient],
    aliases: Optional[list[str]] = None,
) -> Optional[dict]:
    """
    Find an existing concept in Neo4j by canonical name or alias.

    Uses the Neo4j client's `find_concept_by_canonical_name` method to check
    for existing concepts. Checks both the normalized name and any aliases.

    Args:
        normalized_name: Normalized (lowercase) concept name
        neo4j_client: Neo4j client for graph queries
        aliases: Optional list of aliases to also check

    Returns:
        Dict with concept info if found, None otherwise:
        {
            "id": str,
            "name": str,
            "definition": str,
        }
    """
    if not neo4j_client:
        return None

    try:
        # Check canonical name first
        result = await neo4j_client.find_concept_by_canonical_name(normalized_name)
        if result:
            return result

        # Also check aliases if provided
        if aliases:
            for alias in aliases:
                result = await neo4j_client.find_concept_by_canonical_name(alias.lower())
                if result:
                    return result

        return None

    except Exception as e:
        logger.warning(f"Failed to check for existing concept: {e}")
        return None


def deduplicate_concepts(concepts: list[Concept]) -> list[Concept]:
    """
    Deduplicate a list of concepts by normalized name.

    When duplicates are found, the concept with the more detailed definition
    is kept. Aliases are merged.

    Args:
        concepts: List of extracted Concept objects

    Returns:
        Deduplicated list of Concept objects

    Example:
        If concepts contains both "Behavior Cloning (BC)" and "BC",
        only one will be returned with the better definition.
    """
    if not concepts:
        return []

    # Track unique concepts by normalized name
    unique: dict[str, tuple[NormalizedConcept, Concept]] = {}

    for concept in concepts:
        norm = NormalizedConcept(concept.name)

        # Check if we already have this concept
        existing_key = None
        for key, (existing_norm, _) in unique.items():
            if norm.matches(existing_norm):
                existing_key = key
                break

        if existing_key:
            # Merge with existing - keep the one with better definition
            _, existing_concept = unique[existing_key]
            if _is_better_definition(concept.definition, existing_concept.definition):
                # Use the new concept's definition but merge aliases
                unique[existing_key] = (norm, concept)
                logger.debug(
                    f"Merged duplicate concept: '{concept.name}' -> '{existing_concept.name}'"
                )
        else:
            # New unique concept
            unique[norm.normalized] = (norm, concept)

    result = [concept for _, concept in unique.values()]
    deduped_count = len(concepts) - len(result)
    if deduped_count > 0:
        logger.info(f"Deduplicated {deduped_count} concept(s) from {len(concepts)}")

    return result


def _is_better_definition(new_def: Optional[str], old_def: Optional[str]) -> bool:
    """
    Determine if a new definition is better than an existing one.

    Prefers longer, more detailed definitions.
    """
    if not new_def:
        return False
    if not old_def:
        return True
    # Prefer longer definition as it's likely more detailed
    return len(new_def) > len(old_def)


async def find_or_create_canonical_concept(
    concept: Concept,
    neo4j_client: Optional[Neo4jClient],
) -> tuple[str, bool]:
    """
    Find an existing concept or prepare for creation with canonical name.

    This ensures concepts are stored with consistent canonical names
    in Neo4j, enabling proper MERGE behavior.

    Args:
        concept: The extracted concept
        neo4j_client: Neo4j client for lookup

    Returns:
        Tuple of (canonical_name, exists):
        - canonical_name: The canonical name to use for storage
        - exists: True if concept already exists in Neo4j
    """
    canonical = get_canonical_name(concept.name)
    normalized, aliases = normalize_concept_name(concept.name)

    # Check if concept already exists
    existing = await find_existing_concept(normalized, neo4j_client, aliases)

    if existing:
        # Use the existing concept's name for consistency
        return existing["name"], True

    return canonical, False
