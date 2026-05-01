# 🏥 EDflow — Emergency Department Intelligence Platform

> **Operational analytics for emergency departments — powered by real EDIS data.**

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://edflow-demo.streamlit.app)

---

## What is EDflow?

EDflow automates the descriptive analytics and operational benchmarking that typically takes consultants days to produce manually using Excel and simulation tools. Upload 3 months of EDIS records and get an instant, interactive dashboard covering all key ED performance metrics.

EDflow is built by an operations consultant with 15+ years of experience redesigning emergency departments using discrete-event simulation and data analytics.

---

## Live Demo

🔗 **[Launch EDflow Demo](https://edflow-demo.streamlit.app)**

The demo includes three data options:
- 🧪 **Synthetic data** — statistically modelled ED dataset (4,500 visits, 91 days)
- 🏥 **MIMIC-IV-ED** — real de-identified research data from Beth Israel Deaconess Medical Center, Boston (MIT / PhysioNet)
- 📁 **Your own data** — upload a CSV or Excel export from Epic, Cerner, Meditech, or any EDIS

---

## Features

### Free Tier — Descriptive Analytics
| Feature | Status |
|---|---|
| Intelligent column mapping (fuzzy match, 20+ EDIS formats) | ✅ Live |
| Automated data standardization and quality check | ✅ Live |
| LOS statistics — by disposition, acuity, location, psych | ✅ Live |
| Cross-segment analysis (Acute×Dispo, Psych×Dispo) | ✅ Live |
| Process flow intervals (door-to-triage, door-to-physician, etc.) | ✅ Live |
| ED occupancy and queue analysis over time | ✅ Live |
| Volume patterns — hourly, daily, heatmap (hour × day) | ✅ Live |
| Performance benchmarks against targets | ✅ Live |
| Interactive filters (acuity, disposition, shift, psych, date) | ✅ Live |
| Export to Excel and PDF | ✅ Live |
| MIMIC-IV-ED integration (real research data) | ✅ Live |

### Premium Tier — Simulation-Based Optimization
| Feature | Status |
|---|---|
| Discrete-event simulation engine | 🔒 Premium |
| Acute / urgent partitioning recommendations | 🔒 Premium |
| Track and bed redesign | 🔒 Premium |
| Staff schedule optimization | 🔒 Premium |
| What-if scenario comparison | 🔒 Premium |
| Projected LOS and LWBS improvement estimates | 🔒 Premium |

---

## Data Privacy

EDflow is designed for **de-identified operational data only** — no patient names, MRNs, or dates of birth. This type of EDIS export is outside HIPAA's individually identifiable information scope.

Uploaded files are processed **in-session only** — data is never stored, transmitted, or retained after the browser tab is closed.

On-premise deployment is available for organizations that require data to remain within their own network.

---

## Compatible EDIS Systems

- Epic (Reporting Workbench exports)
- Cerner
- Meditech
- Any CSV/Excel EDIS export

Column names are mapped automatically regardless of naming convention.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend / App | Streamlit |
| Data processing | Python, pandas, numpy |
| Fuzzy column mapping | RapidFuzz |
| Charts | Plotly |
| Research data | MIMIC-IV-ED (PhysioNet) |
| Hosting | Streamlit Cloud |

---

## Project Structure

```
edflow/
├── schema.py          # Canonical field definitions + aliases
├── mapper.py          # Intelligent fuzzy column name mapping
├── ingest.py          # Load → clean → standardize → derive
├── kpis.py            # KPI computation engine
├── occupancy.py       # Census, queue, and flow analysis
├── synthetic.py       # Realistic synthetic ED data generator
└── mimic_loader.py    # MIMIC-IV-ED data loader

pages/
├── 1_Dashboard.py     # Interactive analytics dashboard
└── 2_Upload.py        # Data upload and column mapping UI

Home.py                # Entry point
requirements.txt       # Python dependencies
```

---

## Roadmap

See [ROADMAP.md](ROADMAP.md) for the full planned feature list and milestone tracker.

---

## About

EDflow is a product of **Opsient** — operational intelligence tools for healthcare and supply chain.

- 🌐 Website: [opsient.com](https://opsient.com) *(coming soon)*
- 📧 Contact: [PLACEHOLDER@email.com]
- 🔗 LinkedIn: [PLACEHOLDER]

---

## Data Attribution

MIMIC-IV-ED demo data:
> Johnson, A., Bulgarelli, L., Pollard, T., Horng, S., Celi, L. A., & Mark, R. (2023).
> MIMIC-IV-ED (version 2.2). PhysioNet. https://doi.org/10.13026/5ntk-km72

Licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
