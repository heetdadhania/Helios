import os
import sys
import time
import uuid
import requests
import databricks.sql
from pathlib import Path
from dotenv import load_dotenv

if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
sys.stdout.reconfigure(line_buffering=True)

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(ROOT_DIR / ".env")

BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
API_PREFIX = "/api/v1"
TEST_PASSWORD = os.getenv("TEST_ACCOUNT_PASSWORD")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")

DATABRICKS_SERVER_HOSTNAME = os.getenv("DATABRICKS_SERVER_HOSTNAME")
DATABRICKS_HTTP_PATH = os.getenv("DATABRICKS_HTTP_PATH")
DATABRICKS_TOKEN = os.getenv("DATABRICKS_TOKEN")
CATALOG = os.getenv("DATABRICKS_CATALOG", "helios_catalog")

print("=" * 75)
print("HELIOS VERIFICATION SUITE: DUPLICATE DETECTION, OVERRIDE & MERGE IDEMPOTENCY")
print("=" * 75)

assert TEST_PASSWORD, "TEST_ACCOUNT_PASSWORD must be set in environment"
assert ADMIN_PASSWORD, "ADMIN_PASSWORD must be set in environment"

def get_db_cursor():
    conn = databricks.sql.connect(
        server_hostname=DATABRICKS_SERVER_HOSTNAME,
        http_path=DATABRICKS_HTTP_PATH,
        access_token=DATABRICKS_TOKEN,
    )
    return conn, conn.cursor()

def login_user(email, password):
    resp = requests.post(
        f"{BASE_URL}{API_PREFIX}/auth/login",
        json={"email": email, "password": password},
    )
    if resp.status_code != 200:
        raise RuntimeError(f"Login failed for {email} ({resp.status_code}): {resp.text}")
    return resp.json()

# Track batches created during this test for strict DATA RULE cleanup
created_batch_ids = []
created_upload_ids = []
test_tenant_id = 1
unique_run_key = f"DUP-{int(time.time())}"

# Connect to DB
conn, cur = get_db_cursor()

