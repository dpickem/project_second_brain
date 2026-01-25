# Assistant Tool Calling Implementation Plan

> **Document Status**: Implementation Plan  
> **Created**: January 2026  
> **Target Phase**: Phase 11 (Assistant Enhancement)  
> **Estimated Effort**: 8-12 days  
> **Design Doc**: `design_docs/09_assistant_tool_calling.md`

---

## 1. Executive Summary

This document provides a detailed implementation plan for adding **tool calling** (function calling) capabilities to the AI Assistant service. Tool calling enables the assistant to take actions on behalf of the user—such as generating exercises, creating flashcards, or searching the knowledge graph—through natural language requests.

### Why Tool Calling Matters

Tool calling transforms the assistant from a passive Q&A interface into an active learning partner:

| Without Tools | With Tools |
|---------------|------------|
| "Here's how to practice transformers..." | *Generates exercise directly in chat* |
| "You should create a flashcard for this" | *Creates the flashcard and confirms* |
| "Search your notes for attention mechanisms" | *Searches and shows relevant results* |
| "Your mastery level might be low" | *Queries actual mastery data* |

### System Architecture Overview

```text
TOOL CALLING ARCHITECTURE
=========================

┌─────────────────────────────────────────────────────────────────────────────┐
│                              USER MESSAGE                                    │
│                  "Generate an exercise about attention mechanisms"           │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         ASSISTANT SERVICE                                    │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │ ToolRegistry          ToolExecutor           LLMClient               │  │
│  │ - Tool schemas        - Arg validation       - complete_with_tools() │  │
│  │ - OpenAI format       - Handler dispatch     - Tool response format  │  │
│  │ - Registration        - Error handling       - Multi-turn support    │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                    ┌─────────────────┴─────────────────┐
                    ▼                                   ▼
         ┌──────────────────┐                ┌──────────────────┐
         │  NO TOOL CALLS   │                │   TOOL CALLS     │
         │  (text response) │                │   (function)     │
         └────────┬─────────┘                └────────┬─────────┘
                  │                                   │
                  ▼                                   ▼
         ┌──────────────────┐    ┌────────────────────────────────────────┐
         │  Return response │    │            TOOL HANDLERS               │
         │    as-is         │    ├────────────────────────────────────────┤
         └──────────────────┘    │ generate_exercise → ExerciseGenerator  │
                                 │ create_flashcard  → SpacedRepService   │
                                 │ search_knowledge  → KnowledgeSearch    │
                                 │ get_mastery       → MasteryService     │
                                 │ get_weak_spots    → MasteryService     │
                                 └────────────────────────────────────────┘
                                                      │
                                                      ▼
                                             ┌──────────────────┐
                                             │  RESULT HANDLER  │
                                             │  - Format output │
                                             │  - Build context │
                                             │  - Final response│
                                             └──────────────────┘
```

### Scope

| In Scope | Out of Scope |
|----------|--------------|
| Tool registry and executor infrastructure | External service tools (email, calendar) |
| 5 initial tools (exercise, flashcard, search, mastery, weak spots) | Multi-step autonomous agent workflows |
| LLM client extension for tool calling | Tool calling in streaming mode (Phase 2) |
| API response model updates | User-defined custom tools |
| Frontend tool result display | Tool confirmation dialogs |
| Unit and integration tests | Mobile-specific tool UI |

### Implementation Phases Summary

| Phase | Focus | Days | Tasks |
|-------|-------|------|-------|
| 11A | Core Infrastructure | 2-3 | ToolRegistry, ToolExecutor, LLMClient extension |
| 11B | Tool Handlers | 2-3 | 5 tool handler implementations |
| 11C | Service Integration | 2 | AssistantService updates, response models |
| 11D | Frontend Integration | 2-3 | Tool result components, exercise card, search results |
| 11E | Testing & Polish | 1-2 | Unit tests, integration tests, error handling |

**Total Estimated Effort**: 8-12 days

---

## 2. Prerequisites

### 2.1 Prior Phases Required

| Phase | Component | Why Required |
|-------|-----------|--------------|
| **Phase 6-8** | Learning System | ExerciseGenerator, MasteryService, SpacedRepService |
| **Phase 3-4** | Knowledge Graph | KnowledgeSearchService for search tool |
| **Phase 3** | LLM Client | Base LiteLLM integration |
| **Phase 1** | PostgreSQL + Redis | Session management, card storage |

### 2.2 Existing Services (Already Implemented)

The following services are already implemented and will be used by tool handlers:

| Service | Location | Status |
|---------|----------|--------|
| `ExerciseGenerator` | `services/learning/exercise_generator.py` | ✅ Complete |
| `SpacedRepService` | `services/learning/spaced_rep_service.py` | ✅ Complete |
| `MasteryService` | `services/learning/mastery_service.py` | ✅ Complete |
| `KnowledgeSearchService` | `services/knowledge_graph/search.py` | ✅ Complete |
| `LLMClient` | `services/llm/client.py` | ✅ Complete (needs extension) |
| `AssistantService` | `services/assistant/service.py` | ✅ Partial (needs tool integration) |

### 2.3 New Dependencies

No new pip dependencies required. Tool calling uses existing LiteLLM which already supports function calling.

### 2.4 Environment Variables

```bash
# Add to .env file

# Tool Calling Configuration
ASSISTANT_TOOLS_ENABLED=true                    # Enable/disable tool calling
ASSISTANT_TOOL_TIMEOUT_SECONDS=30               # Max execution time per tool
ASSISTANT_MAX_TOOL_CALLS_PER_MESSAGE=3          # Limit tool calls per request
```

---

## 3. Implementation Phases

### Phase 11A: Core Infrastructure (Days 1-3)

#### Task 11A.1: Tool Definition and Registry

**Purpose**: Create the foundational classes for defining and managing tools.

**Files to Create**:
- `backend/app/services/assistant/tools.py`
- `backend/app/services/assistant/tool_registry.py`

**Implementation**:

```python
# backend/app/services/assistant/tools.py

from dataclasses import dataclass
from typing import Any, Callable, Coroutine, Optional
from enum import Enum

class ToolName(str, Enum):
    """Available tool names."""
    GENERATE_EXERCISE = "generate_exercise"
    CREATE_FLASHCARD = "create_flashcard"
    SEARCH_KNOWLEDGE = "search_knowledge"
    GET_MASTERY = "get_mastery"
    GET_WEAK_SPOTS = "get_weak_spots"

@dataclass
class ToolDefinition:
    """Definition of a tool for LLM function calling."""
    name: ToolName
    description: str
    parameters: dict[str, Any]  # JSON Schema
    handler: Optional[Callable[..., Coroutine[Any, Any, Any]]] = None
```

**Tool Registry Implementation**:

