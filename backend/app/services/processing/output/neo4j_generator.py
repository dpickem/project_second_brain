"""
Neo4j Knowledge Graph Generator

Creates knowledge graph nodes and relationships from processing results.

Nodes created:
- Content node with embedding
- Concept nodes for core concepts (with optional Obsidian notes)

Relationships created:
- CONTAINS: Content -> Concept
- RELATES_TO/EXTENDS/etc: Content -> Content

Usage:
    from app.services.processing.output.neo4j_generator import create_knowledge_nodes

    node_id = await create_knowledge_nodes(content, result, llm_client, neo4j_client)
"""

import logging
from typing import Optional

from app.models.content import UnifiedContent
from app.config.processing import processing_settings
from app.enums.processing import SummaryLevel, ConceptImportance
from app.models.processing import ProcessingResult
from app.services.llm.client import LLMClient
from app.services.knowledge_graph.client import Neo4jClient
from app.services.processing.output.obsidian_generator import (
    generate_concept_notes_for_content,
)

logger = logging.getLogger(__name__)


async def create_knowledge_nodes(
    content: UnifiedContent,
    result: ProcessingResult,
    llm_client: LLMClient,
    neo4j_client: Neo4jClient,
    generate_concept_notes: bool = True,
) -> Optional[str]:
    """
    Create knowledge graph nodes and relationships.

    Creates:
    1. Content node with embedding for the processed content
    2. Concept nodes for core concepts (with Obsidian notes if enabled)
    3. CONTAINS relationships from content to concepts
    4. Cross-content relationships from connection discovery

    Args:
        content: Original unified content
        result: Processing result with all stages
        llm_client: LLM client for embedding generation
        neo4j_client: Neo4j client for graph operations
        generate_concept_notes: If True, also generate Obsidian markdown notes
                               for core concepts (default: True)

    Returns:
        Created content node ID, or None if failed
    """
    try:
        # Get summary for embedding
        summary = result.summaries.get(SummaryLevel.STANDARD.value, content.title)
        embedding_text = f"{content.title}\n\n{summary}"

        # Generate embedding - embed() returns (list[list[float]], LLMUsage)
        embeddings, _usage = await llm_client.embed([embedding_text])
        embedding = embeddings[0] if embeddings else []

        # Combine all tags and ensure flat list of strings (no nested lists)
        all_tags = []
        for tag in result.tags.domain_tags + result.tags.meta_tags:
            if isinstance(tag, list):
                all_tags.extend(str(t) for t in tag)
            else:
                all_tags.append(str(tag))

        # Create content node
        # Use the obsidian note path from result (set by pipeline after note generation)
        # or fall back to content.obsidian_path if available
        file_path = result.obsidian_note_path or content.obsidian_path

        content_node_id = await neo4j_client.create_content_node(
            content_id=content.id,
            title=content.title,
            content_type=result.analysis.content_type,
            summary=summary[: processing_settings.NEO4J_SUMMARY_TRUNCATE],
            embedding=embedding,
            tags=all_tags,
            source_url=content.source_url,
            file_path=file_path,
            metadata={
                "domain": str(result.analysis.domain) if result.analysis.domain else "",
                "complexity": (
                    str(result.analysis.complexity)
                    if result.analysis.complexity
                    else ""
                ),
                "authors": ", ".join(content.authors) if content.authors else "",
            },
        )

        logger.debug(f"Created content node: {content_node_id}")

        # Generate Obsidian notes for concepts first (if enabled)
        # This gives us file paths to store in Neo4j
        concept_file_paths: dict[str, str] = {}
        if generate_concept_notes:
            try:
                created_notes = await generate_concept_notes_for_content(
                    content=content,
                    result=result,
                    importance_filter=ConceptImportance.CORE,
                )
                concept_file_paths = {
                    note["name"]: note["file_path"] for note in created_notes
                }
                logger.info(f"Generated {len(created_notes)} concept notes")
            except Exception as e:
                logger.error(f"Failed to generate concept notes: {e}")
                # Continue without concept notes - they're optional

        # Create concept nodes for core concepts
        core_concepts = [
            c
            for c in result.extraction.concepts
            if c.importance == ConceptImportance.CORE.value
        ]

        for concept in core_concepts:
            try:
                # Generate concept embedding - embed() returns (list[list[float]], LLMUsage)
                concept_text = f"{concept.name}: {concept.definition}"
                concept_emb, _usage = await llm_client.embed([concept_text])
                concept_embedding = concept_emb[0] if concept_emb else []

                # Get file path if we generated a note for this concept
                concept_file_path = concept_file_paths.get(concept.name)

                # Create concept node with file path
                await neo4j_client.create_concept_node(
                    concept=concept,
                    embedding=concept_embedding,
                    file_path=concept_file_path,
                )

                # Link content to concept
                await neo4j_client.link_content_to_concept(
                    content_id=content.id,
                    concept_id=concept.id,
                    importance=concept.importance,
                )

                logger.debug(
                    f"Created concept node: {concept.name} (note: {concept_file_path})"
                )

            except Exception as e:
                logger.error(f"Failed to create concept node '{concept.name}': {e}")

        # Create concept-to-concept relationships
        for concept in core_concepts:
            for related in concept.related_concepts:
                try:
                    created = await neo4j_client.link_concept_to_concept(
                        source_name=concept.name,
                        target_name=related.name,
                        relationship_type=related.relationship,
                    )
                    if created:
                        logger.debug(
                            f"Created concept link: {concept.name} "
                            f"-[{related.relationship}]-> {related.name}"
                        )
                except Exception as e:
                    logger.error(
                        f"Failed to link concept '{concept.name}' to '{related.name}': {e}"
                    )

        # Create cross-content relationships
        for conn in result.connections:
            try:
                await neo4j_client.create_relationship(
                    source_id=content.id,
                    target_id=conn.target_id,
                    relationship_type=conn.relationship_type,
                    properties={
                        "strength": conn.strength,
                        "explanation": conn.explanation,
                    },
                )
                logger.debug(
                    f"Created relationship: {content.title} "
                    f"-[{conn.relationship_type}]-> {conn.target_title}"
                )
            except Exception as e:
                logger.error(
                    f"Failed to create relationship to '{conn.target_title}': {e}"
                )

        # Link Content node to Note node if they share the same file_path
        # This bridges processed content with Obsidian vault representation
        if file_path:
            try:
                link_result = await neo4j_client.link_content_to_note_by_path(file_path)
                if link_result:
                    logger.debug(
                        f"Linked Content to Note: {link_result['content_id']} "
                        f"-> {link_result['note_id']}"
                    )
            except Exception as e:
                logger.debug(f"No Note node found to link for {file_path}: {e}")

        logger.info(
            f"Created knowledge graph nodes for {content.title}: "
            f"1 content, {len(core_concepts)} concepts, {len(result.connections)} connections"
        )

        return content_node_id

    except Exception as e:
        logger.error(f"Failed to create knowledge nodes: {e}")
        return None


