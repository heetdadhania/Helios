import json
import logging
import re
import secrets
import string
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
try:
    from databricks.sql.client import Cursor
except ImportError:
    Cursor = Any  # type: ignore

from app.core.config import settings
from app.core.dependencies import get_current_user, get_db_cursor, require_team_or_admin
from app.core.security import get_password_hash
from app.repositories.team_repository import TeamRepository
from app.repositories.tenant_repository import TenantRepository
from app.repositories.user_repository import UserRepository
from app.schemas.auth import ResetPasswordResponse, UserOut, UserRole
from app.schemas.tenant import (
    EditOwnerRequest,
    OwnerResponse,
    ReplaceOwnerRequest,
    TenantCreate,
    TenantOut,
    ToggleOwnerActiveRequest,
)
from app.services.owner_service import (
    check_and_safeguard_single_owner,
    ensure_no_active_owner,
    execute_password_reset,
)

logger = logging.getLogger(__name__)

router = APIRouter()

# Validation regexes
PHONE_REGEX = re.compile(r"^[0-9+\-() ]{7,20}$")
EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")


def _generate_temp_password(length: int = 12) -> str:
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
    response_model=TenantOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new tenant organization with full onboarding payload",
)
def create_tenant(
    tenant_in: TenantCreate,
    cursor: Cursor = Depends(get_db_cursor),
    current_user: UserOut = Depends(require_team_or_admin),
) -> TenantOut:
    """
    Onboard a new tenant organization. Available to Team Members and Admins.
    
    Validations:
      - Valid email format for contact_email and owner_email (if provided).
      - Phone number contains only digits, spaces, plus, dash, parentheses (7-20 chars).
      - website_url (if provided) starts with http:// or https://.
      - business_name must not be already used by another active tenant (returns 409).
      - If assigned_team_member_id is provided, verifies user exists and has role team_member,
        then creates the platform.team_assignments row.
      - If caller is a team_member and no assignment given, assigns tenant to caller automatically.
      - Creates SMB Owner login with server-generated temporary password hashed via bcrypt.
      - Returns temporary password ONCE in the response; never logs it.
    """
    tenant_repo = TenantRepository(cursor)
    user_repo = UserRepository(cursor)

    # 1. Validate email format
    contact_email_clean = str(tenant_in.contact_email).strip().lower()
    if not EMAIL_REGEX.match(contact_email_clean):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid contact_email format.",
        )

    owner_email_clean = (
        str(tenant_in.owner_email).strip().lower()
        if tenant_in.owner_email
        else contact_email_clean
    )
    if not EMAIL_REGEX.match(owner_email_clean):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid owner_email format.",
        )

    # 2. Validate phone number format (digits, spaces, plus, dash, parentheses, length 7-20)
    phone_clean = tenant_in.phone_number.strip()
    if len(phone_clean) < 7 or len(phone_clean) > 20 or not PHONE_REGEX.match(phone_clean):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Phone number must be between 7 and 20 characters and contain only digits, spaces, plus, dash, and parentheses.",
        )

    # 3. Validate website_url (must start with http:// or https:// if provided)
    website_clean = tenant_in.website_url.strip() if tenant_in.website_url else None
    if website_clean:
        if not (website_clean.startswith("http://") or website_clean.startswith("https://")):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid website_url: URL must start with http:// or https://",
            )

    # 4. Check business_name uniqueness among active tenants (return 409 if exists)
    business_name_clean = tenant_in.business_name.strip()
    existing_tenant = tenant_repo.get_by_business_name(business_name_clean, only_active=True)
    if existing_tenant:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"An active organization with business name '{business_name_clean}' already exists.",
        )

    # 5. Check owner email uniqueness in platform.users (return 409 if exists)
    existing_user = user_repo.get_by_email(owner_email_clean)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A user with email '{owner_email_clean}' already exists.",
        )

    # 6. Team member assignment resolution
    effective_team_member_id: Optional[int] = tenant_in.assigned_team_member_id

    if effective_team_member_id is not None:
        assigned_user = user_repo.get_by_id(effective_team_member_id)
        if not assigned_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Assigned team member ID {effective_team_member_id} does not exist.",
            )
        assigned_role = str(assigned_user.get("role", "")).lower()
        if assigned_role != UserRole.TEAM_MEMBER.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"User ID {effective_team_member_id} has role '{assigned_role}', but must be 'team_member'.",
            )
        if not assigned_user.get("is_active", True):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Assigned team member ID {effective_team_member_id} is inactive.",
            )
    elif current_user.role == UserRole.TEAM_MEMBER:
        # If caller is a team_member and no assignment is given, assign to caller automatically
        effective_team_member_id = current_user.id

    # 7. Generate temporary password server-side and hash with bcrypt
    temp_password = _generate_temp_password(length=14)
    hashed_password = get_password_hash(temp_password)

    # 8. Insert platform.tenants row
    created_tenant = tenant_repo.create(
        business_name=business_name_clean,
        industry=tenant_in.industry.strip(),
        contact_person_name=tenant_in.contact_person_name.strip(),
        contact_email=contact_email_clean,
        phone_number=phone_clean,
        address_line1=tenant_in.address_line1.strip(),
        city=tenant_in.city.strip(),
        state=tenant_in.state.strip(),
        postal_code=tenant_in.postal_code.strip(),
        country=tenant_in.country.strip(),
        address_line2=tenant_in.address_line2.strip() if tenant_in.address_line2 else None,
        website_url=website_clean,
        tax_id=tenant_in.tax_id.strip() if tenant_in.tax_id else None,
        assigned_team_member_id=effective_team_member_id,
        created_by=current_user.id,
    )

    new_tenant_id = int(created_tenant["tenant_id"])

    # 9. Create platform.team_assignments row if assigned
    if effective_team_member_id is not None:
        tenant_repo.create_team_assignment(
            user_id=effective_team_member_id,
            tenant_id=new_tenant_id,
        )

    # 10. Provision SMB Owner login in platform.users (NEVER log the temporary password)
    owner_display_name = tenant_in.contact_person_name.strip() or f"{business_name_clean} Owner"
    ensure_no_active_owner(new_tenant_id, cursor=cursor)
    created_owner = user_repo.create(
        name=owner_display_name,
        email=owner_email_clean,
        password_hash=hashed_password,
        role=UserRole.SMB_OWNER.value,
        tenant_id=new_tenant_id,
    )
    # Safeguard check: re-count active owners; if > 1, deactivate newer and return 409
    check_and_safeguard_single_owner(new_tenant_id, int(created_owner["user_id"]), cursor=cursor)

    # Secure logging without password
    logger.info(
        "Tenant onboarded successfully: tenant_id=%d, business_name='%s', created_by=%d (%s), owner_email='%s', assigned_team_member_id=%s",
        new_tenant_id,
        business_name_clean,
        current_user.id,
        current_user.role.value,
        owner_email_clean,
        str(effective_team_member_id),
    )

    # 11. Return response containing temporary password ONCE
    return TenantOut(
        tenant_id=new_tenant_id,
        business_name=created_tenant.get("business_name", business_name_clean),
        industry=created_tenant.get("industry"),
        contact_person_name=created_tenant.get("contact_person_name"),
        contact_email=created_tenant.get("contact_email", contact_email_clean),
        phone_number=created_tenant.get("phone_number"),
        address_line1=created_tenant.get("address_line1"),
        address_line2=created_tenant.get("address_line2"),
        city=created_tenant.get("city"),
        state=created_tenant.get("state"),
        postal_code=created_tenant.get("postal_code"),
        country=created_tenant.get("country"),
        website_url=created_tenant.get("website_url"),
        tax_id=created_tenant.get("tax_id"),
        assigned_team_member_id=effective_team_member_id,
        created_by=created_tenant.get("created_by", current_user.id),
        created_at=created_tenant.get("created_at"),
        is_active=bool(created_tenant.get("is_active", True)),
        temporary_password=temp_password,
        owner_id=int(created_owner["user_id"]),
        owner_name=owner_display_name,
        owner_email=owner_email_clean,
        owner_phone=phone_clean,
        owner_is_active=True,
    )


