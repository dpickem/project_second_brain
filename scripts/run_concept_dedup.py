#!/usr/bin/env python3
"""
Run concept deduplication on existing data.

This script:
1. Migrates existing Neo4j concepts to use canonical_name property
2. Deduplicates Neo4j concept nodes with matching canonical names
3. Cleans up duplicate Obsidian concept note files (e.g., Concept_1.md, Concept_2.md)

Usage:
    # Dry run (preview changes without making them)
    python scripts/run_concept_dedup.py --dry-run

    # Actually run deduplication
    python scripts/run_concept_dedup.py

    # Skip specific steps
    python scripts/run_concept_dedup.py --skip-migration --skip-neo4j

    # Only clean up Obsidian files
    python scripts/run_concept_dedup.py --skip-migration --skip-neo4j
"""

import asyncio
import argparse
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_path))


async def main(
    dry_run: bool = False,
    skip_migration: bool = False,
    skip_neo4j: bool = False,
    skip_obsidian: bool = False,
):
    """Run concept deduplication."""
    from app.services.knowledge_graph import get_neo4j_client
    from app.services.processing.cleanup import (
        migrate_concepts_to_canonical_names,
        deduplicate_neo4j_concepts,
        cleanup_duplicate_concept_files,
    )

    neo4j_client = None

    try:
        # Step 1: Neo4j migration
        if not skip_migration and not skip_neo4j:
            print("Connecting to Neo4j...")
            neo4j_client = await get_neo4j_client()

            if not neo4j_client:
                print("WARNING: Could not connect to Neo4j. Skipping Neo4j steps.")
                skip_neo4j = True
            else:
                print("\n=== Step 1: Migrating concepts to canonical_name format ===")
                migrated = await migrate_concepts_to_canonical_names(neo4j_client)
                print(f"Migrated {migrated} concepts to canonical_name format")
        else:
            print("\n=== Step 1: Skipping migration ===")

        # Step 2: Neo4j deduplication
        if not skip_neo4j:
            if neo4j_client is None:
                print("Connecting to Neo4j...")
                neo4j_client = await get_neo4j_client()

            if neo4j_client:
                print("\n=== Step 2: Deduplicating Neo4j concepts ===")
                if dry_run:
                    print("(DRY RUN - no changes will be made)")

                result = await deduplicate_neo4j_concepts(neo4j_client, dry_run=dry_run)

                print(f"\nNeo4j Results:")
                print(f"  Duplicates found: {result['duplicates_found']}")
                print(f"  Concepts merged: {result['concepts_merged']}")
                print(f"  Relationships redirected: {result['relationships_redirected']}")
        else:
            print("\n=== Step 2: Skipping Neo4j deduplication ===")

        # Step 3: Obsidian file cleanup
        if not skip_obsidian:
            print("\n=== Step 3: Cleaning up duplicate Obsidian concept files ===")
            if dry_run:
                print("(DRY RUN - no changes will be made)")

            file_result = await cleanup_duplicate_concept_files(dry_run=dry_run)

            print(f"\nObsidian Results:")
            print(f"  Duplicate files found: {file_result['duplicates_found']}")
            print(f"  Files deleted: {file_result['files_deleted']}")
            print(f"  Files renamed: {file_result['files_renamed']}")
        else:
            print("\n=== Step 3: Skipping Obsidian cleanup ===")

        if dry_run:
            print("\n" + "=" * 50)
            print("DRY RUN COMPLETE - No changes were made.")
            print("To actually run, remove the --dry-run flag:")
            print("  python scripts/run_concept_dedup.py")

        return 0

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1

    finally:
        if neo4j_client:
            await neo4j_client.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Deduplicate concepts in Neo4j and Obsidian"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without making them",
    )
    parser.add_argument(
        "--skip-migration",
        action="store_true",
        help="Skip the Neo4j canonical_name migration step",
    )
    parser.add_argument(
        "--skip-neo4j",
        action="store_true",
        help="Skip all Neo4j operations",
    )
    parser.add_argument(
        "--skip-obsidian",
        action="store_true",
        help="Skip Obsidian file cleanup",
    )

    args = parser.parse_args()

    exit_code = asyncio.run(main(
        dry_run=args.dry_run,
        skip_migration=args.skip_migration,
        skip_neo4j=args.skip_neo4j,
        skip_obsidian=args.skip_obsidian,
    ))
    sys.exit(exit_code)
