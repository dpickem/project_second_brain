"""
Assistant Service

Core service for AI assistant functionality including:
- RAG-powered chat conversations
- Conversation management (CRUD)
- Prompt suggestions (powered by MasteryService)
- Study recommendations (powered by MasteryService + SpacedRepService)
- Quiz generation (powered by ExerciseGenerator)
- Concept explanations

Usage:
    service = AssistantService(db, neo4j_client, llm_client)
    response = await service.chat(conversation_id, message)
"""

import logging
import uuid
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import settings
from app.db.models_assistant import (
    AssistantConversation,
    AssistantMessage,
    MessageRole,
)
from app.enums.api import ExplanationStyle
from app.enums.pipeline import PipelineOperation
from app.models.assistant import (
    ChatResponse,
    ConversationDetail,
    ConversationListResponse,
    ConversationUpdateResponse,
    ExplanationResponse,
    KnowledgeSearchResponse,
    KnowledgeSearchResult,
    PromptSuggestion,
    QuizQuestion,
    QuizResponse,
    RecommendationsResponse,
    RelatedConcept,
    SourceReference,
    StudyRecommendation,
    SuggestionsResponse,
)
from app.models.learning import ExerciseGenerateRequest
from app.services.cost_tracking import CostTracker
from app.services.knowledge_graph import KnowledgeSearchService, Neo4jClient
from app.services.learning.exercise_generator import ExerciseGenerator
from app.services.learning.mastery_service import MasteryService
from app.services.learning.spaced_rep_service import SpacedRepService
from app.services.llm.client import LLMClient, get_default_text_model
from app.services.assistant.conversation_manager import ConversationManager

logger = logging.getLogger(__name__)


# =============================================================================
# Constants
# =============================================================================

# System prompt for the assistant
ASSISTANT_SYSTEM_PROMPT = """You are a knowledgeable AI assistant for a personal \
knowledge management system called Second Brain. Your role is to help the user:

1. Explore and understand their saved knowledge (papers, articles, notes, concepts)
2. Make connections between different pieces of information
3. Answer questions using the knowledge base as context
4. Suggest areas for learning and review

When answering questions:
- Use the provided context from the knowledge base when available
- Be clear about what comes from the user's knowledge base vs general knowledge
- Provide helpful explanations and make connections between concepts
- Suggest related topics the user might want to explore

Keep responses focused, helpful, and well-structured. Use markdown formatting \
when appropriate."""


# =============================================================================
# Service Implementation
# =============================================================================


