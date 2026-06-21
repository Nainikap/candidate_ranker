"""
phase2_scorer/skill_scorer.py
──────────────────────────────
Feature Group A: Skill Relevance Score
 
Formula per skill:
  contribution = tier_weight × proficiency_weight × depth_multiplier × credibility_multiplier
 
Final score = clip(sum(contributions) / NORMALIZER, 0, 1)
 
Special rules:
  - TIER_D dominance penalty: >3 anti-skills and no TIER_A → score × 0.3
  - Skill with proficiency=advanced but assessment < 45 → credibility penalty
"""
 
import math
from config.jd_config import (
    SKILL_TIER_LOOKUP,
    TIER_WEIGHTS,
    PROFICIENCY_WEIGHTS,
    ASSESSMENT_CREDIBILITY,
    HONEYPOT,
)
from config.scoring_weights import SKILL_DEPTH_LOG_BASE, SKILL_SCORE_NORMALIZER
from utils.text_cleaner import clean_skill
 

def _get_tier(skill_name: str) -> str:
    name = clean_skill(skill_name)
    if name in SKILL_TIER_LOOKUP:
        return SKILL_TIER_LOOKUP[name]
    for kw, tier in SKILL_TIER_LOOKUP.items():
        if kw in name or name in kw:
            return tier
    return "UNKOWN"

def _depth_multiplier(duration_months: int|float|None) -> float:
    """log(1 + duration_months / BASE) — rewards depth over breadth."""
    months = max(0.0, duration_months or 0)
    return math.log1p((months)/SKILL_DEPTH_LOG_BASE)

def _credibility_multiplier(proficiency: str,
                            assessment_score: float|None
) -> float:
    """
    Adjust score based on whether assessment score backs up claimed proficiency.
    Only applies when assessment score is available AND proficiency is advanced.
    """
    if assessment_score is None or assessment_score<0:
        return 1.0
    
    prof = (proficiency or "").lower()
    if prof not in ("advanced", "expert") :
        return 1.0
    
    cfg = ASSESSMENT_CREDIBILITY
    if assessment_score>=cfg["boost"]["min_score"]:
        return cfg["boost"]["multiplier"]
    elif assessment_score>=cfg["neutral"]["min_score"]:
        return cfg["neutral"]["min_score"]
    else:
        return cfg["penalty"]["min_score"]
    
def score_skill(candidate: dict) -> float:
    """
    Compute skill relevance score for a candidate.
 
    Returns:
        Float in [0, 1]
    """
    skills          = candidate.get("skills", [])
    assessment_map  = candidate.get("redrob_signals", {}).get(
        "skill_assessment_scores", {}
    ) or {}
 
    if not skills:
        return 0.0
    
    total_contribution = 0.0
    tier_a_count       = 0
    tier_d_count       = 0

    for skill in skills:
        name = clean_skill(skill.get("name", ""))
        proficiency = (skill.get("proficiency") or "beginner").lower()
        duration    = skill.get("duration_months") or 0

        tier = _get_tier(name)
        tier_w = TIER_WEIGHTS.get(tier, 0.0)
        prof = PROFICIENCY_WEIGHTS.get(proficiency, 0.3)
        depth = _depth_multiplier(duration)
        assessment_val = assessment_map.get(skill.get("name", ""), None)
        credibility = _credibility_multiplier(proficiency, assessment_val)

        contribution = tier_w*prof*depth*credibility
        total_contribution += contribution

        if tier == "TIER_A":
            tier_a_count+=1
        elif tier == "TIER_D":
            tier_d_count+=1

    raw = total_contribution/SKILL_SCORE_NORMALIZER
    score = min(1.0, max(0.0, raw))

    if tier_d_count > 3 and tier_a_count == 0:
        score *= 0.3

    return round(score, 6)