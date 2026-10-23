import json
import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from databricks.sql.client import Cursor

from app.core.config import settings
from app.core.dependencies import get_current_user, get_db_cursor
from app.repositories.base import BaseRepository
from app.repositories.notification_repository import NotificationRepository
from app.repositories.user_repository import UserRepository
from app.schemas.auth import UserOut, UserRole
from app.schemas.profile import (
    AdminContact,
    AdminProfileResponse,
    AssignedOrgSummary,
    OrganizationProfile,
    OwnerProfileResponse,
    PlatformSummary,
    ProfileResponse,
    ProfileUpdateEmail,
    ProfileUpdateMe,
    ProfileUpdateOrganization,
    TeamMemberContact,
    TeamMemberProfileResponse,
    TeamMemberSummary,
    UserMe,
)
from app.services.auth_service import AuthService

logger = logging.getLogger(__name__)

router = APIRouter()


def _format_dt(val: Any) -> Optional[str]:
    if val is None:
        return None
    if hasattr(val, "isoformat"):
        return val.isoformat()
    return str(val)


def _get_admin_contact(repo: BaseRepository, catalog: str) -> Optional[AdminContact]:
    """Fetch the first active admin contact."""
    query = f"""
        SELECT name, email, phone_number
        FROM `{catalog}`.`platform`.`users`
        WHERE lower(role) = 'admin' AND coalesce(is_active, true) = true
        ORDER BY user_id ASC
        LIMIT 1
    """
    row = repo.execute_single(query)
    if not row:
        return None
    return AdminContact(
        name=row["name"],
        email=row["email"],
        phone=row.get("phone_number"),
    )


