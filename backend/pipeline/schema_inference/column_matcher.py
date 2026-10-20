import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from rapidfuzz import fuzz

logger = logging.getLogger(__name__)

DEFAULT_SIMILARITY_THRESHOLD: float = 80.0


def normalize_column_name(name: str) -> str:
    """
    Normalizes a column name by lowercasing, stripping whitespace,
    and replacing symbols/non-alphanumeric characters with underscores.
    """
    if not name:
        return ""
    cleaned = name.strip().lower()
    cleaned = re.sub(r"[^\w]+", "_", cleaned)
    return cleaned.strip("_")


def match_column(
    incoming_name: str,
    fields_dict: Dict[str, Dict[str, Any]],
    threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
) -> Optional[Dict[str, Any]]:
    """
    Fuzzy-matches a single incoming column against candidate template fields.
    Checks canonical names and all registered aliases.

    Returns:
        Dict with target_field, score (0-100), matched_alias, and is_exact,
        or None if no field meets the similarity threshold.
    """
    norm_incoming = normalize_column_name(incoming_name)
    if not norm_incoming:
        return None

    best_match: Optional[str] = None
    best_alias: Optional[str] = None
    best_score: float = 0.0

    for field_name, field_def in fields_dict.items():
        norm_field = normalize_column_name(field_name)

        # 1. Exact canonical match check
        if norm_incoming == norm_field:
            return {
                "target_field": field_name,
                "score": 100.0,
                "matched_alias": field_name,
                "is_exact": True,
            }

        # 2. Check aliases for exact match
        aliases = field_def.get("aliases", [])
        for alias in aliases:
            norm_alias = normalize_column_name(alias)
            if norm_incoming == norm_alias:
                return {
                    "target_field": field_name,
                    "score": 100.0,
                    "matched_alias": alias,
                    "is_exact": True,
                }

        # 3. Fuzzy match against canonical name
        score_canonical = fuzz.token_sort_ratio(norm_incoming, norm_field)
        if score_canonical > best_score:
            best_score = float(score_canonical)
            best_match = field_name
            best_alias = field_name

        # 4. Fuzzy match against aliases
        for alias in aliases:
            norm_alias = normalize_column_name(alias)
            score_alias = fuzz.token_sort_ratio(norm_incoming, norm_alias)
            if score_alias > best_score:
                best_score = float(score_alias)
                best_match = field_name
                best_alias = alias

    if best_match is not None and best_score >= threshold:
        return {
            "target_field": best_match,
            "score": round(best_score, 2),
            "matched_alias": best_alias,
            "is_exact": best_score >= 99.5,
        }

    return None


def match_columns_to_template(
    incoming_columns: List[str],
    template: Dict[str, Any],
    threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
) -> Dict[str, Optional[Dict[str, Any]]]:
    """
    Matches a list of incoming columns to a given template schema.
    Resolves conflicts if multiple incoming columns map to the same target field
    by giving preference to the highest scoring match.

    Returns:
        Dictionary mapping incoming_column_name -> match details or None.
    """
    fields_dict = template.get("fields", {})
    raw_matches: Dict[str, Optional[Dict[str, Any]]] = {}

    for col in incoming_columns:
        match = match_column(col, fields_dict, threshold=threshold)
        raw_matches[col] = match

    # Resolve duplicates: if multiple incoming columns map to the same target_field,
    # keep the one with the highest score.
    target_to_cols: Dict[str, List[Tuple[str, float]]] = {}
    for col, match in raw_matches.items():
        if match:
            target = match["target_field"]
            target_to_cols.setdefault(target, []).append((col, match["score"]))

    final_mapping: Dict[str, Optional[Dict[str, Any]]] = {}
    for col, match in raw_matches.items():
        if match is None:
            final_mapping[col] = None
            continue

        target = match["target_field"]
        candidates = target_to_cols.get(target, [])
        best_candidate_col, best_candidate_score = max(candidates, key=lambda x: x[1])

        if col == best_candidate_col:
            final_mapping[col] = match
        else:
            logger.info(
                "Column '%s' yielded lower score (%s) for '%s' than '%s' (%s); skipped.",
                col,
                match["score"],
                target,
                best_candidate_col,
                best_candidate_score,
            )
            final_mapping[col] = None

    return final_mapping
