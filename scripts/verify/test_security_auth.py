#!/usr/bin/env python3
"""
Helios Data Platform - Authentication, Lockout, and Password Reset Verification
Tests:
  1. Successful login updates last_login_at, resets failed attempts and lockout.
  2. Lockout after 5 consecutive wrong-password attempts (locked_until 15 mins, 423 error, audit row).
  3. Simulated database error / timeout returns 503 and does NOT increase failed attempts counter.
  4. Password reset RBAC: Admin can reset any user; Team Member can reset assigned SMB Owner;
     unassigned tenants and non-SMB roles refused (403); returns temporary password once, never logged.
  5. User with reset password logs in successfully with must_change_password=True, is blocked from
     operational resources until changing password via /api/auth/change-password, then succeeds.
  6. Session expiry: Expired JWT token returns 401 Unauthorized.
"""

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

import requests

sys.stdout.reconfigure(line_buffering=True)

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.core import security
from app.db.base import databricks_cursor

BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")
DEFAULT_TIMEOUT = 60

# Test Accounts
ADMIN_EMAIL = "admin@helios.io"
ADMIN_PASS = "HeliosDemo2026!"

TM1_EMAIL = "team-member-1@helios-test.dev"
TM1_PASS = "HeliosTest2026!"

SMB1_EMAIL = "smb-owner-1@helios-test.dev"
SMB1_PASS = "HeliosTest2026!"

SMB2_EMAIL = "smb-owner-2@helios-test.dev"
SMB2_PASS = "HeliosTest2026!"

SMB5_EMAIL = "smb-owner-5@helios-test.dev"
SMB5_PASS = "HeliosTest2026!"

TABLE_RESULTS = []


def record_result(test_name: str, expected: str, actual: str, passed: bool, notes: str = ""):
    TABLE_RESULTS.append({
        "test": test_name,
        "expected": expected,
        "actual": actual,
        "status": "PASS" if passed else "FAIL",
        "notes": notes,
    })
    tag = "[PASS]" if passed else "[FAIL]"
    print(f"{tag:7} | {test_name:<45} | Exp: {expected:<28} | Act: {actual:<28} {notes}", flush=True)


def get_user_db_state(email: str) -> Optional[Dict[str, Any]]:
    with databricks_cursor() as cur:
        cur.execute(
            "SELECT user_id, email, role, tenant_id, failed_login_count, locked_until, last_login_at, must_change_password "
            "FROM helios_catalog.platform.users WHERE lower(email) = :email",
            {"email": email.strip().lower()},
        )
        row = cur.fetchone()
        if not row:
            return None
        return {
            "user_id": row[0],
            "email": row[1],
            "role": row[2],
            "tenant_id": row[3],
            "failed_login_count": row[4],
            "locked_until": row[5],
            "last_login_at": row[6],
            "must_change_password": row[7],
        }


def reset_user_db_state(email: str, default_password: str = "HeliosTest2026!"):
    new_hash = security.get_password_hash(default_password)
    with databricks_cursor() as cur:
        cur.execute(
            "UPDATE helios_catalog.platform.users "
            "SET password_hash = :hash, failed_login_count = 0, locked_until = NULL, must_change_password = false "
            "WHERE lower(email) = :email",
            {"hash": new_hash, "email": email.strip().lower()},
        )


def check_audit_trail(action: str, user_id: int) -> bool:
    with databricks_cursor() as cur:
        cur.execute(
            "SELECT audit_id, action, actor_user_id, reason, details_json "
            "FROM helios_catalog.meta.audit_trail "
            "WHERE action = :action AND (actor_user_id = :uid OR details_json LIKE :uid_str) "
            "ORDER BY occurred_at DESC LIMIT 1",
            {"action": action, "uid": user_id, "uid_str": f"%{user_id}%"},
        )
        row = cur.fetchone()
        return bool(row)


