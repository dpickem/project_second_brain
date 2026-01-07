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

## Completed Items

_None yet._

---

## Notes

- When addressing tech debt, update this document and move items to "Completed"
- Include PR/commit references when closing items
- Consider adding new items discovered during development

