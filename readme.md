# Redrob Intelligent Candidate Ranker

A CPU-only, network-off candidate ranking pipeline built for the **Intelligent Candidate Discovery & Ranking Challenge**. Given a 100K-candidate pool and a job description, it produces a ranked shortlist of the top 100 best-fit candidates — complete with scores and human-readable reasoning — in under 5 minutes, without a GPU and without calling any external API.

The system is built around a simple thesis: **a candidate ranker that only does keyword/embedding matching will rank fabricated profiles just as highly as real ones.** This pipeline instead reasons about career trajectory, company quality, behavioral availability, and logical consistency — and explicitly hunts for honeypot profiles with subtly impossible claims (e.g. 8 years at a company founded 2 years ago, "expert" in 12 skills with 0 months of experience in each).

---

## Quick start

```bash
pip install -r requirements.txt

python3 main.py \
  --candidates data/candidates.jsonl \
  --output results/ranked_output.csv \
  --top-n 100
```

Output is a plain CSV at `results/ranked_output.csv`:

```
candidate_id,rank,score,reasoning
CAND_0042871,1,0.987,"Senior AI Engineer with 7 years building RAG and FAISS experience at Flipkart; Bangalore-based, willing to relocate."
CAND_0019884,2,0.973,"ML Engineer with 6 years building Vector Search and Python experience at Razorpay. Notice period 120 days."
...
```

### Input format

`--candidates` expects a **JSONL** file — one JSON object per line, matching the Redrob candidate schema (`profile`, `career_history`, `education`, `skills`, `redrob_signals`). If your data is a single JSON array, convert it first:

```bash
python3 -c "
import json
with open('data/raw.json') as f:
    candidates = json.load(f)
with open('data/candidates.jsonl', 'w') as f:
    for c in candidates:
        f.write(json.dumps(c) + '\n')
"
```

### CLI flags

| Flag           | Default                     | Description                                                                |
| -------------- | --------------------------- | -------------------------------------------------------------------------- |
| `--candidates` | `data/candidates.jsonl`     | Path to input JSONL                                                        |
| `--output`     | `results/ranked_output.csv` | Path for output CSV                                                        |
| `--top-n`      | `100`                       | Number of ranked candidates to output                                      |
| `--debug`      | off                         | Verbose per-phase diagnostics (timing, score distributions, sanity checks) |

---

## Why this approach

Most naive solutions to this problem do: `embed(JD)` → `embed(candidate)` → cosine similarity → rank. That approach has no concept of career trajectory, can't detect logically inconsistent profiles, treats "I know Python" the same as "shipped Python at scale," and is slow on 100K candidates without a GPU.

This pipeline instead:

- Decomposes the JD into structured, weighted requirements (hard must-haves, soft nice-to-haves, explicit anti-signals) once, up front — every scoring decision downstream references this.
- Scores candidates across **independent feature axes** (skills, trajectory, title alignment, behavioral availability, logistics) rather than a single similarity number.
- Runs **two independent retrieval signals** (TF-IDF on full profile text, BM25 on skills-only text) and takes their **union** with role-aware dynamic thresholds — no arbitrary fixed cutoff that risks dropping a strong candidate due to corpus noise.
- Applies a **6-rule logical consistency engine** to the final shortlist that catches fabricated profiles by checking internal consistency (tenure vs. graduation year, claimed proficiency vs. verified assessment scores, statistically impossible perfection clusters) — not by pattern-matching on suspicious keywords.
- Generates reasoning strings **from the computed feature scores**, never by re-reading raw text — this guarantees the stated reasoning is always consistent with the actual score, and keeps the final phase fast.

---

## Pipeline architecture

```
100K candidates (JSONL)
        │
        ▼
┌───────────────────────────────────────────────────────────┐
│ PHASE 1 — Filter & Retrieve (dynamic shortlist, ~8K–20K)  │
│                                                             │
│  1. hard_rules.py        → eliminate obvious misfits       │
│                             (location, non-tech title,     │
│                             services-only career, zero      │
│                             skill overlap)                  │
│  2. title_cluster.py     → assign role family + dynamic     │
│                             TF-IDF/BM25 thresholds per       │
│                             family (ML_ENGINEER gets an     │
│                             easier bar than NON_TECH)        │
│  3. tfidf_retrieval.py   → TF-IDF cosine similarity on       │
│                             full profile text vs. JD query   │
│  4. bm25_retrieval.py    → BM25 on skills-only text          │
│                             (length-normalized, immune to     │
│                             skill-list padding)               │
│  5+6. orchestrator       → UNION of TF-IDF ∪ BM25 survivors,  │
│                             dynamically sized (no fixed N)     │
└───────────────────────────────────────────────────────────┘
        │
        ▼
┌───────────────────────────────────────────────────────────┐
│ PHASE 2 — Deep Score (parallel, joblib)                    │
│                                                             │
│  skill_scorer.py            → tier × proficiency ×          │
│                                depth × credibility           │
│  trajectory_scorer.py       → product-co ratio, seniority   │
│                                arc, production-language       │
│                                detection, title-hop penalty   │
│  title_alignment_scorer.py  → role family fit × YOE          │
│                                calibration vs. JD's 5-9yr band │
│  behavioral_scorer.py       → recency, engagement,            │
│                                GitHub activity, credibility    │
│  logistics_scorer.py        → location + notice period        │
│  orchestrator                → weighted composition +          │
│                                hard multipliers (services-only,│
│                                outside-India, non-tech)         │
└───────────────────────────────────────────────────────────┘
        │
        ▼  top 200 by final_score
┌───────────────────────────────────────────────────────────┐
│ PHASE 3 — Re-rank (top 200 only)                            │
│                                                             │
│  honeypot_detector.py    → 6 independent logical-consistency │
│                             rules, graduated penalty           │
│                             (1 trigger → ×0.35, 3+ → ×0.03)     │
│  tfidf_rarity_bonus.py   → small lift for rare-but-relevant    │
│                             skills within the top-200 pool       │
└───────────────────────────────────────────────────────────┘
        │
        ▼  top 100
┌───────────────────────────────────────────────────────────┐
│ REASONING — generate from features, not raw text             │
└───────────────────────────────────────────────────────────┘
        │
        ▼
┌───────────────────────────────────────────────────────────┐
│ OUTPUT — tie-break, validate, write CSV                      │
│                                                             │
│  csv_writer.py → ties broken by ascending candidate_id;       │
│                  validates monotonic scores, honeypot rate     │
│                  ≤10% in top 100, no honeypot in top 10,        │
│                  no NON_TECH in top 20                            │
└───────────────────────────────────────────────────────────┘
        │
        ▼
results/ranked_output.csv
```

