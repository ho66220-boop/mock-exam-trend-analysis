from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
TABLE_DIR = ROOT / "output" / "tables"
FIGURE_DIR = ROOT / "output" / "figures"
REPORT_DIR = ROOT / "output" / "reports"


def read_csv(name: str) -> pd.DataFrame:
    path = TABLE_DIR / name
    if not path.exists():
        raise FileNotFoundError(f"Missing {path}")
    return pd.read_csv(path)


def fmt_float(value, digits: int = 1) -> str:
    if pd.isna(value):
        return "-"
    return f"{value:.{digits}f}"


def fmt_pct(value) -> str:
    if pd.isna(value):
        return "-"
    return f"{value:.1%}"


def markdown_table(df: pd.DataFrame, columns: list[tuple[str, str]], limit: int | None = None) -> str:
    if limit is not None:
        df = df.head(limit)
    headers = [header for _, header in columns]
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for _, row in df.iterrows():
        values = []
        for column, _ in columns:
            value = row[column]
            if column.endswith("_rate") or "rate" in column:
                values.append(fmt_pct(value))
            elif column in {"cv_r2_mean", "pearson_corr"}:
                values.append(fmt_float(value, 3))
            elif isinstance(value, float):
                values.append(fmt_float(value))
            else:
                values.append(str(value))
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def figure(name: str, alt: str) -> str:
    path = FIGURE_DIR / name
    if not path.exists():
        return f"> 그림 파일 없음: `{name}`"
    return f"![{alt}](../figures/{name})"


