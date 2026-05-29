from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SAMPLE_DIR = ROOT / "data" / "sample"
OUTPUT_PATH = SAMPLE_DIR / "mock_exam_sample.xlsx"

EXAMS = [
    (1, "3월 메가대성 더 프리미엄 모의고사"),
    (2, "4월 메가대성 더 프리미엄 모의고사"),
    (3, "5월 전국 대단위 실전 모의고사"),
    (4, "6월 평가원 모의고사"),
    (5, "7월 메가대성 더 프리미엄 모의고사"),
    (6, "8월 메가대성 더 프리미엄 모의고사"),
    (7, "9월 전국 대단위 실전 모의고사"),
    (8, "9월 평가원 모의고사"),
    (9, "10월 메가대성 더 프리미엄 모의고사"),
    (10, "11월 메가대성 더 프리미엄 모의고사"),
    (11, "2026학년도 수능"),
]

KOREAN = ["언어와매체", "화법과작문"]
MATH_NATURAL = ["미적분", "기하"]
MATH_HUMAN = ["확률과통계"]
INQUIRY_NATURAL = ["물리학Ⅰ", "화학Ⅰ", "생명과학Ⅰ", "지구과학Ⅰ"]
INQUIRY_HUMAN = ["생활과윤리", "사회문화", "한국지리", "세계지리", "정치와법", "윤리와사상"]


def clamp(value: float, lo: int = 1, hi: int = 100) -> int:
    return int(np.clip(round(value), lo, hi))


def grade_from_percentile(value: float) -> int:
    if value >= 90:
        return 1
    if value >= 80:
        return 2
    if value >= 70:
        return 3
    if value >= 60:
        return 4
    if value >= 45:
        return 5
    if value >= 30:
        return 6
    return 7


def generate() -> pd.DataFrame:
    rng = np.random.default_rng(42)
    rows = []
    header = {
        "시험순서": np.nan,
        "시험명": np.nan,
        "익명ID": np.nan,
        "수능 응시 여부": np.nan,
        "계열": np.nan,
        "국어": "선택과목",
        "Unnamed: 6": "백분위",
        "수학": "선택과목",
        "Unnamed: 8": "백분위",
        "영어": "등급",
        "한국사": "등급",
        "탐구1": "선택과목",
        "Unnamed: 12": "백분위",
        "탐구2": "선택과목",
        "Unnamed: 14": "백분위",
    }
    rows.append(header)

    for idx in range(1, 181):
        student_id = f"샘플학생{idx}"
        track = "자연계열" if rng.random() < 0.58 else "인문계열"
        csat_flag = "Y" if rng.random() < 0.72 else "N"
        base = np.clip(rng.normal(78, 13), 35, 98)
        korean_bias = rng.normal(0, 7)
        math_bias = rng.normal(0, 8)
        inquiry_bias = rng.normal(0, 7)
        volatility = rng.uniform(3.0, 9.5)
        attendance_prob = rng.uniform(0.55, 0.95)
        trend = rng.normal(0.25, 0.55)

        korean_subject = rng.choice(KOREAN)
        if track == "자연계열":
            math_subject = rng.choice(MATH_NATURAL, p=[0.82, 0.18])
            inquiry_pool = INQUIRY_NATURAL
        else:
            math_subject = rng.choice(MATH_HUMAN)
            inquiry_pool = INQUIRY_HUMAN
        inquiry_subjects = rng.choice(inquiry_pool, size=2, replace=False).tolist()

        switch_month = None
        if rng.random() < 0.13:
            switch_month = int(rng.choice([4, 5, 6, 7, 8, 9], p=[0.14, 0.14, 0.16, 0.32, 0.12, 0.12]))

        for order, exam_name in EXAMS:
            is_csat = "수능" in exam_name
            if is_csat and csat_flag != "Y":
                continue
            if not is_csat and rng.random() > attendance_prob:
                continue

            if switch_month and order >= switch_month:
                inquiry_subjects = rng.choice(inquiry_pool, size=2, replace=False).tolist()
                switch_month = None
                inquiry_bias += rng.normal(2.5, 4.0)

            exam_effect = (order - 5.5) * trend
            csat_effect = rng.normal(1.2, 4.5) if is_csat else rng.normal(0, 2.0)
            noise = volatility * (0.7 if is_csat else 1.0)

            korean_pct = clamp(base + korean_bias + exam_effect + csat_effect + rng.normal(0, noise))
            math_pct = clamp(base + math_bias + exam_effect + csat_effect + rng.normal(0, noise))
            inq1_pct = clamp(base + inquiry_bias + exam_effect + csat_effect + rng.normal(0, noise))
            inq2_pct = clamp(base + inquiry_bias + exam_effect + csat_effect + rng.normal(0, noise))
            english_grade = grade_from_percentile(base + rng.normal(0, 9))
            history_grade = grade_from_percentile(base + rng.normal(0, 12))

            if rng.random() < 0.025:
                korean_pct = 0
            if rng.random() < 0.035:
                math_pct = 0
            if rng.random() < 0.035:
                inq1_pct = 0
            if rng.random() < 0.035:
                inq2_pct = 0

            rows.append(
                {
                    "시험순서": order,
                    "시험명": exam_name,
                    "익명ID": student_id,
                    "수능 응시 여부": csat_flag,
                    "계열": track,
                    "국어": korean_subject,
                    "Unnamed: 6": korean_pct,
                    "수학": math_subject,
                    "Unnamed: 8": math_pct,
                    "영어": english_grade,
                    "한국사": history_grade,
                    "탐구1": inquiry_subjects[0],
                    "Unnamed: 12": inq1_pct,
                    "탐구2": inquiry_subjects[1],
                    "Unnamed: 14": inq2_pct,
                }
            )

    return pd.DataFrame(rows)


def main() -> None:
    SAMPLE_DIR.mkdir(parents=True, exist_ok=True)
    df = generate()
    df.to_excel(OUTPUT_PATH, index=False)
    print(f"created={OUTPUT_PATH}")
    print(f"rows={len(df)}")


if __name__ == "__main__":
    main()
