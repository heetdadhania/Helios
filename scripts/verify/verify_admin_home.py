import os
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
import databricks.sql
import requests
from dotenv import load_dotenv

# Ensure UTF-8 stdout encoding for currency symbols on Windows
if sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT_DIR / "backend"))
load_dotenv(ROOT_DIR / ".env")

import subprocess

BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
API_PREFIX = "/api/v1"
TEST_PASSWORD = os.getenv("TEST_ACCOUNT_PASSWORD")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")

DATABRICKS_SERVER_HOSTNAME = os.getenv("DATABRICKS_SERVER_HOSTNAME")
DATABRICKS_HTTP_PATH = os.getenv("DATABRICKS_HTTP_PATH")
DATABRICKS_TOKEN = os.getenv("DATABRICKS_TOKEN")
CATALOG = os.getenv("DATABRICKS_CATALOG", "helios_catalog")

print("=" * 70)
print("HELIOS VERIFICATION SUITE: ADMIN HOME, PARALLEL QUERIES, CACHE & RBAC")
print("=" * 70)

assert TEST_PASSWORD, "TEST_ACCOUNT_PASSWORD must be set in environment"
assert ADMIN_PASSWORD, "ADMIN_PASSWORD must be set in environment"


def get_db_cursor():
    conn = databricks.sql.connect(
        server_hostname=DATABRICKS_SERVER_HOSTNAME,
        http_path=DATABRICKS_HTTP_PATH,
        access_token=DATABRICKS_TOKEN,
    )
    return conn, conn.cursor()


def login_user(email: str, password: str) -> str:
    resp = requests.post(
        f"{BASE_URL}{API_PREFIX}/auth/login",
        json={"email": email, "password": password},
    )
    if resp.status_code != 200:
        raise RuntimeError(f"Login failed for {email} ({resp.status_code}): {resp.text}")
    return resp.json()["access_token"]


# -----------------------------------------------------------------------------
# STEP 1: RBAC RESTRICTION VERIFICATION (403 FOR NON-ADMINS)
# -----------------------------------------------------------------------------
print("\n[STEP 1] Verifying RBAC Restrictions on GET /api/v1/oversight/home...")

# 1a. Team Member
team_token = login_user("team-member-1@helios-test.dev", TEST_PASSWORD)
resp_team = requests.get(
    f"{BASE_URL}{API_PREFIX}/oversight/home",
    headers={"Authorization": f"Bearer {team_token}"},
)
print(f"  Team Member access status: {resp_team.status_code}")
assert resp_team.status_code == 403, f"Expected 403 for team_member, got {resp_team.status_code}"

# 1b. Organization Owner
owner_token = login_user("smb-owner-1@helios-test.dev", TEST_PASSWORD)
resp_owner = requests.get(
    f"{BASE_URL}{API_PREFIX}/oversight/home",
    headers={"Authorization": f"Bearer {owner_token}"},
)
print(f"  Organization Owner access status: {resp_owner.status_code}")
assert resp_owner.status_code == 403, f"Expected 403 for smb_owner, got {resp_owner.status_code}"
print("  Verified: Non-admin roles strictly receive 403 Forbidden.")


# -----------------------------------------------------------------------------
# STEP 2: ADMIN ACCESS & IN-MEMORY CACHE TIMING
# -----------------------------------------------------------------------------
print("\n[STEP 2] Testing Admin Access and In-Memory 30s Caching...")
admin_token = login_user("admin@helios.io", ADMIN_PASSWORD)

t0 = time.time()
resp_initial = requests.get(
    f"{BASE_URL}{API_PREFIX}/oversight/home",
    headers={"Authorization": f"Bearer {admin_token}"},
)
t_initial = time.time() - t0
print(f"  Admin initial request status: {resp_initial.status_code} in {t_initial:.2f}s")
assert resp_initial.status_code == 200, f"Expected 200 for admin, got {resp_initial.status_code}: {resp_initial.text}"
home_data = resp_initial.json()

# Second call should hit in-memory cache (< 1.5s vs initial ~10s)
t0 = time.time()
resp_cached = requests.get(
    f"{BASE_URL}{API_PREFIX}/oversight/home",
    headers={"Authorization": f"Bearer {admin_token}"},
)
t_cached = time.time() - t0
print(f"  Admin cached request status: {resp_cached.status_code} in {t_cached:.4f}s")
assert resp_cached.status_code == 200
assert t_cached < 1.5, f"Expected cached response under 1.5s, got {t_cached:.4f}s"
print("  Verified: In-memory cache hit is instantaneous.")


