import logging
from typing import Any, Dict, List, Optional

try:
    from databricks.sql.client import Cursor
except ImportError:
    Cursor = Any  # type: ignore

from app.core.config import settings

logger = logging.getLogger("helios.repositories.oversight")


class OversightRepository:
    """
    Repository providing cross-tenant administrative queries, health indicators,
    internal platform usage analytics, and audit log exports.
    """

    def __init__(self, cursor: Cursor, catalog: Optional[str] = None) -> None:
        self.cursor = cursor
        self.catalog = catalog or settings.DATABRICKS_CATALOG
        self.tenants_table = f"`{self.catalog}`.`platform`.`tenants`"
        self.pipeline_table = f"`{self.catalog}`.`platform`.`pipeline_status`"
        self.audit_table = f"`{self.catalog}`.`meta`.`etl_audit_log`"
        self.dq_table = f"`{self.catalog}`.`meta`.`data_quality_log`"
        self.shipments_table = f"`{self.catalog}`.`gold`.`fact_shipments`"
        self.orders_table = f"`{self.catalog}`.`gold`.`fact_orders`"
        self.summary_table = f"`{self.catalog}`.`gold`.`fact_orders_daily_summary`"

    def _fetch_all(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Helper to execute query and return list of dictionaries."""
        if params:
            self.cursor.execute(query, params)
        else:
            self.cursor.execute(query)
        rows = self.cursor.fetchall() or []
        columns = [desc[0] for desc in self.cursor.description] if self.cursor.description else []
        return [dict(zip(columns, row)) for row in rows]

    def _fetch_one(self, query: str, params: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """Helper to execute query and return a single dictionary or None."""
        if params:
            self.cursor.execute(query, params)
        else:
            self.cursor.execute(query)
        row = self.cursor.fetchone()
        if not row:
            return None
        columns = [desc[0] for desc in self.cursor.description] if self.cursor.description else []
        return dict(zip(columns, row))

    def get_tenant_by_id(self, tenant_id: int) -> Optional[Dict[str, Any]]:
        """Fetch tenant information by ID."""
        query = f"""
            SELECT 
                tenant_id, 
                business_name, 
                coalesce(lower(replace(business_name, ' ', '_')), concat('tenant_', string(tenant_id))) AS slug,
                'starter' AS tier,
                industry,
                contact_email,
                created_by,
                created_at,
                is_active
            FROM {self.tenants_table}
            WHERE tenant_id = :tenant_id
            LIMIT 1
        """
        return self._fetch_one(query, {"tenant_id": tenant_id})

    def get_all_tenants(self) -> List[Dict[str, Any]]:
        """Fetch all tenants registered on the platform."""
        query = f"""
            SELECT 
                tenant_id, 
                business_name, 
                coalesce(lower(replace(business_name, ' ', '_')), concat('tenant_', string(tenant_id))) AS slug,
                'starter' AS tier,
                industry,
                contact_email,
                created_by,
                created_at,
                is_active
            FROM {self.tenants_table}
            ORDER BY tenant_id ASC
        """
        return self._fetch_all(query)

    def get_latest_pipeline_status_per_tenant(self) -> Dict[int, Dict[str, Any]]:
        """
        Fetch the most recent pipeline status per tenant.
        Returns a mapping of tenant_id -> status dictionary.
        """
        query = f"""
            SELECT 
                ps.tenant_id,
                ps.batch_id,
                ps.current_stage,
                ps.status,
                ps.updated_at,
                ps.error_message
            FROM (
                SELECT 
                    tenant_id,
                    batch_id,
                    stage AS current_stage,
                    status,
                    updated_at,
                    error_message,
                    row_number() OVER (PARTITION BY tenant_id ORDER BY updated_at DESC) as rn
                FROM {self.pipeline_table}
            ) ps
            WHERE ps.rn = 1
        """
        try:
            rows = self._fetch_all(query)
            return {int(r["tenant_id"]): r for r in rows if r.get("tenant_id") is not None}
        except Exception as exc:
            logger.warning("Could not execute window query on pipeline_status: %s. Using fallback query.", exc)
            fallback_q = f"""
                SELECT 
                    tenant_id,
                    batch_id,
                    stage AS current_stage,
                    status,
                    updated_at,
                    error_message
                FROM {self.pipeline_table}
                ORDER BY updated_at DESC
            """
            rows = self._fetch_all(fallback_q)
            result: Dict[int, Dict[str, Any]] = {}
            for r in rows:
                tid = int(r.get("tenant_id", 0))
                if tid not in result:
                    result[tid] = r
            return result

    def get_tenant_late_delivery_rates(self) -> Dict[int, Dict[str, Any]]:
        """
        Fetch late delivery percentage and shipment counts per tenant.
        Returns a mapping of tenant_id -> shipment metrics.
        """
        query = f"""
            SELECT 
                tenant_id,
                count(*) AS total_shipments,
                sum(CASE WHEN late_flag THEN 1 ELSE 0 END) AS late_shipments,
                round(sum(CASE WHEN late_flag THEN 1.0 ELSE 0.0 END) / nullif(count(*), 0) * 100.0, 2) AS late_rate_pct,
                round(avg(coalesce(shipping_days, 0)), 2) AS avg_shipping_days
            FROM {self.shipments_table}
            GROUP BY tenant_id
        """
        try:
            rows = self._fetch_all(query)
            return {int(r["tenant_id"]): r for r in rows if r.get("tenant_id") is not None}
        except Exception as exc:
            logger.warning("Could not query shipments for health evaluation: %s", exc)
            return {}

    def get_usage_pipeline_runs_per_day(self, limit_days: int = 30) -> List[Dict[str, Any]]:
        """
        Aggregate daily pipeline runs from platform.pipeline_status.
        """
        query = f"""
            SELECT 
                cast(to_date(coalesce(created_at, updated_at)) AS string) AS date_str,
                count(*) AS total_runs,
                sum(CASE WHEN lower(status) in ('success', 'completed') THEN 1 ELSE 0 END) AS successful_runs,
                sum(CASE WHEN lower(status) in ('failed', 'restart_required') THEN 1 ELSE 0 END) AS failed_runs
            FROM {self.pipeline_table}
            WHERE coalesce(created_at, updated_at) IS NOT NULL
            GROUP BY 1
            ORDER BY 1 DESC
            LIMIT :limit_days
        """
        try:
            rows = self._fetch_all(query, {"limit_days": limit_days})
            return sorted(rows, key=lambda x: str(x.get("date_str", "")))
        except Exception as exc:
            logger.warning("Could not fetch daily pipeline runs: %s", exc)
            return []

    def get_usage_batches_per_tenant(self) -> List[Dict[str, Any]]:
        """
        Calculate total batches processed per tenant from pipeline_status and tenants.
        """
        query = f"""
            SELECT 
                t.tenant_id,
                t.business_name AS tenant_name,
                count(DISTINCT ps.batch_id) AS batch_count,
                max(ps.updated_at) AS last_batch_at
            FROM {self.tenants_table} t
            LEFT JOIN {self.pipeline_table} ps ON t.tenant_id = ps.tenant_id
            GROUP BY t.tenant_id, t.business_name
            ORDER BY batch_count DESC, t.tenant_id ASC
        """
        return self._fetch_all(query)

    def get_usage_rows_ingested_per_day(self, limit_days: int = 30) -> List[Dict[str, Any]]:
        """
        Calculate total rows ingested per day from meta.etl_audit_log for bronze_ingest stage.
        """
        query = f"""
            SELECT 
                cast(to_date(started_at) AS string) AS date_str,
                sum(coalesce(row_count, 0)) AS rows_ingested
            FROM {self.audit_table}
            WHERE stage IN ('bronze', 'bronze_ingest') AND started_at IS NOT NULL
            GROUP BY 1
            ORDER BY 1 DESC
            LIMIT :limit_days
        """
        try:
            rows = self._fetch_all(query, {"limit_days": limit_days})
            return sorted(rows, key=lambda x: str(x.get("date_str", "")))
        except Exception as exc:
            logger.warning("Could not fetch rows ingested trend: %s", exc)
            return []

    def get_overall_usage_totals(self) -> Dict[str, int]:
        """Fetch total counts for runs, rows, and batches."""
        runs_q = f"SELECT count(*) FROM {self.pipeline_table}"
        self.cursor.execute(runs_q)
        total_runs = (self.cursor.fetchone() or [0])[0] or 0

        rows_q = f"SELECT sum(coalesce(row_count, 0)) FROM {self.audit_table} WHERE stage IN ('bronze', 'bronze_ingest')"
        self.cursor.execute(rows_q)
        total_rows = (self.cursor.fetchone() or [0])[0] or 0

        batches_q = f"SELECT count(DISTINCT batch_id) FROM {self.pipeline_table}"
        self.cursor.execute(batches_q)
        total_batches = (self.cursor.fetchone() or [0])[0] or 0

        active_t_q = f"SELECT count(DISTINCT tenant_id) FROM {self.pipeline_table}"
        self.cursor.execute(active_t_q)
        active_tenants = (self.cursor.fetchone() or [0])[0] or 0

        return {
            "total_runs": int(total_runs),
            "total_rows_ingested": int(total_rows),
            "total_batches": int(total_batches),
            "active_tenants_count": int(active_tenants),
        }

    def get_audit_export_records(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Combine system-wide audit records from meta.etl_audit_log and meta.data_quality_log.
        """
        audit_where: List[str] = []
        audit_params: Dict[str, Any] = {}
        if start_date:
            audit_where.append("to_date(a.started_at) >= :start_date")
            audit_params["start_date"] = start_date
        if end_date:
            audit_where.append("to_date(a.started_at) <= :end_date")
            audit_params["end_date"] = end_date

        audit_where_sql = f"WHERE {' AND '.join(audit_where)}" if audit_where else ""

        audit_query = f"""
            SELECT 
                'etl_audit' AS log_type,
                a.log_id,
                cast(a.started_at AS string) AS timestamp,
                a.batch_id,
                coalesce(ps.tenant_id, 0) AS tenant_id,
                coalesce(t.business_name, 'System') AS tenant_name,
                a.stage AS stage_or_table,
                a.status AS status_or_reason,
                cast(coalesce(a.row_count, 0) AS string) AS row_count_or_identifier,
                coalesce(a.error_message, '') AS error_detail
            FROM {self.audit_table} a
            LEFT JOIN {self.pipeline_table} ps ON a.batch_id = ps.batch_id
            LEFT JOIN {self.tenants_table} t ON ps.tenant_id = t.tenant_id
            {audit_where_sql}
        """

        dq_where: List[str] = []
        dq_params: Dict[str, Any] = {}
        if start_date:
            dq_where.append("to_date(dq.logged_at) >= :start_date")
            dq_params["start_date"] = start_date
        if end_date:
            dq_where.append("to_date(dq.logged_at) <= :end_date")
            dq_params["end_date"] = end_date

        dq_where_sql = f"WHERE {' AND '.join(dq_where)}" if dq_where else ""

        dq_query = f"""
            SELECT 
                'data_quality' AS log_type,
                dq.log_id,
                cast(dq.logged_at AS string) AS timestamp,
                dq.batch_id,
                dq.tenant_id,
                coalesce(t.business_name, 'Tenant') AS tenant_name,
                dq.table_name AS stage_or_table,
                dq.rejection_reason AS status_or_reason,
                coalesce(dq.row_identifier, '') AS row_count_or_identifier,
                '' AS error_detail
            FROM {self.dq_table} dq
            LEFT JOIN {self.tenants_table} t ON dq.tenant_id = t.tenant_id
            {dq_where_sql}
        """

        combined_query = f"""
            {audit_query}
            UNION ALL
            {dq_query}
            ORDER BY timestamp DESC
            LIMIT 5000
        """
        combined_params = {**audit_params, **dq_params}
        try:
            return self._fetch_all(combined_query, combined_params if combined_params else None)
        except Exception as exc:
            logger.warning("Could not execute UNION audit query: %s. Querying audit log only.", exc)
            return self._fetch_all(audit_query, audit_params if audit_params else None)
