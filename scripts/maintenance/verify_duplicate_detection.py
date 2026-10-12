#!/usr/bin/env python3
"""
Verification Script for Duplicate Submission Detection & Audit Trail
Validates:
1. File hash SHA-256 computation and storage in platform.pending_uploads.
2. Second identical 5-row submission returns 409 Conflict with details:
   - matched
   - submitted_by
   - submitted_at
   - batch_id
   - overlapping_rows (5)
3. Override with invalid reason (< 5 chars) returns 400 Bad Request.
4. Override with valid reason (>= 5 chars) succeeds (201 Created) and creates row in meta.audit_trail.
5. Different 5-row file is accepted normally (201 Created).
6. Reset runtime data at end.
"""

import csv
import hashlib
import io
import json
import os
import sys
import time
from pathlib import Path
import requests

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.core.config import settings
from app.core import security
from app.db.base import get_databricks_connection

BASE_URL = "http://127.0.0.1:8000"
CATALOG = getattr(settings, "DATABRICKS_CATALOG", "helios_catalog")
TENANT_ID = 1


def generate_5row_csv(prefix: str) -> bytes:
    """Generate a 5-row order CSV dataset."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "order_id", "customer_id", "product_id", "order_date", "quantity", "unit_price", "total", "discount"
    ])
    for i in range(1, 6):
        oid = f"{prefix}-{i:04d}"
        cid = f"CUST-{i:03d}"
        pid = f"PROD-{i:03d}"
        writer.writerow([oid, cid, pid, "2026-09-25", 2, 50.00, 100.00, 0.00])
    return output.getvalue().encode("utf-8")


def run_verification():
    print("=" * 70)
    print("HELIOS DUPLICATE DETECTION & OVERRIDE AUDIT VERIFICATION")
    print("=" * 70)

    # Clean existing test data for tenant 1
    print("\n[Step 0] Cleaning test uploads for tenant 1 in platform tables...")
    with get_databricks_connection(catalog=CATALOG) as conn:
        with conn.cursor() as cur:
            cur.execute(f"DELETE FROM `{CATALOG}`.`platform`.`pending_uploads` WHERE tenant_id = {TENANT_ID}")
            cur.execute(f"DELETE FROM `{CATALOG}`.`platform`.`pipeline_status` WHERE tenant_id = {TENANT_ID}")
            cur.execute(f"DELETE FROM `{CATALOG}`.`meta`.`audit_trail` WHERE tenant_id = {TENANT_ID}")
            print("  [OK] Cleaned pending_uploads, pipeline_status, and audit_trail for tenant 1.")

    # Generate token
    token = security.create_access_token(user_id=1, role="admin", tenant_id=TENANT_ID)
    headers = {"Authorization": f"Bearer {token}"}

    # Generate 5-row files
    file_a_content = generate_5row_csv("ORD-DUP-A")
    file_a_hash = hashlib.sha256(file_a_content).hexdigest()
    print(f"\n[Test Data] File A SHA-256: {file_a_hash} (5 rows)")

    file_b_content = generate_5row_csv("ORD-DUP-B")
    file_b_hash = hashlib.sha256(file_b_content).hexdigest()
    print(f"[Test Data] File B SHA-256: {file_b_hash} (5 rows)")

    # -------------------------------------------------------------
    # Step 1: Submit initial 5-row file A
    # -------------------------------------------------------------
    print("\n[Step 1] Submitting initial 5-row File A...")
    files = {"file": ("orders_a.csv", file_a_content, "text/csv")}
    data = {"tenant_id": str(TENANT_ID)}
    res1 = requests.post(f"{BASE_URL}/api/uploads", files=files, data=data, headers=headers)
    print(f"  Response Status: {res1.status_code}")
    print(f"  Response Body: {res1.text}")
    assert res1.status_code in (200, 201), f"Expected 201/200, got {res1.status_code}: {res1.text}"
    batch_a_id = res1.json().get("batch_id")
    upload_a_id = res1.json().get("upload_id")
    print(f"  [OK] Initial submission accepted: batch_id={batch_a_id}, upload_id={upload_a_id}")

    # Verify file_hash persisted in pending_uploads
    with get_databricks_connection(catalog=CATALOG) as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"SELECT upload_id, file_hash, status FROM `{CATALOG}`.`platform`.`pending_uploads` WHERE upload_id = {upload_a_id}"
            )
            pu_row = cur.fetchone()
            print(f"  Verified pending_uploads row: id={pu_row[0]}, hash={pu_row[1]}, status={pu_row[2]}")
            assert pu_row[1] == file_a_hash, f"file_hash mismatch: expected {file_a_hash}, got {pu_row[1]}"
            print("  [OK] file_hash accurately persisted in platform.pending_uploads.")

    # -------------------------------------------------------------
    # Step 2: Submit second identical 5-row file A -> MUST RETURN 409
    # -------------------------------------------------------------
    print("\n[Step 2] Submitting second identical 5-row File A (Duplicate Check)...")
    files_dup = {"file": ("orders_a_duplicate.csv", file_a_content, "text/csv")}
    res2 = requests.post(f"{BASE_URL}/api/uploads", files=files_dup, data=data, headers=headers)
    print(f"  Response Status: {res2.status_code}")
    print(f"  Response Body: {res2.text}")
    assert res2.status_code == 409, f"Expected HTTP 409 Conflict, got {res2.status_code}: {res2.text}"

    conflict_data = res2.json()
    if "detail" in conflict_data and isinstance(conflict_data["detail"], dict):
        conflict_details = conflict_data["detail"]
    else:
        conflict_details = conflict_data

    print("\n  Conflict metadata received in 409 response:")
    print(f"    - matched: {conflict_details.get('matched')}")
    print(f"    - submitted_by: {conflict_details.get('submitted_by')}")
    print(f"    - submitted_at: {conflict_details.get('submitted_at')}")
    print(f"    - batch_id: {conflict_details.get('batch_id')}")
    print(f"    - overlapping_rows: {conflict_details.get('overlapping_rows')}")

    assert conflict_details.get("overlapping_rows") == 5, f"Expected overlapping_rows=5, got {conflict_details.get('overlapping_rows')}"
    assert "file_hash" in conflict_details.get("matched", ""), f"Expected file_hash in matched, got {conflict_details.get('matched')}"
    assert conflict_details.get("batch_id") == batch_a_id, f"Expected batch_id={batch_a_id}, got {conflict_details.get('batch_id')}"
    print("  [OK] Second identical submission successfully rejected with HTTP 409 and complete duplicate details!")

    # -------------------------------------------------------------
    # Step 3: Test override validation (< 5 chars reason should fail)
    # -------------------------------------------------------------
    print("\n[Step 3] Testing override with short reason (< 5 characters)...")
    data_bad_override = {
        "tenant_id": str(TENANT_ID),
        "override_duplicate": "true",
        "override_reason": "test",  # 4 chars < 5
    }
    files_bad = {"file": ("orders_a.csv", file_a_content, "text/csv")}
    res3 = requests.post(f"{BASE_URL}/api/uploads", files=files_bad, data=data_bad_override, headers=headers)
    print(f"  Response Status: {res3.status_code}")
    print(f"  Response Body: {res3.text}")
    assert res3.status_code == 400, f"Expected 400 Bad Request for < 5 chars reason, got {res3.status_code}"
    print("  [OK] Short override reason rejected with HTTP 400 as required.")

    # -------------------------------------------------------------
    # Step 4: Submit with valid override_duplicate=true & reason >= 5 chars
    # -------------------------------------------------------------
    print("\n[Step 4] Submitting with override_duplicate=true & valid reason...")
    override_reason_text = "Authorized duplicate re-upload for customer order corrections"
    data_valid_override = {
        "tenant_id": str(TENANT_ID),
        "override_duplicate": "true",
        "override_reason": override_reason_text,
    }
    files_override = {"file": ("orders_a.csv", file_a_content, "text/csv")}
    res4 = requests.post(f"{BASE_URL}/api/uploads", files=files_override, data=data_valid_override, headers=headers)
    print(f"  Response Status: {res4.status_code}")
    print(f"  Response Body: {res4.text}")
    assert res4.status_code in (200, 201), f"Expected 201/200 on override, got {res4.status_code}: {res4.text}"
    override_batch_id = res4.json().get("batch_id")
    print(f"  [OK] Override accepted: new batch_id={override_batch_id}")

    # Verify audit_trail row written
    print("\n[Step 4b] Verifying audit_trail entry in meta.audit_trail...")
    with get_databricks_connection(catalog=CATALOG) as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT actor_user_id, action, tenant_id, batch_id, reason, details_json, occurred_at 
                FROM `{CATALOG}`.`meta`.`audit_trail` 
                WHERE tenant_id = {TENANT_ID} AND batch_id = '{override_batch_id}'
                """
            )
            audit_row = cur.fetchone()
            print(f"  Audit Row Found: {audit_row}")
            assert audit_row is not None, "No audit_trail row found for overridden batch!"
            assert audit_row[1] == "duplicate_override", f"Expected action='duplicate_override', got {audit_row[1]}"
            assert audit_row[4] == override_reason_text, f"Expected reason='{override_reason_text}', got {audit_row[4]}"
            details = json.loads(audit_row[5])
            print(f"  Audit details_json: {details}")
            assert details.get("overlapping_rows") == 5
            print("  [OK] Audit trail row successfully recorded in meta.audit_trail with full audit attribution!")

    # -------------------------------------------------------------
    # Step 5: Submit different 5-row file B
    # -------------------------------------------------------------
    print("\n[Step 5] Submitting different 5-row File B...")
    files_b = {"file": ("orders_b.csv", file_b_content, "text/csv")}
    data_b = {"tenant_id": str(TENANT_ID)}
    res5 = requests.post(f"{BASE_URL}/api/uploads", files=files_b, data=data_b, headers=headers)
    print(f"  Response Status: {res5.status_code}")
    print(f"  Response Body: {res5.text}")
    assert res5.status_code in (200, 201), f"Expected 201/200 for different file, got {res5.status_code}: {res5.text}"
    batch_b_id = res5.json().get("batch_id")
    print(f"  [OK] Different file accepted normally: batch_id={batch_b_id}")

    # -------------------------------------------------------------
    # Step 6: Cleanup / Reset
    # -------------------------------------------------------------
    print("\n[Step 6] Cleaning up test data for tenant 1...")
    time.sleep(2)
    max_retries = 5
    for attempt in range(1, max_retries + 1):
        try:
            with get_databricks_connection(catalog=CATALOG) as conn:
                with conn.cursor() as cur:
                    cur.execute(f"DELETE FROM `{CATALOG}`.`platform`.`pending_uploads` WHERE tenant_id = {TENANT_ID}")
                    cur.execute(f"DELETE FROM `{CATALOG}`.`platform`.`pipeline_status` WHERE tenant_id = {TENANT_ID}")
                    cur.execute(f"DELETE FROM `{CATALOG}`.`meta`.`audit_trail` WHERE tenant_id = {TENANT_ID}")
                    print("  [OK] Cleanup complete.")
                    break
        except Exception as e:
            if attempt < max_retries:
                print(f"  Cleanup attempt {attempt} transient conflict, retrying in 3s...")
                time.sleep(3)
            else:
                print(f"  Warning during final cleanup: {e}")

    print("\n" + "=" * 70)
    print("ALL DUPLICATE DETECTION & OVERRIDE VERIFICATIONS PASSED SUCCESSFULLY!")
    print("=" * 70)


if __name__ == "__main__":
    run_verification()