async def update_content_node(
    content_id: str,
    title: str,
    result: ProcessingResult,
    llm_client: LLMClient,
    neo4j_client: Neo4jClient,
    content: Optional[UnifiedContent] = None,
    generate_concept_notes: bool = True,
) -> bool:
    """
    Update an existing content node with new processing results.

    Used when content is reprocessed. This performs a full update:
    1. Deletes old outgoing relationships
    2. Updates the content node properties and embedding
    3. Creates new concept nodes and CONTAINS relationships (with optional Obsidian notes)
    4. Creates new cross-content relationships

    Args:
        content_id: ID of content node to update
        title: Content title (for embedding generation)
        result: New processing result
        llm_client: LLM client for embedding
        neo4j_client: Neo4j client for updates
        content: Optional UnifiedContent for concept note generation
        generate_concept_notes: If True and content provided, generate Obsidian notes

    Returns:
        True if successful, False otherwise
    """
    try:
        # Step 1: Delete old outgoing relationships
        deleted_count = await neo4j_client.delete_content_relationships(content_id)
        logger.debug(f"Deleted {deleted_count} old relationships for {content_id}")

        # Step 2: Update content node with new embedding - embed() returns (list[list[float]], LLMUsage)
        summary = result.summaries.get(SummaryLevel.STANDARD.value, "")
        embedding_text = f"{title}\n\n{summary}"
        embeddings, _usage = await llm_client.embed([embedding_text])

        # Flatten tags to ensure no nested lists
        all_tags = []
        for tag in result.tags.domain_tags + result.tags.meta_tags:
            if isinstance(tag, list):
                all_tags.extend(str(t) for t in tag)
            else:
                all_tags.append(str(tag))

        await neo4j_client.create_content_node(
            content_id=content_id,
            title=title,
            content_type=result.analysis.content_type,
            summary=summary[: processing_settings.NEO4J_SUMMARY_TRUNCATE],
            embedding=embeddings[0] if embeddings else [],
            tags=all_tags,
            metadata={
                "domain": str(result.analysis.domain) if result.analysis.domain else "",
                "complexity": (
                    str(result.analysis.complexity)
                    if result.analysis.complexity
                    else ""
                ),
            },
        )

        # Step 3: Generate concept notes if enabled and content provided
        concept_file_paths: dict[str, str] = {}
        if generate_concept_notes and content is not None:
            try:
                created_notes = await generate_concept_notes_for_content(
                    content=content,
                    result=result,
                    importance_filter=ConceptImportance.CORE,
                )
                concept_file_paths = {
                    note["name"]: note["file_path"] for note in created_notes
                }
            except Exception as e:
                logger.error(f"Failed to generate concept notes: {e}")

        # Step 4: Create concept nodes for core concepts
        core_concepts = [
            c
            for c in result.extraction.concepts
            if c.importance == ConceptImportance.CORE.value
        ]

        for concept in core_concepts:
            try:
                concept_text = f"{concept.name}: {concept.definition}"
                concept_emb, _usage = await llm_client.embed([concept_text])
                concept_file_path = concept_file_paths.get(concept.name)

                await neo4j_client.create_concept_node(
                    concept=concept,
                    embedding=concept_emb[0] if concept_emb else [],
                    file_path=concept_file_path,
                )

                await neo4j_client.link_content_to_concept(
                    content_id=content_id,
                    concept_id=concept.id,
                    importance=concept.importance,
                )

            except Exception as e:
                logger.error(f"Failed to update concept node '{concept.name}': {e}")

        # Step 5: Create concept-to-concept relationships
        for concept in core_concepts:
            for related in concept.related_concepts:
                try:
                    await neo4j_client.link_concept_to_concept(
                        source_name=concept.name,
                        target_name=related.name,
                        relationship_type=related.relationship,
                    )
                except Exception as e:
                    logger.error(
                        f"Failed to link concept '{concept.name}' to '{related.name}': {e}"
                    )

        # Step 6: Create cross-content relationships
        for conn in result.connections:
            try:
                await neo4j_client.create_relationship(
                    source_id=content_id,
                    target_id=conn.target_id,
                    relationship_type=conn.relationship_type,
                    properties={
                        "strength": conn.strength,
                        "explanation": conn.explanation,
                    },
                )
            except Exception as e:
                logger.error(
                    f"Failed to create relationship to '{conn.target_title}': {e}"
                )

        logger.info(
            f"Updated knowledge graph for {content_id}: "
            f"{len(core_concepts)} concepts, {len(result.connections)} connections"
        )

        return True

    except Exception as e:
        logger.error(f"Failed to update content node: {e}")
        return False