```python
# backend/app/services/assistant/tool_registry.py

from typing import Optional
from app.services.assistant.tools import ToolDefinition, ToolName

class ToolRegistry:
    """Registry of available tools for the assistant."""
    
    def __init__(self):
        self._tools: dict[ToolName, ToolDefinition] = {}
    
    def register(self, tool: ToolDefinition) -> None:
        """Register a tool definition."""
        self._tools[tool.name] = tool
    
    def get(self, name: ToolName) -> Optional[ToolDefinition]:
        """Get a tool by name."""
        return self._tools.get(name)
    
    def get_all(self) -> list[ToolDefinition]:
        """Get all registered tools."""
        return list(self._tools.values())
    
    def to_openai_format(self) -> list[dict]:
        """Convert tools to OpenAI function calling format."""
        return [
            {
                "type": "function",
                "function": {
                    "name": tool.name.value,
                    "description": tool.description,
                    "parameters": tool.parameters,
                }
            }
            for tool in self._tools.values()
        ]
```

**Checklist**:
- [ ] Create `ToolName` enum with all 5 tool names
- [ ] Create `ToolDefinition` dataclass with schema validation
- [ ] Implement `ToolRegistry` class with registration and lookup
- [ ] Add `to_openai_format()` for LiteLLM compatibility
- [ ] Unit tests for registry operations

---

#### Task 11A.2: Tool Executor

**Purpose**: Execute tool calls safely with error handling and result formatting.

**File**: `backend/app/services/assistant/tool_executor.py`

**Implementation**:

```python
# backend/app/services/assistant/tool_executor.py

import json
import logging
from typing import Any, Optional
from dataclasses import dataclass

from app.services.assistant.tool_registry import ToolRegistry
from app.services.assistant.tools import ToolName

logger = logging.getLogger(__name__)

@dataclass
class ToolCallResult:
    """Result of executing a tool."""
    tool_name: str
    arguments: dict[str, Any]
    result: Any
    success: bool
    error: Optional[str] = None

class ToolExecutor:
    """Executes tool calls from LLM responses."""
    
    def __init__(self, registry: ToolRegistry):
        self.registry = registry
    
    async def execute(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        context: dict[str, Any],
    ) -> ToolCallResult:
        """Execute a single tool call."""
        try:
            tool = self.registry.get(ToolName(tool_name))
            if not tool:
                return ToolCallResult(
                    tool_name=tool_name,
                    arguments=arguments,
                    result=None,
                    success=False,
                    error=f"Unknown tool: {tool_name}"
                )
            
            if not tool.handler:
                return ToolCallResult(
                    tool_name=tool_name,
                    arguments=arguments,
                    result=None,
                    success=False,
                    error=f"Tool handler not configured: {tool_name}"
                )
            
            result = await tool.handler(arguments, context)
            
            logger.info(f"Tool {tool_name} executed successfully")
            return ToolCallResult(
                tool_name=tool_name,
                arguments=arguments,
                result=result,
                success=True,
            )
            
        except Exception as e:
            logger.error(f"Tool {tool_name} execution failed: {e}")
            return ToolCallResult(
                tool_name=tool_name,
                arguments=arguments,
                result=None,
                success=False,
                error=str(e),
            )
    
    async def execute_all(
        self,
        tool_calls: list[dict],
        context: dict[str, Any],
    ) -> list[ToolCallResult]:
        """Execute multiple tool calls sequentially."""
        results = []
        for call in tool_calls:
            arguments = call.get("function", {}).get("arguments", {})
            if isinstance(arguments, str):
                arguments = json.loads(arguments)
            
            result = await self.execute(
                tool_name=call.get("function", {}).get("name"),
                arguments=arguments,
                context=context,
            )
            results.append(result)
        
        return results
```

**Checklist**:
- [ ] Create `ToolCallResult` dataclass
- [ ] Implement `ToolExecutor` with single tool execution
- [ ] Add `execute_all` for batch execution
- [ ] Handle JSON argument parsing (string or dict)
- [ ] Proper error handling and logging
- [ ] Unit tests for executor

---

#### Task 11A.3: LLM Client Extension

**Purpose**: Add tool calling support to the existing LLM client.

**File**: `backend/app/services/llm/client.py` (modify existing)

**Implementation**:

Add the `complete_with_tools` method to the existing `LLMClient` class:

```python
# Add to backend/app/services/llm/client.py

async def complete_with_tools(
    self,
    operation: Union[PipelineOperation, str],
    messages: list[dict],
    tools: list[dict],
    temperature: float = 0.3,
    max_tokens: int = 4096,
    pipeline: Optional[Union[PipelineName, str]] = None,
    content_id: Optional[str] = None,
    model: Optional[str] = None,
) -> tuple[dict, LLMUsage]:
    """
    Generate a completion with tool calling support.
    
    Args:
        operation: PipelineOperation enum
        messages: Chat messages
        tools: Tool definitions in OpenAI format
        temperature: Sampling temperature
        max_tokens: Max tokens in response
        pipeline: Pipeline name for cost tracking
        content_id: Content ID for cost tracking
        model: Optional model override
    
    Returns:
        Tuple of (response dict with content and/or tool_calls, LLMUsage)
    """
    model = model or self.get_model_for_operation(operation)
    adjusted_temp = _adjust_temperature_for_model(model, temperature)
    
    kwargs = {
        "model": model,
        "messages": messages,
        "temperature": adjusted_temp,
        "max_tokens": max_tokens,
        "tools": tools,
        "tool_choice": "auto",
    }
    
    start_time = time.perf_counter()
    response = await acompletion(**kwargs)
    latency_ms = int((time.perf_counter() - start_time) * 1000)
    
    usage = extract_usage_from_response(
        response=response,
        model=model,
        request_type="text",
        latency_ms=latency_ms,
        pipeline=pipeline,
        content_id=content_id,
        operation=operation,
    )
    
    message = response.choices[0].message
    
    # Convert tool_calls to serializable format
    tool_calls = None
    if hasattr(message, 'tool_calls') and message.tool_calls:
        tool_calls = [
            {
                "id": tc.id,
                "type": "function",
                "function": {
                    "name": tc.function.name,
                    "arguments": tc.function.arguments,
                }
            }
            for tc in message.tool_calls
        ]
    
    return {
        "content": message.content,
        "tool_calls": tool_calls,
    }, usage
```

**Checklist**:
- [ ] Add `complete_with_tools` method to `LLMClient`
- [ ] Handle tool_calls in response parsing
- [ ] Track usage/cost for tool-enabled completions
- [ ] Convert tool_calls to serializable dict format
- [ ] Unit tests with mocked LLM responses

---

### Phase 11B: Tool Handlers (Days 4-6)

#### Task 11B.1: Generate Exercise Handler

**Purpose**: Generate adaptive exercises through the assistant.

**File**: `backend/app/services/assistant/tool_handlers.py`

