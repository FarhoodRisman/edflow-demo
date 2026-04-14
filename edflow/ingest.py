"""
edflow/ingest.py
Full ingestion pipeline:
  1. Load file
  2. Map column names
  3. Standardize & clean all values
  4. Derive computed columns
  5. QC report
"""

import pandas as pd
import numpy as np
import re
from io import BytesIO
from edflow.mapper import map_columns, apply_mapping
from edflow.schema import FIELDS, REQUIRED_FIELDS, DISPOSITION_MAP


# ── 1. LOAD ────────────────────────────────────────────────────────────────────

def load_file(source) -> pd.DataFrame:
    """Accepts file path or Streamlit UploadedFile. Supports CSV and Excel."""
    if hasattr(source, "name"):
        fname = source.name.lower()
    else:
        fname = str(source).lower()

    if fname.endswith((".xlsx", ".xls")):
        return pd.read_excel(source, dtype=str)
    else:
        for enc in ["utf-8", "latin-1", "cp1252"]:
            try:
                if hasattr(source, "seek"):
                    source.seek(0)
                return pd.read_csv(source, dtype=str, encoding=enc, low_memory=False)
            except UnicodeDecodeError:
                continue
        raise ValueError("Could not decode file. Please save as UTF-8 CSV.")


# ── 2. VALUE STANDARDIZATION ───────────────────────────────────────────────────

def _clean_string(val) -> str | None:
    """Strip whitespace, normalize encoding, return None if empty."""
    if pd.isna(val):
        return None
    s = str(val).strip()
    return s if s not in ("", "nan", "NaN", "NULL", "null", "N/A", "n/a", "NA") else None


def _parse_datetime(series: pd.Series) -> pd.Series:
    """
    Robustly parse datetime columns handling all common formats:
    - Standard ISO: 2023-03-01 14:32:00
    - US format:    3/1/2023 2:32 PM
    - Excel serial: 44956.123  (days since 1900-01-01)
    - Compact:      20230301143200
    - Time only:    14:32  (will use a reference date)
    """
    # Try standard parsing first
    parsed = pd.to_datetime(series, errors="coerce", dayfirst=False)

    # For values that failed, try Excel serial number format
    failed_mask = parsed.isna() & series.notna()
    if failed_mask.any():
        def try_excel_serial(val):
            try:
                f = float(str(val).strip())
                # Excel serial: days since 1899-12-30
                if 30000 < f < 60000:
                    return pd.Timestamp("1899-12-30") + pd.Timedelta(days=f)
            except (ValueError, TypeError):
                pass
            return pd.NaT

        reparsed = series[failed_mask].apply(try_excel_serial)
        parsed[failed_mask] = reparsed

    # For remaining failures try compact format YYYYMMDDHHMMSS
    failed_mask = parsed.isna() & series.notna()
    if failed_mask.any():
        def try_compact(val):
            s = str(val).strip().replace(" ", "").replace("-", "").replace(":", "")
            if len(s) == 14 and s.isdigit():
                try:
                    return pd.Timestamp(
                        int(s[:4]), int(s[4:6]), int(s[6:8]),
                        int(s[8:10]), int(s[10:12]), int(s[12:14])
                    )
                except Exception:
                    pass
            return pd.NaT

        reparsed = series[failed_mask].apply(try_compact)
        parsed[failed_mask] = reparsed

    return parsed


def _parse_acuity(series: pd.Series) -> pd.Series:
    """
    Normalize acuity to integer 1–5.
    Handles: '2', 'ESI 3', 'CTAS-4', 'Level 1', 'II', 'High', etc.
    """
    roman  = {"i": 1, "ii": 2, "iii": 3, "iv": 4, "v": 5}
    verbal = {"resuscitation": 1, "emergent": 2, "urgent": 3,
              "less urgent": 4, "non urgent": 5, "non-urgent": 5,
              "immediate": 1, "high": 2, "medium": 3, "low": 4, "minimal": 5}

    def parse_one(val):
        if pd.isna(val):
            return np.nan
        s = str(val).lower().strip()
        # Direct digit 1-5
        m = re.search(r"\b([1-5])\b", s)
        if m:
            return int(m.group(1))
        # Roman numeral
        for rom, num in roman.items():
            if re.fullmatch(rom, s) or re.search(rf"\b{rom}\b", s):
                return num
        # Verbal scale
        for word, num in verbal.items():
            if word in s:
                return num
        return np.nan

    return series.apply(parse_one)


def _parse_disposition(series: pd.Series) -> pd.Series:
    """Map raw disposition strings → canonical DC/ADM/TRF/AMA/LEFT/EXP/OTHER."""
    def map_one(val):
        if pd.isna(val):
            return "OTHER"
        key = str(val).lower().strip()
        # Exact match
        if key in DISPOSITION_MAP:
            return DISPOSITION_MAP[key]
        # Partial / contains match
        for k, v in DISPOSITION_MAP.items():
            if k in key:
                return v
        return "OTHER"
    return series.apply(map_one)


