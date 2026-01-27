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
import re
from datetime import datetime, timezone
from typing import Any, Optional, TypedDict

from jinja2 import Environment, FileSystemLoader, TemplateNotFound

from app.config.settings import TEMPLATES_DIR
from app.enums.content import AnnotationType
from app.enums.processing import ConceptImportance, SummaryLevel
from app.models.content import UnifiedContent
from app.models.processing import Concept, ProcessingResult
from app.services.obsidian.vault import get_vault_manager

logger = logging.getLogger(__name__)


class TemplateData(TypedDict, total=False):
    """
    Data structure passed to Jinja2 templates for note generation.

    Different templates may use different subsets of these variables.
    All fields are optional (total=False) since templates vary by content type.
    """

    # Basic metadata
    content_type: str
    title: str
    content_id: str
    authors: list[str]
    author: str
    tags: list[str]
    domain: str
    complexity: str
    status: str
    # Dates
    created_date: str
    processed_date: str
    # Source info
    source_url: str
    source_path: str
    # Summaries
    summary: str
    summary_brief: str
    overview: str
    detailed_notes: str
    # Key findings/takeaways
    key_findings: list[str]
    takeaways: list[str]
    # Concepts (list of dicts with name, definition, importance)
    concepts: list[dict[str, Any]]
    # Annotations
    highlights: list[dict[str, Any]]
    handwritten_notes: list[dict[str, Any]]
    has_handwritten_notes: bool
    # Interactive elements
    mastery_questions: list[dict[str, Any]]
    tasks: list[dict[str, Any]]
    action_items: list[str]
    # Connections
    connections: list[dict[str, Any]]
    related: list[str]
    # Idea-specific variables
    idea: str
    context: str
    importance: str
    next_steps: list[str]

# UUID pattern to detect UUID-like titles
UUID_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.IGNORECASE
)


def _get_best_title(content: UnifiedContent, result: ProcessingResult) -> str:
    """
    Get the best title to use for the note filename.

    Priority:
    1. Original filename from metadata (if stored)
    2. Content title (if not a UUID)
    3. First line of summary that looks like a title
    4. First key topic from analysis
    5. Fallback to content ID

    Args:
        content: Original unified content
        result: Processing result with analysis and summaries

    Returns:
        Best available title for the note
    """
    # Check if content.title looks like a UUID
    title = content.title
    is_uuid_title = bool(UUID_PATTERN.match(title))

    if not is_uuid_title and title and title != "Untitled PDF":
        return title

    # Try to get original filename from metadata
    original_filename = content.metadata.get("original_filename") if content.metadata else None
    if original_filename:
        # Clean up: remove .pdf extension
        if original_filename.lower().endswith(".pdf"):
            original_filename = original_filename[:-4]
        original_filename = original_filename.replace("_", " ").strip()
        if original_filename and not UUID_PATTERN.match(original_filename):
            return original_filename

    # Try to extract title from summary (look for "Title:" or first heading)
    standard_summary = result.summaries.get(SummaryLevel.STANDARD.value, "")
    if standard_summary:
        # Look for patterns like "### Summary: Paper Title" or "**Paper Title**"
        title_patterns = [
            r"###\s*Summary[:\s]+(.+?)(?:\n|$)",  # ### Summary: Title
            r"\*\*(.+?)\*\*",  # **Bold title**
        ]
        for pattern in title_patterns:
            match = re.search(pattern, standard_summary)
            if match:
                extracted = match.group(1).strip()
                # Only use if it's reasonable length and not generic
                if 10 < len(extracted) < 200 and not extracted.lower().startswith("the problem"):
                    return extracted

    # Try first key topic from analysis
    if result.analysis.key_topics:
        first_topic = result.analysis.key_topics[0]
        if len(first_topic) > 10:
            return first_topic.title()

    # Fallback to content ID
    return content.id


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