@router.get(
    "/me",
    response_model=ProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Detailed Current User Profile",
    description="Retrieve role-specific profile details for the authenticated user without security columns.",
)
def get_profile_me(
    current_user: UserOut = Depends(get_current_user),
    cursor: Cursor = Depends(get_db_cursor),
) -> ProfileResponse:
    catalog = settings.DATABRICKS_CATALOG
    base_repo = BaseRepository(cursor)
    user_repo = UserRepository(cursor, catalog=catalog)

    # Fetch full user row (without returning security columns to client)
    user_record = user_repo.get_by_id(current_user.id)
    if not user_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User account record not found.",
        )

    user_me = UserMe(
        name=str(user_record.get("name") or ""),
        email=str(user_record.get("email") or ""),
        phone=user_record.get("phone_number"),
        last_login=_format_dt(user_record.get("last_login_at")),
        staff_id=user_record.get("staff_id"),
        designation=user_record.get("designation"),
    )

    admin_contact = _get_admin_contact(base_repo, catalog)

    # 1. Organization Owner (smb_owner)
    if current_user.role == UserRole.SMB_OWNER:
        tenant_id = current_user.tenant_id
        org_profile: Optional[OrganizationProfile] = None
        assigned_tm: Optional[TeamMemberContact] = None

        if tenant_id is not None:
            # Query tenant details
            tenant_q = f"""
                SELECT 
                    tenant_id,
                    business_name,
                    industry,
                    contact_email,
                    contact_person_name,
                    phone_number,
                    address_line1,
                    address_line2,
                    city,
                    state,
                    postal_code,
                    country,
                    website_url,
                    tax_id,
                    created_at
                FROM `{catalog}`.`platform`.`tenants`
                WHERE tenant_id = :tenant_id
                LIMIT 1
            """
            t_row = base_repo.execute_single(tenant_q, {"tenant_id": tenant_id})
            if t_row:
                addr_parts = [
                    t_row.get("address_line1"),
                    t_row.get("address_line2"),
                    t_row.get("city"),
                    t_row.get("state"),
                    t_row.get("postal_code"),
                    t_row.get("country"),
                ]
                full_address = ", ".join(p.strip() for p in addr_parts if p and p.strip()) or None

                org_profile = OrganizationProfile(
                    business_name=t_row.get("business_name") or "",
                    industry=t_row.get("industry"),
                    contact_person=t_row.get("contact_person_name"),
                    contact_email=t_row.get("contact_email"),
                    phone=t_row.get("phone_number"),
                    full_address=full_address,
                    address_line1=t_row.get("address_line1"),
                    address_line2=t_row.get("address_line2"),
                    city=t_row.get("city"),
                    state=t_row.get("state"),
                    pin_code=t_row.get("postal_code"),
                    website=t_row.get("website_url"),
                    gstin=t_row.get("tax_id"),
                    created_date=_format_dt(t_row.get("created_at")),
                )

            # Query assigned team member for this tenant
            tm_q = f"""
                SELECT u.name, u.email, u.phone_number, u.designation
                FROM `{catalog}`.`platform`.`team_assignments` ta
                INNER JOIN `{catalog}`.`platform`.`users` u ON ta.user_id = u.user_id
                WHERE ta.tenant_id = :tenant_id AND coalesce(u.is_active, true) = true
                ORDER BY ta.assigned_at DESC
                LIMIT 1
            """
            tm_row = base_repo.execute_single(tm_q, {"tenant_id": tenant_id})
            if tm_row:
                assigned_tm = TeamMemberContact(
                    name=tm_row["name"],
                    email=tm_row["email"],
                    phone=tm_row.get("phone_number"),
                    designation=tm_row.get("designation"),
                )

        return OwnerProfileResponse(
            role="smb_owner",
            me=user_me,
            organization=org_profile,
            assigned_team_member=assigned_tm,
            admin_contact=admin_contact,
        )

    # 2. Operations Team Member (team_member)
    elif current_user.role == UserRole.TEAM_MEMBER:
        # Query assigned organizations strictly from team_assignments
        orgs_q = f"""
            SELECT 
                t.tenant_id,
                t.business_name,
                t.industry,
                t.city,
                t.state,
                t.contact_person_name,
                max(d.full_date) AS gold_max_date,
                cast(max(ps.created_at) AS date) AS ps_max_date
            FROM `{catalog}`.`platform`.`team_assignments` ta
            INNER JOIN `{catalog}`.`platform`.`tenants` t ON ta.tenant_id = t.tenant_id
            LEFT JOIN `{catalog}`.`gold`.`fact_orders_daily_summary` s ON t.tenant_id = s.tenant_id
            LEFT JOIN `{catalog}`.`gold`.`dim_date` d ON s.date_id = d.date_id
            LEFT JOIN `{catalog}`.`platform`.`pipeline_status` ps ON t.tenant_id = ps.tenant_id
            WHERE ta.user_id = :user_id
            GROUP BY 
                t.tenant_id,
                t.business_name,
                t.industry,
                t.city,
                t.state,
                t.contact_person_name
            ORDER BY t.business_name ASC
        """
        org_rows = base_repo.execute_query(orgs_q, {"user_id": current_user.id})

        assigned_orgs: List[AssignedOrgSummary] = []
        if org_rows:
            # Query owner contacts for these tenants
            t_ids = [str(r["tenant_id"]) for r in org_rows if r.get("tenant_id") is not None]
            owners_map: Dict[int, Dict[str, Any]] = {}
            if t_ids:
                id_str = ",".join(t_ids)
                owners_q = f"""
                    SELECT user_id, tenant_id, name, email, phone_number, coalesce(is_active, true) as is_active
                    FROM `{catalog}`.`platform`.`users`
                    WHERE tenant_id IN ({id_str}) AND lower(role) = 'smb_owner'
                    ORDER BY is_active DESC, user_id DESC
                """
                owner_rows = base_repo.execute_query(owners_q)
                for o in owner_rows:
                    tid = int(o["tenant_id"])
                    if tid not in owners_map:
                        owners_map[tid] = o
                    elif not owners_map[tid].get("is_active") and o.get("is_active"):
                        owners_map[tid] = o

            for r in org_rows:
                tid = int(r["tenant_id"])
                owner_data = owners_map.get(tid, {})
                last_date = r.get("gold_max_date") or r.get("ps_max_date")

                assigned_orgs.append(
                    AssignedOrgSummary(
                        tenant_id=tid,
                        business_name=r.get("business_name") or f"Organization #{tid}",
                        industry=r.get("industry"),
                        city=r.get("city"),
                        state=r.get("state"),
                        contact_person=r.get("contact_person_name"),
                        owner_name=owner_data.get("name"),
                        owner_email=owner_data.get("email"),
                        owner_phone=owner_data.get("phone_number"),
                        last_data_date=_format_dt(last_date),
                    )
                )

        return TeamMemberProfileResponse(
            role="team_member",
            me=user_me,
            assigned_organizations=assigned_orgs,
            admin_contact=admin_contact,
        )

    # 3. Platform Administrator (admin)
    elif current_user.role == UserRole.ADMIN:
        # Platform summary counts
        counts_q = f"""
            SELECT
                (SELECT count(*) FROM `{catalog}`.`platform`.`tenants` WHERE coalesce(is_active, true) = true) AS active_orgs,
                (SELECT count(*) FROM `{catalog}`.`platform`.`users` WHERE lower(role) = 'smb_owner' AND coalesce(is_active, true) = true) AS active_owners,
                (SELECT count(*) FROM `{catalog}`.`platform`.`users` WHERE lower(role) = 'team_member' AND coalesce(is_active, true) = true) AS active_tms
        """
        counts_row = base_repo.execute_single(counts_q) or {}
        platform_summary = PlatformSummary(
            active_organizations=int(counts_row.get("active_orgs") or 0),
            active_owners=int(counts_row.get("active_owners") or 0),
            active_team_members=int(counts_row.get("active_tms") or 0),
        )

        # Team members list with assigned org counts
        tm_list_q = f"""
            SELECT 
                u.user_id,
                u.name,
                u.email,
                u.phone_number,
                u.designation,
                count(ta.tenant_id) AS assigned_count
            FROM `{catalog}`.`platform`.`users` u
            LEFT JOIN `{catalog}`.`platform`.`team_assignments` ta ON u.user_id = ta.user_id
            WHERE lower(u.role) = 'team_member'
            GROUP BY u.user_id, u.name, u.email, u.phone_number, u.designation
            ORDER BY u.name ASC
        """
        tm_rows = base_repo.execute_query(tm_list_q)
        team_members = [
            TeamMemberSummary(
                user_id=int(r["user_id"]),
                name=r["name"],
                email=r["email"],
                phone=r.get("phone_number"),
                designation=r.get("designation"),
                assigned_organizations_count=int(r.get("assigned_count") or 0),
            )
            for r in tm_rows
        ]

        return AdminProfileResponse(
            role="admin",
            me=user_me,
            platform_summary=platform_summary,
            team_members=team_members,
        )

    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Role not permitted to access profile service.",
        )


