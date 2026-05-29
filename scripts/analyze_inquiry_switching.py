from pathlib import Path

import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = ROOT / "data" / "processed"
TABLE_DIR = ROOT / "output" / "tables"
FIGURE_DIR = ROOT / "output" / "figures"
REPORT_DIR = ROOT / "output" / "reports"


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


def month_order(month: str) -> int:
    if month == "수능":
        return 12
    try:
        return int(str(month).replace("월", ""))
    except ValueError:
        return 99


def inquiry_set(row: pd.Series) -> str | None:
    subjects = [
        row.get("inquiry1_subject"),
        row.get("inquiry2_subject"),
    ]
    clean = sorted(
        subject
        for subject in subjects
        if pd.notna(subject) and str(subject).strip() and str(subject).strip() != "nan"
    )
    if not clean:
        return None
    return " + ".join(clean)


def load_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    pre = pd.read_csv(PROCESSED_DIR / "pre_csat_records.csv")
    targets = pd.read_csv(PROCESSED_DIR / "csat_targets.csv")
    return pre, targets


def prepare_records(pre: pd.DataFrame) -> pd.DataFrame:
    records = pre.copy()
    records = records.sort_values(["student_id", "exam_order", "exam_name"])
    records["month"] = records["exam_name"].apply(extract_month)
    records["month_order"] = records["month"].apply(month_order)
    records["inquiry_set"] = records.apply(inquiry_set, axis=1)
    records["inquiry_mean"] = records[["inquiry1_percentile", "inquiry2_percentile"]].mean(
        axis=1, skipna=True
    )
    return records


def build_student_switch_profiles(records: pd.DataFrame, targets: pd.DataFrame) -> pd.DataFrame:
    targets = targets.copy()
    targets["csat_inquiry_mean"] = targets[["inquiry1_percentile", "inquiry2_percentile"]].mean(
        axis=1, skipna=True
    )
    target_lookup = targets.set_index("student_id")

    rows = []
    for student_id, group in records.groupby("student_id"):
        valid_subject = group.dropna(subset=["inquiry_set"]).copy()
        valid_score = group.dropna(subset=["inquiry_mean"]).copy()
        unique_sets = valid_subject["inquiry_set"].dropna().unique().tolist()
        changed = len(unique_sets) > 1

        first_change_order = np.nan
        first_change_month = pd.NA
        from_set = pd.NA
        to_set = pd.NA
        before_mean = np.nan
        after_mean = np.nan
        immediate_after_mean = np.nan
        post_record_count = 0

        if changed:
            previous_set = None
            change_row = None
            for _, row in valid_subject.iterrows():
                current_set = row["inquiry_set"]
                if previous_set is None:
                    previous_set = current_set
                    continue
                if current_set != previous_set:
                    change_row = row
                    from_set = previous_set
                    to_set = current_set
                    break
                previous_set = current_set

            if change_row is not None:
                first_change_order = change_row["exam_order"]
                first_change_month = change_row["month"]
                before = valid_score[valid_score["exam_order"] < first_change_order]
                after = valid_score[valid_score["exam_order"] >= first_change_order]
                before_mean = before["inquiry_mean"].mean()
                after_mean = after["inquiry_mean"].mean()
                immediate_after_mean = after.head(2)["inquiry_mean"].mean()
                post_record_count = len(after)

        csat_inquiry = (
            target_lookup.loc[student_id, "csat_inquiry_mean"]
            if student_id in target_lookup.index
            else np.nan
        )
        rows.append(
            {
                "student_id": student_id,
                "inquiry_changed": changed,
                "inquiry_set_count": len(unique_sets),
                "first_inquiry_set": unique_sets[0] if unique_sets else pd.NA,
                "last_inquiry_set": unique_sets[-1] if unique_sets else pd.NA,
                "from_set": from_set,
                "to_set": to_set,
                "change_month": first_change_month,
                "change_order": first_change_order,
                "pre_change_inquiry_mean": before_mean,
                "post_change_inquiry_mean": after_mean,
                "immediate_after_change_mean": immediate_after_mean,
                "post_change_record_count": post_record_count,
                "pre_all_inquiry_mean": valid_score["inquiry_mean"].mean(),
                "latest_pre_inquiry_mean": valid_score.tail(1)["inquiry_mean"].mean(),
                "csat_inquiry_mean": csat_inquiry,
                "post_minus_pre": after_mean - before_mean
                if pd.notna(after_mean) and pd.notna(before_mean)
                else np.nan,
                "csat_minus_pre_change": csat_inquiry - before_mean
                if pd.notna(csat_inquiry) and pd.notna(before_mean)
                else np.nan,
                "csat_minus_post_change": csat_inquiry - after_mean
                if pd.notna(csat_inquiry) and pd.notna(after_mean)
                else np.nan,
            }
        )

    return pd.DataFrame(rows)


