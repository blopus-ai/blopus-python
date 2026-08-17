"""Unit tests for transport-agnostic helpers (no network)."""
import pytest

from blopus import _common as C
from blopus.exceptions import (
    AuthError,
    BadRequestError,
    BlopusError,
    NotFoundError,
    QuotaError,
    RateLimitError,
    ServerError,
    error_from_response,
)


def test_build_search_body_omits_unset():
    body = C.build_search_body("hi")
    assert body == {"query": "hi", "count": 10, "freshness": "all", "offset": 0}


def test_build_search_body_includes_set():
    body = C.build_search_body(
        "hi",
        count=5,
        freshness="pd",
        include_domains=["a.com"],
        exclude_domains=["b.com"],
        start_date="2026-01-01",
        end_date="2026-02-01",
        language="en",
        offset=10,
        include_excerpt=True,
        excerpt_chars=900,
    )
    assert body["count"] == 5
    assert body["include_domains"] == ["a.com"]
    assert body["exclude_domains"] == ["b.com"]
    assert body["start_date"] == "2026-01-01"
    assert body["language"] == "en"
    assert body["include_excerpt"] is True
    assert body["excerpt_chars"] == 900


def test_normalize_fetch_urls_single():
    is_batch, urls, single = C.normalize_fetch_urls("https://x.com")
    assert is_batch is False and single == "https://x.com" and urls == ["https://x.com"]


def test_normalize_fetch_urls_batch():
    is_batch, urls, single = C.normalize_fetch_urls(["https://x.com", "https://y.com"])
    assert is_batch is True and single is None and len(urls) == 2


def test_normalize_fetch_urls_empty_list_raises():
    with pytest.raises(BlopusError):
        C.normalize_fetch_urls([])


def test_chunking_over_50():
    urls = [f"https://x.com/{i}" for i in range(120)]
    chunks = C.chunk_urls(urls)
    assert len(chunks) == 3
    assert [len(c) for c in chunks] == [50, 50, 20]


@pytest.mark.parametrize(
    "status,code,exc",
    [
        (401, "unauthorized", AuthError),
        (403, "forbidden", AuthError),
        (402, "quota_exceeded", QuotaError),
        (429, "rate_limited", RateLimitError),
        (404, "not_found", NotFoundError),
        (400, "bad_request", BadRequestError),
        (413, "payload_too_large", BadRequestError),
        (503, "upstream_unavailable", ServerError),
        (500, "internal_error", ServerError),
    ],
)
def test_error_mapping(status, code, exc):
    err = error_from_response(status, {"error": {"code": code, "message": "x"}})
    assert isinstance(err, exc)
    assert err.code == code
    assert err.status == status


def test_error_mapping_by_status_only():
    err = error_from_response(429, None, retry_after=7)
    assert isinstance(err, RateLimitError)
    assert err.retry_after == 7


def test_should_retry():
    assert C.should_retry(429, 0, 2) is True
    assert C.should_retry(500, 0, 2) is True
    assert C.should_retry(400, 0, 2) is False
    assert C.should_retry(None, 0, 2) is True   # connection error
    assert C.should_retry(429, 2, 2) is False   # out of retries


def test_parse_retry_after():
    assert C.parse_retry_after("5") == 5
    assert C.parse_retry_after(None) is None
    assert C.parse_retry_after("garbage") is None
