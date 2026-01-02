"""
Text Completion Wrapper using LiteLLM

LiteLLM provides a unified interface to 100+ LLM providers using
the format "provider/model-name".

Key features over simpler abstractions (e.g., AISuite):
- Built-in spend tracking and cost logging
- Rate limiting (TPM/RPM) to prevent runaway costs
- Budget limits with alerts
- Automatic fallbacks to backup models
- Native async support (acompletion)

Configuration (via app.config.settings):
- TEXT_MODEL: Default model for text completion
- API keys: OPENAI_API_KEY, MISTRAL_API_KEY, ANTHROPIC_API_KEY, etc.

See: https://docs.litellm.ai/

Usage:
    from app.pipelines.utils.text_client import text_completion

    response, usage = await text_completion(
        model="openai/gpt-4o-mini",
        prompt="Summarize this text in 3 bullet points",
        pipeline="voice_transcribe",
        operation="note_expansion"
    )
"""

import logging
import os
import time
from typing import Optional

import litellm
from litellm import completion, acompletion

from app.config.settings import settings
from app.pipelines.utils.cost_types import (
    LLMUsage,
    extract_usage_from_response,
    create_error_usage,
)
from app.pipelines.utils.api_utils import adjust_temperature_for_model

logger = logging.getLogger(__name__)

# Configure LiteLLM logging (set_verbose is deprecated)
if settings.DEBUG:
    os.environ["LITELLM_LOG"] = "DEBUG"


def _build_messages(
    prompt: str,
    system_prompt: Optional[str] = None,
) -> list[dict[str, str]]:
    """Build messages list from prompt and optional system prompt."""
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})

    messages.append({"role": "user", "content": prompt})

    return messages


def _build_kwargs(
    model: str,
    messages: list[dict[str, str]],
    max_tokens: int,
    temperature: float,
    json_mode: bool,
) -> dict:
    """Build completion kwargs dict."""
    # Adjust temperature for models that require specific values
    adjusted_temp = adjust_temperature_for_model(model, temperature)

    kwargs = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": adjusted_temp,
    }

    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}

    return kwargs


def _process_response(
    response,
    model: str,
    latency_ms: int,
    pipeline: Optional[str],
    content_id: Optional[int],
    operation: Optional[str],
) -> tuple[str, LLMUsage]:
    """Extract content and usage from response, log if cost available."""
    usage = extract_usage_from_response(
        response=response,
        model=model,
        request_type="text",
        latency_ms=latency_ms,
        pipeline=pipeline,
        content_id=content_id,
        operation=operation,
    )

    if usage.cost_usd:
        logger.info(
            f"Text completion [{model}] - "
            f"Cost: ${usage.cost_usd:.4f}, "
            f"Tokens: {usage.total_tokens}, "
            f"Latency: {usage.latency_ms}ms"
        )

    logger.debug(f"Text completion successful with {model}")
    return response.choices[0].message.content, usage


def _handle_error(
    error: Exception,
    model: str,
    latency_ms: int,
    pipeline: Optional[str],
    content_id: Optional[int],
    operation: Optional[str],
) -> None:
    """Create error usage record and log error. Always re-raises."""
    create_error_usage(
        model=model,
        request_type="text",
        latency_ms=latency_ms,
        error_message=str(error),
        pipeline=pipeline,
        content_id=content_id,
        operation=operation,
    )
    logger.error(f"Text completion failed with {model}: {error}")
    raise error


def text_completion_sync(
    model: str,
    prompt: str,
    system_prompt: Optional[str] = None,
    max_tokens: int = 2000,
    json_mode: bool = False,
    temperature: float = 0.7,
    pipeline: Optional[str] = None,
    content_id: Optional[int] = None,
    operation: Optional[str] = None,
) -> tuple[str, LLMUsage]:
    """
    Execute text completion with any LiteLLM-supported model (synchronous).

    Args:
        model: LiteLLM model identifier (format: "provider/model-name")
               e.g., "openai/gpt-4o-mini", "anthropic/claude-sonnet-4-20250514"
        prompt: Text prompt for the model (user message)
        system_prompt: Optional system prompt to set context/behavior
        max_tokens: Maximum tokens in response
        json_mode: Request structured JSON output
        temperature: Sampling temperature (lower = more deterministic)
        pipeline: Name of calling pipeline for cost attribution
        content_id: Associated content ID for cost attribution
        operation: Specific operation name (e.g., "note_expansion")

    Returns:
        Tuple of (response_text, LLMUsage with cost/token info)

    Example:
        >>> response, usage = text_completion_sync(
        ...     model="openai/gpt-4o-mini",
        ...     prompt="Summarize: Today we discussed project timelines...",
        ...     system_prompt="You are a helpful note-taking assistant.",
        ...     pipeline="voice_transcribe",
        ...     operation="note_expansion"
        ... )
        >>> print(f"Cost: ${usage.cost_usd:.4f}")
    """
    messages = _build_messages(prompt, system_prompt)
    kwargs = _build_kwargs(model, messages, max_tokens, temperature, json_mode)

    start_time = time.perf_counter()
    try:
        response = completion(**kwargs)
        latency_ms = int((time.perf_counter() - start_time) * 1000)
        return _process_response(
            response, model, latency_ms, pipeline, content_id, operation
        )
    except Exception as e:
        latency_ms = int((time.perf_counter() - start_time) * 1000)
        _handle_error(e, model, latency_ms, pipeline, content_id, operation)


