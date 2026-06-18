"""
phase2_scorer/logistics_scorer.py
───────────────────────────────────
Feature Group E: Location & Logistics Score
 
Axes:
  E1. Location (Pune/Noida preferred → acceptable cities → India other → outside)
  E2. Notice period (0-30 days ideal, 30+ increasingly penalized)
"""
 
from config.jd_config import (
    LOCATION_SCORES,
    NOTICE_PERIOD_SCORES,
    INDIA_COUNTRY_VARIANTS,
)
from config.scoring_weights import LOGISTICS_WEIGHTS
from utils.text_cleaner import extract_city, clean, is_india
 
def _location_score(candidate: dict) -> float:
    """E1: Score based on candidate location vs JD preferences."""
    profile  = candidate.get("profile", {})
    signals  = candidate.get("redrob_signals", {}) or {}
 
    location = profile.get("location", "")
    country  = profile.get("country", "")
    willing  = signals.get("willing_to_relocate", True)
 
    # Outside India
    if not is_india(country, location):
        return LOCATION_SCORES["outside_india"]["score"]   # 0.05
 
    city = extract_city(location)
 
    # Preferred cities
    if city in LOCATION_SCORES["preferred"]["cities"]:
        return LOCATION_SCORES["preferred"]["score"]       # 1.0
 
    # Acceptable cities
    if city in LOCATION_SCORES["acceptable"]["cities"]:
        return LOCATION_SCORES["acceptable"]["score"]      # 0.75
 
    # Anywhere else in India
    if willing:
        return LOCATION_SCORES["india_other"]["score"]     # 0.50
    else:
        return LOCATION_SCORES["india_no_relocate"]["score"]  # 0.30
 
def _notice_score(candidate:dict) -> float:
    signals = candidate.get("redrob_signals", {}) or {}
    days = signals.get("notice_period_days", 60)

    if days is None or days<0:
        days=60

    for lo, hi, score in NOTICE_PERIOD_SCORES:
        if lo<= days <= hi:
            return score
    return 0.10

def score_logistics(candidate: dict)-> float:
    w = LOGISTICS_WEIGHTS
    score = (
        w["location"]* _location_score(candidate)+
        w["notice_period"]* _notice_score(candidate)
    )

    return round(min(1.0, max(0.0, score)), 6)