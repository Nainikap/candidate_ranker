"""
config/jd_config.py
───────────────────
Single source of truth for everything derived from the JD.
To adapt this system to a different role, only this file (and scoring_weights.py)
needs to change — no logic files need to be touched.

JD: Senior AI Engineer — Redrob AI (Series A)
"""

# ── Skill tiers ───────────────────────────────────────────────────────────────
# TIER_A: Must-have. Absence heavily penalizes. Match = strong positive signal.
# TIER_B: Nice-to-have. Presence boosts but absence doesn't penalize.
# TIER_C: Neutral/adjacent. Minor positive at best.
# TIER_D: Anti-signal. JD explicitly doesn't want CV/Speech/Robotics specialists.

SKILL_TIERS = {
    "TIER_A": [
        # Embeddings & retrieval (absolute must-have per JD)
        "embeddings", "embedding", "sentence-transformers", "sentence transformers",
        "bge", "e5", "openai embeddings", "text embeddings",
        # Vector databases (must-have per JD)
        "faiss", "pinecone", "weaviate", "qdrant", "milvus", "opensearch",
        "elasticsearch", "vector database", "vector db", "vector search",
        "hybrid search", "hybrid retrieval", "dense retrieval", "semantic search",
        # Retrieval & ranking (core of the role)
        "rag", "retrieval augmented generation", "retrieval-augmented",
        "information retrieval", "ranking", "re-ranking", "reranking",
        "learning to rank", "ltr", "bm25",
        # Evaluation frameworks (explicitly called out in JD)
        "ndcg", "mrr", "map", "mean average precision", "mean reciprocal rank",
        "ranking evaluation", "eval framework", "offline evaluation",
        "a/b testing", "ab testing",
        # Core language
        "python",
        # LLMs in production context
        "llm", "large language model", "llms",
    ],

    "TIER_B": [
        # Fine-tuning (nice-to-have per JD)
        "lora", "qlora", "peft", "fine-tuning", "fine tuning", "finetuning",
        "instruction tuning", "rlhf",
        # LLM orchestration (acceptable if paired with deeper experience)
        "langchain", "llamaindex", "llama index", "langsmith",
        # ML infra
        "mlflow", "weights & biases", "wandb", "experiment tracking",
        "model serving", "inference optimization", "triton", "bentoml",
        # Learning-to-rank models
        "xgboost", "lightgbm", "lambdamart", "ranknet",
        # NLP fundamentals
        "nlp", "natural language processing", "transformers", "bert", "roberta",
        "tokenization", "text classification",
        # Cloud & infra (supporting, not primary)
        "aws", "gcp", "azure", "docker", "kubernetes",
        # Data / feature work
        "feature engineering", "feature store", "spark", "kafka",
        # Open source signal
        "open source", "huggingface", "hugging face",
    ],

    "TIER_C": [
        # Data engineering (adjacent, not core)
        "sql", "postgresql", "mysql", "mongodb",
        "airflow", "dbt", "snowflake", "redshift", "bigquery",
        "pyspark", "hadoop", "hive",
        # Generic software engineering
        "rest api", "fastapi", "flask", "django",
        "react", "typescript", "javascript", "node.js",
        "java", "go", "scala", "rust",
        # General ML (not retrieval-specific)
        "scikit-learn", "sklearn", "pandas", "numpy",
        "statistical modeling", "regression", "classification",
        "apache beam", "celery", "redis",
    ],

    "TIER_D": [
        # Explicit anti-signals — CV/Speech/Robotics without NLP/IR
        "computer vision", "image classification", "object detection",
        "image segmentation", "yolo", "cnn", "convolutional",
        "speech recognition", "asr", "tts", "text to speech",
        "speech synthesis", "whisper", "wav2vec",
        "robotics", "ros", "slam", "autonomous",
        "gans", "generative adversarial", "diffusion models", "stable diffusion",
        "image generation", "midjourney",
        # Pure data visualization / BI
        "tableau", "power bi", "looker", "grafana",
        # Design tools
        "photoshop", "figma", "illustrator", "canva",
        # Marketing / non-tech
        "seo", "marketing", "crm", "salesforce",
    ],
}

# Flat lookup: skill_name_lower → tier string
# Built once at import time for O(1) lookup during scoring
SKILL_TIER_LOOKUP: dict[str, str] = {}
for tier, skills in SKILL_TIERS.items():
    for skill in skills:
        SKILL_TIER_LOOKUP[skill.lower()] = tier


# ── Tier weights for scoring ───────────────────────────────────────────────────
TIER_WEIGHTS = {
    "TIER_A": 3.0,
    "TIER_B": 1.5,
    "TIER_C": 0.2,
    "TIER_D": -1.0,
    "UNKNOWN": 0.0,
}

