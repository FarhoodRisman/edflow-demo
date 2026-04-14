"""
edflow/kpis.py
Computes all descriptive KPIs from the clean EDflow DataFrame.
Includes cross-segment analysis matching the full screenshot layout.
All time values in minutes.
"""

import pandas as pd
import numpy as np


# ── Helpers ───────────────────────────────────────────────────────────────────

def _stats(series: pd.Series) -> dict | None:
    s = series.dropna()
    if len(s) < 5:
        return None
    arr = np.sort(s.values)
    n   = len(arr)

    def pct(p):
        return float(np.percentile(arr, p))

    return {
        "n":    n,
        "avg":  round(float(s.mean()), 1),
        "min":  round(float(arr[0]), 1),
        "p25":  round(pct(25), 1),
        "med":  round(pct(50), 1),
        "p75":  round(pct(75), 1),
        "p90":  round(pct(90), 1),
        "max":  round(float(arr[-1]), 1),
        "u2hr": round((s <= 120).sum() / n * 100, 1),
        "u3hr": round((s <= 180).sum() / n * 100, 1),
        "u4hr": round((s <= 240).sum() / n * 100, 1),
    }


def _vol_pct(n: int, total: int) -> float:
    if total == 0: return 0.0
    return round(n / total * 100, 1)


def _seg_stats(df, mask, col="los", total=None):
    """Stats for a masked subset, with vol_pct added."""
    subset = df[mask][col] if mask.any() else pd.Series(dtype=float)
    s = _stats(subset)
    if s and total:
        s["vol_pct"] = _vol_pct(s["n"], total)
    return s


# ── 1. LOS TABLE ──────────────────────────────────────────────────────────────

def los_table(df: pd.DataFrame) -> dict:
    """
    Full LOS statistics matching the screenshot layout.
    Includes cross-segments: acute×dispo, psych×dispo, non-psych×dispo.
    """
    if "los" not in df.columns:
        return {}

    total = len(df)
    result = {
        "total_visits": total,
        "overall": _stats(df["los"]),
    }
    if result["overall"]:
        result["overall"]["vol_pct"] = 100.0

    # ── By Disposition ────────────────────────────────────────────────────────
    result["by_disposition"] = {}
    for d in ["DC","ADM","TRF","AMA","LEFT","EXP"]:
        mask = df["disposition_type"] == d
        result["by_disposition"][d] = _seg_stats(df, mask, total=total)

    # ── By Acuity ─────────────────────────────────────────────────────────────
    result["by_acuity"] = {}
    if "acuity" in df.columns:
        for a in [1,2,3,4,5]:
            mask = df["acuity"] == a
            result["by_acuity"][a] = _seg_stats(df, mask, total=total)

    # ── By Location ───────────────────────────────────────────────────────────
    result["by_location"] = {}
    if "is_horiz" in df.columns:
        result["by_location"]["horiz"] = _seg_stats(df, df["is_horiz"]==True,  total=total)
        result["by_location"]["vert"]  = _seg_stats(df, df["is_horiz"]==False, total=total)

    # ── By Psych ──────────────────────────────────────────────────────────────
    result["by_psych"] = {}
    if "is_psych" in df.columns:
        result["by_psych"]["psych"]     = _seg_stats(df, df["is_psych"]==True,  total=total)
        result["by_psych"]["non_psych"] = _seg_stats(df, df["is_psych"]==False, total=total)

    # ── By Acute zone ─────────────────────────────────────────────────────────
    result["by_zone"] = {}
    if "is_acute" in df.columns:
        result["by_zone"]["acute"]     = _seg_stats(df, df["is_acute"]==True,  total=total)
        result["by_zone"]["non_acute"] = _seg_stats(df, df["is_acute"]==False, total=total)
    elif "acuity" in df.columns:
        # Fallback: acute = acuity 1-2, non-acute = 4-5, 3 split
        result["by_zone"]["acute"]     = _seg_stats(df, df["acuity"]<=2, total=total)
        result["by_zone"]["non_acute"] = _seg_stats(df, df["acuity"]>=4, total=total)

    # ── Cross-segments: Acute × Disposition ───────────────────────────────────
    result["acute_by_disposition"] = {}
    if "is_acute" in df.columns:
        acute_mask = df["is_acute"] == True
        for d in ["DC","ADM","TRF"]:
            mask = acute_mask & (df["disposition_type"] == d)
            result["acute_by_disposition"][d] = _seg_stats(df, mask, total=total)

    # ── Cross-segments: Psych × Disposition ───────────────────────────────────
    result["psych_by_disposition"] = {}
    result["non_psych_by_disposition"] = {}
    if "is_psych" in df.columns:
        psych_mask     = df["is_psych"] == True
        non_psych_mask = df["is_psych"] == False
        for d in ["DC","ADM","TRF"]:
            d_mask = df["disposition_type"] == d
            result["psych_by_disposition"][d]     = _seg_stats(df, psych_mask & d_mask,     total=total)
            result["non_psych_by_disposition"][d] = _seg_stats(df, non_psych_mask & d_mask, total=total)

    return result


