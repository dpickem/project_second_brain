"""
Assistant API Models (Pydantic)

Request/response schemas for the AI Assistant API including:
- Chat conversations and messages
- Prompt suggestions
- Knowledge search
- Study recommendations
- Quiz generation
- Concept explanations

Usage:
    from app.models.assistant import (
        ChatRequest,
        ChatResponse,
        ConversationListResponse,
    )

API Contract:
    Request models use StrictRequest (extra="forbid") to reject unknown fields.
    This catches frontend/backend mismatches early with clear 422 errors.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional, Literal, TYPE_CHECKING

from pydantic import BaseModel, Field

from app.models.base import StrictRequest, StrictResponse

if TYPE_CHECKING:
    from app.db.models_assistant import AssistantConversation, AssistantMessage


# =============================================================================
# Chat Models
# =============================================================================


class ChatRequest(StrictRequest):
    """
    Request to send a message to the AI assistant.

    Attributes:
        conversation_id: Existing conversation ID (null to start new conversation)
        message: User message content

    Note: Uses StrictRequest - unknown fields will be rejected with 422.
    """

    conversation_id: Optional[str] = Field(
        None, description="Conversation ID (null to start new conversation)"
    )
    message: str = Field(..., min_length=1, max_length=10000)


class SourceReference(BaseModel):
    """
    A source referenced by the assistant in its response.

    Attributes:
        id: Content or concept ID
        title: Display title
        relevance: Relevance score (0-1)
    """

    id: str
    title: str
    relevance: float = Field(ge=0, le=1)


class ChatResponse(BaseModel):
    """
    Response from the AI assistant.

    Attributes:
        conversation_id: The conversation this message belongs to
        response: Assistant's response text
        sources: Optional list of referenced sources
    """

    conversation_id: str
    response: str
    sources: list[SourceReference] = Field(default_factory=list)


# =============================================================================
# Conversation Models
# =============================================================================


class MessageInfo(BaseModel):
    """
    A single message in a conversation.

    Attributes:
        id: Message unique identifier
        role: Message role (user or assistant)
        content: Message content
        timestamp: When the message was sent
    """

    id: str
    role: Literal["user", "assistant"]
    content: str
    timestamp: datetime

    @classmethod
    def from_db_record(cls, record: AssistantMessage) -> MessageInfo:
        """
        Create a MessageInfo from a database AssistantMessage record.

        Factory method for converting SQLAlchemy models to Pydantic models
        when loading messages from the database.

        Args:
            record: SQLAlchemy AssistantMessage record from the database

        Returns:
            MessageInfo instance with data from the database record

        Example:
            >>> message = MessageInfo.from_db_record(db_message)
        """
        return cls(
            id=record.message_uuid,
            role=record.role.value,  # Convert enum to string
            content=record.content,
            timestamp=record.created_at,
        )


class ConversationSummary(BaseModel):
    """
    Summary of a conversation for list views.

    Attributes:
        id: Conversation unique identifier
        title: Conversation title (auto-generated or user-set)
        created_at: When the conversation started
        updated_at: When the conversation was last updated
        message_count: Number of messages in the conversation
    """

    id: str
    title: str
    created_at: datetime
    updated_at: datetime
    message_count: int

    @classmethod
    def from_db_record(cls, record: AssistantConversation) -> ConversationSummary:
        """
        Create a ConversationSummary from a database AssistantConversation record.

        Factory method for converting SQLAlchemy models to Pydantic models
        when loading conversation summaries from the database.

        Args:
            record: SQLAlchemy AssistantConversation record from the database

        Returns:
            ConversationSummary instance with data from the database record

        Example:
            >>> summary = ConversationSummary.from_db_record(db_conversation)
        """
        return cls(
            id=record.conversation_uuid,
            title=record.title,
            created_at=record.created_at,
            updated_at=record.updated_at,
            message_count=len(record.messages) if record.messages else 0,
        )


class ConversationListResponse(BaseModel):
    """
    Paginated list of conversations.

    Attributes:
        conversations: List of conversation summaries
        total: Total number of conversations
    """

    conversations: list[ConversationSummary]
    total: int


class ConversationDetail(BaseModel):
    """
    Full conversation with all messages.

    Attributes:
        id: Conversation unique identifier
        title: Conversation title
        created_at: When the conversation started
        messages: All messages in chronological order
    """

    id: str
    title: str
    created_at: datetime
    messages: list[MessageInfo]

    @classmethod
    def from_db_record(cls, record: AssistantConversation) -> ConversationDetail:
        """
        Create a ConversationDetail from a database AssistantConversation record.

        Factory method for converting SQLAlchemy models to Pydantic models
        when loading full conversation details from the database.

        Args:
            record: SQLAlchemy AssistantConversation record from the database
                   (should have messages relationship loaded)

        Returns:
            ConversationDetail instance with data from the database record

        Example:
            >>> detail = ConversationDetail.from_db_record(db_conversation)
        """
        messages = [
            MessageInfo.from_db_record(msg)
            for msg in (record.messages or [])
        ]
        return cls(
            id=record.conversation_uuid,
            title=record.title,
            created_at=record.created_at,
            messages=messages,
        )


class ConversationUpdateRequest(StrictRequest):
    """
    Request to update conversation metadata.

    Attributes:
        title: New title for the conversation

    Note: Uses StrictRequest - unknown fields will be rejected with 422.
    """

    title: str = Field(..., min_length=1, max_length=200)


class ConversationUpdateResponse(BaseModel):
    """
    Response after updating a conversation.

    Attributes:
        id: Conversation unique identifier
        title: Updated title
        updated_at: When the update was made
    """

    id: str
    title: str
    updated_at: datetime


class DeleteResponse(BaseModel):
    """
    Generic deletion response.

    Attributes:
        success: Whether the deletion was successful
        deleted_id: ID of the deleted resource (optional)
        cleared_count: Number of items cleared (optional)
    """

    success: bool
    deleted_id: Optional[str] = None
    cleared_count: Optional[int] = None


# =============================================================================
# Suggestions Models
# =============================================================================


class PromptSuggestion(BaseModel):
    """
    A suggested prompt for the user.

    Attributes:
        text: Suggested prompt text
        category: Category of the suggestion (e.g., "review", "explore", "learn")
        topic_id: Optional related topic ID
    """

    text: str
    category: str
    topic_id: Optional[str] = None


class SuggestionsResponse(BaseModel):
    """
    Response containing prompt suggestions.

    Attributes:
        suggestions: List of suggested prompts
    """

    suggestions: list[PromptSuggestion]


# =============================================================================
# Search Models
# =============================================================================


class KnowledgeSearchResult(BaseModel):
    """
    A single search result from the knowledge base.

    Attributes:
        id: Content or concept ID
        title: Display title
        snippet: Relevant text snippet
        score: Relevance score (0-1)
        type: Type of content (e.g., "paper", "note", "concept")
    """

    id: str
    title: str
    snippet: str
    score: float = Field(ge=0, le=1)
    type: str


class KnowledgeSearchResponse(BaseModel):
    """
    Response containing search results.

    Attributes:
        results: List of matching results
    """

    results: list[KnowledgeSearchResult]


# =============================================================================
# Recommendations Models
# =============================================================================


class StudyRecommendation(BaseModel):
    """
    A personalized study recommendation.

    Attributes:
        topic_id: ID of the recommended topic
        topic_name: Display name of the topic
        reason: Why this topic is recommended
        priority: Recommendation priority
    """

    topic_id: str
    topic_name: str
    reason: str
    priority: Literal["high", "medium", "low"]


class RecommendationsResponse(BaseModel):
    """
    Response containing study recommendations.

    Attributes:
        recommendations: List of recommended topics
    """

    recommendations: list[StudyRecommendation]


# =============================================================================
# Quiz Models
# =============================================================================


class QuizRequest(StrictRequest):
    """
    Request to generate a quiz.

    Attributes:
        topic_id: Topic ID to generate quiz for
        question_count: Number of questions to generate

    Note: Uses StrictRequest - unknown fields will be rejected with 422.
    """

    topic_id: str
    question_count: int = Field(default=5, ge=1, le=20)


class QuizQuestion(BaseModel):
    """
    A single quiz question.

    Attributes:
        id: Question unique identifier
        question: Question text
        options: Multiple choice options (if applicable)
        type: Question type
    """

    id: str
    question: str
    options: Optional[list[str]] = None
    type: Literal["multiple_choice", "free_response"]


class QuizResponse(BaseModel):
    """
    Generated quiz response.

    Attributes:
        quiz_id: Unique identifier for this quiz
        topic: Topic name
        questions: List of quiz questions
    """

    quiz_id: str
    topic: str
    questions: list[QuizQuestion]


# =============================================================================
# Explanation Models
# =============================================================================


class RelatedConcept(BaseModel):
    """
    A concept related to the explained topic.

    Attributes:
        id: Concept ID
        name: Concept name
    """

    id: str
    name: str


class ExplanationResponse(BaseModel):
    """
    AI-generated explanation of a concept.

    Attributes:
        concept: Concept name
        explanation: Detailed explanation text
        examples: Optional list of examples
        related_concepts: Optional list of related concepts
    """

    concept: str
    explanation: str
    examples: list[str] = Field(default_factory=list)
    related_concepts: list[RelatedConcept] = Field(default_factory=list)
