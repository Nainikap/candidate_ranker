"""
phase3_rerank/honeypot_detector.py
─────────────────────────────────────
The most important file in this project.
 
6-rule logical consistency engine. Each rule independently checks for
an "impossible" pattern in the candidate's profile. Triggers are counted,
not OR'd — graduated penalty based on how many rules fire.

RULE 1: Tenure impossibility
  Claimed years_of_experience wildly exceeds sum of career_history durations.
 
RULE 2: Graduation timeline impossibility
  Candidate started working before (or unreasonably close to) graduating.
 
RULE 3: Skill inflation
  Multiple skills claimed "advanced" with near-zero duration_months.
 
RULE 4: Assessment-proficiency contradiction
  Claims "advanced" proficiency but verified assessment score is very low.
 
RULE 5: Statistically impossible perfection
  Cluster of suspiciously perfect/round signals across multiple fields.
 
RULE 6: Company tenure vs founding year impossibility
  years_at_company exceeds company's age (when founding year is inferrable).
"""
 
from config.jd_config import HONEYPOT
from utils.text_cleaner import clean_skill
 
def _tenure_impossibility(candidate: dict) -> bool:
    profile = candidate.get("profile", {})
    career = candidate.get("career_history", [])
    claimed_yrs = profile.get("years_of_experience", 0) or 0

    if claimed_yrs <= 0:
        return False
    total_months = sum(r.get("duration_months", 0) or 0 for r in career)
    if total_months==0:
        return False
    claimed_months = claimed_yrs*12
    tolerance = HONEYPOT["tenure_inflation_ratio"] 

    return claimed_months > (total_months*tolerance)

def _extract_Start_year(date_str :str|None) -> int|None:
    if not date_str or len(date_str)<4:
        return None
    try:
        return int(date_str[:4])
    except ValueError:
        return None
    
def _graduation_impossibility(candidate: dict) -> bool:

    education = candidate.get("education", [])
    career    = candidate.get("career_history", [])

    if not education or not career:
        return False
    
    grad_years = [e.get("end_year") for e in education if e.get("end_year")]
    if not grad_years:
        return False
    latest_grad_yr = max(grad_years)

    start_yr = [
        _extract_Start_year(r.get("start_date")) 
        for r in career
    ]

    start_years = [y for y in start_years if y is not None]
    if not start_years:
        return False
    
    earliest_job_yr = min(start_years)
    return earliest_job_yr < (latest_grad_yr-1)

def _skill_inflame(candidate: dict) -> bool:

    skills = candidate.get("skills", [])
    min_months = HONEYPOT["advanced_skill_min_months"]   
    min_count  = HONEYPOT["advanced_skill_min_count"]

    count = 0
    for skill in skills:
        prof     = (skill.get("proficiency") or "").lower()
        duration = skill.get("duration_months", 0) or 0
        if prof == "advanced" and duration < min_months:
            count += 1
 
    return count >= min_count

def _assessment_contradiction(candidate: dict) -> bool:
    skills = candidate.get("skills", [])
    signals = candidate.get("redrob_signals", {}) or {}
    assessments = signals.get("skill_assessment_scores", {}) or {}

    if not assessments:
        return False
    
    max_score   = HONEYPOT["assessment_advanced_max_score"]   
    min_count   = HONEYPOT["assessment_mismatch_count"] 

    count =0
    for skill in skills:
        name = skill.get("name", "")
        prof = (skill.get("proficiency") or "").lower()
        if prof!= "advanced":
            continue
        score = assessments.get(name)
        if score is not None and score>= 0 and score < max_score:
            count+=1

    return count>= min_count

def _too_perfect(candidate: dict) -> bool:
    signals = candidate.get("redrob_signals", {}) or {}
    skills = candidate.get("skills", [])

    perfect_sign = 0
    gh = signals.get("github_activity_score", -1)
    if gh is not None and gh>=9.8:
        perfect_sign+=1
    
    complete = signals.get("profile_completeness_score", 0) or 0
    if complete > 99.5:
        perfect_sign+=1

    assessments = signals.get("skill+assessment_score", {}) or {}
    if assessments:
        scores = [v for v in assessments.values() if v is not None and v >= 0]
        if scores and all(s > 95 for s in scores):
            perfect_sign += 1

    max_real = HONEYPOT["max_realistic_skills_advanced"]
    advanced_count = sum(
        1 for s in skills if (s.get("proficiency") or "").lower() == "advanced"
    )
    if advanced_count > max_real:
        perfect_sign+=1

    # Interview completion rate AND offer acceptance rate both perfect
    icr = signals.get("interview_completion_rate", -1)
    oar = signals.get("offer_acceptance_rate", -1)

    if icr is not None and oar is not None and icr>=0.95 and oar>=0.95:
        perfect_sign +=1

    threshold = HONEYPOT["perfect_signal_threshold"]
    return perfect_sign >= threshold

def _company_fake(candidate: dict) -> bool:
    career = candidate.get("career_history", [])

    for role in career:
        founded = role.get("company_founded_year")
        if founded is None:
            continue

        duration = (role.get("duration_months", 0) or 0)/12
        start_yr = _extract_Start_year(role.get("start_date"))
        if start_yr is None:
            continue

        company_age_at_start = start_yr - founded
        if company_age_at_start < 0:
            return True
        
        if duration > (start_yr -founded +5):
            return True
    
    return False

RULES = [
    ("tenure_impossibility",        _tenure_impossibility),
    ("graduation_impossibility",    _graduation_impossibility),
    ("skill_inflation",             _skill_inflame),
    ("assessment_contradiction",    _assessment_contradiction),
    ("too_perfect",                 _too_perfect),
    ("company_founding_impossible", _company_fake)
]

def detect_honeypot(candidate: dict) -> bool:

    from config.jd_config import MULTIPLIERS
 
    triggered = []
    for rule, fn in RULES:
        try:
            if fn(candidate):
                triggered.append(rule)
        except Exception:
            continue
    trigger_count =len(triggered)

    mult_map = MULTIPLIERS["honeypot_triggers"]
    if trigger_count >=3:
        multiplier = mult_map[3]
    else:
        multiplier = mult_map.get(trigger_count, 1.0)

    return {
        "trigger_count": trigger_count,
        "triggered_rules": triggered,
        "multiplier": multiplier,
    }