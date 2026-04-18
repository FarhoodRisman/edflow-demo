"""
pages/2_Upload.py
EDflow — EDIS data upload page.
Three entry points:
  1. Synthetic sample data (instant, no upload)
  2. MIMIC-IV-ED real research data (instant, no upload)
  3. Upload your own EDIS CSV / Excel file
"""

import streamlit as st
import pandas as pd
from pathlib import Path

from edflow.ingest import run_ingestion, load_file, clean, add_derived_columns, quality_report
from edflow.mapper import map_columns, apply_mapping
from edflow.schema import FIELDS, REQUIRED_FIELDS
from edflow.synthetic import generate_sample_data
from edflow.kpis import compute_all

st.set_page_config(
    page_title="EDflow — Data Upload",
    page_icon="🏥",
    layout="wide"
)

# ── If data already loaded — show summary ─────────────────────────────────────
if "edflow_df" in st.session_state:
    df      = st.session_state["edflow_df"]
    qc      = st.session_state.get("edflow_qc", {})
    source  = st.session_state.get("edflow_source", "file")

    badge = {
        "synthetic": "🧪 Synthetic sample data",
        "mimic":     "🏥 MIMIC-IV-ED research data",
        "file":      "📁 Your uploaded data",
    }.get(source, "📁 Data loaded")

    st.success(
        f"{badge} — **{len(df):,} visits** "
        f"({qc.get('date_min','?')} → {qc.get('date_max','?')})"
    )

    c1, c2, c3 = st.columns([1,1,2])
    with c1:
        if st.button("→ Go to Dashboard", type="primary", use_container_width=True):
            st.switch_page("pages/1_Dashboard.py")
    with c2:
        if st.button("↺ Load different data", use_container_width=True):
            for k in ["edflow_df","edflow_qc","edflow_source"]:
                st.session_state.pop(k, None)
            st.rerun()
    st.stop()


# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("## 🏥 EDflow — Load Data")

