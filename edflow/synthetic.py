"""
edflow/synthetic.py
Generates a rich, realistic synthetic EDIS dataset for demo purposes.
Designed to populate all EDflow KPIs meaningfully.

Design principles:
- Realistic hourly/daily arrival patterns with peaks and troughs
- Acuity-appropriate LOS, disposition, and process times
- Psych patients with distinctly longer stays
- Boarding behaviour for admits and transfers
- Sufficient volume across all cross-segments (acuity × disposition × psych)
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta


def generate_sample_data(
    n_visits: int = 4500,
    start_date: str = "2024-01-01",
    seed: int = 42
) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    start = datetime.strptime(start_date, "%Y-%m-%d")

    # ── Arrival pattern ───────────────────────────────────────────────────────
    # Realistic ED arrival curve:
    # - overnight trough 01:00-06:00
    # - morning ramp 07:00-10:00
    # - afternoon peak 11:00-19:00
    # - evening decline 20:00-23:00
    hour_weights = np.array([
        0.55, 0.40, 0.32, 0.28, 0.28, 0.32,   # 00-05
        0.55, 0.90, 1.30, 1.60, 1.80, 1.95,   # 06-11
        2.05, 2.10, 2.10, 2.05, 1.95, 1.85,   # 12-17
        1.70, 1.50, 1.30, 1.10, 0.88, 0.68,   # 18-23
    ])
    hour_weights /= hour_weights.sum()

    # Day-of-week multiplier — busier Mon/Tue, quieter Sun
    dow_weights = np.array([0.88, 1.08, 1.10, 1.05, 1.02, 0.98, 0.89])

    # Generate arrival times over 91 days
    arrival_offsets = []
    for day in range(91):
        dow = day % 7
        # Each day gets a share of total visits proportional to dow weight
        day_volume = int(round(n_visits / 91 * dow_weights[dow] / dow_weights.mean()))
        for _ in range(max(1, day_volume)):
            hour   = rng.choice(24, p=hour_weights)
            minute = rng.integers(0, 60)
            second = rng.integers(0, 60)
            arrival_offsets.append(day * 86400 + hour * 3600 + minute * 60 + second)

    arrival_offsets = sorted(arrival_offsets)[:n_visits]
    arrivals = [start + timedelta(seconds=int(s)) for s in arrival_offsets]
    n = len(arrivals)

    # ── Acuity — realistic ED distribution ───────────────────────────────────
    # CTAS/ESI: ~3% level1, 17% level2, 50% level3, 22% level4, 8% level5
    acuity = rng.choice([1,2,3,4,5], size=n, p=[0.03, 0.17, 0.50, 0.22, 0.08])

    # ── Psych flag — 7% overall, higher in acuity 2-3 ────────────────────────
    psych_prob = np.where(acuity==1, 0.05,
                 np.where(acuity==2, 0.12,
                 np.where(acuity==3, 0.08,
                 np.where(acuity==4, 0.04, 0.02))))
    is_psych = rng.random(n) < psych_prob

    # ── Acute zone flag — acuity 1,2, all psych, some acuity 3 ───────────────
    is_acute = (acuity <= 2) | is_psych | ((acuity == 3) & (rng.random(n) < 0.35))

    # ── Disposition — acuity + psych + acute dependent ────────────────────────
    # [DC, ADM, TRF, AMA, LEFT]
    dispo_probs = {
        (1, False): [0.05, 0.78, 0.10, 0.04, 0.03],
        (1, True):  [0.03, 0.72, 0.12, 0.07, 0.06],
        (2, False): [0.18, 0.62, 0.09, 0.06, 0.05],
        (2, True):  [0.10, 0.55, 0.12, 0.12, 0.11],
        (3, False): [0.60, 0.20, 0.05, 0.08, 0.07],
        (3, True):  [0.35, 0.32, 0.08, 0.13, 0.12],
        (4, False): [0.74, 0.06, 0.02, 0.09, 0.09],
        (4, True):  [0.55, 0.15, 0.05, 0.13, 0.12],
        (5, False): [0.82, 0.02, 0.01, 0.08, 0.07],
        (5, True):  [0.70, 0.08, 0.03, 0.10, 0.09],
    }
    dispo_cats = ["DC", "ADM", "TRF", "AMA", "LEFT"]
    dispositions = np.array([
        rng.choice(dispo_cats,
                   p=dispo_probs.get((int(acuity[i]), bool(is_psych[i])),
                                     dispo_probs[(3, False)]))
        for i in range(n)
    ])

    # ── Process times (log-normal, minutes) ───────────────────────────────────
    def lognorm(mu, sigma, size):
        return np.clip(
            np.exp(rng.normal(np.log(mu), sigma, size)),
            1, mu * 6
        ).astype(int)

    # Door to triage — faster for high acuity
    triage_mu = np.where(acuity==1, 2,
                np.where(acuity==2, 6,
                np.where(acuity==3, 12,
                np.where(acuity==4, 16, 20))))
    door_to_triage = np.array([lognorm(triage_mu[i], 0.55, 1)[0] for i in range(n)])

    # Triage to bed
    bed_mu = np.where(acuity==1, 5,
             np.where(acuity==2, 18,
             np.where(acuity==3, 38,
             np.where(acuity==4, 45, 30))))
    triage_to_bed = np.array([lognorm(bed_mu[i], 0.75, 1)[0] for i in range(n)])

    # Bed to nurse eval
    bed_to_nurse = lognorm(9, 0.5, n)

    # Nurse to physician
    nurse_to_physician = np.where(acuity<=2, lognorm(12, 0.5, n),
                                             lognorm(22, 0.65, n))

    # ── LOS — depends on acuity, disposition, psych ───────────────────────────
    base_los = {
        "DC":   {1:150, 2:180, 3:190, 4:155, 5:110},
        "ADM":  {1:480, 2:450, 3:420, 4:380, 5:340},
        "TRF":  {1:380, 2:360, 3:340, 4:300, 5:280},
        "AMA":  {1:90,  2:100, 3:95,  4:85,  5:70},
        "LEFT": {1:45,  2:55,  3:60,  4:55,  5:45},
    }
    los_values = []
    for i in range(n):
        mu = base_los[dispositions[i]][int(acuity[i])]
        if is_psych[i]:
            mu = int(mu * 1.9)
        los = int(np.exp(rng.normal(np.log(mu), 0.42)))
        los_values.append(max(10, los))
    los_values = np.array(los_values)

    # ── Build timestamps ──────────────────────────────────────────────────────
    triage_times     = [arrivals[i] + timedelta(minutes=int(door_to_triage[i]))
                        for i in range(n)]
    bed_times        = [triage_times[i] + timedelta(minutes=int(triage_to_bed[i]))
                        for i in range(n)]
    nurse_times      = [bed_times[i] + timedelta(minutes=int(bed_to_nurse[i]))
                        for i in range(n)]
    physician_times  = [nurse_times[i] + timedelta(minutes=int(nurse_to_physician[i]))
                        for i in range(n)]
    first_order      = [physician_times[i] + timedelta(minutes=int(rng.integers(4,20)))
                        for i in range(n)]
    dispo_decision   = [arrivals[i] + timedelta(minutes=int(los_values[i] * 0.78))
                        for i in range(n)]
    departure_times  = [arrivals[i] + timedelta(minutes=int(los_values[i]))
                        for i in range(n)]

    # ── Arrival mode — acuity weighted ───────────────────────────────────────
    mode_probs = {
        1: [0.10, 0.65, 0.15, 0.06, 0.04],
        2: [0.30, 0.48, 0.12, 0.06, 0.04],
        3: [0.65, 0.22, 0.07, 0.04, 0.02],
        4: [0.78, 0.12, 0.05, 0.04, 0.01],
        5: [0.88, 0.06, 0.03, 0.02, 0.01],
    }
    modes_list = ["Walk-in","EMS","Transfer","Police","Air"]
    modes = np.array([
        rng.choice(modes_list, p=mode_probs[int(acuity[i])])
        for i in range(n)
    ])

    # ── Chief complaints ──────────────────────────────────────────────────────
    complaints = {
        1: ["Cardiac arrest","Respiratory failure","Major trauma",
            "Stroke","Septic shock","Anaphylaxis"],
        2: ["Chest pain","Shortness of breath","Altered consciousness",
            "Severe abdominal pain","High fever","Syncope"],
        3: ["Abdominal pain","Headache","Back pain","Vomiting",
            "Dizziness","Chest pain","Fever","Weakness","Palpitations"],
        4: ["Sore throat","Ear pain","Minor laceration","Sprain",
            "Rash","UTI symptoms","Mild pain","Cough"],
        5: ["Prescription refill","Minor rash","Cold symptoms",
            "Follow-up concern","Mild headache","Insect bite"],
    }
    psych_complaints = [
        "Suicidal ideation","Psychiatric assessment","Severe anxiety",
        "Depression","Overdose","Behavioral emergency",
        "Psychiatric emergency","Substance intoxication","Self-harm"
    ]
    chief_complaints = np.array([
        rng.choice(psych_complaints) if is_psych[i]
        else rng.choice(complaints[int(acuity[i])])
        for i in range(n)
    ])

    # ── Bed IDs — zone-appropriate ────────────────────────────────────────────
    acute_beds   = [f"A{i}" for i in range(1,16)]   # Acute zone
    urgent_beds  = [f"U{i}" for i in range(1,13)]   # Urgent zone
    resus_beds   = [f"R{i}" for i in range(1,5)]    # Resus
    psych_beds   = [f"P{i}" for i in range(1,7)]    # Psych
    chair_beds   = [f"CH{i}" for i in range(1,8)]   # Vertical/chairs

    def assign_bed(i):
        if is_psych[i]:
            return rng.choice(psych_beds)
        if acuity[i] == 1:
            return rng.choice(resus_beds)
        if is_acute[i]:
            return rng.choice(acute_beds)
        if acuity[i] == 5 and rng.random() < 0.4:
            return rng.choice(chair_beds)
        return rng.choice(urgent_beds)

    bed_ids = np.array([assign_bed(i) for i in range(n)])

    # ── Ages — acuity weighted ────────────────────────────────────────────────
    age_mu = np.where(acuity==1, 62,
             np.where(acuity==2, 58,
             np.where(acuity==3, 45,
             np.where(acuity==4, 35, 28))))
    ages = np.clip(
        np.array([int(rng.normal(age_mu[i], 20)) for i in range(n)]),
        1, 99
    )

    # ── Visit IDs ─────────────────────────────────────────────────────────────
    visit_ids = [f"V{str(100000+i)}" for i in range(n)]

    # ── Assemble DataFrame ────────────────────────────────────────────────────
    df = pd.DataFrame({
        "visit_id":            visit_ids,
        "arrival_time":        arrivals,
        "arrival_mode":        modes,
        "acuity":              acuity.astype(int),
        "triage_time":         triage_times,
        "bed_time":            bed_times,
        "nurse_eval_time":     nurse_times,
        "physician_eval_time": physician_times,
        "first_order_time":    first_order,
        "dispo_decision_time": dispo_decision,
        "departure_time":      departure_times,
        "disposition_type":    dispositions,
        "chief_complaint":     chief_complaints,
        "age":                 ages,
        "bed_id":              bed_ids,
        "is_psych":            is_psych,
        "is_acute":            is_acute,
    })

    # ── Derived columns ───────────────────────────────────────────────────────
    def mins(t2, t1):
        diff = (df[t2] - df[t1]).dt.total_seconds() / 60
        return diff.where(diff >= 0)

    df["los"]                    = mins("departure_time",       "arrival_time")
    df["door_to_triage"]         = mins("triage_time",          "arrival_time")
    df["door_to_bed"]            = mins("bed_time",             "arrival_time")
    df["door_to_physician"]      = mins("physician_eval_time",  "arrival_time")
    df["door_to_first_order"]    = mins("first_order_time",     "arrival_time")
    df["eval_to_decision"]       = mins("dispo_decision_time",  "physician_eval_time")
    df["decision_to_departure"]  = mins("departure_time",       "dispo_decision_time")
    df["triage_to_bed"]          = mins("bed_time",             "triage_time")
    df["bed_to_physician"]       = mins("physician_eval_time",  "bed_time")

    df["is_horiz"]       = ~df["bed_id"].str.startswith("CH")
    df["arrival_hour"]   = df["arrival_time"].dt.hour
    df["arrival_dow"]    = df["arrival_time"].dt.day_name()
    df["arrival_month"]  = df["arrival_time"].dt.to_period("M").astype(str)

    return df