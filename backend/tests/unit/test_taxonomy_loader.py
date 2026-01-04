"""
Unit Tests for Tag Taxonomy Loader

Tests the TagTaxonomy dataclass and TagTaxonomyLoader for:
- Tag validation methods
- YAML parsing and flattening
- Caching behavior
- Various YAML structure formats
"""

import pytest
from pathlib import Path
from unittest.mock import patch, AsyncMock

from app.services.processing.stages.taxonomy_loader import (
    TagTaxonomy,
    TagTaxonomyLoader,
    get_tag_taxonomy,
)


# ============================================================================
# TagTaxonomy Dataclass Tests
# ============================================================================


class TestTagTaxonomy:
    """Test suite for the TagTaxonomy dataclass."""

    @pytest.fixture
    def sample_taxonomy(self) -> TagTaxonomy:
        """Create a sample taxonomy for testing."""
        return TagTaxonomy(
            domains=[
                "ml/architecture/transformers",
                "ml/architecture/llms",
                "ml/training/optimization",
                "systems/distributed/consensus",
            ],
            status=["actionable", "review", "archived"],
            quality=["foundational", "deep-dive", "reference"],
        )

    def test_meta_property(self, sample_taxonomy: TagTaxonomy) -> None:
        """meta property should combine status and quality with prefixes."""
        meta = sample_taxonomy.meta

        assert "status/actionable" in meta
        assert "status/review" in meta
        assert "status/archived" in meta
        assert "quality/foundational" in meta
        assert "quality/deep-dive" in meta
        assert "quality/reference" in meta
        assert len(meta) == 6

    def test_all_tags_property(self, sample_taxonomy: TagTaxonomy) -> None:
        """all_tags should include both domain and meta tags."""
        all_tags = sample_taxonomy.all_tags

        # Domain tags
        assert "ml/architecture/transformers" in all_tags
        assert "systems/distributed/consensus" in all_tags

        # Meta tags
        assert "status/actionable" in all_tags
        assert "quality/foundational" in all_tags

        # Total count
        assert len(all_tags) == 4 + 6  # 4 domains + 6 meta

    def test_validate_domain_tag_valid(self, sample_taxonomy: TagTaxonomy) -> None:
        """validate_domain_tag should return True for valid domain tags."""
        assert sample_taxonomy.validate_domain_tag("ml/architecture/transformers")
        assert sample_taxonomy.validate_domain_tag("systems/distributed/consensus")

    def test_validate_domain_tag_invalid(self, sample_taxonomy: TagTaxonomy) -> None:
        """validate_domain_tag should return False for invalid tags."""
        assert not sample_taxonomy.validate_domain_tag("invalid/tag")
        assert not sample_taxonomy.validate_domain_tag("status/actionable")  # Meta tag
        assert not sample_taxonomy.validate_domain_tag("")

    def test_validate_meta_tag_valid(self, sample_taxonomy: TagTaxonomy) -> None:
        """validate_meta_tag should return True for valid meta tags."""
        assert sample_taxonomy.validate_meta_tag("status/actionable")
        assert sample_taxonomy.validate_meta_tag("status/review")
        assert sample_taxonomy.validate_meta_tag("quality/foundational")

    def test_validate_meta_tag_invalid(self, sample_taxonomy: TagTaxonomy) -> None:
        """validate_meta_tag should return False for invalid tags."""
        assert not sample_taxonomy.validate_meta_tag("invalid/tag")
        assert not sample_taxonomy.validate_meta_tag("ml/architecture/transformers")
        assert not sample_taxonomy.validate_meta_tag("actionable")  # Missing prefix

    def test_validate_tag_accepts_both_types(
        self, sample_taxonomy: TagTaxonomy
    ) -> None:
        """validate_tag should return True for both domain and meta tags."""
        assert sample_taxonomy.validate_tag("ml/architecture/transformers")
        assert sample_taxonomy.validate_tag("status/actionable")
        assert sample_taxonomy.validate_tag("quality/deep-dive")
        assert not sample_taxonomy.validate_tag("invalid/tag")

    def test_filter_valid_tags(self, sample_taxonomy: TagTaxonomy) -> None:
        """filter_valid_tags should split tags into domain and meta."""
        tags = [
            "ml/architecture/transformers",
            "status/actionable",
            "invalid/tag",
            "systems/distributed/consensus",
            "quality/foundational",
        ]

        domain_tags, meta_tags = sample_taxonomy.filter_valid_tags(tags)

        assert domain_tags == [
            "ml/architecture/transformers",
            "systems/distributed/consensus",
        ]
        assert meta_tags == ["status/actionable", "quality/foundational"]

    def test_filter_valid_tags_empty_input(self, sample_taxonomy: TagTaxonomy) -> None:
        """filter_valid_tags should handle empty input."""
        domain_tags, meta_tags = sample_taxonomy.filter_valid_tags([])
        assert domain_tags == []
        assert meta_tags == []

    def test_get_invalid_tags(self, sample_taxonomy: TagTaxonomy) -> None:
        """get_invalid_tags should return tags not in taxonomy."""
        tags = [
            "ml/architecture/transformers",  # valid
            "invalid/tag",  # invalid
            "unknown",  # invalid
            "status/actionable",  # valid
        ]

        invalid = sample_taxonomy.get_invalid_tags(tags)
        assert invalid == ["invalid/tag", "unknown"]

    def test_empty_taxonomy(self) -> None:
        """Empty taxonomy should handle all operations gracefully."""
        taxonomy = TagTaxonomy()

        assert taxonomy.domains == []
        assert taxonomy.status == []
        assert taxonomy.quality == []
        assert taxonomy.meta == []
        assert taxonomy.all_tags == []
        assert not taxonomy.validate_tag("any/tag")


