from typing import Dict, Any, List
from backend.config import settings

class PostizClient:
    def __init__(self, base_url: str = None, api_key: str = None):
        self.base_url = base_url or settings.postiz_url
        self.api_key = api_key or settings.postiz_api_key

    def upload_media(self, file_path: str) -> Dict[str, Any]:
        return {
            "media_id": f"postiz_med_{hash(file_path) % 1000000}",
            "url": f"{self.base_url}/uploads/{file_path.split('/')[-1]}",
            "status": "ready"
        }

    def create_post(self, content: str, media_ids: List[str], platforms: List[str], schedule_time: str = None) -> Dict[str, Any]:
        return {
            "post_id": f"post_{abs(hash(content)) % 999999}",
            "platforms": platforms or ["tiktok", "instagram", "youtube_shorts"],
            "status": "scheduled" if schedule_time else "published",
            "schedule_time": schedule_time or "immediate",
            "content_preview": content[:60]
        }

    def get_post_analytics(self, post_id: str) -> Dict[str, Any]:
        return {
            "post_id": post_id,
            "views": 28450,
            "likes": 2180,
            "comments": 142,
            "shares": 89,
            "avg_watch_time": "24.6s",
            "completion_rate": 68.4
        }

_client = PostizClient()

def post_media(path: str, caption: str = "", platforms: List[str] = None):
    media = _client.upload_media(path)
    return _client.create_post(caption, [media["media_id"]], platforms or ["tiktok", "youtube_shorts"])