def _extract_code_template_data(content: UnifiedContent) -> dict[str, Any]:
    """
    Extract CODE-specific template variables from GitHub repo analysis.

    Parses the structured LLM analysis in full_text to extract sections like
    Purpose, Architecture, Tech Stack, and Key Learnings. Also extracts
    metadata like stars, language from content.metadata.

    Args:
        content: UnifiedContent with GitHub repo analysis in full_text

    Returns:
        Dict with code.md.j2 template variables:
        - url, language, stars (from metadata)
        - purpose, architecture, tech_stack, learnings, ideas (from full_text)
    """
    metadata = content.metadata or {}
    full_text = content.full_text or ""

    # Helper to extract a section from markdown
    def extract_section(text: str, section_patterns: list[str]) -> str:
        """Extract content between a section header and the next section."""
        for pattern in section_patterns:
            match = re.search(
                pattern + r"[:\s]*\n(.*?)(?=\n(?:###|\d+\.\s*\*\*|\*\*\d+\.)|$)",
                text,
                re.DOTALL | re.IGNORECASE
            )
            if match:
                return match.group(1).strip()
        return ""

    # Helper to extract list items from a section
    def extract_list_items(text: str, section_patterns: list[str]) -> list[str]:
        """Extract bullet points or numbered items from a section."""
        section = extract_section(text, section_patterns)
        if not section:
            return []
        
        items = []
        # Match numbered items (1., 2.) or bullet points (-, *)
        for match in re.finditer(r"(?:^|\n)\s*(?:\d+\.|\-|\*)\s*(.+?)(?=\n|$)", section):
            item = match.group(1).strip()
            # Remove markdown formatting like **bold**
            item = re.sub(r"\*\*(.+?)\*\*", r"\1", item)
            if item:
                items.append(item)
        
        return items

    # Extract purpose
    purpose = extract_section(full_text, [
        r"\*\*Purpose\*\*",
        r"### 1\. Purpose",
        r"## Purpose",
        r"1\.\s*\*\*Purpose\*\*",
    ])

    # Extract architecture
    architecture = extract_section(full_text, [
        r"\*\*Architecture Overview\*\*",
        r"### 2\. Architecture",
        r"## Architecture Overview",
        r"2\.\s*\*\*Architecture Overview\*\*",
    ])

    # Extract tech stack as structured data
    tech_stack_section = extract_section(full_text, [
        r"\*\*Tech Stack\*\*",
        r"### 3\. Tech Stack",
        r"## Tech Stack",
        r"3\.\s*\*\*Tech Stack\*\*",
    ])
    tech_stack = {
        "language": metadata.get("language", ""),
        "framework": "",
        "dependencies": "",
    }
    # Try to parse framework/dependencies from tech stack section
    if tech_stack_section:
        # Look for patterns like "Framework: X" or "- Framework: X"
        framework_match = re.search(r"[Ff]ramework[s]?[:\s]+([^\n,]+)", tech_stack_section)
        if framework_match:
            tech_stack["framework"] = framework_match.group(1).strip()
        
        deps_match = re.search(r"[Dd]ependenc(?:y|ies)[:\s]+([^\n]+)", tech_stack_section)
        if deps_match:
            tech_stack["dependencies"] = deps_match.group(1).strip()

    # Extract key learnings as list
    learnings = extract_list_items(full_text, [
        r"\*\*Key Learnings\*\*",
        r"### 4\. Key Learnings",
        r"## Key Learnings",
        r"4\.\s*\*\*Key Learnings\*\*",
    ])

    # Extract notable features as ideas
    ideas = extract_list_items(full_text, [
        r"\*\*Notable Features\*\*",
        r"### 5\. Notable Features",
        r"## Notable Features",
        r"5\.\s*\*\*Notable Features\*\*",
    ])

    # Extract patterns from architecture section (look for pattern mentions)
    patterns = []
    if architecture:
        # Look for "pattern" mentions
        pattern_matches = re.findall(r"(?:\*\*)?([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+[Pp]attern)(?:\*\*)?", architecture)
        for p in pattern_matches[:5]:  # Limit to 5
            patterns.append({"name": p, "description": ""})

    return {
        "url": content.source_url or "",
        "language": metadata.get("language", ""),
        "stars": metadata.get("stars", ""),
        "purpose": purpose,
        "why_saved": "",  # User can fill this in
        "architecture": architecture,
        "tech_stack": tech_stack,
        "patterns": patterns,
        "learnings": learnings,
        "ideas": ideas,
    }


