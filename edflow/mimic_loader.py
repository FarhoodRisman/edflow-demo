"""
edflow/mimic_loader.py
Loads MIMIC-IV-ED tables and maps them to the EDflow canonical schema.

MIMIC-IV-ED tables used:
  edstays.csv   → core visit info (arrival, departure, disposition, transport)
  triage.csv    → acuity (ESI), chief complaint, vitals at triage
  diagnosis.csv → ICD discharge diagnoses (primary only)

Usage:
  from edflow.mimic_loader import load_mimic
  df = load_mimic("data/mimic_demo")
"""

import pandas as pd
import numpy as np
from pathlib import Path


# ── Value maps ────────────────────────────────────────────────────────────────

MIMIC_DISPO_MAP = {
    "home":                        "DC",
    "home health care":            "DC",
    "discharged":                  "DC",
    "admitted":                    "ADM",
    "transfer to other facility":  "TRF",
    "transfer":                    "TRF",
    "transferred":                 "TRF",
    "left without being seen":     "LEFT",
    "left before triage":          "LEFT",
    "eloped":                      "LEFT",
    "left against medical advice": "AMA",
    "ama":                         "AMA",
    "expired":                     "EXP",
    "deceased":                    "EXP",
}

MIMIC_MODE_MAP = {
    "walk in":   "Walk-in",
    "walking":   "Walk-in",
    "ambulance": "EMS",
    "ems":       "EMS",
    "helicopter":"Air",
    "air":       "Air",
    "transfer":  "Transfer",
    "police":    "Police",
    "unknown":   "Unknown",
}

PSYCH_KEYWORDS = [
    "suicid", "psych", "mental", "overdose", " od ",
    "anxiety", "depress", "hallucin", "behavioral",
    "substance", "intox", "detox", "schizo", "bipolar",
    "self harm", "self-harm"
]


# ── Helper functions ──────────────────────────────────────────────────────────

def _find_file(base: Path, filename: str, required: bool = True):
    matches = list(base.rglob(filename))
    if matches:
        return matches[0]
    if required:
        raise FileNotFoundError(
            f"Could not find '{filename}' under {base}.\n"
            f"Make sure the MIMIC-IV-ED CSV files are in: {base}"
        )
    return None


def _map_values(series: pd.Series, mapping: dict, default: str = "OTHER") -> pd.Series:
    def map_one(val):
        if pd.isna(val):
            return default
        s = str(val).lower().strip()
        if s in mapping:
            return mapping[s]
        for k, v in mapping.items():
            if k in s:
                return v
        return default
    return series.apply(map_one)


def _psych_flag(series: pd.Series) -> pd.Series:
    pattern = "|".join(PSYCH_KEYWORDS)
    return series.astype(str).str.lower().str.contains(pattern, na=False)


def _safe_mins(df, t2_col, t1_col):
    """Compute duration in minutes between two timestamp columns."""
    diff = (df[t2_col] - df[t1_col]).dt.total_seconds() / 60
    return diff.where(diff >= 0).where(diff <= 10_080)  # cap at 7 days


def _print_summary(df: pd.DataFrame):
    print("\n── MIMIC-IV-ED Load Summary ──────────────────────────")
    print(f"Total visits:      {len(df):,}")
    if "arrival_time" in df.columns:
        valid = df["arrival_time"].dropna()
        if len(valid):
            print(f"Date range:        {valid.min().date()} → {valid.max().date()}")
    if "acuity" in df.columns:
        print(f"Acuity dist:       {dict(df['acuity'].value_counts().sort_index())}")
    if "disposition_type" in df.columns:
        print(f"Disposition dist:  {dict(df['disposition_type'].value_counts())}")
    if "los" in df.columns:
        print(f"Median LOS:        {df['los'].median():.0f} min")
    null_pcts = {
        c: f"{round(df[c].isna().sum()/len(df)*100,1)}%"
        for c in ["arrival_time","departure_time","acuity",
                  "disposition_type","chief_complaint"]
        if c in df.columns
    }
    print(f"Key null rates:    {null_pcts}")
    print("──────────────────────────────────────────────────────\n")


# ── Main loader ───────────────────────────────────────────────────────────────

