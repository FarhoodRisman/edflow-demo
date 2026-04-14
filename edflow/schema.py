"""
edflow/schema.py
EDflow canonical schema — v2
All EDIS uploads are standardized to these field names regardless of source system.
"""

# ── Canonical Field Definitions ───────────────────────────────────────────────
#
# Standard Name         : short, clean snake_case used throughout the codebase
# Label                 : human-readable name shown in the UI
# Required              : file is rejected if this field cannot be mapped
# Type                  : how the column is parsed
# Aliases               : every known variation across Epic, Cerner, Meditech, etc.
#
# ─────────────────────────────────────────────────────────────────────────────

FIELDS = {

    # ── REQUIRED ─────────────────────────────────────────────────────────────

    "visit_id": {
        "label": "Visit ID",
        "required": True,
        "type": "string",
        "description": "Unique ED encounter identifier (non-PHI)",
        "aliases": [
            "ed identifier", "visit id", "visit number", "encounter id",
            "encounter number", "account number", "ed id", "csn", "fin",
            "patient visit id", "ed encounter", "encounter", "visit",
            "ed visit id", "pat enc csn id", "accession", "id",
            "edidentifier", "visitid", "encounterid"
        ],
    },

    "arrival_time": {
        "label": "Arrival Time",
        "required": True,
        "type": "datetime",
        "description": "Date/time patient arrived in ED (quick registration)",
        "aliases": [
            "arrival in ed (quick reg) date / time", "arrival in ed date / time",
            "arrv date/time", "arrival date/time", "arrival time", "arrival date",
            "arrival datetime", "arrived", "ed arrival time", "ed arrival date time",
            "quick reg time", "registration time", "reg time", "check in time",
            "date of arrival", "arrivaltime", "arrival", "arrv dt", "arr date time",
            "ed arrival", "quick reg date time", "arrv date time"
        ],
    },

    "arrival_mode": {
        "label": "Mode of Arrival",
        "required": True,
        "type": "category",
        "description": "How the patient arrived (walk-in, EMS, transfer, etc.)",
        "aliases": [
            "mode of arrival", "arrival method", "arrival mode", "transport mode",
            "mode of transport", "how arrived", "arrival transport",
            "ambulance flag", "arrival method", "means of arrival",
            "arrivalmode", "arr mode", "transportation", "transport",
            "means of transport", "arrival by"
        ],
    },

    "acuity": {
        "label": "Acuity Level",
        "required": True,
        "type": "integer",
        "description": "Triage acuity/severity level (CTAS or ESI scale 1–5)",
        "aliases": [
            "triage category or acuity", "triage category", "triage level",
            "acuity", "acuity level", "ctas", "esi", "triage acuity",
            "triage score", "severity", "acuitylevel", "triagecategory",
            "triage", "acuity score", "triage priority", "priority level",
            "triage cat", "triage category or acuity level", "level"
        ],
    },

    "triage_time": {
        "label": "Triage Time",
        "required": True,
        "type": "datetime",
        "description": "Date/time triage assessment was completed",
        "aliases": [
            "triage date / time", "triage date/time", "triage time",
            "triage datetime", "triage date", "triage start",
            "triage completed", "triage assessment time",
            "nurse triage time", "triagetime", "triage start time",
            "triage dttm", "triage dt"
        ],
    },

    "physician_eval_time": {
        "label": "Physician Eval Time",
        "required": True,
        "type": "datetime",
        "description": "Date/time of first physician or provider evaluation",
        "aliases": [
            "phys eval date / time", "phys eval date/time", "phys eval time",
            "physician eval date/time", "physician evaluation time",
            "provider eval time", "md eval time", "first assessment",
            "doctor time", "physician evaluation date/time",
            "physician eval", "md assessment time", "physevaltime",
            "provider assessment time", "dr eval time", "physician contact time",
            "initial physician eval", "first provider contact",
            "physician eval time", "phys eval time", "md eval time",
            "physician_eval_time", "phys_eval_time"
        ],
    },

    "departure_time": {
        "label": "Departure Time",
        "required": True,
        "type": "datetime",
        "description": "Date/time patient left the ED (door-out)",
        "aliases": [
            "leave ed date / time", "leave ed date/time", "leave ed time",
            "departure time", "departure datetime", "ed departure",
            "ed exit time", "discharge time", "ed discharge time",
            "exit time", "patient out time", "left ed time",
            "departuretime", "leave time", "ed leave time",
            "disch date/time", "discharge date time", "disch dttm",
            "ed disch date time", "left ed date time",
            "ed_disposition_dttm", "ed disposition dttm",
            "disposition dttm", "dispo dttm"
        ],
    },

    "disposition_type": {
        "label": "Disposition Type",
        "required": True,
        "type": "category",
        "description": "ED visit outcome category (DC, Admit, Transfer, AMA, LWBS)",
        "aliases": [
            "ed discharge disposition type", "ed disch disposition",
            "disposition type", "disposition", "ed disposition",
            "discharge disposition", "dispo", "discharge type",
            "patient disposition", "dispositiontype", "ed disch dispo",
            "ed discharge disposition", "visit disposition",
            "discharge disposition type"
        ],
    },

    # ── NICE TO HAVE ─────────────────────────────────────────────────────────

    "disposition_location": {
        "label": "Disposition Location",
        "required": False,
        "type": "string",
        "description": "Where patient went after ED (home, IP unit, transfer destination)",
        "aliases": [
            "disposition location (home, ip unit, transfer type)",
            "disposition location", "discharge location", "dispo location",
            "discharge destination", "transfer destination", "admit location",
            "ip unit", "destination", "discharged to", "admitted to",
            "dispositionlocation"
        ],
    },

    "direct_bed_time": {
        "label": "Direct Bed Time",
        "required": False,
        "type": "datetime",
        "description": "Date/time of sorting or direct bedding decision",
        "aliases": [
            "sorting or direct bedding date / time", "direct bedding date/time",
            "direct bed time", "sorting time", "direct bedding",
            "directbedtime", "sort time", "direct bed date time",
            "bedding time", "direct bedding time"
        ],
    },

    "bed_time": {
        "label": "In-Bed Time",
        "required": False,
        "type": "datetime",
        "description": "Date/time patient was placed in an ED bed",
        "aliases": [
            "in bed date / time", "in bed date/time", "in bed time",
            "bed time", "bed placement time", "roomed time", "room time",
            "bedded time", "placed in bed", "bedtime", "bed datetime",
            "room date time", "roomed date time", "inbedtime",
            "bed dttm", "room dttm"
        ],
    },

    "nurse_eval_time": {
        "label": "Nurse Eval Time",
        "required": False,
        "type": "datetime",
        "description": "Date/time of initial nurse evaluation",
        "aliases": [
            "initial nurse eval date / time", "initial nurse eval date/time",
            "nurse eval time", "initial nurse eval", "nurse assessment time",
            "rn eval time", "nurse evaluation time", "nurseevaltime",
            "rn assessment time", "nursing eval time", "rn eval date time"
        ],
    },

    "first_order_time": {
        "label": "First Order Time",
        "required": False,
        "type": "datetime",
        "description": "Date/time physician placed first order",
        "aliases": [
            "phys first order date / time", "phys first order date/time",
            "first order time", "phys first order", "physician first order",
            "initial order time", "firstordertime", "order time",
            "first order date time", "md first order time"
        ],
    },

    "dispo_decision_time": {
        "label": "Dispo Decision Time",
        "required": False,
        "type": "datetime",
        "description": "Date/time physician decided on patient disposition",
        "aliases": [
            "phys decide dispo date / time", "phys decide dispo date/time",
            "dispo decision time", "disposition decision time",
            "decide dispo time", "physician decide dispo",
            "dispodecisiontime", "md dispo decision time",
            "dispo decided time", "disposition decided"
        ],
    },

    "bed_id": {
        "label": "Bed / Room ID",
        "required": False,
        "type": "string",
        "description": "Initial ED bed or room assigned after triage",
        "aliases": [
            "initial ed bed #, after triage", "initial ed bed #",
            "bed number", "bed no", "bed id", "room number", "room no",
            "initial bed", "ed bed", "bedid", "bed#", "room", "bed",
            "ed room", "room id", "roomed", "bed assignment"
        ],
    },

    "chief_complaint": {
        "label": "Chief Complaint",
        "required": False,
        "type": "string",
        "description": "Chief complaint or reason for visit",
        "aliases": [
            "chief complaint or reason for visit", "chief complaint",
            "complaint", "reason for visit", "presenting complaint",
            "cc", "chiefcomplaint", "reason", "presenting problem",
            "visit reason", "primary complaint"
        ],
    },

    "diagnosis": {
        "label": "Discharge Diagnosis",
        "required": False,
        "type": "string",
        "description": "ED discharge diagnosis",
        "aliases": [
            "ed discharge diagnosis", "discharge diagnosis", "diagnosis",
            "primary diagnosis", "dx", "final diagnosis", "ed diagnosis",
            "discharge dx", "icd diagnosis", "principal diagnosis"
        ],
    },

    "age": {
        "label": "Age",
        "required": False,
        "type": "float",
        "description": "Patient age at time of visit",
        "aliases": [
            "age", "patient age", "age at visit", "age years",
            "age (years)", "pt age", "age yr"
        ],
    },

    "physician": {
        "label": "Attending Physician",
        "required": False,
        "type": "string",
        "description": "Primary attending physician",
        "aliases": [
            "primary phys", "physician", "attending", "md", "doctor",
            "attending physician", "primary physician", "primaryphys",
            "attending md", "ed physician", "staff physician"
        ],
    },

    "app": {
        "label": "APP / PA / NP",
        "required": False,
        "type": "string",
        "description": "Advanced practice provider (PA or NP)",
        "aliases": [
            "app / pa / np", "app", "pa", "np", "mid level",
            "advanced practice provider", "nurse practitioner",
            "physician assistant", "midlevel", "pa np"
        ],
    },

    "resident": {
        "label": "Resident / Med Student",
        "required": False,
        "type": "string",
        "description": "Resident or medical student involved in care",
        "aliases": [
            "resident / med student", "resident", "medical student",
            "med student", "resident physician", "trainee",
            "resident med student", "pgy"
        ],
    },
}

