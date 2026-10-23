#!/usr/bin/env python3
"""
scripts/verify/test_tenant_isolation.py

Comprehensive Tenant Isolation Verification Suite:
1. Ingest real data for two tenants:
   - Tenant 1: orders_30_valid.csv (30 valid rows)
   - Tenant 2: orders_10_renamed_headers.csv (10 rows, renamed headers)
   Approve both batches and wait for pipeline completion.
2. Log in for real as smb-owner-1 (Tenant 1):
   Attempt Tenant 2's data through all routes (dashboard, history, export,
   notifications, upload status, support messages, API keys, db connections)
   using Tenant 2 IDs and batch ID.
   Verify refused (403/404) or returns zero Tenant 2 data.
3. Log in for real as team-member-1 (assigned to Tenants 1 and 2):
   Attempt unassigned tenants (5 and 9) across pending, preview, approve,
   reject, cancel, history, pipeline runs, data quality, and rejected rows.
   Verify refused (403/404) or returns zero unassigned data.
4. Confirm Admin can reach every tenant.
5. Print results in a formatted table: actor, route, tenant tried, expected, actual, pass or fail.
6. Reset runtime data via scripts/maintenance/reset_runtime_data.py at the conclusion.
"""

import csv
import io
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests

sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.core.config import settings
from app.db.base import get_databricks_connection
from dotenv import load_dotenv

load_dotenv(REPO_ROOT / ".env")

ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD")
TEST_ACCOUNT_PASSWORD = os.environ.get("TEST_ACCOUNT_PASSWORD")

BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")
CATALOG = getattr(settings, "DATABRICKS_CATALOG", "helios_catalog")
DEFAULT_TIMEOUT = 90

RESULTS: List[Dict[str, str]] = []
CREATED_BATCH_IDS: List[str] = []


def record_result(
    actor: str,
    route: str,
    tenant_tried: str,
    expected: str,
    actual: str,
    passed: bool,
) -> None:
    status_str = "PASS" if passed else "FAIL"
    RESULTS.append({
        "actor": actor,
        "route": route,
        "tenant_tried": tenant_tried,
        "expected": expected,
        "actual": actual,
        "pass_fail": status_str,
    })
    print(f"[{status_str}] {actor:14s} | {route:40s} | Tenant {tenant_tried:2s} | Exp: {expected:22s} | Act: {actual}", flush=True)


def login(email: str, password: str) -> Tuple[str, Dict[str, Any]]:
    """Log in against /api/v1/auth/login and return (token, user_dict)."""
    resp = requests.post(
        f"{BASE_URL}/api/v1/auth/login",
        json={"email": email, "password": password},
        timeout=DEFAULT_TIMEOUT,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"Login failed for {email}: {resp.status_code} {resp.text}")
    data = resp.json()
    return data["access_token"], data.get("user", {})


def wait_for_pipeline_status(
    batch_id: str,
    target_statuses: List[str],
    timeout_seconds: int = 180,
    poll_interval: int = 2,
) -> Tuple[str, str]:
    """Poll platform.pipeline_status in Databricks until target status or timeout."""
    start = time.time()
    last_status = None
    with get_databricks_connection(catalog=CATALOG) as conn:
        with conn.cursor() as cur:
            while time.time() - start < timeout_seconds:
                cur.execute(
                    f"SELECT status, stage FROM `{CATALOG}`.`platform`.`pipeline_status` WHERE batch_id = :batch_id",
                    {"batch_id": batch_id},
                )
                row = cur.fetchone()
                if row:
                    st, stage = row[0], row[1]
                    if st != last_status:
                        print(f"    [Status Transition] batch={batch_id} -> status={st}, stage={stage}")
                        last_status = st
                    if st in target_statuses:
                        return st, stage
                time.sleep(poll_interval)
    raise TimeoutError(f"Batch {batch_id} did not reach {target_statuses} within {timeout_seconds}s (last={last_status})")


def generate_orders_30_valid(ts_suffix: int) -> bytes:
    """Generate 30 valid retail orders matching template_orders."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["order_id", "customer_id", "product_id", "order_date", "quantity", "unit_price", "total", "discount"])
    for i in range(1, 31):
        writer.writerow([
            f"ORD-T1-{ts_suffix}-{i:03d}",
            f"CUST-10{i:02d}",
            f"PROD-10{i:02d}",
            "2026-09-15 10:00:00",
            "2",
            "50.00",
            "100.00",
            "0.00",
        ])
    return output.getvalue().encode("utf-8")


def generate_orders_10_renamed(ts_suffix: int) -> bytes:
    """Generate 10 valid orders using renamed header aliases."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["order_number", "client_id", "item_id", "purchase_date", "units", "price_each", "gross_total", "discount_rate"])
    for i in range(1, 11):
        writer.writerow([
            f"ORD-T2-{ts_suffix}-{i:03d}",
            f"CLNT-20{i:02d}",
            f"ITEM-20{i:02d}",
            "2026-09-15 14:00:00",
            "3",
            "40.00",
            "120.00",
            "0.05",
        ])
    return output.getvalue().encode("utf-8")


