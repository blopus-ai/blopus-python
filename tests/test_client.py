"""Client tests using a mock httpx transport (no network)."""
import httpx
import pytest

from blopus import Blopus
from blopus.exceptions import QuotaError, RateLimitError
from blopus.models import BatchFetchResponse, FetchResult, SearchResponse


def make_client(handler, **kw):
    client = Blopus(api_key="blp_live_test", **kw)
    client._http = httpx.Client(
        base_url=client.base_url,
        transport=httpx.MockTransport(handler),
        headers={"User-Agent": "blopus-python/test"},
    )
    return client


def test_search_parses_and_sends_ua():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["ua"] = request.headers.get("User-Agent")
        seen["path"] = request.url.path
        return httpx.Response(200, json={
            "query": "cats",
            "results": [
                {"title": "Cats", "url": "https://x.com", "snippet": "meow",
                 "domain": "x.com", "score": 0.9},
            ],
            "count": 1,
            "offset": 0,
            "more_results": True,
            "remaining_quota": 1499,
        })

    client = make_client(handler)
    res = client.search("cats", count=1)
    assert isinstance(res, SearchResponse)
    assert res.results[0].title == "Cats"
    assert res.results[0].score == 0.9
    assert res.more_results is True
    assert res.remaining_quota == 1499
    assert seen["path"] == "/v1/search"
    assert seen["ua"].startswith("blopus-python/")
    assert len(res) == 1
    assert res[0].url == "https://x.com"


def test_single_fetch():
    def handler(request):
        assert request.url.path == "/v1/fetch"
        return httpx.Response(200, json={
            "url": "https://x.com/a", "title": "A", "content": "body",
            "domain": "x.com", "found": True,
        })

    client = make_client(handler)
    doc = client.fetch("https://x.com/a")
    assert isinstance(doc, FetchResult)
    assert doc.content == "body"


def test_batch_fetch_autochunks():
    calls = []

    def handler(request):
        import json
        body = json.loads(request.content)
        urls = body["urls"]
        calls.append(len(urls))
        return httpx.Response(200, json={
            "results": [{"url": u, "title": "t", "content": "c"} for u in urls],
            "failed_results": [],
            "count": len(urls),
            "remaining_quota": 100,
        })

    client = make_client(handler, chunk_delay=0)
    urls = [f"https://x.com/{i}" for i in range(120)]
    res = client.fetch(urls)
    assert isinstance(res, BatchFetchResponse)
    assert calls == [50, 50, 20]       # auto-chunked into <=50
    assert res.count == 120
    assert res.remaining_quota == 100


def test_quota_error_raised():
    def handler(request):
        return httpx.Response(402, json={
            "error": {"code": "quota_exceeded", "message": "Monthly quota exhausted."}})

    client = make_client(handler)
    with pytest.raises(QuotaError):
        client.search("x")


def test_rate_limit_retries_then_raises():
    state = {"n": 0}

    def handler(request):
        state["n"] += 1
        return httpx.Response(429, headers={"Retry-After": "0"},
                              json={"error": {"code": "rate_limited", "message": "slow"}})

    client = make_client(handler, max_retries=2)
    with pytest.raises(RateLimitError):
        client.search("x")
    assert state["n"] == 3   # initial + 2 retries
