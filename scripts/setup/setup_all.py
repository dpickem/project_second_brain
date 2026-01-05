#!/usr/bin/env python3
"""
Complete Second Brain Setup

Orchestrates all setup scripts to create the complete vault structure.

Steps:
1. Creates data directories and vault folders
2. Creates Obsidian templates
3. Creates meta notes (dashboard, workflows)
4. Validates the setup

Usage:
    python scripts/setup/setup_all.py
    python scripts/setup/setup_all.py --data-dir ~/my/data
    python scripts/setup/setup_all.py --skip-validation
"""

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Any, Optional

from _common import add_common_args, resolve_paths


def run_script(
    script_name: str, data_dir: str, vault_path: Optional[str] = None
) -> bool:
    """Run a setup script and return success status."""
    script_path = Path(__file__).parent / script_name

    if not script_path.exists():
        print(f"❌ Script not found: {script_path}")
        return False

    cmd: list[str] = [sys.executable, str(script_path), "--data-dir", data_dir]
    if vault_path:
        cmd.extend(["--vault-path", vault_path])

    result = subprocess.run(cmd, capture_output=False)
    return result.returncode == 0


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Complete setup for Second Brain system"
    )
    add_common_args(parser)
    parser.add_argument(
        "--skip-validation", action="store_true", help="Skip validation step"
    )
    args = parser.parse_args()

    config, data_dir, vault_path = resolve_paths(args)

    print("=" * 60)
    print("🧠 SECOND BRAIN - COMPLETE SETUP")
    print("=" * 60)
    print(f"\nData directory: {data_dir}")
    print(f"Vault path:     {vault_path}")
    print()

    steps: list[tuple[str, str]] = [
        ("setup_vault.py", "Creating vault structure"),
        ("create_templates.py", "Creating templates"),
        ("create_meta_notes.py", "Creating meta notes"),
    ]

    if not args.skip_validation:
        steps.append(("validate_vault.py", "Validating setup"))

    success = True

    for script, description in steps:
        print("\n" + "-" * 60)
        print(f"📦 {description}...")
        print("-" * 60 + "\n")

        if not run_script(script, str(data_dir), str(vault_path)):
            print(f"\n❌ {description} failed!")
            success = False
            if script == "validate_vault.py":
                continue  # Validation failure is not fatal
            break

    # Get meta folder from config for help message
    obsidian_config: dict[str, Any] = config.get("obsidian", {})
    meta_config: dict[str, Any] = obsidian_config.get("meta", {})
    meta_folder: str = meta_config.get("folder", "meta")

    print("\n" + "=" * 60)
    if success:
        print("🎉 SETUP COMPLETE!")
        print("=" * 60)
        print("\nNext steps:")
        print("  1. Open Obsidian and select the vault at:")
        print(f"     {vault_path}")
        print("  2. Install community plugins:")
        print("     - Dataview")
        print("     - Templater")
        print("     - Tasks")
        print("     - Tag Wrangler")
        print("     - Linter")
        print(f"  3. Configure Templater folder templates")
        print(f"     (see {meta_folder}/plugin-setup.md)")
        print("  4. Start Docker services:")
        print(f"     DATA_DIR={data_dir} docker-compose up -d")
    else:
        print("❌ SETUP FAILED")
        print("=" * 60)
        print("\nPlease check the errors above and try again.")
        sys.exit(1)


if __name__ == "__main__":
    main()
