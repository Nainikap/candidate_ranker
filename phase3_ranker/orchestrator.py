"""
phase3_rerank/phase3_orchestrator.py
───────────────────────────────────────
Orchestrates Phase 3:
  1. Run honeypot detection on all 200 candidates
  2. Apply honeypot multiplier to final_score
  3. Compute rarity bonus within the 200-candidate pool
  4. Apply rarity bonus as additive lift
  5. Re-sort and return final ranked list
 
This phase NEVER runs on the full 100K or even the 15K shortlist —
only on the top 200 survivors of Phase 2, by design (keeps it fast).
"""

from utils.timer import Timer
from phase3_ranker.honeypot_detect import detect_honeypot
from phase3_ranker.tfidf_rarity_bonus import compute_rarity_bonus
 
def run_phase3(
        top200: list[dict],
        all_candidates: list[dict] | None=None,
        debug: bool =False
) -> list[dict]:
    """
    Run Phase 3 re-ranking on the top 200 candidates from Phase 2.
 
    Args:
        top200:         top 200 candidates sorted by Phase 2 final_score
        all_candidates: full candidate pool (unused directly here, kept for
                         API compatibility / future raw-text re-verification)
        debug:           print diagnostics
 
    Returns:
        Re-ranked list, sorted descending by final final_score.
    """

    if not top200:
        return []
    
    t = Timer("Phase3-Honeypot")
    t.start()
    honeypot_flagged = 0
    for candidate in top200:
        result = detect_honeypot(candidate)
        candidate["honeypot_trigger_count"] = result["trigger_count"]
        candidate["honeypot_trigger_rules"] = result["triggered_rules"]
        candidate["honeypot_multiplier"]      = result["multiplier"]

        if result["trigger_count"]>0:
            honeypot_flagged+=1

        candidate["final_score"] = round(
            candidate["final_score"] * result["multiplier"], 6
        )
    
    top200 = compute_rarity_bonus(top200, debug=debug)
    for candidate in top200:
        candidate["final_score"] = round(
            min(1.0, candidate["final_score"]+candidate.get("rarity_bonus", 0.0)), 6
        )

    top200.sort(key=lambda x: x["final_score"], reverse=True)

    for i, candidate in enumerate(top200):
        candidate["rank"] = i

