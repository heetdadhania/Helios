import json
import os
import urllib.request
import urllib.error
from dotenv import load_dotenv

load_dotenv()

ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD")
TEST_ACCOUNT_PASSWORD = os.environ.get("TEST_ACCOUNT_PASSWORD")

BASE_URL = "http://127.0.0.1:8000"

def http_json(method, path, body=None):
    url = f"{BASE_URL}{path}"
    headers = {"Content-Type": "application/json"}
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            status = resp.status
            content = resp.read().decode("utf-8")
            return status, json.loads(content) if content else None
    except urllib.error.HTTPError as e:
        content = e.read().decode("utf-8")
        try:
            parsed = json.loads(content)
        except Exception:
            parsed = content
        return e.code, parsed

print("--- Testing Backend Health ---")
status, health_resp = http_json("GET", "/api/v1/health")
print(f"GET /api/v1/health -> Status {status}, Response: {health_resp}")
assert status == 200, f"Expected 200, got {status}"

print("\n--- Testing Login with Invalid Password ---")
status, err_resp = http_json("POST", "/api/auth/login", {
    "email": "admin@helios.io",
    "password": "IncorrectPassword123!"
})
print(f"POST /api/auth/login [Wrong Password] -> Status {status}, Response: {err_resp}")
assert status == 401, f"Expected 401, got {status}"

print("\n--- Testing Login with Correct Credentials ---")
# Credentials loaded securely from environment / known test fixtures
status, login_resp = http_json("POST", "/api/auth/login", {
    "email": "admin@helios.io",
    "password": ADMIN_PASSWORD
})
print(f"POST /api/auth/login [Valid Admin] -> Status {status}")
assert status == 200, f"Expected 200, got {status}"
assert "access_token" in login_resp, "Expected access_token in response"
user_info = login_resp.get("user", {})
print(f"Logged in user info: id={user_info.get('id')}, email={user_info.get('email')}, role={user_info.get('role')}")

status, smb_resp = http_json("POST", "/api/auth/login", {
    "email": "smb-owner-1@helios-test.dev",
    "password": TEST_ACCOUNT_PASSWORD
})
print(f"POST /api/auth/login [Valid SMB Owner] -> Status {status}")
assert status == 200, f"Expected 200, got {status}"
smb_info = smb_resp.get("user", {})
print(f"Logged in user info: id={smb_info.get('id')}, email={smb_info.get('email')}, role={smb_info.get('role')}, tenant_id={smb_info.get('tenant_id')}")

print("\nAll Backend and Authentication Tests Passed Successfully!")
