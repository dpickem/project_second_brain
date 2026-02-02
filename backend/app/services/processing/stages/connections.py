"""
Connection Discovery Stage

Discovers semantic relationships between new content and existing knowledge
in the knowledge graph. Uses embedding similarity for candidate selection
and LLM evaluation for relationship characterization.

Optimization: Uses batched evaluation to reduce LLM calls. Instead of
evaluating each candidate individually (N calls), candidates are grouped
into mini-batches and evaluated together (N/batch_size calls).

Usage:
    from app.services.processing.stages.connections import discover_connections

    connections, usages = await discover_connections(
        content, summary, extraction, analysis,
        llm_client, neo4j_client
    )
    for conn in connections:
        print(f"{conn.relationship_type} -> {conn.target_title}")
"""

import logging
from typing import Optional

from app.models.content import UnifiedContent
from app.models.processing import Connection, ExtractionResult, ContentAnalysis
from app.enums import PipelineOperation, RelationshipType, NodeType
from app.models.llm_usage import LLMUsage
from app.services.llm.client import LLMClient
from app.services.knowledge_graph.client import Neo4jClient
from app.config.processing import processing_settings

logger = logging.getLogger(__name__)

# Default batch size for connection evaluation (can be overridden in settings)
DEFAULT_CONNECTION_BATCH_SIZE = 5

# Valid relationship types for content-to-content connections
CONTENT_RELATIONSHIP_TYPES = [
    RelationshipType.RELATES_TO,
    RelationshipType.EXTENDS,
    RelationshipType.CONTRADICTS,
    RelationshipType.PREREQUISITE_FOR,
    RelationshipType.APPLIES,
]


# Descriptions for each relationship type (used in prompt)
RELATIONSHIP_DESCRIPTIONS = {
    RelationshipType.RELATES_TO: "General topical relationship, shared themes or concepts",
    RelationshipType.EXTENDS: "New content builds on, continues, or deepens existing content",
    RelationshipType.CONTRADICTS: "New content challenges, refutes, or disagrees with existing content",
    RelationshipType.PREREQUISITE_FOR: "Existing content is foundational for understanding new content",
    RelationshipType.APPLIES: "New content applies concepts, methods, or ideas from existing content",
}

# Build connection types section for prompt
_connection_types_section = "\n".join(
    f"- {rel_type}: {RELATIONSHIP_DESCRIPTIONS[rel_type]}"
    for rel_type in CONTENT_RELATIONSHIP_TYPES
)

CONNECTION_EVALUATION_PROMPT = f"""Evaluate the relationship between new content and a potential connection.

NEW CONTENT:
Title: {{new_title}}
Summary: {{new_summary}}
Key Concepts: {{new_concepts}}

POTENTIAL CONNECTION:
Title: {{candidate_title}}
Summary: {{candidate_summary}}

Evaluate whether these two pieces of content are meaningfully connected.

Connection Types:
{_connection_types_section}

Return JSON:
{{{{
  "has_connection": true|false,
  "relationship_type": "{"|".join(CONTENT_RELATIONSHIP_TYPES)}",
  "strength": 0.0-1.0,
  "explanation": "1-2 sentence explanation of the connection"
}}}}

Guidelines:
- has_connection should be true only for meaningful, specific connections
- Avoid generic "both are about X" connections
- strength should reflect how central the connection is:
  * 0.8-1.0: Core relationship, directly builds on each other
  * 0.5-0.8: Significant overlap in concepts or methods
  * 0.3-0.5: Related but tangential
- explanation should be specific about what connects them
"""

