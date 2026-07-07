# Mock Exam Trend Analysis

누적 모의고사 성적 데이터를 정리해 학생별 성적 흐름, 응시 패턴, 과목 강점, 변동성, 선택과목 변경과 수능 결과의 관계를 확인하는 분석 프로젝트입니다.

이 프로젝트는 개인별 수능 성적을 단정적으로 예측하거나 학생을 등급화하기 위한 도구가 아닙니다. 목표는 익명화된 누적 성적 데이터를 바탕으로 학생 상담과 운영 판단에 활용할 수 있는 인사이트를 만드는 것입니다.

---

## 1. 프로젝트 목적

학원 모의고사 데이터는 시험이 누적될수록 학생별 흐름을 한눈에 보기 어려워집니다. 학생마다 응시 횟수가 다르고, 일부 과목은 미응시 또는 미기록이 있으며, 선택과목 변경도 함께 관리해야 합니다.

이 프로젝트는 엑셀 원본 데이터를 분석 가능한 형태로 정리한 뒤 다음 질문에 답하는 것을 목표로 합니다.

- 상위권, 중위권, 하위권 학생의 월별 평균 백분위 흐름은 어떻게 다른가
- 수능 이전 모의고사 흐름과 실제 수능 결과는 어떤 관계를 보이는가
- 국어형, 수학형, 탐구형, 균형형 중 어떤 유형이 수능 결과에서 강했는가
- 응시 횟수가 많은 학생과 적은 학생의 수능 결과는 어떻게 다른가
- 변동성이 큰 학생과 작은 학생의 결과 차이는 무엇인가
- 계층 상향 이동과 하향 이동이 어떤 학생 유형에서 더 많이 나타났는가
- 탐구 과목을 변경한 학생은 변경 시기별로 실제 이득을 보았는가
- 어떤 분석 모델이 현재 데이터의 패턴을 가장 잘 설명하는가

---

## 2. 데이터 기준

원본 데이터는 익명화된 학생별 모의고사 누적 엑셀 파일입니다.

| 항목 | 내용 |
| --- | --- |
| 데이터 형태 | 엑셀 기반 누적 성적 데이터 |
| 주요 단위 | 학생별 x 시험별 응시 기록 |
| 학생 식별값 | 익명ID |
| 시험 정보 | 시험순서, 시험명 |
| 학생 정보 | 수능 응시 여부, 계열 |
| 국어 | 선택과목, 백분위 |
| 수학 | 선택과목, 백분위 |
| 영어 | 등급 |
| 한국사 | 등급 |
| 탐구1 | 선택과목, 백분위 |
| 탐구2 | 선택과목, 백분위 |

공개용 더미 데이터 기준:

- 전체 응시 기록: 1,496건
- 전체 샘플 학생: 180명
- 수능 결과 보유 학생: 137명
- 수능 이전 모의고사 기록과 수능 결과가 모두 있는 학생: 137명

원본 엑셀 파일과 전처리 CSV는 민감한 성적 데이터이므로 GitHub에 업로드하지 않습니다.

---

## 3. 저장소 구조

```text
.
├─ README.md
├─ requirements.txt
├─ data/
│  ├─ raw/
│  │  └─ .gitkeep
│  ├─ sample/
│  │  └─ mock_exam_sample.xlsx
│  └─ processed/
│     └─ .gitkeep
├─ output/
│  ├─ figures/
│  │  └─ 분석 결과 이미지
│  ├─ reports/
│  │  └─ 분석 리포트
│  └─ tables/
│     └─ .gitkeep
└─ scripts/
   ├─ preprocess_excel.py
   ├─ analyze_insights.py
   ├─ analyze_student_groups.py
   ├─ compare_models.py
   ├─ segment_student_profiles.py
   ├─ create_segment_figures.py
   ├─ analyze_monthly_mobility.py
   ├─ analyze_inquiry_switching.py
   ├─ generate_dummy_data.py
   ├─ build_final_report.py
   ├─ build_final_report_ppt.py
   └─ build_teacher_ppt.py
```

GitHub에는 분석 코드, 최종 리포트, 시각화 이미지만 포함합니다. `data/raw`, `data/processed`, `output/tables`의 실제 데이터 파일은 `.gitignore`로 제외합니다.

---

## 4. 실행 방법