```python
# backend/app/services/assistant/tool_handlers.py

from typing import Any
from app.models.learning import ExerciseGenerateRequest
from app.enums.learning import ExerciseType

async def handle_generate_exercise(
    arguments: dict[str, Any],
    context: dict[str, Any],
) -> dict:
    """
    Handle generate_exercise tool call.
    
    Args:
        arguments: {topic: str, exercise_type?: str, language?: str}
        context: {exercise_generator, mastery_service}
    """
    exercise_generator = context["exercise_generator"]
    mastery_service = context["mastery_service"]
    
    # Get mastery level for adaptive difficulty
    mastery_level = 0.5
    try:
        mastery_state = await mastery_service.get_mastery_state(arguments["topic"])
        mastery_level = mastery_state.mastery_score
    except Exception:
        pass  # Use default mastery for new topics
    
    # Parse exercise type if provided
    exercise_type = None
    if arguments.get("exercise_type"):
        try:
            exercise_type = ExerciseType(arguments["exercise_type"])
        except ValueError:
            pass  # Let generator choose
    
    # Build request
    request = ExerciseGenerateRequest(
        topic=arguments["topic"],
        exercise_type=exercise_type,
        language=arguments.get("language"),
    )
    
    # Generate exercise
    exercise = await exercise_generator.generate_exercise(
        request=request,
        mastery_level=mastery_level,
        validate_topic=False,  # Allow any topic via chat
    )
    
    return {
        "type": "exercise",
        "exercise_id": str(exercise.exercise_uuid),
        "exercise_type": exercise.exercise_type.value,
        "topic": exercise.topic,
        "difficulty": exercise.difficulty.value,
        "prompt": exercise.prompt,
        "hints": exercise.hints or [],
        "estimated_time_minutes": exercise.estimated_time_minutes,
    }
```

**Tool Definition**:

```python
GENERATE_EXERCISE_TOOL = ToolDefinition(
    name=ToolName.GENERATE_EXERCISE,
    description="""Generate a learning exercise for a specific topic.
Use this when the user asks to practice, quiz themselves, or wants an exercise.
Exercises adapt to the user's mastery level automatically.""",
    parameters={
        "type": "object",
        "properties": {
            "topic": {
                "type": "string",
                "description": "The topic to generate an exercise for (e.g., 'ml/transformers/attention', 'python/async')"
            },
            "exercise_type": {
                "type": "string",
                "enum": ["free_recall", "self_explain", "worked_example", "application",
                         "teach_back", "code_implement", "code_debug", "code_complete",
                         "code_refactor", "compare_contrast"],
                "description": "Optional: Specific type of exercise"
            },
            "language": {
                "type": "string",
                "description": "Programming language for code exercises (e.g., 'python', 'javascript')"
            }
        },
        "required": ["topic"]
    },
    handler=handle_generate_exercise,
)
```

**Checklist**:
- [ ] Implement `handle_generate_exercise` function
- [ ] Create tool definition with JSON schema
- [ ] Integrate with ExerciseGenerator
- [ ] Use MasteryService for adaptive difficulty
- [ ] Return exercise data in consistent format
- [ ] Unit tests with mocked services

---

#### Task 11B.2: Create Flashcard Handler

**Purpose**: Create spaced repetition flashcards through the assistant.

```python
async def handle_create_flashcard(
    arguments: dict[str, Any],
    context: dict[str, Any],
) -> dict:
    """Handle create_flashcard tool call."""
    spaced_rep_service = context["spaced_rep_service"]
    
    card = await spaced_rep_service.create_card(
        front=arguments["front"],
        back=arguments["back"],
        topic=arguments.get("topic"),
        source_note_id=arguments.get("source_note_id"),
    )
    
    return {
        "type": "flashcard",
        "card_id": str(card.card_uuid),
        "front": card.front,
        "back": card.back,
        "topic": card.topic,
        "due_date": card.due_date.isoformat() if card.due_date else None,
    }

CREATE_FLASHCARD_TOOL = ToolDefinition(
    name=ToolName.CREATE_FLASHCARD,
    description="""Create a spaced repetition flashcard.
Use this when the user wants to remember something specific or asks to create a flashcard.""",
    parameters={
        "type": "object",
        "properties": {
            "front": {
                "type": "string",
                "description": "The question or prompt side of the card"
            },
            "back": {
                "type": "string",
                "description": "The answer or explanation side of the card"
            },
            "topic": {
                "type": "string",
                "description": "Optional topic/category for the card"
            }
        },
        "required": ["front", "back"]
    },
    handler=handle_create_flashcard,
)
```

**Checklist**:
- [ ] Implement `handle_create_flashcard` function
- [ ] Create tool definition with JSON schema
- [ ] Integrate with SpacedRepService
- [ ] Return card data with due date
- [ ] Unit tests

---

#### Task 11B.3: Search Knowledge Handler

**Purpose**: Search the knowledge graph through the assistant.

```python
async def handle_search_knowledge(
    arguments: dict[str, Any],
    context: dict[str, Any],
) -> dict:
    """Handle search_knowledge tool call."""
    neo4j_client = context.get("neo4j_client")
    llm_client = context.get("llm_client")
    
    if not neo4j_client:
        return {"type": "error", "message": "Knowledge search not available"}
    
    from app.services.knowledge_graph.search import KnowledgeSearchService
    search_service = KnowledgeSearchService(neo4j_client, llm_client)
    
    results = await search_service.search(
        query=arguments["query"],
        limit=arguments.get("limit", 5),
        use_vector=True,
    )
    
    return {
        "type": "search_results",
        "query": arguments["query"],
        "results": [
            {
                "id": r.get("id"),
                "title": r.get("title"),
                "type": r.get("type", "unknown"),
                "summary": (r.get("summary") or "")[:200],
                "score": r.get("score"),
            }
            for r in results.results
        ],
        "total": results.total,
    }

SEARCH_KNOWLEDGE_TOOL = ToolDefinition(
    name=ToolName.SEARCH_KNOWLEDGE,
    description="""Search the user's knowledge base (notes, papers, concepts).
Use this to find relevant content before answering questions about specific topics.""",
    parameters={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The search query"
            },
            "limit": {
                "type": "integer",
                "description": "Maximum number of results (default: 5)",
                "minimum": 1,
                "maximum": 20
            }
        },
        "required": ["query"]
    },
    handler=handle_search_knowledge,
)
```

**Checklist**:
- [ ] Implement `handle_search_knowledge` function
- [ ] Create tool definition with JSON schema
- [ ] Integrate with KnowledgeSearchService
- [ ] Handle missing Neo4j client gracefully
- [ ] Return truncated summaries for readability
- [ ] Unit tests

---

#### Task 11B.4: Get Mastery Handler

**Purpose**: Query mastery state for a topic.

