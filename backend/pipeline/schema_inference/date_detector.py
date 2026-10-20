import re
from datetime import date, datetime
from typing import Any, Optional, Sequence

from dateutil import parser as date_parser

# Regex to avoid dateutil falsely parsing integers or short numeric IDs as dates
NUMERIC_ID_REGEX = re.compile(r"^\d{1,6}$")
ISO_DATE_REGEX = re.compile(r"^\d{4}-\d{2}-\d{2}(?:[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?)?$")
SLASH_DATE_REGEX = re.compile(r"^\d{1,2}/\d{1,2}/\d{2,4}(?: \d{1,2}:\d{2}(?::\d{2})?)?$")
DASH_DATE_REGEX = re.compile(r"^\d{1,2}-\d{1,2}-\d{2,4}$")


def _is_single_val_date(val: Any) -> bool:
    """Evaluate whether a single non-empty scalar is a parseable date."""
    if isinstance(val, (datetime, date)):
        return True

    text = str(val).strip()
    if not text or NUMERIC_ID_REGEX.match(text):
        return False

    # Must contain some delimiter or timestamp indicator
    if not any(c in text for c in ("-", "/", "T", ":", " ", "Z")):
        return False

    try:
        parsed = date_parser.parse(text)
        # Verify year is within reasonable commercial bounds (1970–2100)
        return 1970 <= parsed.year <= 2100
    except (ValueError, TypeError, OverflowError):
        return False


def is_date_like(sample_values: Any, threshold_ratio: float = 0.75) -> bool:
    """
    Determine if a series of sample column values represent date or timestamp data.
    Accepts a sequence of values or a single string/value.
    Requires at least threshold_ratio of non-null values to parse successfully.
    """
    if sample_values is None:
        return False

    if isinstance(sample_values, (str, bytes)):
        samples = [sample_values]
    elif isinstance(sample_values, Sequence):
        samples = list(sample_values)
    else:
        samples = [sample_values]

    valid_samples = [v for v in samples if v is not None and str(v).strip() != ""]
    if not valid_samples:
        return False

    date_matches = sum(1 for v in valid_samples if _is_single_val_date(v))
    return (date_matches / len(valid_samples)) >= threshold_ratio


def detect_date_format(sample_values: Any) -> Optional[str]:
    """Identify the prevalent date/time format pattern across sample values."""
    if sample_values is None:
        return None

    if isinstance(sample_values, (str, bytes)):
        samples = [sample_values]
    elif isinstance(sample_values, Sequence):
        samples = list(sample_values)
    else:
        samples = [sample_values]

    valid_samples = [str(v).strip() for v in samples if v is not None and str(v).strip() != ""]
    if not valid_samples:
        return None

    # Check for specific strftime format patterns
    iso_datetime_count = sum(1 for v in valid_samples if re.match(r"^\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}", v))
    iso_date_count = sum(1 for v in valid_samples if re.match(r"^\d{4}-\d{2}-\d{2}$", v))
    slash_count = sum(1 for v in valid_samples if re.match(r"^\d{1,2}/\d{1,2}/\d{4}", v))
    dash_count = sum(1 for v in valid_samples if re.match(r"^\d{1,2}-\d{1,2}-\d{4}$", v))

    total = len(valid_samples)
    if iso_datetime_count / total >= 0.5:
        return "%Y-%m-%d %H:%M:%S"
    if iso_date_count / total >= 0.5:
        return "%Y-%m-%d"
    if slash_count / total >= 0.5:
        return "%m/%d/%Y"
    if dash_count / total >= 0.5:
        return "%d-%m-%Y"

    return "General-DateTime" if is_date_like(samples) else None


def standardize_date(val: Any) -> Optional[str]:
    """Parse single value and return canonical ISO-8601 string or None."""
    if val is None or str(val).strip() == "":
        return None

    if isinstance(val, datetime):
        return val.isoformat()
    if isinstance(val, date):
        return datetime(val.year, val.month, val.day).isoformat()

    text = str(val).strip()
    if NUMERIC_ID_REGEX.match(text):
        return None

    try:
        parsed = date_parser.parse(text)
        return parsed.isoformat()
    except Exception:
        return None