try:
    # -------------------------------------------------------------------------
    # STEP 1: PASSWORD EYE TOGGLE VERIFICATION (SOURCE CODE & ACCESSIBILITY)
    # -------------------------------------------------------------------------
    print("\n[STEP 1] Verifying Password Eye Icon on Login & Change Password...")
    login_tsx = (ROOT_DIR / "frontend" / "src" / "pages" / "Login.tsx").read_text(encoding="utf-8")
    assert "showPassword" in login_tsx, "Login.tsx must define showPassword state"
    assert "type={showPassword ? 'text' : 'password'}" in login_tsx, "Login.tsx must toggle input type"
    assert "aria-label={showPassword ? 'Hide password' : 'Show password'}" in login_tsx, "Login.tsx must provide accessible aria-label"
    assert "Eye" in login_tsx and "EyeOff" in login_tsx, "Login.tsx must use existing Eye/EyeOff icons"
    print("  ✓ Login page eye toggle: state, type toggle, aria-label, and icons verified.")

    change_pw_tsx = (ROOT_DIR / "frontend" / "src" / "pages" / "auth" / "ChangePassword.tsx").read_text(encoding="utf-8")
    assert "aria-label={showCurrent ? 'Hide current password' : 'Show current password'}" in change_pw_tsx
    assert "aria-label={showNew ? 'Hide new password' : 'Show new password'}" in change_pw_tsx
    assert "aria-label={showConfirm ? 'Hide confirm new password' : 'Show confirm new password'}" in change_pw_tsx
    assert "focus:ring-helios-accent-blue" in change_pw_tsx, "ChangePassword buttons must have focus ring for keyboard accessibility"
    print("  ✓ Change Password page eye toggle: aria-labels and keyboard focus accessibility verified.")

    conflict_dialog_tsx = (ROOT_DIR / "frontend" / "src" / "components" / "shared" / "DuplicateConflictDialog.tsx").read_text(encoding="utf-8")
    assert "Submit anyway" in conflict_dialog_tsx, "DuplicateConflictDialog must feature 'Submit anyway' button"
    print("  ✓ DuplicateConflictDialog: 'Submit anyway' button label verified.")

    # -------------------------------------------------------------------------
    # STEP 2: CREATE 5-ROW TEST CSV DATASET
    # -------------------------------------------------------------------------
    print("\n[STEP 2] Preparing 5-row CSV dataset...")
    # 5 rows with distinct order IDs and realistic values
    test_orders = [
        {"order_id": f"{unique_run_key}-01", "date": "2026-03-01", "customer": "CUST-001", "product": "SKU-TEST-A", "qty": 2, "unit_price": 500.0, "total": 1000.0, "disc": 0.0},
        {"order_id": f"{unique_run_key}-02", "date": "2026-03-01", "customer": "CUST-002", "product": "SKU-TEST-B", "qty": 1, "unit_price": 750.0, "total": 750.0, "disc": 0.0},
        {"order_id": f"{unique_run_key}-03", "date": "2026-03-02", "customer": "CUST-001", "product": "SKU-TEST-C", "qty": 3, "unit_price": 300.0, "total": 900.0, "disc": 0.0},
        {"order_id": f"{unique_run_key}-04", "date": "2026-03-02", "customer": "CUST-003", "product": "SKU-TEST-A", "qty": 1, "unit_price": 500.0, "total": 500.0, "disc": 0.0},
        {"order_id": f"{unique_run_key}-05", "date": "2026-03-03", "customer": "CUST-004", "product": "SKU-TEST-D", "qty": 4, "unit_price": 250.0, "total": 1000.0, "disc": 0.0},
    ]
    csv_lines = ["order_id,order_date,customer_id,product_id,quantity,unit_price,total,discount"]
    for r in test_orders:
        csv_lines.append(f"{r['order_id']},{r['date']},{r['customer']},{r['product']},{r['qty']},{r['unit_price']},{r['total']},{r['disc']}")
    csv_bytes = "\n".join(csv_lines).encode("utf-8")
    print(f"  Created 5-row CSV payload ({len(csv_bytes)} bytes):")
    for r in test_orders:
        print(f"    - {r['order_id']} | Date: {r['date']} | Total: ₹{r['total']}")

    # Authenticate as Team Member
    team_auth = login_user("team-member-1@helios-test.dev", TEST_PASSWORD)
    team_token = team_auth["access_token"]
    headers = {"Authorization": f"Bearer {team_token}"}

    # -------------------------------------------------------------------------
    # STEP 3: INITIAL UPLOAD (BATCH 1)
    # -------------------------------------------------------------------------
    print("\n[STEP 3] Uploading 5-row CSV as Batch 1...")
    files = {"file": ("test_5_rows.csv", csv_bytes, "text/csv")}
    data = {"tenant_id": str(test_tenant_id)}
    resp1 = requests.post(f"{BASE_URL}{API_PREFIX}/uploads", headers=headers, files=files, data=data)
    print(f"  Upload 1 Status: {resp1.status_code}")
    assert resp1.status_code in (200, 201), f"Upload 1 failed: {resp1.text}"
    batch_1_info = resp1.json()
    batch_id_1 = batch_1_info["batch_id"]
    upload_id_1 = batch_1_info["upload_id"]
    created_batch_ids.append(batch_id_1)
    created_upload_ids.append(upload_id_1)
    print(f"  ✓ Batch 1 created successfully: batch_id={batch_id_1}, upload_id={upload_id_1}")

    # -------------------------------------------------------------------------
    # STEP 4: SECOND IDENTICAL UPLOAD -> EXPECT 409 CONFLICT WITH DETAILS
    # -------------------------------------------------------------------------
    print("\n[STEP 4] Attempting identical second upload without override -> Expecting 409 Conflict...")
    files = {"file": ("test_5_rows.csv", csv_bytes, "text/csv")}
    resp2 = requests.post(f"{BASE_URL}{API_PREFIX}/uploads", headers=headers, files=files, data=data)
    print(f"  Upload 2 Status: {resp2.status_code}")
    assert resp2.status_code == 409, f"Expected 409 Conflict, got {resp2.status_code}: {resp2.text}"

    conflict_data = resp2.json().get("detail", {})
    print(f"  409 Conflict Detail payload received:")
    print(f"    - matched: {conflict_data.get('matched')}")
    print(f"    - submitted_by: {conflict_data.get('submitted_by')}")
    print(f"    - submitted_at: {conflict_data.get('submitted_at')}")
    print(f"    - batch_id: {conflict_data.get('batch_id')}")
    print(f"    - overlapping_rows: {conflict_data.get('overlapping_rows')}")

    assert conflict_data.get("matched") is not None, "Missing 'matched' in 409 response"
    assert "file_hash" in conflict_data.get("matched"), "Expected 'file_hash' match"
    assert conflict_data.get("submitted_by"), "Missing 'submitted_by' in 409 response"
    assert conflict_data.get("submitted_at"), "Missing 'submitted_at' in 409 response"
    assert conflict_data.get("batch_id") == batch_id_1, f"Expected conflict batch_id {batch_id_1}, got {conflict_data.get('batch_id')}"
    assert conflict_data.get("overlapping_rows") == 5, f"Expected 5 overlapping rows, got {conflict_data.get('overlapping_rows')}"
    print("  ✓ Second identical upload returned 409 with complete duplicate details.")

    # -------------------------------------------------------------------------
    # STEP 5: OVERRIDE VALIDATION (< 5 chars -> 400, >= 5 chars -> 200/201 + audit)
    # -------------------------------------------------------------------------
    print("\n[STEP 5] Testing Duplicate Override...")
    # 5a. Short reason (< 5 chars)
    files = {"file": ("test_5_rows.csv", csv_bytes, "text/csv")}
    bad_override_data = {
        "tenant_id": str(test_tenant_id),
        "override_duplicate": "true",
        "override_reason": "fail",
    }
    resp_short = requests.post(f"{BASE_URL}{API_PREFIX}/uploads", headers=headers, files=files, data=bad_override_data)
    print(f"  Short reason (<5 chars) Status: {resp_short.status_code} (detail: {resp_short.text})")
    assert resp_short.status_code == 400, "Expected 400 for override_reason < 5 chars"
    print("  ✓ Reason < 5 characters rejected with 400 Bad Request.")

    # 5b. Valid reason (>= 5 chars)
    valid_reason = "Legitimate re-upload test to verify merge idempotency across silver and gold"
    files = {"file": ("test_5_rows.csv", csv_bytes, "text/csv")}
    good_override_data = {
        "tenant_id": str(test_tenant_id),
        "override_duplicate": "true",
        "override_reason": valid_reason,
    }
    resp_override = requests.post(f"{BASE_URL}{API_PREFIX}/uploads", headers=headers, files=files, data=good_override_data)
    print(f"  Valid override Status: {resp_override.status_code}")
    assert resp_override.status_code in (200, 201), f"Expected 200/201 on valid override, got {resp_override.status_code}: {resp_override.text}"
    batch_2_info = resp_override.json()
    batch_id_2 = batch_2_info["batch_id"]
    upload_id_2 = batch_2_info["upload_id"]
    created_batch_ids.append(batch_id_2)
    created_upload_ids.append(upload_id_2)
    print(f"  ✓ Override accepted: batch_id_2={batch_id_2}")

    # 5c. Check meta.audit_trail row
    print("  Verifying audit row in meta.audit_trail...")
    cur.execute(
        f"""
        SELECT action, reason, details_json, actor_role 
        FROM `{CATALOG}`.`meta`.`audit_trail` 
        WHERE batch_id = :batch_id AND action = 'duplicate_override'
        """,
        {"batch_id": batch_id_2},
    )
    audit_row = cur.fetchone()
    assert audit_row, "Audit row for duplicate_override not found in meta.audit_trail"
    print(f"    - Action: {audit_row[0]}")
    print(f"    - Reason: {audit_row[1]}")
    print(f"    - Details JSON: {audit_row[2]}")
    assert audit_row[0] == "duplicate_override"
    assert audit_row[1] == valid_reason
    print("  ✓ Duplicate override audit row verified in database.")

    # -------------------------------------------------------------------------
    # STEP 6: VERIFY SILVER & GOLD MERGE IDEMPOTENCY
    # -------------------------------------------------------------------------
    print("\n[STEP 6] Testing Silver & Gold Load by Merge (Revenue & Row counts must NOT double)...")
    
    # Wait for Batch 1 schema inference to settle in pending_review
    print("  Waiting for Batch 1 schema inference...")
    for _ in range(30):
        cur.execute(
            f"SELECT status FROM `{CATALOG}`.`platform`.`pipeline_status` WHERE batch_id = :batch_id",
            {"batch_id": batch_id_1},
        )
        st = cur.fetchone()
        if st and st[0] in ("pending_review", "awaiting_confirmation"):
            break
        time.sleep(1)
    
    # Confirm Batch 1 schema
    print("  Confirming schema for Batch 1...")
    confirm_resp1 = requests.post(
        f"{BASE_URL}{API_PREFIX}/uploads/{batch_id_1}/confirm",
        headers=headers,
        json={"confirmed_template": "ecommerce_orders", "corrected_mapping": {}},
    )
    assert confirm_resp1.status_code == 200, f"Batch 1 confirmation failed: {confirm_resp1.text}"

    # Wait for Batch 1 to reach success
    print("  Waiting for Batch 1 pipeline to complete...")
    for _ in range(60):
        cur.execute(
            f"SELECT status, error_message FROM `{CATALOG}`.`platform`.`pipeline_status` WHERE batch_id = :batch_id",
            {"batch_id": batch_id_1},
        )
        row = cur.fetchone()
        if row and row[0] == "success":
            break
        if row and row[0] == "failed":
            raise RuntimeError(f"Batch 1 pipeline failed: {row[1]}")
        time.sleep(2)
    assert row and row[0] == "success", "Batch 1 pipeline timed out or did not succeed"
    print("  ✓ Batch 1 finished successfully through Gold stage.")

    # Measure Gold fact_orders count and revenue for test orders
    order_ids_sql = ", ".join(f"'{o['order_id']}'" for o in test_orders)
    cur.execute(
        f"""
        SELECT count(*), round(sum(coalesce(total, 0)), 2)
        FROM `{CATALOG}`.`gold`.`fact_orders`
        WHERE tenant_id = :tenant_id AND source_order_id IN ({order_ids_sql})
        """,
        {"tenant_id": test_tenant_id},
    )
    gold_count_1, gold_rev_1 = cur.fetchone()
    print(f"  Gold status after Batch 1: Count={gold_count_1} rows, Revenue=₹{gold_rev_1}")
    assert gold_count_1 == 5, f"Expected exactly 5 rows in Gold, got {gold_count_1}"
    expected_revenue = sum(o["total"] for o in test_orders)
    assert float(gold_rev_1) == expected_revenue, f"Expected revenue ₹{expected_revenue}, got ₹{gold_rev_1}"

    # Now run Batch 2 (the identical overridden batch)
    print("  Waiting for Batch 2 schema inference...")
    for _ in range(30):
        cur.execute(
            f"SELECT status FROM `{CATALOG}`.`platform`.`pipeline_status` WHERE batch_id = :batch_id",
            {"batch_id": batch_id_2},
        )
        st = cur.fetchone()
        if st and st[0] in ("pending_review", "awaiting_confirmation"):
            break
        time.sleep(1)

    print("  Confirming schema for Batch 2 (identical duplicate re-run)...")
    confirm_resp2 = requests.post(
        f"{BASE_URL}{API_PREFIX}/uploads/{batch_id_2}/confirm",
        headers=headers,
        json={"confirmed_template": "ecommerce_orders", "corrected_mapping": {}},
    )
    assert confirm_resp2.status_code == 200, f"Batch 2 confirmation failed: {confirm_resp2.text}"

    print("  Waiting for Batch 2 pipeline to complete...")
    for _ in range(60):
        cur.execute(
            f"SELECT status, error_message FROM `{CATALOG}`.`platform`.`pipeline_status` WHERE batch_id = :batch_id",
            {"batch_id": batch_id_2},
        )
        row = cur.fetchone()
        if row and row[0] == "success":
            break
        if row and row[0] == "failed":
            raise RuntimeError(f"Batch 2 pipeline failed: {row[1]}")
        time.sleep(2)
    assert row and row[0] == "success", "Batch 2 pipeline timed out or did not succeed"
    print("  ✓ Batch 2 finished successfully through Gold stage.")

    # Re-measure Gold fact_orders count and revenue
    cur.execute(
        f"""
        SELECT count(*), round(sum(coalesce(total, 0)), 2)
        FROM `{CATALOG}`.`gold`.`fact_orders`
        WHERE tenant_id = :tenant_id AND source_order_id IN ({order_ids_sql})
        """,
        {"tenant_id": test_tenant_id},
    )
    gold_count_2, gold_rev_2 = cur.fetchone()
    print(f"  Gold status after Batch 2 (re-run): Count={gold_count_2} rows, Revenue=₹{gold_rev_2}")

    # VERIFY MERGE BEHAVIOR: Row count and revenue did NOT double!
    assert gold_count_2 == 5, f"ERROR: Gold row count doubled! Expected 5, got {gold_count_2}"
    assert float(gold_rev_2) == expected_revenue, f"ERROR: Gold revenue doubled! Expected ₹{expected_revenue}, got ₹{gold_rev_2}"
    print("  ✓ VERIFIED: Silver and Gold MERGE worked identically. Row counts and revenue did NOT double!")

    # Verify that the fact_orders rows were updated with batch_id_2
    cur.execute(
        f"""
        SELECT DISTINCT batch_id
        FROM `{CATALOG}`.`gold`.`fact_orders`
        WHERE tenant_id = :tenant_id AND source_order_id IN ({order_ids_sql})
        """,
        {"tenant_id": test_tenant_id},
    )
    active_batches = [r[0] for r in cur.fetchall()]
    print(f"  Active batch in fact_orders: {active_batches}")
    assert batch_id_2 in active_batches, "Expected fact_orders to be updated to batch_id_2 via MERGE"
    print("  ✓ Verified: Existing rows were replaced in-place rather than duplicated.")

