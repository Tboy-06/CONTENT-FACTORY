from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

class NicheScorerAgent:
    """
    Scores a chosen niche on 5 dimensions to evaluate its viability.
    """
    def __init__(self):
        self.name = "NicheScorer"

    async def run(self, niche: str) -> Dict[str, Any]:
        logger.info(f"Scoring niche: {niche}")
        
        # In a fully productionized system, this would:
        # 1. Call YouTube Data API to check search volume & competition
        # 2. Call an LLM to evaluate evergreen potential & scalability
        # 3. Look up average CPM rates for the category
        
        # We will mock the AI evaluation here for immediate use, 
        # but structured dynamically based on niche keywords.
        niche_lower = niche.lower()
        
        score_data = {
            "search_volume": 7,
            "competition_level": 5,
            "cpm_rate": 6,
            "evergreen_potential": 8,
            "scalability": 7
        }
        
        if "finance" in niche_lower or "money" in niche_lower or "crypto" in niche_lower:
            score_data["cpm_rate"] = 10
            score_data["competition_level"] = 9
        elif "tech" in niche_lower or "ai" in niche_lower:
            score_data["search_volume"] = 9
            score_data["evergreen_potential"] = 6 # AI changes fast
        elif "gaming" in niche_lower:
            score_data["cpm_rate"] = 3
            score_data["search_volume"] = 10
            score_data["competition_level"] = 10
            
        total_score = sum(score_data.values())
        
        if total_score >= 35:
            recommendation = "GO"
        elif total_score >= 25:
            recommendation = "PROCEED WITH CAUTION"
        else:
            recommendation = "AVOID"
            
        return {
            "niche": niche,
            "scores": score_data,
            "total_score": total_score,
            "max_score": 50,
            "recommendation": recommendation
        }

niche_scorer_agent = NicheScorerAgent()
