# Contributing to Second Brain

Thank you for your interest in contributing to Second Brain! This document provides guidelines and instructions for contributing to the project.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Development Setup](#development-setup)
- [Development Workflow](#development-workflow)
  - [Branching Strategy](#branching-strategy)
  - [Making Changes](#making-changes)
  - [Commit Message Convention](#commit-message-convention)
- [Code Style Guidelines](#code-style-guidelines)
  - [Python (Backend)](#python-backend)
  - [JavaScript/React (Frontend)](#javascriptreact-frontend)
- [Testing Requirements](#testing-requirements)
  - [Backend Tests](#backend-tests)
  - [Frontend Tests](#frontend-tests)
  - [Running All Tests](#running-all-tests)
- [Pull Request Process](#pull-request-process)
- [Reporting Issues](#reporting-issues)
- [Documentation](#documentation)
- [Questions?](#questions)

---

## Code of Conduct

Please read and follow our [Code of Conduct](CODE_OF_CONDUCT.md) to help maintain a welcoming and inclusive community.

---

## Getting Started

### Prerequisites

- **Python 3.11+** - Backend runtime
- **Node.js 18+** - Frontend build tools
- **Docker Desktop** - Required for running PostgreSQL, Redis, and Neo4j
- **At least one LLM API key** (Gemini, Mistral, OpenAI, or Anthropic)

### Development Setup

1. **Fork and clone the repository**

   ```bash
   git clone https://github.com/YOUR_USERNAME/project_second_brain.git
   cd project_second_brain
   ```

2. **Run the interactive setup script**

   ```bash
   python scripts/setup_project.py
   ```

   This will guide you through:
   - Environment configuration (API keys, database credentials)
   - Vault setup (Obsidian folder structure, templates)
   - Docker services startup
   - Database migrations

3. **Verify the setup**

   ```bash
   # Check all services are running
   docker compose ps

   # Access the application
   # Frontend: http://localhost:3000
   # Backend API: http://localhost:8000
   # API Docs: http://localhost:8000/docs
   ```

### Local Development (without Docker for backend/frontend)

If you prefer to run the backend or frontend outside of Docker:

**Backend:**

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

**Frontend:**

```bash
cd frontend
npm install
npm run dev
```

Note: You still need Docker for PostgreSQL, Redis, and Neo4j:

```bash
docker compose up -d postgres redis neo4j
```

---

## Development Workflow

### Branching Strategy

- `main` - Production-ready code
- Feature branches - Named `feature/description` or `fix/description`

```bash
# Create a feature branch
git checkout -b feature/add-new-pipeline

# Or for bug fixes
git checkout -b fix/card-generation-error
```

### Making Changes

1. Create a feature branch from `main`
2. Make your changes
3. Write/update tests as needed
4. Ensure all tests pass
5. Commit with a descriptive message
6. Push and create a pull request

### Commit Message Convention

We use [Conventional Commits](https://www.conventionalcommits.org/) format:

```
<type>: <description>

[optional body]

[optional footer]
```

**Types:**

| Type | Description |
|------|-------------|
| `feat` | New feature |
| `fix` | Bug fix |
| `docs` | Documentation only |
| `style` | Code style (formatting, no logic change) |
| `refactor` | Code refactoring (no feature/fix) |
| `perf` | Performance improvement |
| `test` | Adding or updating tests |
| `chore` | Maintenance tasks |

**Examples:**

```bash
feat: Add voice memo transcription pipeline
fix: Resolve card generation timeout for long content
docs: Update API documentation for review endpoints
refactor: Extract magic numbers to named constants (TD-013)
perf: Fix N+1 query in mastery_service.py (TD-014)
test: Add unit tests for frontmatter parsing
chore: Update dependencies and clean up unused imports
```

---

## Code Style Guidelines

### Python (Backend)

**General Guidelines:**

- Use type hints for all function signatures
- Use `from __future__ import annotations` for forward references
- Follow PEP 8 with 88-character line length (Black formatter style)
- Use async/await for I/O operations

**Import Organization:**

```python
from __future__ import annotations

# Standard library imports
import os
from datetime import datetime, timezone
from typing import TYPE_CHECKING

# Third-party imports
from fastapi import APIRouter, Depends
from pydantic import BaseModel

# Local application imports
from app.models import SomeModel
from app.services import SomeService

if TYPE_CHECKING:
    # Type-only imports (for circular dependency avoidance)
    from app.services.other import OtherService
```

**Naming Conventions:**

- Classes: `PascalCase`
- Functions/methods: `snake_case`
- Constants: `UPPER_SNAKE_CASE`
- Private methods: `_leading_underscore`

**Constants over Magic Numbers:**

```python
# Good
MAX_RETRY_ATTEMPTS = 3
DEFAULT_TIMEOUT_SEC = 30

def fetch_with_retry():
    for _ in range(MAX_RETRY_ATTEMPTS):
        ...

# Bad
def fetch_with_retry():
    for _ in range(3):  # Magic number
        ...
```

### JavaScript/React (Frontend)

**General Guidelines:**

- Use functional components with hooks
- Prefer `const` over `let`
- Use ES6+ features (arrow functions, destructuring, template literals)

**ESLint Configuration:**

The project uses ESLint with React and React Hooks plugins. Key rules:
- `react-hooks/rules-of-hooks`: error
- `react-hooks/exhaustive-deps`: warn
- `no-unused-vars`: warn (with `_` prefix exception)

**Formatting:**

Use Prettier for consistent formatting:

```bash
cd frontend
npm run format
```

**Component Structure:**

```jsx
import { useState, useEffect } from 'react'

// Constants at top
const DEFAULT_PAGE_SIZE = 20

// Component
export function MyComponent({ prop1, prop2 }) {
  const [state, setState] = useState(null)

  useEffect(() => {
    // Effect logic
  }, [dependency])

  // Render
  return (
    <div>
      {/* JSX */}
    </div>
  )
}
```

---

## Testing Requirements

All contributions should include appropriate tests. See [TESTING.md](TESTING.md) for comprehensive testing documentation.

### Backend Tests

Tests are in `backend/tests/` organized as:
- `unit/` - Tests without external dependencies
- `integration/` - Tests requiring running services

```bash
cd backend

# Run unit tests
pytest tests/unit/ -v

# Run integration tests (requires Docker services)
pytest tests/integration/ -v

# Run with coverage
pytest tests/ --cov=app --cov-report=html
```

**Test Naming:**

```
test_<method_name>_<scenario>_<expected_result>

# Examples:
test_create_card_returns_valid_response
test_process_pdf_fails_for_invalid_file
```

### Frontend Tests

**Unit Tests (Vitest):**

```bash
cd frontend

# Run tests
npm test

# Run with coverage
npm run test:coverage
```

**E2E Tests (Playwright):**

```bash
cd frontend

# Run e2e tests
npm run test:e2e

# Run with UI (for debugging)
npm run test:e2e:ui
```

### Running All Tests

Use the unified test runner:

```bash
# Run all tests
python scripts/run_all_tests.py

# Run specific suites
python scripts/run_all_tests.py --backend-unit
python scripts/run_all_tests.py --frontend
python scripts/run_all_tests.py --frontend-e2e

# With coverage
python scripts/run_all_tests.py --coverage
```

---

## Pull Request Process

1. **Before submitting:**
   - Ensure all tests pass: `python scripts/run_all_tests.py`
   - Run linting: `cd frontend && npm run lint`
   - Update documentation if needed

2. **PR Title:** Use the same convention as commit messages
   ```
   feat: Add bulk import for bookmarks
   ```

3. **PR Description:** Include:
   - Summary of changes
   - Related issue number (if applicable)
   - Testing performed
   - Screenshots (for UI changes)

4. **Review Process:**
   - At least one approval required
   - All CI checks must pass
   - Address review feedback promptly

5. **Merging:**
   - Squash and merge preferred for feature branches
   - Delete branch after merge

---

## Reporting Issues

When reporting bugs or requesting features, please include:

**For Bugs:**
- Steps to reproduce
- Expected vs. actual behavior
- Environment details (OS, browser, Python/Node versions)
- Error messages or logs
- Screenshots if applicable

**For Features:**
- Use case description
- Proposed solution (if any)
- Alternatives considered

---

## Documentation

- **Design docs:** `docs/design_docs/` - Technical specifications
- **Implementation plans:** `docs/implementation_plan/` - Roadmaps and task lists
- **API docs:** Auto-generated at http://localhost:8000/docs

When adding new features:
- Update relevant design docs if architecture changes
- Add docstrings to new functions/classes
- Update README if user-facing behavior changes

---

## Questions?

If you have questions about contributing:

1. Check existing documentation in `docs/`
2. Look through open/closed issues
3. Open a new issue with the "question" label

Thank you for contributing to Second Brain!
