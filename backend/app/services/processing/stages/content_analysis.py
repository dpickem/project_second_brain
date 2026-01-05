"""
Content Analysis Stage

The first processing stage that determines content type, domain, complexity,
and key characteristics. This analysis guides downstream processing stages
with appropriate prompts and model configurations.

Usage:
    from app.services.processing.stages.content_analysis import analyze_content

    analysis, usages = await analyze_content(content, llm_client)
    print(f"Type: {analysis.content_type}, Domain: {analysis.domain}")
"""

import logging

from app.models.content import UnifiedContent
from app.models.processing import ContentAnalysis
from app.enums.pipeline import PipelineOperation
from app.enums.processing import ContentDomain, ContentComplexity, ContentLength
from app.pipelines.utils.cost_types import LLMUsage
from app.services.llm.client import LLMClient
from app.config.processing import processing_settings

logger = logging.getLogger(__name__)

# Valid values derived from enums
_VALID_DOMAINS = {e.value.lower() for e in ContentDomain}
_VALID_COMPLEXITY = {e.value.lower() for e in ContentComplexity}
_VALID_LENGTH = {e.value.lower() for e in ContentLength}


ANALYSIS_PROMPT = """Analyze this content and provide structured metadata.

Content Title: {title}
Content Type Hint: {source_type}
Content (truncated to {truncate_limit} chars):
{content}

Provide analysis in JSON format:
{{
  "content_type": "paper|article|book|code|idea|voice_memo",
  "domain": "{domain_options}",
  "complexity": "{complexity_options}",
  "estimated_length": "{length_options}",
  "has_code": true|false,
  "has_math": true|false,
  "has_diagrams": true|false,
  "key_topics": ["topic1", "topic2", "topic3"],
  "language": "en|de|fr|es|..."
}}

Guidelines:
- "paper" for academic/research papers with citations, methodology, results
- "article" for blog posts, news, essays, tutorials
- "book" for book excerpts, chapters, or full books
- "code" for code repositories, technical documentation, API references
- "idea" for quick notes, brainstorms, unstructured thoughts
- "voice_memo" for transcribed audio/voice notes

Complexity levels:
- "foundational": Introductory, suitable for beginners, explains basics
- "intermediate": Assumes some background knowledge, builds on fundamentals
- "advanced": Requires deep domain expertise, specialized terminology

Length:
- "short": < 2000 words
- "medium": 2000-10000 words
- "long": > 10000 words

Key topics should be 3-7 specific topics covered, not generic categories.
"""


async def analyze_content(
    content: UnifiedContent, llm_client: LLMClient
) -> tuple[ContentAnalysis, list[LLMUsage]]:
    """
    Perform initial content analysis to guide downstream processing.

    This is the first stage of the processing pipeline. It determines:
    - Content type (paper, article, book, code, idea, voice_memo)
    - Primary domain (ml, systems, leadership, etc.)
    - Complexity level (foundational, intermediate, advanced)
    - Content characteristics (has_code, has_math, has_diagrams)
    - Key topics covered
    - Language

    Truncation is used even with large-context models for:
    - Cost efficiency (fewer input tokens = less cost)
    - Speed (less content to process)
    - Focus (analysis only needs a representative sample)

    Args:
        content: Unified content from ingestion
        llm_client: LLM client for completion

    Returns:
        Tuple of (ContentAnalysis, list of LLMUsage for cost tracking)
    """
    truncate_limit = processing_settings.ANALYSIS_TRUNCATE
    text_sample = content.full_text[:truncate_limit] if content.full_text else ""

    if not text_sample.strip():
        logger.warning(f"Content {content.id} has no text, using defaults")
        return _default_analysis(content), []

    prompt = ANALYSIS_PROMPT.format(
        title=content.title,
        source_type=content.source_type.value,
        content=text_sample,
        truncate_limit=truncate_limit,
        domain_options="|".join(e.value.lower() for e in ContentDomain),
        complexity_options="|".join(e.value.lower() for e in ContentComplexity),
        length_options="|".join(e.value.lower() for e in ContentLength),
    )

    try:
        # json_mode=True returns parsed JSON with automatic retries on decode errors
        data, usage = await llm_client.complete(
            operation=PipelineOperation.CONTENT_ANALYSIS,
            messages=[{"role": "user", "content": prompt}],
            temperature=processing_settings.ANALYSIS_TEMPERATURE,
            max_tokens=processing_settings.ANALYSIS_MAX_TOKENS,
            json_mode=True,
            content_id=content.id,
        )

        # Validate and normalize values against enums
        content_type = data.get("content_type", content.source_type.value)
        if content_type not in [
            "paper",
            "article",
            "book",
            "code",
            "idea",
            "voice_memo",
        ]:
            content_type = content.source_type.value

        domain = data.get("domain", "general").lower()
        if domain not in _VALID_DOMAINS:
            domain = ContentDomain.GENERAL.value.lower()

        complexity = data.get("complexity", "intermediate").lower()
        if complexity not in _VALID_COMPLEXITY:
            complexity = ContentComplexity.INTERMEDIATE.value.lower()

        estimated_length = data.get("estimated_length", "medium").lower()
        if estimated_length not in _VALID_LENGTH:
            estimated_length = ContentLength.MEDIUM.value.lower()

        result = ContentAnalysis(
            content_type=content_type,
            domain=domain,
            complexity=complexity,
            estimated_length=estimated_length,
            has_code=bool(data.get("has_code", False)),
            has_math=bool(data.get("has_math", False)),
            has_diagrams=bool(data.get("has_diagrams", False)),
            key_topics=data.get("key_topics", [])[:10],  # Limit to 10
            language=data.get("language", "en"),
        )
        return result, [usage]

    except Exception as e:
        logger.error(f"Content analysis failed: {e}")
        return _default_analysis(content), []


def _default_analysis(content: UnifiedContent) -> ContentAnalysis:
    """Return sensible defaults when analysis fails."""
    return ContentAnalysis(
        content_type=content.source_type.value,
        domain=ContentDomain.GENERAL.value.lower(),
        complexity=ContentComplexity.INTERMEDIATE.value.lower(),
        estimated_length=ContentLength.MEDIUM.value.lower(),
        has_code=False,
        has_math=False,
        has_diagrams=False,
        key_topics=[],
        language="en",
    )
