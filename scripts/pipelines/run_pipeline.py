#!/usr/bin/env python3
"""
Unified Pipeline Runner

Test any ingestion pipeline from the command line.

Setup:
    1. Copy .env.example to .env in the project root:
       cp .env.example .env

    2. Fill in required API keys (see .env.example for documentation)

    3. Run any pipeline:
       python run_pipeline.py <pipeline> <args>

Usage:
    # PDF processing (uses OCR for full document extraction)
    python run_pipeline.py pdf /path/to/document.pdf

    # Book OCR (single image or directory)
    python run_pipeline.py book /path/to/page.jpg
    python run_pipeline.py book /path/to/pages/ --title "Deep Work"

    # Voice transcription
    python run_pipeline.py voice /path/to/memo.mp3
    python run_pipeline.py voice /path/to/memo.mp3 --no-expand

    # Web article extraction
    python run_pipeline.py article https://example.com/post

    # GitHub repository import
    python run_pipeline.py github https://github.com/user/repo
    python run_pipeline.py github --starred --limit 5

    # Raindrop.io sync
    python run_pipeline.py raindrop --list-collections
    python run_pipeline.py raindrop --collection 0 --limit 10
    python run_pipeline.py raindrop --since 7d

Environment Variables (set in .env or environment):
    Required (depending on pipeline):
    - OPENAI_API_KEY: For Whisper transcription and text models
    - MISTRAL_API_KEY: For OCR models (default)
    - GITHUB_ACCESS_TOKEN: For GitHub import
    - RAINDROP_ACCESS_TOKEN: For Raindrop sync

    Optional (defaults in backend/app/config/settings.py):
    - OCR_MODEL: Vision model for OCR (default: mistral/mistral-ocr-latest)
    - TEXT_MODEL: Text model for analysis (default: openai/gpt-4o-mini)
    - DEBUG: Enable verbose logging

    See .env.example for full list of available environment variables.
"""

import argparse
import asyncio
import json
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

# Add backend to path for imports (must be before app.* imports)
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "backend"))

from dotenv import load_dotenv

# Load environment variables from project root .env
# Falls back to backend/.env for backwards compatibility
project_root = Path(__file__).parent.parent.parent
if (project_root / ".env").exists():
    load_dotenv(project_root / ".env")
else:
    load_dotenv(project_root / "backend" / ".env")

# App imports (after sys.path setup and env loading)
from app.config import settings
from app.pipelines import (
    BookOCRPipeline,
    GitHubImporter,
    PDFProcessor,
    RaindropSync,
    VoiceTranscriber,
    WebArticlePipeline,
)
from app.pipelines.base import PipelineContentType, PipelineInput
from app.pipelines.book_ocr import BookMetadata


def setup_logging(debug: bool = False) -> None:
    """Configure logging based on debug flag."""
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%H:%M:%S",
    )


def content_to_dict(content: Any) -> dict[str, Any]:
    """Convert UnifiedContent to a JSON-serializable dict."""
    if hasattr(content, "model_dump"):
        data = content.model_dump()
    elif hasattr(content, "__dict__"):
        data = content.__dict__.copy()
    else:
        data = {"content": str(content)}

    # Convert datetime objects
    for key, value in data.items():
        if isinstance(value, datetime):
            data[key] = value.isoformat()
        elif isinstance(value, Path):
            data[key] = str(value)

    return data


def print_result(
    content: Any,
    output_format: str = "summary",
    output_file: Optional[str] = None,
) -> None:
    """
    Print pipeline result and optionally save full JSON to file.

    Args:
        content: UnifiedContent or similar object to display
        output_format: Display format ("summary" or "json")
        output_file: If provided, saves full JSON serialization to this file
    """
    data = content_to_dict(content)

    # Always save full JSON to file if output_file is specified
    if output_file:
        full_json = json.dumps(data, indent=2, default=str)
        Path(output_file).write_text(full_json)
        print(f"Full output saved to: {output_file}")

    # Display to stdout in requested format
    if output_format == "json":
        output = json.dumps(data, indent=2, default=str)
    else:
        output = format_summary(data)

    print(output)


