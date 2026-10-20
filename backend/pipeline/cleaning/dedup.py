import logging
from typing import Any, Dict, List, Optional, Sequence, Tuple

logger = logging.getLogger("helios.pipeline.cleaning.dedup")


def deduplicate_records(
    records: List[Dict[str, Any]],
    key_fields: Sequence[str] = ("order_id",),
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Remove duplicates by natural key(s) such as order_id.
    Keeps the first occurrence of each unique key; subsequent duplicates
    are placed in the rejected list with an explainable rejection_reason.
    
    Returns:
        Tuple of (unique_records, rejected_duplicate_records).
    """
    seen_keys: set[str] = set()
    unique_list: List[Dict[str, Any]] = []
    duplicate_list: List[Dict[str, Any]] = []

    for row in records:
        key_vals = [str(row.get(k, "")).strip().lower() for k in key_fields]
        composite_key = "|".join(key_vals)

        # If natural key is completely empty, it will be handled by null_handler,
        # but if key is present and already seen, flag as duplicate:
        if composite_key and composite_key != "|" * (len(key_fields) - 1):
            if composite_key in seen_keys:
                rej_row = dict(row)
                keys_str = ", ".join(f"{k}={row.get(k)}" for k in key_fields)
                rej_row["rejection_reason"] = f"duplicate_natural_key: {keys_str}"
                duplicate_list.append(rej_row)
                continue
            seen_keys.add(composite_key)

        unique_list.append(row)

    logger.info(
        "Deduplication completed on %s: in=%d, unique=%d, duplicates_rejected=%d",
        list(key_fields),
        len(records),
        len(unique_list),
        len(duplicate_list),
    )
    return unique_list, duplicate_list
