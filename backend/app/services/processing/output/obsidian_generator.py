"""
Obsidian Note Generator

Generates Obsidian-compatible markdown notes from processing results.
Uses content-type-specific Jinja2 templates from config/templates/.

Integrates with VaultManager for:
- Path resolution (get_source_folder)
- Filename sanitization (sanitize_filename)
- Unique path generation (get_unique_path)
- File writing (write_note)

Required templates (must exist for each content type):
- config/templates/paper.md.j2
- config/templates/article.md.j2
- config/templates/book.md.j2
- config/templates/code.md.j2
- config/templates/idea.md.j2
- config/templates/voice_memo.md.j2 (if voice memo content type is used)

Raises FileNotFoundError if template directory or specific template is missing.

Usage:
    from app.services.processing.output.obsidian_generator import generate_obsidian_note

    path = await generate_obsidian_note(content, result)
    print(f"Note created at: {path}")
"""

import logging
from datetime import datetime
from typing import Optional

from jinja2 import Environment, FileSystemLoader, TemplateNotFound

from app.config.settings import TEMPLATES_DIR
from app.enums.content import AnnotationType
from app.enums.processing import SummaryLevel
from app.models.content import UnifiedContent
from app.models.processing import ProcessingResult
from app.services.obsidian.vault import get_vault_manager

logger = logging.getLogger(__name__)


def _get_template_env() -> Environment:
    """
    Get Jinja2 environment with template directory.

    Templates are loaded from config/templates/ (TEMPLATES_DIR from settings).

    Raises:
        FileNotFoundError: If template directory does not exist
    """
    if not TEMPLATES_DIR.exists():
        raise FileNotFoundError(
            f"Template directory not found: {TEMPLATES_DIR}. "
            "Ensure config/templates/ exists with .j2 templates."
        )

    logger.debug(f"Loading templates from: {TEMPLATES_DIR}")
    return Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=False,  # Markdown doesn't need HTML escaping
    )


def _get_template_name(content_type: str) -> str:
    """
    Map content type to template filename.

    Args:
        content_type: Content type from analysis (paper, article, book, etc.)

    Returns:
        Template filename like "paper.md.j2"
    """
    return f"{content_type}.md.j2"


def _prepare_template_data(content: UnifiedContent, result: ProcessingResult) -> dict:
    """
    Prepare data dict for template rendering.

    Maps ProcessingResult fields to template variable names.
    Different templates may use different subsets of these variables.

    Args:
        content: Original unified content
        result: Processing result with all stages

    Returns:
        Dict of template variables
    """
    # Parse annotations into highlights and handwritten notes
    highlights = []
    handwritten_notes = []

    if content.annotations:
        for a in content.annotations:
            if a.type == AnnotationType.DIGITAL_HIGHLIGHT:
                highlights.append(
                    {
                        "text": a.content,
                        "page": a.page_number,
                    }
                )
            elif a.type == AnnotationType.HANDWRITTEN_NOTE:
                handwritten_notes.append(
                    {
                        "text": a.content,
                        "page": a.page_number,
                        "context": a.context,
                    }
                )

    # Format concepts
    concepts = []
    for c in result.extraction.concepts:
        concepts.append(
            {
                "name": c.name,
                "definition": c.definition,
                "importance": c.importance,
            }
        )

    # Format connections
    connections = []
    for c in result.connections:
        connections.append(
            {
                "note": c.target_title,
                "relationship": c.explanation,
                "type": c.relationship_type,
                "strength": c.strength,
            }
        )

    # Format mastery questions
    mastery_questions = []
    for q in result.mastery_questions:
        mastery_questions.append(
            {
                "question": q.question,
                "type": q.question_type,
                "difficulty": q.difficulty,
                "hints": q.hints,
                "key_points": q.key_points,
            }
        )

    # Format tasks/followups
    tasks = []
    for f in result.followups:
        tasks.append(
            {
                "task": f.task,
                "task_type": f.task_type,
                "priority": f.priority,
                "estimated_time": f.estimated_time,
            }
        )

    now = datetime.now()

    return {
        # Basic metadata
        "content_type": result.analysis.content_type,
        "title": _escape_yaml_string(content.title),
        "authors": content.authors or [],
        "author": content.authors[0] if content.authors else "",
        "tags": result.tags.domain_tags + result.tags.meta_tags,
        "domain": result.analysis.domain,
        "complexity": result.analysis.complexity,
        "status": "processed",
        # Dates
        "created_date": now.strftime("%Y-%m-%d"),
        "processed_date": now.strftime("%Y-%m-%d"),
        # Source info (for articles)
        "source_url": content.source_url or "",
        # Summaries
        "summary": result.summaries.get(SummaryLevel.STANDARD.value, ""),
        "summary_brief": result.summaries.get(SummaryLevel.BRIEF.value, ""),
        "overview": result.summaries.get(SummaryLevel.STANDARD.value, ""),
        "detailed_notes": result.summaries.get(SummaryLevel.DETAILED.value, ""),
        # Key findings/takeaways
        "key_findings": result.extraction.key_findings,
        "takeaways": result.extraction.key_findings,
        # Concepts
        "concepts": concepts,
        # Annotations
        "highlights": highlights,
        "handwritten_notes": handwritten_notes,
        "has_handwritten_notes": len(handwritten_notes) > 0,
        # Interactive elements
        "mastery_questions": mastery_questions,
        "tasks": tasks,
        "action_items": [t["task"] for t in tasks],
        # Connections
        "connections": connections,
        "related": [c["note"] for c in connections],
    }


