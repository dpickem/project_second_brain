"""
Raindrop.io Sync Pipeline

Syncs bookmarked web articles with highlights and tags from Raindrop.io.
This pipeline is specifically for Raindrop.io API integration.

For generic web article extraction, use WebArticlePipeline instead.

Features:
- Collection sync with pagination
- Highlight extraction from Raindrop.io
- Full article content fetching (via WebArticlePipeline)
- LLM-powered title extraction for poor Raindrop titles
- Rate limit handling
- Concurrent processing

Usage:
    from app.pipelines import RaindropSync

    sync = RaindropSync(access_token="...")
    items = await sync.sync_collection(since=datetime.now() - timedelta(days=1))
"""

import asyncio
from datetime import datetime
from typing import Any, Optional
from urllib.parse import urlparse

import httpx

from app.config import settings
from app.enums.pipeline import PipelineName, PipelineOperation
from app.models.content import (
    Annotation,
    AnnotationType,
    ContentType,
    UnifiedContent,
)
from app.models.llm_usage import LLMUsage
from app.pipelines.base import BasePipeline, PipelineInput, PipelineContentType
from app.pipelines.web_article import WebArticlePipeline
from app.services.cost_tracking import CostTracker
from app.services.llm import get_llm_client, get_default_text_model, build_messages


# =============================================================================
# CONSTANTS
# =============================================================================

# Pagination defaults
INITIAL_PAGE_NUMBER = 0
DEFAULT_COUNT = 0


