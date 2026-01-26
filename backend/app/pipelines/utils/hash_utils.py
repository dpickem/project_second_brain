"""
Hash Utilities for Content Deduplication

Provides functions for calculating content hashes used in deduplication
to prevent re-processing identical files.

Usage:
    from app.pipelines.utils.hash_utils import calculate_file_hash

    hash_value = calculate_file_hash(Path("document.pdf"))
"""

import hashlib
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse


def calculate_file_hash(file_path: Path, algorithm: str = "sha256") -> str:
    """
    Calculate hash of a file for deduplication.

    Reads the file in chunks to handle large files efficiently.

    Args:
        file_path: Path to the file
        algorithm: Hash algorithm (sha256, md5, sha1)

    Returns:
        Hex string of the hash

    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If algorithm is not supported
    """
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    if algorithm == "sha256":
        hasher = hashlib.sha256()
    elif algorithm == "md5":
        hasher = hashlib.md5()
    elif algorithm == "sha1":
        hasher = hashlib.sha1()
    else:
        raise ValueError(f"Unsupported hash algorithm: {algorithm}")

    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(8192), b""):
            hasher.update(byte_block)

    return hasher.hexdigest()


def calculate_content_hash(content: str, algorithm: str = "sha256") -> str:
    """
    Calculate hash of text content for deduplication.

    Args:
        content: Text content to hash
        algorithm: Hash algorithm

    Returns:
        Hex string of the hash
    """
    if algorithm == "sha256":
        hasher = hashlib.sha256()
    elif algorithm == "md5":
        hasher = hashlib.md5()
    elif algorithm == "sha1":
        hasher = hashlib.sha1()
    else:
        raise ValueError(f"Unsupported hash algorithm: {algorithm}")

    hasher.update(content.encode("utf-8"))
    return hasher.hexdigest()


def calculate_url_hash(url: str) -> str:
    """
    Calculate a normalized hash of a URL.

    Normalizes the URL before hashing to handle equivalent URLs
    (e.g., with/without trailing slash, different parameter order).

    Args:
        url: URL to hash

    Returns:
        Hex string of the hash
    """
    # Parse and normalize URL
    parsed = urlparse(url.lower().strip())

    # Sort query parameters for consistent hashing
    if parsed.query:
        params = parse_qs(parsed.query)
        sorted_params = urlencode(sorted(params.items()), doseq=True)
    else:
        sorted_params = ""

    # Normalize path (remove trailing slash)
    path = parsed.path.rstrip("/") or "/"

    # Reconstruct normalized URL
    normalized = f"{parsed.scheme}://{parsed.netloc}{path}"
    if sorted_params:
        normalized += f"?{sorted_params}"

    return calculate_content_hash(normalized)


def short_hash(hash_value: str, length: int = 8) -> str:
    """
    Return a shortened version of a hash for display/logging.

    Args:
        hash_value: Full hash string
        length: Number of characters to return

    Returns:
        Shortened hash string
    """
    return hash_value[:length]
