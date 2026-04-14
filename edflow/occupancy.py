"""
edflow/occupancy.py
Computes time-based operational metrics from patient timestamps.

Core concept: for any moment T, we can calculate exactly how many patients
were in each stage of care — waiting for triage, waiting for bed,
waiting for physician, in treatment, boarding, etc.

All functions return data ready for plotting.
"""

import pandas as pd
import numpy as np
from datetime import timedelta


# ── Helpers ───────────────────────────────────────────────────────────────────

def _time_grid(df: pd.DataFrame, interval_minutes: int = 30) -> pd.DatetimeIndex:
    """
    Build a regular time grid spanning the full dataset.
    Default 30-minute intervals — fine enough for operational patterns.
    """
    t_min = df["arrival_time"].min().floor("h")
    t_max = df["departure_time"].dropna().max().ceil("h")
    return pd.date_range(t_min, t_max, freq=f"{interval_minutes}min")


def _count_in_stage(df: pd.DataFrame, t_start_col: str, t_end_col: str,
                    grid: pd.DatetimeIndex) -> np.ndarray:
    """
    Vectorized count: for each point in grid, count patients where
    t_start <= T < t_end. Uses numpy broadcasting for speed.
    """
    subset = df[[t_start_col, t_end_col]].dropna()
    if subset.empty:
        return np.zeros(len(grid), dtype=int)

    starts  = subset[t_start_col].values.astype("datetime64[ns]")
    ends    = subset[t_end_col].values.astype("datetime64[ns]")
    grid_ns = grid.values.astype("datetime64[ns]")

    counts = np.sum(
        (starts[np.newaxis, :] <= grid_ns[:, np.newaxis]) &
        (ends[np.newaxis, :]   >  grid_ns[:, np.newaxis]),
        axis=1
    )
    return counts.astype(int)


# ── 1. CENSUS OVER TIME ───────────────────────────────────────────────────────

def census_over_time(df: pd.DataFrame, interval_minutes: int = 30) -> pd.DataFrame:
    """
    Total patients in the ED at each point in time.
    Broken down by: total, by acuity, by psych, by stage of care.

    Returns DataFrame with columns:
        timestamp, total, acuity_1..5, psych, non_psych,
        waiting_triage, waiting_bed, waiting_physician,
        in_treatment, boarding
    """
    if "arrival_time" not in df.columns or "departure_time" not in df.columns:
        return pd.DataFrame()

    grid = _time_grid(df, interval_minutes)
    result = pd.DataFrame({"timestamp": grid})

    # Total census
    result["total"] = _count_in_stage(df, "arrival_time", "departure_time", grid)

    # By acuity
    if "acuity" in df.columns:
        for a in [1, 2, 3, 4, 5]:
            sub = df[df["acuity"] == a]
            if len(sub):
                result[f"acuity_{a}"] = _count_in_stage(
                    sub, "arrival_time", "departure_time", grid)

    # Psych vs non-psych
    if "is_psych" in df.columns:
        result["psych"]     = _count_in_stage(
            df[df["is_psych"]],  "arrival_time", "departure_time", grid)
        result["non_psych"] = _count_in_stage(
            df[~df["is_psych"]], "arrival_time", "departure_time", grid)

    # ── Queue stages ──────────────────────────────────────────────────────────
    # Waiting for triage: arrived but not yet triaged
    if "triage_time" in df.columns:
        result["q_waiting_triage"] = _count_in_stage(
            df, "arrival_time", "triage_time", grid)

    # Waiting for bed: triaged but not yet in bed
    if "triage_time" in df.columns and "bed_time" in df.columns:
        result["q_waiting_bed"] = _count_in_stage(
            df, "triage_time", "bed_time", grid)

    # Waiting for physician: in bed but not yet seen
    if "bed_time" in df.columns and "physician_eval_time" in df.columns:
        result["q_waiting_physician"] = _count_in_stage(
            df, "bed_time", "physician_eval_time", grid)

    # In active treatment: physician seen, dispo not yet decided
    if "physician_eval_time" in df.columns and "dispo_decision_time" in df.columns:
        result["in_treatment"] = _count_in_stage(
            df, "physician_eval_time", "dispo_decision_time", grid)

    # Boarding: dispo decided but still in ED waiting to leave
    if "dispo_decision_time" in df.columns and "departure_time" in df.columns:
        result["boarding"] = _count_in_stage(
            df, "dispo_decision_time", "departure_time", grid)

    # Hour and day for aggregation
    result["hour"] = result["timestamp"].dt.hour
    result["dow"]  = result["timestamp"].dt.day_name()

    return result


