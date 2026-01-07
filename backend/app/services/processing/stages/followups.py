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

FOLLOWUP_PROMPT = f"""Generate actionable follow-up tasks based on this content.

Content:
- Title: {{title}}
- Type: {{content_type}}
- Domain: {{domain}}

Summary: {{summary}}

Key Concepts: {{concepts}}

Reader's Highlights (what they found important):
{{annotations}}

Generate 3-5 follow-up tasks that are:
1. **Actionable**: Can be completed in a single session
2. **Specific**: Clear what needs to be done, not vague
3. **Deepening**: Go beyond surface understanding
4. **Connected**: Relate to other knowledge areas when possible

Task Types:
{_task_types_section}

Priority Guidelines:
{_priority_section}

Return as JSON:
{{{{
  "tasks": [
    {{{{
      "task": "Specific, actionable task description",
      "type": "{"|".join(t.value for t in FollowupTaskType)}",
      "priority": "{"|".join(p.value for p in FollowupPriority)}",
      "estimated_time": "{"|".join(t.value for t in FollowupTimeEstimate)}"
    }}}}
  ]
}}}}

Make tasks specific to THIS content, not generic learning advice.
"""


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
    # Format annotations
    annotations_text = _format_annotations(content)

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

    prompt = FOLLOWUP_PROMPT.format(
        title=content.title,
        content_type=analysis.content_type,
        domain=analysis.domain,
        summary=(
            summary[: processing_settings.FOLLOWUP_SUMMARY_TRUNCATE] if summary else ""
        ),
        concepts=concepts_text,
        annotations=annotations_text,
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


def _format_annotations(content: UnifiedContent) -> str:
    """Format annotations for inclusion in prompt."""
    if not content.annotations:
        return "None provided"

    formatted = []
    for annotation in content.annotations[
        : processing_settings.FOLLOWUP_MAX_ANNOTATIONS
    ]:
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
