"""LangChain adapter: ``blopus.langchain.BlopusSearch`` — a LangChain ``Tool``.

Requires the optional ``langchain-core`` dependency::

    pip install "blopus[langchain]"

Usage::

    from blopus.langchain import BlopusSearch
    tool = BlopusSearch(api_key="blp_live_...")   # or BLOPUS_API_KEY
    agent = create_react_agent(llm, [tool])
"""
from __future__ import annotations

from typing import Any, Optional

from .client import Blopus


def _require_langchain():
    try:
        from langchain_core.tools import Tool  # type: ignore
    except Exception as exc:  # pragma: no cover - optional dep
        raise ImportError(
            "BlopusSearch requires langchain-core. Install with: pip install 'blopus[langchain]'"
        ) from exc
    return Tool


def _format(res) -> str:
    lines = []
    for i, r in enumerate(res.results, 1):
        lines.append(f"{i}. {r.title}\n   {r.url}\n   {r.snippet}")
    return "\n".join(lines) if lines else "No results."


def BlopusSearch(
    api_key: Optional[str] = None,
    *,
    client: Optional[Blopus] = None,
    count: int = 10,
    freshness: str = "all",
    name: str = "blopus_search",
    description: str = (
        "Search the web with Blopus. Input is a search query string. "
        "Returns ranked titles, URLs and snippets. Use for current events, "
        "facts, and finding pages to read."
    ),
    news_only: bool = False,
    **search_kwargs: Any,
):
    """Build a LangChain ``Tool`` backed by ``Blopus.search``."""
    Tool = _require_langchain()
    _client = client or Blopus(api_key=api_key)

    def _run(query: str) -> str:
        res = _client.search(query, count=count, freshness=freshness,
                             news_only=news_only, **search_kwargs)
        return _format(res)

    return Tool(name=name, description=description, func=_run)