### 4.1 패키지 설치

```bash
pip install -r requirements.txt
```

### 4.2 원본 엑셀 배치

실제 원본 엑셀 파일을 `data/raw/` 폴더에 넣으면 내부 분석에 사용할 수 있습니다. 공개 저장소에는 실제 원본 대신 더미 데이터 `data/sample/mock_exam_sample.xlsx`를 포함합니다.

현재 스크립트는 `data/sample/mock_exam_sample.xlsx`가 있으면 샘플 파일을 우선 사용하고, 샘플 파일이 없을 때 `data/raw` 안의 `.xlsx` 파일 1개를 읽도록 구성되어 있습니다.

```text
data/raw/
└─ 실제 원본 엑셀 파일.xlsx

data/sample/
└─ mock_exam_sample.xlsx
```

### 4.3 분석 실행 순서

전체 파이프라인은 한 번에 실행할 수 있습니다. `--source`로 실제 원본과 공개용 더미를 명시적으로 선택하며, 선택한 출처는 `data/processed/dataset_manifest.json`에 기록되어 모든 리포트 상단 배너에 표기됩니다(실데이터/더미 혼입 방지).

```bash
# 공개용 더미(데모)
python scripts/run_all.py --source sample

# 실제 원본(비공개) — data/raw/ 의 실제 엑셀 사용
python scripts/run_all.py --source raw

# PowerPoint 산출물 제외
python scripts/run_all.py --source sample --skip-ppt
```

개별 단계로 실행하려면 다음 순서를 따릅니다(`preprocess_excel.py`만 `--source`를 받습니다).

```bash
python scripts/preprocess_excel.py --source sample
python scripts/analyze_insights.py
python scripts/analyze_student_groups.py
python scripts/compare_models.py
python scripts/segment_student_profiles.py
python scripts/analyze_monthly_mobility.py
python scripts/analyze_inquiry_switching.py
python scripts/create_segment_figures.py
python scripts/build_final_report.py
python scripts/build_final_report_ppt.py
python scripts/build_teacher_ppt.py
```

### 4.4 회귀 검증

핵심 불변식(더미 표본 수, 9월 시험 분리, 모델 설명력, 소표본/생존편향 라벨 등)을 자동 점검합니다.

```bash
python scripts/check_pipeline.py
```

---

## 5. 주요 분석 내용

### 5.1 데이터 전처리

`scripts/preprocess_excel.py`

- 엑셀의 보조 헤더 제거
- 국어, 수학, 탐구 선택과목과 백분위 컬럼 정리
- 수능 기록과 수능 이전 모의고사 기록 분리
- 점수 0을 미응시 또는 미기록 가능성이 있는 결측값으로 처리
- 분석용 CSV 생성

생성 파일:

```text
data/processed/clean_records.csv
data/processed/csat_targets.csv
data/processed/pre_csat_records.csv
```

### 5.2 모의고사 지표와 수능 결과 관계

`scripts/analyze_insights.py`

- 과목별 평균, 최근 점수, 최고점, 변동성 지표 생성
- 수능 결과와의 상관 분석
- 단순 예측 기준선 비교
- 시험별 수능과의 평균 차이 계산

### 5.3 학생 그룹 분석

`scripts/analyze_student_groups.py`

- 응시 횟수별 수능 결과 비교
- 국어형, 수학형, 탐구형, 균형형 분류
- 강점 유형과 수능 결과 비교
- 응시량 x 강점 유형 교차 분석

### 5.4 세분화 학생 프로파일

`scripts/segment_student_profiles.py`

- 수능 이전 모의고사 평균 기준 상위권, 중위권, 하위권 분류
- 과목 강점 유형 분류
- 응시 횟수 그룹 분류
- 변동성 큰 학생과 작은 학생 분류
- 전달용 핵심 세그먼트 생성

### 5.5 월별 흐름 및 계층 이동

`scripts/analyze_monthly_mobility.py`

- 상위권, 중위권, 하위권의 월별 평균 백분위 흐름 시각화
- 수능 이전 계층과 수능 결과 계층 비교
- 상향 이동, 유지, 하향 이동 학생 비율 계산
- 강점 유형, 응시 횟수, 변동성별 계층 이동 분석

### 5.6 탐구 과목 변경 분석

`scripts/analyze_inquiry_switching.py`