# ── 2. FLOW METRICS ───────────────────────────────────────────────────────────

def flow_metrics(df: pd.DataFrame) -> dict:
    """Door-to-X interval statistics for each process step."""
    intervals = {
        "door_to_triage":        "Door to Triage",
        "door_to_bed":           "Door to Bed",
        "door_to_physician":     "Door to Physician",
        "bed_to_physician":      "Bed to Physician",
        "door_to_first_order":   "Door to First Order",
        "eval_to_decision":      "Eval to Dispo Decision",
        "decision_to_departure": "Decision to Departure",
        "los":                   "Total LOS",
    }
    result = {}
    for col, label in intervals.items():
        if col in df.columns:
            s = _stats(df[col])
            if s:
                s["label"] = label
                result[col] = s

    # Flow by acuity — door to physician per acuity level
    result["door_to_physician_by_acuity"] = {}
    if "acuity" in df.columns and "door_to_physician" in df.columns:
        for a in [1,2,3,4,5]:
            s = _stats(df[df["acuity"]==a]["door_to_physician"])
            if s:
                result["door_to_physician_by_acuity"][a] = s

    return result


# ── 3. VOLUME PATTERNS ────────────────────────────────────────────────────────

def volume_patterns(df: pd.DataFrame) -> dict:
    total = len(df)
    result = {}

    if "arrival_hour" in df.columns:
        hourly = df.groupby("arrival_hour").size().reindex(range(24), fill_value=0)
        result["by_hour"] = [
            {"hour": h, "label": f"{h:02d}:00", "n": int(hourly[h])}
            for h in range(24)
        ]

    if "arrival_dow" in df.columns:
        dow_order = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
        dow = df.groupby("arrival_dow").size().reindex(dow_order, fill_value=0)
        result["by_dow"] = [
            {"day": d, "n": int(dow[d]), "vol_pct": _vol_pct(int(dow[d]), total)}
            for d in dow_order
        ]

    if "arrival_month" in df.columns:
        monthly = df.groupby("arrival_month").size().sort_index()
        result["by_month"] = [
            {"month": m, "n": int(n)} for m, n in monthly.items()
        ]

    if "acuity" in df.columns:
        acuity = df.groupby("acuity").size()
        result["by_acuity"] = [
            {"level": int(a), "n": int(acuity.get(a,0)),
             "vol_pct": _vol_pct(int(acuity.get(a,0)), total)}
            for a in [1,2,3,4,5]
        ]

    if "disposition_type" in df.columns:
        dispos = df.groupby("disposition_type").size()
        result["by_disposition"] = [
            {"dispo": d, "n": int(dispos.get(d,0)),
             "vol_pct": _vol_pct(int(dispos.get(d,0)), total)}
            for d in ["DC","ADM","TRF","AMA","LEFT","EXP","OTHER"]
            if dispos.get(d,0) > 0
        ]

    if "arrival_mode" in df.columns:
        modes = df.groupby("arrival_mode").size().sort_values(ascending=False)
        result["by_arrival_mode"] = [
            {"mode": str(m), "n": int(n), "vol_pct": _vol_pct(int(n), total)}
            for m, n in modes.items()
        ]

    # Arrivals heatmap: hour × day of week
    if "arrival_hour" in df.columns and "arrival_dow" in df.columns:
        dow_order = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
        heat = df.groupby(["arrival_dow","arrival_hour"]).size().reset_index(name="n")
        result["heatmap_hour_dow"] = heat.to_dict("records")

    return result


