"""Shared, transport-agnostic helpers used by both the sync and async clients.

Keeping request-building, response-parsing, retry policy and error mapping here
guarantees the two clients behave identically — the only difference between them
is ``httpx.Client`` vs ``httpx.AsyncClient``.
"""
from __future__ import annotations

import json
import os
import random
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Union

from ._version import __version__
from .exceptions import BlopusError, error_from_response

DEFAULT_BASE_URL = "https://api.blopus.ai"
DEFAULT_MCP_URL = "https://mcp.blopus.ai"
DEFAULT_TIMEOUT = 30.0
DEFAULT_MAX_RETRIES = 2
ENV_API_KEY = "BLOPUS_API_KEY"
ENV_BASE_URL = "BLOPUS_BASE_URL"

# Persistent credential store, written by `blopus login` (like `aws configure` /
# `gh auth login`). Honored as a fallback so users never have to touch env vars.
CONFIG_DIR = Path(os.environ.get("BLOPUS_CONFIG_DIR")
                  or (Path.home() / ".config" / "blopus"))
CONFIG_FILE = CONFIG_DIR / "credentials.json"


def load_config_key() -> Optional[str]:
    """Return the API key saved by `blopus login`, or None."""
    try:
        data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        key = data.get("api_key")
        return key if isinstance(key, str) and key else None
    except (OSError, ValueError):
        return None


