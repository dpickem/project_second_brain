"""
Assistant Service Package

Provides AI assistant functionality including:
- Chat conversations with RAG (Retrieval Augmented Generation)
- Prompt suggestions based on knowledge base
- Study recommendations based on learning history
- Quiz generation
- Concept explanations

Usage:
    from app.services.assistant import AssistantService

    service = AssistantService(db, neo4j_client, llm_client)
    response = await service.chat(conversation_id, message)
"""

from app.services.assistant.service import AssistantService

__all__ = ["AssistantService"]