@router.patch(
    "/me",
    response_model=ProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="Update Current User Profile",
    description="Update profile fields (name, phone) for the authenticated user. Forbidden fields are rejected with 422.",
)
def update_profile_me(
    payload: ProfileUpdateMe,
    current_user: UserOut = Depends(get_current_user),
    cursor: Cursor = Depends(get_db_cursor),
) -> ProfileResponse:
    catalog = settings.DATABRICKS_CATALOG
    base_repo = BaseRepository(cursor)
    user_repo = UserRepository(cursor, catalog=catalog)

    user_record = user_repo.get_by_id(current_user.id)
    if not user_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User account record not found.",
        )

    old_name = user_record.get("name")
    old_phone = user_record.get("phone_number")

    updates: Dict[str, Any] = {}
    changes: Dict[str, Any] = {}

    if payload.name is not None and payload.name != old_name:
        updates["name"] = payload.name
        changes["name"] = {"old": old_name, "new": payload.name}

    if payload.phone is not None and payload.phone != old_phone:
        updates["phone_number"] = payload.phone
        changes["phone"] = {"old": old_phone, "new": payload.phone}

    if updates:
        set_clauses = [f"{col} = :{col}" for col in updates.keys()]
        set_clauses.append("updated_at = current_timestamp()")
        sql = f"""
            UPDATE `{catalog}`.`platform`.`users`
            SET {', '.join(set_clauses)}
            WHERE user_id = :user_id
        """
        params = {**updates, "user_id": current_user.id}
        base_repo.execute_non_query(sql, params)

        user_repo.write_audit_log(
            actor_user_id=current_user.id,
            actor_role=current_user.role.value,
            action="profile_updated",
            tenant_id=current_user.tenant_id,
            reason="User updated personal profile details",
            details_json=json.dumps(changes),
        )

    return get_profile_me(current_user=current_user, cursor=cursor)


@router.patch(
    "/me/email",
    response_model=ProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="Update Current User Email",
    description="Update user email with current password verification and global uniqueness check.",
)
def update_profile_email(
    payload: ProfileUpdateEmail,
    current_user: UserOut = Depends(get_current_user),
    cursor: Cursor = Depends(get_db_cursor),
) -> ProfileResponse:
    catalog = settings.DATABRICKS_CATALOG
    base_repo = BaseRepository(cursor)
    user_repo = UserRepository(cursor, catalog=catalog)

    user_record = user_repo.get_by_id(current_user.id)
    if not user_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User account record not found.",
        )

    current_hash = user_record.get("password_hash")
    if not current_hash or not AuthService.verify_password(payload.current_password, current_hash):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Incorrect password.",
        )

    old_email = user_record.get("email")
    new_email = payload.new_email.strip().lower()

    if old_email != new_email:
        # Check global uniqueness
        existing_user = user_repo.get_by_email(new_email)
        if existing_user and int(existing_user.get("user_id") or 0) != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This email is already in use.",
            )

        sql = f"""
            UPDATE `{catalog}`.`platform`.`users`
            SET email = :email, updated_at = current_timestamp()
            WHERE user_id = :user_id
        """
        base_repo.execute_non_query(sql, {"email": new_email, "user_id": current_user.id})

        user_repo.write_audit_log(
            actor_user_id=current_user.id,
            actor_role=current_user.role.value,
            action="email_changed",
            tenant_id=current_user.tenant_id,
            reason="User updated account email",
            details_json=json.dumps({"email": {"old": old_email, "new": new_email}}),
        )

    return get_profile_me(current_user=current_user, cursor=cursor)


