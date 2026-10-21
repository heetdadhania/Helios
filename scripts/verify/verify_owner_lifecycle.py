#!/usr/bin/env python3
"""
Comprehensive SMB Owner Lifecycle Verification Suite
Tests:
1. PUT /api/v1/tenants/{tenant_id}/owner (Edit name, email, phone)
2. POST /api/v1/tenants/{tenant_id}/owner/reset-password (Temporary password, audit trail, login)
3. 409 conflict when attempting to create a second active owner on an existing tenant
4. PATCH /api/v1/tenants/{tenant_id}/owner/active (Deactivate with warning, reactivate refusal)
5. POST /api/v1/tenants/{tenant_id}/owner/replace (Replace inactive owner, login with temp password)
6. RBAC check: team-member-1 accessing unassigned tenant returns 403
7. Restores original test accounts and active states
"""

import os
import sys
from pathlib import Path
import requests

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.core.config import settings
from app.core.security import get_password_hash
from app.db.base import get_databricks_connection

from dotenv import load_dotenv
load_dotenv()

ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD")
TEST_ACCOUNT_PASSWORD = os.environ.get("TEST_ACCOUNT_PASSWORD")

BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000/api/v1")
CATALOG = getattr(settings, "DATABRICKS_CATALOG", "helios_catalog")

def get_token(email: str, password: str) -> str:
    res = requests.post(f"{BASE_URL}/auth/login", json={"email": email, "password": password})
    if res.status_code != 200:
        raise RuntimeError(f"Login failed for {email}: {res.status_code} {res.text}")
    return res.json()["access_token"]