def format_summary(data: dict[str, Any]) -> str:
    """Format content as a human-readable summary."""
    lines = [
        "=" * 60,
        f"Title: {data.get('title', 'Untitled')}",
        f"Type: {data.get('source_type', 'unknown')}",
        f"Created: {data.get('created_at', 'unknown')}",
    ]

    if data.get("authors"):
        lines.append(f"Authors: {', '.join(data['authors'])}")

    if data.get("source_url"):
        lines.append(f"URL: {data['source_url']}")

    if data.get("source_file_path"):
        lines.append(f"File: {data['source_file_path']}")

    lines.append("=" * 60)

    # Full text preview
    full_text = data.get("full_text", "")
    if full_text:
        preview = full_text[:500]
        if len(full_text) > 500:
            preview += f"\n... [{len(full_text) - 500} more characters]"
        lines.append("\n📄 Content Preview:")
        lines.append("-" * 40)
        lines.append(preview)

    # Annotations
    annotations = data.get("annotations", [])
    if annotations:
        lines.append(f"\n📌 Annotations ({len(annotations)}):")
        lines.append("-" * 40)
        for i, annot in enumerate(annotations, 1):
            annot_type = annot.get("type", "unknown")
            content = annot.get("content", "")
            # Show full content, preserving newlines with indentation
            if "\n" in content:
                first_line = content.split("\n")[0]
                lines.append(f"  {i}. [{annot_type}] {first_line}")
                for line in content.split("\n")[1:]:
                    lines.append(f"      {line}")
            else:
                lines.append(f"  {i}. [{annot_type}] {content}")

    # Tags
    tags = data.get("tags", [])
    if tags:
        lines.append(f"\n🏷️  Tags: {', '.join(tags)}")

    # Metadata
    metadata = data.get("metadata", {})
    if metadata:
        lines.append("\n📊 Metadata:")
        lines.append("-" * 40)
        for key, value in list(metadata.items())[:10]:
            if value is not None:
                lines.append(f"  {key}: {value}")

    return "\n".join(lines)


# =============================================================================
# Pipeline Runners
# =============================================================================


async def run_pdf(args: argparse.Namespace) -> None:
    """Run PDF processor pipeline."""
    pdf_path = Path(args.path).expanduser().resolve()
    if not pdf_path.exists():
        print(f"Error: File not found: {pdf_path}")
        sys.exit(1)

    processor = PDFProcessor(track_costs=args.track_costs)

    print(f"Processing PDF: {pdf_path}")
    input_data = PipelineInput(path=pdf_path, content_type=PipelineContentType.PDF)
    content = await processor.process(input_data)

    print_result(content, args.output_format, args.output_file)


async def run_book_ocr(args: argparse.Namespace) -> None:
    """Run book OCR pipeline."""
    input_path = Path(args.path).expanduser().resolve()
    if not input_path.exists():
        print(f"Error: Path not found: {input_path}")
        sys.exit(1)

    pipeline = BookOCRPipeline(
        max_concurrency=args.concurrency,
        track_costs=args.track_costs,
    )

    # Prepare metadata if provided
    metadata = None
    if args.title or args.authors or args.isbn:
        metadata = BookMetadata(
            title=args.title or "Unknown Book",
            authors=args.authors.split(",") if args.authors else [],
            isbn=args.isbn,
        )

    # Get image paths
    if input_path.is_file():
        image_paths = [input_path]
        print(f"Processing single image: {input_path}")
    else:
        supported = {".jpg", ".jpeg", ".png", ".heic", ".webp", ".tiff"}
        image_paths = [p for p in input_path.iterdir() if p.suffix.lower() in supported]
        image_paths.sort()
        print(f"Processing {len(image_paths)} images from: {input_path}")

    if not image_paths:
        print("Error: No supported image files found")
        sys.exit(1)

    content = await pipeline.process_paths(image_paths, book_metadata=metadata)

    # Show preview for each page
    print("\n" + "=" * 60)
    print("📖 PAGE PREVIEWS")
    print("=" * 60)
    
    # Split full_text by page separator and show preview of each
    page_separator = "\n\n---\n\n"
    pages = content.full_text.split(page_separator)
    
    for i, page_text in enumerate(pages, 1):
        # Extract page label (first line in brackets)
        lines = page_text.strip().split("\n")
        page_label = lines[0] if lines else f"Page {i}"
        
        # Get text content (skip the label line)
        text_content = "\n".join(lines[1:]).strip() if len(lines) > 1 else ""
        
        # Show preview (first 200 chars)
        preview = text_content[:200]
        if len(text_content) > 200:
            preview += "..."
        
        print(f"\n{page_label}")
        print("-" * 40)
        if preview:
            print(preview)
        else:
            print("(no text extracted)")
    
    print("\n" + "=" * 60)

    print_result(content, args.output_format, args.output_file)


