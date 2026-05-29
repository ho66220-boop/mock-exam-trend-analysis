from pathlib import Path

import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
TABLE_DIR = ROOT / "output" / "tables"
FIGURE_DIR = ROOT / "output" / "figures"

LEVEL_COLORS = {
    "상위권": "#2f80ed",
    "중위권": "#27ae60",
    "하위권": "#f2994a",
}

STRENGTH_COLORS = {
    "균형형": "#2f80ed",
    "국어형": "#9b51e0",
    "수학형": "#eb5757",
    "탐구형": "#219653",
    "불명확": "#828282",
}

PARTICIPATION_COLORS = {
    "적게 응시(1-3회)": "#f2c94c",
    "보통 응시(4-6회)": "#27ae60",
    "많이 응시(7회 이상)": "#2d9cdb",
}

VOLATILITY_COLORS = {
    "변동성 작음": "#56ccf2",
    "변동성 큼": "#eb5757",
}


def set_korean_font() -> None:
    candidates = ["Malgun Gothic", "맑은 고딕", "Noto Sans CJK KR", "NanumGothic"]
    available = {font.name for font in fm.fontManager.ttflist}
    for name in candidates:
        if name in available:
            plt.rcParams["font.family"] = name
            break
    plt.rcParams["axes.unicode_minus"] = False


def load_table(name: str) -> pd.DataFrame:
    path = TABLE_DIR / name
    if not path.exists():
        raise FileNotFoundError(f"Missing {path}. Run scripts/segment_student_profiles.py first.")
    return pd.read_csv(path)


def label_bars(ax, values, fmt="{:.1f}", dy=0.6) -> None:
    for patch, value in zip(ax.patches, values):
        ax.text(
            patch.get_x() + patch.get_width() / 2,
            patch.get_height() + dy,
            fmt.format(value),
            ha="center",
            va="bottom",
            fontsize=10,
        )


def save_level_summary(level_summary: pd.DataFrame) -> None:
    order = ["상위권", "중위권", "하위권"]
    data = level_summary.set_index("pre_level").loc[order].reset_index()

    fig, ax = plt.subplots(figsize=(8, 5))
    colors = [LEVEL_COLORS[level] for level in data["pre_level"]]
    bars = ax.bar(data["pre_level"], data["avg_csat_core_mean"], color=colors)
    ax.set_title("수능 이전 성취권별 수능 핵심 평균", fontsize=15, pad=14)
    ax.set_ylabel("수능 핵심 평균")
    ax.set_ylim(55, 100)
    ax.grid(axis="y", alpha=0.25)
    for bar, _, row in zip(bars, data["pre_level"], data.itertuples()):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 1.0,
            f"{row.avg_csat_core_mean:.1f}\nn={int(row.n)}",
            ha="center",
            va="bottom",
            fontsize=10,
        )
    fig.tight_layout()
    fig.savefig(FIGURE_DIR / "segment_level_csat_mean.png", dpi=180)
    plt.close(fig)


def save_strength_by_level(level_strength: pd.DataFrame) -> None:
    levels = ["상위권", "중위권", "하위권"]
    strengths = ["균형형", "국어형", "수학형", "탐구형"]
    pivot = level_strength.pivot(
        index="pre_level", columns="strength_label", values="avg_csat_core_mean"
    ).reindex(levels)[strengths]
    count = level_strength.pivot(index="pre_level", columns="strength_label", values="n").reindex(levels)

    fig, ax = plt.subplots(figsize=(10, 5.5))
    x = range(len(levels))
    width = 0.18
    offsets = [-1.5 * width, -0.5 * width, 0.5 * width, 1.5 * width]
    for strength, offset in zip(strengths, offsets):
        values = pivot[strength]
        bars = ax.bar(
            [i + offset for i in x],
            values,
            width=width,
            label=strength,
            color=STRENGTH_COLORS[strength],
        )
        for i, bar in enumerate(bars):
            if pd.isna(values.iloc[i]):
                continue
            n = int(count.loc[levels[i], strength]) if pd.notna(count.loc[levels[i], strength]) else 0
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 0.8,
                f"{values.iloc[i]:.1f}\n({n})",
                ha="center",
                va="bottom",
                fontsize=8,
            )

    ax.set_title("성취권 x 과목 강점 유형별 수능 핵심 평균", fontsize=15, pad=14)
    ax.set_xticks(list(x), levels)
    ax.set_ylabel("수능 핵심 평균")
    ax.set_ylim(55, 100)
    ax.grid(axis="y", alpha=0.25)
    ax.legend(ncol=4, frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.08))
    fig.tight_layout()
    fig.savefig(FIGURE_DIR / "segment_strength_by_level.png", dpi=180)
    plt.close(fig)


