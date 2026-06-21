"""
phase2_scorer/phase2_orchestrator.py
──────────────────────────────────────
Orchestrates all Phase 2 feature scorers.
Computes weighted final score + applies hard multipliers.
Uses joblib for parallel processing across the shortlist.
 
Final formula:
  raw_score = weighted sum of all axis scores
            + small additive bonus from Phase 1 retrieval scores
 
  final_score = raw_score
              × honeypot_multiplier      (applied in Phase 3)
              × services_only_multiplier (if entire career = services)
              × location_hard_penalty    (if outside India + no relocation)
              × non_tech_penalty         (if NON_TECH + no ML skills)
"""
 
import math
from joblib import Parallel, delayed
from tqdm import tqdm
 
from config.jd_config import MULTIPLIERS
from config.scoring_weights import PHASE2_WEIGHTS, PHASE1_FUSION_WEIGHTS
from utils.company_classifier import is_services_only
from utils.text_cleaner import is_india
 
from phase2_scorer.skill_scorer import score_skill
from phase2_scorer.trajectory_scorer import score_trajectory
from phase2_scorer.title_alignment import score_title_alignment
from phase2_scorer.behavioral_scorer import score_behavioral
from phase2_scorer.logistics_scorer import score_logistics

def assessment_credibility_bonus(candidate: dict)-> float:
    """
    Bonus score from skill assessment results.
    Rewards candidates with verified high scores on TIER_A skills.
    """
    from config.jd_config import SKILL_TIER_LOOKUP
    from utils.text_cleaner import clean_skill

    signals = candidate.get("redrob_signals", {}) or {}
    assessments = signals.get("skill_assessment_scores", {}) or {}

    if not assessments:
        return 0.5
    
    tier_a_scores = []
    for skill_name, score in assessments.items():
        tier = SKILL_TIER_LOOKUP.get(clean_skill(skill_name), "UNKOWN")
        if tier == "TIER_A" and score>=0:
            tier_a_scores.append(score)

    if not tier_a_scores:
        return 0.5
    avg = sum(tier_a_scores)/len(tier_a_scores)
    return min(1.0, max(0.0, avg/100))

def _external_validation_bonus(candidate: dict) -> float:
    """
    Bonus for external signals: GitHub activity, publications, open source.
    """

    signals =candidate.get("redrob_signals", {}) or {}

    score=0.4

    gh = signals.get("github_activity_score", -1)
    if gh is None: gh=-1
    if gh>=8:
        score+= 0.3
    elif gh>=4:
        score+=0.15
    elif gh ==-1:
        score -= 0.05
    
    saved = signals.get("saved_by_recruiters_30d", 0) or 0
    if saved >=10:
        score+=0.15
    elif saved>=5:
        score+= 0.08
    
    appearances = signals.get("search_appearances_30d", 0) or 0
    if appearances>=200:
        score+=0.10
    elif appearances>=100:
        score+=0.05
    
    return round(min(1.0, max(0.0, score)),6)

def _compute_multipliers(candidate: dict)->float:
    """
    Compute product of all applicable hard multipliers.
    These are applied after the weighted sum.
    """

    multiplier = 1.0
    profile = candidate.get("profile", {})
    signals =candidate.get("redrob_signals", {}) or {}
    career = candidate.get("career_history", [])

    if is_services_only(career):
        multiplier *= MULTIPLIERS["services_only"]

    country  = profile.get("country", "")
    location = profile.get("location", "")
    willing  = signals.get("willing_to_relocate", True)
    if not is_india(country, location) and not willing:
        multiplier *= MULTIPLIERS["outside_india_hard"] 

    role_family = candidate.get("role_family", "UNKNOWN")
    if role_family == "NON_TECH":
        multiplier *= MULTIPLIERS["non_tech_title"]

    return multiplier

def _score_one(candidate: dict) -> dict:
    """
    Score a single candidate across all axes.
    Returns the candidate dict with scores attached.
    """
    w = PHASE2_WEIGHTS
    f = PHASE1_FUSION_WEIGHTS

    skill_score       = score_skill(candidate)
    trajectory_score  = score_trajectory(candidate)
    title_score       = score_title_alignment(candidate)
    behavioral_score  = score_behavioral(candidate)
    logistics_score   = score_logistics(candidate)
    assessment_bonus  = assessment_credibility_bonus(candidate)
    external_bonus    = _external_validation_bonus(candidate)

    raw = (
        w["skill_relevance"]         * skill_score
      + w["career_trajectory"]       * trajectory_score
      + w["title_alignment"]         * title_score
      + w["behavioral_availability"] * behavioral_score
      + w["logistics"]               * logistics_score
      + w["assessment_credibility"]  * assessment_bonus
      + w["external_validation"]     * external_bonus
    )
    
    p1_tfidf = candidate.get("tfidf_score", 0.0)
    p1_bm25  = candidate.get("bm25_score", 0.0)
    fusion_bonus = (
        f["tfidf_score"] * p1_tfidf
      + f["bm25_score"]  * p1_bm25
    )
    raw += fusion_bonus
    raw *= _compute_multipliers(candidate)

    candidate["scores"] = {
        "skill_relevance":         round(skill_score, 4),
        "career_trajectory":       round(trajectory_score, 4),
        "title_alignment":         round(title_score, 4),
        "behavioral_availability": round(behavioral_score, 4),
        "logistics":               round(logistics_score, 4),
        "assessment_credibility":  round(assessment_bonus, 4),
        "external_validation":     round(external_bonus, 4),
    }

    candidate["final_score"] = round(min(1.0, max(0.0, raw)),6)
    return candidate

def run_phase2(shortlist: list[dict],
               debug: bool=False,
               n_jobs: int =-1
) ->list[dict]:
    """
    Run Phase 2 deep scoring on all shortlisted candidates.
 
    Args:
        shortlist: output of Phase 1 (dynamic size, 8K–20K typically)
        debug:     print diagnostics
        n_jobs:    joblib parallelism (-1 = all cores)
 
    Returns:
        Same list with 'scores' and 'final_score' attached to each candidate.
    """
    if not shortlist:
        return []
    
    if debug:
        print(f"  [Phase 2] Scoring {len(shortlist):,} candidates "
              f"with {n_jobs} workers...")
        
    results = Parallel(n_jobs=n_jobs, prefer="threads")(
        delayed(_score_one)(c)
        for c in tqdm(shortlist, desc="  Scoring", unit="candidates", disable=not debug)
    )

    if debug:
        scores = [r["final_score"] for r in results]
        scores.sort(reverse=True)
        print(f"  [Phase 2] Score distribution:")
        print(f"    Top 1:    {scores[0]:.4f}")
        print(f"    Top 10:   {scores[9]:.4f}" if len(scores) >= 10 else "")
        print(f"    Median:   {scores[len(scores)//2]:.4f}")
        print(f"    Bottom:   {scores[-1]:.4f}")
    return results