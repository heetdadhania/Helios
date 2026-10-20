import json
import logging
import secrets
import string
from typing import Any, Dict, Optional
from fastapi import HTTPException, status
from databricks.sql.client import Cursor

from app.core import security
from app.core.config import settings
from app.db.base import databricks_cursor
from app.repositories.user_repository import UserRepository
from app.schemas.auth import ResetPasswordResponse, UserOut, UserRole

logger = logging.getLogger(__name__)


def _generate_temp_password(length: int = 14) -> str:
    """Generate a secure, high-entropy temporary password."""
    specials = "!@#$%^&*"
    chars = [
        secrets.choice(string.ascii_uppercase),
        secrets.choice(string.ascii_lowercase),
        secrets.choice(string.digits),
        secrets.choice(specials),
    ]
    all_chars = string.ascii_letters + string.digits + specials
    chars += [secrets.choice(all_chars) for _ in range(max(0, length - 4))]
    secrets.SystemRandom().shuffle(chars)
    return "".join(chars)


def ensure_no_active_owner(tenant_id: int, cursor: Optional[Cursor] = None) -> None:
    """
    Ensure the tenant has no active SMB owner.
    Used by every code path that creates an smb_owner user (Add Tenant, replace owner, scripts/seed_accounts.py).
    A second active owner raises HTTP 409 "This tenant already has an owner".
    Immediately checks platform.users before insert.
    """
    catalog = settings.DATABRICKS_CATALOG
    query = f"""
        SELECT user_id, email, is_active 
        FROM `{catalog}`.`platform`.`users`
        WHERE tenant_id = :tenant_id 
          AND role = 'smb_owner' 
          AND coalesce(is_active, true) = true
        LIMIT 1
    """
    parameters = {"tenant_id": int(tenant_id)}

    if cursor is not None:
        cursor.execute(query, parameters)
        row = cursor.fetchone()
    else:
        with databricks_cursor() as cur:
            cur.execute(query, parameters)
            row = cur.fetchone()

    if row:
        logger.warning(
            "Conflict: Tenant %d already has an active SMB owner (user_id=%s, email=%s)",
            tenant_id,
            row[0],
            row[1],
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This organization already has an owner",
        )


def execute_password_reset(
    user_id: int,
    current_user: UserOut,
    cursor: Cursor,
) -> ResetPasswordResponse:
    """
    Shared password reset implementation with RBAC checks and immutable audit logging.
    Used by all reset password routes across auth, team, and tenant owner endpoints.
    Returns the generated temporary password ONCE and never logs it.
    """
    if current_user.role == UserRole.SMB_OWNER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Organization Owners are not authorized to reset user passwords.",
        )

    user_repo = UserRepository(cursor)
    target_user = user_repo.get_by_id(user_id)
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found.",
        )

    # Team Member permission check: target must be smb_owner and in an assigned tenant
    if current_user.role == UserRole.TEAM_MEMBER:
        target_role = str(target_user.get("role", "")).lower()
        if target_role != UserRole.SMB_OWNER.value:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: Team Members can only reset passwords for Organization Owners.",
            )

        from app.repositories.team_repository import TeamRepository
        team_repo = TeamRepository(cursor)
        assigned_tenants = team_repo.get_assigned_tenant_ids(current_user.id)
        target_tenant = target_user.get("tenant_id")
        if target_tenant is None or target_tenant not in assigned_tenants:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: You are not assigned to manage organization {target_tenant}.",
            )

    # Generate high-entropy temporary password (NEVER logged)
    temp_password = _generate_temp_password(14)
    hashed_temp = security.get_password_hash(temp_password)

    # Persist in platform.users with must_change_password=True, clearing failed attempts
    user_repo.reset_password(user_id=user_id, password_hash=hashed_temp)

    # Write immutable audit row to meta.audit_trail (never includes password)
    target_tenant_id = target_user.get("tenant_id")
    target_email = str(target_user.get("email", ""))
    target_role_str = str(target_user.get("role", ""))

    user_repo.write_audit_log(
        actor_user_id=current_user.id,
        actor_role=current_user.role.value,
        action="password_reset",
        tenant_id=target_tenant_id,
        reason=f"Password reset initiated by {current_user.role.value}",
        details_json=json.dumps({
            "target_user_id": user_id,
            "target_email": target_email,
            "target_role": target_role_str,
        }),
    )

    logger.info(
        "Password reset executed successfully for user_id=%d [tenant_id=%s] by actor_id=%d",
        user_id,
        str(target_tenant_id),
        current_user.id,
    )

    return ResetPasswordResponse(
        temporary_password=temp_password,
        must_change_password=True,
        message="Temporary password generated successfully. It will only be shown once.",
    )
