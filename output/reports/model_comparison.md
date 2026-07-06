# 모델 설명력 비교

> **데이터 출처:** 🟡 공개용 더미(데모) 데이터 · `source=sample` · 파일 `mock_exam_sample.xlsx`
> **표본:** 전체 180명 · 수능결과 137명 · 전체기록 1496건 · 수능이전기록 1031건
> **전처리 생성:** 2026-07-06T23:38:20


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

- pre_core_latest: R2 감소 0.128
- pre_math_mean: R2 감소 0.072
- pre_core_mean: R2 감소 0.034
- pre_inquiry_mean: R2 감소 0.026
- pre_inquiry1_mean: R2 감소 0.024
- pre_korean_mean: R2 감소 0.023
- pre_inquiry2_mean: R2 감소 0.022
- pre_core_std: R2 감소 0.017

## Ridge 계수 상위 변수

- num__pre_core_latest: +2.418
- num__pre_math_mean: +2.094
- num__pre_core_mean: +1.761
- num__pre_inquiry_mean: +1.538
- num__pre_inquiry2_mean: +1.530
- num__pre_inquiry1_mean: +1.528
- num__pre_korean_mean: +1.515
- num__pre_core_std: +1.060
- cat__strength_label_수학형: -0.672
- cat__strength_label_균형형: +0.611

## 해석

- R2가 가장 높아도 표본이 작기 때문에 복잡한 모델은 과적합 위험이 있습니다.
- 상담/보고서 용도에서는 Ridge regression처럼 성능과 해석력이 균형 잡힌 모델이 가장 다루기 좋습니다.
- Random forest나 Gradient boosting이 크게 앞서지 않는다면, 비선형 모델보다 선형 모델의 설명을 우선하는 편이 안전합니다.

## 생성 파일

- `output/tables/model_comparison.csv`
- `output/tables/core_model_permutation_importance.csv`
- `output/tables/core_ridge_coefficients.csv`