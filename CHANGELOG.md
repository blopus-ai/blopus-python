# Changelog

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
