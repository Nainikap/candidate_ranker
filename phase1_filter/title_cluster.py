"""
phase1_filter/title_cluster.py
───────────────────────────────
Step 2 of Phase 1: assign each candidate to a role family.
Role family determines the TF-IDF / BM25 threshold they must clear in Phase 1.
 
ML_ENGINEER    → lowest threshold (most likely fit, easiest to pass)
DATA_SCIENTIST → slightly higher
SOFTWARE_ENG   → higher (title misaligned, needs stronger text signal)
DATA_ENGINEER  → higher
NON_TECH       → very high (almost all eliminated by hard_rules already)
UNKNOWN        → mid threshold (benefit of the doubt)
"""
 
from utils.text_cleaner import clean_title
from config.jd_config import ROLE_FAMILIES
 
_FAMILY_KEYWORD_MAP: list[tuple[str, str]] = []
for family_name, config in ROLE_FAMILIES.items():
    for kw in config["keywords"]:
        _FAMILY_KEYWORD_MAP.append((kw.lower(), family_name))
 
# Sort by keyword length descending — match longer phrases first
# ("machine learning engineer" before "engineer")
_FAMILY_KEYWORD_MAP.sort(key=lambda x: len(x[0]), reverse=True)
 
_DEFAULT_THRESHOLDS = {
    "tfidf_threshold": 0.11,
    "bm25_threshold":  0.13,
}

def assign_role_family(candidate: dict) -> dict:
    """
    Assign a role_family and retrieval thresholds to a candidate.
    Mutates candidate in-place (adds 'role_family', 'tfidf_threshold',
    'bm25_threshold' keys) and returns it.
    """

    profile     = candidate.get("profile", {})
    curr_title_raw   = profile.get("current_title", "")
    curr_title_clean = clean_title(curr_title_raw)
    headline    = profile.get("headline", "").lower()

    matched_family = None

    for keyword, family_name in _FAMILY_KEYWORD_MAP:
        if keyword in curr_title_clean or keyword in headline:
            matched_family = family_name
            break
    if matched_family is None:
        candidate["role_family"] = "UNKNOWN"
        candidate["tfidf_threshold"]  = _DEFAULT_THRESHOLDS["tfidf_threshold"]
        candidate["bm25_threshold"]   = _DEFAULT_THRESHOLDS["bm25_threshold"]
    else:
        family_config = ROLE_FAMILIES[matched_family]
        candidate["role_family"] = ROLE_FAMILIES[matched_family]
        candidate["tfidf_threshold"]  = family_config["tfidf_threshold"]
        candidate["bm25_threshold"]   = family_config["bm25_threshold"]

    return candidate

def assign_role_families(candidates: list[dict], debug:bool=False) -> list[dict]:
    """
    Assign role families to all candidates.
    Returns the same list with role_family field added to each.
    """

    for candidate in candidates:
        assign_role_family(candidate)

    if debug:
        from collections import Counter
        counts = Counter(c["role_family"] for c in candidates)
        print("  [Title Cluster] Role family distribution:")
        for family, count in counts.most_common():
            pct = count / len(candidates) * 100
            print(f"    {family:<20} {count:>7,}  ({pct:.1f}%)")

    return candidates
