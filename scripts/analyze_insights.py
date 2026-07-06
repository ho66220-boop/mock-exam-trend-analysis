from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import dataset_meta
import exam_meta


ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = ROOT / "data" / "processed"
TABLE_DIR = ROOT / "output" / "tables"
FIGURE_DIR = ROOT / "output" / "figures"
REPORT_DIR = ROOT / "output" / "reports"

SUBJECTS = {
    "korean": {
        "score": "korean_percentile",
        "label": "국어 백분위",
        "higher_is_better": True,
    },
    "math": {
        "score": "math_percentile",
        "label": "수학 백분위",
        "higher_is_better": True,
    },
    "english": {
        "score": "english_grade",
        "label": "영어 등급",
        "higher_is_better": False,
    },
    "inquiry1": {
        "score": "inquiry1_percentile",
        "label": "탐구1 백분위",
        "higher_is_better": True,
    },
    "inquiry2": {
        "score": "inquiry2_percentile",
        "label": "탐구2 백분위",
        "higher_is_better": True,
    },
}

SUBJECT_SELECTION_COLUMNS = {
    "korean": "korean_subject",
    "math": "math_subject",
    "inquiry1": "inquiry1_subject",
    "inquiry2": "inquiry2_subject",
}


def ensure_dirs() -> None:
    for path in [TABLE_DIR, FIGURE_DIR, REPORT_DIR]:
        path.mkdir(parents=True, exist_ok=True)


def read_processed() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    clean_path = PROCESSED_DIR / "clean_records.csv"
    targets_path = PROCESSED_DIR / "csat_targets.csv"
    pre_path = PROCESSED_DIR / "pre_csat_records.csv"
    missing = [path for path in [clean_path, targets_path, pre_path] if not path.exists()]
    if missing:
        raise FileNotFoundError(
            "Run scripts/preprocess_excel.py first. Missing: "
            + ", ".join(str(path) for path in missing)
        )
    return (
        pd.read_csv(clean_path),
        pd.read_csv(targets_path),
        pd.read_csv(pre_path),
    )


def slope_by_exam_order(group: pd.DataFrame, score_column: str) -> float:
    valid = group[["exam_order", score_column]].dropna()
    if len(valid) < 2:
        return np.nan
    x = valid["exam_order"].to_numpy(dtype=float)
    y = valid[score_column].to_numpy(dtype=float)
    if np.isclose(x.max(), x.min()):
        return np.nan
    return float(np.polyfit(x, y, 1)[0])


def build_student_features(pre: pd.DataFrame, targets: pd.DataFrame) -> pd.DataFrame:
    rows = []
    target_lookup = targets.set_index("student_id")

    for student_id, group in pre.groupby("student_id"):
        if student_id not in target_lookup.index:
            continue
        group = group.sort_values(["exam_order", "exam_name"])
        row = {
            "student_id": student_id,
            "track": target_lookup.loc[student_id, "track"],
            "pre_record_count": len(group),
            "private_record_count": int((~group["exam_name"].apply(exam_meta.is_official)).sum()),
            "official_record_count": int(group["exam_name"].apply(exam_meta.is_official).sum()),
        }

        for subject, meta in SUBJECTS.items():
            score = meta["score"]
            valid = group[["exam_order", "exam_name", score]].dropna()
            target_value = target_lookup.loc[student_id, score]
            row[f"{subject}_csat"] = target_value
            row[f"{subject}_n"] = len(valid)

            if valid.empty:
                row[f"{subject}_mean"] = np.nan
                row[f"{subject}_latest"] = np.nan
                row[f"{subject}_best"] = np.nan
                row[f"{subject}_std"] = np.nan
                row[f"{subject}_first"] = np.nan
                row[f"{subject}_change"] = np.nan
                row[f"{subject}_slope"] = np.nan
                row[f"{subject}_recent2_mean"] = np.nan
                row[f"{subject}_latest_exam"] = pd.NA
                continue

            values = valid[score]
            latest = valid.iloc[-1]
            first = valid.iloc[0]
            row[f"{subject}_mean"] = values.mean()
            row[f"{subject}_latest"] = latest[score]
            row[f"{subject}_best"] = values.max() if meta["higher_is_better"] else values.min()
            row[f"{subject}_std"] = values.std(ddof=0)
            row[f"{subject}_first"] = first[score]
            row[f"{subject}_change"] = latest[score] - first[score]
            row[f"{subject}_slope"] = slope_by_exam_order(group, score)
            row[f"{subject}_recent2_mean"] = valid.tail(2)[score].mean()
            row[f"{subject}_latest_exam"] = latest["exam_name"]

        rows.append(row)

    return pd.DataFrame(rows)


