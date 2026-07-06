"""Canonical exam-name metadata.

Parses an exam name into month / provider / official flag and produces a
trend label plus a numeric sort key. This replaces the fragile
`name.split("월")[0] + "월"` logic that collapsed the two September exams
(9월 사설 + 9월 평가원) into a single point and mislabeled 교육청/사설 exams.
"""
from __future__ import annotations

import re

_MONTH_RE = re.compile(r"(\d+)\s*월")


def parse_month(name: str) -> int | None:
    m = _MONTH_RE.search(str(name))
    return int(m.group(1)) if m else None


def is_csat(name: str) -> bool:
    return "수능" in str(name)


def provider(name: str) -> str:
    """Coarse exam provider: 수능 / 평가원(official) / 사설(private incl. 교육청)."""
    s = str(name)
    if "수능" in s:
        return "수능"
    if "평가원" in s:
        return "평가원"
    return "사설"


def is_official(name: str) -> bool:
    """Official = 평가원-administered (6월/9월 모평) or the 수능 itself."""
    return provider(name) in ("평가원", "수능")


def trend_label(name: str) -> str:
    """Short, unique-per-exam label for monthly trend axes.

    September carries both a 사설 and a 평가원 exam in this calendar, so those
    two are disambiguated; every other month maps to a plain 'N월'.
    """
    if is_csat(name):
        return "수능"
    month = parse_month(name)
    if month is None:
        return str(name)
    if month == 9:
        return "9월(평)" if provider(name) == "평가원" else "9월(사)"
    return f"{month}월"


def label_sort_key(label: str) -> int:
    """Chronological sort key for a trend_label. Scale: month*10 (+1 for 평가원)."""
    if "수능" in str(label):
        return 9990
    m = _MONTH_RE.search(str(label))
    if not m:
        return 9980
    month = int(m.group(1))
    provider_rank = 1 if "평" in str(label) else 0
    return month * 10 + provider_rank