# ============================================================================
# TagTaxonomyLoader Static Methods Tests
# ============================================================================


class TestTagTaxonomyLoaderHelpers:
    """Test suite for TagTaxonomyLoader helper methods."""

    def test_extract_tag_names_from_dict(self) -> None:
        """_extract_tag_names should extract keys from dict."""
        tag_section = {
            "actionable": "Requires action",
            "review": "Needs review",
            "archived": "No longer active",
        }

        result = TagTaxonomyLoader._extract_tag_names(tag_section)

        assert result == ["actionable", "review", "archived"]

    def test_extract_tag_names_from_list(self) -> None:
        """_extract_tag_names should pass through list."""
        tag_section = ["actionable", "review", "archived"]

        result = TagTaxonomyLoader._extract_tag_names(tag_section)

        assert result == ["actionable", "review", "archived"]

    def test_extract_tag_names_empty_dict(self) -> None:
        """_extract_tag_names should handle empty dict."""
        result = TagTaxonomyLoader._extract_tag_names({})
        assert result == []

    def test_extract_tag_names_empty_list(self) -> None:
        """_extract_tag_names should handle empty list."""
        result = TagTaxonomyLoader._extract_tag_names([])
        assert result == []

    def test_extract_tag_names_invalid_type(self) -> None:
        """_extract_tag_names should return empty list for invalid types."""
        result = TagTaxonomyLoader._extract_tag_names(None)  # type: ignore
        assert result == []

        result = TagTaxonomyLoader._extract_tag_names("string")  # type: ignore
        assert result == []

    def test_process_topics_string_list(self) -> None:
        """_process_topics should handle simple string topics."""
        topics = ["transformers", "attention", "llms"]

        result = TagTaxonomyLoader._process_topics(topics, "ml/architecture")

        assert result == [
            "ml/architecture/transformers",
            "ml/architecture/attention",
            "ml/architecture/llms",
        ]

    def test_process_topics_dict_list(self) -> None:
        """_process_topics should handle dict topics with descriptions."""
        topics = [
            {"transformers": "Attention-based models"},
            {"llms": "Large language models"},
        ]

        result = TagTaxonomyLoader._process_topics(topics, "ml/architecture")

        assert result == [
            "ml/architecture/transformers",
            "ml/architecture/llms",
        ]

    def test_process_topics_mixed_list(self) -> None:
        """_process_topics should handle mixed string and dict topics."""
        topics = [
            "transformers",
            {"llms": "Large language models"},
            "attention",
        ]

        result = TagTaxonomyLoader._process_topics(topics, "ml")

        assert result == ["ml/transformers", "ml/llms", "ml/attention"]

    def test_process_topics_empty(self) -> None:
        """_process_topics should handle empty list."""
        result = TagTaxonomyLoader._process_topics([], "ml")
        assert result == []

    def test_process_categories_with_topics(self) -> None:
        """_process_categories should process categories with topics."""
        categories = {
            "architecture": {"topics": ["transformers", "llms"]},
            "training": {"topics": ["optimization", "fine-tuning"]},
        }

        result = TagTaxonomyLoader._process_categories(categories, "ml")

        assert "ml/architecture/transformers" in result
        assert "ml/architecture/llms" in result
        assert "ml/training/optimization" in result
        assert "ml/training/fine-tuning" in result
        assert len(result) == 4

    def test_process_categories_without_topics(self) -> None:
        """_process_categories should use category as tag if no topics."""
        categories = {
            "general": "General ML topics",
            "misc": None,
        }

        result = TagTaxonomyLoader._process_categories(categories, "ml")

        assert result == ["ml/general", "ml/misc"]

    def test_process_categories_mixed(self) -> None:
        """_process_categories should handle mixed categories."""
        categories = {
            "architecture": {"topics": ["transformers"]},
            "general": "General topic",
        }

        result = TagTaxonomyLoader._process_categories(categories, "ml")

        assert "ml/architecture/transformers" in result
        assert "ml/general" in result
        assert len(result) == 2