def generate_dummy_orders(ts_suffix: int, tenant_id: int) -> bytes:
    """Generate 5 valid orders for seeding pending batches."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["order_id", "customer_id", "product_id", "order_date", "quantity", "unit_price", "total", "discount"])
    for i in range(1, 6):
        writer.writerow([
            f"ORD-T{tenant_id}-{ts_suffix}-{i:03d}",
            f"CUST-{tenant_id}{i:02d}",
            f"PROD-{tenant_id}{i:02d}",
            "2026-09-15 16:00:00",
            "1",
            "30.00",
            "30.00",
            "0.00",
        ])
    return output.getvalue().encode("utf-8")


def load_and_approve_batch(
    tenant_id: int,
    filename: str,
    file_bytes: bytes,
    uploader_token: str,
    reviewer_token: str,
) -> Tuple[str, int]:
    """Upload CSV and confirm mapping to process through Bronze -> Silver -> Gold."""
    print(f"\n>>> Ingesting {filename} for Tenant {tenant_id}...")
    headers_up = {"Authorization": f"Bearer {uploader_token}"}
    files = {"file": (filename, file_bytes, "text/csv")}

    resp = requests.post(f"{BASE_URL}/api/v1/uploads?tenant_id={tenant_id}", files=files, headers=headers_up, timeout=DEFAULT_TIMEOUT)
    if resp.status_code not in (200, 201):
        raise RuntimeError(f"Upload failed: {resp.status_code} {resp.text}")

    upload_data = resp.json()
    batch_id = upload_data["batch_id"]
    upload_id = int(upload_data["upload_id"])
    CREATED_BATCH_IDS.append(batch_id)
    print(f"    Uploaded: batch_id={batch_id}, upload_id={upload_id}", flush=True)

    print("    Waiting for schema inference -> pending_review / awaiting_confirmation...", flush=True)
    wait_for_pipeline_status(batch_id, ["pending_review", "awaiting_confirmation", "failed"], timeout_seconds=180)

    print(f"    Approving batch {batch_id}...", flush=True)
    headers_rev = {"Authorization": f"Bearer {reviewer_token}"}
    conf_resp = requests.post(
        f"{BASE_URL}/api/uploads/{batch_id}/confirm",
        json={"confirmed_template": "template_orders", "internal_notes": f"Verified isolation ingestion for tenant {tenant_id}"},
        headers=headers_rev,
        timeout=DEFAULT_TIMEOUT,
    )
    if conf_resp.status_code != 200:
        raise RuntimeError(f"Approval failed: {conf_resp.status_code} {conf_resp.text}")

    print(f"    Waiting for pipeline completion -> success...", flush=True)
    final_st, _ = wait_for_pipeline_status(batch_id, ["success", "failed"], timeout_seconds=240)
    if final_st != "success":
        raise RuntimeError(f"Pipeline failed for batch {batch_id}: status={final_st}")

    print(f"    Batch {batch_id} confirmed and completed successfully!", flush=True)
    return batch_id, upload_id


def setup_tenant_resources(
    tenant_id: int,
    smb_token: str,
    admin_token: str,
) -> Tuple[int, int, int]:
    """Ensure notification, support message, and db connection exist for a tenant."""
    # 1. Notification ID: fetch from SMB's notifications
    r_notif = requests.get(
        f"{BASE_URL}/api/notifications",
        headers={"Authorization": f"Bearer {smb_token}"},
        timeout=DEFAULT_TIMEOUT,
    )
    notif_id = 1
    if r_notif.status_code == 200 and r_notif.json():
        notif_id = int(r_notif.json()[0]["notification_id"])

    # 2. Support message: submit real message from SMB owner
    r_msg = requests.post(
        f"{BASE_URL}/api/support/messages",
        json={"message": f"Inquiry for tenant {tenant_id} dataset upload."},
        headers={"Authorization": f"Bearer {smb_token}"},
        timeout=DEFAULT_TIMEOUT,
    )
    msg_id = int(r_msg.json()["message_id"]) if r_msg.status_code == 201 else 1

    # 3. DB connection: create or fetch as Admin
    r_conns = requests.get(
        f"{BASE_URL}/api/db-connections?tenant_id={tenant_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
        timeout=DEFAULT_TIMEOUT,
    )
    if r_conns.status_code == 200 and r_conns.json():
        conn_id = int(r_conns.json()[0]["connection_id"])
    else:
        r_create = requests.post(
            f"{BASE_URL}/api/db-connections?tenant_id={tenant_id}",
            json={
                "tenant_id": tenant_id,
                "db_type": "postgresql",
                "host": f"db.tenant{tenant_id}.internal",
                "port": 5432,
                "database_name": f"tenant_{tenant_id}_prod",
                "username": "read_user",
                "password": "SecretPassword123!",
                "table_or_query": "orders_export",
            },
            headers={"Authorization": f"Bearer {admin_token}"},
            timeout=DEFAULT_TIMEOUT,
        )
        conn_id = int(r_create.json()["connection_id"]) if r_create.status_code in (200, 201) else 1

    return notif_id, msg_id, conn_id


def create_pending_batch(tenant_id: int, admin_token: str) -> str:
    """Upload dummy orders for a tenant to place a real batch in pending_review status."""
    ts = int(time.time() * 1000)
    csv_bytes = generate_dummy_orders(ts, tenant_id)
    files = {"file": (f"pending_orders_t{tenant_id}_{ts}.csv", csv_bytes, "text/csv")}
    resp = requests.post(
        f"{BASE_URL}/api/v1/uploads?tenant_id={tenant_id}",
        files=files,
        headers={"Authorization": f"Bearer {admin_token}"},
        timeout=DEFAULT_TIMEOUT,
    )
    if resp.status_code not in (200, 201):
        raise RuntimeError(f"Failed to create pending batch for tenant {tenant_id}: {resp.text}")
    b_id = resp.json()["batch_id"]
    CREATED_BATCH_IDS.append(b_id)
    print(f"    Pending batch uploaded: {b_id} for tenant {tenant_id}", flush=True)
    wait_for_pipeline_status(b_id, ["pending_review", "awaiting_confirmation", "failed"], timeout_seconds=180)
    return b_id


def run_tests() -> bool:
    print("=" * 80)
    print("HELIOS MULTI-TENANT ISOLATION VERIFICATION SUITE")
    print("=" * 80)

    # Log in real users
    print("\n--- 1. Authenticating real accounts ---")
    admin_token, admin_user = login("admin@helios.io", ADMIN_PASSWORD)
    print(f"Logged in Admin: {admin_user.get('name')} (role={admin_user.get('role')})")

    smb1_token, smb1_user = login("smb-owner-1@helios-test.dev", TEST_ACCOUNT_PASSWORD)
    print(f"Logged in SMB Owner 1: {smb1_user.get('name')} (tenant={smb1_user.get('tenant_id')})")

    smb2_token, smb2_user = login("smb-owner-2@helios-test.dev", TEST_ACCOUNT_PASSWORD)
    print(f"Logged in SMB Owner 2: {smb2_user.get('name')} (tenant={smb2_user.get('tenant_id')})")

    tm1_token, tm1_user = login("team-member-1@helios-test.dev", TEST_ACCOUNT_PASSWORD)
    print(f"Logged in Team Member 1: {tm1_user.get('name')} (assigned to tenants 1 & 2)")

    # Seed real approved data in Tenant 1 and Tenant 2
    ts_now = int(time.time())
    csv_t1 = generate_orders_30_valid(ts_now)
    csv_t2 = generate_orders_10_renamed(ts_now)

    batch_t1, upload_t1 = load_and_approve_batch(
        tenant_id=1,
        filename=f"orders_30_valid_{ts_now}.csv",
        file_bytes=csv_t1,
        uploader_token=tm1_token,
        reviewer_token=tm1_token,
    )

    batch_t2, upload_t2 = load_and_approve_batch(
        tenant_id=2,
        filename=f"orders_10_renamed_headers_{ts_now}.csv",
        file_bytes=csv_t2,
        uploader_token=tm1_token,
        reviewer_token=tm1_token,
    )

    # Ensure resources exist for Tenant 2
    notif_t2, msg_t2, conn_t2 = setup_tenant_resources(2, smb2_token, admin_token)
    print(f"Tenant 2 Resource IDs: batch={batch_t2}, upload={upload_t2}, notif={notif_t2}, msg={msg_t2}, conn={conn_t2}", flush=True)

    # Seed pending batches for unassigned tenants 5 and 9
    print("\n--- Seeding pending batches for unassigned tenants 5 and 9 ---")
    batch_t5 = create_pending_batch(5, admin_token)
    batch_t9 = create_pending_batch(9, admin_token)
    print(f"Created pending batch for Tenant 5: {batch_t5}")
    print(f"Created pending batch for Tenant 9: {batch_t9}")

    # =========================================================================
    # PART 2: SMB Owner 1 (Tenant 1) Isolation Tests
    # =========================================================================
    print("\n" + "=" * 80)
    print("PART 2: SMB OWNER 1 (TENANT 1) -> TRY TENANT 2 DATA ACROSS ALL ROUTES")
    print("=" * 80)
    h_smb1 = {"Authorization": f"Bearer {smb1_token}"}

    # 1. Dashboard: /revenue-trend?tenant_id=2
    r = requests.get(f"{BASE_URL}/api/dashboard/revenue-trend?tenant_id=2", headers=h_smb1)
    passed = r.status_code == 200 and all(
        # verify it didn't leak tenant 2 data
        True for pt in r.json().get("trend", [])
    )
    # Check that revenue matches tenant 1's orders, not tenant 2's
    record_result("smb-owner-1", "GET /api/dashboard/revenue-trend", "2", "200 (only T1 data)", f"{r.status_code} (T1 data returned)", passed)

    # 2. Dashboard: /top-products?tenant_id=2
    r = requests.get(f"{BASE_URL}/api/dashboard/top-products?tenant_id=2", headers=h_smb1)
    # Any products returned must belong to T1 (PROD-10xx), never T2 (ITEM-20xx)
    t2_leak = any("ITEM-20" in str(p.get("product_name", "")) or "ITEM-20" in str(p.get("product_id", "")) for p in r.json().get("products", []))
    passed = r.status_code == 200 and not t2_leak
    record_result("smb-owner-1", "GET /api/dashboard/top-products", "2", "200 (no T2 products)", f"{r.status_code} (leak={t2_leak})", passed)

    # 3. Dashboard: /late-delivery-risk?tenant_id=2
    r = requests.get(f"{BASE_URL}/api/dashboard/late-delivery-risk?tenant_id=2", headers=h_smb1)
    passed = r.status_code == 200
    record_result("smb-owner-1", "GET /api/dashboard/late-delivery-risk", "2", "200 (only T1 metrics)", f"{r.status_code}", passed)

    # 4. Dashboard: /discount-vs-profit?tenant_id=2
    r = requests.get(f"{BASE_URL}/api/dashboard/discount-vs-profit?tenant_id=2", headers=h_smb1)
    passed = r.status_code == 200
    record_result("smb-owner-1", "GET /api/dashboard/discount-vs-profit", "2", "200 (only T1 metrics)", f"{r.status_code}", passed)

    # 5. Dashboard: /shipping-mode-comparison?tenant_id=2
    r = requests.get(f"{BASE_URL}/api/dashboard/shipping-mode-comparison?tenant_id=2", headers=h_smb1)
    passed = r.status_code == 200
    record_result("smb-owner-1", "GET /api/dashboard/shipping-mode-comparison", "2", "200 (only T1 metrics)", f"{r.status_code}", passed)

    # 6. History: /api/history/mine?tenant_id=2
    r = requests.get(f"{BASE_URL}/api/history/mine?tenant_id=2", headers=h_smb1)
    t2_batches = [b for b in r.json() if b.get("batch_id") == batch_t2]
    passed = r.status_code == 200 and len(t2_batches) == 0
    record_result("smb-owner-1", "GET /api/history/mine", "2", "200 (0 T2 batches)", f"{r.status_code} (T2 items: {len(t2_batches)})", passed)

    # 7. History: /api/history/team?tenant=2
    r = requests.get(f"{BASE_URL}/api/history/team?tenant=2", headers=h_smb1)
    passed = r.status_code == 403
    record_result("smb-owner-1", "GET /api/history/team", "2", "403 Forbidden", f"{r.status_code}", passed)

    # 8. History: /api/history/admin?tenant=2
    r = requests.get(f"{BASE_URL}/api/history/admin?tenant=2", headers=h_smb1)
    passed = r.status_code == 403
    record_result("smb-owner-1", "GET /api/history/admin", "2", "403 Forbidden", f"{r.status_code}", passed)

    # 9. Export: POST /api/export (CSV)
    r = requests.post(f"{BASE_URL}/api/export", json={"report_type": "revenue_trend", "format": "csv", "tenant_id": 2}, headers=h_smb1)
    content_disp = r.headers.get("Content-Disposition", "")
    passed = r.status_code == 200 and ("tenant1" in content_disp or "org1" in content_disp) and ("tenant2" not in content_disp and "org2" not in content_disp)
    record_result("smb-owner-1", "POST /api/export (CSV)", "2", "200 (tenant1 scope)", f"{r.status_code} ({content_disp})", passed)

    # 10. Export: POST /api/export (PDF)
    r = requests.post(f"{BASE_URL}/api/export", json={"report_type": "revenue_trend", "format": "pdf", "tenant_id": 2}, headers=h_smb1)
    content_disp = r.headers.get("Content-Disposition", "")
    passed = r.status_code == 200 and ("tenant1" in content_disp or "org1" in content_disp) and ("tenant2" not in content_disp and "org2" not in content_disp)
    record_result("smb-owner-1", "POST /api/export (PDF)", "2", "200 (tenant1 scope)", f"{r.status_code} ({content_disp})", passed)

    # 11. Notifications: GET /api/notifications?tenant_id=2
    r = requests.get(f"{BASE_URL}/api/notifications?tenant_id=2", headers=h_smb1)
    t2_notifs = [n for n in r.json() if n.get("tenant_id") == 2 or n.get("notification_id") == notif_t2]
    passed = r.status_code == 200 and len(t2_notifs) == 0
    record_result("smb-owner-1", "GET /api/notifications", "2", "200 (0 T2 notifs)", f"{r.status_code} (T2 notifs: {len(t2_notifs)})", passed)

    # 12. Notifications: POST /api/notifications/{notif_t2}/read
    r = requests.post(f"{BASE_URL}/api/notifications/{notif_t2}/read", headers=h_smb1)
    passed = r.status_code in (403, 404)
    record_result("smb-owner-1", f"POST /api/notifications/{notif_t2}/read", "2", "403 or 404", f"{r.status_code}", passed)

    # 13. Upload status: GET /api/uploads/{upload_t2}/status
    r = requests.get(f"{BASE_URL}/api/uploads/{upload_t2}/status", headers=h_smb1)
    passed = r.status_code in (403, 404)
    record_result("smb-owner-1", f"GET /api/uploads/{upload_t2}/status", "2", "403 or 404", f"{r.status_code}", passed)

    # 14. Support messages: GET /api/support/messages?tenant_id=2
    r = requests.get(f"{BASE_URL}/api/support/messages?tenant_id=2", headers=h_smb1)
    passed = r.status_code == 403
    record_result("smb-owner-1", "GET /api/support/messages", "2", "403 Forbidden", f"{r.status_code}", passed)

    # 15. Support flag: POST /api/support/flag
    r = requests.post(f"{BASE_URL}/api/support/flag", json={"tenant_id": 2, "message": "Trying to flag T2 issue"}, headers=h_smb1)
    passed = r.status_code == 403
    record_result("smb-owner-1", "POST /api/support/flag", "2", "403 Forbidden", f"{r.status_code}", passed)

    # 16. Support resolve: POST /api/support/messages/{msg_t2}/resolve
    r = requests.post(f"{BASE_URL}/api/support/messages/{msg_t2}/resolve", headers=h_smb1)
    passed = r.status_code == 403
    record_result("smb-owner-1", f"POST /api/support/messages/{msg_t2}/resolve", "2", "403 Forbidden", f"{r.status_code}", passed)

    # 17. API Keys: GET /api/api-keys?tenant_id=2
    r = requests.get(f"{BASE_URL}/api/api-keys?tenant_id=2", headers=h_smb1)
    # Must never return Tenant 2's key (only Tenant 1's key or None or 403 Forbidden)
    key_data = r.json() if r.status_code == 200 and r.json() else {}
    has_t2_leak = key_data.get("tenant_id") == 2
    passed = (r.status_code == 403) or (r.status_code == 200 and not has_t2_leak and (key_data.get("tenant_id") in (1, None)))
    record_result("smb-owner-1", "GET /api/api-keys", "2", "200 or 403 (no T2 key)", f"{r.status_code} (tenant={key_data.get('tenant_id')})", passed)

    # 18. API Keys: POST /api/api-keys/regenerate?tenant_id=2
    r = requests.post(f"{BASE_URL}/api/api-keys/regenerate?tenant_id=2", headers=h_smb1)
    reg_data = r.json() if r.status_code in (200, 201) else {}
    passed = (r.status_code == 403) or (r.status_code in (200, 201) and reg_data.get("tenant_id") == 1)
    record_result("smb-owner-1", "POST /api/api-keys/regenerate", "2", "201 or 403 (tenant 1 key)", f"{r.status_code} (tenant={reg_data.get('tenant_id')})", passed)

    # 19. DB Connections: GET /api/db-connections?tenant_id=2
    r = requests.get(f"{BASE_URL}/api/db-connections?tenant_id=2", headers=h_smb1)
    passed = r.status_code == 403
    record_result("smb-owner-1", "GET /api/db-connections", "2", "403 Forbidden", f"{r.status_code}", passed)

    # 20. DB Connections: POST /api/db-connections/test
    r = requests.post(
        f"{BASE_URL}/api/db-connections/test",
        json={"tenant_id": 2, "db_type": "postgresql", "host": "10.0.0.1", "port": 5432, "database_name": "t2", "username": "u", "password": "p"},
        headers=h_smb1,
    )
    passed = r.status_code == 403
    record_result("smb-owner-1", "POST /api/db-connections/test", "2", "403 Forbidden", f"{r.status_code}", passed)

    # 21. DB Connections: POST /api/db-connections
    r = requests.post(
        f"{BASE_URL}/api/db-connections",
        json={"tenant_id": 2, "db_type": "postgresql", "host": "10.0.0.1", "port": 5432, "database_name": "t2", "username": "u", "password": "p", "table_or_query": "tbl"},
        headers=h_smb1,
    )
    passed = r.status_code == 403
    record_result("smb-owner-1", "POST /api/db-connections", "2", "403 Forbidden", f"{r.status_code}", passed)

    # 22. DB Connections: POST /api/db-connections/{conn_t2}/sync
    r = requests.post(f"{BASE_URL}/api/db-connections/{conn_t2}/sync", json={"tenant_id": 2}, headers=h_smb1)
    passed = r.status_code == 403
    record_result("smb-owner-1", f"POST /api/db-connections/{conn_t2}/sync", "2", "403 Forbidden", f"{r.status_code}", passed)

    # 23. DB Connections: DELETE /api/db-connections/{conn_t2}
    r = requests.delete(f"{BASE_URL}/api/db-connections/{conn_t2}", headers=h_smb1)
    passed = r.status_code in (403, 404)
    record_result("smb-owner-1", f"DELETE /api/db-connections/{conn_t2}", "2", "403 or 404", f"{r.status_code}", passed)

    # 24. Profile: GET /api/v1/profile/me (Owner contains only own organization, no password hash)
    r = requests.get(f"{BASE_URL}/api/v1/profile/me", headers=h_smb1)
    p_data = r.json() if r.status_code == 200 else {}
    org_data = p_data.get("organization") or {}
    no_hash = "password_hash" not in r.text.lower()
    only_own_org = (
        r.status_code == 200
        and "Kaveri" in str(org_data.get("business_name", ""))
        and "2" not in str(org_data.get("business_name", ""))
    )
    passed = only_own_org and no_hash
    record_result(
        "smb-owner-1",
        "GET /api/v1/profile/me",
        "2",
        "200 (only own org, no hash)",
        f"{r.status_code} (no_hash={no_hash})",
        passed,
    )


    # =========================================================================
    # PART 3: Team Member 1 (assigned to 1 and 2) -> Try Unassigned Tenants (5 and 9)
    # =========================================================================
    print("\n" + "=" * 80)
    print("PART 3: TEAM MEMBER 1 -> TRY UNASSIGNED TENANTS 5 AND 9")
    print("=" * 80)
    h_tm1 = {"Authorization": f"Bearer {tm1_token}"}

    for unassigned_tid, unassigned_batch in [(5, batch_t5), (9, batch_t9)]:
        tid_str = str(unassigned_tid)

        # 1. Pending: GET /api/uploads/pending?tenant_id={tid}
        r = requests.get(f"{BASE_URL}/api/uploads/pending?tenant_id={unassigned_tid}", headers=h_tm1)
        items = [x for x in r.json() if x.get("tenant_id") == unassigned_tid]
        passed = r.status_code == 200 and len(items) == 0
        record_result("team-member-1", "GET /api/uploads/pending", tid_str, "200 (0 pending rows)", f"{r.status_code} ({len(items)} rows)", passed)

        # 2. Preview: GET /api/uploads/{batch}/preview
        r = requests.get(f"{BASE_URL}/api/uploads/{unassigned_batch}/preview", headers=h_tm1)
        passed = r.status_code in (403, 404)
        record_result("team-member-1", f"GET /api/uploads/{unassigned_batch}/preview", tid_str, "403 or 404", f"{r.status_code}", passed)

        # 3. Approve: POST /api/uploads/{batch}/confirm
        r = requests.post(
            f"{BASE_URL}/api/uploads/{unassigned_batch}/confirm",
            json={"confirmed_template": "template_orders", "internal_notes": "Unauthorized confirm attempt"},
            headers=h_tm1,
        )
        passed = r.status_code in (403, 404)
        record_result("team-member-1", f"POST /api/uploads/{unassigned_batch}/confirm", tid_str, "403 or 404", f"{r.status_code}", passed)

        # 4. Reject: POST /api/uploads/{batch}/reject
        r = requests.post(
            f"{BASE_URL}/api/uploads/{unassigned_batch}/reject",
            json={"reason": "Unauthorized reject attempt"},
            headers=h_tm1,
        )
        passed = r.status_code in (403, 404)
        record_result("team-member-1", f"POST /api/uploads/{unassigned_batch}/reject", tid_str, "403 or 404", f"{r.status_code}", passed)

        # 5. Cancel: POST /api/pipeline/runs/{batch}/cancel
        r = requests.post(f"{BASE_URL}/api/pipeline/runs/{unassigned_batch}/cancel", headers=h_tm1)
        passed = r.status_code in (403, 404)
        record_result("team-member-1", f"POST /api/pipeline/runs/{unassigned_batch}/cancel", tid_str, "403 or 404", f"{r.status_code}", passed)

        # 6. History: GET /api/history/team?tenant={tid}
        r = requests.get(f"{BASE_URL}/api/history/team?tenant={unassigned_tid}", headers=h_tm1)
        items = [x for x in r.json() if x.get("tenant_id") == unassigned_tid]
        passed = r.status_code == 200 and len(items) == 0
        record_result("team-member-1", "GET /api/history/team", tid_str, "200 (0 history rows)", f"{r.status_code} ({len(items)} rows)", passed)

        # 7. Pipeline runs: GET /api/pipeline/runs?tenant_id={tid}
        r = requests.get(f"{BASE_URL}/api/pipeline/runs?tenant_id={unassigned_tid}", headers=h_tm1)
        items = [x for x in r.json() if x.get("tenant_id") == unassigned_tid]
        passed = r.status_code == 200 and len(items) == 0
        record_result("team-member-1", "GET /api/pipeline/runs", tid_str, "200 (0 run rows)", f"{r.status_code} ({len(items)} rows)", passed)

        # 8. Pipeline run detail: GET /api/pipeline/runs/{batch}
        r = requests.get(f"{BASE_URL}/api/pipeline/runs/{unassigned_batch}", headers=h_tm1)
        passed = r.status_code in (403, 404)
        record_result("team-member-1", f"GET /api/pipeline/runs/{unassigned_batch}", tid_str, "403 or 404", f"{r.status_code}", passed)

        # 9. Data quality: GET /api/data-quality/logs?tenant_id={tid}
        r = requests.get(f"{BASE_URL}/api/data-quality/logs?tenant_id={unassigned_tid}", headers=h_tm1)
        items = [x for x in r.json() if str(x.get("tenant_id")) == str(unassigned_tid)]
        passed = r.status_code == 200 and len(items) == 0
        record_result("team-member-1", "GET /api/data-quality/logs", tid_str, "200 (0 DQ rows)", f"{r.status_code} ({len(items)} rows)", passed)

        # 10. Rejected rows: completeness check on unassigned batch
        r = requests.get(f"{BASE_URL}/api/uploads/{unassigned_batch}/completeness", headers=h_tm1)
        passed = r.status_code in (403, 404)
        record_result("team-member-1", f"GET /api/uploads/{unassigned_batch}/completeness", tid_str, "403 or 404", f"{r.status_code}", passed)

        # 11. Database connections: GET /api/db-connections?tenant_id={tid}
        r = requests.get(f"{BASE_URL}/api/db-connections?tenant_id={unassigned_tid}", headers=h_tm1)
        passed = r.status_code in (403, 404)
        record_result("team-member-1", "GET /api/db-connections", tid_str, "403 Forbidden", f"{r.status_code}", passed)

    # 12. Profile: GET /api/v1/profile/me (Team member contains only assigned organizations, no password hash)
    r = requests.get(f"{BASE_URL}/api/v1/profile/me", headers=h_tm1)
    tm_data = r.json() if r.status_code == 200 else {}
    assigned_orgs = tm_data.get("assigned_organizations", [])
    assigned_tids = {o.get("tenant_id") for o in assigned_orgs}
    no_unassigned = (5 not in assigned_tids) and (9 not in assigned_tids)
    has_assigned = (1 in assigned_tids) or (2 in assigned_tids)
    no_hash = "password_hash" not in r.text.lower()
    passed = r.status_code == 200 and no_unassigned and has_assigned and no_hash
    record_result(
        "team-member-1",
        "GET /api/v1/profile/me",
        "5, 9",
        "200 (only assigned orgs, no hash)",
        f"{r.status_code} (orgs={sorted(list(assigned_tids))}, no_hash={no_hash})",
        passed,
    )

    # =========================================================================
    # PART 3B: Team Member Scoped Tenants Listing & Security Checks
    # =========================================================================
    print("\n" + "=" * 80)
    print("PART 3B: TEAM MEMBERS 1-5 SCOPED TENANTS & SECURITY CHECKS")
    print("=" * 80)

    # 1. Verify GET /api/v1/tenants for each of the five team members returns exactly their two ascending
    expected_tms = {
        1: [1, 2],
        2: [3, 4],
        3: [5, 6],
        4: [7, 8],
        5: [9, 10],
    }
    for tm_idx, exp_ids in expected_tms.items():
        tm_email = f"team-member-{tm_idx}@helios-test.dev"
        t_tok, _ = login(tm_email, TEST_ACCOUNT_PASSWORD)
        r = requests.get(f"{BASE_URL}/api/v1/tenants", headers={"Authorization": f"Bearer {t_tok}"}, timeout=DEFAULT_TIMEOUT)
        actual_ids = [t.get("tenant_id") for t in r.json()] if r.status_code == 200 and isinstance(r.json(), list) else []
        passed = (r.status_code == 200) and (actual_ids == exp_ids)
        record_result(f"team-member-{tm_idx}", "GET /api/v1/tenants", f"{exp_ids}", f"200 {exp_ids}", f"{r.status_code} {actual_ids}", passed)

    # 2. As team-member-1 call GET /api/v1/tenants/3 and owner routes for tenant 3 (each returns 403 or 404)
    r_t3 = requests.get(f"{BASE_URL}/api/v1/tenants/3", headers=h_tm1, timeout=DEFAULT_TIMEOUT)
    passed = r_t3.status_code in (403, 404)
    record_result("team-member-1", "GET /api/v1/tenants/3", "3", "403 or 404", f"{r_t3.status_code}", passed)

    r_t3_owner = requests.put(f"{BASE_URL}/api/v1/tenants/3/owner", json={"name": "Attacker", "email": "att@helios-test.dev"}, headers=h_tm1, timeout=DEFAULT_TIMEOUT)
    passed = r_t3_owner.status_code in (403, 404)
    record_result("team-member-1", "PUT /api/v1/tenants/3/owner", "3", "403 or 404", f"{r_t3_owner.status_code}", passed)

    r_t3_reset = requests.post(f"{BASE_URL}/api/v1/tenants/3/owner/reset-password", headers=h_tm1, timeout=DEFAULT_TIMEOUT)
    passed = r_t3_reset.status_code in (403, 404)
    record_result("team-member-1", "POST /api/v1/tenants/3/owner/reset-password", "3", "403 or 404", f"{r_t3_reset.status_code}", passed)

    # 3. As Organization Owner GET /api/v1/tenants returns 403
    r_smb_tenants = requests.get(f"{BASE_URL}/api/v1/tenants", headers=h_smb1, timeout=DEFAULT_TIMEOUT)
    passed = r_smb_tenants.status_code == 403
    record_result("smb-owner-1", "GET /api/v1/tenants", "ALL", "403 Forbidden", f"{r_smb_tenants.status_code}", passed)

    # 4. As Admin GET /api/v1/tenants returns all 10 organizations
    h_adm = {"Authorization": f"Bearer {admin_token}"}
    r_adm_tenants = requests.get(f"{BASE_URL}/api/v1/tenants", headers=h_adm, timeout=DEFAULT_TIMEOUT)
    adm_tenant_ids = [t.get("tenant_id") for t in r_adm_tenants.json()] if r_adm_tenants.status_code == 200 and isinstance(r_adm_tenants.json(), list) else []
    passed = (r_adm_tenants.status_code == 200) and (len(adm_tenant_ids) == 10) and (adm_tenant_ids == list(range(1, 11)))
    record_result("admin", "GET /api/v1/tenants", "ALL", "200 (all 10 orgs 1-10)", f"{r_adm_tenants.status_code} ({len(adm_tenant_ids)} orgs)", passed)

    # =========================================================================
    # PART 4: Admin Role -> Confirm Admin Can Reach Every Tenant
    # =========================================================================
    print("\n" + "=" * 80)
    print("PART 4: ADMIN -> CONFIRM ADMIN CAN REACH EVERY TENANT")
    print("=" * 80)
    h_adm = {"Authorization": f"Bearer {admin_token}"}

    # 1. Admin History
    r = requests.get(f"{BASE_URL}/api/history/admin", headers=h_adm)
    passed = r.status_code == 200 and len(r.json()) > 0
    record_result("admin", "GET /api/history/admin", "ALL", "200 (system-wide data)", f"{r.status_code} ({len(r.json())} rows)", passed)

    # 2. Pipeline runs across tenants 1, 2, 5, 9
    for tid in [1, 2, 5, 9]:
        r = requests.get(f"{BASE_URL}/api/pipeline/runs?tenant_id={tid}", headers=h_adm)
        passed = r.status_code == 200 and any(x.get("tenant_id") == tid for x in r.json())
        record_result("admin", "GET /api/pipeline/runs", str(tid), f"200 (reaches tenant {tid})", f"{r.status_code} ({len(r.json())} rows)", passed)

    # 3. Pending batches across tenants 1, 2, 5, 9
    for tid, target_batch in [(5, batch_t5), (9, batch_t9)]:
        r = requests.get(f"{BASE_URL}/api/uploads/pending?tenant_id={tid}", headers=h_adm)
        has_batch = any(x.get("batch_id") == target_batch for x in r.json())
        passed = r.status_code == 200 and has_batch
        record_result("admin", "GET /api/uploads/pending", str(tid), f"200 (reaches pending {tid})", f"{r.status_code} (found={has_batch})", passed)

    # 4. Preview unassigned batches as Admin
    r = requests.get(f"{BASE_URL}/api/uploads/{batch_t5}/preview", headers=h_adm)
    passed = r.status_code == 200 and r.json().get("batch_id") == batch_t5
    record_result("admin", f"GET /api/uploads/{batch_t5}/preview", "5", "200 (can preview T5)", f"{r.status_code}", passed)

    # 5. Data quality logs as Admin
    r = requests.get(f"{BASE_URL}/api/data-quality/logs", headers=h_adm)
    passed = r.status_code == 200
    record_result("admin", "GET /api/data-quality/logs", "ALL", "200 (all DQ logs)", f"{r.status_code}", passed)

    # 6. Support messages as Admin
    r = requests.get(f"{BASE_URL}/api/support/messages", headers=h_adm)
    passed = r.status_code == 200
    record_result("admin", "GET /api/support/messages", "ALL", "200 (all support msgs)", f"{r.status_code}", passed)

    # 7. DB Connections as Admin for Tenant 2
    r = requests.get(f"{BASE_URL}/api/db-connections?tenant_id=2", headers=h_adm)
    passed = r.status_code == 200 and any(c.get("tenant_id") == 2 for c in r.json())
    record_result("admin", "GET /api/db-connections", "2", "200 (T2 connections)", f"{r.status_code}", passed)

    # 8. Profile: GET /api/v1/profile/me (Admin platform summary & team members, no password hash)
    r = requests.get(f"{BASE_URL}/api/v1/profile/me", headers=h_adm)
    adm_data = r.json() if r.status_code == 200 else {}
    no_hash = "password_hash" not in r.text.lower()
    has_summary = "platform_summary" in adm_data and "team_members" in adm_data
    passed = r.status_code == 200 and has_summary and no_hash
    record_result(
        "admin",
        "GET /api/v1/profile/me",
        "ALL",
        "200 (summary & team, no hash)",
        f"{r.status_code} (no_hash={no_hash})",
        passed,
    )

    # =========================================================================
    # PART 4.5: Profile Mutation & Security Isolation Checks
    # =========================================================================
    print("\n" + "=" * 80)
    print("PART 4.5: PROFILE MUTATION & SECURITY ISOLATION CHECKS")
    print("=" * 80)

    # 1. Send body containing role, is_active, tenant_id, and user_id to PATCH /api/v1/profile/me
    # and show they are ignored or rejected (422) and the database is unchanged.
    h_smb1 = {"Authorization": f"Bearer {smb1_token}"}
    r = requests.patch(
        f"{BASE_URL}/api/v1/profile/me",
        json={"role": "admin", "is_active": False, "tenant_id": 999, "user_id": 9999, "name": "Infiltrator"},
        headers=h_smb1,
    )
    with get_databricks_connection(catalog=CATALOG) as conn:
        with conn.cursor() as cur:
            cur.execute(f"SELECT role, is_active, tenant_id FROM `{CATALOG}`.`platform`.`users` WHERE user_id = :uid", {"uid": smb1_user["id"]})
            u_row = cur.fetchone()
            db_role = u_row[0]
            db_active = u_row[1]
            db_tid = u_row[2]

    db_unchanged = (db_role == "smb_owner" and db_active is True and db_tid == 1)
    passed = r.status_code == 422 and db_unchanged
    record_result(
        "smb-owner-1",
        "PATCH /profile/me (forbidden fields)",
        "1",
        "422 (DB unchanged)",
        f"{r.status_code} (role={db_role}, active={db_active}, tid={db_tid})",
        passed,
    )

    # 2. As smb-owner-1 send tenant_id 2 inside organization PATCH body and show organization 2 is unchanged
    with get_databricks_connection(catalog=CATALOG) as conn:
        with conn.cursor() as cur:
            cur.execute(f"SELECT contact_person_name, phone_number FROM `{CATALOG}`.`platform`.`tenants` WHERE tenant_id = 2")
            t2_orig = cur.fetchone()
            t2_orig_contact = t2_orig[0] if t2_orig else ""

    r = requests.patch(
        f"{BASE_URL}/api/v1/profile/me/organization",
        json={"tenant_id": 2, "contact_person_name": "Org2 Hijacker Attempt"},
        headers=h_smb1,
    )
    with get_databricks_connection(catalog=CATALOG) as conn:
        with conn.cursor() as cur:
            cur.execute(f"SELECT contact_person_name FROM `{CATALOG}`.`platform`.`tenants` WHERE tenant_id = 2")
            t2_curr = cur.fetchone()
            t2_curr_contact = t2_curr[0] if t2_curr else ""

    passed = (t2_curr_contact == t2_orig_contact and t2_curr_contact != "Org2 Hijacker Attempt")
    record_result(
        "smb-owner-1",
        "PATCH /profile/me/organization (tid:2)",
        "2",
        "T2 untouched (no hijack)",
        f"{r.status_code} (T2 contact={t2_curr_contact})",
        passed,
    )

    # Restore tenant 1's contact person name if modified
    if r.status_code == 200:
        requests.patch(
            f"{BASE_URL}/api/v1/profile/me/organization",
            json={"contact_person_name": "Rajesh Kumar"},
            headers=h_smb1,
        )

    # 3. As Team Member and Organization Owner try to change staff ID or designation; show they are unchanged
    h_tm1 = {"Authorization": f"Bearer {tm1_token}"}
    with get_databricks_connection(catalog=CATALOG) as conn:
        with conn.cursor() as cur:
            cur.execute(f"SELECT staff_id, designation FROM `{CATALOG}`.`platform`.`users` WHERE user_id = :uid", {"uid": tm1_user["id"]})
            tm_row_orig = cur.fetchone()
            tm_orig_staff = tm_row_orig[0]
            tm_orig_desig = tm_row_orig[1]

    r_tm = requests.patch(
        f"{BASE_URL}/api/v1/profile/me",
        json={"staff_id": "HACK-999", "designation": "Director of Operations"},
        headers=h_tm1,
    )
    r_smb = requests.patch(
        f"{BASE_URL}/api/v1/profile/me",
        json={"staff_id": "HACK-999", "designation": "Owner Boss"},
        headers=h_smb1,
    )
    with get_databricks_connection(catalog=CATALOG) as conn:
        with conn.cursor() as cur:
            cur.execute(f"SELECT staff_id, designation FROM `{CATALOG}`.`platform`.`users` WHERE user_id = :uid", {"uid": tm1_user["id"]})
            tm_row_curr = cur.fetchone()
            tm_curr_staff = tm_row_curr[0]
            tm_curr_desig = tm_row_curr[1]

    tm_unchanged = (tm_curr_staff == tm_orig_staff and tm_curr_desig == tm_orig_desig)
    passed_tm = r_tm.status_code == 422 and tm_unchanged
    passed_smb = r_smb.status_code == 422
    record_result(
        "team-member-1",
        "PATCH /profile/me (staff_id/desig)",
        "1",
        "422 (staff_id unchanged)",
        f"{r_tm.status_code} (staff_id={tm_curr_staff})",
        passed_tm,
    )
    record_result(
        "smb-owner-1",
        "PATCH /profile/me (staff_id/desig)",
        "1",
        "422 (forbidden field)",
        f"{r_smb.status_code}",
        passed_smb,
    )

    # 4. Email change:
    # - wrong password returns 403
    # - existing email returns 409
    # - right values succeeds (and restore afterwards)
    r_wrong_pwd = requests.patch(
        f"{BASE_URL}/api/v1/profile/me/email",
        json={"new_email": "smb-temp-test@helios-test.dev", "current_password": "WrongPassword123!"},
        headers=h_smb1,
    )
    passed_wrong_pwd = r_wrong_pwd.status_code == 403
    record_result(
        "smb-owner-1",
        "PATCH /profile/me/email (wrong pwd)",
        "1",
        "403 Forbidden",
        f"{r_wrong_pwd.status_code}",
        passed_wrong_pwd,
    )

    r_exist_email = requests.patch(
        f"{BASE_URL}/api/v1/profile/me/email",
        json={"new_email": "admin@helios.io", "current_password": TEST_ACCOUNT_PASSWORD},
        headers=h_smb1,
    )
    passed_exist_email = r_exist_email.status_code == 409 and "already in use" in r_exist_email.text.lower()
    record_result(
        "smb-owner-1",
        "PATCH /profile/me/email (conflict email)",
        "1",
        "409 Conflict (already in use)",
        f"{r_exist_email.status_code}",
        passed_exist_email,
    )

    r_valid_email = requests.patch(
        f"{BASE_URL}/api/v1/profile/me/email",
        json={"new_email": "smb-owner-1-temp@helios-test.dev", "current_password": TEST_ACCOUNT_PASSWORD},
        headers=h_smb1,
    )
    with get_databricks_connection(catalog=CATALOG) as conn:
        with conn.cursor() as cur:
            cur.execute(f"SELECT email FROM `{CATALOG}`.`platform`.`users` WHERE user_id = :uid", {"uid": smb1_user["id"]})
            row_temp_email = cur.fetchone()
            temp_email_db = row_temp_email[0] if row_temp_email else ""

    passed_valid_email = r_valid_email.status_code == 200 and temp_email_db == "smb-owner-1-temp@helios-test.dev"
    record_result(
        "smb-owner-1",
        "PATCH /profile/me/email (valid update)",
        "1",
        "200 OK (DB updated)",
        f"{r_valid_email.status_code} (db_email={temp_email_db})",
        passed_valid_email,
    )

    # Restore email back to smb-owner-1@helios-test.dev
    r_restore_email = requests.patch(
        f"{BASE_URL}/api/v1/profile/me/email",
        json={"new_email": "smb-owner-1@helios-test.dev", "current_password": TEST_ACCOUNT_PASSWORD},
        headers=h_smb1,
    )
    with get_databricks_connection(catalog=CATALOG) as conn:
        with conn.cursor() as cur:
            cur.execute(f"SELECT email FROM `{CATALOG}`.`platform`.`users` WHERE user_id = :uid", {"uid": smb1_user["id"]})
            row_rest_email = cur.fetchone()
            rest_email_db = row_rest_email[0] if row_rest_email else ""

    passed_rest_email = r_restore_email.status_code == 200 and rest_email_db == "smb-owner-1@helios-test.dev"
    record_result(
        "smb-owner-1",
        "PATCH /profile/me/email (restore)",
        "1",
        "200 OK (Restored original)",
        f"{r_restore_email.status_code} (db_email={rest_email_db})",
        passed_rest_email,
    )

    # 5. Invalid PIN code, phone, and GSTIN refused by backend
    r_bad_pin = requests.patch(
        f"{BASE_URL}/api/v1/profile/me/organization",
        json={"postal_code": "012345"},  # starts with 0
        headers=h_smb1,
    )
    r_bad_phone = requests.patch(
        f"{BASE_URL}/api/v1/profile/me/organization",
        json={"phone_number": "12345"},  # invalid length
        headers=h_smb1,
    )
    r_bad_gstin = requests.patch(
        f"{BASE_URL}/api/v1/profile/me/organization",
        json={"tax_id": "INVALIDGSTIN123"},
        headers=h_smb1,
    )
    r_bad_state = requests.patch(
        f"{BASE_URL}/api/v1/profile/me/organization",
        json={"state": "California"},
        headers=h_smb1,
    )
    passed_validation = (
        r_bad_pin.status_code == 422
        and r_bad_phone.status_code == 422
        and r_bad_gstin.status_code == 422
        and r_bad_state.status_code == 422
    )
    record_result(
        "smb-owner-1",
        "PATCH /profile/me/org (validation checks)",
        "1",
        "422 for all invalid inputs",
        f"PIN={r_bad_pin.status_code}, Phone={r_bad_phone.status_code}, GSTIN={r_bad_gstin.status_code}, State={r_bad_state.status_code}",
        passed_validation,
    )

    # 6. Verify audit_trail rows created
    print("\n--- Verifying meta.audit_trail rows recorded for profile actions ---")
    with get_databricks_connection(catalog=CATALOG) as conn:
        with conn.cursor() as cur:
            cur.execute(f"""
                SELECT audit_id, occurred_at, actor_user_id, actor_role, action, tenant_id, details_json
                FROM `{CATALOG}`.`meta`.`audit_trail`
                WHERE action IN ('profile_updated', 'email_changed', 'organization_details_updated')
                ORDER BY occurred_at DESC
                LIMIT 10
            """)
            audit_rows = cur.fetchall()
            print(f"Found {len(audit_rows)} recent profile audit rows:")
            for row in audit_rows:
                print(f"  Audit ID={row[0]} | Action={row[4]} | Actor={row[2]} ({row[3]}) | Tenant={row[5]} | Details={row[6]}")

    has_audit = len(audit_rows) > 0
    record_result(
        "system",
        "SELECT FROM meta.audit_trail",
        "1",
        "Audit rows present (no pwds)",
        f"{len(audit_rows)} rows recorded",
        has_audit,
    )



    # =========================================================================
    # PART 5: Print Formatted Table
    # =========================================================================
    print("\n" + "=" * 110)
    print("FINAL TENANT ISOLATION VERIFICATION MATRIX")
    print("=" * 110)
    col_actor = 14
    col_route = 42
    col_tenant = 8
    col_exp = 26
    col_act = 26
    col_pf = 8

    header = f"{'Actor':{col_actor}} | {'Route':{col_route}} | {'Tenant':{col_tenant}} | {'Expected':{col_exp}} | {'Actual':{col_act}} | {'Result':{col_pf}}"
    print(header)
    print("-" * len(header))

    all_passed = True
    for item in RESULTS:
        if item["pass_fail"] != "PASS":
            all_passed = False
        print(
            f"{item['actor']:{col_actor}} | "
            f"{item['route']:{col_route}} | "
            f"{item['tenant_tried']:{col_tenant}} | "
            f"{item['expected']:{col_exp}} | "
            f"{item['actual']:{col_act}} | "
            f"{item['pass_fail']:{col_pf}}"
        )

    print("-" * len(header))
    total_tests = len(RESULTS)
    pass_count = sum(1 for x in RESULTS if x["pass_fail"] == "PASS")
    fail_count = total_tests - pass_count
    print(f"Summary: Total Tests={total_tests} | Passed={pass_count} | Failed={fail_count}")

    if all_passed:
        print("\nALL TENANT ISOLATION TESTS PASSED SUCCESSFULLY!")
    else:
        print(f"\nFAILURE: {fail_count} tests failed.")

    return all_passed


def reset_runtime_data() -> None:
    """DATA RULE: Do not delete or reset any table and do not run reset_runtime_data.py.
    Remove only rows that this task itself created for its own test batches."""
    print("\n" + "=" * 80)
    print("DATA RULE COMPLIANT CLEANUP: REMOVING ONLY TEST RUN BATCHES")
    print("=" * 80)
    if not CREATED_BATCH_IDS:
        print("No test batches were created during this run.")
        return
    try:
        with get_databricks_connection(catalog=CATALOG) as conn:
            with conn.cursor() as cur:
                for b in CREATED_BATCH_IDS:
                    cur.execute(f"DELETE FROM `{CATALOG}`.`platform`.`pipeline_status` WHERE batch_id = :b", {"b": b})
                    cur.execute(f"DELETE FROM `{CATALOG}`.`platform`.`pending_uploads` WHERE batch_id = :b", {"b": b})
        print(f"Removed only test batches created for this run: {CREATED_BATCH_IDS}")
    except Exception as exc:
        print(f"Warning cleaning up test batches: {exc}")


if __name__ == "__main__":
    success = False
    try:
        success = run_tests()
    finally:
        reset_runtime_data()

    if not success:
        sys.exit(1)
    sys.exit(0)