def _parse_arrival_mode(series: pd.Series) -> pd.Series:
    """Normalize arrival mode to standard categories."""
    mode_map = {
        # Walk-in
        "walk":    "Walk-in", "walk in": "Walk-in", "walkin": "Walk-in",
        "self":    "Walk-in", "ambulatory": "Walk-in", "private": "Walk-in",
        "private vehicle": "Walk-in", "car": "Walk-in",
        # EMS / Ambulance
        "ems":       "EMS", "ambulance": "EMS", "paramedic": "EMS",
        "911":       "EMS", "emergency medical": "EMS", "land ambulance": "EMS",
        # Transfer
        "transfer":  "Transfer", "transferred": "Transfer",
        "interfacility": "Transfer", "inter-facility": "Transfer",
        # Air
        "air":       "Air", "helicopter": "Air", "flight": "Air",
        "medevac":   "Air",
        # Police
        "police":    "Police", "law enforcement": "Police",
    }

    def map_one(val):
        if pd.isna(val):
            return "Unknown"
        s = str(val).lower().strip()
        for k, v in mode_map.items():
            if k in s:
                return v
        return str(val).strip().title()   # keep original, title-cased

    return series.apply(map_one)


def _parse_boolean(series: pd.Series) -> pd.Series:
    """
    Normalize any yes/no, true/false, 1/0, Y/N column to True/False.
    """
    true_vals  = {"yes", "y", "true", "t", "1", "x", "✓", "yes "}
    false_vals = {"no",  "n", "false","f", "0", " ", ""}

    def map_one(val):
        if pd.isna(val):
            return None
        s = str(val).lower().strip()
        if s in true_vals:
            return True
        if s in false_vals:
            return False
        return None

    return series.apply(map_one)


def _parse_age(series: pd.Series) -> pd.Series:
    """
    Parse age — handles '45', '45.0', '45 years', '2 months' → float years.
    """
    def parse_one(val):
        if pd.isna(val):
            return np.nan
        s = str(val).lower().strip()
        # months
        m = re.search(r"(\d+\.?\d*)\s*mo", s)
        if m:
            return round(float(m.group(1)) / 12, 2)
        # days
        m = re.search(r"(\d+\.?\d*)\s*d", s)
        if m:
            return round(float(m.group(1)) / 365, 2)
        # plain number
        m = re.search(r"(\d+\.?\d*)", s)
        if m:
            age = float(m.group(1))
            return age if 0 <= age <= 120 else np.nan
        return np.nan

    return series.apply(parse_one)


# ── 3. CLEAN DISPATCHER ────────────────────────────────────────────────────────

