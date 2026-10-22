import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from databricks.sql.client import Cursor

from app.core.config import settings
from app.core.dependencies import get_current_user, get_db_cursor
from app.repositories.base import BaseRepository
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
    TeamMemberContact,
    TeamMemberProfileResponse,
    TeamMemberSummary,
    UserMe,
)

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
