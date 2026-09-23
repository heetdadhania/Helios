import logging
from typing import Any, Dict, List, Optional

try:
    from databricks.sql.client import Cursor
except ImportError:
    Cursor = Any  # type: ignore

from app.core.config import settings

logger = logging.getLogger("helios.repositories.dashboard")


class DashboardRepository:
    """Repository handling all read queries against the Gold layer for customer dashboard charts."""

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

    def get_revenue_trend(self, tenant_id: int, days: int = 30) -> List[Dict[str, Any]]:
        """
        Query pre-aggregated gold.fact_orders_daily_summary joined with dim_date
        strictly scoped to tenant_id for the given lookback window.
        """
        query = f"""
            SELECT
                coalesce(cast(d.full_date AS string), concat(substr(string(s.date_id), 1, 4), '-', substr(string(s.date_id), 5, 2), '-', substr(string(s.date_id), 7, 2))) AS date_str,
                s.total_revenue,
                s.total_orders,
                s.avg_order_value,
                s.total_quantity
            FROM {self.daily_summary_table} s
            LEFT JOIN {self.dim_date_table} d ON s.date_id = d.date_id
            WHERE s.tenant_id = :tenant_id
            ORDER BY s.date_id DESC
            LIMIT :days
        """
        self.cursor.execute(query, {"tenant_id": tenant_id, "days": days})
        rows = self.cursor.fetchall() or []
        columns = [desc[0] for desc in self.cursor.description] if self.cursor.description else []
        results = [dict(zip(columns, row)) for row in rows]
        # Return in ascending chronological order for charts
        return list(reversed(results))

    def get_top_products(self, tenant_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Query fact_orders and dim_product for top revenue products scoped to tenant_id.
        """
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
            WHERE fo.tenant_id = :tenant_id
            GROUP BY p.product_id, p.product_name, p.category
            ORDER BY total_revenue DESC
            LIMIT :limit
        """
        self.cursor.execute(query, {"tenant_id": tenant_id, "limit": limit})
        rows = self.cursor.fetchall() or []
        columns = [desc[0] for desc in self.cursor.description] if self.cursor.description else []
        return [dict(zip(columns, row)) for row in rows]

    def get_late_delivery_risk(self, tenant_id: int) -> Dict[str, Any]:
        """
        Query fact_shipments and dim_delivery_status for overall late delivery rate and status breakdown.
        """
        overview_q = f"""
            SELECT
                count(*) AS total_shipments,
                sum(CASE WHEN late_flag THEN 1 ELSE 0 END) AS late_shipments,
                sum(CASE WHEN NOT late_flag THEN 1 ELSE 0 END) AS on_time_shipments,
                round(avg(coalesce(shipping_days, 0)), 2) AS avg_shipping_days
            FROM {self.fact_shipments_table}
            WHERE tenant_id = :tenant_id
        """
        self.cursor.execute(overview_q, {"tenant_id": tenant_id})
        overview_row = self.cursor.fetchone()
        columns_ov = [desc[0] for desc in self.cursor.description] if self.cursor.description else []
        overview_data = dict(zip(columns_ov, overview_row)) if overview_row else {}

        breakdown_q = f"""
            SELECT
                coalesce(ds.status_name, 'Unknown') AS status_name,
                count(*) AS total_shipments,
                sum(CASE WHEN fs.late_flag THEN 1 ELSE 0 END) AS late_shipments,
                round(sum(CASE WHEN fs.late_flag THEN 1.0 ELSE 0.0 END) / count(*) * 100.0, 2) AS late_rate_pct
            FROM {self.fact_shipments_table} fs
            LEFT JOIN {self.dim_delivery_status_table} ds ON fs.delivery_status_id = ds.delivery_status_id
            WHERE fs.tenant_id = :tenant_id
            GROUP BY ds.status_name
            ORDER BY total_shipments DESC
        """
        self.cursor.execute(breakdown_q, {"tenant_id": tenant_id})
        bd_rows = self.cursor.fetchall() or []
        columns_bd = [desc[0] for desc in self.cursor.description] if self.cursor.description else []
        breakdown_list = [dict(zip(columns_bd, r)) for r in bd_rows]

        return {
            "overview": overview_data,
            "breakdown": breakdown_list,
        }

    def get_discount_vs_profit(self, tenant_id: int) -> List[Dict[str, Any]]:
        """
        Query fact_orders to group sales and gross profit by discount bands.
        """
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
            WHERE tenant_id = :tenant_id
            GROUP BY 1
            ORDER BY 1
        """
        self.cursor.execute(query, {"tenant_id": tenant_id})
        rows = self.cursor.fetchall() or []
        columns = [desc[0] for desc in self.cursor.description] if self.cursor.description else []
        return [dict(zip(columns, row)) for row in rows]

    def get_shipping_mode_comparison(self, tenant_id: int) -> List[Dict[str, Any]]:
        """
        Query fact_shipments and dim_shipping_mode for volume and SLA performance across channels.
        """
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
            WHERE fs.tenant_id = :tenant_id
            GROUP BY sm.mode_name
            ORDER BY shipment_count DESC
        """
        self.cursor.execute(query, {"tenant_id": tenant_id})
        rows = self.cursor.fetchall() or []
        columns = [desc[0] for desc in self.cursor.description] if self.cursor.description else []
        return [dict(zip(columns, row)) for row in rows]