# ── 4. PERFORMANCE BENCHMARKS ─────────────────────────────────────────────────

def performance_benchmarks(df: pd.DataFrame) -> dict:
    """
    % of patients meeting key time targets.
    Useful for accreditation and quality reporting.
    """
    total = len(df)
    result = {}

    targets = {
        "triage_within_15min":    ("door_to_triage",    15),
        "physician_within_30min": ("door_to_physician", 30),
        "physician_within_60min": ("door_to_physician", 60),
        "los_within_4hr":         ("los",              240),
        "los_within_6hr":         ("los",              360),
        "boarding_under_60min":   ("decision_to_departure", 60),
    }

    for key, (col, threshold) in targets.items():
        if col in df.columns:
            met = (df[col] <= threshold).sum()
            result[key] = {
                "n":   int(met),
                "pct": _vol_pct(met, total),
                "threshold_min": threshold,
            }

    # By acuity — physician within 60 min
    result["physician_60min_by_acuity"] = {}
    if "acuity" in df.columns and "door_to_physician" in df.columns:
        for a in [1,2,3,4,5]:
            sub = df[df["acuity"]==a]
            if len(sub):
                met = (sub["door_to_physician"] <= 60).sum()
                result["physician_60min_by_acuity"][a] = {
                    "n": int(met),
                    "pct": _vol_pct(met, len(sub)),
                }

    return result


# ── 5. HEADLINE KPIs ──────────────────────────────────────────────────────────

def headline_kpis(df: pd.DataFrame) -> dict:
    total = len(df)

    lwbs_n = int((df["disposition_type"].isin(["LEFT","AMA"])).sum()) \
             if "disposition_type" in df.columns else 0
    adm_n  = int((df["disposition_type"]=="ADM").sum()) \
             if "disposition_type" in df.columns else 0

    med_los = round(df["los"].median(), 1)             if "los" in df.columns else None
    med_d2p = round(df["door_to_physician"].median(),1) if "door_to_physician" in df.columns else None
    med_d2t = round(df["door_to_triage"].median(),1)    if "door_to_triage" in df.columns else None
    med_d2b = round(df["door_to_bed"].median(),1)       if "door_to_bed" in df.columns else None

    date_min = date_max = date_range_days = None
    if "arrival_time" in df.columns:
        valid = df["arrival_time"].dropna()
        if len(valid):
            date_min        = str(valid.min().date())
            date_max        = str(valid.max().date())
            date_range_days = (valid.max() - valid.min()).days

    return {
        "total_visits":              total,
        "median_los":                med_los,
        "lwbs_n":                    lwbs_n,
        "lwbs_pct":                  _vol_pct(lwbs_n, total),
        "admission_n":               adm_n,
        "admission_pct":             _vol_pct(adm_n, total),
        "median_door_to_physician":  med_d2p,
        "median_door_to_triage":     med_d2t,
        "median_door_to_bed":        med_d2b,
        "date_min":                  date_min,
        "date_max":                  date_max,
        "date_range_days":           date_range_days,
    }


# ── 6. MAIN ENTRY POINT ───────────────────────────────────────────────────────

def compute_all(df: pd.DataFrame) -> dict:
    """Single call — returns everything the dashboard needs."""
    return {
        "headline":     headline_kpis(df),
        "los":          los_table(df),
        "flow":         flow_metrics(df),
        "volume":       volume_patterns(df),
        "benchmarks":   performance_benchmarks(df),
    }