def _prepare_template_data(content: UnifiedContent, result: ProcessingResult) -> TemplateData:
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

    logger.debug(f"Processing {len(content.annotations)} annotations for '{content.title}'")
    
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
    
    logger.info(f"Found {len(highlights)} highlights and {len(handwritten_notes)} handwritten notes")

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

    now = datetime.now(timezone.utc)

    # Get standard summary for idea/context
    standard_summary = result.summaries.get(SummaryLevel.STANDARD.value, "")

    # Get the best title (handles UUID titles)
    best_title = _get_best_title(content, result)

    # Get source path from metadata if available
    source_path = ""
    if content.metadata:
        source_path = content.metadata.get("source_path", "") or content.metadata.get("file_path", "")
    
    # Build base template data (common to all content types)
    data: dict[str, Any] = {
        # Basic metadata
        "content_type": result.analysis.content_type,
        "title": _escape_yaml_string(best_title),
        "content_id": content.id,
        "authors": content.authors or [],
        "author": content.authors[0] if content.authors else "",
        "tags": result.tags.domain_tags + result.tags.meta_tags,
        "domain": result.analysis.domain,
        "complexity": result.analysis.complexity,
        "status": "processed",
        # Dates
        "created_date": now.strftime("%Y-%m-%d"),
        "processed_date": now.strftime("%Y-%m-%d"),
        # Source info
        "source_url": content.source_url or "",
        "source_path": source_path,
        # Summaries
        "summary": standard_summary,
        "summary_brief": result.summaries.get(SummaryLevel.BRIEF.value, ""),
        "overview": standard_summary,
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
        # Idea-specific variables (used by idea.md.j2 template)
        "idea": content.full_text or standard_summary,
        "context": (
            result.analysis.context if hasattr(result.analysis, "context") else ""
        ),
        "importance": (
            result.analysis.importance if hasattr(result.analysis, "importance") else ""
        ),
        "next_steps": [t["task"] for t in tasks],
    }

    # Add CODE-specific variables for code.md.j2 template
    # These are extracted from the GitHubImporter's structured LLM analysis
    if result.analysis.content_type == "code":
        code_data = _extract_code_template_data(content)
        data.update(code_data)
        # Override 'related' with connections if we have them, otherwise keep code_data's empty list
        if connections:
            data["related"] = [c["note"] for c in connections]

    return data


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

    Cleanup on Reprocessing:
        If content.obsidian_path is set (from previous processing) and the new
        note would have a different filename (due to title change), the old file
        is deleted to prevent orphaned duplicate notes.

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

        # Get the best title to use for the filename
        note_title = _get_best_title(content, result)
        logger.debug(f"Using title for note: {note_title}")

        # Check if content already has an existing obsidian note (from previous processing)
        # If so, and the filename would change, delete the old file to prevent duplicates
        old_note_path = None
        if content.obsidian_path:
            old_note_path = vault.vault_path / content.obsidian_path
            # Compute what the new filename would be
            new_filename = vault.sanitize_filename(note_title)
            old_filename = old_note_path.stem
            # Strip any _N suffix from old filename for comparison
            old_filename_base = re.sub(r"_\d+$", "", old_filename)

            if old_filename_base != new_filename and old_note_path.exists():
                try:
                    old_note_path.unlink()
                    logger.info(
                        f"Deleted old note on reprocessing (title changed): {old_note_path}"
                    )
                except Exception as e:
                    logger.warning(f"Failed to delete old note {old_note_path}: {e}")

        # Get path for update (reuses existing note) or create new
        # This prevents creating duplicates like "Paper_1.md", "Paper_2.md" on reprocessing
        output_path = vault.get_path_for_update(
            output_dir, note_title, existing_path=content.obsidian_path
        )

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


