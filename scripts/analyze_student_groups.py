from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = ROOT / "data" / "processed"
TABLE_DIR = ROOT / "output" / "tables"
REPORT_DIR = ROOT / "output" / "reports"

CORE_SUBJECTS = [
    "korean_percentile",
    "math_percentile",
    "inquiry1_percentile",
    "inquiry2_percentile",
]

STRENGTH_LABELS = {
    "korean": "국어형",
    "math": "수학형",
    "inquiry": "탐구형",
    "balanced": "균형형",
    "unclear": "불명확",
}


def load_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    pre = pd.read_csv(PROCESSED_DIR / "pre_csat_records.csv")
    targets = pd.read_csv(PROCESSED_DIR / "csat_targets.csv")
    return pre, targets


def core_mean(df: pd.DataFrame) -> pd.Series:
    return df[CORE_SUBJECTS].mean(axis=1, skipna=True)


def classify_strength(row: pd.Series, margin: float = 5.0) -> str:
    korean = row["pre_korean_mean"]
    math = row["pre_math_mean"]
    inquiry = row["pre_inquiry_mean"]
    values = pd.Series({"korean": korean, "math": math, "inquiry": inquiry}).dropna()
    if len(values) < 2:
        return "unclear"
    top = values.idxmax()
    ordered = values.sort_values(ascending=False)
    if len(ordered) >= 2 and ordered.iloc[0] - ordered.iloc[1] < margin:
        return "balanced"
    return top


def build_student_group_frame(pre: pd.DataFrame, targets: pd.DataFrame) -> pd.DataFrame:
    pre = pre.copy()
    targets = targets.copy()

    pre["is_official"] = pre["exam_name"].str.contains("평가원", na=False)
    pre["pre_core_mean_each_exam"] = core_mean(pre)
    targets["csat_core_mean"] = core_mean(targets)
    targets["csat_inquiry_mean"] = targets[["inquiry1_percentile", "inquiry2_percentile"]].mean(
        axis=1, skipna=True
    )

    grouped = pre.groupby("student_id")
    summary = grouped.agg(
        pre_record_count=("exam_name", "size"),
        private_record_count=("is_official", lambda x: int((~x).sum())),
        official_record_count=("is_official", lambda x: int(x.sum())),
        pre_core_mean=("pre_core_mean_each_exam", "mean"),
        pre_core_latest=("pre_core_mean_each_exam", lambda x: x.dropna().iloc[-1] if x.dropna().size else np.nan),
        pre_core_std=("pre_core_mean_each_exam", lambda x: x.dropna().std(ddof=0)),
        pre_korean_mean=("korean_percentile", "mean"),
        pre_math_mean=("math_percentile", "mean"),
        pre_inquiry1_mean=("inquiry1_percentile", "mean"),
        pre_inquiry2_mean=("inquiry2_percentile", "mean"),
        pre_english_mean=("english_grade", "mean"),
    ).reset_index()

    summary["pre_inquiry_mean"] = summary[["pre_inquiry1_mean", "pre_inquiry2_mean"]].mean(
        axis=1, skipna=True
    )
    summary["strength_type"] = summary.apply(classify_strength, axis=1)
    summary["strength_label"] = summary["strength_type"].map(STRENGTH_LABELS)

    bins = [-1, 3, 6, 99]
    labels = ["적게 응시(1-3회)", "보통 응시(4-6회)", "많이 응시(7회 이상)"]
    summary["participation_group"] = pd.cut(
        summary["pre_record_count"], bins=bins, labels=labels
    ).astype(str)

    merged = summary.merge(
        targets[
            [
                "student_id",
                "track",
                "csat_core_mean",
                "korean_percentile",
                "math_percentile",
                "inquiry1_percentile",
                "inquiry2_percentile",
                "csat_inquiry_mean",
                "english_grade",
            ]
        ].rename(
            columns={
                "korean_percentile": "csat_korean",
                "math_percentile": "csat_math",
                "inquiry1_percentile": "csat_inquiry1",
                "inquiry2_percentile": "csat_inquiry2",
                "english_grade": "csat_english_grade",
            }
        ),
        on="student_id",
        how="inner",
    )

    merged["csat_core_rank_pct"] = merged["csat_core_mean"].rank(pct=True)
    merged["top_25pct_csat"] = merged["csat_core_rank_pct"] >= 0.75
    merged["csat_minus_pre_core_mean"] = merged["csat_core_mean"] - merged["pre_core_mean"]
    return merged.sort_values("csat_core_mean", ascending=False)


def summarize_group(df: pd.DataFrame, column: str) -> pd.DataFrame:
    rows = []
    for group_name, group in df.groupby(column, dropna=False):
        rows.append(
            {
                column: group_name,
                "n": len(group),
                "avg_pre_records": group["pre_record_count"].mean(),
                "avg_pre_core_mean": group["pre_core_mean"].mean(),
                "avg_csat_core_mean": group["csat_core_mean"].mean(),
                "median_csat_core_mean": group["csat_core_mean"].median(),
                "avg_csat_minus_pre": group["csat_minus_pre_core_mean"].mean(),
                "top_25pct_rate": group["top_25pct_csat"].mean(),
                "avg_csat_korean": group["csat_korean"].mean(),
                "avg_csat_math": group["csat_math"].mean(),
                "avg_csat_inquiry": group["csat_inquiry_mean"].mean(),
                "avg_csat_english_grade": group["csat_english_grade"].mean(),
            }
        )
    return pd.DataFrame(rows).sort_values("avg_csat_core_mean", ascending=False)


