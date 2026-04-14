"""
edflow/mapper.py
Fuzzy-matches raw CSV column names to the EDflow canonical schema.
Uses RapidFuzz for scoring. Returns a mapping dict + confidence report.
"""

from rapidfuzz import fuzz, process
from edflow.schema import FIELDS

# Minimum similarity score (0–100) to auto-accept a match
AUTO_ACCEPT_THRESHOLD = 72
# Below this score, the column is flagged for manual review
REVIEW_THRESHOLD = 50


def _normalize(text: str) -> str:
    """Lowercase, strip, collapse spaces, remove punctuation noise."""
    import re
    text = text.lower().strip()
    text = re.sub(r"[_\-/\\]+", " ", text)   # underscores, dashes, slashes → space
    text = re.sub(r"\s+", " ", text)           # collapse whitespace
    text = re.sub(r"[#*]", "", text)           # remove # and *
    return text.strip()


def build_alias_index() -> dict[str, str]:
    """
    Build a flat lookup: normalized_alias → canonical_field_name
    Used for exact-match lookups before fuzzy scoring.
    """
    index = {}
    for field, meta in FIELDS.items():
        for alias in meta["aliases"]:
            index[_normalize(alias)] = field
    return index


ALIAS_INDEX = build_alias_index()


def map_columns(raw_columns: list[str]) -> dict:
    """
    Given a list of raw column names from an uploaded CSV,
    returns a structured result:

    {
      "mapping": {
          "raw_col_name": "canonical_field_name",   # confirmed matches
          ...
      },
      "review": [
          {"raw": "raw_col_name", "suggested": "canonical_field", "score": 67},
          ...
      ],
      "unmapped": ["col_that_matched_nothing", ...],
      "missing_required": ["visit_id", ...],   # required fields not found at all
    }
    """
    mapping = {}          # raw → canonical  (high-confidence)
    review = []           # needs human confirmation
    unmapped = []         # no reasonable match
    used_fields = set()   # prevent double-mapping

    # All canonical aliases as a flat list for fuzzy search
    all_aliases = list(ALIAS_INDEX.keys())

    for raw in raw_columns:
        norm = _normalize(raw)

        # 1. Exact match in alias index
        if norm in ALIAS_INDEX:
            field = ALIAS_INDEX[norm]
            if field not in used_fields:
                mapping[raw] = field
                used_fields.add(field)
                continue

        # 2. Fuzzy match against all known aliases
        result = process.extractOne(
            norm,
            all_aliases,
            scorer=fuzz.token_sort_ratio
        )

        if result is None:
            unmapped.append(raw)
            continue

        matched_alias, score, _ = result
        canonical = ALIAS_INDEX[matched_alias]

        if canonical in used_fields:
            # Field already claimed — try next best
            results = process.extract(norm, all_aliases, scorer=fuzz.token_sort_ratio, limit=10)
            for alias, sc, _ in results:
                alt = ALIAS_INDEX[alias]
                if alt not in used_fields:
                    score = sc
                    canonical = alt
                    break
            else:
                unmapped.append(raw)
                continue

        if score >= AUTO_ACCEPT_THRESHOLD:
            mapping[raw] = canonical
            used_fields.add(canonical)
        elif score >= REVIEW_THRESHOLD:
            review.append({"raw": raw, "suggested": canonical, "score": round(score, 1)})
        else:
            unmapped.append(raw)

    # Which required fields are still unaccounted for?
    from edflow.schema import REQUIRED_FIELDS
    mapped_canonicals = set(mapping.values()) | {r["suggested"] for r in review}
    missing_required = [f for f in REQUIRED_FIELDS if f not in mapped_canonicals]

    return {
        "mapping": mapping,
        "review": review,
        "unmapped": unmapped,
        "missing_required": missing_required,
    }


def apply_mapping(df, mapping: dict):
    """
    Rename DataFrame columns from raw names to canonical names.
    Drops any column not in the mapping.
    Deduplicates if two raw columns mapped to the same canonical name.
    """
    import pandas as pd
    df = df.rename(columns=mapping)
    # Keep only canonical columns (drop unmapped raw cols)
    canonical_cols = [c for c in df.columns if c in FIELDS]
    df = df[canonical_cols]
    # Remove duplicate canonical columns — keep first occurrence
    df = df.loc[:, ~df.columns.duplicated(keep="first")]
    return df