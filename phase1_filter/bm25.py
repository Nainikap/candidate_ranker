"""
phase1_filter/bm25_retrieval.py
────────────────────────────────
Step 4 of Phase 1: BM25 retrieval on skills-only text.
BM25 penalizes document length — a candidate listing 40 skills doesn't
unfairly outscore one with 8 highly relevant ones.
 
Skills text is weighted by proficiency level before indexing.
Returns candidate_id → normalized_bm25_score mapping.
"""
 
import numpy as np
from rank_bm25 import BM25Okapi
 
from utils.text_cleaner import build_skills_text, clean
from config.jd_config import BM25_SKILLS_QUERY
 
def _tokenise(text: str) -> list[str]:
    return clean(text).split()

def run_bm25_retrieval(
        candidates: list[dict],
        debug: bool=False,

) -> dict[str, float]:
     """
    Build BM25 index on skills-only text, query with JD skills.
 
    Args:
        candidates: list of candidate dicts (post hard-rules, with role_family set)
 
    Returns:
        Dict mapping candidate_id → normalized_bm25_score (float, 0–1)
        Only includes candidates whose score >= their role_family bm25_threshold.
    """
     
     if not candidates: return{}

     ids = [c["candidate_id"] for c in candidates]
     corpus = [_tokenise(build_skills_text(c)) for c in candidates]
     thresh = [c.get("bm25_threshold", 0.13) for c in candidates]

     bm25 = BM250kapi(corpus)

     query_tokens = _tokenise(BM25_SKILLS_QUERY)

     raw_scores = bm25.get_scores(query_tokens)
    #normalise
     max_score = raw_scores.max()
     if max_score > 0:
        norm_scores = raw_scores / max_score
     else:
        norm_scores = raw_scores

     results: dict[str, float] ={}
     passed =0

     for cid, score, threshold in zip(ids, norm_scores, thresh):
        if score >= threshold:
            results[cid] = float(score)
            passed += 1
 
     if debug:
        print(f"  [BM25] Passed threshold: {passed:,} / {len(candidates):,}")
        if len(norm_scores) > 0:
            print(f"  [BM25] Score range: "
                  f"min={norm_scores.min():.4f} "
                  f"mean={norm_scores.mean():.4f} "
                  f"max={norm_scores.max():.4f}")
     
     return results

