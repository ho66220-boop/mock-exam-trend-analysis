from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import ElasticNetCV, LinearRegression, RidgeCV
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import KFold, cross_validate
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

import dataset_meta


ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = ROOT / "data" / "processed"
TABLE_DIR = ROOT / "output" / "tables"
REPORT_DIR = ROOT / "output" / "reports"

TARGETS = {
    "csat_core_mean": "수능 핵심 평균",
    "csat_korean": "수능 국어 백분위",
    "csat_math": "수능 수학 백분위",
    "csat_inquiry_mean": "수능 탐구 평균",
}

NUMERIC_FEATURES = [
    "pre_record_count",
    "private_record_count",
    "official_record_count",
    "pre_core_mean",
    "pre_core_latest",
    "pre_core_std",
    "pre_korean_mean",
    "pre_math_mean",
    "pre_inquiry1_mean",
    "pre_inquiry2_mean",
    "pre_english_mean",
    "pre_inquiry_mean",
]

CATEGORICAL_FEATURES = [
    "track",
    "strength_label",
    "participation_group",
]


def load_frame() -> pd.DataFrame:
    path = TABLE_DIR / "student_group_profiles.csv"
    if not path.exists():
        raise FileNotFoundError("Run scripts/analyze_student_groups.py first.")
    return pd.read_csv(path)


def make_preprocessor(scale_numeric: bool = True) -> ColumnTransformer:
    numeric_steps = [("imputer", SimpleImputer(strategy="median"))]
    if scale_numeric:
        numeric_steps.append(("scaler", StandardScaler()))

    return ColumnTransformer(
        transformers=[
            ("num", Pipeline(numeric_steps), NUMERIC_FEATURES),
            (
                "cat",
                Pipeline(
                    [
                        ("imputer", SimpleImputer(strategy="most_frequent")),
                        ("onehot", OneHotEncoder(handle_unknown="ignore")),
                    ]
                ),
                CATEGORICAL_FEATURES,
            ),
        ]
    )


def model_specs() -> dict[str, Pipeline]:
    return {
        "Mean baseline": Pipeline(
            [
                ("preprocess", make_preprocessor()),
                ("model", DummyRegressor(strategy="mean")),
            ]
        ),
        "Linear regression": Pipeline(
            [
                ("preprocess", make_preprocessor()),
                ("model", LinearRegression()),
            ]
        ),
        "Ridge regression": Pipeline(
            [
                ("preprocess", make_preprocessor()),
                ("model", RidgeCV(alphas=[0.1, 1.0, 3.0, 10.0, 30.0, 100.0])),
            ]
        ),
        "ElasticNet": Pipeline(
            [
                ("preprocess", make_preprocessor()),
                (
                    "model",
                    ElasticNetCV(
                        l1_ratio=[0.1, 0.5, 0.9],
                        alphas=[0.01, 0.05, 0.1, 0.5, 1.0],
                        cv=5,
                        max_iter=50000,
                        random_state=42,
                    ),
                ),
            ]
        ),
        "Random forest": Pipeline(
            [
                ("preprocess", make_preprocessor(scale_numeric=False)),
                (
                    "model",
                    RandomForestRegressor(
                        n_estimators=500,
                        min_samples_leaf=5,
                        random_state=42,
                    ),
                ),
            ]
        ),
        "Gradient boosting": Pipeline(
            [
                ("preprocess", make_preprocessor(scale_numeric=False)),
                (
                    "model",
                    GradientBoostingRegressor(
                        n_estimators=120,
                        learning_rate=0.04,
                        max_depth=2,
                        min_samples_leaf=5,
                        random_state=42,
                    ),
                ),
            ]
        ),
    }