# Batched evaluation prompt - evaluates multiple candidates in one call
BATCH_CONNECTION_EVALUATION_PROMPT = f"""Evaluate the relationships between new content and multiple potential connections.

NEW CONTENT:
Title: {{new_title}}
Summary: {{new_summary}}
Key Concepts: {{new_concepts}}

POTENTIAL CONNECTIONS:
{{candidates_section}}

For each candidate, evaluate whether it has a meaningful connection to the new content.

Connection Types:
{_connection_types_section}

Return JSON with an array of evaluations (one per candidate, in the same order):
{{{{
  "evaluations": [
    {{{{
      "candidate_id": "id of the candidate",
      "has_connection": true|false,
      "relationship_type": "{"|".join(CONTENT_RELATIONSHIP_TYPES)}",
      "strength": 0.0-1.0,
      "explanation": "1-2 sentence explanation of the connection"
    }}}},
    ...
  ]
}}}}

Guidelines:
- has_connection should be true only for meaningful, specific connections
- Avoid generic "both are about X" connections
- strength should reflect how central the connection is:
  * 0.8-1.0: Core relationship, directly builds on each other
  * 0.5-0.8: Significant overlap in concepts or methods
  * 0.3-0.5: Related but tangential
- explanation should be specific about what connects them
- Evaluate each candidate independently
"""


async def discover_connections(
    content: UnifiedContent,
    summary: str,
    extraction: ExtractionResult,
    analysis: ContentAnalysis,
    llm_client: LLMClient,
    neo4j_client: Neo4jClient,
    top_k: int = None,
    similarity_threshold: float = None,
    connection_threshold: float = None,
    batch_size: int = None,
) -> tuple[list[Connection], list[LLMUsage]]:
    """
    Discover connections to existing knowledge in the graph.

    Process:
    1. Generate embedding for new content
    2. Find similar content via vector search
    3. Evaluate candidates in batches with LLM (reduces API calls)
    4. Return connections above threshold

    Args:
        content: Unified content being processed
        summary: Generated summary for embedding
        extraction: Extracted concepts and findings
        analysis: Content analysis result
        llm_client: LLM client for embedding and evaluation
        neo4j_client: Neo4j client for vector search
        top_k: Max candidates to evaluate (default from settings)
        similarity_threshold: Min embedding similarity (default from settings)
        connection_threshold: Min connection strength (default from settings)
        batch_size: Number of candidates to evaluate per LLM call (default: 5)

    Returns:
        Tuple of (list of Connection objects sorted by strength, list of LLMUsage)
    """
    # Use defaults from settings
    top_k = top_k or processing_settings.MAX_CONNECTION_CANDIDATES
    similarity_threshold = (
        similarity_threshold or processing_settings.CONNECTION_SIMILARITY_THRESHOLD
    )
    connection_threshold = (
        connection_threshold or processing_settings.CONNECTION_STRENGTH_THRESHOLD
    )
    batch_size = batch_size or getattr(
        processing_settings, "CONNECTION_BATCH_SIZE", DEFAULT_CONNECTION_BATCH_SIZE
    )

    connections = []
    usages: list[LLMUsage] = []

    # Generate embedding for new content
    embedding_text = f"{content.title}\n\n{summary[:processing_settings.CONNECTION_EMBEDDING_TRUNCATE]}"
    try:
        embeddings, embed_usage = await llm_client.embed(
            [embedding_text], content_id=content.id
        )
        usages.append(embed_usage)
        if not embeddings:
            logger.warning("Failed to generate embedding for connection discovery")
            return [], usages
    except Exception as e:
        logger.error(f"Embedding generation failed: {e}")
        return [], usages

    # Find similar content via vector search
    try:
        candidates = await neo4j_client.vector_search(
            embedding=embeddings[0],
            node_type=NodeType.CONTENT.value,
            top_k=top_k * processing_settings.CONNECTION_CANDIDATE_MULTIPLIER,
            threshold=similarity_threshold,
        )
    except Exception as e:
        logger.error(f"Vector search failed: {e}")
        return [], usages

    # Filter out self-connections
    candidates = [c for c in candidates if c.get("id") != content.id]
    logger.debug(f"Found {len(candidates)} similar content candidates (excluding self)")

    if not candidates:
        logger.info(f"No connection candidates found for {content.title}")
        return [], usages

    # Extract concept names for evaluation
    concept_names = [
        c.name
        for c in extraction.concepts[: processing_settings.CONNECTION_MAX_CONCEPTS]
    ]

    # Evaluate candidates in batches
    new_summary_truncated = summary[: processing_settings.CONNECTION_EVAL_SUMMARY_TRUNCATE]
    
    for i in range(0, len(candidates), batch_size):
        batch = candidates[i : i + batch_size]
        
        batch_connections, batch_usage = await _evaluate_connections_batch(
            new_title=content.title,
            new_summary=new_summary_truncated,
            new_concepts=concept_names,
            candidates=batch,
            llm_client=llm_client,
            threshold=connection_threshold,
            content_id=content.id,
        )

        if batch_usage:
            usages.append(batch_usage)

        connections.extend(batch_connections)

        # Stop if we have enough connections
        if len(connections) >= top_k:
            logger.debug(f"Reached {len(connections)} connections, stopping evaluation")
            break

    # Sort by strength descending
    connections.sort(key=lambda c: c.strength, reverse=True)

    logger.info(f"Discovered {len(connections)} connections for {content.title}")
    return connections[:top_k], usages