# ── Proficiency multipliers ────────────────────────────────────────────────────
PROFICIENCY_WEIGHTS = {
    "advanced":     1.0,
    "intermediate": 0.6,
    "beginner":     0.3,
}

# ── Assessment score thresholds (verified vs self-reported) ───────────────────
ASSESSMENT_CREDIBILITY = {
    "boost":   {"min_score": 70, "multiplier": 1.2},   # verified competence
    "neutral": {"min_score": 50, "multiplier": 1.0},
    "penalty": {"min_score":  0, "multiplier": 0.7},   # claimed advanced, scored low
}

# ── TF-IDF query — synthesized from JD's must-have and context ────────────────
TFIDF_QUERY = (
    "senior ML engineer production embeddings vector search RAG retrieval "
    "augmented generation ranking NDCG evaluation product company shipped "
    "real users Python FAISS Elasticsearch hybrid retrieval fine-tuning LLM "
    "inference at scale applied machine learning recommendation system search"
)

# BM25 query focuses only on skills
BM25_SKILLS_QUERY = (
    "embeddings faiss pinecone weaviate qdrant milvus elasticsearch "
    "vector search hybrid search rag retrieval ranking ndcg mrr python "
    "lora fine-tuning nlp transformers xgboost bm25 information retrieval"
)

# ── Role family definitions ───────────────────────────────────────────────────
# Used by title_cluster.py — assigns each candidate to a family
# Lower BM25/TF-IDF threshold = easier to pass Phase 1
ROLE_FAMILIES = {
    "ML_ENGINEER": {
        "keywords": [
            "ml engineer", "machine learning engineer", "ai engineer",
            "applied scientist", "research engineer", "mlops", "ml platform",
            "nlp engineer", "applied ml", "applied ai",
        ],
        "tfidf_threshold": 0.08,
        "bm25_threshold":  0.10,
    },
    "DATA_SCIENTIST": {
        "keywords": [
            "data scientist", "research scientist", "quantitative researcher",
            "decision scientist", "analytics engineer",  # if ML-heavy analytics
        ],
        "tfidf_threshold": 0.10,
        "bm25_threshold":  0.12,
    },
    "SOFTWARE_ENGINEER": {
        "keywords": [
            "software engineer", "backend engineer", "sde", "swe",
            "full stack", "fullstack", "platform engineer",
            "infrastructure engineer", "devops", "site reliability",
        ],
        "tfidf_threshold": 0.14,
        "bm25_threshold":  0.16,
    },
    "DATA_ENGINEER": {
        "keywords": [
            "data engineer", "etl", "pipeline engineer",
            "analytics engineer",  # if data-infra focused
            "spark engineer", "dbt",
        ],
        "tfidf_threshold": 0.13,
        "bm25_threshold":  0.15,
    },
    "NON_TECH": {
        "keywords": [
            "manager", "operations", "marketing", "sales", "hr", "recruiter",
            "designer", "product manager", "business analyst", "consultant",
            "finance", "accounting", "legal", "content",
        ],
        "tfidf_threshold": 0.22,   # very high bar — almost all should be eliminated
        "bm25_threshold":  0.25,
    },
}

# ── Company classification ─────────────────────────────────────────────────────
# Used by hard_rules.py (services-only elimination) and trajectory_scorer.py
SERVICES_COMPANIES = [
    "tcs", "tata consultancy", "infosys", "wipro", "accenture", "cognizant",
    "capgemini", "tech mahindra", "hcl", "hcl technologies", "mindtree",
    "mphasis", "hexaware", "ltimindtree", "lti", "persistent systems",
    "niit technologies", "zensar", "mastech", "igate", "patni",
    "syntel", "kpit", "cyient", "birlasoft", "infotech enterprises",
]

# Keywords in company description / industry that signal product company
PRODUCT_COMPANY_SIGNALS = [
    "saas", "b2b", "b2c", "product", "startup", "series a", "series b",
    "series c", "venture", "funded", "users", "platform", "marketplace",
    "consumer", "enterprise software",
]

# Top-tier companies — get a quality bonus in trajectory scoring
TOP_TIER_COMPANIES = [
    "google", "meta", "microsoft", "amazon", "apple", "netflix", "uber",
    "airbnb", "stripe", "databricks", "snowflake", "openai", "anthropic",
    "deepmind", "cohere", "mistral", "hugging face", "huggingface",
    "flipkart", "swiggy", "zomato", "phonepe", "razorpay", "meesho",
    "cred", "groww", "zepto", "nykaa", "dream11", "byju", "unacademy",
    "ola", "paytm", "myntra", "freshworks", "zoho", "browserstack",
]

