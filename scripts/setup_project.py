#!/usr/bin/env python3
"""
Second Brain - Complete Project Setup

This is the entry point for setting up the entire Second Brain system.
Run this script when you first clone the repository or need to reconfigure.

WHAT THIS SCRIPT DOES:
    1. Environment Setup
       - Creates/updates .env file with all required variables
       - Shows current values (masked for secrets)
       - Provides instructions for obtaining API keys and credentials

    2. System Setup
       - Creates data directories (postgres, neo4j, redis, obsidian)
       - Sets up Obsidian vault structure (folders, templates, config)
       - Creates meta notes and dashboards

    3. Service Setup
       - Validates Docker is available
       - Checks/starts Docker containers
       - Runs database migrations

    4. Help & Documentation
       - Shows how to run tests
       - Points to documentation
       - Provides quick-start commands

USAGE:
    # Interactive setup (recommended for first-time users)
    python scripts/setup_project.py

    # Non-interactive mode (uses defaults or existing .env)
    python scripts/setup_project.py --non-interactive

    # Setup specific components only
    python scripts/setup_project.py --env-only        # Just configure .env
    python scripts/setup_project.py --vault-only      # Just setup vault
    python scripts/setup_project.py --services-only   # Just start services
    python scripts/setup_project.py --help-only       # Just show help/docs

    # Skip specific steps
    python scripts/setup_project.py --skip-services   # Don't start Docker
    python scripts/setup_project.py --skip-migrations # Don't run migrations

PREREQUISITES:
    - Python 3.11+
    - Docker Desktop installed and running
    - Git (for cloning, already done if you're reading this)

"""

import argparse
import os
import secrets
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

# =============================================================================
# Configuration
# =============================================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = PROJECT_ROOT / "backend"
FRONTEND_DIR = PROJECT_ROOT / "frontend"
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
CONFIG_DIR = PROJECT_ROOT / "config"
DOCS_DIR = PROJECT_ROOT / "docs"
ENV_FILE = PROJECT_ROOT / ".env"


# =============================================================================
# Terminal Colors & Formatting
# =============================================================================


