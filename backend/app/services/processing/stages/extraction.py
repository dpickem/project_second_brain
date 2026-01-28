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
from app.models.processing import (
    Concept,
    ConceptExample,
    ConceptMisconception,
    ConceptRelation,
    ExtractionResult,
    ContentAnalysis,
)
from app.enums.pipeline import PipelineOperation
from app.enums.processing import ConceptImportance
from app.models.llm_usage import LLMUsage
from app.services.llm.client import LLMClient
from app.config.processing import processing_settings
from app.services.processing.concept_dedup import deduplicate_concepts

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
   For each concept, provide:
   - Name: The concept name
   - Definition: A clear, concise definition (1-2 sentences, standalone)
   - Context: How this concept is used/discussed in THIS content
   - Importance: 
{_importance_section}
   - Why it matters: Why understanding this concept is valuable (1-2 sentences)
   - Properties: 2-4 key characteristics or attributes of this concept
   - Examples: 1-2 concrete examples that illustrate this concept
   - Misconceptions: Common misunderstandings people have (if applicable)
   - Prerequisites: Other concepts that should be understood first
   - Related concepts: Other concepts in this content it connects to, with relationship type

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
      "why_it_matters": "why understanding this is valuable",
      "properties": ["key characteristic 1", "key characteristic 2"],
      "examples": [
        {{{{"title": "Example Title", "content": "Explanation of the example"}}}}
      ],
      "misconceptions": [
        {{{{"wrong": "common incorrect belief", "correct": "the actual truth"}}}}
      ],
      "prerequisites": ["prerequisite concept 1"],
      "related_concepts": [
        {{{{"name": "related concept", "relationship": "how they're related"}}}}
      ]
    }}}}
  ],
  "key_findings": ["finding or insight 1", "finding or insight 2"],
  "methodologies": ["methodology or technique 1"],
  "tools_mentioned": ["tool or technology 1"],
  "people_mentioned": ["person name 1"]
}}}}

Guidelines:
- Extract 5-15 concepts depending on content length and density
- At least 2-3 should be "{ConceptImportance.CORE.value}" concepts with full detail
- Definitions should be standalone (understandable without reading content)
- Context should explain how concept is used IN THIS SPECIFIC content
- Key findings should be specific claims, not generic observations
- For CORE concepts: provide all fields (properties, examples, misconceptions, prerequisites)
- For SUPPORTING/TANGENTIAL: properties and examples are sufficient, others optional
- Relationship types: "extends", "contrasts with", "is a type of", "enables", "applies to", etc.
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
                # Parse examples
                examples = []
                for ex in c.get("examples", []):
                    if isinstance(ex, dict):
                        examples.append(
                            ConceptExample(
                                title=ex.get("title", ""),
                                content=ex.get("content", ""),
                            )
                        )
                    elif isinstance(ex, str):
                        # Handle case where LLM returns string instead of object
                        examples.append(ConceptExample(content=ex))

                # Parse misconceptions
                misconceptions = []
                for mis in c.get("misconceptions", []):
                    if isinstance(mis, dict) and mis.get("wrong"):
                        misconceptions.append(
                            ConceptMisconception(
                                wrong=mis.get("wrong", ""),
                                correct=mis.get("correct", ""),
                            )
                        )

                # Parse related concepts
                related_concepts = []
                for rel in c.get("related_concepts", []):
                    if isinstance(rel, dict):
                        related_concepts.append(
                            ConceptRelation(
                                name=rel.get("name", ""),
                                relationship=rel.get("relationship", "relates to"),
                            )
                        )
                    elif isinstance(rel, str):
                        # Backward compatibility: handle simple string list
                        related_concepts.append(
                            ConceptRelation(name=rel, relationship="relates to")
                        )

                concepts.append(
                    Concept(
                        name=c.get("name", ""),
                        definition=c.get("definition", ""),
                        context=c.get("context", ""),
                        importance=_validate_importance(
                            c.get("importance", ConceptImportance.SUPPORTING.value)
                        ),
                        why_it_matters=c.get("why_it_matters", ""),
                        properties=c.get("properties", []),
                        examples=examples,
                        misconceptions=misconceptions,
                        prerequisites=c.get("prerequisites", []),
                        related_concepts=related_concepts,
                    )
                )

        # Deduplicate concepts within this extraction
        # This handles cases where LLM extracts "Behavior Cloning (BC)" and "BC" separately
        unique_concepts = deduplicate_concepts(concepts)

        result = ExtractionResult(
            concepts=unique_concepts,
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
