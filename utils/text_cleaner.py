"""
utils/text_cleaner.py
─────────────────────
Normalize company names, skill names, location strings, title strings.
All functions return lowercase stripped strings for consistent matching.
"""

import re


# ── Generic ───────────────────────────────────────────────────────────────────

def clean(text: str | None) -> str:
    """Lowercase, strip, collapse whitespace."""
    if not text:
        return ""
    return re.sub(r"\s+", " ", str(text).lower().strip())


def clean_list(items: list[str] | None) -> list[str]:
    """Clean a list of strings, drop empties."""
    if not items:
        return []
    return [c for item in items if (c := clean(item))]


# ── Skill names ───────────────────────────────────────────────────────────────

_SKILL_ALIASES = {
    # normalize common variants to canonical form used in jd_config
    "sentence transformers":        "sentence-transformers",
    "sentence_transformers":        "sentence-transformers",
    "openai embedding":             "openai embeddings",
    "vector db":                    "vector database",
    "vector dbs":                   "vector database",
    "vector databases":             "vector database",
    "retrieval augmented":          "retrieval augmented generation",
    "retrieval-augmented generation": "retrieval augmented generation",
    "rag systems":                  "rag",
    "fine tuning":                  "fine-tuning",
    "finetuning":                   "fine-tuning",
    "fine_tuning":                  "fine-tuning",
    "qlora":                        "qlora",
    "q-lora":                       "qlora",
    "weights & biases":             "wandb",
    "weights and biases":           "wandb",
    "hugging face":                 "huggingface",
    "scikit learn":                 "scikit-learn",
    "sklearn":                      "scikit-learn",
    "pyspark":                      "spark",
    "apache spark":                 "spark",
    "elastic search":               "elasticsearch",
    "open search":                  "opensearch",
    "large language model":         "llm",
    "large language models":        "llm",
    "gpt":                          "llm",
    "chatgpt":                      "llm",
    "natural language processing":  "nlp",
    "nlp engineer":                 "nlp",
    "text to speech":               "tts",
    "automatic speech recognition": "asr",
    "speech to text":               "asr",
    "computer vision":              "computer vision",
    "cv":                           "computer vision",  # only if standalone
    "generative adversarial network": "gans",
    "generative adversarial networks": "gans",
    "a/b test":                     "a/b testing",
    "ab test":                      "a/b testing",
    "ab testing":                   "a/b testing",
    "mean average precision":       "map",
    "mean reciprocal rank":         "mrr",
    "learning-to-rank":             "learning to rank",
    "learning to rank":             "learning to rank",
}

def clean_skill(skill: str | None) -> str:
    """Normalize a skill name to its canonical form."""
    s = clean(skill)
    return _SKILL_ALIASES.get(s, s)


# ── Company names ─────────────────────────────────────────────────────────────

_COMPANY_STRIP = re.compile(
    r"\b(pvt|ltd|llc|inc|corp|limited|private|technologies|technology|"
    r"solutions|services|systems|group|global|india|soft|tech|infotech)\b",
    re.IGNORECASE,
)

def clean_company(name: str | None) -> str:
    """
    Normalize company name for matching against known lists.
    'Tata Consultancy Services Ltd.' → 'tata consultancy'
    """
    s = clean(name)
    s = _COMPANY_STRIP.sub("", s)
    return re.sub(r"\s+", " ", s).strip()


# ── Location strings ──────────────────────────────────────────────────────────

_LOCATION_ALIASES = {
    "bengaluru":        "bangalore",
    "new delhi":        "delhi",
    "delhi ncr":        "ncr",
    "gurugram":         "gurgaon",
    "ncr":              "ncr",
    "bombay":           "mumbai",
    "hyderabad india":  "hyderabad",
    "remote india":     "remote",
    "india remote":     "remote",
}

def clean_location(loc: str | None) -> str:
    """Normalize location string to a canonical city name."""
    s = clean(loc)
    # strip country suffix patterns like ", india" or "india" at end
    s = re.sub(r",?\s*(india|in)$", "", s).strip()
    return _LOCATION_ALIASES.get(s, s)


def extract_city(location: str | None) -> str:
    """
    Extract the primary city from a location string.
    'Bangalore, Karnataka, India' → 'bangalore'
    """
    loc = clean(location)
    # take first comma-separated token
    city = loc.split(",")[0].strip()
    return _LOCATION_ALIASES.get(city, city)


def is_india(country: str | None, location: str | None) -> bool:
    """Return True if the candidate appears to be based in India."""
    from config.jd_config import INDIA_COUNTRY_VARIANTS
    country_clean = clean(country)
    if any(v in country_clean for v in INDIA_COUNTRY_VARIANTS):
        return True
    loc_clean = clean(location)
    if any(v in loc_clean for v in INDIA_COUNTRY_VARIANTS):
        return True
    return False


# ── Title strings ─────────────────────────────────────────────────────────────

_TITLE_NOISE = re.compile(
    r"\b(at|@|–|-|and|&|the|with|for|of|in|a|an)\b", re.IGNORECASE
)

def clean_title(title: str | None) -> str:
    """
    Normalize job title for role family matching.
    'Senior ML Engineer @ Google' → 'senior ml engineer'
    """
    s = clean(title)
    # remove company reference (anything after @ or 'at [Company]')
    s = re.sub(r"(@|at\s+\w+).*$", "", s).strip()
    s = _TITLE_NOISE.sub(" ", s)
    return re.sub(r"\s+", " ", s).strip()


# ── Text concatenation for TF-IDF / BM25 ─────────────────────────────────────

def build_profile_text(candidate: dict) -> str:
    """
    Concatenate all textual fields into a single document for TF-IDF.
    Weights important fields by repeating them.
    """
    profile = candidate.get("profile", {})
    parts = []

    # Title repeated 3x — highest signal
    title = clean(profile.get("current_title", ""))
    parts.extend([title] * 3)

    # Headline repeated 2x
    headline = clean(profile.get("headline", ""))
    parts.extend([headline] * 2)

    # Summary
    parts.append(clean(profile.get("summary", "")))

    # Career descriptions
    for role in candidate.get("career_history", []):
        parts.append(clean(role.get("description", "")))
        parts.append(clean(role.get("title", "")))

    # Skill names repeated 2x (skills are strong signal)
    for skill in candidate.get("skills", []):
        skill_name = clean_skill(skill.get("name", ""))
        parts.extend([skill_name] * 2)

    return " ".join(p for p in parts if p)


def build_skills_text(candidate: dict) -> str:
    """
    Build a skills-only document for BM25.
    Weights by proficiency: advanced repeated 3x, intermediate 2x, beginner 1x.
    """
    proficiency_repeats = {"expert": 4, "advanced": 3, "intermediate": 2, "beginner": 1}
    parts = []

    for skill in candidate.get("skills", []):
        name = clean_skill(skill.get("name", ""))
        if not name:
            continue
        repeats = proficiency_repeats.get(
            skill.get("proficiency", "beginner").lower(), 1
        )
        parts.extend([name] * repeats)

    # Also include title words — "ML Engineer" signals skill family
    title = clean_title(candidate.get("profile", {}).get("current_title", ""))
    parts.extend(title.split())

    return " ".join(parts)