async def text_completion(
    model: str,
    prompt: str,
    system_prompt: Optional[str] = None,
    max_tokens: int = 2000,
    json_mode: bool = False,
    temperature: float = 0.7,
    pipeline: Optional[str] = None,
    content_id: Optional[int] = None,
    operation: Optional[str] = None,
) -> tuple[str, LLMUsage]:
    """
    Async text completion using LiteLLM's native acompletion.

    This is the preferred method for use in async contexts (FastAPI, Celery async).

    Args:
        model: LiteLLM model identifier (format: "provider/model-name")
        prompt: Text prompt for the model (user message)
        system_prompt: Optional system prompt to set context/behavior
        max_tokens: Maximum tokens in response
        json_mode: Request structured JSON output
        temperature: Sampling temperature
        pipeline: Name of calling pipeline for cost attribution
        content_id: Associated content ID for cost attribution
        operation: Specific operation name

    Returns:
        Tuple of (response_text, LLMUsage with cost/token info)
    """
    messages = _build_messages(prompt, system_prompt)
    return await text_completion_chat(
        model=model,
        messages=messages,
        max_tokens=max_tokens,
        json_mode=json_mode,
        temperature=temperature,
        pipeline=pipeline,
        content_id=content_id,
        operation=operation,
    )


async def text_completion_with_context(
    model: str,
    prompt: str,
    context: str,
    system_prompt: Optional[str] = None,
    max_tokens: int = 2000,
    json_mode: bool = False,
    temperature: float = 0.7,
    pipeline: Optional[str] = None,
    content_id: Optional[int] = None,
    operation: Optional[str] = None,
) -> tuple[str, LLMUsage]:
    """
    Text completion with separate context and prompt.

    Useful when you have a large context (e.g., document text) and a
    specific question or instruction about that context.

    Args:
        model: LiteLLM model identifier
        prompt: Instruction or question about the context
        context: Background context or document text
        system_prompt: Optional system prompt
        max_tokens: Maximum tokens
        json_mode: Request JSON output
        temperature: Sampling temperature
        pipeline: Name of calling pipeline for cost attribution
        content_id: Associated content ID for cost attribution
        operation: Specific operation name

    Returns:
        Tuple of (response_text, LLMUsage with cost/token info)

    Example:
        >>> response, usage = await text_completion_with_context(
        ...     model="openai/gpt-4o-mini",
        ...     prompt="Extract the book title and author from this text.",
        ...     context="The text from page 1 of the book...",
        ...     json_mode=True,
        ...     pipeline="book_ocr",
        ...     operation="metadata_inference"
        ... )
    """
    full_prompt = f"Context:\n{context}\n\n---\n\n{prompt}"
    return await text_completion(
        model=model,
        prompt=full_prompt,
        system_prompt=system_prompt,
        max_tokens=max_tokens,
        json_mode=json_mode,
        temperature=temperature,
        pipeline=pipeline,
        content_id=content_id,
        operation=operation,
    )


async def text_completion_chat(
    model: str,
    messages: list[dict[str, str]],
    max_tokens: int = 2000,
    json_mode: bool = False,
    temperature: float = 0.7,
    pipeline: Optional[str] = None,
    content_id: Optional[int] = None,
    operation: Optional[str] = None,
) -> tuple[str, LLMUsage]:
    """
    Text completion with full message history (chat format).

    This is the core async completion function. Other async functions delegate to this.

    Args:
        model: LiteLLM model identifier
        messages: List of message dicts with 'role' and 'content' keys
                  Roles: 'system', 'user', 'assistant'
        max_tokens: Maximum tokens
        json_mode: Request JSON output
        temperature: Sampling temperature
        pipeline: Name of calling pipeline for cost attribution
        content_id: Associated content ID for cost attribution
        operation: Specific operation name

    Returns:
        Tuple of (response_text, LLMUsage with cost/token info)

    Example:
        >>> messages = [
        ...     {"role": "system", "content": "You are a helpful assistant."},
        ...     {"role": "user", "content": "What is 2+2?"},
        ...     {"role": "assistant", "content": "4"},
        ...     {"role": "user", "content": "And 3+3?"}
        ... ]
        >>> response, usage = await text_completion_chat(
        ...     model="openai/gpt-4o-mini",
        ...     messages=messages,
        ...     pipeline="test",
        ...     operation="math"
        ... )
    """
    kwargs = _build_kwargs(model, messages, max_tokens, temperature, json_mode)

    start_time = time.perf_counter()
    try:
        response = await acompletion(**kwargs)
        latency_ms = int((time.perf_counter() - start_time) * 1000)
        return _process_response(
            response, model, latency_ms, pipeline, content_id, operation
        )
    except Exception as e:
        latency_ms = int((time.perf_counter() - start_time) * 1000)
        _handle_error(e, model, latency_ms, pipeline, content_id, operation)


def get_default_text_model() -> str:
    """Get the default text model from settings."""
    return settings.TEXT_MODEL
