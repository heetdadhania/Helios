#!/usr/bin/env python3
"""
scripts/verify/test_profile_isolation.py
Verification script for GET /api/v1/profile/me tenant isolation and security.
Tests:
1. Owner's response contains only its own organization, and no password hash.
2. Team member's response contains only assigned organizations, and no password hash.
3. Admin response contains platform summary & team members, and no password hash.
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv(".env")

BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")
TEST_ACCOUNT_PASSWORD = os.getenv("TEST_ACCOUNT_PASSWORD")

RESULTS = []

def record_result(actor: str, route: str, tenant_tried: str, expected: str, actual: str, passed: bool):
    status_str = "PASS" if passed else "FAIL"
    RESULTS.append({
        "actor": actor,
        "route": route,
        "tenant_tried": tenant_tried,
        "expected": expected,
        "actual": actual,
        "pass_fail": status_str,
    })
    print(f"[{status_str}] {actor:14s} | {route:25s} | Tenant {tenant_tried:8s} | Exp: {expected:32s} | Act: {actual}")

def login(email: str, password: str) -> str:
    resp = requests.post(f"{BASE_URL}/api/v1/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, f"Login failed for {email}: {resp.text}"
    return resp.json()["access_token"]

def run_profile_isolation_tests():
    print("=" * 110)
    print("PROFILE ENDPOINT TENANT ISOLATION AND SECURITY VERIFICATION")
    print("=" * 110)

    # 1. SMB Owner 1 (Tenant 1)
    smb1_token = login("smb-owner-1@helios-test.dev", TEST_ACCOUNT_PASSWORD)
    r_owner = requests.get(f"{BASE_URL}/api/v1/profile/me", headers={"Authorization": f"Bearer {smb1_token}"})
    p_data = r_owner.json() if r_owner.status_code == 200 else {}
    org_data = p_data.get("organization") or {}
    no_hash_owner = "password_hash" not in r_owner.text.lower()
    only_own_org = (
        r_owner.status_code == 200
        and "Kaveri" in str(org_data.get("business_name", ""))
        and "2" not in str(org_data.get("business_name", ""))
    )
    passed_owner = only_own_org and no_hash_owner
    record_result(
        "smb-owner-1",
        "GET /api/v1/profile/me",
        "2",
        "200 (only own org, no hash)",
        f"{r_owner.status_code} (org='{org_data.get('business_name')}', no_hash={no_hash_owner})",
        passed_owner,
    )

    # 2. Team Member 1 (Assigned to 1 & 2)
    tm1_token = login("team-member-1@helios-test.dev", TEST_ACCOUNT_PASSWORD)
    r_tm = requests.get(f"{BASE_URL}/api/v1/profile/me", headers={"Authorization": f"Bearer {tm1_token}"})
    tm_data = r_tm.json() if r_tm.status_code == 200 else {}
    assigned_orgs = tm_data.get("assigned_organizations", [])
    assigned_tids = {o.get("tenant_id") for o in assigned_orgs}
    no_unassigned = (5 not in assigned_tids) and (9 not in assigned_tids)
    has_assigned = (1 in assigned_tids) and (2 in assigned_tids)
    no_hash_tm = "password_hash" not in r_tm.text.lower()
    passed_tm = r_tm.status_code == 200 and no_unassigned and has_assigned and no_hash_tm
    record_result(
        "team-member-1",
        "GET /api/v1/profile/me",
        "5, 9",
        "200 (only assigned orgs, no hash)",
        f"{r_tm.status_code} (assigned_orgs={sorted(list(assigned_tids))}, no_hash={no_hash_tm})",
        passed_tm,
    )

    # 3. Platform Admin
    admin_token = login("admin@helios.io", ADMIN_PASSWORD)
    r_adm = requests.get(f"{BASE_URL}/api/v1/profile/me", headers={"Authorization": f"Bearer {admin_token}"})
    adm_data = r_adm.json() if r_adm.status_code == 200 else {}
    no_hash_adm = "password_hash" not in r_adm.text.lower()
    has_summary = "platform_summary" in adm_data and "team_members" in adm_data
    passed_adm = r_adm.status_code == 200 and has_summary and no_hash_adm
    record_result(
        "admin",
        "GET /api/v1/profile/me",
        "ALL",
        "200 (summary & team, no hash)",
        f"{r_adm.status_code} (has_summary={has_summary}, no_hash={no_hash_adm})",
        passed_adm,
    )

    # Matrix Table Output
    print("\n" + "=" * 110)
    print("VERIFICATION MATRIX: GET /api/v1/profile/me")
    print("=" * 110)
    col_actor = 14
    col_route = 25
    col_tenant = 10
    col_exp = 34
    col_act = 38
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
            f"{item['actual'][:col_act]:{col_act}} | "
            f"{item['pass_fail']:{col_pf}}"
        )
    print("-" * len(header))
    print(f"Summary: Total Tests={len(RESULTS)} | Passed={sum(1 for x in RESULTS if x['pass_fail'] == 'PASS')} | Failed={sum(1 for x in RESULTS if x['pass_fail'] != 'PASS')}")
    return all_passed

if __name__ == "__main__":
    assert run_profile_isolation_tests()