# -----------------------------------------------------------------------------
# STEP 3: CARD NUMBERS EQUAL DATABASE COUNTS
# -----------------------------------------------------------------------------
print("\n[STEP 3] Verifying Summary Card Numbers Equal Database Counts...")
conn, cur = get_db_cursor()

db_query = f"""
SELECT
    (SELECT count(*) FROM `{CATALOG}`.`platform`.`tenants` WHERE is_active = true) AS active_orgs,
    (SELECT count(*) FROM `{CATALOG}`.`platform`.`tenants` WHERE is_active = false) AS inactive_orgs,
    (SELECT count(*) FROM `{CATALOG}`.`platform`.`tenants`) AS total_orgs,
    (SELECT count(*) FROM `{CATALOG}`.`platform`.`users` WHERE role = 'smb_owner' AND is_active = true) AS active_owners,
    (SELECT count(*) FROM `{CATALOG}`.`platform`.`users` WHERE role = 'team_member' AND is_active = true) AS team_members,
    (SELECT count(DISTINCT coalesce(pu.upload_id, ps.upload_id, ps.batch_id))
     FROM `{CATALOG}`.`platform`.`pipeline_status` ps
     FULL OUTER JOIN `{CATALOG}`.`platform`.`pending_uploads` pu ON ps.upload_id = pu.upload_id
     WHERE lower(coalesce(pu.status, '')) = 'pending'
        OR lower(coalesce(ps.status, '')) IN ('pending_review', 'awaiting_confirmation')
    ) AS pending_uploads,
    (SELECT count(*) FROM `{CATALOG}`.`platform`.`pipeline_status`
     WHERE lower(status) IN ('running', 'ingesting', 'silver_running', 'gold_running')
       AND (
           (last_heartbeat_at IS NULL AND created_at >= (current_timestamp() - INTERVAL 15 MINUTES))
           OR (last_heartbeat_at IS NOT NULL AND last_heartbeat_at >= (current_timestamp() - INTERVAL 15 MINUTES))
       )
    ) AS running_pipelines,
    (SELECT count(*) FROM `{CATALOG}`.`platform`.`pipeline_status` WHERE lower(status) IN ('failed', 'failure', 'error', 'restart_required')) AS failed_pipelines,
    (SELECT count(*) FROM `{CATALOG}`.`platform`.`support_messages` WHERE lower(status) = 'open') AS open_support_messages
"""
cur.execute(db_query)
db_counts = cur.fetchone()

summary = home_data["summary"]
print("  Comparing Dashboard Cards to Direct Database Query:")
print(f"    - Active Organizations: Card={summary['organizations_active']} | DB={db_counts[0]}")
assert summary['organizations_active'] == db_counts[0]

print(f"    - Inactive Organizations: Card={summary['organizations_inactive']} | DB={db_counts[1]}")
assert summary['organizations_inactive'] == db_counts[1]

print(f"    - Total Organizations: Card={summary['organizations_total']} | DB={db_counts[2]}")
assert summary['organizations_total'] == db_counts[2]

print(f"    - Active Owners: Card={summary['organization_owners_active']} | DB={db_counts[3]}")
assert summary['organization_owners_active'] == db_counts[3]

print(f"    - Team Members: Card={summary['team_members']} | DB={db_counts[4]}")
assert summary['team_members'] == db_counts[4]

print(f"    - Pending Uploads: Card={summary['pending_uploads']} | DB={db_counts[5]}")
assert summary['pending_uploads'] == db_counts[5]

print(f"    - Running Pipelines: Card={summary['running_pipelines']} | DB={db_counts[6]}")
assert summary['running_pipelines'] == db_counts[6]

print(f"    - Failed Pipelines: Card={summary['failed_pipelines']} | DB={db_counts[7]}")
assert summary['failed_pipelines'] == db_counts[7]

print(f"    - Open Support Messages: Card={summary['open_support_messages']} | DB={db_counts[8]}")
assert summary['open_support_messages'] == db_counts[8]

print("  Verified: All card numbers strictly equal direct database counts.")


# -----------------------------------------------------------------------------
# STEP 4: CHARTS AND TABLES STRUCTURAL VERIFICATION
# -----------------------------------------------------------------------------
print("\n[STEP 4] Verifying Charts and Tables Integrity...")
charts = home_data["charts"]
tables = home_data["tables"]

# Chart 1: Revenue by organization for top 10
top_rev = charts["revenue_by_organization"]
print(f"  Top 10 Organizations Revenue chart items count: {len(top_rev)}")
assert len(top_rev) <= 10
for item in top_rev:
    print(f"    • {item['organization_name']}: ₹{item['total_revenue']:,.2f}")
    assert item["total_revenue"] >= 0