@router.get(
    "",
    response_model=List[TenantOut],
    summary="List registered tenants (Admin and Team Members)",
)
def list_tenants(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    cursor: Cursor = Depends(get_db_cursor),
    current_user: UserOut = Depends(get_current_user),
) -> List[TenantOut]:
    """Retrieve tenant organizations list scoped by user role and assignments in SQL."""
    if current_user.role == UserRole.SMB_OWNER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Organization Owners cannot list organizations.",
        )

    role_str = "team_member" if current_user.role == UserRole.TEAM_MEMBER else "admin"
    tenant_repo = TenantRepository(cursor)
    raw_tenants = tenant_repo.list_for_user(
        user_id=current_user.id,
        role=role_str,
        limit=limit,
        offset=offset,
    )
    return [TenantOut(**t) for t in raw_tenants]


@router.get(
    "/assigned",
    response_model=List[TenantOut],
    summary="List assigned organizations for caller",
    include_in_schema=False,
)
def list_assigned_tenants(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    cursor: Cursor = Depends(get_db_cursor),
    current_user: UserOut = Depends(get_current_user),
) -> List[TenantOut]:
    """Single-source alias for list_tenants."""
    return list_tenants(limit=limit, offset=offset, cursor=cursor, current_user=current_user)


@router.get(
    "/{tenant_id}",
    response_model=TenantOut,
    summary="Retrieve tenant details by ID",
)
def get_tenant(
    tenant_id: int,
    cursor: Cursor = Depends(get_db_cursor),
    current_user: UserOut = Depends(get_current_user),
) -> TenantOut:
    """Retrieve full tenant profile by numeric tenant_id with strict role-assignment access check."""
    tenant = _check_tenant_access(tenant_id, current_user, cursor)
    return TenantOut(**tenant)


