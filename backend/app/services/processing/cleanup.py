"""
Processing Cleanup Service

Provides cleanup functionality for content reprocessing to ensure
no orphaned records remain after processing is run again.

Cleans up:
- PostgreSQL: ProcessingRun records (cascade deletes concepts, connections,
  questions, followups)
- Neo4j: Content node relationships (preserves node for update)
- Spaced Rep Cards: Optionally deletes cards generated from the content
- Obsidian: Duplicate concept notes (files with _N.md suffix)

Also provides:
- Concept deduplication: Merges duplicate concept nodes in Neo4j

Obsidian Note Handling:
    Obsidian note cleanup is handled separately in obsidian_generator.py:
    - Main content notes: Updated in-place via get_path_for_update(), or
      deleted if title changes (see generate_obsidian_note lines 420-437)
    - Concept notes: Now update in-place instead of creating duplicates

Usage:
    from app.services.processing.cleanup import cleanup_before_reprocessing

    # Before running processing pipeline
    await cleanup_before_reprocessing(content_id, db_session, neo4j_client)

    # Deduplicate existing concepts in Neo4j
    from app.services.processing.cleanup import deduplicate_neo4j_concepts
    result = await deduplicate_neo4j_concepts(neo4j_client)

    # Clean up duplicate Obsidian concept files
    from app.services.processing.cleanup import cleanup_duplicate_concept_files
    result = await cleanup_duplicate_concept_files(dry_run=True)
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


async def deduplicate_neo4j_concepts(
    neo4j_client: Optional[Neo4jClient],
    dry_run: bool = False,
) -> dict:
    """
    Deduplicate existing concept nodes in Neo4j.

    Finds concepts with similar names (e.g., "Behavior Cloning" and
    "Behavior Cloning (BC)") and merges them into a single node.

    The merge process:
    1. Identifies clusters of concepts with matching canonical names
    2. For each cluster, keeps the concept with the best definition
    3. Redirects all relationships to the kept concept
    4. Deletes duplicate nodes

    Args:
        neo4j_client: Neo4j client instance
        dry_run: If True, only report what would be done without making changes

    Returns:
        Dictionary with deduplication stats:
        {
            "duplicates_found": int,
            "concepts_merged": int,
            "relationships_redirected": int,
        }
    """
    if not neo4j_client:
        logger.warning("No Neo4j client provided, skipping deduplication")
        return {"duplicates_found": 0, "concepts_merged": 0, "relationships_redirected": 0}

    from app.services.processing.concept_dedup import normalize_concept_name
    from app.config.settings import settings

    try:
        # Ensure client is initialized
        await neo4j_client._ensure_initialized()

        # Find all concepts grouped by canonical name
        find_duplicates_query = """
        MATCH (c:Concept)
        WITH c, toLower(
            CASE 
                WHEN c.canonical_name IS NOT NULL THEN c.canonical_name
                ELSE c.name
            END
        ) AS canonical
        WITH canonical, collect(c) AS concepts
        WHERE size(concepts) > 1
        RETURN canonical, 
               [c IN concepts | {id: c.id, name: c.name, definition: c.definition}] AS duplicates
        """

        duplicates_found = 0
        concepts_merged = 0
        relationships_redirected = 0

        async with neo4j_client._async_driver.session(
            database=settings.NEO4J_DATABASE
        ) as session:
            result = await session.run(find_duplicates_query)
            clusters = [record async for record in result]

            for cluster in clusters:
                canonical = cluster["canonical"]
                duplicates = cluster["duplicates"]
                duplicates_found += len(duplicates) - 1

                if dry_run:
                    logger.info(
                        f"Would merge {len(duplicates)} concepts under '{canonical}': "
                        f"{[d['name'] for d in duplicates]}"
                    )
                    continue

                # Find the best concept (longest definition)
                best = max(duplicates, key=lambda c: len(c.get("definition") or ""))
                best_id = best["id"]

                # Merge other concepts into the best one
                for dup in duplicates:
                    if dup["id"] == best_id:
                        continue

                    # Redirect incoming relationships
                    redirect_query = """
                    MATCH (c:Concept {id: $dup_id})<-[r]-(source)
                    MATCH (target:Concept {id: $best_id})
                    WHERE NOT (source)-[:CONTAINS]->(target)
                    CREATE (source)-[r2:CONTAINS]->(target)
                    SET r2 = properties(r)
                    DELETE r
                    RETURN count(r) AS redirected
                    """
                    redir_result = await session.run(
                        redirect_query, dup_id=dup["id"], best_id=best_id
                    )
                    redir_record = await redir_result.single()
                    if redir_record:
                        relationships_redirected += redir_record["redirected"]

                    # Redirect outgoing relationships
                    redirect_out_query = """
                    MATCH (c:Concept {id: $dup_id})-[r]->(target)
                    MATCH (source:Concept {id: $best_id})
                    WHERE NOT (source)-[:RELATES_TO]->(target)
                    CREATE (source)-[r2:RELATES_TO]->(target)
                    SET r2 = properties(r)
                    DELETE r
                    RETURN count(r) AS redirected
                    """
                    redir_out_result = await session.run(
                        redirect_out_query, dup_id=dup["id"], best_id=best_id
                    )
                    redir_out_record = await redir_out_result.single()
                    if redir_out_record:
                        relationships_redirected += redir_out_record["redirected"]

                    # Delete the duplicate concept
                    delete_query = """
                    MATCH (c:Concept {id: $dup_id})
                    DETACH DELETE c
                    """
                    await session.run(delete_query, dup_id=dup["id"])
                    concepts_merged += 1

                    logger.info(f"Merged concept '{dup['name']}' into '{best['name']}'")

        result = {
            "duplicates_found": duplicates_found,
            "concepts_merged": concepts_merged,
            "relationships_redirected": relationships_redirected,
        }

        if dry_run:
            logger.info(f"Dry run complete: {result}")
        else:
            logger.info(f"Deduplication complete: {result}")

        return result

    except Exception as e:
        logger.error(f"Failed to deduplicate concepts: {e}")
        return {"duplicates_found": 0, "concepts_merged": 0, "relationships_redirected": 0}


async def migrate_concepts_to_canonical_names(
    neo4j_client: Optional[Neo4jClient],
) -> int:
    """
    Migrate existing concept nodes to use canonical_name property.

    For concepts that were created before the canonical_name deduplication
    was implemented, this adds the canonical_name property based on their
    existing name.

    Args:
        neo4j_client: Neo4j client instance

    Returns:
        Number of concepts migrated
    """
    if not neo4j_client:
        logger.warning("No Neo4j client provided, skipping migration")
        return 0

    from app.services.processing.concept_dedup import get_canonical_name
    from app.config.settings import settings

    try:
        # Ensure client is initialized
        await neo4j_client._ensure_initialized()

        # Find concepts without canonical_name
        find_query = """
        MATCH (c:Concept)
        WHERE c.canonical_name IS NULL
        RETURN c.id AS id, c.name AS name
        """

        migrated = 0

        async with neo4j_client._async_driver.session(
            database=settings.NEO4J_DATABASE
        ) as session:
            result = await session.run(find_query)
            concepts = [record async for record in result]

            for concept in concepts:
                canonical = get_canonical_name(concept["name"]).lower()

                update_query = """
                MATCH (c:Concept {id: $id})
                SET c.canonical_name = $canonical_name
                """
                await session.run(
                    update_query, id=concept["id"], canonical_name=canonical
                )
                migrated += 1

        logger.info(f"Migrated {migrated} concepts to canonical_name format")
        return migrated

    except Exception as e:
        logger.error(f"Failed to migrate concepts: {e}")
        return 0


async def cleanup_duplicate_concept_files(
    dry_run: bool = False,
) -> dict:
    """
    Clean up duplicate concept note files in the Obsidian vault.

    Duplicate concept files have names like "Concept_1.md", "Concept_2.md", etc.
    This function identifies these duplicates and removes them, keeping only
    the base file (e.g., "Concept.md").

    If the base file doesn't exist, the first duplicate is renamed to become
    the base file.

    Args:
        dry_run: If True, only report what would be done without making changes

    Returns:
        Dictionary with cleanup stats:
        {
            "duplicates_found": int,
            "files_deleted": int,
            "files_renamed": int,
        }
    """
    import re
    from pathlib import Path
    from app.services.obsidian.vault import get_vault_manager

    try:
        vault = get_vault_manager()
        concept_folder = vault.get_concept_folder()

        if not concept_folder.exists():
            logger.warning(f"Concept folder does not exist: {concept_folder}")
            return {"duplicates_found": 0, "files_deleted": 0, "files_renamed": 0}

        # Pattern to match duplicate files: "Name_N.md" where N is a number
        duplicate_pattern = re.compile(r"^(.+)_(\d+)\.md$")

        # Group files by their base name
        base_files: dict[str, Path] = {}
        duplicate_files: dict[str, list[Path]] = {}

        for file_path in concept_folder.glob("*.md"):
            match = duplicate_pattern.match(file_path.name)
            if match:
                base_name = match.group(1)
                if base_name not in duplicate_files:
                    duplicate_files[base_name] = []
                duplicate_files[base_name].append(file_path)
            else:
                # Base file (no _N suffix)
                base_name = file_path.stem
                base_files[base_name] = file_path

        duplicates_found = sum(len(dups) for dups in duplicate_files.values())
        files_deleted = 0
        files_renamed = 0

        for base_name, duplicates in duplicate_files.items():
            # Sort duplicates by suffix number
            duplicates.sort(key=lambda p: int(duplicate_pattern.match(p.name).group(2)))

            if base_name in base_files:
                # Base file exists - delete all duplicates
                for dup_path in duplicates:
                    if dry_run:
                        logger.info(f"Would delete: {dup_path.name}")
                    else:
                        dup_path.unlink()
                        logger.info(f"Deleted duplicate: {dup_path.name}")
                    files_deleted += 1
            else:
                # No base file - rename first duplicate to base, delete rest
                first_dup = duplicates[0]
                base_path = concept_folder / f"{base_name}.md"

                if dry_run:
                    logger.info(f"Would rename: {first_dup.name} -> {base_path.name}")
                else:
                    first_dup.rename(base_path)
                    logger.info(f"Renamed: {first_dup.name} -> {base_path.name}")
                files_renamed += 1

                # Delete remaining duplicates
                for dup_path in duplicates[1:]:
                    if dry_run:
                        logger.info(f"Would delete: {dup_path.name}")
                    else:
                        dup_path.unlink()
                        logger.info(f"Deleted duplicate: {dup_path.name}")
                    files_deleted += 1

        result = {
            "duplicates_found": duplicates_found,
            "files_deleted": files_deleted,
            "files_renamed": files_renamed,
        }

        if dry_run:
            logger.info(f"Dry run complete: {result}")
        else:
            logger.info(f"Cleanup complete: {result}")

        return result

    except Exception as e:
        logger.error(f"Failed to cleanup duplicate concept files: {e}")
        return {"duplicates_found": 0, "files_deleted": 0, "files_renamed": 0}
