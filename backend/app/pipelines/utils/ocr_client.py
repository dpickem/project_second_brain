"""
Vision/OCR Completion Wrapper using LiteLLM

LiteLLM provides a unified interface to 100+ LLM providers using
the format "provider/model-name". Supported vision providers include:
- Mistral: mistral/mistral-ocr-2512 (Mistral OCR 3 - best for structured docs)
- OpenAI: openai/gpt-4.1-chat-latest
- Anthropic: anthropic/claude-sonnet-4-20250514
- Google: gemini/gemini-2.5-flash
- Azure: azure/gpt-4-vision

Key features over simpler abstractions (e.g., AISuite):
- Built-in spend tracking and cost logging
- Rate limiting (TPM/RPM) to prevent runaway costs
- Budget limits with alerts
- Automatic fallbacks to backup models
- Native async support (acompletion)

Configuration (via app.config.settings):
- OCR_MODEL: Default model for vision completion
- API keys: OPENAI_API_KEY, MISTRAL_API_KEY, etc.

See: https://docs.litellm.ai/

Usage:
    from app.pipelines.utils.ocr_client import vision_completion

    response, usage = await vision_completion(
        model="mistral/mistral-ocr-2512",
        prompt="Extract all text from this image",
        image_data=base64_image,
        json_mode=True,
        pipeline="book_ocr",
        operation="page_extraction"
    )
"""

import logging
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

logger = logging.getLogger(__name__)

# Configure LiteLLM settings
litellm.set_verbose = settings.DEBUG


def vision_completion_sync(
    model: str,
    prompt: str,
    image_data: str,
    max_tokens: int = 4000,
    json_mode: bool = False,
    image_format: str = "png",
    temperature: float = 0.1,
    # Cost tracking context
    pipeline: Optional[str] = None,
    content_id: Optional[int] = None,
    operation: Optional[str] = None,
) -> tuple[str, LLMUsage]:
    """
    Execute vision completion with any LiteLLM-supported model (synchronous).

    Args:
        model: LiteLLM model identifier (format: "provider/model-name")
               e.g., "mistral/mistral-ocr-2512", "openai/gpt-4.1-chat-latest"
        prompt: Text prompt for the vision model
        image_data: Base64-encoded image data
        max_tokens: Maximum tokens in response
        json_mode: Request structured JSON output
        image_format: Image MIME type suffix (png, jpeg, etc.)
        temperature: Sampling temperature (lower = more deterministic)
        pipeline: Name of calling pipeline for cost attribution
        content_id: Associated content ID for cost attribution
        operation: Specific operation name (e.g., "handwriting_detection")

    Returns:
        Tuple of (response_text, LLMUsage with cost/token info)

    Example:
        >>> response, usage = vision_completion_sync(
        ...     model="mistral/mistral-ocr-2512",
        ...     prompt="Extract all text from this image",
        ...     image_data=base64_image,
        ...     json_mode=True,
        ...     pipeline="book_ocr",
        ...     operation="page_extraction"
        ... )
        >>> print(f"Cost: ${usage.cost_usd:.4f}")
    """
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/{image_format};base64,{image_data}"
                    },
                },
            ],
        }
    ]

    kwargs = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }

    # Add JSON mode if supported by model
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}

    start_time = time.perf_counter()

    try:
        response = completion(**kwargs)
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

        if usage.cost_usd:
            logger.info(
                f"Vision completion [{model}] - "
                f"Cost: ${usage.cost_usd:.4f}, "
                f"Tokens: {usage.total_tokens}, "
                f"Latency: {usage.latency_ms}ms"
            )

        logger.debug(f"Vision completion successful with {model}")
        return response.choices[0].message.content, usage

    except Exception as e:
        latency_ms = int((time.perf_counter() - start_time) * 1000)
        usage = create_error_usage(
            model=model,
            request_type="vision",
            latency_ms=latency_ms,
            error_message=str(e),
            pipeline=pipeline,
            content_id=content_id,
            operation=operation,
        )
        logger.error(f"Vision completion failed with {model}: {e}")
        raise