@router.patch(
    "/me/organization",
    response_model=ProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="Update Organization Profile Details",
    description="Update organization contact details for SMB Owner. Organization is identified strictly by user token tenant_id.",
)
def update_profile_organization(
    payload: ProfileUpdateOrganization,
    current_user: UserOut = Depends(get_current_user),
    cursor: Cursor = Depends(get_db_cursor),
) -> ProfileResponse:
    if current_user.role != UserRole.SMB_OWNER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Organization Owners can update organization details.",
        )

    if current_user.tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No organization associated with this account.",
        )

    catalog = settings.DATABRICKS_CATALOG
    base_repo = BaseRepository(cursor)
    user_repo = UserRepository(cursor, catalog=catalog)

    tenant_q = f"""
        SELECT 
            tenant_id,
            business_name,
            contact_person_name,
            phone_number,
            address_line1,
            address_line2,
            city,
            state,
            postal_code,
            website_url,
            tax_id
        FROM `{catalog}`.`platform`.`tenants`
        WHERE tenant_id = :tenant_id
        LIMIT 1
    """
    curr_tenant = base_repo.execute_single(tenant_q, {"tenant_id": current_user.tenant_id})
    if not curr_tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization record not found.",
        )

    field_mappings = {
        "contact_person_name": "contact_person_name",
        "phone_number": "phone_number",
        "address_line1": "address_line1",
        "address_line2": "address_line2",
        "city": "city",
        "state": "state",
        "postal_code": "postal_code",
        "website_url": "website_url",
        "tax_id": "tax_id",
    }

    updates: Dict[str, Any] = {}
    changes: Dict[str, Any] = {}

    for field, col in field_mappings.items():
        val = getattr(payload, field, None)
        if val is not None:
            old_val = curr_tenant.get(col)
            if val != old_val:
                updates[col] = val
                changes[field] = {"old": old_val, "new": val}

    if updates:
        set_clauses = [f"{col} = :{col}" for col in updates.keys()]
        set_clauses.append("updated_at = current_timestamp()")
        update_q = f"""
            UPDATE `{catalog}`.`platform`.`tenants`
            SET {', '.join(set_clauses)}
            WHERE tenant_id = :tenant_id
        """
        params = {**updates, "tenant_id": current_user.tenant_id}
        base_repo.execute_non_query(update_q, params)

        user_repo.write_audit_log(
            actor_user_id=current_user.id,
            actor_role=current_user.role.value,
            action="organization_details_updated",
            tenant_id=current_user.tenant_id,
            reason="Organization Owner updated organization contact details",
            details_json=json.dumps(changes),
        )

        # Notify assigned team member
        try:
            tm_q = f"""
                SELECT u.user_id
                FROM `{catalog}`.`platform`.`team_assignments` ta
                INNER JOIN `{catalog}`.`platform`.`users` u ON ta.user_id = u.user_id
                WHERE ta.tenant_id = :tenant_id AND coalesce(u.is_active, true) = true
                ORDER BY ta.assigned_at DESC
                LIMIT 1
            """
            tm_row = base_repo.execute_single(tm_q, {"tenant_id": current_user.tenant_id})
            assigned_tm_id = int(tm_row["user_id"]) if tm_row else None

            notif_repo = NotificationRepository(cursor, catalog=catalog)
            biz_name = curr_tenant.get("business_name") or f"Organization #{current_user.tenant_id}"
            notif_repo.create(
                message=f"{biz_name} updated its contact details",
                type="info",
                tenant_id=current_user.tenant_id,
                user_id=assigned_tm_id,
            )
        except Exception as exc:
            logger.warning("Failed to create notification for assigned team member: %s", exc)

    return get_profile_me(current_user=current_user, cursor=cursor)
