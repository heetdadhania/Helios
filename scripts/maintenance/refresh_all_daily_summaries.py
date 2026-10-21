import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO_ROOT, "backend"))
from app.db.base import get_databricks_connection
from app.core.config import settings

CATALOG = getattr(settings, "DATABRICKS_CATALOG", "helios_catalog")

def main():
    print(f"Refreshing fact_orders_daily_summary for all active tenants in {CATALOG}...")
    with get_databricks_connection(catalog=CATALOG) as conn:
        with conn.cursor() as cur:
            cur.execute(f"""
                MERGE INTO `{CATALOG}`.`gold`.`fact_orders_daily_summary` AS target
                USING (
                    SELECT
                        tenant_id,
                        date_id,
                        count(DISTINCT source_order_id) AS total_orders,
                        round(sum(coalesce(total, 0.0000)), 4) AS total_revenue,
                        round(sum(coalesce(total, 0.0000)) / count(DISTINCT source_order_id), 4) AS avg_order_value,
                        sum(coalesce(quantity, 0)) AS total_quantity
                    FROM `{CATALOG}`.`gold`.`fact_orders`
                    GROUP BY tenant_id, date_id
                ) AS source
                ON target.tenant_id = source.tenant_id AND target.date_id = source.date_id
                WHEN MATCHED THEN
                    UPDATE SET
                        target.total_orders = source.total_orders,
                        target.total_revenue = source.total_revenue,
                        target.avg_order_value = source.avg_order_value,
                        target.total_quantity = source.total_quantity,
                        target.updated_at = current_timestamp()
                WHEN NOT MATCHED THEN
                    INSERT (tenant_id, date_id, total_orders, total_revenue, avg_order_value, total_quantity, updated_at)
                    VALUES (source.tenant_id, source.date_id, source.total_orders, source.total_revenue, source.avg_order_value, source.total_quantity, current_timestamp())
            """)
            print("Successfully refreshed fact_orders_daily_summary!")

if __name__ == "__main__":
    main()
