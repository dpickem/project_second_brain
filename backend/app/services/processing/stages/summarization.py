"""
Summarization Stage

Generates multi-level summaries for content:
- Brief: 1-2 sentences for quick reference
- Standard: 1-2 paragraphs for Obsidian frontmatter
- Detailed: Full structured summary for deep comprehension

Content-type-specific prompts ensure relevant information is prioritized.

Usage:
    from app.services.processing.stages.summarization import generate_all_summaries

    summaries, usages = await generate_all_summaries(content, analysis, llm_client)
    print(summaries["standard"])
"""

import logging

from app.models.content import UnifiedContent
from app.enums.pipeline import PipelineOperation
from app.enums.processing import SummaryLevel
from app.models.processing import ContentAnalysis
from app.models.llm_usage import LLMUsage
from app.services.llm.client import LLMClient
from app.config.processing import processing_settings

logger = logging.getLogger(__name__)


# Content-type-specific prompt templates
SUMMARY_PROMPTS = {
    "paper": """Summarize this academic paper at {level} level.

Paper Title: {title}
Authors: {authors}

Paper content:
{content}

Annotations/highlights from the reader (these indicate what they found important):
{annotations}

Summary levels:
- BRIEF: Core contribution in 1-2 sentences. What is the paper's main claim?
- STANDARD: 2-3 paragraphs covering: Problem addressed, Approach taken, Key findings, Implications
- DETAILED: Full structured summary including: Abstract, Introduction context, Methodology, Results, Discussion, Limitations, Future work

Provide a {level} summary:""",
    "article": """Summarize this article at {level} level.

Title: {title}
Source: {source}

Article:
{content}

Reader's highlights (what they found important):
{annotations}

Summary levels:
- BRIEF: Main point in 1-2 sentences
- STANDARD: 2-3 paragraphs with key takeaways and actionable insights
- DETAILED: Comprehensive summary with all major points, examples, and implications

Focus on practical takeaways and actionable insights.

Provide a {level} summary:""",
    "book": """Summarize these book notes/highlights at {level} level.

Book: {title}
Authors: {authors}

Content (highlights, notes, or chapter text):
{content}

The reader highlighted these passages as important - use them to inform the summary.

Summary levels:
- BRIEF: Core theme in 1-2 sentences
- STANDARD: Key ideas and their implications
- DETAILED: Chapter-by-chapter or section-by-section breakdown

Provide a {level} summary:""",
    "code": """Summarize this code repository analysis at {level} level.

Repository: {title}

Analysis:
{content}

Summary levels:
- BRIEF: What the code does in 1-2 sentences
- STANDARD: Purpose, architecture, key patterns
- DETAILED: Full breakdown including: Purpose, Architecture, Tech stack, Notable patterns, Key learnings

Provide a {level} summary:""",
    "idea": """Summarize this idea/note at {level} level.

Title: {title}

Content:
{content}

Summary levels:
- BRIEF: Core idea in 1 sentence
- STANDARD: Main point with context and implications
- DETAILED: Full exploration of the idea with connections

Provide a {level} summary:""",
    "voice_memo": """Summarize this voice memo transcription at {level} level.

Title: {title}

Transcription:
{content}

Summary levels:
- BRIEF: Main point in 1 sentence
- STANDARD: Key points organized logically
- DETAILED: Full summary with all points, ideas, and action items

Provide a {level} summary:""",
}


async def generate_summary(
    content: UnifiedContent,
    analysis: ContentAnalysis,
    level: SummaryLevel,
    llm_client: LLMClient,
    content_id: str | None = None,
) -> tuple[str, LLMUsage]:
    """
    Generate a summary at the specified level.

    Args:
        content: Unified content from ingestion
        analysis: Content analysis result
        level: Summary level (brief, standard, detailed)
        llm_client: LLM client for completion

    Returns:
        Tuple of (summary text, LLMUsage)
    """
    # Select appropriate prompt template
    prompt_template = SUMMARY_PROMPTS.get(
        analysis.content_type, SUMMARY_PROMPTS["article"]  # Default to article template
    )

    # Format annotations
    annotations_text = _format_annotations(content, max_annotations=20)

    # Adjust content length based on level
    content_limits = {
        SummaryLevel.BRIEF: processing_settings.SUMMARY_TRUNCATE_BRIEF,
        SummaryLevel.STANDARD: processing_settings.SUMMARY_TRUNCATE_STANDARD,
        SummaryLevel.DETAILED: processing_settings.SUMMARY_TRUNCATE_DETAILED,
    }
    max_content = content_limits.get(
        level, processing_settings.SUMMARY_TRUNCATE_STANDARD
    )

    prompt = prompt_template.format(
        title=content.title,
        authors=", ".join(content.authors) if content.authors else "Unknown",
        source=content.source_url or "Unknown",
        content=content.full_text[:max_content] if content.full_text else "",
        annotations=annotations_text,
        level=level.value.upper(),
    )

    # Max tokens based on level
    token_limits = {
        SummaryLevel.BRIEF: processing_settings.SUMMARY_MAX_TOKENS_BRIEF,
        SummaryLevel.STANDARD: processing_settings.SUMMARY_MAX_TOKENS_STANDARD,
        SummaryLevel.DETAILED: processing_settings.SUMMARY_MAX_TOKENS_DETAILED,
    }
    max_tokens = token_limits.get(
        level, processing_settings.SUMMARY_MAX_TOKENS_STANDARD
    )

    # Retry logic is handled by @retry decorator on LLMClient.complete()
    return await llm_client.complete(
        operation=PipelineOperation.SUMMARIZATION,
        messages=[{"role": "user", "content": prompt}],
        temperature=processing_settings.SUMMARY_TEMPERATURE,
        max_tokens=max_tokens,
        content_id=content_id or content.id,
    )


async def generate_all_summaries(
    content: UnifiedContent, analysis: ContentAnalysis, llm_client: LLMClient
) -> tuple[dict[str, str], list[LLMUsage]]:
    """
    Generate summaries at all levels.

    Args:
        content: Unified content from ingestion
        analysis: Content analysis result
        llm_client: LLM client for completion

    Returns:
        Tuple of (dict mapping level name to summary text, list of LLMUsage)
        ({"brief": "...", "standard": "...", "detailed": "..."}, [usage1, usage2, usage3])
    """
    summaries = {}
    usages: list[LLMUsage] = []

    for level in SummaryLevel:
        try:
            summary_text, usage = await generate_summary(
                content, analysis, level, llm_client
            )
            summaries[level.value] = summary_text
            usages.append(usage)
            logger.debug(f"Generated {level.value} summary ({len(summary_text)} chars)")
        except Exception as e:
            logger.error(f"Failed to generate {level.value} summary: {e}")
            summaries[level.value] = f"[Summary generation failed: {e}]"

    return summaries, usages


def _format_annotations(content: UnifiedContent, max_annotations: int = 20) -> str:
    """Format annotations for inclusion in prompts."""
    if not content.annotations:
        return "None provided"

    formatted = []
    for annotation in content.annotations[:max_annotations]:
        text = annotation.content[: processing_settings.ANNOTATION_TRUNCATE]
        if annotation.page_number:
            formatted.append(f"- [p.{annotation.page_number}] {text}")
        else:
            formatted.append(f"- {text}")

    return "\n".join(formatted)
