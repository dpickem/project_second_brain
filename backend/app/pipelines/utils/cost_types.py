"""
LLM Usage and Cost Tracking Types

Defines the LLMUsage dataclass and helper functions for extracting
cost/token information from LiteLLM responses.

This module is separate from vlm_client.py and mistral_ocr_client.py to maintain
clear separation between the completion wrapper functions and the cost tracking
data structures.

Usage:
    from app.pipelines.utils.cost_types import LLMUsage, extract_usage_from_response

    usage = extract_usage_from_response(
        response=litellm_response,
        model="mistral/mistral-ocr-latest",
        request_type="vision",
        latency_ms=1234,
        pipeline="book_ocr",
        operation="page_extraction"
    )
"""

import uuid
from dataclasses import dataclass, field, asdict
from typing import Optional

import litellm


@dataclass
class LLMUsage:
    """
    Structured LLM usage data returned from completion calls.

    Contains all information needed for cost tracking and analysis.
    Can be passed directly to the CostTracker service for database persistence.

    Attributes:
        request_id: Unique identifier for this request (auto-generated UUID)
        model: Full model identifier (e.g., "mistral/mistral-ocr-latest")
        provider: Extracted provider name (e.g., "mistral", "openai")
        request_type: Type of request ("vision", "text", "embedding")
        prompt_tokens: Number of input tokens
        completion_tokens: Number of output tokens
        total_tokens: Total tokens used
        cost_usd: Total cost in USD
        input_cost_usd: Cost for input tokens
        output_cost_usd: Cost for output tokens
        pipeline: Name of the calling pipeline (e.g., "book_ocr", "pdf_processor")
        content_id: Associated content ID for cost attribution
        operation: Specific operation name (e.g., "page_extraction", "handwriting_detection")
        latency_ms: Request latency in milliseconds
        success: Whether the request succeeded
        error_message: Error message if request failed
    """

    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    model: str = ""
    provider: str = ""
    request_type: str = ""  # "vision", "text", "embedding"

    # Token usage
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    total_tokens: Optional[int] = None

    # Cost in USD
    cost_usd: Optional[float] = None
    input_cost_usd: Optional[float] = None
    output_cost_usd: Optional[float] = None

    # Context for attribution
    pipeline: Optional[str] = None
    content_id: Optional[int] = None
    operation: Optional[str] = None

    # Performance
    latency_ms: Optional[int] = None
    success: bool = True
    error_message: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for database storage or serialization.

        This is a convenience wrapper around dataclasses.asdict().
        """
        return asdict(self)

    @property
    def total_cost(self) -> float:
        """Return total cost, defaulting to 0 if not available."""
        return self.cost_usd or 0.0

    def __str__(self) -> str:
        """Human-readable string representation."""
        cost_str = f"${self.cost_usd:.4f}" if self.cost_usd else "N/A"
        tokens_str = str(self.total_tokens) if self.total_tokens else "N/A"
        return (
            f"LLMUsage({self.model}, {self.request_type}, "
            f"cost={cost_str}, tokens={tokens_str})"
        )


def extract_provider(model: str) -> str:
    """
    Extract provider name from model identifier.

    Args:
        model: Full model identifier (e.g., "mistral/mistral-ocr-latest")

    Returns:
        Provider name (e.g., "mistral") or "unknown" if not parseable
    """
    if "/" in model:
        return model.split("/")[0]
    return "unknown"


def extract_usage_from_response(
    response,
    model: str,
    request_type: str,
    latency_ms: int,
    pipeline: Optional[str] = None,
    content_id: Optional[int] = None,
    operation: Optional[str] = None,
) -> LLMUsage:
    """
    Extract usage and cost information from a LiteLLM response.

    This function parses the response object returned by litellm.completion()
    or litellm.acompletion() and extracts all available cost and token
    information.

    Args:
        response: LiteLLM response object
        model: Model identifier used for the request
        request_type: Type of request ("vision", "text", "embedding")
        latency_ms: Measured latency in milliseconds
        pipeline: Optional pipeline name for attribution
        content_id: Optional content ID for attribution
        operation: Optional operation name for attribution

    Returns:
        LLMUsage dataclass populated with extracted information
    """
    usage = LLMUsage(
        model=model,
        provider=extract_provider(model),
        request_type=request_type,
        latency_ms=latency_ms,
        pipeline=pipeline,
        content_id=content_id,
        operation=operation,
    )

    # Extract token usage from response.usage
    if hasattr(response, "usage") and response.usage:
        usage.prompt_tokens = getattr(response.usage, "prompt_tokens", None)
        usage.completion_tokens = getattr(response.usage, "completion_tokens", None)
        usage.total_tokens = getattr(response.usage, "total_tokens", None)

    # Extract cost from LiteLLM's hidden params
    if hasattr(response, "_hidden_params") and response._hidden_params:
        hidden = response._hidden_params

        # Total cost
        usage.cost_usd = hidden.get("response_cost")

        # Detailed cost breakdown (if available)
        if "additional_args" in hidden:
            additional = hidden["additional_args"]
            usage.input_cost_usd = additional.get("input_cost")
            usage.output_cost_usd = additional.get("output_cost")

    # Fallback: calculate cost using litellm.completion_cost if not in response
    if usage.cost_usd is None and usage.total_tokens:
        try:
            usage.cost_usd = litellm.completion_cost(
                model=model,
                prompt="",  # We don't have the original prompt here
                completion=response.choices[0].message.content or "",
            )
        except Exception:
            pass  # Cost calculation not available for this model

    return usage


def create_error_usage(
    model: str,
    request_type: str,
    latency_ms: int,
    error_message: str,
    pipeline: Optional[str] = None,
    content_id: Optional[int] = None,
    operation: Optional[str] = None,
) -> LLMUsage:
    """
    Create an LLMUsage record for a failed request.

    Args:
        model: Model identifier
        request_type: Type of request
        latency_ms: Time spent before failure
        error_message: Error description
        pipeline: Optional pipeline name
        content_id: Optional content ID
        operation: Optional operation name

    Returns:
        LLMUsage with success=False and error details
    """
    return LLMUsage(
        model=model,
        provider=extract_provider(model),
        request_type=request_type,
        latency_ms=latency_ms,
        success=False,
        error_message=error_message,
        pipeline=pipeline,
        content_id=content_id,
        operation=operation,
    )
