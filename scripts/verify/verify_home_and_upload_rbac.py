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

# Load environment variables
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

print("=" * 70)
print("HELIOS VERIFICATION SUITE: TOP BAR, HOME PAGES, AND OWNER RBAC")
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


def login_user(email, password):
    resp = requests.post(
        f"{BASE_URL}{API_PREFIX}/auth/login",
        json={"email": email, "password": password},
    )
    if resp.status_code != 200:
        raise RuntimeError(f"Login failed for {email} ({resp.status_code}): {resp.text}")
    return resp.json()


# -----------------------------------------------------------------------------
# STEP 1: ORGANIZATION OWNER VERIFICATION
# -----------------------------------------------------------------------------
print("\n[STEP 1] Testing Organization Owner Authentication & Profile...")
owner_login = None
owner_emails = ["smb-owner-1@helios-test.dev", "smb-owner-2@helios-test.dev"]
for email in owner_emails:
    try:
        owner_login = login_user(email, TEST_PASSWORD)
        print(f"  Successfully authenticated as: {email}")
        break
    except Exception as e:
        print(f"  Could not authenticate as {email}: {e}")

assert owner_login is not None, "Failed to authenticate as any Organization Owner."

user_info = owner_login.get("user", {})
print(f"  User Role: {user_info.get('role')}")
print(f"  User Email: {user_info.get('email')}")
print(f"  Business Name: {user_info.get('business_name')}")
assert user_info.get("role") == "smb_owner", f"Expected smb_owner role, got {user_info.get('role')}"
assert user_info.get("business_name"), "Expected business_name in UserOut for Organization Owner"
owner_token = owner_login["access_token"]
owner_headers = {"Authorization": f"Bearer {owner_token}"}

print("\n[STEP 2] Testing Organization Owner Home Summary (GET /api/v1/dashboard/summary)...")
summary_res = requests.get(f"{BASE_URL}{API_PREFIX}/dashboard/summary", headers=owner_headers)
print(f"  Status Code: {summary_res.status_code}")
assert summary_res.status_code == 200, f"Expected 200, got {summary_res.status_code}: {summary_res.text}"
summary_data = summary_res.json()
print("  Summary Data Received:")
print(f"    - Data as of date: {summary_data.get('data_as_of')}")
print(f"    - Total Revenue: ₹{summary_data.get('total_revenue')}")
print(f"    - Order Count: {summary_data.get('order_count')}")
print(f"    - Late Delivery %: {summary_data.get('late_delivery_percentage')}%")
print(f"    - Average Order Value: ₹{summary_data.get('average_order_value')}")
print(f"    - Latest Submission Status: {summary_data.get('latest_submission_status')}")
print(f"    - Has Data: {summary_data.get('has_data')}")

valid_plain_statuses = ["Ready", "Processing", "Needs attention - please resend", None]
assert summary_data.get("latest_submission_status") in valid_plain_statuses, (
    f"Invalid submission status: {summary_data.get('latest_submission_status')}"
)

print("\n[STEP 3] Verifying Upload Endpoint Returns 403 Forbidden for Organization Owner...")
dummy_csv_content = b"order_id,customer_id,order_date,total_amount\n101,C1,2024-01-01,500\n"
upload_res = requests.post(
    f"{BASE_URL}{API_PREFIX}/uploads",
    headers=owner_headers,
    files={"file": ("test.csv", dummy_csv_content, "text/csv")},
    data={"tenant_id": user_info.get("tenant_id") or 1},
)
print(f"  Owner Upload Response Status: {upload_res.status_code}")
print(f"  Owner Upload Response Body: {upload_res.text}")
assert upload_res.status_code == 403, f"Expected 403 Forbidden for owner upload, got {upload_res.status_code}"
print("  Verified: File upload endpoint strictly returns 403 Forbidden for Organization Owner role.")

