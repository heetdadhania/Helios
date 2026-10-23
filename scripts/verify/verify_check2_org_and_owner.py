import os
import sys
import time
import requests
from pathlib import Path
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend"))
load_dotenv(REPO_ROOT / ".env")

from app.core.config import settings
from app.db.base import get_databricks_connection

BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000/api/v1")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD")
TEST_ACCOUNT_PASSWORD = os.environ.get("TEST_ACCOUNT_PASSWORD")
CATALOG = getattr(settings, "DATABRICKS_CATALOG", "helios_catalog")

def get_token(email: str, password: str) -> str:
    res = requests.post(f"{BASE_URL}/auth/login", json={"email": email, "password": password})
    if res.status_code != 200:
        raise RuntimeError(f"Login failed for {email}: {res.status_code} {res.text}")
    return res.json()["access_token"]

def main():
    print("=" * 75)
    print("CHECK 2: CREATE ORG & OWNER, 2ND OWNER REFUSED, EDIT, RESET, REPLACE, TEAM MEMBER")
    print("=" * 75)

    admin_token = get_token("admin@helios.io", ADMIN_PASSWORD)
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    unique_ts = int(time.time())
    test_org_name = f"Check2 Test Org {unique_ts}"
    initial_owner_email = f"owner_init_{unique_ts}@helios-test.dev"
    initial_owner_name = f"Initial Owner {unique_ts}"
    initial_owner_phone = "+91 98765 43210"

    created_tenant_id = None
    created_user_ids = []

    try:
        # Step 1: Create Organization with its Owner
        print("\n--- STEP 1: Create Organization with Owner ---")
        create_payload = {
            "business_name": test_org_name,
            "industry": "Retail",
            "contact_person_name": initial_owner_name,
            "contact_email": initial_owner_email,
            "phone_number": initial_owner_phone,
            "owner_name": initial_owner_name,
            "owner_email": initial_owner_email,
            "owner_phone": initial_owner_phone,
            "address_line1": "100 MG Road",
            "city": "Bengaluru",
            "state": "Karnataka",
            "postal_code": "560001",
        }
        res_create = requests.post(f"{BASE_URL}/tenants", json=create_payload, headers=admin_headers)
        print(f"POST /tenants Status: {res_create.status_code}")
        assert res_create.status_code == 201, f"Failed to create tenant: {res_create.text}"
        tenant_data = res_create.json()
        created_tenant_id = tenant_data["tenant_id"]
        temp_pwd_init = tenant_data.get("temporary_password")
        print(f"Created Tenant ID: {created_tenant_id}, Temp Password returned: {bool(temp_pwd_init)}")

        # Fetch created owner user_id from database
        with get_databricks_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(f"SELECT user_id FROM `{CATALOG}`.`platform`.`users` WHERE lower(email) = :e", {"e": initial_owner_email.lower()})
                row = cur.fetchone()
                if row:
                    created_user_ids.append(row[0])
                    print(f"Created Initial Owner User ID: {row[0]}")

        # Step 2: Attempt to create a second owner on this organization -> 409 Conflict
        print("\n--- STEP 2: Second Owner Refusal (409 Conflict) ---")
        second_owner_payload = {
            "name": "Second Owner Attempt",
            "email": f"owner_second_{unique_ts}@helios-test.dev",
            "phone_number": "+91 98765 00000"
        }
        res_conflict = requests.post(f"{BASE_URL}/tenants/{created_tenant_id}/owner/replace", json=second_owner_payload, headers=admin_headers)
        print(f"Second owner creation Status: {res_conflict.status_code}, Detail: {res_conflict.json().get('detail')}")
        assert res_conflict.status_code == 409, f"Expected 409, got {res_conflict.status_code}"
        assert "already has an owner" in res_conflict.json().get("detail", "")
        print("[PASS] Second owner refused with 409 Conflict.")

        # Step 3: Edit Owner Details
        print("\n--- STEP 3: Edit Owner Details (PUT /tenants/{tenant_id}/owner) ---")
        edited_name = f"Edited Owner {unique_ts}"
        edited_phone = "+91 91234 56789"
        res_edit = requests.put(
            f"{BASE_URL}/tenants/{created_tenant_id}/owner",
            json={"name": edited_name, "email": initial_owner_email, "phone_number": edited_phone},
            headers=admin_headers,
        )
        print(f"PUT /tenants/{created_tenant_id}/owner Status: {res_edit.status_code}")
        assert res_edit.status_code == 200, f"Edit owner failed: {res_edit.text}"
        data_edit = res_edit.json()
        assert data_edit["name"] == edited_name
        assert data_edit["phone_number"] == edited_phone
        print("[PASS] Owner details successfully edited.")

        # Step 4: Reset Owner Password
        print("\n--- STEP 4: Reset Owner Password ---")
        res_reset = requests.post(f"{BASE_URL}/tenants/{created_tenant_id}/owner/reset-password", headers=admin_headers)
        print(f"POST /tenants/{created_tenant_id}/owner/reset-password Status: {res_reset.status_code}")
        assert res_reset.status_code == 200, f"Reset password failed: {res_reset.text}"
        temp_pwd_reset = res_reset.json().get("temporary_password")
        assert temp_pwd_reset, "Temporary password not returned"
        print("[PASS] Owner password reset successfully, temporary password returned once.")

        # Step 5: Replace Owner (Deactivate first, then Replace)
        print("\n--- STEP 5: Deactivate and Replace Owner ---")
        res_deact = requests.patch(f"{BASE_URL}/tenants/{created_tenant_id}/owner/active", json={"is_active": False}, headers=admin_headers)
        assert res_deact.status_code == 200, f"Deactivate owner failed: {res_deact.text}"
        print(f"Deactivate Status: {res_deact.status_code}, Warning: {res_deact.json().get('warning')}")

        replacement_email = f"owner_replaced_{unique_ts}@helios-test.dev"
        replacement_name = f"Replacement Owner {unique_ts}"
        res_replace = requests.post(
            f"{BASE_URL}/tenants/{created_tenant_id}/owner/replace",
            json={"name": replacement_name, "email": replacement_email, "phone_number": "+91 99999 88888"},
            headers=admin_headers,
        )
        print(f"POST /tenants/{created_tenant_id}/owner/replace Status: {res_replace.status_code}")
        assert res_replace.status_code == 201, f"Replace owner failed: {res_replace.text}"
        data_replace = res_replace.json()
        replacement_uid = data_replace["user_id"]
        created_user_ids.append(replacement_uid)
        print(f"[PASS] Replaced owner with new user_id={replacement_uid}, email={replacement_email}")

        # Step 6: Create Team Member with Assignments
        print("\n--- STEP 6: Create Team Member with Assignments ---")
        tm_email = f"tm_check2_{unique_ts}@helios-test.dev"
        tm_name = f"Test TM {unique_ts}"
        tm_payload = {
            "name": tm_name,
            "email": tm_email,
            "role": "team_member",
            "phone_number": "+91 98765 11111",
            "tenant_ids": [int(created_tenant_id)],
        }
        res_tm = requests.post(f"{BASE_URL}/team-members", json=tm_payload, headers=admin_headers)
        print(f"POST /team-members Status: {res_tm.status_code}")
        assert res_tm.status_code == 201, f"Create team member failed: {res_tm.text}"
        tm_data = res_tm.json()
        tm_user_id = tm_data["user_id"]
        created_user_ids.append(tm_user_id)
        assert int(created_tenant_id) in tm_data.get("tenant_ids", [])
        print(f"[PASS] Team member created with user_id={tm_user_id}, assigned to tenant {created_tenant_id}.")

    finally:
        # Step 7: Clean up ONLY what we created
        print("\n--- STEP 7: CLEANUP OF CREATED TEST DATA ONLY ---")
        with get_databricks_connection() as conn:
            with conn.cursor() as cur:
                if created_tenant_id:
                    cur.execute(f"DELETE FROM `{CATALOG}`.`platform`.`team_assignments` WHERE tenant_id = :t", {"t": created_tenant_id})
                    print(f"Cleaned up team_assignments for tenant {created_tenant_id}")
                for uid in created_user_ids:
                    cur.execute(f"DELETE FROM `{CATALOG}`.`platform`.`team_assignments` WHERE user_id = :u", {"u": uid})
                    cur.execute(f"DELETE FROM `{CATALOG}`.`platform`.`users` WHERE user_id = :u", {"u": uid})
                    print(f"Cleaned up user_id {uid}")
                if created_tenant_id:
                    cur.execute(f"DELETE FROM `{CATALOG}`.`platform`.`tenants` WHERE tenant_id = :t", {"t": created_tenant_id})
                    print(f"Cleaned up tenant_id {created_tenant_id}")

    print("\n" + "=" * 75)
    print("CHECK 2 COMPLETED SUCCESSFULLY AND CLEANED UP!")
    print("=" * 75)

if __name__ == "__main__":
    main()
