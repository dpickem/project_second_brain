# Technical Debt Tracker

This document tracks known technical debt items and improvements for open-source release readiness.

## Table of Contents

- [Priority Levels](#priority-levels)
- [Open-Source Release Blockers](#open-source-release-blockers)
  - [TD-001: Missing LICENSE file](#td-001-missing-license-file)
  - [TD-002: Missing CONTRIBUTING.md](#td-002-missing-contributingmd)
  - [TD-003: Missing CODE_OF_CONDUCT.md](#td-003-missing-code_of_conductmd)
  - [TD-004: CORS wildcard allows all origins](#td-004-cors-wildcard-allows-all-origins)
  - [TD-005: Missing production deployment documentation](#td-005-missing-production-deployment-documentation)
  - [TD-006: README updates for open-source](#td-006-readme-updates-for-open-source)
  - [TD-007: Add CHANGELOG.md and SECURITY.md](#td-007-add-changelogmd-and-securitymd)
- [Backend Tech Debt](#backend-tech-debt)
  - ✅ ~~[TD-008: Use TYPE_CHECKING for type annotation imports](#td-008-use-type_checking-for-type-annotation-imports)~~
  - ✅ ~~[TD-009: Complete LLM/OCR/VLM usage tracking](#td-009-complete-llmocrvlm-usage-tracking)~~
  - ✅ ~~[TD-010: Model factory methods for cross-layer conversions](#td-010-model-factory-methods-for-cross-layer-conversions)~~
  - ✅ ~~[TD-011: Clean up imports and move to top of files](#td-011-clean-up-imports-and-move-to-top-of-files)~~
  - [TD-012: Robust deduplication and cleanup on reprocessing](#td-012-robust-deduplication-and-cleanup-on-reprocessing)
  - ✅ ~~[TD-013: Eliminate magic numbers](#td-013-eliminate-magic-numbers)~~
  - [TD-014: N+1 query in mastery_service.py](#td-014-n1-query-in-mastery_servicepy)
  - ✅ ~~[TD-015: Inconsistent datetime usage](#td-015-inconsistent-datetime-usage)~~
  - [TD-016: Incomplete TODO implementations](#td-016-incomplete-todo-implementations)
  - [TD-017: Large service files need splitting](#td-017-large-service-files-need-splitting)
  - [TD-018: Inconsistent error handling patterns](#td-018-inconsistent-error-handling-patterns)
  - ✅ ~~[TD-019: Missing type hints](#td-019-missing-type-hints)~~
  - [TD-020: Hardcoded upload directory](#td-020-hardcoded-upload-directory)
  - [TD-021: Review and clean up dependencies](#td-021-review-and-clean-up-dependencies)
- [Frontend Tech Debt](#frontend-tech-debt)
  - [TD-022: Remove console.log statements](#td-022-remove-consolelog-statements)
  - [TD-023: Hardcoded URLs throughout frontend](#td-023-hardcoded-urls-throughout-frontend)
  - [TD-024: Missing prop validation](#td-024-missing-prop-validation)
  - [TD-025: Missing error boundaries](#td-025-missing-error-boundaries)
  - [TD-026: Accessibility issues](#td-026-accessibility-issues)
  - [TD-027: Performance - missing memoization](#td-027-performance---missing-memoization)
  - [TD-028: Magic numbers in frontend](#td-028-magic-numbers-in-frontend)
  - [TD-029: Inconsistent state management patterns](#td-029-inconsistent-state-management-patterns)
- [Tests & Scripts](#tests--scripts)
  - [TD-030: Skipped tests due to missing dependencies](#td-030-skipped-tests-due-to-missing-dependencies)
  - [TD-031: Hardcoded path in run_processing.py](#td-031-hardcoded-path-in-run_processingpy)
  - [TD-032: Prototype code should be moved or removed](#td-032-prototype-code-should-be-moved-or-removed)
  - [TD-033: Incomplete test implementation](#td-033-incomplete-test-implementation)
- [Documentation & Config](#documentation--config)
  - [TD-034: Docker compose production configuration](#td-034-docker-compose-production-configuration)
  - [TD-035: Environment variable validation](#td-035-environment-variable-validation)
  - [TD-036: Missing platform-specific setup instructions](#td-036-missing-platform-specific-setup-instructions)
  - [TD-037: Data directory uses tilde expansion](#td-037-data-directory-uses-tilde-expansion)
- [Summary by Priority](#summary-by-priority)
- [Completed Items](#completed-items)
- [Notes](#notes)

---

## Priority Levels

- **P0**: Critical - Must fix before open-source release
- **P1**: High - Should address for clean release
- **P2**: Medium - Address when touching related code
- **P3**: Low - Nice to have / future improvement

---

## Open-Source Release Blockers

### TD-001: Missing LICENSE file
**Priority**: P0  
**Status**: Open  
**Area**: Repository root

**Description**: No LICENSE file exists. Required for open-source release.

**Action**: Add a LICENSE file (MIT, Apache 2.0, etc.) to the repository root.

---

### TD-002: Missing CONTRIBUTING.md
**Priority**: P0  
**Status**: Open  
**Area**: Repository root

**Description**: No contribution guidelines exist. Essential for community contributions.

**Required Content**:
- Development setup instructions
- Code style guidelines
- PR process and requirements
- Testing requirements
- Commit message conventions

---

### TD-003: Missing CODE_OF_CONDUCT.md
**Priority**: P0  
**Status**: Open  
**Area**: Repository root

**Description**: No code of conduct exists. Standard for open-source projects.

**Action**: Add Contributor Covenant or similar code of conduct.

---

### TD-004: CORS wildcard allows all origins
**Priority**: P0  
**Status**: Open  
**Area**: Security

**Description**: `backend/app/main.py:117` uses `allow_origins=["*"]` with only a comment about configuring for production.

**Current Code**:
```python
allow_origins=["*"]  # Configure appropriately for production
```

**Fix**: 
- Use environment variable for CORS origins
- Default to restrictive setting in production
- Document CORS configuration in deployment guide

---

### TD-005: Missing production deployment documentation
**Priority**: P0  
**Status**: Open  
**Area**: Documentation

**Required Documentation**:
- [ ] `docs/deployment/production.md` - Production deployment guide
- [ ] `docs/deployment/security.md` - Security hardening guide
- [ ] SSL/TLS setup instructions
- [ ] Reverse proxy (Nginx) configuration examples
- [ ] Database backup/restore procedures

---

### TD-006: README updates for open-source
**Priority**: P1  
**Status**: Open  
**Area**: Documentation

**Missing Sections**:
- Security policy
- Contributing section (reference to CONTRIBUTING.md)
- License section
- Production deployment overview
- Clone URL should be generic (not user-specific GitHub path)

---

### TD-007: Add CHANGELOG.md and SECURITY.md
**Priority**: P1  
**Status**: Open  
**Area**: Repository root

**Files to Create**:
- `CHANGELOG.md` - Version history and changes
- `SECURITY.md` - Security policy and vulnerability reporting process
- `.github/ISSUE_TEMPLATE.md` - Bug report/feature request template
- `.github/PULL_REQUEST_TEMPLATE.md` - PR description template

---

## Backend Tech Debt

### ✅ TD-008: Use `TYPE_CHECKING` for type annotation imports
**Priority**: P2  
**Status**: ✅ Completed  
**Area**: Backend services

**Description**: Standardize `typing.TYPE_CHECKING` for imports only needed for type hints.

**Target Pattern**:
```python
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.services.some_service import SomeService

class MyClass:
    def __init__(self, service: SomeService) -> None:
        ...
```

**Files to Review**:
- [ ] `backend/app/services/learning/*.py`
- [ ] `backend/app/services/*.py`
- [ ] `backend/app/routers/*.py`
- [ ] `backend/app/pipelines/*.py`

---

### ✅ TD-009: Complete LLM/OCR/VLM usage tracking
**Priority**: P1  
**Status**: ✅ Completed  
**Area**: LLM integration

**Description**: Ensure ALL external model calls are tracked via `LLMUsage` and persisted.

**Audit Required**:
- [ ] `backend/app/services/llm/client.py` - Core LLM client
- [ ] `backend/app/services/assistant/service.py` - Chat/RAG calls
- [ ] `backend/app/services/processing/stages/*.py` - Pipeline stages
- [ ] `backend/app/services/learning/card_generator.py` - Card generation
- [ ] `backend/app/services/learning/exercise_generator.py` - Exercise generation
- [ ] `backend/app/pipelines/*.py` - OCR, transcription
- [ ] `backend/app/services/learning/evaluator.py` - Answer evaluation

**Acceptance Criteria**:
- Every external model API call creates an `LLMUsage` record
- Usage records include: model, tokens, purpose, timestamp, content_id (if applicable)
- Analytics API exposes aggregated usage data

---

### ✅ TD-010: Model factory methods for cross-layer conversions
**Priority**: P2  
**Status**: ✅ Completed  
**Area**: Backend models

**Description**: Standardize factory constructors for converting between DB/Pydantic models.
Use `from __future__ import annotations` for cleaner return type hints (no string quotes needed).

**Target Pattern**:
```python
from __future__ import annotations

class SomeModel:
    @classmethod
    def from_db_record(cls, record: SomeRecord) -> SomeModel:
        """Factory method for DB → Pydantic conversion."""
        ...
```

**Completed Factory Methods**:

*Processing models (`app/models/processing.py`)*:
- [x] `Concept.from_db_record(concept_record)` - ConceptRecord → Concept
- [x] `Connection.from_db_record(connection_record)` - ConnectionRecord → Connection
- [x] `FollowupTask.from_db_record(followup_record)` - FollowupRecord → FollowupTask
- [x] `MasteryQuestion.from_db_record(question_record)` - QuestionRecord → MasteryQuestion

*Content models (`app/models/content.py`)*:
- [x] `UnifiedContent.from_db_content(db_content)` - Already implemented (Content → UnifiedContent)
- [x] `Annotation.from_db_record(annotation_record)` - Annotation (DB) → Annotation (Pydantic)

*Learning models (`app/models/learning.py`)*:
- [x] `CardResponse.from_db_record(card)` - SpacedRepCard → CardResponse
- [x] `ExerciseResponse.from_db_record(exercise)` - Exercise → ExerciseResponse
- [x] `SessionSummary.from_db_record(session)` - PracticeSession → SessionSummary

*Assistant models (`app/models/assistant.py`)*:
- [x] `MessageInfo.from_db_record(message)` - AssistantMessage → MessageInfo
- [x] `ConversationSummary.from_db_record(conversation)` - AssistantConversation → ConversationSummary
- [x] `ConversationDetail.from_db_record(conversation)` - AssistantConversation → ConversationDetail

*DB models (`app/db/models_processing.py`)*:
- [x] `ProcessingRun.from_processing_result(...)` - Already implemented (ProcessingResult → ProcessingRun)

---

### ✅ TD-011: Clean up imports and move to top of files
**Priority**: P2  
**Status**: ✅ Completed  
**Area**: Code organization

**Target Pattern**:
```python
from __future__ import annotations

# Standard library imports
import os
import sys
from typing import TYPE_CHECKING

# Third-party imports
from fastapi import APIRouter
from pydantic import BaseModel

# Local application imports
from app.models import SomeModel
from app.services import SomeService

if TYPE_CHECKING:
    # Type-only imports (for circular dependency avoidance)
    from app.services.other import OtherService
```

**Files to Review**:
- [ ] `backend/app/services/**/*.py`
- [ ] `backend/app/routers/*.py`
- [ ] `frontend/src/**/*.jsx`
- [ ] `frontend/src/**/*.js`

---

### TD-012: Robust deduplication and cleanup on reprocessing
**Priority**: P1  
**Status**: Open  
**Area**: Data integrity

**Description**: Ensure deduplication works robustly throughout the system. When content is reprocessed, properly clean up all old entries.

**Required Cleanup on Reprocessing**:
1. **PostgreSQL**: Old `ProcessingRun`, `TagAssignment`, `Connection`, `Card`, `ExtractionResult` records
2. **Neo4j**: Old nodes and relationships
3. **Obsidian**: Old note files and stale wikilinks

**Acceptance Criteria**:
- Reprocessing the same content results in exactly one entry per store
- No orphaned records in SQL, Neo4j, or Obsidian after reprocessing
- All relationships/connections are properly updated or removed

---

### ✅ TD-013: Eliminate magic numbers
**Priority**: P2  
**Status**: ✅ Completed  
**Area**: Code quality

**Files with Magic Numbers**:
- [x] `backend/app/services/learning/*.py` - Learning algorithm parameters
- [ ] `backend/app/services/processing/stages/*.py` - Processing thresholds (already uses constants)
- [x] `backend/app/services/llm/*.py` - Token limits, timeouts
- [x] `backend/app/routers/*.py` - Pagination limits, defaults
- [x] `backend/app/pipelines/*.py` - Batch sizes, retry counts (already uses constants)
- [x] `backend/app/pipelines/book_ocr.py:82-100` - Already has `DEFAULT_OCR_MAX_TOKENS = 8000`, etc.

**Target Pattern**:
```python
# At top of file, after imports
DEFAULT_BATCH_SIZE = 100
MAX_RETRY_ATTEMPTS = 3
MASTERY_THRESHOLD = 0.8

def process_items(items):
    for batch in chunks(items, DEFAULT_BATCH_SIZE):
        ...
```

---

### TD-014: N+1 query in mastery_service.py
**Priority**: P1  
**Status**: Open  
**Area**: Performance

**Location**: `backend/app/services/learning/mastery_service.py:412-420`

**Issue**: Loop executes a separate query per topic:
```python
for topic_path in topic_paths:
    card_count_query = select(func.count(SpacedRepCard.id)).where(...)
    result = await self.db.execute(card_count_query)
```

**Fix**: Batch queries or use a single query with GROUP BY.

---

### ✅ TD-015: Inconsistent datetime usage
**Priority**: P1  
**Status**: ✅ Completed  
**Area**: Code consistency

**Issue**: Mix of `datetime.utcnow()` and `datetime.now()` across codebase.

**Affected Files**:
- [x] `backend/app/routers/capture.py` - now uses `datetime.now(timezone.utc)`
- [x] `backend/app/services/tasks.py` - now uses `datetime.now(timezone.utc)`
- [x] `backend/app/services/obsidian/frontmatter.py` - now uses `datetime.now(timezone.utc)`

**Fix**: Standardized on `datetime.now(timezone.utc)` for timezone-aware timestamps across all backend files.

---

### TD-016: Incomplete TODO implementations
**Priority**: P2  
**Status**: Open  
**Area**: Implementation gaps

**TODOs Found**:
1. `backend/app/services/tasks.py:957` - `cleanup_old_tasks()` needs implementation
2. `backend/app/pipelines/base.py:190` - `check_duplicate()` returns None, needs DB query
3. `backend/app/pipelines/utils/vlm_client.py:78` - Remove backwards compatibility alias

---

### TD-017: Large service files need splitting
**Priority**: P2  
**Status**: Open  
**Area**: Code organization

**Large Files**:
- `backend/app/services/learning/mastery_service.py` - 1894+ lines
- `backend/app/services/assistant/service.py` - 1007+ lines
- `backend/app/services/learning/evaluator.py` - 828+ lines

**Action**: Split into smaller, focused modules.

---

### TD-018: Inconsistent error handling patterns
**Priority**: P2  
**Status**: Open  
**Area**: Code consistency

**Issues**:
- Most endpoints use `HTTPException` from FastAPI
- Some use custom `ServiceError` exceptions
- `backend/app/routers/assistant.py` uses `@handle_endpoint_errors` decorator
- Other routers don't use this pattern consistently

**Fix**: Standardize on consistent error handling pattern across all routers.

---

### ✅ TD-019: Missing type hints
**Priority**: P2  
**Status**: ✅ Completed (critical files)  
**Area**: Type safety

**Original scope** (completed):
- `backend/app/services/tasks.py` - Added TypedDict return types
- `backend/app/services/obsidian/vault.py` - Added VaultStructureResult
- `backend/app/services/processing/output/obsidian_generator.py` - Added TemplateData

**Extended scope** (completed):
- `backend/app/routers/vault.py` - 10 endpoints
- `backend/app/routers/health.py` - 3 endpoints
- `backend/app/routers/processing.py` - 4 endpoints
- `backend/app/services/scheduler.py` - 7 functions
- `backend/app/main.py` - 3 functions

**Remaining** (lower priority, ~47 functions):
- `services/obsidian/watcher.py` - 9 functions
- `services/knowledge_graph/client.py` - 5 methods
- `middleware/rate_limit.py` - 4 decorators
- Other internal helpers and inner functions

Coverage improved from ~84% to ~90% for return type hints.

---

### TD-020: Hardcoded upload directory
**Priority**: P2  
**Status**: Open  
**Area**: Configuration

**Location**: `backend/app/config/pipelines.py:102`
```python
UPLOAD_DIR: str = "/tmp/second_brain_uploads"
```

**Fix**: Make configurable via environment variable.

---

### TD-021: Review and clean up dependencies
**Priority**: P2  
**Status**: Open  
**Area**: Dependencies

**Issues**:
- `backend/requirements.txt` uses `>=` constraints - consider pinning for production
- `aisuite` (line 47) - unclear if actively used
- Both `pdfplumber` and `pymupdf` included - code primarily uses `pymupdf`

---

## Frontend Tech Debt

### TD-022: Remove console.log statements
**Priority**: P1  
**Status**: Open  
**Area**: Production code quality

**Issue**: 76+ console.log/console.warn statements in production code.

**Key Locations**:
- `frontend/src/pages/PracticeSession.jsx:215, 219`
- `frontend/src/components/dashboard/StreakCalendar.jsx:77, 134`
- `frontend/src/api/client.js:159`
- `frontend/capture/src/` - Multiple files with extensive logging
- `frontend/capture/public/sw.js` - Service worker logging

**Fix**: Remove or gate behind `import.meta.env.DEV` checks.

---

### TD-023: Hardcoded URLs throughout frontend
**Priority**: P1  
**Status**: Open  
**Area**: Configuration

**Locations**:
- `frontend/src/api/client.js:60` - `'http://localhost:8000'`
- `frontend/src/api/capture.js:58, 85, 113` - Multiple localhost instances
- `frontend/src/api/typed-client.js:63` - localhost
- `frontend/capture/src/api/capture.js:23, 28` - localhost
- `frontend/capture/index.html:25` - Hardcoded preconnect
- `frontend/capture/vite.config.js:28` - Hardcoded proxy target
- `frontend/scripts/generate-api-types.js:29` - Hardcoded backend URL

**Fix**: Use environment variables consistently.

---

### TD-024: Missing prop validation
**Priority**: P2  
**Status**: Open  
**Area**: Type safety

**Issue**: No PropTypes or TypeScript. `eslint.config.js:37` has `'react/prop-types': 'off'`.

**Affected Components**:
- `frontend/src/App.jsx:92` - `NavItem` component
- `frontend/src/pages/Dashboard.jsx:172` - `QuickLink` component
- `frontend/src/components/dashboard/QuickCapture.jsx:16`
- `frontend/src/components/common/Input.jsx` - All components

**Fix**: Add PropTypes or consider TypeScript migration.

---

### TD-025: Missing error boundaries
**Priority**: P1  
**Status**: Open  
**Area**: Error handling

**Issue**: No `ErrorBoundary` component exists. React errors will crash the entire app.

**Fix**: Implement error boundaries at route/page level.

---

### TD-026: Accessibility issues
**Priority**: P2  
**Status**: Open  
**Area**: Accessibility

**Missing aria labels**:
- `frontend/src/components/common/Input.jsx:74-84` - Password toggle button
- `frontend/src/components/common/Input.jsx:185-193` - SearchInput clear button
- `frontend/src/pages/Assistant.jsx:144-150` - Quick prompt buttons
- `frontend/src/pages/Knowledge.jsx` - Many interactive elements

**Other issues**:
- Missing visible focus indicators
- No focus trap in modals/dialogs
- Keyboard navigation gaps

---

### TD-027: Performance - missing memoization
**Priority**: P2  
**Status**: Open  
**Area**: Performance

**Issues**:
- `frontend/src/pages/Dashboard.jsx` - `QuickLink` not memoized
- `frontend/src/pages/Assistant.jsx:79-84` - `quickPrompts` recreated every render
- `frontend/src/components/dashboard/QuickCapture.jsx` - callbacks not memoized

**Fix**: Add `React.memo`, `useMemo`, and `useCallback` where appropriate.

---

### TD-028: Magic numbers in frontend
**Priority**: P2  
**Status**: Open  
**Area**: Code quality

**Locations**:
- `frontend/src/pages/Dashboard.jsx:57` - `dailyGoal = 20`
- `frontend/src/pages/Knowledge.jsx:730` - `pageSize = 200`
- `frontend/src/components/GraphViewer/GraphViewer.jsx:69-70` - `width: 800, height: 600`
- `frontend/src/components/GraphViewer/GraphViewer.jsx:165-166` - `-300`, `400`, `100`
- `frontend/src/pages/KnowledgeGraph.jsx:238` - `limit: 200`
- `frontend/src/components/common/Tooltip.jsx:147` - `z-[9999]`

**Fix**: Extract to constants or config.

---

### TD-029: Inconsistent state management patterns
**Priority**: P3  
**Status**: Open  
**Area**: Architecture

**Current State**:
- Zustand stores in `frontend/src/stores/`
- React Query for server state
- Local `useState` throughout
- No clear pattern documentation

**Fix**: Document state management guidelines.

---

## Tests & Scripts

### TD-030: Skipped tests due to missing dependencies
**Priority**: P1  
**Status**: Open  
**Area**: Test coverage

**Skipped Tests**:
- `backend/tests/integration/test_vault_sync.py:24-31` - All tests skipped if `NEO4J_URI` not set
- `backend/tests/integration/test_pipelines.py` - Multiple tests skipped if `SAMPLE_PDF` not found
- `backend/tests/unit/test_code_sandbox.py:260-275` - Skipped if Docker unavailable
- `backend/tests/unit/test_openapi_contract.py:290, 306` - Skipped if snapshot missing

**Fix**: 
- Document test dependencies clearly
- Generate sample files in CI setup
- Add subset of tests that run without optional dependencies

---

### TD-031: Hardcoded path in run_processing.py
**Priority**: P1  
**Status**: Open  
**Area**: Scripts

**Location**: `scripts/run_processing.py:87-89`
```python
os.environ["OBSIDIAN_VAULT_PATH"] = os.path.expanduser(
    "~/workspace/obsidian/second_brain/obsidian"
)
```

**Fix**: Use environment variable with sensible default, or read from `.env`.

---

### TD-032: Prototype code should be moved or removed
**Priority**: P1  
**Status**: Open  
**Area**: Code cleanup

**Files in `prototypes/`**:
- `test_mistral_ocr.py` (554 lines) - Move to `scripts/examples/` or remove
- `test_pdfplumber_annotations.py` (582 lines) - Move or integrate into tests
- `test_pymupdf_annotations.py` (199 lines) - Move or integrate into tests
- `sample_mistral7b.pdf` - Move to `test_data/` or remove

---

### TD-033: Incomplete test implementation
**Priority**: P2  
**Status**: Open  
**Area**: Tests

**Location**: `backend/tests/integration/test_pipelines.py:1001-1010`

**Issue**: Test expects `NotImplementedError` - indicates incomplete implementation.

---

## Documentation & Config

### TD-034: Docker compose production configuration
**Priority**: P1  
**Status**: Open  
**Area**: Deployment

**Issues**:
- Ports exposed to host (5432, 6379, 7474, 7687) - security risk
- No production docker-compose override file
- Missing resource limits (CPU, memory)

**Fix**:
- Create `docker-compose.prod.yml` with resource limits
- Document port security implications
- Add network isolation recommendations

---

### TD-035: Environment variable validation
**Priority**: P2  
**Status**: Open  
**Area**: Configuration

**Issue**: No startup validation for required environment variables.

**Fix**: Add validation at application startup with clear error messages.

---

### TD-036: Missing platform-specific setup instructions
**Priority**: P3  
**Status**: Open  
**Area**: Documentation

**Missing**:
- Platform-specific instructions (Windows, Linux, macOS differences)
- Docker installation verification steps
- Troubleshooting guide for common setup issues
- Post-setup verification checklist

---

### TD-037: Data directory uses tilde expansion
**Priority**: P2  
**Status**: Open  
**Area**: Configuration

**Location**: `.env.example`
```
DATA_DIR=~/workspace/obsidian/second_brain
```

**Issue**: `~` may not expand correctly in all environments (Docker, systemd, etc.).

**Fix**: Use absolute paths or document the limitation.

---

## Summary by Priority

### P0 - Critical (Must fix before release)
- [ ] TD-001: Missing LICENSE file
- [ ] TD-002: Missing CONTRIBUTING.md
- [ ] TD-003: Missing CODE_OF_CONDUCT.md
- [ ] TD-004: CORS wildcard allows all origins
- [ ] TD-005: Missing production deployment documentation

### P1 - High (Should address for clean release)
- [ ] TD-006: README updates for open-source
- [ ] TD-007: Add CHANGELOG.md and SECURITY.md
- ✅ ~~TD-009: Complete LLM/OCR/VLM usage tracking~~
- [ ] TD-012: Robust deduplication and cleanup on reprocessing
- [ ] TD-014: N+1 query in mastery_service.py
- ✅ ~~TD-015: Inconsistent datetime usage~~
- [ ] TD-022: Remove console.log statements
- [ ] TD-023: Hardcoded URLs throughout frontend
- [ ] TD-025: Missing error boundaries
- [ ] TD-030: Skipped tests due to missing dependencies
- [ ] TD-031: Hardcoded path in run_processing.py
- [ ] TD-032: Prototype code should be moved or removed
- [ ] TD-034: Docker compose production configuration

### P2 - Medium (Address when touching related code)
- ✅ ~~TD-008: Use TYPE_CHECKING for type annotation imports~~
- ✅ ~~TD-010: Model factory methods for cross-layer conversions~~
- ✅ ~~TD-011: Clean up imports and move to top of files~~
- ✅ ~~TD-013: Eliminate magic numbers~~
- [ ] TD-016: Incomplete TODO implementations
- [ ] TD-017: Large service files need splitting
- [ ] TD-018: Inconsistent error handling patterns
- ✅ ~~TD-019: Missing type hints~~
- [ ] TD-020: Hardcoded upload directory
- [ ] TD-021: Review and clean up dependencies
- [ ] TD-024: Missing prop validation
- [ ] TD-026: Accessibility issues
- [ ] TD-027: Performance - missing memoization
- [ ] TD-028: Magic numbers in frontend
- [ ] TD-033: Incomplete test implementation
- [ ] TD-035: Environment variable validation
- [ ] TD-037: Data directory uses tilde expansion

### P3 - Low (Nice to have)
- [ ] TD-029: Inconsistent state management patterns
- [ ] TD-036: Missing platform-specific setup instructions

---

## Completed Items

### ✅ TD-008: Use `TYPE_CHECKING` for type annotation imports
**Completed**: 2026-01-26

Standardized import organization across backend files. Moved inline imports to top of files following stdlib → third-party → local pattern. Files updated:
- `backend/app/services/tasks.py` - Moved `sqlalchemy.select`, `ProcessingRun`, `ProcessingRunStatus` to top
- `backend/app/routers/vault.py` - Moved `content_registry` to top, organized imports
- `backend/app/routers/health.py` - Moved `get_vault_manager` to top, organized imports
- `backend/app/pipelines/utils/hash_utils.py` - Moved `urllib.parse` imports to top
- `backend/app/pipelines/utils/image_utils.py` - Moved `PIL.ExifTags` to top
- `backend/app/pipelines/utils/mistral_ocr_client.py` - Moved `re` to top

---

### ✅ TD-011: Clean up imports and move to top of files
**Completed**: 2026-01-26

Same changes as TD-008 (combined effort). Also added documentation comments to `backend/app/services/scheduler.py` explaining intentional deferred imports for Celery tasks (to avoid circular dependencies and heavy module loading at scheduler init).

---

### ✅ TD-009: Complete LLM/OCR/VLM usage tracking
**Completed**: 2026-01-26

Added CostTracker.log_usage() calls to all LLM call sites that were missing usage tracking:
- `backend/app/services/assistant/service.py` - Chat responses and concept explanations now tracked
- `backend/app/routers/review.py` - Card generation usages now persisted
- `backend/app/routers/practice.py` - Exercise generation usages now persisted
- `backend/app/services/learning/evaluator.py` - Text and code evaluation usages now tracked

All LLM calls now log to `llm_usage_log` table with pipeline and operation metadata for cost attribution.

---

### ✅ TD-019: Missing type hints
**Completed**: 2026-01-26

Added TypedDict definitions and return type annotations across critical backend files.

**Phase 1 - TypedDict definitions:**
- `services/obsidian/vault.py` - Added `VaultStructureResult`
- `services/processing/output/obsidian_generator.py` - Added `TemplateData`
- `services/tasks.py` - Added 6 TypedDicts for Celery task returns

**Phase 2 - Router and service return types:**
- `routers/vault.py` - 10 endpoints now have explicit return types
- `routers/health.py` - 3 endpoints
- `routers/processing.py` - 4 endpoints
- `services/scheduler.py` - 7 functions with `-> None`
- `main.py` - 3 functions (lifespan, root, graph)

Coverage improved from ~84% to ~90%. Remaining ~47 functions are internal helpers
and middleware that can be addressed when touching those files.

---

### ✅ TD-013: Eliminate magic numbers
**Completed**: 2026-01-26

Extracted magic numbers to named constants across key backend files:

**`backend/app/services/tasks.py`**:
- Added retry configuration constants: `CONTENT_RETRY_ATTEMPTS`, `CONTENT_RETRY_MULTIPLIER_SEC`, etc.
- Added sync constants: `DEFAULT_SYNC_HOURS`

**`backend/app/services/llm/client.py`**:
- Added LLM retry constants: `LLM_RETRY_ATTEMPTS`, `LLM_RETRY_MULTIPLIER_SEC`, etc.
- Added default generation parameters: `DEFAULT_TEMPERATURE`, `DEFAULT_MAX_TOKENS`

**`backend/app/routers/capture.py`**:
- Added title generation constants: `MAX_TITLE_LENGTH`, `TITLE_TRUNCATE_SUFFIX`
- Added URL fetch constants: `URL_FETCH_TIMEOUT_SEC`, `URL_FETCH_USER_AGENT`

**`backend/app/routers/health.py`**:
- Added `CELERY_INSPECT_TIMEOUT_SEC`

**`backend/app/services/scheduler.py`**:
- Added scheduler constants: `DEFAULT_SYNC_HOURS`, `GITHUB_SYNC_DEFAULT_LIMIT`
- Added cron schedule constants: `RAINDROP_SYNC_INTERVAL_HOURS`, `GITHUB_SYNC_CRON_HOUR`, etc.
- Added `MISFIRE_GRACE_TIME_SEC`

Note: Many pipeline files (book_ocr.py, voice_transcribe.py, etc.) already had well-named constants.

---

### ✅ TD-015: Inconsistent datetime usage
**Completed**: 2026-01-26

Standardized all datetime usage to `datetime.now(timezone.utc)` across backend files:

**Files updated**:
- `backend/app/routers/capture.py` - 12 occurrences
- `backend/app/routers/processing.py` - 1 occurrence
- `backend/app/routers/llm_usage.py` - 3 occurrences
- `backend/app/routers/ingestion.py` - 1 occurrence
- `backend/app/services/tasks.py` - 12 occurrences
- `backend/app/services/scheduler.py` - 2 occurrences
- `backend/app/services/storage.py` - 1 occurrence
- `backend/app/services/cost_tracking.py` - 3 occurrences
- `backend/app/services/obsidian/frontmatter.py` - 2 occurrences
- `backend/app/services/obsidian/indexer.py` - 2 occurrences
- `backend/app/services/processing/output/obsidian_generator.py` - 2 occurrences
- `backend/app/services/learning/spaced_rep_service.py` - 1 occurrence
- `backend/app/services/learning/session_service.py` - 1 occurrence
- `backend/app/pipelines/*.py` - Multiple files (web_article, raindrop_sync, voice_transcribe, pdf_processor, github_importer, book_ocr)

All files now import `timezone` from `datetime` and use `datetime.now(timezone.utc)` instead of `datetime.utcnow()` or naive `datetime.now()`.

---

### ✅ TD-010: Model factory methods for cross-layer conversions
**Completed**: 2026-01-26

Added factory methods to Pydantic models for converting from SQLAlchemy DB records.
Used `from __future__ import annotations` for cleaner return type hints.

**`backend/app/models/processing.py`**:
- Added `Concept.from_db_record(concept_record)` - converts ConceptRecord to Concept
- Added `Connection.from_db_record(connection_record)` - converts ConnectionRecord to Connection
- Added `FollowupTask.from_db_record(followup_record)` - converts FollowupRecord to FollowupTask
- Added `MasteryQuestion.from_db_record(question_record)` - converts QuestionRecord to MasteryQuestion

**`backend/app/models/content.py`**:
- Added `Annotation.from_db_record(annotation_record)` - converts DB Annotation to Pydantic Annotation

**`backend/app/models/learning.py`**:
- Added `CardResponse.from_db_record(card)` - converts SpacedRepCard to CardResponse
- Added `ExerciseResponse.from_db_record(exercise)` - converts Exercise to ExerciseResponse
- Added `SessionSummary.from_db_record(session)` - converts PracticeSession to SessionSummary

**`backend/app/models/assistant.py`**:
- Added `MessageInfo.from_db_record(message)` - converts AssistantMessage to MessageInfo
- Added `ConversationSummary.from_db_record(conversation)` - converts AssistantConversation to ConversationSummary
- Added `ConversationDetail.from_db_record(conversation)` - converts AssistantConversation to ConversationDetail

**Pre-existing factory methods** (already implemented):
- `UnifiedContent.from_db_content()` in `app/models/content.py`
- `ProcessingRun.from_processing_result()` in `app/db/models_processing.py`

All files now use `from __future__ import annotations` and `TYPE_CHECKING` imports for clean forward references.

---

## Notes

- When addressing tech debt, update this document and move items to "Completed"
- Include PR/commit references when closing items
- P0 items must be resolved before open-source announcement
- Total items: 37 (5 P0, 13 P1, 17 P2, 2 P3) — 7 completed
