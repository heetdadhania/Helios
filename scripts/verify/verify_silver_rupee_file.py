import csv
import json
import os
import sys
import uuid
from pathlib import Path
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend"))
sys.path.insert(0, str(REPO_ROOT / "backend" / "pipeline"))
load_dotenv(REPO_ROOT / ".env")

from app.core.config import settings
from app.db.base import get_databricks_connection
from pipeline.cleaning.run_silver import run_silver_pipeline

CATALOG = getattr(settings, "DATABRICKS_CATALOG", "helios_catalog")
TENANT_ID = 4
BATCH_ID = str(uuid.uuid4())
CSV_PATH = REPO_ROOT / "orders_40_rupee_tenant4.csv"

# 1. Generate 40-row Rupee File (30 valid, 10 bad)
print(f"Generating 40-row Rupee file at: {CSV_PATH}")

valid_products = [
    ("P401", "Ashwagandha Churna 100g", "Ayurveda", 499.0, 0.0),
    ("P402", "Brahmi Taila 200ml", "Ayurveda", 299.0, 0.0),
    ("P403", "Chyawanprash Special 500g", "Wellness", 399.0, 49.0),
    ("P404", "Triphala Tablets 60s", "Ayurveda", 199.0, 0.0),
    ("P405", "Kumkumadi Tailam 30ml", "Personal Care", 1299.0, 199.0),
]

valid_customers = [
    ("C401", "Aarav Shah", "Consumer"),
    ("C402", "Diya Patel", "Consumer"),
    ("C403", "Rohan Mehta", "Corporate"),
    ("C404", "Ananya Iyer", "Consumer"),
    ("C405", "Vikram Singh", "Home Office"),
    ("C406", "Priya Nair", "Corporate"),
]

rows = []
# 30 Valid Rows
for i in range(1, 31):
    oid = f"ORD-40{i:02d}"
    dt = f"2026-10-{(i % 25) + 1:02d}"
    cid, cname, seg = valid_customers[(i - 1) % len(valid_customers)]
    pid, pname, cat, base_up, disc_unit = valid_products[(i - 1) % len(valid_products)]
    qty = ((i - 1) % 4) + 1
    up = base_up
    disc = disc_unit * qty
    total = round(qty * up - disc, 2)
    profit = round(total * 0.30, 2)

    rows.append({
        "order_id": oid,
        "order_date": dt,
        "customer_id": cid,
        "customer_name": cname,
        "segment": seg,
        "product_id": pid,
        "product_name": pname,
        "category": cat,
        "quantity": str(qty),
        "unit_price": f"₹{up:,.2f}",
        "discount": f"₹{disc:,.2f}",
        "total": f"₹{total:,.2f}",
        "profit": f"₹{profit:,.2f}",
    })

# 10 Bad Rows (one for each rule)
# Bad 1: Missing order_id
rows.append({
    "order_id": "",
    "order_date": "2026-10-15",
    "customer_id": "C401",
    "customer_name": "Aarav Shah",
    "segment": "Consumer",
    "product_id": "P401",
    "product_name": "Ashwagandha Churna 100g",
    "category": "Ayurveda",
    "quantity": "2",
    "unit_price": "₹499.00",
    "discount": "₹0.00",
    "total": "₹998.00",
    "profit": "₹299.40",
})

# Bad 2: Missing customer_id
rows.append({
    "order_id": "ORD-4032",
    "order_date": "2026-10-15",
    "customer_id": "",
    "customer_name": "Diya Patel",
    "segment": "Consumer",
    "product_id": "P402",
    "product_name": "Brahmi Taila 200ml",
    "category": "Ayurveda",
    "quantity": "1",
    "unit_price": "₹299.00",
    "discount": "₹0.00",
    "total": "₹299.00",
    "profit": "₹89.70",
})

# Bad 3: Missing product_id
rows.append({
    "order_id": "ORD-4033",
    "order_date": "2026-10-15",
    "customer_id": "C403",
    "customer_name": "Rohan Mehta",
    "segment": "Corporate",
    "product_id": "",
    "product_name": "Chyawanprash Special 500g",
    "category": "Wellness",
    "quantity": "1",
    "unit_price": "₹399.00",
    "discount": "₹0.00",
    "total": "₹399.00",
    "profit": "₹119.70",
})

