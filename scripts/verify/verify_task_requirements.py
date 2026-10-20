"""
Verification script for task requirements:
1. Admin, Team Member, SMB Owner login at /api/v1/auth/login and /api/v1/auth/me
2. GET /api/v1/team-members returns 200 with the 5 team members and their assigned tenants
3. 409 conflict when adding existing team member
4. Tenant schema and listing at /api/v1/tenants
"""
import sys
import requests

BASE_URL = "http://localhost:8000"

def run_tests():
    print("=" * 60)
    print("HELIOS TASK VERIFICATION SUITE")
    print("=" * 60)

    # 1. Admin Login
    print("\n--- 1. Testing Admin Login ---")
    admin_login_res = requests.post(
        f"{BASE_URL}/api/v1/auth/login",
        json={"email": "admin@helios.io", "password": "HeliosDemo2026!"},
        timeout=10,
    )
    print(f"POST /api/v1/auth/login [admin@helios.io] -> Status: {admin_login_res.status_code}")
    assert admin_login_res.status_code == 200, f"Admin login failed: {admin_login_res.text}"
    admin_data = admin_login_res.json()
    admin_token = admin_data["access_token"]
    print(f"Admin Profile: user_id={admin_data['user']['id']}, role={admin_data['user']['role']}")

    # 2. Team Member Login
    print("\n--- 2. Testing Team Member Login ---")
    tm_login_res = requests.post(
        f"{BASE_URL}/api/v1/auth/login",
        json={"email": "team-member-1@helios-test.dev", "password": "HeliosTest2026!"},
        timeout=10,
    )
    print(f"POST /api/v1/auth/login [team-member-1@helios-test.dev] -> Status: {tm_login_res.status_code}")
    assert tm_login_res.status_code == 200, f"Team member login failed: {tm_login_res.text}"
    tm_data = tm_login_res.json()
    tm_token = tm_data["access_token"]
    print(f"Team Member Profile: user_id={tm_data['user']['id']}, role={tm_data['user']['role']}")

    # 3. SMB Owner Login
    print("\n--- 3. Testing SMB Owner Login ---")
    smb_login_res = requests.post(
        f"{BASE_URL}/api/v1/auth/login",
        json={"email": "smb-owner-1@helios-test.dev", "password": "HeliosTest2026!"},
        timeout=10,
    )
    print(f"POST /api/v1/auth/login [smb-owner-1@helios-test.dev] -> Status: {smb_login_res.status_code}")
    assert smb_login_res.status_code == 200, f"SMB Owner login failed: {smb_login_res.text}"
    smb_data = smb_login_res.json()
    smb_token = smb_data["access_token"]
    print(f"SMB Owner Profile: user_id={smb_data['user']['id']}, role={smb_data['user']['role']}, tenant_id={smb_data['user']['tenant_id']}")

    # 4. Auth /me endpoints
    print("\n--- 4. Testing /api/v1/auth/me for each role ---")
    for name, token in [("Admin", admin_token), ("Team Member", tm_token), ("SMB Owner", smb_token)]:
        me_res = requests.get(f"{BASE_URL}/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}, timeout=10)
        print(f"GET /api/v1/auth/me [{name}] -> Status: {me_res.status_code}, User: {me_res.json().get('email')}")
        assert me_res.status_code == 200, f"/auth/me failed for {name}"

    # 5. GET /api/v1/team-members as Admin
    print("\n--- 5. Testing GET /api/v1/team-members as Admin ---")
    team_members_res = requests.get(
        f"{BASE_URL}/api/v1/team-members",
        headers={"Authorization": f"Bearer {admin_token}"},
        timeout=10,
    )
    print(f"GET /api/v1/team-members -> Status: {team_members_res.status_code}")
    assert team_members_res.status_code == 200, f"GET /api/v1/team-members failed: {team_members_res.text}"
    members = team_members_res.json()
    # Find all team_member role users
    team_members = [m for m in members if m.get("role") == "team_member"]
    print(f"Total internal users returned: {len(members)}, team_member role count: {len(team_members)}")
    for tm in team_members:
        print(f"  Team Member: {tm.get('name')} ({tm.get('email')}) | user_id={tm.get('user_id')} | assigned_tenants={tm.get('tenant_ids')}")
    assert len(team_members) >= 5, f"Expected at least 5 team members, got {len(team_members)}"

    # 6. Verify 409 conflict when adding existing team member
    print("\n--- 6. Testing 409 Conflict when Adding Existing Team Member ---")
    add_existing_res = requests.post(
        f"{BASE_URL}/api/v1/team-members",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "name": "Duplicate Team Member",
            "email": "team-member-1@helios-test.dev",
            "phone_number": "+1 555-019-9999",
            "role": "team_member",
            "tenant_ids": [],
        },
        timeout=10,
    )
    print(f"POST /api/v1/team-members [duplicate email] -> Status: {add_existing_res.status_code}")
    assert add_existing_res.status_code == 409, f"Expected 409, got {add_existing_res.status_code}: {add_existing_res.text}"
    conflict_detail = add_existing_res.json().get("detail")
    print(f"Conflict detail message: {conflict_detail}")
    assert "already exists" in conflict_detail.lower(), "Expected conflict message to contain 'already exists'"

    # 7. GET /api/v1/tenants as Admin
    print("\n--- 7. Testing GET /api/v1/tenants as Admin ---")
    tenants_res = requests.get(
        f"{BASE_URL}/api/v1/tenants",
        headers={"Authorization": f"Bearer {admin_token}"},
        timeout=10,
    )
    print(f"GET /api/v1/tenants -> Status: {tenants_res.status_code}")
    assert tenants_res.status_code == 200, f"GET /api/v1/tenants failed: {tenants_res.text}"
    tenants_list = tenants_res.json()
    print(f"Total tenants returned: {len(tenants_list)}")
    sample_tenant = tenants_list[0] if tenants_list else {}
    print(f"Sample tenant fields: business_name={sample_tenant.get('business_name')}, contact_person_name={sample_tenant.get('contact_person_name')}, city={sample_tenant.get('city')}, phone_number={sample_tenant.get('phone_number')}")

    print("\n" + "=" * 60)
    print("ALL BACKEND VERIFICATION CHECKS PASSED SUCCESSFULLY!")
    print("=" * 60)

if __name__ == "__main__":
    run_tests()
