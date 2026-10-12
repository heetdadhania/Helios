import logging
from typing import Any, Dict, List, Optional
try:
    from databricks.sql.client import Cursor
except ImportError:
    Cursor = Any  # type: ignore

from app.core.config import settings

logger = logging.getLogger("helios.repositories.data_quality")


class DataQualityRepository:
    """Repository accessing meta.data_quality_log with multi-tenant access controls."""

    def __init__(self, cursor: Cursor, catalog: Optional[str] = None) -> None:
        self.cursor = cursor
        self.catalog = catalog or settings.DATABRICKS_CATALOG
        self.dq_table = f"`{self.catalog}`.`meta`.`data_quality_log`"
        self.tenants_table = f"`{self.catalog}`.`platform`.`tenants`"
        self.assignments_table = f"`{self.catalog}`.`platform`.`team_assignments`"

    def get_assigned_tenant_ids(self, user_id: int) -> List[int]:
        """Fetch tenant IDs assigned to an operations team member."""
        query = f"SELECT tenant_id FROM {self.assignments_table} WHERE user_id = :user_id"
        self.cursor.execute(query, {"user_id": user_id})
        return [int(row[0]) for row in self.cursor.fetchall() or []]

    def list_logs(
        self,
        user_id: int,
        user_role: str,
        tenant_filter: Optional[str] = None,
        batch_filter: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Retrieve rejected data quality logs scoped by RBAC and optional filters."""
        where_clauses: List[str] = []
        params: Dict[str, Any] = {"limit": limit}

        if user_role == "team_member":
            assigned = self.get_assigned_tenant_ids(user_id)
            if not assigned:
                return []
            assigned_placeholders = ", ".join(f":assign_{i}" for i in range(len(assigned)))
            where_clauses.append(f"d.tenant_id IN ({assigned_placeholders})")
            for i, aid in enumerate(assigned):
                params[f"assign_{i}"] = aid

        if tenant_filter and tenant_filter.strip() and tenant_filter.lower() != "all":
            clean_tf = tenant_filter.strip()
            if clean_tf.isdigit():
                where_clauses.append("d.tenant_id = :tenant_id_filter")
                params["tenant_id_filter"] = int(clean_tf)
            else:
                where_clauses.append("lower(t.business_name) = :tenant_name_filter")
                params["tenant_name_filter"] = clean_tf.lower()

        if batch_filter and batch_filter.strip():
            where_clauses.append("d.batch_id = :batch_filter")
            params["batch_filter"] = batch_filter.strip()

        where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

        query = f"""
            SELECT
                d.log_id,
                d.batch_id,
                d.tenant_id,
                coalesce(t.business_name, concat('Tenant #', cast(d.tenant_id AS STRING))) AS tenant_name,
                d.table_name,
                d.rejection_reason,
                d.logged_at
            FROM {self.dq_table} d
            LEFT JOIN {self.tenants_table} t ON d.tenant_id = t.tenant_id
            {where_sql}
            ORDER BY d.logged_at DESC
            LIMIT :limit
        """

        self.cursor.execute(query, params)
        rows = self.cursor.fetchall() or []

        results: List[Dict[str, Any]] = []
        for r in rows:
            reason = str(r[5] or "")
            reason_lower = reason.lower()
            if "drift" in reason_lower or "template" in reason_lower:
                category = "Schema Drift"
            elif "null" in reason_lower:
                category = "Null Threshold Exceeded"
            elif "type" in reason_lower or "currency" in reason_lower or "date" in reason_lower or "format" in reason_lower:
                category = "Type Mismatch"
            elif "duplicate" in reason_lower or "key" in reason_lower or "constraint" in reason_lower:
                category = "Duplicate Key"
            else:
                category = "Schema Drift"

            logged_at_val = r[6]
            iso_timestamp = logged_at_val.isoformat() if hasattr(logged_at_val, "isoformat") else str(logged_at_val)

            results.append({
                "id": f"dql-{r[0]}",
                "batch_id": str(r[1]),
                "tenant_id": str(r[2]),
                "tenant_name": str(r[3]),
                "table_name": str(r[4]),
                "rejection_reason": reason,
                "timestamp": iso_timestamp,
                "error_category": category,
            })

        return results