```python
async def handle_get_mastery(
    arguments: dict[str, Any],
    context: dict[str, Any],
) -> dict:
    """Handle get_mastery tool call."""
    mastery_service = context["mastery_service"]
    
    try:
        mastery = await mastery_service.get_mastery_state(arguments["topic"])
        
        return {
            "type": "mastery",
            "topic": mastery.topic,
            "mastery_score": mastery.mastery_score,
            "confidence": mastery.confidence,
            "total_attempts": mastery.total_attempts,
            "last_practiced": mastery.last_practiced.isoformat() if mastery.last_practiced else None,
            "suggested_exercises": [e.value for e in mastery.suggested_exercises] if mastery.suggested_exercises else [],
        }
    except Exception as e:
        return {
            "type": "mastery",
            "topic": arguments["topic"],
            "mastery_score": 0.0,
            "confidence": 0.0,
            "total_attempts": 0,
            "last_practiced": None,
            "suggested_exercises": [],
            "message": "No practice history for this topic yet",
        }

GET_MASTERY_TOOL = ToolDefinition(
    name=ToolName.GET_MASTERY,
    description="""Get the user's mastery level for a specific topic.
Use this when the user asks about their progress or skill level in a topic.""",
    parameters={
        "type": "object",
        "properties": {
            "topic": {
                "type": "string",
                "description": "The topic to check mastery for"
            }
        },
        "required": ["topic"]
    },
    handler=handle_get_mastery,
)
```

**Checklist**:
- [ ] Implement `handle_get_mastery` function
- [ ] Create tool definition
- [ ] Handle topics with no history gracefully
- [ ] Include suggested exercises in response
- [ ] Unit tests

---

#### Task 11B.5: Get Weak Spots Handler

**Purpose**: Identify topics needing review.

```python
async def handle_get_weak_spots(
    arguments: dict[str, Any],
    context: dict[str, Any],
) -> dict:
    """Handle get_weak_spots tool call."""
    mastery_service = context["mastery_service"]
    
    weak_spots = await mastery_service.get_weak_spots(
        limit=arguments.get("limit", 5)
    )
    
    return {
        "type": "weak_spots",
        "topics": [
            {
                "topic": ws.topic,
                "mastery_score": ws.mastery_score,
                "days_since_practice": ws.days_since_practice,
                "recommendation": ws.recommendation,
            }
            for ws in weak_spots
        ],
    }

GET_WEAK_SPOTS_TOOL = ToolDefinition(
    name=ToolName.GET_WEAK_SPOTS,
    description="""Get topics where the user's mastery is low or declining.
Use this when the user asks what they should study or review.""",
    parameters={
        "type": "object",
        "properties": {
            "limit": {
                "type": "integer",
                "description": "Maximum number of weak spots to return (default: 5)",
                "minimum": 1,
                "maximum": 20
            }
        },
        "required": []
    },
    handler=handle_get_weak_spots,
)
```

**Checklist**:
- [ ] Implement `handle_get_weak_spots` function
- [ ] Create tool definition
- [ ] Include days since practice for context
- [ ] Include recommendations
- [ ] Unit tests

---

#### Task 11B.6: Tool Registration Setup

**Purpose**: Create factory function to set up all tools with handlers.

**File**: `backend/app/services/assistant/tool_setup.py`

```python
# backend/app/services/assistant/tool_setup.py

from app.services.assistant.tool_registry import ToolRegistry
from app.services.assistant.tools import (
    GENERATE_EXERCISE_TOOL,
    CREATE_FLASHCARD_TOOL,
    SEARCH_KNOWLEDGE_TOOL,
    GET_MASTERY_TOOL,
    GET_WEAK_SPOTS_TOOL,
)

def create_tool_registry() -> ToolRegistry:
    """Create and configure the tool registry with all available tools."""
    registry = ToolRegistry()
    
    registry.register(GENERATE_EXERCISE_TOOL)
    registry.register(CREATE_FLASHCARD_TOOL)
    registry.register(SEARCH_KNOWLEDGE_TOOL)
    registry.register(GET_MASTERY_TOOL)
    registry.register(GET_WEAK_SPOTS_TOOL)
    
    return registry
```

**Checklist**:
- [ ] Create `create_tool_registry` factory function
- [ ] Register all 5 tools
- [ ] Export from assistant module `__init__.py`

---

### Phase 11C: Service Integration (Days 7-8)

#### Task 11C.1: Response Models

**Purpose**: Update API response models to include tool call information.

**File**: `backend/app/models/assistant.py` (modify existing)

```python
# Add to backend/app/models/assistant.py

from typing import Optional, Any
from pydantic import BaseModel, Field

class ToolCallInfo(BaseModel):
    """Information about a tool call made by the assistant."""
    name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    result: Optional[dict] = None
    success: bool = True
    error: Optional[str] = None

class ChatResponse(BaseModel):
    """Response from the AI assistant."""
    conversation_id: str
    response: str
    sources: list[SourceReference] = Field(default_factory=list)
    tool_calls: Optional[list[ToolCallInfo]] = None
```

**Checklist**:
- [ ] Create `ToolCallInfo` model
- [ ] Update `ChatResponse` model with `tool_calls` field
- [ ] Add model to module exports

---

#### Task 11C.2: System Prompt Updates

**Purpose**: Update assistant system prompt to guide tool usage.

**File**: `backend/app/services/assistant/prompts.py` (modify or create)

```python
ASSISTANT_SYSTEM_PROMPT_WITH_TOOLS = """You are a knowledgeable AI assistant for a personal \
knowledge management system called Second Brain. Your role is to help the user:

1. Explore and understand their saved knowledge (papers, articles, notes, concepts)
2. Make connections between different pieces of information
3. Answer questions using the knowledge base as context
4. Help them learn through practice and exercises
5. Track their learning progress

You have access to tools that can:
- Generate exercises and quizzes on topics
- Create flashcards for spaced repetition
- Search the knowledge base
- Check mastery levels for topics
- Identify weak spots that need review

IMPORTANT GUIDELINES FOR TOOL USE:
- Use generate_exercise when the user wants to practice, quiz themselves, or test their knowledge
- Use create_flashcard when the user wants to remember something specific
- Use search_knowledge to find relevant content before answering questions
- Use get_mastery or get_weak_spots when discussing learning progress
- Always explain what you did with the tool results in your response
- Be proactive about suggesting exercises for topics the user is discussing

When answering questions:
- Use the provided context from the knowledge base when available
- Be clear about what comes from the user's knowledge base vs general knowledge
- Provide helpful explanations and make connections between concepts
- Suggest exercises or flashcards when appropriate for learning

Keep responses focused, helpful, and well-structured. Use markdown formatting when appropriate."""
```

**Checklist**:
- [ ] Create `ASSISTANT_SYSTEM_PROMPT_WITH_TOOLS`
- [ ] Document when to use each tool
- [ ] Guide proactive tool suggestions

