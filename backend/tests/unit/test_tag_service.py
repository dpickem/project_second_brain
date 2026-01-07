"""
Unit tests for TagService.

Tests the tag validation and synchronization service.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.db.models import Tag
from app.services.tag_service import InvalidTagError, TagService, validate_tags


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_db():
    """Create a mock database session."""
    mock = MagicMock()
    mock.execute = AsyncMock()
    mock.add = MagicMock()
    mock.flush = AsyncMock()
    mock.commit = AsyncMock()
    return mock


@pytest.fixture
def service(mock_db):
    """Create a TagService with mocked database."""
    return TagService(mock_db)


def make_mock_tags(names: list[str]) -> list[MagicMock]:
    """Helper to create mock Tag objects."""
    tags = []
    for i, name in enumerate(names):
        tag = MagicMock(spec=Tag)
        tag.name = name
        tag.id = i + 1
        tags.append(tag)
    return tags


def mock_scalars_result(mock_db, tags: list[MagicMock]):
    """Configure mock_db to return tags via scalars().all()."""
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = tags
    mock_db.execute = AsyncMock(return_value=mock_result)


def mock_scalar_one_result(mock_db, tag: MagicMock | None):
    """Configure mock_db to return a tag via scalar_one_or_none()."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = tag
    mock_db.execute = AsyncMock(return_value=mock_result)


def mock_fetchall_result(mock_db, rows: list[tuple]):
    """Configure mock_db to return rows via fetchall()."""
    mock_result = MagicMock()
    mock_result.fetchall.return_value = rows
    mock_db.execute = AsyncMock(return_value=mock_result)


# =============================================================================
# InvalidTagError Tests
# =============================================================================


class TestInvalidTagError:
    """Tests for InvalidTagError exception."""

    @pytest.mark.parametrize(
        "invalid_tags",
        [
            ["ml/invalid"],
            ["ml/invalid", "programming/nonexistent"],
            [],
        ],
        ids=["single", "multiple", "empty"],
    )
    def test_stores_invalid_tags(self, invalid_tags):
        """Test exception stores and displays invalid tags."""
        error = InvalidTagError(invalid_tags)
        assert error.invalid_tags == invalid_tags
        for tag in invalid_tags:
            assert tag in str(error)


# =============================================================================
# TagService.validate_tags Tests
# =============================================================================


class TestValidateTags:
    """Tests for tag validation."""

    @pytest.mark.asyncio
    async def test_empty_list_returns_empty(self, service, mock_db):
        """Empty input returns empty list without DB query."""
        result = await service.validate_tags([])
        assert result == []
        mock_db.execute.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "tags",
        [
            ["ml/transformers"],
            ["ml/transformers", "ml/attention"],
            ["z/last", "a/first", "m/middle"],
        ],
        ids=["single", "multiple", "preserves_order"],
    )
    async def test_valid_tags_return_input(self, service, mock_db, tags):
        """Valid tags return the same list, preserving order."""
        mock_scalars_result(mock_db, make_mock_tags(tags))
        result = await service.validate_tags(tags)
        assert result == tags

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "input_tags,existing,expected_invalid",
        [
            (["ml/transformers", "ml/bad"], ["ml/transformers"], ["ml/bad"]),
            (["bad1", "bad2"], [], ["bad1", "bad2"]),
        ],
        ids=["partial_missing", "all_missing"],
    )
    async def test_missing_tags_raise_error(
        self, service, mock_db, input_tags, existing, expected_invalid
    ):
        """Missing tags raise InvalidTagError with correct invalid list."""
        mock_scalars_result(mock_db, make_mock_tags(existing))

        with pytest.raises(InvalidTagError) as exc_info:
            await service.validate_tags(input_tags)

        assert set(exc_info.value.invalid_tags) == set(expected_invalid)


# =============================================================================
# TagService.validate_topic Tests
# =============================================================================


class TestValidateTopic:
    """Tests for single topic validation."""

    @pytest.mark.asyncio
    async def test_existing_topic_returns_topic(self, service, mock_db):
        """Existing topic returns the topic string."""
        mock_scalars_result(mock_db, make_mock_tags(["ml/transformers"]))
        result = await service.validate_topic("ml/transformers")
        assert result == "ml/transformers"

    @pytest.mark.asyncio
    async def test_missing_topic_raises_error(self, service, mock_db):
        """Missing topic raises InvalidTagError."""
        mock_scalars_result(mock_db, [])

        with pytest.raises(InvalidTagError) as exc_info:
            await service.validate_topic("nonexistent/topic")

        assert "nonexistent/topic" in exc_info.value.invalid_tags


