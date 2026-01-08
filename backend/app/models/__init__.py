"""
Pydantic models for the application.

For enums, import from app.enums:
    from app.enums import ContentType, PipelineName, ProcessingStage

For models, import from app.models:
    from app.models import UnifiedContent, ProcessingResult, LLMUsage
    from app.models import GraphNode, GraphResponse, SearchRequest  # Knowledge graph
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
from app.models.llm_usage import (
    LLMUsage,
    extract_provider,
    extract_usage_from_response,
    create_error_usage,
)
from app.models.knowledge import (
    GraphNode,
    GraphEdge,
    GraphResponse,
    GraphStats,
    NodeDetails,
    SearchResult,
    SearchRequest,
    SearchResponse,
    NodeConnection,
    ConnectionsResponse,
    TopicNode,
    TopicHierarchyResponse,
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
    # LLM usage tracking
    "LLMUsage",
    "extract_provider",
    "extract_usage_from_response",
    "create_error_usage",
    # Knowledge graph models
    "GraphNode",
    "GraphEdge",
    "GraphResponse",
    "GraphStats",
    "NodeDetails",
    "SearchResult",
    "SearchRequest",
    "SearchResponse",
    "NodeConnection",
    "ConnectionsResponse",
    "TopicNode",
    "TopicHierarchyResponse",
]
