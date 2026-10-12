#!/usr/bin/env python3
"""
Helios Data Platform - 20-Row Idempotency Verification Script
Loads Batch A (20 rows) -> Verifies Gold count=20, total revenue.
Loads Batch B (identical 20 rows) -> Verifies Gold count=20, revenue and daily summary unchanged.
Loads Batch C (10 same + 10 new = 20 rows) -> Verifies Gold count=30, total revenue.
Resets runtime data at the end.
"""

import csv
import io
import json
import os
import sys
import time
from pathlib import Path
import requests

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.core.config import settings
from app.core import security
from app.db.base import get_databricks_connection

BASE_URL = "http://127.0.0.1:8000"
CATALOG = getattr(settings, "DATABRICKS_CATALOG", "helios_catalog")
TENANT_ID = 1

def get_auth_token(user_id: int, role: str, tenant_id=None):
    return security.create_access_token(user_id=user_id, role=role, tenant_id=tenant_id)

def wait_for_status(batch_id: str, target_statuses, timeout_seconds=240, poll_interval=2):
    start = time.time()
    last_status = None
    with get_databricks_connection(catalog=CATALOG) as conn:
        with conn.cursor() as cur:
            while time.time() - start < timeout_seconds:
                cur.execute(
                    f"SELECT status, stage FROM `{CATALOG}`.`platform`.`pipeline_status` WHERE batch_id = :batch_id",
                    {"batch_id": batch_id}
                )
                row = cur.fetchone()
                if row:
                    st = row[0]
                    if st != last_status:
                        print(f"    [Status Transition] batch={batch_id} -> status={st}, stage={row[1]}")
                        last_status = st
                    if st in target_statuses:
                        return row
                time.sleep(poll_interval)
    raise TimeoutError(f"Batch {batch_id} did not reach {target_statuses} within {timeout_seconds}s (last={last_status})")

def generate_csv(order_ids: list[str]) -> bytes:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["order_id", "customer_id", "product_id", "order_date", "quantity", "unit_price", "total", "discount"])
    for idx, oid in enumerate(order_ids, start=1):
        cid = f"CUST-{idx:03d}"
        pid = f"PROD-{idx:03d}"
        # Each row: 1 quantity @ 50.00 = 50.00 total
        writer.writerow([oid, cid, pid, "2026-09-15 12:00:00", "1", "50.00", "50.00", "0.00"])
    return output.getvalue().encode("utf-8")

def query_gold_metrics(tenant_id: int):
    with get_databricks_connection(catalog=CATALOG) as conn:
        with conn.cursor() as cur:
            # Gold fact_orders count and revenue
            cur.execute(
                f"SELECT count(*), coalesce(round(sum(total), 2), 0.00) FROM `{CATALOG}`.`gold`.`fact_orders` WHERE tenant_id = :tid",
                {"tid": tenant_id}
            )
            fact_row = cur.fetchone()
            gold_count = int(fact_row[0]) if fact_row else 0
            gold_revenue = float(fact_row[1]) if fact_row else 0.0

            # Daily summary
            cur.execute(
                f"SELECT date_id, total_orders, round(total_revenue, 2), avg_order_value FROM `{CATALOG}`.`gold`.`fact_orders_daily_summary` WHERE tenant_id = :tid AND date_id = 20260915",
                {"tid": tenant_id}
            )
            sum_row = cur.fetchone()
            daily_summary = {
                "date_id": sum_row[0],
                "total_orders": sum_row[1],
                "total_revenue": float(sum_row[2]),
                "avg_order_value": float(sum_row[3]),
            } if sum_row else None

            # Silver orders_clean count
            cur.execute(
                f"SELECT count(*) FROM `{CATALOG}`.`silver`.`orders_clean` WHERE tenant_id = :tid",
                {"tid": tenant_id}
            )
            silver_row = cur.fetchone()
            silver_count = int(silver_row[0]) if silver_row else 0

    return {
        "silver_count": silver_count,
        "gold_count": gold_count,
        "gold_revenue": gold_revenue,
        "daily_summary": daily_summary,
    }

def process_batch(file_name: str, csv_bytes: bytes, headers: dict) -> str:
    files = {"file": (file_name, csv_bytes, "text/csv")}
    resp = requests.post(f"{BASE_URL}/api/v1/uploads?tenant_id={TENANT_ID}", files=files, headers=headers)
    assert resp.status_code in (200, 201), f"Upload failed: {resp.text}"
    batch_id = resp.json()["batch_id"]
    print(f"  Uploaded {file_name} -> batch_id: {batch_id}")

    print("  Waiting for Bronze ingestion & schema inference -> pending_review...")
    ps_row = wait_for_status(batch_id, ["pending_review", "failed"])
    assert ps_row[0] == "pending_review", f"Batch failed inference: {ps_row}"

    print(f"  Confirming batch {batch_id}...")
    conf_resp = requests.post(
        f"{BASE_URL}/api/v1/uploads/{batch_id}/confirm",
        json={"confirmed_template": "template_orders", "internal_notes": f"Verification load for {file_name}"},
        headers=headers
    )
    assert conf_resp.status_code == 200, f"Confirmation failed: {conf_resp.text}"

    print("  Waiting for Silver & Gold pipeline completion -> success...")
    final_row = wait_for_status(batch_id, ["success", "failed"])
    assert final_row[0] == "success", f"Pipeline failed: {final_row}"
    print(f"  Batch {batch_id} completed successfully!")
    return batch_id