def build_report() -> str:
    level = read_csv("segment_level_summary.csv")
    strength = read_csv("segment_level_strength_summary.csv")
    participation = read_csv("segment_level_participation_summary.csv")
    volatility = read_csv("segment_level_volatility_summary.csv")
    recommendation = read_csv("segment_recommendation_table.csv")
    model = read_csv("model_comparison.csv")
    correlations = read_csv("subject_feature_correlations.csv")
    exam_gap = read_csv("exam_to_csat_gap_summary.csv")
    monthly = read_csv("monthly_level_percentile_trend.csv")
    mobility_strength = read_csv("mobility_by_strength.csv")
    mobility_participation = read_csv("mobility_by_participation.csv")
    mobility_volatility = read_csv("mobility_by_volatility.csv")
    mobility_detailed = read_csv("mobility_by_detailed_segment.csv")
    mobility_profiles = read_csv("student_mobility_profiles.csv")
    inquiry_timing = read_csv("inquiry_switch_timing_summary.csv")
    inquiry_compare = read_csv("inquiry_switch_vs_keep_summary.csv")

    level_order = {"상위권": 0, "중위권": 1, "하위권": 2}
    level = level.sort_values("pre_level", key=lambda s: s.map(level_order))

    core_models = model[model["target"] == "csat_core_mean"].sort_values(
        "cv_r2_mean", ascending=False
    )
    top_corr = correlations.sort_values("abs_corr", ascending=False).head(8)

    best_exam_rows = []
    for label, group in exam_gap.groupby("label"):
        candidate = group[group["n"] >= 30].sort_values("mean_abs_gap").head(1)
        if not candidate.empty:
            best_exam_rows.append(candidate.iloc[0])
    best_exam = pd.DataFrame(best_exam_rows)
    monthly_pivot = (
        monthly.pivot(index="month", columns="pre_level", values="avg_core_percentile")
        .reset_index()
    )
    monthly_pivot["month_order"] = monthly_pivot["month"].apply(
        lambda value: int(str(value).replace("월", "")) if "월" in str(value) else 99
    )
    monthly_pivot = monthly_pivot.sort_values("month_order").drop(columns=["month_order"])
    movement_counts = mobility_profiles["mobility_type"].value_counts()

    lines = [
        "# 샘플 재원생 모의고사-수능 결과 인사이트 종합 리포트",
        "",
        "## 1. 분석 목적",
        "",
        "본 리포트는 샘플 재원생의 누적 모의고사 기록과 수능 결과를 바탕으로, "
        "학생들에게 전달할 수 있는 상담용 인사이트를 정리한 자료입니다. "
        "개인별 수능 성적을 단정적으로 예측하기보다, 어떤 학습 패턴과 과목 조합이 "
        "최종 수능 결과와 연결되었는지를 확인하는 데 목적이 있습니다.",
        "",
        "## 2. 데이터 기준",
        "",
        "- 분석 대상: 수능 이전 모의고사 기록과 수능 결과가 모두 있는 116명",
        "- 핵심 성과 지표: 국어, 수학, 탐구1, 탐구2 백분위 평균",
        "- 영어는 등급 자료이므로 핵심 평균에는 포함하지 않고 보조 지표로 활용",
        "- 점수 0은 미응시 또는 미기록 가능성이 높아 결측값으로 처리",
        "- 상위권/중위권/하위권은 수능 이전 모의고사 핵심 평균의 3분위 기준",
        "",
        "## 3. 월별 상/중/하위권 평균 백분위 흐름",
        "",
        "리포트 초반에는 샘플 재원생들이 월별로 어떤 흐름을 보였는지 먼저 확인합니다. "
        "아래 그래프는 수능 이전 모의고사 핵심 평균 기준으로 상/중/하위권을 나눈 뒤, "
        "각 월의 국어/수학/탐구 평균 백분위를 비교한 것입니다.",
        "",
        figure("monthly_level_percentile_trend.png", "월별 상중하위권 평균 백분위 흐름"),
        "",
        markdown_table(
            monthly_pivot,
            [
                ("month", "월"),
                ("상위권", "상위권 평균"),
                ("중위권", "중위권 평균"),
                ("하위권", "하위권 평균"),
            ],
        ),
        "",
        "월별 흐름은 학생들에게 가장 직관적으로 전달하기 좋은 자료입니다. "
        "특히 상위권은 높은 평균을 비교적 유지하는지, 중위권과 하위권은 어느 시점에서 격차가 벌어지거나 좁혀지는지를 볼 수 있습니다.",
        "",
        "## 4. 전체 요약",
        "",
        markdown_table(
            level,
            [
                ("pre_level", "구분"),
                ("n", "학생 수"),
                ("avg_pre_core_mean", "수능 이전 평균"),
                ("avg_csat_core_mean", "수능 평균"),
                ("top_25pct_rate", "수능 상위 25% 비율"),
                ("rise_rate", "수능 상승률"),
                ("drop_rate", "수능 하락률"),
            ],
        )
        ,
        "",
        figure("segment_level_csat_mean.png", "상중하위권별 수능 핵심 평균"),
        "",
        "핵심적으로 상위권은 수능 결과도 높은 수준을 유지했고, 중위권과 하위권은 일부 상승 사례가 확인됩니다. "
        "다만 하위권은 상승률이 존재하더라도 상위권 진입 비율은 낮아, 기본 성취 수준 자체를 끌어올리는 전략이 중요합니다.",
        "",
        "## 5. 과목 강점 유형별 인사이트",
        "",
        figure("segment_strength_by_level.png", "성취권과 과목 강점 유형별 수능 결과"),
        "",
        "작년 데이터에서는 상위권에서 균형형 학생의 수능 결과가 가장 안정적으로 높았습니다. "
        "중위권은 국어형, 수학형, 균형형의 차이가 크지 않아 약점 보완과 유지 전략을 함께 보는 것이 좋습니다. "
        "하위권에서는 수학형 학생의 상승 가능성이 상대적으로 두드러졌습니다.",
        "",
        markdown_table(
            strength.sort_values(["pre_level", "avg_csat_core_mean"], ascending=[True, False]),
            [
                ("pre_level", "권역"),
                ("strength_label", "강점 유형"),
                ("n", "학생 수"),
                ("avg_csat_core_mean", "수능 평균"),
                ("rise_rate", "상승률"),
                ("drop_rate", "하락률"),
            ],
        ),
        "",
        "## 6. 응시 횟수별 인사이트",
        "",
        figure("segment_participation_by_level.png", "성취권과 응시 횟수별 수능 결과"),
        "",
        "응시 횟수는 인과로 해석하면 안 됩니다. 많이 응시했기 때문에 성적이 오른 것이 아니라, "
        "재원 기간, 성실성, 기존 성취도, 시험 참여 성향이 함께 반영된 지표일 수 있습니다. "
        "그럼에도 작년 데이터에서는 4-6회 보통 응시 그룹이 전 권역에서 비교적 안정적인 결과를 보였습니다.",
        "",
        markdown_table(
            participation.sort_values(["pre_level", "avg_csat_core_mean"], ascending=[True, False]),
            [
                ("pre_level", "권역"),
                ("participation_group", "응시 횟수"),
                ("n", "학생 수"),
                ("avg_csat_core_mean", "수능 평균"),
                ("top_25pct_rate", "상위 25% 비율"),
            ],
        ),
        "",
        "## 7. 변동성별 인사이트",
        "",
        figure("segment_volatility_by_level.png", "성취권과 변동성별 수능 결과"),
        "",
        "상위권에서는 변동성이 작은 학생이 더 안정적으로 높은 수능 결과를 보였습니다. "
        "변동성이 큰 상위권은 평균은 여전히 높지만 하락률이 커져, 월별 흔들림 관리가 중요한 신호로 보입니다.",
        "",
        markdown_table(
            volatility.sort_values(["pre_level", "volatility_group"]),
            [
                ("pre_level", "권역"),
                ("volatility_group", "변동성"),
                ("n", "학생 수"),
                ("avg_csat_core_mean", "수능 평균"),
                ("avg_csat_minus_pre", "수능-수능 이전 평균"),
                ("drop_rate", "하락률"),
            ],
        ),
        "",
        "## 8. 계층 이동 분석",
        "",
        "계층 이동은 수능 이전 모의고사 기준 상/중/하위권과 수능 결과 기준 상/중/하위권을 비교해 계산했습니다. "
        "상향 이동은 최종 수능 계층이 시작 계층보다 높아진 경우, 하향 이동은 낮아진 경우입니다.",
        "",
        f"- 상향 이동: {int(movement_counts.get('상향 이동', 0))}명 ({movement_counts.get('상향 이동', 0) / len(mobility_profiles):.1%})",
        f"- 유지: {int(movement_counts.get('유지', 0))}명 ({movement_counts.get('유지', 0) / len(mobility_profiles):.1%})",
        f"- 하향 이동: {int(movement_counts.get('하향 이동', 0))}명 ({movement_counts.get('하향 이동', 0) / len(mobility_profiles):.1%})",
        "",
        figure("mobility_up_rate_by_strength.png", "강점 유형별 계층 상향 이동 비율"),
        "",
        "강점 유형 기준으로는 탐구형과 수학형의 상향 이동 비율이 상대적으로 높게 나타났습니다. "
        "다만 탐구형은 표본이 10명으로 작아, 안정적인 결론보다는 관찰 신호로 보는 것이 적절합니다.",
        "",
        markdown_table(
            mobility_strength[mobility_strength["n"] >= 5],
            [
                ("strength_label", "강점 유형"),
                ("n", "학생 수"),
                ("up_rate", "상향 이동률"),
                ("down_rate", "하향 이동률"),
                ("stay_rate", "유지율"),
                ("avg_level_move", "평균 이동"),
            ],
        ),
        "",
        "응시 횟수 기준으로는 4-6회 보통 응시 그룹의 상향 이동률이 가장 높았습니다.",
        "",
        markdown_table(
            mobility_participation,
            [
                ("participation_group", "응시 횟수"),
                ("n", "학생 수"),
                ("up_rate", "상향 이동률"),
                ("down_rate", "하향 이동률"),
                ("avg_level_move", "평균 이동"),
            ],
        ),
        "",
        "변동성 기준으로는 상향 이동률 차이가 크지 않았습니다. 다만 변동성은 계층 이동보다 하락 위험이나 안정성 해석에 더 적합한 지표로 보입니다.",
        "",
        markdown_table(
            mobility_volatility,
            [
                ("volatility_group", "변동성"),
                ("n", "학생 수"),
                ("up_rate", "상향 이동률"),
                ("down_rate", "하향 이동률"),
                ("avg_level_move", "평균 이동"),
            ],
        ),
        "",
        "세부 유형 중 계층 이동이 활발했던 조합은 아래와 같습니다. 표본 수가 작으므로 학생 전달 시에는 '작년 데이터에서 관찰된 사례'로 표현하는 것이 안전합니다.",
        "",
        markdown_table(
            mobility_detailed[mobility_detailed["n"] >= 3].head(8),
            [
                ("pre_level", "시작 권역"),
                ("strength_label", "강점"),
                ("participation_group", "응시"),
                ("volatility_group", "변동성"),
                ("n", "학생 수"),
                ("up_rate", "상향 이동률"),
                ("down_rate", "하향 이동률"),
                ("avg_level_move", "평균 이동"),
            ],
        ),
        "",
        "## 9. 전달용 핵심 세그먼트",
        "",
        figure("segment_recommendation_bubble.png", "주요 세그먼트 수능 이전 평균 대비 수능 결과"),
        "",
        markdown_table(
            recommendation,
            [
                ("pre_level", "권역"),
                ("strength_label", "강점"),
                ("participation_group", "응시"),
                ("volatility_group", "변동성"),
                ("n", "학생 수"),
                ("avg_csat_core_mean", "수능 평균"),
                ("insight_message", "전달 메시지"),
            ],
            limit=12,
        ),
        "",
        "## 10. 탐구 과목 변경 인사이트",
        "",
        "탐구 과목 변경은 학생과 학부모가 실제로 많이 궁금해하는 지점입니다. "
        "여기서는 탐구1/탐구2 과목 조합이 바뀐 학생을 탐구 변경 학생으로 보고, "
        "변경 전후 탐구 평균 백분위와 수능 탐구 평균을 비교했습니다.",
        "",
        figure("inquiry_switch_vs_keep_csat.png", "탐구 변경 여부별 수능 탐구 평균"),
        "",
        markdown_table(
            inquiry_compare,
            [
                ("group", "구분"),
                ("n", "학생 수"),
                ("avg_pre_all_inquiry_mean", "수능 이전 탐구 평균"),
                ("avg_latest_pre_inquiry_mean", "최신 수능 이전 탐구"),
                ("avg_csat_inquiry_mean", "수능 탐구 평균"),
                ("avg_csat_minus_pre_all", "수능-수능 이전 평균"),
            ],
        ),
        "",
        "탐구 변경 학생은 전체적으로 탐구 유지 학생보다 수능 이전 탐구 평균과 수능 탐구 평균이 낮았습니다. "
        "따라서 단순히 '바꿔서 성적이 낮았다'고 해석하기보다, 애초에 탐구에서 어려움을 겪던 학생들이 변경을 선택했을 가능성을 함께 봐야 합니다.",
        "",
        figure("inquiry_switch_timing_benefit.png", "탐구 변경 시기별 백분위 이득"),
        "",
        markdown_table(
            inquiry_timing,
            [
                ("change_month", "변경 시기"),
                ("n", "학생 수"),
                ("avg_post_minus_pre", "변경 후-전"),
                ("avg_csat_minus_pre_change", "수능-변경 전"),
                ("avg_csat_minus_post_change", "수능-변경 후"),
                ("benefit_rate_post", "변경 후 이득률"),
                ("benefit_rate_csat", "수능 이득률"),
                ("avg_post_records", "변경 후 기록 수"),
            ],
        ),
        "",
        "시기별로는 7월 변경 학생이 표본 6명으로 가장 많고, 변경 후 평균과 수능 탐구 모두 변경 전보다 높게 나타났습니다. "
        "6월과 9월 변경은 이득 폭이 커 보이지만 표본이 각각 1명, 2명이라 참고 신호로만 봐야 합니다. "
        "4-5월 변경 학생은 수능 탐구가 변경 전 평균보다 낮아, 변경 자체보다 탐구 선택의 어려움이 이미 컸던 집단일 가능성이 있습니다.",
        "",
        "학생에게 전달할 때는 '언제 바꾸면 무조건 좋다'가 아니라, "
        "'늦은 변경은 적응 기록 수가 줄어들고, 변경 후에도 충분한 모의고사 검증이 필요하다'는 메시지가 안전합니다.",
        "",
        "## 11. 모의고사 지표와 수능 결과의 관계",
        "",
        figure("top_feature_correlations.png", "수능 결과와 관련 높은 수능 이전 지표"),
        "",
        "수능 결과와 가장 강하게 연결된 지표는 특정 시험 한 번의 결과보다, "
        "수능 이전 모의고사 평균과 최근 평균이었습니다. 특히 수학과 국어 평균 지표가 강하게 나타났습니다.",
        "",
        markdown_table(
            top_corr,
            [
                ("label", "과목"),
                ("feature", "수능 이전 지표"),
                ("n", "표본 수"),
                ("pearson_corr", "상관계수"),
            ],
        ),
        "",
        "## 12. 시험별 수능과의 차이",
        "",
        figure("average_mock_to_csat_gap_by_subject.png", "과목별 모의고사-수능 평균 절대 차이"),
        "",
        markdown_table(
            best_exam,
            [
                ("label", "과목"),
                ("exam_name", "수능과 가장 가까운 시험"),
                ("n", "표본 수"),
                ("mean_abs_gap", "평균 절대 차이"),
                ("pearson_corr", "상관계수"),
            ],
        ),
        "",
        "## 13. 모델 설명력 비교",
        "",
        figure("model_comparison_core_r2.png", "수능 핵심 평균 모델 설명력 비교"),
        "",
        "모델 비교는 개인별 수능 결과를 예측하기 위한 목적이 아니라, "
        "현재 데이터에서 어떤 형태의 설명 방식이 가장 타당한지 확인하기 위한 검증입니다. "
        "복잡한 비선형 모델보다 선형 계열 모델이 충분히 높은 설명력을 보였기 때문에, "
        "상담용 메시지에서는 단순하고 해석 가능한 지표를 우선하는 것이 적절합니다.",
        "",
        markdown_table(
            core_models,
            [
                ("model", "모델"),
                ("n", "표본 수"),
                ("cv_r2_mean", "교차검증 R2"),
                ("cv_mae_mean", "MAE"),
                ("cv_rmse_mean", "RMSE"),
            ],
        ),
        "",
        "## 14. 학생에게 전달할 때의 표현 예시",
        "",
        "- 샘플 데이터에서는 상위권 학생 중 국어, 수학, 탐구가 고르게 받쳐주는 균형형 학생의 수능 결과가 가장 안정적으로 높았습니다.",
        "- 월별 평균 백분위 흐름을 보면 권역별 격차와 유지 양상이 드러나므로, 학생에게 현재 위치와 변화 방향을 설명하는 데 활용할 수 있습니다.",
        "- 작년 데이터에서는 전체의 73.3%가 같은 계층을 유지했고, 상향 이동은 13.8%, 하향 이동은 12.9%였습니다.",
        "- 상위권이라도 월별 성적 변동이 큰 학생은 수능에서 하락한 사례가 더 많이 관찰되어, 흔들림 관리가 중요합니다.",
        "- 중위권은 특정 한 과목 강점보다 약점 축을 줄이고 전체 평균을 끌어올리는 전략이 효과적으로 보입니다.",
        "- 하위권에서는 상승 사례가 존재하지만, 상위권 진입보다는 기본 백분위 평균을 끌어올리는 누적 관리가 우선입니다.",
        "- 응시 횟수는 결과의 원인으로 단정할 수 없지만, 일정 수준 이상 꾸준히 응시한 학생들이 더 안정적인 결과를 보였습니다.",
        "- 탐구 과목 변경은 변경 자체의 효과보다 변경 전후에 충분한 검증 기록을 확보했는지가 더 중요해 보입니다.",
        "",
        "## 15. 해석 주의",
        "",
        "- 본 분석은 샘플 데이터의 패턴 요약이며 개인별 결과를 보장하지 않습니다.",
        "- 표본 수가 작은 세그먼트는 방향성 참고용으로만 사용해야 합니다.",
        "- 응시 횟수와 수능 결과의 관계는 인과가 아니라 상관 또는 집단 특성의 반영일 수 있습니다.",
        "- 계층 이동은 3분위 기준의 상대적 이동이므로, 경계 부근 학생은 작은 점수 변화로도 이동할 수 있습니다.",
        "- 탐구 변경 분석은 표본 수가 작아 시기별 결론을 강하게 일반화하면 안 됩니다.",
        "- 수능 예측보다는 학습 상태 진단, 약점 보완, 변동성 관리, 상담 우선순위 설정에 활용하는 것이 적절합니다.",
        "",
    ]

    return "\n".join(lines)


def main() -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report = build_report()
    output = REPORT_DIR / "final_insight_report.md"
    output.write_text(report, encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
