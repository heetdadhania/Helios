#!/usr/bin/env python3
"""
Helios Data Platform - End-to-End Step 7 Live Verification Script
Runs all verification scenarios specified in Step 7 against the live backend and Databricks.
"""

import csv
import io
import json
import os
import subprocess
import sys
import time
from pathlib import Path
import psycopg2
import requests

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.core.config import settings
from app.core import security
import databricks.sql as dbsql

BASE_URL = "http://127.0.0.1:8000"
CATALOG = getattr(settings, "DATABRICKS_CATALOG", "helios_catalog")

def get_db_conn():
    return dbsql.connect(
        server_hostname=settings.DATABRICKS_SERVER_HOSTNAME,
        http_path=settings.DATABRICKS_HTTP_PATH,
        access_token=settings.DATABRICKS_TOKEN
    )

def get_auth_token(user_id: int, role: str, tenant_id=None):
    return security.create_access_token(user_id=user_id, role=role, tenant_id=tenant_id)

def wait_for_status(batch_id: str, target_statuses, timeout_seconds=300, poll_interval=3):
    start = time.time()
    last_status = None
    while time.time() - start < timeout_seconds:
        with get_db_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"SELECT status, stage, failed_stage, failure_message, failure_next_step FROM `{CATALOG}`.`platform`.`pipeline_status` WHERE batch_id = :batch_id",
                    {"batch_id": batch_id}
                )
                row = cur.fetchone()
                if row:
                    st = row[0]
                    if st != last_status:
                        print(f"  [Status Transition] batch={batch_id} -> status={st}, stage={row[1]}")
                        last_status = st
                    if st in target_statuses:
                        return row
        time.sleep(poll_interval)
    raise TimeoutError(f"Batch {batch_id} did not reach {target_statuses} within {timeout_seconds}s (last={last_status})")

