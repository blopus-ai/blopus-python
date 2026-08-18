# Topic filters

Blopus indexes every page with the subject areas its publication covers. `topics` and
`exclude_topics` let you scope a search to — or away from — those areas.

**[→ Browse the full vocabulary](https://blopus.ai/docs/topics)** · **[API reference](https://blopus.ai/docs/#topics-endpoint)**

```python
from blopus import Blopus
client = Blopus()

# Only results from publications that cover cybersecurity
client.search("data breach", topics=["cybersecurity"])

# Everything except sports publications
client.search("transfer window", exclude_topics=["sports"])

# What can I filter on? (free — this call is not billed)
for t in client.topics(min_docs=100000):
    print(t.topic, t.documents)
```

---

## What this actually does — and what it does not

We measured before writing this, so here is the honest version.

**What it gives you: a guarantee.** Without a topic filter, most of your results come from
publications outside the domain you care about. With one, all of them are inside it.

| query | on-topic sources, unscoped | with `topics` |
|---|---|---|
| `data breach` → `cybersecurity` | ~3 of 10 | **10 of 10** |
| `model training` → `ai` | ~4 of 10 | **10 of 10** |
| `clinical trial` → `health` | ~0 of 10 | **10 of 10** |
| `interest rates` → `economy` | ~2 of 10 | **10 of 10** |
| `open source` → `software` | ~1 of 10 | **10 of 10** |

*The unscoped column is a lower-bound estimate from source overlap, not an exact count.*

**What it does NOT do: make results "better".** We measured median body length and the rate
of listing/index pages across four query pairs and found no improvement — on two queries
median length went *down*. Latency was 6% faster in the same run, which is close to noise.

So this is a **corpus control** feature, not a relevance boost. That distinction matters,
because it tells you when to reach for it.

---

## When it earns its place

**RAG over an auditable source set.** If you have to defend where an answer came from,
"every document came from a publication covering clinical medicine" is a far better
position than "the search engine chose these ten".

**De-noising a query that collides with another domain.** `transfer window` means one thing
in football and another in immigration policy. `exclude_topics=["sports"]` separates them
without you having to blocklist domains by hand.

**Domain-scoped monitoring.** A daily sweep of `topics=["cybersecurity"]` returns a stable
corpus, so a change in results reflects the news rather than a change in ranking.

**Where NOT to use it:** as a substitute for a good query. `topics=["ai"]` does not mean
"pages about AI" — see the limitation below. Put the subject in the query; use topics to
scope the corpus around it.

---

## The limitation, stated plainly

**A topic describes what a PUBLICATION covers, not what an individual article is about.**

A local newspaper tagged `general_news, local_news, politics, business, community` will
publish the occasional football story. That story is invisible to
`exclude_topics=["sports"]`, because its *publisher* is not a sports publication. Meanwhile a
dedicated football site tagged `sports, football` is excluded correctly.

We are not going to pretend otherwise: source-level tagging is what makes this feature cheap
and instant, and per-article classification is a different product with a different cost.
If you need "no sports *stories*", combine `exclude_topics` with query terms.

---

## Practical notes

- **`topics()` is free.** It is not billed. Fetch it once at startup and cache it.
- **Values are matched exactly.** An unknown topic returns **zero** results rather than
  silently widening your search. That is deliberate — a filter that quietly ignores you is
  worse than one that returns nothing. Do not guess; use the vocabulary.
- **Case and separators are forgiving.** `cybersecurity`, `CyberSecurity`, `pc_gaming` and
  `PC gaming` all work. Published names are `lower_snake_case`.
- **`min_docs` trims the tail.** The default of `1000` hides labels too small to be useful.
- **Multiple topics are OR.** `topics=["ai","software"]` means either, not both.

## Availability

| | |
|---|---|
| REST | `topics`, `exclude_topics` on `POST /v1/search`; `GET /v1/topics` |
| Python | `blopus>=0.5.0` — `search(topics=[...])`, `client.topics()`, `blopus topics` |
| TypeScript | `blopus>=0.5.0` — `search({topics})`, `client.topics()`, `blopus topics` |
| LangChain | `langchain-blopus>=0.3.0` — tool and retriever |
| LlamaIndex | `llama-index-tools-blopus>=0.3.0` |
| MCP | `topics` / `exclude_topics` on `search`, a `blopus_topics` tool, and runtime hints |

---

## If you are calling this from an LLM

The MCP surface does three things so a model does not have to guess:

- the **40 most-used topics are listed inline** on the `search` tool, so common cases need no
  extra call;
- **`blopus_topics`** returns the full list on demand, and costs nothing;
- when a search returns results dominated by one subject area and no filter was set, the
  response carries a hint naming that topic — e.g. *"6 of these 10 results come from
  publications covering 'crypto'"* — so the model can scope or exclude deliberately rather
  than silently inheriting a slant.

If a topic filter matches nothing, the response says so explicitly and points at
`blopus_topics`, because zero results from a typo look exactly like zero results from reality.
