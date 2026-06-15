"""
phase1_filter/tfidf_retrieval.py
─────────────────────────────────
Step 3 of Phase 1: TF-IDF retrieval on full profile text.
Builds a TF-IDF corpus from all surviving candidates after hard rules,
then scores each against the JD query.
 
Returns candidate_id → tfidf_score mapping.
Threshold is per-candidate based on their role_family.
"""

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
 
from utils.text_cleaner import build_profile_text
from config.jd_config import TFIDF_QUERY
 
def run_tfidf_retrieval(
  candidates: list[dict],
  debug: bool=False,
 ) -> dict[str, float]:
    """
    Build TF-IDF index on all candidates, query with JD text.
 
    Args:
        candidates: list of candidate dicts (post hard-rules, with role_family set)
 
    Returns:
        Dict mapping candidate_id → tfidf_score (float, 0–1)
        Only includes candidates whose score >= their role_family threshold.
    """
    if not candidates:
        return {}
    
    if debug:
        print(f"  [TF-IDF] Building corpus from {len(candidates)} candidates...")

    ids = [c["candidate_id"] for c in candidates]
    corpus = [build_profile_text(c) for c in candidates]
    thresh = [c.get("tfidf_threshold", 0.11) for c in candidates]

    n_docs = len(corpus)
    min_df = min(2, max(1, n_docs-1))
    max_df = 0.85 if n_docs>= 10 else 1.0

    vectorizer = TfidfVectorizer(
        ngram_range=(1,2)
        min_df=min_df,
        max_df=max_df,
        sublinear_tf=True,
        max_features=50_000,
        strip_accents="unicode",
        analyzer="word",
        token_pattern=r"[a-z][a-z0-9\-\.\/]+",
    )

    tfidf_matrix = vectorizer.fit_transform(corpus)

    query_vec = vectorizer.transform([TFIDF_QUERY])

    scores = cosine_similarity(query_vec, tfidf_matrix).flatten()

    results: dict[str, float] ={}
    passed=0

    for (cid, score, threshold) in enumerate(zip(ids, scores, thresh)):
        if score>= threshold:
            results[cid] = float(score)
            passed +=1

    if debug:
        print(f"  [TF-IDF] Passed threshold: {passed:,} / {len(candidates):,}")
        if len(scores) > 0:
            print(f"  [TF-IDF] Score range: "
                  f"min={scores.min():.4f} "
                  f"mean={scores.mean():.4f} "
                  f"max={scores.max():.4f}")
            
    return results
 