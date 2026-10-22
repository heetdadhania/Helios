import json
import os
import requests
from dotenv import load_dotenv

load_dotenv(".env")
test_pw = os.getenv("TEST_ACCOUNT_PASSWORD")
admin_pw = os.getenv("ADMIN_PASSWORD")

base_url = "http://localhost:8000"

def check_role(email, password, role_name):
    print(f"\n=================== Testing {role_name}: {email} ===================")
    login_resp = requests.post(f"{base_url}/api/v1/auth/login", json={"email": email, "password": password})
    assert login_resp.status_code == 200, f"Login failed: {login_resp.text}"
    token = login_resp.json()["access_token"]
    
    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.get(f"{base_url}/api/v1/profile/me", headers=headers)
    print(f"Status: {resp.status_code}")
    assert resp.status_code == 200, f"Profile request failed: {resp.text}"
    data = resp.json()
    
    # Assert no password hash or security columns
    raw_text = resp.text.lower()
    for forbidden in ["password_hash", "failed_login_count", "locked_until"]:
        assert forbidden not in raw_text, f"Security leak! Found {forbidden} in response"
    
    print("Role returned:", data.get("role"))
    print("Me:", json.dumps(data.get("me"), indent=2))
    
    if role_name == "smb_owner":
        print("Organization:", json.dumps(data.get("organization"), indent=2))
        print("Assigned TM:", json.dumps(data.get("assigned_team_member"), indent=2))
        print("Admin Contact:", json.dumps(data.get("admin_contact"), indent=2))
    elif role_name == "team_member":
        print("Assigned Orgs Count:", len(data.get("assigned_organizations", [])))
        if data.get("assigned_organizations"):
            print("First Org:", json.dumps(data["assigned_organizations"][0], indent=2))
        print("Admin Contact:", json.dumps(data.get("admin_contact"), indent=2))
    elif role_name == "admin":
        print("Platform Summary:", json.dumps(data.get("platform_summary"), indent=2))
        print("Team Members Count:", len(data.get("team_members", [])))
        if data.get("team_members"):
            print("First TM:", json.dumps(data["team_members"][0], indent=2))

check_role("smb-owner-1@helios-test.dev", test_pw, "smb_owner")
check_role("team-member-1@helios-test.dev", test_pw, "team_member")
check_role("admin@helios.io", admin_pw, "admin")
print("\n>>> All profile endpoint tests passed successfully! <<<")