class Colors:
    """ANSI color codes for terminal output."""

    HEADER = "\033[95m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    UNDERLINE = "\033[4m"
    END = "\033[0m"


def print_header(text: str, char: str = "=") -> None:
    """Print a header with formatting."""
    width = 70
    print(f"\n{Colors.BOLD}{Colors.BLUE}{char * width}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}  {text}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{char * width}{Colors.END}\n")


def print_subheader(text: str) -> None:
    """Print a subheader."""
    print(f"\n{Colors.BOLD}{Colors.CYAN}── {text} ──{Colors.END}\n")


def print_success(text: str) -> None:
    """Print success message."""
    print(f"{Colors.GREEN}✓ {text}{Colors.END}")


def print_failure(text: str) -> None:
    """Print failure message."""
    print(f"{Colors.RED}✗ {text}{Colors.END}")


def print_warning(text: str) -> None:
    """Print warning message."""
    print(f"{Colors.YELLOW}⚠ {text}{Colors.END}")


def print_info(text: str) -> None:
    """Print info message."""
    print(f"{Colors.CYAN}ℹ {text}{Colors.END}")


def print_dim(text: str) -> None:
    """Print dimmed text."""
    print(f"{Colors.DIM}{text}{Colors.END}")


def mask_secret(value: str, show_chars: int = 4) -> str:
    """Mask a secret value, showing only first few characters."""
    if not value:
        return "(not set)"
    if len(value) <= show_chars:
        return "*" * len(value)
    return value[:show_chars] + "*" * (len(value) - show_chars)


# =============================================================================
# Environment Variable Definitions
# =============================================================================


@dataclass
class EnvVar:
    """Definition of an environment variable."""

    name: str
    description: str
    default: str = ""
    required: bool = False
    secret: bool = False
    category: str = "general"
    instructions: str = ""
    example: str = ""
    generate: bool = False  # Auto-generate a secure value


# All environment variables organized by category
ENV_VARS: list[EnvVar] = [
    # -------------------------------------------------------------------------
    # DATA DIRECTORY
    # -------------------------------------------------------------------------
    EnvVar(
        name="DATA_DIR",
        description="Root directory for all persistent data (databases, vault)",
        default="~/workspace/obsidian/second_brain",
        required=True,
        category="data",
        instructions="""
This directory will contain:
  - postgres/   : PostgreSQL database files
  - redis/      : Redis persistence
  - neo4j/      : Neo4j graph database
  - obsidian/   : Your Obsidian vault (notes, templates)
  - uploads/    : Uploaded files staging area

Choose a location with enough disk space (10GB+ recommended).
The directory will be created if it doesn't exist.
""",
        example="~/workspace/obsidian/second_brain",
    ),
    # -------------------------------------------------------------------------
    # DATABASE CREDENTIALS
    # -------------------------------------------------------------------------
    EnvVar(
        name="POSTGRES_USER",
        description="PostgreSQL username",
        default="secondbrain",
        required=True,
        category="database",
        instructions="Username for PostgreSQL. Use any alphanumeric string.",
        example="secondbrain",
    ),
    EnvVar(
        name="POSTGRES_PASSWORD",
        description="PostgreSQL password",
        default="",
        required=True,
        secret=True,
        generate=True,
        category="database",
        instructions="""
Password for PostgreSQL. A secure random password will be auto-generated
if you don't provide one. Keep this secret!
""",
        example="your-secure-password-here",
    ),
    EnvVar(
        name="POSTGRES_DB",
        description="PostgreSQL database name",
        default="secondbrain",
        required=True,
        category="database",
        instructions="Database name for the application.",
        example="secondbrain",
    ),
    EnvVar(
        name="NEO4J_PASSWORD",
        description="Neo4j password",
        default="",
        required=True,
        secret=True,
        generate=True,
        category="database",
        instructions="""
Password for Neo4j graph database. Minimum 8 characters.
A secure random password will be auto-generated if you don't provide one.

Access Neo4j Browser at: http://localhost:7474
Default username: neo4j
""",
        example="your-neo4j-password",
    ),
    # -------------------------------------------------------------------------
    # LLM API KEYS
    # -------------------------------------------------------------------------
    EnvVar(
        name="OPENAI_API_KEY",
        description="OpenAI API key (for GPT models, Whisper, embeddings)",
        default="",
        required=False,
        secret=True,
        category="llm",
        instructions="""
Required for: Text generation, voice transcription (Whisper), embeddings

How to get an OpenAI API key:
1. Go to https://platform.openai.com/
2. Sign up or log in
3. Navigate to API Keys: https://platform.openai.com/api-keys
4. Click "Create new secret key"
5. Copy the key (starts with 'sk-')

Pricing: Pay-per-use, ~$0.01 per 1K tokens for GPT-4o-mini
Free tier: $5 credit for new accounts
""",
        example="sk-proj-xxxxxxxxxxxx",
    ),
    EnvVar(
        name="MISTRAL_API_KEY",
        description="Mistral AI API key (for OCR, text models)",
        default="",
        required=False,
        secret=True,
        category="llm",
        instructions="""
Required for: Document OCR (Mistral OCR model - excellent for PDFs and books)

How to get a Mistral API key:
1. Go to https://console.mistral.ai/
2. Sign up or log in
3. Navigate to API Keys
4. Create a new key

Pricing: ~$1 per 1000 pages for OCR
""",
        example="xxxxxxxxxx",
    ),
    EnvVar(
        name="ANTHROPIC_API_KEY",
        description="Anthropic API key (for Claude models)",
        default="",
        required=False,
        secret=True,
        category="llm",
        instructions="""
Optional: For Claude models (excellent for analysis and reasoning)

How to get an Anthropic API key:
1. Go to https://console.anthropic.com/
2. Sign up or log in
3. Navigate to API Keys
4. Create a new key

Pricing: Pay-per-use
""",
        example="sk-ant-xxxxxxxxxxxx",
    ),
    EnvVar(
        name="GEMINI_API_KEY",
        description="Google Gemini API key (for vision, text models)",
        default="",
        required=False,
        secret=True,
        category="llm",
        instructions="""
Optional: For Google Gemini models (excellent vision capabilities)

How to get a Gemini API key:
1. Go to https://aistudio.google.com/
2. Sign up with Google account
3. Navigate to API Keys
4. Create a new key

Pricing: Generous free tier available
""",
        example="AIzaxxxxxxxxxx",
    ),
    # -------------------------------------------------------------------------
    # MODEL CONFIGURATION
    # -------------------------------------------------------------------------
    # NOTE: Each model requires its corresponding API key to be set.
    # The provider prefix (before /) determines which API key is needed:
    #   - openai/*   → OPENAI_API_KEY
    #   - mistral/*  → MISTRAL_API_KEY
    #   - anthropic/* → ANTHROPIC_API_KEY
    #   - gemini/*   → GEMINI_API_KEY
    EnvVar(
        name="TEXT_MODEL",
        description="Default text model for analysis and generation",
        default="gemini/gemini-3-flash-preview",
        required=False,
        category="models",
        instructions="""
The text model used for:
  - Content summarization
  - Exercise generation
  - Learning assistant conversations

Format: provider/model-name (LiteLLM format)

Recommended options (API key required in parentheses):
  - gemini/gemini-3-flash-preview  (GEMINI_API_KEY) - fast, cost-effective
  - openai/gpt-4o-mini             (OPENAI_API_KEY) - balanced
  - anthropic/claude-sonnet-4-20250514 (ANTHROPIC_API_KEY) - best quality
""",
        example="gemini/gemini-3-flash-preview",
    ),
    EnvVar(
        name="OCR_MODEL",
        description="Model for document OCR (PDFs, book photos)",
        default="mistral/mistral-ocr-latest",
        required=False,
        category="models",
        instructions="""
The model used for extracting text from documents and images.

Recommended options (API key required in parentheses):
  - mistral/mistral-ocr-latest     (MISTRAL_API_KEY) - best for docs, $1/1000 pages
  - gemini/gemini-3-flash-preview  (GEMINI_API_KEY)  - good vision, handles diagrams
  - openai/gpt-4o                  (OPENAI_API_KEY)  - highest accuracy, expensive
""",
        example="mistral/mistral-ocr-latest",
    ),
    EnvVar(
        name="VLM_MODEL",
        description="Vision-language model for image understanding",
        default="gemini/gemini-3-flash-preview",
        required=False,
        category="models",
        instructions="""
The vision model used for:
  - Analyzing diagrams and figures
  - Processing book photos with highlights
  - Understanding visual content

Recommended options (API key required in parentheses):
  - gemini/gemini-3-flash-preview  (GEMINI_API_KEY) - excellent vision
  - openai/gpt-4o                  (OPENAI_API_KEY) - high quality
""",
        example="gemini/gemini-3-flash-preview",
    ),
    # -------------------------------------------------------------------------
    # EXTERNAL SERVICES
    # -------------------------------------------------------------------------
    EnvVar(
        name="RAINDROP_ACCESS_TOKEN",
        description="Raindrop.io access token (for bookmark sync)",
        default="",
        required=False,
        secret=True,
        category="external",
        instructions="""
For syncing bookmarks from Raindrop.io to your knowledge base.

How to get a Raindrop access token:
1. Go to https://app.raindrop.io/settings/integrations
2. Scroll to "For Developers"
3. Click "Create new app"
4. Create app, then click on it
5. Generate "Test token" for personal use

This allows importing your saved articles and highlights.
""",
        example="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
    ),
    EnvVar(
        name="GITHUB_ACCESS_TOKEN",
        description="GitHub personal access token (for repo import)",
        default="",
        required=False,
        secret=True,
        category="external",
        instructions="""
For importing starred repositories and code analysis.

How to create a GitHub token:
1. Go to https://github.com/settings/tokens
2. Click "Generate new token (classic)"
3. Select scopes:
   - repo (for private repos, or just public_repo for public only)
   - read:user
4. Generate and copy the token

Fine-grained tokens also work with "Public Repositories (read-only)" access.
""",
        example="ghp_xxxxxxxxxxxx",
    ),
    # -------------------------------------------------------------------------
    # APPLICATION SETTINGS
    # -------------------------------------------------------------------------
    EnvVar(
        name="DEBUG",
        description="Enable debug mode (verbose logging)",
        default="false",
        required=False,
        category="app",
        instructions="Set to 'true' for development, 'false' for production.",
        example="false",
    ),
]


def get_env_vars_by_category() -> dict[str, list[EnvVar]]:
    """Group environment variables by category."""
    categories: dict[str, list[EnvVar]] = {}
    for var in ENV_VARS:
        if var.category not in categories:
            categories[var.category] = []
        categories[var.category].append(var)
    return categories


CATEGORY_NAMES = {
    "data": "📁 Data Directory",
    "database": "🗄️ Database Credentials",
    "llm": "🤖 LLM API Keys",
    "models": "⚙️ Model Configuration",
    "external": "🔌 External Services",
    "app": "🛠️ Application Settings",
}

# Mapping of LLM provider prefixes to their required API key environment variable
PROVIDER_TO_API_KEY = {
    "openai": "OPENAI_API_KEY",
    "mistral": "MISTRAL_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "gemini": "GEMINI_API_KEY",
    "google": "GEMINI_API_KEY",  # google/ is sometimes used for Gemini
}

# Model variables that determine API key requirements
MODEL_VARS = ["TEXT_MODEL", "OCR_MODEL", "VLM_MODEL"]


def get_provider_from_model(model: str) -> str | None:
    """
    Extract the provider from a LiteLLM model string.

    Examples:
        - "openai/gpt-4o" → "openai"
        - "gemini/gemini-3-flash-preview" → "gemini"
        - "mistral/mistral-ocr-latest" → "mistral"
        - "anthropic/claude-sonnet-4" → "anthropic"
    """
    if not model or "/" not in model:
        return None
    return model.split("/")[0].lower()


def get_required_api_keys(values: dict[str, str]) -> dict[str, list[str]]:
    """
    Determine which API keys are required based on model selection.

    Returns a dict mapping API key name → list of models that need it.
    """
    required: dict[str, list[str]] = {}

    for model_var in MODEL_VARS:
        model_value = values.get(model_var, "")
        if not model_value:
            continue

        provider = get_provider_from_model(model_value)
        if not provider:
            continue

        api_key_var = PROVIDER_TO_API_KEY.get(provider)
        if not api_key_var:
            continue

        if api_key_var not in required:
            required[api_key_var] = []
        required[api_key_var].append(f"{model_var}={model_value}")

    return required


def validate_api_keys(values: dict[str, str]) -> list[str]:
    """
    Validate that required API keys are set based on model configuration.

    Returns a list of warning messages for missing keys.
    """
    warnings: list[str] = []
    required_keys = get_required_api_keys(values)

    for api_key_var, model_usages in required_keys.items():
        api_key_value = values.get(api_key_var, "")
        if not api_key_value:
            models_str = ", ".join(model_usages)
            warnings.append(
                f"{api_key_var} is required for: {models_str}"
            )

    return warnings


def show_api_key_requirements(values: dict[str, str]) -> None:
    """Show which API keys are required based on current model selection."""
    required_keys = get_required_api_keys(values)

    if not required_keys:
        print_info("No model-specific API keys required (no models configured)")
        return

    print_subheader("API Key Requirements (based on model selection)")

    for api_key_var, model_usages in required_keys.items():
        api_key_value = values.get(api_key_var, "")
        status = "✓ Set" if api_key_value else "✗ Missing"
        color = Colors.GREEN if api_key_value else Colors.RED

        print(f"  {color}{status}{Colors.END} {api_key_var}")
        for usage in model_usages:
            print(f"       └─ needed by {usage}")
        print()


# =============================================================================
# Environment File Management
# =============================================================================


def load_existing_env() -> dict[str, str]:
    """Load existing .env file if it exists."""
    env_values: dict[str, str] = {}
    if ENV_FILE.exists():
        with open(ENV_FILE) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, value = line.partition("=")
                    # Remove surrounding quotes
                    value = value.strip().strip('"').strip("'")
                    env_values[key.strip()] = value
    return env_values


def generate_secure_password(length: int = 24) -> str:
    """Generate a secure random password."""
    return secrets.token_urlsafe(length)


def prompt_for_value(
    var: EnvVar, current_value: str, interactive: bool = True
) -> str:
    """Prompt user for an environment variable value."""
    if not interactive:
        # Non-interactive: use current value, default, or generate
        if current_value:
            return current_value
        if var.generate and not var.default:
            return generate_secure_password()
        return var.default

    # Show current state
    print(f"\n{Colors.BOLD}{var.name}{Colors.END}")
    print(f"  {var.description}")

    if var.instructions:
        print(f"{Colors.DIM}{var.instructions.strip()}{Colors.END}")

    # Show current/default value
    if current_value:
        display = mask_secret(current_value) if var.secret else current_value
        print(f"  Current: {Colors.GREEN}{display}{Colors.END}")
    elif var.default:
        print(f"  Default: {Colors.CYAN}{var.default}{Colors.END}")
    elif var.generate:
        print(f"  {Colors.CYAN}(will auto-generate secure password){Colors.END}")

    if var.example:
        print(f"  Example: {Colors.DIM}{var.example}{Colors.END}")

    # Determine prompt text
    if current_value:
        prompt_text = "  Enter new value (or press Enter to keep current): "
    elif var.default:
        prompt_text = f"  Enter value (or press Enter for default): "
    elif var.generate:
        prompt_text = "  Enter value (or press Enter to auto-generate): "
    else:
        prompt_text = "  Enter value: " if var.required else "  Enter value (optional): "

    try:
        user_input = input(prompt_text).strip()
    except KeyboardInterrupt:
        print("\n")
        raise

    # Determine final value
    if user_input:
        return user_input
    elif current_value:
        return current_value
    elif var.generate and not var.default:
        generated = generate_secure_password()
        print(f"  {Colors.GREEN}Generated: {mask_secret(generated)}{Colors.END}")
        return generated
    else:
        return var.default


def write_env_file(values: dict[str, str]) -> None:
    """Write environment variables to .env file."""
    lines = [
        "# =============================================================================",
        "# Second Brain - Environment Configuration",
        "# =============================================================================",
        "#",
        "# This file was generated by scripts/setup_project.py",
        "# You can edit it manually or re-run the setup script.",
        "#",
        "# SECURITY: This file contains secrets. Do NOT commit to version control!",
        "#           It is already in .gitignore.",
        "#",
        "# For documentation on each variable, run: python scripts/setup_project.py --help-env",
        "#",
        "",
    ]

    categories = get_env_vars_by_category()
    category_order = ["data", "database", "llm", "models", "external", "app"]

    for category in category_order:
        if category not in categories:
            continue

        vars_in_category = categories[category]
        category_name = CATEGORY_NAMES.get(category, category.title())

        lines.append(f"# {'-' * 70}")
        lines.append(f"# {category_name}")
        lines.append(f"# {'-' * 70}")

        for var in vars_in_category:
            value = values.get(var.name, var.default)
            # Quote values with spaces
            if " " in value or "=" in value:
                value = f'"{value}"'
            lines.append(f"{var.name}={value}")

        lines.append("")

    with open(ENV_FILE, "w") as f:
        f.write("\n".join(lines))


def setup_environment(interactive: bool = True) -> dict[str, str]:
    """Configure all environment variables."""
    print_header("Environment Configuration")

    existing = load_existing_env()
    if existing:
        print_info(f"Found existing .env file with {len(existing)} variables")
    else:
        print_info("No existing .env file found - starting fresh")

    values: dict[str, str] = {}
    categories = get_env_vars_by_category()
    category_order = ["data", "database", "llm", "models", "external", "app"]

    for category in category_order:
        if category not in categories:
            continue

        vars_in_category = categories[category]
        category_name = CATEGORY_NAMES.get(category, category.title())
        print_subheader(category_name)

        for var in vars_in_category:
            current = existing.get(var.name, "")
            value = prompt_for_value(var, current, interactive)
            values[var.name] = value

    # Write to file
    write_env_file(values)
    print_success(f"Environment configuration saved to {ENV_FILE}")

    # Validate API key requirements based on model selection
    show_api_key_requirements(values)

    warnings = validate_api_keys(values)
    if warnings:
        print_warning("Missing API keys detected!")
        print_info("The following API keys are required based on your model selection:")
        for warning in warnings:
            print(f"  {Colors.YELLOW}• {warning}{Colors.END}")
        print()
        print_info("You can:")
        print_info("  1. Re-run setup: python scripts/setup_project.py --env-only")
        print_info("  2. Edit .env manually")
        print_info("  3. Change model selection to use a different provider")
    else:
        print_success("All required API keys are configured")

    return values


def show_env_help() -> None:
    """Show detailed help for all environment variables."""
    print_header("Environment Variable Reference")

    categories = get_env_vars_by_category()
    category_order = ["data", "database", "llm", "models", "external", "app"]

    for category in category_order:
        if category not in categories:
            continue

        vars_in_category = categories[category]
        category_name = CATEGORY_NAMES.get(category, category.title())
        print_subheader(category_name)

        for var in vars_in_category:
            required = f"{Colors.RED}(required){Colors.END}" if var.required else "(optional)"
            print(f"{Colors.BOLD}{var.name}{Colors.END} {required}")
            print(f"  {var.description}")
            if var.default:
                print(f"  Default: {var.default}")
            if var.example:
                print(f"  Example: {var.example}")
            if var.instructions:
                print(f"{Colors.DIM}{var.instructions}{Colors.END}")
            print()


# =============================================================================
# System Setup Functions
# =============================================================================


def run_setup_script(script_name: str, *args: str) -> bool:
    """Run a setup script from scripts/setup/."""
    script_path = SCRIPTS_DIR / "setup" / script_name
    if not script_path.exists():
        print_failure(f"Script not found: {script_path}")
        return False

    cmd = [sys.executable, str(script_path)] + list(args)
    result = subprocess.run(cmd, cwd=PROJECT_ROOT)
    return result.returncode == 0


def setup_vault(data_dir: str) -> bool:
    """Set up the Obsidian vault structure."""
    print_header("Vault Setup", char="-")

    # Run setup_all.py which orchestrates all vault setup
    return run_setup_script("setup_all.py", "--data-dir", data_dir)


def check_docker() -> bool:
    """Check if Docker is available and running."""
    try:
        result = subprocess.run(
            ["docker", "info"],
            capture_output=True,
            text=True,
        )
        return result.returncode == 0
    except FileNotFoundError:
        return False


def start_docker_services() -> bool:
    """Start Docker services using docker-compose."""
    print_header("Docker Services", char="-")

    if not check_docker():
        print_failure("Docker is not running or not installed")
        print_info("Please install Docker Desktop: https://www.docker.com/products/docker-desktop/")
        return False

    print_success("Docker is running")

    # Check if services are already running
    result = subprocess.run(
        ["docker", "compose", "ps", "-q"],
        capture_output=True,
        text=True,
        cwd=PROJECT_ROOT,
    )

    if result.stdout.strip():
        print_info("Some services are already running")
        print_info("Run 'docker compose down' first if you want to restart")

    print_info("Starting services with docker compose...")
    result = subprocess.run(
        ["docker", "compose", "up", "-d"],
        cwd=PROJECT_ROOT,
    )

    if result.returncode == 0:
        print_success("Docker services started")
        print_info("Services:")
        print_info("  - PostgreSQL:  localhost:5432")
        print_info("  - Redis:       localhost:6379")
        print_info("  - Neo4j:       localhost:7474 (browser), localhost:7687 (bolt)")
        print_info("  - Backend:     localhost:8000")
        print_info("  - Frontend:    localhost:3000")
        return True
    else:
        print_failure("Failed to start Docker services")
        print_info("Check logs with: docker compose logs")
        return False


def run_migrations() -> bool:
    """Run database migrations."""
    print_subheader("Database Migrations")

    result = subprocess.run(
        ["docker", "compose", "exec", "backend", "alembic", "upgrade", "head"],
        cwd=PROJECT_ROOT,
    )

    if result.returncode == 0:
        print_success("Migrations completed")
        return True
    else:
        # Try running locally if Docker exec fails
        print_warning("Docker exec failed, trying local migration...")
        result = subprocess.run(
            ["alembic", "upgrade", "head"],
            cwd=BACKEND_DIR,
        )
        if result.returncode == 0:
            print_success("Migrations completed (local)")
            return True
        print_failure("Migration failed")
        return False


# =============================================================================
# Help & Documentation
# =============================================================================


def show_help(header: str = "Help & Documentation") -> None:
    """Show comprehensive help with all available commands."""
    print_header(header)

    print(f"""
{Colors.BOLD}Quick Start:{Colors.END}

  {Colors.CYAN}Access the application:{Colors.END}
    http://localhost:3000             # Frontend (React app)
    http://localhost:8000             # Backend API
    http://localhost:8000/docs        # API documentation (Swagger)
    http://localhost:7474             # Neo4j Browser

{Colors.BOLD}Available Scripts:{Colors.END}

  {Colors.CYAN}Setup & Configuration:{Colors.END}
    python scripts/setup_project.py              # This script - full setup
    python scripts/setup/setup_all.py            # Set up vault structure only
    python scripts/setup/reset_all.py            # Reset databases and vault

  {Colors.CYAN}Testing:{Colors.END}
    python scripts/run_all_tests.py              # Run all tests
    python scripts/run_all_tests.py --backend    # Backend tests only
    python scripts/run_all_tests.py --frontend   # Frontend tests only
    python scripts/run_all_tests.py --coverage   # With coverage report

  {Colors.CYAN}Content Ingestion:{Colors.END}
    python scripts/pipelines/run_pipeline.py --help          # Full pipeline help
    python scripts/pipelines/run_pipeline.py article <URL>   # Import web article
    python scripts/pipelines/run_pipeline.py pdf <file>      # Process PDF
    python scripts/pipelines/run_pipeline.py book <file>     # OCR book photos
    python scripts/pipelines/run_pipeline.py voice <file>    # Transcribe audio
    python scripts/pipelines/run_pipeline.py github <repo>   # Import GitHub repo
    python scripts/pipelines/run_pipeline.py raindrop        # Sync Raindrop bookmarks

  {Colors.CYAN}Content Processing (LLM analysis):{Colors.END}
    python scripts/run_processing.py list                    # List all ingested content
    python scripts/run_processing.py list --status pending   # List pending content
    python scripts/run_processing.py process-pending         # Process all pending content
    python scripts/run_processing.py process <UUID>          # Process specific content

{Colors.BOLD}Docker Commands:{Colors.END}

  {Colors.CYAN}Services:{Colors.END}
    docker compose up -d                # Start all services
    docker compose down                 # Stop all services
    docker compose logs -f              # View all logs
    docker compose ps                   # Check service status
    docker compose up -d --build        # Rebuild and restart

  {Colors.CYAN}Database Access:{Colors.END}
    # PostgreSQL
    docker exec -it project_second_brain-postgres-1 psql -U $POSTGRES_USER -d $POSTGRES_DB

    # Neo4j Browser
    open http://localhost:7474

    # Redis CLI
    docker exec -it project_second_brain-redis-1 redis-cli

{Colors.BOLD}Local Development (without Docker):{Colors.END}

  {Colors.CYAN}Backend:{Colors.END}
    cd backend && pip install -r requirements.txt
    uvicorn app.main:app --reload

  {Colors.CYAN}Frontend:{Colors.END}
    cd frontend && npm install
    npm run dev

{Colors.BOLD}Documentation:{Colors.END}

  {Colors.CYAN}Project Documentation:{Colors.END}
    README.md                           - Project overview, architecture
    TESTING.md                          - Testing guide
    LEARNING_THEORY.md                  - Learning science foundations

  {Colors.CYAN}Design Documents:{Colors.END}
    docs/design_docs/00_system_overview.md      - System architecture
    docs/design_docs/01_ingestion_layer.md      - Content ingestion
    docs/design_docs/02_llm_processing_layer.md - LLM processing
    docs/design_docs/05_learning_system.md      - Learning system design
    docs/design_docs/06_backend_api.md          - API documentation

  {Colors.CYAN}Implementation Plans:{Colors.END}
    docs/implementation_plan/OVERVIEW.md        - Roadmap overview

{Colors.BOLD}Support:{Colors.END}

  If you encounter issues:
  1. Check docker compose logs -f
  2. Ensure all required API keys are set in .env
  3. Try python scripts/setup/reset_all.py --dry-run to diagnose state
  4. Check docs/implementation_plan/tech_debt.md for known issues
""")


# =============================================================================
# Main Entry Point
# =============================================================================


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Second Brain - Complete Project Setup",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/setup_project.py                  # Full interactive setup
  python scripts/setup_project.py --non-interactive  # Use defaults
  python scripts/setup_project.py --env-only       # Only configure .env
  python scripts/setup_project.py --help-only      # Show help/documentation
  python scripts/setup_project.py --help-env       # Show env var reference
        """,
    )

    # Mode selection
    mode = parser.add_argument_group("Setup Mode")
    mode.add_argument(
        "--non-interactive",
        action="store_true",
        help="Non-interactive mode (use defaults or existing .env)",
    )
    mode.add_argument(
        "--env-only",
        action="store_true",
        help="Only configure environment variables",
    )
    mode.add_argument(
        "--vault-only",
        action="store_true",
        help="Only set up vault structure",
    )
    mode.add_argument(
        "--services-only",
        action="store_true",
        help="Only start Docker services",
    )
    mode.add_argument(
        "--help-only",
        action="store_true",
        help="Only show help and documentation",
    )
    mode.add_argument(
        "--help-env",
        action="store_true",
        help="Show detailed environment variable reference",
    )

    # Skip options
    skip = parser.add_argument_group("Skip Options")
    skip.add_argument(
        "--skip-env",
        action="store_true",
        help="Skip environment configuration",
    )
    skip.add_argument(
        "--skip-vault",
        action="store_true",
        help="Skip vault setup",
    )
    skip.add_argument(
        "--skip-services",
        action="store_true",
        help="Skip starting Docker services",
    )
    skip.add_argument(
        "--skip-migrations",
        action="store_true",
        help="Skip running database migrations",
    )

    return parser.parse_args()


def main() -> int:
    """Main entry point."""
    args = parse_args()

    # Handle help-only modes
    if args.help_env:
        show_env_help()
        return 0

    if args.help_only:
        show_help("Help & Documentation")
        return 0

    print_header("🧠 Second Brain - Project Setup")
    print_info("This script will help you set up the complete Second Brain system.")
    print_info("Press Ctrl+C at any time to cancel.\n")

    success = True
    env_values: dict[str, str] = {}

    try:
        # Determine what to do
        do_all = not any([args.env_only, args.vault_only, args.services_only])
        do_env = (do_all or args.env_only) and not args.skip_env
        do_vault = (do_all or args.vault_only) and not args.skip_vault
        do_services = (do_all or args.services_only) and not args.skip_services
        do_migrations = do_services and not args.skip_migrations

        # Step 1: Environment Configuration
        if do_env:
            env_values = setup_environment(interactive=not args.non_interactive)
        else:
            # Load existing env for other steps
            env_values = load_existing_env()

        # Step 2: Vault Setup
        if do_vault:
            data_dir = env_values.get("DATA_DIR", "~/workspace/obsidian/second_brain")
            data_dir = os.path.expanduser(data_dir)
            if not setup_vault(data_dir):
                print_warning("Vault setup had issues (see above)")
                # Don't fail completely - vault might be partially set up

        # Step 3: Docker Services
        if do_services:
            if not start_docker_services():
                print_warning("Docker services failed to start")
                success = False
            elif do_migrations:
                # Wait a bit for services to be ready
                print_info("Waiting for services to be ready...")
                time.sleep(5)
                if not run_migrations():
                    print_warning("Migrations failed (you may need to run manually)")

        # Show help guide
        show_help("🎉 Setup Complete!")

        return 0 if success else 1

    except KeyboardInterrupt:
        print("\n\n")
        print_warning("Setup cancelled by user")
        return 1
    except Exception as e:
        print_failure(f"Setup failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
