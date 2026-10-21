"""
Verification script for Step 4 of Helios Silver validation task:
- Generates a 40-row rupee CSV file (30 valid and 10 bad rows, one for each rule)
- Submits as a new batch for Organization 4
- Confirms schema mapping and runs Medallion Silver + Gold pipeline
- Verifies: Bronze 40, Silver 30, Quality Log 10, Gold 30
- Inspects the 10 quality log entries (row identifier, rejection reason, original value)
- Removes only that batch's rows, refreshes the affected daily summary, and reports exactly what was removed
"""

import csv
import io
import json
import os
import sys
import time
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO_ROOT, "backend"))

import requests
from dotenv import load_dotenv

load_dotenv()
load_dotenv(os.path.join(REPO_ROOT, ".env"))
load_dotenv(os.path.join(REPO_ROOT, "backend", ".env"))

from app.core.config import settings
from app.db.base import get_databricks_connection

CATALOG = getattr(settings, "DATABRICKS_CATALOG", "helios_catalog")
BASE_URL = "http://127.0.0.1:8000"
TENANT_ID = 4
CSV_FILE_PATH = os.path.join(REPO_ROOT, "orders_40_rupee_org4.csv")


def generate_40_row_file():
    """
    Generate 40-row Indian rupee file for Organization 4:
    - 30 valid rows
    - 10 bad rows, one for each rule:
      1. Missing order_id
      2. Missing customer_id
      3. Missing product_id
      4. Missing or unreadable order_date ("unreadable-date")
      5. Missing quantity
      6. Zero or negative quantity (-2)
      7. Zero or negative unit_price (₹0.00)
      8. Missing or negative total (-₹500.00)
      9. Arithmetic mismatch (total != quantity * unit_price - discount, diff > ₹0.02)
      10. Duplicate order lines (composite key duplicate)
    """
    headers = [
        "order_id",
        "order_date",
        "customer_id",
        "customer_name",
        "segment",
        "product_id",
        "product_name",
        "category",
        "quantity",
        "unit_price",
        "discount",
        "total",
        "profit",
    ]

    rows = []

    # 30 Valid Rows
    products = [
        ("P-401", "Kumkumadi Tailam", "Skincare", 1299.00, 259.80),
        ("P-402", "Bhringraj Hair Oil", "Hair Care", 599.00, 119.80),
        ("P-403", "Neem Body Wash", "Personal Care", 349.00, 69.80),
        ("P-404", "Aloe Vera Gel", "Skincare", 299.00, 59.80),
        ("P-405", "Sandalwood Soap", "Personal Care", 199.00, 39.80),
        ("P-406", "Herbal Shampoo", "Hair Care", 499.00, 99.80),
    ]

    customers = [
        ("C-401", "Meera Nair", "Consumer"),
        ("C-402", "Aarav Sharma", "Corporate"),
        ("C-403", "Priya Nair", "Consumer"),
        ("C-404", "Vikram Singh", "Home Office"),
        ("C-405", "Ananya Iyer", "Corporate"),
    ]

    for i in range(1, 31):
        order_id = f"ORD-ORG4-{1000 + i}"
        order_date = f"2026-10-15 10:{i:02d}:00"
        cust_id, cust_name, segment = customers[(i - 1) % len(customers)]
        prod_id, prod_name, cat, uprice, profit_unit = products[(i - 1) % len(products)]
        qty = ((i - 1) % 4) + 1  # 1 to 4
        disc = 50.00 if i % 3 == 0 else 0.00
        total = round(qty * uprice - disc, 2)
        profit = round(qty * profit_unit, 2)

        rows.append({
            "order_id": order_id,
            "order_date": order_date,
            "customer_id": cust_id,
            "customer_name": cust_name,
            "segment": segment,
            "product_id": prod_id,
            "product_name": prod_name,
            "category": cat,
            "quantity": str(qty),
            "unit_price": f"₹{uprice:,.2f}",
            "discount": f"₹{disc:,.2f}",
            "total": f"₹{total:,.2f}",
            "profit": f"₹{profit:,.2f}",
        })

    # 10 Bad Rows (one for each rule)
    bad_rows_meta = [
        # Bad Row 1 (Rule: missing order_id)
        {
            "order_id": "",
            "order_date": "2026-10-15 11:01:00",
            "customer_id": "C-401",
            "customer_name": "Meera Nair",
            "segment": "Consumer",
            "product_id": "P-401",
            "product_name": "Kumkumadi Tailam",
            "category": "Skincare",
            "quantity": "1",
            "unit_price": "₹1,299.00",
            "discount": "₹0.00",
            "total": "₹1,299.00",
            "profit": "₹259.80",
            "_rule": "Missing order_id",
        },
        # Bad Row 2 (Rule: missing customer_id)
        {
            "order_id": "ORD-ORG4-BAD-02",
            "order_date": "2026-10-15 11:02:00",
            "customer_id": "",
            "customer_name": "Meera Nair",
            "segment": "Consumer",
            "product_id": "P-402",
            "product_name": "Bhringraj Hair Oil",
            "category": "Hair Care",
            "quantity": "2",
            "unit_price": "₹599.00",
            "discount": "₹0.00",
            "total": "₹1,198.00",
            "profit": "₹239.60",
            "_rule": "Missing customer_id",
        },
        # Bad Row 3 (Rule: missing product_id)
        {
            "order_id": "ORD-ORG4-BAD-03",
            "order_date": "2026-10-15 11:03:00",
            "customer_id": "C-403",
            "customer_name": "Priya Nair",
            "segment": "Consumer",
            "product_id": "",
            "product_name": "Neem Body Wash",
            "category": "Personal Care",
            "quantity": "1",
            "unit_price": "₹349.00",
            "discount": "₹0.00",
            "total": "₹349.00",
            "profit": "₹69.80",
            "_rule": "Missing product_id",
        },
        # Bad Row 4 (Rule: missing or unreadable order_date)
        {
            "order_id": "ORD-ORG4-BAD-04",
            "order_date": "unreadable-date",
            "customer_id": "C-404",
            "customer_name": "Vikram Singh",
            "segment": "Home Office",
            "product_id": "P-404",
            "product_name": "Aloe Vera Gel",
            "category": "Skincare",
            "quantity": "1",
            "unit_price": "₹299.00",
            "discount": "₹0.00",
            "total": "₹299.00",
            "profit": "₹59.80",
            "_rule": "Missing/unreadable order_date",
        },
        # Bad Row 5 (Rule: missing quantity)
        {
            "order_id": "ORD-ORG4-BAD-05",
            "order_date": "2026-10-15 11:05:00",
            "customer_id": "C-405",
            "customer_name": "Ananya Iyer",
            "segment": "Corporate",
            "product_id": "P-405",
            "product_name": "Sandalwood Soap",
            "category": "Personal Care",
            "quantity": "",
            "unit_price": "₹199.00",
            "discount": "₹0.00",
            "total": "₹199.00",
            "profit": "₹39.80",
            "_rule": "Missing quantity",
        },
        # Bad Row 6 (Rule: zero or negative quantity)
        {
            "order_id": "ORD-ORG4-BAD-06",
            "order_date": "2026-10-15 11:06:00",
            "customer_id": "C-401",
            "customer_name": "Meera Nair",
            "segment": "Consumer",
            "product_id": "P-406",
            "product_name": "Herbal Shampoo",
            "category": "Hair Care",
            "quantity": "-2",
            "unit_price": "₹499.00",
            "discount": "₹0.00",
            "total": "₹998.00",
            "profit": "₹199.60",
            "_rule": "Zero or negative quantity",
        },
        # Bad Row 7 (Rule: zero or negative unit_price)
        {
            "order_id": "ORD-ORG4-BAD-07",
            "order_date": "2026-10-15 11:07:00",
            "customer_id": "C-402",
            "customer_name": "Aarav Sharma",
            "segment": "Corporate",
            "product_id": "P-401",
            "product_name": "Kumkumadi Tailam",
            "category": "Skincare",
            "quantity": "1",
            "unit_price": "₹0.00",
            "discount": "₹0.00",
            "total": "₹0.00",
            "profit": "₹0.00",
            "_rule": "Zero or negative unit_price",
        },
        # Bad Row 8 (Rule: missing or negative total)
        {
            "order_id": "ORD-ORG4-BAD-08",
            "order_date": "2026-10-15 11:08:00",
            "customer_id": "C-403",
            "customer_name": "Priya Nair",
            "segment": "Consumer",
            "product_id": "P-402",
            "product_name": "Bhringraj Hair Oil",
            "category": "Hair Care",
            "quantity": "1",
            "unit_price": "₹599.00",
            "discount": "₹0.00",
            "total": "-₹500.00",
            "profit": "₹119.80",
            "_rule": "Missing or negative total",
        },
        # Bad Row 9 (Rule: total != qty * unit_price - discount, diff > ₹0.02)
        {
            "order_id": "ORD-ORG4-BAD-09",
            "order_date": "2026-10-15 11:09:00",
            "customer_id": "C-404",
            "customer_name": "Vikram Singh",
            "segment": "Home Office",
            "product_id": "P-403",
            "product_name": "Neem Body Wash",
            "category": "Personal Care",
            "quantity": "2",
            "unit_price": "₹349.00",
            "discount": "₹50.00",
            "total": "₹1,800.00",  # expected 2*349 - 50 = 648 != 1800
            "profit": "₹139.60",
            "_rule": "Total not equal to qty * unit_price - discount",
        },
        # Bad Row 10 (Rule: duplicate order lines)
        {
            "order_id": "ORD-ORG4-1001",  # Same as valid row 1!
            "order_date": "2026-10-15 11:10:00",
            "customer_id": "C-401",
            "customer_name": "Meera Nair",
            "segment": "Consumer",
            "product_id": "P-401",  # Same product as valid row 1!
            "product_name": "Kumkumadi Tailam",
            "category": "Skincare",
            "quantity": "1",
            "unit_price": "₹1,299.00",
            "discount": "₹0.00",
            "total": "₹1,299.00",
            "profit": "₹259.80",
            "_rule": "Duplicate order lines",
        },
    ]

    for br in bad_rows_meta:
        clean_row = {k: v for k, v in br.items() if not k.startswith("_")}
        rows.append(clean_row)

    with open(CSV_FILE_PATH, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Generated 40-row rupee CSV file at {CSV_FILE_PATH}:")
    print(f"  Valid rows: 30")
    print(f"  Bad rows: 10 (one for each rule)")
    for idx, br in enumerate(bad_rows_meta, 1):
        print(f"    Bad Row {idx:2d}: {br['_rule']:40s} | order_id={br['order_id']!r}")

    return CSV_FILE_PATH, bad_rows_meta


def run_verification():
    print("=" * 80)
    print("STEP 4 VERIFICATION: 40-ROW RUPEE FILE FOR ORGANIZATION 4")
    print("=" * 80)

    # 1. Generate file
    csv_path, bad_rows_meta = generate_40_row_file()

    # 2. Login as Admin
    admin_pw = os.environ.get("ADMIN_PASSWORD")
    if not admin_pw:
        raise ValueError("ADMIN_PASSWORD environment variable is not set")

    print("\n--- Logging in as Admin ---")
    login_resp = requests.post(
        f"{BASE_URL}/api/v1/auth/login",
        json={"email": "admin@helios.io", "password": admin_pw},
        timeout=60,
    )
    assert login_resp.status_code == 200, f"Admin login failed: {login_resp.text}"
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("Admin login successful!")

    # 3. Check for existing pending_review batch or upload new file for Tenant 4
    batch_id = None
    upload_id = None

    with get_databricks_connection(catalog=CATALOG) as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT batch_id, upload_id FROM `{CATALOG}`.`platform`.`pipeline_status`
                WHERE tenant_id = {TENANT_ID} AND status = 'pending_review'
                ORDER BY created_at DESC LIMIT 1
                """
            )
            existing_batch = cur.fetchone()
            if existing_batch:
                batch_id = existing_batch[0]
                upload_id = existing_batch[1]
                print(f"Found existing pending_review batch for Org {TENANT_ID}: batch_id={batch_id}, upload_id={upload_id}")

    if not batch_id:
        print(f"\n--- Uploading 40-row file for Organization {TENANT_ID} ---")
        with open(csv_path, "rb") as f:
            files = {"file": ("orders_40_rupee_org4.csv", f, "text/csv")}
            data = {"tenant_id": str(TENANT_ID)}
            upload_resp = requests.post(
                f"{BASE_URL}/api/v1/uploads",
                headers=headers,
                files=files,
                data=data,
                timeout=120,
            )
        assert upload_resp.status_code == 201, f"Upload failed: {upload_resp.text}"
        upload_data = upload_resp.json()
        batch_id = upload_data["batch_id"]
        upload_id = upload_data["upload_id"]
        print(f"Upload created: upload_id={upload_id}, batch_id={batch_id}")

        # 4. Wait for bronze_ingest and schema_inference to complete
        print("\n--- Waiting for Bronze ingestion and schema inference ---")
        for _ in range(60):
            time.sleep(2)
            with get_databricks_connection(catalog=CATALOG) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        f"SELECT stage, status FROM `{CATALOG}`.`platform`.`pipeline_status` WHERE batch_id = :batch_id",
                        {"batch_id": batch_id},
                    )
                    row = cur.fetchone()
                    if row and row[0] == "schema_inference" and row[1] == "pending_review":
                        print(f"Batch {batch_id} ready for review: stage={row[0]}, status={row[1]}")
                        break
        else:
            raise TimeoutError(f"Batch {batch_id} did not reach pending_review status in time")

    # 5. Confirm schema mapping to launch Silver and Gold
    print(f"\n--- Confirming schema mapping for batch {batch_id} ---")
    confirm_resp = requests.post(
        f"{BASE_URL}/api/v1/uploads/{batch_id}/confirm",
        headers=headers,
        json={
            "confirmed_template": "Retail & E-Commerce Orders",
            "corrected_mapping": {},
            "internal_notes": "Step 4 verification batch for organization 4",
        },
        timeout=120,
    )
    assert confirm_resp.status_code == 200, f"Confirm failed: {confirm_resp.text}"
    print(f"Batch confirmation response: {confirm_resp.json()}")

    # 6. Wait for pipeline execution to complete
    print("\n--- Waiting for Silver and Gold execution to complete ---")
    for _ in range(60):
        time.sleep(2)
        with get_databricks_connection(catalog=CATALOG) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"SELECT stage, status, error_message FROM `{CATALOG}`.`platform`.`pipeline_status` WHERE batch_id = :batch_id",
                    {"batch_id": batch_id},
                )
                row = cur.fetchone()
                if row and row[1] in ("success", "completed", "failed"):
                    print(f"Batch finished: stage={row[0]}, status={row[1]}, error={row[2]}")
                    assert row[1] in ("success", "completed"), f"Pipeline execution failed: {row[2]}"
                    break
    else:
        raise TimeoutError(f"Batch {batch_id} did not complete in time")

    # 7. Query and report all counts
    print("\n" + "=" * 80)
    print("STAGE COUNTS VERIFICATION FOR BATCH")
    print("=" * 80)

    with get_databricks_connection(catalog=CATALOG) as conn:
        with conn.cursor() as cur:
            # Bronze count
            cur.execute(
                f"SELECT count(*) FROM `{CATALOG}`.`bronze`.`raw_orders` WHERE batch_id = :batch_id",
                {"batch_id": batch_id},
            )
            bronze_count = cur.fetchone()[0]

            # Silver count
            cur.execute(
                f"SELECT count(*) FROM `{CATALOG}`.`silver`.`orders_clean` WHERE batch_id = :batch_id",
                {"batch_id": batch_id},
            )
            silver_count = cur.fetchone()[0]

            # Quality log count
            cur.execute(
                f"SELECT count(*) FROM `{CATALOG}`.`meta`.`data_quality_log` WHERE batch_id = :batch_id",
                {"batch_id": batch_id},
            )
            quality_log_count = cur.fetchone()[0]

            # Gold count
            cur.execute(
                f"SELECT count(*) FROM `{CATALOG}`.`gold`.`fact_orders` WHERE batch_id = :batch_id",
                {"batch_id": batch_id},
            )
            gold_count = cur.fetchone()[0]

            print(f"Bronze raw rows:   {bronze_count} (Expected: 40)")
            print(f"Silver clean rows: {silver_count} (Expected: 30)")
            print(f"Quality Log rows:  {quality_log_count} (Expected: 10)")
            print(f"Gold fact rows:    {gold_count} (Expected: 30)")

            assert bronze_count == 40, f"Expected Bronze 40, got {bronze_count}"
            assert silver_count == 30, f"Expected Silver 30, got {silver_count}"
            assert quality_log_count == 10, f"Expected Quality Log 10, got {quality_log_count}"
            assert gold_count == 30, f"Expected Gold 30, got {gold_count}"
            print("\nALL 4 ROW COUNT TARGETS MET: Bronze 40, Silver 30, Quality Log 10, Gold 30!")

            # 8. Detailed inspection of the 10 quality log rows
            print("\n" + "-" * 80)
            print("QUALITY LOG REJECTIONS DETAIL (10 BAD ROWS)")
            print("-" * 80)
            cur.execute(
                f"""
                SELECT row_identifier, rejection_reason, logged_at
                FROM `{CATALOG}`.`meta`.`data_quality_log`
                WHERE batch_id = :batch_id
                ORDER BY logged_at ASC
                """,
                {"batch_id": batch_id},
            )
            q_rows = cur.fetchall()
            for idx, r in enumerate(q_rows, 1):
                row_id, reason, logged_at = r[0], r[1], r[2]
                print(f"  [{idx:2d}] Row ID: {row_id:20s} | Reason: {reason}")

    # 9. Cleanup: Remove ONLY this batch's rows and refresh daily summary
    print("\n" + "=" * 80)
    print(f"CLEANUP: REMOVING ONLY BATCH {batch_id} ROWS FOR ORGANIZATION {TENANT_ID}")
    print("=" * 80)

    removed_summary = {}
    with get_databricks_connection(catalog=CATALOG) as conn:
        with conn.cursor() as cur:
            # Gold fact_orders
            cur.execute(
                f"DELETE FROM `{CATALOG}`.`gold`.`fact_orders` WHERE batch_id = :batch_id",
                {"batch_id": batch_id},
            )
            removed_summary["gold.fact_orders"] = gold_count
            print(f"  Removed {gold_count} rows from gold.fact_orders")

            # Silver orders_clean
            cur.execute(
                f"DELETE FROM `{CATALOG}`.`silver`.`orders_clean` WHERE batch_id = :batch_id",
                {"batch_id": batch_id},
            )
            removed_summary["silver.orders_clean"] = silver_count
            print(f"  Removed {silver_count} rows from silver.orders_clean")

            # Bronze raw_orders
            cur.execute(
                f"DELETE FROM `{CATALOG}`.`bronze`.`raw_orders` WHERE batch_id = :batch_id",
                {"batch_id": batch_id},
            )
            removed_summary["bronze.raw_orders"] = bronze_count
            print(f"  Removed {bronze_count} rows from bronze.raw_orders")

            # Quality log
            cur.execute(
                f"DELETE FROM `{CATALOG}`.`meta`.`data_quality_log` WHERE batch_id = :batch_id",
                {"batch_id": batch_id},
            )
            removed_summary["meta.data_quality_log"] = quality_log_count
            print(f"  Removed {quality_log_count} rows from meta.data_quality_log")

            # Audit log
            cur.execute(
                f"DELETE FROM `{CATALOG}`.`meta`.`etl_audit_log` WHERE batch_id = :batch_id",
                {"batch_id": batch_id},
            )
            print("  Removed batch audit log rows from meta.etl_audit_log")

            # Inferred schema
            cur.execute(
                f"DELETE FROM `{CATALOG}`.`platform`.`inferred_schema` WHERE batch_id = :batch_id",
                {"batch_id": batch_id},
            )
            print("  Removed batch row from platform.inferred_schema")

            # Pipeline status
            cur.execute(
                f"DELETE FROM `{CATALOG}`.`platform`.`pipeline_status` WHERE batch_id = :batch_id",
                {"batch_id": batch_id},
            )
            print("  Removed batch row from platform.pipeline_status")

            # Pending upload
            cur.execute(
                f"DELETE FROM `{CATALOG}`.`platform`.`pending_uploads` WHERE upload_id = :upload_id",
                {"upload_id": upload_id},
            )
            print(f"  Removed upload_id {upload_id} from platform.pending_uploads")

            # Refresh affected daily summary
            print("\n--- Refreshing affected daily summary for Organization 4 (date_id=20261015) ---")
            cur.execute(
                f"""
                DELETE FROM `{CATALOG}`.`gold`.`fact_orders_daily_summary`
                WHERE tenant_id = {TENANT_ID} AND date_id = 20261015
                """
            )
            # Run merge to ensure any other existing tenant 4 orders are rolled up
            cur.execute(
                f"""
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
                    WHERE tenant_id = {TENANT_ID}
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
                """
            )
            print("  Daily summary refreshed successfully!")

            # Verify baseline restoration
            cur.execute(f"SELECT count(*) FROM `{CATALOG}`.`bronze`.`raw_orders` WHERE tenant_id = {TENANT_ID}")
            post_bronze = cur.fetchone()[0]
            cur.execute(f"SELECT count(*) FROM `{CATALOG}`.`silver`.`orders_clean` WHERE tenant_id = {TENANT_ID}")
            post_silver = cur.fetchone()[0]
            cur.execute(f"SELECT count(*) FROM `{CATALOG}`.`gold`.`fact_orders` WHERE tenant_id = {TENANT_ID}")
            post_gold = cur.fetchone()[0]
            cur.execute(f"SELECT count(*) FROM `{CATALOG}`.`meta`.`data_quality_log` WHERE tenant_id = {TENANT_ID}")
            post_ql = cur.fetchone()[0]
            cur.execute(f"SELECT count(*) FROM `{CATALOG}`.`gold`.`fact_orders_daily_summary` WHERE tenant_id = {TENANT_ID}")
            post_ds = cur.fetchone()[0]

            print(f"\nFinal Organization {TENANT_ID} Counts after cleanup:")
            print(f"  Bronze raw_orders:          {post_bronze} (baseline: 0)")
            print(f"  Silver orders_clean:        {post_silver} (baseline: 0)")
            print(f"  Gold fact_orders:           {post_gold} (baseline: 0)")
            print(f"  Quality Log:                {post_ql} (baseline: 0)")
            print(f"  Fact Orders Daily Summary:  {post_ds} (baseline: 0)")

            assert post_bronze == 0
            assert post_silver == 0
            assert post_gold == 0
            assert post_ql == 0
            assert post_ds == 0
            print("\nBASELINE RESTORATION VERIFIED: All test rows cleanly removed!")

    print("\n" + "=" * 80)
    print("STEP 4 COMPLETED SUCCESSFULLY!")
    print("=" * 80)


if __name__ == "__main__":
    run_verification()
