# EDflow — Roadmap & Milestone Tracker

## ✅ Phase 1 — Descriptive Analytics (Complete)

### Data Pipeline
- [x] Canonical schema definition (20+ EDIS field types)
- [x] Intelligent fuzzy column name mapping (RapidFuzz)
- [x] Multi-format support (CSV, Excel, Epic, Cerner, Meditech)
- [x] Automated value standardization (datetimes, acuity, disposition, arrival mode)
- [x] Data quality check with rejection reasons and warnings
- [x] Auto-generated visit ID for files with blank first column
- [x] MIMIC-IV-ED integration (real research data, 400k+ visits)
- [x] Realistic synthetic data generator (4,500 visits, all KPIs populated)

### KPI Engine
- [x] LOS statistics — overall, by disposition, by acuity, by location, by psych
- [x] Cross-segment analysis — Acute×Dispo, Psych×Dispo, Non-Psych×Dispo
- [x] Process flow intervals — door-to-triage, door-to-bed, door-to-physician, eval-to-decision, decision-to-departure
- [x] Occupancy and census over time (30-minute intervals)
- [x] Queue analysis — waiting triage, waiting bed, waiting physician, in treatment, boarding
- [x] Volume patterns — hourly, daily, day-of-week, monthly, heatmap
- [x] Performance benchmarks — triage <15min, physician <30/60min, LOS <4/6hr, boarding <60min
- [x] Headline KPIs — median LOS, LWBS%, admission rate, door-to-physician
- [x] Cached computation for fast filter response

### Dashboard
- [x] Multi-page Streamlit app
- [x] Interactive sidebar filters — date, acuity, disposition, arrival mode, psych, shift
- [x] LOS Statistics tab with segment selector (Core / Extended / All)
- [x] Flow Metrics tab with acuity breakdown toggle
- [x] Occupancy & Queues tab — stacked area chart, hourly census, queue summary table
- [x] Volume Patterns tab — hourly bar, day-of-week, heatmap, acuity pie, disposition mix
- [x] Benchmarks tab — gauge cards with targets, physician contact by acuity
- [x] Excel export (multi-sheet) and PDF print
- [x] Active filter badges
- [x] Demo / MIMIC / own-file data source tracking

### Website & Deployment
- [x] Opsient landing page (EDflow + RouteIQ products)
- [x] Contact form
- [x] Privacy notice (de-identified data, session-only processing)
- [x] Deployed to Streamlit Cloud
- [x] Investor demo deployment (edflow-demo.streamlit.app)

---

## 🔄 Phase 2 — Enhanced Descriptive (In Progress)

### KPIs to add
- [ ] Monthly trend analysis — LOS and volume over time (are things improving?)
- [ ] Physician performance breakdown — LOS and door-to-physician by attending
- [ ] Chief complaint analysis — top 10 by volume and median LOS
- [ ] Shift comparison — day vs evening vs night side by side
- [ ] Re-attendance rate (if visit IDs linkable across visits)
- [ ] Bed utilization by zone
- [ ] Patient flow Sankey diagram (acuity → disposition)
- [ ] Arrive-to-triage as standalone column in LOS table

### Platform
- [ ] User authentication (Supabase)
- [ ] Data persistence — saved KPIs per client account
- [ ] Admin panel — view all client accounts
- [ ] Row-level security — clients see only their own data
- [ ] Custom domain (opsient.com)

---

## 🔒 Phase 3 — Simulation-Based Optimization (Premium)

- [ ] Discrete-event simulation engine (SimPy)
- [ ] Base model calibration from uploaded data
- [ ] Acute / urgent partitioning — volume split and routing logic
- [ ] Track and bed redesign — zone sizing recommendations
- [ ] Staff schedule optimization — match provider hours to arrival curves
- [ ] What-if scenario comparison (10+ scenarios side by side)
- [ ] Projected LOS and LWBS improvement estimates with confidence intervals
- [ ] Redesign report export (PDF)

---

## 🚀 Phase 4 — Scale & Expansion

- [ ] Stripe billing integration
- [ ] Self-serve signup and onboarding
- [ ] SurgFlow — Surgical Services / OR analytics
- [ ] ClinicFlow — Outpatient Clinic analytics
- [ ] RouteIQ — Supply chain pickup and delivery (parallel track)
- [ ] Snowflake / enterprise deployment option
- [ ] HIPAA BAA documentation
- [ ] SOC 2 readiness
