"""
Sorting validation and SQL mapping for Helios list endpoints.
Strictly ensures that user-supplied sort field names are never interpolated directly into SQL.
Invalid sort field names are rejected with HTTP 422 Unprocessable Entity.
"""

from typing import Dict, Optional
from fastapi import HTTPException, status


ORGANIZATION_SORT_FIELDS: Dict[str, str] = {
    "id": "t.tenant_id",
    "name": "lower(coalesce(t.business_name, t.name))",
    "industry": "lower(coalesce(t.industry, ''))",
    "state": "lower(coalesce(t.state, ''))",
    "created": "t.created_at",
    "last_data": "coalesce(t.last_data_received_at, t.created_at)",
    "last data": "coalesce(t.last_data_received_at, t.created_at)",
    "status": "coalesce(t.is_active, true)",
}

TEAM_MEMBER_SORT_FIELDS: Dict[str, str] = {
    "id": "u.user_id",
    "name": "lower(u.name)",
    "email": "lower(u.email)",
    "designation": "lower(coalesce(u.designation, ''))",
    "assigned_count": "coalesce(ta_cnt.cnt, 0)",
    "assigned count": "coalesce(ta_cnt.cnt, 0)",
    "created": "u.created_at",
    "status": "coalesce(u.is_active, true)",
}

PENDING_UPLOADS_SORT_FIELDS: Dict[str, str] = {
    "date": "ps.created_at",
    "organization": "lower(coalesce(t.business_name, ''))",
    "source": "lower(coalesce(pu.source_type, 'upload'))",
    "status": "lower(ps.status)",
}

HISTORY_SORT_FIELDS: Dict[str, str] = {
    "date": "ps.created_at",
    "organization": "lower(coalesce(t.business_name, ''))",
    "source": "lower(coalesce(pu.source_type, 'upload'))",
    "status": "lower(ps.status)",
}

PIPELINE_HEALTH_SORT_FIELDS: Dict[str, str] = {
    "updated": "coalesce(ps.updated_at, ps.created_at)",
    "organization": "lower(coalesce(t.business_name, ''))",
    "stage": "lower(ps.stage)",
    "status": "lower(ps.status)",
}

DATA_QUALITY_SORT_FIELDS: Dict[str, str] = {
    "time": "d.logged_at",
    "organization": "lower(coalesce(t.business_name, ''))",
    "table": "lower(d.table_name)",
    "reason": "lower(d.rejection_reason)",
}

SUPPORT_SORT_FIELDS: Dict[str, str] = {
    "date": "sm.created_at",
    "organization": "lower(coalesce(t.business_name, ''))",
    "status": "lower(sm.status)",
    "source": "lower(sm.message_source)",
}

AUDIT_SORT_FIELDS: Dict[str, str] = {
    "time": "a.occurred_at",
    "actor": "lower(coalesce(u.name, cast(a.actor_user_id as string)))",
    "action": "lower(a.action)",
    "organization": "lower(coalesce(t.business_name, ''))",
}


def validate_and_resolve_sort(
    sort_by: Optional[str],
    sort_order: Optional[str],
    allowed_fields: Dict[str, str],
    default_clause: str,
) -> str:
    """
    Validate sort_by and sort_order against an allow-list of fields.
    Never puts user-supplied sort_by text into SQL.
    Returns safe ORDER BY SQL clause.
    Raises HTTPException(422) if sort_by or sort_order is invalid.
    """
    if not sort_by or not sort_by.strip():
        if sort_order and sort_order.strip():
            order_str = sort_order.strip().lower()
            if order_str not in ("asc", "desc"):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Invalid sort order '{sort_order}'. Allowed orders: ['asc', 'desc']",
                )
        return default_clause

    clean_by = sort_by.strip().lower()
    norm_by = clean_by.replace(" ", "_")

    matched_col = None
    for key, col in allowed_fields.items():
        k_clean = key.lower()
        if k_clean == clean_by or k_clean.replace(" ", "_") == norm_by:
            matched_col = col
            break

    if not matched_col:
        valid_keys = sorted(list(set(k.lower() for k in allowed_fields.keys())))
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid sort field '{sort_by}'. Allowed sort fields: {valid_keys}",
        )

    order_str = "asc" if not sort_order or not sort_order.strip() else sort_order.strip().lower()
    if order_str not in ("asc", "desc"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid sort order '{sort_order}'. Allowed orders: ['asc', 'desc']",
        )

    direction = "ASC" if order_str == "asc" else "DESC"
    return f"{matched_col} {direction}"