def summarize_switch_timing(profiles: pd.DataFrame) -> pd.DataFrame:
    changed = profiles[profiles["inquiry_changed"]].dropna(subset=["change_month"]).copy()
    rows = []
    for month, group in changed.groupby("change_month"):
        rows.append(
            {
                "change_month": month,
                "month_order": month_order(month),
                "n": len(group),
                "avg_pre_change_inquiry_mean": group["pre_change_inquiry_mean"].mean(),
                "avg_post_change_inquiry_mean": group["post_change_inquiry_mean"].mean(),
                "avg_post_minus_pre": group["post_minus_pre"].mean(),
                "avg_csat_inquiry_mean": group["csat_inquiry_mean"].mean(),
                "avg_csat_minus_pre_change": group["csat_minus_pre_change"].mean(),
                "avg_csat_minus_post_change": group["csat_minus_post_change"].mean(),
                "benefit_rate_post": (group["post_minus_pre"] > 0).mean(),
                "benefit_rate_csat": (group["csat_minus_pre_change"] > 0).mean(),
                "avg_post_records": group["post_change_record_count"].mean(),
            }
        )
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows).sort_values("month_order")


def compare_changers(profiles: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for changed, group in profiles.groupby("inquiry_changed"):
        rows.append(
            {
                "group": "탐구 변경" if changed else "탐구 유지",
                "n": len(group),
                "avg_pre_all_inquiry_mean": group["pre_all_inquiry_mean"].mean(),
                "avg_latest_pre_inquiry_mean": group["latest_pre_inquiry_mean"].mean(),
                "avg_csat_inquiry_mean": group["csat_inquiry_mean"].mean(),
                "avg_csat_minus_pre_all": (
                    group["csat_inquiry_mean"] - group["pre_all_inquiry_mean"]
                ).mean(),
            }
        )
    return pd.DataFrame(rows)


def save_timing_figure(summary: pd.DataFrame) -> None:
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    if summary.empty:
        return
    data = summary.sort_values("month_order")
    fig, ax = plt.subplots(figsize=(10, 5.4))
    x = np.arange(len(data))
    width = 0.28
    ax.bar(
        x - width,
        data["avg_post_minus_pre"],
        width=width,
        color="#2f80ed",
        label="변경 후 평균 - 변경 전 평균",
    )
    ax.bar(
        x,
        data["avg_csat_minus_pre_change"],
        width=width,
        color="#27ae60",
        label="수능 탐구 - 변경 전 평균",
    )
    ax.bar(
        x + width,
        data["avg_csat_minus_post_change"],
        width=width,
        color="#f2994a",
        label="수능 탐구 - 변경 후 평균",
    )
    ax.axhline(0, color="#333333", linewidth=0.8)
    ax.set_title("탐구 변경 시기별 백분위 이득", fontsize=15, pad=14)
    ax.set_xticks(x, [f"{m}\n(n={int(n)})" for m, n in zip(data["change_month"], data["n"])])
    ax.set_ylabel("백분위 차이")
    ax.grid(axis="y", alpha=0.25)
    ax.legend(frameon=False, ncol=1, loc="upper left")
    fig.tight_layout()
    fig.savefig(FIGURE_DIR / "inquiry_switch_timing_benefit.png", dpi=180)
    plt.close(fig)


def save_change_compare_figure(compare: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(7, 5))
    colors = ["#2f80ed" if group == "탐구 변경" else "#828282" for group in compare["group"]]
    bars = ax.bar(compare["group"], compare["avg_csat_inquiry_mean"], color=colors)
    ax.set_title("탐구 변경 여부별 수능 탐구 평균", fontsize=15, pad=14)
    ax.set_ylabel("수능 탐구 평균 백분위")
    ax.set_ylim(55, 90)
    ax.grid(axis="y", alpha=0.25)
    for bar, (_, row) in zip(bars, compare.iterrows()):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.7,
            f"{row['avg_csat_inquiry_mean']:.1f}\nn={int(row['n'])}",
            ha="center",
            va="bottom",
            fontsize=10,
        )
    fig.tight_layout()
    fig.savefig(FIGURE_DIR / "inquiry_switch_vs_keep_csat.png", dpi=180)
    plt.close(fig)


