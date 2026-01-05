#!/usr/bin/env python3
"""
Reset All Databases and Vault

Resets all databases (PostgreSQL, Redis, Neo4j) and the Obsidian vault
to their initial empty state. Use this script to:

    - Start fresh during development
    - Clean up after testing
    - Reset a corrupted state
    - Prepare for a clean deployment

WHAT GETS RESET:

    PostgreSQL  All tables dropped (including alembic_version migration history).
                Migrations are automatically applied after reset to restore schema.

    Redis       All keys flushed via FLUSHALL command.
                Clears task queues (Celery), cache data, and session storage.

    Neo4j       All nodes, relationships, constraints, and indexes deleted.
                The knowledge graph is completely emptied.

    Vault       All markdown notes and files removed from Obsidian vault.
                With --keep-structure: folders preserved, only files deleted.
                Without: entire directory removed (run setup_vault.py to recreate).

    Uploads     All uploaded files removed from the staging directory.
                Original source files (PDFs, images, audio) are permanently deleted.

USAGE:

    # Reset everything (interactive confirmation required)
    python scripts/setup/reset_all.py

    # Reset everything without confirmation (DANGEROUS - use in scripts only)
    python scripts/setup/reset_all.py --yes

    # Preview what would be reset (safe - no changes made)
    python scripts/setup/reset_all.py --dry-run

    # Reset specific components only
    python scripts/setup/reset_all.py --postgres-only
    python scripts/setup/reset_all.py --redis-only
    python scripts/setup/reset_all.py --neo4j-only
    python scripts/setup/reset_all.py --vault-only
    python scripts/setup/reset_all.py --uploads-only

    # Combine component flags
    python scripts/setup/reset_all.py --postgres-only --redis-only

    # Reset vault but keep folder structure (delete files only)
    python scripts/setup/reset_all.py --vault-only --keep-structure

    # Custom paths (override environment/config)
    python scripts/setup/reset_all.py --data-dir ~/my/data
    python scripts/setup/reset_all.py --vault-path ~/my/vault

ENVIRONMENT VARIABLES:

    Database connections (loaded from .env or environment):
        POSTGRES_HOST       PostgreSQL hostname (default: localhost)
        POSTGRES_PORT       PostgreSQL port (default: 5432)
        POSTGRES_USER       PostgreSQL username
        POSTGRES_PASSWORD   PostgreSQL password
        POSTGRES_DB         PostgreSQL database name
        REDIS_URL           Redis connection URL (default: redis://localhost:6379/0)
        NEO4J_URI           Neo4j bolt URI (default: bolt://localhost:7687)
        NEO4J_USER          Neo4j username (default: neo4j)
        NEO4J_PASSWORD      Neo4j password

    Paths (priority: CLI args > env vars > config/default.yaml):
        DATA_DIR            Root data directory containing all subdirectories
        OBSIDIAN_VAULT_PATH Direct path to Obsidian vault

SAFETY FEATURES:

    - Interactive confirmation: Must type 'RESET' to proceed (bypass with --yes)
    - Dry-run mode: See exactly what would be reset without making changes
    - Component selection: Reset only what you need, leave the rest intact
    - Keep structure: For vault, remove content but preserve folder organization

POST-RESET STEPS:

    PostgreSQL migrations are applied automatically after reset.
    To skip automatic migrations, use: --no-migrate

    After resetting vault (without --keep-structure):
        python scripts/setup/setup_vault.py

    After full reset, to set up everything fresh:
        python scripts/setup/setup_all.py

WARNING:
    This operation is DESTRUCTIVE and cannot be undone!
    All data will be permanently deleted.
    Always use --dry-run first to verify what will be reset.
"""

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

# Add scripts/setup directory to path for _common import
_SCRIPTS_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _SCRIPTS_DIR.parent.parent
sys.path.insert(0, str(_SCRIPTS_DIR))
# Add project root for backend.app imports
sys.path.insert(0, str(_PROJECT_ROOT))
# Add backend directory (backend modules use relative imports like 'from app.config')
sys.path.insert(0, str(_PROJECT_ROOT / "backend"))

# Third-party imports (after path setup)
import redis as redis_lib
from neo4j import GraphDatabase
from sqlalchemy import create_engine, text

# Local imports (after path setup)
from _common import add_common_args, resolve_paths
from app.config.settings import settings


