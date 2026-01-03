"""
GitHub Repository Importer Pipeline

Analyzes starred repositories and extracts learnings using LLM analysis.
Fetches README, file structure, and generates structured analysis.

Features:
- Starred repos sync
- Individual repo import by URL
- README content extraction
- File tree analysis
- LLM-powered analysis (purpose, architecture, tech stack, learnings)
- LLM cost tracking for all API calls

Usage:
    from app.pipelines import GitHubImporter

    importer = GitHubImporter(access_token="ghp_...")
    repos = await importer.import_starred_repos(limit=10)
"""

from datetime import datetime
from typing import Optional

import httpx

from app.models.content import ContentType, UnifiedContent
from app.pipelines.base import BasePipeline, PipelineInput, PipelineContentType
from app.pipelines.utils.cost_types import LLMUsage, PipelineName, PipelineOperation
from app.pipelines.utils.text_client import get_default_text_model, text_completion
from app.services.cost_tracking import CostTracker

# Default configuration
DEFAULT_TIMEOUT = 30.0
DEFAULT_STARRED_REPOS_LIMIT = 50

# File tree limits
MAX_TREE_FILES = 100  # Max files to fetch from GitHub tree API
TREE_DISPLAY_LIMIT = 50  # Files shown in LLM context

# README truncation limit
README_TRUNCATE_LIMIT = 8000  # Chars for LLM context

# LLM parameters
LLM_MAX_TOKENS = 2000
LLM_TEMPERATURE = 0.3


