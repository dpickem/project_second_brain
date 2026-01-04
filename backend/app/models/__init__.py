"""
Pydantic models for the application.

For enums, import from app.enums:
    from app.enums import ContentType, PipelineName, ProcessingStage

For models, import from app.models:
    from app.models import UnifiedContent, ProcessingResult
"""

from app.models.content import (
    Annotation,
    UnifiedContent,
)
from app.models.processing import (
    ContentAnalysis,
    Concept,
    ExtractionResult,
    TagAssignment,
    Connection,
    FollowupTask,
    MasteryQuestion,
    ProcessingResult,
)

__all__ = [
    # Content models
    "Annotation",
    "UnifiedContent",
    # Processing models
    "ContentAnalysis",
    "Concept",
    "ExtractionResult",
    "TagAssignment",
    "Connection",
    "FollowupTask",
    "MasteryQuestion",
    "ProcessingResult",
]
