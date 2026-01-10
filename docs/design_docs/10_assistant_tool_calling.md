# Assistant Tool Calling Design

> **Document Status**: Design Specification  
> **Last Updated**: January 2026  
> **Related Docs**: `06_backend_api.md`, `05_learning_system.md`, `07_frontend_application.md`

---

## 1. Overview

This document describes the design for adding **tool calling** (function calling) capabilities to the AI Assistant service. Tool calling enables the assistant to take actions on behalf of the user—such as generating exercises, creating flashcards, or searching the knowledge graph—through natural language requests.

### Goals

| Goal | Description |
|------|-------------|
| **Natural Interface** | Users can request actions via chat: "Generate an exercise on transformers" |
| **Extensible Architecture** | Easy to add new tools without modifying core chat logic |
| **Transparent Execution** | Users see what tools were used and their results |
| **Learning Integration** | Deep integration with ExerciseGenerator, SpacedRepService, MasteryService |

### Non-Goals

- Tool calling for external services (email, calendar, etc.)
- Multi-step autonomous agent workflows
- Tool calling in streaming mode (Phase 2)

---

## 2. Architecture

### 2.1 High-Level Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              USER MESSAGE                                    │
│                  "Generate an exercise about attention mechanisms"           │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         ASSISTANT SERVICE                                    │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │  1. Build messages with tool definitions                               │ │
│  │  2. Call LLM with tools enabled                                        │ │
│  │  3. Check response for tool_calls                                      │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
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
         ┌──────────────────┐                ┌──────────────────┐
         │  Return response │                │  TOOL EXECUTOR   │
         │    as-is         │                │  Execute tool(s) │
         └──────────────────┘                │  with arguments  │
                                             └────────┬─────────┘
                                                      │
                                                      ▼
                                             ┌──────────────────┐
                                             │  RESULT HANDLER  │
                                             │  - Format output │
                                             │  - Build context │
                                             │  - Final response│
                                             └────────┬─────────┘
                                                      │
                                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              CHAT RESPONSE                                   │
│  {                                                                           │
│    "response": "Here's an exercise on attention mechanisms...",             │
│    "tool_calls": [{name: "generate_exercise", result: {...}}],              │
│    "sources": [...]                                                          │
│  }                                                                           │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Component Responsibilities

| Component | Responsibility |
|-----------|----------------|
| **ToolRegistry** | Registers available tools with schemas |
| **ToolExecutor** | Validates arguments and executes tools |
| **AssistantService** | Orchestrates tool calling within chat flow |
| **LLMClient** | Passes tool definitions to LLM, handles tool_calls in response |

---

## 3. Tool Definitions

### 3.1 Tool Schema Format

Tools are defined using JSON Schema format compatible with OpenAI/Anthropic/Gemini function calling:

```python
# backend/app/services/assistant/tools.py

from dataclasses import dataclass
from typing import Any, Callable, Coroutine
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
    handler: Callable[..., Coroutine[Any, Any, Any]]

# Example tool definition
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
                "description": "Optional: Specific type of exercise. If not provided, one is selected based on mastery level."
            },
            "language": {
                "type": "string",
                "description": "Programming language for code exercises (e.g., 'python', 'javascript'). Only needed for code topics."
            }
        },
        "required": ["topic"]
    },
    handler=None  # Set at runtime
)
```

### 3.2 Initial Tool Set

| Tool | Description | Parameters |
|------|-------------|------------|
| `generate_exercise` | Generate adaptive exercise for a topic | `topic`, `exercise_type?`, `language?` |
| `create_flashcard` | Create a spaced repetition card | `front`, `back`, `topic?` |
| `search_knowledge` | Search the knowledge graph | `query`, `limit?` |
| `get_mastery` | Get mastery state for a topic | `topic` |
| `get_weak_spots` | Get topics needing review | `limit?` |

---

## 4. Implementation

### 4.1 Tool Registry

