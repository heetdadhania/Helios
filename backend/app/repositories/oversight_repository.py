from datetime import date, datetime, timedelta, timezone
import logging
from typing import Any, Dict, List, Optional, Tuple

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
        self.dim_date_table = f"`{self.catalog}`.`gold`.`dim_date`"
        self.users_table = f"`{self.catalog}`.`platform`.`users`"
        self.team_table = f"`{self.catalog}`.`platform`.`team_assignments`"
        self.support_table = f"`{self.catalog}`.`platform`.`support_messages`"
        self.pending_table = f"`{self.catalog}`.`platform`.`pending_uploads`"

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

    def get_tenants_by_ids(self, tenant_ids: List[int]) -> Dict[int, Dict[str, Any]]:
        """
        Fetch multiple tenants by ID in a single set-based query to eliminate N+1 queries.
        Returns a mapping of tenant_id -> tenant dictionary.
        """
        if not tenant_ids:
            return {}
        ids = [int(i) for i in tenant_ids]
        ids_str = ", ".join(str(i) for i in ids)
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
            WHERE tenant_id IN ({ids_str})
        """
        rows = self._fetch_all(query)
        return {int(r["tenant_id"]): r for r in rows if r.get("tenant_id") is not None}

    def _get_comparison_anchor_dates(
        self,
        table: str,
        tenant_ids: List[int],
        date_col: str = "date_id",
    ) -> Dict[int, Any]:
        """Fetch max date per tenant from gold.fact_orders_daily_summary joined to gold.dim_date."""
        if not tenant_ids:
            return {}
        ids = [int(i) for i in tenant_ids]
        ids_str = ", ".join(str(i) for i in ids)
        query = f"""
            SELECT s.tenant_id, max(d.full_date) AS max_date
            FROM {self.summary_table} s
            JOIN `{self.catalog}`.`gold`.`dim_date` d ON s.date_id = d.date_id
            WHERE s.tenant_id IN ({ids_str})
            GROUP BY s.tenant_id
        """
        try:
            rows = self._fetch_all(query)
            return {int(r["tenant_id"]): r.get("max_date") for r in rows if r.get("tenant_id") is not None}
        except Exception:
            fallback_q = f"SELECT tenant_id, max({date_col}) AS max_date FROM {table} WHERE tenant_id IN ({ids_str}) GROUP BY tenant_id"
            rows = self._fetch_all(fallback_q)
            return {int(r["tenant_id"]): r.get("max_date") for r in rows if r.get("tenant_id") is not None}

    def _resolve_start_date_id(self, anchor_val: Any, days: Optional[int]) -> Tuple[Optional[int], Optional[int]]:
        """Convert anchor date value to (start_date_id, end_date_id) integer tuple (YYYYMMDD)."""
        if days is None or anchor_val is None:
            return (None, None)
        anchor_date = None
        if isinstance(anchor_val, (date, datetime)):
            anchor_date = anchor_val if isinstance(anchor_val, date) else anchor_val.date()
        else:
            val_str = str(anchor_val).strip()
            if val_str.isdigit() and len(val_str) == 8:
                try:
                    anchor_date = datetime.strptime(val_str, "%Y%m%d").date()
                except ValueError:
                    pass
            elif "-" in val_str:
                try:
                    anchor_date = datetime.strptime(val_str[:10], "%Y-%m-%d").date()
                except ValueError:
                    pass
        if anchor_date is None:
            return (None, None)
        start = anchor_date - timedelta(days=days - 1)
        end = anchor_date
        return (int(start.strftime("%Y%m%d")), int(end.strftime("%Y%m%d")))

    def get_comparison_revenue_metrics(
        self,
        tenant_ids: List[int],
        days: Optional[int],
        anchor_dates: Optional[Dict[int, Any]] = None,
    ) -> Dict[int, Dict[str, Any]]:
        """
        Fetch total revenue and orders for multiple tenants in a single set-based query,
        eliminating the N+1 pattern in compare_tenants.
        """
        if not tenant_ids:
            return {}
        ids = [int(i) for i in tenant_ids]
        ids_str = ", ".join(str(i) for i in ids)

        where_sql = f"tenant_id IN ({ids_str})"
        if days is not None:
            anchors = anchor_dates if anchor_dates is not None else self._get_comparison_anchor_dates(self.summary_table, ids, "date_id")
            tenant_clauses = []
            for tid in ids:
                start_date_id, end_date_id = self._resolve_start_date_id(anchors.get(tid), days)
                if start_date_id is not None and end_date_id is not None:
                    tenant_clauses.append(f"(tenant_id = {tid} AND date_id >= {start_date_id} AND date_id <= {end_date_id})")
            if tenant_clauses:
                where_sql = " OR ".join(tenant_clauses)
            else:
                where_sql = "1 = 0"

        query = f"""
            SELECT 
                tenant_id,
                coalesce(sum(total_revenue), 0.0) AS total_revenue,
                coalesce(sum(total_orders), 0) AS total_orders
            FROM {self.summary_table}
            WHERE {where_sql}
            GROUP BY tenant_id
        """
        try:
            rows = self._fetch_all(query)
            return {int(r["tenant_id"]): r for r in rows if r.get("tenant_id") is not None}
        except Exception as exc:
            logger.warning("Error fetching batch revenue comparison metrics: %s", exc)
            return {}

    def get_comparison_delivery_metrics(
        self,
        tenant_ids: List[int],
        days: Optional[int],
        anchor_dates: Optional[Dict[int, Any]] = None,
    ) -> Dict[int, Dict[str, Any]]:
        """
        Fetch shipment totals, late shipments, and average shipping days for multiple tenants
        in a single set-based query, eliminating the N+1 pattern in compare_tenants.
        """
        if not tenant_ids:
            return {}
        ids = [int(i) for i in tenant_ids]
        ids_str = ", ".join(str(i) for i in ids)

        where_sql = f"tenant_id IN ({ids_str})"
        if days is not None:
            anchors = anchor_dates if anchor_dates is not None else self._get_comparison_anchor_dates(self.summary_table, ids, "date_id")
            tenant_clauses = []
            for tid in ids:
                start_date_id, end_date_id = self._resolve_start_date_id(anchors.get(tid), days)
                if start_date_id is not None and end_date_id is not None:
                    tenant_clauses.append(f"(tenant_id = {tid} AND date_id >= {start_date_id} AND date_id <= {end_date_id})")
            if tenant_clauses:
                where_sql = " OR ".join(tenant_clauses)
            else:
                where_sql = "1 = 0"

        query = f"""
            SELECT 
                tenant_id,
                count(*) AS total_shipments,
                sum(CASE WHEN late_flag THEN 1 ELSE 0 END) AS late_shipments,
                round(sum(CASE WHEN late_flag THEN 1.0 ELSE 0.0 END) / nullif(count(*), 0) * 100.0, 2) AS late_pct,
                round(avg(coalesce(shipping_days, 0)), 2) AS avg_shipping_days
            FROM {self.shipments_table}
            WHERE {where_sql}
            GROUP BY tenant_id
        """
        try:
            rows = self._fetch_all(query)
            return {int(r["tenant_id"]): r for r in rows if r.get("tenant_id") is not None}
        except Exception as exc:
            logger.warning("Error fetching batch delivery comparison metrics: %s", exc)
            return {}

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

    def get_tenant_late_delivery_rates(
        self,
        tenant_ids: Optional[List[int]] = None,
        days: Optional[int] = None,
        anchor_dates: Optional[Dict[int, Any]] = None,
    ) -> Dict[int, Dict[str, Any]]:
        """
        Fetch late delivery percentage and shipment counts per tenant.
        Returns a mapping of tenant_id -> shipment metrics.
        """
        where_clauses = []
        if tenant_ids:
            ids_str = ", ".join(str(int(i)) for i in tenant_ids)
            where_clauses.append(f"tenant_id IN ({ids_str})")

        if days is not None and anchor_dates:
            tenant_clauses = []
            for tid, anchor in anchor_dates.items():
                start_id, end_id = self._resolve_start_date_id(anchor, days)
                if start_id is not None and end_id is not None:
                    tenant_clauses.append(f"(tenant_id = {tid} AND date_id >= {start_id} AND date_id <= {end_id})")
            if tenant_clauses:
                where_clauses.append(f"({' OR '.join(tenant_clauses)})")
            elif tenant_ids:
                where_clauses.append("1 = 0")

        where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

        query = f"""
            SELECT 
                tenant_id,
                count(*) AS total_shipments,
                sum(CASE WHEN late_flag THEN 1 ELSE 0 END) AS late_shipments,
                round(sum(CASE WHEN late_flag THEN 1.0 ELSE 0.0 END) / nullif(count(*), 0) * 100.0, 2) AS late_rate_pct,
                round(avg(coalesce(shipping_days, 0)), 2) AS avg_shipping_days
            FROM {self.shipments_table}
            {where_sql}
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
        """Fetch total counts for runs, rows, and batches in unified queries."""
        pipeline_q = f"""
            SELECT 
                count(*) AS total_runs,
                count(DISTINCT batch_id) AS total_batches,
                count(DISTINCT tenant_id) AS active_tenants
            FROM {self.pipeline_table}
        """
        self.cursor.execute(pipeline_q)
        row = self.cursor.fetchone() or [0, 0, 0]
        total_runs = row[0] or 0
        total_batches = row[1] or 0
        active_tenants = row[2] or 0

        rows_q = f"SELECT sum(coalesce(row_count, 0)) FROM {self.audit_table} WHERE stage IN ('bronze', 'bronze_ingest')"
        self.cursor.execute(rows_q)
        total_rows = (self.cursor.fetchone() or [0])[0] or 0

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

    def get_admin_home_summary(self) -> Dict[str, Any]:
        """Fetch summary metrics for Admin Home."""
        query = f"""
            SELECT
                (SELECT count(*) FROM {self.tenants_table} WHERE is_active = true) AS active_orgs,
                (SELECT count(*) FROM {self.tenants_table} WHERE is_active = false) AS inactive_orgs,
                (SELECT count(*) FROM {self.tenants_table}) AS total_orgs,
                (SELECT count(*) FROM {self.users_table} WHERE role = 'smb_owner' AND is_active = true) AS active_owners,
                (SELECT count(*) FROM {self.users_table} WHERE role = 'team_member' AND is_active = true) AS team_members,
                (SELECT count(DISTINCT coalesce(pu.upload_id, ps.upload_id, ps.batch_id))
                 FROM {self.pipeline_table} ps
                 FULL OUTER JOIN {self.pending_table} pu ON ps.upload_id = pu.upload_id
                 WHERE lower(coalesce(pu.status, '')) = 'pending'
                    OR lower(coalesce(ps.status, '')) IN ('pending_review', 'awaiting_confirmation')
                ) AS pending_uploads,
                (SELECT count(*) FROM {self.pipeline_table}
                 WHERE lower(status) IN ('running', 'ingesting', 'silver_running', 'gold_running')
                   AND (
                       (last_heartbeat_at IS NULL AND created_at >= (current_timestamp() - INTERVAL 15 MINUTES))
                       OR (last_heartbeat_at IS NOT NULL AND last_heartbeat_at >= (current_timestamp() - INTERVAL 15 MINUTES))
                   )
                ) AS running_pipelines,
                (SELECT count(*) FROM {self.pipeline_table} WHERE lower(status) IN ('failed', 'failure', 'error', 'restart_required')) AS failed_pipelines,
                (SELECT count(*) FROM {self.support_table} WHERE lower(status) = 'open') AS open_support_messages
        """
        row = self._fetch_one(query) or {}
        return {
            "organizations_active": int(row.get("active_orgs") or 0),
            "organizations_inactive": int(row.get("inactive_orgs") or 0),
            "organizations_total": int(row.get("total_orgs") or 0),
            "organization_owners_active": int(row.get("active_owners") or 0),
            "team_members": int(row.get("team_members") or 0),
            "pending_uploads": int(row.get("pending_uploads") or 0),
            "running_pipelines": int(row.get("running_pipelines") or 0),
            "failed_pipelines": int(row.get("failed_pipelines") or 0),
            "open_support_messages": int(row.get("open_support_messages") or 0),
        }

    def get_admin_home_top_10_revenue(self) -> List[Dict[str, Any]]:
        """
        Fetch top 10 organizations by revenue (each organization's latest 30 days of its own data).
        """
        query = f"""
            WITH tenant_anchors AS (
                SELECT 
                    s.tenant_id,
                    max(d.full_date) AS max_date
                FROM {self.summary_table} s
                JOIN {self.dim_date_table} d ON s.date_id = d.date_id
                GROUP BY s.tenant_id
            ),
            tenant_30d_rev AS (
                SELECT 
                    s.tenant_id,
                    round(coalesce(sum(s.total_revenue), 0.0), 2) AS total_revenue
                FROM {self.summary_table} s
                JOIN {self.dim_date_table} d ON s.date_id = d.date_id
                JOIN tenant_anchors a ON s.tenant_id = a.tenant_id
                WHERE d.full_date >= date_sub(a.max_date, 29)
                  AND d.full_date <= a.max_date
                GROUP BY s.tenant_id
            )
            SELECT 
                t.tenant_id,
                t.business_name AS organization_name,
                coalesce(r.total_revenue, 0.0) AS total_revenue
            FROM {self.tenants_table} t
            JOIN tenant_30d_rev r ON t.tenant_id = r.tenant_id
            WHERE r.total_revenue > 0
            ORDER BY total_revenue DESC
            LIMIT 10
        """
        rows = self._fetch_all(query)
        return [
            {
                "tenant_id": int(r["tenant_id"]),
                "organization_name": r.get("organization_name") or f"Organization #{r['tenant_id']}",
                "total_revenue": float(r.get("total_revenue") or 0.0),
            }
            for r in rows
        ]

    def get_admin_home_pipeline_runs_14d(self) -> List[Dict[str, Any]]:
        """
        Fetch pipeline runs per day split into success and failed for the last 14 days.
        """
        query = f"""
            SELECT 
                cast(to_date(coalesce(created_at, updated_at)) AS string) AS date_str,
                sum(CASE WHEN lower(status) in ('success', 'completed') THEN 1 ELSE 0 END) AS successful_runs,
                sum(CASE WHEN lower(status) in ('failed', 'restart_required', 'error') THEN 1 ELSE 0 END) AS failed_runs,
                count(*) AS total_runs
            FROM {self.pipeline_table}
            WHERE coalesce(created_at, updated_at) >= (current_date() - INTERVAL 14 DAYS)
            GROUP BY 1
            ORDER BY 1 ASC
        """
        raw_rows = self._fetch_all(query)
        by_date = {r["date_str"]: r for r in raw_rows if r.get("date_str")}

        today = date.today()
        result = []
        for i in range(13, -1, -1):
            d_str = (today - timedelta(days=i)).isoformat()
            if d_str in by_date:
                item = by_date[d_str]
                result.append({
                    "date": d_str,
                    "successful_runs": int(item.get("successful_runs") or 0),
                    "failed_runs": int(item.get("failed_runs") or 0),
                    "total_runs": int(item.get("total_runs") or 0),
                })
            else:
                result.append({
                    "date": d_str,
                    "successful_runs": 0,
                    "failed_runs": 0,
                    "total_runs": 0,
                })
        return result

    def get_admin_home_tables(self) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Fetch 10 organizations and 10 recent activity rows for Admin Home.
        """
        orgs_q = f"""
            WITH last_dates AS (
                SELECT 
                    s.tenant_id,
                    max(d.full_date) AS last_date
                FROM {self.summary_table} s
                JOIN {self.dim_date_table} d ON s.date_id = d.date_id
                GROUP BY s.tenant_id
            ),
            owners AS (
                SELECT 
                    u.tenant_id,
                    coalesce(nullif(trim(u.name), ''), u.email) AS owner_name
                FROM {self.users_table} u
                WHERE u.role = 'smb_owner' AND u.is_active = true
            ),
            team_members AS (
                SELECT 
                    ta.tenant_id,
                    concat_ws(', ', collect_list(coalesce(nullif(trim(u.name), ''), u.email))) AS assigned_team_member
                FROM {self.team_table} ta
                JOIN {self.users_table} u ON ta.user_id = u.user_id
                GROUP BY ta.tenant_id
            )
            SELECT 
                t.tenant_id,
                t.business_name AS name,
                t.is_active,
                coalesce(o.owner_name, 'Unassigned') AS owner,
                coalesce(tm.assigned_team_member, 'Unassigned') AS assigned_team_member,
                cast(ld.last_date AS string) AS last_data_received
            FROM {self.tenants_table} t
            LEFT JOIN owners o ON t.tenant_id = o.tenant_id
            LEFT JOIN team_members tm ON t.tenant_id = tm.tenant_id
            LEFT JOIN last_dates ld ON t.tenant_id = ld.tenant_id
            ORDER BY t.created_at DESC, t.tenant_id DESC
            LIMIT 10
        """
        org_rows = self._fetch_all(orgs_q)
        organizations = [
            {
                "tenant_id": int(r["tenant_id"]),
                "name": r.get("name") or f"Organization #{r['tenant_id']}",
                "owner": r.get("owner") or "Unassigned",
                "assigned_team_member": r.get("assigned_team_member") or "Unassigned",
                "last_data_received": str(r["last_data_received"]) if r.get("last_data_received") else None,
                "is_active": bool(r.get("is_active", True)),
            }
            for r in org_rows
        ]

        act_q = f"""
            SELECT 
                ps.batch_id,
                ps.tenant_id,
                t.business_name AS tenant_name,
                ps.stage,
                CASE 
                    WHEN LOWER(ps.status) IN ('running', 'ingesting', 'silver_running', 'gold_running')
                         AND (
                             (ps.last_heartbeat_at IS NULL AND ps.created_at < (current_timestamp() - INTERVAL 15 MINUTES))
                             OR
                             (ps.last_heartbeat_at IS NOT NULL AND ps.last_heartbeat_at < (current_timestamp() - INTERVAL 15 MINUTES))
                         ) THEN 'stalled'
                    ELSE ps.status
                END AS status,
                ps.error_message,
                ps.created_at AS timestamp
            FROM {self.pipeline_table} ps
            LEFT JOIN {self.tenants_table} t ON ps.tenant_id = t.tenant_id
            ORDER BY ps.created_at DESC
            LIMIT 10
        """
        act_rows = self._fetch_all(act_q)
        recent_activity = [
            {
                "batch_id": r.get("batch_id"),
                "tenant_id": int(r["tenant_id"]) if r.get("tenant_id") is not None else None,
                "tenant_name": r.get("tenant_name"),
                "stage": r.get("stage"),
                "status": r.get("status") or "unknown",
                "error_message": r.get("error_message"),
                "timestamp": r.get("timestamp"),
            }
            for r in act_rows
        ]
        return organizations, recent_activity
