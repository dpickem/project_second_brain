#!/usr/bin/env python3
"""
End-to-End Content Processing Script

Run the full LLM processing pipeline on ingested content.

This script processes content through all 7 stages:
1. Content Analysis - Determine type, domain, complexity
2. Summarization - Generate brief, standard, and detailed summaries
3. Concept Extraction - Extract key concepts, findings, entities
4. Tagging - Assign tags from controlled vocabulary
5. Connection Discovery - Find relationships to existing knowledge
6. Follow-up Generation - Create actionable learning tasks
7. Question Generation - Create mastery questions

Setup:
    1. Ensure PostgreSQL is running (docker-compose up -d postgres)
    2. Copy .env.example to .env in the project root and fill in API keys
    3. Run any command below

Usage:
    # List all content in the database
    python run_processing.py list
    python run_processing.py list --status pending
    python run_processing.py list --status all

    # Process specific content by UUID
    python run_processing.py process <content_uuid>

    # Process all pending content
    python run_processing.py process-pending
    python run_processing.py process-pending --limit 10

    # Reprocess already-processed content (force reprocess)
    python run_processing.py process <content_uuid> --force

    # Skip specific stages
    python run_processing.py process <content_uuid> --no-summaries --no-questions

    # Dry run (show what would be processed without actually processing)
    python run_processing.py process-pending --dry-run

Environment Variables (set in .env or environment):
    Required:
    - POSTGRES_URL: PostgreSQL connection string
    - OPENAI_API_KEY: For LLM processing

    Optional:
    - NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD: For connection discovery
    - OBSIDIAN_VAULT_PATH: For Obsidian note generation
    - DEBUG: Enable verbose logging

Example:
    # First, ingest some content using run_pipeline.py
    python scripts/pipelines/run_pipeline.py article https://example.com/post

    # Then process it
    python scripts/run_processing.py process-pending
"""

import argparse
import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from typing import Optional

# Add backend to path for imports (must be before app.* imports)
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from dotenv import load_dotenv

# Load environment variables from project root .env
project_root = Path(__file__).parent.parent
if (project_root / ".env").exists():
    load_dotenv(project_root / ".env")
else:
    load_dotenv(project_root / "backend" / ".env")

# Override DEBUG to suppress SQLAlchemy echo (engine uses echo=settings.DEBUG)
os.environ["DEBUG"] = "false"

# Set local Obsidian vault path (Docker uses /vault mount point)
# Always override for local script execution - .env may have Docker's /vault path
os.environ["OBSIDIAN_VAULT_PATH"] = os.path.expanduser(
    "~/workspace/obsidian/second_brain/obsidian"
)

# App imports (after sys.path setup and env loading)
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.db.base import async_session_maker
from app.db.models import Content as DBContent, ContentStatus
from app.models.content import ProcessingStatus
from app.models.processing import ProcessingResult
from app.services.storage import load_content, update_status
from app.services.processing import process_content, PipelineConfig
from app.services.knowledge_graph.client import get_neo4j_client


async def ensure_neo4j_indexes() -> None:
    """Ensure Neo4j vector indexes exist (creates them if missing)."""
    try:
        client = await get_neo4j_client()
        await client.setup_indexes()
    except Exception as e:
        logging.warning(f"Could not setup Neo4j indexes (Neo4j may not be running): {e}")


def setup_logging(debug: bool = False) -> None:
    """Configure logging based on debug flag."""
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%H:%M:%S",
    )
    # Reduce noise from httpx and other libs (unless --debug)
    if not debug:
        logging.getLogger("httpx").setLevel(logging.WARNING)
        logging.getLogger("httpcore").setLevel(logging.WARNING)
        logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
        logging.getLogger("sqlalchemy.pool").setLevel(logging.WARNING)


# =============================================================================
# List Command
# =============================================================================