# ── Location scoring ───────────────────────────────────────────────────────────
LOCATION_SCORES = {
    "preferred": {
        "cities": ["pune", "noida"],
        "score": 1.0,
    },
    "acceptable": {
        "cities": [
            "mumbai", "delhi", "ncr", "gurgaon", "gurugram",
            "hyderabad", "bangalore", "bengaluru", "kolkata",
            "chennai", "ahmedabad", "jaipur",
        ],
        "score": 0.75,
    },
    "india_other": {
        "score": 0.50,   # anywhere else in India, willing to relocate
    },
    "india_no_relocate": {
        "score": 0.30,   # India but not preferred city, not willing to relocate
    },
    "outside_india": {
        "score": 0.05,   # JD explicitly does not sponsor visas
    },
}

INDIA_COUNTRY_VARIANTS = [
    "india", "in", "bharat", "IN",
]

# ── Notice period scoring ──────────────────────────────────────────────────────
NOTICE_PERIOD_SCORES = [
    (0,   30,  1.00),   # can buy out, ideal
    (31,  60,  0.65),
    (61,  90,  0.40),
    (91,  120, 0.25),
    (121, 999, 0.10),
]

# ── Experience range ───────────────────────────────────────────────────────────
IDEAL_YOE_MIN = 5
IDEAL_YOE_MAX = 9

YOE_SCORE_MAP = [
    (0,   3,   0.30),   # too junior
    (3,   5,   0.70),   # slightly under
    (5,   9,   1.00),   # ideal band
    (9,   12,  0.85),   # slightly over
    (12,  15,  0.65),
    (15,  99,  0.45),   # significantly overqualified
]

# ── Behavioral signal thresholds ──────────────────────────────────────────────
RECENCY_SCORES = [
    (0,   30,  1.00),
    (31,  90,  0.80),
    (91,  180, 0.50),
    (181, 365, 0.25),
    (366, 9999, 0.05),
]

GITHUB_SCORES = {
    -1:    -0.10,   # not connected — mild penalty for AI role
    (0,3): 0.00,
    (4,7): 0.10,
    (8,10): 0.20,
}

# ── Hard multipliers (applied after weighted sum) ─────────────────────────────
MULTIPLIERS = {
    "honeypot_triggers": {
        0: 1.00,
        1: 0.50,
        2: 0.15,
        3: 0.05,    # 3+ triggers → near-zero
    },
    "services_only":       0.30,   # entire career at IT services, no product co
    "outside_india_hard":  0.10,   # outside India + unwilling to relocate
    "non_tech_title":      0.15,   # NON_TECH family + no compensating ML skills
    "pure_research":       0.35,   # only academic/research, no production deploy
    "recent_llm_only":     0.40,   # < 12 months AI, only LangChain/OpenAI wrappers
}

# ── Production language keywords (for career description text) ────────────────
PRODUCTION_LANGUAGE = {
    "positive": [
        "production", "deployed", "real users", "at scale", "shipped",
        "millions", "serving", "inference", "live system", "product",
        "launched", "in production", "real-time", "latency", "throughput",
        "billions", "requests per second", "rps", "users",
    ],
    "negative": [
        "arxiv", "paper", "academic", "research only", "benchmark only",
        "never deployed", "side project only", "kaggle only",
        "theoretical", "simulation",
    ],
}

# ── Seniority level mapping (for arc scoring) ─────────────────────────────────
SENIORITY_LEVELS = {
    0: ["intern", "trainee", "apprentice", "fresher"],
    1: ["junior", "associate", "entry", "graduate"],
    2: ["engineer", "analyst", "developer", "scientist", "specialist"],
    3: ["senior", "sr.", "sr "],
    4: ["staff", "lead", "tech lead", "technical lead"],
    5: ["principal", "director", "distinguished", "fellow", "vp", "head of"],
}

# Flat reverse lookup: keyword → level int
SENIORITY_LOOKUP: dict[str, int] = {}
for level, keywords in SENIORITY_LEVELS.items():
    for kw in keywords:
        SENIORITY_LOOKUP[kw.lower()] = level

# ── Honeypot detection thresholds ────────────────────────────────────────────
HONEYPOT = {
    "tenure_inflation_ratio":        1.4,    # claimed > actual × this → trigger
    "advanced_skill_min_months":     6,      # advanced with < 6 months → suspicious
    "advanced_skill_min_count":      3,      # ≥3 such skills → trigger
    "assessment_advanced_max_score": 45,     # advanced but scored < 45 → mismatch
    "assessment_mismatch_count":     2,      # ≥2 such mismatches → trigger
    "perfect_signal_threshold":      3,      # ≥3 "too perfect" signals → trigger
    "max_realistic_skills_advanced": 10,     # >10 skills all advanced = suspicious
}