def _check_tenant_access(tenant_id: int, current_user: UserOut, cursor: Cursor) -> Dict[str, Any]:
    """
    Enforce tenant-level authorization:
      - Admin: authorized for all tenants
      - Team Member: authorized ONLY for assigned tenants (403 if unassigned)
      - SMB Owner: forbidden (403)
      - Returns 404 if tenant does not exist.
    """
    if current_user.role == UserRole.SMB_OWNER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Organization Owners are not authorized to manage organization owners.",
        )

    tenant_repo = TenantRepository(cursor)
    tenant = tenant_repo.get_by_id(tenant_id)
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Organization {tenant_id} not found.",
        )

    if current_user.role == UserRole.TEAM_MEMBER:
        team_repo = TeamRepository(cursor)
        assigned_tenants = team_repo.get_assigned_tenant_ids(current_user.id)
        if tenant_id not in assigned_tenants:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: You are not assigned to manage organization {tenant_id}.",
            )

    return tenant


@router.put(
    "/{tenant_id}/owner",
    response_model=OwnerResponse,
    status_code=status.HTTP_200_OK,
    summary="Edit Tenant SMB Owner",
    description="Update name, email, and phone of the SMB Owner. Email must remain globally unique. Writes an audit trail row.",
)
def edit_tenant_owner(
    tenant_id: int,
    payload: EditOwnerRequest,
    cursor: Cursor = Depends(get_db_cursor),
    current_user: UserOut = Depends(get_current_user),
) -> OwnerResponse:
    """Edit owner profile details for a tenant organization."""
    _check_tenant_access(tenant_id, current_user, cursor)

    user_repo = UserRepository(cursor)
    tenant_repo = TenantRepository(cursor)
    owner = user_repo.get_owner_by_tenant_id(tenant_id)
    if not owner:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No Organization Owner found for organization {tenant_id}.",
        )

    clean_email = str(payload.email).strip().lower()
    clean_name = payload.name.strip()
    clean_phone = payload.phone_number.strip() if payload.phone_number else None

    if not EMAIL_REGEX.match(clean_email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid email format.",
        )

    if clean_phone and not PHONE_REGEX.match(clean_phone):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Phone number must contain only digits, spaces, plus, dash, and parentheses, and be 7-20 characters long.",
        )

    # Check email uniqueness against other users
    existing_user = user_repo.get_by_email(clean_email)
    if existing_user and int(existing_user["user_id"]) != int(owner["user_id"]):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A user with email '{clean_email}' already exists.",
        )

    # Update platform.users and platform.tenants contact info
    user_repo.update_owner_details(
        user_id=owner["user_id"],
        name=clean_name,
        email=clean_email,
        phone_number=clean_phone,
    )
    tenant_repo.update_contact_info(
        tenant_id=tenant_id,
        contact_person_name=clean_name,
        contact_email=clean_email,
        phone_number=clean_phone,
    )

    # Audit trail
    user_repo.write_audit_log(
        actor_user_id=current_user.id,
        actor_role=current_user.role.value,
        action="edit_owner",
        tenant_id=tenant_id,
        reason=f"SMB Owner details updated by {current_user.role.value}",
        details_json=json.dumps({
            "owner_user_id": owner["user_id"],
            "old_email": owner.get("email"),
            "new_email": clean_email,
            "name": clean_name,
        }),
    )

    logger.info(
        "SMB Owner updated: tenant_id=%d, owner_user_id=%d, new_email=%s by actor=%d",
        tenant_id,
        owner["user_id"],
        clean_email,
        current_user.id,
    )

    return OwnerResponse(
        user_id=owner["user_id"],
        tenant_id=tenant_id,
        name=clean_name,
        email=clean_email,
        phone_number=clean_phone,
        is_active=bool(owner.get("is_active", True)),
        role="smb_owner",
        message="SMB Owner details updated successfully.",
    )


