"""
pages/1_Dashboard.py
EDflow descriptive dashboard with interactive filters.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import io

from edflow.kpis import compute_all
from edflow.occupancy import compute_occupancy
from edflow.schema import FIELDS

@st.cache_data(show_spinner=False)
def cached_kpis(df_hash, df):
    return compute_all(df)

@st.cache_data(show_spinner=False)
def cached_occupancy(df_hash, df):
    return compute_occupancy(df)

st.set_page_config(page_title="EDflow — Dashboard", page_icon="🏥", layout="wide")

# ── Guard ─────────────────────────────────────────────────────────────────────
if "edflow_df" not in st.session_state:
    st.warning("No data loaded. Please upload your EDIS file first.")
    if st.button("← Go to Upload"):
        st.switch_page("pages/2_Upload.py")
    st.stop()

# ── Colour palette ────────────────────────────────────────────────────────────
DISPO_CLR = {"DC":"#22c55e","ADM":"#ef4444","TRF":"#f97316",
             "AMA":"#a855f7","LEFT":"#f59e0b","EXP":"#64748b"}
ACU_CLR   = {1:"#ef4444",2:"#f97316",3:"#eab308",4:"#22c55e",5:"#3b82f6"}
ACU_NAMES = {1:"Acuity 1 — Resuscitation",2:"Acuity 2 — Emergent",
             3:"Acuity 3 — Urgent",4:"Acuity 4 — Less Urgent",5:"Acuity 5 — Non-Urgent"}
STAGE_CLR = {
    "q_waiting_triage":    "#fbbf24",
    "q_waiting_bed":       "#f97316",
    "q_waiting_physician": "#ef4444",
    "in_treatment":        "#0ea5e9",
    "boarding":            "#8b5cf6",
}
STAGE_LABELS = {
    "q_waiting_triage":    "Waiting Triage",
    "q_waiting_bed":       "Waiting Bed",
    "q_waiting_physician": "Waiting Physician",
    "in_treatment":        "In Treatment",
    "boarding":            "Boarding",
}

# ════════════════════════════════════════════════════════════════════════════════
# SIDEBAR FILTERS
# ════════════════════════════════════════════════════════════════════════════════
raw_df  = st.session_state["edflow_df"]
is_demo = st.session_state.get("edflow_is_demo", False)

with st.sidebar:
    st.markdown("### ⚡ EDflow")
    st.markdown("---")
    st.markdown("#### 🔍 Filters")
    st.caption("All charts and tables update instantly")

    # Date range
    if "arrival_time" in raw_df.columns:
        min_date = raw_df["arrival_time"].min().date()
        max_date = raw_df["arrival_time"].max().date()
        date_range = st.date_input(
            "Date range",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date,
            key="filter_date"
        )
    else:
        date_range = None

    # Acuity
    acuity_options = sorted(raw_df["acuity"].dropna().unique().tolist()) \
                     if "acuity" in raw_df.columns else []
    selected_acuity = st.multiselect(
        "Acuity level",
        options=acuity_options,
        default=acuity_options,
        format_func=lambda x: f"Level {x}",
        key="filter_acuity"
    )

    # Disposition
    dispo_options = sorted(raw_df["disposition_type"].dropna().unique().tolist()) \
                    if "disposition_type" in raw_df.columns else []
    selected_dispo = st.multiselect(
        "Disposition",
        options=dispo_options,
        default=dispo_options,
        key="filter_dispo"
    )

    # Arrival mode
    mode_options = sorted(raw_df["arrival_mode"].dropna().unique().tolist()) \
                   if "arrival_mode" in raw_df.columns else []
    selected_mode = st.multiselect(
        "Arrival mode",
        options=mode_options,
        default=mode_options,
        key="filter_mode"
    )

    # Psych toggle
    psych_filter = st.radio(
        "Patient type",
        options=["All patients", "Psych only", "Non-psych only"],
        index=0,
        key="filter_psych"
    )

    # Shift filter
    shift_filter = st.radio(
        "Shift",
        options=["All shifts", "Day (07:00–15:00)",
                 "Evening (15:00–23:00)", "Night (23:00–07:00)"],
        index=0,
        key="filter_shift"
    )

    st.markdown("---")
    if st.button("↺ Reset all filters", use_container_width=True):
        for k in ["filter_date","filter_acuity","filter_dispo",
                  "filter_mode","filter_psych","filter_shift"]:
            st.session_state.pop(k, None)
        st.rerun()

    st.markdown("---")
    if st.button("← Upload New File", use_container_width=True):
        for k in ["edflow_df","edflow_qc","edflow_is_demo"]:
            st.session_state.pop(k, None)
        st.switch_page("pages/2_Upload.py")


# ── Apply filters ─────────────────────────────────────────────────────────────
df = raw_df.copy()

# Date
if date_range and len(date_range) == 2:
    start, end = pd.Timestamp(date_range[0]), pd.Timestamp(date_range[1])
    df = df[(df["arrival_time"] >= start) & (df["arrival_time"] <= end + pd.Timedelta(days=1))]

# Acuity
if selected_acuity and "acuity" in df.columns:
    df = df[df["acuity"].isin(selected_acuity)]

# Disposition
if selected_dispo and "disposition_type" in df.columns:
    df = df[df["disposition_type"].isin(selected_dispo)]

# Arrival mode
if selected_mode and "arrival_mode" in df.columns:
    df = df[df["arrival_mode"].isin(selected_mode)]

# Psych
if psych_filter == "Psych only" and "is_psych" in df.columns:
    df = df[df["is_psych"] == True]
elif psych_filter == "Non-psych only" and "is_psych" in df.columns:
    df = df[df["is_psych"] == False]

# Shift
if shift_filter != "All shifts" and "arrival_hour" in df.columns:
    if shift_filter == "Day (07:00–15:00)":
        df = df[df["arrival_hour"].between(7, 14)]
    elif shift_filter == "Evening (15:00–23:00)":
        df = df[df["arrival_hour"].between(15, 22)]
    elif shift_filter == "Night (23:00–07:00)":
        df = df[(df["arrival_hour"] >= 23) | (df["arrival_hour"] < 7)]

# ── Warn if filtered to too few rows ─────────────────────────────────────────
if len(df) < 30:
    st.warning(f"⚠️ Only {len(df)} visits match current filters — statistics may not be reliable.")

# ── Compute KPIs on filtered data ─────────────────────────────────────────────
# Build a reliable cache key from filter state
df_hash = hash((
    len(df),
    str(selected_acuity),
    str(selected_dispo),
    str(selected_mode),
    psych_filter,
    shift_filter,
    str(date_range),
))

with st.spinner("Updating metrics..."):
    kpis = cached_kpis(df_hash, df)

h    = kpis["headline"]
los  = kpis["los"]
flow = kpis["flow"]
vol  = kpis["volume"]
bm   = kpis["benchmarks"]

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("## 🏥 EDflow — Descriptive Dashboard")
demo_badge = " &nbsp;🧪 *Sample data*" if is_demo else ""

# Active filter badges
active = []
if selected_acuity and len(selected_acuity) < len(acuity_options):
    active.append(f"Acuity: {', '.join(str(a) for a in selected_acuity)}")
if selected_dispo and len(selected_dispo) < len(dispo_options):
    active.append(f"Dispo: {', '.join(selected_dispo)}")
if psych_filter != "All patients":
    active.append(psych_filter)
if shift_filter != "All shifts":
    active.append(shift_filter)

filter_str = " &nbsp;·&nbsp; ".join([f"🔵 {f}" for f in active]) if active else "No filters active"

st.caption(
    f"{h['date_min']} → {h['date_max']} &nbsp;·&nbsp; "
    f"**{h['total_visits']:,} visits** &nbsp;·&nbsp; "
    f"{h['date_range_days']} days{demo_badge}"
    f"<br><small style='color:#9ca3af'>{filter_str}</small>",
    unsafe_allow_html=True
)

# ── Headline KPI cards ─────────────────────────────────────────────────────────
k1,k2,k3,k4,k5,k6 = st.columns(6)

# Compare filtered vs total for deltas
total_n = len(raw_df)
filt_n  = len(df)
delta_n = filt_n - total_n if active else None

k1.metric("Visits (filtered)",      f"{filt_n:,}",
          delta=f"{delta_n:,} vs total" if delta_n is not None else None,
          delta_color="off")
k2.metric("Median LOS",             f"{h['median_los']} min"    if h['median_los'] else "N/A")
k3.metric("Door to Physician",      f"{h['median_door_to_physician']} min"
                                     if h['median_door_to_physician'] else "N/A")
k4.metric("Door to Triage",         f"{h['median_door_to_triage']} min"
                                     if h['median_door_to_triage'] else "N/A")
k5.metric("LWBS / AMA",             f"{h['lwbs_pct']}%",
          delta=f"{h['lwbs_n']} visits", delta_color="inverse")
k6.metric("Admission Rate",         f"{h['admission_pct']}%",
          delta=f"{h['admission_n']} admits", delta_color="off")

st.markdown("---")

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📋 LOS Statistics",
    "⏱️  Flow Metrics",
    "🏥 Occupancy & Queues",
    "📊 Volume Patterns",
    "🎯 Benchmarks",
])


# ════════════════════════════════════════════════════════════════════════════════
# TAB 1 — LOS STATISTICS
# ════════════════════════════════════════════════════════════════════════════════
with tab1:
    st.markdown("### Length of Stay — Statistics Table")
    st.caption("All values in minutes · updates with filters")

    # Quick segment selector
    seg_choice = st.radio(
        "Show columns:",
        ["Core (Disposition + Acuity)", "Extended (Zone + Psych × Dispo)", "All"],
        horizontal=True, key="los_seg"
    )

    COLS_CORE = [
        ("overall",             "Overall LOS",  "#f8fafc"),
        ("by_disposition.DC",   "DC",           "#dcfce7"),
        ("by_disposition.ADM",  "ADM",          "#fee2e2"),
        ("by_disposition.TRF",  "TRF",          "#ffedd5"),
        ("by_disposition.AMA",  "AMA",          "#f3e8ff"),
        ("by_disposition.LEFT", "LEFT",         "#fef9c3"),
        ("by_acuity.1",         "Acuity 1",     "#fee2e2"),
        ("by_acuity.2",         "Acuity 2",     "#ffedd5"),
        ("by_acuity.3",         "Acuity 3",     "#fef9c3"),
        ("by_acuity.4",         "Acuity 4",     "#dcfce7"),
        ("by_acuity.5",         "Acuity 5",     "#dbeafe"),
    ]
    COLS_EXT = [
        ("by_location.horiz",              "Horiz Bed",        "#d1fae5"),
        ("by_location.vert",               "Vert / Chair",     "#e0f2fe"),
        ("by_psych.psych",                 "Psych",            "#f3e8ff"),
        ("by_psych.non_psych",             "Non-Psych",        "#f0fdf4"),
        ("by_zone.acute",                  "Acute Zone",       "#fee2e2"),
        ("by_zone.non_acute",              "Non-Acute Zone",   "#dcfce7"),
        ("acute_by_disposition.DC",        "Acute DC",         "#dcfce7"),
        ("acute_by_disposition.ADM",       "Acute ADM",        "#fee2e2"),
        ("psych_by_disposition.DC",        "Psych DC",         "#f3e8ff"),
        ("psych_by_disposition.ADM",       "Psych ADM",        "#f3e8ff"),
        ("non_psych_by_disposition.DC",    "Non-Psych DC",     "#f0fdf4"),
        ("non_psych_by_disposition.ADM",   "Non-Psych ADM",    "#f0fdf4"),
    ]

    if seg_choice == "Core (Disposition + Acuity)":
        COLS = COLS_CORE
    elif seg_choice == "Extended (Zone + Psych × Dispo)":
        COLS = [COLS_CORE[0]] + COLS_EXT
    else:
        COLS = COLS_CORE + COLS_EXT

    ROWS = [
        ("avg","Average"),("min","Minimum"),("p25","25th %ile"),
        ("med","Median"),("p75","75th %ile"),("p90","90th %ile"),
        ("max","Maximum"),("vol_pct","% of Volume"),
        ("u2hr","Cum % ≤ 2 hr"),("u3hr","Cum % ≤ 3 hr"),("u4hr","Cum % ≤ 4 hr"),
    ]

    def get_seg(path):
        parts = path.split(".")
        node = los
        for p in parts:
            if node is None: return None
            node = node.get(p) if isinstance(node,dict) else None
        return node

    table_data = {"Statistic": [r[1] for r in ROWS]}
    for path, label, _ in COLS:
        seg = get_seg(path)
        col_vals = []
        for field, _ in ROWS:
            if seg is None:
                col_vals.append("—")
            elif field == "vol_pct" and path == "overall":
                col_vals.append("100%")
            else:
                val = seg.get(field)
                if val is None:
                    col_vals.append("—")
                elif field in ("vol_pct","u2hr","u3hr","u4hr"):
                    col_vals.append(f"{val}%")
                else:
                    col_vals.append(str(int(val)) if val==int(val) else str(val))
        table_data[label] = col_vals

    table_df = pd.DataFrame(table_data)

    def style_row(row):
        if row["Statistic"] == "Median":
            return ["font-weight:bold;background:#f0f9ff"] * len(row)
        elif row["Statistic"] == "% of Volume":
            return ["background:#fef9c3;font-weight:bold"] * len(row)
        elif "Cum %" in row["Statistic"]:
            return ["background:#f0fdf4"] * len(row)
        return [""] * len(row)

    st.dataframe(table_df.style.apply(style_row,axis=1),
                 use_container_width=True, hide_index=True, height=430)

    ch1, ch2 = st.columns(2)
    with ch1:
        dispo_data = [
            {"Disposition": d,
             "Median LOS": los["by_disposition"].get(d,{}).get("med",0) or 0,
             "90th %ile":  los["by_disposition"].get(d,{}).get("p90",0) or 0}
            for d in ["DC","ADM","TRF","AMA","LEFT"]
            if los["by_disposition"].get(d)
        ]
        if dispo_data:
            fig = px.bar(pd.DataFrame(dispo_data), x="Disposition",
                         y=["Median LOS","90th %ile"], barmode="group",
                         title="LOS by Disposition (min)",
                         color_discrete_sequence=["#0ea5e9","#94a3b8"])
            fig.update_layout(height=300,margin=dict(t=40,b=20,l=0,r=0),
                              legend_title="",plot_bgcolor="white",paper_bgcolor="white")
            st.plotly_chart(fig, use_container_width=True)

    with ch2:
        acu_data = [
            {"Acuity": f"A{a}",
             "Median": los["by_acuity"].get(a,{}).get("med",0) or 0,
             "90th":   los["by_acuity"].get(a,{}).get("p90",0) or 0}
            for a in [1,2,3,4,5] if los["by_acuity"].get(a)
        ]
        if acu_data:
            fig = px.bar(pd.DataFrame(acu_data), x="Acuity",
                         y=["Median","90th"], barmode="group",
                         title="LOS by Acuity (min)",
                         color_discrete_sequence=["#0ea5e9","#94a3b8"])
            fig.update_layout(height=300,margin=dict(t=40,b=20,l=0,r=0),
                              legend_title="",plot_bgcolor="white",paper_bgcolor="white")
            st.plotly_chart(fig, use_container_width=True)

    # Export
    st.markdown("---")
    ex1, ex2 = st.columns(2)
    with ex1:
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as writer:
            table_df.to_excel(writer, sheet_name="LOS Statistics", index=False)
            if flow:
                pd.DataFrame([
                    {"Interval":v["label"],"Median":v["med"],"90th":v["p90"],"N":v["n"]}
                    for v in flow.values() if isinstance(v,dict) and "label" in v
                ]).to_excel(writer, sheet_name="Flow Metrics", index=False)
            pd.DataFrame([h]).to_excel(writer, sheet_name="Headline KPIs", index=False)
        buf.seek(0)
        st.download_button("⬇ Download Excel", data=buf,
            file_name=f"EDflow_{h['date_min']}_{h['date_max']}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    with ex2:
        st.markdown("""<button onclick="window.print()"
            style="background:#0f172a;color:white;border:none;padding:8px 20px;
                   border-radius:6px;cursor:pointer;font-size:14px;font-weight:600;">
            🖨️ Print / Save as PDF</button>""", unsafe_allow_html=True)
        st.caption("Opens browser print dialog → Save as PDF")


# ════════════════════════════════════════════════════════════════════════════════
# TAB 2 — FLOW METRICS
# ════════════════════════════════════════════════════════════════════════════════
with tab2:
    st.markdown("### Process Flow Intervals")
    st.caption("Door-to-X times in minutes")

    if not flow:
        st.info("Flow metrics require triage, bed, physician eval and departure timestamps.")
    else:
        core_flow = {k:v for k,v in flow.items()
                     if isinstance(v,dict) and "label" in v}
        flow_items = list(core_flow.items())

        cols = st.columns(min(len(flow_items),4))
        for i,(key,val) in enumerate(flow_items[:4]):
            cols[i].metric(val["label"], f"{val['med']} min",
                           help=f"90th %ile: {val['p90']} min · N={val['n']:,}")

        # Flow by acuity toggle
        show_by_acuity = st.toggle("Break down door-to-physician by acuity", value=False)

        if show_by_acuity and flow.get("door_to_physician_by_acuity"):
            d2p_acu = flow["door_to_physician_by_acuity"]
            acu_flow_data = [
                {"Acuity": f"Acuity {a}",
                 "Median": d2p_acu[a]["med"],
                 "90th %ile": d2p_acu[a]["p90"],
                 "color": ACU_CLR[a]}
                for a in [1,2,3,4,5] if a in d2p_acu
            ]
            if acu_flow_data:
                fig = go.Figure()
                for row in acu_flow_data:
                    fig.add_trace(go.Bar(
                        name=row["Acuity"], x=[row["Acuity"]],
                        y=[row["Median"]], marker_color=row["color"],
                        text=[row["Median"]], textposition="outside"
                    ))
                fig.update_layout(
                    title="Door to Physician by Acuity (median, min)",
                    height=320, showlegend=False,
                    plot_bgcolor="white", paper_bgcolor="white",
                    margin=dict(t=40,b=20,l=0,r=0)
                )
                st.plotly_chart(fig, use_container_width=True)
        else:
            labels  = [v["label"] for v in core_flow.values()]
            medians = [v["med"]   for v in core_flow.values()]
            p90s    = [v["p90"]   for v in core_flow.values()]
            fig = go.Figure()
            fig.add_trace(go.Bar(name="Median",    x=labels, y=medians,
                                 marker_color="#0ea5e9",text=medians,textposition="outside"))
            fig.add_trace(go.Bar(name="90th %ile", x=labels, y=p90s,
                                 marker_color="#94a3b8",text=p90s,textposition="outside"))
            fig.update_layout(barmode="group",height=380,
                              title="Process Interval Benchmarks (minutes)",
                              plot_bgcolor="white",paper_bgcolor="white",
                              margin=dict(t=50,b=60,l=0,r=0),xaxis_tickangle=-20)
            st.plotly_chart(fig, use_container_width=True)

        # Detailed table
        with st.expander("View detailed interval statistics table"):
            stat_labels = [("avg","Avg"),("min","Min"),("p25","25th"),
                           ("med","Median"),("p75","75th"),("p90","90th"),
                           ("max","Max"),("u2hr","≤2hr%"),("u3hr","≤3hr%")]
            rows = []
            for key,val in core_flow.items():
                row = {"Interval":val["label"],"N":f"{val['n']:,}"}
                for f,l in stat_labels:
                    v = val.get(f)
                    row[l] = f"{v}%" if "%" in l and v is not None else (str(v) if v else "—")
                rows.append(row)
            st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True)


# ════════════════════════════════════════════════════════════════════════════════
# TAB 3 — OCCUPANCY & QUEUES
# ════════════════════════════════════════════════════════════════════════════════
with tab3:
    st.markdown("### ED Occupancy & Queue Analysis")
    st.caption("Based on actual patient timestamps — 30-minute intervals")

    # Compute occupancy only when this tab is active
    with st.spinner("Computing occupancy metrics..."):
        occ  = cached_occupancy(df_hash, df)
    peak = occ["peak"]
    pk1,pk2,pk3,pk4,pk5 = st.columns(5)
    pk1.metric("Peak Census",               peak.get("peak_census","—"))
    pk2.metric("Avg Census",                peak.get("avg_census","—"))
    pk3.metric("Peak Waiting for Physician", peak.get("peak_waiting_physician","—"))
    pk4.metric("Peak Boarding",             peak.get("peak_boarding","—"))
    pk5.metric("Total Boarding Hours",
               f"{int(peak.get('total_boarding_hours',0)):,} hrs")

    st.markdown("---")

    census_df = occ["census"]
    if not census_df.empty:
        # Toggle: stacked area or individual lines
        chart_type = st.radio("Chart type", ["Stacked Area","Lines"],
                              horizontal=True, key="occ_chart")
        available = {k:v for k,v in STAGE_LABELS.items() if k in census_df.columns}

        fig = go.Figure()
        for col,label in available.items():
            if chart_type == "Stacked Area":
                fig.add_trace(go.Scatter(
                    x=census_df["timestamp"],y=census_df[col],
                    name=label,stackgroup="one",mode="none",
                    fillcolor=STAGE_CLR.get(col,"#94a3b8"),
                    hovertemplate=f"{label}: %{{y}}<extra></extra>"
                ))
            else:
                fig.add_trace(go.Scatter(
                    x=census_df["timestamp"],y=census_df[col],
                    name=label,mode="lines",
                    line=dict(color=STAGE_CLR.get(col,"#94a3b8"),width=2),
                    hovertemplate=f"{label}: %{{y}}<extra></extra>"
                ))
        fig.update_layout(
            height=380,plot_bgcolor="white",paper_bgcolor="white",
            margin=dict(t=20,b=40,l=0,r=0),hovermode="x unified",
            legend=dict(orientation="h",yanchor="bottom",y=1.02),
            xaxis=dict(gridcolor="#f1f5f9"),
            yaxis=dict(title="Patients in ED",gridcolor="#f1f5f9"),
        )
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")
    bh1,bh2 = st.columns(2)
    with bh1:
        by_hour = occ["by_hour"]
        if not by_hour.empty:
            available_hr = {k:v for k,v in STAGE_LABELS.items() if k in by_hour.columns}
            fig2 = go.Figure()
            for col,label in available_hr.items():
                fig2.add_trace(go.Bar(x=by_hour["hour"],y=by_hour[col],
                                      name=label,marker_color=STAGE_CLR.get(col,"#94a3b8")))
            fig2.update_layout(barmode="stack",height=320,
                               title="Avg Census by Hour",
                               plot_bgcolor="white",paper_bgcolor="white",
                               margin=dict(t=40,b=40,l=0,r=0),
                               legend=dict(orientation="h",yanchor="bottom",y=1.02,
                                           font=dict(size=10)),
                               xaxis=dict(title="Hour",tickmode="linear",tick0=0,
                                          dtick=2,gridcolor="#f1f5f9"),
                               yaxis=dict(title="Avg Patients",gridcolor="#f1f5f9"))
            st.plotly_chart(fig2, use_container_width=True)

    with bh2:
        arr = occ["arrivals"]
        if not arr.empty:
            fig3 = go.Figure(go.Bar(
                x=arr["hour"],y=arr["avg_arrivals_per_hour"],
                marker_color="#0ea5e9",
                text=arr["avg_arrivals_per_hour"].round(1),
                textposition="outside",
            ))
            fig3.update_layout(height=320,title="Avg Arrivals per Hour",
                               plot_bgcolor="white",paper_bgcolor="white",
                               margin=dict(t=40,b=40,l=0,r=0),
                               xaxis=dict(title="Hour",tickmode="linear",
                                          tick0=0,dtick=2,gridcolor="#f1f5f9"),
                               yaxis=dict(title="Avg Arrivals",gridcolor="#f1f5f9"))
            st.plotly_chart(fig3, use_container_width=True)

    with st.expander("View queue summary table by hour"):
        if not occ["by_hour"].empty:
            bh = occ["by_hour"].copy()
            rmap = {"hour":"Hour","total":"Total","q_waiting_triage":"Wait Triage",
                    "q_waiting_bed":"Wait Bed","q_waiting_physician":"Wait Physician",
                    "in_treatment":"In Treatment","boarding":"Boarding"}
            dcols = [c for c in rmap if c in bh.columns]
            tbl   = bh[dcols].rename(columns=rmap)
            tbl["Hour"] = tbl["Hour"].apply(lambda h: f"{int(h):02d}:00")
            def hi_peak(row):
                if "Total" in row.index and row["Total"]==tbl["Total"].max():
                    return ["background:#fef9c3;font-weight:bold"]*len(row)
                return [""]*len(row)
            st.dataframe(
                tbl.style.apply(hi_peak,axis=1).format(
                    {c:"{:.1f}" for c in tbl.columns if c!="Hour"}),
                use_container_width=True, hide_index=True, height=420)


# ════════════════════════════════════════════════════════════════════════════════
# TAB 4 — VOLUME PATTERNS
# ════════════════════════════════════════════════════════════════════════════════
with tab4:
    st.markdown("### Volume Patterns")

    r1c1,r1c2 = st.columns(2)
    with r1c1:
        if vol.get("by_hour"):
            hdf = pd.DataFrame(vol["by_hour"])
            fig = px.bar(hdf,x="label",y="n",title="Arrivals by Hour of Day",
                         labels={"label":"Hour","n":"Visits"},
                         color="n",color_continuous_scale="Blues")
            fig.update_layout(height=300,margin=dict(t=40,b=40,l=0,r=0),
                              showlegend=False,plot_bgcolor="white",
                              paper_bgcolor="white",coloraxis_showscale=False)
            fig.update_xaxes(tickangle=-45,tickfont_size=10)
            st.plotly_chart(fig, use_container_width=True)

    with r1c2:
        if vol.get("by_dow"):
            ddf = pd.DataFrame(vol["by_dow"])
            fig = px.bar(ddf,x="day",y="n",title="Arrivals by Day of Week",
                         labels={"day":"Day","n":"Visits"},
                         color_discrete_sequence=["#8b5cf6"])
            fig.update_layout(height=300,margin=dict(t=40,b=20,l=0,r=0),
                              plot_bgcolor="white",paper_bgcolor="white")
            st.plotly_chart(fig, use_container_width=True)

    # Heatmap — hour × day of week
    if vol.get("heatmap_hour_dow"):
        st.markdown("#### Arrival Heatmap — Hour × Day of Week")
        st.caption("Average visits per cell across the 3-month period")
        hmap_df = pd.DataFrame(vol["heatmap_hour_dow"])
        dow_order = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
        pivot = hmap_df.pivot_table(
            index="arrival_dow", columns="arrival_hour", values="n",
            aggfunc="mean"
        ).reindex(dow_order)
        fig = px.imshow(
            pivot,
            labels=dict(x="Hour of Day",y="Day of Week",color="Avg Visits"),
            color_continuous_scale="Blues",
            title="Arrival Intensity — Hour × Day of Week",
            aspect="auto"
        )
        fig.update_layout(height=320,margin=dict(t=40,b=20,l=0,r=0))
        st.plotly_chart(fig, use_container_width=True)

    r2c1,r2c2 = st.columns(2)
    with r2c1:
        if vol.get("by_acuity"):
            adf = pd.DataFrame(vol["by_acuity"])
            adf["label"] = adf["level"].apply(lambda x: f"Acuity {x}")
            fig = px.pie(adf,names="label",values="n",title="Acuity Mix",
                         color="label",
                         color_discrete_map={f"Acuity {k}":v for k,v in ACU_CLR.items()})
            fig.update_layout(height=300,margin=dict(t=40,b=20,l=0,r=0))
            fig.update_traces(textinfo="percent+label",textfont_size=11)
            st.plotly_chart(fig, use_container_width=True)

    with r2c2:
        if vol.get("by_disposition"):
            ddf = pd.DataFrame(vol["by_disposition"])
            fig = px.bar(ddf,x="dispo",y="n",title="Disposition Mix",
                         labels={"dispo":"Disposition","n":"Visits"},
                         color="dispo",color_discrete_map=DISPO_CLR)
            fig.update_layout(height=300,margin=dict(t=40,b=20,l=0,r=0),
                              showlegend=False,plot_bgcolor="white",paper_bgcolor="white")
            st.plotly_chart(fig, use_container_width=True)

    if vol.get("by_arrival_mode"):
        mdf = pd.DataFrame(vol["by_arrival_mode"])
        fig = px.bar(mdf,x="n",y="mode",orientation="h",
                     title="Arrivals by Mode",labels={"n":"Visits","mode":""},
                     color_discrete_sequence=["#0ea5e9"])
        fig.update_layout(height=max(200,len(mdf)*40),
                          margin=dict(t=40,b=20,l=0,r=0),
                          plot_bgcolor="white",paper_bgcolor="white")
        st.plotly_chart(fig, use_container_width=True)


# ════════════════════════════════════════════════════════════════════════════════
# TAB 5 — BENCHMARKS
# ════════════════════════════════════════════════════════════════════════════════
with tab5:
    st.markdown("### Performance Benchmarks")
    st.caption("% of patients meeting key time targets")

    if not bm:
        st.info("Benchmark metrics require triage, physician eval and departure timestamps.")
    else:
        # Benchmark cards
        b_items = [
            ("triage_within_15min",    "Triaged within 15 min",   "#0ea5e9", "Target: 95%"),
            ("physician_within_30min", "Physician within 30 min", "#10b981", "Target: 80%"),
            ("physician_within_60min", "Physician within 60 min", "#8b5cf6", "Target: 95%"),
            ("los_within_4hr",         "LOS within 4 hours",      "#f59e0b", "Target: 90%"),
            ("los_within_6hr",         "LOS within 6 hours",      "#22c55e", "Target: 98%"),
            ("boarding_under_60min",   "Boarding < 60 min",       "#ef4444", "Target: 80%"),
        ]
        cols = st.columns(3)
        for i,(key,label,color,target) in enumerate(b_items):
            if key in bm:
                val = bm[key]
                pct = val["pct"]
                # Gauge-style metric with color
                cols[i%3].markdown(f"""
                <div style='background:white;border:1px solid #e5e7eb;border-radius:10px;
                            padding:16px;margin-bottom:12px;text-align:center'>
                    <div style='font-size:11px;color:#9ca3af;font-weight:700;
                                text-transform:uppercase;letter-spacing:0.5px;margin-bottom:6px'>
                        {label}
                    </div>
                    <div style='font-size:32px;font-weight:900;color:{color}'>{pct}%</div>
                    <div style='font-size:11px;color:#d1d5db;margin-top:4px'>{target}</div>
                    <div style='background:#f1f5f9;border-radius:4px;height:6px;
                                margin-top:8px;overflow:hidden'>
                        <div style='background:{color};width:{min(pct,100)}%;
                                    height:100%;border-radius:4px'></div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

        # Physician within 60 min by acuity
        if bm.get("physician_60min_by_acuity"):
            st.markdown("---")
            st.markdown("#### Physician Contact within 60 min — by Acuity")
            acu_bm = bm["physician_60min_by_acuity"]
            bm_data = [
                {"Acuity": f"Acuity {a}",
                 "% Met": acu_bm[a]["pct"],
                 "N met": acu_bm[a]["n"],
                 "color": ACU_CLR[a]}
                for a in [1,2,3,4,5] if a in acu_bm
            ]
            if bm_data:
                fig = go.Figure()
                for row in bm_data:
                    fig.add_trace(go.Bar(
                        name=row["Acuity"],x=[row["Acuity"]],y=[row["% Met"]],
                        marker_color=row["color"],
                        text=[f"{row['% Met']}%"],textposition="outside"
                    ))
                fig.add_hline(y=95,line_dash="dash",line_color="#94a3b8",
                              annotation_text="95% target",annotation_position="right")
                fig.update_layout(
                    height=320,showlegend=False,
                    plot_bgcolor="white",paper_bgcolor="white",
                    margin=dict(t=40,b=20,l=0,r=0),
                    yaxis=dict(title="%",range=[0,110],gridcolor="#f1f5f9"),
                )
                st.plotly_chart(fig, use_container_width=True)


