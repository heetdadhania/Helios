import re
from typing import Any, List, Optional, Sequence

import pandas as pd

from pipeline.schema_inference.date_detector import is_date_like

CURRENCY_REGEX = re.compile(
    r"^\s*(?:[$€£¥₹]|Rs\.?|INR)?\s*-?\d{1,3}(?:(?:,\d{2,3})*|\d*)(?:\.\d{1,4})?\s*(?:/-\s*|[$€£¥₹]|Rs\.?|INR)?\s*$",
    re.IGNORECASE,
)
INTEGER_REGEX = re.compile(r"^-?\d+$")
FLOAT_REGEX = re.compile(r"^-?\d*\.\d+$")
BOOLEAN_SET = {"true", "false", "yes", "no", "t", "f", "1", "0"}


def _has_currency_indicators(values: List[str]) -> bool:
    """Check if values contain monetary currency symbols or standard financial formats."""
    has_inr_indicators = any(
        "₹" in v or "rs" in v.lower() or "inr" in v.upper() or v.strip().endswith("/-")
        for v in values
    )
    has_symbols = any(any(c in v for c in ("$", "€", "£", "¥", "₹")) for v in values)
    all_match_currency = all(CURRENCY_REGEX.match(v) for v in values)
    return has_inr_indicators or has_symbols or (all_match_currency and any("." in v for v in values))


def _is_boolean_column(values: List[str]) -> bool:
    """Check if column values are boolean-compatible."""
    if not values:
        return False
    lowered = [v.lower() for v in values]
    return all(v in BOOLEAN_SET for v in lowered) and len(set(lowered)) > 0


def _is_numeric_column(values: List[str]) -> Optional[str]:
    """Check if column values represent pure integers or decimal floats."""
    clean_vals = [v.replace(",", "") for v in values]
    if all(INTEGER_REGEX.match(v) for v in clean_vals):
        return "integer"
    if all(FLOAT_REGEX.match(v) or INTEGER_REGEX.match(v) for v in clean_vals) and any("." in v for v in clean_vals):
        return "float"
    return None


def infer_column_type(sample_values: Sequence[Any]) -> str:
    """
    Infer column data type using pandas inference, date parsing, and regex rules.
    
    Returns standard SQL/Delta type: 'decimal', 'integer', 'float', 'timestamp', 'boolean', 'string'.
    """
    valid_raw = [v for v in sample_values if v is not None and str(v).strip() != ""]
    if not valid_raw:
        return "string"

    # 1. Native Python/pandas boolean check
    if all(isinstance(v, bool) for v in valid_raw):
        return "boolean"

    str_values = [str(v).strip() for v in valid_raw]

    # 2. String boolean representation check
    if _is_boolean_column(str_values):
        return "boolean"

    # 3. Currency symbol and financial decimal check
    if _has_currency_indicators(str_values):
        return "decimal"

    # 4. Pure integer or float check
    numeric_type = _is_numeric_column(str_values)
    if numeric_type:
        return numeric_type

    # 5. Date / Timestamp check via dateutil
    if is_date_like(valid_raw):
        return "timestamp"

    # 6. Pandas Series type fallback
    try:
        series = pd.Series(valid_raw)
        converted = pd.to_numeric(series, errors="coerce")
        if converted.notnull().all():
            return "float" if (converted % 1 != 0).any() else "integer"
    except Exception:
        pass

    return "string"
