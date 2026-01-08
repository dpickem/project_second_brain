"""
Knowledge Graph related enums.

Defines enums for graph visualization and querying.

Note: For Neo4j storage relationship types, see app.enums.processing.RelationshipType.
This file contains API/visualization-oriented enums.
"""

from enum import Enum


class GraphConnectionType(str, Enum):
    """
    Types of connections displayed in the knowledge graph visualization.

    These represent the semantic relationships users see when exploring
    the graph. Maps to underlying Neo4j relationship types but provides
    a user-friendly API surface.

    Note: For internal Neo4j relationship types used during content processing,
    see app.enums.processing.RelationshipType.

    Values:
        REFERENCES: Cites or references another piece of content
        RELATES_TO: General topical relationship
        PREREQUISITE: Foundational knowledge required to understand
        BUILDS_ON: Extends or continues previous work
        CONTRADICTS: Challenges or refutes claims
        SUPPORTS: Provides evidence or validation
        CONTAINS: Parent contains child (e.g., Content contains Concept)
        LINKS_TO: Explicit hyperlink or cross-reference
    """

    REFERENCES = "REFERENCES"
    RELATES_TO = "RELATES_TO"
    PREREQUISITE = "PREREQUISITE"
    BUILDS_ON = "BUILDS_ON"
    CONTRADICTS = "CONTRADICTS"
    SUPPORTS = "SUPPORTS"
    CONTAINS = "CONTAINS"
    LINKS_TO = "LINKS_TO"


class ConnectionDirection(str, Enum):
    """
    Direction filter for connection queries.

    Used by the /connections/{node_id} endpoint to filter
    relationships by direction relative to the queried node.

    Values:
        INCOMING: Only relationships pointing to the node
        OUTGOING: Only relationships pointing from the node
        BOTH: All relationships (default)
    """

    INCOMING = "incoming"
    OUTGOING = "outgoing"
    BOTH = "both"

