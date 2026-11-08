from __future__ import annotations

from typing import Any, Dict, List, Optional

import httpx
from backend.config import get_settings

settings = get_settings()


class WebSearcher:
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
        self.tavily_key = settings.tavily_api_key
        self.serpapi_key = settings.serpapi_key

    async def search_tavily(
        self,
        query: str,
        max_results: int = 10,
        search_depth: str = "basic",
        include_domains: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        if not self.tavily_key:
            return {"results": [], "error": "No Tavily API key"}

        payload = {
            "api_key": self.tavily_key,
            "query": query,
            "max_results": max_results,
            "search_depth": search_depth,
            "include_answer": True,
            "include_raw_content": False,
        }
        if include_domains:
            payload["include_domains"] = include_domains

        resp = await self.client.post("https://api.tavily.com/search", json=payload)
        resp.raise_for_status()
        data = resp.json()

        results = []
        for r in data.get("results", []):
            results.append({
                "title": r.get("title"),
                "url": r.get("url"),
                "content": r.get("content"),
                "score": r.get("score"),
            })

        return {
            "results": results,
            "answer": data.get("answer"),
            "query": data.get("query"),
        }

    async def search_serpapi(
        self,
        query: str,
        max_results: int = 10,
        engine: str = "google",
    ) -> Dict[str, Any]:
        if not self.serpapi_key:
            return {"results": [], "error": "No SerpAPI key"}

        params = {
            "api_key": self.serpapi_key,
            "q": query,
            "engine": engine,
            "num": max_results,
        }

        resp = await self.client.get("https://serpapi.com/search", params=params)
        resp.raise_for_status()
        data = resp.json()

        results = []
        for r in data.get("organic_results", []):
            results.append({
                "title": r.get("title"),
                "url": r.get("link"),
                "snippet": r.get("snippet"),
                "position": r.get("position"),
            })

        return {"results": results, "search_metadata": data.get("search_metadata")}

    async def search(
        self,
        query: str,
        max_results: int = 10,
        prefer: str = "tavily",
    ) -> Dict[str, Any]:
        if prefer == "tavily" and self.tavily_key:
            return await self.search_tavily(query, max_results)
        elif prefer == "serpapi" and self.serpapi_key:
            return await self.search_serpapi(query, max_results)
        elif self.tavily_key:
            return await self.search_tavily(query, max_results)
        elif self.serpapi_key:
            return await self.search_serpapi(query, max_results)
        else:
            return {"results": [], "error": "No search API keys configured"}

    async def search_reddit(self, query: str, max_results: int = 10) -> Dict[str, Any]:
        return await self.search_tavily(
            query=f"site:reddit.com {query}",
            max_results=max_results,
            include_domains=["reddit.com"],
        )

    async def search_github(self, query: str, max_results: int = 10) -> Dict[str, Any]:
        return await self.search_tavily(
            query=f"site:github.com {query}",
            max_results=max_results,
            include_domains=["github.com"],
        )

    async def close(self):
        await self.client.aclose()


_web_searcher: Optional[WebSearcher] = None


def get_web_searcher() -> WebSearcher:
    global _web_searcher
    if _web_searcher is None:
        _web_searcher = WebSearcher()
    return _web_searcher