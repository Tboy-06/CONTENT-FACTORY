from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

from typing import Dict, Any
import logging
import json
import re
from backend.engine.brain import ask_brain

logger = logging.getLogger(__name__)

class NicheScorerAgent:
    """
    Scores a chosen niche on 5 dimensions to evaluate its viability.
    Uses AI reasoning to return real metrics and tailored recommendations.
    """
    def __init__(self):
        self.name = "NicheScorer"

    async def run(self, niche: str) -> Dict[str, Any]:
        logger.info(f"Scoring niche: {niche}")
        
        prompt = (
            f"You are an expert YouTube and TikTok algorithmic strategist. Evaluate the video niche: '{niche}'.\n"
            "Score each dimension from 1 to 10 (integers):\n"
            "- search_volume (1 = tiny, 10 = massive viral interest)\n"
            "- competition_level (1 = highly saturated, 10 = wide open blue ocean)\n"
            "- cpm_rate (1 = very low ad spend, 10 = premium high-ticket advertisers)\n"
            "- evergreen_potential (1 = dies in 2 days, 10 = relevant for years)\n"
            "- scalability (1 = hard to automate, 10 = effortless volume production)\n\n"
            "Return strictly a JSON object with this format:\n"
            "{\n"
            '  "scores": {\n'
            '    "search_volume": 8,\n'
            '    "competition_level": 6,\n'
            '    "cpm_rate": 7,\n'
            '    "evergreen_potential": 9,\n'
            '    "scalability": 8\n'
            '  },\n'
            '  "recommendation": "GO",\n'
            '  "rationale": "One crisp sentence explaining why."\n'
            "}"
        )

        try:
            raw_res = await ask_brain(prompt, format_json=True)
            match = re.search(r'\{.*\}', raw_res, re.DOTALL)
            if match:
                parsed = json.loads(match.group(0))
                scores = parsed.get("scores", {})
                clean_scores = {
                    "search_volume": max(1, min(10, int(scores.get("search_volume", 7)))),
                    "competition_level": max(1, min(10, int(scores.get("competition_level", 6)))),
                    "cpm_rate": max(1, min(10, int(scores.get("cpm_rate", 6)))),
                    "evergreen_potential": max(1, min(10, int(scores.get("evergreen_potential", 7)))),
                    "scalability": max(1, min(10, int(scores.get("scalability", 7))))
                }
                total_score = sum(clean_scores.values())
                rec = parsed.get("recommendation", "GO" if total_score >= 32 else "PROCEED WITH CAUTION")
                return {
                    "niche": niche,
                    "scores": clean_scores,
                    "total_score": total_score,
                    "max_score": 50,
                    "recommendation": rec,
                    "rationale": parsed.get("rationale", f"Analysis completed for {niche}.")
                }
        except Exception as e:
            logger.warning(f"[NicheScorer] AI evaluation failed ({e}), falling back to heuristic")

        # Heuristic calculation if offline
        niche_lower = niche.lower()
        score_data = {
            "search_volume": 7,
            "competition_level": 6,
            "cpm_rate": 6,
            "evergreen_potential": 8,
            "scalability": 7
        }
        if any(w in niche_lower for w in ["finance", "money", "investing", "crypto", "business"]):
            score_data["cpm_rate"] = 10
            score_data["competition_level"] = 4
        elif any(w in niche_lower for w in ["tech", "ai", "coding", "software"]):
            score_data["search_volume"] = 9
            score_data["cpm_rate"] = 8
            score_data["evergreen_potential"] = 6
        elif any(w in niche_lower for w in ["history", "documentary", "mystery"]):
            score_data["evergreen_potential"] = 10
            score_data["search_volume"] = 8
            score_data["cpm_rate"] = 7

        total = sum(score_data.values())
        return {
            "niche": niche,
            "scores": score_data,
            "total_score": total,
            "max_score": 50,
            "recommendation": "GO" if total >= 34 else "PROCEED WITH CAUTION"
        }

niche_scorer_agent = NicheScorerAgent()
