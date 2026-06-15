import argparse
import sys
from pathlib import Path
 
from utils.timer import Timer
from utils.data_loader import stream_candidates, load_all_candidates
from phase1_filter.orchestrator import run_phase1
from phase2_scorer.orchestrator import run_phase2
from phase3_ranker.orchestrator import run_phase3
from reasoning.reason_generator import generate_reasoning
from output.csv_writer import write_output
 
def parse_args():
    parser = argparse.ArgumentParser(
        description="Redrob Intelligent Candidate Ranker — CPU-only, no API calls"
    )
    parser.add_argument(
        "--candidates",
        type=str,
        default="data/candidates.jsonl",
        help="Path to candidates JSONL file (one JSON object per line)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="results/ranked_output.csv",
        help="Path for output CSV",
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=100,
        help="Number of top candidates to output (default: 100)",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Print verbose per-phase diagnostics",
    )
    return parser.parse_args()

def main():
  args = parse_args()

  candidates_path = Path(args.candidates)
  output_path = Path(args.output)

  if not candidates_path.exists():
     print(f"[ERROR] Candidates file not found: {candidates_path}")
     sys.exit(1)
    
  output_path.parent.mkdir(parents=True, exist_ok=True)

  global_timer = Timer("total pipeline")
  global_timer.start()
  
  # ── Phase 1: Filter 100K → dynamic shortlist ──────────────────────────────
  print("\n[PHASE 1] Loading & filtering candidates...")
  t1 = Timer("Phase 1")
  t1.start()

   # Stream all candidates into memory as lightweight dicts for Phase 1
    # Each dict contains only fields needed for filtering — not full JSON

  all_candidates = load_all_candidates(candidates_path, debug=args.debug)
  print(f"  Loaded {len(all_candidates):,} candidates from disk")

  phase1_results = run_phase1(all_candidates, debug=args.debug)
  t1.stop()

  print(f"  Phase 1 shortlist: {len(phase1_results):,} candidates")
  print(f"  Phase 1 time: {t1.elapsed:.1f}s")

  if len(phase1_results)==0:
    print("[ERROR] Phase 1 returned 0 candidates. Check JD config or input data.")
    sys.exit(1)

  # ── Phase 2: Deep score shortlist
  print(f"\n[PHASE 2] Deep scoring {len(phase1_results):,} candidates...")
  t2 = Timer("Phase 2")
  t2.start()

  phase2_results = run_phase2(phase1_results, debug=args.debug)
  t2.stop()

  phase2_results.sort(key=lambda x: x["final_score"], reverse=True)
  top200 = phase2_results[:200]

  print(f"  Phase 2 top score:  {top200[0]['final_score']:.4f}")
  print(f"  Phase 2 #200 score: {top200[-1]['final_score']:.4f}")
  print(f"  Phase 2 time: {t2.elapsed:.1f}s")

  #phase 3: re-rank top 200 to 100
  print(f"\n[PHASE 3] Re-ranking top 200 → final top {args.top_n}...")
  t3 = Timer("Phase 3")
  t3.start()

  phase3_reults = run_phase3(top200, all_candidates, debug=args.debug)
  final_top = phase3_reults[:args.top_n]
  t3.stop()

  print(f"  Final top score:  {final_top[0]['final_score']:.4f}")
  print(f"  Final #{args.top_n} score: {final_top[-1]['final_score']:.4f}")
  print(f"  Phase 3 time: {t3.elapsed:.1f}s")

  # ── Reasoning: generate strings for top N 
  print(f"\n[REASONING] Generating reasoning for top {args.top_n}...")
  t4 = Timer("Reasoning")
  t4.start()

  final_top = generate_reasoning(final_top, debug=args.debug)
  t2.stop()
  print(f"  Reasoning time: {t4.elapsed:.1f}s")

  print(f"\n[OUTPUT] Writing results to {output_path}...")
  write_output(final_top, output_path, debug=args.debug)

  #summary
  global_timer.stop()

  if global_timer.elapsed > 240:
     print(f"\n[WARN] Runtime {global_timer.elapsed:.0f}s is close to 300s budget.")
  elif global_timer.elapsed > 300:
     print(f"\n[ERROR] Runtime exceeded 300s budget: {global_timer.elapsed:.0f}s")

  print()
  _print_preview(final_top[:5])

def _print_preview(top5):
   print("print preview: ")
   for c in top5:
      print(
        f"  #{c['rank']:>3}  {c['candidate_id']}  "
        f"score={c['final_score']:.3f}  "
        f"{c.get('reasoning','')[:80]}..."
      ) 
   print()

if __name__ == "__main__":
    main()
   