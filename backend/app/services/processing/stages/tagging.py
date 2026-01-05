"""
Tagging Stage

Assigns tags from the controlled vocabulary (tag taxonomy) to content.
Tags enable filtering, grouping, and discovering content by domain,
status, or quality level.

The taxonomy is loaded from config/tag-taxonomy.yaml (single source of truth).

Usage:
    from app.services.processing.stages.tagging import assign_tags

    tags, usages = await assign_tags(content.title, analysis, summary, llm_client)
    print(f"Domain tags: {tags.domain_tags}")
    print(f"Meta tags: {tags.meta_tags}")
"""

import logging

from app.config.processing import processing_settings
from app.models.processing import ContentAnalysis, TagAssignment
from app.enums.pipeline import PipelineOperation
from app.pipelines.utils.cost_types import LLMUsage
from app.services.llm.client import LLMClient
from app.services.processing.stages.taxonomy_loader import get_tag_taxonomy, TagTaxonomy

logger = logging.getLogger(__name__)


TAGGING_PROMPT = """Assign tags to this content from the provided taxonomy.

Content Analysis:
- Title: {title}
- Type: {content_type}
- Domain: {domain}
- Complexity: {complexity}
- Key Topics: {key_topics}

Summary: {summary}

Available Tags (select from these ONLY):

DOMAIN TAGS (hierarchical, e.g., ml/transformers/attention):
{domain_tags}

META TAGS (status and quality):
{meta_tags}

Rules:
1. Assign 1-5 domain tags (most specific that applies)
2. Assign 1-2 meta tags (status + quality)
3. ONLY use tags from the provided taxonomy
4. Prefer more specific tags over general ones
5. If the taxonomy has a clear gap, suggest a new tag

Return as JSON:
{{
  "domain_tags": ["domain/category/topic", "domain/category/topic2"],
  "meta_tags": ["status/actionable", "quality/deep-dive"],
  "suggested_new_tags": ["domain/new-tag if taxonomy has clear gap"],
  "reasoning": "Brief explanation of tag choices"
}}
"""


async def assign_tags(
    content_title: str,
    analysis: ContentAnalysis,
    summary: str,
    llm_client: LLMClient,
    taxonomy: TagTaxonomy = None,
    content_id: str | None = None,
) -> tuple[TagAssignment, list[LLMUsage]]:
    """
    Assign tags from controlled vocabulary.

    Args:
        content_title: Title of the content
        analysis: Content analysis result
        summary: Generated summary (standard level preferred)
        llm_client: LLM client for completion
        taxonomy: Optional pre-loaded taxonomy (loads from config if not provided)

    Returns:
        Tuple of (TagAssignment with validated tags, list of LLMUsage)
    """
    # Load taxonomy from source of truth if not provided
    if taxonomy is None:
        taxonomy = await get_tag_taxonomy()

    # Format domain tags for prompt (limit to avoid token overflow)
    max_tags = processing_settings.TAGGING_MAX_DOMAIN_TAGS
    domain_tags_str = ", ".join(taxonomy.domains[:max_tags])
    if len(taxonomy.domains) > max_tags:
        domain_tags_str += f", ... ({len(taxonomy.domains) - max_tags} more)"

    meta_tags_str = ", ".join(taxonomy.meta)

    # Truncate inputs per configured limits
    max_topics = processing_settings.TAGGING_MAX_KEY_TOPICS
    max_summary = processing_settings.TAGGING_SUMMARY_TRUNCATE

    prompt = TAGGING_PROMPT.format(
        title=content_title,
        content_type=analysis.content_type,
        domain=analysis.domain,
        complexity=analysis.complexity,
        key_topics=", ".join(analysis.key_topics[:max_topics]),
        summary=summary[:max_summary] if summary else "No summary available",
        domain_tags=domain_tags_str,
        meta_tags=meta_tags_str,
    )

    try:
        data, usage = await llm_client.complete(
            operation=PipelineOperation.TAG_ASSIGNMENT,
            messages=[{"role": "user", "content": prompt}],
            temperature=processing_settings.TAGGING_TEMPERATURE,
            max_tokens=processing_settings.TAGGING_MAX_TOKENS,
            json_mode=True,
            content_id=content_id,
        )

        # Extract and validate tags
        suggested_domains = data.get("domain_tags", [])
        suggested_meta = data.get("meta_tags", [])

        # Filter to only valid tags
        valid_domain_tags = [
            t for t in suggested_domains if taxonomy.validate_domain_tag(t)
        ]
        valid_meta_tags = [t for t in suggested_meta if taxonomy.validate_meta_tag(t)]

        # Track invalid suggestions for potential new tags
        invalid_domains = [t for t in suggested_domains if t not in valid_domain_tags]
        invalid_meta = [t for t in suggested_meta if t not in valid_meta_tags]

        if invalid_domains:
            logger.info(f"LLM suggested invalid domain tags: {invalid_domains}")
        if invalid_meta:
            logger.info(f"LLM suggested invalid meta tags: {invalid_meta}")

        # Combine explicit suggestions with invalid tags as new tag suggestions
        new_tag_suggestions = (
            data.get("suggested_new_tags", []) + invalid_domains + invalid_meta
        )

        result = TagAssignment(
            domain_tags=valid_domain_tags,
            meta_tags=valid_meta_tags,
            suggested_new_tags=list(set(new_tag_suggestions)),  # Deduplicate
            reasoning=data.get("reasoning", ""),
        )
        return result, [usage]

    except Exception as e:
        logger.error(f"Tag assignment failed: {e}")
        return TagAssignment(meta_tags=["status/review"]), []