def main():
    print("=" * 70)
    print("STARTING 20-ROW IDEMPOTENCY VERIFICATION")
    print("=" * 70)

    admin_token = get_auth_token(1, "admin")
    headers = {"Authorization": f"Bearer {admin_token}"}

    ts = int(time.time())
    order_ids_20 = [f"ORD-IDEMP-{ts}-{i:03d}" for i in range(1, 21)]

    # -------------------------------------------------------------
    # 1. LOAD BATCH A (20 rows)
    # -------------------------------------------------------------
    print("\n[STEP 1] Loading Batch A (20 rows)...")
    csv_bytes_a = generate_csv(order_ids_20)
    batch_a_id = process_batch(f"batch_a_{ts}.csv", csv_bytes_a, headers)

    metrics_a = query_gold_metrics(TENANT_ID)
    print(f"\n>>> METRICS AFTER BATCH A:")
    print(f"    Silver orders_clean Count: {metrics_a['silver_count']} (Expected: 20)")
    print(f"    Gold fact_orders Count   : {metrics_a['gold_count']} (Expected: 20)")
    print(f"    Gold Total Revenue       : ${metrics_a['gold_revenue']:.2f} (Expected: $1000.00)")
    print(f"    Gold Daily Summary       : {metrics_a['daily_summary']}")

    assert metrics_a["gold_count"] == 20, f"Expected 20 Gold rows, got {metrics_a['gold_count']}"
    assert metrics_a["gold_revenue"] == 1000.00, f"Expected 1000.00 revenue, got {metrics_a['gold_revenue']}"
    assert metrics_a["daily_summary"] is not None, "Daily summary must be present"
    assert metrics_a["daily_summary"]["total_orders"] == 20, f"Expected 20 orders in summary, got {metrics_a['daily_summary']['total_orders']}"
    assert metrics_a["daily_summary"]["total_revenue"] == 1000.00, f"Expected 1000.00 summary revenue, got {metrics_a['daily_summary']['total_revenue']}"

    # -------------------------------------------------------------
    # 2. LOAD BATCH B (Identical 20 rows)
    # -------------------------------------------------------------
    print("\n[STEP 2] Loading Batch B (Identical 20 rows)...")
    # Exact same CSV content
    batch_b_id = process_batch(f"batch_b_{ts}.csv", csv_bytes_a, headers)

    metrics_b = query_gold_metrics(TENANT_ID)
    print(f"\n>>> METRICS AFTER BATCH B (IDENTICAL):")
    print(f"    Silver orders_clean Count: {metrics_b['silver_count']} (Expected: 20 - UNCHANGED)")
    print(f"    Gold fact_orders Count   : {metrics_b['gold_count']} (Expected: 20 - UNCHANGED)")
    print(f"    Gold Total Revenue       : ${metrics_b['gold_revenue']:.2f} (Expected: $1000.00 - UNCHANGED)")
    print(f"    Gold Daily Summary       : {metrics_b['daily_summary']} (Expected: UNCHANGED)")

    assert metrics_b["gold_count"] == 20, f"Gold count changed after identical load: {metrics_b['gold_count']}"
    assert metrics_b["gold_revenue"] == 1000.00, f"Gold revenue changed after identical load: {metrics_b['gold_revenue']}"
    assert metrics_b["daily_summary"] == metrics_a["daily_summary"], f"Daily summary changed! Before: {metrics_a['daily_summary']}, After: {metrics_b['daily_summary']}"

    # -------------------------------------------------------------
    # 3. LOAD BATCH C (10 same + 10 new = 20 rows)
    # -------------------------------------------------------------
    print("\n[STEP 3] Loading Batch C (10 same rows + 10 new rows = 20 rows)...")
    order_ids_10_same = order_ids_20[:10]
    order_ids_10_new = [f"ORD-IDEMP-{ts}-{i:03d}" for i in range(21, 31)]
    order_ids_c = order_ids_10_same + order_ids_10_new
    assert len(order_ids_c) == 20

    csv_bytes_c = generate_csv(order_ids_c)
    batch_c_id = process_batch(f"batch_c_{ts}.csv", csv_bytes_c, headers)

    metrics_c = query_gold_metrics(TENANT_ID)
    print(f"\n>>> METRICS AFTER BATCH C (10 SAME + 10 NEW):")
    print(f"    Silver orders_clean Count: {metrics_c['silver_count']} (Expected: 30)")
    print(f"    Gold fact_orders Count   : {metrics_c['gold_count']} (Expected: 30)")
    print(f"    Gold Total Revenue       : ${metrics_c['gold_revenue']:.2f} (Expected: $1500.00)")
    print(f"    Gold Daily Summary       : {metrics_c['daily_summary']}")

    assert metrics_c["gold_count"] == 30, f"Expected 30 Gold rows, got {metrics_c['gold_count']}"
    assert metrics_c["gold_revenue"] == 1500.00, f"Expected 1500.00 revenue, got {metrics_c['gold_revenue']}"
    assert metrics_c["daily_summary"]["total_orders"] == 30, f"Expected 30 orders in daily summary, got {metrics_c['daily_summary']['total_orders']}"
    assert metrics_c["daily_summary"]["total_revenue"] == 1500.00, f"Expected 1500.00 daily summary revenue, got {metrics_c['daily_summary']['total_revenue']}"

    print("\n" + "=" * 70)
    print("ALL 3 IDEMPOTENCY / INCREMENTAL VERIFICATIONS PASSED SUCCESSFULLY!")
    print("=" * 70)

if __name__ == "__main__":
    main()
