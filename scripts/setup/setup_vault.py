#!/usr/bin/env python3
"""
Obsidian Vault Structure Setup

Creates the data directory structure and Obsidian vault folder hierarchy.
Uses VaultManager.ensure_structure() for consistent folder creation.

Usage:
    python scripts/setup/setup_vault.py
    python scripts/setup/setup_vault.py --data-dir ~/my/data
    python scripts/setup/setup_vault.py --skip-data-dirs
    python scripts/setup/setup_vault.py --regenerate-taxonomy
"""

import argparse
import asyncio
import json
from pathlib import Path
from typing import Any

from _common import add_common_args, load_tag_taxonomy, resolve_paths
from app.services.obsidian.vault import create_vault_manager


def create_data_directories(data_dir: Path, config: dict[str, Any]) -> None:
    """Create the root data directory structure from config."""

    data_config = config.get("data", {})
    subdirs_config = data_config.get("subdirs", {})

    if not subdirs_config:
        print("⚠️  No data.subdirs defined in config")
        return

    print(f"📁 Creating data directory structure at: {data_dir}")

    data_dir.mkdir(parents=True, exist_ok=True)

    for subdir_key, subdir_name in subdirs_config.items():
        subdir_path = data_dir / subdir_name
        subdir_path.mkdir(parents=True, exist_ok=True)
        print(f"  ✅ {subdir_name}/")

    print()


async def create_vault_structure(vault_path: Path, config: dict[str, Any]) -> None:
    """
    Create the Obsidian vault folder structure using VaultManager.

    Uses VaultManager.ensure_structure() for consistent folder creation
    across CLI scripts and API endpoints.
    """
    # Ensure vault root exists first (VaultManager validates this)
    vault_path.mkdir(parents=True, exist_ok=True)

    # Use VaultManager for structure creation (consistency with API)
    vault = create_vault_manager(str(vault_path), validate=True)
    result = await vault.ensure_structure()

    print("📁 Vault structure:")
    if result["created"]:
        print(f"  Created {len(result['created'])} folders:")
        for folder in result["created"]:
            print(f"    ✅ {folder}")
    if result["existed"]:
        print(f"  Already existed: {len(result['existed'])} folders")

    # Create .gitkeep files for empty folders
    for folder in vault_path.rglob("*"):
        if folder.is_dir() and not any(folder.iterdir()):
            (folder / ".gitkeep").touch()

    content_types = config.get("content_types", {})
    print(f"\n✅ Vault structure ready at: {vault_path}")
    print(f"   Content types: {len(content_types)}")


def create_obsidian_config(vault_path: Path, config: dict[str, Any]) -> None:
    """Create Obsidian app configuration from config."""

    obsidian_config = config.get("obsidian", {})

    obsidian_dir = vault_path / ".obsidian"
    obsidian_dir.mkdir(exist_ok=True)

    # App settings
    app_config = obsidian_config.get("app_config", {})
    app_settings: dict[str, Any] = {
        "alwaysUpdateLinks": app_config.get("always_update_links", True),
        "newFileLocation": "folder",
        "newFileFolderPath": app_config.get("new_file_folder", "sources/ideas"),
        "attachmentFolderPath": app_config.get("attachment_folder", "assets"),
        "showUnsupportedFiles": False,
        "strictLineBreaks": False,
        "useMarkdownLinks": app_config.get("use_markdown_links", False),
        "promptDelete": True,
    }

    with open(obsidian_dir / "app.json", "w") as f:
        json.dump(app_settings, f, indent=2)

    # Core plugins
    core_plugins = obsidian_config.get("core_plugins", [])
    if core_plugins:
        with open(obsidian_dir / "core-plugins.json", "w") as f:
            json.dump(core_plugins, f, indent=2)

    # Daily notes settings
    daily_notes_config = obsidian_config.get("daily_notes", {})
    if daily_notes_config:
        daily_notes_settings: dict[str, str] = {
            "folder": daily_notes_config.get("folder", "daily"),
            "format": daily_notes_config.get("format", "YYYY-MM-DD"),
            "template": daily_notes_config.get("template", "templates/daily.md"),
        }
        with open(obsidian_dir / "daily-notes.json", "w") as f:
            json.dump(daily_notes_settings, f, indent=2)

    # Templates settings
    templates_config = obsidian_config.get("templates", {})
    if templates_config:
        templates_settings: dict[str, str] = {
            "folder": templates_config.get("folder", "templates"),
            "dateFormat": templates_config.get("date_format", "YYYY-MM-DD"),
            "timeFormat": templates_config.get("time_format", "HH:mm"),
        }
        with open(obsidian_dir / "templates.json", "w") as f:
            json.dump(templates_settings, f, indent=2)

    print("\n⚙️  Obsidian configuration created")


