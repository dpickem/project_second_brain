"""
Centralized enum definitions for the application.

All enums are organized by domain:
- pipeline.py: Pipeline names, operations, content types
- processing.py: Processing stages, statuses, summary levels
- content.py: Content types, annotation types, processing status

Usage:
    from app.enums import PipelineName, PipelineOperation, ContentType

    # Or import from specific module
    from app.enums.pipeline import PipelineName
"""

from app.enums.pipeline import (
    PipelineName,
    PipelineOperation,
    PipelineContentType,
)
from app.enums.processing import (
    ProcessingStage,
    ProcessingRunStatus,
    SummaryLevel,
    ContentDomain,
    ContentComplexity,
    ContentLength,
    ConceptImportance,
    FollowupTaskType,
    FollowupPriority,
    FollowupTimeEstimate,
    QuestionType,
    QuestionDifficulty,
    RelationshipType,
    TagCategory,
    NodeType,
)
from app.enums.content import (
    ContentType,
    AnnotationType,
    ProcessingStatus,
)

__all__ = [
    # Pipeline enums
    "PipelineName",
    "PipelineOperation",
    "PipelineContentType",
    # Processing enums
    "ProcessingStage",
    "ProcessingRunStatus",
    "SummaryLevel",
    "ContentDomain",
    "ContentComplexity",
    "ContentLength",
    "ConceptImportance",
    "FollowupTaskType",
    "FollowupPriority",
    "FollowupTimeEstimate",
    "QuestionType",
    "QuestionDifficulty",
    "RelationshipType",
    "TagCategory",
    "NodeType",
    # Content enums
    "ContentType",
    "AnnotationType",
    "ProcessingStatus",
]
