#!/usr/bin/env python3
"""
Update OpenAPI Schema Snapshot

Updates the OpenAPI schema snapshot used by contract tests.
Run this after making intentional API changes.

Usage (from backend container):
    python scripts/update_openapi_snapshot.py

Or via Make:
    make snapshot
"""

import json
import sys
from pathlib import Path


def main():
    """Update the OpenAPI schema snapshot."""
    try:
        from fastapi.testclient import TestClient
        from app.main import app
    except ImportError as e:
        print(f"Error: {e}")
        print("This script must be run from the backend container or with app in PYTHONPATH")
        sys.exit(1)

    snapshot_path = Path("tests/snapshots/openapi.json")

    # Get current schema
    client = TestClient(app)
    response = client.get("/openapi.json")

    if response.status_code != 200:
        print(f"Error: Failed to fetch OpenAPI schema (status {response.status_code})")
        sys.exit(1)

    schema = response.json()

    # Ensure directory exists
    snapshot_path.parent.mkdir(parents=True, exist_ok=True)

    # Write formatted JSON
    with open(snapshot_path, "w") as f:
        json.dump(schema, f, indent=2, sort_keys=True)
        f.write("\n")

    # Print summary
    paths_count = len(schema.get("paths", {}))
    schemas_count = len(schema.get("components", {}).get("schemas", {}))

    print(f"Updated OpenAPI snapshot: {snapshot_path}")
    print(f"  Paths: {paths_count}")
    print(f"  Schemas: {schemas_count}")


if __name__ == "__main__":
    main()