```python
# backend/app/services/assistant/tool_registry.py

from typing import Optional
from app.services.assistant.tools import ToolDefinition, ToolName

class ToolRegistry:
    """
    Registry of available tools for the assistant.
    
    Manages tool definitions and provides them in LLM-ready format.
    """
    
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
        """
        Convert tools to OpenAI function calling format.
        
        Returns format compatible with LiteLLM tools parameter.
        """
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

### 4.2 Tool Executor

```python
# backend/app/services/assistant/tool_executor.py

import json
import logging
from typing import Any
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
    """
    Executes tool calls from LLM responses.
    
    Validates arguments against tool schema and invokes handlers.
    """
    
    def __init__(self, registry: ToolRegistry):
        self.registry = registry
    
    async def execute(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        context: dict[str, Any],
    ) -> ToolCallResult:
        """
        Execute a single tool call.
        
        Args:
            tool_name: Name of the tool to execute
            arguments: Arguments from LLM
            context: Execution context (db, services, etc.)
        
        Returns:
            ToolCallResult with execution outcome
        """
        try:
            # Get tool definition
            tool = self.registry.get(ToolName(tool_name))
            if not tool:
                return ToolCallResult(
                    tool_name=tool_name,
                    arguments=arguments,
                    result=None,
                    success=False,
                    error=f"Unknown tool: {tool_name}"
                )
            
            # Execute handler
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
        """
        Execute multiple tool calls.
        
        Args:
            tool_calls: List of tool calls from LLM response
            context: Execution context
        
        Returns:
            List of ToolCallResults
        """
        results = []
        for call in tool_calls:
            # Parse arguments (may be string or dict depending on provider)
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

### 4.3 Tool Handlers

```python
# backend/app/services/assistant/tool_handlers.py

"""
Tool handler implementations.

Each handler receives validated arguments and execution context,
and returns a result that will be formatted for the user.
"""

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
        context: {db, llm_client, mastery_service, exercise_generator}
    
    Returns:
        Exercise data for response formatting
    """
    exercise_generator = context["exercise_generator"]
    mastery_service = context["mastery_service"]
    
    # Get mastery level for adaptive difficulty
    mastery_level = 0.5
    try:
        mastery_state = await mastery_service.get_mastery_state(arguments["topic"])
        mastery_level = mastery_state.mastery_score
    except Exception:
        pass  # Use default mastery
    
    # Build request
    request = ExerciseGenerateRequest(
        topic=arguments["topic"],
        exercise_type=ExerciseType(arguments["exercise_type"]) if arguments.get("exercise_type") else None,
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
        "exercise_id": exercise.exercise_uuid,
        "exercise_type": exercise.exercise_type.value,
        "topic": exercise.topic,
        "difficulty": exercise.difficulty.value,
        "prompt": exercise.prompt,
        "hints": exercise.hints,
        "estimated_time_minutes": exercise.estimated_time_minutes,
        # Don't include solution in chat response
    }


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
    )
    
    return {
        "type": "flashcard",
        "card_id": card.card_uuid,
        "front": card.front,
        "back": card.back,
        "due_date": card.due_date.isoformat() if card.due_date else None,
    }


async def handle_search_knowledge(
    arguments: dict[str, Any],
    context: dict[str, Any],
) -> dict:
    """Handle search_knowledge tool call."""
    neo4j_client = context.get("neo4j_client")
    llm_client = context.get("llm_client")
    
    if not neo4j_client:
        return {"type": "error", "message": "Knowledge search not available"}
    
    from app.services.knowledge_graph import KnowledgeSearchService
    search_service = KnowledgeSearchService(neo4j_client, llm_client)
    
    results, _ = await search_service.semantic_search(
        query=arguments["query"],
        limit=arguments.get("limit", 5),
    )
    
    return {
        "type": "search_results",
        "query": arguments["query"],
        "results": [
            {
                "id": r.get("id"),
                "title": r.get("title"),
                "summary": r.get("summary", "")[:200],
                "score": r.get("score"),
            }
            for r in results
        ],
    }


async def handle_get_mastery(
    arguments: dict[str, Any],
    context: dict[str, Any],
) -> dict:
    """Handle get_mastery tool call."""
    mastery_service = context["mastery_service"]
    
    mastery = await mastery_service.get_mastery_state(arguments["topic"])
    
    return {
        "type": "mastery",
        "topic": mastery.topic,
        "mastery_score": mastery.mastery_score,
        "confidence": mastery.confidence,
        "last_practiced": mastery.last_practiced.isoformat() if mastery.last_practiced else None,
        "suggested_exercises": [e.value for e in mastery.suggested_exercises],
    }


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
                "recommendation": ws.recommendation,
            }
            for ws in weak_spots
        ],
    }
```

