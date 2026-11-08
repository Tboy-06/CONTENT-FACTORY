from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

import httpx
from backend.config import get_settings

settings = get_settings()


class YouTubeAPI:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.youtube_api_key
        self.base_url = "https://www.googleapis.com/youtube/v3"
        self.client = httpx.AsyncClient(timeout=30.0)

    async def search(
        self,
        query: str,
        max_results: int = 10,
        order: str = "viewCount",
        published_after: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not self.api_key:
            return {"videos": [], "error": "No YouTube API key configured"}

        params = {
            "part": "snippet",
            "q": query,
            "type": "video",
            "maxResults": min(max_results, 50),
            "order": order,
            "key": self.api_key,
        }
        if published_after:
            params["publishedAfter"] = published_after

        resp = await self.client.get(f"{self.base_url}/search", params=params)
        resp.raise_for_status()
        data = resp.json()

        videos = []
        for item in data.get("items", []):
            vid = item["id"]["videoId"]
            snippet = item["snippet"]
            videos.append({
                "video_id": vid,
                "title": snippet["title"],
                "description": snippet["description"][:500],
                "channel_id": snippet["channelId"],
                "channel": snippet["channelTitle"],
                "published_at": snippet["publishedAt"],
                "thumbnails": snippet["thumbnails"],
                "url": f"https://www.youtube.com/watch?v={vid}",
            })

        return {"videos": videos, "total_results": data.get("pageInfo", {}).get("totalResults", 0)}

    async def get_video_details(self, video_ids: List[str]) -> List[Dict[str, Any]]:
        if not self.api_key or not video_ids:
            return []

        params = {
            "part": "snippet,statistics,contentDetails",
            "id": ",".join(video_ids[:50]),
            "key": self.api_key,
        }
        resp = await self.client.get(f"{self.base_url}/videos", params=params)
        resp.raise_for_status()
        data = resp.json()

        results = []
        for item in data.get("items", []):
            stats = item.get("statistics", {})
            results.append({
                "video_id": item["id"],
                "title": item["snippet"]["title"],
                "view_count": int(stats.get("viewCount", 0)),
                "like_count": int(stats.get("likeCount", 0)),
                "comment_count": int(stats.get("commentCount", 0)),
                "duration": item["contentDetails"]["duration"],
            })
        return results

    async def get_channel_videos(self, channel_id: str, max_results: int = 10) -> List[Dict[str, Any]]:
        # Get uploads playlist
        params = {"part": "contentDetails", "id": channel_id, "key": self.api_key}
        resp = await self.client.get(f"{self.base_url}/channels", params=params)
        resp.raise_for_status()
        data = resp.json()
        if not data.get("items"):
            return []

        uploads_playlist = data["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]

        # Get videos from uploads playlist
        params = {"part": "snippet", "playlistId": uploads_playlist, "maxResults": max_results, "key": self.api_key}
        resp = await self.client.get(f"{self.base_url}/playlistItems", params=params)
        resp.raise_for_status()
        data = resp.json()

        videos = []
        for item in data.get("items", []):
            snippet = item["snippet"]
            vid = snippet["resourceId"]["videoId"]
            videos.append({
                "video_id": vid,
                "title": snippet["title"],
                "description": snippet["description"][:500],
                "published_at": snippet["publishedAt"],
                "url": f"https://www.youtube.com/watch?v={vid}",
            })
        return videos

    async def close(self):
        await self.client.aclose()


_youtube_api: Optional[YouTubeAPI] = None


def get_youtube_api() -> YouTubeAPI:
    global _youtube_api
    if _youtube_api is None:
        _youtube_api = YouTubeAPI()
    return _youtube_api