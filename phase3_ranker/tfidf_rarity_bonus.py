"""
phase3_rerank/tfidf_rarity_bonus.py
──────────────────────────────────────
Rare-but-relevant skill bonus.
 
Runs only on the top 200 — computes how rare each candidate's TIER_A skills
are within that pool, and gives a small lift to candidates whose strong
skills are uncommon (signal: they have differentiated, hard-to-find expertise
rather than generic overlap with everyone else in the shortlist).
 
Example: if only 2% of the top-200 have FAISS experience, a candidate with
FAISS gets more credit than one with the more common "Python" skill.
"""
 
import math
from collections import Counter
from config.jd_config import SKILL_TIER_LOOKUP
from config.scoring_weights import PHASE3_WEIGHTS
from utils.text_cleaner import clean_skill
 
 
def _get_tier_a_skills(candidate: dict) -> list[str]:
    """Extract all TIER_A skill names (normalized) a candidate has."""
    skills = candidate.get("skills", [])
    result = []
    for skill in skills:
        name = clean_skill(skill.get("name", ""))
        if SKILL_TIER_LOOKUP.get(name) == "TIER_A":
            result.append(name)
    return result

def compute_rarity_bonus(top_candidates: list[dict], debug: bool = False) -> list[dict]:
    if not top_candidates:
        return top_candidates
    
    n = len(top_candidates)
    skill_doc_frequency = Counter()
    candidate_skill_map = {}

    for candidate in top_candidates:
        tier_a_skills = set(_get_tier_a_skills(candidate))
        candidate_skill_map[candidate["candidate_id"]] = tier_a_skills
        for skill in tier_a_skills:
            skill_doc_frequency[skill] +=1

    max_bonus = PHASE3_WEIGHTS["rarity_bonus_max"]

    for c in top_candidates:
        cid = c["candidate_id"]
        tier_a_skills = candidate_skill_map.get(cid, set())

        if not tier_a_skills:
            c["rarity_bonus"] = 0.0
            continue

        idf_scores = []
        for skill in tier_a_skills:
            df = skill_doc_frequency.get(skill, n)
            idf = math.log((n+1)/(df+1))
            idf_scores.append(idf)
        
        avg_idf = sum(idf_scores)/len(idf_scores)
        max_possbile_idf = math.log((n+1)/2)
        normalised = avg_idf/max_possbile_idf if max_possbile_idf>0 else 0.0

        c["rarity_bonus"] = round(min(max_bonus, max(0.0, normalised*max_bonus)), 6)

    return top_candidates

