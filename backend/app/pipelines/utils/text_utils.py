"""
Text Processing Utilities

Provides functions for text cleaning, JSON extraction, and text manipulation
used across ingestion pipelines.

Usage:
    from app.pipelines.utils.text_utils import (
        clean_text,
        extract_json_from_response,
        normalize_llm_json_response,
    )

    text = clean_text(raw_text)
    data = extract_json_from_response(llm_response)
    data = normalize_llm_json_response(data, "concepts")  # Ensure dict structure
    chunks = split_into_chunks(long_text, chunk_size=1000, chunk_overlap=100)
"""

import json
import re
from typing import Any, Optional

import markdown
from bs4 import BeautifulSoup
from langchain_text_splitters import (
    RecursiveCharacterTextSplitter,
    MarkdownTextSplitter,
    TokenTextSplitter,
)


def normalize_llm_json_response(data: Any, expected_key: str) -> dict:
    """
    Normalize an LLM JSON response to ensure it's a dict with expected structure.

    Use this for responses that should have a list under a specific key,
    like {"concepts": [...]} or {"questions": [...]}.

    Sometimes LLMs return a list directly instead of a dict with the expected key.
    This function handles that case by wrapping the list in a dict.

    Examples:
        # If LLM returns: [{"name": "foo"}, {"name": "bar"}]
        # And expected_key is "concepts"
        # Returns: {"concepts": [{"name": "foo"}, {"name": "bar"}]}

        # If LLM returns: {"concepts": [...]}
        # Returns as-is: {"concepts": [...]}

    Args:
        data: Parsed JSON from LLM (could be dict or list)
        expected_key: The key that should contain the list (e.g., "concepts", "questions")

    Returns:
        Normalized dict with the expected key
    """
    if isinstance(data, dict):
        return data
    elif isinstance(data, list):
        # Wrap the list in a dict with the expected key
        return {expected_key: data}
    else:
        # Return empty dict for unexpected types
        return {}


def unwrap_llm_single_object_response(data: Any) -> dict:
    """
    Unwrap an LLM JSON response that should be a single object.

    Use this for responses that should be a flat dict with multiple keys,
    like {"content_type": "...", "domain": "...", "complexity": "..."}.

    Sometimes LLMs wrap the object in a list: [{"content_type": "...", ...}]
    This function handles that case by extracting the first item.

    Examples:
        # If LLM returns: [{"content_type": "paper", "domain": "ml"}]
        # Returns: {"content_type": "paper", "domain": "ml"}

        # If LLM returns: {"content_type": "paper", "domain": "ml"}
        # Returns as-is: {"content_type": "paper", "domain": "ml"}

    Args:
        data: Parsed JSON from LLM (could be dict or list with one dict)

    Returns:
        The dict object (unwrapped from list if necessary)
    """
    if isinstance(data, dict):
        return data
    elif isinstance(data, list) and len(data) > 0 and isinstance(data[0], dict):
        # Unwrap the first item from the list
        return data[0]
    else:
        # Return empty dict for unexpected types
        return {}


def clean_text(text: str) -> str:
    """
    Clean and normalize text content.

    - Removes excessive whitespace
    - Normalizes line endings
    - Removes null characters
    - Strips leading/trailing whitespace

    Args:
        text: Raw text to clean

    Returns:
        Cleaned text
    """
    if not text:
        return ""

    # Remove null characters
    text = text.replace("\x00", "")

    # Normalize line endings
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Remove excessive blank lines (more than 2 consecutive)
    text = re.sub(r"\n{3,}", "\n\n", text)

    # Normalize multiple spaces to single space (but preserve newlines)
    text = re.sub(r"[^\S\n]+", " ", text)

    # Strip leading/trailing whitespace from each line
    lines = [line.strip() for line in text.split("\n")]
    text = "\n".join(lines)

    # Final strip
    return text.strip()


def extract_json_from_response(response_text: str) -> Optional[Any]:
    """
    Extract JSON from an LLM response that may contain markdown code blocks.

    Handles various formats:
    - Raw JSON
    - JSON in ```json ... ``` blocks
    - JSON in ``` ... ``` blocks

    Note:
        Only the first JSON block found is extracted. If the response contains
        multiple JSON blocks, subsequent blocks are ignored.

    Args:
        response_text: LLM response text

    Returns:
        Parsed JSON object, or None if parsing fails
    """
    if not response_text:
        return None

    text = response_text.strip()

    # Try to extract from markdown code blocks
    patterns = [
        r"```json\s*([\s\S]*?)\s*```",  # ```json ... ```
        r"```\s*([\s\S]*?)\s*```",  # ``` ... ```
    ]

    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            text = match.group(1).strip()
            break

    # Try to parse as JSON
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Try to find JSON object or array in the text
        json_patterns = [
            r"(\{[\s\S]*\})",  # JSON object
            r"(\[[\s\S]*\])",  # JSON array
        ]

        for pattern in json_patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    return json.loads(match.group(1))
                except json.JSONDecodeError:
                    continue

    return None