def save_participation_by_level(level_participation: pd.DataFrame) -> None:
    levels = ["상위권", "중위권", "하위권"]
    groups = ["적게 응시(1-3회)", "보통 응시(4-6회)", "많이 응시(7회 이상)"]
    pivot = level_participation.pivot(
        index="pre_level", columns="participation_group", values="avg_csat_core_mean"
    ).reindex(levels)[groups]
    count = level_participation.pivot(index="pre_level", columns="participation_group", values="n").reindex(levels)

    fig, ax = plt.subplots(figsize=(10, 5.5))
    x = range(len(levels))
    width = 0.23
    offsets = [-width, 0, width]
    for group, offset in zip(groups, offsets):
        values = pivot[group]
        bars = ax.bar(
            [i + offset for i in x],
            values,
            width=width,
            label=group,
            color=PARTICIPATION_COLORS[group],
        )
        for i, bar in enumerate(bars):
            n = int(count.loc[levels[i], group]) if pd.notna(count.loc[levels[i], group]) else 0
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 0.8,
                f"{values.iloc[i]:.1f}\n({n})",
                ha="center",
                va="bottom",
                fontsize=8,
            )

    ax.set_title("성취권 x 응시 횟수별 수능 핵심 평균", fontsize=15, pad=14)
    ax.set_xticks(list(x), levels)
    ax.set_ylabel("수능 핵심 평균")
    ax.set_ylim(55, 100)
    ax.grid(axis="y", alpha=0.25)
    ax.legend(ncol=3, frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.08))
    fig.tight_layout()
    fig.savefig(FIGURE_DIR / "segment_participation_by_level.png", dpi=180)
    plt.close(fig)


def save_volatility_by_level(level_volatility: pd.DataFrame) -> None:
    levels = ["상위권", "중위권", "하위권"]
    groups = ["변동성 작음", "변동성 큼"]
    pivot = level_volatility.pivot(
        index="pre_level", columns="volatility_group", values="avg_csat_core_mean"
    ).reindex(levels)[groups]
    drop = level_volatility.pivot(index="pre_level", columns="volatility_group", values="drop_rate").reindex(levels)

    fig, ax = plt.subplots(figsize=(9, 5.2))
    x = range(len(levels))
    width = 0.28
    for group, offset in zip(groups, [-width / 2, width / 2]):
        values = pivot[group]
        bars = ax.bar(
            [i + offset for i in x],
            values,
            width=width,
            label=group,
            color=VOLATILITY_COLORS[group],
        )
        for i, bar in enumerate(bars):
            drop_rate = drop.loc[levels[i], group]
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 0.8,
                f"{values.iloc[i]:.1f}\n하락 {drop_rate:.0%}",
                ha="center",
                va="bottom",
                fontsize=8,
            )

    ax.set_title("성취권 x 변동성별 수능 핵심 평균", fontsize=15, pad=14)
    ax.set_xticks(list(x), levels)
    ax.set_ylabel("수능 핵심 평균")
    ax.set_ylim(55, 100)
    ax.grid(axis="y", alpha=0.25)
    ax.legend(ncol=2, frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.08))
    fig.tight_layout()
    fig.savefig(FIGURE_DIR / "segment_volatility_by_level.png", dpi=180)
    plt.close(fig)