def save_config_key(api_key: str) -> Path:
    """Persist the API key to the config file with owner-only permissions."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps({"api_key": api_key}) + "\n", encoding="utf-8")
    try:
        os.chmod(CONFIG_FILE, 0o600)
    except OSError:
        pass
    return CONFIG_FILE


def clear_config_key() -> bool:
    """Delete the stored credential. Returns True if a file was removed."""
    try:
        CONFIG_FILE.unlink()
        return True
    except OSError:
        return False

# Server-enforced cap: at most 50 URLs per /v1/fetch call.
BATCH_URL_LIMIT = 50
# Small courtesy delay between auto-chunked batches to respect per-second limits.
DEFAULT_CHUNK_DELAY = 0.25

# A *real* User-Agent is mandatory: Cloudflare 1010-blocks default library UAs
# (python-httpx/..., node-fetch, etc.) on api.blopus.ai.
USER_AGENT = f"blopus-python/{__version__}"

# Retry these HTTP statuses with backoff (transient / rate-limited).
RETRY_STATUSES = frozenset({429, 500, 502, 503, 504})


def resolve_api_key(api_key: Optional[str]) -> str:
    # Precedence: explicit arg > env var > saved credential (`blopus login`).
    key = api_key or os.environ.get(ENV_API_KEY) or load_config_key()
    if not key:
        raise BlopusError(
            "No API key found. Run `blopus login` to save one, or set the "
            f"{ENV_API_KEY} environment variable, or pass api_key=...",
            code="no_api_key",
        )
    return key


def resolve_base_url(base_url: Optional[str]) -> str:
    return (base_url or os.environ.get(ENV_BASE_URL) or DEFAULT_BASE_URL).rstrip("/")


def build_headers(api_key: str, user_agent: str = USER_AGENT) -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {api_key}",
        "User-Agent": user_agent,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def build_search_body(
    query: str,
    *,
    count: int = 10,
    freshness: str = "all",
    include_domains: Optional[Sequence[str]] = None,
    exclude_domains: Optional[Sequence[str]] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    language: Optional[str] = None,
    offset: int = 0,
    include_excerpt: bool = False,
    excerpt_chars: Optional[int] = None,
    news_only: bool = False,
    min_words: int | None = None,
    include_images: bool = False,
    topics: Optional[Sequence[str]] = None,
    exclude_topics: Optional[Sequence[str]] = None,
    recency: Optional[str] = None,
    include_content: bool = False,
    content_chars: Optional[int] = None,
) -> Dict[str, Any]:
    """Assemble the JSON body for ``POST /v1/search`` (omitting unset optionals)."""
    body: Dict[str, Any] = {
        "query": query,
        "count": count,
        "freshness": freshness,
        "offset": offset,
    }
    if include_domains:
        body["include_domains"] = list(include_domains)
    if exclude_domains:
        body["exclude_domains"] = list(exclude_domains)
    if start_date is not None:
        body["start_date"] = start_date
    if end_date is not None:
        body["end_date"] = end_date
    if language is not None:
        body["language"] = language
    if include_excerpt:
        body["include_excerpt"] = True
    if excerpt_chars is not None:
        body["excerpt_chars"] = excerpt_chars
    # recency changes RANKING; freshness FILTERS. Sent only when set, so the server
    # default ("normal") stays authoritative.
    if recency is not None:
        body["recency"] = recency
    if include_content:
        body["include_content"] = True
    if content_chars is not None:
        body["content_chars"] = content_chars
    if news_only:
        # only send it when true — an older gateway would 422 on an unknown field
        body["news_only"] = True
    if min_words:
        # Hard `word_count >= n` filter in the engine. About 10-17% of the index is
        # under 120 words - tag listings, stubs, photo captions - and they rank on
        # keywords without saying anything.
        body["min_words"] = int(min_words)
    if topics:
        # Topics describe what a PUBLICATION covers, not what one article is about.
        # Matched exactly against a published vocabulary (see Blopus.topics()), so an
        # unknown value returns nothing rather than silently widening the search.
        body["topics"] = [t for t in topics]
    if exclude_topics:
        body["exclude_topics"] = [t for t in exclude_topics]
    if include_images:
        # Hero image URL per result. OFF by default because it costs roughly 295
        # tokens per 10 results, which matters when the caller is an LLM. Coverage is
        # partial, so `image` is None on plenty of hits - treat that as normal.
        body["include_images"] = True
    return body


def normalize_fetch_urls(
    url_or_urls: Union[str, Sequence[str]],
) -> tuple[bool, List[str], Optional[str]]:
    """Return (is_batch, url_list, single_url).

    A single string is a single fetch; any sequence is a batch (even length 1).
    """
    if isinstance(url_or_urls, str):
        return False, [url_or_urls], url_or_urls
    urls = [str(u) for u in url_or_urls]
    if not urls:
        raise BlopusError("fetch() requires at least one URL.", code="bad_request")
    return True, urls, None


def chunk_urls(urls: Sequence[str], size: int = BATCH_URL_LIMIT) -> List[List[str]]:
    return [list(urls[i : i + size]) for i in range(0, len(urls), size)]


def parse_json_or_raise(status: int, text: str, retry_after: Optional[int]) -> Dict[str, Any]:
    """Parse a response body; raise a typed error for non-2xx statuses."""
    import json

    body: Optional[Dict[str, Any]]
    try:
        body = json.loads(text) if text else None
    except (ValueError, TypeError):
        body = None
    if 200 <= status < 300:
        if not isinstance(body, dict):
            raise error_from_response(status, {"error": {"code": "invalid_response",
                                                         "message": "Malformed JSON from API."}})
        return body
    raise error_from_response(status, body, retry_after=retry_after)


def parse_retry_after(value: Optional[str]) -> Optional[int]:
    if not value:
        return None
    try:
        return max(0, int(float(value)))
    except (TypeError, ValueError):
        return None


def backoff_seconds(attempt: int, retry_after: Optional[int]) -> float:
    """Exponential backoff with jitter; honor server Retry-After when present."""
    if retry_after is not None:
        return float(retry_after)
    return min(8.0, (2 ** attempt) * 0.5) + random.uniform(0, 0.25)


def should_retry(status: Optional[int], attempt: int, max_retries: int) -> bool:
    if attempt >= max_retries:
        return False
    if status is None:  # connection error
        return True
    return status in RETRY_STATUSES
