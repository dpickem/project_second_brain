"""
Concept Extraction Stage

Extracts structured information from content:
- Concepts with definitions, context, and importance
- Key findings and insights
- Methodologies and techniques
- Tools and technologies mentioned
- People referenced

Usage:
    from app.services.processing.stages.extraction import extract_concepts

    result, usages = await extract_concepts(content, analysis, llm_client)
    for concept in result.concepts:
        print(f"{concept.name}: {concept.definition}")
"""

import logging

from app.models.content import UnifiedContent
from app.models.processing import Concept, ExtractionResult, ContentAnalysis
from app.enums.pipeline import PipelineOperation
from app.enums.processing import ConceptImportance
from app.pipelines.utils.cost_types import LLMUsage
from app.services.llm.client import LLMClient
from app.config.processing import processing_settings

logger = logging.getLogger(__name__)


# Build importance section from enum
_importance_section = "\n".join(
    f'     * "{i.value}" - {desc}'
    for i, desc in [
        (ConceptImportance.CORE, "Central to understanding this content"),
        (ConceptImportance.SUPPORTING, "Helps understand core concepts"),
        (ConceptImportance.TANGENTIAL, "Mentioned but not essential"),
    ]
)

EXTRACTION_PROMPT = f"""Extract structured information from this content.

Title: {{title}}
Domain: {{domain}}
Complexity: {{complexity}}

Content:
{{content}}

Extract the following:

1. **CONCEPTS**: Key ideas, terms, frameworks, theories mentioned
   - Name: The concept name
   - Definition: A clear, concise definition
   - Context: How this concept is used/discussed in THIS content
   - Importance: 
{_importance_section}
   - Related concepts: Other concepts in this content it connects to

2. **KEY FINDINGS**: Main insights, conclusions, claims, or arguments made

3. **METHODOLOGIES**: Approaches, techniques, algorithms, or processes described

4. **TOOLS**: Software, frameworks, libraries, or technologies mentioned

5. **PEOPLE**: Authors, researchers, practitioners, or thought leaders referenced

Return as JSON:
{{{{
  "concepts": [
    {{{{
      "name": "concept name",
      "definition": "clear definition in 1-2 sentences",
      "context": "how it's used in this specific content",
      "importance": "{"|".join(i.value for i in ConceptImportance)}",
      "related_concepts": ["concept1", "concept2"]
    }}}}
  ],
  "key_findings": ["finding or insight 1", "finding or insight 2"],
  "methodologies": ["methodology or technique 1"],
  "tools_mentioned": ["tool or technology 1"],
  "people_mentioned": ["person name 1"]
}}}}

Guidelines:
- Extract 5-15 concepts depending on content length and density
- At least 2-3 should be "{ConceptImportance.CORE.value}" concepts
- Definitions should be standalone (understandable without reading content)
- Context should explain how concept is used IN THIS SPECIFIC content
- Key findings should be specific claims, not generic observations
"""


async def extract_concepts(
    content: UnifiedContent, analysis: ContentAnalysis, llm_client: LLMClient
) -> tuple[ExtractionResult, list[LLMUsage]]:
    """
    Extract concepts, findings, and entities from content.

    Args:
        content: Unified content from ingestion
        analysis: Content analysis result
        llm_client: LLM client for completion

    Returns:
        Tuple of (ExtractionResult, list of LLMUsage for cost tracking)
    """
    text_content = (
        content.full_text[: processing_settings.EXTRACTION_TRUNCATE]
        if content.full_text
        else ""
    )

    if not text_content.strip():
        logger.warning(f"Content {content.id} has no text for extraction")
        return ExtractionResult(), []

    prompt = EXTRACTION_PROMPT.format(
        title=content.title,
        domain=analysis.domain,
        complexity=analysis.complexity,
        content=text_content,
    )

    try:
        data, usage = await llm_client.complete(
            operation=PipelineOperation.CONCEPT_EXTRACTION,
            messages=[{"role": "user", "content": prompt}],
            temperature=processing_settings.EXTRACTION_TEMPERATURE,
            max_tokens=processing_settings.EXTRACTION_MAX_TOKENS,
            json_mode=True,
            content_id=content.id,
        )

        # Parse concepts
        concepts = []
        for c in data.get("concepts", []):
            if c.get("name"):  # Skip empty concepts
                concepts.append(
                    Concept(
                        name=c.get("name", ""),
                        definition=c.get("definition", ""),
                        context=c.get("context", ""),
                        importance=_validate_importance(
                            c.get("importance", ConceptImportance.SUPPORTING.value)
                        ),
                        related_concepts=c.get("related_concepts", []),
                    )
                )

        result = ExtractionResult(
            concepts=concepts,
            key_findings=data.get("key_findings", []),
            methodologies=data.get("methodologies", []),
            tools_mentioned=data.get("tools_mentioned", []),
            people_mentioned=data.get("people_mentioned", []),
        )
        return result, [usage]

    except Exception as e:
        logger.error(f"Concept extraction failed: {e}")
        return ExtractionResult(), []


def _validate_importance(importance: str) -> str:
    """Validate and normalize importance level."""
    importance = importance.upper().strip()
    valid_values = {e.value for e in ConceptImportance}
    if importance in valid_values:
        return importance
    return ConceptImportance.SUPPORTING.value