# ============================================================================
# _flatten_domain_tags Tests
# ============================================================================


class TestFlattenDomainTags:
    """Test suite for the _flatten_domain_tags method."""

    def test_simple_leaf_nodes(self) -> None:
        """Should handle simple key-value leaf nodes."""
        domains = {
            "ml": "Machine Learning",
            "systems": "Systems Engineering",
        }

        result = TagTaxonomyLoader._flatten_domain_tags(domains)

        assert result == ["ml", "systems"]

    def test_nested_dict_recursion(self) -> None:
        """Should recurse into nested dicts without special keys."""
        domains = {
            "ml": {
                "deep-learning": "DL stuff",
                "classical": "Classical ML",
            }
        }

        result = TagTaxonomyLoader._flatten_domain_tags(domains)

        assert "ml/deep-learning" in result
        assert "ml/classical" in result
        assert len(result) == 2

    def test_domain_with_categories(self) -> None:
        """Should process domains with 'categories' key."""
        domains = {
            "ml": {
                "name": "Machine Learning",
                "categories": {
                    "architecture": {"topics": ["transformers", "llms"]},
                },
            }
        }

        result = TagTaxonomyLoader._flatten_domain_tags(domains)

        assert "ml/architecture/transformers" in result
        assert "ml/architecture/llms" in result

    def test_category_with_topics(self) -> None:
        """Should process category with 'topics' key directly."""
        domains = {"architecture": {"topics": ["transformers", "attention", "llms"]}}

        result = TagTaxonomyLoader._flatten_domain_tags(domains)

        assert result == [
            "architecture/transformers",
            "architecture/attention",
            "architecture/llms",
        ]

    def test_deeply_nested_structure(self) -> None:
        """Should handle deeply nested structures."""
        domains = {
            "ml": {
                "name": "Machine Learning",
                "categories": {
                    "architecture": {
                        "topics": [
                            {"transformers": "desc"},
                            "llms",
                        ]
                    },
                    "training": {"topics": ["optimization"]},
                },
            },
            "systems": {
                "distributed": "Distributed systems",
            },
        }

        result = TagTaxonomyLoader._flatten_domain_tags(domains)

        assert "ml/architecture/transformers" in result
        assert "ml/architecture/llms" in result
        assert "ml/training/optimization" in result
        assert "systems/distributed" in result

    def test_with_prefix(self) -> None:
        """Should prepend prefix to all paths."""
        domains = {"deep": "Deep stuff", "shallow": "Shallow stuff"}

        result = TagTaxonomyLoader._flatten_domain_tags(domains, prefix="ml")

        assert result == ["ml/deep", "ml/shallow"]

    def test_empty_domains(self) -> None:
        """Should handle empty domains dict."""
        result = TagTaxonomyLoader._flatten_domain_tags({})
        assert result == []

    def test_none_values(self) -> None:
        """Should handle None values as leaf nodes."""
        domains = {"ml": None, "systems": None}

        result = TagTaxonomyLoader._flatten_domain_tags(domains)

        assert result == ["ml", "systems"]


