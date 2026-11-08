from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

import httpx


class PostizClient:
    def __init__(self):
        self.base_url = os.getenv("POSTIZ_URL", "http://localhost:3000").rstrip("/")
        self.api_key = os.getenv("POSTIZ_API_KEY", "")
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=60.0,
            )
        return self._client

    async def create_post(
        self,
        account_id: str,
        content: str,
        media_paths: List[str],
        media_type: str = "video",
    ) -> Dict[str, Any]:
        client = await self._get_client()

        media_ids = []
        for path in media_paths:
            if not os.path.exists(path):
                raise FileNotFoundError(f"Media not found: {path}")

            with open(path, "rb") as f:
                files = {"file": (os.path.basename(path), f, self._get_mime_type(path))}
                resp = await client.post("/api/v1/media/upload", files=files)
                resp.raise_for_status()
                media_ids.append(resp.json()["id"])

        payload = {
            "accountId": account_id,
            "content": content,
            "mediaIds": media_ids,
        }

        resp = await client.post("/api/v1/posts", json=payload)
        resp.raise_for_status()
        return resp.json()

    async def schedule_post(
        self,
        account_id: str,
        content: str,
        media_paths: List[str],
        scheduled_at: str,
        media_type: str = "video",
    ) -> Dict[str, Any]:
        client = await self._get_client()

        media_ids = []
        for path in media_paths:
            if not os.path.exists(path):
                raise FileNotFoundError(f"Media not found: {path}")

            with open(path, "rb") as f:
                files = {"file": (os.path.basename(path), f, self._get_mime_type(path))}
                resp = await client.post("/api/v1/media/upload", files=files)
                resp.raise_for_status()
                media_ids.append(resp.json()["id"])

        payload = {
            "accountId": account_id,
            "content": content,
            "mediaIds": media_ids,
            "scheduledAt": scheduled_at,
        }

        resp = await client.post("/api/v1/posts/schedule", json=payload)
        resp.raise_for_status()
        return resp.json()

    async def get_accounts(self) -> List[Dict[str, Any]]:
        client = await self._get_client()
        resp = await client.get("/api/v1/accounts")
        resp.raise_for_status()
        return resp.json()

    async def get_post(self, post_id: str) -> Dict[str, Any]:
        client = await self._get_client()
        resp = await client.get(f"/api/v1/posts/{post_id}")
        resp.raise_for_status()
        return resp.json()

    async def get_analytics(self, account_id: str, days: int = 30) -> Dict[str, Any]:
        client = await self._get_client()
        resp = await client.get(f"/api/v1/analytics/{account_id}", params={"days": days})
        resp.raise_for_status()
        return resp.json()

    def _get_mime_type(self, path: str) -> str:
        ext = os.path.splitext(path)[1].lower()
        return {
            ".mp4": "video/mp4",
            ".mov": "video/quicktime",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".webp": "image/webp",
        }.get(ext, "application/octet-stream")

    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None