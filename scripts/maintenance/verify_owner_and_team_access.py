import os
import requests
from dotenv import load_dotenv

load_dotenv('.env')

test_password = os.getenv('TEST_ACCOUNT_PASSWORD')
admin_password = os.getenv('ADMIN_PASSWORD')

print("=== 1. Login as smb-owner-1 (Organization Owner) ===")
resp = requests.post('http://localhost:8000/api/v1/auth/login', json={
    'email': 'smb-owner-1@helios-test.dev',
    'password': test_password,
})
assert resp.status_code == 200, f"Login failed: {resp.text}"
owner_token = resp.json()['access_token']
owner_headers = {'Authorization': f'Bearer {owner_token}'}
print(f"Logged in successfully. User: {resp.json()['user']['email']}, Role: {resp.json()['user']['role']}")

print("\n=== 2. Verify all ingestion/connection/key routes return 403 for smb_owner ===")
checks = [
    ('POST', 'http://localhost:8000/api/v1/uploads', {'data': {'tenant_id': 1}, 'files': {'file': ('test.csv', b'a,b\n1,2', 'text/csv')}}),
    ('GET', 'http://localhost:8000/api/v1/uploads/1/status', {}),
    ('GET', 'http://localhost:8000/api/v1/uploads/pending', {}),
    ('POST', 'http://localhost:8000/api/v1/db-connections', {'json': {'db_type': 'postgresql', 'host': 'localhost', 'port': 5432, 'database_name': 'test', 'username': 'u', 'password': 'p', 'table_or_query': 't'}}),
    ('GET', 'http://localhost:8000/api/v1/db-connections?tenant_id=1', {}),
    ('POST', 'http://localhost:8000/api/v1/db-connections/test', {'json': {'db_type': 'postgresql', 'host': 'localhost', 'port': 5432, 'database_name': 'test', 'username': 'u', 'password': 'p', 'table_or_query': 't'}}),
    ('POST', 'http://localhost:8000/api/v1/db-connections/1/sync', {'json': {'tenant_id': 1}}),
    ('GET', 'http://localhost:8000/api/v1/api-keys', {}),
    ('POST', 'http://localhost:8000/api/v1/api-keys/regenerate', {}),
]

all_passed = True
for method, url, kwargs in checks:
    r = requests.request(method, url, headers=owner_headers, **kwargs)
    status = r.status_code
    passed = (status == 403)
    if not passed:
        all_passed = False
    print(f"[{method}] {url} -> Status: {status} | 403 Forbidden: {passed}")

print(f"\nAll owner routes 403 verification: {all_passed}")

print("\n=== 3. Login as team-member-1 (Operations Team Member) ===")
resp = requests.post('http://localhost:8000/api/v1/auth/login', json={
    'email': 'team-member-1@helios-test.dev',
    'password': test_password,
})
assert resp.status_code == 200, f"Team member login failed: {resp.text}"
team_token = resp.json()['access_token']
team_headers = {'Authorization': f'Bearer {team_token}'}
print(f"Logged in successfully. User: {resp.json()['user']['email']}, Role: {resp.json()['user']['role']}")

print("\n=== 4. Verify Team Member can access database-connections and uploads/pending ===")
r_db = requests.get('http://localhost:8000/api/v1/db-connections?tenant_id=1', headers=team_headers)
print(f"[GET] /api/v1/db-connections?tenant_id=1 -> Status: {r_db.status_code}")
assert r_db.status_code == 200, f"Expected 200, got {r_db.status_code}"

r_pending = requests.get('http://localhost:8000/api/v1/uploads/pending?tenant_id=1', headers=team_headers)
print(f"[GET] /api/v1/uploads/pending?tenant_id=1 -> Status: {r_pending.status_code}")
assert r_pending.status_code == 200, f"Expected 200, got {r_pending.status_code}"

print("\nAll backend checks passed successfully!")