### 4.4 LLM Client Extension

```python
# backend/app/services/llm/client.py (additions)

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
        "tool_choice": "auto",  # Let model decide when to use tools
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
    
    return {
        "content": message.content,
        "tool_calls": message.tool_calls if hasattr(message, 'tool_calls') else None,
    }, usage
```

### 4.5 Updated AssistantService.chat()

```python
# backend/app/services/assistant/service.py (updated chat method)

async def chat(
    self,
    message: str,
    conversation_id: Optional[str] = None,
    enable_tools: bool = True,
) -> ChatResponse:
    """
    Send a message to the assistant and get a response.
    
    Uses RAG for context retrieval and optionally enables tool calling
    for actions like exercise generation.
    
    Args:
        message: User's message text.
        conversation_id: Existing conversation UUID, or None to create new.
        enable_tools: Whether to enable tool calling (default True).
    
    Returns:
        ChatResponse with conversation_id, response text, sources, and tool results.
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
    
    # Search knowledge base for context
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
                        relevance=min(r.get("score", 0), 1.0),
                    )
                    for r in results if r.get("id")
                ]
        except Exception as e:
            logger.warning(f"Knowledge search failed: {e}")
    
    # Get conversation history
    history = await self._get_conversation_history(conversation)
    
    # Generate response (with or without tools)
    tool_results = []
    if enable_tools and self.llm and self.tool_registry:
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
    
    # Save assistant response
    await self._add_message(conversation, MessageRole.ASSISTANT, response_text)
    
    return ChatResponse(
        conversation_id=conversation.conversation_uuid,
        response=response_text,
        sources=sources,
        tool_calls=[
            ToolCallInfo(
                name=tr.tool_name,
                result=tr.result,
                success=tr.success,
            )
            for tr in tool_results
        ] if tool_results else None,
    )


async def _generate_response_with_tools(
    self,
    message: str,
    context: str = "",
    history: Optional[list[dict[str, str]]] = None,
) -> tuple[str, list[ToolCallResult]]:
    """
    Generate a response with tool calling support.
    
    Implements a tool calling loop:
    1. Send message to LLM with tool definitions
    2. If LLM returns tool_calls, execute them
    3. Send tool results back to LLM for final response
    """
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
        temperature=settings.ASSISTANT_LLM_TEMPERATURE,
        max_tokens=settings.ASSISTANT_LLM_MAX_TOKENS,
    )
    
    # Check for tool calls
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
    
    # Add tool results to messages
    messages.append({
        "role": "assistant",
        "content": response.get("content"),
        "tool_calls": tool_calls,
    })
    
    for i, (call, result) in enumerate(zip(tool_calls, tool_results)):
        messages.append({
            "role": "tool",
            "tool_call_id": call.get("id"),
            "content": json.dumps(result.result) if result.success else f"Error: {result.error}",
        })
    
    # Second LLM call for final response
    final_response, _ = await self.llm.complete(
        operation=PipelineOperation.CONTENT_ANALYSIS,
        messages=messages,
        temperature=settings.ASSISTANT_LLM_TEMPERATURE,
        max_tokens=settings.ASSISTANT_LLM_MAX_TOKENS,
    )
    
    return final_response, tool_results
```

---

## 5. API Changes

### 5.1 Updated Response Models

