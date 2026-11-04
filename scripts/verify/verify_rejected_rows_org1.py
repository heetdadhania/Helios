"""
Verification script for:
GET /api/v1/quality/rejected-rows/{batch_id}.csv
Verifies with Organization 1 demo batch:
1. Admin download: 200 OK, UTF-8 BOM present, CSV opens correctly.
2. Row count equals quality-log count (6 rejected rows).
3. Assigned team member (team-member-1, assigned to Org 1): 200 OK, 6 rows.
4. Unassigned team member (team-member-2, unassigned to Org 1): 403 Forbidden.
5. SMB Owner: 403 Forbidden.
"""

import csv
import io
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
BACKEND_DIR = REPO_ROOT / "backend"
sys.path.insert(0, str(BACKEND_DIR))
sys.path.insert(0, str(REPO_ROOT))

from fastapi.testclient import TestClient
from app.main import app
from app.core.dependencies import get_current_user, get_db_cursor
from app.schemas.auth import UserOut, UserRole

def run_verification():
    print("=" * 80)
    print("VERIFICATION: REJECTED ROWS CSV FOR INDIAN ORGANIZATION 1")
    print("=" * 80)

    # Load Organization 1 orders file
    org1_csv_path = REPO_ROOT / "scripts" / "data" / "helios_indian_data" / "org01_orders.csv"
    with open(org1_csv_path, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        all_rows = list(reader)

    print(f"Loaded {len(all_rows)} rows from org01_orders.csv")

    # Find the 6 bad rows (order_id starting with ORD-01-9)
    bad_rows = [r for r in all_rows if "-9" in r.get("order_id", "")]
    print(f"Identified {len(bad_rows)} rejected rows in Org 1 dataset:")
    for idx, br in enumerate(bad_rows, 1):
        print(f"  [{idx}] order_id={br['order_id']} | qty={br.get('quantity')} | date={br.get('order_date')}")

    assert len(bad_rows) == 6, f"Expected 6 bad rows in Org 1 dataset, got {len(bad_rows)}"

    BATCH_ID = "batch-org1-orders-demo-001"
    TENANT_ID = 1

    # Simulate meta.data_quality_log entries for these 6 rows
    now = datetime(2026, 10, 19, 12, 0, 0, tzinfo=timezone.utc)
    dq_log_entries = []
    for idx, br in enumerate(bad_rows, 1):
        reason = (
            "missing_required_key: quantity" if br.get("quantity") == ""
            else "invalid_quantity: quantity must be greater than zero (original_value: -2)" if str(br.get("quantity")) == "-2"
            else "invalid_date_fields: order_date (original_value: not-a-date)" if br.get("order_date") == "not-a-date"
            else "data_quality_validation_failure"
        )
        dq_log_entries.append((
            1000 + idx,       # log_id
            BATCH_ID,         # batch_id
            TENANT_ID,        # tenant_id
            "silver.orders_clean", # table_name
            br["order_id"],   # row_identifier
            reason,           # rejection_reason
            now,              # logged_at
        ))

    bronze_raw_entries = [
        (idx, json.dumps(row)) for idx, row in enumerate(all_rows, 1)
    ]

    mock_cursor = MagicMock()

    # Define cursor behavior
    def mock_cursor_execute(query, params=None):
        q = query.lower()
        if "pipeline_status" in q:
            mock_cursor.fetchone.return_value = (TENANT_ID,)
        elif "platform`.`team_assignments" in q and "limit 1" in q:
            # Check user_id in params
            uid = (params or {}).get("user_id")
            # user_id 1 is admin; user_id 10 is team-member-1 (assigned to tenant 1)
            # user_id 20 is team-member-2 (assigned to tenant 3 & 4, unassigned to tenant 1)
            if uid == 10:
                mock_cursor.fetchone.return_value = (1,)
            else:
                mock_cursor.fetchone.return_value = None
        elif "meta`.`data_quality_log" in q:
            mock_cursor.fetchall.return_value = dq_log_entries
        elif "bronze`.`raw_orders" in q:
            mock_cursor.fetchall.return_value = bronze_raw_entries
        elif "bronze`.`raw_shipping" in q:
            mock_cursor.fetchall.return_value = []
        else:
            mock_cursor.fetchone.return_value = None
            mock_cursor.fetchall.return_value = []

    mock_cursor.execute.side_effect = mock_cursor_execute

    client = TestClient(app)
    app.dependency_overrides[get_db_cursor] = lambda: mock_cursor

    # -------------------------------------------------------------
    # 1. ADMIN DOWNLOAD VERIFICATION
    # -------------------------------------------------------------
    print("\n--- Test 1: Admin downloads rejected rows CSV ---")
    admin_user = UserOut(
        id=1,
        name="Platform Admin",
        email="admin@helios.io",
        role=UserRole.ADMIN,
        tenant_id=None,
    )
    app.dependency_overrides[get_current_user] = lambda: admin_user

    resp = client.get(f"/api/v1/quality/rejected-rows/{BATCH_ID}.csv")
    print(f"Admin response status: {resp.status_code}")
    print(f"Content-Type: {resp.headers.get('content-type')}")
    print(f"Content-Disposition: {resp.headers.get('content-disposition')}")

    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    assert "text/csv" in resp.headers.get("content-type", "")
    assert f'filename="rejected_rows_{BATCH_ID}.csv"' in resp.headers.get("content-disposition", "")

    # Verify UTF-8 BOM
    raw_content = resp.content
    assert raw_content.startswith(b"\xef\xbb\xbf"), "CSV does not start with UTF-8 BOM (0xEF 0xBB 0xBF)"
    print("BOM check: PASSED (Starts with UTF-8 byte-order mark \\xef\\xbb\\xbf)")

    # Parse CSV correctly
    decoded_text = raw_content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(decoded_text))
    csv_rows = list(reader)

    print(f"CSV downloaded row count: {len(csv_rows)} (Quality log count: {len(dq_log_entries)})")
    assert len(csv_rows) == len(dq_log_entries), f"Row count {len(csv_rows)} != quality-log count {len(dq_log_entries)}"
    print("Row count equality check: PASSED (Downloaded CSV rows == quality log count == 6)")

    # Verify row fields
    for idx, r in enumerate(csv_rows, 1):
        assert "order_id" in r, "Missing order_id column"
        assert "rejection_reason" in r, "Missing rejection_reason column"
        print(f"  Row {idx}: {r['order_id']} | Reason: {r['rejection_reason'][:55]}...")

    # -------------------------------------------------------------
    # 2. ASSIGNED TEAM MEMBER VERIFICATION
    # -------------------------------------------------------------
    print("\n--- Test 2: Assigned Team Member (team-member-1, assigned to Org 1) ---")
    tm1_user = UserOut(
        id=10,
        name="Team Member 1",
        email="team-member-1@helios-test.dev",
        role=UserRole.TEAM_MEMBER,
        tenant_id=None,
    )
    app.dependency_overrides[get_current_user] = lambda: tm1_user

    resp_tm1 = client.get(f"/api/v1/quality/rejected-rows/{BATCH_ID}.csv")
    print(f"Assigned team member response status: {resp_tm1.status_code}")
    assert resp_tm1.status_code == 200, f"Expected 200, got {resp_tm1.status_code}"
    tm1_csv = list(csv.DictReader(io.StringIO(resp_tm1.content.decode("utf-8-sig"))))
    assert len(tm1_csv) == 6, f"Expected 6 rows, got {len(tm1_csv)}"
    print(f"Assigned team member access check: PASSED (200 OK, {len(tm1_csv)} rows)")

    # -------------------------------------------------------------
    # 3. UNASSIGNED TEAM MEMBER VERIFICATION
    # -------------------------------------------------------------
    print("\n--- Test 3: Unassigned Team Member (team-member-2, unassigned to Org 1) ---")
    tm2_user = UserOut(
        id=20,
        name="Team Member 2",
        email="team-member-2@helios-test.dev",
        role=UserRole.TEAM_MEMBER,
        tenant_id=None,
    )
    app.dependency_overrides[get_current_user] = lambda: tm2_user

    resp_tm2 = client.get(f"/api/v1/quality/rejected-rows/{BATCH_ID}.csv")
    print(f"Unassigned team member response status: {resp_tm2.status_code}")
    print(f"Unassigned team member error detail: {resp_tm2.json().get('detail')}")
    assert resp_tm2.status_code in (403, 404), f"Expected 403 or 404, got {resp_tm2.status_code}"
    print(f"Unassigned team member isolation check: PASSED (Returned {resp_tm2.status_code})")

    # -------------------------------------------------------------
    # 4. SMB OWNER FORBIDDEN VERIFICATION
    # -------------------------------------------------------------
    print("\n--- Test 4: SMB Owner access attempt ---")
    owner_user = UserOut(
        id=30,
        name="Owner User",
        email="owner-org1@helios-test.dev",
        role=UserRole.SMB_OWNER,
        tenant_id=1,
    )
    app.dependency_overrides[get_current_user] = lambda: owner_user

    resp_owner = client.get(f"/api/v1/quality/rejected-rows/{BATCH_ID}.csv")
    print(f"SMB Owner response status: {resp_owner.status_code}")
    assert resp_owner.status_code == 403, f"Expected 403, got {resp_owner.status_code}"
    print("SMB Owner access check: PASSED (Returned 403 Forbidden)")

    print("\n" + "=" * 80)
    print("ALL VERIFICATION CHECKS PASSED SUCCESSFULLY!")
    print("=" * 80)

if __name__ == "__main__":
    run_verification()

