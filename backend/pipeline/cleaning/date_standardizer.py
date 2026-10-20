import logging
import re
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from dateutil import parser as date_parser

logger = logging.getLogger("helios.pipeline.cleaning.date")

NUMERIC_ONLY_REGEX = re.compile(r"^\d{1,8}$")


def standardize_timestamp(value: Any) -> Optional[str]:
    """
    Standardize a date/time representation into canonical ISO-8601 string (UTC).
    Guards against numeric IDs, out-of-range years, and unparseable text.
    
    Returns:
        ISO formatted string (e.g. '2024-03-15T14:30:00Z' or '2024-03-15 14:30:00'),
        or None if input is empty or invalid.
    """
    if value is None:
        return None

    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.strftime("%Y-%m-%d %H:%M:%S")
        return value.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    if isinstance(value, date):
        return f"{value.strftime('%Y-%m-%d')} 00:00:00"

    text = str(value).strip()
    if not text or text.lower() in ("null", "none", "nan", "n/a", ""):
        return None

    # Guard against pure numbers being misparsed as dates
    if NUMERIC_ONLY_REGEX.match(text):
        return None

    try:
        parsed = date_parser.parse(text)
        # Verify plausible year range
        if parsed.year < 1970 or parsed.year > 2100:
            logger.warning("Parsed date out of commercial bounds (1970-2100): %s", parsed.year)
            return None

        if parsed.tzinfo is not None:
            parsed = parsed.astimezone(timezone.utc)

        return parsed.strftime("%Y-%m-%d %H:%M:%S")
    except (ValueError, TypeError, OverflowError) as exc:
        logger.warning("Failed to parse date string '%s': %s", value, exc)
        return None


def standardize_date_fields(
    record: Dict[str, Any],
    date_fields: List[str],
) -> Tuple[Dict[str, Any], List[str]]:
    """
    Standardize all specified date fields in a single dictionary record.
    
    Returns:
        Tuple of (updated_record, list_of_error_field_names).
    """
    updated = dict(record)
    errors: List[str] = []

    for field in date_fields:
        if field in updated and updated[field] is not None and str(updated[field]).strip() != "":
            raw_val = updated[field]
            standardized = standardize_timestamp(raw_val)
            if standardized is None:
                errors.append(field)
            else:
                updated[field] = standardized

    return updated, errors
