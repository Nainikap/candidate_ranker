"""
phase1_filter/phase1_orchestrator.py
─────────────────────────────────────
Orchestrates all Phase 1 steps:
  Step 1: Hard rules       → eliminate obvious misfits
  Step 2: Title clustering → assign role family + retrieval thresholds
  Step 3: TF-IDF retrieval → score on full profile text
  Step 4: BM25 retrieval   → score on skills-only text
  Step 5: Union            → keep candidates passing EITHER retrieval signal
  Step 6: Attach scores    → carry tfidf_score + bm25_score into Phase 2
 
Dynamic sizing: no fixed cutoff — takes whoever clears their threshold.
"""

from utils.timer import Timer
from phase1_filter.hard_rules import apply_hard_rules
from phase1_filter.title_cluster import assign_role_families
from phase1_filter.tf_idf import run_tfidf_retrieval
from phase1_filter.bm25 import run_bm25_retrieval
 
def run_phase1(
        all_candidates: list[dict],
        debug: bool = False,
) -> list[dict]:
        """
    Run the full Phase 1 pipeline.
 
    Args:
        all_candidates: full list of 100K candidate dicts
        debug:          print verbose diagnostics
 
    Returns:
        Shortlisted candidates with phase1 scores attached.
        Size is dynamic — whoever clears retrieval thresholds.
    """
    
    #step 1 hard rules
        survivors, hard_rule_stats = apply_hard_rules(all_candidates, debug=debug)
        if not survivors: return []

    #step 2 title clustering
        survivors = assign_role_families(survivors, debug=debug)

    #step 3 tf-idf 
        tfidf_scores = run_tfidf_retrieval(survivors, debug=debug)
    #step 4 bm25
        bm25_scores = run_bm25_retrieval(survivors, debug=debug)
        
    #union
        tfidf_ids = set(tfidf_scores.keys())
        bm25_ids = set(bm25_scores.keys())
        union_ids = tfidf_ids | bm25_ids

        both_ids   = tfidf_ids & bm25_ids
        only_tfidf = tfidf_ids - bm25_ids
        only_bm25  = bm25_ids  - tfidf_ids

        print(f"  [Union] Both signals:    {len(both_ids):,}")
        print(f"  [Union] TF-IDF only:     {len(only_tfidf):,}")
        print(f"  [Union] BM25 only:       {len(only_bm25):,}")
        print(f"  [Union] Total unique:    {len(union_ids):,}")

        shortlist = []

        for candidate in survivors:
                cid = candidate["candidate_id"]
                if cid not in union_ids:
                        continue
                
                ts = tfidf_scores.get(cid, 0.0)
                bs = bm25_scores.get(cid, 0.0)

                candidate["tfidf_score"]    = ts
                candidate["bm25_score"]     = bs
                candidate["phase1_score"]   = (ts + bs) / 2.0
                candidate["caught_by_both"] = cid in both_ids

                shortlist.append(candidate)