async def list_content(
    status_filter: Optional[str] = None,
    limit: int = 100,
    output_format: str = "summary",
) -> None:
    """List content in the database."""
    async with async_session_maker() as session:
        query = select(DBContent).options(selectinload(DBContent.annotations))

        # Apply status filter
        if status_filter and status_filter != "all":
            try:
                status_enum = ContentStatus(status_filter.upper())
                query = query.where(DBContent.status == status_enum)
            except ValueError:
                print(f"❌ Invalid status: {status_filter}")
                print(f"   Valid options: pending, processing, processed, failed, all")
                sys.exit(1)

        query = query.order_by(DBContent.created_at.desc()).limit(limit)
        result = await session.execute(query)
        items = result.scalars().all()

        if not items:
            print("📭 No content found matching criteria")
            return

        # Get counts by status
        count_query = select(DBContent.status, func.count(DBContent.id)).group_by(
            DBContent.status
        )
        count_result = await session.execute(count_query)
        status_counts = {row[0].value: row[1] for row in count_result.all()}

        print("\n" + "=" * 70)
        print("📚 CONTENT DATABASE")
        print("=" * 70)
        print(f"\nStatus counts:")
        for status, count in sorted(status_counts.items()):
            emoji = {
                "PENDING": "⏳",
                "PROCESSING": "🔄",
                "PROCESSED": "✅",
                "FAILED": "❌",
            }.get(status, "❓")
            print(f"  {emoji} {status}: {count}")

        print(f"\n{'─' * 70}")
        print(f"Showing {len(items)} items" + (f" (filtered by: {status_filter})" if status_filter else ""))
        print(f"{'─' * 70}\n")

        if output_format == "json":
            data = [
                {
                    "content_uuid": item.content_uuid,
                    "title": item.title,
                    "content_type": item.content_type,
                    "status": item.status.value if hasattr(item.status, "value") else str(item.status),
                    "created_at": item.created_at.isoformat() if item.created_at else None,
                    "processed_at": item.processed_at.isoformat() if item.processed_at else None,
                    "source_url": item.source_url,
                }
                for item in items
            ]
            print(json.dumps(data, indent=2))
        else:
            for item in items:
                status_str = item.status.value if hasattr(item.status, "value") else str(item.status)
                emoji = {
                    "PENDING": "⏳",
                    "PROCESSING": "🔄",
                    "PROCESSED": "✅",
                    "FAILED": "❌",
                }.get(status_str, "❓")

                title_display = item.title[:50] + "..." if len(item.title or "") > 50 else item.title
                print(f"{emoji} [{item.content_type}] {title_display}")
                print(f"   ID: {item.content_uuid}")
                print(f"   Status: {status_str}")
                if item.source_url:
                    url_display = item.source_url[:60] + "..." if len(item.source_url) > 60 else item.source_url
                    print(f"   URL: {url_display}")
                if item.created_at:
                    print(f"   Created: {item.created_at.strftime('%Y-%m-%d %H:%M')}")
                print()


# =============================================================================
# Process Command
# =============================================================================


def format_processing_result(result: ProcessingResult) -> str:
    """Format processing result as a human-readable summary."""
    lines = [
        "=" * 60,
        f"📊 PROCESSING RESULT",
        "=" * 60,
        f"\nContent ID: {result.content_id}",
        f"⏱️  Processing time: {result.processing_time_seconds:.2f}s",
        f"💰 Estimated cost: ${result.estimated_cost_usd:.4f}",
    ]

    # Analysis
    lines.append(f"\n📋 Analysis:")
    lines.append(f"   Type: {result.analysis.content_type}")
    lines.append(f"   Domain: {result.analysis.domain}")
    lines.append(f"   Complexity: {result.analysis.complexity}")
    lines.append(f"   Key topics: {', '.join(result.analysis.key_topics[:5])}")

    # Summaries
    if result.summaries:
        lines.append(f"\n📝 Summaries: {len(result.summaries)} levels generated")
        for level, summary in result.summaries.items():
            preview = summary[:100] + "..." if len(summary) > 100 else summary
            lines.append(f"   [{level}] {preview}")

    # Extraction
    if result.extraction:
        lines.append(f"\n🔍 Extraction:")
        lines.append(f"   Concepts: {len(result.extraction.concepts)}")
        if result.extraction.concepts:
            for concept in result.extraction.concepts[:5]:
                importance_icon = "⭐" if concept.importance == "core" else "○"
                definition_preview = concept.definition[:80] + "..." if len(concept.definition) > 80 else concept.definition
                lines.append(f"      {importance_icon} {concept.name}: {definition_preview}")
            if len(result.extraction.concepts) > 5:
                lines.append(f"      ... and {len(result.extraction.concepts) - 5} more")
        
        lines.append(f"   Key findings: {len(result.extraction.key_findings)}")
        if result.extraction.key_findings:
            for finding in result.extraction.key_findings[:3]:
                finding_preview = finding[:80] + "..." if len(finding) > 80 else finding
                lines.append(f"      • {finding_preview}")
            if len(result.extraction.key_findings) > 3:
                lines.append(f"      ... and {len(result.extraction.key_findings) - 3} more")
        
        lines.append(f"   Methodologies: {len(result.extraction.methodologies)}")
        if result.extraction.methodologies:
            for method in result.extraction.methodologies[:3]:
                method_preview = method[:80] + "..." if len(method) > 80 else method
                lines.append(f"      • {method_preview}")
        
        lines.append(f"   Tools mentioned: {len(result.extraction.tools_mentioned)}")
        if result.extraction.tools_mentioned:
            tools_str = ", ".join(result.extraction.tools_mentioned[:8])
            if len(result.extraction.tools_mentioned) > 8:
                tools_str += f", ... +{len(result.extraction.tools_mentioned) - 8} more"
            lines.append(f"      {tools_str}")

    # Tags
    if result.tags:
        all_tags = result.tags.domain_tags + result.tags.meta_tags
        if all_tags:
            lines.append(f"\n🏷️  Tags: {', '.join(all_tags[:10])}")

    # Connections
    if result.connections:
        lines.append(f"\n🔗 Connections: {len(result.connections)} discovered")
        for conn in result.connections[:3]:
            lines.append(f"   → {conn.target_title} ({conn.relationship_type})")

    # Follow-ups
    if result.followups:
        lines.append(f"\n📌 Follow-ups: {len(result.followups)} tasks")
        for task in result.followups[:3]:
            lines.append(f"   • {task.task[:60]}...")

    # Questions
    if result.mastery_questions:
        lines.append(f"\n❓ Mastery questions: {len(result.mastery_questions)}")
        for q in result.mastery_questions[:2]:
            lines.append(f"   • {q.question[:60]}...")

    # Output paths
    if result.obsidian_note_path:
        lines.append(f"\n📓 Obsidian note: {result.obsidian_note_path}")
    if result.neo4j_node_id:
        lines.append(f"🔷 Neo4j node: {result.neo4j_node_id}")

    return "\n".join(lines)


