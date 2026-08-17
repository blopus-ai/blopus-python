"""CrewAI adapter: ``blopus.crewai.BlopusSearchTool`` — a CrewAI ``BaseTool``.

Requires the optional ``crewai`` dependency::

    pip install "blopus[crewai]"

Usage::

    from blopus.crewai import BlopusSearchTool
    tool = BlopusSearchTool(api_key="blp_live_...")
    agent = Agent(role="researcher", tools=[tool], ...)
"""
from __future__ import annotations

from typing import Optional

from .client import Blopus


def _requirements():
    try:
        from crewai.tools import BaseTool  # type: ignore
        from pydantic import BaseModel, Field  # type: ignore
    except Exception as exc:  # pragma: no cover - optional dep
        raise ImportError(
            "BlopusSearchTool requires crewai. Install with: pip install 'blopus[crewai]'"
        ) from exc
    return BaseTool, BaseModel, Field


def BlopusSearchTool(
    api_key: Optional[str] = None,
    *,
    client: Optional[Blopus] = None,
    count: int = 10,
    freshness: str = "all",
    news_only: bool = False,
    **search_kwargs,
):
    """Return a CrewAI ``BaseTool`` backed by ``Blopus.search``.

    ``news_only`` and any other :meth:`Blopus.search` keyword are accepted so this
    adapter is not the odd one out — the LangChain and LlamaIndex wrappers already
    take them, and a parameter missing from one framework's wrapper is a parameter
    that framework's users cannot reach.
    """
    BaseTool, BaseModel, Field = _requirements()
    _client = client or Blopus(api_key=api_key)

    class _Schema(BaseModel):
        query: str = Field(..., description="The search query.")

    class _BlopusSearchTool(BaseTool):
        name: str = "Blopus Web Search"
        description: str = (
            "Search the web with Blopus for current events, facts, and pages to read. "
            "Input is a query string; returns ranked titles, URLs and snippets."
        )
        args_schema: type = _Schema

        def _run(self, query: str) -> str:
            res = _client.search(query, count=count, freshness=freshness,
                                 news_only=news_only, **search_kwargs)
            if not res.results:
                return "No results."
            return "\n".join(
                f"{i}. {r.title}\n   {r.url}\n   {r.snippet}"
                for i, r in enumerate(res.results, 1)
            )

    return _BlopusSearchTool()
