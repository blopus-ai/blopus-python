# Changelog

## 0.5.0

### Added
- `topics` / `exclude_topics` on `search()` (sync, async, and CLI `--topics` /
  `--exclude-topics`). Narrow to — or away from — whole subject areas.
- `client.topics(min_docs=1000)` and CLI `blopus topics`, returning the vocabulary you may
  pass. **Not billed.** Topics are matched exactly, so an unknown value returns zero results;
  without a published vocabulary that is indistinguishable from a genuine no-match.
- `Topic` model.

### Note
A topic describes what a **publication** covers, not what an individual article is about:
`topics=["ai"]` means "pages from AI-focused sites", which is broader and coarser than
"pages about AI". Use it to scope or de-noise a search, not as a substitute for the query.


## 0.4.0

### Added
- `include_images` on `search()` (sync, async and CLI `--include-images`). Returns a hero
  image URL per result. Off by default: it costs roughly 295 tokens per 10 results, which
  matters when the caller is a language model. Coverage is partial, so `result.image` is
  `None` on plenty of hits — always check before using it.
- `SearchResult.image`, `.image_w`, `.image_h`.
- `SearchResult.word_count`, returned on every result whether or not you filter on it, so a
  40-word stub is visible before you read it.
- CLI `--min-words`, which the library supported but the CLI never exposed.


## 0.3.5

- Add `min_words` to `search()` (sync and async). Only return results whose body has at least
  that many words. The engine has always supported it; it was simply never exposed. Measured
  10.2% of the news index and 17.3% of the rest index are under 120 words, and a caller could
  not otherwise exclude them.

## 0.3.4

- Point `Documentation` at https://blopus.ai/docs/. The previous URL did not resolve.
- Publish the source, so the `Source` link on PyPI resolves.
- Version bump also refreshes the User-Agent sent by the client.

## 0.3.3

- Search and fetch clients, sync and async, with CLI and MCP config helpers.
- Optional adapters for LangChain, LlamaIndex and CrewAI.
