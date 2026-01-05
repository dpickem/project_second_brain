"""
Common utilities shared across setup scripts.

This module provides shared configuration loading and path resolution
functions used by all setup scripts.

CONFIGURATION SOURCES (in priority order):
    1. Command-line arguments (--data-dir, --vault-path)
    2. Environment variables (DATA_DIR, OBSIDIAN_VAULT_PATH)
    3. Backend settings (backend/app/config/settings.py)
    4. YAML config (config/default.yaml)

For secrets and deployment config, see .env.example
"""

import os
import sys
from argparse import ArgumentParser, Namespace
from pathlib import Path
from typing import Any, Optional

import yaml

# Add project root and backend to path for imports (scripts/setup/ -> project root)
# Must happen before importing from backend
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_BACKEND_DIR = _PROJECT_ROOT / "backend"
sys.path.insert(0, str(_PROJECT_ROOT))
sys.path.insert(0, str(_BACKEND_DIR))

# Now import path constants from backend config
from app.config import CONFIG_DIR


def load_config() -> dict[str, Any]:
    """Load configuration from config/default.yaml."""
    config_path = CONFIG_DIR / "default.yaml"

    if not config_path.exists():
        print(f"❌ Configuration not found: {config_path}")
        sys.exit(1)

    with open(config_path) as f:
        return yaml.safe_load(f)


def load_tag_taxonomy() -> dict[str, Any]:
    """Load tag taxonomy from config/tag-taxonomy.yaml."""
    taxonomy_path = CONFIG_DIR / "tag-taxonomy.yaml"

    if not taxonomy_path.exists():
        print(f"⚠️  Tag taxonomy not found: {taxonomy_path}")
        return {}

    with open(taxonomy_path) as f:
        return yaml.safe_load(f)


def _get_settings_data_dir() -> Optional[Path]:
    """
    Try to get DATA_DIR from backend settings.

    Returns None if backend settings are not available.
    """
    try:
        from app.config.settings import settings

        if settings.DATA_DIR:
            return Path(settings.DATA_DIR).expanduser().resolve()
    except ImportError:
        pass
    return None


def _get_settings_vault_path() -> Optional[Path]:
    """
    Try to get OBSIDIAN_VAULT_PATH from backend settings.

    Returns None if backend settings are not available.
    """
    try:
        from app.config.settings import settings

        if settings.OBSIDIAN_VAULT_PATH:
            return Path(settings.OBSIDIAN_VAULT_PATH).expanduser().resolve()
    except ImportError:
        pass
    return None


def get_data_dir(
    args_data_dir: Optional[str] = None, config: Optional[dict[str, Any]] = None
) -> Path:
    """
    Get the root data directory.

    Priority:
    1. --data-dir argument
    2. DATA_DIR environment variable
    3. Backend settings (settings.DATA_DIR)
    4. data.root from config/default.yaml
    """
    if args_data_dir:
        return Path(args_data_dir).expanduser().resolve()

    if os.environ.get("DATA_DIR"):
        return Path(os.environ["DATA_DIR"]).expanduser().resolve()

    # Try backend settings
    settings_dir = _get_settings_data_dir()
    if settings_dir:
        return settings_dir

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
    3. Backend settings (settings.OBSIDIAN_VAULT_PATH)
    4. DATA_DIR / data.subdirs.obsidian from config
    """
    if args_vault_path:
        return Path(args_vault_path).expanduser().resolve()

    if os.environ.get("OBSIDIAN_VAULT_PATH"):
        return Path(os.environ["OBSIDIAN_VAULT_PATH"]).expanduser().resolve()

    # Try backend settings
    settings_path = _get_settings_vault_path()
    if settings_path:
        return settings_path

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