async def run_voice(args: argparse.Namespace) -> None:
    """Run voice transcription pipeline."""
    audio_path = Path(args.path).expanduser().resolve()
    if not audio_path.exists():
        print(f"Error: File not found: {audio_path}")
        sys.exit(1)

    transcriber = VoiceTranscriber(
        whisper_model=args.whisper_model,
        text_model=args.text_model if not args.no_expand else None,
        expand_notes=not args.no_expand,
        track_costs=args.track_costs,
    )

    print(f"Transcribing: {audio_path}")
    content = await transcriber.process_path(audio_path, expand=not args.no_expand)

    print_result(content, args.output_format, args.output_file)


async def run_article(args: argparse.Namespace) -> None:
    """Run web article extraction pipeline."""
    pipeline = WebArticlePipeline(timeout=args.timeout)

    print(f"Extracting article: {args.url}")
    input_data = PipelineInput(url=args.url, content_type=PipelineContentType.ARTICLE)
    content = await pipeline.process(input_data)

    # Save markdown file if output file is specified and content is markdown
    if args.output_file and content.metadata.get("format") == "markdown":
        md_path = Path(args.output_file).with_suffix(".md")
        markdown_content = content.metadata.get("markdown") or content.full_text

        # Add title as H1 header if not already present
        if not markdown_content.startswith("# "):
            markdown_content = f"# {content.title}\n\n{markdown_content}"

        md_path.write_text(markdown_content)
        print(f"Markdown saved to: {md_path}")

    print_result(content, args.output_format, args.output_file)


async def run_github(args: argparse.Namespace) -> None:
    """Run GitHub importer pipeline."""
    token = args.token or settings.GITHUB_ACCESS_TOKEN
    if not token:
        print("Error: GITHUB_ACCESS_TOKEN not set. Provide via --token or environment.")
        sys.exit(1)

    importer = GitHubImporter(
        access_token=token,
        track_costs=args.track_costs,
    )

    try:
        if args.starred:
            print(f"Importing starred repos (limit: {args.limit})")
            contents = await importer.import_starred_repos(limit=args.limit)
            for content in contents:
                print_result(content, args.output_format)
                print("\n" + "=" * 60 + "\n")
        else:
            if not args.url:
                print("Error: Provide a GitHub URL or use --starred")
                sys.exit(1)
            print(f"Importing repo: {args.url}")
            content = await importer.import_repo(args.url)
            print_result(content, args.output_format, args.output_file)
    finally:
        await importer.close()


async def run_raindrop(args: argparse.Namespace) -> None:
    """Run Raindrop.io sync pipeline."""
    token = args.token or settings.RAINDROP_ACCESS_TOKEN
    if not token:
        print("Error: RAINDROP_ACCESS_TOKEN not set. Provide via --token or environment.")
        sys.exit(1)

    sync = RaindropSync(
        access_token=token,
        max_concurrent=args.concurrency,
    )

    # Parse since argument
    since = None
    if args.since:
        if args.since.endswith("d"):
            days = int(args.since[:-1])
            since = datetime.now() - timedelta(days=days)
        elif args.since.endswith("w"):
            weeks = int(args.since[:-1])
            since = datetime.now() - timedelta(weeks=weeks)
        else:
            since = datetime.fromisoformat(args.since)

    try:
        if args.list_collections:
            print("Fetching collections...")
            collections = await sync.get_collections()
            # Sort by full path for logical hierarchy display
            collections.sort(key=lambda c: c.get("full_path", "").lower())
            for coll in collections:
                print(f"  [{coll.get('_id')}] {coll.get('full_path', coll.get('title', ''))} ({coll.get('count', 0)} items)")
        else:
            print(f"Syncing Raindrop collection {args.collection} (limit: {args.limit})")
            if since:
                print(f"  Since: {since.isoformat()}")

            contents = await sync.sync_collection(
                collection_id=args.collection,
                since=since,
                limit=args.limit,
            )

            # Save all items to file if output_file specified
            if args.output_file:
                all_data = [content_to_dict(c) for c in contents]
                full_json = json.dumps(all_data, indent=2, default=str)
                Path(args.output_file).write_text(full_json)
                print(f"Full output saved to: {args.output_file}")

            for content in contents:
                print_result(content, args.output_format)
                print("\n" + "-" * 60 + "\n")

            print(f"\nSynced {len(contents)} items")
    finally:
        await sync.close()


# =============================================================================
# CLI Setup
# =============================================================================