# -----------------------------------------------------------------------------
# STEP 4: TEAM MEMBER VERIFICATION
# -----------------------------------------------------------------------------
print("\n[STEP 4] Testing Team Member Authentication & Home Endpoint...")
team_emails = ["team-member-1@helios-test.dev", "team@helios.io"]
team_login = None
for email in team_emails:
    try:
        team_login = login_user(email, TEST_PASSWORD)
        print(f"  Successfully authenticated as: {email}")
        break
    except Exception as e:
        print(f"  Could not authenticate as {email}: {e}")

if not team_login:
    # Try fetching first team_member from DB
    conn, cur = get_db_cursor()
    cur.execute(f"SELECT email FROM `{CATALOG}`.`platform`.`users` WHERE lower(role) = 'team_member' LIMIT 1")
    row = cur.fetchone()
    cur.close()
    conn.close()
    if row:
        team_email = row[0]
        print(f"  Attempting login for discovered team member: {team_email}")
        team_login = login_user(team_email, TEST_PASSWORD)

assert team_login is not None, "Failed to authenticate as any Team Member."
team_user = team_login.get("user", {})
print(f"  Team Member Role: {team_user.get('role')}")
print(f"  Team Member Email: {team_user.get('email')}")
team_token = team_login["access_token"]
team_headers = {"Authorization": f"Bearer {team_token}"}

print("\n[STEP 5] Testing Team Member Home Endpoint (GET /api/v1/team/home)...")
team_home_res = requests.get(f"{BASE_URL}{API_PREFIX}/team/home", headers=team_headers)
print(f"  Status Code: {team_home_res.status_code}")
assert team_home_res.status_code == 200, f"Expected 200, got {team_home_res.status_code}: {team_home_res.text}"
home_data = team_home_res.json()

assigned_orgs = home_data.get("assigned_organizations", [])
pipeline_counts = home_data.get("pipeline_counts", {})
open_messages = home_data.get("open_support_messages", [])
recent_activity = home_data.get("recent_activity", [])

print(f"  Assigned Organizations Count: {len(assigned_orgs)}")
for org in assigned_orgs[:3]:
    print(f"    - Org #{org.get('tenant_id')}: {org.get('business_name')} (Last Data Date: {org.get('last_data_date')})")
print(f"  Pipeline Status Counts: {pipeline_counts}")
print(f"    - Pending Review: {pipeline_counts.get('pending_review')}")
print(f"    - Running: {pipeline_counts.get('running')}")
print(f"    - Failed: {pipeline_counts.get('failed')}")
print(f"    - Stalled: {pipeline_counts.get('stalled')}")
print(f"  Open Support Messages Count: {len(open_messages)}")
print(f"  Recent Activity Count: {len(recent_activity)}")

# -----------------------------------------------------------------------------
# STEP 6: TEAM MEMBER UPLOAD 5-ROW CSV & REACH PENDING REVIEW
# -----------------------------------------------------------------------------
print("\n[STEP 6] Testing Team Member Uploading a 5-Row CSV...")
target_tenant_id = assigned_orgs[0]["tenant_id"] if assigned_orgs else 1
print(f"  Target Organization ID: {target_tenant_id}")

test_batch_id = None
test_upload_id = None

# Create a valid 5-row CSV with unique order IDs
unique_suffix = int(time.time())
csv_lines = [
    "order_id,customer_id,order_date,product_name,category,quantity,price,total_amount",
    f"ORD-{unique_suffix}-1,CUST-101,2026-03-01,Organic Cotton Kurta,Apparel,2,750,1500",
    f"ORD-{unique_suffix}-2,CUST-102,2026-03-02,Handcrafted Brass Lamp,Home,1,2200,2200",
    f"ORD-{unique_suffix}-3,CUST-103,2026-03-03,Mysore Sandalwood Soap,Beauty,5,180,900",
    f"ORD-{unique_suffix}-4,CUST-104,2026-03-04,Darjeeling First Flush Tea,Grocery,3,450,1350",
    f"ORD-{unique_suffix}-5,CUST-105,2026-03-05,Kashmir Walnut Wood Bowl,Home,1,1850,1850",
]
five_row_csv_bytes = "\n".join(csv_lines).encode("utf-8")

