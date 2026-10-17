"""
Web search tool using DuckDuckGo (via ddgs / duckduckgo_search).
Requires no API key and provides real-time search results.
"""

from typing import Any, Dict
from aria.tools.base import BaseTool


class WebSearchTool(BaseTool):
    name = "web_search"
    description = (
        "Search the web for up-to-date information, news, papers, and articles on any query. "
        "Returns titles, snippets, and URLs."
    )
    parameters = {
        "query": {
            "type": "string",
            "description": "The search query to look up on the web.",
        },
        "max_results": {
            "type": "integer",
            "description": "Number of results to retrieve (default: 5, max: 10).",
        },
    }

    def execute(self, **kwargs) -> str:
        query = kwargs.get("query")
        if not query:
            return "Error: 'query' parameter is required for web_search."

        max_results = kwargs.get("max_results", 5)
        try:
            max_results = min(int(max_results), 10)
        except (ValueError, TypeError):
            max_results = 5

        # Try importing ddgs first, fallback to duckduckgo_search
        DDGS_Class = None
        try:
            from ddgs import DDGS
            DDGS_Class = DDGS
        except ImportError:
            try:
                from duckduckgo_search import DDGS
                DDGS_Class = DDGS
            except ImportError:
                return "Error: Neither 'ddgs' nor 'duckduckgo_search' is installed."

        try:
            with DDGS_Class() as ddgs:
                results = list(ddgs.text(query, max_results=max_results))

            if not results:
                return f"No web search results found for query: '{query}'."

            formatted_output = [f"Web search results for: '{query}' (Found {len(results)}):\n"]
            for i, r in enumerate(results, start=1):
                title = r.get("title", "Untitled")
                snippet = r.get("body", "No description available.")
                url = r.get("href", "")
                formatted_output.append(f"[{i}] {title}\n    Snippet: {snippet}\n    URL: {url}")

            return "\n\n".join(formatted_output)

        except Exception as e:
            return f"Error executing web search for '{query}': {str(e)}"