def save_recommendation_bubble(recommendations: pd.DataFrame) -> None:
    data = recommendations.head(12).copy()
    data["label"] = (
        data["pre_level"]
        + "\n"
        + data["strength_label"]
        + " / "
        + data["volatility_group"]
    )
    colors = [LEVEL_COLORS[level] for level in data["pre_level"]]
    sizes = data["n"] * 90

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.scatter(
        data["avg_pre_core_mean"],
        data["avg_csat_core_mean"],
        s=sizes,
        c=colors,
        alpha=0.78,
        edgecolor="#333333",
        linewidth=0.8,
    )
    for _, row in data.iterrows():
        ax.text(
            row["avg_pre_core_mean"] + 0.25,
            row["avg_csat_core_mean"] + 0.25,
            f"{row['pre_level']} {row['strength_label']}\nn={int(row['n'])}",
            fontsize=8,
        )
    ax.plot([55, 100], [55, 100], color="#777777", linestyle="--", linewidth=1)
    ax.set_title("전달용 주요 세그먼트: 수능 이전 평균 대비 수능 결과", fontsize=15, pad=14)
    ax.set_xlabel("수능 이전 모의고사 핵심 평균")
    ax.set_ylabel("수능 핵심 평균")
    ax.set_xlim(55, 100)
    ax.set_ylim(55, 100)
    ax.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(FIGURE_DIR / "segment_recommendation_bubble.png", dpi=180)
    plt.close(fig)


def save_model_comparison() -> None:
    path = TABLE_DIR / "model_comparison.csv"
    if not path.exists():
        return
    data = pd.read_csv(path)
    core = data[data["target"] == "csat_core_mean"].sort_values("cv_r2_mean")

    fig, ax = plt.subplots(figsize=(9, 5))
    colors = ["#828282" if name == "Mean baseline" else "#2f80ed" for name in core["model"]]
    bars = ax.barh(core["model"], core["cv_r2_mean"], color=colors)
    ax.axvline(0, color="#333333", linewidth=0.8)
    ax.set_title("수능 핵심 평균 모델 설명력 비교", fontsize=15, pad=14)
    ax.set_xlabel("5-fold 교차검증 R2")
    ax.grid(axis="x", alpha=0.25)
    for bar, value, mae in zip(bars, core["cv_r2_mean"], core["cv_mae_mean"]):
        ax.text(
            value + 0.02,
            bar.get_y() + bar.get_height() / 2,
            f"R2 {value:.3f} / MAE {mae:.1f}",
            va="center",
            fontsize=9,
        )
    fig.tight_layout()
    fig.savefig(FIGURE_DIR / "model_comparison_core_r2.png", dpi=180)
    plt.close(fig)


def main() -> None:
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    set_korean_font()

    level_summary = load_table("segment_level_summary.csv")
    level_strength = load_table("segment_level_strength_summary.csv")
    level_participation = load_table("segment_level_participation_summary.csv")
    level_volatility = load_table("segment_level_volatility_summary.csv")
    recommendations = load_table("segment_recommendation_table.csv")

    save_level_summary(level_summary)
    save_strength_by_level(level_strength)
    save_participation_by_level(level_participation)
    save_volatility_by_level(level_volatility)
    save_recommendation_bubble(recommendations)
    save_model_comparison()

    print("created:")
    for name in [
        "segment_level_csat_mean.png",
        "segment_strength_by_level.png",
        "segment_participation_by_level.png",
        "segment_volatility_by_level.png",
        "segment_recommendation_bubble.png",
        "model_comparison_core_r2.png",
    ]:
        print(FIGURE_DIR / name)


if __name__ == "__main__":
    main()