@router.post(
    "/{tenant_id}/owner/reset-password",
    response_model=ResetPasswordResponse,
    status_code=status.HTTP_200_OK,
    summary="Reset Tenant SMB Owner Password",
    description="Reset password for the SMB Owner of the tenant using shared reset logic. Returns temporary password once and never logs it.",
)
def reset_tenant_owner_password(
    tenant_id: int,
    cursor: Cursor = Depends(get_db_cursor),
    current_user: UserOut = Depends(get_current_user),
) -> ResetPasswordResponse:
    """Reset password for tenant SMB Owner."""
    _check_tenant_access(tenant_id, current_user, cursor)

    user_repo = UserRepository(cursor)
    owner = user_repo.get_owner_by_tenant_id(tenant_id)
    if not owner:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No Organization Owner found for organization {tenant_id}.",
        )

    return execute_password_reset(
        user_id=int(owner["user_id"]),
        current_user=current_user,
        cursor=cursor,
    )


@router.patch(
    "/{tenant_id}/owner/active",
    response_model=OwnerResponse,
    status_code=status.HTTP_200_OK,
    summary="Activate or Deactivate Tenant SMB Owner",
    description="Toggle active status of the SMB Owner. Reactivating is refused if another active owner exists. Deactivating returns a warning.",
)
def toggle_tenant_owner_active(
    tenant_id: int,
    payload: ToggleOwnerActiveRequest,
    cursor: Cursor = Depends(get_db_cursor),
    current_user: UserOut = Depends(get_current_user),
) -> OwnerResponse:
    """Activate or deactivate the SMB Owner account for a tenant."""
    _check_tenant_access(tenant_id, current_user, cursor)

    user_repo = UserRepository(cursor)
    owner = user_repo.get_owner_by_tenant_id(tenant_id)
    if not owner:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No Organization Owner found for organization {tenant_id}.",
        )

    owner_id = int(owner["user_id"])
    target_active = bool(payload.is_active)
    warning_message = None

    if target_active:
        # Check: refused if another active owner exists
        catalog = settings.DATABRICKS_CATALOG
        conflict_query = f"""
            SELECT user_id, email FROM `{catalog}`.`platform`.`users`
            WHERE tenant_id = :tenant_id 
              AND role = 'smb_owner' 
              AND coalesce(is_active, true) = true 
              AND user_id != :owner_id
            LIMIT 1
        """
        cursor.execute(conflict_query, {"tenant_id": tenant_id, "owner_id": owner_id})
        other_active = cursor.fetchone()
        if other_active:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This organization already has an active owner",
            )
        action_name = "reactivate_owner"
        confirm_msg = "Organization Owner account reactivated successfully."
    else:
        action_name = "deactivate_owner"
        warning_message = "This organization has no active owner until replaced."
        confirm_msg = "Organization Owner account deactivated."

    # Update active status
    user_repo.toggle_user_active(owner_id, target_active)

    # Audit trail
    user_repo.write_audit_log(
        actor_user_id=current_user.id,
        actor_role=current_user.role.value,
        action=action_name,
        tenant_id=tenant_id,
        reason=f"SMB Owner active status set to {target_active} by {current_user.role.value}",
        details_json=json.dumps({
            "owner_user_id": owner_id,
            "is_active": target_active,
            "warning": warning_message,
        }),
    )

    logger.info(
        "SMB Owner active status updated: tenant_id=%d, owner_user_id=%d, is_active=%s by actor=%d",
        tenant_id,
        owner_id,
        target_active,
        current_user.id,
    )

    return OwnerResponse(
        user_id=owner_id,
        tenant_id=tenant_id,
        name=str(owner.get("name", "")),
        email=str(owner.get("email", "")),
        phone_number=owner.get("phone_number"),
        is_active=target_active,
        role="smb_owner",
        warning=warning_message,
        message=confirm_msg,
    )