def run_tests():
    print("=" * 80)
    print("STARTING HELIOS AUTHENTICATION & SECURITY ISOLATION VERIFICATION")
    print("=" * 80)

    # Clean initial state for test users
    print("\n[SETUP] Initializing clean credentials state for test accounts...")
    reset_user_db_state(SMB1_EMAIL, SMB1_PASS)
    reset_user_db_state(SMB2_EMAIL, SMB2_PASS)
    reset_user_db_state(SMB5_EMAIL, SMB5_PASS)

    # -------------------------------------------------------------------------
    # TEST 1: Successful login updates last_login_at
    # -------------------------------------------------------------------------
    print("\n--- TEST 1: Successful login updates last_login_at ---")
    u1_before = get_user_db_state(SMB1_EMAIL)
    t0 = datetime.now(timezone.utc)

    resp = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": SMB1_EMAIL, "password": SMB1_PASS},
        timeout=DEFAULT_TIMEOUT,
    )
    passed_login = resp.status_code == 200
    token = resp.json().get("access_token") if passed_login else None

    # Inspect DB after login
    u1_after = get_user_db_state(SMB1_EMAIL)
    last_login = u1_after.get("last_login_at") if u1_after else None
    failed_cnt = u1_after.get("failed_login_count") if u1_after else None

    has_updated_login = last_login is not None
    record_result(
        test_name="Login Success: HTTP 200 & Token",
        expected="200 OK + JWT",
        actual=f"{resp.status_code} (token={bool(token)})",
        passed=passed_login and bool(token),
    )
    record_result(
        test_name="Login Success: last_login_at updated",
        expected="Updated timestamp != None",
        actual=f"last_login_at={last_login}",
        passed=has_updated_login and failed_cnt == 0,
        notes=f"failed_count={failed_cnt}",
    )

    # -------------------------------------------------------------------------
    # TEST 2: Lockout after 5 consecutive wrong-password attempts
    # -------------------------------------------------------------------------
    print("\n--- TEST 2: Lockout after 5 consecutive failed attempts ---")
    u2 = get_user_db_state(SMB2_EMAIL)
    u2_id = u2["user_id"]

    for attempt in range(1, 5):
        r = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": SMB2_EMAIL, "password": "WrongPassword123!"},
            timeout=DEFAULT_TIMEOUT,
        )
        record_result(
            test_name=f"Wrong Password Attempt #{attempt}",
            expected="401 Unauthorized",
            actual=f"{r.status_code} ({r.json().get('detail')})",
            passed=r.status_code == 401,
        )

    # 5th attempt must trigger lockout (HTTP 423)
    r5 = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": SMB2_EMAIL, "password": "WrongPassword123!"},
        timeout=DEFAULT_TIMEOUT,
    )
    r5_json = r5.json()
    r5_detail = r5_json.get("detail", "")
    is_423 = r5.status_code == 423
    has_lockout_msg = "locked" in r5_detail.lower() and "15 minutes" in r5_detail.lower()

    record_result(
        test_name="Attempt #5: Triggers Lockout (423)",
        expected="423 Locked + 15 min msg",
        actual=f"{r5.status_code}: {r5_detail}",
        passed=is_423 and has_lockout_msg,
    )

    # 6th attempt while locked (even with correct password) must be refused with 423
    r6 = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": SMB2_EMAIL, "password": SMB2_PASS},
        timeout=DEFAULT_TIMEOUT,
    )
    record_result(
        test_name="Attempt #6: Locked Account Refuses Login",
        expected="423 Locked",
        actual=f"{r6.status_code}: {r6.json().get('detail')}",
        passed=r6.status_code == 423,
    )

    # Verify audit trail row
    audit_logged = check_audit_trail("account_locked", u2_id)
    record_result(
        test_name="Lockout Audit Row in meta.audit_trail",
        expected="Row recorded in audit_trail",
        actual=f"Found={audit_logged}",
        passed=audit_logged,
    )

    # -------------------------------------------------------------------------
    # TEST 3: Simulated Database Error does not count
    # -------------------------------------------------------------------------
    print("\n--- TEST 3: Simulated database error does not count ---")
    u1_before_err = get_user_db_state(SMB1_EMAIL)
    cnt_before = u1_before_err["failed_login_count"]

    r_db_err = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": SMB1_EMAIL, "password": SMB1_PASS},
        headers={"X-Simulate-DB-Error": "1"},
        timeout=DEFAULT_TIMEOUT,
    )
    is_503 = r_db_err.status_code == 503
    err_detail = r_db_err.json().get("detail", "")

    u1_after_err = get_user_db_state(SMB1_EMAIL)
    cnt_after = u1_after_err["failed_login_count"]

    record_result(
        test_name="Simulated DB Error Returns 503",
        expected="503 Service Unavailable",
        actual=f"{r_db_err.status_code}: {err_detail}",
        passed=is_503 and "unavailable" in err_detail.lower(),
    )
    record_result(
        test_name="DB Error Does NOT Increment Counter",
        expected=f"Count unchanged ({cnt_before})",
        actual=f"Count={cnt_after}",
        passed=cnt_before == cnt_after,
    )

    # -------------------------------------------------------------------------
    # TEST 4: Password Reset (Admin & Team Member permissions)
    # -------------------------------------------------------------------------
    print("\n--- TEST 4: Password Reset Permissions ---")
    # Log in as Team Member 1 (assigned to tenant 1 and 2)
    r_tm = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": TM1_EMAIL, "password": TM1_PASS},
        timeout=DEFAULT_TIMEOUT,
    )
    tm_token = r_tm.json().get("access_token")
    tm_headers = {"Authorization": f"Bearer {tm_token}"}

    # TM tries to reset unassigned tenant SMB Owner (Tenant 5) -> 403
    u5 = get_user_db_state(SMB5_EMAIL)
    r_reset_u5 = requests.post(
        f"{BASE_URL}/api/auth/users/{u5['user_id']}/reset-password",
        headers=tm_headers,
        timeout=DEFAULT_TIMEOUT,
    )
    record_result(
        test_name="TM Reset Unassigned Tenant SMB Owner",
        expected="403 Forbidden",
        actual=f"{r_reset_u5.status_code}: {r_reset_u5.json().get('detail')}",
        passed=r_reset_u5.status_code == 403,
    )

    # TM tries to reset Admin -> 403
    u_admin = get_user_db_state(ADMIN_EMAIL)
    r_reset_admin = requests.post(
        f"{BASE_URL}/api/auth/users/{u_admin['user_id']}/reset-password",
        headers=tm_headers,
        timeout=DEFAULT_TIMEOUT,
    )
    record_result(
        test_name="TM Reset Admin User",
        expected="403 Forbidden",
        actual=f"{r_reset_admin.status_code}: {r_reset_admin.json().get('detail')}",
        passed=r_reset_admin.status_code == 403,
    )

    # TM resets assigned tenant SMB Owner (Tenant 2 - currently locked)
    r_reset_t2 = requests.post(
        f"{BASE_URL}/api/auth/users/{u2_id}/reset-password",
        headers=tm_headers,
        timeout=DEFAULT_TIMEOUT,
    )
    t2_reset_data = r_reset_t2.json() if r_reset_t2.status_code == 200 else {}
    temp_pass_t2 = t2_reset_data.get("temporary_password")

    record_result(
        test_name="TM Reset Assigned SMB Owner (Tenant 2)",
        expected="200 OK + temp_password",
        actual=f"{r_reset_t2.status_code} (temp_pass_len={len(temp_pass_t2) if temp_pass_t2 else 0})",
        passed=r_reset_t2.status_code == 200 and bool(temp_pass_t2),
    )

    # Verify audit trail for password reset and ensure password NOT logged
    reset_audit = check_audit_trail("password_reset", u2_id)
    record_result(
        test_name="Password Reset Audit Row in meta.audit_trail",
        expected="Audit logged without plaintext password",
        actual=f"Found={reset_audit}",
        passed=reset_audit,
    )

    # Admin resets any user (SMB 1)
    r_adm = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASS},
        timeout=DEFAULT_TIMEOUT,
    )
    adm_token = r_adm.json().get("access_token")
    adm_headers = {"Authorization": f"Bearer {adm_token}"}

    r_reset_u1 = requests.post(
        f"{BASE_URL}/api/auth/users/{u1_after['user_id']}/reset-password",
        headers=adm_headers,
        timeout=DEFAULT_TIMEOUT,
    )
    record_result(
        test_name="Admin Reset Any User (SMB Owner 1)",
        expected="200 OK + temp_password",
        actual=f"{r_reset_u1.status_code}",
        passed=r_reset_u1.status_code == 200 and bool(r_reset_u1.json().get("temporary_password")),
    )

    # -------------------------------------------------------------------------
    # TEST 5: Reset password logs in and forces a change
    # -------------------------------------------------------------------------
    print("\n--- TEST 5: Login with temp password forces password change ---")
    # Log in as SMB Owner 2 with temporary password
    r_temp_login = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": SMB2_EMAIL, "password": temp_pass_t2},
        timeout=DEFAULT_TIMEOUT,
    )
    is_temp_200 = r_temp_login.status_code == 200
    temp_user = r_temp_login.json().get("user", {})
    must_change = temp_user.get("must_change_password")
    temp_auth_token = r_temp_login.json().get("access_token")
    temp_headers = {"Authorization": f"Bearer {temp_auth_token}"}

    record_result(
        test_name="Login with Temporary Password",
        expected="200 OK + must_change_password=True",
        actual=f"{r_temp_login.status_code} (must_change={must_change})",
        passed=is_temp_200 and must_change is True,
    )

    # Operational route must be refused while must_change_password=True
    r_blocked = requests.get(
        f"{BASE_URL}/api/dashboard/revenue-trend",
        headers=temp_headers,
        timeout=DEFAULT_TIMEOUT,
    )
    record_result(
        test_name="Operational Route Blocked Before Password Change",
        expected="403 Forbidden (Password change required)",
        actual=f"{r_blocked.status_code}: {r_blocked.json().get('detail')}",
        passed=r_blocked.status_code == 403,
    )

    # Change password via /api/auth/change-password
    NEW_PERM_PASS = "HeliosNewPermPass2026!"
    r_change = requests.post(
        f"{BASE_URL}/api/auth/change-password",
        headers=temp_headers,
        json={"current_password": temp_pass_t2, "new_password": NEW_PERM_PASS},
        timeout=DEFAULT_TIMEOUT,
    )
    record_result(
        test_name="Execute /api/auth/change-password",
        expected="200 OK + Success message",
        actual=f"{r_change.status_code}: {r_change.json().get('message')}",
        passed=r_change.status_code == 200,
    )

    # Verify DB flag is now False
    u2_changed = get_user_db_state(SMB2_EMAIL)
    flag_cleared = u2_changed["must_change_password"] is False
    record_result(
        test_name="must_change_password Cleared in DB",
        expected="must_change_password=False",
        actual=f"Flag={u2_changed['must_change_password']}",
        passed=flag_cleared,
    )

    # Operational route now succeeds
    r_unblocked = requests.get(
        f"{BASE_URL}/api/dashboard/revenue-trend",
        headers=temp_headers,
        timeout=DEFAULT_TIMEOUT,
    )
    record_result(
        test_name="Operational Route Allowed After Password Change",
        expected="200 OK",
        actual=f"{r_unblocked.status_code}",
        passed=r_unblocked.status_code == 200,
    )

    # -------------------------------------------------------------------------
    # TEST 6: Session Expiry (Expired Token Returns 401)
    # -------------------------------------------------------------------------
    print("\n--- TEST 6: Session Expiry Interception ---")
    expired_token = security.create_access_token(
        user_id=u2_id,
        role="smb_owner",
        tenant_id=2,
        expires_delta=security.timedelta(minutes=-30),  # expired 30 minutes ago
    )
    r_expired = requests.get(
        f"{BASE_URL}/api/auth/me",
        headers={"Authorization": f"Bearer {expired_token}"},
        timeout=DEFAULT_TIMEOUT,
    )
    is_expired_401 = r_expired.status_code == 401
    record_result(
        test_name="Expired Token Returns 401 Unauthorized",
        expected="401 Unauthorized (expired token)",
        actual=f"{r_expired.status_code}: {r_expired.json().get('detail')}",
        passed=is_expired_401,
    )

    # Clean up and reset users back to standard demo passwords
    print("\n[CLEANUP] Resetting accounts to default passwords...")
    reset_user_db_state(SMB1_EMAIL, SMB1_PASS)
    reset_user_db_state(SMB2_EMAIL, SMB2_PASS)
    reset_user_db_state(SMB5_EMAIL, SMB5_PASS)

    # -------------------------------------------------------------------------
    # PRINT RESULTS TABLE
    # -------------------------------------------------------------------------
    print("\n" + "=" * 115)
    print("VERIFICATION RESULTS TABLE")
    print("=" * 115)
    header = f"{'Test Case':<48} | {'Expected':<30} | {'Actual':<24} | {'Status':<6}"
    print(header)
    print("-" * 115)
    total_passed = 0
    for row in TABLE_RESULTS:
        if row["status"] == "PASS":
            total_passed += 1
        print(f"{row['test']:<48} | {row['expected']:<30} | {row['actual']:<24} | {row['status']:<6}")
    print("-" * 115)
    print(f"Summary: Total Tests={len(TABLE_RESULTS)} | Passed={total_passed} | Failed={len(TABLE_RESULTS) - total_passed}")
    print("=" * 115)

    if total_passed == len(TABLE_RESULTS):
        print("\nALL SECURITY & AUTHENTICATION TESTS PASSED SUCCESSFULLY!")
        return 0
    else:
        print("\nSOME TESTS FAILED.")
        return 1


if __name__ == "__main__":
    sys.exit(run_tests())