def generate_tag_taxonomy_md(vault_path: Path, config: dict[str, Any]) -> None:
    """Generate tag taxonomy markdown from config/tag-taxonomy.yaml."""

    taxonomy = load_tag_taxonomy()

    if not taxonomy:
        print("⚠️  Skipping tag taxonomy generation (no config found)")
        return

    obsidian_config = config.get("obsidian", {})
    meta_config = obsidian_config.get("meta", {})
    meta_folder = meta_config.get("folder", "meta")
    taxonomy_file = meta_config.get("tag_taxonomy_file", "tag-taxonomy.md")

    lines: list[str] = [
        "---",
        "type: meta",
        "title: Tag Taxonomy",
        "---",
        "",
        "> [!warning] Auto-Generated File",
        "> This file is automatically generated from `config/tag-taxonomy.yaml`.",
        "> **Do not edit this file directly** — your changes will be overwritten.",
        "> To modify the tag taxonomy, edit `config/tag-taxonomy.yaml` and run:",
        "> ```bash",
        "> python scripts/setup/setup_vault.py --regenerate-taxonomy",
        "> ```",
        "",
        "# Tag Taxonomy",
        "",
        "This document defines the valid tags for the knowledge base.",
        "Tags follow the `domain/category/topic` hierarchy (up to 3 levels).",
        "",
        "## Usage Rules",
        "",
        "1. **1-3 domain tags** per note (use most specific that applies)",
        "2. **1 status tag** (required for all notes)",
        "3. **1 quality tag** (recommended)",
        "4. **NO source tags** — folder path already indicates source type",
        "5. Prefer existing tags over creating new ones",
        "",
        "---",
        "",
    ]

    # Domain tags
    domains = taxonomy.get("domains", {})
    if domains:
        lines.append("## Domain Tags")
        lines.append("")

        for domain_key, domain_config in domains.items():
            domain_name = domain_config.get(
                "name", domain_key.replace("-", " ").title()
            )
            lines.append(f"### {domain_name}")
            lines.append("")

            categories = domain_config.get("categories", {})
            for cat_key, cat_config in categories.items():
                cat_name = cat_config.get("name", cat_key.replace("-", " ").title())
                lines.append(f"#### {domain_key}/{cat_key}/ — {cat_name}")
                lines.append("")

                topics = cat_config.get("topics", [])
                for topic in topics:
                    if isinstance(topic, dict):
                        topic_key = list(topic.keys())[0]
                        topic_desc = topic[topic_key]
                        lines.append(
                            f"- `{domain_key}/{cat_key}/{topic_key}` — {topic_desc}"
                        )
                    else:
                        lines.append(f"- `{domain_key}/{cat_key}/{topic}`")

                lines.append("")

    # Status tags
    status_tags = taxonomy.get("status", [])
    if status_tags:
        lines.extend(
            [
                "---",
                "",
                "## Status Tags",
                "",
                "| Tag | Description | When to Use |",
                "|-----|-------------|-------------|",
            ]
        )
        for tag in status_tags:
            if isinstance(tag, dict):
                tag_name = list(tag.keys())[0]
                tag_desc = tag[tag_name]
                lines.append(f"| `status/{tag_name}` | {tag_desc} | |")
            else:
                lines.append(f"| `status/{tag}` | | |")
        lines.append("")

    # Quality tags
    quality_tags = taxonomy.get("quality", [])
    if quality_tags:
        lines.extend(
            [
                "---",
                "",
                "## Quality Tags",
                "",
                "| Tag | Description | When to Use |",
                "|-----|-------------|-------------|",
            ]
        )
        for tag in quality_tags:
            if isinstance(tag, dict):
                tag_name = list(tag.keys())[0]
                tag_desc = tag[tag_name]
                lines.append(f"| `quality/{tag_name}` | {tag_desc} | |")
            else:
                lines.append(f"| `quality/{tag}` | | |")
        lines.append("")

    lines.extend(
        [
            "---",
            "",
            "## Adding New Tags",
            "",
            "Before adding a new tag:",
            "",
            "1. Check if an existing tag covers the concept",
            "2. Consider if it fits the hierarchical structure",
            "3. Ensure it will be used for 3+ notes",
            "4. Add to `config/tag-taxonomy.yaml`",
            "5. Run `python scripts/setup/setup_vault.py --regenerate-taxonomy`",
            "",
            "---",
            "",
            "*Generated from `config/tag-taxonomy.yaml`*",
        ]
    )

    output_path = vault_path / meta_folder / taxonomy_file
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as f:
        f.write("\n".join(lines))

    print(f"✅ Generated: {meta_folder}/{taxonomy_file}")


async def async_main(args, config: dict, data_dir: Path, vault_path: Path) -> None:
    """Async main for vault setup operations."""
    if args.regenerate_taxonomy:
        generate_tag_taxonomy_md(vault_path, config)
    else:
        if not args.skip_data_dirs:
            create_data_directories(data_dir, config)

        await create_vault_structure(vault_path, config)
        create_obsidian_config(vault_path, config)
        generate_tag_taxonomy_md(vault_path, config)


def main() -> None:
    parser = argparse.ArgumentParser(description="Create Obsidian vault structure")
    add_common_args(parser)
    parser.add_argument(
        "--skip-data-dirs",
        action="store_true",
        help="Skip creating data directories (neo4j, postgres, redis)",
    )
    parser.add_argument(
        "--regenerate-taxonomy",
        action="store_true",
        help="Only regenerate tag taxonomy markdown",
    )
    args = parser.parse_args()

    config, data_dir, vault_path = resolve_paths(args)

    print(f"🧠 Second Brain Vault Setup")
    print(f"   Data directory: {data_dir}")
    print(f"   Vault path: {vault_path}")
    print()

    asyncio.run(async_main(args, config, data_dir, vault_path))

    print("\n🎉 Vault structure setup complete!")


if __name__ == "__main__":
    main()
