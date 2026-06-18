"""
phase2_scorer/title_alignment_scorer.py
────────────────────────────────────────
Feature Group C: Title & Role Alignment Score
 
Axes:
  C1. Role family match (ML_ENGINEER=1.0 down to NON_TECH=0.05)
  C2. Years of experience calibration (ideal 5-9 years per JD)
 
Uses role_family already assigned by Phase 1 title_cluster.
"""
 
from config.jd_config import YOE_SCORE_MAP, ROLE_FAMILIES
from utils.text_cleaner import clean
 
_FAMILY_ALIGNMENT = {
    "ML_ENGINEER":      1.00,
    "DATA_SCIENTIST":   0.75,
    "SOFTWARE_ENGINEER":0.40,
    "DATA_ENGINEER":    0.30,
    "NON_TECH":         0.05,
    "UNKNOWN":          0.35,
}

def _yoe_score(years: float | int| None) -> float:
    """Score years of experience against the JD's 5-9 year ideal band."""

    yoe = float(years or 0)
    for lo, hi, score in YOE_SCORE_MAP:
        if lo <= yoe < hi:
            return score
    return 0.3

def score_title_alignment(candidate: dict) -> float:
    """
    Compute title & role alignment score.
 
    Returns:
        Float in [0, 1]
    """

    profile     = candidate.get("profile", {})
    role_family = candidate.get("role_family", "UNKNOWN")
    yoe         = profile.get("years_of_experience", 0)

    family_score = _FAMILY_ALIGNMENT.get(role_family, 0.35)
    yoe_s = _yoe_score(yoe)

    raw = 0.65*family_score +0.35*yoe_s
    return round(min(1.0, max(0.0, raw)), 6)