---

#### Task 11C.3: AssistantService Integration

**Purpose**: Update AssistantService to support tool calling.

**File**: `backend/app/services/assistant/service.py` (modify existing)

**Key Changes**:

1. Add tool registry and executor to constructor
2. Create `_generate_response_with_tools` method
3. Update `chat` method to optionally use tools
4. Handle tool execution loop (call → execute → respond)

```python
# Updates to backend/app/services/assistant/service.py

class AssistantService:
    def __init__(
        self,
        db: AsyncSession,
        llm: Optional[LLMClient] = None,
        neo4j: Optional[Neo4jClient] = None,
        # New dependencies
        tool_registry: Optional[ToolRegistry] = None,
        exercise_generator: Optional[ExerciseGenerator] = None,
        mastery_service: Optional[MasteryService] = None,
        spaced_rep_service: Optional[SpacedRepService] = None,
    ):
        self.db = db
        self.llm = llm
        self.neo4j = neo4j
        self.tool_registry = tool_registry
        self.tool_executor = ToolExecutor(tool_registry) if tool_registry else None
        self.exercise_generator = exercise_generator
        self.mastery_service = mastery_service
        self.spaced_rep_service = spaced_rep_service
    
    async def chat(
        self,
        message: str,
        conversation_id: Optional[str] = None,
        enable_tools: bool = True,
    ) -> ChatResponse:
        """Send a message with optional tool calling support."""
        # ... existing conversation and context logic ...
        
        tool_results = []
        if enable_tools and self.tool_registry and self.llm:
            response_text, tool_results = await self._generate_response_with_tools(
                message=message,
                context=context,
                history=history,
            )
        else:
            response_text = await self._generate_response(
                message=message,
                context=context,
                history=history,
            )
        
        # ... save and return response with tool_calls ...
    
    async def _generate_response_with_tools(
        self,
        message: str,
        context: str = "",
        history: Optional[list[dict]] = None,
    ) -> tuple[str, list[ToolCallResult]]:
        """Generate response with tool calling loop."""
        messages = [{"role": "system", "content": ASSISTANT_SYSTEM_PROMPT_WITH_TOOLS}]
        
        if history:
            messages.extend(history[:-1])
        
        user_content = f"{context}\n\nUser: {message}" if context else message
        messages.append({"role": "user", "content": user_content})
        
        # First LLM call with tools
        tools = self.tool_registry.to_openai_format()
        response, _ = await self.llm.complete_with_tools(
            operation=PipelineOperation.CONTENT_ANALYSIS,
            messages=messages,
            tools=tools,
        )
        
        tool_calls = response.get("tool_calls")
        if not tool_calls:
            return response.get("content", ""), []
        
        # Execute tools
        execution_context = {
            "db": self.db,
            "llm_client": self.llm,
            "neo4j_client": self.neo4j,
            "mastery_service": self.mastery_service,
            "spaced_rep_service": self.spaced_rep_service,
            "exercise_generator": self.exercise_generator,
        }
        
        tool_results = await self.tool_executor.execute_all(tool_calls, execution_context)
        
        # Add tool results to messages for final response
        messages.append({
            "role": "assistant",
            "content": response.get("content"),
            "tool_calls": tool_calls,
        })
        
        for call, result in zip(tool_calls, tool_results):
            messages.append({
                "role": "tool",
                "tool_call_id": call.get("id"),
                "content": json.dumps(result.result) if result.success else f"Error: {result.error}",
            })
        
        # Final LLM call with tool results
        final_response, _ = await self.llm.complete(
            operation=PipelineOperation.CONTENT_ANALYSIS,
            messages=messages,
        )
        
        return final_response, tool_results
```

**Checklist**:
- [ ] Add tool-related dependencies to constructor
- [ ] Create `_generate_response_with_tools` method
- [ ] Implement tool calling loop (LLM → execute → LLM)
- [ ] Update `chat` method to use tools when enabled
- [ ] Add `enable_tools` parameter to `chat`
- [ ] Format tool results for API response

---

#### Task 11C.4: Router Updates

**Purpose**: Ensure the assistant router properly initializes tool dependencies.

**File**: `backend/app/routers/assistant.py` (modify existing)

**Key Changes**:

1. Initialize tool registry in router
2. Inject learning services into AssistantService
3. Handle `enable_tools` parameter

```python
# Updates to assistant router initialization

from app.services.assistant.tool_setup import create_tool_registry
from app.services.learning.exercise_generator import ExerciseGenerator
from app.services.learning.mastery_service import MasteryService
from app.services.learning.spaced_rep_service import SpacedRepService

# Create tool registry at module level
tool_registry = create_tool_registry()

@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db),
    llm: LLMClient = Depends(get_llm_client),
    neo4j: Neo4jClient = Depends(get_neo4j_client),
):
    # Initialize services
    mastery_service = MasteryService(db)
    spaced_rep_service = SpacedRepService(db)
    exercise_generator = ExerciseGenerator(db, llm)
    
    service = AssistantService(
        db=db,
        llm=llm,
        neo4j=neo4j,
        tool_registry=tool_registry,
        exercise_generator=exercise_generator,
        mastery_service=mastery_service,
        spaced_rep_service=spaced_rep_service,
    )
    
    return await service.chat(
        message=request.message,
        conversation_id=request.conversation_id,
        enable_tools=request.enable_tools if hasattr(request, 'enable_tools') else True,
    )
```

**Checklist**:
- [ ] Import tool registry factory
- [ ] Initialize learning services in router
- [ ] Pass all dependencies to AssistantService
- [ ] Handle `enable_tools` from request

---

### Phase 11D: Frontend Integration (Days 9-11)

#### Task 11D.1: API Type Updates

**Purpose**: Update frontend API types to include tool call information.

**File**: `frontend/src/api/types.ts` or update via API type generation

```typescript
// frontend/src/api/types.ts (or generated types)

interface ToolCallInfo {
  name: string;
  arguments?: Record<string, unknown>;
  result?: Record<string, unknown>;
  success: boolean;
  error?: string;
}

interface ChatResponse {
  conversation_id: string;
  response: string;
  sources: SourceReference[];
  tool_calls?: ToolCallInfo[];
}
```

**Checklist**:
- [ ] Add `ToolCallInfo` interface
- [ ] Update `ChatResponse` interface
- [ ] Run type generation script if using OpenAPI

---

#### Task 11D.2: Tool Result Components

**Purpose**: Create React components to display tool results.

**File**: `frontend/src/components/assistant/ToolCallResult.jsx`

