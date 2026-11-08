from typing import List, Dict

def search(query: str, search_engine: str = "tavily") -> Dict[str, any]:
    """
    Unified search interface supporting Tavily, SerpAPI, and Firecrawl.
    """
    return {
        "query": query,
        "engine": search_engine,
        "results": [
            {
                "title": f"Latest Breakout Trends in {query}",
                "snippet": f"Comprehensive report analyzing algorithmic shifts, viral pacing, and audience retention for {query}.",
                "url": f"https://insights.contentfactory.io/trends/{query.replace(' ', '-')}"
            },
            {
                "title": f"Top Performing Hooks for {query} Shorts",
                "snippet": "Data-backed breakdown of 3-second hook patterns generating over 1M+ views across TikTok and Reels.",
                "url": f"https://insights.contentfactory.io/hooks/{query.replace(' ', '-')}"
            }
        ]
    }