# =============================================================================
# TagService.get_tag Tests
# =============================================================================


class TestGetTag:
    """Tests for getting a single tag."""

    @pytest.mark.asyncio
    async def test_existing_tag_returns_tag_object(self, service, mock_db):
        """Existing tag returns the Tag object."""
        mock_tag = make_mock_tags(["ml/transformers"])[0]
        mock_scalar_one_result(mock_db, mock_tag)

        result = await service.get_tag("ml/transformers")

        assert result is mock_tag
        assert result.name == "ml/transformers"

    @pytest.mark.asyncio
    async def test_nonexistent_tag_raises_error(self, service, mock_db):
        """Non-existent tag raises InvalidTagError."""
        mock_scalar_one_result(mock_db, None)

        with pytest.raises(InvalidTagError) as exc_info:
            await service.get_tag("nonexistent/tag")

        assert "nonexistent/tag" in exc_info.value.invalid_tags


# =============================================================================
# TagService.sync_taxonomy_to_db Tests
# =============================================================================


class TestSyncTaxonomyToDb:
    """Tests for syncing taxonomy to database."""

    @pytest.fixture
    def mock_taxonomy(self):
        """Create a mock taxonomy with 3 tags."""
        taxonomy = MagicMock()
        taxonomy.all_tags = ["ml/transformers", "ml/attention", "programming/python"]
        return taxonomy

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "existing_tags,expected_created",
        [
            ([], 3),  # none exist -> create all 3
            ([("ml/transformers",)], 2),  # 1 exists -> create 2
            (
                [("ml/transformers",), ("ml/attention",), ("programming/python",)],
                0,
            ),  # all exist
        ],
        ids=["none_exist", "partial_exist", "all_exist"],
    )
    async def test_sync_creates_missing_tags(
        self, service, mock_db, mock_taxonomy, existing_tags, expected_created
    ):
        """Sync creates only missing tags."""
        with patch(
            "app.services.tag_service.get_tag_taxonomy",
            new_callable=AsyncMock,
            return_value=mock_taxonomy,
        ):
            mock_fetchall_result(mock_db, existing_tags)
            service._create_tags = AsyncMock(return_value=[])

            result = await service.sync_taxonomy_to_db()

        assert result == expected_created

        if expected_created > 0:
            service._create_tags.assert_called_once()
            created = service._create_tags.call_args[0][0]
            assert len(created) == expected_created
            mock_db.commit.assert_called_once()
        else:
            mock_db.commit.assert_not_called()


# =============================================================================
# TagService.get_all_tags Tests
# =============================================================================


class TestGetAllTags:
    """Tests for getting all tags."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "tag_names,expected_count",
        [
            ([], 0),
            (["a/first", "b/second", "c/third"], 3),
        ],
        ids=["empty", "multiple"],
    )
    async def test_returns_tag_list(self, service, mock_db, tag_names, expected_count):
        """Returns list of tags from database."""
        mock_scalars_result(mock_db, make_mock_tags(tag_names))
        result = await service.get_all_tags()
        assert len(result) == expected_count


# =============================================================================
# Convenience Function Tests
# =============================================================================


class TestConvenienceFunction:
    """Tests for the module-level validate_tags function."""

    @pytest.mark.asyncio
    async def test_delegates_to_service(self, mock_db):
        """Convenience function delegates to TagService."""
        mock_scalars_result(mock_db, make_mock_tags(["ml/transformers"]))
        result = await validate_tags(mock_db, ["ml/transformers"])
        assert result == ["ml/transformers"]

    @pytest.mark.asyncio
    async def test_raises_on_invalid(self, mock_db):
        """Convenience function raises InvalidTagError for invalid tags."""
        mock_scalars_result(mock_db, [])
        with pytest.raises(InvalidTagError):
            await validate_tags(mock_db, ["invalid/tag"])

    @pytest.mark.asyncio
    async def test_empty_list(self, mock_db):
        """Empty list returns empty list."""
        result = await validate_tags(mock_db, [])
        assert result == []