```jsx
// frontend/src/components/assistant/ToolCallResult.jsx

import React from 'react';
import { ExerciseCard } from './ExerciseCard';
import { FlashcardCreated } from './FlashcardCreated';
import { SearchResults } from './SearchResults';
import { MasteryDisplay } from './MasteryDisplay';
import { WeakSpotsPanel } from './WeakSpotsPanel';

export function ToolCallResult({ toolCall }) {
  if (!toolCall.success) {
    return (
      <div className="p-3 bg-red-500/10 border border-red-500/30 rounded-lg text-red-400 text-sm">
        Tool failed: {toolCall.name}
        {toolCall.error && <span className="block mt-1 text-xs">{toolCall.error}</span>}
      </div>
    );
  }

  const result = toolCall.result;
  if (!result) return null;

  switch (result.type) {
    case 'exercise':
      return <ExerciseCard exercise={result} />;
    case 'flashcard':
      return <FlashcardCreated card={result} />;
    case 'search_results':
      return <SearchResults results={result.results} query={result.query} />;
    case 'mastery':
      return <MasteryDisplay mastery={result} />;
    case 'weak_spots':
      return <WeakSpotsPanel topics={result.topics} />;
    default:
      return null;
  }
}
```

**Checklist**:
- [ ] Create `ToolCallResult` component with type switching
- [ ] Handle error state display
- [ ] Create placeholder components for each result type

---

#### Task 11D.3: Exercise Card Component

**Purpose**: Display generated exercises in chat.

**File**: `frontend/src/components/assistant/ExerciseCard.jsx`

```jsx
// frontend/src/components/assistant/ExerciseCard.jsx

import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';

export function ExerciseCard({ exercise }) {
  const [showHints, setShowHints] = useState(false);
  const navigate = useNavigate();

  const handleStartExercise = () => {
    navigate(`/practice?exercise=${exercise.exercise_id}`);
  };

  return (
    <div className="bg-bg-elevated rounded-xl p-4 border border-border-primary mt-4">
      <div className="flex items-center gap-2 mb-3">
        <span className="text-xl">📝</span>
        <span className="font-medium text-text-primary">Exercise Generated</span>
        <span className="px-2 py-0.5 bg-indigo-500/20 text-indigo-400 rounded text-xs">
          {exercise.exercise_type.replace('_', ' ')}
        </span>
        <span className="px-2 py-0.5 bg-gray-500/20 text-gray-400 rounded text-xs">
          {exercise.difficulty}
        </span>
      </div>

      <p className="text-text-secondary text-sm mb-2">
        Topic: <span className="text-text-primary">{exercise.topic}</span>
      </p>

      {exercise.estimated_time_minutes && (
        <p className="text-text-tertiary text-xs mb-3">
          ⏱️ Estimated time: {exercise.estimated_time_minutes} minutes
        </p>
      )}

      {exercise.hints?.length > 0 && (
        <button
          onClick={() => setShowHints(!showHints)}
          className="text-sm text-indigo-400 hover:text-indigo-300 mb-2"
        >
          {showHints ? 'Hide hints' : `Show ${exercise.hints.length} hints`}
        </button>
      )}

      {showHints && (
        <ul className="mt-2 mb-3 text-sm text-text-secondary space-y-1">
          {exercise.hints.map((hint, i) => (
            <li key={i}>💡 {hint}</li>
          ))}
        </ul>
      )}

      <div className="mt-3 flex gap-2">
        <button
          onClick={handleStartExercise}
          className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-sm font-medium"
        >
          Start Exercise
        </button>
        <button className="px-4 py-2 bg-bg-secondary hover:bg-bg-tertiary text-text-secondary rounded-lg text-sm">
          Practice Later
        </button>
      </div>
    </div>
  );
}
```

**Checklist**:
- [ ] Create `ExerciseCard` component
- [ ] Display exercise type and difficulty badges
- [ ] Implement collapsible hints
- [ ] Add "Start Exercise" button with navigation
- [ ] Add "Practice Later" functionality

---

#### Task 11D.4: Other Result Components

**Purpose**: Create remaining tool result display components.

**Files to Create**:
- `frontend/src/components/assistant/FlashcardCreated.jsx`
- `frontend/src/components/assistant/SearchResults.jsx`
- `frontend/src/components/assistant/MasteryDisplay.jsx`
- `frontend/src/components/assistant/WeakSpotsPanel.jsx`

```jsx
// frontend/src/components/assistant/FlashcardCreated.jsx

export function FlashcardCreated({ card }) {
  return (
    <div className="bg-bg-elevated rounded-xl p-4 border border-green-500/30 mt-4">
      <div className="flex items-center gap-2 mb-3">
        <span className="text-xl">🗂️</span>
        <span className="font-medium text-text-primary">Flashcard Created</span>
      </div>
      
      <div className="space-y-2 text-sm">
        <div>
          <span className="text-text-tertiary">Front:</span>
          <p className="text-text-primary">{card.front}</p>
        </div>
        <div>
          <span className="text-text-tertiary">Back:</span>
          <p className="text-text-secondary">{card.back}</p>
        </div>
        {card.due_date && (
          <p className="text-text-tertiary text-xs">
            First review: {new Date(card.due_date).toLocaleDateString()}
          </p>
        )}
      </div>
    </div>
  );
}
```

```jsx
// frontend/src/components/assistant/SearchResults.jsx

export function SearchResults({ results, query }) {
  if (!results || results.length === 0) {
    return (
      <div className="bg-bg-elevated rounded-xl p-4 border border-border-primary mt-4">
        <p className="text-text-secondary text-sm">No results found for "{query}"</p>
      </div>
    );
  }

  return (
    <div className="bg-bg-elevated rounded-xl p-4 border border-border-primary mt-4">
      <div className="flex items-center gap-2 mb-3">
        <span className="text-xl">🔍</span>
        <span className="font-medium text-text-primary">
          Found {results.length} results
        </span>
      </div>
      
      <ul className="space-y-2">
        {results.map((result, i) => (
          <li key={i} className="p-2 bg-bg-secondary rounded-lg">
            <p className="font-medium text-text-primary text-sm">{result.title}</p>
            {result.summary && (
              <p className="text-text-tertiary text-xs mt-1 line-clamp-2">
                {result.summary}
              </p>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}
```

```jsx
// frontend/src/components/assistant/MasteryDisplay.jsx

export function MasteryDisplay({ mastery }) {
  const masteryPercent = Math.round(mastery.mastery_score * 100);
  
  return (
    <div className="bg-bg-elevated rounded-xl p-4 border border-border-primary mt-4">
      <div className="flex items-center gap-2 mb-3">
        <span className="text-xl">📊</span>
        <span className="font-medium text-text-primary">Mastery: {mastery.topic}</span>
      </div>
      
      <div className="flex items-center gap-3">
        <div className="flex-1 h-2 bg-bg-tertiary rounded-full overflow-hidden">
          <div
            className="h-full bg-indigo-500 rounded-full"
            style={{ width: `${masteryPercent}%` }}
          />
        </div>
        <span className="text-text-primary font-medium">{masteryPercent}%</span>
      </div>
      
      {mastery.last_practiced && (
        <p className="text-text-tertiary text-xs mt-2">
          Last practiced: {new Date(mastery.last_practiced).toLocaleDateString()}
        </p>
      )}
      
      {mastery.suggested_exercises?.length > 0 && (
        <p className="text-text-secondary text-xs mt-2">
          Suggested: {mastery.suggested_exercises.join(', ')}
        </p>
      )}
    </div>
  );
}
```

