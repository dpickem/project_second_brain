"""
Tag Service

Provides tag validation against the database Tag table and utilities
for synchronizing the YAML taxonomy to the database.

This service ensures referential consistency between tags used in
SpacedRepCards/Exercises and the canonical Tag table.

Usage:
    from app.services.tag_service import TagService

    service = TagService(db)

    # Validate tags exist (raises if invalid)
    await service.validate_tags(["ml/transformers", "ml/attention"])

    # Sync YAML taxonomy to database
    await service.sync_taxonomy_to_db()
"""

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Tag
from app.services.processing.stages.taxonomy_loader import get_tag_taxonomy

logger = logging.getLogger(__name__)


class InvalidTagError(Exception):
    """Raised when tags are not found in the database."""

    def __init__(self, invalid_tags: list[str]):
        self.invalid_tags = invalid_tags
        super().__init__(f"Invalid tags not in database: {invalid_tags}")


class TagService:
    """
    Service for tag validation and management.

    Validates tags against the database Tag table to ensure
    referential consistency. Use sync_taxonomy_to_db() to populate
    tags from the YAML taxonomy file.
    """

    def __init__(self, db: AsyncSession):
        """Initialize tag service."""
        self.db = db

    async def validate_tags(self, tags: list[str]) -> list[str]:
        """
        Validate that all tags exist in the database.

        Args:
            tags: List of tag strings to validate

        Returns:
            List of validated tag strings (same as input if all valid)

        Raises:
            InvalidTagError: If any tags don't exist in the database
        """
        if not tags:
            return []

        # Get existing tags from database
        existing = await self._get_existing_tags(tags)
        existing_names = {t.name for t in existing}

        # Find missing tags
        missing = [t for t in tags if t not in existing_names]

        if missing:
            raise InvalidTagError(missing)

        return tags

    async def validate_topic(self, topic: str) -> str:
        """
        Validate a single topic string.

        Convenience wrapper around validate_tags for single topic validation.

        Args:
            topic: Topic string to validate

        Returns:
            Validated topic string

        Raises:
            InvalidTagError: If topic is invalid
        """
        await self.validate_tags([topic])
        return topic

    async def get_tag(self, tag_name: str) -> Tag:
        """
        Get a tag by name.

        Tags must exist in the database. Use sync_taxonomy_to_db() to populate
        tags from the YAML taxonomy file.

        Args:
            tag_name: Tag name to retrieve

        Returns:
            Tag database object

        Raises:
            InvalidTagError: If tag does not exist in database
        """
        result = await self.db.execute(select(Tag).where(Tag.name == tag_name))
        tag = result.scalar_one_or_none()

        if tag:
            return tag

        raise InvalidTagError([tag_name])

    async def sync_taxonomy_to_db(self) -> int:
        """
        Synchronize YAML taxonomy to database Tag table.

        Creates any tags from the taxonomy that don't exist in the database.
        Does NOT delete tags that are no longer in taxonomy.

        Returns:
            Number of tags created
        """
        taxonomy = await get_tag_taxonomy()
        all_tags = taxonomy.all_tags

        # Get existing tags
        result = await self.db.execute(select(Tag.name))
        existing_names = {row[0] for row in result.fetchall()}

        # Find missing
        missing = [t for t in all_tags if t not in existing_names]

        if not missing:
            logger.info("Tag table already in sync with taxonomy")
            return 0

        # Create missing tags
        await self._create_tags(missing)
        await self.db.commit()

        logger.info(f"Synced taxonomy to database: created {len(missing)} tags")
        return len(missing)

    async def get_all_tags(self) -> list[Tag]:
        """Get all tags from the database."""
        result = await self.db.execute(select(Tag).order_by(Tag.name))
        return list(result.scalars().all())

    async def _get_existing_tags(self, tag_names: list[str]) -> list[Tag]:
        """Get existing tags by name."""
        if not tag_names:
            return []

        result = await self.db.execute(select(Tag).where(Tag.name.in_(tag_names)))
        return list(result.scalars().all())

    async def _create_tags(self, tag_names: list[str]) -> list[Tag]:
        """Create multiple tags."""
        tags = []
        for name in tag_names:
            tag = Tag(name=name)
            self.db.add(tag)
            tags.append(tag)

        await self.db.flush()
        return tags


# Convenience function for use without explicit service instantiation
async def validate_tags(db: AsyncSession, tags: list[str]) -> list[str]:
    """
    Validate tags against the database.

    Args:
        db: Database session
        tags: List of tag strings

    Returns:
        List of validated tags

    Raises:
        InvalidTagError: If tags don't exist in database
    """
    service = TagService(db)
    return await service.validate_tags(tags)

