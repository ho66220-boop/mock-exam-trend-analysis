from pathlib import Path

import numpy as np
import pandas as pd

import dataset_meta
import stats_utils


ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = ROOT / "data" / "processed"
TABLE_DIR = ROOT / "output" / "tables"
REPORT_DIR = ROOT / "output" / "reports"


def load_profiles() -> pd.DataFrame:
    path = TABLE_DIR / "student_group_profiles.csv"
    if not path.exists():
        raise FileNotFoundError("Run scripts/analyze_student_groups.py first.")
    return pd.read_csv(path)


def add_segments(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    upper_cut = df["pre_core_mean"].quantile(2 / 3)
    lower_cut = df["pre_core_mean"].quantile(1 / 3)
    volatility_cut = df["pre_core_std"].median()

    conditions = [
        df["pre_core_mean"] >= upper_cut,
        df["pre_core_mean"] <= lower_cut,
    ]
    df["pre_level"] = np.select(conditions, ["상위권", "하위권"], default="중위권")
    df["volatility_group"] = np.where(
        df["pre_core_std"] >= volatility_cut, "변동성 큼", "변동성 작음"
    )
    df["result_change_group"] = pd.cut(
        df["csat_minus_pre_core_mean"],
        bins=[-999, -5, 5, 999],
        labels=["수능 하락", "유지", "수능 상승"],
    ).astype(str)

    df["segment"] = (
        df["pre_level"]
        + " / "
        + df["strength_label"]
        + " / "
        + df["participation_group"]
        + " / "
        + df["volatility_group"]
    )

    return df


def summarize(df: pd.DataFrame, group_cols: list[str], min_n: int = 1) -> pd.DataFrame:
    rows = []
    grouped = df.groupby(group_cols, dropna=False)
    for keys, group in grouped:
        if not isinstance(keys, tuple):
            keys = (keys,)
        if len(group) < min_n:
            continue
        row = {col: val for col, val in zip(group_cols, keys)}
        row.update(
            {
                "n": len(group),
                "avg_pre_core_mean": group["pre_core_mean"].mean(),
                "avg_pre_volatility": group["pre_core_std"].mean(),
                "avg_csat_core_mean": group["csat_core_mean"].mean(),
                "median_csat_core_mean": group["csat_core_mean"].median(),
                "avg_csat_minus_pre": group["csat_minus_pre_core_mean"].mean(),
                "top_25pct_rate": group["top_25pct_csat"].mean(),
                "rise_rate": (group["result_change_group"] == "수능 상승").mean(),
                "drop_rate": (group["result_change_group"] == "수능 하락").mean(),
                "avg_csat_korean": group["csat_korean"].mean(),
                "avg_csat_math": group["csat_math"].mean(),
                "avg_csat_inquiry": group["csat_inquiry_mean"].mean(),
                "avg_csat_english_grade": group["csat_english_grade"].mean(),
            }
        )
        rows.append(row)
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows).sort_values(
        ["avg_csat_core_mean", "n"], ascending=[False, False]
    )


def build_recommendation_table(df: pd.DataFrame) -> pd.DataFrame:
    detailed = summarize(
        df,
        ["pre_level", "strength_label", "participation_group", "volatility_group"],
        min_n=3,
    )
    if detailed.empty:
        return detailed

    def message(row: pd.Series) -> str:
        notes = []
        if row["avg_csat_core_mean"] >= 85:
            notes.append("수능 결과가 강한 조합")
        elif row["avg_csat_core_mean"] < 75:
            notes.append("보완 관리가 필요한 조합")
        else:
            notes.append("중간권 유지 조합")

        if row["rise_rate"] >= 0.35:
            notes.append("수능 상승 사례 비율 높음")
        if row["drop_rate"] >= 0.30:
            notes.append("수능 하락 위험 관찰")
        if row["volatility_group"] == "변동성 큼":
            notes.append("월별 흔들림 점검 필요")
        if row["strength_label"] == "균형형":
            notes.append("균형 유지 전략 유효")
        elif row["strength_label"] in ["국어형", "수학형", "탐구형"]:
            notes.append("약한 축 보완이 핵심")
        return " / ".join(notes)

    detailed["insight_message"] = detailed.apply(message, axis=1)
    return detailed