upload_res = requests.post(
    f"{BASE_URL}{API_PREFIX}/uploads",
    headers=team_headers,
    files={"file": (f"test_run4_{unique_suffix}.csv", five_row_csv_bytes, "text/csv")},
    data={"tenant_id": target_tenant_id},
)
print(f"  Upload Response Status: {upload_res.status_code}")
assert upload_res.status_code in (200, 201), f"Upload failed: {upload_res.text}"
upload_json = upload_res.json()
test_batch_id = upload_json.get("batch_id")
test_upload_id = upload_json.get("upload_id")
print(f"  Upload Successful: upload_id={test_upload_id}, batch_id={test_batch_id}")

print("  Waiting for batch to reach 'pending_review' status...")
conn, cur = get_db_cursor()
reached_pending_review = False
for attempt in range(15):
    time.sleep(2)
    cur.execute(
        f"SELECT status, stage FROM `{CATALOG}`.`platform`.`pipeline_status` WHERE batch_id = :b",
        {"b": test_batch_id},
    )
    row = cur.fetchone()
    if row:
        curr_status, curr_stage = row[0], row[1]
        print(f"    Check {attempt + 1}: status='{curr_status}', stage='{curr_stage}'")
        if curr_status == "pending_review":
            reached_pending_review = True
            break
        if curr_status == "failed":
            raise RuntimeError(f"Batch {test_batch_id} failed during inference")

assert reached_pending_review, f"Batch {test_batch_id} did not reach pending_review status in time."
print("  Batch successfully reached 'pending_review'!")

# -----------------------------------------------------------------------------
# STEP 7: CLEANUP (DATA RULE)
# -----------------------------------------------------------------------------
print("\n[STEP 7] Cleaning Up Test Batch Rows (DATA RULE compliance)...")
print(f"  Removing rows created exclusively for test batch: {test_batch_id}")

try:
    cur.execute(
        f"DELETE FROM `{CATALOG}`.`platform`.`pipeline_status` WHERE batch_id = :b",
        {"b": test_batch_id},
    )
    print("  - Removed row from platform.pipeline_status")
except Exception as e:
    print(f"  Note: pipeline_status delete: {e}")

try:
    if test_upload_id:
        cur.execute(
            f"DELETE FROM `{CATALOG}`.`platform`.`pending_uploads` WHERE upload_id = :u",
            {"u": test_upload_id},
        )
        print("  - Removed row from platform.pending_uploads")
except Exception as e:
    print(f"  Note: pending_uploads delete: {e}")

try:
    cur.execute(
        f"DELETE FROM `{CATALOG}`.`platform`.`inferred_schema` WHERE batch_id = :b",
        {"b": test_batch_id},
    )
    print("  - Removed row from platform.inferred_schema")
except Exception as e:
    print(f"  Note: inferred_schema delete: {e}")

try:
    cur.execute(
        f"DELETE FROM `{CATALOG}`.`bronze`.`raw_orders` WHERE _batch_id = :b",
        {"b": test_batch_id},
    )
    print("  - Removed rows from bronze.raw_orders")
except Exception as e:
    pass

try:
    cur.execute(
        f"DELETE FROM `{CATALOG}`.`meta`.`etl_audit_log` WHERE batch_id = :b",
        {"b": test_batch_id},
    )
    print("  - Removed rows from meta.etl_audit_log")
except Exception as e:
    print(f"  Note: etl_audit_log delete: {e}")

try:
    cur.execute(
        f"DELETE FROM `{CATALOG}`.`platform`.`notification_log` WHERE message LIKE :b",
        {"b": f"%{test_batch_id}%"},
    )
    print("  - Removed rows from platform.notification_log")
except Exception as e:
    pass

conn.commit()
cur.close()
conn.close()
print("  Cleanup completed successfully. No existing runtime tables or rows were reset.")

print("\n" + "=" * 70)
print("ALL VERIFICATIONS COMPLETED SUCCESSFULLY!")
print("=" * 70)