def clean(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """
    Apply value standardization to every canonical column present.
    Returns (cleaned_df, cleaning_report).
    """
    report = {}
    datetime_fields = [f for f, m in FIELDS.items() if m["type"] == "datetime"]

    for col in datetime_fields:
        if col not in df.columns:
            continue
        before_null = df[col].isna().sum()
        df[col] = _parse_datetime(df[col])
        new_null = df[col].isna().sum() - before_null
        if new_null > 0:
            report[col] = f"{new_null} values could not be parsed as datetime"

    if "acuity" in df.columns:
        before_null = df["acuity"].isna().sum()
        df["acuity"] = _parse_acuity(df["acuity"])
        new_null = df["acuity"].isna().sum() - before_null
        if new_null > 0:
            report["acuity"] = f"{new_null} values could not be parsed as 1–5"
        df["acuity"] = df["acuity"].astype("Int64")

    if "disposition_type" in df.columns:
        df["disposition_type"] = _parse_disposition(df["disposition_type"])

    if "arrival_mode" in df.columns:
        df["arrival_mode"] = _parse_arrival_mode(df["arrival_mode"])

    if "age" in df.columns:
        df["age"] = _parse_age(df["age"])

    # String fields — clean whitespace and nulls
    string_fields = [f for f, m in FIELDS.items() if m["type"] == "string"]
    for col in string_fields:
        if col in df.columns:
            df[col] = df[col].apply(_clean_string)

    return df, report


# ── 4. DERIVED COLUMNS ─────────────────────────────────────────────────────────

def add_derived_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Compute all derived metrics from clean timestamps."""

    # Fallback visit_id
    if "visit_id" not in df.columns:
        df["visit_id"] = ["V" + str(i+1).zfill(6) for i in range(len(df))]

    def mins(t2, t1):
        diff = (t2 - t1).dt.total_seconds() / 60
        return diff.where(diff >= 0).where(diff <= 10_080)  # cap at 7 days

    pairs = [
        ("los",                  "departure_time",      "arrival_time"),
        ("door_to_triage",       "triage_time",         "arrival_time"),
        ("door_to_bed",          "bed_time",            "arrival_time"),
        ("door_to_physician",    "physician_eval_time", "arrival_time"),
        ("door_to_first_order",  "first_order_time",    "arrival_time"),
        ("eval_to_decision",     "dispo_decision_time", "physician_eval_time"),
        ("decision_to_departure","departure_time",      "dispo_decision_time"),
        ("triage_to_bed",        "bed_time",            "triage_time"),
        ("bed_to_physician",     "physician_eval_time", "bed_time"),
    ]
    for col, t2, t1 in pairs:
        if t2 in df.columns and t1 in df.columns:
            df[col] = mins(df[t2], df[t1])

    # Psych flag
    psych_kw = ["psych", "mental", "suicide", "suicidal", "overdose", "od",
                "psychiatric", "behavioral", "anxiety", "depress", "hallucin",
                "substance", "intox", "detox", "schizo", "bipolar"]
    for src in ["chief_complaint", "diagnosis"]:
        if src in df.columns:
            df["is_psych"] = df[src].astype(str).str.lower().str.contains(
                "|".join(psych_kw), na=False)
            break
    else:
        df["is_psych"] = False

    # Horizontal vs vertical (chair) bed — based on bed_id naming conventions
    if "bed_id" in df.columns:
        df["is_horiz"] = ~df["bed_id"].astype(str).str.lower().str.contains(
            "chair|ch|vertical|vert|wc|wheel", na=False)
    else:
        df["is_horiz"] = True

    # Temporal features
    if "arrival_time" in df.columns:
        df["arrival_hour"]  = df["arrival_time"].dt.hour
        df["arrival_dow"]   = df["arrival_time"].dt.day_name()
        df["arrival_month"] = df["arrival_time"].dt.to_period("M").astype(str)

    return df


# ── 5. QC REPORT ───────────────────────────────────────────────────────────────

def quality_report(df: pd.DataFrame, mapping_result: dict, cleaning_notes: dict) -> dict:
    n = len(df)
    report = {
        "total_rows": n,
        "passed": False,
        "rejection_reasons": [],
        "warnings": [],
        "field_coverage": {},
        "cleaning_notes": cleaning_notes,
        "mapping_review": mapping_result.get("review", []),
        "unmapped_columns": mapping_result.get("unmapped", []),
    }

    for field in REQUIRED_FIELDS:
        if field not in df.columns:
            report["rejection_reasons"].append(
                f"Required column '{field}' could not be mapped.")

    if n < 500:
        report["rejection_reasons"].append(
            f"Only {n} rows found. Minimum ~500 visits needed.")

    if "arrival_time" in df.columns:
        valid = df["arrival_time"].dropna()
        if len(valid):
            days = (valid.max() - valid.min()).days
            if days < 60:
                report["warnings"].append(
                    f"Date range is only {days} days. 90-day minimum recommended.")
            report["date_range_days"] = days
            report["date_min"] = str(valid.min().date())
            report["date_max"] = str(valid.max().date())

    for field in FIELDS:
        if field in df.columns:
            null_pct = round(df[field].isna().sum() / n * 100, 1)
            report["field_coverage"][field] = {
                "present": True, "null_pct": null_pct,
                "required": FIELDS[field]["required"]}
            if null_pct > 20 and FIELDS[field]["required"]:
                report["warnings"].append(
                    f"'{field}' has {null_pct}% missing values.")
        else:
            report["field_coverage"][field] = {
                "present": False, "null_pct": 100.0,
                "required": FIELDS[field]["required"]}

    if "los" in df.columns:
        neg     = (df["los"] < 0).sum()
        extreme = (df["los"] > 1440).sum()
        if neg     > 0: report["warnings"].append(f"{neg} visits have negative LOS.")
        if extreme > 0: report["warnings"].append(f"{extreme} visits have LOS > 24 hours.")

    report["passed"] = len(report["rejection_reasons"]) == 0
    return report


# ── 6. MAIN PIPELINE ───────────────────────────────────────────────────────────

def run_ingestion(source) -> dict:
    """Full pipeline entry point. Call this from Streamlit."""
    raw_df = load_file(source)

    # Auto-assign visit_id if first column is blank/unnamed
    if raw_df.columns[0] in ["", "Unnamed: 0"] or str(raw_df.columns[0]).startswith("Unnamed"):
        raw_df = raw_df.rename(columns={raw_df.columns[0]: "visit_id"})

    mapping_result = map_columns(list(raw_df.columns))

    if mapping_result["missing_required"]:
        return {
            "passed": False, "df": None,
            "qc": {
                "passed": False,
                "rejection_reasons": [
                    f"Could not find required field: '{f}'"
                    for f in mapping_result["missing_required"]],
                "warnings": [],
                "mapping_review":    mapping_result["review"],
                "unmapped_columns":  mapping_result["unmapped"],
                "total_rows":        len(raw_df),
            },
            "mapping": mapping_result,
        }

    df = apply_mapping(raw_df, mapping_result["mapping"])
    df, cleaning_notes = clean(df)
    df = add_derived_columns(df)
    qc = quality_report(df, mapping_result, cleaning_notes)

    return {
        "passed":  qc["passed"],
        "df":      df if qc["passed"] else None,
        "qc":      qc,
        "mapping": mapping_result,
    }