def create_parser() -> argparse.ArgumentParser:
    """Create argument parser with subcommands for each pipeline."""
    parser = argparse.ArgumentParser(
        description="Test ingestion pipelines from the command line",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument(
        "--debug", action="store_true", help="Enable debug logging"
    )

    subparsers = parser.add_subparsers(dest="command", help="Pipeline to run")

    # Common arguments
    def add_common_args(p: argparse.ArgumentParser) -> None:
        p.add_argument(
            "--output-format",
            "-f",
            choices=["summary", "json"],
            default="summary",
            help="Output format (default: summary)",
        )
        p.add_argument(
            "--output-file",
            "-o",
            help="Save output to file instead of stdout",
        )
        p.add_argument(
            "--track-costs",
            action="store_true",
            help="Enable LLM cost tracking to database (requires PostgreSQL)",
        )

    # PDF subcommand
    pdf_parser = subparsers.add_parser("pdf", help="Process PDF documents")
    pdf_parser.add_argument("path", help="Path to PDF file")
    add_common_args(pdf_parser)

    # Book OCR subcommand
    book_parser = subparsers.add_parser("book", help="OCR book page photos")
    book_parser.add_argument("path", help="Path to image file or directory")
    book_parser.add_argument("--title", help="Book title (optional)")
    book_parser.add_argument("--authors", help="Comma-separated author names")
    book_parser.add_argument("--isbn", help="Book ISBN")
    book_parser.add_argument(
        "--concurrency",
        type=int,
        default=5,
        help="Max concurrent OCR requests (default: 5)",
    )
    add_common_args(book_parser)

    # Voice subcommand
    voice_parser = subparsers.add_parser("voice", help="Transcribe voice memos")
    voice_parser.add_argument("path", help="Path to audio file")
    voice_parser.add_argument(
        "--no-expand",
        action="store_true",
        help="Skip note expansion (raw transcript only)",
    )
    voice_parser.add_argument(
        "--whisper-model",
        default="whisper-1",
        help="Whisper model to use (default: whisper-1)",
    )
    voice_parser.add_argument(
        "--text-model",
        help="Text model for note expansion (default from settings)",
    )
    add_common_args(voice_parser)

    # Article subcommand
    article_parser = subparsers.add_parser("article", help="Extract web article content")
    article_parser.add_argument("url", help="Article URL")
    article_parser.add_argument(
        "--timeout",
        type=float,
        default=30.0,
        help="Request timeout in seconds (default: 30)",
    )
    add_common_args(article_parser)

    # GitHub subcommand
    github_parser = subparsers.add_parser("github", help="Import GitHub repositories")
    github_parser.add_argument("url", nargs="?", help="GitHub repository URL")
    github_parser.add_argument(
        "--starred",
        action="store_true",
        help="Import starred repositories instead of single repo",
    )
    github_parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Max repos to import when using --starred (default: 10)",
    )
    github_parser.add_argument(
        "--token",
        help="GitHub access token (default from GITHUB_ACCESS_TOKEN)",
    )
    add_common_args(github_parser)

    # Raindrop subcommand
    raindrop_parser = subparsers.add_parser("raindrop", help="Sync Raindrop.io bookmarks")
    raindrop_parser.add_argument(
        "--collection",
        type=int,
        default=0,
        help="Collection ID (0=all, -1=unsorted, -99=trash, default: 0)",
    )
    raindrop_parser.add_argument(
        "--since",
        help="Sync items since date (e.g., '7d', '2w', '2024-01-01')",
    )
    raindrop_parser.add_argument(
        "--limit",
        type=int,
        help="Max items to sync",
    )
    raindrop_parser.add_argument(
        "--list-collections",
        action="store_true",
        help="List available collections and exit",
    )
    raindrop_parser.add_argument(
        "--concurrency",
        type=int,
        default=5,
        help="Max concurrent requests (default: 5)",
    )
    raindrop_parser.add_argument(
        "--token",
        help="Raindrop access token (default from RAINDROP_ACCESS_TOKEN)",
    )
    add_common_args(raindrop_parser)

    return parser


async def main() -> None:
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    setup_logging(args.debug)

    # Route to appropriate pipeline
    runners = {
        "pdf": run_pdf,
        "book": run_book_ocr,
        "voice": run_voice,
        "article": run_article,
        "github": run_github,
        "raindrop": run_raindrop,
    }

    runner = runners.get(args.command)
    if runner:
        await runner(args)
    else:
        print(f"Unknown command: {args.command}")
        sys.exit(1)


async def run_with_cleanup() -> None:
    """Run main and properly cleanup LiteLLM async clients."""
    try:
        await main()
    finally:
        # Cleanup LiteLLM async HTTP clients to avoid RuntimeWarning
        try:
            import litellm
            if hasattr(litellm, "aclient") and litellm.aclient:
                await litellm.aclient.close()
        except Exception:
            pass


if __name__ == "__main__":
    asyncio.run(run_with_cleanup())
