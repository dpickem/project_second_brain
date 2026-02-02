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
# These prompts are designed to extract maximum detail at each summary level
SUMMARY_PROMPTS = {
    "paper": """Summarize this academic paper at {level} level.

Paper Title: {title}
Authors: {authors}

Paper content:
{content}

Annotations/highlights from the reader (these indicate what they found important):
{annotations}

Summary levels and requirements:

**BRIEF**: Core contribution in 2-3 sentences maximum. What is the paper's main claim and why does it matter?

**STANDARD**: A comprehensive 3-5 paragraph summary covering:
- **Problem & Motivation**: What specific problem does this paper address? Why is it important?
- **Approach & Methods**: What approach do the authors take? What are the key technical innovations?
- **Key Results**: What are the main findings? Include specific numbers, metrics, or quantitative results where available.
- **Implications**: Why do these results matter? What can practitioners learn from this?

**DETAILED**: A thorough, structured summary that captures the full substance of the paper. Include:

### Problem Statement & Motivation
- What specific gap or challenge does this paper address?
- What prior work does it build upon or challenge?
- Why is this problem important to solve?

### Technical Approach
- Describe the methodology in detail
- What are the key algorithmic or theoretical contributions?
- What assumptions or simplifications are made?
- Include mathematical formulations, algorithm steps, or architectural details where relevant

### Experiments & Results
- What datasets, benchmarks, or experimental setups were used?
- Report specific quantitative results (accuracy, speedup, etc.)
- How do results compare to baselines or prior work?
- What ablation studies or analyses were performed?

### Key Insights & Takeaways
- What are the most surprising or important findings?
- What worked well and what didn't?
- What are the practical implications?

### Limitations & Future Directions
- What limitations do the authors acknowledge?
- What questions remain unanswered?
- What future research directions do they suggest?

### Reader's Highlighted Passages
If the reader highlighted passages, incorporate what they found important into the relevant sections above.

Be thorough and specific. Include technical details, numbers, and concrete examples. The goal is to create notes detailed enough that someone reading them gets substantial value without reading the original paper.

Provide a {level} summary:""",

    "article": """Summarize this article at {level} level.

Title: {title}
Source: {source}

Article:
{content}

Reader's highlights (what they found important):
{annotations}

Summary levels and requirements:

**BRIEF**: Main takeaway in 2-3 sentences. What is the core message and why should someone care?

**STANDARD**: A thorough 3-5 paragraph summary covering:
- **Main Thesis**: What is the article's central argument or message?
- **Key Points**: What are the 3-5 most important ideas, with supporting evidence?
- **Examples & Evidence**: Include specific examples, data, or quotes that support the points
- **Actionable Insights**: What can readers do with this information?

**DETAILED**: A comprehensive summary that captures the full value of the article:

### Core Message
- What is the central thesis or main argument?
- Why did the author write this? What problem are they addressing?

### Key Ideas & Arguments
For each major point the article makes:
- State the idea clearly
- Summarize the supporting evidence or reasoning
- Include specific examples, data, or quotes
- Note any counterarguments or nuances

### Frameworks, Models, or Methods
- If the article introduces any frameworks, mental models, or methods, explain them in detail
- Include step-by-step processes if applicable

### Practical Applications
- How can this information be applied?
- What specific actions can readers take?
- What situations is this most relevant for?

### Connections & Context
- How does this relate to other ideas in the field?
- What assumptions underlie the arguments?
- What perspectives might disagree?

### Notable Quotes & Examples
- Include 2-4 particularly insightful quotes or examples that capture key ideas

Focus on extracting maximum practical value. Be specific and concrete, not generic.

Provide a {level} summary:""",

    "book": """Summarize these book notes/highlights at {level} level.

Book: {title}
Authors: {authors}

Content (highlights, notes, or chapter text):
{content}

The reader highlighted these passages as important - use them to inform the summary.

Summary levels and requirements:

**BRIEF**: Core theme and value proposition in 2-3 sentences.

**STANDARD**: A 4-6 paragraph summary covering:
- **Main Thesis**: What is the book's central argument or theme?
- **Key Ideas**: The 4-6 most important concepts or frameworks
- **Evidence & Examples**: Supporting stories or data that illustrate the ideas
- **Practical Takeaways**: How to apply these ideas

**DETAILED**: A comprehensive summary organized by theme or chapter:

### Book Overview
- What is the book's central thesis?
- Who is the target audience?
- What problem does it solve or question does it answer?

### Major Themes & Ideas
For each key concept or chapter theme:
- State the main idea clearly
- Explain the supporting arguments or evidence
- Include memorable examples, stories, or case studies
- Note practical applications

### Key Frameworks & Models
- Describe any frameworks, models, or systems introduced
- Explain how to apply them
- Include diagrams or step-by-step processes if applicable

### Most Important Passages
Based on the reader's highlights:
- Quote and explain the most insightful passages
- Connect them to the broader themes

### Practical Applications
- What are the main actionable takeaways?
- How can readers implement these ideas?
- What habits, practices, or mindset shifts does the book recommend?

### Critical Assessment
- What are the book's strengths?
- What limitations or criticisms might apply?
- What type of reader would benefit most?

Be generous with detail. The goal is to capture enough substance that these notes serve as a useful reference for years to come.

Provide a {level} summary:""",

    "code": """Summarize this code repository analysis at {level} level.

Repository: {title}

Analysis:
{content}

Summary levels and requirements:

**BRIEF**: What the code does and its primary use case in 2-3 sentences.

**STANDARD**: A 3-4 paragraph summary covering:
- **Purpose**: What problem does this code solve?
- **Architecture**: High-level structure and key components
- **Key Patterns**: Notable design patterns or techniques used
- **Usage**: How to use this code

**DETAILED**: A comprehensive technical summary:

### Purpose & Use Cases
- What problem does this code solve?
- What are the primary use cases?
- Who is the target user (library consumer, API user, etc.)?

### Architecture Overview
- What is the high-level structure?
- What are the main modules/packages and their responsibilities?
- How do components interact?
- Include a conceptual diagram if helpful

### Technical Implementation
- What languages, frameworks, and key dependencies are used?
- What are the core data structures or abstractions?
- What algorithms or techniques are notable?
- How is state managed?

### Key Design Decisions
- What architectural patterns are used (MVC, microservices, etc.)?
- What trade-offs were made and why?
- What makes this implementation interesting or unique?

### API & Usage Patterns
- What are the main entry points?
- How is the code typically used?
- Include example usage patterns

### Code Quality & Practices
- What testing approaches are used?
- How is the code organized?
- What documentation exists?

### Learning Takeaways
- What techniques or patterns are worth learning from this codebase?
- What would you do differently?

Provide a {level} summary:""",

    "idea": """Summarize this idea/note at {level} level.

Title: {title}

Content:
{content}

Summary levels and requirements:

**BRIEF**: The core idea in 1-2 sentences.

**STANDARD**: A 2-3 paragraph summary covering:
- What is the idea?
- Why does it matter?
- How might it be applied or developed?

**DETAILED**: A thorough exploration:

### Core Idea
- State the central concept clearly
- What problem does it address or question does it answer?

### Context & Background
- What prompted this idea?
- What existing ideas does it build on or connect to?

### Key Components
- Break down the idea into its constituent parts
- Explain how they fit together

### Implications & Applications
- What would change if this idea is correct?
- How could it be applied practically?
- What experiments or projects could test it?

### Open Questions
- What aspects need more development?
- What challenges or objections might arise?

### Connections
- How does this relate to other ideas or projects?

Provide a {level} summary:""",

    "voice_memo": """Summarize this voice memo transcription at {level} level.

Title: {title}

Transcription:
{content}

Summary levels and requirements:

**BRIEF**: Main point or purpose in 1-2 sentences.

**STANDARD**: A 2-4 paragraph summary covering:
- What is the main topic or purpose of this memo?
- What are the key points made?
- What action items or decisions emerged?

**DETAILED**: A comprehensive summary:

### Main Topic & Purpose
- What prompted this voice memo?
- What is the central subject?

### Key Points & Ideas
- List and explain each major point discussed
- Include relevant details and context
- Note any reasoning or justification provided

### Decisions & Conclusions
- What decisions were made or conclusions reached?
- What is the reasoning behind them?

### Action Items & Next Steps
- List specific action items mentioned
- Note any deadlines or priorities
- Identify who is responsible for what (if applicable)

### Questions & Open Items
- What questions were raised but not answered?
- What needs follow-up?

### Context & Connections
- How does this relate to other projects or ongoing work?
- What background knowledge is assumed?

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
