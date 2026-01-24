"""
Follow-up Task Generation Stage

Generates actionable follow-up tasks based on content and reader highlights.
Tasks transform passive reading into active learning by providing specific
next steps.

Task Types:
- RESEARCH: "Look up X to understand Y better"
- PRACTICE: "Try implementing X"
- CONNECT: "Explore how this relates to Z"
- APPLY: "Use this on project W"
- REVIEW: "Revisit X after applying this"

Usage:
    from app.services.processing.stages.followups import generate_followups

    tasks, usages = await generate_followups(content, analysis, summary, extraction, llm_client)
    for task in tasks:
        print(f"[{task.priority}] {task.task} ({task.estimated_time})")
"""

import logging

from app.models.content import UnifiedContent
from app.models.processing import FollowupTask, ContentAnalysis, ExtractionResult
from app.enums import (
    PipelineOperation,
    FollowupTaskType,
    FollowupPriority,
    FollowupTimeEstimate,
)
from app.models.llm_usage import LLMUsage
from app.services.llm.client import LLMClient
from app.config.processing import processing_settings

logger = logging.getLogger(__name__)

# Build prompt sections from enums
_task_types_section = "\n".join(
    f"- {t.value}: {desc}"
    for t, desc in [
        (
            FollowupTaskType.RESEARCH,
            '"Look up X to understand Y better" or "Read the original paper on Z"',
        ),
        (
            FollowupTaskType.PRACTICE,
            '"Try implementing X" or "Build a small project using Y"',
        ),
        (
            FollowupTaskType.CONNECT,
            '"Explore how this relates to Z" or "Compare with approach W"',
        ),
        (
            FollowupTaskType.APPLY,
            '"Use this technique on project W" or "Try this method at work"',
        ),
        (
            FollowupTaskType.REVIEW,
            '"Revisit X after applying this" or "Re-read after practicing"',
        ),
    ]
)

_priority_section = "\n".join(
    f"- {p.value}: {desc}"
    for p, desc in [
        (FollowupPriority.HIGH, "Fundamental to understanding, should do soon"),
        (FollowupPriority.MEDIUM, "Would deepen understanding"),
        (FollowupPriority.LOW, "Nice to have, optional enrichment"),
    ]
)

FOLLOWUP_PROMPT_TEMPLATE = """Generate actionable follow-up tasks based on this content.

Content:
- Title: {title}
- Type: {content_type}
- Domain: {domain}

Summary: {summary}

Key Concepts: {concepts}

Reader's Highlights (what they found important):
{annotations}

Generate {min_tasks}-{max_tasks} follow-up tasks that are:
1. **Actionable**: Can be completed in a single session
2. **Specific**: Clear what needs to be done, not vague
3. **Deepening**: Go beyond surface understanding
4. **Connected**: Relate to other knowledge areas when possible

**IMPORTANT for Research Articles/Papers:**
If the reader highlighted any citations or references (e.g., "[Smith et al., 2023]", "as shown by Johnson (2022)", 
or any academic citation format), create HIGH priority RESEARCH tasks to read those referenced papers.
Format these as: "Read '[Paper Title]' by [Authors] to understand [specific concept from the highlight context]"

**IMPORTANT: Generate MORE tasks for content with more highlights!**
- Each highlighted citation should become a RESEARCH task
- Key concepts should become PRACTICE or CONNECT tasks
- Aim for comprehensive coverage of the reader's interests

Task Types:
""" + _task_types_section + """

Priority Guidelines:
""" + _priority_section + """

Return as JSON:
{{
  "tasks": [
    {{
      "task": "Specific, actionable task description",
      "type": """ + '"{}"'.format("|".join(t.value for t in FollowupTaskType)) + """,
      "priority": """ + '"{}"'.format("|".join(p.value for p in FollowupPriority)) + """,
      "estimated_time": """ + '"{}"'.format("|".join(t.value for t in FollowupTimeEstimate)) + """
    }}
  ]
}}

Make tasks specific to THIS content, not generic learning advice.
For highlighted references/citations, always include them as RESEARCH tasks with HIGH priority.
"""