# ── Privacy notice ────────────────────────────────────────────────────────────
st.markdown("""
<div style='background:#f0fdf4;border:1px solid #bbf7d0;border-radius:10px;
            padding:14px 18px;margin-bottom:24px;display:flex;
            gap:14px;align-items:flex-start'>
    <div style='font-size:20px'>🔒</div>
    <div>
        <div style='font-weight:700;font-size:13px;color:#166534;margin-bottom:4px'>
            Only operational de-identified data
        </div>
        <div style='font-size:12px;color:#374151;line-height:1.6'>
            EDflow works with <strong>de-identified operational data</strong>
            (no names, MRNs, or DOBs).
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# ── Three entry points ────────────────────────────────────────────────────────
col1, col2, col3 = st.columns(3, gap="large")

# ── Option 1 — Synthetic sample data ─────────────────────────────────────────
with col1:
    st.markdown("""
    <div style='border:2px solid #0ea5e9;border-radius:12px;padding:22px;
                background:linear-gradient(135deg,#f0f9ff,#fff);text-align:center;
                min-height:220px'>
        <div style='font-size:36px;margin-bottom:8px'>🧪</div>
        <div style='font-weight:800;font-size:15px;color:#0f172a;margin-bottom:8px'>
            Synthetic Sample Data
        </div>
        <div style='font-size:12px;color:#6b7280;line-height:1.6;margin-bottom:6px'>
            Statistically modelled ED dataset — 4,500 visits over 91 days.
            All KPIs, filters, and charts fully populated. No upload needed.
        </div>
        <div style='background:#f0f9ff;border-radius:6px;padding:5px 10px;
                    display:inline-block;font-size:11px;color:#0369a1;font-weight:600'>
            Instant · No registration
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("<div style='margin-top:8px'>", unsafe_allow_html=True)
    if st.button("▶  Load Synthetic Data", type="primary",
                 use_container_width=True, key="btn_synthetic"):
        with st.spinner("Generating sample dataset..."):
            df = generate_sample_data(n_visits=4500, start_date="2024-01-01")
            kpis = compute_all(df)
            h    = kpis["headline"]
            st.session_state["edflow_df"]     = df
            st.session_state["edflow_qc"]     = h
            st.session_state["edflow_source"] = "synthetic"
        st.switch_page("pages/1_Dashboard.py")
    st.markdown("</div>", unsafe_allow_html=True)

# ── Option 2 — MIMIC-IV-ED ────────────────────────────────────────────────────
with col2:
    mimic_available = Path("data/mimic_demo/edstays.csv").exists()

    st.markdown(f"""
    <div style='border:2px solid {"#8b5cf6" if mimic_available else "#e5e7eb"};
                border-radius:12px;padding:22px;
                background:{"linear-gradient(135deg,#faf5ff,#fff)" if mimic_available else "#fafafa"};
                text-align:center;min-height:220px'>
        <div style='font-size:36px;margin-bottom:8px'>🏥</div>
        <div style='font-weight:800;font-size:15px;color:#0f172a;margin-bottom:8px'>
            MIMIC-IV-ED Research Data
        </div>
        <div style='font-size:12px;color:#6b7280;line-height:1.6;margin-bottom:6px'>
            Real de-identified ED data from Beth Israel Deaconess Medical Center,
            Boston. Published by MIT. 222 visits in the demo subset.
        </div>
        <div style='background:{"#f5f3ff" if mimic_available else "#f1f5f9"};
                    border-radius:6px;padding:5px 10px;display:inline-block;
                    font-size:11px;
                    color:{"#6d28d9" if mimic_available else "#94a3b8"};
                    font-weight:600'>
            {"✅ Ready" if mimic_available else "⚠️ Demo files not found"}
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<div style='margin-top:8px'>", unsafe_allow_html=True)
    if mimic_available:
        if st.button("▶  Load MIMIC-IV-ED Demo", type="primary",
                     use_container_width=True, key="btn_mimic"):
            with st.spinner("Loading MIMIC-IV-ED data..."):
                from edflow.mimic_loader import load_mimic
                df   = load_mimic("data/mimic_demo")
                kpis = compute_all(df)
                h    = kpis["headline"]
                st.session_state["edflow_df"]     = df
                st.session_state["edflow_qc"]     = h
                st.session_state["edflow_source"] = "mimic"
            st.switch_page("pages/1_Dashboard.py")
    else:
        st.button("▶  Load MIMIC-IV-ED Demo",
                  use_container_width=True,
                  key="btn_mimic_disabled",
                  disabled=True)
        st.caption("Run `python3 -c 'from edflow.mimic_loader import load_mimic'` "
                   "to verify setup")
    st.markdown("</div>", unsafe_allow_html=True)

    # MIMIC credit
    st.markdown("""
    <div style='font-size:10px;color:#d1d5db;text-align:center;margin-top:6px'>
        Johnson et al., PhysioNet 2023 · CC BY 4.0
    </div>
    """, unsafe_allow_html=True)

# ── Option 3 — Upload your own file ──────────────────────────────────────────
with col3:
    st.markdown("""
    <div style='border:1px solid #e5e7eb;border-radius:12px;padding:22px;
                background:#fafafa;text-align:center;min-height:220px'>
        <div style='font-size:36px;margin-bottom:8px'>📁</div>
        <div style='font-weight:800;font-size:15px;color:#0f172a;margin-bottom:8px'>
            Upload Your EDIS Data
        </div>
        <div style='font-size:12px;color:#6b7280;line-height:1.6;margin-bottom:6px'>
            Upload a 3-month export from Epic, Cerner, Meditech, or any EDIS.
            Column names are mapped automatically regardless of format.
        </div>
        <div style='background:#f1f5f9;border-radius:6px;padding:5px 10px;
                    display:inline-block;font-size:11px;color:#64748b;font-weight:600'>
            CSV · XLSX · XLS
        </div>
    </div>
    """, unsafe_allow_html=True)

    uploaded = st.file_uploader(
        "Drop your file here",
        type=["csv","xlsx","xls"],
        label_visibility="collapsed",
        key="file_uploader"
    )

# ── Process uploaded file ─────────────────────────────────────────────────────
if uploaded:
    st.markdown("---")
    st.markdown("### Column Mapping")

    with st.spinner("Reading and mapping columns..."):
        uploaded.seek(0)
        raw_df         = load_file(uploaded)
        raw_columns    = list(raw_df.columns)
        mapping_result = map_columns(raw_columns)

    c1, c2, c3 = st.columns(3)
    c1.metric("Auto-mapped",        len(mapping_result["mapping"]))
    c2.metric("Needs review",       len(mapping_result["review"]))
    c3.metric("Unmapped (ignored)", len(mapping_result["unmapped"]))

    # Auto-confirmed
    if mapping_result["mapping"]:
        with st.expander("✅ Auto-confirmed mappings", expanded=False):
            rows = [{"Your column": r, "Mapped to": c,
                     "Required": "✓" if FIELDS[c]["required"] else "○",
                     "Label": FIELDS[c]["label"]}
                    for r, c in mapping_result["mapping"].items()]
            st.dataframe(pd.DataFrame(rows),
                         use_container_width=True, hide_index=True)

    # Review
    user_review = {}
    if mapping_result["review"]:
        st.markdown("**🔍 Please confirm these low-confidence matches:**")
        for item in mapping_result["review"]:
            ca, cb, cc = st.columns([2,2,1])
            ca.markdown(f"`{item['raw']}`")
            choice = cb.selectbox(
                "Map to:",
                options=["— skip —"] + list(FIELDS.keys()),
                format_func=lambda k: f"{k}  ({FIELDS[k]['label']})" if k in FIELDS else k,
                index=list(FIELDS.keys()).index(item["suggested"]) + 1
                      if item["suggested"] in FIELDS else 0,
                key=f"review_{item['raw']}"
            )
            cc.markdown(
                f"<small style='color:gray'>confidence: {item['score']}%</small>",
                unsafe_allow_html=True)
            if choice != "— skip —":
                user_review[item["raw"]] = choice

    # Manual override for missing required fields
    already_mapped = set(mapping_result["mapping"].values()) | set(user_review.values())
    still_missing  = [f for f in REQUIRED_FIELDS if f not in already_mapped]
    user_manual = {}
    if still_missing:
        st.markdown("---")
        st.error(f"⚠️ {len(still_missing)} required field(s) not detected — "
                 "please assign manually:")
        for field in still_missing:
            ca, cb = st.columns([2,3])
            ca.markdown(
                f"**{FIELDS[field]['label']}**  \n"
                f"<small style='color:gray'>{FIELDS[field]['description']}</small>",
                unsafe_allow_html=True)
            choice = cb.selectbox(
                "Which column is this?",
                options=["— not in my file —"] + raw_columns,
                key=f"manual_{field}"
            )
            if choice != "— not in my file —":
                user_manual[choice] = field

    # Unmapped
    if mapping_result["unmapped"]:
        with st.expander(
                f"⬜ {len(mapping_result['unmapped'])} unmapped columns (ignored)"):
            st.write(", ".join(f"`{c}`" for c in mapping_result["unmapped"]))

    # Confirm button
    st.markdown("---")
    if st.button("✅ Confirm Mappings & Validate", type="primary"):
        combined = {**mapping_result["mapping"], **user_review, **user_manual}

        uploaded.seek(0)
        raw2 = load_file(uploaded)
        df   = apply_mapping(raw2, combined)
        df, notes = clean(df)
        df   = add_derived_columns(df)

        final_missing  = [f for f in REQUIRED_FIELDS if f not in combined.values()]
        updated_mapping = {
            **mapping_result,
            "mapping":         combined,
            "review":          [],
            "missing_required": final_missing,
        }
        qc = quality_report(df, updated_mapping, notes)

        if qc["passed"]:
            kpis = compute_all(df)
            h    = kpis["headline"]
            st.success(
                f"✅ Validation passed — **{len(df):,} visits** ready "
                f"({qc.get('date_min','?')} → {qc.get('date_max','?')})"
            )
            st.session_state["edflow_df"]     = df
            st.session_state["edflow_qc"]     = h
            st.session_state["edflow_source"] = "file"

            # Field coverage
            st.markdown("### Field Coverage")
            cov_rows = [
                {"Field":    FIELDS[f]["label"],
                 "Required": "✓" if FIELDS[f]["required"] else "○",
                 "Found":    "✅" if i["present"] else "❌",
                 "Missing %":f"{i['null_pct']}%"}
                for f, i in qc.get("field_coverage",{}).items()
            ]
            st.dataframe(pd.DataFrame(cov_rows),
                         use_container_width=True, hide_index=True)

            if st.button("→ Go to Dashboard", type="primary"):
                st.switch_page("pages/1_Dashboard.py")
        else:
            st.error("❌ Validation failed:")
            for r in qc["rejection_reasons"]:
                st.markdown(f"- 🚫 {r}")

        if qc.get("warnings"):
            with st.expander(f"⚠️ {len(qc['warnings'])} warning(s)"):
                for w in qc["warnings"]:
                    st.markdown(f"- {w}")