"""
Unified LLM Client supporting multiple providers via LiteLLM.

LiteLLM provides a unified interface to 100+ LLM providers using
the format "provider/model-name". Key features:
- Operation-based model selection via PipelineOperation enum
- Built-in cost tracking via LLMUsage
- Automatic retries with exponential backoff
- Native async support

See: https://docs.litellm.ai/

Usage:
    from app.enums import PipelineName, PipelineOperation
    from app.services.llm import get_llm_client

    client = get_llm_client()

    # Async completion with usage tracking
    response, usage = await client.complete(
        operation=PipelineOperation.SUMMARIZATION,
        messages=[{"role": "user", "content": "Summarize..."}],
        pipeline=PipelineName.WEB_ARTICLE,
        content_id="uuid-here",
    )
    print(f"Cost: ${usage.cost_usd:.4f}")

    # Sync completion (for Celery tasks)
    response, usage = client.complete_sync(
        operation=PipelineOperation.CONTENT_TYPE_CLASSIFICATION,
        messages=[...]
    )

    # Generate embeddings
    embeddings, usage = await client.embed(["text1", "text2"])
"""

import json
import logging
import os
import time
from typing import Any, Optional, Union

import litellm
from litellm import acompletion, aembedding, completion, embedding
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config.settings import settings
from app.enums.pipeline import PipelineName, PipelineOperation
from app.models.llm_usage import (
    LLMUsage,
    extract_usage_from_response,
    create_error_usage,
)

logger = logging.getLogger(__name__)

# Configure LiteLLM
litellm.drop_params = True  # Drop unsupported params instead of erroring
if settings.DEBUG:
    os.environ["LITELLM_LOG"] = "DEBUG"


def get_default_text_model() -> str:
    """Get the default text model from settings."""
    return settings.TEXT_MODEL


def build_messages(
    prompt: str,
    system_prompt: Optional[str] = None,
) -> list[dict[str, str]]:
    """
    Build messages list from prompt and optional system prompt.

    Args:
        prompt: User prompt text
        system_prompt: Optional system prompt

    Returns:
        List of message dicts for LLM API
    """
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})
    return messages


def _adjust_temperature_for_model(model: str, temperature: float) -> float:
    """
    Adjust temperature based on model requirements.

    Some models have specific temperature requirements:
    - Gemini 3 models require temperature=1.0 to avoid infinite loops
      and degraded reasoning performance.

    Args:
        model: Model identifier (e.g., "gemini/gemini-3-flash-preview")
        temperature: Requested temperature value

    Returns:
        Adjusted temperature value appropriate for the model
    """
    # Gemini 3 models need temperature=1.0
    if "gemini-3" in model.lower():
        return 1.0
    return temperature