def correlation_table(features: pd.DataFrame) -> pd.DataFrame:
    rows = []
    feature_suffixes = ["latest", "mean", "recent2_mean", "best", "slope", "std", "change"]
    for subject, meta in SUBJECTS.items():
        target = f"{subject}_csat"
        for suffix in feature_suffixes:
            feature = f"{subject}_{suffix}"
            pair = features[[target, feature]].dropna()
            if len(pair) < 20:
                corr = np.nan
            else:
                corr = pair[target].corr(pair[feature])
            rows.append(
                {
                    "subject": subject,
                    "label": meta["label"],
                    "target": target,
                    "feature": feature,
                    "n": len(pair),
                    "pearson_corr": corr,
                    "abs_corr": abs(corr) if pd.notna(corr) else np.nan,
                }
            )
    return pd.DataFrame(rows).sort_values(["abs_corr", "n"], ascending=[False, False])


def exam_gap_table(pre: pd.DataFrame, targets: pd.DataFrame) -> pd.DataFrame:
    rows = []
    target_scores = targets.set_index("student_id")
    for subject, meta in SUBJECTS.items():
        score = meta["score"]
        joined = pre[["student_id", "exam_name", score]].join(
            target_scores[[score]].rename(columns={score: "csat_score"}),
            on="student_id",
            how="inner",
        )
        joined = joined.dropna(subset=[score, "csat_score"])
        joined["gap"] = joined["csat_score"] - joined[score]
        joined["abs_gap"] = joined["gap"].abs()
        for exam_name, group in joined.groupby("exam_name"):
            if len(group) < 10:
                corr = np.nan
            else:
                corr = group[score].corr(group["csat_score"])
            rows.append(
                {
                    "subject": subject,
                    "label": meta["label"],
                    "exam_name": exam_name,
                    "n": len(group),
                    "mean_gap_csat_minus_mock": group["gap"].mean(),
                    "mean_abs_gap": group["abs_gap"].mean(),
                    "pearson_corr": corr,
                }
            )
    return pd.DataFrame(rows).sort_values(["subject", "mean_abs_gap"])