def load_mimic(data_dir: str) -> pd.DataFrame:
    """
    Load and join MIMIC-IV-ED tables into EDflow canonical DataFrame.

    Args:
        data_dir: path to folder containing the MIMIC-IV-ED CSV files

    Returns:
        Clean DataFrame in EDflow canonical schema with derived columns.
    """
    data_path = Path(data_dir)

    # ── 1. Load edstays ───────────────────────────────────────────────────────
    print(f"Loading edstays...")
    edstays = pd.read_csv(_find_file(data_path, "edstays.csv"), dtype=str)
    print(f"  → {len(edstays):,} ED stays")

    # ── 2. Load triage ────────────────────────────────────────────────────────
    print(f"Loading triage...")
    triage = pd.read_csv(_find_file(data_path, "triage.csv"), dtype=str)
    print(f"  → {len(triage):,} triage records")

    # ── 3. Load diagnosis (optional) ──────────────────────────────────────────
    diag_path = _find_file(data_path, "diagnosis.csv", required=False)
    if diag_path:
        print(f"Loading diagnosis...")
        diagnosis = pd.read_csv(diag_path, dtype=str)
        primary_dx = (
            diagnosis[diagnosis["seq_num"] == "1"][["stay_id","icd_title"]]
            .rename(columns={"icd_title": "diagnosis"})
        )
        print(f"  → {len(primary_dx):,} primary diagnoses")
    else:
        primary_dx = None
        print("  diagnosis.csv not found — skipping")

    # ── 4. Join tables ────────────────────────────────────────────────────────
    triage_keep = ["stay_id","chiefcomplaint","acuity",
                   "pain","heartrate","resprate","o2sat","sbp","dbp","temperature"]
    triage_use  = triage[[c for c in triage_keep if c in triage.columns]]

    df = edstays.merge(triage_use, on="stay_id", how="left")
    if primary_dx is not None:
        df = df.merge(primary_dx, on="stay_id", how="left")

    print(f"Joined: {len(df):,} rows, {len(df.columns)} columns")

    # ── 5. Map to canonical schema ────────────────────────────────────────────

    df["visit_id"] = df["stay_id"].astype(str)

    # Parse timestamps
    for raw, canon in [("intime","arrival_time"), ("outtime","departure_time")]:
        if raw in df.columns:
            df[canon] = pd.to_datetime(df[raw], errors="coerce")

    # Acuity — ESI 1-5
    if "acuity" in df.columns:
        df["acuity"] = pd.to_numeric(df["acuity"], errors="coerce").astype("Int64")

    # Disposition
    if "disposition" in df.columns:
        df["disposition_type"] = _map_values(df["disposition"], MIMIC_DISPO_MAP)

    # Arrival mode
    if "arrival_transport" in df.columns:
        df["arrival_mode"] = _map_values(
            df["arrival_transport"], MIMIC_MODE_MAP, default="Unknown")

    # Chief complaint
    if "chiefcomplaint" in df.columns:
        df["chief_complaint"] = df["chiefcomplaint"].str.strip()

    # Psych flag
    if "chief_complaint" in df.columns:
        df["is_psych"] = _psych_flag(df["chief_complaint"])
    elif "diagnosis" in df.columns:
        df["is_psych"] = _psych_flag(df["diagnosis"])
    else:
        df["is_psych"] = False

    # Age — not in MIMIC-IV-ED standalone
    if "age" not in df.columns:
        df["age"] = np.nan

    # Horizontal bed — MIMIC has no bed info, assume horizontal
    df["is_horiz"] = True

    # ── 6. Triage time estimate ───────────────────────────────────────────────
    # MIMIC-IV-ED has no separate triage timestamp
    # Estimate as arrival + 8 minutes (typical median)
    if "arrival_time" in df.columns:
        df["triage_time"]           = df["arrival_time"] + pd.Timedelta(minutes=8)
        df["triage_time_estimated"] = True

    # ── 7. Shift dates back 100 years ────────────────────────────────────────
    # MIMIC deliberately shifts all dates ~100 years forward for de-identification
    for col in ["arrival_time", "departure_time", "triage_time"]:
        if col in df.columns:
            df[col] = df[col] - pd.DateOffset(years=100)

    # ── 8. Derived columns ────────────────────────────────────────────────────
    if "arrival_time" in df.columns and "departure_time" in df.columns:
        df["los"] = _safe_mins(df, "departure_time", "arrival_time")

    if "arrival_time" in df.columns and "triage_time" in df.columns:
        df["door_to_triage"] = _safe_mins(df, "triage_time", "arrival_time")

    # Temporal features — computed AFTER date shift
    if "arrival_time" in df.columns:
        df["arrival_hour"]  = df["arrival_time"].dt.hour
        df["arrival_dow"]   = df["arrival_time"].dt.day_name()
        df["arrival_month"] = df["arrival_time"].dt.to_period("M").astype(str)

    # ── 9. Keep canonical columns only ───────────────────────────────────────
    canonical_cols = [
        "visit_id", "arrival_time", "departure_time", "triage_time",
        "arrival_mode", "acuity", "disposition_type", "chief_complaint",
        "diagnosis", "age", "is_psych", "is_horiz",
        "los", "door_to_triage",
        "arrival_hour", "arrival_dow", "arrival_month",
        "triage_time_estimated",
        # Triage vitals
        "pain", "heartrate", "resprate", "o2sat", "sbp", "dbp", "temperature",
        # Keep for future MIMIC-IV linkage
        "subject_id", "hadm_id", "stay_id",
    ]
    df = df[[c for c in canonical_cols if c in df.columns]]

    # ── 10. Quality summary ───────────────────────────────────────────────────
    _print_summary(df)

    return df