class LLMClient:
    """
    Unified LLM client with operation-based model selection and usage tracking.

    Provides async and sync methods for completions and embeddings.
    Automatically selects the configured model for each operation type
    and returns detailed LLMUsage objects for cost tracking.

    Operations are defined in PipelineOperation enum and cover:
    - Text operations: summarization, extraction, classification, etc.
    - Vision operations: page_extraction, document_ocr, etc.
    - Embeddings: vector representations

    Attributes:
        MODELS: Operation -> model mapping from settings
    """

    # Model mapping by operation - uses settings for configurability
    # Operations not explicitly mapped use the default TEXT_MODEL
    MODELS = {
        # Vision/OCR operations use VLM
        PipelineOperation.PAGE_EXTRACTION: settings.VLM_MODEL,
        PipelineOperation.DOCUMENT_OCR: settings.VLM_MODEL,
        # Embeddings
        PipelineOperation.EMBEDDINGS: "openai/text-embedding-3-small",
        # All other operations default to TEXT_MODEL (see get_model_for_operation)
    }

    def __init__(self):
        """Initialize the LLM client and validate API keys."""
        self._validate_api_keys()

    def _validate_api_keys(self):
        """
        Verify at least one API key is set.

        Raises:
            ValueError: If no API keys are configured
        """
        available_keys = []

        if os.getenv("OPENAI_API_KEY") or settings.OPENAI_API_KEY:
            available_keys.append("OpenAI")
        if os.getenv("ANTHROPIC_API_KEY") or settings.ANTHROPIC_API_KEY:
            available_keys.append("Anthropic")
        if os.getenv("GEMINI_API_KEY") or settings.GEMINI_API_KEY:
            available_keys.append("Google/Gemini")
        if os.getenv("MISTRAL_API_KEY") or settings.MISTRAL_API_KEY:
            available_keys.append("Mistral")

        if not available_keys:
            logger.warning(
                "No LLM API keys configured. Set at least one of: "
                "OPENAI_API_KEY, ANTHROPIC_API_KEY, GEMINI_API_KEY, MISTRAL_API_KEY"
            )
        else:
            logger.info(f"LLM client initialized with providers: {available_keys}")

    def get_model_for_operation(self, operation: Union[PipelineOperation, str]) -> str:
        """
        Get the configured model for a specific operation.

        Args:
            operation: PipelineOperation enum value

        Returns:
            Model identifier in LiteLLM format (provider/model-name)
        """
        # Convert string to enum if needed (backward compatibility)
        if isinstance(operation, str):
            try:
                operation = PipelineOperation(operation)
            except ValueError:
                logger.warning(
                    f"Unknown operation type: {operation}, using default model"
                )
                return settings.TEXT_MODEL
        return self.MODELS.get(operation, settings.TEXT_MODEL)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        reraise=True,
    )
    async def complete(
        self,
        operation: Union[PipelineOperation, str],
        messages: list[dict],
        temperature: float = 0.3,
        max_tokens: int = 4096,
        json_mode: bool = False,
        pipeline: Optional[Union[PipelineName, str]] = None,
        content_id: Optional[str] = None,
        model: Optional[str] = None,
    ) -> tuple[Union[str, Any], LLMUsage]:
        """
        Generate a completion using the appropriate model for the operation.

        Args:
            operation: PipelineOperation enum specifying the operation type.
                Used for both model selection and cost attribution.
            messages: Chat messages in OpenAI format
                [{"role": "user", "content": "..."}, ...]
            temperature: Sampling temperature (0-1, lower = more deterministic)
            max_tokens: Maximum tokens in response
            json_mode: Request structured JSON output and parse response as JSON.
                Returns parsed dict/list. JSONDecodeError triggers retry.
            pipeline: PipelineName enum for cost attribution (which pipeline)
            content_id: Content UUID for cost attribution
            model: Optional model override (bypasses operation-based selection)

        Returns:
            Tuple of (response_text or parsed JSON if json_mode, LLMUsage)

        Raises:
            json.JSONDecodeError: If json_mode=True and response is not valid JSON
                after all retries
            Exception: If completion fails after retries
        """
        model = model or self.get_model_for_operation(operation)
        adjusted_temp = _adjust_temperature_for_model(model, temperature)

        kwargs = {
            "model": model,
            "messages": messages,
            "temperature": adjusted_temp,
            "max_tokens": max_tokens,
        }

        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        start_time = time.perf_counter()

        try:
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

            if usage.cost_usd:
                logger.debug(
                    f"LLM completion [{model}] - Cost: ${usage.cost_usd:.4f}, "
                    f"Tokens: {usage.total_tokens}, Latency: {latency_ms}ms"
                )

            content = response.choices[0].message.content

            if json_mode:
                # JSONDecodeError will trigger @retry
                content = json.loads(content)

            return content, usage

        except json.JSONDecodeError:
            # Let @retry handle JSON parse failures
            logger.warning(f"JSON decode error, will retry (model={model})")
            raise
        except Exception as e:
            latency_ms = int((time.perf_counter() - start_time) * 1000)
            logger.error(f"LLM completion failed: {e} (model={model})")

            # Create error usage for tracking
            create_error_usage(
                model=model,
                request_type="text",
                latency_ms=latency_ms,
                error_message=str(e),
                pipeline=pipeline,
                content_id=content_id,
                operation=operation,
            )
            raise

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        reraise=True,
    )
    def complete_sync(
        self,
        operation: Union[PipelineOperation, str],
        messages: list[dict],
        temperature: float = 0.3,
        max_tokens: int = 4096,
        json_mode: bool = False,
        pipeline: Optional[Union[PipelineName, str]] = None,
        content_id: Optional[str] = None,
        model: Optional[str] = None,
    ) -> tuple[Union[str, Any], LLMUsage]:
        """
        Synchronous completion for use in Celery tasks and other sync contexts.

        Why this exists (vs using complete()):
            Celery workers run tasks in a synchronous context by default - there is
            no active event loop. The async complete() method uses `await acompletion()`
            which requires an event loop, making it unusable directly in Celery tasks.

            While you could use `asyncio.run()` to create a new event loop per call,
            this adds overhead and can cause issues with nested loops and connection
            pooling. This method uses LiteLLM's native sync `completion()` function
            instead, which is the cleanest approach for sync contexts.

        When to use which:
            - FastAPI endpoints: use `await complete()` (async context)
            - Celery tasks: use `complete_sync()` (sync context)
            - Sync scripts/CLI: use `complete_sync()` (sync context)

        Args:
            operation: PipelineOperation enum specifying the operation type.
                Used for both model selection and cost attribution.
            messages: Chat messages in OpenAI format
            temperature: Sampling temperature (0-1)
            max_tokens: Maximum tokens in response
            json_mode: Request structured JSON output and parse response as JSON.
                Returns parsed dict/list. JSONDecodeError triggers retry.
            pipeline: PipelineName enum for cost attribution (which pipeline)
            content_id: Content UUID for cost attribution
            model: Optional model override (bypasses operation-based selection)

        Returns:
            Tuple of (response_text or parsed JSON if json_mode, LLMUsage)
        """
        model = model or self.get_model_for_operation(operation)
        adjusted_temp = _adjust_temperature_for_model(model, temperature)

        kwargs = {
            "model": model,
            "messages": messages,
            "temperature": adjusted_temp,
            "max_tokens": max_tokens,
        }

        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        start_time = time.perf_counter()

        try:
            response = completion(**kwargs)
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

            content = response.choices[0].message.content

            if json_mode:
                # JSONDecodeError will trigger @retry
                content = json.loads(content)

            return content, usage

        except json.JSONDecodeError:
            # Let @retry handle JSON parse failures
            logger.warning(f"JSON decode error, will retry (model={model})")
            raise
        except Exception as e:
            latency_ms = int((time.perf_counter() - start_time) * 1000)
            logger.error(f"LLM completion failed: {e} (model={model})")

            create_error_usage(
                model=model,
                request_type="text",
                latency_ms=latency_ms,
                error_message=str(e),
                pipeline=pipeline,
                content_id=content_id,
                operation=operation,
            )
            raise

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        reraise=True,
    )
    async def embed(
        self,
        texts: list[str],
        pipeline: Optional[Union[PipelineName, str]] = None,
        content_id: Optional[str] = None,
    ) -> tuple[list[list[float]], LLMUsage]:
        """
        Generate embeddings for a list of texts.

        Args:
            texts: List of texts to embed
            pipeline: PipelineName enum for cost attribution
            content_id: Content UUID for cost attribution

        Returns:
            Tuple of (list of embedding vectors, LLMUsage)
        """
        operation = PipelineOperation.EMBEDDINGS
        model = self.get_model_for_operation(operation)

        start_time = time.perf_counter()
        response = await aembedding(model=model, input=texts)
        latency_ms = int((time.perf_counter() - start_time) * 1000)

        usage = extract_usage_from_response(
            response=response,
            model=model,
            request_type="embedding",
            latency_ms=latency_ms,
            pipeline=pipeline,
            content_id=content_id,
            operation=operation,
        )

        embeddings = [item["embedding"] for item in response.data]
        return embeddings, usage

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        reraise=True,
    )
    def embed_sync(
        self,
        texts: list[str],
        pipeline: Optional[Union[PipelineName, str]] = None,
        content_id: Optional[str] = None,
    ) -> tuple[list[list[float]], LLMUsage]:
        """
        Synchronous embedding for use in Celery tasks and other sync contexts.

        See complete_sync() docstring for detailed explanation of why sync
        variants are needed for Celery (no event loop in worker context).

        Args:
            texts: List of texts to embed
            pipeline: PipelineName enum for cost attribution
            content_id: Content UUID for cost attribution

        Returns:
            Tuple of (list of embedding vectors, LLMUsage)
        """
        operation = PipelineOperation.EMBEDDINGS
        model = self.get_model_for_operation(operation)

        start_time = time.perf_counter()
        response = embedding(model=model, input=texts)
        latency_ms = int((time.perf_counter() - start_time) * 1000)

        usage = extract_usage_from_response(
            response=response,
            model=model,
            request_type="embedding",
            latency_ms=latency_ms,
            pipeline=pipeline,
            content_id=content_id,
            operation=operation,
        )

        embeddings = [item["embedding"] for item in response.data]
        return embeddings, usage

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        reraise=True,
    )
    async def complete_with_vision(
        self,
        operation: Union[PipelineOperation, str],
        messages: list[dict],
        images: list[str],
        temperature: float = 0.3,
        max_tokens: int = 4096,
        json_mode: bool = False,
        pipeline: Optional[Union[PipelineName, str]] = None,
        content_id: Optional[str] = None,
    ) -> tuple[Union[str, Any], LLMUsage]:
        """
        Generate a completion with image inputs.

        Args:
            operation: PipelineOperation enum (e.g., PAGE_EXTRACTION, DOCUMENT_OCR).
                Used for both model selection and cost attribution.
            messages: Chat messages with text content
            images: List of base64-encoded images or URLs
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response
            json_mode: Request structured JSON output and parse response as JSON.
                Returns parsed dict/list. JSONDecodeError triggers retry.
            pipeline: PipelineName enum for cost attribution (which pipeline)
            content_id: Content UUID for cost attribution

        Returns:
            Tuple of (response_text or parsed JSON if json_mode, LLMUsage)
        """
        model = self.get_model_for_operation(operation)
        adjusted_temp = _adjust_temperature_for_model(model, temperature)

        # Format messages with images for vision models
        formatted_messages = []
        for msg in messages:
            if msg["role"] == "user" and images:
                content = [{"type": "text", "text": msg["content"]}]
                for img in images:
                    if img.startswith("http"):
                        content.append({"type": "image_url", "image_url": {"url": img}})
                    else:
                        content.append(
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/jpeg;base64,{img}"},
                            }
                        )
                formatted_messages.append({"role": "user", "content": content})
            else:
                formatted_messages.append(msg)

        kwargs = {
            "model": model,
            "messages": formatted_messages,
            "temperature": adjusted_temp,
            "max_tokens": max_tokens,
        }

        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        start_time = time.perf_counter()
        response = await acompletion(**kwargs)
        latency_ms = int((time.perf_counter() - start_time) * 1000)

        usage = extract_usage_from_response(
            response=response,
            model=model,
            request_type="vision",
            latency_ms=latency_ms,
            pipeline=pipeline,
            content_id=content_id,
            operation=operation,
        )

        content = response.choices[0].message.content

        if json_mode:
            # JSONDecodeError will trigger @retry
            content = json.loads(content)

        return content, usage


# Singleton instance
_client: Optional[LLMClient] = None


def get_llm_client() -> LLMClient:
    """
    Get or create singleton LLM client.

    Returns:
        Shared LLMClient instance
    """
    global _client
    if _client is None:
        _client = LLMClient()
    return _client


def reset_llm_client():
    """Reset the singleton client (useful for testing)."""
    global _client
    _client = None