```python
# backend/app/models/assistant.py (additions)

class ToolCallInfo(BaseModel):
    """
    Information about a tool call made by the assistant.
    
    Attributes:
        name: Tool name that was called
        result: Tool execution result (type varies by tool)
        success: Whether the tool executed successfully
    """
    name: str
    result: Optional[dict] = None
    success: bool = True


class ChatResponse(BaseModel):
    """
    Response from the AI assistant.
    
    Attributes:
        conversation_id: The conversation this message belongs to
        response: Assistant's response text
        sources: Optional list of referenced sources
        tool_calls: Optional list of tool calls made (NEW)
    """
    conversation_id: str
    response: str
    sources: list[SourceReference] = Field(default_factory=list)
    tool_calls: Optional[list[ToolCallInfo]] = None  # NEW
```

### 5.2 Example API Response

```json
{
  "conversation_id": "abc123",
  "response": "I've generated a free recall exercise for you on attention mechanisms. Here's your exercise:\n\n**Exercise: Free Recall**\n\nWithout looking at your notes, explain the attention mechanism in transformers. Include:\n- The purpose of attention\n- How queries, keys, and values work\n- The computation of attention weights\n\n*Estimated time: 5 minutes*\n\nWould you like hints, or are you ready to try?",
  "sources": [
    {"id": "note-123", "title": "Transformer Architecture", "relevance": 0.92}
  ],
  "tool_calls": [
    {
      "name": "generate_exercise",
      "result": {
        "type": "exercise",
        "exercise_id": "ex-456",
        "exercise_type": "free_recall",
        "topic": "ml/transformers/attention",
        "difficulty": "intermediate",
        "prompt": "Without looking at your notes, explain the attention mechanism...",
        "hints": ["Think about the purpose of attention first", "..."],
        "estimated_time_minutes": 5
      },
      "success": true
    }
  ]
}
```

---

## 6. Frontend Integration

### 6.1 Updated Message Display

The frontend should handle `tool_calls` in responses to display rich content:

```jsx
// frontend/src/pages/Assistant.jsx (conceptual additions)

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

function ToolCallResult({ toolCall }) {
  if (!toolCall.success) {
    return <div className="tool-error">Tool failed: {toolCall.name}</div>;
  }
  
  switch (toolCall.result?.type) {
    case 'exercise':
      return <ExerciseCard exercise={toolCall.result} />;
    case 'flashcard':
      return <FlashcardCreated card={toolCall.result} />;
    case 'search_results':
      return <SearchResults results={toolCall.result.results} />;
    case 'mastery':
      return <MasteryDisplay mastery={toolCall.result} />;
    default:
      return null;
  }
}
```

### 6.2 Exercise Card Component

```jsx
function ExerciseCard({ exercise }) {
  const [showHints, setShowHints] = useState(false);
  
  return (
    <div className="bg-bg-elevated rounded-xl p-4 border border-border-primary mt-4">
      <div className="flex items-center gap-2 mb-3">
        <span className="text-xl">📝</span>
        <span className="font-medium">Exercise Generated</span>
        <Badge variant="info">{exercise.exercise_type}</Badge>
        <Badge variant="default">{exercise.difficulty}</Badge>
      </div>
      
      <p className="text-text-secondary text-sm mb-2">
        Topic: {exercise.topic}
      </p>
      
      {exercise.hints?.length > 0 && (
        <button 
          onClick={() => setShowHints(!showHints)}
          className="text-sm text-indigo-400 hover:text-indigo-300"
        >
          {showHints ? 'Hide hints' : `Show ${exercise.hints.length} hints`}
        </button>
      )}
      
      {showHints && (
        <ul className="mt-2 text-sm text-text-secondary">
          {exercise.hints.map((hint, i) => (
            <li key={i}>💡 {hint}</li>
          ))}
        </ul>
      )}
      
      <div className="mt-3 flex gap-2">
        <Button size="sm" variant="primary">
          Start Exercise
        </Button>
        <Button size="sm" variant="ghost">
          Practice Later
        </Button>
      </div>
    </div>
  );
}
```

---

## 7. System Prompt Updates

### 7.1 Assistant System Prompt with Tools

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

---

## 8. Error Handling