class AssistantService:
    """
    Service for AI assistant operations.

    Provides RAG-powered chat, conversation management, suggestions,
    recommendations, quiz generation, and concept explanations.

    Integrates with learning services:
    - MasteryService: For weak spot detection and study recommendations
    - SpacedRepService: For due card information
    - ExerciseGenerator: For quiz/exercise generation

    Attributes:
        db: Async database session for conversation persistence.
        neo4j: Optional Neo4j client for knowledge graph queries.
        llm: Optional LLM client for chat completions.
        mastery_service: Service for mastery tracking and weak spots.
        spaced_rep_service: Service for spaced repetition cards.
        exercise_generator: Service for exercise/quiz generation.

    Example:
        >>> service = AssistantService(db, neo4j_client, llm_client)
        >>> response = await service.chat(message="What is ML?")
        >>> print(response.response)
    """

    def __init__(
        self,
        db: AsyncSession,
        neo4j_client: Optional[Neo4jClient] = None,
        llm_client: Optional[LLMClient] = None,
    ) -> None:
        """
        Initialize the assistant service.

        Args:
            db: Database session for conversation persistence.
            neo4j_client: Neo4j client for knowledge graph queries.
                If None, RAG context retrieval is disabled.
            llm_client: LLM client for chat completions.
                If None, responses return an error message.
        """
        self.db = db
        self.neo4j = neo4j_client
        self.llm = llm_client

        # Initialize conversation manager
        self._conversation_manager = ConversationManager(db)

        # Initialize learning services (lazy)
        self._mastery_service: Optional[MasteryService] = None
        self._spaced_rep_service: Optional[SpacedRepService] = None
        self._exercise_generator: Optional[ExerciseGenerator] = None

    @property
    def conversation_manager(self) -> ConversationManager:
        """Access to conversation manager for CRUD operations."""
        return self._conversation_manager

    @property
    def mastery_service(self) -> MasteryService:
        """Lazy-initialized MasteryService."""
        if self._mastery_service is None:
            self._mastery_service = MasteryService(self.db)
        return self._mastery_service

    @property
    def spaced_rep_service(self) -> SpacedRepService:
        """Lazy-initialized SpacedRepService."""
        if self._spaced_rep_service is None:
            self._spaced_rep_service = SpacedRepService(self.db)
        return self._spaced_rep_service

    @property
    def exercise_generator(self) -> Optional[ExerciseGenerator]:
        """Lazy-initialized ExerciseGenerator (requires LLM client)."""
        if self._exercise_generator is None and self.llm:
            self._exercise_generator = ExerciseGenerator(
                llm_client=self.llm,
                db=self.db,
            )
        return self._exercise_generator

    # =========================================================================
    # Private Helper Methods
    # =========================================================================

    def _format_context(self, results: list[dict]) -> str:
        """
        Format search results as context for the LLM.

        Creates a bulleted list of relevant items from the knowledge base,
        truncating summaries to ASSISTANT_MAX_SUMMARY_LENGTH characters.

        Args:
            results: List of search result dictionaries with 'title' and
                optional 'summary' keys.

        Returns:
            Formatted context string, or empty string if no results.
        """
        if not results:
            return ""

        context_parts = ["Relevant information from your knowledge base:\n"]
        for r in results:
            title = r.get("title", "Untitled")
            summary = r.get("summary", "")
            if summary:
                # Truncate long summaries
                truncated = summary[: settings.ASSISTANT_MAX_SUMMARY_LENGTH]
                context_parts.append(f"- {title}: {truncated}")
            else:
                context_parts.append(f"- {title}")

        return "\n".join(context_parts)

    async def _search_knowledge_base(
        self,
        query: str,
        limit: Optional[int] = None,
        min_score: Optional[float] = None,
    ) -> list[dict]:
        """
        Search the knowledge base for relevant content.

        Helper method that handles the common pattern of creating a
        KnowledgeSearchService and executing a semantic search.

        Args:
            query: Search query string.
            limit: Maximum number of results. Defaults to ASSISTANT_CHAT_SEARCH_LIMIT.
            min_score: Minimum relevance score threshold. Defaults to ASSISTANT_CHAT_SEARCH_MIN_SCORE.

        Returns:
            List of search result dictionaries.

        Raises:
            Exception: If search fails (caught and logged by caller).
        """
        if not self.neo4j:
            return []

        # Use settings defaults if not specified
        limit = limit or settings.ASSISTANT_CHAT_SEARCH_LIMIT
        min_score = min_score or settings.ASSISTANT_CHAT_SEARCH_MIN_SCORE

        search_service = KnowledgeSearchService(self.neo4j, self.llm)
        results, _ = await search_service.semantic_search(
            query=query,
            limit=limit,
            min_score=min_score,
        )
        return results

    async def _get_conversation_history(
        self,
        conversation: AssistantConversation,
        max_messages: Optional[int] = None,
    ) -> list[dict[str, str]]:
        """
        Get recent conversation history for context.

        Args:
            conversation: The conversation to get history from.
            max_messages: Maximum number of messages to include.

        Returns:
            List of message dictionaries with 'role' and 'content' keys,
            formatted for the LLM messages API.
        """
        max_messages = max_messages or settings.ASSISTANT_MAX_HISTORY_MESSAGES
        messages = conversation.messages[-max_messages:]
        return [
            {
                "role": msg.role.value,
                "content": msg.content,
            }
            for msg in messages
        ]

    async def _generate_response(
        self,
        message: str,
        context: str = "",
        history: Optional[list[dict[str, str]]] = None,
    ) -> str:
        """
        Generate a response using the LLM.

        Args:
            message: User's current message.
            context: Optional RAG context from knowledge base.
            history: Optional conversation history (excludes current message).

        Returns:
            Generated response text, or error message if LLM unavailable.
        """
        if not self.llm:
            return (
                "I apologize, but I'm currently unable to generate responses. "
                "The AI service is not available."
            )

        # Build messages for the LLM
        messages: list[dict[str, str]] = [
            {"role": "system", "content": ASSISTANT_SYSTEM_PROMPT}
        ]

        # Add conversation history (excluding the current message which will be added separately)
        if history:
            messages.extend(history[:-1])

        # Build user message with context
        user_content = message
        if context:
            user_content = f"{context}\n\nUser question: {message}"

        messages.append({"role": "user", "content": user_content})

        try:
            response, usage = await self.llm.complete(
                operation=PipelineOperation.CONTENT_ANALYSIS,
                messages=messages,
                model=get_default_text_model(),
                temperature=settings.ASSISTANT_LLM_TEMPERATURE,
                max_tokens=settings.ASSISTANT_LLM_MAX_TOKENS,
            )
            # Track LLM usage for cost monitoring
            if usage:
                usage.pipeline = "assistant"
                usage.operation = "chat_response"
                await CostTracker.log_usage(usage)
            return str(response) if not isinstance(response, str) else response
        except Exception as e:
            logger.error(f"LLM completion failed: {e}")
            return (
                "I apologize, but I encountered an error while generating a "
                "response. Please try again."
            )

    # =========================================================================
    # Conversation Persistence Methods (delegated to ConversationManager)
    # =========================================================================

    async def _create_conversation(self, first_message: str) -> AssistantConversation:
        """Create a new conversation. Delegates to ConversationManager."""
        return await self._conversation_manager.create_conversation(first_message)

    async def _get_conversation(
        self, conversation_id: str
    ) -> Optional[AssistantConversation]:
        """Get conversation by ID. Delegates to ConversationManager."""
        return await self._conversation_manager.get_conversation_by_id(conversation_id)

    async def _add_message(
        self,
        conversation: AssistantConversation,
        role: MessageRole,
        content: str,
    ) -> AssistantMessage:
        """Add message to conversation. Delegates to ConversationManager."""
        return await self._conversation_manager.add_message(conversation, role, content)

    # =========================================================================
    # Chat Methods
    # =========================================================================

    async def chat(
        self,
        message: str,
        conversation_id: Optional[str] = None,
    ) -> ChatResponse:
        """
        Send a message to the assistant and get a response.

        Uses RAG to retrieve relevant context from the knowledge base
        before generating a response.

        Args:
            message: User's message text.
            conversation_id: Existing conversation UUID, or None to create new.

        Returns:
            ChatResponse with conversation_id, response text, and sources.

        Raises:
            ValueError: If conversation_id is provided but not found.

        Example:
            >>> response = await service.chat("What is machine learning?")
            >>> print(response.response)
            Machine learning is...
        """
        # Get or create conversation
        if conversation_id:
            conversation = await self._get_conversation(conversation_id)
            if not conversation:
                raise ValueError(f"Conversation not found: {conversation_id}")
        else:
            conversation = await self._create_conversation(message)

        # Save user message
        await self._add_message(conversation, MessageRole.USER, message)

        # Search knowledge base for relevant context
        sources: list[SourceReference] = []
        context = ""

        if self.neo4j and self.llm:
            try:
                results = await self._search_knowledge_base(query=message)
                if results:
                    context = self._format_context(results)
                    sources = [
                        SourceReference(
                            id=r.get("id", ""),
                            title=r.get("title", "Untitled"),
                            # Clamp relevance to [0, 1]
                            relevance=min(r.get("score", 0), 1.0),
                        )
                        for r in results
                        if r.get("id")
                    ]
            except Exception as e:
                logger.warning(f"Knowledge search failed: {e}")

        # Get conversation history for context
        history = await self._get_conversation_history(conversation)

        # Generate response
        response_text = await self._generate_response(
            message=message,
            context=context,
            history=history,
        )

        # Save assistant response
        await self._add_message(conversation, MessageRole.ASSISTANT, response_text)

        return ChatResponse(
            conversation_id=conversation.conversation_uuid,
            response=response_text,
            sources=sources,
        )

    # =========================================================================
    # Conversation Management (delegated to ConversationManager)
    # =========================================================================

    async def get_conversations(
        self,
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> ConversationListResponse:
        """Get paginated list of conversations. Delegates to ConversationManager."""
        return await self._conversation_manager.get_conversations(limit, offset)

    async def get_conversation(
        self, conversation_id: str
    ) -> Optional[ConversationDetail]:
        """Get a specific conversation with all messages. Delegates to ConversationManager."""
        return await self._conversation_manager.get_conversation(conversation_id)

    async def delete_conversation(self, conversation_id: str) -> bool:
        """Delete a conversation and all its messages. Delegates to ConversationManager."""
        return await self._conversation_manager.delete_conversation(conversation_id)

    async def clear_conversation_messages(self, conversation_id: str) -> int:
        """Clear all messages from a conversation. Delegates to ConversationManager."""
        return await self._conversation_manager.clear_conversation_messages(conversation_id)

    async def clear_all_conversations(self) -> int:
        """Delete all conversations and messages. Delegates to ConversationManager."""
        return await self._conversation_manager.clear_all_conversations()

    async def rename_conversation(
        self,
        conversation_id: str,
        title: str,
    ) -> Optional[ConversationUpdateResponse]:
        """Rename a conversation. Delegates to ConversationManager."""
        return await self._conversation_manager.rename_conversation(conversation_id, title)

    # =========================================================================
    # Suggestions (powered by MasteryService)
    # =========================================================================

    async def get_suggestions(self) -> SuggestionsResponse:
        """
        Get AI-generated prompt suggestions based on learning state.

        Uses MasteryService to identify weak spots and generates
        personalized suggestions based on the user's learning needs.

        Returns:
            SuggestionsResponse with list of suggestions.
        """
        suggestions: list[PromptSuggestion] = []

        # Try to get personalized suggestions from weak spots
        try:
            weak_spots = await self.mastery_service.get_weak_spots(limit=3)
            for ws in weak_spots:
                suggestions.append(
                    PromptSuggestion(
                        text=f"Help me understand {ws.topic} better",
                        category="review",
                        topic_id=ws.topic,
                    )
                )
        except Exception as e:
            logger.debug(f"Could not get weak spot suggestions: {e}")

        # Try to get due card count for suggestion
        try:
            due_response = await self.spaced_rep_service.get_due_cards(limit=1)
            if due_response.total_due > 0:
                suggestions.append(
                    PromptSuggestion(
                        text=f"I have {due_response.total_due} cards due for review. Help me study!",
                        category="review",
                    )
                )
        except Exception as e:
            logger.debug(f"Could not get due cards count: {e}")

        # Add default suggestions if we don't have enough personalized ones
        default_suggestions = [
            PromptSuggestion(
                text="What are the key concepts I should review today?",
                category="review",
            ),
            PromptSuggestion(
                text="What connections exist between my recent notes?",
                category="explore",
            ),
            PromptSuggestion(
                text="Summarize what I've been learning about recently",
                category="learn",
            ),
            PromptSuggestion(
                text="Help me understand the relationship between my saved papers",
                category="explore",
            ),
        ]

        # Add defaults to fill up to at least 5 suggestions
        for suggestion in default_suggestions:
            if len(suggestions) >= 5:
                break
            # Avoid duplicates
            if not any(s.text == suggestion.text for s in suggestions):
                suggestions.append(suggestion)

        return SuggestionsResponse(suggestions=suggestions)

    # =========================================================================
    # Knowledge Search
    # =========================================================================

    async def search_knowledge(self, query: str) -> KnowledgeSearchResponse:
        """
        Search the knowledge base for relevant content.

        Args:
            query: Search query string.

        Returns:
            KnowledgeSearchResponse with list of results, or empty list if unavailable.
        """
        if not self.neo4j:
            return KnowledgeSearchResponse(results=[])

        try:
            results = await self._search_knowledge_base(
                query=query,
                limit=settings.ASSISTANT_KNOWLEDGE_SEARCH_LIMIT,
                min_score=settings.ASSISTANT_KNOWLEDGE_SEARCH_MIN_SCORE,
            )

            return KnowledgeSearchResponse(
                results=[
                    KnowledgeSearchResult(
                        id=r.get("id", ""),
                        title=r.get("title", "Untitled"),
                        snippet=(
                            r.get("summary", "")[: settings.ASSISTANT_SNIPPET_LENGTH]
                            if r.get("summary")
                            else ""
                        ),
                        score=min(r.get("score", 0), 1.0),
                        type=r.get("node_type", "unknown"),
                    )
                    for r in results
                    if r.get("id")
                ]
            )
        except Exception as e:
            logger.error(f"Knowledge search failed: {e}")
            return KnowledgeSearchResponse(results=[])

    # =========================================================================
    # Recommendations (powered by MasteryService + SpacedRepService)
    # =========================================================================

    async def get_recommendations(self) -> RecommendationsResponse:
        """
        Get personalized study recommendations based on learning history.

        Uses MasteryService to identify weak spots and SpacedRepService
        to get due card information for actionable recommendations.

        Returns:
            RecommendationsResponse with list of recommendations.
        """
        recommendations: list[StudyRecommendation] = []

        # Get due cards count for spaced repetition recommendation
        try:
            due_response = await self.spaced_rep_service.get_due_cards(limit=1)
            if due_response.total_due > 0:
                recommendations.append(
                    StudyRecommendation(
                        topic_id="spaced-rep",
                        topic_name="Review Due Cards",
                        reason=f"You have {due_response.total_due} cards due for spaced repetition review",
                        priority="high",
                    )
                )
        except Exception as e:
            logger.debug(f"Could not get due cards: {e}")

        # Get weak spots for targeted practice recommendations
        try:
            weak_spots = await self.mastery_service.get_weak_spots(
                limit=settings.ASSISTANT_QUIZ_CONTEXT_LIMIT
            )
            for ws in weak_spots:
                priority = "high" if ws.mastery_score < 0.3 else "medium"
                recommendations.append(
                    StudyRecommendation(
                        topic_id=ws.topic,
                        topic_name=ws.topic.replace("/", " > ").title(),
                        reason=ws.recommendation,
                        priority=priority,  # type: ignore[arg-type]
                    )
                )
        except Exception as e:
            logger.debug(f"Could not get weak spots: {e}")

        # Add default if no recommendations found
        if not recommendations:
            recommendations = [
                StudyRecommendation(
                    topic_id="general",
                    topic_name="Explore Your Knowledge",
                    reason="Start by reviewing your saved content and notes",
                    priority="medium",
                ),
            ]

        return RecommendationsResponse(recommendations=recommendations)

    # =========================================================================
    # Quiz Generation (powered by ExerciseGenerator)
    # =========================================================================

    async def generate_quiz(
        self,
        topic_id: str,
        question_count: Optional[int] = None,
    ) -> QuizResponse:
        """
        Generate a quiz on a specific topic.

        Uses ExerciseGenerator to create adaptive exercises based on
        the topic and the user's current mastery level.

        Args:
            topic_id: Topic identifier to generate quiz for.
            question_count: Number of questions to generate (default: 5).

        Returns:
            QuizResponse with quiz_id, topic, and generated questions.
            Returns empty questions list if ExerciseGenerator unavailable.
        """
        question_count = question_count or settings.ASSISTANT_DEFAULT_QUIZ_QUESTIONS
        quiz_id = str(uuid.uuid4())

        if not self.exercise_generator:
            return QuizResponse(
                quiz_id=quiz_id,
                topic=topic_id,
                questions=[],
            )

        # Get mastery level for the topic
        mastery_level = 0.5  # Default
        try:
            mastery_state = await self.mastery_service.get_mastery_state(topic_id)
            mastery_level = mastery_state.mastery_score
        except Exception as e:
            logger.debug(f"Could not get mastery for {topic_id}: {e}")

        # Generate exercises using ExerciseGenerator
        questions: list[QuizQuestion] = []
        for _ in range(question_count):
            try:
                request = ExerciseGenerateRequest(topic=topic_id)
                exercise, _usages = await self.exercise_generator.generate_exercise(
                    request=request,
                    mastery_level=mastery_level,
                    ensure_topic=True,  # Auto-create tag if not in database
                )

                # Convert exercise to quiz question format
                questions.append(
                    QuizQuestion(
                        id=exercise.exercise_uuid,
                        question=exercise.prompt,
                        type="free_response",  # type: ignore[arg-type]
                        options=None,  # Exercises are free-response
                    )
                )
            except Exception as e:
                logger.warning(f"Failed to generate quiz question: {e}")
                # Continue with remaining questions

        return QuizResponse(
            quiz_id=quiz_id,
            topic=topic_id,
            questions=questions,
        )

    # =========================================================================
    # Concept Explanations
    # =========================================================================

    async def explain_concept(
        self,
        concept_id: str,
        style: ExplanationStyle = ExplanationStyle.DETAILED,
    ) -> ExplanationResponse:
        """
        Get an AI-generated explanation of a concept.

        Args:
            concept_id: Concept identifier to explain.
            style: Explanation style:
                - SIMPLE: Brief, beginner-friendly
                - DETAILED: Comprehensive with technical details (default)
                - ELI5: Explain Like I'm 5 - simple analogies, no jargon

        Returns:
            ExplanationResponse with explanation, examples, and related concepts.
        """
        if not self.llm:
            return ExplanationResponse(
                concept=concept_id,
                explanation="Unable to generate explanation - AI service unavailable.",
                examples=[],
                related_concepts=[],
            )

        # Get concept context from knowledge base
        concept_context = ""
        related_concepts: list[RelatedConcept] = []

        if self.neo4j:
            try:
                results = await self._search_knowledge_base(
                    query=concept_id,
                    limit=settings.ASSISTANT_QUIZ_CONTEXT_LIMIT,
                    min_score=settings.ASSISTANT_KNOWLEDGE_SEARCH_MIN_SCORE,
                )
                if results:
                    concept_context = self._format_context(results)
                    # Skip first result (likely the concept itself), take next 3
                    related_concepts = [
                        RelatedConcept(id=r.get("id", ""), name=r.get("title", ""))
                        for r in results[1:4]
                        if r.get("id")
                    ]
            except Exception as e:
                logger.warning(f"Could not get concept context: {e}")

        # Build style-specific instructions
        style_instructions: dict[ExplanationStyle, str] = {
            ExplanationStyle.SIMPLE: "Provide a brief, straightforward explanation suitable for beginners.",
            ExplanationStyle.DETAILED: "Provide a comprehensive explanation with technical details.",
            ExplanationStyle.ELI5: "Explain like I'm 5 years old - use simple analogies and avoid jargon.",
        }
        style_instruction = style_instructions.get(
            style, style_instructions[ExplanationStyle.DETAILED]
        )

        prompt = f"""Explain the concept: {concept_id}

{concept_context}

{style_instruction}

Include:
1. A clear explanation
2. 2-3 practical examples

Return as JSON with format:
{{"explanation": "...", "examples": ["example 1", "example 2"]}}"""

        try:
            response, usage = await self.llm.complete(
                operation=PipelineOperation.CONTENT_ANALYSIS,
                messages=[{"role": "user", "content": prompt}],
                model=get_default_text_model(),
                temperature=settings.ASSISTANT_LLM_TEMPERATURE,
                max_tokens=settings.ASSISTANT_LLM_MAX_TOKENS,
                json_mode=True,
            )
            # Track LLM usage for cost monitoring
            if usage:
                usage.pipeline = "assistant"
                usage.operation = "concept_explanation"
                await CostTracker.log_usage(usage)

            # Handle response (could be dict or str if json_mode failed)
            explanation = ""
            examples: list[str] = []
            if isinstance(response, dict):
                explanation = response.get("explanation", "")
                examples = response.get("examples", [])

            return ExplanationResponse(
                concept=concept_id,
                explanation=explanation,
                examples=examples,
                related_concepts=related_concepts,
            )

        except Exception as e:
            logger.error(f"Concept explanation failed: {e}")
            return ExplanationResponse(
                concept=concept_id,
                explanation="Unable to generate explanation due to an error.",
                examples=[],
                related_concepts=related_concepts,
            )
