"""Search client abstraction for ResearcherAgent."""

from typing import Any

import httpx

from multi_agent_research_lab.core.config import get_settings
from multi_agent_research_lab.core.schemas import SourceDocument


class SearchClient:
    """Provider-agnostic search client.

    If `TAVILY_API_KEY` is set, this client calls Tavily Search. If the key is
    missing or the request fails, it falls back to deterministic mock documents
    so the lab remains runnable.
    """

    def search(self, query: str, max_results: int = 5) -> list[SourceDocument]:
        """Search for documents relevant to a query."""

        settings = get_settings()
        if not settings.tavily_api_key:
            return self._mock_search(query, max_results, reason="missing_tavily_api_key")

        try:
            response = httpx.post(
                "https://api.tavily.com/search",
                headers={
                    "Authorization": f"Bearer {settings.tavily_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "query": query,
                    "search_depth": "basic",
                    "max_results": max_results,
                    "include_answer": False,
                    "include_raw_content": False,
                },
                timeout=settings.timeout_seconds,
            )
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            return self._mock_search(query, max_results, reason=f"tavily_error:{exc}")

        results = payload.get("results", [])
        if not isinstance(results, list) or not results:
            return self._mock_search(query, max_results, reason="empty_tavily_results")

        documents: list[SourceDocument] = []
        for index, item in enumerate(results[:max_results], start=1):
            if not isinstance(item, dict):
                continue
            documents.append(self._source_from_tavily_item(index, item))

        return documents or self._mock_search(query, max_results, reason="invalid_tavily_results")

    def _source_from_tavily_item(self, index: int, item: dict[str, Any]) -> SourceDocument:
        title = str(item.get("title") or f"Tavily result {index}")
        url = item.get("url")
        content = item.get("content") or item.get("raw_content") or ""
        return SourceDocument(
            title=title,
            url=str(url) if url else None,
            snippet=str(content)[:1000],
            metadata={
                "rank": index,
                "provider": "tavily",
                "score": item.get("score"),
                "favicon": item.get("favicon"),
            },
        )

    def _mock_search(self, query: str, max_results: int, reason: str) -> list[SourceDocument]:
        topics = [
            "background and definitions",
            "current approaches",
            "trade-offs and risks",
            "practical implementation guidance",
            "evaluation criteria",
        ]
        return [
            SourceDocument(
                title=f"Mock source {index}: {topic.title()}",
                url=f"https://example.com/mock-source-{index}",
                snippet=(
                    f"This mock source discusses {topic} for the query '{query}'. "
                    "It is deterministic fallback data, not live web evidence."
                ),
                metadata={"rank": index, "provider": "mock", "fallback_reason": reason},
            )
            for index, topic in enumerate(topics[:max_results], start=1)
        ]
