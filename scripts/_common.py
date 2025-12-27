"""
Common utilities shared across setup scripts.

This module provides shared configuration loading and path resolution
functions used by all setup scripts.
"""

import os
import sys
from argparse import ArgumentParser, Namespace
from pathlib import Path
from typing import Any, Optional

import yaml

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


def load_config() -> dict[str, Any]:
    """Load configuration from config/default.yaml."""
    config_path = Path(__file__).parent.parent / "config" / "default.yaml"

    if not config_path.exists():
        print(f"❌ Configuration not found: {config_path}")
        sys.exit(1)

    with open(config_path) as f:
        return yaml.safe_load(f)


def load_tag_taxonomy() -> dict[str, Any]:
    """Load tag taxonomy from config/tag-taxonomy.yaml."""
    taxonomy_path = Path(__file__).parent.parent / "config" / "tag-taxonomy.yaml"

    if not taxonomy_path.exists():
        print(f"⚠️  Tag taxonomy not found: {taxonomy_path}")
        return {}

    with open(taxonomy_path) as f:
        return yaml.safe_load(f)


def get_data_dir(
    args_data_dir: Optional[str] = None, config: Optional[dict[str, Any]] = None
) -> Path:
    """
    Get the root data directory.

    Priority:
    1. --data-dir argument
    2. DATA_DIR environment variable
    3. data.root from config/default.yaml
    """
    if args_data_dir:
        return Path(args_data_dir).expanduser().resolve()

    if os.environ.get("DATA_DIR"):
        return Path(os.environ["DATA_DIR"]).expanduser().resolve()

    # Fall back to config default
    if config:
        data_config = config.get("data", {})
        default_root = data_config.get("root", "~/workspace/obsidian/second_brain")
        return Path(default_root).expanduser().resolve()

    # Ultimate fallback if no config available yet
    return Path("~/workspace/obsidian/second_brain").expanduser().resolve()


def get_vault_path(
    data_dir: Path, config: dict[str, Any], args_vault_path: Optional[str] = None
) -> Path:
    """
    Get the Obsidian vault path.

    Priority:
    1. --vault-path argument
    2. OBSIDIAN_VAULT_PATH env var
    3. DATA_DIR / data.subdirs.obsidian from config
    """
    if args_vault_path:
        return Path(args_vault_path).expanduser().resolve()

    if os.environ.get("OBSIDIAN_VAULT_PATH"):
        return Path(os.environ["OBSIDIAN_VAULT_PATH"]).expanduser().resolve()

    # Get obsidian subdir name from config
    data_config = config.get("data", {})
    subdirs = data_config.get("subdirs", {})
    obsidian_subdir = subdirs.get("obsidian", "obsidian")

    return data_dir / obsidian_subdir


def add_common_args(parser: ArgumentParser) -> ArgumentParser:
    """Add common arguments to an argument parser."""
    parser.add_argument(
        "--data-dir",
        type=str,
        help="Root data directory (default from config/default.yaml)",
    )
    parser.add_argument(
        "--vault-path",
        type=str,
        help="Direct path to Obsidian vault (overrides data-dir/obsidian)",
    )
    return parser


def resolve_paths(args: Namespace) -> tuple[dict[str, Any], Path, Path]:
    """
    Resolve data_dir and vault_path from arguments and config.

    Returns:
        tuple: (config, data_dir, vault_path)
    """
    config = load_config()
    data_dir = get_data_dir(getattr(args, "data_dir", None), config)
    vault_path = get_vault_path(data_dir, config, getattr(args, "vault_path", None))
    return config, data_dir, vault_path
