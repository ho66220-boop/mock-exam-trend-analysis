"""Shared dataset-source metadata helpers.

`preprocess_excel.py` writes a manifest recording which source (real raw vs
public dummy) produced `data/processed/`, along with row/student counts and a
timestamp. Every report-writing script stamps a header block from this manifest
so that a report can never silently mix real and demo numbers again.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROCESSED_DIR = ROOT / "data" / "processed"
MANIFEST_NAME = "dataset_manifest.json"


def manifest_path(processed_dir: Path | None = None) -> Path:
    base = Path(processed_dir) if processed_dir is not None else DEFAULT_PROCESSED_DIR
    return base / MANIFEST_NAME


def write_manifest(processed_dir: Path, data: dict) -> Path:
    processed_dir = Path(processed_dir)
    processed_dir.mkdir(parents=True, exist_ok=True)
    path = processed_dir / MANIFEST_NAME
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def load_manifest(processed_dir: Path | None = None) -> dict | None:
    path = manifest_path(processed_dir)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def header_lines(processed_dir: Path | None = None) -> list[str]:
    """Markdown blockquote lines describing the data source of this report."""
    m = load_manifest(processed_dir)
    if not m:
        return [
            "> ⚠️ **데이터 출처 미상** — `scripts/preprocess_excel.py`를 먼저 실행해 "
            "`data/processed/dataset_manifest.json`을 생성하세요.",
            "",
        ]
    source = m.get("source", "unknown")
    is_real = source == "raw"
    banner = "🔴 실제 원본 데이터 (비공개)" if is_real else "🟡 공개용 더미(데모) 데이터"
    return [
        f"> **데이터 출처:** {banner} · `source={source}` · 파일 `{m.get('source_file', '?')}`",
        f"> **표본:** 전체 {m.get('clean_students', '?')}명 · "
        f"수능결과 {m.get('csat_students', '?')}명 · 전체기록 {m.get('clean_rows', '?')}건 · "
        f"수능이전기록 {m.get('pre_rows', '?')}건",
        f"> **전처리 생성:** {m.get('generated_at', '?')}",
        "",
    ]


def with_header(lines: list[str], processed_dir: Path | None = None) -> list[str]:
    """Insert the source header block right after a report's `# title` line."""
    header = header_lines(processed_dir)
    if lines and lines[0].lstrip().startswith("#"):
        return [lines[0], ""] + header + lines[1:]
    return header + list(lines)