def reset_postgresql(dry_run: bool = False) -> bool:
    """
    Reset PostgreSQL database by dropping all tables.

    Returns True on success, False on failure.
    """
    print("\n🐘 Resetting PostgreSQL...")

    if dry_run:
        print(f"   Would connect to: {settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}")
        print(f"   Would drop all tables in database: {settings.POSTGRES_DB}")
        return True

    try:
        engine = create_engine(settings.POSTGRES_URL_SYNC)

        with engine.connect() as conn:
            # Disable foreign key checks temporarily
            conn.execute(text("SET session_replication_role = 'replica';"))

            # Get all table names
            result = conn.execute(
                text(
                    """
                SELECT tablename FROM pg_tables
                WHERE schemaname = 'public'
            """
                )
            )
            tables = [row[0] for row in result]

            if not tables:
                print("   ℹ️  No tables found - database already empty")
            else:
                # Drop all tables
                for table in tables:
                    conn.execute(text(f'DROP TABLE IF EXISTS "{table}" CASCADE'))
                    print(f"   🗑️  Dropped table: {table}")

                # Also drop alembic version table if exists
                conn.execute(text("DROP TABLE IF EXISTS alembic_version CASCADE"))

            # Re-enable foreign key checks
            conn.execute(text("SET session_replication_role = 'origin';"))
            conn.commit()

        print(f"   ✅ PostgreSQL reset complete ({len(tables)} tables dropped)")
        return True

    except Exception as e:
        print(f"   ❌ PostgreSQL reset failed: {e}")
        return False


