from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
SAMPLE_RAW_DIR = ROOT / "data" / "sample"
PROCESSED_DIR = ROOT / "data" / "processed"

COLUMN_NAMES = [
    "exam_order",
    "exam_name",
    "student_id",
    "csat_flag",
    "track",
    "korean_subject",
    "korean_percentile",
    "math_subject",
    "math_percentile",
    "english_grade",
    "history_grade",
    "inquiry1_subject",
    "inquiry1_percentile",
    "inquiry2_subject",
    "inquiry2_percentile",
]

NUMERIC_COLUMNS = [
    "exam_order",
    "korean_percentile",
    "math_percentile",
    "english_grade",
    "history_grade",
    "inquiry1_percentile",
    "inquiry2_percentile",
]

SUBJECT_COLUMNS = [
    "korean_subject",
    "math_subject",
    "inquiry1_subject",
    "inquiry2_subject",
]

CSAT_KEYWORD = "\uc218\ub2a5"


def find_raw_excel() -> Path:
    search_dir = SAMPLE_RAW_DIR if (SAMPLE_RAW_DIR / "mock_exam_sample.xlsx").exists() else RAW_DIR
    files = sorted(search_dir.glob("*.xlsx"))
    if not files:
        raise FileNotFoundError(f"No .xlsx file found in {search_dir}")
    if len(files) > 1:
        names = ", ".join(file.name for file in files)
        raise RuntimeError(f"Expected one raw Excel file, found {len(files)}: {names}")
    return files[0]


def load_and_clean(path: Path) -> pd.DataFrame:
    df = pd.read_excel(path)
    df = df[df.iloc[:, 2].notna()].copy()
    df.columns = COLUMN_NAMES

    for column in NUMERIC_COLUMNS:
        df[column] = pd.to_numeric(df[column], errors="coerce")

    for column in ["exam_name", "student_id", "csat_flag", "track", *SUBJECT_COLUMNS]:
        df[column] = df[column].astype("string").str.strip()

    df["is_csat"] = df["exam_name"].str.contains(CSAT_KEYWORD, na=False)
    df["is_before_csat"] = ~df["is_csat"]

    # In this workbook, zero appears in score fields where a score was not recorded.
    score_columns = [
        "korean_percentile",
        "math_percentile",
        "english_grade",
        "history_grade",
        "inquiry1_percentile",
        "inquiry2_percentile",
    ]
    for column in score_columns:
        df[f"{column}_raw"] = df[column]
        df[column] = df[column].mask(df[column] == 0)

    return df.sort_values(["student_id", "exam_order", "exam_name"]).reset_index(drop=True)


def main() -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    source = find_raw_excel()
    clean = load_and_clean(source)

    csat_targets = clean[clean["is_csat"]].copy()
    csat_students = set(csat_targets["student_id"])
    pre_csat_records = clean[
        clean["student_id"].isin(csat_students) & clean["is_before_csat"]
    ].copy()

    clean.to_csv(PROCESSED_DIR / "clean_records.csv", index=False, encoding="utf-8-sig")
    csat_targets.to_csv(PROCESSED_DIR / "csat_targets.csv", index=False, encoding="utf-8-sig")
    pre_csat_records.to_csv(
        PROCESSED_DIR / "pre_csat_records.csv", index=False, encoding="utf-8-sig"
    )

    print(f"source={source}")
    print(f"clean_records={len(clean)} rows, {clean['student_id'].nunique()} students")
    print(
        f"csat_targets={len(csat_targets)} rows, "
        f"{csat_targets['student_id'].nunique()} students"
    )
    print(
        f"pre_csat_records={len(pre_csat_records)} rows, "
        f"{pre_csat_records['student_id'].nunique()} students"
    )


if __name__ == "__main__":
    main()