# ============================================================================
# YAML Parsing Integration Tests
# ============================================================================


class TestYamlParsing:
    """Test YAML parsing with actual file I/O."""

    @pytest.fixture
    def sample_yaml_content(self) -> str:
        """Sample YAML content matching expected structure."""
        return """
domains:
  ml:
    name: "Machine Learning"
    categories:
      architecture:
        topics:
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

status:
  actionable: "Requires action"
  review: "Needs review"
  archived: "No longer active"

quality:
  foundational: "Core knowledge"
  deep-dive: "In-depth exploration"
  reference: "Quick reference"
"""

    @pytest.fixture
    def temp_taxonomy_file(self, tmp_path: Path, sample_yaml_content: str) -> Path:
        """Create a temporary taxonomy YAML file."""
        taxonomy_file = tmp_path / "tag-taxonomy.yaml"
        taxonomy_file.write_text(sample_yaml_content)
        return taxonomy_file

    @pytest.mark.asyncio
    async def test_parse_yaml_taxonomy(self, temp_taxonomy_file: Path) -> None:
        """_parse_yaml_taxonomy should correctly parse YAML file."""
        taxonomy = await TagTaxonomyLoader._parse_yaml_taxonomy(temp_taxonomy_file)

        # Check domains
        assert "ml/architecture/transformers" in taxonomy.domains
        assert "ml/architecture/attention" in taxonomy.domains
        assert "ml/architecture/llms" in taxonomy.domains
        assert "ml/training/optimization" in taxonomy.domains
        assert "systems/distributed/consensus" in taxonomy.domains

        # Check status
        assert "actionable" in taxonomy.status
        assert "review" in taxonomy.status
        assert "archived" in taxonomy.status

        # Check quality
        assert "foundational" in taxonomy.quality
        assert "deep-dive" in taxonomy.quality
        assert "reference" in taxonomy.quality

    @pytest.mark.asyncio
    async def test_parse_yaml_taxonomy_list_format(self, tmp_path: Path) -> None:
        """Should handle status/quality as simple lists."""
        yaml_content = """
domains:
  ml: "Machine Learning"

status:
  - actionable
  - review

quality:
  - foundational
  - reference
"""
        taxonomy_file = tmp_path / "taxonomy.yaml"
        taxonomy_file.write_text(yaml_content)

        taxonomy = await TagTaxonomyLoader._parse_yaml_taxonomy(taxonomy_file)

        assert taxonomy.status == ["actionable", "review"]
        assert taxonomy.quality == ["foundational", "reference"]


# ============================================================================
# Caching Tests
# ============================================================================


