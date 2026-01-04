"""
LLM Processing Module

Transforms raw ingested content into structured, connected knowledge.
The pipeline performs seven processing stages:

1. Content Analysis - Determine type, domain, complexity
2. Summarization - Generate brief, standard, and detailed summaries
3. Concept Extraction - Extract key concepts, findings, entities
4. Tagging - Assign tags from controlled vocabulary
5. Connection Discovery - Find relationships to existing knowledge
6. Follow-up Generation - Create actionable learning tasks
7. Question Generation - Create mastery questions

Usage:
    from app.services.processing import process_content, PipelineConfig

    result = await process_content(content, config=PipelineConfig())
"""

from app.services.processing.pipeline import process_content, PipelineConfig

__all__ = ["process_content", "PipelineConfig"]
