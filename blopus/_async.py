"""Asynchronous Blopus client (httpx.AsyncClient). Mirrors :class:`Blopus` exactly.

    import asyncio
    from blopus import AsyncBlopus

    async def main():
        async with AsyncBlopus() as client:
            res = await client.search("openai news", freshness="pw")
            docs = await client.fetch([r.url for r in res])

    asyncio.run(main())
"""
from __future__ import annotations

import asyncio
from typing import Optional, Sequence, Union

import httpx

from . import _common as C
from .exceptions import APIConnectionError
from .models import BatchFetchResponse, FetchFailure, FetchResult, SearchResponse


class AsyncBlopus:
    """Async client for the Blopus search + fetch API. Same surface as :class:`Blopus`."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        *,
        base_url: Optional[str] = None,
        timeout: float = C.DEFAULT_TIMEOUT,
        max_retries: int = C.DEFAULT_MAX_RETRIES,
        chunk_delay: float = C.DEFAULT_CHUNK_DELAY,
        user_agent: str = C.USER_AGENT,
    ) -> None:
        self._api_key = C.resolve_api_key(api_key)
        self.base_url = C.resolve_base_url(base_url)
        self.max_retries = max_retries
        self.chunk_delay = chunk_delay
        self._http = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=timeout,
            headers=C.build_headers(self._api_key, user_agent),
        )

    async def aclose(self) -> None:
        await self._http.aclose()

    async def __aenter__(self) -> "AsyncBlopus":
        return self

    async def __aexit__(self, *exc) -> None:
        await self.aclose()

    async def _post(self, path: str, body: dict) -> dict:
        attempt = 0
        while True:
            status: Optional[int] = None
            retry_after: Optional[int] = None
            try:
                resp = await self._http.post(path, json=body)
                status = resp.status_code
                retry_after = C.parse_retry_after(resp.headers.get("Retry-After"))
                if 200 <= status < 300:
                    return C.parse_json_or_raise(status, resp.text, retry_after)
            except httpx.HTTPError as exc:
                if not C.should_retry(None, attempt, self.max_retries):
                    raise APIConnectionError(f"Request failed: {exc}") from exc
                await asyncio.sleep(C.backoff_seconds(attempt, None))
                attempt += 1
                continue

            if C.should_retry(status, attempt, self.max_retries):
                await asyncio.sleep(C.backoff_seconds(attempt, retry_after))
                attempt += 1
                continue
            return C.parse_json_or_raise(status, resp.text, retry_after)

    async def search(
        self,
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
        min_words: Optional[int] = None,
        recency: Optional[str] = None,
        include_content: bool = False,
        content_chars: Optional[int] = None,
    ) -> SearchResponse:
        """Run a web search. Always costs 1 credit regardless of params.

        Set ``min_words=120`` when you want something to READ - analysis, background,
        a comparison. It drops tag listings and stub pages, which are keyword bait.
        Leave it off for breaking news, where a two-line wire story is a real answer.

        Set ``news_only=True`` when the question is about events — what happened,
        who announced what, market reaction, election results, earnings news. It
        searches only sources with a newsroom over a dedicated news channel, so it
        is *faster* than an unscoped search, and drops vendor blogs, marketing
        pages and documentation that crowd news results.

        Leave it off for documentation, tutorials, forums or reference material,
        and whenever a question wants both — "what's new in Python 3.14" needs the
        release announcement *and* the changelog. Omitting it searches everything,
        so it is always the safe default.
        """
        body = C.build_search_body(
            query,
            count=count,
            freshness=freshness,
            include_domains=include_domains,
            exclude_domains=exclude_domains,
            start_date=start_date,
            end_date=end_date,
            language=language,
            offset=offset,
            include_excerpt=include_excerpt,
            excerpt_chars=excerpt_chars,
            news_only=news_only,
            min_words=min_words,
            recency=recency,
            include_content=include_content,
            content_chars=content_chars,
        )
        return SearchResponse.from_dict(await self._post("/v1/search", body))

    async def fetch(
        self, url_or_urls: Union[str, Sequence[str]]
    ) -> Union[FetchResult, BatchFetchResponse]:
        is_batch, urls, single = C.normalize_fetch_urls(url_or_urls)
        if not is_batch:
            data = await self._post("/v1/fetch", {"url": single})
            return FetchResult.from_dict(data)
        return await self._fetch_batch(urls)

    async def _fetch_batch(self, urls: Sequence[str]) -> BatchFetchResponse:
        chunks = C.chunk_urls(urls)
        merged_results: list[FetchResult] = []
        merged_failed: list[FetchFailure] = []
        remaining: Optional[int] = None
        for i, chunk in enumerate(chunks):
            if i > 0 and self.chunk_delay > 0:
                await asyncio.sleep(self.chunk_delay)
            data = await self._post("/v1/fetch", {"urls": list(chunk)})
            part = BatchFetchResponse.from_dict(data)
            merged_results.extend(part.results)
            merged_failed.extend(part.failed_results)
            if part.remaining_quota is not None:
                remaining = part.remaining_quota
        return BatchFetchResponse(
            results=merged_results,
            failed_results=merged_failed,
            count=len(merged_results),
            remaining_quota=remaining,
        )
