from pathlib import Path

import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import dataset_meta
import stats_utils

# Students within this many points of a tertile cut can flip level on noise alone.
BOUNDARY_BAND = 2.0


ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = ROOT / "data" / "processed"
TABLE_DIR = ROOT / "output" / "tables"
FIGURE_DIR = ROOT / "output" / "figures"
REPORT_DIR = ROOT / "output" / "reports"

CORE_SUBJECTS = [
    "korean_percentile",
    "math_percentile",
    "inquiry1_percentile",
    "inquiry2_percentile",
]

LEVEL_ORDER = {"하위권": 0, "중위권": 1, "상위권": 2}
LEVEL_COLORS = {"상위권": "#2f80ed", "중위권": "#27ae60", "하위권": "#f2994a"}


def set_korean_font() -> None:
    candidates = ["Malgun Gothic", "맑은 고딕", "Noto Sans CJK KR", "NanumGothic"]
    available = {font.name for font in fm.fontManager.ttflist}
    for name in candidates:
        if name in available:
            plt.rcParams["font.family"] = name
            break
    plt.rcParams["axes.unicode_minus"] = False


def extract_month(exam_name: str) -> str:
    if "수능" in str(exam_name):
        return "수능"
    return str(exam_name).split("월", 1)[0] + "월"


def month_sort_key(month: str) -> int:
    if month == "수능":
        return 12
    try:
        return int(month.replace("월", ""))
    except ValueError:
        return 99


def load_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    clean = pd.read_csv(PROCESSED_DIR / "clean_records.csv")
    segmented = pd.read_csv(TABLE_DIR / "segmented_student_profiles.csv")
    return clean, segmented


def assign_csat_level(segmented: pd.DataFrame) -> pd.DataFrame:
    segmented = segmented.copy()
    lower = segmented["csat_core_mean"].quantile(1 / 3)
    upper = segmented["csat_core_mean"].quantile(2 / 3)
    segmented["csat_level"] = np.select(
        [
            segmented["csat_core_mean"] >= upper,
            segmented["csat_core_mean"] <= lower,
        ],
        ["상위권", "하위권"],
        default="중위권",
    )
    boundary_distance = np.minimum(
        (segmented["csat_core_mean"] - lower).abs(),
        (segmented["csat_core_mean"] - upper).abs(),
    )
    segmented["csat_boundary_distance"] = boundary_distance
    segmented["near_csat_boundary"] = boundary_distance <= BOUNDARY_BAND
    segmented["pre_level_score"] = segmented["pre_level"].map(LEVEL_ORDER)
    segmented["csat_level_score"] = segmented["csat_level"].map(LEVEL_ORDER)
    segmented["level_move"] = segmented["csat_level_score"] - segmented["pre_level_score"]
    segmented["mobility_type"] = np.select(
        [
            segmented["level_move"] > 0,
            segmented["level_move"] < 0,
        ],
        ["상향 이동", "하향 이동"],
        default="유지",
    )
    return segmented


def build_monthly_trend(clean: pd.DataFrame, segmented: pd.DataFrame) -> pd.DataFrame:
    levels = segmented[["student_id", "pre_level"]]
    records = clean.merge(levels, on="student_id", how="inner")
    records = records[~records["is_csat"]].copy()
    records["month"] = records["exam_name"].apply(extract_month)
    records["month_order"] = records["month"].apply(month_sort_key)
    records["core_mean"] = records[CORE_SUBJECTS].mean(axis=1, skipna=True)

    trend = (
        records.groupby(["month_order", "month", "pre_level"], as_index=False)
        .agg(
            n=("student_id", "nunique"),
            record_count=("student_id", "size"),
            avg_core_percentile=("core_mean", "mean"),
            avg_korean=("korean_percentile", "mean"),
            avg_math=("math_percentile", "mean"),
            avg_inquiry1=("inquiry1_percentile", "mean"),
            avg_inquiry2=("inquiry2_percentile", "mean"),
        )
        .sort_values(["month_order", "pre_level"])
    )
    return trend


def build_mobility_summary(segmented: pd.DataFrame, group_cols: list[str]) -> pd.DataFrame:
    rows = []
    for keys, group in segmented.groupby(group_cols, dropna=False):
        if not isinstance(keys, tuple):
            keys = (keys,)
        row = {col: value for col, value in zip(group_cols, keys)}
        row.update(
            {
                "n": len(group),
                "up_rate": (group["mobility_type"] == "상향 이동").mean(),
                "down_rate": (group["mobility_type"] == "하향 이동").mean(),
                "stay_rate": (group["mobility_type"] == "유지").mean(),
                "avg_level_move": group["level_move"].mean(),
                "avg_pre_core_mean": group["pre_core_mean"].mean(),
                "avg_csat_core_mean": group["csat_core_mean"].mean(),
                "avg_csat_minus_pre": group["csat_minus_pre_core_mean"].mean(),
            }
        )
        rows.append(row)
    return pd.DataFrame(rows).sort_values(["up_rate", "avg_level_move", "n"], ascending=False)


