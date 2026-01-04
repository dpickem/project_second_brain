"""
Processing Stages

Each stage is a standalone module that performs a specific transformation:

- content_analysis: Initial content classification and metadata extraction
- summarization: Multi-level summary generation
- extraction: Concept, entity, and key finding extraction
- taxonomy_loader: Dynamic tag taxonomy loading from config
- tagging: Tag assignment from controlled vocabulary
- connections: Connection discovery to existing knowledge
- followups: Follow-up task generation
- questions: Mastery question generation

Return Types:
    All stages return a tuple of (result, list[LLMUsage]) where:
    - result: The stage's primary output (ContentAnalysis, dict, etc.)
    - list[LLMUsage]: Usage records for cost tracking (to be persisted via CostTracker)

    This enables per-operation cost attribution and historical cost analysis.

Stages can be run independently or orchestrated by the pipeline.
"""

from app.services.processing.stages.content_analysis import analyze_content
from app.services.processing.stages.summarization import (
    generate_summary,
    generate_all_summaries,
)
from app.services.processing.stages.extraction import extract_concepts
from app.services.processing.stages.taxonomy_loader import (
    get_tag_taxonomy,
    TagTaxonomy,
    TagTaxonomyLoader,
)
from app.services.processing.stages.tagging import assign_tags
from app.services.processing.stages.connections import discover_connections
from app.services.processing.stages.followups import generate_followups
from app.services.processing.stages.questions import generate_mastery_questions

__all__ = [
    "analyze_content",
    "generate_summary",
    "generate_all_summaries",
    "extract_concepts",
    "get_tag_taxonomy",
    "TagTaxonomy",
    "TagTaxonomyLoader",
    "assign_tags",
    "discover_connections",
    "generate_followups",
    "generate_mastery_questions",
]