```jsx
// frontend/src/components/assistant/WeakSpotsPanel.jsx

export function WeakSpotsPanel({ topics }) {
  if (!topics || topics.length === 0) {
    return (
      <div className="bg-bg-elevated rounded-xl p-4 border border-border-primary mt-4">
        <p className="text-text-secondary text-sm">No weak spots detected. Great job! 🎉</p>
      </div>
    );
  }

  return (
    <div className="bg-bg-elevated rounded-xl p-4 border border-amber-500/30 mt-4">
      <div className="flex items-center gap-2 mb-3">
        <span className="text-xl">⚠️</span>
        <span className="font-medium text-text-primary">Topics Needing Review</span>
      </div>
      
      <ul className="space-y-2">
        {topics.map((topic, i) => (
          <li key={i} className="p-2 bg-bg-secondary rounded-lg">
            <div className="flex justify-between items-center">
              <span className="text-text-primary text-sm">{topic.topic}</span>
              <span className="text-amber-400 text-xs">
                {Math.round(topic.mastery_score * 100)}%
              </span>
            </div>
            {topic.recommendation && (
              <p className="text-text-tertiary text-xs mt-1">{topic.recommendation}</p>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}
```

**Checklist**:
- [ ] Create `FlashcardCreated` component
- [ ] Create `SearchResults` component with empty state
- [ ] Create `MasteryDisplay` with progress bar
- [ ] Create `WeakSpotsPanel` with recommendations

---

#### Task 11D.5: Update Assistant Message Display

**Purpose**: Integrate tool results into chat message display.

**File**: `frontend/src/pages/Assistant.jsx` (modify existing)

```jsx
// Update message rendering in Assistant.jsx

function AssistantMessage({ message }) {
  return (
    <div className="assistant-message">
      {/* Text response */}
      <ReactMarkdown>{message.content}</ReactMarkdown>

      {/* Tool call results */}
      {message.tool_calls?.map((toolCall, index) => (
        <ToolCallResult key={index} toolCall={toolCall} />
      ))}

      {/* Sources */}
      {message.sources?.length > 0 && (
        <SourcesList sources={message.sources} />
      )}
    </div>
  );
}
```

**Checklist**:
- [ ] Import `ToolCallResult` component
- [ ] Render tool calls in message display
- [ ] Ensure proper ordering (text → tools → sources)
- [ ] Test with various tool result types

---

### Phase 11E: Testing & Polish (Days 12-13)

#### Task 11E.1: Unit Tests

**Files**:
- `backend/tests/unit/test_tool_registry.py`
- `backend/tests/unit/test_tool_executor.py`
- `backend/tests/unit/test_tool_handlers.py`

```python
# backend/tests/unit/test_tool_registry.py

import pytest
from app.services.assistant.tool_registry import ToolRegistry
from app.services.assistant.tools import ToolDefinition, ToolName

class TestToolRegistry:
    def test_register_tool(self):
        registry = ToolRegistry()
        tool = ToolDefinition(
            name=ToolName.GENERATE_EXERCISE,
            description="Test tool",
            parameters={"type": "object", "properties": {}},
        )
        
        registry.register(tool)
        assert registry.get(ToolName.GENERATE_EXERCISE) == tool
    
    def test_get_unknown_tool(self):
        registry = ToolRegistry()
        assert registry.get(ToolName.GENERATE_EXERCISE) is None
    
    def test_to_openai_format(self):
        registry = ToolRegistry()
        tool = ToolDefinition(
            name=ToolName.SEARCH_KNOWLEDGE,
            description="Search the knowledge base",
            parameters={"type": "object", "properties": {"query": {"type": "string"}}},
        )
        registry.register(tool)
        
        openai_format = registry.to_openai_format()
        assert len(openai_format) == 1
        assert openai_format[0]["type"] == "function"
        assert openai_format[0]["function"]["name"] == "search_knowledge"
```

```python
# backend/tests/unit/test_tool_executor.py

import pytest
from unittest.mock import AsyncMock, MagicMock
from app.services.assistant.tool_executor import ToolExecutor, ToolCallResult
from app.services.assistant.tool_registry import ToolRegistry
from app.services.assistant.tools import ToolDefinition, ToolName

class TestToolExecutor:
    @pytest.fixture
    def mock_registry(self):
        registry = ToolRegistry()
        
        async def mock_handler(args, ctx):
            return {"type": "test", "data": args.get("input")}
        
        tool = ToolDefinition(
            name=ToolName.SEARCH_KNOWLEDGE,
            description="Test tool",
            parameters={},
            handler=mock_handler,
        )
        registry.register(tool)
        return registry
    
    @pytest.fixture
    def executor(self, mock_registry):
        return ToolExecutor(mock_registry)
    
    @pytest.mark.asyncio
    async def test_execute_valid_tool(self, executor):
        result = await executor.execute(
            tool_name="search_knowledge",
            arguments={"input": "test"},
            context={},
        )
        
        assert result.success is True
        assert result.result["type"] == "test"
        assert result.result["data"] == "test"
    
    @pytest.mark.asyncio
    async def test_execute_unknown_tool(self, executor):
        result = await executor.execute(
            tool_name="nonexistent_tool",
            arguments={},
            context={},
        )
        
        assert result.success is False
        assert "Unknown tool" in result.error
    
    @pytest.mark.asyncio
    async def test_execute_all(self, executor):
        tool_calls = [
            {"function": {"name": "search_knowledge", "arguments": '{"input": "a"}'}},
            {"function": {"name": "search_knowledge", "arguments": {"input": "b"}}},
        ]
        
        results = await executor.execute_all(tool_calls, {})
        
        assert len(results) == 2
        assert all(r.success for r in results)
```

**Checklist**:
- [ ] Unit tests for ToolRegistry
- [ ] Unit tests for ToolExecutor
- [ ] Unit tests for each tool handler (mocked dependencies)
- [ ] Test error handling paths

---

#### Task 11E.2: Integration Tests

**File**: `backend/tests/integration/test_assistant_tools.py`