### 8.1 Tool Execution Errors

```python
class ToolExecutionError(Exception):
    """Raised when tool execution fails."""
    def __init__(self, tool_name: str, message: str):
        self.tool_name = tool_name
        self.message = message
        super().__init__(f"Tool '{tool_name}' failed: {message}")
```

### 8.2 Graceful Degradation

- If tool execution fails, include error in tool result and let LLM explain
- If LLM doesn't support tools, fall back to non-tool response
- If specific tool handler is unavailable (e.g., missing LLM client), return appropriate error

---

## 9. Configuration

### 9.1 Settings

```python
# backend/app/config/settings.py (additions)

class Settings(BaseSettings):
    # ... existing settings ...
    
    # Tool Calling
    ASSISTANT_TOOLS_ENABLED: bool = True
    ASSISTANT_TOOL_TIMEOUT_SECONDS: int = 30
    ASSISTANT_MAX_TOOL_CALLS_PER_MESSAGE: int = 3
```

---

## 10. Testing

### 10.1 Unit Tests

```python
# backend/tests/unit/test_tool_executor.py

import pytest
from app.services.assistant.tool_executor import ToolExecutor
from app.services.assistant.tool_registry import ToolRegistry

class TestToolExecutor:
    @pytest.fixture
    def executor(self, mock_registry):
        return ToolExecutor(mock_registry)
    
    async def test_execute_valid_tool(self, executor):
        result = await executor.execute(
            tool_name="generate_exercise",
            arguments={"topic": "ml/transformers"},
            context={"exercise_generator": mock_generator},
        )
        assert result.success
        assert result.result["type"] == "exercise"
    
    async def test_execute_unknown_tool(self, executor):
        result = await executor.execute(
            tool_name="unknown_tool",
            arguments={},
            context={},
        )
        assert not result.success
        assert "Unknown tool" in result.error
```

### 10.2 Integration Tests

```python
# backend/tests/integration/test_assistant_tools.py

async def test_chat_with_exercise_generation(
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
    assert len(data["tool_calls"]) == 1
    assert data["tool_calls"][0]["name"] == "generate_exercise"
    assert data["tool_calls"][0]["success"] is True
    assert data["tool_calls"][0]["result"]["type"] == "exercise"
```

---

## 11. Implementation Plan

### Phase 1: Core Infrastructure (1-2 days)
1. Create `ToolRegistry` and `ToolExecutor` classes
2. Add `complete_with_tools()` to LLMClient
3. Define initial tool schemas

### Phase 2: Tool Handlers (2-3 days)
1. Implement `generate_exercise` handler
2. Implement `create_flashcard` handler
3. Implement `search_knowledge` handler
4. Implement `get_mastery` and `get_weak_spots` handlers

### Phase 3: Service Integration (1-2 days)
1. Update `AssistantService.chat()` with tool calling loop
2. Update response models with `tool_calls`
3. Update system prompt

### Phase 4: Frontend (2-3 days)
1. Handle `tool_calls` in chat responses
2. Create exercise card component
3. Create flashcard confirmation component
4. Polish UI/UX

### Phase 5: Testing & Polish (1-2 days)
1. Unit tests for tool executor
2. Integration tests for chat with tools
3. Error handling edge cases

---

## 12. Future Enhancements

### Phase 2 Considerations
- **Streaming with tools**: Stream text, then append tool results
- **Multi-turn tool use**: Allow follow-up tool calls based on results
- **Tool confirmation**: Ask user before executing certain tools
- **Custom tools**: Allow users to define simple tools

### Additional Tools
- `schedule_review`: Schedule a topic for review at specific time
- `create_note`: Create a new note in Obsidian vault
- `explain_connection`: Explain how two concepts are related
- `suggest_reading`: Suggest content to read based on learning goals

---

## 13. Related Documents

- `05_learning_system.md` — Exercise generation and mastery tracking
- `06_backend_api.md` — API structure and patterns
- `07_frontend_application.md` — Frontend components
- `09_data_models.md` — Data models and schemas
