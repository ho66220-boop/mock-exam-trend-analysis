"""Lightweight regression checks for the analysis pipeline.

Runs the full pipeline on the deterministic sample data (seeded generator) and
asserts a set of invariants so that a refactor can't silently break the numbers
or reintroduce fixed bugs (9월 collapse, benefit-rate NaN, collinear importance,
missing source/reliability labels).

    python scripts/check_pipeline.py            # run sample pipeline, then check
    python scripts/check_pipeline.py --no-run   # check existing outputs only
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
PROCESSED = ROOT / "data" / "processed"
TABLES = ROOT / "output" / "tables"
REPORTS = ROOT / "output" / "reports"

_failures: list[str] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {name}" + (f" — {detail}" if detail and not condition else ""))
    if not condition:
        _failures.append(name)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-run", action="store_true", help="Check existing outputs, don't re-run.")
    args = parser.parse_args(argv)

    if not args.no_run:
        subprocess.run(
            [sys.executable, str(SCRIPTS / "run_all.py"), "--source", "sample", "--skip-ppt"],
            check=True,
        )

    # --- manifest: deterministic sample counts ---
    manifest = json.loads((PROCESSED / "dataset_manifest.json").read_text(encoding="utf-8"))
    check("manifest source is sample", manifest.get("source") == "sample", str(manifest.get("source")))
    check("sample clean_students == 180", manifest.get("clean_students") == 180, str(manifest.get("clean_students")))
    check("sample csat_students == 137", manifest.get("csat_students") == 137, str(manifest.get("csat_students")))

    # --- analysis base size ---
    groups = pd.read_csv(TABLES / "student_group_profiles.csv")
    check("student_group_profiles has 137 rows", len(groups) == 137, str(len(groups)))

    # --- September no longer collapses ---
    trend = pd.read_csv(TABLES / "monthly_level_percentile_trend.csv")
    months = set(trend["month"].unique())
    check("September split into 사/평", {"9월(사)", "9월(평)"}.issubset(months), str(sorted(months)))

    # --- model sanity: baseline negative, best core clearly positive ---
    models = pd.read_csv(TABLES / "model_comparison.csv")
    core = models[models["target"] == "csat_core_mean"]
    baseline_r2 = core[core["model"] == "Mean baseline"]["cv_r2_mean"].iloc[0]
    best_r2 = core["cv_r2_mean"].max()
    check("mean baseline R2 < 0", baseline_r2 < 0, f"{baseline_r2:.3f}")
    check("best core R2 > 0.5", best_r2 > 0.5, f"{best_r2:.3f}")

    # --- importance uses the decorrelated feature set (no composite means) ---
    importance = pd.read_csv(TABLES / "core_model_permutation_importance.csv")
    feats = set(importance["feature"])
    check("importance excludes pre_core_mean (collinear)", "pre_core_mean" not in feats)
    check("importance includes pre_core_latest", "pre_core_latest" in feats)

    # --- benefit_rate is NaN-safe and reports its denominator ---
    timing = pd.read_csv(TABLES / "inquiry_switch_timing_summary.csv")
    check("timing has n_post_benefit column", "n_post_benefit" in timing.columns)
    valid_rates = timing["benefit_rate_post"].dropna()
    check(
        "benefit_rate_post within [0,1]",
        bool(((valid_rates >= 0) & (valid_rates <= 1)).all()),
    )

    # --- labeling: source banner, survivorship, reliability tags present ---
    final_md = (REPORTS / "final_insight_report.md").read_text(encoding="utf-8")
    check("final report has source banner", "데이터 출처:" in final_md)
    check("final report has survivorship caution", "생존편향" in final_md)
    group_md = (REPORTS / "student_group_insights.md").read_text(encoding="utf-8")
    check("small groups flagged", "소표본" in group_md)

    print()
    if _failures:
        print(f"{len(_failures)} check(s) FAILED: {', '.join(_failures)}")
        return 1
    print("All checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
