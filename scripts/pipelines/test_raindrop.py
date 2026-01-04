#!/usr/bin/env python3
"""
Test script to list all Raindrop.io collections.

Usage:
    python scripts/pipelines/test_raindrop.py

    # Or with a specific token:
    RAINDROP_ACCESS_TOKEN=your_token python scripts/pipelines/test_raindrop.py

Setup:
    1. Get your Raindrop.io access token from:
       https://app.raindrop.io/settings/integrations

    2. Either:
       - Set RAINDROP_ACCESS_TOKEN in your .env file
       - Or export it: export RAINDROP_ACCESS_TOKEN=your_token
"""

import asyncio
import sys
from pathlib import Path

# Add backend to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "backend"))

from dotenv import load_dotenv

# Load environment variables from project root .env
project_root = Path(__file__).parent.parent.parent
if (project_root / ".env").exists():
    load_dotenv(project_root / ".env")
else:
    load_dotenv(project_root / "backend" / ".env")

from app.config import settings
from app.pipelines.raindrop_sync import RaindropSync


async def main():
    """List all Raindrop.io collections."""
    token = settings.RAINDROP_ACCESS_TOKEN

    if not token:
        print("❌ Error: RAINDROP_ACCESS_TOKEN not set.")
        print()
        print("To fix this:")
        print("  1. Get your token from: https://app.raindrop.io/settings/integrations")
        print("  2. Add to your .env file: RAINDROP_ACCESS_TOKEN=your_token")
        print("  3. Or export it: export RAINDROP_ACCESS_TOKEN=your_token")
        sys.exit(1)

    print("🔐 Connecting to Raindrop.io...")
    print()

    sync = RaindropSync(access_token=token)

    try:
        collections = await sync.get_collections(include_nested=True)

        if not collections:
            print("📭 No collections found.")
            return

        print(f"📚 Found {len(collections)} collections:")
        print()
        print(f"{'ID':<12} {'Items':<8} {'Title'}")
        print("-" * 60)

        # Sort by item count (descending)
        collections.sort(key=lambda c: c.get("count", 0), reverse=True)

        for coll in collections:
            coll_id = coll.get("_id", "?")
            title = coll.get("title", "Untitled")
            count = coll.get("count", 0)
            parent = coll.get("parent", {})

            # Indent nested collections
            indent = "  └─ " if parent and parent.get("$id") else ""

            print(f"{coll_id:<12} {count:<8} {indent}{title}")

        print()
        print("Special collection IDs:")
        print("  0    = All raindrops")
        print("  -1   = Unsorted")
        print("  -99  = Trash")
        print()
        print("To sync a collection, use:")
        print("  python scripts/pipelines/run_pipeline.py raindrop --collection <ID>")

    finally:
        await sync.close()


if __name__ == "__main__":
    asyncio.run(main())
