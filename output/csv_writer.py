"""
output/csv_writer.py
─────────────────────
Validates the final ranked list and writes the output CSV.

Validation checks (per the competition brief):
  - Scores must be monotonically decreasing (rank 1 > rank 2 > ... > rank N)
  - Honeypot rate in top 100 must not exceed 10% (Stage 3 disqualification filter)
  - No honeypot should appear in top 10 (strong signal of a working system)
  - No NON_TECH role family in top 20
  - candidate_id must be present and unique

Tie-break rule:
  - If two or more consecutive candidates have the exact same final_score
    (after rounding to 3 decimal places, matching the CSV's displayed
    precision), they are ordered by candidate_id ascending. This guarantees
    a fully deterministic, reproducible ranking — re-running the pipeline
    on the same input always produces byte-identical output, and judges
    never see an arbitrary/unstable ordering among tied scores.

Output format (exact columns from the brief):
  candidate_id, rank, score, reasoning
"""

import csv
from pathlib import Path


def _apply_tie_break(ranked: list[dict]) -> list[dict]:
    """
    Re-sort the ranked list so that ties in final_score are broken by
    candidate_id ascending, then re-assign rank 1..N accordingly.

    Ties are detected on the score AS DISPLAYED (rounded to 3 decimals),
    since that's the precision written to the CSV — two candidates that
    differ only beyond the 3rd decimal would otherwise look tied to a
    human or automated grader reading the file, but sort inconsistently
    run-to-run if left to float comparison or insertion order.
    """
    def _sort_key(c: dict):
        displayed_score = round(c.get("final_score", 0.0), 3)
        return (-displayed_score, c.get("candidate_id", ""))

    tie_broken = sorted(ranked, key=_sort_key)

    for i, c in enumerate(tie_broken, 1):
        c["rank"] = i

    return tie_broken


def _validate_monotonic_scores(ranked: list[dict]) -> list[str]:
    """
    Check scores are non-increasing by rank. Returns list of warning strings.

    Compares scores at the CSV's displayed precision (3 decimals), matching
    _apply_tie_break's tie-detection precision. A strict <= comparison is
    used (not <), since legitimate ties — now ordered by candidate_id via
    the tie-break — are expected and should not be flagged as violations.
    """
    warnings = []
    for i in range(1, len(ranked)):
        prev_score = round(ranked[i - 1].get("final_score", 0.0), 3)
        curr_score = round(ranked[i].get("final_score", 0.0), 3)
        if curr_score > prev_score:
            warnings.append(
                f"Score not monotonic at rank {i+1}: "
                f"{ranked[i]['candidate_id']}={curr_score:.3f} > "
                f"{ranked[i-1]['candidate_id']}={prev_score:.3f}"
            )
    return warnings


def _validate_honeypot_rate(ranked: list[dict], top_n: int = 100) -> tuple[float, list[str]]:
    """
    Compute honeypot rate in top N. Returns (rate_pct, warnings).
    Per the brief: rate > 10% in top 100 = disqualification.
    """
    warnings = []
    pool = ranked[:top_n]
    if not pool:
        return 0.0, warnings

    flagged = sum(1 for c in pool if c.get("honeypot_trigger_count", 0) > 0)
    rate = flagged / len(pool) * 100

    if rate > 10.0:
        warnings.append(
            f"DISQUALIFICATION RISK: honeypot rate in top {top_n} is "
            f"{rate:.1f}% (exceeds 10% threshold). {flagged}/{len(pool)} flagged."
        )

    return rate, warnings


def _validate_top10_honeypots(ranked: list[dict]) -> list[str]:
    """Check for honeypots specifically in the top 10."""
    warnings = []
    top10 = ranked[:10]
    flagged = [c for c in top10 if c.get("honeypot_trigger_count", 0) > 0]
    if flagged:
        ids = ", ".join(c["candidate_id"] for c in flagged)
        warnings.append(
            f"{len(flagged)} honeypot(s) in top 10 — strong signal the system "
            f"is reading keywords, not profiles: {ids}"
        )
    return warnings


def _validate_top20_non_tech(ranked: list[dict]) -> list[str]:
    """Check for NON_TECH role family candidates in top 20."""
    warnings = []
    top20 = ranked[:20]
    non_tech = [c for c in top20 if c.get("role_family") == "NON_TECH"]
    if non_tech:
        ids = ", ".join(c["candidate_id"] for c in non_tech)
        warnings.append(
            f"{len(non_tech)} NON_TECH candidate(s) in top 20: {ids}"
        )
    return warnings


def _validate_unique_ids(ranked: list[dict]) -> list[str]:
    """Check candidate_id uniqueness and presence."""
    warnings = []
    seen = set()
    for c in ranked:
        cid = c.get("candidate_id")
        if not cid:
            warnings.append("Found candidate with missing candidate_id")
            continue
        if cid in seen:
            warnings.append(f"Duplicate candidate_id: {cid}")
        seen.add(cid)
    return warnings


def validate_output(ranked: list[dict], debug: bool = False) -> dict:
    """
    Run all validation checks against the final ranked list.

    Returns:
        {
          "passed": bool,
          "honeypot_rate": float,
          "warnings": [str, ...],
          "errors": [str, ...]
        }
    """
    all_warnings = []
    errors = []

    all_warnings.extend(_validate_unique_ids(ranked))
    all_warnings.extend(_validate_monotonic_scores(ranked))
    all_warnings.extend(_validate_top10_honeypots(ranked))
    all_warnings.extend(_validate_top20_non_tech(ranked))

    honeypot_rate, hp_warnings = _validate_honeypot_rate(ranked, top_n=100)
    for w in hp_warnings:
        if "DISQUALIFICATION" in w:
            errors.append(w)
        else:
            all_warnings.append(w)

    passed = len(errors) == 0

    if debug or all_warnings or errors:
        print("  [Validation] Results:")
        print(f"    Honeypot rate (top 100): {honeypot_rate:.1f}%")
        for w in all_warnings:
            print(f"    [WARN] {w}")
        for e in errors:
            print(f"    [ERROR] {e}")
        if passed and not all_warnings:
            print("    All checks passed cleanly.")

    return {
        "passed": passed,
        "honeypot_rate": honeypot_rate,
        "warnings": all_warnings,
        "errors": errors,
    }


def write_output(
    ranked: list[dict],
    output_path: Path,
    debug: bool = False,
) -> dict:
    """
    Validate and write the final ranked candidates to CSV.

    Args:
        ranked:      final list of top N candidates with rank, final_score,
                     reasoning attached
        output_path: destination CSV path
        debug:       print verbose validation output

    Returns:
        Validation result dict (see validate_output)
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    ranked = _apply_tie_break(ranked)

    validation = validate_output(ranked, debug=debug)

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, quoting=csv.QUOTE_MINIMAL)
        writer.writerow(["candidate_id", "rank", "score", "reasoning"])

        for c in ranked:
            writer.writerow([
                c.get("candidate_id", ""),
                c.get("rank", ""),
                f"{c.get('final_score', 0.0):.3f}",
                c.get("reasoning", ""),
            ])

    if debug:
        print(f"  [Output] Wrote {len(ranked)} rows to {output_path}")

    return validation