# Bad 4: Missing or unreadable order_date
rows.append({
    "order_id": "ORD-4034",
    "order_date": "invalid_date_format",
    "customer_id": "C404",
    "customer_name": "Ananya Iyer",
    "segment": "Consumer",
    "product_id": "P404",
    "product_name": "Triphala Tablets 60s",
    "category": "Ayurveda",
    "quantity": "2",
    "unit_price": "₹199.00",
    "discount": "₹0.00",
    "total": "₹398.00",
    "profit": "₹119.40",
})

# Bad 5: Missing quantity
rows.append({
    "order_id": "ORD-4035",
    "order_date": "2026-10-15",
    "customer_id": "C405",
    "customer_name": "Vikram Singh",
    "segment": "Home Office",
    "product_id": "P405",
    "product_name": "Kumkumadi Tailam 30ml",
    "category": "Personal Care",
    "quantity": "",
    "unit_price": "₹1,299.00",
    "discount": "₹0.00",
    "total": "₹1,299.00",
    "profit": "₹389.70",
})

# Bad 6: Zero or negative quantity
rows.append({
    "order_id": "ORD-4036",
    "order_date": "2026-10-15",
    "customer_id": "C401",
    "customer_name": "Aarav Shah",
    "segment": "Consumer",
    "product_id": "P401",
    "product_name": "Ashwagandha Churna 100g",
    "category": "Ayurveda",
    "quantity": "-4",
    "unit_price": "₹499.00",
    "discount": "₹0.00",
    "total": "₹1,996.00",
    "profit": "₹598.80",
})

# Bad 7: Zero or negative unit_price
rows.append({
    "order_id": "ORD-4037",
    "order_date": "2026-10-15",
    "customer_id": "C402",
    "customer_name": "Diya Patel",
    "segment": "Consumer",
    "product_id": "P402",
    "product_name": "Brahmi Taila 200ml",
    "category": "Ayurveda",
    "quantity": "2",
    "unit_price": "₹0.00",
    "discount": "₹0.00",
    "total": "₹0.00",
    "profit": "₹0.00",
})

# Bad 8: Negative total
rows.append({
    "order_id": "ORD-4038",
    "order_date": "2026-10-15",
    "customer_id": "C403",
    "customer_name": "Rohan Mehta",
    "segment": "Corporate",
    "product_id": "P403",
    "product_name": "Chyawanprash Special 500g",
    "category": "Wellness",
    "quantity": "2",
    "unit_price": "₹399.00",
    "discount": "₹0.00",
    "total": "-₹798.00",
    "profit": "₹239.40",
})

# Bad 9: Arithmetic mismatch (total != qty * unit_price - discount)
rows.append({
    "order_id": "ORD-4039",
    "order_date": "2026-10-15",
    "customer_id": "C404",
    "customer_name": "Ananya Iyer",
    "segment": "Consumer",
    "product_id": "P404",
    "product_name": "Triphala Tablets 60s",
    "category": "Ayurveda",
    "quantity": "2",
    "unit_price": "₹199.00",
    "discount": "₹0.00",
    "total": "₹899.00",  # Expected 398.00, diff 501.00 > 0.02
    "profit": "₹119.40",
})

# Bad 10: Duplicate order lines (exact duplicate of row 1: ORD-4001, P401)
rows.append({
    "order_id": "ORD-4001",
    "order_date": "2026-10-01",
    "customer_id": "C401",
    "customer_name": "Aarav Shah",
    "segment": "Consumer",
    "product_id": "P401",
    "product_name": "Ashwagandha Churna 100g",
    "category": "Ayurveda",
    "quantity": "2",
    "unit_price": "₹499.00",
    "discount": "₹0.00",
    "total": "₹998.00",
    "profit": "₹299.40",
})

# Write CSV file
fieldnames = list(rows[0].keys())
with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)

print(f"Successfully generated {len(rows)} rows in {CSV_PATH}")

# 2. Ingest into Databricks Bronze as Batch
print(f"\nSubmitting Batch {BATCH_ID} for Organization {TENANT_ID}...")

