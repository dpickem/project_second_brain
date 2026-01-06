#!/usr/bin/env python3
"""
Vault Validation Script

Validates the Obsidian vault structure and configuration.
Uses VaultManager for path validation and statistics.

Usage:
    python scripts/setup/validate_vault.py
    python scripts/setup/validate_vault.py --data-dir ~/my/data

Exit codes:
    0 - Validation passed
    1 - Validation failed with errors
"""

import argparse
import asyncio
import sys
from pathlib import Path
from typing import Any

from _common import add_common_args, resolve_paths
from app.services.obsidian.vault import create_vault_manager


async def validate_vault(vault_path: Path, config: dict[str, Any]) -> bool:
    """
    Validate Obsidian vault structure and configuration.

    Uses VaultManager for path validation when possible.

    Returns:
        True if validation passed, False if errors found
    """
    errors: list[str] = []
    warnings: list[str] = []

    print(f"🔍 Validating vault at: {vault_path}\n")

    # Check if vault exists
    if not vault_path.exists():
        errors.append(f"Vault directory does not exist: {vault_path}")
        print(f"❌ Vault directory does not exist")
        return False

    if not vault_path.is_dir():
        errors.append(f"Vault path is not a directory: {vault_path}")
        print(f"❌ Vault path is not a directory")
        return False

    # Use VaultManager for validation
    try:
        vault = create_vault_manager(str(vault_path), validate=True)
        stats = await vault.get_vault_stats()
        print(f"📊 Vault stats: {stats['total_notes']} total notes")
        for type_key, count in stats.get("by_type", {}).items():
            if count > 0:
                print(f"   - {type_key}: {count}")
        print()
    except ValueError as e:
        errors.append(str(e))
        print(f"❌ VaultManager validation failed: {e}")
        return False

    content_types: dict[str, Any] = config.get("content_types", {})
    obsidian_config: dict[str, Any] = config.get("obsidian", {})

    # Build list of required folders from system_folders and content types
    system_folders: list[str] = obsidian_config.get("system_folders", [])
    required_folders: list[str] = [f.split("/")[0] for f in system_folders]
    required_folders = list(set(required_folders))

    for type_key, type_config in content_types.items():
        folder = type_config.get("folder")
        if folder:
            required_folders.append(folder)

    print("📁 Checking folder structure:")
    for folder in required_folders:
        folder_path = vault_path / folder
        if folder_path.exists():
            print(f"  ✅ {folder}")
        else:
            errors.append(f"Missing folder: {folder}")
            print(f"  ❌ {folder} (missing)")

    print()

    # Build list of required templates from content types
    required_templates: set[str] = set()
    for type_key, type_config in content_types.items():
        template = type_config.get("template")
        if template:
            required_templates.add(template)

    print("📄 Checking templates:")
    for template in sorted(required_templates):
        template_path = vault_path / template
        if template_path.exists():
            try:
                content = template_path.read_text()
                if content.startswith("---"):
                    end_idx = content.find("---", 3)
                    if end_idx > 0:
                        frontmatter = content[3:end_idx].strip()
                        if "type:" in frontmatter:
                            print(f"  ✅ {template}")
                        else:
                            warnings.append(
                                f"Template missing 'type' field: {template}"
                            )
                            print(f"  ⚠️  {template} (missing type field)")
                    else:
                        warnings.append(f"Invalid frontmatter in template: {template}")
                        print(f"  ⚠️  {template} (invalid frontmatter)")
                else:
                    warnings.append(f"Template missing frontmatter: {template}")
                    print(f"  ⚠️  {template} (no frontmatter)")
            except Exception as e:
                errors.append(f"Cannot read template: {template} - {e}")
                print(f"  ❌ {template} (read error)")
        else:
            errors.append(f"Missing template: {template}")
            print(f"  ❌ {template} (missing)")

    print()

    # Check meta files
    meta_config: dict[str, Any] = obsidian_config.get("meta", {})
    meta_folder: str = meta_config.get("folder", "meta")

    required_meta: list[str] = [f"{meta_folder}/dashboard.md"]
    optional_meta: list[str] = [
        f"{meta_folder}/tag-taxonomy.md",
        f"{meta_folder}/workflows.md",
        f"{meta_folder}/plugin-setup.md",
        "reviews/_queue.md",
    ]

    print("📋 Checking meta files:")
    for meta_file in required_meta:
        meta_path = vault_path / meta_file
        if meta_path.exists():
            print(f"  ✅ {meta_file}")
        else:
            errors.append(f"Missing required meta file: {meta_file}")
            print(f"  ❌ {meta_file} (missing)")

    for meta_file in optional_meta:
        meta_path = vault_path / meta_file
        if meta_path.exists():
            print(f"  ✅ {meta_file}")
        else:
            warnings.append(f"Missing optional meta file: {meta_file}")
            print(f"  ⚠️  {meta_file} (optional, missing)")

    print()

    # Check Obsidian config
    obsidian_config_dir = vault_path / ".obsidian"
    if obsidian_config_dir.exists():
        config_files: list[str] = ["app.json", "core-plugins.json"]
        missing_configs: list[str] = [
            f for f in config_files if not (obsidian_config_dir / f).exists()
        ]

        if missing_configs:
            warnings.append(
                f"Missing Obsidian config files: {', '.join(missing_configs)}"
            )
            print(
                f"⚙️  Obsidian configuration: ⚠️  (missing: {', '.join(missing_configs)})"
            )
        else:
            print("⚙️  Obsidian configuration: ✅")
    else:
        warnings.append("Obsidian configuration folder not found")
        print("⚙️  Obsidian configuration: ⚠️  (not configured)")

    print()

    # Summary
    print("=" * 60)
    if errors:
        print(f"❌ Validation FAILED with {len(errors)} error(s):")
        for error in errors:
            print(f"   - {error}")
    else:
        print("✅ Validation PASSED")

    if warnings:
        print(f"\n⚠️  {len(warnings)} warning(s):")
        for warning in warnings:
            print(f"   - {warning}")

    return len(errors) == 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate Obsidian vault structure")
    add_common_args(parser)
    args = parser.parse_args()

    config, data_dir, vault_path = resolve_paths(args)

    success = asyncio.run(validate_vault(vault_path, config))

    if not success:
        print("\n💡 To fix missing items, run:")
        print("   python scripts/setup/setup_all.py")

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
