"""
phase2_scorer/trajectory_scorer.py
────────────────────────────────────
Feature Group B: Career Trajectory Score
 
Axes:
  B1. Product company ratio (weighted by duration)
  B2. Seniority arc (non-decreasing = good, stagnant = okay, declining = bad)
  B3. Production language detector (keyword hits in descriptions)
  B4. Company quality score (top-tier > product > unknown > research > services)
 
Special penalties:
  - Title-hopping: ≥3 short roles (<18 months) with seniority jump → penalty
  - Pure research: no production deployment signals → penalty
"""
 
import re
from config.jd_config import (
    SENIORITY_LOOKUP,
    PRODUCTION_LANGUAGE,
    MULTIPLIERS,
)
from config.scoring_weights import TRAJECTORY_WEIGHTS
from utils.text_cleaner import clean, clean_title
from utils.company_classifier import (
    get_product_ratio,
    get_company_quality_score,
    classify_company,
)
 
def _seniority_level(title: str) -> int:
    """Map a job title to an integer seniority level (0–5)."""
    t = clean_title(title)
    best = 2
    for kw, level in SENIORITY_LOOKUP.items():
        if kw in t:
            best = max(best, level)
    return best

def _sernioriy_arc_score(career_history: list[dict]) ->float:
    """
    Score based on whether seniority level is non-decreasing over time.
    History should be in chronological order (oldest first).
    """
    if not career_history:
        return 0.5
    
    levels = [_seniority_level(r.get("title", "")) for r in career_history]

    if len(levels) ==1:
        return 0.7
    
    increases = sum(1 for i in range(1, len(levels)) if levels[i]>levels[i-1])
    decreases = sum(1 for i in range(1, len(levels)) if levels[i]<levels[i-1])
    stagnant = sum(1 for i in range(1, len(levels)) if levels[i]==levels[i-1])
    total_gaps = len(levels)-1

    if decreases ==0 and increases>0:
        return 1.0
    elif decreases ==0 and stagnant==total_gaps:
        return 0.6
    elif decreases>0 and increases>decreases:
        return 0.7
    else:
        return 0.4
    
def _title_hop_penalty(career_history: list[dict]) -> float:
    """
    Detect title-chasing: ≥3 short stints (<18 months) with a seniority jump.
    Returns a multiplier: 1.0 (no penalty) or 0.7 (title-hopper detected).
    """

    hops = 0
    prev_level =-1

    for role in career_history:
        duration = role.get("duration_months", 0) or 0
        level    = _seniority_level(role.get("title", ""))
        if duration < 18 and level > prev_level and prev_level >= 0:
            hops += 1
        prev_level = level
    return 0.7 if hops>=3 else 1.0

def _production_language_score(career_history: list[dict]) -> float:
    """
    Scan all role descriptions for production vs research language.
    Returns score in [0, 1].
    """

    positiive_keys = PRODUCTION_LANGUAGE["positive"]
    negative_keys = PRODUCTION_LANGUAGE["negative"]

    positive_hits =0
    negative_hits =0

    for role in career_history:
        desc = clean(role.get("description", ""))
        positive_hits += sum(1 for kw in positiive_keys if kw in desc)
        negative_hits += sum(1 for kw in negative_keys if kw in desc)

    raw = 0.5 + (min(positive_hits, 4)*0.1) - (min(negative_hits, 3)*0.1)
    return min(1.0, max(0.0, raw))

def score_trajectory(candidate: dict) -> float:
    """
    Compute career trajectory score for a candidate.
 
    Returns:
        Float in [0, 1]
    """
    career = candidate.get("career_history", [])

    if not career:
        return 0.3
    
    def _sort_key(r):
        return r.get("start_date") or "0000"
    
    career_sorted = sorted(career, key=_sort_key)

    product_ratio = get_product_ratio(career)
    if product_ratio >= 0.4:
        product_score = 1.0
    elif product_ratio >= 0.3:
        product_score = 0.6 + (product_ratio - 0.3) / 0.3 * 0.4
    elif product_ratio > 0.0:
        product_score = 0.3 + product_ratio 
    else:
        product_score = 0.0 

    arc_score = _sernioriy_arc_score(career_sorted)
    prod_lang_score = _production_language_score(career)
    quality_score = get_company_quality_score(career)

    w = TRAJECTORY_WEIGHTS
    raw = (
        w["product_ratio"]       * product_score
      + w["seniority_arc"]       * arc_score
      + w["production_language"] * prod_lang_score
      + w["company_quality"]     * quality_score
    )

    hop_penalty = _title_hop_penalty(career_sorted)
    raw *= hop_penalty

    return round(min(1.0, max(0.0, raw)), 6)