- 탐구1/탐구2 과목 조합 변경 학생 탐지
- 변경 시기별 변경 전후 탐구 평균 비교
- 변경 시기별 수능 탐구 이득 여부 분석
- 탐구 유지 학생과 탐구 변경 학생 비교

### 5.7 모델 설명력 비교

`scripts/compare_models.py`

개인별 수능 성적을 예측하기 위한 목적이 아니라, 현재 데이터에서 어떤 형태의 설명 방식이 가장 타당한지 확인하기 위한 비교입니다.

비교 모델:

- 평균 기준선
- Linear Regression
- Ridge Regression
- ElasticNet
- Random Forest
- Gradient Boosting

---

## 6. 주요 산출물

### 6.1 최종 리포트

```text
output/reports/final_insight_report.md
```

포함 내용:

- 월별 상/중/하위권 평균 백분위 흐름
- 전체 상/중/하위권 요약
- 과목 강점 유형별 인사이트
- 응시 횟수별 인사이트
- 변동성별 인사이트
- 계층 이동 분석
- 탐구 과목 변경 인사이트
- 모의고사 지표와 수능 결과의 관계
- 시험별 수능과의 차이
- 모델 설명력 비교
- 학생에게 전달할 표현 예시
- 해석 주의사항

### 6.2 보조 리포트

```text
output/reports/insight_report.md
output/reports/student_group_insights.md
output/reports/segmented_student_insights.md
output/reports/monthly_mobility_insights.md
output/reports/inquiry_switching_insights.md
output/reports/model_comparison.md
```

### 6.3 공유용 PPT

```text
output/reports/mock_exam_insight_teacher_briefing.pptx
```

PPT의 그래프와 표는 이미지가 아니라 PowerPoint 차트/표 객체로 생성되어, 축 제목, 범례, 표 문구, 데이터 값을 직접 수정할 수 있습니다.

### 6.4 시각화

```text
output/figures/monthly_level_percentile_trend.png
output/figures/segment_level_csat_mean.png
output/figures/segment_strength_by_level.png
output/figures/segment_participation_by_level.png
output/figures/segment_volatility_by_level.png
output/figures/segment_recommendation_bubble.png
output/figures/mobility_up_rate_by_strength.png
output/figures/inquiry_switch_vs_keep_csat.png
output/figures/inquiry_switch_timing_benefit.png
output/figures/model_comparison_core_r2.png
output/figures/top_feature_correlations.png
output/figures/average_mock_to_csat_gap_by_subject.png
```

---

## 7. 해석 원칙

이 프로젝트의 분석 결과는 학생 상담을 위한 참고 자료입니다.

- 개인별 수능 결과를 보장하거나 단정하지 않습니다.
- 응시 횟수와 성적 결과의 관계를 인과로 해석하지 않습니다.
- 계층 이동은 3분위 기준의 상대적 이동이므로 경계 부근 학생은 작은 점수 변화로도 이동할 수 있습니다.
- 탐구 변경 분석은 표본 수가 작아 시기별 결론을 강하게 일반화하지 않습니다.
- 수능 결과가 있는 학생이 전체 학생 중 일부이므로 수능 관련 분석은 참고 신호로 사용합니다.

---

## 8. 데이터 관리 기준

실제 성적 데이터에는 민감한 학업 정보가 포함될 수 있으므로 원본 데이터는 공개 저장소에 업로드하지 않습니다.

GitHub에 포함하는 자료:

- 분석 스크립트
- 실행 환경 파일
- 최종 리포트
- 결과 시각화 이미지
- 폴더 구조 유지용 `.gitkeep`

GitHub에서 제외하는 자료:

- 원본 엑셀 파일
- 전처리 CSV
- 분석용 중간 테이블 CSV
- 로컬 가상환경 및 캐시 파일

---

## 9. 프로젝트 한계

본 프로젝트는 특정 입시 사이클의 재원생 데이터를 기반으로 합니다. 따라서 모든 수험생에게 일반화하기 어렵습니다.

또한 학생별 응시 횟수와 시험별 응시자 구성이 다르기 때문에 단순 평균 비교에는 주의가 필요합니다. 분석 결과는 정밀한 예측 모델이 아니라, 상담과 운영 판단을 돕는 패턴 요약으로 해석해야 합니다.
