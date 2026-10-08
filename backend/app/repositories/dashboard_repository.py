import logging
import time
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

try:
    from databricks.sql.client import Cursor
except ImportError:
    Cursor = Any  # type: ignore

from app.core.config import settings
from app.db.base import databricks_cursor

logger = logging.getLogger("helios.repositories.dashboard")


class DashboardRepository:
    """
    Repository handling all read queries against the Gold layer for customer dashboard charts.
    
    Lookback window filtering behavior:
      - When `days` is specified (e.g., 7, 30), metrics are strictly filtered to the window
        [anchor_date - (days - 1), anchor_date], where anchor_date is dynamically determined
        as the most recent business date present in the tenant's data (MAX date_id).
        If the table contains no data for the tenant, anchor_date falls back to the current UTC date.
      - When `days` is None, all-time records are queried without any date boundary constraint.

    Includes retry-with-backoff on query execution to absorb warehouse cold starts and transient connection drops.
    """

    def __init__(self, cursor: Cursor, catalog: Optional[str] = None):
        self.cursor = cursor
        self.catalog = catalog or settings.DATABRICKS_CATALOG
        self.daily_summary_table = f"`{self.catalog}`.`gold`.`fact_orders_daily_summary`"
        self.dim_date_table = f"`{self.catalog}`.`gold`.`dim_date`"
        self.fact_orders_table = f"`{self.catalog}`.`gold`.`fact_orders`"
        self.dim_product_table = f"`{self.catalog}`.`gold`.`dim_product`"
        self.fact_shipments_table = f"`{self.catalog}`.`gold`.`fact_shipments`"
        self.dim_shipping_mode_table = f"`{self.catalog}`.`gold`.`dim_shipping_mode`"
        self.dim_delivery_status_table = f"`{self.catalog}`.`gold`.`dim_delivery_status`"

    def _execute_query_with_retry(
        self,
        query: str,
        params: Optional[Dict[str, Any]] = None,
        max_retries: int = 3,
        base_backoff: float = 1.0,
    ) -> List[Dict[str, Any]]:
        """Execute a query returning multiple rows with retry-with-backoff for cold start absorption."""
        last_exception = None
        for attempt in range(1, max_retries + 1):
            try:
                if attempt == 1 and self.cursor is not None:
                    self.cursor.execute(query, params or {})
                    rows = self.cursor.fetchall() or []
                    columns = [desc[0] for desc in self.cursor.description] if self.cursor.description else []
                    return [dict(zip(columns, row)) for row in rows]

                with databricks_cursor(catalog=self.catalog) as fresh_cursor:
                    fresh_cursor.execute(query, params or {})
                    rows = fresh_cursor.fetchall() or []
                    columns = [desc[0] for desc in fresh_cursor.description] if fresh_cursor.description else []
                    return [dict(zip(columns, row)) for row in rows]
            except Exception as exc:
                last_exception = exc
                if attempt < max_retries:
                    backoff = base_backoff * (2 ** (attempt - 1))
                    logger.warning(
                        "Dashboard query attempt %d/%d failed: %s. Retrying in %.1fs...",
                        attempt,
                        max_retries,
                        exc,
                        backoff,
                    )
                    time.sleep(backoff)
                else:
                    logger.error(
                        "All %d dashboard query attempts failed. Last error: %s",
                        max_retries,
                        exc,
                    )
                    raise exc
        if last_exception:
            raise last_exception
        return []

    def _execute_single_with_retry(
        self,
        query: str,
        params: Optional[Dict[str, Any]] = None,
        max_retries: int = 3,
        base_backoff: float = 1.0,
    ) -> Dict[str, Any]:
        """Execute a query returning a single row with retry-with-backoff for cold start absorption."""
        last_exception = None
        for attempt in range(1, max_retries + 1):
            try:
                if attempt == 1 and self.cursor is not None:
                    self.cursor.execute(query, params or {})
                    row = self.cursor.fetchone()
                    columns = [desc[0] for desc in self.cursor.description] if self.cursor.description else []
                    return dict(zip(columns, row)) if row else {}

                with databricks_cursor(catalog=self.catalog) as fresh_cursor:
                    fresh_cursor.execute(query, params or {})
                    row = fresh_cursor.fetchone()
                    columns = [desc[0] for desc in fresh_cursor.description] if fresh_cursor.description else []
                    return dict(zip(columns, row)) if row else {}
            except Exception as exc:
                last_exception = exc
                if attempt < max_retries:
                    backoff = base_backoff * (2 ** (attempt - 1))
                    logger.warning(
                        "Dashboard single query attempt %d/%d failed: %s. Retrying in %.1fs...",
                        attempt,
                        max_retries,
                        exc,
                        backoff,
                    )
                    time.sleep(backoff)
                else:
                    logger.error(
                        "All %d dashboard single query attempts failed. Last error: %s",
                        max_retries,
                        exc,
                    )
                    raise exc
        if last_exception:
            raise last_exception
        return {}

    def _get_anchor_date(self, table: str, tenant_id: int, date_col: str = "date_id") -> date:
        """
        Determine the anchor date for the lookback window.
        Uses the most recent date present in the tenant's data (MAX date_id).
        Falls back to current UTC date if the table contains no data.
        """
        query = f"SELECT max({date_col}) AS max_date FROM {table} WHERE tenant_id = :tenant_id"
        row = self._execute_single_with_retry(query, {"tenant_id": tenant_id})
        val = row.get("max_date") if row else None
        if val is None and row and len(row) > 0:
            val = next(iter(row.values()))
        if val is not None:
            if isinstance(val, int) or (isinstance(val, str) and str(val).isdigit() and len(str(val)) == 8):
                try:
                    return datetime.strptime(str(val), "%Y%m%d").date()
                except ValueError:
                    pass
            elif hasattr(val, "strftime"):
                return val if isinstance(val, date) else val.date()
        return datetime.now(timezone.utc).date()

    def _calculate_date_bounds(
        self,
        table: str,
        tenant_id: int,
        days: Optional[int],
        date_col: str = "date_id",
    ) -> Optional[int]:
        """
        Calculate start date_id in YYYYMMDD format for the lookback window.
        Returns None if days is None (all-time range).
        """
        if days is None:
            return None
        anchor = self._get_anchor_date(table, tenant_id, date_col)
        start_date = anchor - timedelta(days=days - 1)
        return int(start_date.strftime("%Y%m%d"))

    def get_revenue_trend(self, tenant_id: int, days: Optional[int] = 30) -> List[Dict[str, Any]]:
        """
        Query pre-aggregated gold.fact_orders_daily_summary joined with dim_date
        strictly scoped to tenant_id for the given lookback window.
        """
        start_date_id = self._calculate_date_bounds(self.daily_summary_table, tenant_id, days)

        where_clauses = ["s.tenant_id = :tenant_id"]
        params: Dict[str, Any] = {"tenant_id": tenant_id}
        if days is not None:
            params["days"] = days

        if start_date_id is not None:
            where_clauses.append("s.date_id >= :start_date_id")
            params["start_date_id"] = start_date_id

        where_sql = " AND ".join(where_clauses)
        query = f"""
            SELECT
                coalesce(cast(d.full_date AS string), concat(substr(string(s.date_id), 1, 4), '-', substr(string(s.date_id), 5, 2), '-', substr(string(s.date_id), 7, 2))) AS date_str,
                s.total_revenue,
                s.total_orders,
                s.avg_order_value,
                s.total_quantity
            FROM {self.daily_summary_table} s
            LEFT JOIN {self.dim_date_table} d ON s.date_id = d.date_id
            WHERE {where_sql}
            ORDER BY s.date_id ASC
        """
        return self._execute_query_with_retry(query, params)

    def get_top_products(
        self,
        tenant_id: int,
        limit: int = 10,
        days: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Query fact_orders and dim_product for top revenue products scoped to tenant_id
        within the requested lookback window (or all-time if days is None).
        """
        start_date_id = self._calculate_date_bounds(self.fact_orders_table, tenant_id, days)

        where_clauses = ["fo.tenant_id = :tenant_id"]
        params: Dict[str, Any] = {"tenant_id": tenant_id, "limit": limit}
        if days is not None:
            params["days"] = days

        if start_date_id is not None:
            where_clauses.append("fo.date_id >= :start_date_id")
            params["start_date_id"] = start_date_id

        where_sql = " AND ".join(where_clauses)
        query = f"""
            SELECT
                p.product_id,
                p.product_name,
                coalesce(p.category, 'General') AS category,
                round(sum(coalesce(fo.total, 0.0)), 2) AS total_revenue,
                sum(coalesce(fo.quantity, 0)) AS total_units_sold,
                count(DISTINCT fo.source_order_id) AS total_orders
            FROM {self.fact_orders_table} fo
            INNER JOIN {self.dim_product_table} p 
               ON fo.product_id = p.product_id
              AND fo.tenant_id = p.tenant_id
            WHERE {where_sql}
            GROUP BY p.product_id, p.product_name, p.category
            ORDER BY total_revenue DESC
            LIMIT :limit
        """
        return self._execute_query_with_retry(query, params)

    def get_late_delivery_risk(
        self,
        tenant_id: int,
        days: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Query fact_shipments and dim_delivery_status for overall late delivery rate and status breakdown
        within the requested lookback window (or all-time if days is None).
        """
        start_date_id = self._calculate_date_bounds(self.fact_shipments_table, tenant_id, days)

        where_clauses_ov = ["tenant_id = :tenant_id"]
        params: Dict[str, Any] = {"tenant_id": tenant_id}
        if days is not None:
            params["days"] = days

        if start_date_id is not None:
            where_clauses_ov.append("date_id >= :start_date_id")
            params["start_date_id"] = start_date_id

        where_sql_ov = " AND ".join(where_clauses_ov)
        overview_q = f"""
            SELECT
                count(*) AS total_shipments,
                sum(CASE WHEN late_flag THEN 1 ELSE 0 END) AS late_shipments,
                sum(CASE WHEN NOT late_flag THEN 1 ELSE 0 END) AS on_time_shipments,
                round(avg(coalesce(shipping_days, 0)), 2) AS avg_shipping_days
            FROM {self.fact_shipments_table}
            WHERE {where_sql_ov}
        """
        overview_data = self._execute_single_with_retry(overview_q, params)

        where_clauses_bd = ["fs.tenant_id = :tenant_id"]
        if start_date_id is not None:
            where_clauses_bd.append("fs.date_id >= :start_date_id")
        where_sql_bd = " AND ".join(where_clauses_bd)

        breakdown_q = f"""
            SELECT
                coalesce(ds.status_name, 'Unknown') AS status_name,
                count(*) AS total_shipments,
                sum(CASE WHEN fs.late_flag THEN 1 ELSE 0 END) AS late_shipments,
                round(sum(CASE WHEN fs.late_flag THEN 1.0 ELSE 0.0 END) / count(*) * 100.0, 2) AS late_rate_pct
            FROM {self.fact_shipments_table} fs
            LEFT JOIN {self.dim_delivery_status_table} ds ON fs.delivery_status_id = ds.delivery_status_id
            WHERE {where_sql_bd}
            GROUP BY ds.status_name
            ORDER BY total_shipments DESC
        """
        breakdown_list = self._execute_query_with_retry(breakdown_q, params)

        return {
            "overview": overview_data,
            "breakdown": breakdown_list,
        }

    def get_discount_vs_profit(
        self,
        tenant_id: int,
        days: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Query fact_orders to group sales and gross profit by discount bands
        within the requested lookback window (or all-time if days is None).
        """
        start_date_id = self._calculate_date_bounds(self.fact_orders_table, tenant_id, days)

        where_clauses = ["tenant_id = :tenant_id"]
        params: Dict[str, Any] = {"tenant_id": tenant_id}
        if days is not None:
            params["days"] = days

        if start_date_id is not None:
            where_clauses.append("date_id >= :start_date_id")
            params["start_date_id"] = start_date_id

        where_sql = " AND ".join(where_clauses)
        query = f"""
            SELECT
                CASE 
                    WHEN coalesce(discount, 0.0) = 0.0 OR coalesce(total, 0.0) = 0.0 THEN '0%'
                    WHEN (discount / (total + discount)) <= 0.10 THEN '1-10%'
                    WHEN (discount / (total + discount)) <= 0.20 THEN '11-20%'
                    WHEN (discount / (total + discount)) <= 0.30 THEN '21-30%'
                    ELSE '>30%'
                END AS band,
                round(sum(coalesce(total, 0.0)), 2) AS total_revenue,
                round(sum(coalesce(discount, 0.0)), 2) AS total_discount,
                round(sum(coalesce(profit, 0.0)), 2) AS total_profit,
                count(*) AS order_count
            FROM {self.fact_orders_table}
            WHERE {where_sql}
            GROUP BY 1
            ORDER BY 1
        """
        return self._execute_query_with_retry(query, params)

    def get_shipping_mode_comparison(
        self,
        tenant_id: int,
        days: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Query fact_shipments and dim_shipping_mode for volume and SLA performance across channels
        within the requested lookback window (or all-time if days is None).
        """
        start_date_id = self._calculate_date_bounds(self.fact_shipments_table, tenant_id, days)

        where_clauses = ["fs.tenant_id = :tenant_id"]
        params: Dict[str, Any] = {"tenant_id": tenant_id}
        if days is not None:
            params["days"] = days

        if start_date_id is not None:
            where_clauses.append("fs.date_id >= :start_date_id")
            params["start_date_id"] = start_date_id

        where_sql = " AND ".join(where_clauses)
        query = f"""
            SELECT
                coalesce(sm.mode_name, 'Standard') AS mode_name,
                count(*) AS shipment_count,
                round(avg(coalesce(fs.shipping_days, 0)), 2) AS avg_shipping_days,
                sum(CASE WHEN fs.late_flag THEN 1 ELSE 0 END) AS late_count,
                round(sum(CASE WHEN fs.late_flag THEN 1.0 ELSE 0.0 END) / count(*) * 100.0, 2) AS late_rate_pct,
                round(sum(CASE WHEN NOT fs.late_flag THEN 1.0 ELSE 0.0 END) / count(*) * 100.0, 2) AS on_time_rate_pct
            FROM {self.fact_shipments_table} fs
            LEFT JOIN {self.dim_shipping_mode_table} sm ON fs.shipping_mode_id = sm.shipping_mode_id
            WHERE {where_sql}
            GROUP BY sm.mode_name
            ORDER BY shipment_count DESC
        """
        return self._execute_query_with_retry(query, params)