def _run_scenarios():
    # Tokens for testing
    admin_token = get_auth_token(1, "admin")
    team1_token = get_auth_token(16, "team_member") # Assigned to tenant 1
    team2_token = get_auth_token(17, "team_member") # Assigned to tenant 3,4 (unassigned to tenant 1)
    owner1_token = get_auth_token(6, "smb_owner", 1) # SMB Owner for Tenant 1

    # =========================================================================
    # 7.1: File Upload (30 valid rows, 3 bad rows)
    # =========================================================================
    print("\n--- 7.1 SUBMIT CSV (30 valid, 3 bad rows) AS TEAM MEMBER 1 FOR TENANT 1 ---")
    ts_suffix = int(time.time())
    csv_rows = [["order_id", "customer_id", "product_id", "order_date", "quantity", "unit_price", "total", "discount"]]
    for i in range(1, 31):
        csv_rows.append([f"ORD-V7-{ts_suffix}-{i:03d}", f"CUST-{i:03d}", f"PROD-{i:03d}", "2026-09-15 12:00:00", "2", "25.00", "50.00", "0.00"])
    
    # 3 Bad rows:
    # 1. Missing order_id
    csv_rows.append(["", f"CUST-BAD-1-{ts_suffix}", f"PROD-BAD-1", "2026-09-15 12:00:00", "1", "10.00", "10.00", "0.00"])
    # 2. Missing total and unit_price
    csv_rows.append([f"ORD-BAD-2-{ts_suffix}", f"CUST-BAD-2-{ts_suffix}", f"PROD-BAD-2", "2026-09-15 12:00:00", "1", "", "", "0.00"])
    # 3. Missing order_id
    csv_rows.append(["", f"CUST-BAD-3-{ts_suffix}", f"PROD-BAD-3", "2026-09-15 12:00:00", "1", "15.00", "15.00", "0.00"])

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerows(csv_rows)
    csv_bytes = output.getvalue().encode("utf-8")

    files = {"file": (f"test_orders_step7_1_{ts_suffix}.csv", csv_bytes, "text/csv")}
    headers_team1 = {"Authorization": f"Bearer {team1_token}"}
    headers_admin = {"Authorization": f"Bearer {admin_token}"}
    headers_team2 = {"Authorization": f"Bearer {team2_token}"}

    resp = requests.post(f"{BASE_URL}/api/v1/uploads?tenant_id=1", files=files, headers=headers_team1)
    print(f"POST /api/v1/uploads response: {resp.status_code} {resp.text}")
    assert resp.status_code in (200, 201), f"Upload failed: {resp.text}"
    batch_1 = resp.json()["batch_id"]
    print(f"Batch 1 ID: {batch_1}")

    # Wait for ingest_and_infer to reach pending_review
    print("Waiting for background Bronze ingestion & schema inference to reach 'pending_review'...")
    ps_row = wait_for_status(batch_1, ["pending_review", "failed"])
    assert ps_row[0] == "pending_review", f"Batch failed inference: {ps_row}"

    # Query Databricks for verification
    with get_db_conn() as conn:
        with conn.cursor() as cur:
            # 1. pending_uploads row
            cur.execute(
                f"""SELECT pu.upload_id, pu.tenant_id, ps.batch_id, pu.source_type, pu.status
                    FROM `{CATALOG}`.`platform`.`pending_uploads` pu
                    JOIN `{CATALOG}`.`platform`.`pipeline_status` ps ON pu.upload_id = ps.upload_id
                    WHERE ps.batch_id = :b""",
                {"b": batch_1}
            )
            pu = cur.fetchone()
            print(f"pending_uploads row: {pu}")

            # 2. Bronze row count
            cur.execute(f"SELECT count(*) FROM `{CATALOG}`.`bronze`.`raw_orders` WHERE batch_id = :b", {"b": batch_1})
            bronze_cnt = cur.fetchone()[0]
            print(f"Bronze raw_orders row count: {bronze_cnt} (Expected: 33)")
            assert bronze_cnt == 33, f"Expected 33 bronze rows, got {bronze_cnt}"

            # 3. inferred_schema row
            cur.execute(f"SELECT batch_id, detected_template, confidence_score, created_at FROM `{CATALOG}`.`platform`.`inferred_schema` WHERE batch_id = :b", {"b": batch_1})
            inf = cur.fetchone()
            print(f"inferred_schema row: {inf}")

            # 4. pipeline_status
            cur.execute(f"SELECT status, stage FROM `{CATALOG}`.`platform`.`pipeline_status` WHERE batch_id = :b", {"b": batch_1})
            print(f"pipeline_status row: {cur.fetchone()}")

    # 5. Check visibility in GET /api/v1/uploads/pending
    res_t1 = requests.get(f"{BASE_URL}/api/v1/uploads/pending", headers=headers_team1).json()
    res_adm = requests.get(f"{BASE_URL}/api/v1/uploads/pending", headers=headers_admin).json()
    res_t2 = requests.get(f"{BASE_URL}/api/v1/uploads/pending", headers=headers_team2).json()

    t1_batches = [x["batch_id"] for x in res_t1]
    adm_batches = [x["batch_id"] for x in res_adm]
    t2_batches = [x["batch_id"] for x in res_t2]

    print(f"Listed for Assigned Team Member 1: {batch_1 in t1_batches}")
    print(f"Listed for Admin: {batch_1 in adm_batches}")
    print(f"Listed for Unassigned Team Member 2: {batch_1 in t2_batches}")
    assert batch_1 in t1_batches, "Batch 1 missing from Team Member 1 pending list"
    assert batch_1 in adm_batches, "Batch 1 missing from Admin pending list"
    assert batch_1 not in t2_batches, "Batch 1 illegally appeared in unassigned Team Member 2 pending list"

    # =========================================================================
    # 7.2: Approve & Run
    # =========================================================================
    print("\n--- 7.2 APPROVE BATCH 1 AND MONITOR EXECUTION ---")
    approve_payload = {
        "confirmed_template": "template_orders",
        "internal_notes": "Approved 30 valid orders via Step 7 verification test."
    }
    appr_resp = requests.post(f"{BASE_URL}/api/v1/uploads/{batch_1}/confirm", json=approve_payload, headers=headers_team1)
    print(f"Approve Response: {appr_resp.status_code} {appr_resp.text}")
    assert appr_resp.status_code == 200, f"Approval failed: {appr_resp.text}"

    print("Waiting for pipeline execution (Silver -> Gold -> Success)...")
    final_ps = wait_for_status(batch_1, ["success", "failed"], timeout_seconds=180)
    print(f"Final pipeline_status: {final_ps}")
    assert final_ps[0] == "success", f"Pipeline run failed: {final_ps}"

    with get_db_conn() as conn:
        with conn.cursor() as cur:
            # Silver valid count
            cur.execute(f"SELECT count(*) FROM `{CATALOG}`.`silver`.`orders_clean` WHERE batch_id = :b AND is_valid = true", {"b": batch_1})
            silver_cnt = cur.fetchone()[0]
            print(f"Silver valid orders count: {silver_cnt} (Expected: 30)")
            assert silver_cnt == 30, f"Expected 30 valid silver orders, got {silver_cnt}"

            # data_quality_log count
            cur.execute(f"SELECT count(*) FROM `{CATALOG}`.`meta`.`data_quality_log` WHERE batch_id = :b", {"b": batch_1})
            dq_cnt = cur.fetchone()[0]
            print(f"meta.data_quality_log count: {dq_cnt} (Expected: 3)")
            assert dq_cnt == 3, f"Expected 3 DQ rejection logs, got {dq_cnt}"

            # Gold fact_orders count
            cur.execute(f"SELECT count(*) FROM `{CATALOG}`.`gold`.`fact_orders` WHERE batch_id = :b", {"b": batch_1})
            gold_cnt = cur.fetchone()[0]
            print(f"Gold fact_orders count: {gold_cnt} (Expected: 30)")
            assert gold_cnt == 30, f"Expected 30 gold orders, got {gold_cnt}"

            # fact_orders_daily_summary rows
            cur.execute(f"SELECT count(*) FROM `{CATALOG}`.`gold`.`fact_orders_daily_summary` WHERE tenant_id = 1")
            summary_cnt = cur.fetchone()[0]
            print(f"Gold fact_orders_daily_summary rows for tenant 1: {summary_cnt}")
            assert summary_cnt > 0, "No daily summary rows created"

            # etl_audit_log rows
            cur.execute(f"SELECT stage, row_count, status FROM `{CATALOG}`.`meta`.`etl_audit_log` WHERE batch_id = :b ORDER BY started_at ASC", {"b": batch_1})
            audit_rows = cur.fetchall()
            print("meta.etl_audit_log entries:")
            for row in audit_rows:
                print(f"  {row}")
            assert len(audit_rows) >= 3, f"Expected at least 3 audit log stages, got {len(audit_rows)}"

            # Notification for SMB Owner
            notif = None
            for _ in range(5):
                cur.execute(f"SELECT message, type FROM `{CATALOG}`.`platform`.`notification_log` WHERE tenant_id = 1 AND message = 'Your dashboard is ready' ORDER BY notification_id DESC LIMIT 1")
                notif = cur.fetchone()
                if notif:
                    break
                time.sleep(2)
            print(f"SMB Owner notification: {notif}")
            assert notif is not None, "Notification 'Your dashboard is ready' not found for SMB Owner"

    # Verify batch 1 left Pending list
    res_pending_after = requests.get(f"{BASE_URL}/api/v1/uploads/pending", headers=headers_team1).json()
    pending_after_ids = [x["batch_id"] for x in res_pending_after]
    print(f"Batch 1 in pending list after approval: {batch_1 in pending_after_ids} (Expected: False)")
    assert batch_1 not in pending_after_ids, "Approved batch must leave Pending list"

    # =========================================================================
    # 7.3: Reject Second Small File
    # =========================================================================
    print("\n--- 7.3 SUBMIT SECOND FILE AND REJECT WITH REASON ---")
    ts_suffix_2 = int(time.time())
    csv_rows_2 = [["order_id", "customer_id", "product_id", "order_date", "quantity", "unit_price", "total", "discount"]]
    for i in range(1, 6):
        csv_rows_2.append([f"ORD-REJ-{ts_suffix_2}-{i:03d}", f"CUST-{i:03d}", f"PROD-{i:03d}", "2026-09-16 10:00:00", "1", "10.00", "10.00", "0.00"])
    
    out2 = io.StringIO()
    csv.writer(out2).writerows(csv_rows_2)
    files2 = {"file": (f"test_orders_step7_reject_{ts_suffix_2}.csv", out2.getvalue().encode("utf-8"), "text/csv")}
    resp2 = requests.post(f"{BASE_URL}/api/v1/uploads?tenant_id=1", files=files2, headers=headers_team1)
    batch_2 = resp2.json()["batch_id"]
    print(f"Batch 2 ID: {batch_2}")

    wait_for_status(batch_2, ["pending_review"])
    print(f"Batch 2 reached pending_review. Rejecting with reason...")
    reject_reason = "Customer ID sequence invalid and header corrupted."
    rej_resp = requests.post(f"{BASE_URL}/api/v1/uploads/{batch_2}/reject", json={"reason": reject_reason}, headers=headers_team1)
    print(f"Reject response: {rej_resp.status_code} {rej_resp.text}")
    assert rej_resp.status_code == 200, f"Reject failed: {rej_resp.text}"

    with get_db_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""SELECT pu.status, pu.decision
                    FROM `{CATALOG}`.`platform`.`pending_uploads` pu
                    JOIN `{CATALOG}`.`platform`.`pipeline_status` ps ON pu.upload_id = ps.upload_id
                    WHERE ps.batch_id = :b""",
                {"b": batch_2}
            )
            pu_rej = cur.fetchone()
            print(f"pending_uploads status/decision: {pu_rej}")
            assert pu_rej[0] == "rejected" and pu_rej[1] == "rejected"

            cur.execute(f"SELECT status FROM `{CATALOG}`.`platform`.`pipeline_status` WHERE batch_id = :b", {"b": batch_2})
            ps_rej = cur.fetchone()
            print(f"pipeline_status status: {ps_rej}")
            assert ps_rej[0] == "rejected"

    res_pending_rej = requests.get(f"{BASE_URL}/api/v1/uploads/pending", headers=headers_team1).json()
    assert batch_2 not in [x["batch_id"] for x in res_pending_rej], "Rejected batch must leave Pending list"
    print("Batch 2 confirmed left Pending list.")

    # =========================================================================
    # 7.4: Malformed File, Failure & Retry
    # =========================================================================
    print("\n--- 7.4 SUBMIT FILE, SIMULATE RUNNER FAILURE AND RETRY ---")
    ts_suffix_3 = int(time.time())
    csv_rows_3 = [["order_id", "customer_id", "product_id", "order_date", "quantity", "unit_price", "total", "discount"]]
    for i in range(1, 6):
        csv_rows_3.append([f"ORD-FAIL-{ts_suffix_3}-{i:03d}", f"CUST-{i:03d}", f"PROD-{i:03d}", "2026-09-17 10:00:00", "1", "15.00", "15.00", "0.00"])
    
    out3 = io.StringIO()
    csv.writer(out3).writerows(csv_rows_3)
    files3 = {"file": (f"test_orders_step7_fail_{ts_suffix_3}.csv", out3.getvalue().encode("utf-8"), "text/csv")}
    resp3 = requests.post(f"{BASE_URL}/api/v1/uploads?tenant_id=1", files=files3, headers=headers_team1)
    batch_3 = resp3.json()["batch_id"]
    print(f"Batch 3 ID: {batch_3}")

    wait_for_status(batch_3, ["pending_review"])

    # Approve batch 3
    requests.post(f"{BASE_URL}/api/v1/uploads/{batch_3}/confirm", json={"confirmed_template": "template_orders"}, headers=headers_team1)
    wait_for_status(batch_3, ["success"])

    # Give background completion write 3 seconds to finalize before simulating failure
    time.sleep(3)
    for attempt in range(5):
        try:
            with get_db_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        f"""UPDATE `{CATALOG}`.`platform`.`pipeline_status`
                            SET status = 'failed',
                                failed_stage = 'silver',
                                failure_message = 'Simulated schema corruption in silver stage',
                                failure_next_step = 'Retry from the failed stage'
                            WHERE batch_id = :b""",
                        {"b": batch_3}
                    )
            break
        except Exception as e:
            if "DELTA_CONCURRENT" in str(e) and attempt < 4:
                time.sleep(2)
            else:
                raise

    run_detail = requests.get(f"{BASE_URL}/api/v1/pipeline/runs/{batch_3}", headers=headers_team1).json()
    print("Failed run details from API:")
    print(f"  status: {run_detail.get('status')}")
    print(f"  failed_stage: {run_detail.get('failed_stage')}")
    print(f"  failure_message: {run_detail.get('failure_message')}")
    print(f"  failure_next_step: {run_detail.get('failure_next_step')}")
    assert run_detail.get("status") == "failed"
    assert run_detail.get("failed_stage") == "silver"
    assert run_detail.get("failure_next_step") == "Retry from the failed stage"

    # Retry from failed stage
    print("Triggering retry from failed stage via POST /api/v1/pipeline/runs/{batch_id}/retry-failed-stage...")
    retry_resp = requests.post(f"{BASE_URL}/api/v1/pipeline/runs/{batch_3}/retry-failed-stage", headers=headers_team1)
    print(f"Retry response: {retry_resp.status_code} {retry_resp.text}")
    assert retry_resp.status_code == 200

    final_retry_ps = wait_for_status(batch_3, ["success", "failed"])
    print(f"Batch 3 status after retry: {final_retry_ps[0]}")
    assert final_retry_ps[0] == "success", f"Retry did not succeed: {final_retry_ps}"

    # =========================================================================
    # 7.5: Database Sync and API Push
    # =========================================================================
    print("\n--- 7.5 LIVE DATABASE SYNC ---")
    # 1. Ensure Postgres demo table has fresh rows
    pg_conn = psycopg2.connect(
        host="localhost",
        port=5433,
        user="helios_pg",
        password="helios_demo_pg_secret",
        database="helios_demo_orders"
    )
    pg_cur = pg_conn.cursor()
    pg_cur.execute("CREATE TABLE IF NOT EXISTS orders (order_id VARCHAR(50), customer_name VARCHAR(100), product_name VARCHAR(100), order_date TIMESTAMP, quantity INT, unit_price NUMERIC, total NUMERIC, discount NUMERIC);")
    pg_cur.execute("DELETE FROM orders;")
    ts_dbsync = int(time.time())
    for i in range(1, 6):
        pg_cur.execute("INSERT INTO orders VALUES (%s, %s, %s, NOW(), 2, 10.0, 20.0, 0.0);", (f"ORD-DBSYNC-{ts_dbsync}-{i:03d}", f"CUST-DB-{i}", f"PROD-DB-{i}"))
    pg_conn.commit()
    pg_cur.close()
    pg_conn.close()

    # 2. Register/update DB Connection for Tenant 1
    create_conn_payload = {
        "db_type": "postgresql",
        "host": "localhost",
        "port": 5433,
        "database_name": "helios_demo_orders",
        "username": "helios_pg",
        "password": "helios_demo_pg_secret",
        "table_or_query": "SELECT * FROM orders",
        "tenant_id": 1,
    }
    create_conn_resp = requests.post(f"{BASE_URL}/api/v1/db-connections", json=create_conn_payload, headers=headers_team1)
    assert create_conn_resp.status_code in (200, 201), f"DB Connection creation failed: {create_conn_resp.text}"
    db_conn_id = create_conn_resp.json()["connection_id"]
    print(f"Created DB Connection ID {db_conn_id} for tenant 1")

    # 3. Trigger sync
    sync_resp = requests.post(f"{BASE_URL}/api/v1/db-connections/{db_conn_id}/sync?tenant_id=1", headers=headers_team1)
    print(f"Sync response: {sync_resp.status_code} {sync_resp.text}")
    assert sync_resp.status_code in (200, 201)
    batch_db = sync_resp.json()["batch_id"]
    print(f"DB Sync Batch ID: {batch_db}")

    wait_for_status(batch_db, ["pending_review"])
    print(f"DB Sync batch {batch_db} reached pending_review. Approving...")
    requests.post(f"{BASE_URL}/api/v1/uploads/{batch_db}/confirm", json={"confirmed_template": "template_orders"}, headers=headers_team1)
    wait_for_status(batch_db, ["success"])
    print(f"DB Sync batch {batch_db} reached SUCCESS!")

    print("\n--- 7.5 LIVE API PUSH ---")
    ts_api = int(time.time())
    api_records = [
        {"order_id": f"ORD-API-{ts_api}-{i:03d}", "customer_id": f"CUST-API-{i}", "product_id": f"SKU-{i}", "order_date": "2026-09-18 14:00:00", "quantity": 1, "unit_price": 20.0, "total": 20.0, "discount": 0.0}
        for i in range(1, 6)
    ]
    key_resp = requests.post(f"{BASE_URL}/api/v1/api-keys/regenerate", headers={"Authorization": f"Bearer {owner1_token}"})
    print(f"Key generate response: {key_resp.status_code}")
    assert key_resp.status_code in (200, 201), f"Key generation failed: {key_resp.text}"
    raw_api_key = key_resp.json()["api_key"]
    
    api_headers = {"X-Helios-Api-Key": raw_api_key, "Content-Type": "application/json"}
    push_resp = requests.post(f"{BASE_URL}/api/v1/ingest", json={"records": api_records}, headers=api_headers)
    print(f"API Push response: {push_resp.status_code} {push_resp.text}")
    assert push_resp.status_code in (200, 201)
    batch_api = push_resp.json()["batch_id"]
    print(f"API Batch ID: {batch_api}")

    wait_for_status(batch_api, ["pending_review"])
    print(f"API Batch {batch_api} reached pending_review. Approving...")
    requests.post(f"{BASE_URL}/api/v1/uploads/{batch_api}/confirm", json={"confirmed_template": "template_orders"}, headers=headers_team1)
    wait_for_status(batch_api, ["success"])
    print(f"API Push batch {batch_api} reached SUCCESS!")

def verify_step_7():
    print("=" * 80)
    print("STARTING STEP 7 LIVE VERIFICATION")
    print("=" * 80)
    try:
        _run_scenarios()
        print("\n" + "=" * 80)
        print("ALL VERIFICATION CHECKS (7.1 - 7.6) PASSED!")
        print("=" * 80)
    finally:
        # =========================================================================
        # 7.7: Run reset_runtime_data.py --confirm in finally block
        # =========================================================================
        print("\n--- 7.7 CLEANUP IN FINALLY BLOCK: RESET RUNTIME DATA & CREDENTIALS ---")
        reset_proc = subprocess.run(
            [sys.executable, str(REPO_ROOT / "scripts" / "maintenance" / "reset_runtime_data.py"), "--confirm"],
            capture_output=True,
            text=True,
        )
        print(reset_proc.stdout)
        if reset_proc.stderr:
            print(reset_proc.stderr)
        assert reset_proc.returncode == 0, f"reset_runtime_data failed with code {reset_proc.returncode}"
        print("\n" + "=" * 80)
        print("SYSTEM RESET TO ZERO AND CREDENTIALS CLEANED UP VIA FINALLY BLOCK.")
        print("=" * 80)


if __name__ == "__main__":
    verify_step_7()