class GitHubImporter(BasePipeline):
    """
    GitHub repository importer for extracting learnings from code repos.

    Analyzes starred repositories and generates structured knowledge notes about purpose,
    architecture, and key learnings. Tracks LLM costs for all API calls.

    Routing:
    - Content type: PipelineContentType.CODE
    - Input: GitHub URL (url field in PipelineInput)
    """

    BASE_URL = "https://api.github.com"
    SUPPORTED_CONTENT_TYPES = {PipelineContentType.CODE}
    PIPELINE_NAME = PipelineName.GITHUB_IMPORTER

    def __init__(
        self,
        access_token: str,
        text_model: Optional[str] = None,
        timeout: float = DEFAULT_TIMEOUT,
        track_costs: bool = True,
    ):
        """
        Initialize GitHub importer.

        Args:
            access_token: GitHub personal access token
            text_model: LLM model for repo analysis. Defaults to value from
                environment variable via get_default_text_model().
            timeout: HTTP request timeout
            track_costs: Whether to log LLM costs to database
        """
        super().__init__()
        self.text_model = text_model or get_default_text_model()
        self.track_costs = track_costs
        self._usage_records: list[LLMUsage] = []
        self._content_id: Optional[str] = None
        self.client = httpx.AsyncClient(
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/vnd.github.v3+json",
            },
            timeout=timeout,
        )

    def supports(self, input_data: PipelineInput) -> bool:
        """
        Check if this pipeline can handle the input.

        Requires:
        - content_type == CODE
        - url is set and is a GitHub URL
        """
        if not isinstance(input_data, PipelineInput):
            return False

        if input_data.content_type != PipelineContentType.CODE:
            return False

        if input_data.url is None:
            return False

        return input_data.url.startswith("https://github.com/")

    async def process(
        self,
        input_data: PipelineInput,
        content_id: Optional[str] = None,
    ) -> UnifiedContent:
        """
        Process a GitHub URL from PipelineInput.

        Args:
            input_data: PipelineInput with GitHub URL
            content_id: Optional content ID for cost attribution and tracking

        Returns:
            UnifiedContent with repo analysis
        """
        if input_data.url is None:
            raise ValueError("PipelineInput.url is required for GitHub import")

        return await self.import_repo(input_data.url, content_id)

    async def import_starred_repos(
        self, limit: int = DEFAULT_STARRED_REPOS_LIMIT
    ) -> list[UnifiedContent]:
        """
        Import user's starred repositories.

        Args:
            limit: Maximum number of repos to import

        Returns:
            List of UnifiedContent objects
        """
        try:
            response = await self.client.get(
                f"{self.BASE_URL}/user/starred",
                params={
                    "per_page": limit,
                    "sort": "created",
                    "direction": "desc",
                },
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            self.logger.error(f"Failed to fetch starred repos: {e}")
            raise

        repos = response.json()
        results = []

        for repo in repos:
            try:
                content = await self._analyze_repo(repo)
                results.append(content)
            except Exception as e:
                self.logger.error(
                    f"Failed to analyze {repo.get('full_name', 'unknown')}: {e}"
                )

        self.logger.info(f"Imported {len(results)} starred repos")
        return results

    async def import_repo(
        self,
        repo_url: str,
        content_id: Optional[str] = None,
    ) -> UnifiedContent:
        """
        Import a specific repository by URL.

        Args:
            repo_url: GitHub repository URL
            content_id: Optional content ID for cost attribution and tracking

        Returns:
            UnifiedContent with repo analysis
        """
        # Reset usage records for this processing run
        self._usage_records = []
        self._content_id = content_id

        # Parse owner/repo from URL
        url_clean = repo_url.replace("https://github.com/", "")
        parts = url_clean.split("/")
        owner, repo = parts[0], parts[1].split("#")[0].split("?")[0]

        response = await self.client.get(f"{self.BASE_URL}/repos/{owner}/{repo}")
        response.raise_for_status()

        return await self._analyze_repo(response.json())

    async def _analyze_repo(self, repo: dict) -> UnifiedContent:
        """Analyze a repository and create content."""
        full_name = repo.get("full_name", "unknown/unknown")

        self.logger.info(f"Analyzing repository: {full_name}")

        # Fetch README
        readme = await self._get_readme(full_name)

        # Get file tree
        tree = await self._get_tree(full_name)

        # Generate analysis
        analysis = await self._generate_analysis(repo, readme, tree)

        # Parse dates
        created_at = datetime.now()
        if repo.get("created_at"):
            try:
                created_at = datetime.fromisoformat(
                    repo.get("created_at", "").replace("Z", "+00:00")
                )
            except (ValueError, TypeError):
                pass

        # Log all accumulated LLM costs to database
        if self.track_costs and self._usage_records:
            total_cost = sum(u.cost_usd or 0 for u in self._usage_records)
            self.logger.info(
                f"GitHub import complete for {full_name} - Total LLM cost: ${total_cost:.4f} "
                f"({len(self._usage_records)} API calls)"
            )
            await CostTracker.log_usages_batch(self._usage_records)

        # Extract owner login safely
        owner = repo.get("owner", {})
        owner_login = (
            owner.get("login", "unknown") if isinstance(owner, dict) else "unknown"
        )

        return UnifiedContent(
            source_type=ContentType.CODE,
            source_url=repo.get("html_url", ""),
            title=full_name,
            authors=[owner_login],
            created_at=created_at,
            full_text=analysis,
            tags=repo.get("topics", []),
            metadata={
                "github_id": repo.get("id"),
                "stars": repo.get("stargazers_count", 0),
                "forks": repo.get("forks_count", 0),
                "language": repo.get("language"),
                "license": repo.get("license", {}).get("name"),
                "description": repo.get("description"),
                "is_fork": repo.get("fork", False),
                "default_branch": repo.get("default_branch", "main"),
                "llm_cost_usd": sum(u.cost_usd or 0 for u in self._usage_records),
                "llm_api_calls": len(self._usage_records),
            },
        )

    async def _get_readme(self, full_name: str) -> str:
        """Fetch README content from repository."""
        try:
            response = await self.client.get(
                f"{self.BASE_URL}/repos/{full_name}/readme",
                headers={"Accept": "application/vnd.github.raw"},
            )
            if response.status_code == 200:
                return response.text
        except Exception as e:
            self.logger.debug(f"No README found for {full_name}: {e}")

        return ""

    async def _get_tree(self, full_name: str) -> list[str]:
        """Get repository file tree."""
        try:
            response = await self.client.get(
                f"{self.BASE_URL}/repos/{full_name}/git/trees/HEAD",
                params={"recursive": "1"},
            )
            if response.status_code == 200:
                tree = response.json().get("tree", [])
                return [item["path"] for item in tree if item.get("type") == "blob"][
                    :MAX_TREE_FILES
                ]
        except Exception as e:
            self.logger.debug(f"Failed to get tree for {full_name}: {e}")

        return []

    async def _generate_analysis(self, repo: dict, readme: str, tree: list[str]) -> str:
        """Generate LLM-powered repository analysis.

        Args:
            repo: GitHub repository data from API
            readme: README content (may be empty)
            tree: List of file paths in the repository

        Returns:
            Formatted analysis string with repo details and learnings

        Raises:
            ValueError: If text_model is not configured
            Exception: If LLM analysis fails
        """
        if not self.text_model:
            raise ValueError("text_model is required for repository analysis")

        # Build context for LLM analysis
        context = self._build_analysis_context(repo, readme, tree)

        prompt = """Analyze this GitHub repository and provide a structured summary for learning purposes.

Include the following sections:
1. **Purpose**: What problem does this project solve? Who is it for?
2. **Architecture Overview**: Key design patterns, architecture decisions, and code organization
3. **Tech Stack**: Main technologies, frameworks, and notable dependencies
4. **Key Learnings**: What can be learned from this project? Best practices demonstrated?
5. **Notable Features**: Interesting or innovative features worth studying

Keep the analysis concise but informative. Focus on aspects that would be valuable for a developer studying this codebase."""

        response, usage = await text_completion(
            model=self.text_model,
            prompt=prompt,
            system_prompt=f"You are a senior software engineer analyzing a GitHub repository.\n\nRepository Information:\n{context}",
            max_tokens=LLM_MAX_TOKENS,
            temperature=LLM_TEMPERATURE,
            pipeline=self.PIPELINE_NAME,
            content_id=self._content_id,
            operation=PipelineOperation.REPO_ANALYSIS,
        )

        # Track usage for batch logging
        self._usage_records.append(usage)

        self.logger.debug(
            f"LLM analysis complete for {repo.get('full_name', 'unknown')} - "
            f"Cost: ${usage.cost_usd or 0:.4f}"
        )

        # Combine basic info header with LLM analysis
        header = self._build_header(repo)
        return f"{header}\n\n{response}"

    def _build_analysis_context(self, repo: dict, readme: str, tree: list[str]) -> str:
        """Build context string for LLM analysis prompt."""
        parts = [
            f"Repository: {repo.get('full_name', 'unknown/unknown')}",
            f"Description: {repo.get('description', 'No description')}",
            f"Language: {repo.get('language', 'Unknown')}",
            f"Stars: {repo.get('stargazers_count', 0)} | Forks: {repo.get('forks_count', 0)}",
            f"Topics: {', '.join(repo.get('topics', [])) or 'None'}",
        ]

        if readme:
            # Truncate README to avoid token limits
            readme_excerpt = readme[:README_TRUNCATE_LIMIT]
            if len(readme) > README_TRUNCATE_LIMIT:
                readme_excerpt += "\n... (truncated)"
            parts.append(f"\n## README\n{readme_excerpt}")

        if tree:
            tree_str = "\n".join(tree[:TREE_DISPLAY_LIMIT])
            if len(tree) > TREE_DISPLAY_LIMIT:
                tree_str += f"\n... and {len(tree) - TREE_DISPLAY_LIMIT} more files"
            parts.append(f"\n## File Structure\n{tree_str}")

        return "\n".join(parts)

    def _build_header(self, repo: dict) -> str:
        """Build a header section with basic repo info."""
        return "\n".join(
            [
                f"# {repo.get('full_name', 'unknown/unknown')}",
                "",
                f"**Description:** {repo.get('description', 'No description')}",
                f"**Stars:** {repo.get('stargazers_count', 0)} | **Forks:** {repo.get('forks_count', 0)}",
                f"**Language:** {repo.get('language', 'Unknown')}",
                f"**Topics:** {', '.join(repo.get('topics', [])) or 'None'}",
            ]
        )

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
