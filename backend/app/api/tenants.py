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

from app.core.dependencies import get_db_cursor, require_team_or_admin
from app.core.security import get_password_hash
from app.repositories.tenant_repository import TenantRepository
from app.repositories.user_repository import UserRepository
from app.schemas.auth import UserOut, UserRole
from app.schemas.tenant import TenantCreate, TenantOut

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
            detail=f"An active tenant with business name '{business_name_clean}' already exists.",
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
    user_repo.create(
        name=owner_display_name,
        email=owner_email_clean,
        password_hash=hashed_password,
        role=UserRole.SMB_OWNER.value,
        tenant_id=new_tenant_id,
    )

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
        owner_email=owner_email_clean,
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
    current_user: UserOut = Depends(require_team_or_admin),
) -> List[TenantOut]:
    """Retrieve tenant organizations list for oversight."""
    tenant_repo = TenantRepository(cursor)
    raw_tenants = tenant_repo.list_all(limit=limit, offset=offset)
    return [TenantOut(**t) for t in raw_tenants]


@router.get(
    "/{tenant_id}",
    response_model=TenantOut,
    summary="Retrieve tenant details by ID",
)
def get_tenant(
    tenant_id: int,
    cursor: Cursor = Depends(get_db_cursor),
    current_user: UserOut = Depends(require_team_or_admin),
) -> TenantOut:
    """Retrieve full tenant profile by numeric tenant_id."""
    tenant_repo = TenantRepository(cursor)
    tenant = tenant_repo.get_by_id(tenant_id)
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant {tenant_id} not found.",
        )
    return TenantOut(**tenant)
