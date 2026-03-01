"""
AI_SYNAPSE — Web Search Integration

Provides web search capability for research and current information.
Uses DuckDuckGo (no API key required).
"""

import logging
from typing import List, Dict, Optional
from dataclasses import dataclass
import urllib.request
import urllib.parse
import json
import re

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
    Web search using DuckDuckGo.
    
    No API key required - uses DuckDuckGo's instant answer API.
    
    Example:
        search = WebSearch()
        results = search.search("Python 3.12 new features")
        for r in results:
            print(f"{r.title}: {r.url}")
    """
    
    def __init__(self):
        self.base_url = "https://duckduckgo.com/html/"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
    
    def search(self, query: str, max_results: int = 5) -> List[SearchResult]:
        """
        Search the web.
        
        Args:
            query: Search query
            max_results: Maximum results to return
            
        Returns:
            List of search results
        """
        try:
            # Try DuckDuckGo Lite first (faster, simpler)
            results = self._search_ddg_lite(query, max_results)
            if results:
                return results
            
            # Fallback to scraping HTML
            return self._search_ddg_html(query, max_results)
            
        except Exception as e:
            logger.error(f"Web search failed: {e}")
            return []
    
    def _search_ddg_lite(self, query: str, max_results: int) -> List[SearchResult]:
        """Search using DuckDuckGo Lite."""
        import urllib.request
        import urllib.parse
        
        encoded_query = urllib.parse.quote(query)
        url = f"https://lite.duckduckgo.com/lite/?q={encoded_query}"
        
        req = urllib.request.Request(
            url,
            headers=self.headers,
            method='GET'
        )
        
        with urllib.request.urlopen(req, timeout=10) as response:
            html = response.read().decode('utf-8')
        
        results = []
        
        # Parse results from HTML
        # Look for result links and snippets
        import re
        
        # Find result blocks
        result_pattern = r'<a[^>]*class="[^"]*result-link[^"]*"[^>]*href="([^"]+)"[^>]*>(.*?)</a>'
        snippet_pattern = r'<td[^>]*class="result-snippet"[^>]*>(.*?)</td>'
        
        links = re.findall(result_pattern, html, re.DOTALL)
        snippets = re.findall(snippet_pattern, html, re.DOTALL)
        
        for i, (href, title) in enumerate(links[:max_results]):
            # Clean up title
            title = re.sub(r'<[^>]+>', '', title).strip()
            
            # Get snippet if available
            snippet = ""
            if i < len(snippets):
                snippet = re.sub(r'<[^>]+>', '', snippets[i]).strip()
            
            # Clean URL
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
    
    def _search_ddg_html(self, query: str, max_results: int) -> List[SearchResult]:
        """Fallback search using regular DuckDuckGo."""
        import urllib.request
        import urllib.parse
        
        encoded_query = urllib.parse.quote(query)
        url = f"https://duckduckgo.com/html/?q={encoded_query}"
        
        req = urllib.request.Request(
            url,
            headers=self.headers,
            method='GET'
        )
        
        with urllib.request.urlopen(req, timeout=10) as response:
            html = response.read().decode('utf-8')
        
        results = []
        import re
        
        # Look for result blocks
        # Pattern: result link with title and snippet
        pattern = r'<a[^>]*class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>.*?<a[^>]*class="result__snippet"[^>]*>(.*?)</a>'
        matches = re.findall(pattern, html, re.DOTALL)
        
        for href, title, snippet in matches[:max_results]:
            # Clean up HTML
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
    search = WebSearch()
    results = search.search("Python 3.12 new features", max_results=3)
    print(search.format_results(results))
