"""
Output Generators

Generate final outputs from processing results:

- obsidian_generator: Creates Obsidian-compatible markdown notes
- neo4j_generator: Creates knowledge graph nodes and relationships

Each generator takes a ProcessingResult and creates persistent artifacts.
"""

from app.services.processing.output.obsidian_generator import generate_obsidian_note
from app.services.processing.output.neo4j_generator import create_knowledge_nodes

__all__ = ["generate_obsidian_note", "create_knowledge_nodes"]
