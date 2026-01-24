# Technical Debt Tracker

This document tracks known technical debt items and refactoring tasks across the codebase.

## Table of Contents

- [Priority Levels](#priority-levels)
- [Open Items](#open-items)
  - [Code Quality & Patterns](#code-quality--patterns)
    - [TD-001: Use TYPE_CHECKING for type annotation imports](#td-001-use-type_checking-for-type-annotation-imports)
    - [TD-002: Complete LLM/OCR/VLM usage tracking and persistence](#td-002-complete-llmocrvlm-usage-tracking-and-persistence)
    - [TD-003: Move cross-layer model construction logic into model factory methods](#td-003-move-cross-layer-model-construction-logic-into-model-factory-methods)
    - [TD-004: Clean up imports and move to top of files](#td-004-clean-up-imports-and-move-to-top-of-files)
    - [TD-005: Robust deduplication and cleanup on reprocessing](#td-005-robust-deduplication-and-cleanup-on-reprocessing)
    - [TD-006: Eliminate magic numbers from codebase](#td-006-eliminate-magic-numbers-from-codebase)
- [Completed Items](#completed-items)
- [Notes](#notes)

---

## Priority Levels

- **P0**: Critical - Blocking or causing issues
- **P1**: High - Should address soon
- **P2**: Medium - Address when touching related code
- **P3**: Low - Nice to have

---

## Open Items

### Code Quality & Patterns

#### TD-001: Use `TYPE_CHECKING` for type annotation imports
**Priority**: P2  
**Status**: Open  
**Area**: Backend services

**Description**:  
Standardize the use of `typing.TYPE_CHECKING` for imports that are only needed for type hints. This pattern avoids circular imports at runtime while maintaining full type safety for static analysis.

**Current State**:  
- Some files use string forward references (`Optional["ClassName"]`)
- Some files have potential circular import issues
- Inconsistent patterns across the codebase

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

**Related**:  
- Example implementation: `backend/app/services/learning/session_service.py`

---

#### TD-003: Move cross-layer model construction logic into model factory methods
**Priority**: P2  
**Status**: Open  
**Area**: Backend models (Pydantic + SQLAlchemy)

**Description**:  
Standardize the pattern of defining **factory constructors** on the model classes (both Pydantic models and SQLAlchemy ORM models) for converting from common upstream sources (DB records, pipeline outputs, API payloads). This avoids duplicated “mapping glue” across routers/services/tasks and makes conversions testable, discoverable, and consistent.

**Motivation / Current Pain**:  
- Conversion logic is frequently repeated inline (e.g., mapping DB `Content` → Pydantic `UnifiedContent`, or Pydantic `ProcessingResult` → DB `ProcessingRun`)
- Inline mappings drift over time (fields added/renamed in one path but not others)
- Harder to ensure consistent defaults, timestamps, and optional field handling

**Target Pattern**:
```python
class SomeModel:
    @classmethod
    def from_source_x(cls, x: SourceX) -> "SomeModel":
        ...
```

**Examples / Candidates**:
- [ ] `UnifiedContent.from_db_content(db_content)` (DB → Pydantic)
- [ ] `ProcessingRun.from_processing_result(...)` (Pydantic → DB)
- [ ] Consider similar factories for: `TagAssignment`, `ExtractionResult`, `Connection`, etc. where conversions happen repeatedly across layers.

**Acceptance Criteria**:
- Conversion/mapping logic lives primarily on the model class (or a dedicated `model_factories.py` module if a model can’t depend on a source type without circular imports)
- Call sites use the factory method instead of hand-rolling mappings
- Add focused unit tests for each factory method (one per conversion direction/source)

---

#### TD-004: Clean up imports and move to top of files
**Priority**: P2  
**Status**: Open  
**Area**: Backend & Frontend codebase

**Description**:  
Standardize import organization across the codebase. All imports should be moved to the top of files where possible, following Python/JavaScript conventions and improving code readability.

**Current State**:  
- Some files have inline imports scattered throughout the code
- Inconsistent import ordering and grouping
- Some local imports used to avoid circular dependencies (should use `TYPE_CHECKING` instead per TD-001)

**Target Pattern**:
```python
# Python files
from __future__ import annotations  # If using PEP 563

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

```javascript
// JavaScript/React files
// Third-party imports first
import React from 'react';
import { useState } from 'react';

// Local imports
import { MyComponent } from './components';
import { useMyHook } from '../hooks';
```

**Files to Review**:
- [ ] `backend/app/services/**/*.py`
- [ ] `backend/app/routers/*.py`
- [ ] `frontend/src/**/*.jsx`
- [ ] `frontend/src/**/*.js`

**Acceptance Criteria**:
- All imports at the top of files (except justified `TYPE_CHECKING` blocks)
- Consistent grouping: stdlib → third-party → local
- No inline imports unless absolutely necessary (with comment explaining why)
- Linter/formatter rules enforced (isort for Python, ESLint for JS)

---

#### TD-002: Complete LLM/OCR/VLM usage tracking and persistence
**Priority**: P1  
**Status**: Open  
**Area**: Backend services, LLM integration

**Description**:  
Ensure ALL external model calls (LLM, OCR, VLM) are consistently tracked via `LLMUsage` and persisted to the database. This enables cost monitoring, usage analytics, and debugging of model interactions.

**Current State**:  
- `LLMUsage` model exists in `app/models/llm.py`
- Some pipeline stages return usage data but persistence is inconsistent
- OCR calls (Mistral) may not be fully tracked
- VLM (vision-language model) calls need audit
- Assistant service tracks usage but may not persist all calls
- No centralized dashboard or API for usage analytics

**Required Work**:
1. **Audit all model call sites**:
   - [ ] `backend/app/services/llm/client.py` - Core LLM client
   - [ ] `backend/app/services/assistant/service.py` - Chat/RAG calls
   - [ ] `backend/app/services/processing/stages/*.py` - Pipeline stages
   - [ ] `backend/app/services/learning/card_generator.py` - Card generation
   - [ ] `backend/app/services/learning/exercise_generator.py` - Exercise generation
   - [ ] `backend/app/pipelines/*.py` - Ingestion pipelines (OCR, transcription)
   - [ ] `backend/app/services/learning/evaluator.py` - Answer evaluation

2. **Ensure consistent tracking pattern**:
   ```python
   usage = LLMUsage(
       model=response.model,
       prompt_tokens=response.usage.prompt_tokens,
       completion_tokens=response.usage.completion_tokens,
       total_tokens=response.usage.total_tokens,
       purpose="card_generation",  # Consistent purpose tags
       content_id=content.id,      # Link to content when applicable
   )
   db.add(usage)
   await db.commit()
   ```

3. **Add usage analytics API**:
   - [ ] `GET /api/analytics/llm-usage` - Usage by model, purpose, time period
   - [ ] `GET /api/analytics/llm-costs` - Estimated costs based on token counts

4. **Distinguish model types**:
   - `llm` - Text generation (GPT-4, Claude, etc.)
   - `ocr` - Document OCR (Mistral pixtral, etc.)
   - `vlm` - Vision-language (image understanding)
   - `embedding` - Text embeddings
   - `transcription` - Audio transcription (Whisper)

**Acceptance Criteria**:
- Every external model API call creates an `LLMUsage` record
- Usage records include: model, tokens, purpose, timestamp, content_id (if applicable)
- Analytics API exposes aggregated usage data
- Dashboard displays usage trends and estimated costs

**Related**:  
- `backend/app/models/llm.py` - LLMUsage model
- `backend/app/db/models_processing.py` - May need schema updates
- `backend/app/services/llm/client.py` - Primary LLM interface

---

#### TD-005: Robust deduplication and cleanup on reprocessing
**Priority**: P1  
**Status**: Open  
**Area**: Backend services, Data integrity

**Description**:  
Ensure deduplication works robustly throughout the system. When content is reprocessed, the system must properly clean up all old entries across all data stores to prevent orphaned or duplicate data.

**Current State**:  
- Reprocessing may leave stale data in various stores
- Old database entries may not be properly cleaned up
- Neo4j nodes and relationships may become orphaned
- Obsidian notes may accumulate duplicates or stale versions

**Required Cleanup on Reprocessing**:
1. **PostgreSQL (SQL database)**:
   - [ ] Delete old `ProcessingRun` records for the content
   - [ ] Delete old `TagAssignment` records
   - [ ] Delete old `Connection` records
   - [ ] Delete old `Card` records (flashcards, exercises)
   - [ ] Delete old `ExtractionResult` records
   - [ ] Update or replace `Content` record (not duplicate)

2. **Neo4j (Knowledge Graph)**:
   - [ ] Delete old node for the content
   - [ ] Delete all relationships connected to the old node
   - [ ] Ensure new node creation doesn't create duplicates
   - [ ] Handle cascading relationship cleanup

3. **Obsidian (Markdown notes)**:
   - [ ] Delete or overwrite the old note file
   - [ ] Update/remove old wikilinks in other notes pointing to old content
   - [ ] Handle renamed content (old filename → new filename)
   - [ ] Clean up any orphaned attachments

4. **Deduplication Strategy**:
   - [ ] Use `content_id` (UUID) as the canonical identifier across all stores
   - [ ] Implement idempotent processing (same input → same output)
   - [ ] Add "upsert" semantics where appropriate (insert or update)
   - [ ] Consider soft-delete vs hard-delete tradeoffs

**Acceptance Criteria**:
- Reprocessing the same content results in exactly one entry per store
- No orphaned records in SQL, Neo4j, or Obsidian after reprocessing
- All relationships/connections are properly updated or removed
- Audit log tracks what was cleaned up during reprocessing
- Integration tests verify cleanup across all data stores

**Related**:  
- `backend/app/services/processing/pipeline.py` - Main processing pipeline
- `backend/app/services/obsidian/vault.py` - Obsidian note management
- `backend/app/services/obsidian/sync.py` - Obsidian sync service
- `backend/app/services/neo4j/` - Neo4j graph operations
- `backend/app/models/content.py` - Content model with `content_id`

---

#### TD-006: Eliminate magic numbers from codebase
**Priority**: P2  
**Status**: Open  
**Area**: Backend & Frontend codebase

**Description**:  
Remove all magic numbers (hard-coded numeric literals with unclear meaning) from the codebase. These should be replaced with named constants at the file/module level or moved to user-configurable settings where appropriate.

**Why This Matters**:  
- Magic numbers obscure intent and make code harder to understand
- Hard-coded values scattered across files are difficult to maintain consistently
- Users cannot easily customize behavior without editing source code
- Changes to thresholds/limits require hunting through multiple files

**Current State**:  
- Various numeric literals embedded directly in code (timeouts, thresholds, limits, weights, etc.)
- No centralized configuration for tunable parameters
- Inconsistent patterns: some values are constants, others inline

**Target Pattern**:

For implementation constants (not user-configurable):
```python
# At top of file, after imports
DEFAULT_BATCH_SIZE = 100
MAX_RETRY_ATTEMPTS = 3
CACHE_TTL_SECONDS = 3600
MASTERY_THRESHOLD = 0.8

def process_items(items):
    for batch in chunks(items, DEFAULT_BATCH_SIZE):
        ...
```

For user-configurable settings:
```python
# In config/settings.py or similar
class LearningSettings(BaseSettings):
    mastery_threshold: float = 0.8
    review_interval_days: int = 7
    max_cards_per_session: int = 20

# Usage
settings = get_settings()
if score >= settings.mastery_threshold:
    ...
```

**Files to Review**:
- [ ] `backend/app/services/learning/*.py` - Learning algorithm parameters
- [ ] `backend/app/services/processing/stages/*.py` - Processing thresholds
- [ ] `backend/app/services/llm/*.py` - Token limits, timeouts
- [ ] `backend/app/routers/*.py` - Pagination limits, defaults
- [ ] `backend/app/pipelines/*.py` - Batch sizes, retry counts
- [ ] `frontend/src/**/*.jsx` - UI constants, animation durations

**Acceptance Criteria**:
- No numeric literals with unclear meaning remain in business logic
- Constants are named descriptively (e.g., `MAX_TOKENS_PER_REQUEST`, not `MAX`)
- User-tunable parameters are exposed via configuration (YAML/env vars)
- Constants are defined at module level or in dedicated constants files
- Comments explain non-obvious values where needed
- Configuration changes don't require code modifications

**Related**:  
- `backend/app/config/` - Existing configuration modules
- `config/default.yaml` - User-facing configuration file

---

## Completed Items

_None yet._

---

## Notes

- When addressing tech debt, update this document and move items to "Completed"
- Include PR/commit references when closing items
- Consider adding new items discovered during development

