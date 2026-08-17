"""LlamaIndex adapter: ``blopus.llamaindex.BlopusToolSpec``.

Requires the optional ``llama-index-core`` dependency::

    pip install "blopus[llamaindex]"

Usage::

    from blopus.llamaindex import BlopusToolSpec
    tools = BlopusToolSpec(api_key="blp_live_...").to_tool_list()
    agent = FunctionAgent(tools=tools, llm=llm)

``BlopusToolSpec`` is a factory: it builds a subclass of LlamaIndex's
``BaseToolSpec`` lazily, so importing this module never hard-requires
llama-index (it is only needed when you actually construct the spec).
"""
from __future__ import annotations

from typing import List, Optional

from .client import Blopus


def _base_tool_spec():
    try:
        from llama_index.core.tools.tool_spec.base import BaseToolSpec  # type: ignore
    except Exception as exc:  # pragma: no cover - optional dep
        raise ImportError(
            "BlopusToolSpec requires llama-index-core. "
            "Install with: pip install 'blopus[llamaindex]'"
        ) from exc
    return BaseToolSpec


def BlopusToolSpec(
    api_key: Optional[str] = None,
    *,
    client: Optional[Blopus] = None,
    count: int = 10,
    freshness: str = "all",
    news_only: bool = False,
    **search_kwargs,
):
    """Return a LlamaIndex tool spec exposing Blopus ``search`` and ``fetch``.

    ``news_only=True`` restricts search to newsroom sources — faster, and free of
    vendor blogs and documentation. Use it for event-driven agents; leave it off
    for agents that also need docs or reference material.
    """
    BaseToolSpec = _base_tool_spec()
    _client = client or Blopus(api_key=api_key)

    class _BlopusToolSpec(BaseToolSpec):  # type: ignore[misc, valid-type]
        spec_functions = ["blopus_search", "blopus_fetch"]

        def blopus_search(self, query: str) -> List[dict]:
            """Search the web. Returns a list of {title, url, snippet, score} results."""
            res = _client.search(query, count=count, freshness=freshness,
                                 news_only=news_only, **search_kwargs)
            return [
                {"title": r.title, "url": r.url, "snippet": r.snippet, "score": r.score}
                for r in res.results
            ]

        def blopus_fetch(self, url: str) -> dict:
            """Fetch the indexed content of a single URL. Returns {url, title, content}."""
            doc = _client.fetch(url)
            return {
                "url": doc.url,
                "title": doc.title,
                "content": doc.content,
                "found": doc.found,
            }

    return _BlopusToolSpec()
