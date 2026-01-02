"""
Vision Language Model (VLM) Completion Client using LiteLLM

LiteLLM provides a unified interface to 100+ LLM providers using
the format "provider/model-name". This client handles vision/image
understanding tasks using chat-based vision models.

Supported Vision Chat Models:
- Google: gemini/gemini-2.5-flash, gemini/gemini-2.0-flash
- OpenAI: openai/gpt-4o, openai/gpt-4o-mini
- Anthropic: anthropic/claude-sonnet-4-20250514

For dedicated OCR tasks (PDF document processing), use the mistral_ocr_client
module which provides direct access to Mistral's specialized OCR API.

Key features:
- Built-in spend tracking and cost logging
- Rate limiting (TPM/RPM) to prevent runaway costs
- Budget limits with alerts
- Automatic fallbacks to backup models
- Native async support

Configuration (via app.config.settings):
- VLM_MODEL: Default model for vision completion
- API keys: OPENAI_API_KEY, GOOGLE_API_KEY, ANTHROPIC_API_KEY, etc.

See: https://docs.litellm.ai/docs/providers

Usage:
    from app.pipelines.utils.vlm_client import vision_completion

    # Single image vision
    response, usage = await vision_completion(
        model="gemini/gemini-2.5-flash",
        prompt="Describe this image",
        image_data=base64_image,
        pipeline="book_ocr",
    )
"""

import logging
import os
import time
from typing import Any, Optional

from litellm import acompletion, completion

from app.config.settings import settings
from app.pipelines.utils.api_utils import adjust_temperature_for_model
from app.pipelines.utils.cost_types import (
    LLMUsage,
    create_error_usage,
    extract_usage_from_response,
)

logger = logging.getLogger(__name__)

# Configure LiteLLM logging (set_verbose is deprecated)
if settings.DEBUG:
    os.environ["LITELLM_LOG"] = "DEBUG"


# =============================================================================
# Helper Functions
# =============================================================================


def get_default_vlm_model() -> str:
    """
    Get the default Vision Language Model from settings.

    Returns the configured VLM_MODEL, falling back to OCR_MODEL for
    backwards compatibility.
    """
    return getattr(settings, "VLM_MODEL", None) or settings.OCR_MODEL


# TODO: Remove this. we don't care about backwards compatibility anymore.
# Keep old name for backwards compatibility
get_default_ocr_model = get_default_vlm_model


# =============================================================================
# Public API - Vision Completion
# =============================================================================


async def vision_completion(
    model: str,
    prompt: str,
    image_data: str,
    max_tokens: int = 4000,
    json_mode: bool = False,
    image_format: str = "png",
    temperature: float = 0.1,
    pipeline: Optional[str] = None,
    content_id: Optional[int] = None,
    operation: Optional[str] = None,
) -> tuple[str, LLMUsage]:
    """
    Async vision completion using LiteLLM with chat-based vision models.

    Sends an image with a text prompt to a vision-capable model and returns
    the response. Use this for image understanding, visual question answering,
    and general vision tasks.

    For dedicated PDF OCR, use mistral_ocr_client.ocr_pdf_document instead.

    Args:
        model: LiteLLM model identifier (format: "provider/model-name")
               - "gemini/gemini-2.5-flash"
               - "openai/gpt-4o"
               - "anthropic/claude-sonnet-4-20250514"
        prompt: Text prompt describing what to do with the image
        image_data: Base64-encoded image data
        max_tokens: Maximum tokens in response
        json_mode: Request structured JSON output
        image_format: Image MIME type suffix (png, jpeg, etc.)
        temperature: Sampling temperature (0.0-1.0)
        pipeline: Name of calling pipeline for cost attribution
        content_id: Associated content ID for cost attribution
        operation: Specific operation name

    Returns:
        Tuple of (response_text, LLMUsage with cost/token info)

    Example:
        >>> response, usage = await vision_completion(
        ...     model="openai/gpt-4o",
        ...     prompt="What objects are in this image?",
        ...     image_data=base64_image,
        ... )
        >>> print(response)
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

    kwargs: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": adjust_temperature_for_model(model, temperature),
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
        create_error_usage(
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


def vision_completion_sync(
    model: str,
    prompt: str,
    image_data: str,
    max_tokens: int = 4000,
    json_mode: bool = False,
    image_format: str = "png",
    temperature: float = 0.1,
    pipeline: Optional[str] = None,
    content_id: Optional[int] = None,
    operation: Optional[str] = None,
) -> tuple[str, LLMUsage]:
    """
    Synchronous vision completion using LiteLLM.

    Args:
        model: LiteLLM model identifier
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

    kwargs: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": adjust_temperature_for_model(model, temperature),
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
        create_error_usage(
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
    pipeline: Optional[str] = None,
    content_id: Optional[int] = None,
    operation: Optional[str] = None,
) -> tuple[str, LLMUsage]:
    """
    Vision completion with multiple images.

    Useful for comparing documents, processing multi-page content,
    or analyzing multiple images in a single request.

    Args:
        model: LiteLLM model identifier
        prompt: Text prompt for the vision model
        images: List of base64-encoded images
        max_tokens: Maximum tokens in response
        json_mode: Request JSON output
        image_format: Image MIME type
        temperature: Sampling temperature
        pipeline: Name of calling pipeline for cost attribution
        content_id: Associated content ID for cost attribution
        operation: Specific operation name

    Returns:
        Tuple of (response_text, LLMUsage with cost/token info)

    Example:
        >>> response, usage = await vision_completion_multi_image(
        ...     model="openai/gpt-4o",
        ...     prompt="Compare these two images",
        ...     images=[image1_base64, image2_base64],
        ... )
    """
    content: list[dict[str, Any]] = [{"type": "text", "text": prompt}]

    for img_data in images:
        content.append(
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/{image_format};base64,{img_data}"},
            }
        )

    messages = [{"role": "user", "content": content}]

    kwargs: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": adjust_temperature_for_model(model, temperature),
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
        create_error_usage(
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

