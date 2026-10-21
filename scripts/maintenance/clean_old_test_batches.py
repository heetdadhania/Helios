import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO_ROOT, "backend"))
from app.db.base import get_databricks_connection
from app.core.config import settings

CATALOG = getattr(settings, "DATABRICKS_CATALOG", "helios_catalog")

def main():
    print(f"Cleaning older test batches 74604503 and df6cecb5 in {CATALOG}...")
    with get_databricks_connection(catalog=CATALOG) as conn:
        with conn.cursor() as cur:
            # 1. Remove 74604503 (tenant 1 old batch) from fact_orders
            cur.execute(f"DELETE FROM `{CATALOG}`.`gold`.`fact_orders` WHERE batch_id = '74604503-4d00-4d6b-8eb9-e9025bb762a9'")
            print("  Deleted batch 74604503 from gold.fact_orders")

            # 1b. Remove 98dbb5bd (tenant 1 old shipping batch) from fact_shipments
            cur.execute(f"DELETE FROM `{CATALOG}`.`gold`.`fact_shipments` WHERE batch_id = '98dbb5bd-5d43-459c-8e1a-a94ef1da2219'")
            print("  Deleted batch 98dbb5bd from gold.fact_shipments")

            # 2. Remove df6cecb5 (tenant 2 old batch) from fact_orders
            cur.execute(f"DELETE FROM `{CATALOG}`.`gold`.`fact_orders` WHERE batch_id = 'df6cecb5-9308-4bdb-8aed-1d520d465319'")
            print("  Deleted batch df6cecb5 from gold.fact_orders")

            # 3. Clean tenant 2 from gold.fact_orders_daily_summary
            cur.execute(f"DELETE FROM `{CATALOG}`.`gold`.`fact_orders_daily_summary` WHERE tenant_id = 2")
            print("  Deleted tenant 2 from gold.fact_orders_daily_summary")

            # 4. Refresh tenant 1 daily summary from remaining fact_orders (batch 92274a99)
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
                    WHERE tenant_id = 1
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
            print("  Refreshed tenant 1 in gold.fact_orders_daily_summary")

            # Also delete pipeline_status for df6cecb5 so tenant 2 is seen as needing ingest
            cur.execute(f"DELETE FROM `{CATALOG}`.`platform`.`pipeline_status` WHERE batch_id = 'df6cecb5-9308-4bdb-8aed-1d520d465319'")
            cur.execute(f"DELETE FROM `{CATALOG}`.`platform`.`pipeline_status` WHERE batch_id = '74604503-4d00-4d6b-8eb9-e9025bb762a9'")
            print("  Deleted old pipeline_status rows")

    print("Cleanup complete!")

if __name__ == "__main__":
    main()