```python
# backend/tests/integration/test_assistant_tools.py

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

class TestAssistantToolCalling:
    @pytest.mark.asyncio
    async def test_chat_triggers_exercise_tool(
        self,
        client: AsyncClient,
        db: AsyncSession,
    ):
        """Test that asking for an exercise triggers tool call."""
        response = await client.post(
            "/api/assistant/chat",
            json={"message": "Generate an exercise about Python decorators"},
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["tool_calls"] is not None
        assert len(data["tool_calls"]) >= 1
        
        exercise_call = next(
            (tc for tc in data["tool_calls"] if tc["name"] == "generate_exercise"),
            None
        )
        assert exercise_call is not None
        assert exercise_call["success"] is True
        assert exercise_call["result"]["type"] == "exercise"
    
    @pytest.mark.asyncio
    async def test_chat_without_tools(
        self,
        client: AsyncClient,
    ):
        """Test chat with tools disabled."""
        response = await client.post(
            "/api/assistant/chat",
            json={
                "message": "What is machine learning?",
                "enable_tools": False,
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["tool_calls"] is None or len(data["tool_calls"]) == 0
    
    @pytest.mark.asyncio
    async def test_flashcard_creation_tool(
        self,
        client: AsyncClient,
        db: AsyncSession,
    ):
        """Test flashcard creation through assistant."""
        response = await client.post(
            "/api/assistant/chat",
            json={"message": "Create a flashcard: Q: What is FSRS? A: Free Spaced Repetition Scheduler"},
        )
        
        assert response.status_code == 200
        data = response.json()
        
        flashcard_call = next(
            (tc for tc in data.get("tool_calls", []) if tc["name"] == "create_flashcard"),
            None
        )
        
        if flashcard_call:
            assert flashcard_call["success"] is True
            assert flashcard_call["result"]["type"] == "flashcard"
```

**Checklist**:
- [ ] Integration test for exercise generation via chat
- [ ] Integration test for flashcard creation via chat
- [ ] Integration test for search tool
- [ ] Integration test for mastery tools
- [ ] Test tools disabled mode
- [ ] Test error handling for tool failures

---

#### Task 11E.3: Error Handling Polish

**Purpose**: Ensure graceful degradation when tools fail.

**Key Error Scenarios**:

1. **Tool handler raises exception**: Catch, log, return error in result
2. **Missing service dependency**: Return appropriate error message
3. **LLM doesn't support tools**: Fall back to non-tool response
4. **Tool timeout**: Implement timeout wrapper with configurable limit

```python
# Add timeout handling to ToolExecutor

import asyncio
from app.config import settings

async def execute_with_timeout(
    self,
    tool_name: str,
    arguments: dict[str, Any],
    context: dict[str, Any],
) -> ToolCallResult:
    """Execute a tool with timeout protection."""
    try:
        return await asyncio.wait_for(
            self.execute(tool_name, arguments, context),
            timeout=settings.ASSISTANT_TOOL_TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError:
        return ToolCallResult(
            tool_name=tool_name,
            arguments=arguments,
            result=None,
            success=False,
            error=f"Tool execution timed out after {settings.ASSISTANT_TOOL_TIMEOUT_SECONDS}s",
        )
```

**Checklist**:
- [ ] Add timeout handling to tool execution
- [ ] Test missing dependency scenarios
- [ ] Test LLM tool-calling fallback
- [ ] Verify error messages are user-friendly
- [ ] Add logging for all error paths

---

#### Task 11E.4: Configuration Updates

**Purpose**: Add settings and document configuration options.

**File**: `backend/app/config/settings.py` (add to existing)

```python
# Add to Settings class

# Tool Calling Configuration
ASSISTANT_TOOLS_ENABLED: bool = Field(
    default=True,
    description="Enable tool calling in assistant"
)
ASSISTANT_TOOL_TIMEOUT_SECONDS: int = Field(
    default=30,
    description="Maximum time for tool execution"
)
ASSISTANT_MAX_TOOL_CALLS_PER_MESSAGE: int = Field(
    default=3,
    description="Maximum tool calls per user message"
)
```

**Checklist**:
- [ ] Add settings with sensible defaults
- [ ] Update `.env.example` with new variables
- [ ] Document settings in README or config docs

---

## 4. File Structure Summary

```
backend/app/services/assistant/
├── __init__.py                    # Module exports
├── service.py                     # AssistantService (updated)
├── prompts.py                     # System prompts (updated)
├── tools.py                       # ToolName enum, ToolDefinition
├── tool_registry.py               # ToolRegistry class
├── tool_executor.py               # ToolExecutor class
├── tool_handlers.py               # Handler implementations
└── tool_setup.py                  # Factory function

backend/app/models/
└── assistant.py                   # ToolCallInfo, ChatResponse (updated)

backend/tests/unit/
├── test_tool_registry.py
├── test_tool_executor.py
└── test_tool_handlers.py

backend/tests/integration/
└── test_assistant_tools.py

frontend/src/components/assistant/
├── ToolCallResult.jsx             # Tool result dispatcher
├── ExerciseCard.jsx               # Exercise display
├── FlashcardCreated.jsx           # Flashcard confirmation
├── SearchResults.jsx              # Search results list
├── MasteryDisplay.jsx             # Mastery progress
└── WeakSpotsPanel.jsx             # Weak spots list
```

---

## 5. Testing Checklist

### Unit Tests
- [ ] ToolRegistry: register, get, get_all, to_openai_format
- [ ] ToolExecutor: execute valid, unknown, error, execute_all
- [ ] Tool handlers: each handler with mocked dependencies
- [ ] LLMClient.complete_with_tools: response parsing

### Integration Tests
- [ ] Chat with exercise generation tool
- [ ] Chat with flashcard creation tool
- [ ] Chat with search tool
- [ ] Chat with mastery tools
- [ ] Chat with tools disabled
- [ ] Error handling paths

### Frontend Tests
- [ ] ToolCallResult renders correct component by type
- [ ] ExerciseCard displays all fields and handles interactions
- [ ] Error states display appropriately
- [ ] Integration with Assistant page

---

## 6. Rollout Plan

### Phase 1: Backend Only (Days 1-8)
- Deploy backend changes with `ASSISTANT_TOOLS_ENABLED=false`
- Verify existing assistant functionality unchanged
- Run integration tests in staging

### Phase 2: Enable Tools (Day 9)
- Set `ASSISTANT_TOOLS_ENABLED=true`
- Monitor logs for tool execution
- Verify LLM cost tracking includes tool calls

### Phase 3: Frontend (Days 9-11)
- Deploy frontend changes
- Verify tool results display correctly
- Test all tool result component types

### Phase 4: Polish (Days 12-13)
- Address any issues from production
- Performance optimization if needed
- Documentation updates

---

## 7. Related Documents

- `design_docs/09_assistant_tool_calling.md` — Design specification
- `design_docs/05_learning_system.md` — Exercise generation and mastery
- `design_docs/06_backend_api.md` — API structure
- `design_docs/07_frontend_application.md` — Frontend components
- `implementation_plan/05_learning_system_implementation.md` — Learning services reference
- `implementation_plan/06_backend_api_implementation.md` — Backend API reference
