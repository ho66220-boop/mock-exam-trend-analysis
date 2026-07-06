# 모델 설명력 비교

> **데이터 출처:** 🟡 공개용 더미(데모) 데이터 · `source=sample` · 파일 `mock_exam_sample.xlsx`
> **표본:** 전체 180명 · 수능결과 137명 · 전체기록 1496건 · 수능이전기록 1031건
> **전처리 생성:** 2026-07-07T00:00:53
> ⚠️ **생존편향 주의:** 전체 180명 중 수능 결과가 있는 137명(76.1%)만 수능 관련 분석에 포함됩니다. 수능 미응시·미기록 43명은 제외되므로, 아래 수치는 '끝까지 남아 수능을 치른 학생' 기준으로 읽어야 합니다.


## 기준

- 대상: `student_group_profiles.csv`의 수능 이전 기록 보유 학생
- 검증: 5-fold 교차검증
- 주요 지표: R2는 설명력, MAE는 평균 절대 오차입니다.
- 이 결과는 상담용 인사이트 검증이며 개인별 수능 예측기로 해석하지 않습니다.

## 타깃별 최고 모델

- 수능 핵심 평균: ElasticNet (R2 0.810, MAE 4.46, n=137)
- 수능 탐구 평균: Ridge regression (R2 0.774, MAE 5.10, n=137)
- 수능 국어 백분위: ElasticNet (R2 0.782, MAE 5.37, n=131)
- 수능 수학 백분위: ElasticNet (R2 0.752, MAE 5.81, n=134)

## 수능 핵심 평균 모델 순위

- ElasticNet: R2 0.810, MAE 4.46, RMSE 5.55
- Ridge regression: R2 0.808, MAE 4.49, RMSE 5.58
- Random forest: R2 0.801, MAE 4.55, RMSE 5.77
- Linear regression: R2 0.796, MAE 4.70, RMSE 5.82
- Gradient boosting: R2 0.782, MAE 4.71, RMSE 6.03
- Mean baseline: R2 -0.056, MAE 11.13, RMSE 13.46

## 수능 핵심 평균에서 중요한 변수

> 중요도는 교차검증 홀드아웃 기준(각 폴드의 테스트셋에서 측정)이며, 파생 중복 변수(pre_core_mean, pre_inquiry_mean, 응시량 파생 라벨 등)를 제외한 비공선 피처 집합에 대해 계산했습니다.

- pre_core_latest: R2 감소 0.142
- pre_math_mean: R2 감소 0.089
- pre_inquiry1_mean: R2 감소 0.084
- pre_inquiry2_mean: R2 감소 0.077
- pre_korean_mean: R2 감소 0.051
- pre_core_std: R2 감소 0.018
- track: R2 감소 0.006
- pre_record_count: R2 감소 0.000

## Ridge 계수 상위 변수 (비공선 피처)

- num__pre_core_latest: +3.451
- num__pre_inquiry1_mean: +2.649
- num__pre_math_mean: +2.642
- num__pre_inquiry2_mean: +2.478
- num__pre_korean_mean: +1.986
- num__pre_core_std: +1.213
- cat__track_인문계열: +0.739
- cat__track_자연계열: -0.739
- num__pre_record_count: -0.281
- num__pre_english_mean: +0.020

## 해석

- R2가 가장 높아도 표본이 작기 때문에 복잡한 모델은 과적합 위험이 있습니다.
- 상담/보고서 용도에서는 Ridge regression처럼 성능과 해석력이 균형 잡힌 모델이 가장 다루기 좋습니다.
- Random forest나 Gradient boosting이 크게 앞서지 않는다면, 비선형 모델보다 선형 모델의 설명을 우선하는 편이 안전합니다.

## 생성 파일

- `output/tables/model_comparison.csv`
- `output/tables/core_model_permutation_importance.csv`
- `output/tables/core_ridge_coefficients.csv`