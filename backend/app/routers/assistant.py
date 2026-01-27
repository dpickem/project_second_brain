"""
Assistant API Router

Exposes AI assistant and chat operations via REST API.

Endpoints:
    POST /api/assistant/chat                              - Send message to assistant
    GET  /api/assistant/conversations                     - List conversations
    GET  /api/assistant/conversations/{id}                - Get conversation with messages
    DELETE /api/assistant/conversations/{id}              - Delete conversation
    PATCH /api/assistant/conversations/{id}               - Rename conversation
    DELETE /api/assistant/conversations/{id}/messages     - Clear conversation messages
    DELETE /api/assistant/conversations                   - Delete all conversations
    GET  /api/assistant/suggestions                       - Get prompt suggestions
    GET  /api/assistant/search                            - Search knowledge base
    GET  /api/assistant/recommendations                   - Get study recommendations
    POST /api/assistant/quiz                              - Generate quiz
    GET  /api/assistant/explain/{concept_id}              - Explain concept

Models are defined in app.models.assistant.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_db
from app.enums import ExplanationStyle
from app.middleware.error_handling import handle_endpoint_errors
from app.models.assistant import (
    ChatRequest,
    ChatResponse,
    ConversationDetail,
    ConversationListResponse,
    ConversationUpdateRequest,
    ConversationUpdateResponse,
    DeleteResponse,
    ExplanationResponse,
    KnowledgeSearchResponse,
    QuizRequest,
    QuizResponse,
    RecommendationsResponse,
    SuggestionsResponse,
)
from app.services.assistant import AssistantService
from app.services.knowledge_graph import get_neo4j_client
from app.services.llm import get_llm_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/assistant", tags=["assistant"])


# =============================================================================
# Dependency Injection
# =============================================================================


async def get_assistant_service(
    db: AsyncSession = Depends(get_db),
) -> AssistantService:
    """
    Get assistant service with all dependencies.

    Attempts to initialize Neo4j and LLM clients, but gracefully
    degrades if they are unavailable.

    Args:
        db: Async database session from FastAPI dependency injection.

    Returns:
        Configured AssistantService instance.
    """
    neo4j_client = None
    llm_client = None

    # Initialize optional clients with graceful degradation
    try:
        neo4j_client = await get_neo4j_client()
        await neo4j_client._ensure_initialized()
    except Exception as e:
        logger.warning(f"Neo4j client not available: {e}")

    try:
        llm_client = get_llm_client()
    except Exception as e:
        logger.warning(f"LLM client not available: {e}")

    return AssistantService(db, neo4j_client, llm_client)


# =============================================================================
# Chat Endpoints
# =============================================================================


@router.post("/chat", response_model=ChatResponse)
@handle_endpoint_errors("Chat")
async def send_message(
    request: ChatRequest,
    service: AssistantService = Depends(get_assistant_service),
) -> ChatResponse:
    """
    Send a message to the AI assistant and get a response.

    Args:
        request: Chat request with message and optional conversation_id.
        service: Injected assistant service.

    Returns:
        ChatResponse with conversation_id, response, and sources.

    Raises:
        HTTPException 404: If specified conversation not found.
        HTTPException 500: If chat processing fails.
    """
    return await service.chat(
        message=request.message,
        conversation_id=request.conversation_id,
    )


# =============================================================================
# Conversation Endpoints
# =============================================================================


@router.get("/conversations", response_model=ConversationListResponse)
@handle_endpoint_errors("Get conversations")
async def get_conversations(
    limit: int = Query(20, ge=1, le=100, description="Max conversations to return"),
    offset: int = Query(0, ge=0, description="Number to skip for pagination"),
    service: AssistantService = Depends(get_assistant_service),
) -> ConversationListResponse:
    """
    Get paginated list of all conversations.

    Args:
        limit: Maximum conversations to return (1-100).
        offset: Number to skip for pagination.
        service: Injected assistant service.

    Returns:
        ConversationListResponse with conversations and total count.

    Raises:
        HTTPException 500: If retrieval fails.
    """
    return await service.get_conversations(limit=limit, offset=offset)


@router.get("/conversations/{conversation_id}", response_model=ConversationDetail)
@handle_endpoint_errors("Get conversation")
async def get_conversation(
    conversation_id: str,
    service: AssistantService = Depends(get_assistant_service),
) -> ConversationDetail:
    """
    Get a specific conversation with all its messages.

    Args:
        conversation_id: Unique conversation identifier.
        service: Injected assistant service.

    Returns:
        ConversationDetail with messages.

    Raises:
        HTTPException 404: If conversation not found.
        HTTPException 500: If retrieval fails.
    """
    result = await service.get_conversation(conversation_id)

    if not result:
        raise HTTPException(status_code=404, detail="Conversation not found")

    return result


@router.delete("/conversations/{conversation_id}", response_model=DeleteResponse)
@handle_endpoint_errors("Delete conversation")
async def delete_conversation(
    conversation_id: str,
    service: AssistantService = Depends(get_assistant_service),
) -> DeleteResponse:
    """
    Delete a conversation and all its messages.

    Args:
        conversation_id: Unique conversation identifier.
        service: Injected assistant service.

    Returns:
        DeleteResponse with success status.

    Raises:
        HTTPException 404: If conversation not found.
        HTTPException 500: If deletion fails.
    """
    deleted = await service.delete_conversation(conversation_id)

    if not deleted:
        raise HTTPException(status_code=404, detail="Conversation not found")

    return DeleteResponse(success=True, deleted_id=conversation_id)


@router.patch(
    "/conversations/{conversation_id}", response_model=ConversationUpdateResponse
)
@handle_endpoint_errors("Rename conversation")
async def rename_conversation(
    conversation_id: str,
    request: ConversationUpdateRequest,
    service: AssistantService = Depends(get_assistant_service),
) -> ConversationUpdateResponse:
    """
    Rename a conversation.

    Args:
        conversation_id: Unique conversation identifier.
        request: Update request with new title.
        service: Injected assistant service.

    Returns:
        ConversationUpdateResponse with updated metadata.

    Raises:
        HTTPException 404: If conversation not found.
        HTTPException 500: If update fails.
    """
    result = await service.rename_conversation(conversation_id, request.title)

    if not result:
        raise HTTPException(status_code=404, detail="Conversation not found")

    return result


@router.delete(
    "/conversations/{conversation_id}/messages", response_model=DeleteResponse
)
@handle_endpoint_errors("Clear messages")
async def clear_conversation_messages(
    conversation_id: str,
    service: AssistantService = Depends(get_assistant_service),
) -> DeleteResponse:
    """
    Clear all messages from a conversation.

    Args:
        conversation_id: Unique conversation identifier.
        service: Injected assistant service.

    Returns:
        DeleteResponse with count of cleared messages.

    Raises:
        HTTPException 500: If clearing fails.
    """
    count = await service.clear_conversation_messages(conversation_id)
    return DeleteResponse(success=True, cleared_count=count)


@router.delete("/conversations", response_model=DeleteResponse)
@handle_endpoint_errors("Clear all conversations")
async def clear_all_conversations(
    service: AssistantService = Depends(get_assistant_service),
) -> DeleteResponse:
    """
    Delete all conversations and messages.

    Args:
        service: Injected assistant service.

    Returns:
        DeleteResponse with count of cleared conversations.

    Raises:
        HTTPException 500: If clearing fails.
    """
    count = await service.clear_all_conversations()
    return DeleteResponse(success=True, cleared_count=count)


# =============================================================================
# Suggestions Endpoint
# =============================================================================


@router.get("/suggestions", response_model=SuggestionsResponse)
@handle_endpoint_errors("Get suggestions")
async def get_suggestions(
    service: AssistantService = Depends(get_assistant_service),
) -> SuggestionsResponse:
    """
    Get AI-generated prompt suggestions based on current knowledge base.

    Args:
        service: Injected assistant service.

    Returns:
        SuggestionsResponse with list of suggested prompts.

    Raises:
        HTTPException 500: If suggestion generation fails.
    """
    return await service.get_suggestions()


# =============================================================================
# Search Endpoint
# =============================================================================


@router.get("/search", response_model=KnowledgeSearchResponse)
@handle_endpoint_errors("Search")
async def search_knowledge(
    q: str = Query(..., min_length=1, max_length=500, description="Search query"),
    service: AssistantService = Depends(get_assistant_service),
) -> KnowledgeSearchResponse:
    """
    Search knowledge base for content relevant to a query.

    Args:
        q: Search query string.
        service: Injected assistant service.

    Returns:
        KnowledgeSearchResponse with search results.

    Raises:
        HTTPException 500: If search fails.
    """
    return await service.search_knowledge(q)


# =============================================================================
# Recommendations Endpoint
# =============================================================================


@router.get("/recommendations", response_model=RecommendationsResponse)
@handle_endpoint_errors("Get recommendations")
async def get_recommendations(
    service: AssistantService = Depends(get_assistant_service),
) -> RecommendationsResponse:
    """
    Get personalized study recommendations based on learning history.

    Args:
        service: Injected assistant service.

    Returns:
        RecommendationsResponse with prioritized study recommendations.

    Raises:
        HTTPException 500: If recommendation generation fails.
    """
    return await service.get_recommendations()


# =============================================================================
# Quiz Endpoint
# =============================================================================


@router.post("/quiz", response_model=QuizResponse)
@handle_endpoint_errors("Quiz generation")
async def generate_quiz(
    request: QuizRequest,
    service: AssistantService = Depends(get_assistant_service),
) -> QuizResponse:
    """
    Generate a quiz on a specific topic.

    Args:
        request: Quiz parameters (topic_id and question_count).
        service: Injected assistant service.

    Returns:
        QuizResponse with generated questions.

    Raises:
        HTTPException 500: If quiz generation fails.
    """
    return await service.generate_quiz(
        topic_id=request.topic_id,
        question_count=request.question_count,
    )


# =============================================================================
# Explanation Endpoint
# =============================================================================


@router.get("/explain/{concept_id}", response_model=ExplanationResponse)
@handle_endpoint_errors("Explanation")
async def explain_concept(
    concept_id: str,
    style: ExplanationStyle = Query(
        "detailed",
        description="Explanation style: 'simple', 'detailed', or 'eli5'",
    ),
    service: AssistantService = Depends(get_assistant_service),
) -> ExplanationResponse:
    """
    Get an AI-generated explanation of a concept.

    Args:
        concept_id: Concept identifier to explain.
        style: Explanation style ('simple', 'detailed', or 'eli5').
        service: Injected assistant service.

    Returns:
        ExplanationResponse with explanation, examples, and related concepts.

    Raises:
        HTTPException 500: If explanation generation fails.
    """
    return await service.explain_concept(concept_id, style)
