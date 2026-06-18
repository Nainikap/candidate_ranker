"""
phase2_scorer/behavioral_scorer.py
────────────────────────────────────
Feature Group D: Behavioral & Availability Score
 
Axes:
  D1. Recency (days since last_active_date)
  D2. Engagement signals (open_to_work, response rate, response time,
                          interview completion)
  D3. GitHub & external validation
  D4. Profile credibility (verified contacts, completeness, linkedin)
"""
 
from datetime import datetime, timezone
from config.jd_config import RECENCY_SCORES, GITHUB_SCORES
from config.scoring_weights import BEHAVIORAL_WEIGHTS


_TODAY = datetime.now(tz=timezone.utc).replace(tzinfo=None)

def _days_since(datestr: str | None) -> int|None:
    if not datestr:
        return None
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            dt = datetime.strptime(datestr[:19], fmt)
            return max(0, (_TODAY -dt).days)
        except ValueError:
            continue
    return None

def _recency_score(signals: dict) -> float:
    last_active = signals.get("last_active_date")
    days = _days_since(last_active)

    if days is None:
        return 0.4
    
    for lo, hi, score in RECENCY_SCORES:
        if lo<= days <= hi:
            return score
        
    return 0.05

def _engagement_score(signals: dict) -> float:
    score=0.5

    if signals.get("open_to_work_flag") is True:
        score+= 0.10
    elif signals.get("open_to_work_flag") is False:
        score -= 0.10

    rr = signals.get("recruiter_response_data", -1)
    if rr>=0:
        if rr> 0.5:
            score+=0.10
        elif rr<0.2:
            score-=0.10

    rt = signals.get("avg_response_time", -1)
    if rt>=0:
        if rt < 24:
            score += 0.10
        elif rt > 72:
            score -= 0.05

    icr = signals.get("interview_completion_rate", -1)
    if icr >= 0:
        if icr > 0.7:
            score += 0.05
        elif icr < 0.4:
            score -= 0.05
    
    return min(1.0, max(0.0, score))

def _github_score(signals: dict)-> float:
    gh = signals.get("github_activity_score", -1)
    if gh is None:
        gh=-1
    if gh== -1:
        return 0.5 + GITHUB_SCORES[-1]
    
    if 0<= gh <= 3:
        return 0.5+0.0
    elif gh <= 7:
        return 0.5 + 0.10
    else:
        return 0.7
    
def _credibility_score(signals: dict) -> float:
    score=0.5

    if signals.get("verified_email"):
        score += 0.05
    if signals.get("verified_phone"):
        score += 0.05
    if signals.get("linkedin_connected"):
        score += 0.03
    
    completeness = signals.get("profile_completeness_score", 50) or 50
    score += (completeness / 100)*0.10
    return min(1.0, max(0.0, score))

def score_behavioral(candidate: dict) -> float:
    signals = candidate.get("redrob_signals", {}) or {}

    w = BEHAVIORAL_WEIGHTS
    score = (
        w["recency"]*_recency_score(signals)
        + w["engagement"]         * _engagement_score(signals)
      + w["github_activity"]    * _github_score(signals)
      + w["profile_credibility"]* _credibility_score(signals)
    )

    return round(min(1.0, max(0.0, score)), 6)