def write_report(
    segmented: pd.DataFrame,
    level_summary: pd.DataFrame,
    level_strength: pd.DataFrame,
    level_participation: pd.DataFrame,
    level_volatility: pd.DataFrame,
    recommendations: pd.DataFrame,
) -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    lines = [
        "# 세분화 학생 그룹 인사이트",
        "",
        "## 분류 기준",
        "",
        "- 상위권/중위권/하위권은 수능 이전 모의고사 핵심 평균의 3분위 기준입니다.",
        "- 핵심 평균은 국어, 수학, 탐구1, 탐구2 백분위 평균입니다.",
        "- 강점 유형은 국어/수학/탐구/균형형으로 분류했습니다.",
        "- 응시 횟수는 1-3회, 4-6회, 7회 이상으로 나눴습니다.",
        "- 변동성은 학생별 모의고사 핵심 평균 표준편차의 중앙값 기준으로 나눴습니다.",
        f"- n<{stats_utils.MIN_RELIABLE_N}인 세부 조합은 소표본으로 표시하며, 수치는 참고용입니다.",
        "",
        f"- 분석 대상: {segmented['student_id'].nunique()}명",
        "",
        "## 상/중/하위권별 수능 결과",
        "",
    ]

    for _, row in level_summary.sort_values("avg_pre_core_mean", ascending=False).iterrows():
        lines.append(
            f"- {row['pre_level']}: n={int(row['n'])}, "
            f"수능 이전 평균 {row['avg_pre_core_mean']:.1f}, "
            f"수능 평균 {row['avg_csat_core_mean']:.1f}, "
            f"상위 25% 비율 {row['top_25pct_rate']:.1%}, "
            f"수능 상승률 {row['rise_rate']:.1%}, 하락률 {row['drop_rate']:.1%}"
        )

    lines.extend(["", "## 권역별 강점 유형", ""])
    for level in ["상위권", "중위권", "하위권"]:
        subset = level_strength[level_strength["pre_level"] == level].head(5)
        if subset.empty:
            continue
        lines.append(f"### {level}")
        for _, row in subset.iterrows():
            lines.append(
                f"- {row['strength_label']}: n={int(row['n'])}, "
                f"수능 평균 {row['avg_csat_core_mean']:.1f}, "
                f"상승률 {row['rise_rate']:.1%}, 하락률 {row['drop_rate']:.1%}"
                f"{stats_utils.reliability_tag(row['n'])}"
            )
        lines.append("")

    lines.extend(["## 권역별 응시 횟수", ""])
    for level in ["상위권", "중위권", "하위권"]:
        subset = level_participation[level_participation["pre_level"] == level].head(5)
        if subset.empty:
            continue
        lines.append(f"### {level}")
        for _, row in subset.iterrows():
            lines.append(
                f"- {row['participation_group']}: n={int(row['n'])}, "
                f"수능 평균 {row['avg_csat_core_mean']:.1f}, "
                f"상위 25% 비율 {row['top_25pct_rate']:.1%}"
                f"{stats_utils.reliability_tag(row['n'])}"
            )
        lines.append("")

    lines.extend(["## 변동성별 결과", ""])
    for _, row in level_volatility.sort_values(["pre_level", "volatility_group"]).iterrows():
        lines.append(
            f"- {row['pre_level']} / {row['volatility_group']}: n={int(row['n'])}, "
            f"수능 평균 {row['avg_csat_core_mean']:.1f}, "
            f"수능-수능 이전 평균 {row['avg_csat_minus_pre']:.1f}, "
            f"하락률 {row['drop_rate']:.1%}"
            f"{stats_utils.reliability_tag(row['n'])}"
        )

    lines.extend(["", "## 전달용 핵심 세그먼트", ""])
    for _, row in recommendations.head(12).iterrows():
        lines.append(
            f"- {row['pre_level']} / {row['strength_label']} / "
            f"{row['participation_group']} / {row['volatility_group']}: "
            f"n={int(row['n'])}, 수능 평균 {row['avg_csat_core_mean']:.1f}, "
            f"{row['insight_message']}"
            f"{stats_utils.reliability_tag(row['n'])}"
        )

    lines.extend(
        [
            "",
            "## 해석 주의",
            "",
            "- 그룹별 n이 작은 조합은 학생 지도용 참고 신호로만 사용해야 합니다.",
            "- 응시 횟수는 원인이라기보다 재원 기간, 성실성, 기존 성취도와 섞인 지표입니다.",
            "- 현재 결과는 샘플 데이터의 패턴 요약이며, 개인별 결과 보장은 아닙니다.",
            "",
            "## 생성 파일",
            "",
            "- `output/tables/segmented_student_profiles.csv`",
            "- `output/tables/segment_level_summary.csv`",
            "- `output/tables/segment_level_strength_summary.csv`",
            "- `output/tables/segment_level_participation_summary.csv`",
            "- `output/tables/segment_level_volatility_summary.csv`",
            "- `output/tables/segment_recommendation_table.csv`",
        ]
    )

    lines = dataset_meta.with_header(lines, PROCESSED_DIR)
    (REPORT_DIR / "segmented_student_insights.md").write_text(
        "\n".join(lines), encoding="utf-8"
    )


def main() -> None:
    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    profiles = load_profiles()
    segmented = add_segments(profiles)

    level_summary = summarize(segmented, ["pre_level"])
    level_strength = summarize(segmented, ["pre_level", "strength_label"])
    level_participation = summarize(segmented, ["pre_level", "participation_group"])
    level_volatility = summarize(segmented, ["pre_level", "volatility_group"])
    recommendations = build_recommendation_table(segmented)

    segmented.to_csv(
        TABLE_DIR / "segmented_student_profiles.csv", index=False, encoding="utf-8-sig"
    )
    level_summary.to_csv(
        TABLE_DIR / "segment_level_summary.csv", index=False, encoding="utf-8-sig"
    )
    level_strength.to_csv(
        TABLE_DIR / "segment_level_strength_summary.csv",
        index=False,
        encoding="utf-8-sig",
    )
    level_participation.to_csv(
        TABLE_DIR / "segment_level_participation_summary.csv",
        index=False,
        encoding="utf-8-sig",
    )
    level_volatility.to_csv(
        TABLE_DIR / "segment_level_volatility_summary.csv",
        index=False,
        encoding="utf-8-sig",
    )
    recommendations.to_csv(
        TABLE_DIR / "segment_recommendation_table.csv",
        index=False,
        encoding="utf-8-sig",
    )

    write_report(
        segmented,
        level_summary,
        level_strength,
        level_participation,
        level_volatility,
        recommendations,
    )

    print(f"students={segmented['student_id'].nunique()}")
    print(f"report={REPORT_DIR / 'segmented_student_insights.md'}")


if __name__ == "__main__":
    main()
