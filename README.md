# blopus — Python SDK

Official Python client for the [Blopus](https://blopus.ai) web search + fetch API.
Blopus is a cheap, fast web-search API backed by an owned index — built for bots
and agents.

The SDK talks to exactly two data-plane endpoints: `POST /v1/search` and
`POST /v1/fetch` on `https://api.blopus.ai`.



### Topic filters

> **[Full guide: TOPICS.md](TOPICS.md)** — what topic filtering does and does not do, measured. Browse the vocabulary at [blopus.ai/docs/topics](https://blopus.ai/docs/topics).


```python
# what can I filter on?
for t in client.topics(min_docs=100000)[:10]:
    print(t.topic, t.documents)

res = client.search("data breach", topics=["cybersecurity"])
res = client.search("world cup", exclude_topics=["sports"])   # de-noise
```

`client.topics()` is free. Topics are matched **exactly**, so an unknown value returns zero
results rather than silently widening the search — call `topics()` instead of guessing.

A topic describes what a **publication** covers, not what an individual article is about:
`topics=["ai"]` means "pages from AI-focused sites", which is broader than "pages about AI".

### Images

Ask for a hero image URL per result:

```python
res = client.search("tesla factory", include_images=True)
for r in res.results:
    if r.image:                      # None is normal — coverage is partial
        print(r.title, r.image, f"{r.image_w}x{r.image_h}")
```

Off by default because it costs roughly 295 tokens per 10 results. Never promise a user a
picture before you have a non-null URL in hand.

### Filtering out stubs

Every result carries `word_count`, so you can see that a hit is a stub before reading it.
`min_words` turns that into a filter:

```python
res = client.search("how does raft consensus work", min_words=120)
```

Use it when the user wants something to READ. Leave it off for breaking news, where a
two-line wire story is a legitimate answer.

## Install

```bash
pip install blopus
```

Optional framework adapters:

```bash
pip install "blopus[langchain]"     # blopus.langchain.BlopusSearch
pip install "blopus[llamaindex]"    # blopus.llamaindex.BlopusToolSpec
pip install "blopus[crewai]"        # blopus.crewai.BlopusSearchTool
```

## News scoping (`news_only`)

Set `news_only=True` when the question is about **events** — what happened, who
announced what, market reaction, election results, earnings news. It searches only
sources with a real newsroom, over a **dedicated news channel** that is **faster**
than an unscoped search, and it drops the vendor blogs, marketing pages and
documentation that otherwise crowd news results.

```python
# events → scope it, and pair with a freshness window
client.search("what did the Fed announce", freshness="pd", news_only=True)

# documentation / reference → leave it off
client.search("kubernetes ingress example")

# wants both the announcement AND the changelog → leave it off
client.search("what's new in Python 3.14")
```

Omitting it searches everything, so leaving it off is always the safe choice.

## Authentication

Pass an API key (`blp_live_...`) directly, or set `BLOPUS_API_KEY`:

```bash
export BLOPUS_API_KEY="blp_live_xxx"
```

## Quickstart

```python
from blopus import Blopus

client = Blopus()  # reads BLOPUS_API_KEY

res = client.search("who won the game last night", count=5, freshness="pd", news_only=True)
for hit in res:
    print(hit.score, hit.title, hit.url)
print("remaining quota:", res.remaining_quota)

# Fetch indexed page content
doc = client.fetch("https://example.com/article")
print(doc.title, len(doc.content))
```

### Async

```python
import asyncio
from blopus import AsyncBlopus

async def main():
    async with AsyncBlopus() as client:
        res = await client.search("openai news", freshness="pw")
        docs = await client.fetch([r.url for r in res])  # batch fetch
        print(docs.count, "fetched,", len(docs.failed_results), "missing")

asyncio.run(main())
```

## `search(...)`

```python
client.search(
    query,
    count=10,                 # 1..50
    freshness="all",          # pd | pw | pm | p3m | p1y | all
    news_only=False,          # True = newsroom sources only. Faster dedicated news channel;
                              # drops vendor blogs/docs. Use it for events; leave it off for
                              # documentation, tutorials, forums — or when you want both.
    include_domains=None,     # ["techcrunch.com", ...]
    exclude_domains=None,
    start_date=None,          # "YYYY-MM-DD" or epoch seconds
    end_date=None,
    language=None,            # "en", "pt", ...
    offset=0,                 # pagination, up to 200
    include_excerpt=False,    # opt in to longer excerpts
    excerpt_chars=None,       # up to 1200
)
```

Returns a `SearchResponse` (iterable over `SearchResult`):

```python
res.query            # echoed query
res.results          # list[SearchResult]
res.count            # number of results returned
res.offset
res.more_results     # bool — more pages available
res.remaining_quota  # int — your remaining monthly units

# SearchResult fields:
# title, url, snippet, domain, site_name, favicon,
# published_at, age_seconds, language, score
```

Search always costs **1 credit**, regardless of parameters or excerpt size.

## `fetch(url_or_urls)`

```python
# single URL -> FetchResult
doc = client.fetch("https://example.com/a")
doc.url, doc.canonical_url, doc.title, doc.content, doc.domain, doc.published_at, doc.language, doc.found

# list of URLs -> BatchFetchResponse
batch = client.fetch(["https://a.com", "https://b.com"])
batch.results          # list[FetchResult] that were found
batch.failed_results   # list[FetchFailure] (url, found=False)
batch.count            # number found (== credits billed)
batch.remaining_quota
```

Batches over the server cap of **50 URLs** are automatically split into ≤50-URL
calls, run sequentially with a small delay, and merged for you. Fetch bills per
document found.

## Errors

All errors subclass `blopus.BlopusError`:

| Exception            | When                                   |
|----------------------|----------------------------------------|
| `AuthError`          | 401 / 403 — bad, missing or revoked key |
| `QuotaError`         | 402 — monthly quota exhausted           |
| `RateLimitError`     | 429 — slow down (`.retry_after`)        |
| `NotFoundError`      | 404 — no indexed content for a URL      |
| `BadRequestError`    | 400 / 413 — malformed / too large       |
| `ServerError`        | 5xx — gateway/backend problem           |
| `APIConnectionError` | network failure (no response)           |

Requests to `429`/`5xx`/connection errors are retried with exponential backoff
(honoring `Retry-After`); tune with `Blopus(max_retries=...)`.

## MCP

Blopus also exposes a hosted MCP server (`search` + `fetch` tools) at
`https://mcp.blopus.ai`, using the same Bearer auth.

```python
from blopus import mcp_config, print_mcp_config
print_mcp_config()        # prints the mcpServers JSON to paste into your MCP client
cfg = mcp_config()        # or get it as a dict
```

## CLI

```bash
blopus search "who won the game" --count 5 --freshness pd --news-only
blopus search "openai" --include-domains techcrunch.com,theverge.com --json
blopus fetch https://example.com/a https://example.com/b
blopus mcp-config
```

## License

MIT
