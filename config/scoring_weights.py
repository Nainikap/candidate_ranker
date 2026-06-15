"""
config/scoring_weights.py
─────────────────────────
All scoring formula weights.
Tune these without touching any logic files.

The final score formula:
    raw_score = sum(PHASE2_WEIGHTS[axis] × axis_score for each axis)
    final_score = raw_score × product(applicable hard multipliers)
"""

# ── Phase 2 axis weights (must sum to 1.0) ────────────────────────────────────
PHASE2_WEIGHTS = {
    "skill_relevance":          0.30,   # TIER_A/B/C/D match depth × proficiency
    "career_trajectory":        0.20,   # product co ratio, seniority arc, production lang
    "title_alignment":          0.15,   # role family match × YOE calibration
    "behavioral_availability":  0.15,   # recency, engagement, github, credibility
    "logistics":                0.10,   # location + notice period
    "assessment_credibility":   0.05,   # verified skill scores vs self-reported
    "external_validation":      0.05,   # github activity, publications, open source
}

assert abs(sum(PHASE2_WEIGHTS.values()) - 1.0) < 1e-9, \
    "PHASE2_WEIGHTS must sum to 1.0"

# ── Phase 1 score fusion weights (for carrying forward into Phase 2) ──────────
PHASE1_FUSION_WEIGHTS = {
    "tfidf_score": 0.05,   # small boost if caught by TF-IDF
    "bm25_score":  0.05,   # small boost if caught by BM25
}
# Note: these are additive bonuses on top of the raw_score before multipliers

# ── Phase 3 re-ranking adjustments ────────────────────────────────────────────
PHASE3_WEIGHTS = {
    "rarity_bonus_max":        0.04,   # max additive bonus for rare+relevant skills
    "production_language_max": 0.04,   # max additive bonus for production signals
                                       # in career descriptions
}

# ── Skill scoring sub-weights ─────────────────────────────────────────────────
SKILL_DEPTH_LOG_BASE = 12   # log(1 + duration_months / BASE)
                             # 12 = 1 year unit; log(1+3yrs) ≈ 1.39, log(1+6mo) ≈ 0.41

SKILL_SCORE_NORMALIZER = 15.0   # divide raw skill sum by this to get 0-1
                                 # tuned for a candidate with 5 TIER_A skills at
                                 # advanced/3yrs each → score ≈ 1.0

# ── Trajectory sub-weights ────────────────────────────────────────────────────
TRAJECTORY_WEIGHTS = {
    "product_ratio":         0.40,
    "seniority_arc":         0.25,
    "production_language":   0.20,
    "company_quality":       0.15,
}

# ── Behavioral sub-weights ────────────────────────────────────────────────────
BEHAVIORAL_WEIGHTS = {
    "recency":               0.40,
    "engagement":            0.30,   # open_to_work, response rate, response time
    "github_activity":       0.20,
    "profile_credibility":   0.10,   # verified email/phone, completeness
}

# ── Logistics sub-weights ─────────────────────────────────────────────────────
LOGISTICS_WEIGHTS = {
    "location":              0.60,
    "notice_period":         0.40,
}