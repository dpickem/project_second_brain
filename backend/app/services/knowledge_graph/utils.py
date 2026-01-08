"""
Knowledge Graph Utility Functions

Helper functions for transforming and processing knowledge graph data.

Functions:
    - build_topic_tree: Build hierarchical tree from flat topic list

Usage:
    from app.services.knowledge_graph.utils import build_topic_tree

    flat_topics = [{"path": "ml", "content_count": 10}, ...]
    roots, max_depth = build_topic_tree(flat_topics)
"""

from app.models.knowledge import TopicNode


def build_topic_tree(flat_topics: list[dict]) -> tuple[list[TopicNode], int]:
    """
    Build a hierarchical tree structure from a flat list of topics.

    Topics are organized by slash-separated paths. This function converts
    a flat list from Neo4j query results into a nested tree structure
    suitable for UI rendering.

    Path structure:
        - ml/                           (depth 0)
          - ml/deep-learning/           (depth 1)
            - ml/deep-learning/transformers/  (depth 2)

    Args:
        flat_topics: List of topic dicts from Neo4j query, each containing:
            - path (str): Topic path (e.g., "ml/deep-learning/transformers")
            - content_count (int): Number of content items with this topic

    Returns:
        Tuple of:
            - roots (list[TopicNode]): List of root-level topic nodes with
              nested children
            - max_depth (int): Maximum depth of the tree (0 for single level)

    Example:
        >>> topics = [
        ...     {"path": "ml", "content_count": 10},
        ...     {"path": "ml/deep-learning", "content_count": 5},
        ...     {"path": "ml/deep-learning/transformers", "content_count": 3},
        ... ]
        >>> roots, depth = build_topic_tree(topics)
        >>> roots[0].name
        'ml'
        >>> roots[0].children[0].name
        'deep-learning'
        >>> depth
        2

    Notes:
        - Topics are sorted by path before processing to ensure parents
          exist before their children
        - Orphan topics (with missing parent) are added to roots
        - Returns empty list and 0 depth for empty input
    """
    if not flat_topics:
        return [], 0

    nodes: dict[str, TopicNode] = {}
    roots: list[TopicNode] = []
    max_depth = 0

    # Sort by path to ensure parents come before children
    sorted_topics = sorted(flat_topics, key=lambda x: x["path"])

    for t in sorted_topics:
        path = t["path"]
        parts = path.strip("/").split("/") if "/" in path else [path]
        depth = len(parts) - 1
        max_depth = max(max_depth, depth)

        node = TopicNode(
            path=path,
            name=parts[-1],
            depth=depth,
            content_count=t["content_count"],
            children=[],
        )
        nodes[path] = node

        # Find parent and attach as child
        if depth == 0:
            roots.append(node)
        else:
            parent_path = "/".join(parts[:-1])
            if parent_path in nodes:
                nodes[parent_path].children.append(node)
            else:
                # Orphan topic - parent doesn't exist, add to roots
                roots.append(node)

    return roots, max_depth