def cross_summary(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (participation, strength), group in df.groupby(
        ["participation_group", "strength_label"], dropna=False
    ):
        rows.append(
            {
                "participation_group": participation,
                "strength_label": strength,
                "n": len(group),
                "avg_csat_core_mean": group["csat_core_mean"].mean(),
                "top_25pct_rate": group["top_25pct_csat"].mean(),
                "avg_csat_minus_pre": group["csat_minus_pre_core_mean"].mean(),
            }
        )
    return pd.DataFrame(rows).sort_values(
        ["avg_csat_core_mean", "n"], ascending=[False, False]
    )


def write_report(
    student_groups: pd.DataFrame,
    participation: pd.DataFrame,
    strength: pd.DataFrame,
    cross: pd.DataFrame,
) -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    lines = [
        "# 학생 그룹별 수능 결과 인사이트",
        "",
        "## 기준",
        "",
        f"- 분석 대상: 수능 이전 기록과 수능 결과가 모두 있는 {student_groups['student_id'].nunique()}명",
        "- 수능 결과 우수 기준은 국어, 수학, 탐구1, 탐구2 백분위 평균입니다.",
        "- 영어는 등급이라 평균 비교에는 별도 지표로만 포함했습니다.",
        "- 강점 유형은 수능 이전 모의고사 평균에서 국어/수학/탐구 중 5점 이상 앞서는 축으로 분류했습니다.",
        "",
        "## 사설/모의 응시 횟수별 결과",
        "",
    ]

    for _, row in participation.iterrows():
        lines.append(
            f"- {row['participation_group']}: n={int(row['n'])}, "
            f"수능 핵심 평균 {row['avg_csat_core_mean']:.1f}, "
            f"상위 25% 비율 {row['top_25pct_rate']:.1%}, "
            f"수능-수능 이전 평균 차이 {row['avg_csat_minus_pre']:.1f}"
        )

    lines.extend(["", "## 과목 강점 유형별 결과", ""])
    for _, row in strength.iterrows():
        lines.append(
            f"- {row['strength_label']}: n={int(row['n'])}, "
            f"수능 핵심 평균 {row['avg_csat_core_mean']:.1f}, "
            f"상위 25% 비율 {row['top_25pct_rate']:.1%}, "
            f"국/수/탐 평균 {row['avg_csat_korean']:.1f}/"
            f"{row['avg_csat_math']:.1f}/{row['avg_csat_inquiry']:.1f}"
        )

    lines.extend(["", "## 응시량 x 강점 유형 상위 조합", ""])
    for _, row in cross.head(8).iterrows():
        lines.append(
            f"- {row['participation_group']} + {row['strength_label']}: "
            f"n={int(row['n'])}, 수능 핵심 평균 {row['avg_csat_core_mean']:.1f}, "
            f"상위 25% 비율 {row['top_25pct_rate']:.1%}"
        )

    lines.extend(
        [
            "",
            "## 해석 메모",
            "",
            "- 응시 횟수는 성실성/잔류기간/상위권 선별 효과가 섞여 있을 수 있어 인과로 해석하면 안 됩니다.",
            "- 강점 유형은 상담용 분류입니다. 표본 수가 작은 그룹은 방향성 참고용으로만 봐야 합니다.",
            "- 다음 단계에서는 상위권, 하락 위험군, 수능에서 크게 오른 학생을 학생별 태그로 분리하는 것이 좋습니다.",
            "",
            "## 생성 파일",
            "",
            "- `output/tables/student_group_profiles.csv`",
            "- `output/tables/participation_group_summary.csv`",
            "- `output/tables/strength_type_summary.csv`",
            "- `output/tables/participation_x_strength_summary.csv`",
        ]
    )

    (REPORT_DIR / "student_group_insights.md").write_text(
        "\n".join(lines), encoding="utf-8"
    )


def main() -> None:
    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    pre, targets = load_data()
    student_groups = build_student_group_frame(pre, targets)
    participation = summarize_group(student_groups, "participation_group")
    strength = summarize_group(student_groups, "strength_label")
    cross = cross_summary(student_groups)

    student_groups.to_csv(
        TABLE_DIR / "student_group_profiles.csv", index=False, encoding="utf-8-sig"
    )
    participation.to_csv(
        TABLE_DIR / "participation_group_summary.csv", index=False, encoding="utf-8-sig"
    )
    strength.to_csv(
        TABLE_DIR / "strength_type_summary.csv", index=False, encoding="utf-8-sig"
    )
    cross.to_csv(
        TABLE_DIR / "participation_x_strength_summary.csv",
        index=False,
        encoding="utf-8-sig",
    )
    write_report(student_groups, participation, strength, cross)

    print(f"students={student_groups['student_id'].nunique()}")
    print(f"report={REPORT_DIR / 'student_group_insights.md'}")


if __name__ == "__main__":
    main()
