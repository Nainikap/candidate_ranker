"""
reasoning/reasoning_generator.py
───────────────────────────────────
Generates reasoning strings for the final top N candidates.
 
CRITICAL DESIGN PRINCIPLE: reasoning is generated FROM the feature scores
already computed in Phase 2/3 — it never re-reads or re-interprets raw JSON.
This keeps it fast (no LLM calls, no re-parsing) and ensures the stated
reasoning is always consistent with the actual score that was assigned.
 
Template structure (per the target output format):
  "[LEAD]; [SKILLS/COMPANY context]. [CONCERN if exists]. [LOCATION if relevant]."
 
Rules:
  - Never mention a skill that scored below TIER_B
  - Always state the top concern honestly if one exists
  - Keep under ~40 words
  - Use actual computed values — years, skill names, company names
"""
 
from config.jd_config import SKILL_TIER_LOOKUP, ROLE_FAMILIES
from utils.text_cleaner import clean_skill, extract_city
from utils.company_classifier import classify_company
 
def _get_top_skills(candidate: dict, max_skills: int=2) -> list[str]:
    skills = candidate.get("skills", [])
    scored =[]
    tier_priority = {"TIER_A":2, "TIER_B":1}
    prof_priority = {"advanced": 2, "intermediate": 1, "beginner": 0}

    for skill in skills:
        raw_name = skill.get("name", "")
        norm_name = clean_skill(raw_name)
        tier = SKILL_TIER_LOOKUP.get(norm_name, "UNKNOWN")
        if tier not in ("TIER_A", "TIER_B"):
            continue

        prof = (skill.get("proficiency") or "beginner").lower()
        duration = skill.get("duration_months", 0) or 0

        priority = (
            tier_priority.get(tier, 0),
            prof_priority.get(prof, 0),
            duration,
        )
        scored.append((priority, raw_name))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [name for _, name in scored[:max_skills]]

def _get_company_phrase(candidate: dict) -> str|None:
    profile = candidate.get("profile", {})
    company = profile.get("current_company", "")
    industry = profile.get("current_industry", "")

    if not company:
        return None
    ctype = classify_company(company, industry)
    if ctype =="top_tier":
        return f"at {company}"
    if ctype == "product":
        return f"at {company} (product company)"
    
    return None

def _get_years_phrase(candidate: dict) -> str:
    years = candidate.get("profile", {}).get("years_of_experience")
    if years is None:
        return None
    years_int = round(float(years))
    return f"{years_int} years"

def _get_title_phrase(candidate: dict) -> str:
    title = candidate.get("profile", {}).get("current_title", "")
    return title if title else "Candidate"

def _identify_top_concern(candidate: dict) -> str|None:
    """
    Identify the single most relevant concern about this candidate,
    derived from already-computed scores. Priority order matters:
    honeypot > notice period > location > low behavioral > low skill.
    """
    scores  = candidate.get("scores", {})
    signals = candidate.get("redrob_signals", {}) or {}
    profile = candidate.get("profile", {})

    if candidate.get("honeypot_trigger_count", 0)>0:
        return "profile shows inconsistencies worth verifying in interview"
    notice = signals.get("notice_period_days")
    if notice is not None and notice >=90:
        return f"notice period {notice} days"
    elif notice is not None and notice>=60:
        return f"notice period {notice} days"
    
    location = profile.get("location", "")
    country  = profile.get("country", "")
    city = extract_city(location)
    preferred = {"pune", "noida"}
    acceptable = {
        "mumbai", "delhi", "ncr", "gurgaon", "gurugram", "hyderabad",
        "bangalore", "bengaluru", "kolkata", "chennai",
    }
    willing = signals.get("willing_to_relocate", True)

    if city not in preferred and city not in acceptable:
        if willing:
            return f"based in {city.title()}, open to relocation" if city else None
        else:
            return f"based in {city.title()}, relocation unconfirmed" if city else None
        
    last_active = signals.get("last_active_date")
    if last_active and last_active<"2026-01-01":
        return "limited recent platform activity"
    
    rr = signals.get("recruiter_response_rate")
    if rr is not None and rr<0.2:
        return "low recruiter response rate historically"
    if scores.get("skill_relevance", 1.0) <0.35:
        return "skills are adjacent rather than core to the role"
    
    return None

def _build_lead(candidate: dict) -> str:
    """Build the strongest opening statement from title + years + top skills."""
    title = _get_title_phrase(candidate)
    years = _get_years_phrase(candidate)
    top_skills = _get_top_skills(candidate, max_skills=2)
 
    parts = [title]
    if years:
        parts.append(f"for {years}")
 
    if top_skills:
        skill_str = " and ".join(top_skills)
        parts.append(f"building {skill_str}" if len(top_skills) > 0 else "")
 
    return " ".join(p for p in parts if p)

def _build_company_phrase(candidate: dict) -> str|None:
    company_phrase = _get_company_phrase(candidate)
    if company_phrase:
        return f"experience {company_phrase}"
    return None
def _build_location_phrase(candidate: dict) -> str|None:
    profile = candidate.get("profile", {})
    location = profile.get("location", "")
    city = extract_city(location)
    signals = candidate.get("redrob_signals", {}) or {}

    if city in {"Pune", "Noida"}:
        return f"{city.title()}-based"
    if signals.get("willing_to_relocate") and city:
        return f"{city.title()}-based, willing to relocate"
    return None

def _build_reasoning(candidate: dict, rank: int) -> str|None:
    final_score = candidate.get("final_score", 0.0)
    scores      = candidate.get("scores", {})

    if final_score<0.45 and scores.get("skill_relevance", 1.0)<0.4:
        return(
            "Adjacent skills only — likely below cutoff but included as "
            "final filler given experience and engagement signals."
        )
    lead = _build_lead(candidate)
    company_clause = _build_company_phrase(candidate)
    location_clause = _build_location_phrase(candidate)
    concern = _identify_top_concern(candidate)

    sentence_parts = [lead]

    if company_clause:
        sentence_parts[-1] = sentence_parts[-1] + f" {company_clause}"

    main_sentence = "; ".join(filter(None, [sentence_parts[0]]))

    final_test = main_sentence.strip()
    if not final_text.endswith((".", ";")):
        final_text += ";"

    if location_clause and not concern:
        final_text += f" {location_clause}."
    else:
        final_text = final_text.rstrip(";") + "."
    if concern:
        final_text = final_text.rstrip(".")
        final_text += f". {concern.capitalize()}."
    return final_text

def generate_reasoning(ranked_cand: list[dict],
                       debug: bool = False,
) -> list[dict]:
    for candidate in ranked_cand:
        rank = candidate.get("rank", 0)
        candidate["reasoning"] = _build_reasoning(candidate, rank)
    if debug:
        print("  [Reasoning] Sample outputs:")
        for c in ranked_cand[:3]:
            print(f"    #{c['rank']} {c['candidate_id']}: {c['reasoning']}")
        print("    ...")
        if len(ranked_cand) > 1:
            last = ranked_cand[-1]
            print(f"    #{last['rank']} {last['candidate_id']}: {last['reasoning']}")

    return ranked_cand