class TestTaxonomyCaching:
    """Test taxonomy caching behavior."""

    def setup_method(self) -> None:
        """Reset cache before each test."""
        TagTaxonomyLoader.invalidate_cache()

    def test_invalidate_cache(self) -> None:
        """invalidate_cache should clear cached taxonomy."""
        # Set some cached values
        TagTaxonomyLoader._taxonomy = TagTaxonomy(domains=["test"])
        TagTaxonomyLoader._last_loaded = 12345.0

        # Invalidate
        TagTaxonomyLoader.invalidate_cache()

        assert TagTaxonomyLoader._taxonomy is None
        assert TagTaxonomyLoader._last_loaded is None

    @pytest.mark.asyncio
    async def test_get_taxonomy_caching(self, tmp_path: Path) -> None:
        """get_taxonomy should cache and reuse taxonomy."""
        yaml_content = """
domains:
  ml: "Machine Learning"
status: []
quality: []
"""
        taxonomy_file = tmp_path / "tag-taxonomy.yaml"
        taxonomy_file.write_text(yaml_content)

        # Patch settings to use temp file and set long TTL
        with patch(
            "app.services.processing.stages.taxonomy_loader.processing_settings"
        ) as mock_settings:
            mock_settings.TAG_TAXONOMY_PATH = str(taxonomy_file)
            mock_settings.TAG_TAXONOMY_CACHE_TTL = 3600  # 1 hour

            # First call loads from file
            taxonomy1 = await TagTaxonomyLoader.get_taxonomy()

            # Modify file (but cache should be used)
            taxonomy_file.write_text(
                """
domains:
  systems: "Systems"
status: []
quality: []
"""
            )

            # Second call should return cached version
            taxonomy2 = await TagTaxonomyLoader.get_taxonomy()

            assert taxonomy1 is taxonomy2
            assert "ml" in taxonomy1.domains

    @pytest.mark.asyncio
    async def test_get_taxonomy_force_reload(self, tmp_path: Path) -> None:
        """get_taxonomy with force_reload should bypass cache."""
        yaml_content = """
domains:
  ml: "Machine Learning"
status: []
quality: []
"""
        taxonomy_file = tmp_path / "tag-taxonomy.yaml"
        taxonomy_file.write_text(yaml_content)

        with patch(
            "app.services.processing.stages.taxonomy_loader.processing_settings"
        ) as mock_settings:
            mock_settings.TAG_TAXONOMY_PATH = str(taxonomy_file)
            mock_settings.TAG_TAXONOMY_CACHE_TTL = 3600

            # First call
            taxonomy1 = await TagTaxonomyLoader.get_taxonomy()
            assert "ml" in taxonomy1.domains

            # Modify file
            taxonomy_file.write_text(
                """
domains:
  systems: "Systems"
status: []
quality: []
"""
            )

            # Force reload
            taxonomy2 = await TagTaxonomyLoader.get_taxonomy(force_reload=True)

            assert "systems" in taxonomy2.domains
            assert "ml" not in taxonomy2.domains


# ============================================================================
# Error Handling Tests
# ============================================================================


class TestErrorHandling:
    """Test error handling in taxonomy loading."""

    def setup_method(self) -> None:
        """Reset cache before each test."""
        TagTaxonomyLoader.invalidate_cache()

    @pytest.mark.asyncio
    async def test_missing_file_raises_error(self) -> None:
        """Should raise FileNotFoundError for missing taxonomy file."""
        with patch(
            "app.services.processing.stages.taxonomy_loader.processing_settings"
        ) as mock_settings:
            mock_settings.TAG_TAXONOMY_PATH = "/nonexistent/path/taxonomy.yaml"

            with pytest.raises(FileNotFoundError) as exc_info:
                await TagTaxonomyLoader.get_taxonomy()

            assert "Tag taxonomy config not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_invalid_yaml_raises_error(self, tmp_path: Path) -> None:
        """Should raise ValueError for invalid YAML."""
        taxonomy_file = tmp_path / "bad-taxonomy.yaml"
        taxonomy_file.write_text("invalid: yaml: content: [")

        with patch(
            "app.services.processing.stages.taxonomy_loader.processing_settings"
        ) as mock_settings:
            mock_settings.TAG_TAXONOMY_PATH = str(taxonomy_file)

            with pytest.raises(ValueError) as exc_info:
                await TagTaxonomyLoader.get_taxonomy()

            assert "Invalid tag taxonomy configuration" in str(exc_info.value)


# ============================================================================
# Convenience Function Tests
# ============================================================================


class TestGetTagTaxonomy:
    """Test the get_tag_taxonomy convenience function."""

    def setup_method(self) -> None:
        """Reset cache before each test."""
        TagTaxonomyLoader.invalidate_cache()

    @pytest.mark.asyncio
    async def test_get_tag_taxonomy_delegates_to_loader(self, tmp_path: Path) -> None:
        """get_tag_taxonomy should delegate to TagTaxonomyLoader."""
        yaml_content = """
domains:
  test: "Test domain"
status:
  active: "Active"
quality:
  good: "Good quality"
"""
        taxonomy_file = tmp_path / "taxonomy.yaml"
        taxonomy_file.write_text(yaml_content)

        with patch(
            "app.services.processing.stages.taxonomy_loader.processing_settings"
        ) as mock_settings:
            mock_settings.TAG_TAXONOMY_PATH = str(taxonomy_file)
            mock_settings.TAG_TAXONOMY_CACHE_TTL = 3600

            taxonomy = await get_tag_taxonomy()

            assert isinstance(taxonomy, TagTaxonomy)
            assert "test" in taxonomy.domains
            assert "active" in taxonomy.status
            assert "good" in taxonomy.quality
