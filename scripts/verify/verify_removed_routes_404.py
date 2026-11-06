import os
import sys
sys.path.insert(0, os.path.abspath("backend"))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_removed_routes_return_404():
    print("Testing that all removed API push and API key routes return HTTP 404...")

    routes_to_test = [
        ("POST", "/api/ingest"),
        ("POST", "/api/v1/ingest"),
        ("GET", "/api/api-keys"),
        ("GET", "/api/v1/api-keys"),
        ("POST", "/api/api-keys/regenerate"),
        ("POST", "/api/v1/api-keys/regenerate"),
    ]

    all_passed = True
    for method, path in routes_to_test:
        if method == "POST":
            resp = client.post(path, json={"records": []})
        else:
            resp = client.get(path)
        
        status = resp.status_code
        passed = (status == 404)
        if not passed:
            all_passed = False
        print(f"  [{method}] {path:30} -> HTTP {status} | 404 Expected: {passed}")

    assert all_passed, "Some removed routes did not return 404!"
    print("\nSUCCESS: All removed API push and API key routes return HTTP 404!")

if __name__ == "__main__":
    test_removed_routes_return_404()