async def _evaluate_connections_batch(
    new_title: str,
    new_summary: str,
    new_concepts: list[str],
    candidates: list[dict],
    llm_client: LLMClient,
    threshold: float,
    content_id: str | None = None,
) -> tuple[list[Connection], Optional[LLMUsage]]:
    """
    Evaluate multiple potential connections in a single LLM call.

    This batched approach reduces API calls from N to ceil(N/batch_size),
    significantly improving processing speed and reducing costs.

    Args:
        new_title: Title of new content
        new_summary: Summary of new content
        new_concepts: Key concepts from new content
        candidates: List of candidates from vector search
        llm_client: LLM client for evaluation
        threshold: Minimum strength threshold
        content_id: Content ID for cost tracking

    Returns:
        Tuple of (list of valid Connections, LLMUsage if call made)
    """
    if not candidates:
        return [], None

    # Build candidates section for prompt
    candidates_section = ""
    for idx, candidate in enumerate(candidates, 1):
        candidate_id = candidate.get("id", f"candidate_{idx}")
        candidate_title = candidate.get("title") or candidate.get("name", "Unknown")
        candidate_summary = candidate.get("summary", "No summary available")[
            : processing_settings.CONNECTION_CANDIDATE_SUMMARY_TRUNCATE
        ]
        candidates_section += f"""
[Candidate {idx}]
ID: {candidate_id}
Title: {candidate_title}
Summary: {candidate_summary}
"""

    prompt = BATCH_CONNECTION_EVALUATION_PROMPT.format(
        new_title=new_title,
        new_summary=new_summary,
        new_concepts=", ".join(new_concepts) if new_concepts else "None extracted",
        candidates_section=candidates_section.strip(),
    )

    try:
        data, usage = await llm_client.complete(
            operation=PipelineOperation.CONNECTION_DISCOVERY,
            messages=[{"role": "user", "content": prompt}],
            temperature=processing_settings.CONNECTION_TEMPERATURE,
            max_tokens=processing_settings.CONNECTION_MAX_TOKENS * len(candidates),
            json_mode=True,
            content_id=content_id,
        )

        connections = []
        evaluations = data.get("evaluations", [])
        
        # Create a mapping of candidate_id to candidate for lookup
        candidate_map = {c.get("id"): c for c in candidates}
        
        for eval_result in evaluations:
            if not eval_result.get("has_connection"):
                continue

            strength = float(eval_result.get("strength", 0))
            if strength < threshold:
                continue

            candidate_id = eval_result.get("candidate_id")
            candidate = candidate_map.get(candidate_id)
            
            if not candidate:
                # Try to match by position if ID matching fails
                logger.debug(f"Could not find candidate with ID {candidate_id}")
                continue

            relationship_type = eval_result.get("relationship_type", RelationshipType.RELATES_TO)
            if relationship_type not in CONTENT_RELATIONSHIP_TYPES:
                relationship_type = RelationshipType.RELATES_TO

            connection = Connection(
                target_id=candidate["id"],
                target_title=candidate.get("title") or candidate.get("name", "Unknown"),
                relationship_type=relationship_type,
                strength=strength,
                explanation=eval_result.get("explanation", ""),
            )
            connections.append(connection)

        logger.debug(f"Batch evaluation: {len(connections)}/{len(candidates)} candidates passed threshold")
        return connections, usage

    except Exception as e:
        logger.error(f"Batch connection evaluation failed: {e}")
        # Fallback to individual evaluation on batch failure
        logger.info("Falling back to individual connection evaluation")
        return await _fallback_individual_evaluation(
            new_title, new_summary, new_concepts, candidates,
            llm_client, threshold, content_id
        )