---

## Project structure

```
redrob_ranker/
├── main.py                       # Orchestrates all phases, CLI entry point
│
├── config/
│   ├── jd_config.py               # All JD-derived constants: skill tiers,
│   │                               # company lists, location/notice scoring,
│   │                               # honeypot thresholds. Change the role →
│   │                               # change this file, not the logic.
│   └── scoring_weights.py         # All formula weights in one place
│
├── phase1_filter/
│   ├── hard_rules.py               # O(N) elimination pass
│   ├── title_cluster.py            # Role family assignment
│   ├── tfidf_retrieval.py          # TF-IDF retrieval
│   ├── bm25_retrieval.py           # BM25 retrieval (skills-only)
│   └── phase1_orchestrator.py      # Union logic, dynamic sizing
│
├── phase2_scorer/
│   ├── skill_scorer.py
│   ├── trajectory_scorer.py
│   ├── title_alignment_scorer.py
│   ├── behavioral_scorer.py
│   ├── logistics_scorer.py
│   └── phase2_orchestrator.py      # Weighted composition, parallel (joblib)
│
├── phase3_rerank/
│   ├── honeypot_detector.py        # The most important file in the project
│   ├── tfidf_rarity_bonus.py
│   └── phase3_orchestrator.py
│
├── reasoning/
│   └── reasoning_generator.py      # Feature → human-readable string
│
├── output/
│   └── csv_writer.py               # Tie-break, validation, CSV write
│
├── utils/
│   ├── data_loader.py              # JSONL streaming/loading
│   ├── text_cleaner.py             # Normalization, profile/skills text builders
│   ├── company_classifier.py       # services / product / top_tier / research
│   └── timer.py
│
├── data/                           # Input JSONL (gitignored)
├── results/                        # Output CSV (gitignored)
├── tests/
└── requirements.txt
```

---

## Honeypot detection

The dataset includes ~80 honeypot candidates with subtly impossible profiles. Six independent rules run on the final top-200 shortlist:

| Rule                                | What it catches                                                                                              |
| ----------------------------------- | ------------------------------------------------------------------------------------------------------------ |
| Tenure impossibility                | Claimed `years_of_experience` far exceeds the sum of `career_history` durations                              |
| Graduation timeline impossibility   | Candidate's earliest job start date predates their graduation year                                           |
| Skill inflation                     | Multiple skills claimed "advanced"/"expert" with near-zero `duration_months`                                 |
| Assessment contradiction            | Claims "advanced"/"expert" proficiency but verified `skill_assessment_scores` are very low                   |
| Statistically impossible perfection | Cluster of suspiciously maxed-out signals (GitHub activity, profile completeness, assessment scores all ≥99) |
| Company founding impossibility      | Tenure at a company exceeds the company's age (when inferrable)                                              |

Triggers are **counted, not OR'd** — a graduated penalty multiplier applies based on how many rules fire (1 trigger → ×0.35, 2 → ×0.10, 3+ → ×0.03). This was deliberately tuned aggressive: a single logical impossibility is treated as a strong fabrication signal, not a minor concern, since the competition's Stage 3 filter disqualifies any submission with >10% honeypot rate in the top 100.

---

## Performance

Designed to run well within the 5-minute, CPU-only, no-GPU budget:

| Phase              | Target time | What's happening                                                                             |
| ------------------ | ----------- | -------------------------------------------------------------------------------------------- |
| Phase 1            | ~90–120s    | Hard rules (O(N) scan) + title clustering + TF-IDF/BM25 fit & query on the survivor pool     |
| Phase 2            | ~60–90s     | Parallel (joblib) feature scoring across the dynamic shortlist (typically 8K–20K candidates) |
| Phase 3            | ~5–10s      | Honeypot detection + rarity bonus on top 200 only — by design, never runs on the full pool   |
| Reasoning + Output | ~2–5s       | String generation for top 100, validation, CSV write                                         |

No GPU, no API calls, no external network access required — only `scikit-learn`, `rank-bm25`, `numpy`/`pandas`/`scipy`, and `joblib`.

---

## Tuning

All scoring weights live in `config/scoring_weights.py`; all JD-specific constants (skill tiers, company lists, location preferences, honeypot thresholds) live in `config/jd_config.py`. To adapt this pipeline to a different job description, only these two files need to change — no logic files need to be touched.
