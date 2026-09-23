import logging
import re
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("helios.pipeline.cleaning.currency")

CURRENCY_SYMBOLS_REGEX = re.compile(r"[$€£¥₹\s,']")
PARENTHESES_NEGATIVE_REGEX = re.compile(r"^\((.+)\)$")


def clean_currency(value: Any) -> Optional[float]:
    """
    Clean and convert a monetary/currency string or number into a standard float.
    Handles currency symbols ($ € £ ¥ ₹), commas, whitespace, and accounting negatives like (12.50).
    
    Returns:
        float rounded to 4 decimal places, or None if value is empty or unparseable.
    """
    if value is None:
        return None

    if isinstance(value, (int, float)):
        return round(float(value), 4)

    text = str(value).strip()
    if not text or text.lower() in ("null", "none", "nan", "n/a", ""):
        return None

    # Check for accounting negative notation: (12.50) -> -12.50
    is_negative = False
    paren_match = PARENTHESES_NEGATIVE_REGEX.match(text)
    if paren_match:
        is_negative = True
        text = paren_match.group(1).strip()
    elif text.startswith("-"):
        is_negative = True
        text = text[1:].strip()

    # Strip currency symbols, commas, quotes, and whitespace
    sanitized = CURRENCY_SYMBOLS_REGEX.sub("", text)
    if not sanitized:
        return None

    try:
        parsed_val = float(sanitized)
        if is_negative:
            parsed_val = -parsed_val
        return round(parsed_val, 4)
    except ValueError:
        logger.warning("Failed to parse currency value: '%s'", value)
        return None


def clean_currency_fields(
    record: Dict[str, Any],
    currency_fields: List[str],
) -> Tuple[Dict[str, Any], List[str]]:
    """
    Clean specified monetary fields in a single record.
    
    Returns:
        Tuple of (updated_record, list_of_error_field_names).
    """
    updated = dict(record)
    errors: List[str] = []

    for field in currency_fields:
        if field in updated and updated[field] is not None and str(updated[field]).strip() != "":
            raw_val = updated[field]
            cleaned = clean_currency(raw_val)
            if cleaned is None:
                errors.append(field)
            else:
                updated[field] = cleaned

    return updated, errors