# ── Convenience sets ──────────────────────────────────────────────────────────
REQUIRED_FIELDS   = [k for k, v in FIELDS.items() if v["required"]]
OPTIONAL_FIELDS   = [k for k, v in FIELDS.items() if not v["required"]]
DATETIME_FIELDS   = [k for k, v in FIELDS.items() if v["type"] == "datetime"]

# ── Disposition value normalisation → canonical categories ────────────────────
DISPOSITION_MAP = {
    # Discharge / home
    "home": "DC", "discharged": "DC", "discharge": "DC", "dc": "DC",
    "left": "DC", "released": "DC", "to home": "DC", "routine discharge": "DC",
    "d/c": "DC", "discharge home": "DC", "disch": "DC",
    # Admitted
    "admitted": "ADM", "admission": "ADM", "adm": "ADM", "inpatient": "ADM",
    "admit": "ADM", "ip": "ADM", "observation": "ADM", "obs": "ADM",
    "admit inpatient": "ADM", "inpt": "ADM",
    # Transfer
    "transfer": "TRF", "transferred": "TRF", "trf": "TRF",
    "transfer out": "TRF", "transferred out": "TRF", "xfer": "TRF",
    # AMA
    "ama": "AMA", "against medical advice": "AMA", "left ama": "AMA",
    "against advice": "AMA",
    # LWBS / Left without being seen
    "lwbs": "LEFT", "left without being seen": "LEFT",
    "left without seen": "LEFT", "eloped": "LEFT",
    "left without treatment": "LEFT", "left before treatment": "LEFT",
    "left before seen": "LEFT", "did not wait": "LEFT", "dnw": "LEFT",
    "walked out": "LEFT", "left without triage": "LEFT",
    # Deceased
    "expired": "EXP", "deceased": "EXP", "death": "EXP", "dead": "EXP",
    "doi": "EXP",
}

CANONICAL_DISPOSITIONS = ["DC", "ADM", "TRF", "AMA", "LEFT", "EXP", "OTHER"]