async def process_single_content(
    content_id: str,
    config: PipelineConfig,
    force: bool = False,
    output_format: str = "summary",
    output_file: Optional[str] = None,
) -> Optional[ProcessingResult]:
    """Process a single content item."""
    print(f"\n🔍 Loading content: {content_id}")

    # Load content from database
    content = await load_content(content_id)
    if not content:
        print(f"❌ Content not found: {content_id}")
        return None

    print(f"📄 Title: {content.title}")
    print(f"📦 Type: {content.source_type.value}")
    print(f"📊 Current status: {content.processing_status.value}")

    # Check if already processed
    if content.processing_status == ProcessingStatus.PROCESSED and not force:
        print(f"⚠️  Content already processed. Use --force to reprocess.")
        return None

    # Update status to PROCESSING
    await update_status(content_id, ContentStatus.PROCESSING.value)
    print(f"\n🚀 Starting processing pipeline...")

    try:
        result = await process_content(content, config=config)

        # Update status to PROCESSED
        await update_status(content_id, ContentStatus.PROCESSED.value)

        # Display result
        if output_format == "json":
            print(json.dumps(result.model_dump(), indent=2, default=str))
        else:
            print(format_processing_result(result))

        # Save to file if requested
        if output_file:
            Path(output_file).write_text(
                json.dumps(result.model_dump(), indent=2, default=str)
            )
            print(f"\n💾 Full result saved to: {output_file}")

        print(f"\n✅ Processing complete!")
        return result

    except Exception as e:
        # Update status to FAILED
        await update_status(content_id, ContentStatus.FAILED.value, error=str(e))
        print(f"\n❌ Processing failed: {e}")
        logging.exception("Processing error")
        return None


async def process_pending_content(
    config: PipelineConfig,
    limit: int = 10,
    dry_run: bool = False,
    output_format: str = "summary",
) -> list[ProcessingResult]:
    """Process all pending content."""
    async with async_session_maker() as session:
        # Get pending content
        query = (
            select(DBContent)
            .where(DBContent.status == ContentStatus.PENDING)
            .order_by(DBContent.created_at.asc())
            .limit(limit)
        )
        result = await session.execute(query)
        pending_items = result.scalars().all()

    if not pending_items:
        print("📭 No pending content to process")
        return []

    print(f"\n📋 Found {len(pending_items)} pending item(s)")
    print("=" * 60)

    for i, item in enumerate(pending_items, 1):
        title_display = item.title[:50] + "..." if len(item.title or "") > 50 else item.title
        print(f"  {i}. [{item.content_type}] {title_display}")
        print(f"     ID: {item.content_uuid}")

    if dry_run:
        print(f"\n🔍 DRY RUN - no content will be processed")
        return []

    print(f"\n{'─' * 60}")
    print(f"Starting processing...")
    print(f"{'─' * 60}\n")

    results = []
    for i, item in enumerate(pending_items, 1):
        print(f"\n[{i}/{len(pending_items)}] Processing: {item.title}")
        result = await process_single_content(
            item.content_uuid,
            config=config,
            force=False,
            output_format=output_format,
        )
        if result:
            results.append(result)

    # Summary
    print(f"\n{'=' * 60}")
    print(f"📊 BATCH PROCESSING SUMMARY")
    print(f"{'=' * 60}")
    print(f"Total items: {len(pending_items)}")
    print(f"Successful: {len(results)}")
    print(f"Failed: {len(pending_items) - len(results)}")

    if results:
        total_time = sum(r.processing_time_seconds for r in results)
        total_cost = sum(r.estimated_cost_usd for r in results)
        print(f"Total time: {total_time:.2f}s")
        print(f"Total cost: ${total_cost:.4f}")

    return results


