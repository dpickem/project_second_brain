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
from datetime import datetime
from typing import Any, Optional
from urllib.parse import urlparse

import httpx
from trafilatura import bare_extraction

from app.enums.content import ContentType
from app.models.content import UnifiedContent
from app.pipelines.base import BasePipeline, PipelineContentType, PipelineInput
from app.enums.pipeline import PipelineName, PipelineOperation
from app.services.llm import get_llm_client, get_default_text_model, build_messages

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

# Jina Reader API for JS-rendered pages (free, no API key required)
JINA_READER_URL = "https://r.jina.ai/"


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
        timeout: float = 30.0,
        text_model: Optional[str] = None,
    ) -> None:
        """
        Initialize web article pipeline.

        Args:
            timeout: HTTP request timeout in seconds (default: 30.0)
            text_model: LLM model for title extraction fallback. Defaults to
                       settings.TEXT_MODEL via get_default_text_model().
        """
        super().__init__()
        self.timeout: float = timeout
        self.text_model: str = text_model or get_default_text_model()

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
        if not text or len(text) < 50:
            # Not enough text to extract a title
            return urlparse(url).netloc or "Untitled"

        # Use first ~2000 chars for title extraction (usually intro has key info)
        text_sample = text[:2000] if len(text) > 2000 else text

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
                max_tokens=50,
                temperature=0.3,
                pipeline=self.PIPELINE_NAME,
            )

            if response:
                # Clean up the response
                title = response.strip().strip('"').strip("'").strip()
                if 3 <= len(title) <= 200:
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
        """
        try:
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
