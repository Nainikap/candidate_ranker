"""
utils/data_loader.py
────────────────────
Stream 100K JSONL candidates without loading everything into RAM at once.
load_all_candidates() reads line-by-line and stores only parsed dicts.
Each dict is the full candidate JSON — downstream modules pick what they need.
"""
 
import json
from pathlib import Path
from tqdm import tqdm

def stream_candidates(path: Path):
  """
    Generator: yield one parsed candidate dict per line.
    Skips blank lines and malformed JSON with a warning.
    """
  with open(path, "r", encoding="utf-8") as f:
    for no, line in enumerate(f,1):
      line = line.strip()
      if not line:
        continue
      try:
        yield json.loads(line)
      except json.JSONDecodeError as e:
        print(f"  [WARN] Skipping line {no}: {e}")

def load_all_candidates(path: Path, debug: bool=False) -> list[dict]:
      """
    Load all candidates into a list of dicts.
    Memory estimate: ~200–400 MB for 100K rich profiles.
 
    Each dict has the structure:
      {
        "candidate_id": str,
        "profile": { ... },
        "career_history": [ ... ],
        "education": [ ... ],
        "skills": [ ... ],
        "certifications": [ ... ],
        "redrob_signals": { ... },
      }
    """
      candidates =[]
      path = Path(path)

      if not path.exists():
         raise FileNotFoundError(f"Candidates file not found: {path}")
      
      if debug:
        # Count lines first only for the progress bar total (cheap pass,
        # no JSON parsing, no list materialization of raw lines)
        with open(path, "r", encoding="utf-8") as f:
            total_lines = sum(1 for _ in f)
        print(f"  [DEBUG] Streaming {total_lines:,} lines from {path}")
        progress = tqdm(total=total_lines, desc="  Loading", unit="candidates")
      else:
        progress = None
 
      candidates = []
      for candidate in stream_candidates(path):
        candidates.append(candidate)
        if progress is not None:
            progress.update(1)
 
      if progress is not None:
        progress.close()
 
      return candidates
 

def get_candidate_text_fields(candidate: dict) -> dict:
   """
    Extract only the text fields needed for TF-IDF / BM25 indexing.
    Returns a lightweight dict — avoids carrying full profile into vectorizer.
    """
   profile = candidate.get("profile", {})
   career  = candidate.get("career_history", [])
   skills  = candidate.get("skills", [])

   return {
        "candidate_id": candidate.get("candidate_id", ""),
        "title":        profile.get("current_title", ""),
        "headline":     profile.get("headline", ""),
        "summary":      profile.get("summary", ""),
        "location":     profile.get("location", ""),
        "country":      profile.get("country", ""),
        "company":      profile.get("current_company", ""),
        "industry":     profile.get("current_industry", ""),
        "descriptions": [r.get("description", "") for r in career],
        "role_titles":  [r.get("title", "") for r in career],
        "skill_names":  [s.get("name", "") for s in skills],
        "skill_profs":  [s.get("proficiency", "") for s in skills],
    }

      