# =============================================================================
# CLI Setup
# =============================================================================


def create_parser() -> argparse.ArgumentParser:
    """Create argument parser with subcommands."""
    parser = argparse.ArgumentParser(
        description="Run end-to-end LLM processing on ingested content",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument("--debug", action="store_true", help="Enable debug logging")

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # List command
    list_parser = subparsers.add_parser("list", help="List content in the database")
    list_parser.add_argument(
        "--status",
        choices=["pending", "processing", "processed", "failed", "all"],
        default=None,
        help="Filter by status (default: show all)",
    )
    list_parser.add_argument(
        "--limit",
        type=int,
        default=100,
        help="Maximum number of items to show (default: 100)",
    )
    list_parser.add_argument(
        "--format",
        "-f",
        choices=["summary", "json"],
        default="summary",
        help="Output format (default: summary)",
    )

    # Process single content command
    process_parser = subparsers.add_parser(
        "process", help="Process specific content by UUID"
    )
    process_parser.add_argument("content_id", help="Content UUID to process")
    process_parser.add_argument(
        "--force", action="store_true", help="Force reprocess even if already processed"
    )
    add_processing_args(process_parser)

    # Process pending command
    pending_parser = subparsers.add_parser(
        "process-pending", help="Process all pending content"
    )
    pending_parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Maximum number of items to process (default: 10)",
    )
    pending_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be processed without actually processing",
    )
    add_processing_args(pending_parser)

    return parser


def add_processing_args(parser: argparse.ArgumentParser) -> None:
    """Add common processing arguments to a parser."""
    # Output options
    parser.add_argument(
        "--format",
        "-f",
        choices=["summary", "json"],
        default="summary",
        help="Output format (default: summary)",
    )
    parser.add_argument(
        "--output-file",
        "-o",
        metavar="FILE",
        help="Save full processing result to JSON file (includes all extraction details)",
    )

    # Stage toggles
    parser.add_argument(
        "--no-summaries",
        action="store_true",
        help="Skip summary generation",
    )
    parser.add_argument(
        "--no-extraction",
        action="store_true",
        help="Skip concept extraction",
    )
    parser.add_argument(
        "--no-tags",
        action="store_true",
        help="Skip tag assignment",
    )
    parser.add_argument(
        "--no-connections",
        action="store_true",
        help="Skip connection discovery",
    )
    parser.add_argument(
        "--no-followups",
        action="store_true",
        help="Skip follow-up generation",
    )
    parser.add_argument(
        "--no-questions",
        action="store_true",
        help="Skip mastery question generation",
    )

    # Output toggles
    parser.add_argument(
        "--no-obsidian",
        action="store_true",
        help="Skip Obsidian note generation",
    )
    parser.add_argument(
        "--no-neo4j",
        action="store_true",
        help="Skip Neo4j node creation",
    )


def build_config(args: argparse.Namespace) -> PipelineConfig:
    """Build PipelineConfig from command-line arguments."""
    return PipelineConfig(
        generate_summaries=not getattr(args, "no_summaries", False),
        extract_concepts=not getattr(args, "no_extraction", False),
        assign_tags=not getattr(args, "no_tags", False),
        discover_connections=not getattr(args, "no_connections", False),
        generate_followups=not getattr(args, "no_followups", False),
        generate_questions=not getattr(args, "no_questions", False),
        create_obsidian_note=not getattr(args, "no_obsidian", False),
        create_neo4j_nodes=not getattr(args, "no_neo4j", False),
    )


async def main() -> None:
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    setup_logging(args.debug)

    if args.command == "list":
        await list_content(
            status_filter=args.status,
            limit=args.limit,
            output_format=args.format,
        )

    elif args.command == "process":
        # Ensure Neo4j indexes exist before processing
        await ensure_neo4j_indexes()
        config = build_config(args)
        await process_single_content(
            args.content_id,
            config=config,
            force=args.force,
            output_format=args.format,
            output_file=getattr(args, "output_file", None),
        )

    elif args.command == "process-pending":
        # Ensure Neo4j indexes exist before processing
        await ensure_neo4j_indexes()
        config = build_config(args)
        await process_pending_content(
            config=config,
            limit=args.limit,
            dry_run=args.dry_run,
            output_format=args.format,
        )


async def run_with_cleanup() -> None:
    """Run main and properly cleanup async clients."""
    try:
        await main()
    finally:
        # Give pending async callbacks time to complete
        await asyncio.sleep(0.1)

        # Cleanup LiteLLM async HTTP clients
        try:
            import litellm

            if hasattr(litellm, "aclient") and litellm.aclient:
                await litellm.aclient.close()
        except Exception:
            pass


if __name__ == "__main__":
    asyncio.run(run_with_cleanup())

