"""
Web Article Pipeline

Extracts content from web article URLs using Trafilatura.
Handles generic article/blog post URLs without requiring any external service integration.

Features:
- Article content extraction via Trafilatura
- Title extraction from HTML
- Metadata extraction (author, date)
- Clean text output

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

from trafilatura import bare_extraction, fetch_url

from app.models.content import ContentType, UnifiedContent
from app.pipelines.base import BasePipeline, PipelineContentType, PipelineInput


class WebArticlePipeline(BasePipeline):
    """
    Generic web article extraction pipeline.

    Extracts article content, title, and metadata from any web URL
    using Trafilatura for content extraction.

    Routing:
    - Content type: PipelineContentType.ARTICLE
    - Input: Article URL (url field in PipelineInput)

    Note: For Raindrop.io bookmark sync with highlights, use RaindropSync instead.
    """

    SUPPORTED_CONTENT_TYPES = {PipelineContentType.ARTICLE}

    def __init__(self, timeout: float = 30.0) -> None:
        """
        Initialize web article pipeline.

        Args:
            timeout: HTTP request timeout in seconds (default: 30.0)
        """
        super().__init__()
        self.timeout: float = timeout

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
        title = extraction.get("title") or self._title_from_url(url)
        author = extraction.get("author")
        date_str = extraction.get("date")
        text = extraction.get("text") or ""

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

    async def _extract_article(self, url: str) -> dict[str, Any]:
        """
        Extract article content and metadata from URL using Trafilatura.

        Args:
            url: URL of the article to fetch and extract

        Returns:
            Dict with extracted fields: title, author, date, text, etc.
        """
        try:
            # Trafilatura's fetch_url is sync, run in executor
            loop = asyncio.get_event_loop()
            downloaded = await loop.run_in_executor(None, fetch_url, url)

            if downloaded:
                # Use bare_extraction for full metadata
                extraction = await loop.run_in_executor(
                    None,
                    lambda: bare_extraction(
                        downloaded,
                        include_comments=False,
                        include_tables=True,
                        include_links=False,
                    ),
                )
                return extraction or {}
        except Exception as e:
            self.logger.warning(f"Failed to extract article from {url}: {e}")

        return {}

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

    def _title_from_url(self, url: str) -> str:
        """
        Generate a fallback title from URL path.

        Args:
            url: URL to extract title from

        Returns:
            Title derived from URL path, or "Untitled" if extraction fails
        """
        try:
            parsed = urlparse(url)
            path_parts = [p for p in parsed.path.split("/") if p]
            if path_parts:
                # Use last path segment, replace hyphens/underscores with spaces
                title = path_parts[-1].replace("-", " ").replace("_", " ")
                # Remove common extensions
                for ext in [".html", ".htm", ".php", ".aspx"]:
                    title = title.replace(ext, "")
                return title.title()
        except Exception:
            pass
        return "Untitled"

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
        ]
        for field in optional_fields:
            if extraction.get(field):
                metadata[field] = extraction[field]

        return metadata