def run_migrations(dry_run: bool = False) -> bool:
    """
    Run Alembic migrations to recreate the database schema.

    Returns True on success, False on failure.
    """
    print("\n📦 Applying database migrations...")

    if dry_run:
        print("   Would run: alembic upgrade head")
        return True

    try:
        result = subprocess.run(
            ["alembic", "upgrade", "head"],
            cwd=_PROJECT_ROOT / "backend",
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            print("   ✅ Migrations applied successfully")
            # Show migration output if any
            if result.stdout.strip():
                for line in result.stdout.strip().split("\n"):
                    if line.strip():
                        print(f"      {line.strip()}")
            return True
        else:
            print(f"   ❌ Migration failed:")
            if result.stderr.strip():
                for line in result.stderr.strip().split("\n"):
                    print(f"      {line}")
            return False

    except FileNotFoundError:
        print("   ❌ Alembic not found. Is it installed?")
        print("   💡 Try: pip install alembic")
        return False
    except Exception as e:
        print(f"   ❌ Migration failed: {e}")
        return False


def reset_redis(dry_run: bool = False) -> bool:
    """
    Reset Redis by flushing all data.

    Returns True on success, False on failure.
    """
    print("\n🔴 Resetting Redis...")

    if dry_run:
        print(f"   Would connect to: {settings.REDIS_URL}")
        print("   Would flush all databases (FLUSHALL)")
        return True

    try:
        # Parse Redis URL
        client = redis_lib.from_url(settings.REDIS_URL)

        # Get info before flush
        info = client.info("keyspace")
        key_count = sum(
            db_info.get("keys", 0) for db_info in info.values() if isinstance(db_info, dict)
        )

        # Flush all databases
        client.flushall()

        print(f"   ✅ Redis reset complete ({key_count} keys flushed)")
        return True

    except redis_lib.ConnectionError as e:
        print(f"   ❌ Redis connection failed: {e}")
        print("   💡 Is Redis running? Try: docker-compose up -d redis")
        return False
    except Exception as e:
        print(f"   ❌ Redis reset failed: {e}")
        return False


def reset_neo4j(dry_run: bool = False) -> bool:
    """
    Reset Neo4j by deleting all nodes and relationships.

    Returns True on success, False on failure.
    """
    print("\n🔵 Resetting Neo4j...")

    if dry_run:
        print(f"   Would connect to: {settings.NEO4J_URI}")
        print("   Would delete all nodes and relationships")
        return True

    try:
        driver = GraphDatabase.driver(
            settings.NEO4J_URI,
            auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
        )

        with driver.session() as session:
            # Get counts before deletion
            result = session.run("MATCH (n) RETURN count(n) as count")
            node_count = result.single()["count"]

            result = session.run("MATCH ()-[r]->() RETURN count(r) as count")
            rel_count = result.single()["count"]

            # Delete all nodes and relationships
            # Using DETACH DELETE to handle relationships automatically
            session.run("MATCH (n) DETACH DELETE n")

            # Also drop all constraints and indexes
            constraints = session.run("SHOW CONSTRAINTS")
            for constraint in constraints:
                constraint_name = constraint.get("name")
                if constraint_name:
                    try:
                        session.run(f"DROP CONSTRAINT {constraint_name}")
                        print(f"   🗑️  Dropped constraint: {constraint_name}")
                    except Exception:
                        pass  # Constraint might not exist

            indexes = session.run("SHOW INDEXES")
            for index in indexes:
                index_name = index.get("name")
                # Skip internal indexes
                if index_name and not index_name.startswith("constraint"):
                    try:
                        session.run(f"DROP INDEX {index_name}")
                        print(f"   🗑️  Dropped index: {index_name}")
                    except Exception:
                        pass  # Index might not exist

        driver.close()

        print(f"   ✅ Neo4j reset complete ({node_count} nodes, {rel_count} relationships deleted)")
        return True

    except Exception as e:
        print(f"   ❌ Neo4j reset failed: {e}")
        print("   💡 Is Neo4j running? Try: docker-compose up -d neo4j")
        return False


def reset_vault(vault_path: Path, keep_structure: bool = False, dry_run: bool = False) -> bool:
    """
    Reset Obsidian vault by removing all content.

    Args:
        vault_path: Path to the Obsidian vault
        keep_structure: If True, preserves folder structure but removes files
        dry_run: If True, only show what would be done

    Returns True on success, False on failure.
    """
    print("\n📁 Resetting Obsidian Vault...")
    print(f"   Path: {vault_path}")

    if not vault_path.exists():
        print("   ℹ️  Vault directory does not exist - nothing to reset")
        return True

    if dry_run:
        if keep_structure:
            print("   Would remove all files but keep folder structure")
        else:
            print("   Would remove entire vault directory")
        return True

    try:
        if keep_structure:
            # Remove all files but keep directories
            file_count = 0
            for item in vault_path.rglob("*"):
                if item.is_file():
                    # Keep .gitkeep files to preserve empty directories
                    if item.name == ".gitkeep":
                        continue
                    item.unlink()
                    file_count += 1

            print(f"   ✅ Vault reset complete ({file_count} files removed, structure preserved)")
        else:
            # Remove entire vault directory
            shutil.rmtree(vault_path)
            print("   ✅ Vault directory removed completely")
            print("   💡 Run 'python scripts/setup/setup_vault.py' to recreate structure")

        return True

    except PermissionError as e:
        print(f"   ❌ Permission denied: {e}")
        return False
    except Exception as e:
        print(f"   ❌ Vault reset failed: {e}")
        return False


def reset_uploads(data_dir: Path, dry_run: bool = False) -> bool:
    """
    Reset uploads directory by removing all uploaded files.

    Returns True on success, False on failure.
    """
    uploads_path = data_dir / "uploads"
    print("\n📤 Resetting Uploads Directory...")
    print(f"   Path: {uploads_path}")

    if not uploads_path.exists():
        print("   ℹ️  Uploads directory does not exist - nothing to reset")
        return True

    if dry_run:
        print("   Would remove all uploaded files")
        return True

    try:
        file_count = 0
        for item in uploads_path.rglob("*"):
            if item.is_file():
                item.unlink()
                file_count += 1

        # Remove empty subdirectories
        for item in sorted(uploads_path.rglob("*"), reverse=True):
            if item.is_dir() and not any(item.iterdir()):
                item.rmdir()

        print(f"   ✅ Uploads reset complete ({file_count} files removed)")
        return True

    except Exception as e:
        print(f"   ❌ Uploads reset failed: {e}")
        return False


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Reset all databases and vault to initial empty state",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/setup/reset_all.py                    # Reset everything (interactive)
  python scripts/setup/reset_all.py --yes              # Reset everything (no confirmation)
  python scripts/setup/reset_all.py --postgres-only    # Reset only PostgreSQL
  python scripts/setup/reset_all.py --vault-only --keep-structure  # Clear vault files only
        """,
    )

    add_common_args(parser)

    # Confirmation flags
    parser.add_argument(
        "--yes",
        "-y",
        action="store_true",
        help="Skip confirmation prompt (dangerous!)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be reset without actually doing it",
    )

    # Component selection flags
    parser.add_argument(
        "--postgres-only",
        action="store_true",
        help="Reset only PostgreSQL database",
    )
    parser.add_argument(
        "--redis-only",
        action="store_true",
        help="Reset only Redis cache",
    )
    parser.add_argument(
        "--neo4j-only",
        action="store_true",
        help="Reset only Neo4j graph database",
    )
    parser.add_argument(
        "--vault-only",
        action="store_true",
        help="Reset only Obsidian vault",
    )
    parser.add_argument(
        "--uploads-only",
        action="store_true",
        help="Reset only uploads directory",
    )

    # Vault options
    parser.add_argument(
        "--keep-structure",
        action="store_true",
        help="When resetting vault, keep folder structure but remove files",
    )

    # PostgreSQL options
    parser.add_argument(
        "--no-migrate",
        action="store_true",
        help="Skip running migrations after PostgreSQL reset",
    )

    args = parser.parse_args()

    # Resolve paths from config
    config, data_dir, vault_path = resolve_paths(args)

    # Determine what to reset
    reset_all = not any(
        [
            args.postgres_only,
            args.redis_only,
            args.neo4j_only,
            args.vault_only,
            args.uploads_only,
        ]
    )

    reset_postgres = reset_all or args.postgres_only
    reset_redis_flag = reset_all or args.redis_only
    reset_neo4j_flag = reset_all or args.neo4j_only
    reset_vault_flag = reset_all or args.vault_only
    reset_uploads_flag = reset_all or args.uploads_only

    # Display what will be reset
    print("=" * 60)
    print("🔄 SECOND BRAIN RESET")
    print("=" * 60)

    if args.dry_run:
        print("🔍 DRY RUN MODE - No changes will be made\n")

    print("Components to reset:")
    if reset_postgres:
        migrate_note = "" if args.no_migrate else " + migrations"
        print(f"  • PostgreSQL (all tables{migrate_note})")
    if reset_redis_flag:
        print("  • Redis (all keys)")
    if reset_neo4j_flag:
        print("  • Neo4j (all nodes and relationships)")
    if reset_vault_flag:
        structure_note = " (keeping structure)" if args.keep_structure else " (complete removal)"
        print(f"  • Obsidian Vault{structure_note}")
        print(f"    Path: {vault_path}")
    if reset_uploads_flag:
        print(f"  • Uploads directory")
        print(f"    Path: {data_dir / 'uploads'}")

    print()

    # Confirmation prompt
    if not args.dry_run and not args.yes:
        print("⚠️  WARNING: This operation is DESTRUCTIVE and cannot be undone!")
        print("   All data will be permanently deleted.\n")

        try:
            response = input("Type 'RESET' to confirm: ")
            if response != "RESET":
                print("\n❌ Reset cancelled")
                sys.exit(1)
        except KeyboardInterrupt:
            print("\n\n❌ Reset cancelled")
            sys.exit(1)

    # Perform resets
    results = []

    if reset_postgres:
        postgres_success = reset_postgresql(args.dry_run)
        results.append(("PostgreSQL", postgres_success))

        # Run migrations if postgres reset succeeded and --no-migrate not specified
        if postgres_success and not args.no_migrate:
            migration_success = run_migrations(args.dry_run)
            results.append(("Migrations", migration_success))

    if reset_redis_flag:
        results.append(("Redis", reset_redis(args.dry_run)))

    if reset_neo4j_flag:
        results.append(("Neo4j", reset_neo4j(args.dry_run)))

    if reset_vault_flag:
        results.append(
            ("Vault", reset_vault(vault_path, args.keep_structure, args.dry_run))
        )

    if reset_uploads_flag:
        results.append(("Uploads", reset_uploads(data_dir, args.dry_run)))

    # Summary
    print("\n" + "=" * 60)
    print("📊 RESET SUMMARY")
    print("=" * 60)

    success_count = 0
    failure_count = 0

    for name, success in results:
        if success:
            print(f"  ✅ {name}")
            success_count += 1
        else:
            print(f"  ❌ {name}")
            failure_count += 1

    print()

    if failure_count > 0:
        print(f"⚠️  {failure_count} component(s) failed to reset")
        sys.exit(1)
    else:
        if args.dry_run:
            print("🔍 Dry run complete - no changes were made")
        else:
            print("🎉 All components reset successfully!")

            if reset_vault_flag and not args.keep_structure:
                print("\n💡 To recreate vault structure, run:")
                print("   python scripts/setup/setup_vault.py")


if __name__ == "__main__":
    main()
