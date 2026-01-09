"""
Centralized enum definitions for the application.

All enums are organized by domain:
- pipeline.py: Pipeline names, operations, content types
- processing.py: Processing stages, statuses, summary levels
- content.py: Content types, annotation types, processing status
- knowledge.py: Knowledge graph connection types, query directions

Usage:
    from app.enums import PipelineName, PipelineOperation, ContentType

    # Or import from specific module
    from app.enums.pipeline import PipelineName
    from app.enums.knowledge import GraphConnectionType
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
from app.enums.learning import (
    CardState,
    Rating,
    ExerciseType,
    ExerciseDifficulty,
    MasteryTrend,
    SessionType,
    CodeLanguage,
)
from app.enums.knowledge import (
    GraphConnectionType,
    ConnectionDirection,
)
from app.enums.api import (
    ExplanationStyle,
    RateLimitType,
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
    # Learning enums
    "CardState",
    "Rating",
    "ExerciseType",
    "ExerciseDifficulty",
    "MasteryTrend",
    "SessionType",
    "CodeLanguage",
    # Knowledge graph enums
    "GraphConnectionType",
    "ConnectionDirection",
    # API enums
    "ExplanationStyle",
    "RateLimitType",
]
