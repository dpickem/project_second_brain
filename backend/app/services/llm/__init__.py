"""
LLM Service Module

Provides a unified interface to multiple LLM providers via LiteLLM.
Supports operation-based model selection and cost tracking.

Key Components:
- client.py: LLMClient class with async/sync completion and embedding methods

All methods return (response, LLMUsage) tuples for consistent cost tracking.

Usage:
    from app.enums import PipelineName, PipelineOperation
    from app.services.llm import get_llm_client, LLMUsage

    client = get_llm_client()
    response, usage = await client.complete(
        operation=PipelineOperation.SUMMARIZATION,
        messages=[{"role": "user", "content": "Summarize this..."}],
        pipeline=PipelineName.WEB_ARTICLE,
        content_id="uuid",
    )
    print(f"Cost: ${usage.cost_usd:.4f}, Tokens: {usage.total_tokens}")
"""

from app.pipelines.utils.cost_types import LLMUsage
from app.services.llm.client import (
    LLMClient,
    get_llm_client,
    reset_llm_client,
    get_default_text_model,
    build_messages,
)

__all__ = [
    "LLMClient",
    "LLMUsage",
    "get_llm_client",
    "reset_llm_client",
    "get_default_text_model",
    "build_messages",
]