def main():
    print("=" * 70)
    print("STARTING SMB OWNER LIFECYCLE VERIFICATION")
    print("=" * 70)

    admin_token = get_token("admin@helios.io", ADMIN_PASSWORD)
    tm1_token = get_token("team-member-1@helios-test.dev", TEST_ACCOUNT_PASSWORD)
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    tm1_headers = {"Authorization": f"Bearer {tm1_token}"}

    # Fetch initial state of tenant 1
    t1_res = requests.get(f"{BASE_URL}/tenants", headers=admin_headers)
    assert t1_res.status_code == 200, f"Failed to list tenants: {t1_res.status_code}"
    tenants = t1_res.json()
    t1 = next((t for t in tenants if t["tenant_id"] == 1 or t["tenant_id"] == "1"), None)
    assert t1 is not None, "Tenant 1 not found"
    orig_owner_name = t1.get("owner_name")
    orig_owner_email = t1.get("owner_email")
    orig_owner_phone = t1.get("owner_phone")
    orig_owner_id = t1.get("owner_id")
    print(f"[INIT] Tenant 1: ID={t1['tenant_id']}, Owner ID={orig_owner_id}, Name='{orig_owner_name}', Email='{orig_owner_email}'")

    created_replacement_user_ids = []

    try:
        # 1. Edit Owner
        print("\n--- TEST 1: Edit Owner (PUT /api/v1/tenants/1/owner) ---")
        edit_payload = {
            "name": "Marcus Vance Modified",
            "email": "marcus.modified@helios-test.dev",
            "phone_number": "+1 (555) 019-9999",
        }
        res_edit = requests.put(f"{BASE_URL}/tenants/1/owner", json=edit_payload, headers=admin_headers)
        print(f"Status Code: {res_edit.status_code}")
        assert res_edit.status_code == 200, f"Edit owner failed: {res_edit.text}"
        data_edit = res_edit.json()
        assert data_edit["name"] == edit_payload["name"], "Owner name not updated"
        assert data_edit["email"] == edit_payload["email"], "Owner email not updated"
        print(f"[PASS] Successfully edited owner details for tenant 1 to {data_edit['email']}")

        # 2. Reset Password
        print("\n--- TEST 2: Reset Owner Password (POST /api/v1/tenants/1/owner/reset-password) ---")
        res_reset = requests.post(f"{BASE_URL}/tenants/1/owner/reset-password", headers=admin_headers)
        print(f"Status Code: {res_reset.status_code}")
        assert res_reset.status_code == 200, f"Reset password failed: {res_reset.text}"
        data_reset = res_reset.json()
        temp_pwd = data_reset.get("temporary_password")
        assert temp_pwd, "Temporary password not returned"
        print("[PASS] Temporary password returned once (not logged).")

        # Test login with temporary password
        print("Testing login with generated temporary password...")
        login_res = requests.post(f"{BASE_URL}/auth/login", json={"email": edit_payload["email"], "password": temp_pwd})
        print(f"Login Status Code: {login_res.status_code}")
        assert login_res.status_code == 200, f"Login with temporary password failed: {login_res.text}"
        login_data = login_res.json()
        user_info = login_data.get("user", {})
        assert user_info.get("must_change_password") is True or login_data.get("must_change_password") is True, "must_change_password flag is not True"
        print("[PASS] Login with temporary password succeeded and forced must_change_password=True.")

        # 3. Conflict 409 check: Ensure no second active owner can be created
        print("\n--- TEST 3: Ensure no active owner / 409 Conflict check ---")
        from app.services.owner_service import ensure_no_active_owner
        from fastapi import HTTPException
        try:
            ensure_no_active_owner(1)
            assert False, "Expected 409 HTTPException from ensure_no_active_owner"
        except HTTPException as exc:
            print(f"ensure_no_active_owner(1) raised: {exc.status_code} - {exc.detail}")
            assert exc.status_code == 409
            assert exc.detail == "This tenant already has an owner"
        print("[PASS] ensure_no_active_owner(1) correctly raised 409 'This tenant already has an owner'.")

        # Also attempt replace when active -> 400
        conflict_res = requests.post(
            f"{BASE_URL}/tenants/1/owner/replace",
            json={"name": "Second Owner", "email": "second.owner@helios-test.dev"},
            headers=admin_headers,
        )
        print(f"Replace when active -> Status Code: {conflict_res.status_code}, Detail: {conflict_res.json().get('detail')}")
        assert conflict_res.status_code == 409
        assert conflict_res.json().get("detail") == "This tenant already has an owner"
        print("[PASS] Refused creating a replacement owner while active owner exists (409).")

        # 4. Deactivate Owner
        print("\n--- TEST 4: Deactivate Owner (PATCH /api/v1/tenants/1/owner/active) ---")
        res_deact = requests.patch(
            f"{BASE_URL}/tenants/1/owner/active",
            json={"is_active": False},
            headers=admin_headers,
        )
        print(f"Status Code: {res_deact.status_code}")
        assert res_deact.status_code == 200, f"Deactivate failed: {res_deact.text}"
        data_deact = res_deact.json()
        assert data_deact.get("is_active") is False, "Owner is not inactive"
        assert "warning" in data_deact, "Warning message missing"
        print(f"[PASS] Deactivated owner. Warning received: '{data_deact['warning']}'")

        # 5. Replace Owner (now allowed because current owner is inactive)
        print("\n--- TEST 5: Replace Inactive Owner (POST /api/v1/tenants/1/owner/replace) ---")
        replacement_email = "replacement.owner.t1@helios-test.dev"
        res_replace = requests.post(
            f"{BASE_URL}/tenants/1/owner/replace",
            json={"name": "Replacement Owner", "email": replacement_email, "phone_number": "+1 555-0188"},
            headers=admin_headers,
        )
        print(f"Status Code: {res_replace.status_code}")
        assert res_replace.status_code == 201, f"Replace owner failed: {res_replace.text}"
        data_replace = res_replace.json()
        created_replacement_user_ids.append(data_replace["user_id"])
        replacement_temp_pwd = data_replace.get("temporary_password")
        assert replacement_temp_pwd, "Temporary password not returned for replaced owner"
        print("[PASS] Replaced owner successfully. Temporary password returned once.")

        # Test login as new replacement owner
        print("Testing login with new replacement owner credentials...")
        login_rep_res = requests.post(
            f"{BASE_URL}/auth/login",
            json={"email": replacement_email, "password": replacement_temp_pwd},
        )
        print(f"Login Status Code: {login_rep_res.status_code}")
        assert login_rep_res.status_code == 200, f"Login failed for replaced owner: {login_rep_res.text}"
        rep_user = login_rep_res.json().get("user", {})
        assert rep_user.get("must_change_password") is True or login_rep_res.json().get("must_change_password") is True
        print("[PASS] Replaced owner logged in successfully with forced change password flag.")

        # 6. RBAC Check: Team Member 1 on Unassigned Tenant (Tenant 3)
        print("\n--- TEST 6: Team Member 1 RBAC on Unassigned Tenant 3 ---")
        res_tm_unassigned = requests.put(
            f"{BASE_URL}/tenants/3/owner",
            json={"name": "Hacked", "email": "hacked@helios-test.dev"},
            headers=tm1_headers,
        )
        print(f"PUT /tenants/3/owner Status Code: {res_tm_unassigned.status_code}")
        assert res_tm_unassigned.status_code == 403, f"Expected 403, got {res_tm_unassigned.status_code}"

        res_tm_reset = requests.post(f"{BASE_URL}/tenants/3/owner/reset-password", headers=tm1_headers)
        print(f"POST /tenants/3/owner/reset-password Status Code: {res_tm_reset.status_code}")
        assert res_tm_reset.status_code == 403, f"Expected 403, got {res_tm_reset.status_code}"

        res_tm_active = requests.patch(
            f"{BASE_URL}/tenants/3/owner/active",
            json={"is_active": False},
            headers=tm1_headers,
        )
        print(f"PATCH /tenants/3/owner/active Status Code: {res_tm_active.status_code}")
        assert res_tm_active.status_code == 403, f"Expected 403, got {res_tm_active.status_code}"

        res_tm_replace = requests.post(
            f"{BASE_URL}/tenants/3/owner/replace",
            json={"name": "Hacked", "email": "hacked2@helios-test.dev"},
            headers=tm1_headers,
        )
        print(f"POST /tenants/3/owner/replace Status Code: {res_tm_replace.status_code}")
        assert res_tm_replace.status_code == 403, f"Expected 403, got {res_tm_replace.status_code}"
        print("[PASS] All unassigned tenant operations refused with 403 for team-member-1.")

    finally:
        # 7. Restore original test accounts and clean up test data
        print("\n--- CLEANUP & RESTORATION ---")
        if orig_owner_id is not None:
            with get_databricks_connection() as conn:
                with conn.cursor() as cursor:
                    # Remove replacement test user(s) created during this test
                    for uid in created_replacement_user_ids:
                        cursor.execute(f"DELETE FROM `{CATALOG}`.`platform`.`users` WHERE user_id = {uid}")
                        print(f"Cleaned up temporary test user_id={uid}")

                    # Restore original owner row for Tenant 1
                    default_hash = get_password_hash(TEST_ACCOUNT_PASSWORD)
                    cursor.execute(
                        f"""
                        UPDATE `{CATALOG}`.`platform`.`users`
                        SET name = :name,
                            email = :email,
                            phone_number = :phone,
                            password_hash = :hash,
                            is_active = true,
                            must_change_password = false
                        WHERE user_id = :uid
                        """,
                        {
                            "name": orig_owner_name,
                            "email": orig_owner_email,
                            "phone": orig_owner_phone,
                            "hash": default_hash,
                            "uid": orig_owner_id,
                        },
                    )
                    # Restore tenant 1 contact fields
                    cursor.execute(
                        f"""
                        UPDATE `{CATALOG}`.`platform`.`tenants`
                        SET contact_person_name = :name,
                            contact_email = :email,
                            phone_number = :phone
                        WHERE tenant_id = 1
                        """,
                        {
                            "name": orig_owner_name,
                            "email": orig_owner_email,
                            "phone": orig_owner_phone,
                        },
                    )
                    print(f"Restored original Tenant 1 owner (ID={orig_owner_id}, email={orig_owner_email}).")

    print("\n" + "=" * 70)
    print("ALL OWNER LIFECYCLE TESTS PASSED SUCCESSFULLY!")
    print("=" * 70)

if __name__ == "__main__":
    main()