def evaluate_models(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    cv = KFold(n_splits=5, shuffle=True, random_state=42)
    scoring = {
        "r2": "r2",
        "neg_mae": "neg_mean_absolute_error",
        "neg_rmse": "neg_root_mean_squared_error",
    }

    for target, target_label in TARGETS.items():
        data = df[NUMERIC_FEATURES + CATEGORICAL_FEATURES + [target]].dropna(
            subset=[target]
        )
        x = data[NUMERIC_FEATURES + CATEGORICAL_FEATURES]
        y = data[target]

        for model_name, model in model_specs().items():
            scores = cross_validate(
                model,
                x,
                y,
                scoring=scoring,
                cv=cv,
                n_jobs=None,
                error_score="raise",
            )
            rows.append(
                {
                    "target": target,
                    "target_label": target_label,
                    "model": model_name,
                    "n": len(data),
                    "cv_r2_mean": scores["test_r2"].mean(),
                    "cv_r2_std": scores["test_r2"].std(ddof=0),
                    "cv_mae_mean": -scores["test_neg_mae"].mean(),
                    "cv_mae_std": scores["test_neg_mae"].std(ddof=0),
                    "cv_rmse_mean": -scores["test_neg_rmse"].mean(),
                    "cv_rmse_std": scores["test_neg_rmse"].std(ddof=0),
                }
            )

    result = pd.DataFrame(rows)
    return result.sort_values(["target", "cv_r2_mean"], ascending=[True, False])


def permutation_importance_holdout(
    model: Pipeline,
    x: pd.DataFrame,
    y: pd.Series,
    repeats: int = 30,
) -> pd.DataFrame:
    rng = np.random.default_rng(42)
    model.fit(x, y)
    pred = model.predict(x)
    baseline = r2_score(y, pred)

    rows = []
    for feature in x.columns:
        drops = []
        for _ in range(repeats):
            shuffled = x.copy()
            shuffled[feature] = rng.permutation(shuffled[feature].to_numpy())
            shuffled_pred = model.predict(shuffled)
            drops.append(baseline - r2_score(y, shuffled_pred))
        rows.append(
            {
                "feature": feature,
                "r2_drop_mean": float(np.mean(drops)),
                "r2_drop_std": float(np.std(drops)),
            }
        )
    return pd.DataFrame(rows).sort_values("r2_drop_mean", ascending=False)


def fitted_linear_coefficients(df: pd.DataFrame, target: str) -> pd.DataFrame:
    data = df[NUMERIC_FEATURES + CATEGORICAL_FEATURES + [target]].dropna(subset=[target])
    x = data[NUMERIC_FEATURES + CATEGORICAL_FEATURES]
    y = data[target]

    model = Pipeline(
        [
            ("preprocess", make_preprocessor()),
            ("model", RidgeCV(alphas=[0.1, 1.0, 3.0, 10.0, 30.0, 100.0])),
        ]
    )
    model.fit(x, y)
    preprocessor = model.named_steps["preprocess"]
    feature_names = preprocessor.get_feature_names_out()
    coefs = model.named_steps["model"].coef_
    return (
        pd.DataFrame(
            {
                "feature": feature_names,
                "coefficient": coefs,
                "abs_coefficient": np.abs(coefs),
            }
        )
        .sort_values("abs_coefficient", ascending=False)
        .reset_index(drop=True)
    )


def write_report(results: pd.DataFrame, importance: pd.DataFrame, coefficients: pd.DataFrame) -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    lines = [
        "# 모델 설명력 비교",
        "",
        "## 기준",
        "",
        "- 대상: `student_group_profiles.csv`의 수능 이전 기록 보유 학생",
        "- 검증: 5-fold 교차검증",
        "- 주요 지표: R2는 설명력, MAE는 평균 절대 오차입니다.",
        "- 이 결과는 상담용 인사이트 검증이며 개인별 수능 예측기로 해석하지 않습니다.",
        "",
        "## 타깃별 최고 모델",
        "",
    ]

    for target, group in results.groupby("target", sort=False):
        best = group.sort_values("cv_r2_mean", ascending=False).iloc[0]
        lines.append(
            f"- {best['target_label']}: {best['model']} "
            f"(R2 {best['cv_r2_mean']:.3f}, MAE {best['cv_mae_mean']:.2f}, n={int(best['n'])})"
        )

    lines.extend(["", "## 수능 핵심 평균 모델 순위", ""])
    core = results[results["target"] == "csat_core_mean"].sort_values(
        "cv_r2_mean", ascending=False
    )
    for _, row in core.iterrows():
        lines.append(
            f"- {row['model']}: R2 {row['cv_r2_mean']:.3f}, "
            f"MAE {row['cv_mae_mean']:.2f}, RMSE {row['cv_rmse_mean']:.2f}"
        )

    lines.extend(["", "## 수능 핵심 평균에서 중요한 변수", ""])
    for _, row in importance.head(8).iterrows():
        lines.append(f"- {row['feature']}: R2 감소 {row['r2_drop_mean']:.3f}")

    lines.extend(["", "## Ridge 계수 상위 변수", ""])
    for _, row in coefficients.head(10).iterrows():
        sign = "+" if row["coefficient"] >= 0 else "-"
        lines.append(
            f"- {row['feature']}: {sign}{abs(row['coefficient']):.3f}"
        )

    lines.extend(
        [
            "",
            "## 해석",
            "",
            "- R2가 가장 높아도 표본이 작기 때문에 복잡한 모델은 과적합 위험이 있습니다.",
            "- 상담/보고서 용도에서는 Ridge regression처럼 성능과 해석력이 균형 잡힌 모델이 가장 다루기 좋습니다.",
            "- Random forest나 Gradient boosting이 크게 앞서지 않는다면, 비선형 모델보다 선형 모델의 설명을 우선하는 편이 안전합니다.",
            "",
            "## 생성 파일",
            "",
            "- `output/tables/model_comparison.csv`",
            "- `output/tables/core_model_permutation_importance.csv`",
            "- `output/tables/core_ridge_coefficients.csv`",
        ]
    )

    lines = dataset_meta.with_header(lines, PROCESSED_DIR)
    (REPORT_DIR / "model_comparison.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    df = load_frame()
    results = evaluate_models(df)
    results.to_csv(TABLE_DIR / "model_comparison.csv", index=False, encoding="utf-8-sig")

    target = "csat_core_mean"
    data = df[NUMERIC_FEATURES + CATEGORICAL_FEATURES + [target]].dropna(subset=[target])
    x = data[NUMERIC_FEATURES + CATEGORICAL_FEATURES]
    y = data[target]
    best_core_name = (
        results[results["target"] == target]
        .sort_values("cv_r2_mean", ascending=False)
        .iloc[0]["model"]
    )
    best_model = model_specs()[best_core_name]
    importance = permutation_importance_holdout(best_model, x, y)
    coefficients = fitted_linear_coefficients(df, target)

    importance.to_csv(
        TABLE_DIR / "core_model_permutation_importance.csv",
        index=False,
        encoding="utf-8-sig",
    )
    coefficients.to_csv(
        TABLE_DIR / "core_ridge_coefficients.csv", index=False, encoding="utf-8-sig"
    )
    write_report(results, importance, coefficients)

    best = results[results["target"] == target].iloc[0]
    print(
        f"best_core_model={best['model']} "
        f"r2={best['cv_r2_mean']:.3f} mae={best['cv_mae_mean']:.2f}"
    )
    print(f"report={REPORT_DIR / 'model_comparison.md'}")


if __name__ == "__main__":
    main()
