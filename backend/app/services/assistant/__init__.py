"""
Assistant Service Package

Provides AI assistant functionality including:
- Chat conversations with RAG (Retrieval Augmented Generation)
- Conversation management (CRUD operations)
- Prompt suggestions based on knowledge base
- Study recommendations based on learning history
- Quiz generation
- Concept explanations

Modules:
- service: Main AssistantService with chat and feature methods
- conversation_manager: ConversationManager for conversation CRUD

Usage:
    from app.services.assistant import AssistantService

    service = AssistantService(db, neo4j_client, llm_client)
    response = await service.chat(conversation_id, message)
"""

from app.services.assistant.service import AssistantService
from app.services.assistant.conversation_manager import ConversationManager

__all__ = ["AssistantService", "ConversationManager"]