async def _fallback_individual_evaluation(
    new_title: str,
    new_summary: str,
    new_concepts: list[str],
    candidates: list[dict],
    llm_client: LLMClient,
    threshold: float,
    content_id: str | None = None,
) -> tuple[list[Connection], Optional[LLMUsage]]:
    """
    Fallback to individual evaluation if batch fails.
    
    Returns connections and a synthetic usage object combining all calls.
    """
    connections = []
    total_input_tokens = 0
    total_output_tokens = 0
    total_cost = 0.0
    
    for candidate in candidates:
        connection, usage = await _evaluate_connection(
            new_title=new_title,
            new_summary=new_summary,
            new_concepts=new_concepts,
            candidate=candidate,
            llm_client=llm_client,
            threshold=threshold,
            content_id=content_id,
        )
        
        if usage:
            total_input_tokens += usage.input_tokens or 0
            total_output_tokens += usage.output_tokens or 0
            total_cost += usage.cost_usd or 0
        
        if connection:
            connections.append(connection)
    
    # Create synthetic usage object for the fallback
    combined_usage = LLMUsage(
        operation=PipelineOperation.CONNECTION_DISCOVERY,
        model="fallback-individual",
        input_tokens=total_input_tokens,
        output_tokens=total_output_tokens,
        cost_usd=total_cost,
        content_id=content_id,
    ) if total_input_tokens > 0 else None
    
    return connections, combined_usage


async def _evaluate_connection(
    new_title: str,
    new_summary: str,
    new_concepts: list[str],
    candidate: dict,
    llm_client: LLMClient,
    threshold: float,
    content_id: str | None = None,
) -> tuple[Optional[Connection], Optional[LLMUsage]]:
    """
    Evaluate a single potential connection using LLM.

    Args:
        new_title: Title of new content
        new_summary: Summary of new content
        new_concepts: Key concepts from new content
        candidate: Candidate from vector search
        llm_client: LLM client for evaluation
        threshold: Minimum strength threshold

    Returns:
        Tuple of (Connection if valid else None, LLMUsage if call made else None)
    """
    prompt = CONNECTION_EVALUATION_PROMPT.format(
        new_title=new_title,
        new_summary=new_summary,
        new_concepts=", ".join(new_concepts) if new_concepts else "None extracted",
        candidate_title=candidate.get("title") or candidate.get("name", "Unknown"),
        candidate_summary=candidate.get("summary", "No summary available")[
            : processing_settings.CONNECTION_CANDIDATE_SUMMARY_TRUNCATE
        ],
    )

    try:
        data, usage = await llm_client.complete(
            operation=PipelineOperation.CONNECTION_DISCOVERY,
            messages=[{"role": "user", "content": prompt}],
            temperature=processing_settings.CONNECTION_TEMPERATURE,
            max_tokens=processing_settings.CONNECTION_MAX_TOKENS,
            json_mode=True,
            content_id=content_id,
        )

        if not data.get("has_connection"):
            return None, usage

        strength = float(data.get("strength", 0))
        if strength < threshold:
            return None, usage

        relationship_type = data.get("relationship_type", RelationshipType.RELATES_TO)
        if relationship_type not in CONTENT_RELATIONSHIP_TYPES:
            relationship_type = RelationshipType.RELATES_TO

        connection = Connection(
            target_id=candidate["id"],
            target_title=candidate.get("title") or candidate.get("name", "Unknown"),
            relationship_type=relationship_type,
            strength=strength,
            explanation=data.get("explanation", ""),
        )
        return connection, usage

    except Exception as e:
        logger.error(f"Connection evaluation failed: {e}")
        return None, None
