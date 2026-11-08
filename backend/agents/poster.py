from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx

from backend.agents.base import AgentResult, Job as AgentJob, BaseAgent
from backend.agents.llm_client import get_gemini_client
from backend.config import get_settings
from backend.tools.postiz_client import PostizClient
from backend.vault.repository import (
    get_job,
    update_job_status,
    add_asset,
    update_job_config,
    get_job_assets,
)
from backend.vault.models import JobStatus

settings = get_settings()


@dataclass
class PostConfig:
    platform: str
    account_id: str
    caption: str
    media_path: str
    media_type: str
    scheduled_at: Optional[datetime] = None
    tags: Optional[List[str]] = None


@dataclass
class PostResult:
    platform: str
    post_id: Optional[str]
    url: Optional[str]
    success: bool
    error: Optional[str] = None


class PosterAgent(BaseAgent):
    name = "poster"
    description = "Posts finalized content to social platforms via Postiz"

    def __init__(self):
        super().__init__(agent_id="poster")
        self.postiz = PostizClient()
        self.llm = get_gemini_client()

    async def _create_llm_client(self):
        return self.llm

    async def _run_impl(self, job: AgentJob, context: Dict[str, Any]) -> AgentResult:
        db_job = await get_job(job.id)
        if not db_job:
            return AgentResult(success=False, error="Job not found in DB")

        assets = await get_job_assets(job.id)
        video_assets = [a for a in assets if a.asset_type == "video"]
        image_assets = [a for a in assets if a.asset_type == "image"]

        if not video_assets and not image_assets:
            return AgentResult(success=False, error="No post-ready assets found")

        platforms = (db_job.config_json or {}).get("platforms", ["tiktok", "instagram", "youtube"])
        results = []

        for platform in platforms:
            account_id = self._get_account_id(platform)
            if not account_id:
                results.append(PostResult(
                    platform=platform,
                    post_id=None,
                    url=None,
                    success=False,
                    error=f"No account configured for {platform}"
                ))
                continue

            for asset in video_assets + image_assets:
                caption = await self._generate_caption(db_job, asset, platform)
                post_result = await self._post_to_platform(
                    platform=platform,
                    account_id=account_id,
                    caption=caption,
                    media_path=asset.path,
                    media_type=asset.asset_type,
                    tags=self._get_tags(db_job, platform)
                )
                results.append(post_result)

                if post_result.success:
                    await add_asset(
                        job_id=job.id,
                        asset_type=asset.asset_type,
                        path=asset.path,
                        metadata={
                            "platform": platform,
                            "post_id": post_result.post_id,
                            "url": post_result.url,
                            "posted_at": datetime.utcnow().isoformat(),
                        }
                    )

        success_count = sum(1 for r in results if r.success)
        await update_job_status(job.id, JobStatus.COMPLETED, "POSTED")
        await update_job_config(job.id, {"post_results": [r.__dict__ for r in results]})

        return AgentResult(
            success=success_count > 0,
            output={
                "posted": success_count,
                "failed": len(results) - success_count,
                "results": [r.__dict__ for r in results],
            },
            error=None if success_count > 0 else "All posts failed",
        )

    def _get_account_id(self, platform: str) -> Optional[str]:
        env_map = {
            "tiktok": "POSTIZ_TIKTOK_ACCOUNT_ID",
            "instagram": "POSTIZ_INSTAGRAM_ACCOUNT_ID",
            "youtube": "POSTIZ_YOUTUBE_ACCOUNT_ID",
            "twitter": "POSTIZ_TWITTER_ACCOUNT_ID",
            "linkedin": "POSTIZ_LINKEDIN_ACCOUNT_ID",
        }
        return os.getenv(env_map.get(platform, ""))

    def _get_tags(self, job, platform: str) -> List[str]:
        base_tags = job.config.get("tags", [])
        platform_tags = {
            "tiktok": ["#fyp", "#viral", "#trending"],
            "instagram": ["#reels", "#explore", "#viral"],
            "youtube": ["#shorts", "#viral", "#trending"],
            "twitter": [],
            "linkedin": [],
        }
        return base_tags + platform_tags.get(platform, [])

    async def _generate_caption(self, job, asset, platform: str) -> str:
        prompt = f"""
Write a {platform}-optimized caption for this content:
- Niche: {job.config.get('niche', 'general')}
- Style: {job.config.get('style_notes', 'engaging')}
- Hook: {(asset.metadata_json or {}).get('hook', 'Watch this!')}
- CTA: {job.config.get('cta', 'Follow for more!')}

Requirements:
- Max 2200 chars for Instagram, 150 for TikTok, 5000 for YouTube
- Include 3-5 relevant hashtags
- Native tone for {platform}
- Include CTA naturally
"""
        result = await self.llm.generate(prompt, temperature=0.7, max_tokens=500)
        return result["text"].strip()

    async def _post_to_platform(
        self,
        platform: str,
        account_id: str,
        caption: str,
        media_path: str,
        media_type: str,
        tags: List[str]
    ) -> PostResult:
        try:
            full_caption = caption + "\n\n" + " ".join(tags) if tags else caption

            if platform in ["tiktok", "instagram", "youtube"]:
                post = await self.postiz.create_post(
                    account_id=account_id,
                    content=full_caption,
                    media_paths=[media_path],
                    media_type="video" if media_type == "video" else "image",
                )
            else:
                post = await self.postiz.create_post(
                    account_id=account_id,
                    content=full_caption,
                    media_paths=[media_path] if media_type == "image" else [],
                )

            return PostResult(
                platform=platform,
                post_id=post.get("id"),
                url=post.get("url") or post.get("permalink"),
                success=True,
            )
        except Exception as e:
            return PostResult(
                platform=platform,
                post_id=None,
                url=None,
                success=False,
                error=str(e),
            )

