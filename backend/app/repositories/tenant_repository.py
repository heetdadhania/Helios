import logging
import time
from typing import Any, Dict, List, Optional
try:
    from databricks.sql.client import Cursor
except ImportError:
    Cursor = Any  # type: ignore

from app.core.config import settings
from app.db.base import databricks_cursor
from app.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class TenantRepository(BaseRepository):
    """
    Data access repository for platform.tenants stored in Databricks Unity Catalog.
    
    Manages tenant records, extended onboarding details, and team member assignments.
    """

    def __init__(self, cursor: Optional[Cursor] = None, catalog: Optional[str] = None) -> None:
        super().__init__(cursor)
        self.catalog = catalog or settings.DATABRICKS_CATALOG
        self.table = f"`{self.catalog}`.`platform`.`tenants`"
        self.team_assignments_table = f"`{self.catalog}`.`platform`.`team_assignments`"
        self.users_table = f"`{self.catalog}`.`platform`.`users`"

    def _attach_owners(self, tenants: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Attach current SMB owner profile and active status to tenant dictionaries."""
        if not tenants:
            return tenants
        tenant_ids = [int(t["tenant_id"]) for t in tenants if t.get("tenant_id") is not None]
        if not tenant_ids:
            return tenants

        id_str = ",".join(str(i) for i in tenant_ids)
        query = f"""
            SELECT user_id, tenant_id, name, email, phone_number, coalesce(is_active, true) as is_active
            FROM {self.users_table}
            WHERE tenant_id IN ({id_str}) AND role = 'smb_owner'
            ORDER BY is_active DESC, user_id DESC
        """
        try:
            rows = self.execute_query(query)
            owner_map: Dict[int, Dict[str, Any]] = {}
            for r in rows:
                tid = int(r["tenant_id"])
                if tid not in owner_map:
                    owner_map[tid] = r
                elif not owner_map[tid].get("is_active") and r.get("is_active"):
                    owner_map[tid] = r

            for t in tenants:
                tid = int(t["tenant_id"])
                o = owner_map.get(tid)
                if o:
                    t["owner_id"] = o.get("user_id")
                    t["owner_name"] = o.get("name")
                    t["owner_email"] = o.get("email")
                    t["owner_phone"] = o.get("phone_number")
                    t["owner_is_active"] = bool(o.get("is_active", True))
                else:
                    t["owner_id"] = None
                    t["owner_name"] = None
                    t["owner_email"] = None
                    t["owner_phone"] = None
                    t["owner_is_active"] = False
        except Exception as exc:
            logger.warning("Could not attach owner info to tenants: %s", exc)
        return tenants

    def get_by_id(
        self,
        tenant_id: int,
        max_retries: int = 3,
        base_backoff: float = 1.0,
    ) -> Optional[Dict[str, Any]]:
        """Fetch tenant record by primary key tenant_id with retry-with-backoff."""
        query = f"SELECT * FROM {self.table} WHERE tenant_id = :tenant_id LIMIT 1"
        parameters = {"tenant_id": tenant_id}

        last_exception = None
        for attempt in range(1, max_retries + 1):
            try:
                if attempt == 1 and self.cursor is not None:
                    res = self.execute_single(query, parameters)
                    return self._attach_owners([res])[0] if res else None

                with databricks_cursor(catalog=self.catalog) as fresh_cursor:
                    repo = BaseRepository(fresh_cursor)
                    res = repo.execute_single(query, parameters)
                    if not res:
                        return None
                    # Use fresh cursor to attach owner
                    tenant_repo = TenantRepository(fresh_cursor, catalog=self.catalog)
                    return tenant_repo._attach_owners([res])[0]
            except Exception as exc:
                last_exception = exc
                if attempt < max_retries:
                    backoff = base_backoff * (2 ** (attempt - 1))
                    logger.warning(
                        "Transient error fetching tenant by ID [tenant_id=%d] on attempt %d/%d: %s. Retrying in %.1fs...",
                        tenant_id,
                        attempt,
                        max_retries,
                        exc,
                        backoff,
                    )
                    time.sleep(backoff)
                else:
                    logger.error("Failed fetching tenant [tenant_id=%d]: %s", tenant_id, exc)
                    raise exc

        if last_exception:
            raise last_exception
        return None

    def get_by_business_name(
        self,
        business_name: str,
        only_active: bool = True,
        max_retries: int = 3,
        base_backoff: float = 1.0,
    ) -> Optional[Dict[str, Any]]:
        """Fetch tenant record by business name (case-insensitive lookup)."""
        clean_name = business_name.strip().lower()
        if only_active:
            query = f"SELECT * FROM {self.table} WHERE lower(business_name) = :name AND is_active = true LIMIT 1"
        else:
            query = f"SELECT * FROM {self.table} WHERE lower(business_name) = :name LIMIT 1"
        parameters = {"name": clean_name}

        last_exception = None
        for attempt in range(1, max_retries + 1):
            try:
                if attempt == 1 and self.cursor is not None:
                    return self.execute_single(query, parameters)

                with databricks_cursor(catalog=self.catalog) as fresh_cursor:
                    repo = BaseRepository(fresh_cursor)
                    return repo.execute_single(query, parameters)
            except Exception as exc:
                last_exception = exc
                if attempt < max_retries:
                    time.sleep(base_backoff * (2 ** (attempt - 1)))
                else:
                    raise exc

        if last_exception:
            raise last_exception
        return None

    def get_by_slug(self, slug: str) -> Optional[Dict[str, Any]]:
        """Backwards compatibility helper: Fetch tenant by slug or business_name."""
        clean = slug.strip().lower()
        # Try business_name match
        match = self.get_by_business_name(clean, only_active=False)
        if match:
            return match
        query = f"SELECT * FROM {self.table} WHERE lower(business_name) LIKE :pattern LIMIT 1"
        return self.execute_single(query, {"pattern": f"%{clean}%"})

    def list_all(
        self,
        limit: int = 100,
        offset: int = 0,
        is_active: Optional[bool] = None,
    ) -> List[Dict[str, Any]]:
        """Retrieve paginated list of tenant records from platform.tenants."""
        if is_active is not None:
            query = f"""
                SELECT * FROM {self.table}
                WHERE is_active = :is_active
                ORDER BY tenant_id ASC
                LIMIT :limit OFFSET :offset
            """
            raw = self.execute_query(query, {"is_active": is_active, "limit": limit, "offset": offset})
            return self._attach_owners(raw)

        query = f"""
            SELECT * FROM {self.table}
            ORDER BY tenant_id ASC
            LIMIT :limit OFFSET :offset
        """
        raw = self.execute_query(query, {"limit": limit, "offset": offset})
        return self._attach_owners(raw)

    def list_for_user(
        self,
        user_id: int,
        role: str,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve organizations scoped by caller role directly in SQL:
          - admin: all organizations
          - team_member: active organizations assigned via platform.team_assignments
        Always ordered ascending by tenant_id.
        """
        if role == "team_member":
            query = f"""
                SELECT t.* FROM {self.table} t
                INNER JOIN {self.team_assignments_table} ta ON t.tenant_id = ta.tenant_id
                WHERE ta.user_id = :user_id AND coalesce(t.is_active, true) = true
                ORDER BY t.tenant_id ASC
                LIMIT :limit OFFSET :offset
            """
            raw = self.execute_query(query, {"user_id": user_id, "limit": limit, "offset": offset})
            return self._attach_owners(raw)

        # Admin: all organizations
        query = f"""
            SELECT * FROM {self.table}
            ORDER BY tenant_id ASC
            LIMIT :limit OFFSET :offset
        """
        raw = self.execute_query(query, {"limit": limit, "offset": offset})
        return self._attach_owners(raw)

    def update_contact_info(
        self,
        tenant_id: int,
        contact_person_name: str,
        contact_email: str,
        phone_number: str,
    ) -> None:
        """Update contact fields on platform.tenants."""
        query = f"""
            UPDATE {self.table}
            SET contact_person_name = :name,
                contact_email = :email,
                phone_number = :phone
            WHERE tenant_id = :tenant_id
        """
        self.execute_non_query(
            query,
            {
                "tenant_id": int(tenant_id),
                "name": contact_person_name.strip(),
                "email": contact_email.strip().lower(),
                "phone": phone_number.strip(),
            },
        )

    def create(
        self,
        business_name: str,
        industry: str,
        contact_person_name: str,
        contact_email: str,
        phone_number: str,
        address_line1: str,
        city: str,
        state: str,
        postal_code: str,
        country: str,
        address_line2: Optional[str] = None,
        website_url: Optional[str] = None,
        tax_id: Optional[str] = None,
        assigned_team_member_id: Optional[int] = None,
        created_by: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Insert a complete new tenant entry into platform.tenants Delta table and return the created record.
        """
        clean_name = business_name.strip()
        clean_email = contact_email.strip().lower()

        insert_query = f"""
            INSERT INTO {self.table} (
                business_name,
                industry,
                contact_person_name,
                contact_email,
                phone_number,
                address_line1,
                address_line2,
                city,
                state,
                postal_code,
                country,
                website_url,
                tax_id,
                assigned_team_member_id,
                created_by,
                created_at,
                is_active
            ) VALUES (
                :business_name,
                :industry,
                :contact_person_name,
                :contact_email,
                :phone_number,
                :address_line1,
                :address_line2,
                :city,
                :state,
                :postal_code,
                :country,
                :website_url,
                :tax_id,
                :assigned_team_member_id,
                :created_by,
                current_timestamp(),
                true
            )
        """
        self.execute_non_query(
            insert_query,
            {
                "business_name": clean_name,
                "industry": industry.strip(),
                "contact_person_name": contact_person_name.strip(),
                "contact_email": clean_email,
                "phone_number": phone_number.strip(),
                "address_line1": address_line1.strip(),
                "address_line2": address_line2.strip() if address_line2 else None,
                "city": city.strip(),
                "state": state.strip(),
                "postal_code": postal_code.strip(),
                "country": country.strip(),
                "website_url": website_url.strip() if website_url else None,
                "tax_id": tax_id.strip() if tax_id else None,
                "assigned_team_member_id": assigned_team_member_id,
                "created_by": created_by,
            },
        )

        # Retrieve the newly generated tenant record
        created = self.get_by_business_name(clean_name, only_active=True)
        if not created:
            # Fallback by email
            query = f"SELECT * FROM {self.table} WHERE lower(contact_email) = :email ORDER BY tenant_id DESC LIMIT 1"
            created = self.execute_single(query, {"email": clean_email})

        if not created:
            raise RuntimeError(f"Tenant creation verification failed for {clean_name}")

        return created

    def create_team_assignment(self, user_id: int, tenant_id: int) -> None:
        """
        Record a team member assignment to a tenant in platform.team_assignments.
        Idempotent: skips if assignment already exists.
        """
        check_query = f"""
            SELECT 1 FROM {self.team_assignments_table}
            WHERE user_id = :user_id AND tenant_id = :tenant_id
            LIMIT 1
        """
        exists = self.execute_single(check_query, {"user_id": user_id, "tenant_id": tenant_id})
        if not exists:
            insert_query = f"""
                INSERT INTO {self.team_assignments_table} (user_id, tenant_id, assigned_at)
                VALUES (:user_id, :tenant_id, current_timestamp())
            """
            self.execute_non_query(insert_query, {"user_id": user_id, "tenant_id": tenant_id})