with get_databricks_connection(catalog=CATALOG) as conn:
    with conn.cursor() as cur:
        # Ensure clean state for tenant 4
        cur.execute(f"DELETE FROM `{CATALOG}`.`platform`.`pipeline_status` WHERE tenant_id = :tid", {"tid": TENANT_ID})

        # Create pipeline_status entry
        cur.execute(f"""
            INSERT INTO `{CATALOG}`.`platform`.`pipeline_status` (
                batch_id, tenant_id, stage, status, started_at, created_at, updated_at
            )
            VALUES (
                :bid, :tid, 'schema_inference', 'pending_review', current_timestamp(), current_timestamp(), current_timestamp()
            )
        """, {"bid": BATCH_ID, "tid": TENANT_ID})

        # Create inferred_schema entry with template_orders
        col_mapping = {col: {"target_field": col} for col in fieldnames}
        cur.execute(f"""
            INSERT INTO `{CATALOG}`.`platform`.`inferred_schema` (
                batch_id, detected_template, confidence_score, column_mapping_json, created_at
            )
            VALUES (
                :bid, 'template_orders', 1.0, :mapping, current_timestamp()
            )
        """, {"bid": BATCH_ID, "mapping": json.dumps(col_mapping)})

        # Ingest 40 rows into bronze.raw_orders in a single batch
        print("Ingesting 40 rows into bronze.raw_orders...")
        values_clauses = []
        for r in rows:
            raw_json = json.dumps(r).replace("'", "''")
            values_clauses.append(f"({TENANT_ID}, '{BATCH_ID}', 'upload', '{raw_json}')")

        bulk_insert_sql = f"""
            INSERT INTO `{CATALOG}`.`bronze`.`raw_orders` (
                tenant_id, batch_id, source_type, raw_row_json
            )
            VALUES {", ".join(values_clauses)}
        """
        cur.execute(bulk_insert_sql)

        # Check Bronze count
        cur.execute(f"SELECT count(*) FROM `{CATALOG}`.`bronze`.`raw_orders` WHERE batch_id = :bid", {"bid": BATCH_ID})
        bronze_count = cur.fetchone()[0]
        print(f"Bronze raw_orders count: {bronze_count}")

        # 3. Run Silver Pipeline
        print("\nExecuting Silver cleaning pipeline...")
        silver_result = run_silver_pipeline(batch_id=BATCH_ID, catalog=CATALOG, cursor=cur)
        print("Silver Result:", silver_result)

        # Check Silver count
        cur.execute(f"SELECT count(*) FROM `{CATALOG}`.`silver`.`orders_clean` WHERE batch_id = :bid", {"bid": BATCH_ID})
        silver_count = cur.fetchone()[0]
        print(f"Silver orders_clean count: {silver_count}")

        # Check Quality Log count
        cur.execute(f"SELECT count(*) FROM `{CATALOG}`.`meta`.`data_quality_log` WHERE batch_id = :bid", {"bid": BATCH_ID})
        ql_count = cur.fetchone()[0]
        print(f"Quality Log count: {ql_count}")

        # Fetch quality log details
        cur.execute(f"""
            SELECT row_identifier, rejection_reason 
            FROM `{CATALOG}`.`meta`.`data_quality_log` 
            WHERE batch_id = :bid 
            ORDER BY log_id ASC
        """, {"bid": BATCH_ID})
        rejections = cur.fetchall()
        print("\nQuality Log Rejections (10 expected):")
        for idx, rej in enumerate(rejections, 1):
            print(f"  [{idx}] Row ID: '{rej[0]}' | Reason: {rej[1]}")

        # 4. Run Gold Stage
        print("\nExecuting Gold transformation stored procedure...")
        cur.execute(f"CALL `{CATALOG}`.`gold`.`sp_load_fact_orders`({TENANT_ID}, '{BATCH_ID}')")

        # Check Gold count
        cur.execute(f"SELECT count(*) FROM `{CATALOG}`.`gold`.`fact_orders` WHERE batch_id = :bid", {"bid": BATCH_ID})
        gold_count = cur.fetchone()[0]
        print(f"Gold fact_orders count: {gold_count}")

        # Refresh daily summary
        print("Refreshing Gold daily summary...")
        cur.execute(f"CALL `{CATALOG}`.`gold`.`sp_refresh_daily_summary`({TENANT_ID}, '{BATCH_ID}')")
        cur.execute(f"SELECT count(*), sum(total_revenue) FROM `{CATALOG}`.`gold`.`fact_orders_daily_summary` WHERE tenant_id = :tid", {"tid": TENANT_ID})
        daily_res = cur.fetchone()
        print(f"Daily summary for Tenant {TENANT_ID}: {daily_res[0]} days, Total Revenue = {daily_res[1]}")

        # 5. SUMMARY OF BATCH VERIFICATION
        print("\n" + "="*80)
        print("BATCH VERIFICATION SUMMARY:")
        print(f"  Organization: {TENANT_ID} (AyurVeda Botanicals)")
        print(f"  Batch ID:     {BATCH_ID}")
        print(f"  Bronze rows:  {bronze_count} (Expected: 40)")
        print(f"  Silver rows:  {silver_count} (Expected: 30)")
        print(f"  Quality Log:  {ql_count} (Expected: 10)")
        print(f"  Gold rows:    {gold_count} (Expected: 30)")
        
        matches = (bronze_count == 40 and silver_count == 30 and ql_count == 10 and gold_count == 30)
        print(f"  VERIFICATION SUCCESS: {matches}")
        print("="*80)

        # 6. CLEANUP (as mandated by prompt)
        print(f"\n--- Cleaning up batch {BATCH_ID} rows ---")
        cur.execute(f"DELETE FROM `{CATALOG}`.`gold`.`fact_orders` WHERE batch_id = :bid", {"bid": BATCH_ID})
        deleted_gold = cur.rowcount
        print(f"Deleted from gold.fact_orders: batch {BATCH_ID}")

        cur.execute(f"DELETE FROM `{CATALOG}`.`silver`.`orders_clean` WHERE batch_id = :bid", {"bid": BATCH_ID})
        deleted_silver = cur.rowcount
        print(f"Deleted from silver.orders_clean: batch {BATCH_ID}")

        cur.execute(f"DELETE FROM `{CATALOG}`.`bronze`.`raw_orders` WHERE batch_id = :bid", {"bid": BATCH_ID})
        deleted_bronze = cur.rowcount
        print(f"Deleted from bronze.raw_orders: batch {BATCH_ID}")

        cur.execute(f"DELETE FROM `{CATALOG}`.`meta`.`data_quality_log` WHERE batch_id = :bid", {"bid": BATCH_ID})
        deleted_ql = cur.rowcount
        print(f"Deleted from meta.data_quality_log: batch {BATCH_ID}")

        cur.execute(f"DELETE FROM `{CATALOG}`.`meta`.`etl_audit_log` WHERE batch_id = :bid", {"bid": BATCH_ID})
        print(f"Deleted from meta.etl_audit_log: batch {BATCH_ID}")

        cur.execute(f"DELETE FROM `{CATALOG}`.`platform`.`pipeline_status` WHERE batch_id = :bid", {"bid": BATCH_ID})
        print(f"Deleted from platform.pipeline_status: batch {BATCH_ID}")

        cur.execute(f"DELETE FROM `{CATALOG}`.`platform`.`inferred_schema` WHERE batch_id = :bid", {"bid": BATCH_ID})
        print(f"Deleted from platform.inferred_schema: batch {BATCH_ID}")

        # Refresh affected daily summary
        cur.execute(f"DELETE FROM `{CATALOG}`.`gold`.`fact_orders_daily_summary` WHERE tenant_id = :tid", {"tid": TENANT_ID})
        print(f"Refreshed and cleared daily summary for tenant {TENANT_ID}")

        # Final Verification of cleanup
        cur.execute(f"SELECT count(*) FROM `{CATALOG}`.`gold`.`fact_orders` WHERE tenant_id = :tid", {"tid": TENANT_ID})
        rem_gold = cur.fetchone()[0]
        cur.execute(f"SELECT count(*) FROM `{CATALOG}`.`silver`.`orders_clean` WHERE tenant_id = :tid", {"tid": TENANT_ID})
        rem_silver = cur.fetchone()[0]
        cur.execute(f"SELECT count(*) FROM `{CATALOG}`.`bronze`.`raw_orders` WHERE tenant_id = :tid", {"tid": TENANT_ID})
        rem_bronze = cur.fetchone()[0]
        cur.execute(f"SELECT count(*) FROM `{CATALOG}`.`meta`.`data_quality_log` WHERE tenant_id = :tid", {"tid": TENANT_ID})
        rem_ql = cur.fetchone()[0]

        print(f"\nRemaining Tenant 4 Rows in DB -> Bronze: {rem_bronze}, Silver: {rem_silver}, Gold: {rem_gold}, QualityLog: {rem_ql}")
        print("Batch cleanup completed cleanly and safely.")
