import logging
import re
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("helios.pipeline.cleaning.currency")

CURRENCY_PREFIX_REGEX = re.compile(r"^\s*(?:₹|Rs\.?|INR|[$€£¥])\s*", re.IGNORECASE)
CURRENCY_SUFFIX_REGEX = re.compile(r"\s*(?:/-\s*|₹|Rs\.?|INR|[$€£¥]\s*)$", re.IGNORECASE)
PARENTHESES_NEGATIVE_REGEX = re.compile(r"^\((.+)\)$")


def clean_currency(value: Any) -> Optional[Decimal]:
    """
    Clean and convert a monetary/currency string or number into a standard Decimal with no floating point.
    Handles Indian currency formats ("₹1,25,000.00", "₹ 1,250.50", "Rs. 1,250", "Rs 1250",
    "INR 899", "1,25,000", "1250/-", " 899 "), standard currency symbols ($ € £ ¥),
    commas, whitespace, and accounting negatives like (12.50).
    
    Returns:
        Decimal representation, or None if value is unparseable or invalid.
    """
    if value is None:
        return None

    if isinstance(value, Decimal):
        return value

    if isinstance(value, (int, float)):
        try:
            return Decimal(str(value))
        except (InvalidOperation, ValueError):
            return None

    text = str(value).strip()
    if not text or text.lower() in ("null", "none", "nan", "n/a", ""):
        return None

    is_negative = False
    paren_match = PARENTHESES_NEGATIVE_REGEX.match(text)
    if paren_match:
        is_negative = True
        text = paren_match.group(1).strip()
    elif text.startswith("-"):
        is_negative = True
        text = text[1:].strip()

    text = CURRENCY_PREFIX_REGEX.sub("", text).strip()
    if text.startswith("-"):
        is_negative = True
        text = text[1:].strip()

    text = CURRENCY_SUFFIX_REGEX.sub("", text).strip()
    text = CURRENCY_PREFIX_REGEX.sub("", text).strip()

    if not text:
        return None

    sanitized = text.replace(",", "").replace(" ", "").replace("'", "")
    if not re.match(r"^\d+(?:\.\d+)?$", sanitized):
        logger.warning("Failed to parse currency value: '%s'", value)
        return None

    try:
        dec = Decimal(sanitized)
        if is_negative:
            dec = -dec
        return dec
    except (InvalidOperation, ValueError):
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