def save_monthly_trend_figure(trend: pd.DataFrame) -> None:
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(10, 5.5))
    for level in ["상위권", "중위권", "하위권"]:
        data = trend[trend["pre_level"] == level].sort_values("month_order")
        ax.plot(
            data["month"],
            data["avg_core_percentile"],
            marker="o",
            linewidth=2.4,
            color=LEVEL_COLORS[level],
            label=level,
        )
        for _, row in data.iterrows():
            ax.text(
                row["month"],
                row["avg_core_percentile"] + 0.8,
                f"{row['avg_core_percentile']:.1f}",
                ha="center",
                fontsize=8,
                color=LEVEL_COLORS[level],
            )

    ax.set_title("월별 상/중/하위권 평균 백분위 흐름", fontsize=15, pad=14)
    ax.set_xlabel("시험 월")
    ax.set_ylabel("국어/수학/탐구 평균 백분위")
    ax.set_ylim(55, 100)
    ax.grid(alpha=0.25)
    ax.legend(frameon=False, ncol=3, loc="upper center", bbox_to_anchor=(0.5, -0.1))
    fig.tight_layout()
    fig.savefig(FIGURE_DIR / "monthly_level_percentile_trend.png", dpi=180)
    plt.close(fig)


def save_mobility_figure(mobility_strength: pd.DataFrame) -> None:
    data = mobility_strength[mobility_strength["n"] >= 5].copy()
    data = data.sort_values("up_rate", ascending=True)
    fig, ax = plt.subplots(figsize=(9, 5.2))
    bars = ax.barh(data["strength_label"], data["up_rate"], color="#2f80ed")
    ax.set_title("강점 유형별 계층 상향 이동 비율", fontsize=15, pad=14)
    ax.set_xlabel("상향 이동 비율")
    ax.set_xlim(0, max(0.6, data["up_rate"].max() + 0.1))
    ax.grid(axis="x", alpha=0.25)
    for bar, (_, row) in zip(bars, data.iterrows()):
        ax.text(
            bar.get_width() + 0.015,
            bar.get_y() + bar.get_height() / 2,
            f"{row['up_rate']:.1%} (n={int(row['n'])})",
            va="center",
            fontsize=9,
        )
    fig.tight_layout()
    fig.savefig(FIGURE_DIR / "mobility_up_rate_by_strength.png", dpi=180)
    plt.close(fig)