async def generate_obsidian_note(
    content: UnifiedContent, result: ProcessingResult
) -> Optional[str]:
    """
    Generate an Obsidian-compatible markdown note.

    Uses content-type-specific Jinja2 templates from config/templates/.
    Each content type (paper, article, book, etc.) must have a corresponding
    template file like paper.md.j2, article.md.j2, etc.

    Integrates with VaultManager for:
    - Folder resolution via get_source_folder()
    - Unique path generation via get_unique_path()
    - File writing via write_note()

    Creates a well-formatted note with:
    - YAML frontmatter (type, title, tags, etc.)
    - Multi-level summaries
    - Key findings and concepts
    - Highlights from annotations
    - Mastery questions as checkboxes
    - Follow-up tasks
    - Wiki-links for connections

    Args:
        content: Original unified content
        result: Processing result with all stages

    Returns:
        Path to created note, or None if failed
    """
    try:
        # Get vault manager for path operations
        vault = get_vault_manager()

        # Get Jinja2 environment
        env = _get_template_env()

        # Load content-type-specific template
        template_name = _get_template_name(result.analysis.content_type)
        try:
            template = env.get_template(template_name)
            logger.debug(f"Using template: {template_name}")
        except TemplateNotFound:
            raise FileNotFoundError(
                f"No template found for content type '{result.analysis.content_type}'. "
                f"Expected: config/templates/{template_name}"
            )

        # Prepare template data
        data = _prepare_template_data(content, result)

        # Render the note
        note_content = template.render(**data)

        # Get output folder via VaultManager (uses ContentTypeRegistry)
        content_type = result.analysis.content_type
        output_dir = vault.get_source_folder(content_type)

        # Get unique path (handles duplicates automatically)
        output_path = await vault.get_unique_path(output_dir, content.title)

        # Write the note via VaultManager
        await vault.write_note(output_path, note_content)

        # Return relative path from vault root (what the API expects)
        relative_path = output_path.relative_to(vault.vault_path)
        
        logger.info(f"Generated Obsidian note: {output_path}")
        return str(relative_path)

    except Exception as e:
        logger.error(f"Failed to generate Obsidian note: {e}")
        return None


def _escape_yaml_string(s: str) -> str:
    """Escape a string for YAML frontmatter."""
    if not s:
        return ""
    # Escape quotes and ensure it's valid YAML
    return s.replace('"', '\\"').replace("\n", " ")
