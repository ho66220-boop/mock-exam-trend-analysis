"""Run the whole analysis pipeline in one command.

    python scripts/run_all.py --source sample     # public demo (default: auto)
    python scripts/run_all.py --source raw         # real private data
    python scripts/run_all.py --source raw --skip-ppt

Only preprocess takes --source; every downstream script reads data/processed,
so the whole run is pinned to one data source and cannot mix real and demo.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"

# README section 4.3 order (dependencies already respected).
ANALYSIS_STEPS = [
    "analyze_insights.py",
    "analyze_student_groups.py",
    "compare_models.py",
    "segment_student_profiles.py",
    "analyze_monthly_mobility.py",
    "analyze_inquiry_switching.py",
    "create_segment_figures.py",
    "build_final_report.py",
]
PPT_STEPS = [
    "build_final_report_ppt.py",
    "build_teacher_ppt.py",
]


def run_step(script: str, args: list[str] | None = None) -> None:
    cmd = [sys.executable, str(SCRIPTS / script), *(args or [])]
    print(f">> {script} {' '.join(args or [])}".rstrip())
    subprocess.run(cmd, check=True)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Run the full mock-exam analysis pipeline.")
    parser.add_argument("--source", choices=["raw", "sample", "auto"], default="auto")
    parser.add_argument("--skip-ppt", action="store_true", help="Skip the PowerPoint builders.")
    args = parser.parse_args(argv)

    run_step("preprocess_excel.py", ["--source", args.source])
    for script in ANALYSIS_STEPS:
        run_step(script)
    if not args.skip_ppt:
        for script in PPT_STEPS:
            run_step(script)

    print("\nPipeline complete.")


if __name__ == "__main__":
    main()