class RaindropSync(BasePipeline):
    """
    Raindrop.io bookmark sync pipeline.

    Syncs bookmarks with their highlights from Raindrop.io and fetches
    full article content using WebArticlePipeline.

    This pipeline is NOT registered with PipelineRegistry by default because
    it requires an access token and is typically used for batch sync operations
    via sync_collection(), not single-item processing.

    For generic article URL processing, use WebArticlePipeline instead.

    Usage:
        sync = RaindropSync(access_token="...")
        items = await sync.sync_collection(since=datetime.now() - timedelta(days=1))
    """

    # API Configuration
    BASE_URL = "https://api.raindrop.io/rest/v1"
    SUPPORTED_CONTENT_TYPES: set[PipelineContentType] = set()  # Not used via registry

    # Default values
    DEFAULT_TIMEOUT_SECONDS: float = 30.0
    DEFAULT_MAX_CONCURRENT: int = 5
    DEFAULT_PAGE_SIZE: int = 50

    # Special collection IDs (from Raindrop.io API)
    COLLECTION_ALL: int = 0  # All raindrops
    COLLECTION_UNSORTED: int = -1  # Unsorted items
    COLLECTION_TRASH: int = -99  # Trash

    # Rate limiting
    RATE_LIMIT_STATUS_CODE: int = 429
    RATE_LIMIT_WAIT_SECONDS: int = 60

    def __init__(
        self,
        access_token: str,
        timeout: Optional[float] = None,
        max_concurrent: Optional[int] = None,
        track_costs: bool = True,
    ) -> None:
        """
        Initialize Raindrop sync.

        Args:
            access_token: Raindrop.io API access token
            timeout: HTTP request timeout in seconds (default: DEFAULT_TIMEOUT_SECONDS)
            max_concurrent: Max concurrent article fetches (default: DEFAULT_MAX_CONCURRENT)
            track_costs: Whether to log LLM costs to database (default: True)
        """
        super().__init__()
        self.access_token: str = access_token
        self.timeout: float = (
            timeout if timeout is not None else self.DEFAULT_TIMEOUT_SECONDS
        )
        self.max_concurrent: int = (
            max_concurrent
            if max_concurrent is not None
            else self.DEFAULT_MAX_CONCURRENT
        )
        self.track_costs: bool = track_costs
        self._usage_records: list[LLMUsage] = []
        self.client: httpx.AsyncClient = httpx.AsyncClient(
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=self.timeout,
        )
        self._semaphore: asyncio.Semaphore = asyncio.Semaphore(self.max_concurrent)

    def supports(self, input_data: PipelineInput) -> bool:
        """
        Check if this pipeline can handle the input.

        Always returns False because RaindropSync is not meant to be used
        via PipelineRegistry. Use sync_collection() directly instead.

        For generic article URL processing, use WebArticlePipeline.

        Args:
            input_data: PipelineInput to check for compatibility

        Returns:
            Always False - use sync_collection() directly
        """
        # RaindropSync requires API token and is used for batch sync only
        return False

    async def process(self, input_data: PipelineInput) -> UnifiedContent:
        """
        Not implemented - use sync_collection() instead.

        RaindropSync is designed for batch sync operations, not single-item
        processing via PipelineRegistry.

        For generic article URL processing, use WebArticlePipeline.

        Args:
            input_data: PipelineInput (not used)

        Raises:
            NotImplementedError: Always - use sync_collection() instead
        """
        raise NotImplementedError(
            "RaindropSync does not support single-item processing via registry. "
            "Use sync_collection() for batch sync, or WebArticlePipeline for "
            "generic article URL processing."
        )

    async def sync_collection(
        self,
        collection_id: Optional[int] = None,
        since: Optional[datetime] = None,
        limit: Optional[int] = None,
    ) -> list[UnifiedContent]:
        """
        Sync raindrops from a collection.

        Uses Raindrop.io API endpoint:
        - GET /raindrops/{collectionId} - get raindrops in collection

        Special collection IDs (use class constants):
        - COLLECTION_ALL (0): All raindrops
        - COLLECTION_UNSORTED (-1): Unsorted items
        - COLLECTION_TRASH (-99): Trash

        See: https://developer.raindrop.io/v1/raindrops

        Args:
            collection_id: Raindrop collection ID (default: COLLECTION_ALL)
            since: Only sync items created after this date (default: None, sync all)
            limit: Maximum number of items to sync (default: None, no limit)

        Returns:
            List of UnifiedContent objects with article content and highlights
        """
        if collection_id is None:
            collection_id = self.COLLECTION_ALL

        # Reset usage records for this sync run
        self._usage_records = []

        params: dict[str, Any] = {"perpage": self.DEFAULT_PAGE_SIZE, "page": INITIAL_PAGE_NUMBER}

        if since:
            params["search"] = f"created:>{since.strftime('%Y-%m-%d')}"

        all_items: list[UnifiedContent] = []

        while True:
            try:
                response = await self.client.get(
                    f"{self.BASE_URL}/raindrops/{collection_id}",
                    params=params,
                )
                response.raise_for_status()
                data = response.json()
            except httpx.HTTPStatusError as e:
                if e.response.status_code == self.RATE_LIMIT_STATUS_CODE:
                    # Rate limited - wait and retry
                    self.logger.warning(
                        f"Rate limited, waiting {self.RATE_LIMIT_WAIT_SECONDS} seconds"
                    )
                    await asyncio.sleep(self.RATE_LIMIT_WAIT_SECONDS)
                    continue
                raise

            # Check API result
            if not data.get("result", True):  # Default True for backwards compat
                self.logger.warning("API returned result=false for raindrops")
                break

            if not data.get("items"):
                break

            # Process items concurrently with semaphore
            tasks = [self._process_with_semaphore(item) for item in data["items"]]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for result in results:
                if isinstance(result, UnifiedContent):
                    all_items.append(result)
                elif isinstance(result, Exception):
                    self.logger.error(f"Failed to process raindrop: {result}")

            # Check if we have enough items
            if limit and len(all_items) >= limit:
                all_items = all_items[:limit]
                break

            params["page"] += 1
            total_count = data.get("count", DEFAULT_COUNT)

            if params["page"] * self.DEFAULT_PAGE_SIZE >= total_count:
                break

        # Log accumulated LLM costs to database
        if self.track_costs and self._usage_records:
            total_cost = sum(u.cost_usd or 0 for u in self._usage_records)
            self.logger.info(
                f"Raindrop sync complete - Total LLM cost: ${total_cost:.4f} "
                f"({len(self._usage_records)} API calls)"
            )
            await CostTracker.log_usages_batch(self._usage_records)

        self.logger.info(f"Synced {len(all_items)} items from Raindrop")
        return all_items

    async def _process_with_semaphore(self, item: dict[str, Any]) -> UnifiedContent:
        """
        Process a raindrop with concurrency control.

        Args:
            item: Raindrop item dict from API response

        Returns:
            UnifiedContent with processed article
        """
        async with self._semaphore:
            return await self._process_raindrop(item)

    async def _process_raindrop(self, item: dict[str, Any]) -> UnifiedContent:
        """
        Convert a raindrop API item to UnifiedContent.

        Args:
            item: Raindrop item dict from API with link, title, tags, etc.

        Returns:
            UnifiedContent with article content, highlights as annotations, and metadata
        """
        url = item["link"]
        raindrop_title = item.get("title", "")
        
        # Fetch full article content
        article_content = await self._fetch_article_content(url)

        # Determine best title: use LLM if Raindrop title is poor quality
        title = await self._get_best_title(raindrop_title, article_content, url)

        # Get highlights
        highlights = await self._get_highlights(item["_id"])

        # Create annotations from highlights
        annotations: list[Annotation] = [
            Annotation(
                type=AnnotationType.DIGITAL_HIGHLIGHT,
                content=h.get("text", ""),
                context=h.get("note"),
            )
            for h in highlights
            if h.get("text")
        ]

        # Parse creation date
        created_at = datetime.now()
        if item.get("created"):
            try:
                created_at = datetime.fromisoformat(
                    item["created"].replace("Z", "+00:00")
                )
            except (ValueError, TypeError):
                pass

        # Get tags
        tags: list[str] = item.get("tags", [])

        return UnifiedContent(
            source_type=ContentType.ARTICLE,
            source_url=url,
            title=title,
            authors=[item.get("creator", "Unknown")],
            created_at=created_at,
            full_text=article_content
            or f"[Content could not be fetched from {url}]",
            annotations=annotations,
            tags=tags,
            metadata={
                "raindrop_id": item["_id"],
                "collection_id": item.get("collection", {}).get("$id"),
                "cover": item.get("cover"),
                "excerpt": item.get("excerpt"),
            },
        )

    async def _get_best_title(
        self, raindrop_title: str, article_content: str, url: str
    ) -> str:
        """
        Generate the best title for an article using LLM.

        Always uses the LLM to generate a clean, descriptive title based on
        the article content. The existing Raindrop title is provided as context
        to help the LLM understand what the article is about.

        Args:
            raindrop_title: Title from Raindrop API (used as context hint)
            article_content: Fetched article text content
            url: Source URL (fallback if LLM fails)

        Returns:
            LLM-generated title, or fallback to raindrop_title/URL hostname
        """
        # Need content to generate a good title
        if not article_content:
            return raindrop_title or urlparse(url).netloc or "Untitled"

        try:
            title = await self._generate_title_with_llm(
                article_content, raindrop_title, url
            )
            if title:
                if raindrop_title and title != raindrop_title:
                    self.logger.info(
                        f"Generated title: '{raindrop_title}' -> '{title}'"
                    )
                return title
        except Exception as e:
            self.logger.warning(f"LLM title generation failed: {e}")

        # Fallback to original Raindrop title or URL hostname
        return raindrop_title or urlparse(url).netloc or "Untitled"

    async def _generate_title_with_llm(
        self, article_content: str, existing_title: str, url: str
    ) -> Optional[str]:
        """
        Use LLM to generate a clean, descriptive title for an article.

        Args:
            article_content: Article body text
            existing_title: Current title from Raindrop (may be URL or poor quality)
            url: Source URL for context

        Returns:
            Generated title string, or None if generation fails
        """
        # Use first N chars for title generation
        text_sample = (
            article_content[:settings.RAINDROP_TITLE_SAMPLE_LENGTH]
            if len(article_content) > settings.RAINDROP_TITLE_SAMPLE_LENGTH
            else article_content
        )

        # Build prompt with existing title as context
        context_hint = ""
        if existing_title and not existing_title.startswith(("http://", "https://", "www.")):
            context_hint = f"\nThe current title is: \"{existing_title}\" (this may or may not be accurate)"

        prompt = f"""Generate a concise, descriptive title for this article.
The title should:
- Be 5-15 words
- Capture the main topic or thesis
- Be suitable for a note-taking system
- NOT be a URL or domain name
{context_hint}

Article text:
{text_sample}

Respond with ONLY the title, nothing else."""

        client = get_llm_client()
        messages = build_messages(
            prompt,
            "You are a helpful assistant that generates article titles. Respond with only the title, no quotes or explanation.",
        )

        response, usage = await client.complete(
            operation=PipelineOperation.TITLE_EXTRACTION,
            messages=messages,
            model=get_default_text_model(),
            max_tokens=settings.RAINDROP_TITLE_MAX_TOKENS,
            temperature=settings.RAINDROP_TITLE_TEMPERATURE,
            pipeline=PipelineName.RAINDROP_SYNC,
        )

        # Track LLM usage for cost reporting
        if usage:
            self._usage_records.append(usage)

        if response:
            # Clean up the response
            title = response.strip().strip('"').strip("'").strip()
            if settings.RAINDROP_TITLE_MIN_LENGTH <= len(title) <= settings.RAINDROP_TITLE_MAX_LENGTH:
                return title

        return None

    async def _fetch_article_content(self, url: str) -> str:
        """
        Extract main content from URL using WebArticlePipeline.

        Args:
            url: URL of the article to fetch and extract content from

        Returns:
            Extracted article text, or empty string if extraction fails
        """
        try:
            pipeline = WebArticlePipeline()
            return await pipeline.extract_text_only(url)
        except Exception as e:
            self.logger.warning(f"Failed to fetch article from {url}: {e}")
            return ""

    async def _get_highlights(self, raindrop_id: int) -> list[dict[str, Any]]:
        """
        Get highlights for a specific raindrop.

        Uses Raindrop.io API endpoint:
        - GET /raindrop/{id} - get single raindrop with highlights

        See: https://developer.raindrop.io/v1/raindrops

        Args:
            raindrop_id: Raindrop item ID to fetch highlights for

        Returns:
            List of highlight dicts with 'text' and optional 'note' fields
        """
        try:
            response = await self.client.get(f"{self.BASE_URL}/raindrop/{raindrop_id}")
            response.raise_for_status()
            data = response.json()

            if not data.get("result"):
                self.logger.warning(
                    f"API returned result=false for raindrop {raindrop_id}"
                )
                return []

            return data.get("item", {}).get("highlights", [])
        except Exception as e:
            self.logger.warning(f"Failed to get highlights for {raindrop_id}: {e}")
            return []

    async def get_collections(
        self, include_nested: bool = True
    ) -> list[dict[str, Any]]:
        """
        Get list of user's collections with full hierarchy paths.

        Uses Raindrop.io API endpoints:
        - GET /collections - root collections
        - GET /collections/childrens - nested collections

        See: https://developer.raindrop.io/v1/collections/methods

        Args:
            include_nested: If True, also fetch nested/child collections (default: True)

        Returns:
            List of collection dicts with _id, title, count, parent, full_path, etc.
            The full_path field contains the complete hierarchy (e.g., "Parent / Child").
        """
        all_collections: list[dict[str, Any]] = []

        try:
            # Get root collections
            response = await self.client.get(f"{self.BASE_URL}/collections")
            response.raise_for_status()
            data = response.json()

            if data.get("result"):
                all_collections.extend(data.get("items", []))
            else:
                self.logger.warning("API returned result=false for root collections")

            # Get nested collections if requested
            if include_nested:
                response = await self.client.get(
                    f"{self.BASE_URL}/collections/childrens"
                )
                response.raise_for_status()
                data = response.json()

                if data.get("result"):
                    all_collections.extend(data.get("items", []))

        except Exception as e:
            self.logger.error(f"Failed to get collections: {e}")

        # Add full_path to each collection
        self._add_collection_paths(all_collections)

        return all_collections

    def _add_collection_paths(self, collections: list[dict[str, Any]]) -> None:
        """
        Add full_path field to each collection showing its hierarchy.

        Modifies collections in place, adding a 'full_path' key with the
        complete path from root to the collection (e.g., "Parent / Child / Grandchild").

        Args:
            collections: List of collection dicts to modify in place
        """
        # Build lookup for hierarchy traversal
        coll_by_id: dict[int, dict[str, Any]] = {
            c.get("_id"): c for c in collections if c.get("_id") is not None
        }

        def get_full_path(coll: dict[str, Any]) -> str:
            """Build full hierarchy path for a collection."""
            path_parts = [coll.get("title", "")]
            parent_info = coll.get("parent")
            while parent_info:
                parent_id = parent_info.get("$id")
                if parent_id and parent_id in coll_by_id:
                    parent = coll_by_id[parent_id]
                    path_parts.insert(0, parent.get("title", ""))
                    parent_info = parent.get("parent")
                else:
                    break
            return " / ".join(path_parts)

        for coll in collections:
            coll["full_path"] = get_full_path(coll)

    async def close(self) -> None:
        """Close the HTTP client and release resources."""
        await self.client.aclose()
