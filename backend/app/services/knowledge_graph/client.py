"""
Neo4j Knowledge Graph Client

Provides a clean interface for knowledge graph operations:
- Vector similarity search for connection discovery
- Content and concept node creation
- Relationship management
- Graph traversal queries

Usage:
    from app.services.knowledge_graph import get_neo4j_client

    client = await get_neo4j_client()

    # Find similar content
    similar = await client.vector_search(embedding, top_k=10)

    # Create a content node
    node_id = await client.create_content_node(content, embedding, tags)
"""

import json
import logging
from typing import Optional

from neo4j import AsyncGraphDatabase, GraphDatabase

from app.config.settings import settings
from app.config.processing import processing_settings
from app.models.processing import Concept
from app.enums import ConceptImportance, NodeType
from app.services.knowledge_graph.queries import (
    SETUP_INDEX_QUERIES,
    MERGE_CONTENT_NODE,
    MERGE_CONCEPT_NODE,
    MERGE_NOTE_NODE,
    DELETE_NOTE_OUTGOING_LINKS,
    CREATE_NOTE_LINK,
    GET_CONTENT_BY_ID,
    DELETE_CONTENT_AND_RELATIONS,
    DELETE_CONTENT_OUTGOING_RELATIONSHIPS,
    CREATE_RELATIONSHIP,
    LINK_CONCEPTS_BY_NAME,
    GET_CONNECTED_NODES,
    VECTOR_SEARCH,
    VERIFY_CONNECTIVITY,
    LIST_INDEX_NAMES,
    GET_ALL_GRAPH_DATA,
    LINK_CONTENT_TO_NOTE_BY_FILE_PATH,
    FIND_NOTE_BY_FILE_PATH,
    FIND_CONTENT_BY_FILE_PATH,
    LINK_ALL_CONTENT_TO_NOTES,
)

logger = logging.getLogger(__name__)


