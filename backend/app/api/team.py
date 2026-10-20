import logging
import re
import secrets
import string
from typing import List, Optional

from databricks.sql.client import Cursor
from fastapi import APIRouter, Depends, HTTPException, status

from app.core.dependencies import get_current_user, get_db_cursor, require_admin
from app.core.security import get_password_hash
from app.repositories.team_repository import TeamRepository
from app.schemas.auth import UserOut, UserRole
from app.schemas.team import (
    ReplaceAssignmentsRequest,
    TeamMemberCreate,
    TeamMemberCreatedResponse,
    TeamMemberOut,
    ToggleActiveRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter()

PHONE_REGEX = re.compile(r"^[0-9+\-() ]{7,20}$")
EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")


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
    "",
    response_model=TeamMemberCreatedResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register Team Member",
    description="Register a new internal team member or admin, generate a temporary password, and assign tenants.",
)
def create_team_member(
    payload: TeamMemberCreate,
    cursor: Cursor = Depends(get_db_cursor),
    current_admin: UserOut = Depends(require_admin),
) -> TeamMemberCreatedResponse:
    """
    Register an internal team member or administrator (Admin only).
    
    Validations:
      - Email uniqueness (409 if taken).
      - Phone number format (7-20 chars with allowed symbols).
      - Tenant existence: verifies all specified tenant_ids exist in platform.tenants.
    
    Generates a secure temporary password, hashes it, sets must_change_password=True,
    inserts team_assignments rows, and returns the temporary password ONCE without logging it.
    """
    team_repo = TeamRepository(cursor)

    # 1. Validate email format & uniqueness
    clean_email = str(payload.email).strip().lower()
    if not EMAIL_REGEX.match(clean_email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid email format.",
        )

    existing_user = team_repo.get_by_email(clean_email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A user with email '{clean_email}' already exists.",
        )

    # 2. Validate phone number format
    clean_phone = payload.phone_number.strip()
    if not PHONE_REGEX.match(clean_phone):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Phone number must be between 7 and 20 characters and contain only digits, spaces, plus, dash, and parentheses.",
        )

    # 3. Verify tenant existence if tenant_ids provided
    tenant_ids = payload.tenant_ids or []
    if tenant_ids:
        missing_tenants = team_repo.verify_tenants_exist(tenant_ids)
        if missing_tenants:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"The following organization IDs do not exist: {missing_tenants}",
            )

    # 4. Generate temporary password server-side and hash (DO NOT LOG PASSWORD)
    temp_password = _generate_temp_password(length=14)
    password_hash = get_password_hash(temp_password)

    # 5. Insert user record into platform.users
    user_record = team_repo.create_user(
        name=payload.name.strip(),
        email=clean_email,
        password_hash=password_hash,
        role=payload.role.value,
        phone_number=clean_phone,
        staff_id=payload.staff_id.strip() if payload.staff_id else None,
        designation=payload.designation.strip() if payload.designation else None,
        must_change_password=True,
    )
    user_id = int(user_record["user_id"])

    # 6. Insert team assignments
    if tenant_ids:
        team_repo.add_assignments(user_id, tenant_ids)

    # 7. Fetch full user data with assignments
    full_user = team_repo.get_by_id(user_id) or user_record
    assigned_list = full_user.get("tenant_ids", tenant_ids)

    logger.info(
        "Team member registered successfully: user_id=%d, email=%s, role=%s by admin=%d",
        user_id,
        clean_email,
        payload.role.value,
        current_admin.id,
    )

    return TeamMemberCreatedResponse(
        user_id=user_id,
        id=user_id,
        name=str(full_user.get("name", payload.name)),
        email=clean_email,
        phone_number=clean_phone,
        role=str(full_user.get("role", payload.role.value)),
        staff_id=full_user.get("staff_id"),
        designation=full_user.get("designation"),
        is_active=bool(full_user.get("is_active", True)),
        created_at=full_user.get("created_at"),
        tenant_ids=assigned_list,
        assigned_tenants=assigned_list,
        must_change_password=True,
        temporary_password=temp_password,
    )


@router.get(
    "",
    response_model=List[TeamMemberOut],
    status_code=status.HTTP_200_OK,
    summary="List Team Members",
    description="Retrieve all internal team members and admins along with their assigned tenant IDs (Admin only).",
)
def list_team_members(
    cursor: Cursor = Depends(get_db_cursor),
    current_admin: UserOut = Depends(require_admin),
) -> List[TeamMemberOut]:
    """List all team members and admins with their assigned tenant IDs."""
    team_repo = TeamRepository(cursor)
    members = team_repo.list_team_members()
    return [TeamMemberOut.model_validate(m) for m in members]


@router.put(
    "/{user_id}/assignments",
    response_model=TeamMemberOut,
    status_code=status.HTTP_200_OK,
    summary="Replace Team Member Assignments",
    description="Replace the full list of assigned tenants for a team member (Admin only).",
)
def replace_team_member_assignments(
    user_id: int,
    payload: ReplaceAssignmentsRequest,
    cursor: Cursor = Depends(get_db_cursor),
    current_admin: UserOut = Depends(require_admin),
) -> TeamMemberOut:
    """Replace all tenant assignments for a given team member."""
    team_repo = TeamRepository(cursor)
    user = team_repo.get_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Team member with ID {user_id} not found.",
        )

    # Verify all new tenant IDs exist
    if payload.tenant_ids:
        missing_tenants = team_repo.verify_tenants_exist(payload.tenant_ids)
        if missing_tenants:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"The following organization IDs do not exist: {missing_tenants}",
            )

    team_repo.replace_assignments(user_id, payload.tenant_ids)

    updated_user = team_repo.get_by_id(user_id)
    logger.info(
        "Updated tenant assignments for user_id=%d to %s by admin=%d",
        user_id,
        payload.tenant_ids,
        current_admin.id,
    )
    return TeamMemberOut.model_validate(updated_user)


@router.patch(
    "/{user_id}/active",
    response_model=TeamMemberOut,
    status_code=status.HTTP_200_OK,
    summary="Toggle Team Member Active Status",
    description="Activate or deactivate an internal team member (Admin only).",
)
def toggle_team_member_active_status(
    user_id: int,
    payload: ToggleActiveRequest,
    cursor: Cursor = Depends(get_db_cursor),
    current_admin: UserOut = Depends(require_admin),
) -> TeamMemberOut:
    """Activate or deactivate a team member account."""
    team_repo = TeamRepository(cursor)
    user = team_repo.get_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Team member with ID {user_id} not found.",
        )

    team_repo.set_active_status(user_id, payload.is_active)

    updated_user = team_repo.get_by_id(user_id)
    logger.info(
        "Toggled active status for user_id=%d to is_active=%s by admin=%d",
        user_id,
        payload.is_active,
        current_admin.id,
    )
    return TeamMemberOut.model_validate(updated_user)


@router.post(
    "/{user_id}/reset-password",
    status_code=status.HTTP_200_OK,
    summary="Reset User Password",
    description="Admin can reset any user's password; Team Member can reset the SMB Owner of an assigned tenant.",
)
def reset_team_user_password(
    user_id: int,
    current_user: UserOut = Depends(get_current_user),
    cursor: Cursor = Depends(get_db_cursor),
):
    from app.api.auth import _execute_password_reset
    return _execute_password_reset(user_id, current_user, cursor)