def _calculate_task_range(annotation_count: int, concept_count: int) -> tuple[int, int]:
    """
    Calculate the min/max number of tasks to generate based on content richness.
    
    More annotations and concepts = more potential follow-up tasks.
    
    Uses settings from processing_settings for all thresholds and limits.
    """
    settings = processing_settings
    
    # Base tasks for minimal content
    base_min = settings.FOLLOWUP_BASE_MIN_TASKS
    base_max = settings.FOLLOWUP_BASE_MAX_TASKS
    
    # Add tasks for annotations (capped contribution)
    annotation_bonus = min(
        annotation_count // settings.FOLLOWUP_ANNOTATIONS_PER_BONUS,
        settings.FOLLOWUP_MAX_ANNOTATION_BONUS
    )
    
    # Add tasks for concepts
    concept_bonus = min(
        concept_count // settings.FOLLOWUP_CONCEPTS_PER_BONUS,
        settings.FOLLOWUP_MAX_CONCEPT_BONUS
    )
    
    # Calculate min/max with conservative min scaling
    min_tasks = base_min + (annotation_bonus // 2)
    max_tasks = base_max + annotation_bonus + concept_bonus
    
    # Cap at configured limits
    min_tasks = max(
        settings.FOLLOWUP_MIN_TASKS_FLOOR,
        min(min_tasks, settings.FOLLOWUP_MIN_TASKS_CEILING)
    )
    max_tasks = max(
        min_tasks + 2,
        min(max_tasks, settings.FOLLOWUP_MAX_TASKS_CEILING)
    )
    
    return min_tasks, max_tasks


async def generate_followups(
    content: UnifiedContent,
    analysis: ContentAnalysis,
    summary: str,
    extraction: ExtractionResult,
    llm_client: LLMClient,
) -> tuple[list[FollowupTask], list[LLMUsage]]:
    """
    Generate follow-up tasks for deeper engagement.

    Args:
        content: Unified content from ingestion
        analysis: Content analysis result
        summary: Generated summary
        extraction: Extracted concepts and findings
        llm_client: LLM client for completion

    Returns:
        Tuple of (list of FollowupTask objects, list of LLMUsage)
    """
    # Format annotations - use higher limit for richer content
    annotation_count = len(content.annotations) if content.annotations else 0
    concept_count = len(extraction.concepts) if extraction.concepts else 0
    
    # Dynamic limit: include more annotations for content-rich documents
    max_annotations = min(
        max(processing_settings.FOLLOWUP_MAX_ANNOTATIONS, annotation_count // processing_settings.FOLLOWUP_CONCEPTS_PER_BONUS),
        processing_settings.FOLLOWUP_ANNOTATIONS_HARD_CAP
    )
    annotations_text = _format_annotations(content, max_annotations)
    logger.info(f"Follow-up generation: {annotation_count} annotations, using {max_annotations} in prompt")

    # Format concepts
    concepts_text = (
        ", ".join(
            [
                c.name
                for c in extraction.concepts[
                    : processing_settings.FOLLOWUP_MAX_CONCEPTS
                ]
            ]
        )
        if extraction.concepts
        else "None extracted"
    )

    # Calculate dynamic task range based on content richness
    min_tasks, max_tasks = _calculate_task_range(annotation_count, concept_count)
    logger.info(f"Follow-up task range: {min_tasks}-{max_tasks} tasks (based on {annotation_count} annotations, {concept_count} concepts)")

    prompt = FOLLOWUP_PROMPT_TEMPLATE.format(
        title=content.title,
        content_type=analysis.content_type,
        domain=analysis.domain,
        summary=(
            summary[: processing_settings.FOLLOWUP_SUMMARY_TRUNCATE] if summary else ""
        ),
        concepts=concepts_text,
        annotations=annotations_text,
        min_tasks=min_tasks,
        max_tasks=max_tasks,
    )

    try:
        data, usage = await llm_client.complete(
            operation=PipelineOperation.FOLLOWUP_GENERATION,
            messages=[{"role": "user", "content": prompt}],
            temperature=processing_settings.FOLLOWUP_TEMPERATURE,
            max_tokens=processing_settings.FOLLOWUP_MAX_TOKENS,
            json_mode=True,
            content_id=content.id,
        )
        
        logger.info(f"Follow-up LLM response: {data}")

        tasks = []
        for t in data.get("tasks", []):
            if t.get("task"):  # Skip empty tasks
                tasks.append(
                    FollowupTask(
                        task=t.get("task", ""),
                        task_type=_validate_task_type(
                            t.get("type", FollowupTaskType.RESEARCH.value)
                        ),
                        priority=_validate_priority(
                            t.get("priority", FollowupPriority.MEDIUM.value)
                        ),
                        estimated_time=_validate_time(
                            t.get(
                                "estimated_time", FollowupTimeEstimate.THIRTY_MIN.value
                            )
                        ),
                    )
                )

        logger.debug(f"Generated {len(tasks)} follow-up tasks")
        return tasks, [usage]

    except Exception as e:
        logger.error(f"Follow-up generation failed: {e}")
        return [], []


def _format_annotations(content: UnifiedContent, max_annotations: int = None) -> str:
    """Format annotations for inclusion in prompt.
    
    Args:
        content: Content with annotations
        max_annotations: Maximum annotations to include (defaults to settings value)
    """
    if not content.annotations:
        return "None provided"

    limit = max_annotations or processing_settings.FOLLOWUP_MAX_ANNOTATIONS
    
    formatted = []
    for annotation in content.annotations[:limit]:
        text = annotation.content[: processing_settings.FOLLOWUP_ANNOTATION_TRUNCATE]
        formatted.append(f"- {text}")

    return "\n".join(formatted)


def _validate_task_type(task_type: str) -> str:
    """Validate and normalize task type."""
    task_type = task_type.upper().strip()
    valid_types = [t.value for t in FollowupTaskType]
    if task_type in valid_types:
        return task_type
    return FollowupTaskType.RESEARCH.value


def _validate_priority(priority: str) -> str:
    """Validate and normalize priority."""
    priority = priority.upper().strip()
    valid_priorities = [p.value for p in FollowupPriority]
    if priority in valid_priorities:
        return priority
    return FollowupPriority.MEDIUM.value


def _validate_time(time: str) -> str:
    """Validate and normalize time estimate."""
    # Handle common LLM output formats
    time = time.upper().strip().replace("+", "_PLUS")
    valid_times = [t.value for t in FollowupTimeEstimate]
    if time in valid_times:
        return time
    return FollowupTimeEstimate.THIRTY_MIN.value
