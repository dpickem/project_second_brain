# Technical Debt Tracker

This document tracks known technical debt items and improvements for open-source release readiness.

## Table of Contents

- [Priority Levels](#priority-levels)
- [Open-Source Release Blockers](#open-source-release-blockers)
  - ✅ ~~[TD-001: Missing LICENSE file](#td-001-missing-license-file)~~
  - ✅ ~~[TD-002: Missing CONTRIBUTING.md](#td-002-missing-contributingmd)~~
  - ⏭️ ~~[TD-003: Missing CODE_OF_CONDUCT.md](#td-003-missing-code_of_conductmd)~~ (won't do)
  - ✅ ~~[TD-004: CORS wildcard allows all origins](#td-004-cors-wildcard-allows-all-origins)~~
  - ✅ ~~[TD-005: Missing production deployment documentation](#td-005-missing-production-deployment-documentation)~~
  - ✅ ~~[TD-006: README updates for open-source](#td-006-readme-updates-for-open-source)~~
  - ✅ ~~[TD-007: Add CHANGELOG.md and SECURITY.md](#td-007-add-changelogmd-and-securitymd)~~
- [Backend Tech Debt](#backend-tech-debt)
  - ✅ ~~[TD-008: Use TYPE_CHECKING for type annotation imports](#td-008-use-type_checking-for-type-annotation-imports)~~
  - ✅ ~~[TD-009: Complete LLM/OCR/VLM usage tracking](#td-009-complete-llmocrvlm-usage-tracking)~~
  - ✅ ~~[TD-010: Model factory methods for cross-layer conversions](#td-010-model-factory-methods-for-cross-layer-conversions)~~
  - ✅ ~~[TD-011: Clean up imports and move to top of files](#td-011-clean-up-imports-and-move-to-top-of-files)~~
  - ✅ ~~[TD-012: Robust deduplication and cleanup on reprocessing](#td-012-robust-deduplication-and-cleanup-on-reprocessing)~~
  - ✅ ~~[TD-013: Eliminate magic numbers](#td-013-eliminate-magic-numbers)~~
  - ✅ ~~[TD-014: N+1 query in mastery_service.py](#td-014-n1-query-in-mastery_servicepy)~~
  - ✅ ~~[TD-015: Inconsistent datetime usage](#td-015-inconsistent-datetime-usage)~~
  - ✅ ~~[TD-016: Incomplete TODO implementations](#td-016-incomplete-todo-implementations)~~
  - ✅ ~~[TD-017: Large service files need splitting](#td-017-large-service-files-need-splitting)~~
  - ✅ ~~[TD-018: Inconsistent error handling patterns](#td-018-inconsistent-error-handling-patterns)~~
  - ✅ ~~[TD-019: Missing type hints](#td-019-missing-type-hints)~~
  - ✅ ~~[TD-020: Hardcoded upload directory](#td-020-hardcoded-upload-directory)~~
  - ✅ ~~[TD-021: Review and clean up dependencies](#td-021-review-and-clean-up-dependencies)~~
  - ✅ ~~[TD-038: Concept deduplication not working](#td-038-concept-deduplication-not-working)~~
  - ✅ ~~[TD-039: Exercises not synced to Obsidian vault](#td-039-exercises-not-synced-to-obsidian-vault)~~
  - ✅ ~~[TD-040: PDF images not integrated into summaries](#td-040-pdf-images-not-integrated-into-summaries)~~
- [Frontend Tech Debt](#frontend-tech-debt)
  - ✅ ~~[TD-022: Remove console.log statements](#td-022-remove-consolelog-statements)~~
  - ✅ ~~[TD-023: Hardcoded URLs throughout frontend](#td-023-hardcoded-urls-throughout-frontend)~~
  - ✅ ~~[TD-024: Missing prop validation](#td-024-missing-prop-validation)~~
  - ✅ ~~[TD-025: Missing error boundaries](#td-025-missing-error-boundaries)~~
  - ✅ ~~[TD-026: Accessibility issues](#td-026-accessibility-issues)~~
  - ✅ ~~[TD-027: Performance - missing memoization](#td-027-performance---missing-memoization)~~
  - ✅ ~~[TD-028: Magic numbers in frontend](#td-028-magic-numbers-in-frontend)~~
  - ✅ ~~[TD-029: Inconsistent state management patterns](#td-029-inconsistent-state-management-patterns)~~
- [Tests & Scripts](#tests--scripts)
  - ✅ ~~[TD-030: Skipped tests due to missing dependencies](#td-030-skipped-tests-due-to-missing-dependencies)~~
  - ✅ ~~[TD-031: Hardcoded path in run_processing.py](#td-031-hardcoded-path-in-run_processingpy)~~
  - ✅ ~~[TD-032: Prototype code should be moved or removed](#td-032-prototype-code-should-be-moved-or-removed)~~
  - ✅ ~~[TD-033: Test verifies intentional NotImplementedError](#td-033-test-verifies-intentional-notimplementederror)~~
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

### ✅ TD-001: Missing LICENSE file
**Priority**: P0  
**Status**: ✅ Completed  
**Area**: Repository root

**Description**: No LICENSE file exists. Required for open-source release.

**Action**: Add a LICENSE file (MIT, Apache 2.0, etc.) to the repository root.

---

### ✅ TD-002: Missing CONTRIBUTING.md
**Priority**: P0  
**Status**: ✅ Completed  
**Area**: Repository root

**Description**: No contribution guidelines exist. Essential for community contributions.

**Required Content**:
- Development setup instructions
- Code style guidelines
- PR process and requirements
- Testing requirements
- Commit message conventions

---

### ⏭️ TD-003: Missing CODE_OF_CONDUCT.md
**Priority**: P0  
**Status**: Won't Do  
**Area**: Repository root

**Description**: No code of conduct exists. Standard for open-source projects.

**Action**: Add Contributor Covenant or similar code of conduct.

**Decision**: Deferred - can be added manually from https://www.contributor-covenant.org/ if needed.

---

### ✅ TD-004: CORS wildcard allows all origins
**Priority**: P0  
**Status**: ✅ Completed  
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

### ✅ TD-005: Missing production deployment documentation
**Priority**: P0  
**Status**: ✅ Completed  
**Area**: Documentation

**Required Documentation**:
- [x] `docs/deployment/production.md` - Production deployment guide
- [x] `docs/deployment/security.md` - Security hardening guide
- [x] SSL/TLS setup instructions
- [x] Reverse proxy (Nginx) configuration examples
- [x] Database backup/restore procedures

---

### ✅ TD-006: README updates for open-source
**Priority**: P1  
**Status**: ✅ Completed  
**Area**: Documentation

**Missing Sections** (all addressed):
- ✅ Security section (links to security.md, vulnerability reporting guidance)
- ✅ Contributing section (reference to CONTRIBUTING.md with quick start)
- ✅ License section (MIT license description)
- ✅ Production deployment overview (links to docs/deployment/)
- ✅ Clone URL made generic (placeholder for username)

---

### ✅ TD-007: Add CHANGELOG.md and SECURITY.md
**Priority**: P1  
**Status**: ✅ Completed  
**Area**: Repository root

**Files Created**:
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

### ✅ TD-012: Robust deduplication and cleanup on reprocessing
**Priority**: P1  
**Status**: ✅ Completed  
**Area**: Data integrity

**Description**: Ensure deduplication works robustly throughout the system. When content is reprocessed, properly clean up all old entries.

**Implemented Cleanup**:
1. **PostgreSQL**: Deletes old `ProcessingRun` records (cascade deletes related `FollowupRecord`, `QuestionRecord`, `ConceptRecord`, `ConnectionRecord`)
2. **Neo4j**: Deletes outgoing relationships from content node (preserves node for update)
3. **Obsidian**: Main notes updated in-place or deleted if title changes (handled in `obsidian_generator.py`). Concept notes intentionally preserved across sources.
4. **Cards**: Optionally deletable (disabled by default to preserve user's spaced rep history)

**Implementation**:
- New cleanup service: `app/services/processing/cleanup.py`
- Integrated into both processing paths:
  - API background task: `_run_processing()` in `routers/processing.py`
  - Celery task: `_run_llm_processing_impl()` in `services/tasks.py`
- Obsidian handled in `obsidian_generator.py` via `get_path_for_update()` and old file deletion

**Acceptance Criteria** (all met):
- ✅ Reprocessing the same content results in exactly one ProcessingRun per processing
- ✅ No orphaned records in PostgreSQL after reprocessing (cascade deletes)
- ✅ No orphaned Neo4j relationships after reprocessing
- ✅ No duplicate Obsidian notes after reprocessing (update in place or delete old)

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

### ✅ TD-014: N+1 query in mastery_service.py
**Priority**: P1  
**Status**: ✅ Completed  
**Area**: Performance

**Location**: `backend/app/services/learning/mastery_service.py:409-431`

**Issue**: Loop executed a separate query per topic when counting cards.

**Fix**: Replaced N+1 loop with a single batched query using PostgreSQL's `unnest` function
to expand the tags array, then GROUP BY to count cards per topic in one database round-trip.

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

### ✅ TD-016: Incomplete TODO implementations
**Priority**: P2  
**Status**: ✅ Completed  
**Area**: Implementation gaps

**TODOs Implemented**:
1. ✅ `cleanup_old_tasks()` in `tasks.py` - Now marks stuck PROCESSING items as FAILED after 6 hours
2. ✅ `check_duplicate()` in `base.py` - Now queries database for matching `raw_file_hash`
3. ✅ Removed `get_default_ocr_model` alias from `vlm_client.py` - Updated `book_ocr.py` to use `get_default_vlm_model`

---

### ✅ ~~TD-017: Large service files need splitting~~
**Priority**: P2  
**Status**: ✅ Completed  
**Area**: Code organization

**Large Files (Before → After)**:
- `backend/app/services/learning/mastery_service.py` - 1909 → 1369 lines (~28% reduction)
- `backend/app/services/assistant/service.py` - 1020 → 834 lines (~18% reduction)
- `backend/app/services/learning/evaluator.py` - 841 → 751 lines (~11% reduction)

**New Modules Created**:
1. `backend/app/services/learning/time_tracking.py` (376 lines) - `TimeTrackingService`
   - Time investment tracking
   - Learning time logging
   - Time aggregation by topic/activity
   - Period grouping (day/week/month)

2. `backend/app/services/learning/streak_tracking.py` (341 lines) - `StreakTrackingService`
   - Practice streak calculations
   - Activity heatmap data
   - Milestone tracking

3. `backend/app/services/assistant/conversation_manager.py` (311 lines) - `ConversationManager`
   - Conversation CRUD operations
   - Message management
   - Separated from core chat/feature logic

4. `backend/app/services/learning/evaluation_prompts.py` (112 lines)
   - LLM prompts for text and code evaluation
   - Separated from evaluator logic

**Pattern Used**: Services delegate to sub-services for specific domains while maintaining existing public APIs.

**Total**: 1140 lines extracted, improving code organization and maintainability.

---

### ✅ TD-018: Inconsistent error handling patterns
**Priority**: P2  
**Status**: ✅ Completed  
**Area**: Code consistency

**Issues** (resolved):
- Most endpoints use `HTTPException` from FastAPI
- Some use custom `ServiceError` exceptions
- `backend/app/routers/assistant.py` uses `@handle_endpoint_errors` decorator
- Other routers don't use this pattern consistently

**Fix Applied**: Standardized error handling across all routers using the `@handle_endpoint_errors` decorator.

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

### ✅ TD-020: Hardcoded upload directory
**Priority**: P2  
**Status**: ✅ Completed  
**Area**: Configuration

**Location**: `backend/app/config/settings.py:168`

**Issue**: `UPLOAD_DIR` was hardcoded to `/tmp/second_brain_uploads`:
- Not cross-platform (Windows uses different temp paths)
- Duplicate definition existed in `pipelines.py` (never used)

**Fix**:
- Changed default to use `tempfile.gettempdir()` for cross-platform compatibility
- Added `UPLOAD_DIR_PATH` property for convenient Path object access
- Removed redundant definition from `pipelines.py`
- Updated `.env.example` documentation

---

### ✅ TD-021: Review and clean up dependencies
**Priority**: P2  
**Status**: ✅ Completed  
**Area**: Dependencies

**Issues identified**:
- `backend/requirements.txt` uses `>=` constraints - consider pinning for production
- `aisuite` (line 47) - unclear if actively used
- Both `pdfplumber` and `pymupdf` included - code primarily uses `pymupdf`

**Resolution**:
- Removed `aisuite` - never imported anywhere in the codebase
- Added production versioning guidance to requirements.txt header
- Clarified pdfplumber is kept for prototypes (used in `prototypes/test_pdfplumber_annotations.py`)
- Updated comments to clarify pymupdf is the production library
- Fixed misleading config comment (`PDF_TEXT_ENGINE` only supports pymupdf)
- Fixed inaccurate docstrings in `pdf_processor.py` that mentioned pdfplumber

---

### ✅ TD-038: Concept deduplication not working
**Priority**: P1  
**Status**: ✅ Completed  
**Area**: Data integrity

**Description**: Concepts were being duplicated badly in the database. For example, "Behavior Cloning (BC)" appeared 10+ times as separate concept entries instead of being deduplicated.

**Root Cause**: Neo4j MERGE was matching by exact name, so "Behavior Cloning (BC)", "Behavior Cloning", and "BC" were all treated as different concepts.

**Fix Implemented**:

1. **New concept deduplication module** (`app/services/processing/concept_dedup.py`):
   - `normalize_concept_name()` - Extracts canonical name and aliases from parentheses
   - `get_canonical_name()` - Returns the base concept name for storage
   - `extract_aliases()` - Extracts aliases like "BC" from "Behavior Cloning (BC)"
   - `deduplicate_concepts()` - Deduplicates within a single extraction

2. **Neo4j changes** (`services/knowledge_graph/queries.py` and `client.py`):
   - MERGE now uses `canonical_name` (lowercase, no aliases) for matching
   - `display_name` stores the preferred display format
   - `aliases` array accumulates all aliases from different sources
   - Constraint updated to enforce uniqueness on `canonical_name`

3. **Extraction stage integration** (`services/processing/stages/extraction.py`):
   - Calls `deduplicate_concepts()` before returning results
   - Handles LLM extracting the same concept multiple times with different names

4. **Batch deduplication helpers** (`services/processing/cleanup.py`):
   - `deduplicate_neo4j_concepts()` - Merges existing duplicate concept nodes
   - `migrate_concepts_to_canonical_names()` - Adds canonical_name to old concepts

**Migration for Existing Data**:
```python
from app.services.processing.cleanup import (
    migrate_concepts_to_canonical_names,
    deduplicate_neo4j_concepts,
)

# First, add canonical_name to existing concepts
await migrate_concepts_to_canonical_names(neo4j_client)

# Then deduplicate (dry_run=True to preview changes)
result = await deduplicate_neo4j_concepts(neo4j_client, dry_run=True)
# result = await deduplicate_neo4j_concepts(neo4j_client)  # Actually merge
```

---

### ✅ TD-039: Exercises not synced to Obsidian vault
**Priority**: P2  
**Status**: ✅ Completed  
**Area**: Data synchronization

**Description**: Exercises exist only in the PostgreSQL database but are not being written as Obsidian notes. This breaks the "single source of truth" philosophy where all learning content should be accessible in the Obsidian vault.

**Current State** (after fix):
- Cards (spaced repetition) → ❓ (stored in DB, not synced to vault)
- Exercises → ✅ Written to Obsidian
- Concepts → ✅ Written to Obsidian
- Main content notes → ✅ Written to Obsidian

**Implementation**:
- [x] Created exercise template (`config/templates/exercise.md.j2`)
- [x] Added `get_exercise_folder()` to VaultManager
- [x] Added `generate_exercise_note()` and `generate_exercise_notes_for_content()` to `obsidian_generator.py`
- [x] Integrated exercise sync into processing pipeline (`pipeline.py`)
- [x] Folder structure: `exercises/by-topic/{topic}/` (e.g., `exercises/by-topic/ml_transformers/`)

---

### ✅ TD-040: PDF images not integrated into summaries
**Priority**: P2  
**Status**: ✅ Completed  
**Area**: Content processing / UX

**Description**: During PDF/book OCR processing, images are extracted but not utilized in the final output. These images (diagrams, figures, charts, etc.) should be:
1. Integrated into the detailed summary at appropriate locations
2. Rendered in Obsidian markdown notes with proper image embeds
3. Displayed in the web UI when viewing content

**Implementation**:

**1. PDF Processor Changes** (`backend/app/pipelines/pdf_processor.py`):
- Changed `include_images` default to `True` (was `False`)
- Added call to `save_extracted_images()` to persist images to vault
- Store image metadata in `UnifiedContent.metadata["extracted_images"]`
- Image paths added to `asset_paths` list

**2. New Image Storage Service** (`backend/app/services/processing/output/image_storage.py`):
- `save_extracted_images()` - Saves base64 images from OCR to vault assets folder
- `delete_content_images()` - Cleanup function for reprocessing
- `ExtractedImage` dataclass with path, page, description, dimensions
- Image optimization: resize to max 1200px, PNG compression
- Storage location: `vault/assets/images/{content_id}/page_N_img_M.png`

**3. Obsidian Integration** (`obsidian_generator.py`, templates):
- Added `figures` and `has_figures` to `TemplateData`
- `_prepare_template_data()` extracts figures from content metadata
- Updated templates with Figures section:
  - `paper.md.j2` - Shows figures with Obsidian wikilink syntax
  - `article.md.j2` - Shows figures when available
  - `book.md.j2` - Shows figures when available

**4. API Endpoints** (`backend/app/routers/vault.py`):
- `GET /api/vault/assets/{asset_path}` - Serve images/assets from vault
- `GET /api/vault/content/{content_id}/images` - List images for a content item

**Template Format**:
```markdown
## Figures

### Figure 1 (Page 3)
![[assets/images/abc123/page_3_img_0.png]]
*Description from OCR annotation*
```

**Storage Structure**:
```
vault/
└── assets/
    └── images/
        └── {content_id}/
            ├── page_1_img_0.png
            ├── page_1_img_1.png
            └── page_3_img_0.png
```

**Naming Convention**: `page_{N}_img_{M}.png` where N is 1-indexed page number and M is 0-indexed image index on that page.

---

## Frontend Tech Debt

### ✅ TD-022: Remove console.log statements
**Priority**: P1  
**Status**: ✅ Completed  
**Area**: Production code quality

**Issue**: 76+ console.log/console.warn statements in production code.

**Key Locations** (all fixed):
- `frontend/src/pages/PracticeSession.jsx` - Removed debug logs
- `frontend/src/components/dashboard/StreakCalendar.jsx` - Removed debug logs
- `frontend/src/api/client.js` - Already gated behind `import.meta.env.DEV`
![1769542452093](image/tech_debt/1769542452093.png)- `frontend/capture/src/` - Removed extensive logging from capture components
- `frontend/capture/public/sw.js` - Removed service worker logging

**Fix Applied**: Removed all console.log/warn/error statements from production code. Remaining statements are in:
- Test files (e2e specs) - appropriate for test output
- Build scripts - appropriate for build feedback
- JSDoc documentation examples - not actual code execution
- DEV-gated statements (`client.js` response interceptor)

---

### ✅ TD-023: Hardcoded URLs throughout frontend
**Priority**: P1  
**Status**: ✅ Completed  
**Area**: Configuration

**Locations** (all fixed):
- `frontend/src/api/client.js` - Now exports `API_URL` for shared use
- `frontend/src/api/capture.js` - Now imports `API_URL` from client.js
- `frontend/src/api/typed-client.js` - Now imports `API_URL` from client.js
- `frontend/capture/src/api/capture.js` - Uses constants for defaults, smart fallback for mobile
- `frontend/capture/index.html` - Removed hardcoded preconnect
- `frontend/capture/vite.config.js` - Now uses `process.env.VITE_API_URL` for proxy target
- `frontend/scripts/generate-api-types.js` - Already used `process.env.BACKEND_URL` (no change needed)

**Fix Applied**: 
- Centralized `API_URL` export in `client.js` as single source of truth
- Other modules now import from `client.js` instead of redefining
- PWA uses named constants with intelligent fallback for mobile LAN access
- Created `frontend/.env.example` documenting `VITE_API_URL` and `VITE_CAPTURE_API_KEY`

---

### ✅ TD-024: Missing prop validation
**Priority**: P2  
**Status**: ✅ Completed  
**Area**: Type safety

**Issue**: No PropTypes or TypeScript. `eslint.config.js:37` had `'react/prop-types': 'off'`.

**Affected Components**:
- `frontend/src/App.jsx` - `NavItem` and `AnimatedPage` components
- `frontend/src/pages/Dashboard.jsx` - `QuickLink` component
- `frontend/src/components/dashboard/QuickCapture.jsx` - `QuickCapture` and `InlineCapture` components
- `frontend/src/components/common/Input.jsx` - `Input`, `Textarea`, `SearchInput`, `Select`, `Checkbox` components

**Fix Applied**: Added PropTypes to all affected components and enabled `react/prop-types: 'warn'` in ESLint.

---

### ✅ TD-025: Missing error boundaries
**Priority**: P1  
**Status**: ✅ Completed  
**Area**: Error handling

**Issue**: No `ErrorBoundary` component exists. React errors will crash the entire app.

**Fix**: Implemented error boundaries at route/page level.

---

### ✅ TD-026: Accessibility issues
**Priority**: P2  
**Status**: ✅ Completed  
**Area**: Accessibility

**Fixed aria labels**:
- `frontend/src/components/common/Input.jsx` - Password toggle button now has `aria-label`, `aria-pressed`, and focus ring
- `frontend/src/components/common/Input.jsx` - SearchInput clear button now has `aria-label` and focus ring
- `frontend/src/pages/Assistant.jsx` - Quick prompt buttons now have `aria-label` and focus ring, group has `role="group"`
- `frontend/src/pages/Knowledge.jsx` - Added accessibility to folder tree, note selection, view toggles, section visibility controls

**Other fixes**:
- Added visible focus indicators (`focus:ring-2`) to interactive elements
- Modal uses Headless UI Dialog which provides built-in focus trap
- Added `aria-expanded`, `aria-controls`, `aria-pressed`, `aria-selected`, `aria-current` attributes where appropriate
- Added `role="tablist"`, `role="tab"`, `role="tabpanel"`, `role="listbox"`, `role="option"` for proper semantics

---

### ✅ TD-027: Performance - missing memoization
**Priority**: P2  
**Status**: ✅ Completed  
**Area**: Performance

**Issues** (all resolved):
- `frontend/src/pages/Dashboard.jsx` - `QuickLink` wrapped with `React.memo`
- `frontend/src/pages/Assistant.jsx` - `quickPrompts` moved to module-level constant, handlers memoized with `useCallback`
- `frontend/src/components/dashboard/QuickCapture.jsx` - All callbacks memoized with `useCallback`

**Fix Applied**: Added `React.memo`, and `useCallback` where appropriate to prevent unnecessary re-renders.

---

### ✅ TD-028: Magic numbers in frontend
**Priority**: P2  
**Status**: ✅ Completed  
**Area**: Code quality

**Locations** (all resolved):
- `frontend/src/pages/Dashboard.jsx` - `dailyGoal` → `DEFAULT_DAILY_GOAL`
- `frontend/src/pages/Knowledge.jsx` - `pageSize` → `VAULT_PAGE_SIZE`
- `frontend/src/components/GraphViewer/GraphViewer.jsx` - dimensions → `DEFAULT_GRAPH_WIDTH`, `DEFAULT_GRAPH_HEIGHT`
- `frontend/src/components/GraphViewer/GraphViewer.jsx` - force params → `GRAPH_CHARGE_STRENGTH`, `GRAPH_CHARGE_DISTANCE_MAX`, `GRAPH_LINK_DISTANCE`
- `frontend/src/pages/KnowledgeGraph.jsx` - `limit` → `GRAPH_NODE_LIMIT`
- `frontend/src/components/common/Tooltip.jsx` - `z-[9999]` → `Z_INDEX.TOOLTIP`

**Fix Applied**: Created `frontend/src/constants/ui.js` with named constants and z-index scale.

---

### ✅ TD-029: Inconsistent state management patterns
**Priority**: P3  
**Status**: ✅ Completed  
**Area**: Architecture

**Current State**:
- Zustand stores in `frontend/src/stores/`
- React Query for server state
- Local `useState` throughout
- No clear pattern documentation

**Fix**: Document state management guidelines AND apply them consistently.

**Resolution**:
1. Created `docs/design_docs/11_frontend_state_management.md` with comprehensive guidelines
2. Fixed `Knowledge.jsx` to use `useSettingsStore` instead of raw localStorage for section visibility

**Note**: `Analytics.jsx` uses local `useState` for `timeRange` and `viewMode` - this is acceptable
as these are page-specific UI state that doesn't necessarily need to persist across sessions.

---

## Tests & Scripts

### ✅ TD-030: Skipped tests due to missing dependencies
**Priority**: P1  
**Status**: ✅ Completed  
**Area**: Test coverage

**Previously Skipped Tests** (now all run):
- `backend/tests/integration/test_vault_sync.py` - Was skipping if `NEO4J_URI` not set
- `backend/tests/integration/test_pipelines.py` - Was skipping if `SAMPLE_PDF` not found
- `backend/tests/unit/test_code_sandbox.py` - Was skipping if Docker unavailable
- `backend/tests/unit/test_openapi_contract.py` - Was skipping if snapshot missing

**Resolution**: 
- **test_vault_sync.py**: Removed unnecessary pytestmark skip - tests already mock Neo4j client
- **test_code_sandbox.py**: Fixed broken skipif syntax (was using `pytest.importorskip` incorrectly)
- **test_openapi_contract.py**: Generated `tests/snapshots/openapi.json` snapshot file
- **test_pipelines.py**: Sample PDFs already exist in `test_data/`, paths resolve correctly
- Added comprehensive "Optional Test Dependencies" section to `TESTING.md`
- Docker integration tests still require Docker, but skipif now works correctly

---

### ✅ TD-031: Hardcoded path in run_processing.py
**Priority**: P1  
**Status**: ✅ Completed  
**Area**: Scripts

**Location**: `scripts/run_processing.py:87-89`

**Previous Code**:
```python
os.environ["OBSIDIAN_VAULT_PATH"] = os.path.expanduser(
    "~/workspace/obsidian/second_brain/obsidian"
)
```

**Resolution**:
- Changed to use environment variable with sensible default (`~/obsidian_vault`)
- Only overrides if not set or if set to Docker's `/vault` path
- Prints informative message about using default path
- Updated docstring to document the environment variable

---

### ✅ TD-032: Prototype code should be moved or removed
**Priority**: P1  
**Status**: ✅ Completed  
**Area**: Code cleanup

**Resolution**:
- Moved `test_mistral_ocr.py` → `scripts/examples/mistral_ocr_example.py`
- Moved `test_pdfplumber_annotations.py` → `scripts/examples/pdfplumber_annotations_example.py`
- Moved `test_pymupdf_annotations.py` → `scripts/examples/pymupdf_annotations_example.py`
- Moved `sample_mistral7b.pdf` → `test_data/`
- Removed `prototypes/ocr_results/` (generated test outputs)
- Removed empty `prototypes/` directory
- Updated path references in scripts to work from new location
- Created `scripts/examples/README.md` documenting all example scripts

---

### ✅ TD-033: Test verifies intentional NotImplementedError
**Priority**: P2  
**Status**: ✅ Completed (no code change needed)  
**Area**: Tests

**Location**: `backend/tests/integration/test_pipelines.py:1001-1010`

**Original Issue**: Test expects `NotImplementedError` - appeared to indicate incomplete implementation.

**Resolution**: This is **intentional behavior**, not a bug. The `RaindropSync.process()` method deliberately raises `NotImplementedError` because:
1. `RaindropSync` is designed for batch sync operations via `sync_collection()`
2. It is NOT meant to be used through `PipelineRegistry` for single-item processing
3. For single-article processing, `WebArticlePipeline` should be used instead

The test correctly verifies this design constraint. Updated title from "Incomplete test implementation" to "Test verifies intentional NotImplementedError" to clarify this is expected behavior.

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
- ✅ ~~TD-001: Missing LICENSE file~~
- ✅ ~~TD-002: Missing CONTRIBUTING.md~~
- ⏭️ ~~TD-003: Missing CODE_OF_CONDUCT.md~~ (won't do)
- ✅ ~~TD-004: CORS wildcard allows all origins~~
- ✅ ~~TD-005: Missing production deployment documentation~~

### P1 - High (Should address for clean release)
- ✅ ~~TD-006: README updates for open-source~~
- ✅ ~~TD-007: Add CHANGELOG.md and SECURITY.md~~
- ✅ ~~TD-009: Complete LLM/OCR/VLM usage tracking~~
- ✅ ~~TD-012: Robust deduplication and cleanup on reprocessing~~
- ✅ ~~TD-014: N+1 query in mastery_service.py~~
- ✅ ~~TD-015: Inconsistent datetime usage~~
- ✅ ~~TD-022: Remove console.log statements~~
- ✅ ~~TD-023: Hardcoded URLs throughout frontend~~
- ✅ ~~TD-025: Missing error boundaries~~
- ✅ ~~TD-030: Skipped tests due to missing dependencies~~
- ✅ ~~TD-031: Hardcoded path in run_processing.py~~
- ✅ ~~TD-032: Prototype code should be moved or removed~~
- [ ] TD-034: Docker compose production configuration
- ✅ ~~TD-038: Concept deduplication not working~~

### P2 - Medium (Address when touching related code)
- ✅ ~~TD-008: Use TYPE_CHECKING for type annotation imports~~
- ✅ ~~TD-010: Model factory methods for cross-layer conversions~~
- ✅ ~~TD-011: Clean up imports and move to top of files~~
- ✅ ~~TD-013: Eliminate magic numbers~~
- ✅ ~~TD-016: Incomplete TODO implementations~~
- ✅ ~~TD-017: Large service files need splitting~~
- ✅ ~~TD-018: Inconsistent error handling patterns~~
- ✅ ~~TD-019: Missing type hints~~
- ✅ ~~TD-020: Hardcoded upload directory~~
- ✅ ~~TD-021: Review and clean up dependencies~~
- ✅ ~~TD-024: Missing prop validation~~
- ✅ ~~TD-026: Accessibility issues~~
- ✅ ~~TD-027: Performance - missing memoization~~
- ✅ ~~TD-028: Magic numbers in frontend~~
- ✅ ~~TD-033: Test verifies intentional NotImplementedError~~
- [ ] TD-035: Environment variable validation
- [ ] TD-037: Data directory uses tilde expansion
- ✅ ~~TD-039: Exercises not synced to Obsidian vault~~
- ✅ ~~TD-040: PDF images not integrated into summaries~~

### P3 - Low (Nice to have)
- ✅ ~~TD-029: Inconsistent state management patterns~~
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

### ✅ TD-014: N+1 query in mastery_service.py
**Completed**: 2026-01-26

Fixed N+1 query performance issue in `get_enhanced_topic_states()` method.

**Before**: Loop executed separate query for each topic (N+1 pattern):
```python
for topic_path in topic_paths:
    card_count_query = select(func.count(SpacedRepCard.id)).where(...)
    result = await self.db.execute(card_count_query)
```

**After**: Single batched query using PostgreSQL `unnest` + GROUP BY:
```python
unnested_tags = select(
    SpacedRepCard.id.label("card_id"),
    func.unnest(SpacedRepCard.tags).label("topic"),
).subquery()

card_count_query = select(
    unnested_tags.c.topic,
    func.count(distinct(unnested_tags.c.card_id)).label("card_count"),
).where(unnested_tags.c.topic.in_(topic_paths)).group_by(unnested_tags.c.topic)
```

This reduces database round-trips from O(n) to O(1) where n is the number of topics.

---

### ✅ TD-012: Robust deduplication and cleanup on reprocessing
**Completed**: 2026-01-26

Created cleanup service for handling reprocessing deduplication.

**New file**: `backend/app/services/processing/cleanup.py`

Key functions:
- `cleanup_processing_runs()` - Deletes old ProcessingRun records with cascade
- `cleanup_neo4j_relationships()` - Removes outgoing relationships from content node
- `cleanup_spaced_rep_cards()` - Optionally deletes cards (disabled by default)
- `cleanup_before_reprocessing()` - Main orchestrator called before processing

**Integration points**:
- `backend/app/routers/processing.py:_run_processing()` - API background task
- `backend/app/services/tasks.py:_run_llm_processing_impl()` - Celery task

**Behavior**:
- Cleanup runs automatically before each processing pipeline execution
- PostgreSQL cascade deletes handle FollowupRecord, QuestionRecord, ConceptRecord, ConnectionRecord
- Neo4j relationships are cleared so new ones can be created
- Spaced rep cards preserved by default (user has review history)
- Obsidian notes: Main content notes updated in-place or deleted if title changes
  (handled in `obsidian_generator.py`, not cleanup service)
- Concept notes intentionally preserved across sources (multiple content can reference same concept)

---

### ✅ TD-016: Incomplete TODO implementations
**Completed**: 2026-01-26

Implemented three incomplete TODO items:

**1. `cleanup_old_tasks()` in `backend/app/services/tasks.py`**:
- Finds content stuck in PROCESSING status for >6 hours
- Marks them as FAILED to prevent eternal stuck state
- Redis cleanup handled automatically by Celery (result_expires=86400)

**2. `check_duplicate()` in `backend/app/pipelines/base.py`**:
- Now queries database for existing content with matching `raw_file_hash`
- Returns existing UnifiedContent if found, enabling duplicate skip
- Best-effort: logs warning but doesn't fail on errors

**3. Removed backwards compatibility alias in `vlm_client.py`**:
- Removed `get_default_ocr_model = get_default_vlm_model` alias
- Updated `book_ocr.py` to import `get_default_vlm_model` directly
- Updated `__init__.py` exports

---

### ✅ TD-017: Large service files need splitting
**Completed**: 2026-01-26

Split large service files into focused sub-modules:

**1. `mastery_service.py` (1909 → 1369 lines, ~28% reduction)**:
- Created `time_tracking.py` - `TimeTrackingService` (376 lines)
- Created `streak_tracking.py` - `StreakTrackingService` (341 lines)

**2. `assistant/service.py` (1020 → 834 lines, ~18% reduction)**:
- Created `conversation_manager.py` - `ConversationManager` (311 lines)

**3. `evaluator.py` (841 → 751 lines, ~11% reduction)**:
- Created `evaluation_prompts.py` - LLM prompts (112 lines)

**Pattern**: Parent services delegate to sub-services while maintaining existing public APIs.
Total lines extracted: 1140

---

### ✅ TD-020: Hardcoded upload directory
**Completed**: 2026-01-26

Made upload directory configurable with cross-platform default.

**Changes**:

**`backend/app/config/settings.py`**:
- Changed `UPLOAD_DIR` default from hardcoded `/tmp/second_brain_uploads` to `tempfile.gettempdir() / "second_brain_uploads"`
- Added `UPLOAD_DIR_PATH` property for convenient Path object access
- Uses Python's `tempfile` module for cross-platform temp directory detection

**`backend/app/config/pipelines.py`**:
- Removed redundant `UPLOAD_DIR` definition (was never used, storage.py imports from settings.py)

**`.env.example`**:
- Updated documentation to explain default behavior
- Changed example to commented-out override instead of hardcoded value

The upload directory is still fully configurable via the `UPLOAD_DIR` environment variable for users who need a specific location.

---

### ✅ TD-021: Review and clean up dependencies
**Completed**: 2026-01-26

Reviewed and cleaned up `backend/requirements.txt`.

**Changes**:

**Removed**:
- `aisuite` - Never imported anywhere in the codebase (searched all .py files)

**Clarified**:
- Added version strategy header explaining `>=` for dev, lock file for production
- Reordered pymupdf before pdfplumber (pymupdf is the production library)
- Updated comments: pymupdf is used by `pdf_utils.py`, pdfplumber is for prototypes

**Fixed misleading documentation**:
- `backend/app/config/pipelines.py`: Updated `PDF_TEXT_ENGINE` comment to note only pymupdf is implemented
- `backend/app/pipelines/pdf_processor.py`: Fixed docstrings that incorrectly mentioned pdfplumber

**Decision on pdfplumber**:
Kept pdfplumber as it's used in `prototypes/test_pdfplumber_annotations.py`. Prototype cleanup is tracked separately in TD-032.

---

### ✅ TD-001: Missing LICENSE file
**Completed**: 2026-01-26

Added MIT License to repository root.

**License chosen**: MIT License - the most permissive widely-recognized open source license. Allows:
- Commercial use
- Modification
- Distribution
- Private use

With only one requirement: include license and copyright notice in copies.

**File created**: `LICENSE` in repository root

---

### ✅ TD-002: Missing CONTRIBUTING.md
**Completed**: 2026-01-26

Added comprehensive contribution guidelines derived from the existing project setup.

**Contents**:
- Development setup instructions (prerequisites, setup script, Docker services)
- Development workflow (branching strategy, making changes)
- Commit message convention (Conventional Commits format)
- Code style guidelines:
  - Python: type hints, import organization, naming conventions, constants
  - JavaScript/React: ESLint rules, Prettier formatting, component structure
- Testing requirements (pytest for backend, Vitest/Playwright for frontend)
- Pull request process
- Issue reporting guidelines

**File created**: `CONTRIBUTING.md` in repository root

---

### ✅ TD-004: CORS wildcard allows all origins
**Completed**: 2026-01-26

Made CORS origins configurable via environment variable while keeping permissive defaults for development.

**Changes**:
- Added `CORS_ORIGINS` setting to `backend/app/config/settings.py`
  - Default: `"*"` (allows all origins for development)
  - Accepts comma-separated list of origins for production
- Added `CORS_ORIGINS_LIST` property to parse the setting
- Updated `backend/app/main.py` to use `settings.CORS_ORIGINS_LIST`
- Documented in `.env.example`

**Configuration**:
```bash
# Development (default)
CORS_ORIGINS=*

# Production
CORS_ORIGINS=https://yourdomain.com,https://app.yourdomain.com
```

---

### ✅ TD-005: Missing production deployment documentation
**Completed**: 2026-01-27

Created comprehensive production deployment documentation.

**Files created**:

**`docs/deployment/production.md`** - Production deployment guide covering:
- Server setup and prerequisites
- Docker production configuration with `docker-compose.prod.yml` override
- SSL/TLS setup with Let's Encrypt and Certbot
- Nginx reverse proxy configuration (rate limiting, security headers, upstream proxying)
- Environment configuration for production
- Database backup and restore procedures (PostgreSQL, Neo4j, Obsidian vault)
- Monitoring and health checks
- Maintenance procedures (updates, log viewing, cleanup)
- Troubleshooting common issues

**`docs/deployment/security.md`** - Security hardening guide covering:
- Pre-production security checklist
- Network security (firewall, fail2ban, Docker network isolation)
- Authentication and authorization
- Secrets management and rotation schedules
- Database security (PostgreSQL, Redis, Neo4j)
- Container security (non-root execution, resource limits, image scanning)
- API security (rate limiting, input validation, CORS, security headers)
- SSL/TLS best practices (modern ciphers, HSTS, testing)
- Monitoring and auditing
- Incident response procedures

---

### ✅ TD-018: Inconsistent error handling patterns
**Completed**: 2026-01-27

Standardized error handling across all routers using a shared decorator pattern.

**Changes**:

**Shared Error Handling Decorator** (`backend/app/middleware/error_handling.py`):
- Moved `handle_endpoint_errors` decorator from `assistant.py` to shared middleware module
- Added imports: `functools`, `Callable`, `Coroutine`, `Any`, `TypeVar`
- Decorator catches exceptions and converts to appropriate HTTPException:
  - `HTTPException` → re-raised as-is
  - `ValueError` → 404 (typically not-found scenarios)
  - Other exceptions → 500 with logged error

**Routers Updated**:

| Router | Endpoints Updated |
|--------|------------------|
| `assistant.py` | 12 endpoints (removed local decorator definition) |
| `analytics.py` | 10 endpoints |
| `review.py` | 10 endpoints |
| `practice.py` | 8 endpoints |
| `knowledge.py` | 9 endpoints |
| `llm_usage.py` | 5 endpoints |

**Total**: 54 endpoints now use consistent `@handle_endpoint_errors` decorator.

**Benefits**:
- Consistent error response format across all endpoints
- Centralized logging of errors with operation context
- Reduced boilerplate (removed ~200 lines of repetitive try/except blocks)
- Easier to maintain and enhance error handling logic

---

### ✅ TD-006: README updates for open-source
**Completed**: 2026-01-27

Updated README.md with all missing sections for open-source release readiness.

**Changes**:

**Table of Contents**:
- Added links to new sections: Production Deployment, Contributing, Security, License

**Clone URL**:
- Changed from user-specific `github.com/dpickem/dpickem_project_second_brain` to generic `github.com/<your-username>/second-brain`

**New Sections Added**:

**🚢 Production Deployment**:
- Links to `docs/deployment/production.md` and `docs/deployment/security.md`
- Key production steps checklist
- Quick environment configuration example

**🤝 Contributing**:
- References `CONTRIBUTING.md` for full details
- Quick start commands for contributors

**🔒 Security**:
- Links to security hardening guide
- Vulnerability reporting guidance
- Summary of security features

**📄 License**:
- MIT License description
- Links to LICENSE file
- Summary of permissions

---

### ✅ TD-007: Add CHANGELOG.md and SECURITY.md
**Completed**: 2026-01-27

Created all required files for open-source release readiness.

**Files created**:

**`CHANGELOG.md`**:
- Uses Keep a Changelog format with Semantic Versioning
- Documents v0.1.0 initial release with all major features
- Includes [Unreleased] section for ongoing development
- Categories: Added, Changed, Fixed, Security, Technical

**`SECURITY.md`**:
- Vulnerability reporting instructions (private disclosure)
- Response timeline expectations (48h acknowledgment, 7d assessment, 30d resolution)
- Security best practices for deployment
- Overview of built-in security features
- Known security considerations (local-first design, LLM data handling)

**`.github/ISSUE_TEMPLATE.md`**:
- Supports Bug Reports, Feature Requests, Documentation Issues, Questions
- Structured sections for reproduction steps, environment details, logs
- Checklist for completeness

**`.github/PULL_REQUEST_TEMPLATE.md`**:
- Summary and related issues sections
- Type of change checkboxes
- Testing checklist (unit, integration, frontend, E2E, manual)
- Documentation and code quality checklist

---

### ✅ TD-022: Remove console.log statements
**Completed**: 2026-01-27

Removed all production console.log/warn/error statements from frontend code.

**Files updated**:

**Main app (`frontend/src/`)**:
- `pages/PracticeSession.jsx` - Removed session end debug logs
- `components/dashboard/StreakCalendar.jsx` - Removed calendar mapping debug logs
- `hooks/useLocalStorage.js` - Removed localStorage error warnings
- `api/client.js` - Already properly gated behind `import.meta.env.DEV`

**Mobile capture PWA (`frontend/capture/`)**:
- `src/api/capture.js` - Removed sync progress logs and debug statements
- `src/hooks/useMediaRecorder.js` - Removed extensive MediaRecorder debug logs
- `src/main.jsx` - Removed PWA service worker registration logs
- `src/components/TextCapture.jsx` - Removed capture error logs
- `src/components/PhotoCapture.jsx` - Removed capture error logs
- `src/components/UrlCapture.jsx` - Removed capture error logs
- `src/components/VoiceCapture.jsx` - Removed recording and capture logs
- `src/components/PdfCapture.jsx` - Removed capture error logs
- `src/components/RecentCaptures.jsx` - Removed clear error logs
- `src/hooks/usePendingCaptures.js` - Removed IndexedDB error logs
- `src/pages/MobileCapture.jsx` - Removed sync progress logs
- `src/pages/ShareTarget.jsx` - Removed share handling error logs
- `public/sw.js` - Removed service worker debug logs (added DEBUG constant)

**Preserved (appropriate locations)**:
- Test files (`e2e/screenshots.spec.js`) - Test output
- Build scripts (`scripts/generate-api-types.js`) - Build feedback
- JSDoc examples in API documentation - Not actual code execution
- DEV-gated logs (`client.js` response interceptor) - Only in development

---

### ✅ TD-023: Hardcoded URLs throughout frontend
**Completed**: 2026-01-27

Centralized API URL configuration across the frontend codebase.

**Changes**:

**`frontend/src/api/client.js`**:
- Exported `API_URL` constant as single source of truth
- Added `DEFAULT_API_URL` constant for clarity

**`frontend/src/api/capture.js`**:
- Now imports `API_URL` from `client.js`
- Removed 3 redundant inline `API_URL` definitions

**`frontend/src/api/typed-client.js`**:
- Now imports `API_URL` from `client.js`
- Removed redundant `API_URL` definition

**`frontend/capture/src/api/capture.js`**:
- Added named constants (`DEFAULT_API_URL`, `DEFAULT_BACKEND_PORT`)
- Enhanced `getApiUrl()` JSDoc documentation
- Smart fallback preserved for mobile LAN access

**`frontend/capture/index.html`**:
- Removed hardcoded `<link rel="preconnect" href="http://localhost:8000">`

**`frontend/capture/vite.config.js`**:
- Proxy target now uses `process.env.VITE_API_URL || 'http://localhost:8000'`

**New file: `frontend/.env.example`**:
- Documents `VITE_API_URL` environment variable
- Documents `VITE_CAPTURE_API_KEY` for PWA authentication

**Note**: `frontend/scripts/generate-api-types.js` already used `process.env.BACKEND_URL` - no change needed.

---

### ✅ TD-024: Missing prop validation
**Completed**: 2026-01-27

Added PropTypes validation to all key frontend components and enabled ESLint enforcement.

**Files updated**:

**`frontend/src/App.jsx`**:
- Added `PropTypes` import
- Added `NavItem.propTypes` - validates `to` (string, required), `icon` (node, required), `title` (string, required), `shortcut` (string, optional)
- Added `AnimatedPage.propTypes` - validates `children` (node, required)

**`frontend/src/pages/Dashboard.jsx`**:
- Added `PropTypes` import
- Added `QuickLink.propTypes` - validates `to`, `icon`, `title`, `description` (all strings, required)

**`frontend/src/components/dashboard/QuickCapture.jsx`**:
- Added `PropTypes` import
- Added `QuickCapture.propTypes` - validates `onSuccess` (func), `placeholder` (string), `className` (string)
- Added `InlineCapture.propTypes` - validates `onSuccess` (func), `className` (string)

**`frontend/src/components/common/Input.jsx`**:
- Added `PropTypes` import
- Added `Input.propTypes` - validates label, error, hint, icon, iconPosition, size, type, className, wrapperClassName
- Added `Textarea.propTypes` - validates label, error, hint, size, rows, className, wrapperClassName
- Added `SearchInput.propTypes` - validates placeholder, onClear, value
- Added `Select.propTypes` - validates label, error, hint, size, options (with shape), placeholder, className, wrapperClassName
- Added `Checkbox.propTypes` - validates label, description, error, className

**`frontend/eslint.config.js`**:
- Changed `'react/prop-types': 'off'` to `'react/prop-types': 'warn'`
- Enables lint warnings for components missing PropTypes validation

---

### ✅ TD-025: Missing error boundaries
**Completed**: 2026-01-27

Implemented React error boundaries to catch JavaScript errors and prevent full app crashes.

**Files created**:

**`frontend/src/components/common/ErrorBoundary.jsx`**:
- `ErrorBoundary` - Generic error boundary with customizable fallback (function or element)
- `PageErrorBoundary` - Route-aware boundary that auto-resets on navigation via `resetKey` prop
- `DefaultErrorFallback` - Styled fallback UI with error details (dev only), refresh and retry buttons

**Features**:
- Catches JavaScript errors anywhere in child component tree
- Shows user-friendly fallback UI instead of blank screen
- "Try Again" button to reset and re-render
- "Refresh Page" button as fallback
- Error details shown in development mode only
- Route-aware reset: navigating to a different page clears the error state
- Optional `onError` callback for error logging/reporting

**`frontend/src/components/common/index.js`**:
- Added exports for `ErrorBoundary`, `PageErrorBoundary`, `DefaultErrorFallback`

**`frontend/src/App.jsx`**:
- Wrapped routes with `PageErrorBoundary` using `location.pathname` as `resetKey`
- Errors in any page component are now caught and displayed gracefully

---

### ✅ TD-026: Accessibility issues
**Completed**: 2026-01-27

Added ARIA attributes and focus indicators to improve screen reader support and keyboard navigation.

**Files updated**:

**`frontend/src/components/common/Input.jsx`**:
- Password toggle button: Added `aria-label` (dynamic based on state), `aria-pressed`, `aria-hidden` on icons, visible focus ring
- SearchInput clear button: Added `aria-label`, `aria-hidden` on icon, visible focus ring

**`frontend/src/pages/Assistant.jsx`**:
- Quick prompts container: Added `role="group"` and `aria-label`
- Quick prompt buttons: Added `aria-label`, visible focus ring

**`frontend/src/pages/Knowledge.jsx`**:
- Folder tree: `aria-expanded`, `aria-controls`, `aria-label` on folder buttons, `role="group"` on note lists
- Note buttons: `aria-current` for selected state, focus rings
- View toggle: `role="tablist"`, `role="tab"`, `aria-selected`, `aria-controls`
- Notes panel: `id` for ARIA reference, `role="tabpanel"`
- List view: `role="listbox"`, `role="option"`, `aria-selected`
- Command palette button: `aria-label`
- Section visibility: `aria-pressed`, `aria-label`, `aria-hidden` on icons
- Show All/None buttons: `aria-label`

**`frontend/src/components/common/Modal.jsx`**:
- ConfirmModal buttons: Added `focus-visible:ring` focus indicators

**Accessibility improvements**:
- All interactive elements now have visible focus indicators
- Modal dialogs use Headless UI's built-in focus trap
- Proper ARIA roles communicate UI semantics to assistive technology

### ✅ TD-027: Performance - missing memoization
**Completed**: 2026-01-27

Added React memoization patterns to prevent unnecessary re-renders in frontend components.

**Files updated**:

**`frontend/src/pages/Dashboard.jsx`**:
- Imported `memo` from React
- Wrapped `QuickLink` component with `React.memo` to prevent re-renders when parent state changes

**`frontend/src/pages/Assistant.jsx`**:
- Imported `useCallback` from React
- Moved `quickPrompts` array to module-level constant `QUICK_PROMPTS` (was recreated every render)
- Memoized `handleSend` with `useCallback` (dependencies: `input`, `chatMutation`)
- Memoized `handleKeyDown` with `useCallback` (dependency: `handleSend`)
- Memoized `handleQuickPrompt` with `useCallback` (no dependencies)

**`frontend/src/components/dashboard/QuickCapture.jsx`**:
- Imported `useCallback` from React
- `QuickCapture` component:
  - Memoized `handleSubmit` with `useCallback` (dependencies: `text`, `createCards`, `createExercises`, `captureMutation`)
  - Memoized `handleKeyDown` with `useCallback` (dependency: `handleSubmit`)
- `InlineCapture` component:
  - Memoized `handleChange` with `useCallback` (no dependencies)
  - Memoized `handleFocus` with `useCallback` (no dependencies)
  - Memoized `handleBlur` with `useCallback` (dependency: `text`)
  - Memoized `handleKeyDown` with `useCallback` (dependencies: `text`, `captureMutation`)
  - Memoized `handleCaptureClick` with `useCallback` (dependencies: `text`, `captureMutation`)

**Performance benefits**:
- Reduced unnecessary re-renders of child components
- Stable callback references prevent child component re-renders
- Static data moved outside component lifecycle

---

### ✅ TD-028: Magic numbers in frontend
**Completed**: 2026-01-27

Extracted magic numbers to named constants in a new `frontend/src/constants/ui.js` file.

**New file created**: `frontend/src/constants/ui.js`

**Constants added**:
- `DEFAULT_DAILY_GOAL` (20) - Daily review card goal
- `VAULT_PAGE_SIZE` (200) - Pagination size for vault notes
- `DEFAULT_GRAPH_WIDTH` (800) - Default graph container width
- `DEFAULT_GRAPH_HEIGHT` (600) - Default graph container height
- `GRAPH_NODE_LIMIT` (200) - Maximum nodes to fetch for graph display
- `GRAPH_CHARGE_STRENGTH` (-300) - D3 force charge strength
- `GRAPH_CHARGE_DISTANCE_MAX` (400) - D3 force charge max distance
- `GRAPH_LINK_DISTANCE` (100) - D3 force link distance
- `Z_INDEX` object with layered values (BASE, DROPDOWN, STICKY, MODAL_BACKDROP, MODAL, TOOLTIP)

**Files updated**:
- `frontend/src/constants/index.js` - Added export for `ui.js`
- `frontend/src/pages/Dashboard.jsx` - Uses `DEFAULT_DAILY_GOAL`
- `frontend/src/pages/Knowledge.jsx` - Uses `VAULT_PAGE_SIZE`
- `frontend/src/components/GraphViewer/GraphViewer.jsx` - Uses graph dimension and force constants
- `frontend/src/pages/KnowledgeGraph.jsx` - Uses `GRAPH_NODE_LIMIT`
- `frontend/src/components/common/Tooltip.jsx` - Uses `Z_INDEX.TOOLTIP`

**Benefits**:
- Constants are documented with JSDoc comments
- Single source of truth for configuration values
- Easier to adjust values across the application
- Z-index scale prevents arbitrary stacking conflicts

---

### ✅ TD-029: Inconsistent state management patterns
**Completed**: 2026-01-27

Documented state management guidelines and applied them consistently across the frontend.

**Files created/modified**:

1. **`docs/design_docs/11_frontend_state_management.md`** - Comprehensive guidelines covering:
   - Decision tree for choosing between Zustand, React Query, and useState
   - Documentation for each Zustand store (settings, UI, practice, review)
   - Store design conventions (structure, naming, selectors)
   - React Query patterns and query key conventions
   - Anti-patterns to avoid
   - Summary cheat sheet

2. **`frontend/src/stores/settingsStore.js`** - Added:
   - `knowledgeSectionVisibility` state object for note viewer section toggles
   - `toggleKnowledgeSection(key)` action
   - `setKnowledgeSectionVisibility(visibility)` action
   - Persistence via Zustand's `persist` middleware

3. **`frontend/src/pages/Knowledge.jsx`** - Refactored:
   - Removed raw `localStorage.getItem/setItem` calls
   - Now uses `useSettingsStore` for section visibility
   - Follows documented state management patterns

---

### ✅ TD-030: Skipped tests due to missing dependencies
**Completed**: 2026-01-28

Fixed all unnecessarily skipped tests so they can run without external dependencies.

**Changes**:

**1. test_vault_sync.py** - Removed unnecessary skip:
- Tests already use `mock_neo4j_client` fixture - no real Neo4j needed
- Removed `pytestmark` skipif that required `NEO4J_URI` env var
- All 15 tests now run with mocked Neo4j client

**2. test_code_sandbox.py** - Fixed broken skipif syntax:
- `pytest.importorskip` was used incorrectly in `@pytest.mark.skipif`
- Added `_is_docker_available()` helper function that properly checks Docker daemon
- Docker integration tests now correctly skip only when Docker is unavailable

**3. test_openapi_contract.py** - Generated snapshot file:
- Created `backend/tests/snapshots/openapi.json` with 82 endpoints and 122 schemas
- Snapshot comparison tests now pass instead of skipping

**4. test_pipelines.py** - Verified paths work:
- Sample PDFs exist in `test_data/` directory
- Path resolution `Path(__file__).parent.parent.parent.parent / "test_data"` is correct
- All PDF pipeline tests now run (not skipped)

**Additional**: Added "Optional Test Dependencies" section to `TESTING.md` documenting
which tests have optional requirements and how to enable them

---

### ✅ TD-031: Hardcoded path in run_processing.py
**Completed**: 2026-01-28

Made Obsidian vault path configurable in `scripts/run_processing.py`.

**Changes**:
- Changed from hardcoded `~/workspace/obsidian/second_brain/obsidian` to use environment variable
- Added sensible default (`~/obsidian_vault`) when not set or when Docker path detected
- Prints informative message when using default path
- Updated docstring to document `OBSIDIAN_VAULT_PATH` environment variable
- Script now respects `.env` file settings while providing fallback for local execution

---

### ✅ TD-032: Prototype code should be moved or removed
**Completed**: 2026-01-28

Reorganized prototype files to proper locations.

**File Movements**:
- `prototypes/test_mistral_ocr.py` → `scripts/examples/mistral_ocr_example.py`
- `prototypes/test_pdfplumber_annotations.py` → `scripts/examples/pdfplumber_annotations_example.py`
- `prototypes/test_pymupdf_annotations.py` → `scripts/examples/pymupdf_annotations_example.py`
- `prototypes/sample_mistral7b.pdf` → `test_data/sample_mistral7b.pdf`

**Cleanup**:
- Removed `prototypes/ocr_results/` directory (generated test outputs)
- Removed empty `prototypes/` directory
- Updated path references in all scripts to work from new locations
- Created `scripts/examples/README.md` documenting all example scripts

---

### ✅ TD-033: Test verifies intentional NotImplementedError
**Completed**: 2026-01-28

Clarified that this test is correct - no code change needed.

**Analysis**:
The test at `backend/tests/integration/test_pipelines.py:1001-1010` was initially flagged as
"incomplete test implementation" but is actually **intentional behavior**:

1. `RaindropSync.process()` deliberately raises `NotImplementedError`
2. This is by design - `RaindropSync` is for batch sync via `sync_collection()`
3. It should NOT be used via `PipelineRegistry` for single-item processing
4. For single-article processing, use `WebArticlePipeline` instead

The test correctly verifies this design constraint. Updated tech debt title to reflect
that this is expected behavior, not a bug.

---

### ✅ TD-038: Concept deduplication not working
**Completed**: 2026-01-28

Implemented comprehensive concept deduplication to prevent duplicate concepts like "Behavior Cloning (BC)" and "Behavior Cloning" from being stored as separate nodes.

**New Files**:
- `backend/app/services/processing/concept_dedup.py` - Name normalization and deduplication utilities

**Changes**:
- `backend/app/services/knowledge_graph/queries.py` - MERGE_CONCEPT_NODE now uses canonical_name
- `backend/app/services/knowledge_graph/client.py` - create_concept_node uses normalized names, added find_concept_by_canonical_name
- `backend/app/services/processing/stages/extraction.py` - Calls deduplicate_concepts() on extraction results
- `backend/app/services/processing/cleanup.py` - Added batch deduplication functions

**Key Functions**:
- `normalize_concept_name()` - Extracts canonical name and aliases
- `get_canonical_name()` - Returns base name without aliases
- `deduplicate_concepts()` - Deduplicates within a single extraction
- `deduplicate_neo4j_concepts()` - Batch deduplication for existing data
- `migrate_concepts_to_canonical_names()` - Migration helper for old concepts

---

### ✅ TD-039: Exercises not synced to Obsidian vault
**Completed**: 2026-01-28

Implemented exercise synchronization to Obsidian vault.

**Changes**:

**1. New template** (`config/templates/exercise.md.j2`):
- YAML frontmatter with type, topic, difficulty, tags, source content links
- Exercise prompt section
- Collapsible hints section (hidden by default)
- Expected key points section (hidden by default)
- Worked example section (for worked_example type exercises)
- Starter code section (for code exercises)
- Buggy code section (for debug exercises)
- Collapsible solution section (hidden by default)
- Test cases section (for code exercises)
- Links to source content

**2. VaultManager** (`backend/app/services/obsidian/vault.py`):
- Added `get_exercise_folder()` method for exercise folder resolution

**3. Obsidian Generator** (`backend/app/services/processing/output/obsidian_generator.py`):
- Added `generate_exercise_note()` function for single exercise note generation
- Added `generate_exercise_notes_for_content()` function for batch exercise note generation
- Exercises are stored in `exercises/by-topic/{topic}/` folder structure
- Filenames include exercise UUID suffix for uniqueness

**4. Processing Pipeline** (`backend/app/services/processing/pipeline.py`):
- Integrated exercise note generation after exercise creation
- Exercise notes generated when `create_obsidian_note` is enabled and exercises exist

**Folder Structure**:
```
vault/
└── exercises/
    └── by-topic/
        └── ml_transformers/
            └── Free Recall - ml_transformers_abc12345.md
```

---

### ✅ TD-040: PDF images not integrated into summaries
**Completed**: 2026-01-28

Implemented full image extraction and integration for PDF/book processing.

**Changes**:

**1. PDF Processor** (`backend/app/pipelines/pdf_processor.py`):
- Changed `include_images` default from `False` to `True`
- Images are now extracted during OCR and saved to vault
- Image metadata stored in `UnifiedContent.metadata["extracted_images"]`

**2. New Image Storage Service** (`backend/app/services/processing/output/image_storage.py`):
- `save_extracted_images()` - Save base64 images to vault assets folder
- `delete_content_images()` - Cleanup for reprocessing
- `ExtractedImage` dataclass with vault_path, page_number, description, dimensions
- Image optimization: resize to 1200px max, PNG compression
- Storage: `vault/assets/images/{content_id}/page_N_img_M.png`

**3. Obsidian Integration**:
- Added `figures` and `has_figures` to template data
- Updated `paper.md.j2`, `article.md.j2`, `book.md.j2` with Figures section
- Images embedded with Obsidian wikilink syntax: `![[vault_path]]`

**4. API Endpoints** (`backend/app/routers/vault.py`):
- `GET /api/vault/assets/{path}` - Serve assets (images, PDFs) from vault
- `GET /api/vault/content/{id}/images` - List images for a content item

**Folder Structure**:
```
vault/
└── assets/
    └── images/
        └── {content_id}/
            ├── page_1_img_0.png
            └── page_3_img_0.png
```

---

## Notes

- When addressing tech debt, update this document and move items to "Completed"
- Include PR/commit references when closing items
- P0 items must be resolved before open-source announcement
- Total items: 40 (5 P0, 14 P1, 19 P2, 2 P3) — 34 completed
