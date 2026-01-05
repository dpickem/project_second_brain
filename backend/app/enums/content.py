"""
Content-related enums.

Defines enums for content types, annotation types, and processing status.
"""

from enum import Enum


class ContentType(str, Enum):
    """
    Built-in content types for the ingestion system.

    This enum should stay in sync with config/default.yaml content_types section.
    The enum provides compile-time type safety in Python code, while the YAML
    config defines runtime behavior (folders, templates, icons).

    TO ADD A NEW CONTENT TYPE:
    1. Add to config/default.yaml content_types section (defines folder, template, etc.)
    2. Add to this enum (e.g., PODCAST = "PODCAST") for type safety
    3. Create Obsidian template in vault's templates/ folder
    4. Create Jinja2 template in config/templates/
    5. Run `python scripts/setup/setup_vault.py` to create folders

    See config/default.yaml for the full content type registry with all configuration.
    """

    # Technical content
    PAPER = "PAPER"
    ARTICLE = "ARTICLE"
    BOOK = "BOOK"
    CODE = "CODE"
    IDEA = "IDEA"
    VOICE_MEMO = "VOICE_MEMO"

    # Career & personal development
    CAREER = "CAREER"
    PERSONAL = "PERSONAL"
    PROJECT = "PROJECT"
    REFLECTION = "REFLECTION"
    NON_TECH = "NON_TECH"

    # System types
    DAILY = "DAILY"
    CONCEPT = "CONCEPT"
    EXERCISE = "EXERCISE"


class AnnotationType(str, Enum):
    """Types of annotations that can be attached to content."""

    DIGITAL_HIGHLIGHT = "DIGITAL_HIGHLIGHT"
    HANDWRITTEN_NOTE = "HANDWRITTEN_NOTE"
    TYPED_COMMENT = "TYPED_COMMENT"
    DIAGRAM = "DIAGRAM"
    UNDERLINE = "UNDERLINE"


class ProcessingStatus(str, Enum):
    """Processing status for content items.

    Values must match the PostgreSQL contentstatus enum (uppercase).
    """

    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    PROCESSED = "PROCESSED"
    FAILED = "FAILED"