async def generate_concept_note(
    concept: Concept,
    source_content: UnifiedContent,
    result: ProcessingResult,
) -> Optional[str]:
    """
    Generate an Obsidian-compatible markdown note for a concept.

    Creates atomic concept notes that link back to their source content
    and to related concepts. These notes enable Zettelkasten-style knowledge
    management where concepts are first-class citizens.

    Args:
        concept: The extracted concept with all its rich data
        source_content: The content this concept was extracted from
        result: Processing result for context (tags, domain, etc.)

    Returns:
        Path to created note (relative to vault), or None if failed
    """
    try:
        vault = get_vault_manager()
        env = _get_template_env()

        template_name = _get_template_name("concept")
        try:
            template = env.get_template(template_name)
            logger.debug(f"Using template: {template_name}")
        except TemplateNotFound:
            raise FileNotFoundError(
                f"No template found for concept notes. "
                f"Expected: config/templates/{template_name}"
            )

        now = datetime.now(timezone.utc)

        # Format examples for template (list of dicts with title/content)
        examples = [
            {"title": ex.title or f"Example {i+1}", "content": ex.content}
            for i, ex in enumerate(concept.examples)
        ]

        # Format misconceptions for template (list of dicts with wrong/correct)
        misconceptions = [
            {"wrong": mis.wrong, "correct": mis.correct}
            for mis in concept.misconceptions
        ]

        # Format related concepts for template (list of dicts with name/relationship)
        related_concepts = [
            {"name": rel.name, "relationship": rel.relationship}
            for rel in concept.related_concepts
        ]

        # Use why_it_matters from concept, or generate a contextual one
        importance_text = concept.why_it_matters
        if not importance_text:
            importance_text = (
                f"This concept is central to understanding {source_content.title}."
            )

        # Prepare template data with all rich concept fields
        data = {
            "title": _escape_yaml_string(concept.name),
            "domain": result.analysis.domain or "",
            "complexity": result.analysis.complexity or "foundational",
            "tags": result.tags.domain_tags + ["concept"],
            "created_date": now.strftime("%Y-%m-%d"),
            "definition": concept.definition,
            "importance": importance_text,
            "properties": concept.properties,
            "examples": examples,
            "misconceptions": misconceptions,
            "prerequisites": concept.prerequisites,
            "related_concepts": related_concepts,
            "sources": [source_content.title],
        }

        # Render the note
        note_content = template.render(**data)

        # Get concepts folder and write note
        concept_folder = vault.get_concept_folder()
        output_path = await vault.get_unique_path(concept_folder, concept.name)
        await vault.write_note(output_path, note_content)

        # Return relative path from vault root
        relative_path = output_path.relative_to(vault.vault_path)
        logger.info(f"Generated concept note: {output_path}")
        return str(relative_path)

    except Exception as e:
        logger.error(f"Failed to generate concept note for '{concept.name}': {e}")
        return None


async def generate_concept_notes_for_content(
    content: UnifiedContent,
    result: ProcessingResult,
    importance_filter: ConceptImportance = ConceptImportance.CORE,
) -> list[dict]:
    """
    Generate Obsidian notes for all concepts extracted from content.

    Creates individual markdown notes for each concept and returns
    info needed to update their Neo4j nodes with file paths.

    Args:
        content: Source content the concepts were extracted from
        result: Processing result containing extracted concepts
        importance_filter: Only create notes for concepts at this importance level
                          or higher. CORE = core only, SUPPORTING = core + supporting,
                          TANGENTIAL = all concepts

    Returns:
        List of dicts with concept info:
            - name: Concept name
            - id: Concept ID
            - file_path: Path to created note (relative to vault)
    """
    created_concepts = []

    # Filter concepts by importance
    if importance_filter == ConceptImportance.CORE:
        concepts = [
            c
            for c in result.extraction.concepts
            if c.importance == ConceptImportance.CORE.value
        ]
    elif importance_filter == ConceptImportance.SUPPORTING:
        concepts = [
            c
            for c in result.extraction.concepts
            if c.importance
            in (ConceptImportance.CORE.value, ConceptImportance.SUPPORTING.value)
        ]
    else:  # TANGENTIAL = all concepts
        concepts = result.extraction.concepts

    if not concepts:
        logger.debug(
            f"No concepts to generate notes for (filter: {importance_filter.value})"
        )
        return created_concepts

    for concept in concepts:
        # Pass the full concept object with all its rich data
        # The concept already contains related_concepts with relationship types
        file_path = await generate_concept_note(
            concept=concept,
            source_content=content,
            result=result,
        )

        if file_path:
            created_concepts.append(
                {
                    "name": concept.name,
                    "id": concept.id,
                    "file_path": file_path,
                }
            )

    logger.info(
        f"Generated {len(created_concepts)} concept notes for '{content.title}'"
    )
    return created_concepts
