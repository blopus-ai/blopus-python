"""Typed result models (plain dataclasses — no pydantic dependency).

These mirror the deployed gateway response shapes 1:1. Each model keeps the raw
JSON in ``.raw`` so forward-compatible fields are never lost.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterator, List, Optional


def _as_int(v: Any) -> Optional[int]:
    if v is None:
        return None
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def _as_float(v: Any) -> Optional[float]:
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


@dataclass
class SearchResult:
    """One search hit from ``POST /v1/search``."""

    title: str = ""
    url: str = ""
    snippet: str = ""
    domain: Optional[str] = None
    site_name: Optional[str] = None
    favicon: Optional[str] = None
    published_at: Optional[int] = None
    age_seconds: Optional[int] = None
    language: Optional[str] = None
    score: Optional[float] = None
    #: Crawl time. ``published_at`` falls back to this when the article date is unknown.
    fetched_at: Optional[int] = None
    #: How many near-identical pages were collapsed into this hit.
    duplicate_count: int = 0
    #: Full text. Present only when the request set ``include_content``.
    content: Optional[str] = None
    raw: Dict[str, Any] = field(default_factory=dict, repr=False)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "SearchResult":
        return cls(
            title=d.get("title") or "",
            url=d.get("url") or "",
            snippet=d.get("snippet") or "",
            domain=d.get("domain"),
            site_name=d.get("site_name"),
            favicon=d.get("favicon"),
            published_at=_as_int(d.get("published_at")),
            age_seconds=_as_int(d.get("age_seconds")),
            language=d.get("language"),
            score=_as_float(d.get("score")),
            fetched_at=_as_int(d.get("fetched_at")),
            duplicate_count=_as_int(d.get("duplicate_count")) or 0,
            # only present when include_content was requested
            content=d.get("content"),
            raw=d,
        )


@dataclass
class SearchResponse:
    """Full response from ``POST /v1/search``. Iterable over its results."""

    query: str = ""
    results: List[SearchResult] = field(default_factory=list)
    count: int = 0
    offset: int = 0
    more_results: bool = False
    remaining_quota: Optional[int] = None
    raw: Dict[str, Any] = field(default_factory=dict, repr=False)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "SearchResponse":
        results = [SearchResult.from_dict(r) for r in (d.get("results") or [])]
        return cls(
            query=d.get("query") or "",
            results=results,
            count=_as_int(d.get("count")) if d.get("count") is not None else len(results),
            offset=_as_int(d.get("offset")) or 0,
            more_results=bool(d.get("more_results")),
            remaining_quota=_as_int(d.get("remaining_quota")),
            raw=d,
        )

    def __iter__(self) -> Iterator[SearchResult]:
        return iter(self.results)

    def __len__(self) -> int:
        return len(self.results)

    def __getitem__(self, i: int) -> SearchResult:
        return self.results[i]


@dataclass
class FetchResult:
    """A single fetched document (indexed page content)."""

    url: str = ""
    canonical_url: Optional[str] = None
    title: str = ""
    content: str = ""
    domain: Optional[str] = None
    published_at: Optional[int] = None
    language: Optional[str] = None
    found: bool = True
    raw: Dict[str, Any] = field(default_factory=dict, repr=False)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "FetchResult":
        return cls(
            url=d.get("url") or "",
            canonical_url=d.get("canonical_url"),
            title=d.get("title") or "",
            content=d.get("content") or "",
            domain=d.get("domain"),
            published_at=_as_int(d.get("published_at")),
            language=d.get("language"),
            found=bool(d.get("found", True)),
            raw=d,
        )


@dataclass
class FetchFailure:
    """A URL that had no indexed content."""

    url: str = ""
    found: bool = False
    raw: Dict[str, Any] = field(default_factory=dict, repr=False)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "FetchFailure":
        return cls(url=d.get("url") or "", found=bool(d.get("found", False)), raw=d)


@dataclass
class BatchFetchResponse:
    """Response from a batch ``POST /v1/fetch`` (a list of URLs)."""

    results: List[FetchResult] = field(default_factory=list)
    failed_results: List[FetchFailure] = field(default_factory=list)
    count: int = 0
    remaining_quota: Optional[int] = None
    raw: Dict[str, Any] = field(default_factory=dict, repr=False)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "BatchFetchResponse":
        results = [FetchResult.from_dict(r) for r in (d.get("results") or [])]
        failed = [FetchFailure.from_dict(r) for r in (d.get("failed_results") or [])]
        return cls(
            results=results,
            failed_results=failed,
            count=_as_int(d.get("count")) if d.get("count") is not None else len(results),
            remaining_quota=_as_int(d.get("remaining_quota")),
            raw=d,
        )

    def __iter__(self) -> Iterator[FetchResult]:
        return iter(self.results)

    def __len__(self) -> int:
        return len(self.results)
