from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional
from fastapi import HTTPException, status

from app.repositories.notification_repository import NotificationRepository
from app.repositories.support_repository import SupportRepository
from app.schemas.support import (
    SupportMessageOut,
    SupportMessageResolveResponse,
)

logger = logging.getLogger("helios.services.support")


class SupportService:
    """Service handling support messaging routing, notifications, and resolution."""

    @classmethod
    def send_message(
        cls,
        tenant_id: int,
        from_user_id: int,
        message: str,
        repo: SupportRepository,
    ) -> SupportMessageOut:
        """
        Send a support message / update request from an SMB Owner.
        Resolves to_user_id by checking platform.team_assignments for tenant_id.
        If no Team Member is assigned, falls back to any Admin so message is never unrouted.
        Triggers an operational notification to the resolved recipient.
        """
        if not message or not message.strip():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Message content cannot be empty.",
            )

        # 1. Resolve recipient (assigned Team Member or fallback Admin)
        to_user_id = repo.resolve_recipient_user_id(tenant_id=tenant_id)

        # 2. Persist message in platform.support_messages
        created_raw = repo.create_message(
            tenant_id=tenant_id,
            from_user_id=from_user_id,
            to_user_id=to_user_id,
            message=message.strip(),
        )

        # 3. Trigger notification to the recipient user
        try:
            notification_repo = NotificationRepository(repo.cursor, catalog=repo.catalog)
            snippet = message.strip()[:60] + ("..." if len(message.strip()) > 60 else "")
            tenant_label = created_raw.get("tenant_name") or f"Tenant #{tenant_id}"
            notification_repo.create(
                tenant_id=tenant_id,
                user_id=to_user_id,
                message=f"New support request from {tenant_label}: \"{snippet}\"",
                type="info",
            )
        except Exception as exc:
            logger.warning("Could not dispatch notification for support message: %s", exc)

        return SupportMessageOut.model_validate(created_raw)

    @classmethod
    def flag_for_admin(
        cls,
        tenant_id: int,
        from_user_id: int,
        message: str,
        batch_id: Optional[str],
        repo: SupportRepository,
    ) -> SupportMessageOut:
        """
        Submit a flagged escalation from a Team Member or Admin.
        Always routes to an Admin user regardless of team_assignments.
        Sets message_source='team_member'.
        Triggers an operational warning notification to the recipient Admin.
        """
        if not message or not message.strip():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Escalation message content cannot be empty.",
            )

        # 1. Always route to an Admin regardless of team_assignments
        to_user_id = repo.resolve_admin_user_id()

        # 2. Format message with optional batch reference if provided
        batch_tag = f"[Batch: {batch_id.strip()}] " if batch_id and batch_id.strip() else ""
        formatted_message = f"{batch_tag}{message.strip()}"

        # 3. Persist escalation message with message_source='team_member'
        created_raw = repo.create_message(
            tenant_id=tenant_id,
            from_user_id=from_user_id,
            to_user_id=to_user_id,
            message=formatted_message,
            message_source="team_member",
            batch_id=batch_id,
        )

        # 4. Trigger warning notification to the recipient Admin
        try:
            notification_repo = NotificationRepository(repo.cursor, catalog=repo.catalog)
            snippet = message.strip()[:60] + ("..." if len(message.strip()) > 60 else "")
            tenant_label = created_raw.get("tenant_name") or f"Tenant #{tenant_id}"
            batch_desc = f" on batch {batch_id}" if batch_id else ""
            notification_repo.create(
                tenant_id=tenant_id,
                user_id=to_user_id,
                message=f"Team Member flagged issue{batch_desc} for {tenant_label}: \"{snippet}\"",
                type="warning",
            )
        except Exception as exc:
            logger.warning("Could not dispatch notification for flag escalation: %s", exc)

        return SupportMessageOut.model_validate(created_raw)

    @classmethod
    def get_messages(
        cls,
        user_id: int,
        user_role: str,
        status_filter: Optional[str],
        repo: SupportRepository,
    ) -> List[SupportMessageOut]:
        """
        List support messages:
        - Team Member sees only messages routed to them.
        - Admin sees all messages across all tenants.
        """
        raw_list = repo.get_messages(
            user_id=user_id,
            user_role=user_role,
            status_filter=status_filter,
        )
        return [SupportMessageOut.model_validate(r) for r in raw_list]

    @classmethod
    def resolve_message(
        cls,
        message_id: int,
        user_id: int,
        user_role: str,
        repo: SupportRepository,
    ) -> SupportMessageResolveResponse:
        """
        Mark a support message as resolved.
        Allowed for Admins and Team Members (if message is routed to them or Admin).
        """
        existing = repo.get_message_by_id(message_id)
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Support message with ID {message_id} was not found.",
            )

        if user_role.lower() != "admin" and existing.get("to_user_id") != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to resolve messages assigned to another user.",
            )

        updated = repo.resolve_message(message_id)
        resolved_dt = (
            updated.get("resolved_at") if updated and updated.get("resolved_at")
            else datetime.now(timezone.utc)
        )

        return SupportMessageResolveResponse(
            success=True,
            message="Support message marked as resolved.",
            message_id=message_id,
            status="resolved",
            resolved_at=resolved_dt,
        )
