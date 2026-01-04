"""
Knowledge Graph Schema Definitions

Defines the node labels, relationship types, and property schemas
used in the Neo4j knowledge graph.

Node Labels:
- Content: Papers, articles, books, code, ideas, voice memos
- Concept: Key concepts, terms, ideas extracted from content
- Tag: Tags from the controlled taxonomy

Relationship Types:
- CONTAINS: Content -> Concept (content contains a concept)
- RELATES_TO: Content -> Content (general topical relationship)
- EXTENDS: Content -> Content (builds on existing content)
- CONTRADICTS: Content -> Content (challenges existing content)
- PREREQUISITE_FOR: Content -> Content (foundational for understanding)
- APPLIES: Content -> Content (applies concepts from another)
- HAS_TAG: Content -> Tag (content has a tag)
"""

from dataclasses import dataclass, field
from typing import Optional

from app.enums import RelationshipType, ConceptImportance, TagCategory


@dataclass
class ContentNodeSchema:
    """Schema for Content nodes in Neo4j."""

    # Required properties
    id: str  # UUID from UnifiedContent
    title: str  # Content title
    type: str  # paper, article, book, code, idea, voice_memo

    # Optional properties
    summary: str = ""  # Standard summary
    source_url: Optional[str] = None
    embedding: list[float] = field(default_factory=list)  # 1536-dim vector
    tags: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    # Timestamps (set by Neo4j)
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


@dataclass
class ConceptNodeSchema:
    """Schema for Concept nodes in Neo4j."""

    # Required properties
    id: str  # UUID
    name: str  # Concept name (unique)
    definition: str  # Clear definition

    # Optional properties
    importance: str = ConceptImportance.SUPPORTING.value
    embedding: list[float] = field(default_factory=list)

    # Timestamps
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


@dataclass
class TagNodeSchema:
    """Schema for Tag nodes in Neo4j."""

    name: str  # Full tag path (e.g., ml/transformers/attention)
    description: str = ""
    category: str = TagCategory.DOMAIN.value


@dataclass
class RelationshipSchema:
    """Base schema for relationship properties."""

    # Optional properties that can be added to any relationship
    strength: float = 0.5  # 0-1 connection strength
    explanation: str = ""  # Why this relationship exists
    created_at: Optional[str] = None


@dataclass
class ContainsRelationship(RelationshipSchema):
    """Schema for CONTAINS relationship (Content -> Concept)."""

    importance: str = ConceptImportance.SUPPORTING.value
    context: str = ""  # How concept is used in this content


@dataclass
class ContentRelationship(RelationshipSchema):
    """Schema for Content -> Content relationships."""

    relationship_type: str = RelationshipType.RELATES_TO.value
    verified_by_user: bool = False  # User confirmed this connection