async def vision_completion(
    model: str,
    prompt: str,
    image_data: str,
    max_tokens: int = 4000,
    json_mode: bool = False,
    image_format: str = "png",
    temperature: float = 0.1,
    # Cost tracking context
    pipeline: Optional[str] = None,
    content_id: Optional[int] = None,
    operation: Optional[str] = None,
) -> tuple[str, LLMUsage]:
    """
    Async version of vision_completion using LiteLLM's native acompletion.

    This is the preferred method for use in async contexts (FastAPI, Celery async).

    Args:
        model: LiteLLM model identifier (format: "provider/model-name")
        prompt: Text prompt for the vision model
        image_data: Base64-encoded image data
        max_tokens: Maximum tokens in response
        json_mode: Request structured JSON output
        image_format: Image MIME type suffix
        temperature: Sampling temperature
        pipeline: Name of calling pipeline for cost attribution
        content_id: Associated content ID for cost attribution
        operation: Specific operation name

    Returns:
        Tuple of (response_text, LLMUsage with cost/token info)
    """
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/{image_format};base64,{image_data}"
                    },
                },
            ],
        }
    ]

    kwargs = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
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
            request_type="vision",
            latency_ms=latency_ms,
            pipeline=pipeline,
            content_id=content_id,
            operation=operation,
        )

        if usage.cost_usd:
            logger.info(
                f"Vision completion [{model}] - "
                f"Cost: ${usage.cost_usd:.4f}, "
                f"Tokens: {usage.total_tokens}, "
                f"Latency: {usage.latency_ms}ms"
            )

        logger.debug(f"Vision completion successful with {model}")
        return response.choices[0].message.content, usage

    except Exception as e:
        latency_ms = int((time.perf_counter() - start_time) * 1000)
        usage = create_error_usage(
            model=model,
            request_type="vision",
            latency_ms=latency_ms,
            error_message=str(e),
            pipeline=pipeline,
            content_id=content_id,
            operation=operation,
        )
        logger.error(f"Vision completion failed with {model}: {e}")
        raise


async def vision_completion_multi_image(
    model: str,
    prompt: str,
    images: list[str],
    max_tokens: int = 4000,
    json_mode: bool = False,
    image_format: str = "png",
    temperature: float = 0.1,
    # Cost tracking context
    pipeline: Optional[str] = None,
    content_id: Optional[int] = None,
    operation: Optional[str] = None,
) -> tuple[str, LLMUsage]:
    """
    Vision completion with multiple images.

    Useful for comparing documents or processing multi-page content.

    Args:
        model: LiteLLM model identifier
        prompt: Text prompt
        images: List of base64-encoded images
        max_tokens: Maximum tokens
        json_mode: Request JSON output
        image_format: Image MIME type
        temperature: Sampling temperature
        pipeline: Name of calling pipeline for cost attribution
        content_id: Associated content ID for cost attribution
        operation: Specific operation name

    Returns:
        Tuple of (response_text, LLMUsage with cost/token info)
    """
    content = [{"type": "text", "text": prompt}]

    for img_data in images:
        content.append(
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/{image_format};base64,{img_data}"},
            }
        )

    messages = [{"role": "user", "content": content}]

    kwargs = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
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
            request_type="vision",
            latency_ms=latency_ms,
            pipeline=pipeline,
            content_id=content_id,
            operation=operation,
        )

        if usage.cost_usd:
            logger.info(
                f"Multi-image vision [{model}] - "
                f"Cost: ${usage.cost_usd:.4f}, "
                f"Images: {len(images)}, "
                f"Tokens: {usage.total_tokens}"
            )

        return response.choices[0].message.content, usage

    except Exception as e:
        latency_ms = int((time.perf_counter() - start_time) * 1000)
        usage = create_error_usage(
            model=model,
            request_type="vision",
            latency_ms=latency_ms,
            error_message=str(e),
            pipeline=pipeline,
            content_id=content_id,
            operation=operation,
        )
        logger.error(f"Multi-image vision completion failed: {e}")
        raise


def get_default_ocr_model() -> str:
    """Get the default OCR model from settings."""
    return settings.OCR_MODEL