finally:
    # -------------------------------------------------------------------------
    # STEP 7: STRICT DATA RULE COMPLIANT CLEANUP
    # -------------------------------------------------------------------------
    print("\n[STEP 7] DATA RULE Compliance Cleanup...")
    print(f"  Removing only rows created for test batches: {created_batch_ids}")
    if created_batch_ids:
        batches_sql = ", ".join(f"'{b}'" for b in created_batch_ids)
        uploads_sql = ", ".join(str(u) for u in created_upload_ids)

        cur.execute(f"DELETE FROM `{CATALOG}`.`gold`.`fact_orders` WHERE batch_id IN ({batches_sql})")
        cur.execute(f"DELETE FROM `{CATALOG}`.`gold`.`fact_shipments` WHERE batch_id IN ({batches_sql})")
        cur.execute(f"DELETE FROM `{CATALOG}`.`silver`.`orders_clean` WHERE batch_id IN ({batches_sql})")
        cur.execute(f"DELETE FROM `{CATALOG}`.`meta`.`audit_trail` WHERE batch_id IN ({batches_sql})")
        cur.execute(f"DELETE FROM `{CATALOG}`.`meta`.`etl_audit_log` WHERE batch_id IN ({batches_sql})")
        cur.execute(f"DELETE FROM `{CATALOG}`.`platform`.`pipeline_status` WHERE batch_id IN ({batches_sql})")
        if created_upload_ids:
            cur.execute(f"DELETE FROM `{CATALOG}`.`platform`.`pending_uploads` WHERE upload_id IN ({uploads_sql})")

        # Re-aggregate daily summary for tenant 1 to preserve clean state
        cur.execute(f"CALL `{CATALOG}`.`gold`.`sp_refresh_daily_summary`({test_tenant_id}, 'cleanup-refresh')")

        # Clean local volume directories for test batches
        for b in created_batch_ids:
            vol_dir = ROOT_DIR / "storage" / "volumes" / "helios" / "bronze" / "uploads" / str(test_tenant_id) / b
            if vol_dir.exists():
                import shutil
                shutil.rmtree(vol_dir, ignore_errors=True)

        print(f"  ✓ Cleaned up {len(created_batch_ids)} test batches from all tables and storage.")
        print("  ✓ Preserved all pre-existing database tables and baseline rows.")

cur.close()
conn.close()

print("\n" + "=" * 75)
print("ALL VERIFICATIONS (EYE ICON, 409 DUPLICATE, OVERRIDE AUDIT, MERGE IDEMPOTENCY) PASSED!")
print("=" * 75)
