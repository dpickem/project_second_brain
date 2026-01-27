"""
Processing Cleanup Service

Provides cleanup functionality for content reprocessing to ensure
no orphaned records remain after processing is run again.

Cleans up:
- PostgreSQL: ProcessingRun records (cascade deletes concepts, connections,
  questions, followups)
- Neo4j: Content node relationships (preserves node for update)
- Spaced Rep Cards: Optionally deletes cards generated from the content

Obsidian Note Handling:
    Obsidian note cleanup is handled separately in obsidian_generator.py:
    - Main content notes: Updated in-place via get_path_for_update(), or
      deleted if title changes (see generate_obsidian_note lines 420-437)
    - Concept notes: Intentionally preserved across sources since multiple
      content items can reference the same concept

Usage:
    from app.services.processing.cleanup import cleanup_before_reprocessing

    # Before running processing pipeline
    await cleanup_before_reprocessing(content_id, db_session, neo4j_client)
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Optional

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models_processing import ProcessingRun

if TYPE_CHECKING:
    from app.services.knowledge_graph.client import Neo4jClient

logger = logging.getLogger(__name__)


async def cleanup_processing_runs(
    content_pk: int,
    session: AsyncSession,
) -> int:
    """
    Delete all ProcessingRun records for a content item.

    This uses SQLAlchemy's cascade delete to automatically remove:
    - ConceptRecord entries
    - ConnectionRecord entries
    - QuestionRecord entries
    - FollowupRecord entries

    Args:
        content_pk: Primary key (integer) of the Content record
        session: SQLAlchemy async session

    Returns:
        Number of ProcessingRun records deleted
    """
    # Find all processing runs for this content
    result = await session.execute(
        select(ProcessingRun).where(ProcessingRun.content_id == content_pk)
    )
    runs = result.scalars().all()

    if not runs:
        logger.debug(f"No existing processing runs for content pk={content_pk}")
        return 0

    # Delete each run (cascade will handle related records)
    count = 0
    for run in runs:
        await session.delete(run)
        count += 1

    await session.flush()
    logger.info(f"Deleted {count} processing run(s) for content pk={content_pk}")
    return count


async def cleanup_neo4j_relationships(
    content_uuid: str,
    neo4j_client: Optional[Neo4jClient],
) -> int:
    """
    Delete outgoing relationships from a content node in Neo4j.

    Preserves the content node itself so it can be updated with new
    relationships during reprocessing.

    Args:
        content_uuid: Content UUID string
        neo4j_client: Neo4j client instance (or None to skip)

    Returns:
        Number of relationships deleted
    """
    if not neo4j_client:
        logger.debug("No Neo4j client provided, skipping relationship cleanup")
        return 0

    try:
        deleted = await neo4j_client.delete_content_relationships(content_uuid)
        if deleted > 0:
            logger.info(
                f"Deleted {deleted} Neo4j relationship(s) for content {content_uuid}"
            )
        return deleted
    except Exception as e:
        logger.warning(f"Failed to cleanup Neo4j relationships: {e}")
        return 0


async def cleanup_spaced_rep_cards(
    content_uuid: str,
    session: AsyncSession,
    delete_cards: bool = False,
) -> int:
    """
    Optionally delete spaced repetition cards for a content item.

    By default, cards are NOT deleted during reprocessing since users
    may have review history. Set delete_cards=True to force deletion.

    Args:
        content_uuid: Content UUID string
        session: SQLAlchemy async session
        delete_cards: If True, delete cards. If False, skip (default)

    Returns:
        Number of cards deleted (0 if delete_cards=False)
    """
    if not delete_cards:
        logger.debug("Card deletion disabled, preserving existing cards")
        return 0

    from app.db.models_learning import SpacedRepCard

    result = await session.execute(
        delete(SpacedRepCard).where(SpacedRepCard.content_id == content_uuid)
    )
    count = result.rowcount
    if count > 0:
        logger.info(f"Deleted {count} spaced rep card(s) for content {content_uuid}")
    return count


async def cleanup_before_reprocessing(
    content_pk: int,
    content_uuid: str,
    session: AsyncSession,
    neo4j_client: Optional[Neo4jClient] = None,
    delete_cards: bool = False,
) -> dict:
    """
    Perform full cleanup before reprocessing content.

    This ensures no orphaned records remain after reprocessing by:
    1. Deleting old ProcessingRun records (cascade deletes related records)
    2. Deleting Neo4j relationships (preserves node for update)
    3. Optionally deleting spaced repetition cards

    Args:
        content_pk: Primary key (integer) of the Content record
        content_uuid: Content UUID string
        session: SQLAlchemy async session
        neo4j_client: Neo4j client instance (optional)
        delete_cards: If True, also delete spaced rep cards

    Returns:
        Dictionary with cleanup counts:
        {
            "processing_runs": int,
            "neo4j_relationships": int,
            "cards": int
        }

    Example:
        >>> async with async_session_maker() as session:
        ...     cleanup_result = await cleanup_before_reprocessing(
        ...         content_pk=db_content.id,
        ...         content_uuid=content_id,
        ...         session=session,
        ...         neo4j_client=neo4j_client,
        ...     )
        ...     await session.commit()
    """
    logger.info(f"Starting cleanup before reprocessing for content {content_uuid}")

    # Clean up PostgreSQL records
    runs_deleted = await cleanup_processing_runs(content_pk, session)

    # Clean up Neo4j relationships
    neo4j_deleted = await cleanup_neo4j_relationships(content_uuid, neo4j_client)

    # Optionally clean up cards
    cards_deleted = await cleanup_spaced_rep_cards(
        content_uuid, session, delete_cards=delete_cards
    )

    result = {
        "processing_runs": runs_deleted,
        "neo4j_relationships": neo4j_deleted,
        "cards": cards_deleted,
    }

    logger.info(f"Cleanup completed for {content_uuid}: {result}")
    return result
