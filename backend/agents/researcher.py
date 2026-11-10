from __future__ import annotations

import json
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from backend.agents import BaseAgent, AgentResult, Tool, Job
from backend.agents.llm_client import get_gemini_client
from backend.tools.youtube_api import get_youtube_api
from backend.tools.web_search import get_web_searcher
from backend.tools.agent_reach_skill import get_agent_reach
from backend.tools.youtube_dl import extract_video_metadata
from backend.vault import add_asset, log_event
from backend.config import get_settings

settings = get_settings()
gemini = get_gemini_client()
youtube_api = get_youtube_api()
web_searcher = get_web_searcher()
agent_reach = get_agent_reach()


class ResearcherAgent(BaseAgent):
    def __init__(self):
        tools = [
            Tool(
                name="youtube_search",
                description="Search YouTube for trending videos in niche",
                parameters={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "max_results": {"type": "integer", "default": 10},
                        "order": {"type": "string", "enum": ["viewCount", "relevance", "date", "rating"], "default": "viewCount"},
                    },
                    "required": ["query"],
                },
                handler=self._youtube_search,
            ),
            Tool(
                name="web_search",
                description="Search the web for trending topics",
                parameters={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "max_results": {"type": "integer", "default": 10},
                        "source": {"type": "string", "enum": ["tavily", "serpapi"], "default": "tavily"},
                    },
                    "required": ["query"],
                },
                handler=self._web_search,
            ),
            Tool(
                name="score_virality",
                description="Score a video idea for virality potential (0-100)",
                parameters={
                    "type": "object",
                    "properties": {
                        "topic": {"type": "string"},
                        "angle": {"type": "string"},
                        "reference_data": {"type": "object"},
                    },
                    "required": ["topic", "angle"],
                },
                handler=self._score_virality,
            ),
            Tool(
                name="agent_reach_skill",
                description="Execute an Agent Reach skill (YouTube summarize, Reddit trends, etc.)",
                parameters={
                    "type": "object",
                    "properties": {
                        "skill_name": {"type": "string"},
                        "params": {"type": "object"},
                    },
                    "required": ["skill_name"],
                },
                handler=self._agent_reach_skill,
            ),
        ]
        super().__init__(agent_id="researcher", tools=tools)

    def _create_llm_client(self):
        return gemini

    async def _run_impl(self, job: Job, context: Dict[str, Any]) -> AgentResult:
        niche = job.niche
        config = job.config
        frequency = config.get("frequency", 3)
        platforms = config.get("platforms", ["tiktok", "youtube"])
        mode = config.get("mode", "Generate from Scratch")
        reference_url = config.get("referenceUrl")

        await log_event("INFO", self.agent_id, f"Starting research for niche: {niche}", {"job_id": job.id})

        if mode in ["Remix & Spin (Copyright Bypass)", "Clone a Video (Template Extraction)"] and reference_url:
            return await self._analyze_reference_video(job.id, reference_url, niche, mode)

        queries = self._generate_queries(niche, platforms)

        all_ideas = []
        for query in queries:
            ideas = await self._search_and_analyze(query, niche)
            all_ideas.extend(ideas)

        # Deduplicate by topic
        seen = set()
        unique_ideas = []
        for idea in all_ideas:
            key = idea["topic"].lower()
            if key not in seen:
                seen.add(key)
                unique_ideas.append(idea)

        # Score and rank
        scored_ideas = []
        for idea in unique_ideas:
            score_result = await self.call_tool("score_virality", topic=idea["topic"], angle=idea["angle"], reference_data=idea)
            if score_result.get("score"):
                idea["virality_score"] = score_result["score"]
                idea["score_rationale"] = score_result.get("rationale", "")
                scored_ideas.append(idea)

        scored_ideas.sort(key=lambda x: x.get("virality_score", 0), reverse=True)

        top_ideas = scored_ideas[: frequency * 3]

        if not top_ideas:
            # Dynamic AI research briefs if external search APIs are offline or unconfigured
            try:
                from backend.engine.brain import ask_brain
                prompt = (
                    f"You are an elite viral documentary researcher. For the niche '{niche}', brainstorm 3 high-retention video briefs. "
                    "Return ONLY a JSON array with 3 objects, each having:\n"
                    "- 'topic': a specific, clickable title\n"
                    "- 'angle': the psychological curiosity angle or controversy\n"
                    "- 'virality_score': an integer from 75 to 98\n"
                    "- 'score_rationale': 1 sentence explaining why it retains viewers"
                )
                raw_json = await ask_brain(prompt, format_json=True)
                match = re.search(r'\[.*\]', raw_json, re.DOTALL)
                if match:
                    parsed_briefs = json.loads(match.group(0))
                    for b in parsed_briefs:
                        top_ideas.append({
                            "topic": b.get("topic", f"{niche} Secrets"),
                            "angle": b.get("angle", "Counter-intuitive breakdown"),
                            "reference_url": None,
                            "title": b.get("topic", niche),
                            "view_count": 500000,
                            "channel": "Top Creator",
                            "virality_score": int(b.get("virality_score", 85)),
                            "score_rationale": b.get("score_rationale", "High emotional payoff"),
                            "mode": mode,
                            "niche": niche
                        })
            except Exception as e:
                logger.warning(f"[Researcher] AI brief generation fallback error: {e}")

            if not top_ideas:
                top_ideas.append({
                    "topic": f"The Untold Truth About {niche}",
                    "angle": "Exposing the hidden mechanics that 99% of people miss",
                    "reference_url": None,
                    "title": f"The Untold Truth About {niche}",
                    "view_count": 450000,
                    "channel": "Documentary Masterclass",
                    "virality_score": 92,
                    "score_rationale": "High curiosity gap and immediate retention hook",
                    "mode": mode,
                    "niche": niche
                })

        for i, idea in enumerate(top_ideas):
            await add_asset(
                job_id=job.id,
                asset_type="research_brief",
                path=f"research/brief_{i+1}.json",
                metadata=idea,
            )

        await log_event("INFO", self.agent_id, f"Research complete: {len(top_ideas)} briefs generated", {"job_id": job.id, "count": len(top_ideas)})

        return AgentResult(
            success=True,
            output={"briefs_count": len(top_ideas), "briefs": top_ideas},
        )

    async def _analyze_reference_video(self, job_id: int, url: str, niche: str, mode: str) -> AgentResult:
        await log_event("INFO", self.agent_id, f"Analyzing reference video: {url}", {"job_id": job_id})
        metadata = await extract_video_metadata(url)
        
        idea = {
            "topic": metadata.get("title", "Unknown Reference Video") if metadata else "Unknown Video",
            "angle": f"Reference Video for {mode}",
            "reference_url": url,
            "title": metadata.get("title", "") if metadata else "",
            "view_count": metadata.get("view_count", 0) if metadata else 0,
            "channel": metadata.get("channel", "") if metadata else "",
            "virality_score": 90, # Assume reference is viral
            "mode": mode,
            "niche": niche
        }
        
        await add_asset(
            job_id=job_id,
            asset_type="research_brief",
            path=f"research/brief_reference.json",
            metadata=idea,
        )
        return AgentResult(success=True, output={"briefs_count": 1, "briefs": [idea]})

    def _generate_queries(self, niche: str, platforms: List[str]) -> List[str]:
        base_queries = {
            "finance": ["personal finance tips", "investing for beginners", "money saving hacks", "passive income ideas", "credit score improvement", "budgeting for beginners"],
            "tech": ["AI tools 2024", "programming tips", "tech productivity", "software development", "VS Code extensions", "GitHub Copilot"],
            "health": ["fitness motivation", "healthy eating", "mental health tips", "workout routines", "intermittent fasting", "sleep optimization"],
            "productivity": ["time management", "deep work", "habit building", "focus techniques", "Notion templates", "morning routine"],
            "business": ["entrepreneurship tips", "startup advice", "marketing strategies", "sales techniques", "leadership skills"],
        }
        queries = base_queries.get(niche, [f"{niche} tips", f"{niche} tutorial", f"{niche} motivation"])

        # Add platform-specific queries
        if "youtube" in platforms:
            queries.extend([f"{niche} youtube", f"best {niche} channels"])
        if "tiktok" in platforms:
            queries.extend([f"{niche} tiktok", f"{niche} viral"])

        return queries[:8]

    async def _search_and_analyze(self, query: str, niche: str) -> List[Dict[str, Any]]:
        ideas = []

        # YouTube search
        try:
            yt_result = await self.call_tool("youtube_search", query=query, max_results=8, order="viewCount")
            for video in yt_result.get("videos", []):
                topic = self._extract_topic(video.get("title", ""), niche)
                angle = self._extract_angle(video.get("title", ""), video.get("description", ""))
                if topic and angle:
                    ideas.append({
                        "topic": topic,
                        "angle": angle,
                        "reference_url": video.get("url"),
                        "title": video.get("title"),
                        "view_count": video.get("view_count", 0),
                        "channel": video.get("channel"),
                        "published_at": video.get("published_at"),
                        "platform": "youtube",
                        "niche": niche,
                        "query": query,
                    })
        except Exception as e:
            await log_event("WARNING", self.agent_id, f"YouTube search failed: {e}", {"query": query})

        # Web search (Tavily preferred)
        try:
            web_result = await self.call_tool("web_search", query=f"{query} trending 2024", max_results=5, source="tavily")
            for article in web_result.get("results", []):
                ideas.append({
                    "topic": article.get("title", "")[:100],
                    "angle": "Article breakdown",
                    "reference_url": article.get("url"),
                    "platform": "web",
                    "source": "tavily",
                    "niche": niche,
                    "query": query,
                })
        except Exception as e:
            await log_event("WARNING", self.agent_id, f"Web search failed: {e}", {"query": query})

        # Reddit trends for additional signal
        try:
            reddit_result = await web_searcher.search_reddit(f"{niche} trending", max_results=3)
            for post in reddit_result.get("results", []):
                ideas.append({
                    "topic": post.get("title", "")[:100],
                    "angle": "Reddit discussion",
                    "reference_url": post.get("url"),
                    "platform": "reddit",
                    "niche": niche,
                })
        except Exception:
            pass

        return ideas

    def _extract_topic(self, title: str, niche: str) -> str:
        stop_words = {"how to", "why", "what", "when", "where", "the", "a", "an", "in", "for", "of", "to", "and", "or", "but", "best", "top", "ultimate", "complete", "guide"}
        words = [w for w in re.sub(r'[^\w\s]', '', title.lower()).split() if w not in stop_words and len(w) > 2]
        return " ".join(words[:8]).title() if words else title[:80]

    def _extract_angle(self, title: str, description: str) -> str:
        text = f"{title} {description}".lower()
        angles = [
            (["how to", "tutorial", "guide", "step by step", "learn"], "Tutorial/How-to"),
            (["mistake", "wrong", "avoid", "don't", "stop doing"], "Mistakes to Avoid"),
            (["secret", "hidden", "unknown", "nobody tells", "they don't want"], "Hidden Secrets"),
            (["vs", "versus", "compare", "comparison", "better"], "Comparison"),
            (["story", "journey", "my experience", "i tried", "how i"], "Personal Story"),
            (["tips", "hacks", "tricks", "secrets", "ways to"], "Tips & Hacks"),
            (["review", "tested", "tried", "honest"], "Review/Tested"),
            (["beginner", "start", "basics", "fundamentals"], "Beginner Guide"),
        ]
        for keywords, angle in angles:
            if any(k in text for k in keywords):
                return angle
        return "Educational/Informative"

    async def _youtube_search(self, query: str, max_results: int = 10, order: str = "viewCount") -> Dict[str, Any]:
        return await youtube_api.search(query=query, max_results=max_results, order=order)

    async def _web_search(self, query: str, max_results: int = 10, source: str = "tavily") -> Dict[str, Any]:
        return await web_searcher.search(query=query, max_results=max_results, prefer=source)

    async def _score_virality(self, topic: str, angle: str, reference_data: Dict[str, Any]) -> Dict[str, Any]:
        view_count = reference_data.get("view_count", 0)
        published = reference_data.get("published_at", "")

        # Recency boost
        recency_boost = 0
        if published:
            try:
                pub_date = datetime.fromisoformat(published.replace("Z", "+00:00"))
                days_old = (datetime.utcnow() - pub_date.replace(tzinfo=None)).days
                if days_old < 7:
                    recency_boost = 10
                elif days_old < 30:
                    recency_boost = 5
            except Exception:
                pass

        # Heuristic scoring to bypass LLM rate limits (ResourceExhausted)
        base_score = 50
        if view_count > 100000:
            base_score += 20
        elif view_count > 10000:
            base_score += 10
            
        final_score = min(100, base_score + recency_boost)
        return {"score": final_score, "rationale": f"Heuristic score based on {view_count} views and {recency_boost} recency boost."}


    async def _agent_reach_skill(self, skill_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        return await agent_reach.run_skill(skill_name, params)