def truncate_text(text: str, max_length: int, suffix: str = "...") -> str:
    """
    Truncate text to a maximum length, adding suffix if truncated.

    Tries to break at word boundaries when possible.

    Args:
        text: Text to truncate
        max_length: Maximum length (including suffix)
        suffix: String to append if truncated

    Returns:
        Truncated text
    """
    if not text or len(text) <= max_length:
        return text

    # Account for suffix length
    target_length = max_length - len(suffix)

    if target_length <= 0:
        return suffix[:max_length]

    # Try to break at word boundary
    truncated = text[:target_length]

    # Find last space
    last_space = truncated.rfind(" ")
    if last_space > target_length * 0.7:  # Only break at word if not too far back
        truncated = truncated[:last_space]

    return truncated + suffix


def extract_title_from_text(text: str, max_length: int = 100) -> str:
    """
    Extract a title from the beginning of text content.

    Looks for the first meaningful line that could serve as a title.

    Args:
        text: Text content
        max_length: Maximum title length

    Returns:
        Extracted title
    """
    if not text:
        return "Untitled"

    lines = text.strip().split("\n")

    for line in lines:
        # Clean the line
        clean = line.strip()

        # Skip empty lines and common non-title patterns
        if not clean:
            continue
        if clean.startswith("#"):
            clean = clean.lstrip("#").strip()
        if len(clean) < 5:
            continue

        # Return the first valid line as title
        return truncate_text(clean, max_length, "...")

    return "Untitled"


def normalize_whitespace(text: str) -> str:
    """
    Normalize all whitespace to single spaces.

    Args:
        text: Input text

    Returns:
        Text with normalized whitespace
    """
    return " ".join(text.split())


def remove_markdown_formatting(text: str) -> str:
    """
    Remove markdown formatting from text, converting to plain text.

    Uses the markdown library to convert to HTML, then BeautifulSoup
    to extract clean text. This is more robust than regex-based approaches
    as it handles edge cases and nested formatting correctly.

    Args:
        text: Markdown text

    Returns:
        Plain text without markdown formatting
    """
    if not text:
        return ""

    # Convert Markdown to HTML
    html_text = markdown.markdown(text)

    # Use BeautifulSoup to extract clean text
    soup = BeautifulSoup(html_text, "html.parser")
    plain_text = soup.get_text(separator=" ", strip=True)

    return clean_text(plain_text)


def split_into_chunks(
    text: str,
    chunk_size: int = 4000,
    chunk_overlap: int = 200,
    separators: Optional[list[str]] = None,
) -> list[str]:
    """
    Split text into overlapping chunks using LangChain's RecursiveCharacterTextSplitter.

    This splitter tries to split on natural boundaries (paragraphs, sentences, words)
    in order of preference, making it ideal for preserving semantic coherence.

    Args:
        text: Text to split
        chunk_size: Target size of each chunk (in characters)
        chunk_overlap: Number of characters to overlap between chunks
        separators: Custom separators to use (defaults to paragraphs, newlines, sentences, words)

    Returns:
        List of text chunks
    """
    if not text:
        return []

    if len(text) <= chunk_size:
        return [text]

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=separators or ["\n\n", "\n", ". ", "! ", "? ", "; ", ", ", " ", ""],
        length_function=len,
    )

    return splitter.split_text(text)


def split_markdown_into_chunks(
    text: str,
    chunk_size: int = 4000,
    chunk_overlap: int = 200,
) -> list[str]:
    """
    Split markdown text into chunks, respecting markdown structure.

    Uses LangChain's MarkdownTextSplitter which splits on markdown headers
    and other structural elements, preserving document organization.

    Args:
        text: Markdown text to split
        chunk_size: Target size of each chunk (in characters)
        chunk_overlap: Number of characters to overlap between chunks

    Returns:
        List of markdown chunks
    """
    if not text:
        return []

    if len(text) <= chunk_size:
        return [text]

    splitter = MarkdownTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )

    return splitter.split_text(text)


def split_by_tokens(
    text: str,
    chunk_size: int = 1000,
    chunk_overlap: int = 100,
    model_name: str = "gpt-4",
) -> list[str]:
    """
    Split text into chunks based on token count rather than characters.

    Uses LangChain's TokenTextSplitter with tiktoken encoding to ensure
    chunks stay within model token limits. More accurate for LLM processing.

    Args:
        text: Text to split
        chunk_size: Target size of each chunk (in tokens)
        chunk_overlap: Number of tokens to overlap between chunks
        model_name: Model name for tokenizer (affects token counting)

    Returns:
        List of text chunks
    """
    if not text:
        return []

    splitter = TokenTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        model_name=model_name,
    )

    return splitter.split_text(text)
