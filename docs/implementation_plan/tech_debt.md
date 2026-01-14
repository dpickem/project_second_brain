# Technical Debt Tracker

This document tracks known technical debt items and refactoring tasks across the codebase.

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

## Completed Items

_None yet._

---

## Notes

- When addressing tech debt, update this document and move items to "Completed"
- Include PR/commit references when closing items
- Consider adding new items discovered during development

