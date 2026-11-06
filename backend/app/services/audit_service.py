"""Service layer for recording and querying operational and security audit events."""

import logging
from typing import Any, Optional, Union

try:
    from databricks.sql.client import Cursor
except ImportError:
    Cursor = Any  # type: ignore

from app.repositories.audit_repository import AuditRepository
from app.schemas.audit import AuditLogItem
from app.schemas.common import PaginatedResponse

logger = logging.getLogger("helios.services.audit")


def write_audit_log(
    cursor: Cursor,
    actor_user_id: Optional[int],
    actor_role: Optional[str],
    action: str,
    tenant_id: Optional[int] = None,
    batch_id: Optional[str] = None,
    reason: Optional[str] = None,
    details: Optional[Union[dict, str]] = None,
) -> None:
    """
    Unified, single audit logging helper.
    Records an immutable audit event to meta.audit_trail across all application modules.
    """
    repo = AuditRepository(cursor)
    repo.write_audit_log(
        actor_user_id=actor_user_id,
        actor_role=actor_role,
        action=action,
        tenant_id=tenant_id,
        batch_id=batch_id,
        reason=reason,
        details_json=details,
    )


class AuditService:
    """Central service for audit log mutations and queries."""

    @staticmethod
    def log(
        cursor: Cursor,
        actor_user_id: Optional[int],
        actor_role: Optional[str],
        action: str,
        tenant_id: Optional[int] = None,
        batch_id: Optional[str] = None,
        reason: Optional[str] = None,
        details: Optional[Union[dict, str]] = None,
    ) -> None:
        """Alias for write_audit_log."""
        write_audit_log(
            cursor=cursor,
            actor_user_id=actor_user_id,
            actor_role=actor_role,
            action=action,
            tenant_id=tenant_id,
            batch_id=batch_id,
            reason=reason,
            details=details,
        )

    @classmethod
    def get_audit_trail(
        cls,
        cursor: Cursor,
        page: int = 1,
        page_size: int = 20,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        actor: Optional[str] = None,
        action: Optional[str] = None,
        tenant_id: Optional[int] = None,
        organization: Optional[str] = None,
        order_by: str = "a.occurred_at DESC, a.audit_id DESC",
    ) -> PaginatedResponse[AuditLogItem]:
        """
        Fetch paginated audit trail items with optional filters.
        Strictly accessible by Administrators.
        """
        repo = AuditRepository(cursor)
        items, total = repo.list_audit_logs(
            page=page,
            page_size=page_size,
            start_date=start_date,
            end_date=end_date,
            actor=actor,
            action=action,
            tenant_id=tenant_id,
            organization=organization,
            order_by=order_by,
        )
        return PaginatedResponse[AuditLogItem](
            items=[AuditLogItem.model_validate(item) for item in items],
            total=total,
            page=page,
            page_size=page_size,
        )

