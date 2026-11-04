import csv
import io
import json
import logging
from typing import Any, Dict, List, Optional, Tuple
try:
    from databricks.sql.client import Cursor
except ImportError:
    Cursor = Any  # type: ignore

from fastapi import HTTPException, status
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
        self.pipeline_table = f"`{self.catalog}`.`platform`.`pipeline_status`"
        self.bronze_orders_table = f"`{self.catalog}`.`bronze`.`raw_orders`"
        self.bronze_shipping_table = f"`{self.catalog}`.`bronze`.`raw_shipping`"

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
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Retrieve rejected data quality logs scoped by RBAC and optional filters with pagination."""
        where_clauses: List[str] = []
        params: Dict[str, Any] = {}

        if user_role == "team_member":
            assigned = self.get_assigned_tenant_ids(user_id)
            if not assigned:
                return [], 0
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

        count_query = f"""
            SELECT COUNT(*) AS total
            FROM {self.dq_table} d
            LEFT JOIN {self.tenants_table} t ON d.tenant_id = t.tenant_id
            {where_sql}
        """
        self.cursor.execute(count_query, params)
        count_row = self.cursor.fetchone()
        total = int(count_row[0]) if count_row and count_row[0] is not None else 0

        offset = max(0, (page - 1) * page_size)
        item_params = {**params, "limit": page_size, "offset": offset}

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
            LIMIT :limit OFFSET :offset
        """

        self.cursor.execute(query, item_params)
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

        if total == 0 and len(results) > 0:
            total = len(results)
        return results, total

    def get_rejected_rows_csv(self, batch_id: str, user_id: int, user_role: str) -> str:
        """
        Build and return a UTF-8 CSV string (with BOM) containing the original row content
        and rejection reason for rows excluded in Silver for the given batch.
        RBAC:
          - team_member: allowed only for assigned organizations, strictly enforced in the query.
          - admin: allowed for all organizations.
        """
        # 1. Resolve batch existence and tenant_id
        q_batch = f"SELECT tenant_id FROM {self.pipeline_table} WHERE batch_id = :batch_id LIMIT 1"
        self.cursor.execute(q_batch, {"batch_id": batch_id})
        batch_row = self.cursor.fetchone()
        tenant_id: Optional[int] = None
        if batch_row and batch_row[0] is not None:
            tenant_id = int(batch_row[0])
        else:
            q_dq = f"SELECT tenant_id FROM {self.dq_table} WHERE batch_id = :batch_id LIMIT 1"
            self.cursor.execute(q_dq, {"batch_id": batch_id})
            dq_b_row = self.cursor.fetchone()
            if dq_b_row and dq_b_row[0] is not None:
                tenant_id = int(dq_b_row[0])
            else:
                q_bo = f"SELECT tenant_id FROM {self.bronze_orders_table} WHERE batch_id = :batch_id LIMIT 1"
                self.cursor.execute(q_bo, {"batch_id": batch_id})
                bo_b_row = self.cursor.fetchone()
                if bo_b_row and bo_b_row[0] is not None:
                    tenant_id = int(bo_b_row[0])
                else:
                    q_bs = f"SELECT tenant_id FROM {self.bronze_shipping_table} WHERE batch_id = :batch_id LIMIT 1"
                    self.cursor.execute(q_bs, {"batch_id": batch_id})
                    bs_b_row = self.cursor.fetchone()
                    if bs_b_row and bs_b_row[0] is not None:
                        tenant_id = int(bs_b_row[0])

        if tenant_id is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Batch '{batch_id}' not found.",
            )

        # 2. RBAC validation: For team_member, verify assignment to tenant_id
        if user_role == "team_member":
            q_access = f"SELECT 1 FROM {self.assignments_table} WHERE user_id = :user_id AND tenant_id = :tenant_id LIMIT 1"
            self.cursor.execute(q_access, {"user_id": user_id, "tenant_id": tenant_id})
            if not self.cursor.fetchone():
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Access denied: You are not assigned to organization {tenant_id}.",
                )

        # 3. Retrieve rejection entries from meta.data_quality_log with query-level RBAC
        if user_role == "team_member":
            dq_query = f"""
                SELECT
                    d.log_id,
                    d.batch_id,
                    d.tenant_id,
                    d.table_name,
                    d.row_identifier,
                    d.rejection_reason,
                    d.logged_at
                FROM {self.dq_table} d
                INNER JOIN {self.assignments_table} ta
                    ON d.tenant_id = ta.tenant_id AND ta.user_id = :user_id
                WHERE d.batch_id = :batch_id
                ORDER BY d.log_id ASC
            """
            self.cursor.execute(dq_query, {"batch_id": batch_id, "user_id": user_id})
        else:
            dq_query = f"""
                SELECT
                    d.log_id,
                    d.batch_id,
                    d.tenant_id,
                    d.table_name,
                    d.row_identifier,
                    d.rejection_reason,
                    d.logged_at
                FROM {self.dq_table} d
                WHERE d.batch_id = :batch_id
                ORDER BY d.log_id ASC
            """
            self.cursor.execute(dq_query, {"batch_id": batch_id})

        dq_rows = self.cursor.fetchall() or []

        # 4. Retrieve Bronze raw rows for this batch with query-level RBAC
        if user_role == "team_member":
            b_query_orders = f"""
                SELECT b.raw_id, b.raw_row_json
                FROM {self.bronze_orders_table} b
                INNER JOIN {self.assignments_table} ta
                    ON b.tenant_id = ta.tenant_id AND ta.user_id = :user_id
                WHERE b.batch_id = :batch_id
                ORDER BY b.raw_id ASC
            """
            self.cursor.execute(b_query_orders, {"batch_id": batch_id, "user_id": user_id})
            b_rows = self.cursor.fetchall() or []
            if not b_rows:
                b_query_shipping = f"""
                    SELECT b.raw_id, b.raw_row_json
                    FROM {self.bronze_shipping_table} b
                    INNER JOIN {self.assignments_table} ta
                        ON b.tenant_id = ta.tenant_id AND ta.user_id = :user_id
                    WHERE b.batch_id = :batch_id
                    ORDER BY b.raw_id ASC
                """
                self.cursor.execute(b_query_shipping, {"batch_id": batch_id, "user_id": user_id})
                b_rows = self.cursor.fetchall() or []
        else:
            b_query_orders = f"""
                SELECT b.raw_id, b.raw_row_json
                FROM {self.bronze_orders_table} b
                WHERE b.batch_id = :batch_id
                ORDER BY b.raw_id ASC
            """
            self.cursor.execute(b_query_orders, {"batch_id": batch_id})
            b_rows = self.cursor.fetchall() or []
            if not b_rows:
                b_query_shipping = f"""
                    SELECT b.raw_id, b.raw_row_json
                    FROM {self.bronze_shipping_table} b
                    WHERE b.batch_id = :batch_id
                    ORDER BY b.raw_id ASC
                """
                self.cursor.execute(b_query_shipping, {"batch_id": batch_id})
                b_rows = self.cursor.fetchall() or []

        # Parse Bronze records
        bronze_records: List[tuple[int, Dict[str, Any]]] = []
        for row in b_rows:
            raw_id = row[0]
            raw_json = row[1]
            if isinstance(raw_json, str):
                try:
                    data = json.loads(raw_json)
                except Exception:
                    data = {"raw_payload": raw_json}
            elif isinstance(raw_json, dict):
                data = dict(raw_json)
            else:
                data = {"raw_payload": str(raw_json)}
            bronze_records.append((raw_id, data))

        # 5. Build matched rejected rows correlating meta.data_quality_log with Bronze raw rows
        matched_results: List[Dict[str, Any]] = []
        used_bronze_indices: set[int] = set()

        for dq in dq_rows:
            row_id = str(dq[4] or "").strip()
            reason = str(dq[5] or "")
            matched_idx: Optional[int] = None

            # Attempt 1: Exact identifier match
            if row_id and row_id not in ("missing_row_id", "None", "NULL"):
                for idx, (brid, bdata) in enumerate(bronze_records):
                    if idx in used_bronze_indices:
                        continue
                    candidate_ids = {
                        str(bdata.get("order_id") or "").strip(),
                        str(bdata.get("shipment_id") or "").strip(),
                        str(bdata.get("tracking_number") or "").strip(),
                        str(bdata.get("product_id") or "").strip(),
                        str(bdata.get("customer_id") or "").strip(),
                    }
                    if row_id in candidate_ids:
                        matched_idx = idx
                        break

            # Attempt 2: Missing key match if reason indicates missing required field
            if matched_idx is None and ("missing" in reason.lower() or row_id in ("missing_row_id", "", "None", "NULL")):
                for idx, (brid, bdata) in enumerate(bronze_records):
                    if idx in used_bronze_indices:
                        continue
                    if not bdata.get("order_id"):
                        matched_idx = idx
                        break

            # Attempt 3: Characteristic matching from error reason
            if matched_idx is None:
                reason_lower = reason.lower()
                for idx, (brid, bdata) in enumerate(bronze_records):
                    if idx in used_bronze_indices:
                        continue
                    if "quantity" in reason_lower and (
                        not bdata.get("quantity")
                        or str(bdata.get("quantity")).startswith("-")
                        or str(bdata.get("quantity")) == "0"
                    ):
                        matched_idx = idx
                        break
                    if "date" in reason_lower and (
                        "not-a-date" in str(bdata.get("order_date", "")).lower()
                        or "unreadable" in str(bdata.get("order_date", "")).lower()
                    ):
                        matched_idx = idx
                        break
                    if "unit_price" in reason_lower and (
                        str(bdata.get("unit_price")) in ("0", "₹0.00", "$0.00", "0.00")
                        or str(bdata.get("unit_price", "")).startswith("-")
                    ):
                        matched_idx = idx
                        break
                    if "total" in reason_lower and (
                        not bdata.get("total")
                        or str(bdata.get("total", "")).startswith("-")
                    ):
                        matched_idx = idx
                        break

            # Attempt 4: Next available unused bronze row
            if matched_idx is None:
                for idx in range(len(bronze_records)):
                    if idx not in used_bronze_indices:
                        matched_idx = idx
                        break

            if matched_idx is not None:
                used_bronze_indices.add(matched_idx)
                out_row = dict(bronze_records[matched_idx][1])
            else:
                out_row = {"row_identifier": row_id} if row_id else {}

            out_row["rejection_reason"] = reason
            matched_results.append(out_row)

        # 6. Gather all column headers preserving Bronze column order, with rejection_reason last
        fieldnames: List[str] = []
        seen_fields: set[str] = set()

        # If we have bronze records, seed fields from the first one
        if bronze_records:
            for k in bronze_records[0][1].keys():
                if k != "rejection_reason" and k not in seen_fields:
                    seen_fields.add(k)
                    fieldnames.append(k)

        for r in matched_results:
            for k in r.keys():
                if k != "rejection_reason" and k not in seen_fields:
                    seen_fields.add(k)
                    fieldnames.append(k)

        if not fieldnames and not matched_results:
            fieldnames = ["row_identifier", "rejection_reason"]
        elif "rejection_reason" not in fieldnames:
            fieldnames.append("rejection_reason")

        # 7. Write CSV with UTF-8 BOM prefix
        output = io.StringIO()
        output.write("\ufeff")  # UTF-8 BOM
        writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for r in matched_results:
            writer.writerow(r)

        return output.getvalue()