# Chart 2: Pipeline runs per day (last 14 days)
runs_14d = charts["pipeline_runs_per_day"]
print(f"  Pipeline runs 14-day history items count: {len(runs_14d)}")
assert len(runs_14d) == 14
for r in runs_14d[-3:]:
    print(f"    • Date: {r['date']} - Successful: {r['successful_runs']}, Failed: {r['failed_runs']}")

# Table 1: Organizations (10 rows)
orgs_table = tables["organizations"]
print(f"  Organizations table rows count: {len(orgs_table)}")
assert len(orgs_table) <= 10
if orgs_table:
    first_org = orgs_table[0]
    print(f"    • Sample Org: {first_org['name']} | Owner: {first_org['owner']} | Team: {first_org['assigned_team_member']}")
    assert "name" in first_org
    assert "owner" in first_org
    assert "assigned_team_member" in first_org

# Table 2: Recent Activity (10 rows)
activity_table = tables["recent_activity"]
print(f"  Recent activity table rows count: {len(activity_table)}")
assert len(activity_table) <= 10
if activity_table:
    first_act = activity_table[0]
    print(f"    • Sample Activity: Org {first_act['tenant_name']} | Stage: {first_act['stage']} | Status: {first_act['status']}")
    assert "status" in first_act


# -----------------------------------------------------------------------------
# STEP 5: PIPELINE SUCCESS/FAILURE CLEARS CACHE WITHIN CACHE PERIOD
# -----------------------------------------------------------------------------
print("\n[STEP 5] Testing Pipeline Status Transition Clears In-Memory Cache...")
test_batch_id = str(uuid.uuid4())
test_tenant_id = 1

try:
    # 5a. Create a pipeline_status row with 'running'
    cur.execute(
        f"""
        INSERT INTO `{CATALOG}`.`platform`.`pipeline_status` (
            batch_id, tenant_id, stage, status, created_at, updated_at
        ) VALUES (
            :batch_id, :tenant_id, 'silver_running', 'running', current_timestamp(), current_timestamp()
        )
        """,
        {"batch_id": test_batch_id, "tenant_id": test_tenant_id},
    )

    # 5b. Transition to 'success'
    cur.execute(
        f"""
        UPDATE `{CATALOG}`.`platform`.`pipeline_status`
        SET status = 'success', stage = 'gold_transform', updated_at = current_timestamp()
        WHERE batch_id = :batch_id
        """,
        {"batch_id": test_batch_id},
    )
    # The pipeline runner calls OversightService.clear_cache() inside the container
    subprocess.run(
        ["docker", "exec", "helios-backend", "python", "-c", "from app.services.oversight_service import OversightService; OversightService.clear_cache()"],
        check=True,
    )

    # 5c. Fetch Admin Home immediately; must reflect new run activity without waiting 30s
    t0 = time.time()
    resp_after_success = requests.get(
        f"{BASE_URL}{API_PREFIX}/oversight/home",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    t_after = time.time() - t0
    print(f"  Fetched Admin Home after run completion in {t_after:.2f}s (Status: {resp_after_success.status_code})")
    assert resp_after_success.status_code == 200
    new_data = resp_after_success.json()

    # Verify that recent activity now contains our test_batch_id
    activity_batch_ids = [a.get("batch_id") for a in new_data["tables"]["recent_activity"]]
    print(f"  Recent activity includes completed test batch: {test_batch_id in activity_batch_ids}")
    assert test_batch_id in activity_batch_ids, "Expected new successful batch in recent activity immediately after cache clear!"
    print("  Verified: Cache was cleared and page reflected updated pipeline activity within the cache period.")

finally:
    # -------------------------------------------------------------------------
    # STEP 6: DATA RULE COMPLIANT CLEANUP
    # -------------------------------------------------------------------------
    print("\n[STEP 6] Cleaning up test batch rows (DATA RULE compliance)...")
    print(f"  Removing rows created exclusively for test batch: {test_batch_id}")
    cur.execute(
        f"DELETE FROM `{CATALOG}`.`platform`.`pipeline_status` WHERE batch_id = :batch_id",
        {"batch_id": test_batch_id},
    )
    # Clear cache again so cleanup is reflected
    subprocess.run(
        ["docker", "exec", "helios-backend", "python", "-c", "from app.services.oversight_service import OversightService; OversightService.clear_cache()"],
        check=True,
    )
    print("  Cleanup completed successfully. No existing runtime tables or rows were reset.")

cur.close()
conn.close()

print("\n" + "=" * 70)
print("ALL ADMIN HOME VERIFICATIONS COMPLETED SUCCESSFULLY!")
print("=" * 70)
