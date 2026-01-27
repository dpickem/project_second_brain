"""
Conversation Manager

Handles CRUD operations for assistant conversations and messages.

This module is extracted from AssistantService to reduce file size
and improve code organization.

Usage:
    manager = ConversationManager(db)
    conversations = await manager.get_conversations(limit=20)
    conversation = await manager.get_conversation(conversation_id)
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config.settings import settings
from app.db.models_assistant import (
    AssistantConversation,
    AssistantMessage,
    MessageRole,
)
from app.models.assistant import (
    ConversationDetail,
    ConversationListResponse,
    ConversationSummary,
    ConversationUpdateResponse,
    MessageInfo,
)

logger = logging.getLogger(__name__)


class ConversationManager:
    """
    Manager for conversation persistence operations.

    Handles creating, reading, updating, and deleting conversations
    and their associated messages.
    """

    def __init__(self, db: AsyncSession):
        """
        Initialize the conversation manager.

        Args:
            db: SQLAlchemy async database session.
        """
        self.db = db

    # =========================================================================
    # Internal Helper Methods
    # =========================================================================

    async def create_conversation(self, first_message: str) -> AssistantConversation:
        """
        Create a new conversation with auto-generated title.

        Title is derived from the first message, truncated to ASSISTANT_MAX_TITLE_LENGTH.

        Args:
            first_message: The user's first message in the conversation.

        Returns:
            The newly created AssistantConversation instance with messages loaded.
        """
        max_len = settings.ASSISTANT_MAX_TITLE_LENGTH
        # Generate title from first message
        title = first_message[:max_len].strip()
        if len(first_message) > max_len:
            title += "..."

        conversation = AssistantConversation(
            conversation_uuid=str(uuid.uuid4()),
            title=title,
        )
        self.db.add(conversation)
        await self.db.flush()

        # Refresh with messages loaded to avoid lazy loading issues in async
        await self.db.refresh(conversation, attribute_names=["messages"])
        return conversation

    async def get_conversation_by_id(
        self, conversation_id: str
    ) -> Optional[AssistantConversation]:
        """
        Get a conversation by UUID with messages eagerly loaded.

        Args:
            conversation_id: Conversation UUID.

        Returns:
            AssistantConversation with messages, or None if not found.
        """
        result = await self.db.execute(
            select(AssistantConversation)
            .options(selectinload(AssistantConversation.messages))
            .where(AssistantConversation.conversation_uuid == conversation_id)
        )
        return result.scalars().first()

    async def add_message(
        self,
        conversation: AssistantConversation,
        role: MessageRole,
        content: str,
    ) -> AssistantMessage:
        """
        Add a message to an existing conversation.

        Also updates the conversation's updated_at timestamp.

        Args:
            conversation: The conversation to add to.
            role: Message role (user or assistant).
            content: Message content.

        Returns:
            The newly created AssistantMessage instance.
        """
        message = AssistantMessage(
            message_uuid=str(uuid.uuid4()),
            conversation_id=conversation.id,
            role=role,
            content=content,
        )
        self.db.add(message)

        # Update conversation timestamp
        conversation.updated_at = datetime.now(timezone.utc)

        await self.db.flush()
        await self.db.refresh(message)

        # Refresh conversation to include new message
        await self.db.refresh(conversation, attribute_names=["messages"])

        return message

    # =========================================================================
    # Public Conversation Management Methods
    # =========================================================================

    async def get_conversations(
        self,
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> ConversationListResponse:
        """
        Get paginated list of conversations.

        Conversations are ordered by updated_at descending (most recent first).

        Args:
            limit: Maximum conversations to return.
            offset: Number to skip for pagination.

        Returns:
            ConversationListResponse with conversations list and total count.
        """
        limit = limit or settings.ASSISTANT_DEFAULT_PAGE_LIMIT

        # Get total count
        count_result = await self.db.execute(
            select(func.count()).select_from(AssistantConversation)
        )
        total = count_result.scalar_one()

        # Get conversations
        result = await self.db.execute(
            select(AssistantConversation)
            .options(selectinload(AssistantConversation.messages))
            .order_by(AssistantConversation.updated_at.desc())
            .offset(offset)
            .limit(limit)
        )
        conversations = result.scalars().all()

        return ConversationListResponse(
            conversations=[
                ConversationSummary(
                    id=c.conversation_uuid,
                    title=c.title,
                    created_at=c.created_at,
                    updated_at=c.updated_at,
                    message_count=len(c.messages),
                )
                for c in conversations
            ],
            total=total,
        )

    async def get_conversation(
        self, conversation_id: str
    ) -> Optional[ConversationDetail]:
        """
        Get a specific conversation with all messages.

        Args:
            conversation_id: Conversation UUID.

        Returns:
            ConversationDetail with messages, or None if not found.
        """
        conversation = await self.get_conversation_by_id(conversation_id)
        if not conversation:
            return None

        return ConversationDetail(
            id=conversation.conversation_uuid,
            title=conversation.title,
            created_at=conversation.created_at,
            messages=[
                MessageInfo(
                    id=m.message_uuid,
                    role=m.role.value,  # type: ignore[arg-type]
                    content=m.content,
                    timestamp=m.created_at,
                )
                for m in conversation.messages
            ],
        )

    async def delete_conversation(self, conversation_id: str) -> bool:
        """
        Delete a conversation and all its messages.

        Messages are cascade-deleted due to database relationship.

        Args:
            conversation_id: Conversation UUID.

        Returns:
            True if deleted, False if not found.
        """
        result = await self.db.execute(
            delete(AssistantConversation).where(
                AssistantConversation.conversation_uuid == conversation_id
            )
        )
        return result.rowcount > 0

    async def clear_conversation_messages(self, conversation_id: str) -> int:
        """
        Clear all messages from a conversation.

        The conversation itself is preserved.

        Args:
            conversation_id: Conversation UUID.

        Returns:
            Number of messages deleted, or 0 if conversation not found.
        """
        conversation = await self.get_conversation_by_id(conversation_id)
        if not conversation:
            return 0

        result = await self.db.execute(
            delete(AssistantMessage).where(
                AssistantMessage.conversation_id == conversation.id
            )
        )
        return result.rowcount

    async def clear_all_conversations(self) -> int:
        """
        Delete all conversations and messages.

        Returns:
            Number of conversations deleted.
        """
        result = await self.db.execute(delete(AssistantConversation))
        return result.rowcount

    async def rename_conversation(
        self,
        conversation_id: str,
        title: str,
    ) -> Optional[ConversationUpdateResponse]:
        """
        Rename a conversation.

        Args:
            conversation_id: Conversation UUID.
            title: New title for the conversation.

        Returns:
            ConversationUpdateResponse with updated info, or None if not found.
        """
        conversation = await self.get_conversation_by_id(conversation_id)
        if not conversation:
            return None

        conversation.title = title
        conversation.updated_at = datetime.now(timezone.utc)
        await self.db.flush()

        return ConversationUpdateResponse(
            id=conversation.conversation_uuid,
            title=conversation.title,
            updated_at=conversation.updated_at,
        )
