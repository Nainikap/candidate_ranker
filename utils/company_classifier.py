"""
utils/company_classifier.py
────────────────────────────
Classify a company name as: services | product | research | top_tier | unknown.
Used by both hard_rules.py (services-only elimination) and
trajectory_scorer.py (product ratio + company quality bonus).
Single source of truth — no duplicate logic.
"""
 
from functools import lru_cache
from utils.text_cleaner import clean_company
from config.jd_config import (
    SERVICES_COMPANIES,
    PRODUCT_COMPANY_SIGNALS,
    TOP_TIER_COMPANIES,
)

_SERVICES_SET = {clean_company(c) for c in SERVICES_COMPANIES}
_TOP_TIER_SET = {clean_company(c) for c in TOP_TIER_COMPANIES}

_RESEARCH_KEYWORDS = [
    "university", "college", "institute", "iit", "iim", "nit", "bits",
    "research lab", "research centre", "research center", "labs",
    "academia", "academic", "phd", "postdoc",
]
 
_PRODUCT_KEYWORDS = [
    "saas", "b2b", "b2c", "startup", "series", "funded",
    "platform", "marketplace", "consumer", "app",
]

CompanyType = str

@lru_cache(maxsize=4096)
def classify_company(
    company_name: str |None,
    industry: str | None=None,
    company_size: str | None=None,

) -> CompanyType:
     """
    Classify a company into a type category.
 
    Args:
        company_name: Raw company name string
        industry:     Industry label from profile (e.g. "IT Services")
        company_size: Size bucket (e.g. "10001+", "201-500")
 
    Returns:
        One of: "top_tier", "services", "research", "product", "unknown"
    """
     
     name_clean = clean_company(company_name or "")
     industry_clean = (industry or "").lower()

     #if company is in top tier company then ignore that it is a service company
     for top in _TOP_TIER_SET:
          if top and top in name_clean:
               return "top_tier"
    
     #services check
     for svc in _SERVICES_SET:
          if svc and svc in name_clean:
               return "services"
          
     #industry label signals
     if any(kw in industry_clean for kw in [
          "it services", "consulting", "outsourcing", "staffing", "bpo", "kpo"
     ]):
          return "services"
     #large company with 10k+ size
     if company_size == "10001+" and not any(
          kw in name_clean for kw in _PRODUCT_KEYWORDS
     ):
          pass
     #research check
     if any(kw in name_clean for kw in _RESEARCH_KEYWORDS):
        return "research"
 
     if any(kw in industry_clean for kw in ["education", "research", "academic"]):
        return "research"
     
     #product company check
     if any(kw in industry_clean for kw in [
        "software", "saas", "fintech", "edtech", "healthtech", "e-commerce",
        "internet", "technology", "consumer", "media",
    ]):
        return "product"
 
     if any(kw in name_clean for kw in _PRODUCT_KEYWORDS):
        return "product"
     
     return "unknown"

def is_services_only(career_history: list[dict]) -> bool:
    """
    Return True if the candidate's ENTIRE career history is at services companies.
    A single product/top-tier role in their history = not services-only.
    """
    if not career_history:
        return False
    
    for role in career_history:
        company = role.get("comoany", "")
        industry = role.get("industry", "")
        size     = role.get("company_size", "")
        ctype    = classify_company(company, industry, size)
        if ctype in ("product", "top_tier"):
            return False
        
    return True

def get_product_ratio(career_history: list[dict]) -> float:
    """
    Fraction of total career months spent at product or top-tier companies.
    Used by trajectory_scorer for product_ratio feature.
    """

    if not career_history:
        return 0.0
 
    total_months   = 0
    product_months = 0
 
    for role in career_history:
        duration = role.get("duration_months", 0) or 0
        company  = role.get("company", "")
        industry = role.get("industry", "")
        size     = role.get("company_size", "")
        ctype    = classify_company(company, industry, size)
 
        total_months += duration
        if ctype in ("product", "top_tier"):
            product_months += duration
 
    if total_months == 0:
        return 0.0
 
    return product_months / total_months

def get_company_quality_score(career_history: list[dict]) -> float:
    """
    Score [0, 1] reflecting the overall quality of companies in career history.
    Top-tier: 1.0, product: 0.7, unknown: 0.4, services: 0.2, research: 0.3
    Returns the weighted average by duration.
    """
    quality_map = {
        "top_tier": 1.0,
        "product":  0.7,
        "unknown":  0.4,
        "research": 0.3,
        "services": 0.2,
    }

    if not career_history: return 0.3

    weighted_sum = 0.0
    total_months = 0

    for role in career_history:
        duration = role.get("duration_months", 0) or 0
        company  = role.get("company", "")
        industry = role.get("industry", "")
        size     = role.get("company_size", "")
        ctype    = classify_company(company, industry, size)
        quality = quality_map.get(ctype, 0.4)

        weighted_sum += duration*quality
        total_months += duration

    if total_months ==0:
        return 0.3
    
    return weighted_sum/total_months
     