def selection_consistency(pre: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for student_id, group in pre.groupby("student_id"):
        row = {"student_id": student_id, "pre_record_count": len(group)}
        for subject, column in SUBJECT_SELECTION_COLUMNS.items():
            values = group[column].dropna().astype(str)
            row[f"{subject}_selection_count"] = values.nunique()
            row[f"{subject}_changed"] = values.nunique() > 1
            row[f"{subject}_selections"] = " | ".join(sorted(values.unique()))
        rows.append(row)
    result = pd.DataFrame(rows)
    change_cols = [f"{subject}_changed" for subject in SUBJECT_SELECTION_COLUMNS]
    result["any_selection_changed"] = result[change_cols].any(axis=1)
    result["changed_subject_count"] = result[change_cols].sum(axis=1)
    return result.sort_values(["changed_subject_count", "pre_record_count"], ascending=False)


def loocv_linear_mae(data: pd.DataFrame, target: str, predictors: list[str]) -> tuple[int, float, float]:
    valid = data[[target, *predictors]].dropna()
    if len(valid) < 20:
        return len(valid), np.nan, np.nan

    y = valid[target].to_numpy(dtype=float)
    x = valid[predictors].to_numpy(dtype=float)
    baseline_errors = []
    model_errors = []

    for i in range(len(valid)):
        train_mask = np.ones(len(valid), dtype=bool)
        train_mask[i] = False
        y_train = y[train_mask]
        x_train = x[train_mask]
        x_test = x[~train_mask]
        y_test = y[~train_mask][0]

        baseline_pred = y_train.mean()
        design = np.column_stack([np.ones(len(x_train)), x_train])
        coef, *_ = np.linalg.lstsq(design, y_train, rcond=None)
        model_pred = np.r_[1.0, x_test[0]] @ coef

        baseline_errors.append(abs(y_test - baseline_pred))
        model_errors.append(abs(y_test - model_pred))

    return len(valid), float(np.mean(baseline_errors)), float(np.mean(model_errors))


def prediction_baseline(features: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for subject, meta in SUBJECTS.items():
        target = f"{subject}_csat"
        predictor_sets = {
            "latest_only": [f"{subject}_latest"],
            "mean_only": [f"{subject}_mean"],
            "latest_mean_slope": [
                f"{subject}_latest",
                f"{subject}_mean",
                f"{subject}_slope",
            ],
        }
        for name, predictors in predictor_sets.items():
            n, baseline_mae, model_mae = loocv_linear_mae(features, target, predictors)
            rows.append(
                {
                    "subject": subject,
                    "label": meta["label"],
                    "model": name,
                    "n": n,
                    "mean_only_baseline_mae": baseline_mae,
                    "model_mae": model_mae,
                    "mae_improvement": baseline_mae - model_mae
                    if pd.notna(model_mae)
                    else np.nan,
                }
            )
    return pd.DataFrame(rows).sort_values(["subject", "model"])


def save_figures(correlations: pd.DataFrame, gaps: pd.DataFrame) -> None:
    top = correlations.head(12).iloc[::-1]
    plt.figure(figsize=(9, 6))
    plt.barh(top["feature"], top["pearson_corr"])
    plt.axvline(0, color="black", linewidth=0.8)
    plt.xlabel("Pearson correlation with CSAT result")
    plt.tight_layout()
    plt.savefig(FIGURE_DIR / "top_feature_correlations.png", dpi=160)
    plt.close()

    gap_summary = gaps.groupby("subject", as_index=False)["mean_abs_gap"].mean()
    plt.figure(figsize=(7, 4))
    plt.bar(gap_summary["subject"], gap_summary["mean_abs_gap"])
    plt.ylabel("Mean absolute gap")
    plt.tight_layout()
    plt.savefig(FIGURE_DIR / "average_mock_to_csat_gap_by_subject.png", dpi=160)
    plt.close()


def write_report(
    features: pd.DataFrame,
    correlations: pd.DataFrame,
    gaps: pd.DataFrame,
    consistency: pd.DataFrame,
    baseline: pd.DataFrame,
) -> None:
    top_corr = correlations.dropna(subset=["pearson_corr"]).head(8)
    best_gap = gaps.dropna(subset=["pearson_corr"]).sort_values(
        ["subject", "mean_abs_gap"]
    )
    changed_count = int(consistency["any_selection_changed"].sum())

    lines = [
        "# 모의고사-수능 인사이트 1차 분석",
        "",
        "## 분석 기준",
        "",
        f"- 수능 결과와 이전 모의고사 기록이 함께 있는 학생: {features['student_id'].nunique()}명",
        "- 점수 0은 미기록 가능성이 높아 결측값으로 처리했습니다.",
        "- 영어는 등급 자료라 값이 낮을수록 좋은 성적입니다.",
        "",
        "## 먼저 볼 만한 신호",
        "",
    ]

    for _, row in top_corr.iterrows():
        lines.append(
            f"- {row['label']} / `{row['feature']}`: "
            f"상관계수 {row['pearson_corr']:.3f} (n={int(row['n'])})"
        )

    lines.extend(
        [
            "",
            "## 간단 예측 기준선",
            "",
            "아래 값은 leave-one-out 방식의 평균절대오차(MAE)입니다. "
            "표본이 작으므로 모델 성능 확정이 아니라 가능성 점검용으로 봐야 합니다.",
            "",
        ]
    )

    for _, row in baseline.iterrows():
        if pd.isna(row["model_mae"]):
            continue
        lines.append(
            f"- {row['label']} / {row['model']}: "
            f"기준선 MAE {row['mean_only_baseline_mae']:.2f}, "
            f"모델 MAE {row['model_mae']:.2f}, "
            f"개선 {row['mae_improvement']:.2f}"
        )

    lines.extend(
        [
            "",
            "## 시험별 수능과의 차이",
            "",
            "과목별로 `mean_abs_gap`이 작고 상관이 높은 시험이 수능과 더 가까운 지표입니다.",
            "",
        ]
    )

    for subject in SUBJECTS:
        subset = best_gap[best_gap["subject"] == subject].head(3)
        if subset.empty:
            continue
        lines.append(f"### {SUBJECTS[subject]['label']}")
        for _, row in subset.iterrows():
            lines.append(
                f"- {row['exam_name']}: 평균 절대 차이 {row['mean_abs_gap']:.2f}, "
                f"상관 {row['pearson_corr']:.3f}, n={int(row['n'])}"
            )
        lines.append("")

    lines.extend(
        [
            "## 선택과목 일관성",
            "",
            f"- 수능 이전 기록이 있는 학생 중 선택과목 변경 흔적이 있는 학생: {changed_count}명",
            "- 선택과목 변경 학생은 별도 그룹으로 묶어 성적 변동성과 함께 보는 것을 추천합니다.",
            "",
            "## 생성 파일",
            "",
            "- `output/tables/student_csat_features.csv`",
            "- `output/tables/subject_feature_correlations.csv`",
            "- `output/tables/exam_to_csat_gap_summary.csv`",
            "- `output/tables/selection_consistency.csv`",
            "- `output/tables/prediction_baseline.csv`",
            "- `output/figures/top_feature_correlations.png`",
            "- `output/figures/average_mock_to_csat_gap_by_subject.png`",
        ]
    )

    lines = dataset_meta.with_header(lines, PROCESSED_DIR)
    (REPORT_DIR / "insight_report.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    ensure_dirs()
    _, targets, pre = read_processed()

    features = build_student_features(pre, targets)
    correlations = correlation_table(features)
    gaps = exam_gap_table(pre, targets)
    consistency = selection_consistency(pre)
    baseline = prediction_baseline(features)

    features.to_csv(TABLE_DIR / "student_csat_features.csv", index=False, encoding="utf-8-sig")
    correlations.to_csv(TABLE_DIR / "subject_feature_correlations.csv", index=False, encoding="utf-8-sig")
    gaps.to_csv(TABLE_DIR / "exam_to_csat_gap_summary.csv", index=False, encoding="utf-8-sig")
    consistency.to_csv(TABLE_DIR / "selection_consistency.csv", index=False, encoding="utf-8-sig")
    baseline.to_csv(TABLE_DIR / "prediction_baseline.csv", index=False, encoding="utf-8-sig")

    save_figures(correlations, gaps)
    write_report(features, correlations, gaps, consistency, baseline)

    print(f"students_with_features={features['student_id'].nunique()}")
    print(f"top_correlation={correlations.iloc[0]['feature']}:{correlations.iloc[0]['pearson_corr']:.3f}")
    print(f"report={REPORT_DIR / 'insight_report.md'}")


if __name__ == "__main__":
    main()
