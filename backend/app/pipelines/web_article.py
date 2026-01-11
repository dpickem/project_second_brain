"""
Web Article Pipeline

Extracts content from web article URLs using Jina Reader API (primary) with
Trafilatura fallback. Handles generic article/blog post URLs.

Features:
- Article content extraction via Jina Reader (handles JS-rendered pages)
- Fallback to Trafilatura for static HTML pages
- Title extraction from HTML with LLM fallback for missing/poor titles
- Metadata extraction (author, date)
- Clean text/markdown output
- Rate limiting for Jina Reader API (configurable via settings.JINA_RATE_LIMIT_RPM)

Usage:
    from app.pipelines import WebArticlePipeline, PipelineInput, PipelineContentType

    pipeline = WebArticlePipeline()
    input_data = PipelineInput(
        url="https://example.com/article",
        content_type=PipelineContentType.ARTICLE,
    )
    content = await pipeline.process(input_data)
"""

import asyncio
import time
from datetime import datetime
from typing import Any, Optional
from urllib.parse import urlparse

import httpx
from trafilatura import bare_extraction

from app.config import settings
from app.enums.content import ContentType
from app.models.content import UnifiedContent
from app.models.llm_usage import LLMUsage
from app.pipelines.base import BasePipeline, PipelineContentType, PipelineInput
from app.enums.pipeline import PipelineName, PipelineOperation
from app.services.cost_tracking import CostTracker
from app.services.llm import get_llm_client, get_default_text_model, build_messages


# =============================================================================
# CONSTANTS
# =============================================================================

# Jina Reader API
JINA_READER_URL = "https://r.jina.ai/"
SECONDS_PER_MINUTE = 60.0

# Title extraction thresholds
MIN_TEXT_LENGTH_FOR_TITLE = 50  # Minimum chars needed to extract a title
TITLE_EXTRACTION_SAMPLE_LENGTH = 2000  # Chars to sample for title extraction
TITLE_EXTRACTION_MAX_TOKENS = 50  # Max tokens for LLM title response
TITLE_EXTRACTION_TEMPERATURE = 0.3  # LLM temperature for title extraction
TITLE_MIN_LENGTH = 3  # Minimum valid title length
TITLE_MAX_LENGTH = 200  # Maximum valid title length

# Browser-like headers to avoid 403 errors from bot detection
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "DNT": "1",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}


# =============================================================================
# RATE LIMITER
# =============================================================================


class JinaRateLimiter:
    """
    Token bucket rate limiter for Jina Reader API.

    Enforces requests per minute (RPM) limits globally across all
    WebArticlePipeline instances to avoid 429 errors.

    Rate limits configured via settings.JINA_RATE_LIMIT_RPM:
    - Free tier: 20 RPM (default)
    - Paid tiers: 500-5000 RPM

    See: https://jina.ai/api-dashboard/rate-limit
    """

    _instance: Optional["JinaRateLimiter"] = None
    _lock: asyncio.Lock = asyncio.Lock()

    def __init__(self, rpm: int) -> None:
        """
        Initialize rate limiter.

        Args:
            rpm: Requests per minute limit
        """
        self.rpm = rpm
        self.min_interval = SECONDS_PER_MINUTE / rpm
        self.last_request_time: float = 0.0
        self._async_lock = asyncio.Lock()

    @classmethod
    async def get_instance(cls) -> "JinaRateLimiter":
        """Get or create the singleton rate limiter instance."""
        async with cls._lock:
            if cls._instance is None:
                cls._instance = cls(rpm=settings.JINA_RATE_LIMIT_RPM)
            return cls._instance

    @classmethod
    def reset(cls) -> None:
        """Reset the singleton (for testing)."""
        cls._instance = None

    async def acquire(self) -> None:
        """
        Acquire permission to make a request, waiting if necessary.

        This method blocks until enough time has passed since the last
        request to stay within the rate limit.
        """
        async with self._async_lock:
            now = time.monotonic()
            elapsed = now - self.last_request_time

            if elapsed < self.min_interval:
                wait_time = self.min_interval - elapsed
                await asyncio.sleep(wait_time)

            self.last_request_time = time.monotonic()


# =============================================================================
# PIPELINE
# =============================================================================