@router.post(
    "/{tenant_id}/owner/replace",
    response_model=OwnerResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Replace Inactive SMB Owner",
    description="Allowed only when current owner is inactive. Creates new owner with temporary password shown once and must_change_password true.",
)
def replace_tenant_owner(
    tenant_id: int,
    payload: ReplaceOwnerRequest,
    cursor: Cursor = Depends(get_db_cursor),
    current_user: UserOut = Depends(get_current_user),
) -> OwnerResponse:
    """Provision a new SMB Owner for a tenant organization whose current owner is inactive."""
    _check_tenant_access(tenant_id, current_user, cursor)

    # 1. Enforce that NO active owner exists for this tenant
    ensure_no_active_owner(tenant_id, cursor=cursor)

    user_repo = UserRepository(cursor)
    tenant_repo = TenantRepository(cursor)

    clean_email = str(payload.email).strip().lower()
    clean_name = payload.name.strip()
    clean_phone = payload.phone_number.strip() if payload.phone_number else None

    if not EMAIL_REGEX.match(clean_email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid email format.",
        )

    if clean_phone and not PHONE_REGEX.match(clean_phone):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Phone number must contain only digits, spaces, plus, dash, and parentheses, and be 7-20 characters long.",
        )

    # Check email uniqueness across platform.users
    existing_user = user_repo.get_by_email(clean_email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A user with email '{clean_email}' already exists.",
        )

    # Generate high-entropy temporary password (NEVER logged)
    temp_password = _generate_temp_password(14)
    hashed_password = get_password_hash(temp_password)

    # Insert new owner user into platform.users
    new_user = user_repo.create(
        name=clean_name,
        email=clean_email,
        password_hash=hashed_password,
        role=UserRole.SMB_OWNER.value,
        tenant_id=tenant_id,
    )
    new_user_id = int(new_user["user_id"])

    # Ensure must_change_password is true and set phone number
    catalog = settings.DATABRICKS_CATALOG
    update_new_user_sql = f"""
        UPDATE `{catalog}`.`platform`.`users`
        SET phone_number = :phone_number,
            must_change_password = true,
            is_active = true
        WHERE user_id = :user_id
    """
    cursor.execute(update_new_user_sql, {"phone_number": clean_phone, "user_id": new_user_id})

    # Safeguard check: re-count active owners; if > 1, deactivate newer and return 409
    check_and_safeguard_single_owner(tenant_id, new_user_id, cursor=cursor)

    # Update tenant contact info to reflect new owner
    tenant_repo.update_contact_info(
        tenant_id=tenant_id,
        contact_person_name=clean_name,
        contact_email=clean_email,
        phone_number=clean_phone,
    )

    # Audit trail
    user_repo.write_audit_log(
        actor_user_id=current_user.id,
        actor_role=current_user.role.value,
        action="replace_owner",
        tenant_id=tenant_id,
        reason=f"New SMB Owner appointed by {current_user.role.value}",
        details_json=json.dumps({
            "new_owner_user_id": new_user_id,
            "new_email": clean_email,
            "name": clean_name,
        }),
    )

    logger.info(
        "SMB Owner replaced: tenant_id=%d, new_owner_user_id=%d, email=%s by actor=%d",
        tenant_id,
        new_user_id,
        clean_email,
        current_user.id,
    )

    return OwnerResponse(
        user_id=new_user_id,
        tenant_id=tenant_id,
        name=clean_name,
        email=clean_email,
        phone_number=clean_phone,
        is_active=True,
        role="smb_owner",
        temporary_password=temp_password,
        must_change_password=True,
        message="New SMB Owner created successfully. The temporary password will only be shown once.",
    )