# ── 2. AVERAGE CENSUS BY HOUR ─────────────────────────────────────────────────

def avg_census_by_hour(census_df: pd.DataFrame) -> pd.DataFrame:
    """
    Average census at each hour of day (0-23), across all days.
    Shows typical operational load by hour.
    """
    if census_df.empty:
        return pd.DataFrame()

    cols = ["total"] + [c for c in census_df.columns
                        if c.startswith(("acuity_","q_","in_treatment","boarding","psych"))]
    cols = [c for c in cols if c in census_df.columns]

    return census_df.groupby("hour")[cols].mean().round(1).reset_index()


# ── 3. PEAK METRICS ───────────────────────────────────────────────────────────

def peak_metrics(census_df: pd.DataFrame, df: pd.DataFrame) -> dict:
    """
    Summary of peak operational loads.
    """
    if census_df.empty:
        return {}

    result = {}

    if "total" in census_df.columns:
        peak_row = census_df.loc[census_df["total"].idxmax()]
        result["peak_census"]      = int(census_df["total"].max())
        result["peak_census_time"] = str(peak_row["timestamp"])
        result["avg_census"]       = round(census_df["total"].mean(), 1)
        result["median_census"]    = round(census_df["total"].median(), 1)

    if "q_waiting_physician" in census_df.columns:
        result["peak_waiting_physician"] = int(census_df["q_waiting_physician"].max())
        result["avg_waiting_physician"]  = round(census_df["q_waiting_physician"].mean(), 1)

    if "q_waiting_bed" in census_df.columns:
        result["peak_waiting_bed"] = int(census_df["q_waiting_bed"].max())
        result["avg_waiting_bed"]  = round(census_df["q_waiting_bed"].mean(), 1)

    if "boarding" in census_df.columns:
        result["peak_boarding"] = int(census_df["boarding"].max())
        result["avg_boarding"]  = round(census_df["boarding"].mean(), 1)
        # Boarding hours = total boarding patient-minutes / 60
        if "dispo_decision_time" in df.columns and "departure_time" in df.columns:
            boarding_mins = (
                df["departure_time"] - df["dispo_decision_time"]
            ).dt.total_seconds().dropna() / 60
            boarding_mins = boarding_mins[boarding_mins > 0]
            result["total_boarding_hours"] = round(boarding_mins.sum() / 60, 0)
            result["median_boarding_time"] = round(boarding_mins.median(), 1)

    return result


# ── 4. SIMULTANEOUS ARRIVALS ──────────────────────────────────────────────────

def arrival_intensity(df: pd.DataFrame, interval_minutes: int = 60) -> pd.DataFrame:
    """
    Number of new arrivals per hour-of-day, averaged across all days.
    Useful for staffing decisions.
    """
    if "arrival_time" not in df.columns:
        return pd.DataFrame()

    df = df.copy()
    df["hour"]       = df["arrival_time"].dt.hour
    df["arrival_date"] = df["arrival_time"].dt.date

    # Count arrivals per (date, hour)
    hourly = df.groupby(["arrival_date","hour"]).size().reset_index(name="n")

    # Average across days
    n_days = df["arrival_date"].nunique()
    avg_by_hour = hourly.groupby("hour")["n"].sum() / n_days

    return pd.DataFrame({
        "hour":  avg_by_hour.index,
        "label": [f"{h:02d}:00" for h in avg_by_hour.index],
        "avg_arrivals_per_hour": avg_by_hour.values.round(1),
    })


# ── 5. SIMULTANEOUS PATIENTS NEEDING A BED ────────────────────────────────────

def bed_demand_by_hour(census_df: pd.DataFrame) -> pd.DataFrame:
    """
    Average number of patients occupying a bed (bed_time → departure_time) by hour.
    Useful for bed planning.
    """
    if census_df.empty or "total" not in census_df.columns:
        return pd.DataFrame()
    return avg_census_by_hour(census_df)


# ── 6. MAIN ENTRY POINT ───────────────────────────────────────────────────────

def compute_occupancy(df: pd.DataFrame) -> dict:
    """
    Full occupancy analysis. Call this from the dashboard.

    Returns:
    {
      "census":        DataFrame — full time-series census
      "by_hour":       DataFrame — average census by hour of day
      "arrivals":      DataFrame — average arrivals per hour
      "peak":          dict      — peak/avg summary metrics
    }
    """
    census   = census_over_time(df, interval_minutes=30)
    by_hour  = avg_census_by_hour(census)
    arrivals = arrival_intensity(df)
    peaks    = peak_metrics(census, df)

    return {
        "census":   census,
        "by_hour":  by_hour,
        "arrivals": arrivals,
        "peak":     peaks,
    }