def write_report(
    trend: pd.DataFrame,
    segmented: pd.DataFrame,
    strength: pd.DataFrame,
    participation: pd.DataFrame,
    volatility: pd.DataFrame,
    detailed: pd.DataFrame,
) -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    movement_counts = segmented["mobility_type"].value_counts()
    top_detailed = detailed[detailed["n"] >= 3].head(10)

    lines = [
        "# 월별 흐름 및 계층 이동 분석",
        "",
        "## 월별 상/중/하위권 평균 백분위",
        "",
        "수능 이전 모의고사 핵심 평균을 기준으로 상/중/하위권을 나눈 뒤, 각 월의 평균 백분위를 비교했습니다.",
        "",
        "![월별 상중하 평균 백분위](../figures/monthly_level_percentile_trend.png)",
        "",
        "## 계층 이동 기준",
        "",
        "- 시작 계층: 수능 이전 모의고사 핵심 평균 기준 상/중/하위권",
        "- 최종 계층: 수능 핵심 평균 기준 상/중/하위권",
        "- 상향 이동: 최종 계층이 시작 계층보다 높아진 경우",
        "- 하향 이동: 최종 계층이 시작 계층보다 낮아진 경우",
        "",
        "> ⚠️ **평균회귀(RTM) 주의:** 시작 계층은 여러 번의 모의고사 *평균*(분산이 작음)이고 "
        "최종 계층은 *단일 수능*(분산이 큼)의 3분위입니다. 노이즈가 큰 단일 시험을 3등분해 "
        "평균과 비교하면, 실제 실력 변화가 없어도 상향·하향 이동이 기계적으로 발생합니다. "
        "또한 3분위 상대이동이라 상향과 하향은 대체로 상쇄되는 제로섬 구조이므로, "
        "'상향 이동'을 곧 '성적 향상'으로 읽으면 안 됩니다.",
        "",
        "## 전체 이동 결과",
        "",
    ]
    for label in ["상향 이동", "유지", "하향 이동"]:
        count = int(movement_counts.get(label, 0))
        lines.append(f"- {label}: {count}명 ({count / len(segmented):.1%})")

    movers = segmented[segmented["mobility_type"] != "유지"]
    near_boundary_movers = int(movers["near_csat_boundary"].sum()) if len(movers) else 0
    total_movers = len(movers)
    if total_movers:
        lines.append(
            f"- 이 중 수능 3분위 경계밴드(±{BOUNDARY_BAND:.0f}점) 안에서 이동한 학생은 "
            f"{near_boundary_movers}/{total_movers}명입니다. 경계밴드 이동은 작은 점수차로도 "
            f"뒤바뀌므로 평균회귀 인공물일 가능성이 큽니다."
        )

    lines.extend(["", "## 강점 유형별 상향 이동", ""])
    for _, row in strength.iterrows():
        lines.append(
            f"- {row['strength_label']}: n={int(row['n'])}, "
            f"상향 {row['up_rate']:.1%}, 하향 {row['down_rate']:.1%}, "
            f"평균 이동 {row['avg_level_move']:.2f}"
            f"{stats_utils.reliability_tag(row['n'])}"
        )

    lines.extend(
        [
            "",
            "![강점 유형별 상향 이동 비율](../figures/mobility_up_rate_by_strength.png)",
            "",
            "## 응시 횟수별 상향 이동",
            "",
        ]
    )
    for _, row in participation.iterrows():
        lines.append(
            f"- {row['participation_group']}: n={int(row['n'])}, "
            f"상향 {row['up_rate']:.1%}, 하향 {row['down_rate']:.1%}, "
            f"평균 이동 {row['avg_level_move']:.2f}"
            f"{stats_utils.reliability_tag(row['n'])}"
        )

    lines.extend(["", "## 변동성별 상향 이동", ""])
    for _, row in volatility.iterrows():
        lines.append(
            f"- {row['volatility_group']}: n={int(row['n'])}, "
            f"상향 {row['up_rate']:.1%}, 하향 {row['down_rate']:.1%}, "
            f"평균 이동 {row['avg_level_move']:.2f}"
            f"{stats_utils.reliability_tag(row['n'])}"
        )

    lines.extend(["", "## 계층 이동이 활발한 세부 유형", ""])
    for _, row in top_detailed.iterrows():
        lines.append(
            f"- {row['pre_level']} / {row['strength_label']} / {row['participation_group']} / "
            f"{row['volatility_group']}: n={int(row['n'])}, "
            f"상향 {row['up_rate']:.1%}, 하향 {row['down_rate']:.1%}, "
            f"평균 이동 {row['avg_level_move']:.2f}"
            f"{stats_utils.reliability_tag(row['n'])}"
        )

    lines.extend(
        [
            "",
            "## 해석 주의",
            "",
            "- 계층 이동은 3분위 기준의 상대적 이동입니다. 절대 점수가 크게 변하지 않아도 경계 부근 학생은 이동할 수 있습니다(위 평균회귀 주의 참고).",
            f"- n<{stats_utils.MIN_RELIABLE_N}로 표시된 그룹은 소표본이므로 방향성 참고용으로만 사용해야 합니다.",
            "- 상향 이동이 많다는 것은 해당 유형의 모든 학생이 오른다는 뜻이 아니라, 이 데이터에서 그런 사례 비율이 높았다는 의미입니다.",
        ]
    )

    lines = dataset_meta.with_header(lines, PROCESSED_DIR)
    (REPORT_DIR / "monthly_mobility_insights.md").write_text(
        "\n".join(lines), encoding="utf-8"
    )


def main() -> None:
    set_korean_font()
    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    clean, segmented = load_data()
    segmented = assign_csat_level(segmented)
    trend = build_monthly_trend(clean, segmented)

    strength = build_mobility_summary(segmented, ["strength_label"])
    participation = build_mobility_summary(segmented, ["participation_group"])
    volatility = build_mobility_summary(segmented, ["volatility_group"])
    detailed = build_mobility_summary(
        segmented, ["pre_level", "strength_label", "participation_group", "volatility_group"]
    )

    trend.to_csv(TABLE_DIR / "monthly_level_percentile_trend.csv", index=False, encoding="utf-8-sig")
    segmented.to_csv(TABLE_DIR / "student_mobility_profiles.csv", index=False, encoding="utf-8-sig")
    strength.to_csv(TABLE_DIR / "mobility_by_strength.csv", index=False, encoding="utf-8-sig")
    participation.to_csv(TABLE_DIR / "mobility_by_participation.csv", index=False, encoding="utf-8-sig")
    volatility.to_csv(TABLE_DIR / "mobility_by_volatility.csv", index=False, encoding="utf-8-sig")
    detailed.to_csv(TABLE_DIR / "mobility_by_detailed_segment.csv", index=False, encoding="utf-8-sig")

    save_monthly_trend_figure(trend)
    save_mobility_figure(strength)
    write_report(trend, segmented, strength, participation, volatility, detailed)

    print(f"trend_rows={len(trend)}")
    print(f"report={REPORT_DIR / 'monthly_mobility_insights.md'}")


if __name__ == "__main__":
    main()
