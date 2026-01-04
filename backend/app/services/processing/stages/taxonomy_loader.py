"""
Tag Taxonomy Loader

Loads tag taxonomy from the single source of truth: config/tag-taxonomy.yaml

The taxonomy defines all valid tags in the Second Brain system. Tags follow
a hierarchical structure: domain/category/topic

YAML Configuration Structure:
    The config/tag-taxonomy.yaml file has three top-level sections:

    ```yaml
    domains:
      ml:                           # Top-level domain
        name: "Machine Learning"
        categories:
          architecture:             # Category within domain
            topics:                 # List of topics
              - transformers
              - attention
              - llms
          training:
            topics:
              - optimization
              - fine-tuning
      systems:
        name: "Systems"
        categories:
          distributed:
            topics:
              - consensus
              - replication

    status:                         # Meta tags for content status
      actionable: "Requires action"
      review: "Needs review"
      archived: "No longer active"

    quality:                        # Meta tags for content quality
      foundational: "Core knowledge"
      deep-dive: "In-depth exploration"
      reference: "Quick reference"
    ```

    This is flattened to path-style tags:
    - domains: ["ml/architecture/transformers", "ml/architecture/attention", ...]
    - status: ["actionable", "review", "archived"]
    - quality: ["foundational", "deep-dive", "reference"]

    Meta tags are prefixed when accessed via TagTaxonomy.meta:
    - ["status/actionable", "status/review", "quality/foundational", ...]

Usage:
    from app.services.processing.stages.taxonomy_loader import get_tag_taxonomy

    taxonomy = await get_tag_taxonomy()

    # Validate a tag
    if taxonomy.validate_domain_tag("ml/transformers/attention"):
        print("Valid tag!")
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
import time

import aiofiles
import yaml

from app.config.processing import processing_settings
from app.config.settings import PROJECT_ROOT

logger = logging.getLogger(__name__)


@dataclass
class TagTaxonomy:
    """
    Loaded tag taxonomy with domain and meta tags.

    Provides validation methods to check if tags are in the taxonomy
    and utility methods to filter tags by category.
    """

    # Flat list of all domain tags (e.g., "ml/transformers/attention")
    domains: list[str] = field(default_factory=list)

    # Status tags (e.g., "status/actionable")
    status: list[str] = field(default_factory=list)

    # Quality tags (e.g., "quality/foundational")
    quality: list[str] = field(default_factory=list)

    @property
    def meta(self) -> list[str]:
        """Get all meta tags (status + quality)."""
        return [f"status/{s}" for s in self.status] + [
            f"quality/{q}" for q in self.quality
        ]

    @property
    def all_tags(self) -> list[str]:
        """Get all tags in the taxonomy."""
        return self.domains + self.meta

    def validate_domain_tag(self, tag: str) -> bool:
        """Check if tag is in domain taxonomy."""
        return tag in self.domains

    def validate_meta_tag(self, tag: str) -> bool:
        """Check if tag is in meta taxonomy (status/quality)."""
        return tag in self.meta

    def validate_tag(self, tag: str) -> bool:
        """Check if tag is valid (domain or meta)."""
        return tag in self.all_tags

    def filter_valid_tags(self, tags: list[str]) -> tuple[list[str], list[str]]:
        """
        Split tags into valid domain and meta tags.

        Args:
            tags: List of tag strings to validate

        Returns:
            Tuple of (valid_domain_tags, valid_meta_tags)
        """
        domain_tags = [t for t in tags if self.validate_domain_tag(t)]
        meta_tags = [t for t in tags if self.validate_meta_tag(t)]
        return domain_tags, meta_tags

    def get_invalid_tags(self, tags: list[str]) -> list[str]:
        """Get tags that are not in the taxonomy."""
        return [t for t in tags if not self.validate_tag(t)]


class TagTaxonomyLoader:
    """
    Loads tag taxonomy from YAML configuration.

    Single source of truth: config/tag-taxonomy.yaml

    The taxonomy is cached and can be refreshed when the config file changes.
    Uses singleton pattern to avoid repeated file reads.
    """

    _instance: Optional["TagTaxonomyLoader"] = None
    _taxonomy: Optional[TagTaxonomy] = None
    _last_loaded: Optional[float] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    async def get_taxonomy(cls, force_reload: bool = False) -> TagTaxonomy:
        """
        Get the current tag taxonomy, loading if necessary.

        Args:
            force_reload: Force reload from config file

        Returns:
            TagTaxonomy with domain and meta tags

        Raises:
            FileNotFoundError: If config file is missing
            ValueError: If config file is invalid
        """
        # Check cache validity
        if cls._taxonomy is not None and not force_reload:
            if cls._last_loaded is not None:
                age = time.time() - cls._last_loaded
                if age < processing_settings.TAG_TAXONOMY_CACHE_TTL:
                    return cls._taxonomy

        # Reload taxonomy
        cls._taxonomy = await cls._load_taxonomy()
        cls._last_loaded = time.time()
        return cls._taxonomy

    @classmethod
    async def _load_taxonomy(cls) -> TagTaxonomy:
        """Load taxonomy from config/tag-taxonomy.yaml."""
        config_file = Path(processing_settings.TAG_TAXONOMY_PATH)

        # Try relative to project root if not absolute
        if not config_file.exists():
            config_file = PROJECT_ROOT / processing_settings.TAG_TAXONOMY_PATH

        if not config_file.exists():
            raise FileNotFoundError(
                f"Tag taxonomy config not found: {processing_settings.TAG_TAXONOMY_PATH}. "
                "This file is required - no fallback is used."
            )

        try:
            taxonomy = await cls._parse_yaml_taxonomy(config_file)
            logger.info(
                f"Loaded taxonomy from config: "
                f"{len(taxonomy.domains)} domains, "
                f"{len(taxonomy.status)} status, "
                f"{len(taxonomy.quality)} quality"
            )
            return taxonomy
        except Exception as e:
            logger.error(f"Failed to parse tag taxonomy config: {e}")
            raise ValueError(f"Invalid tag taxonomy configuration: {e}")

    @classmethod
    async def _parse_yaml_taxonomy(cls, path: Path) -> TagTaxonomy:
        """
        Parse tag taxonomy from YAML config file.

        Converts hierarchical YAML structure to flat tag paths.
        See module docstring for full YAML structure documentation.

        Args:
            path: Path to the tag-taxonomy.yaml file

        Returns:
            TagTaxonomy with:
            - domains: Flattened paths like ["ml/architecture/transformers", ...]
            - status: Status tag names like ["actionable", "review", ...]
            - quality: Quality tag names like ["foundational", "deep-dive", ...]
        """
        async with aiofiles.open(path, "r", encoding="utf-8") as f:
            content = await f.read()

        data = yaml.safe_load(content)

        # Parse hierarchical domain tags into flat paths
        domains = cls._flatten_domain_tags(data.get("domains", {}))

        # Parse status and quality tags (can be dict with descriptions or list)
        status = cls._extract_tag_names(data.get("status", {}))
        quality = cls._extract_tag_names(data.get("quality", {}))

        return TagTaxonomy(domains=domains, status=status, quality=quality)

    @staticmethod
    def _extract_tag_names(tag_section: dict | list) -> list[str]:
        """
        Extract tag names from a YAML section.

        Handles both formats:
        - Dict with descriptions: {actionable: "desc", review: "desc"} -> ["actionable", "review"]
        - Simple list: ["actionable", "review"] -> ["actionable", "review"]

        Args:
            tag_section: Either a dict (keys are tag names) or list (items are tag names)

        Returns:
            List of tag name strings
        """
        if isinstance(tag_section, dict):
            return list(tag_section.keys())
        if isinstance(tag_section, list):
            return tag_section
        return []

    @classmethod
    def _flatten_domain_tags(
        cls, domains: dict[str, dict | str | None], prefix: str = ""
    ) -> list[str]:
        """
        Flatten hierarchical domain structure to slash-separated path strings.

        Recursively traverses the YAML domain hierarchy and produces flat paths.
        Handles multiple YAML structures for flexibility.

        Args:
            domains: Dict from YAML with nested domain/category/topic structure.
                Keys are domain names, values can be:
                - dict with "categories" key: domain with nested categories
                - dict with "topics" key: category with topic list
                - dict (other): recurse deeper
                - str/None: leaf node (the key itself is the tag)
            prefix: Current path prefix for recursion (e.g., "ml/architecture")

        Returns:
            List of flattened tag paths like ["ml/architecture/transformers", ...]

        Example YAML input:
            ml:
              name: "Machine Learning"
              categories:
                architecture:
                  topics: [transformers, llms]

        Example output:
            ["ml/architecture/transformers", "ml/architecture/llms"]
        """
        tags: list[str] = []

        for key, value in domains.items():
            path = f"{prefix}/{key}" if prefix else key

            if not isinstance(value, dict):
                # Leaf node: value is string description or None
                tags.append(path)
                continue

            # Value is a dict - determine structure type
            if "categories" in value:
                tags.extend(cls._process_categories(value["categories"], path))
            elif "topics" in value:
                tags.extend(cls._process_topics(value["topics"], path))
            else:
                # Generic nested dict - recurse
                tags.extend(cls._flatten_domain_tags(value, path))

        return tags

    @classmethod
    def _process_categories(
        cls, categories: dict[str, dict | str | None], domain_path: str
    ) -> list[str]:
        """
        Process the 'categories' section of a domain.

        Args:
            categories: Dict of category_name -> category_value
            domain_path: Parent domain path (e.g., "ml")

        Returns:
            List of tag paths for all categories and their topics
        """
        tags: list[str] = []

        for cat_name, cat_value in categories.items():
            cat_path = f"{domain_path}/{cat_name}"

            if isinstance(cat_value, dict) and "topics" in cat_value:
                tags.extend(cls._process_topics(cat_value["topics"], cat_path))
            else:
                # Category without topics - the category itself is the tag
                tags.append(cat_path)

        return tags

    @classmethod
    def _process_topics(
        cls, topics: list[str | dict[str, str]], parent_path: str
    ) -> list[str]:
        """
        Process a 'topics' list into tag paths.

        Args:
            topics: List of topics, each can be:
                - str: simple topic name
                - dict: {topic_name: description}
            parent_path: Parent path (e.g., "ml/architecture")

        Returns:
            List of tag paths like ["ml/architecture/transformers", ...]
        """
        tags: list[str] = []

        for topic in topics:
            if isinstance(topic, dict):
                # Topic with description: {transformers: "Attention-based models"}
                for topic_name in topic.keys():
                    tags.append(f"{parent_path}/{topic_name}")
            else:
                # Simple string topic
                tags.append(f"{parent_path}/{topic}")

        return tags

    @classmethod
    def invalidate_cache(cls):
        """Invalidate cached taxonomy (call when config file changes)."""
        cls._taxonomy = None
        cls._last_loaded = None
        logger.debug("Tag taxonomy cache invalidated")


# Convenience function
async def get_tag_taxonomy(force_reload: bool = False) -> TagTaxonomy:
    """
    Get the current tag taxonomy.

    Args:
        force_reload: Force reload from config file

    Returns:
        TagTaxonomy with validated tags
    """
    return await TagTaxonomyLoader.get_taxonomy(force_reload)
