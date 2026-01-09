"""
SQLAlchemy Database Models for AI Assistant

Tables:
- assistant_conversations: Chat conversations with the AI assistant
- assistant_messages: Individual messages within conversations

These models support the assistant chat feature with conversation
persistence and message history.
"""

from __future__ import annotations

from datetime import datetime, timezone
import enum

from sqlalchemy import String, Text, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def _utc_now() -> datetime:
    """Return current UTC time as timezone-aware datetime."""
    return datetime.now(timezone.utc)


class MessageRole(enum.Enum):
    """
    Role of a message in a conversation.

    Values:
        USER: Message from the user
        ASSISTANT: Response from the AI assistant
    """

    USER = "user"
    ASSISTANT = "assistant"


class AssistantConversation(Base):
    """
    Chat conversation with the AI assistant.

    Tracks conversation metadata including auto-generated or user-set titles.
    Messages are stored in a separate table with a foreign key relationship.

    Attributes:
        id: Primary key, auto-incrementing integer identifier.
        conversation_uuid: Globally unique UUID string identifier. This is the
            PRIMARY identifier used in API responses. Indexed with unique constraint.
        title: Human-readable title for the conversation. Auto-generated from
            first message or user-set. Max 200 characters.
        created_at: Timestamp when the conversation was started.
        updated_at: Timestamp of last message in the conversation.
        messages: List of messages in this conversation.
    """

    __tablename__ = "assistant_conversations"

    id: Mapped[int] = mapped_column(primary_key=True)

    # Conversation identification
    conversation_uuid: Mapped[str] = mapped_column(
        String(36), unique=True, index=True, nullable=False
    )
    title: Mapped[str] = mapped_column(String(200), default="New Conversation")

    # Timestamps (timezone-aware UTC)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utc_now, onupdate=_utc_now
    )

    # Relationships
    messages: Mapped[list[AssistantMessage]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="AssistantMessage.created_at",
    )


class AssistantMessage(Base):
    """
    Individual message within an assistant conversation.

    Stores both user messages and assistant responses with timestamps.

    Attributes:
        id: Primary key, auto-incrementing integer identifier.
        message_uuid: Globally unique UUID string identifier. Used in API responses.
            Indexed with unique constraint.
        conversation_id: Foreign key to parent conversation.
        role: Message role (USER or ASSISTANT).
        content: Message text content.
        created_at: Timestamp when the message was created.
        conversation: Reference to parent conversation.
    """

    __tablename__ = "assistant_messages"

    id: Mapped[int] = mapped_column(primary_key=True)

    # Message identification
    message_uuid: Mapped[str] = mapped_column(
        String(36), unique=True, index=True, nullable=False
    )

    # Conversation reference
    conversation_id: Mapped[int] = mapped_column(
        ForeignKey("assistant_conversations.id", ondelete="CASCADE"),
        index=True,
    )

    # Message content
    role: Mapped[MessageRole] = mapped_column(SQLEnum(MessageRole), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # Timestamps (timezone-aware UTC)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utc_now
    )

    # Relationships
    conversation: Mapped[AssistantConversation] = relationship(
        back_populates="messages"
    )