class Neo4jClient:
    """
    Client for Neo4j knowledge graph operations.

    Provides async methods for vector search, node creation, and relationship
    management. Supports both async (FastAPI) and sync (Celery) usage patterns.

    The knowledge graph stores:
    - Content nodes: Papers, articles, books, etc. with embeddings
    - Concept nodes: Key concepts with definitions and embeddings
    - Relationships: RELATES_TO, EXTENDS, CONTAINS, etc.

    Vector similarity search is used for connection discovery, finding
    semantically similar content based on embedding distance.
    """

    def __init__(self):
        """Initialize Neo4j drivers for async and sync operations."""
        self._async_driver = None
        self._sync_driver = None
        self._initialized = False

    async def _ensure_initialized(self):
        """Lazily initialize drivers and indexes on first use."""
        if not self._initialized:
            try:
                self._async_driver = AsyncGraphDatabase.driver(
                    settings.NEO4J_URI,
                    auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
                )
                self._sync_driver = GraphDatabase.driver(
                    settings.NEO4J_URI,
                    auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
                )
                self._initialized = True
                logger.info(f"Neo4j client connected to {settings.NEO4J_URI}")

                # Only setup indexes if they don't exist
                if not await self._are_indexes_initialized():
                    await self._setup_indexes_internal()
            except Exception as e:
                logger.error(f"Failed to connect to Neo4j: {e}")
                raise

    async def _are_indexes_initialized(self) -> bool:
        """
        Check if required vector indexes already exist.

        Returns:
            True if all required indexes exist, False otherwise
        """
        required_indexes = {"content_embedding_index", "concept_embedding_index"}

        try:
            async with self._async_driver.session(
                database=settings.NEO4J_DATABASE
            ) as session:
                result = await session.run(LIST_INDEX_NAMES)
                existing_indexes = {record["name"] async for record in result}

                missing = required_indexes - existing_indexes
                if missing:
                    logger.debug(f"Missing Neo4j indexes: {missing}")
                    return False
                return True
        except Exception as e:
            logger.debug(f"Could not check indexes: {e}")
            return False

    async def close(self):
        """Close database connections."""
        if self._async_driver:
            await self._async_driver.close()
        if self._sync_driver:
            self._sync_driver.close()
        self._initialized = False

    async def verify_connectivity(self) -> bool:
        """
        Verify Neo4j connectivity.

        Returns:
            True if connected successfully, False otherwise
        """
        await self._ensure_initialized()
        try:
            async with self._async_driver.session(
                database=settings.NEO4J_DATABASE
            ) as session:
                result = await session.run(VERIFY_CONNECTIVITY)
                await result.single()
                return True
        except Exception as e:
            logger.error(f"Neo4j connectivity check failed: {e}")
            return False

    async def _setup_indexes_internal(self):
        """
        Internal method to create indexes (called during initialization).

        Does NOT call _ensure_initialized() to avoid circular calls.
        """
        logger.info("Creating Neo4j indexes (first-time setup)...")
        async with self._async_driver.session(
            database=settings.NEO4J_DATABASE
        ) as session:
            for query in SETUP_INDEX_QUERIES:
                try:
                    await session.run(query)
                    logger.debug(f"Executed: {query[:50]}...")
                except Exception as e:
                    # Index might already exist
                    logger.debug(f"Index creation note: {e}")

        logger.info("Neo4j indexes setup complete")

    async def setup_indexes(self):
        """
        Create necessary indexes for efficient querying.

        Creates:
        - Vector index on Content.embedding
        - Vector index on Concept.embedding
        - Unique constraint on Content.id
        - Unique constraint on Concept.name
        - Regular indexes for type and created_at

        Queries are defined in app.services.knowledge_graph.queries

        Note: Indexes are automatically created on first connection,
        but this method can be called explicitly if needed.
        """
        await self._ensure_initialized()
        # Indexes already created during initialization, but run again to be safe
        await self._setup_indexes_internal()

    async def vector_search(
        self,
        embedding: list[float],
        node_type: str = NodeType.CONTENT.value,
        top_k: int = processing_settings.NEO4J_VECTOR_SEARCH_TOP_K,
        threshold: float = processing_settings.NEO4J_VECTOR_SEARCH_THRESHOLD,
    ) -> list[dict]:
        """
        Find similar nodes using vector similarity search.

        Uses Neo4j's vector index to find nodes with similar embeddings.
        This is the core of connection discovery.

        Args:
            embedding: Query embedding vector (1536 dimensions for OpenAI)
            node_type: Type of node to search (use NodeType enum values)
            top_k: Number of results to return
            threshold: Minimum similarity score (0-1)

        Returns:
            List of matching nodes with similarity scores:
            [{"id": "...", "title": "...", "summary": "...", "type": "...", "score": 0.85}]
        """
        await self._ensure_initialized()

        index_name = f"{node_type.lower()}_embedding_index"

        async with self._async_driver.session(
            database=settings.NEO4J_DATABASE
        ) as session:
            result = await session.run(
                VECTOR_SEARCH,
                index_name=index_name,
                top_k=top_k,
                embedding=embedding,
                threshold=threshold,
            )
            records = [dict(record) async for record in result]
            return records

    async def create_content_node(
        self,
        content_id: str,
        title: str,
        content_type: str,
        summary: str,
        embedding: list[float],
        tags: list[str],
        source_url: Optional[str] = None,
        file_path: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> str:
        """
        Create a Content node in the knowledge graph.

        Content nodes represent ingested items (papers, articles, books, etc.)
        and include embeddings for vector similarity search.

        Args:
            content_id: Unique identifier (UUID from UnifiedContent)
            title: Content title
            content_type: Type (paper, article, book, etc.)
            summary: Generated summary for display and search
            embedding: Vector embedding for similarity search
            tags: Assigned tags from taxonomy
            source_url: Original source URL if available
            file_path: Path to the Obsidian vault note file
            metadata: Additional metadata dict

        Returns:
            The created node's ID
        """
        await self._ensure_initialized()

        # Convert metadata dict to JSON string to avoid Neo4j nested collection issues
        metadata_json = json.dumps(metadata) if metadata else "{}"

        async with self._async_driver.session(
            database=settings.NEO4J_DATABASE
        ) as session:
            result = await session.run(
                MERGE_CONTENT_NODE,
                id=content_id,
                title=title,
                content_type=content_type,
                summary=(
                    summary[: processing_settings.NEO4J_SUMMARY_TRUNCATE]
                    if summary
                    else ""
                ),
                embedding=embedding,
                tags=tags,
                source_url=source_url,
                file_path=file_path,
                metadata=metadata_json,
            )
            record = await result.single()
            return record["id"]

    async def create_concept_node(
        self, concept: Concept, embedding: list[float], file_path: Optional[str] = None
    ) -> str:
        """
        Create or merge a Concept node.

        Concepts are merged by canonical_name (lowercase, no aliases) to ensure
        proper deduplication. For example, "Behavior Cloning (BC)" and "Behavior
        Cloning" will merge to the same node.

        If a concept with the same canonical name exists:
        - Definition is updated only if the new one is more detailed and "core"
        - Aliases are accumulated from all sources
        - Display name is updated to prefer the more complete version

        Args:
            concept: The extracted Concept object
            embedding: Vector embedding for similarity search
            file_path: Optional path to Obsidian note for this concept

        Returns:
            The created/merged node's ID
        """
        await self._ensure_initialized()

        # Import here to avoid circular import
        from app.services.processing.concept_dedup import (
            get_canonical_name,
            extract_aliases,
        )

        # Normalize concept name for deduplication
        canonical_name = get_canonical_name(concept.name).lower()
        display_name = get_canonical_name(concept.name)  # Original case, no aliases
        aliases = extract_aliases(concept.name)

        async with self._async_driver.session(
            database=settings.NEO4J_DATABASE
        ) as session:
            result = await session.run(
                MERGE_CONCEPT_NODE,
                id=concept.id,
                canonical_name=canonical_name,
                display_name=display_name,
                definition=concept.definition,
                embedding=embedding,
                importance=concept.importance,
                aliases=aliases,
                file_path=file_path,
            )
            record = await result.single()
            return record["id"]

    async def create_relationship(
        self,
        source_id: str,
        target_id: str,
        relationship_type: str,
        properties: Optional[dict] = None,
    ):
        """
        Create a relationship between two nodes.

        Args:
            source_id: ID of the source node
            target_id: ID of the target node
            relationship_type: Type of relationship (RELATES_TO, EXTENDS, etc.)
            properties: Optional properties dict for the relationship
        """
        await self._ensure_initialized()

        # Sanitize relationship type for Cypher
        rel_type = relationship_type.upper().replace("-", "_").replace(" ", "_")
        query = CREATE_RELATIONSHIP.format(rel_type=rel_type)

        async with self._async_driver.session(
            database=settings.NEO4J_DATABASE
        ) as session:
            await session.run(
                query,
                source_id=source_id,
                target_id=target_id,
                properties=properties or {},
            )

    async def link_content_to_concept(
        self,
        content_id: str,
        concept_id: str,
        importance: str = ConceptImportance.SUPPORTING.value,
    ):
        """
        Create a CONTAINS relationship from content to concept.

        Args:
            content_id: ID of the content node
            concept_id: ID of the concept node
            importance: Importance level (CORE, SUPPORTING, TANGENTIAL)
        """
        await self.create_relationship(
            source_id=content_id,
            target_id=concept_id,
            relationship_type="CONTAINS",
            properties={"importance": importance},
        )

    async def link_concept_to_concept(
        self,
        source_name: str,
        target_name: str,
        relationship_type: str,
        properties: Optional[dict] = None,
    ) -> bool:
        """
        Create a relationship between two concepts by canonical name.

        Concepts are merged by canonical_name in Neo4j, so we normalize the
        names before linking. This handles cases like linking "Behavior
        Cloning (BC)" to "Machine Learning" where the canonical names are
        used for matching.

        Args:
            source_name: Name of the source concept (will be normalized)
            target_name: Name of the target concept (will be normalized)
            relationship_type: Type of relationship (EXTENDS, ENABLES, IS_TYPE_OF, etc.)
            properties: Optional properties dict for the relationship

        Returns:
            True if relationship was created, False if either concept doesn't exist
        """
        await self._ensure_initialized()

        # Import here to avoid circular import
        from app.services.processing.concept_dedup import get_canonical_name

        # Normalize concept names for matching
        source_canonical = get_canonical_name(source_name).lower()
        target_canonical = get_canonical_name(target_name).lower()

        # Sanitize relationship type for Cypher
        rel_type = relationship_type.upper().replace("-", "_").replace(" ", "_")
        query = LINK_CONCEPTS_BY_NAME.format(rel_type=rel_type)

        async with self._async_driver.session(
            database=settings.NEO4J_DATABASE
        ) as session:
            result = await session.run(
                query,
                source_canonical=source_canonical,
                target_canonical=target_canonical,
                properties=properties or {},
            )
            record = await result.single()
            return record is not None

    async def find_concept_by_canonical_name(
        self,
        canonical_name: str,
    ) -> Optional[dict]:
        """
        Find a concept by its canonical (normalized) name.

        This is used for deduplication checks before creating new concepts.

        Args:
            canonical_name: Lowercase canonical name to search for

        Returns:
            Dict with concept info if found: {"id": str, "name": str, "definition": str}
            None if no matching concept exists
        """
        await self._ensure_initialized()

        query = """
        MATCH (c:Concept)
        WHERE c.canonical_name = $canonical_name
        RETURN c.id AS id, c.name AS name, c.definition AS definition
        LIMIT 1
        """

        async with self._async_driver.session(
            database=settings.NEO4J_DATABASE
        ) as session:
            result = await session.run(query, canonical_name=canonical_name)
            record = await result.single()

            if record:
                return {
                    "id": record["id"],
                    "name": record["name"],
                    "definition": record["definition"],
                }
            return None

    async def get_connected_nodes(
        self,
        node_id: str,
        relationship_types: Optional[list[str]] = None,
        max_depth: int = processing_settings.NEO4J_GRAPH_TRAVERSAL_DEPTH,
    ) -> list[dict]:
        """
        Get nodes connected to a given node.

        Traverses the graph from a starting node to find related nodes
        up to max_depth hops away.

        Args:
            node_id: Starting node ID
            relationship_types: Optional list of relationship types to follow
            max_depth: Maximum traversal depth (default 2)

        Returns:
            List of connected node dictionaries
        """
        await self._ensure_initialized()

        rel_filter = ""
        if relationship_types:
            rel_filter = ":" + "|".join(relationship_types)

        query = GET_CONNECTED_NODES.format(rel_filter=rel_filter, max_depth=max_depth)

        async with self._async_driver.session(
            database=settings.NEO4J_DATABASE
        ) as session:
            result = await session.run(query, node_id=node_id)
            return [dict(record) async for record in result]

    async def get_content_by_id(self, content_id: str) -> Optional[dict]:
        """
        Get a content node by its ID.

        Args:
            content_id: Content UUID

        Returns:
            Content node dict or None if not found
        """
        await self._ensure_initialized()

        async with self._async_driver.session(
            database=settings.NEO4J_DATABASE
        ) as session:
            result = await session.run(GET_CONTENT_BY_ID, id=content_id)
            record = await result.single()
            return dict(record) if record else None

    async def delete_content_node(self, content_id: str) -> bool:
        """
        Delete a content node and its relationships.

        Args:
            content_id: Content UUID to delete

        Returns:
            True if deleted, False if not found
        """
        await self._ensure_initialized()

        async with self._async_driver.session(
            database=settings.NEO4J_DATABASE
        ) as session:
            result = await session.run(DELETE_CONTENT_AND_RELATIONS, id=content_id)
            record = await result.single()
            return bool(record and record.get("deleted"))

    async def delete_content_relationships(self, content_id: str) -> int:
        """
        Delete all outgoing relationships from a content node.

        Used when reprocessing content to clear old relationships
        before creating new ones.

        Args:
            content_id: Content UUID

        Returns:
            Number of relationships deleted
        """
        await self._ensure_initialized()

        async with self._async_driver.session(
            database=settings.NEO4J_DATABASE
        ) as session:
            result = await session.run(
                DELETE_CONTENT_OUTGOING_RELATIONSHIPS, id=content_id
            )
            record = await result.single()
            return record["deleted_count"] if record else 0

    # =========================================================================
    # Obsidian Vault Sync Operations (Note nodes)
    # =========================================================================
    # Note nodes represent Obsidian vault files for graph visualization.
    # They are distinct from Content nodes (which have embeddings and summaries).

    async def merge_note_node(
        self,
        node_id: str,
        title: str,
        note_type: str,
        tags: list[str],
        file_path: Optional[str] = None,
        source_url: Optional[str] = None,
    ) -> str:
        """
        Create or update a Note node from an Obsidian vault file.

        Note nodes are lightweight representations of vault files used for
        link visualization and graph navigation. Unlike Content nodes, they
        don't have embeddings or summaries.

        Args:
            node_id: Unique identifier (from frontmatter or generated UUID)
            title: Note title (from frontmatter or filename)
            note_type: Content type (paper, article, daily, etc.)
            tags: Combined frontmatter and inline tags
            file_path: Relative path to the note file from vault root
            source_url: Original source URL if available (from frontmatter)

        Returns:
            The node's ID
        """
        await self._ensure_initialized()

        async with self._async_driver.session(
            database=settings.NEO4J_DATABASE
        ) as session:
            result = await session.run(
                MERGE_NOTE_NODE,
                node_id=node_id,
                title=title,
                note_type=note_type,
                tags=tags,
                file_path=file_path,
                source_url=source_url,
            )
            record = await result.single()
            return record["id"]

    async def sync_note_links(self, source_id: str, target_ids: list[str]) -> int:
        """
        Synchronize outgoing wikilinks for a Note node.

        Uses delete-and-recreate strategy: clears existing LINKS_TO relationships
        then creates new ones. Target notes are created as placeholders if they
        don't exist yet.

        Args:
            source_id: ID of the source Note node
            target_ids: List of target Note IDs (from extracted wikilinks)

        Returns:
            Number of links created
        """
        await self._ensure_initialized()

        async with self._async_driver.session(
            database=settings.NEO4J_DATABASE
        ) as session:
            # Clear existing links
            await session.run(DELETE_NOTE_OUTGOING_LINKS, source_id=source_id)

            # Create new links
            for target_id in target_ids:
                await session.run(
                    CREATE_NOTE_LINK,
                    source_id=source_id,
                    target_id=target_id,
                )

            return len(target_ids)

    # =========================================================================
    # Content-Note Linking Operations
    # =========================================================================
    # These methods bridge Content nodes (from LLM processing) with Note nodes
    # (from vault sync), connecting them via REPRESENTS relationships when they
    # share the same file_path.

    async def link_content_to_note_by_path(self, file_path: str) -> Optional[dict]:
        """
        Create a REPRESENTS relationship between Content and Note with same file_path.

        This bridges the processed content (Content node with embeddings, summaries)
        with its Obsidian vault representation (Note node with wikilinks).

        Args:
            file_path: Relative path to the note file from vault root

        Returns:
            Dict with content_id and note_id if linked, None if no match found
        """
        await self._ensure_initialized()

        async with self._async_driver.session(
            database=settings.NEO4J_DATABASE
        ) as session:
            result = await session.run(
                LINK_CONTENT_TO_NOTE_BY_FILE_PATH,
                file_path=file_path,
            )
            record = await result.single()
            if record:
                return {
                    "content_id": record["content_id"],
                    "note_id": record["note_id"],
                }
            return None

    async def find_note_by_file_path(self, file_path: str) -> Optional[dict]:
        """
        Find a Note node by its file path.

        Args:
            file_path: Relative path to the note file from vault root

        Returns:
            Dict with id and title if found, None otherwise
        """
        await self._ensure_initialized()

        async with self._async_driver.session(
            database=settings.NEO4J_DATABASE
        ) as session:
            result = await session.run(
                FIND_NOTE_BY_FILE_PATH,
                file_path=file_path,
            )
            record = await result.single()
            if record:
                return {"id": record["id"], "title": record["title"]}
            return None

    async def find_content_by_file_path(self, file_path: str) -> Optional[dict]:
        """
        Find a Content node by its file path.

        Args:
            file_path: Relative path to the note file from vault root

        Returns:
            Dict with id and title if found, None otherwise
        """
        await self._ensure_initialized()

        async with self._async_driver.session(
            database=settings.NEO4J_DATABASE
        ) as session:
            result = await session.run(
                FIND_CONTENT_BY_FILE_PATH,
                file_path=file_path,
            )
            record = await result.single()
            if record:
                return {"id": record["id"], "title": record["title"]}
            return None

    async def link_all_content_to_notes(self) -> int:
        """
        Create REPRESENTS relationships for all Content/Note pairs with matching file_paths.

        This is a backfill operation to link existing Content and Note nodes
        that were created before this linking feature was added.

        Returns:
            Number of new REPRESENTS relationships created
        """
        await self._ensure_initialized()

        async with self._async_driver.session(
            database=settings.NEO4J_DATABASE
        ) as session:
            result = await session.run(LINK_ALL_CONTENT_TO_NOTES)
            record = await result.single()
            return record["linked_count"] if record else 0

    # =========================================================================
    # Graph Visualization Operations
    # =========================================================================

    async def get_all_graph_data(self) -> dict:
        """
        Get all nodes and relationships from the knowledge graph.

        Returns the full graph structure with nodes and relationships
        for visualization purposes.

        Returns:
            Dict with "nodes" and "relationships" lists, or message if not connected
        """
        await self._ensure_initialized()

        async with self._async_driver.session(
            database=settings.NEO4J_DATABASE
        ) as session:
            result = await session.run(GET_ALL_GRAPH_DATA)
            nodes = []
            rels = []
            seen = set()

            async for record in result:
                n = record["n"]
                m = record["m"]
                r = record["r"]

                if n.id not in seen:
                    nodes.append({"id": n.id, "labels": list(n.labels), **dict(n)})
                    seen.add(n.id)

                if m.id not in seen:
                    nodes.append({"id": m.id, "labels": list(m.labels), **dict(m)})
                    seen.add(m.id)

                rels.append(
                    {
                        "start": r.start_node.id,
                        "end": r.end_node.id,
                        "type": r.type,
                    }
                )

            return {"nodes": nodes, "relationships": rels}


# Singleton instance
_client: Optional[Neo4jClient] = None


async def get_neo4j_client() -> Neo4jClient:
    """
    Get or create singleton Neo4j client.

    Returns:
        Shared Neo4jClient instance
    """
    global _client
    if _client is None:
        _client = Neo4jClient()
    return _client


async def close_neo4j_client():
    """Close the singleton client connection."""
    global _client
    if _client:
        await _client.close()
        _client = None
