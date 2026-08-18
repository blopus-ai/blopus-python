"""Blopus — official Python SDK for the Blopus web search + fetch API.

Quickstart::

    from blopus import Blopus

    client = Blopus(api_key="blp_live_...")   # or set BLOPUS_API_KEY
    for hit in client.search("latest ai news", freshness="pd"):
        print(hit.title, hit.url)

    doc = client.fetch("https://example.com/article")

The SDK calls only two data-plane endpoints — ``POST /v1/search`` and
``POST /v1/fetch`` on https://api.blopus.ai.
"""
from __future__ import annotations

from ._async import AsyncBlopus
from ._version import __version__
from .client import Blopus
from .exceptions import (
    APIConnectionError,
    AuthError,
    BadRequestError,
    BlopusError,
    NotFoundError,
    QuotaError,
    RateLimitError,
    ServerError,
)
from .mcp import mcp_config, print_mcp_config
from .models import (
    BatchFetchResponse,
    FetchFailure,
    FetchResult,
    SearchResponse,
    SearchResult,
    Topic,
)

__all__ = [
    "__version__",
    "Blopus",
    "AsyncBlopus",
    "mcp_config",
    "print_mcp_config",
    # models
    "SearchResponse",
    "Topic",
    "SearchResult",
    "FetchResult",
    "FetchFailure",
    "BatchFetchResponse",
    # exceptions
    "BlopusError",
    "APIConnectionError",
    "AuthError",
    "BadRequestError",
    "NotFoundError",
    "RateLimitError",
    "QuotaError",
    "ServerError",
]
