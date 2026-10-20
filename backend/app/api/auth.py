import json
import secrets
import string
from fastapi import APIRouter, Depends, HTTPException, Request, status
from databricks.sql.client import Cursor
from app.core import security
from app.core.config import settings
from app.core.dependencies import get_current_user, get_db_cursor
from app.repositories.team_repository import TeamRepository
from app.repositories.user_repository import UserRepository
from app.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    ResetPasswordResponse,
    TokenResponse,
    UserOut,
    UserRole,
)
from app.services.auth_service import AuthService

router = APIRouter()


def _generate_temp_password(length: int = 14) -> str:
    """Generate a secure, high-entropy temporary password with mixed characters."""
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


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="User Login",
    description="Authenticate user credentials against platform.users and return a signed JWT bearer token.",
)
def login(
    login_data: LoginRequest,
    request: Request,
    cursor: Cursor = Depends(get_db_cursor),
) -> TokenResponse:
    """
    Authenticate against platform.users table.
    
    Returns JWT access token with user details: id, name, email, role, tenant_id.
    Accepts X-Simulate-DB-Error header in development to verify warehouse failure handling.
    """
    simulate_db_error = (
        request.headers.get("x-simulate-db-error", "").lower() in ("1", "true", "yes")
        and settings.is_development
    )
    authenticated_user = AuthService.authenticate_user(
        cursor=cursor,
        email=login_data.email,
        password=login_data.password,
        simulate_db_error=simulate_db_error,
    )
    return AuthService.build_token_response(authenticated_user)


@router.get(
    "/me",
    response_model=UserOut,
    status_code=status.HTTP_200_OK,
    summary="Get Current User Profile",
    description="Retrieve profile and tenant boundary details for the currently authenticated user.",
)
def get_current_user_profile(
    current_user: UserOut = Depends(get_current_user),
) -> UserOut:
    """Return the active user profile extracted from the JWT token and platform.users."""
    return current_user


@router.post(
    "/change-password",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="Change User Password",
    description="Verify current password, hash new password, and clear must_change_password requirement.",
)
def change_password(
    payload: ChangePasswordRequest,
    current_user: UserOut = Depends(get_current_user),
    cursor: Cursor = Depends(get_db_cursor),
) -> dict:
    """
    Update password for the currently authenticated user.
    
    Verifies current password, applies new password (minimum 10 characters),
    and resets must_change_password to false.
    """
    user_repo = UserRepository(cursor)
    user_record = user_repo.get_by_id(current_user.id)
    if not user_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User account not found.",
        )

    stored_hash = str(user_record.get("password_hash", ""))
    if not AuthService.verify_password(payload.current_password, stored_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect.",
        )

    new_hash = security.get_password_hash(payload.new_password)
    user_repo.update_password(
        user_id=current_user.id,
        password_hash=new_hash,
        must_change_password=False,
    )

    return {
        "success": True,
        "message": "Password changed successfully.",
    }


def _execute_password_reset(
    user_id: int,
    current_user: UserOut,
    cursor: Cursor,
) -> ResetPasswordResponse:
    """
    Perform password reset with RBAC checks and immutable audit trail recording.
    
    Permissions:
      - Admin: Can reset any user's password.
      - Team Member: Can reset the SMB Owner of an assigned tenant.
      - SMB Owner: Forbidden (403).
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

    # Write immutable audit row to meta.audit_trail (omits password)
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

    return ResetPasswordResponse(
        temporary_password=temp_password,
        must_change_password=True,
        message="Temporary password generated successfully. It will only be shown once.",
    )


@router.post(
    "/users/{user_id}/reset-password",
    response_model=ResetPasswordResponse,
    status_code=status.HTTP_200_OK,
    summary="Reset User Password",
    description="Admin can reset any user's password; Team Member can reset the SMB Owner of an assigned tenant.",
)
def reset_user_password(
    user_id: int,
    current_user: UserOut = Depends(get_current_user),
    cursor: Cursor = Depends(get_db_cursor),
) -> ResetPasswordResponse:
    return _execute_password_reset(user_id, current_user, cursor)


@router.post(
    "/{user_id}/reset-password",
    response_model=ResetPasswordResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
def reset_user_password_alias(
    user_id: int,
    current_user: UserOut = Depends(get_current_user),
    cursor: Cursor = Depends(get_db_cursor),
) -> ResetPasswordResponse:
    return _execute_password_reset(user_id, current_user, cursor)