class WebArticlePipeline(BasePipeline):
    """
    Generic web article extraction pipeline.

    Extracts article content, title, and metadata from any web URL
    using Jina Reader API (primary) with Trafilatura fallback.

    Routing:
    - Content type: PipelineContentType.ARTICLE
    - Input: Article URL (url field in PipelineInput)

    Note: For Raindrop.io bookmark sync with highlights, use RaindropSync instead.
    """

    SUPPORTED_CONTENT_TYPES = {PipelineContentType.ARTICLE}
    PIPELINE_NAME = PipelineName.WEB_ARTICLE

    def __init__(
        self,
        timeout: Optional[float] = None,
        text_model: Optional[str] = None,
        track_costs: bool = True,
    ) -> None:
        """
        Initialize web article pipeline.

        Args:
            timeout: HTTP request timeout in seconds. Defaults to
                    settings.ARTICLE_HTTP_TIMEOUT.
            text_model: LLM model for title extraction fallback. Defaults to
                       settings.TEXT_MODEL via get_default_text_model().
            track_costs: Whether to log LLM costs to database. Defaults to True.
        """
        super().__init__()
        self.timeout: float = (
            timeout if timeout is not None else settings.ARTICLE_HTTP_TIMEOUT
        )
        self.text_model: str = text_model or get_default_text_model()
        self.track_costs: bool = track_costs
        self._usage_records: list[LLMUsage] = []
        self._content_id: Optional[str] = None

    def supports(self, input_data: PipelineInput) -> bool:
        """
        Check if this pipeline can handle the input.

        Requires:
        - content_type == ARTICLE
        - url is set

        Args:
            input_data: PipelineInput to check for compatibility

        Returns:
            True if this pipeline can process the input, False otherwise
        """
        if not isinstance(input_data, PipelineInput):
            return False

        if input_data.content_type != PipelineContentType.ARTICLE:
            return False

        return input_data.url is not None

    async def process(self, input_data: PipelineInput) -> UnifiedContent:
        """
        Extract article content from a URL.

        Args:
            input_data: PipelineInput with article URL in the url field

        Returns:
            UnifiedContent with extracted article content and metadata

        Raises:
            ValueError: If input_data.url is None
        """
        if input_data.url is None:
            raise ValueError("PipelineInput.url is required for article processing")

        # Reset usage records for this processing run
        self._usage_records = []
        self._content_id = input_data.content_id

        url = input_data.url
        extraction = await self._extract_article(url)

        # Extract metadata
        author = extraction.get("author")
        date_str = extraction.get("date")
        text = extraction.get("text") or ""

        # Use LLM for title extraction
        title = await self._extract_title_with_llm(text, url)

        # Parse date if available
        created_at = datetime.now()
        if date_str:
            try:
                created_at = datetime.fromisoformat(date_str)
            except (ValueError, TypeError):
                pass

        # Build authors list
        authors: list[str] = []
        if author:
            authors = [author]

        # Log accumulated LLM costs to database
        if self.track_costs and self._usage_records:
            total_cost = sum(u.cost_usd or 0 for u in self._usage_records)
            self.logger.info(
                f"Article extraction complete - Total LLM cost: ${total_cost:.4f} "
                f"({len(self._usage_records)} API calls)"
            )
            await CostTracker.log_usages_batch(self._usage_records)

        return UnifiedContent(
            source_type=ContentType.ARTICLE,
            source_url=url,
            title=title,
            authors=authors,
            created_at=created_at,
            full_text=text or f"[Content could not be extracted from {url}]",
            metadata=self._build_metadata(extraction, url),
        )

    async def _extract_title_with_llm(self, text: str, url: str) -> str:
        """
        Use LLM to extract an appropriate title from article text.

        Args:
            text: Article body text
            url: Source URL (used as fallback if LLM fails)

        Returns:
            Extracted title, or URL hostname as fallback
        """
        if not text or len(text) < MIN_TEXT_LENGTH_FOR_TITLE:
            # Not enough text to extract a title
            return urlparse(url).netloc or "Untitled"

        # Use first N chars for title extraction (usually intro has key info)
        text_sample = (
            text[:TITLE_EXTRACTION_SAMPLE_LENGTH]
            if len(text) > TITLE_EXTRACTION_SAMPLE_LENGTH
            else text
        )

        prompt = f"""Extract a concise, descriptive title for this article. 
The title should:
- Be 5-15 words
- Capture the main topic or thesis
- Be suitable for a note-taking system

Article text:
{text_sample}

Respond with ONLY the title, nothing else."""

        try:
            client = get_llm_client()
            messages = build_messages(
                prompt,
                "You are a helpful assistant that extracts article titles. Respond with only the title, no quotes or explanation.",
            )
            response, usage = await client.complete(
                operation=PipelineOperation.TITLE_EXTRACTION,
                messages=messages,
                model=self.text_model,
                max_tokens=TITLE_EXTRACTION_MAX_TOKENS,
                temperature=TITLE_EXTRACTION_TEMPERATURE,
                pipeline=self.PIPELINE_NAME,
                content_id=self._content_id,
            )

            # Track LLM usage for cost reporting
            if usage:
                self._usage_records.append(usage)

            if response:
                # Clean up the response
                title = response.strip().strip('"').strip("'").strip()
                if TITLE_MIN_LENGTH <= len(title) <= TITLE_MAX_LENGTH:
                    self.logger.info(f"LLM extracted title: '{title}'")
                    return title

        except Exception as e:
            self.logger.warning(f"LLM title extraction failed: {e}")

        # Fallback to URL hostname
        return urlparse(url).netloc or "Untitled"

    async def _extract_article(self, url: str) -> dict[str, Any]:
        """
        Extract article content and metadata from URL.

        Tries Jina Reader API first (more reliable, handles JS-rendered pages),
        then falls back to Trafilatura for static HTML if Jina fails.

        Args:
            url: URL of the article to fetch and extract

        Returns:
            Dict with extracted fields: title, author, date, text, etc.
        """
        # Try Jina Reader first (more reliable, handles JS-rendered pages)
        result = await self._extract_with_jina(url)
        if result.get("text"):
            return result

        # Fallback to Trafilatura for static HTML pages
        self.logger.debug(f"Jina Reader failed, trying Trafilatura for {url}")
        return await self._extract_with_trafilatura(url)

    async def _extract_with_trafilatura(self, url: str) -> dict[str, Any]:
        """Extract using trafilatura (works for static HTML pages)."""
        try:
            async with httpx.AsyncClient(
                headers=DEFAULT_HEADERS,
                timeout=self.timeout,
                follow_redirects=True,
            ) as client:
                response = await client.get(url)
                response.raise_for_status()
                downloaded = response.text

            if downloaded:
                loop = asyncio.get_event_loop()
                extraction = await loop.run_in_executor(
                    None,
                    lambda: bare_extraction(
                        downloaded,
                        include_comments=False,
                        include_tables=True,
                        include_links=False,
                    ),
                )
                if extraction is None:
                    return {}
                if isinstance(extraction, dict):
                    result = extraction
                else:
                    result = self._document_to_dict(extraction)
                # Add source and format metadata
                result["source"] = "trafilatura"
                result["format"] = "text"
                return result
        except httpx.HTTPStatusError as e:
            self.logger.debug(f"HTTP {e.response.status_code} for {url}")
        except Exception as e:
            self.logger.debug(f"Trafilatura extraction failed for {url}: {e}")

        return {}

    async def _extract_with_jina(self, url: str) -> dict[str, Any]:
        """
        Extract using Jina Reader API (handles JS-rendered pages).

        Jina Reader (r.jina.ai) is a free service that renders JavaScript
        and returns clean markdown content.

        Rate limiting is enforced globally via settings.JINA_RATE_LIMIT_RPM.
        See: https://jina.ai/api-dashboard/rate-limit
        """
        try:
            # Acquire rate limit token before making request
            rate_limiter = await JinaRateLimiter.get_instance()
            await rate_limiter.acquire()

            jina_url = f"{JINA_READER_URL}{url}"
            async with httpx.AsyncClient(
                timeout=self.timeout,
                follow_redirects=True,
            ) as client:
                response = await client.get(jina_url)
                response.raise_for_status()
                content = response.text

            if content:
                # Jina returns markdown with title on first line
                lines = content.strip().split("\n")
                title = ""
                markdown = content

                # Extract title from first markdown heading
                if lines and lines[0].startswith("# "):
                    title = lines[0][2:].strip()
                    markdown = "\n".join(lines[1:]).strip()

                return {
                    "text": markdown,  # For compatibility
                    "markdown": markdown,
                    "title": title,
                    "source": "jina_reader",
                    "format": "markdown",
                }
        except httpx.HTTPStatusError as e:
            self.logger.warning(f"Jina Reader HTTP {e.response.status_code} for {url}")
        except Exception as e:
            self.logger.warning(f"Jina Reader failed for {url}: {e}")

        return {}

    def _document_to_dict(self, doc: Any) -> dict[str, Any]:
        """
        Convert a trafilatura Document object to a dictionary.

        Trafilatura >= 1.6 returns Document objects instead of dicts.

        Args:
            doc: Trafilatura Document object

        Returns:
            Dict with document fields
        """
        result: dict[str, Any] = {}

        # Core content fields
        for field in ["title", "author", "date", "text", "comments"]:
            value = getattr(doc, field, None)
            if value:
                result[field] = value

        # Metadata fields
        for field in [
            "hostname",
            "sitename",
            "description",
            "categories",
            "tags",
            "license",
            "language",
            "url",
            "source",
            "source_hostname",
            "excerpt",
            "id",
            "fingerprint",
            "raw_text",
        ]:
            value = getattr(doc, field, None)
            if value:
                result[field] = value

        return result

    async def extract_text_only(self, url: str) -> str:
        """
        Extract just the main text content from a URL.

        Convenience method for when only the text is needed.

        Args:
            url: URL of the article to fetch

        Returns:
            Extracted article text, or empty string if extraction fails
        """
        extraction = await self._extract_article(url)
        return extraction.get("text") or ""

    def _build_metadata(self, extraction: dict[str, Any], url: str) -> dict[str, Any]:
        """
        Build metadata dict from extraction results.

        Args:
            extraction: Trafilatura extraction result dict
            url: Original URL

        Returns:
            Metadata dict with available fields
        """
        metadata: dict[str, Any] = {
            "source_url": url,
        }

        # Add optional fields if present
        optional_fields = [
            "hostname",
            "sitename",
            "description",
            "categories",
            "tags",
            "license",
            "language",
            "format",
            "source",
        ]
        for field in optional_fields:
            if extraction.get(field):
                metadata[field] = extraction[field]

        # Include markdown content explicitly if available
        if extraction.get("markdown"):
            metadata["markdown"] = extraction["markdown"]

        return metadata
