"""
phase1_filter/hard_rules.py
────────────────────────────
Step 1 of Phase 1: eliminate obvious misfits via O(N) linear scan.
Returns only candidates that pass ALL hard rules.
 
Rules applied (in order of cheapness):
  R1. Location: outside India + unwilling to relocate → eliminate
  R2. Title family: NON_TECH with zero compensating ML skills → eliminate
  R3. Services-only career with zero product experience → eliminate
  R4. Zero TIER_A or TIER_B skill overlap with JD → eliminate
  R5. Current title is purely non-technical domain (marketing/ops/design) → eliminate
"""

from utils.text_cleaner import (
    clean, clean_skill, extract_city, is_india, clean_title
)
from utils.company_classifier import is_services_only
from config.jd_config import (
    SKILL_TIER_LOOKUP,
    ROLE_FAMILIES,
    SERVICES_COMPANIES,
    LOCATION_SCORES,
    INDIA_COUNTRY_VARIANTS,
)

_NON_TECH_KEYWORDS = set(ROLE_FAMILIES["NON_TECH"]["keywords"])
 
_COMPENSATING_ML_SKILLS = {
    # If a NON_TECH title candidate has ANY of these, don't eliminate them
    "python", "embeddings", "embedding", "faiss", "pinecone", "weaviate",
    "qdrant", "milvus", "elasticsearch", "opensearch", "rag",
    "retrieval augmented generation", "vector search", "nlp",
    "large language model", "llm", "fine-tuning", "lora", "transformers",
    "ranking", "information retrieval", "bm25", "sentence-transformers",
}

def _passes_location(candidate: dict) -> bool:
     """
    R1: Eliminate if outside India AND not willing to relocate.
    If country is blank or ambiguous, give benefit of the doubt.
    """
     profile =candidate.get("profile", {})
     signals = candidate.get("redrob_signals", {})
     country = profile.get("country", "")
     location = profile.get("location", "")
     willing = signals.get("willing_to_relocate", True)

     if is_india(country, location):
          return True
     
     if country and not is_india(country, location):
          return False
     
     loc_clean = clean(location)
     if not loc_clean: return True
     indian_cities = []
     for family in LOCATION_SCORES.values():
          indian_cities.extend(family.get("cities", []))

     if any(city in loc_clean for city in indian_cities):
          return True
     if any(v in loc_clean for v in INDIA_COUNTRY_VARIANTS):
          return True
     return False

def _passes_title(candidate: dict) -> bool:
     """
    R2 + R5: Eliminate NON_TECH titles unless they have compensating ML skills.
    Pure marketing/operations/design with no ML exposure → eliminate.
    """
     profile     = candidate.get("profile", {})
     title_raw   = profile.get("current_title", "")
     title_clean = clean_title(title_raw)
     
     is_non_tech = any(kw in title_clean for kw in _NON_TECH_KEYWORDS)

     if not is_non_tech:
          return True
     skills = candidate.get("skills", [])
     for skill in skills:
          skill_name = clean_skill(skill.get("name", ""))
          if skill_name in _COMPENSATING_ML_SKILLS:
               return True
          
     summary = clean(profile.get("summary", ""))
     ml_summary_keywords = [
        "ml", "machine learning", "deep learning", "neural", "embedding",
        "retrieval", "nlp", "llm", "vector", "ranking", "recommendation",
    ]
     
     if any(kw in summary for kw in ml_summary_keywords):
          return True
     
     return False

def _passes_services_check(candidate: dict) -> bool:
     """
    R3: Eliminate if entire career is at services companies with ZERO product exp.
    A single product/top-tier role anywhere in history → keep.
    """
     
     career = candidate.get("career_history", [])
     if not career:
          return False
     
     return not is_services_only(career)

def _passes_skill_overlap(candidate: dict) -> bool:
     """
    R4: Eliminate if candidate has ZERO TIER_A or TIER_B skills.
    Candidates with no overlap whatsoever are irrelevant regardless of title.
    """
     
     skills = candidate.get("skills", [])
     if not skills:
          profile = candidate.get("profile", {})
          summary = clean(profile.get("summary", ""))
          tier_A_keywords = [
            "embedding", "vector", "retrieval", "rag", "faiss", "ranking",
            "nlp", "llm", "elasticsearch", "pinecone",
        ]
          return any(kw in summary for kw in tier_A_keywords)  
     for skill in skills:
          name = clean_skill(skill.get("name", ""))
          tier = SKILL_TIER_LOOKUP.get(name, "UNKNOWN")
          if tier in ("TIER_A", "TIER_B"):
               return True
          
     
     for role in candidate.get("career_history", []):
        desc = clean(role.get("description", ""))
        implicit_signals = [
            "embedding", "vector search", "retrieval", "nlp", "ranking",
            "recommendation", "search engine", "faiss", "elasticsearch",
            "language model", "fine-tun",
        ]
        if any(sig in desc for sig in implicit_signals):
            return True
        
     return False

def apply_hard_rules(
          candidates: list[dict],
          debug: bool=False,
) -> tuple[list[dict], dict]:
     """
    Apply all hard rules to the full candidate list.
 
    Returns:
        survivors: list of candidates that passed all rules
        stats:     dict with per-rule elimination counts for diagnostics
    """
     stats = {
        "total_input":       len(candidates),
        "failed_location":   0,
        "failed_title":      0,
        "failed_services":   0,
        "failed_skill_overlap": 0,
        "survivors":         0,
    }
     
     survivors = []

     for candidate in candidates:
          if not _passes_location(candidate):
               stats["failed_location"] +=1
               continue
          if not _passes_title(candidate):
               stats["failed_title"] +=1
               continue
          if not _passes_services_check(candidate):
               stats["failed_services"] +=1
               continue
          if not _passes_skill_overlap(candidate):
               stats["failed_skill_overlap"] +=1
               continue
          survivors.append(candidate)

     stats["survivors"] = len(survivors)

     if debug:
        total = stats["total_input"]
        print(f"  [Hard Rules] Input:          {total:>7,}")
        print(f"  [Hard Rules] Failed location:{stats['failed_location']:>7,}  "
                f"({stats['failed_location']/total*100:.1f}%)")
        print(f"  [Hard Rules] Failed title:   {stats['failed_title']:>7,}  "
                f"({stats['failed_title']/total*100:.1f}%)")
        print(f"  [Hard Rules] Failed services:{stats['failed_services']:>7,}  "
                f"({stats['failed_services']/total*100:.1f}%)")
        print(f"  [Hard Rules] Failed skills:  {stats['failed_skill_overlap']:>7,}  "
                f"({stats['failed_skill_overlap']/total*100:.1f}%)")
        print(f"  [Hard Rules] Survivors:      {stats['survivors']:>7,}  "
                f"({stats['survivors']/total*100:.1f}%)")
        
     return survivors, stats


     