def write_report(profiles: pd.DataFrame, timing: pd.DataFrame, compare: pd.DataFrame) -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    changed = profiles[profiles["inquiry_changed"]]
    lines = [
        "# 탐구 과목 변경 분석",
        "",
        "## 분석 기준",
        "",
        "- 대상: 수능 이전 기록과 수능 탐구 결과가 있는 학생",
        "- 탐구 변경: 탐구1/탐구2 과목 조합이 이전 시험과 달라진 경우",
        "- 변경 시기: 처음으로 탐구 과목 조합이 달라진 시험 월",
        "- 이득 기준: 변경 후 탐구 평균 백분위가 변경 전보다 올랐는지, 그리고 수능 탐구 평균이 변경 전보다 올랐는지",
        "",
        f"- 탐구 변경 학생: {len(changed)}명",
        f"- 탐구 유지 학생: {len(profiles) - len(changed)}명",
        "",
        "## 변경 여부별 결과",
        "",
    ]
    for _, row in compare.iterrows():
        lines.append(
            f"- {row['group']}: n={int(row['n'])}, "
            f"수능 이전 탐구 평균 {row['avg_pre_all_inquiry_mean']:.1f}, "
            f"최신 수능 이전 탐구 {row['avg_latest_pre_inquiry_mean']:.1f}, "
            f"수능 탐구 {row['avg_csat_inquiry_mean']:.1f}, "
            f"수능-수능 이전 평균 {row['avg_csat_minus_pre_all']:.1f}"
        )

    lines.extend(
        [
            "",
            "![탐구 변경 여부별 수능 탐구 평균](../figures/inquiry_switch_vs_keep_csat.png)",
            "",
            "## 변경 시기별 이득",
            "",
        ]
    )

    if timing.empty:
        lines.append("- 탐구 변경 시기별로 분석할 수 있는 표본이 없습니다.")
    else:
        for _, row in timing.iterrows():
            lines.append(
                f"- {row['change_month']}: n={int(row['n'])}, "
                f"변경 후-전 {row['avg_post_minus_pre']:.1f}, "
                f"수능-변경 전 {row['avg_csat_minus_pre_change']:.1f}, "
                f"수능-변경 후 {row['avg_csat_minus_post_change']:.1f}, "
                f"변경 후 이득률 {row['benefit_rate_post']:.1%}, "
                f"수능 이득률 {row['benefit_rate_csat']:.1%}"
            )

    lines.extend(
        [
            "",
            "![탐구 변경 시기별 백분위 이득](../figures/inquiry_switch_timing_benefit.png)",
            "",
            "## 해석 주의",
            "",
            "- 탐구 변경은 이미 어려움을 겪던 학생이 선택했을 가능성이 있어, 변경 자체의 효과로 단정할 수 없습니다.",
            "- 시기별 표본 수가 작으면 평균이 일부 학생에게 크게 흔들릴 수 있습니다.",
            "- 상담에서는 '언제 바꾸면 오른다'보다 '늦은 변경은 적응 기록 수가 줄어든다'는 리스크까지 함께 전달하는 것이 안전합니다.",
        ]
    )
    (REPORT_DIR / "inquiry_switching_insights.md").write_text(
        "\n".join(lines), encoding="utf-8"
    )


def main() -> None:
    set_korean_font()
    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    pre, targets = load_data()
    records = prepare_records(pre)
    profiles = build_student_switch_profiles(records, targets)
    timing = summarize_switch_timing(profiles)
    compare = compare_changers(profiles)

    profiles.to_csv(TABLE_DIR / "inquiry_switch_profiles.csv", index=False, encoding="utf-8-sig")
    timing.to_csv(TABLE_DIR / "inquiry_switch_timing_summary.csv", index=False, encoding="utf-8-sig")
    compare.to_csv(TABLE_DIR / "inquiry_switch_vs_keep_summary.csv", index=False, encoding="utf-8-sig")

    save_timing_figure(timing)
    save_change_compare_figure(compare)
    write_report(profiles, timing, compare)

    print(f"students={len(profiles)}")
    print(f"switchers={int(profiles['inquiry_changed'].sum())}")
    print(f"report={REPORT_DIR / 'inquiry_switching_insights.md'}")


if __name__ == "__main__":
    main()
