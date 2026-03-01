"""
AI_SYNAPSE — Web Search Integration

Provides web search capability for research and current information.
Uses DuckDuckGo (no API key required).
"""

import logging
import re
import time
import urllib.parse
from typing import List, Optional
from dataclasses import dataclass

import httpx

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """Single search result."""
    title: str
    url: str
    snippet: str
    source: str


class WebSearch:
    """
    Async web search using DuckDuckGo.

    No API key required - uses DuckDuckGo's HTML endpoints.
    Results are cached with a configurable TTL.

    Example:
        search = WebSearch()
        results = await search.search("Python 3.12 new features")
        for r in results:
            print(f"{r.title}: {r.url}")
    """

    CACHE_TTL = 300  # 5 minutes

    def __init__(self):
        self.base_url = "https://duckduckgo.com/html/"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        self._client: Optional[httpx.AsyncClient] = None
        self._cache: dict[str, tuple[float, List[SearchResult]]] = {}

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(headers=self.headers, timeout=10.0)
        return self._client

    def _cache_get(self, key: str) -> Optional[List[SearchResult]]:
        entry = self._cache.get(key)
        if entry is None:
            return None
        ts, results = entry
        if time.monotonic() - ts > self.CACHE_TTL:
            del self._cache[key]
            return None
        return results

    def _cache_set(self, key: str, results: List[SearchResult]):
        self._cache[key] = (time.monotonic(), results)

    async def search(self, query: str, max_results: int = 5) -> List[SearchResult]:
        """
        Search the web asynchronously.

        Args:
            query: Search query
            max_results: Maximum results to return

        Returns:
            List of search results
        """
        cache_key = f"{query}:{max_results}"
        cached = self._cache_get(cache_key)
        if cached is not None:
            return cached

        try:
            # Try DuckDuckGo Lite first (faster, simpler)
            results = await self._search_ddg_lite(query, max_results)
            if results:
                self._cache_set(cache_key, results)
                return results

            # Fallback to scraping HTML
            results = await self._search_ddg_html(query, max_results)
            self._cache_set(cache_key, results)
            return results

        except Exception as e:
            logger.error(f"Web search failed: {e}")
            return []

    async def _search_ddg_lite(self, query: str, max_results: int) -> List[SearchResult]:
        """Search using DuckDuckGo Lite."""
        client = await self._get_client()
        encoded_query = urllib.parse.quote(query)
        url = f"https://lite.duckduckgo.com/lite/?q={encoded_query}"

        response = await client.get(url)
        html = response.text

        results = []

        # Parse results from HTML
        result_pattern = r'<a[^>]*class="[^"]*result-link[^"]*"[^>]*href="([^"]+)"[^>]*>(.*?)</a>'
        snippet_pattern = r'<td[^>]*class="result-snippet"[^>]*>(.*?)</td>'

        links = re.findall(result_pattern, html, re.DOTALL)
        snippets = re.findall(snippet_pattern, html, re.DOTALL)

        for i, (href, title) in enumerate(links[:max_results]):
            title = re.sub(r'<[^>]+>', '', title).strip()

            snippet = ""
            if i < len(snippets):
                snippet = re.sub(r'<[^>]+>', '', snippets[i]).strip()

            href = href.strip()
            if href.startswith('//'):
                href = 'https:' + href

            results.append(SearchResult(
                title=title,
                url=href,
                snippet=snippet,
                source="DuckDuckGo"
            ))

        return results

    async def _search_ddg_html(self, query: str, max_results: int) -> List[SearchResult]:
        """Fallback search using regular DuckDuckGo."""
        client = await self._get_client()
        encoded_query = urllib.parse.quote(query)
        url = f"https://duckduckgo.com/html/?q={encoded_query}"

        response = await client.get(url)
        html = response.text

        results = []

        pattern = r'<a[^>]*class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>.*?<a[^>]*class="result__snippet"[^>]*>(.*?)</a>'
        matches = re.findall(pattern, html, re.DOTALL)

        for href, title, snippet in matches[:max_results]:
            title = re.sub(r'<[^>]+>', '', title).strip()
            snippet = re.sub(r'<[^>]+>', '', snippet).strip()

            results.append(SearchResult(
                title=title,
                url=href,
                snippet=snippet,
                source="DuckDuckGo"
            ))

        return results

    def format_results(self, results: List[SearchResult]) -> str:
        """Format search results as text."""
        if not results:
            return "No results found."

        lines = [f"Found {len(results)} results:\n"]

        for i, result in enumerate(results, 1):
            lines.append(f"{i}. {result.title}")
            lines.append(f"   URL: {result.url}")
            if result.snippet:
                lines.append(f"   {result.snippet[:200]}...")
            lines.append("")

        return "\n".join(lines)


# Simple test
if __name__ == "__main__":
    import asyncio

    async def main():
        search = WebSearch()
        results = await search.search("Python 3.12 new features", max_results=3)
        print(search.format_results(results))

    asyncio.run(main())
