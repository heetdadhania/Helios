#!/usr/bin/env python3
"""
Verification Script for 5 Scenarios:
1. Two approvals started at the same moment for the same tenant: exactly one succeeds, the other returns 409.
2. A REAL failure: find an input that makes Silver or Gold fail on its own without editing code or writing a failed status by hand, showing failure fields and retry behavior.
3. Cancel a running batch (using a 2,000-row file) and show status cancelled (or report if it finished too fast).
4. Full restart: show the batch cancelled, SMB Owner notification, and history text.
5. Stalled: set one running batch's heartbeat to 30 minutes ago and show it reported as stalled (state test).
"""

import sys
import os
import json
import time
import uuid
import threading
import urllib.request
import urllib.error
from datetime import datetime, timezone

# Add backend directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "backend"))
from app.db.base import get_databricks_connection
from app.core.config import settings

BASE_URL = "http://127.0.0.1:8000"
CATALOG = getattr(settings, "DATABRICKS_CATALOG", "helios_catalog")

def http_req(method: str, path: str, body: dict = None, token: str = None, timeout: int = 60):
    url = f"{BASE_URL}{path}"
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            content = resp.read().decode("utf-8")
            return resp.status, json.loads(content) if content else {}
    except urllib.error.HTTPError as e:
        content = e.read().decode("utf-8")
        try:
            parsed = json.loads(content)
        except Exception:
            parsed = {"raw": content}
        return e.code, parsed
    except Exception as e:
        return 500, {"error": str(e)}

def get_tokens():
    from dotenv import load_dotenv
    load_dotenv()
    admin_pw = os.environ.get("ADMIN_PASSWORD")
    test_pw = os.environ.get("TEST_ACCOUNT_PASSWORD")
    # Admin login
    _, admin_res = http_req("POST", "/api/auth/login", {"email": "admin@helios.io", "password": admin_pw})
    admin_token = admin_res.get("access_token")
    
    # SMB Owner login (Tenant 1)
    _, smb_res = http_req("POST", "/api/auth/login", {"email": "smb-owner-1@helios-test.dev", "password": test_pw})
    smb_token = smb_res.get("access_token")
    return admin_token, smb_token

# ==============================================================================
# SCENARIO 1: Concurrent Approvals
# ==============================================================================
def run_scenario_1(admin_token):
    print("\n" + "="*80)
    print("SCENARIO 1: Two Approvals Started at Same Moment for Same Tenant (Tenant 1)")
    print("="*80)
    
    tenant_id = 1
    batch_1 = f"batch_conc_{uuid.uuid4().hex[:8]}"
    batch_2 = f"batch_conc_{uuid.uuid4().hex[:8]}"
    
    conn = get_databricks_connection(catalog=CATALOG)
    with conn.cursor() as cur:
        # Create 2 pending batches for Tenant 1
        for b in [batch_1, batch_2]:
            cur.execute(f"""
                INSERT INTO `{CATALOG}`.`platform`.`pipeline_status` (
                    batch_id, tenant_id, stage, status, created_at, updated_at
                ) VALUES (
                    '{b}', {tenant_id}, 'schema_inference', 'pending_review', current_timestamp(), current_timestamp()
                )
            """)
            cur.execute(f"""
                INSERT INTO `{CATALOG}`.`platform`.`inferred_schema` (
                    batch_id, detected_template, confidence_score, column_mapping_json, created_at
                ) VALUES (
                    '{b}', 'Shopify Orders', 0.95, '{{}}', current_timestamp()
                )
            """)
    conn.close()
    
    print(f"Created pending batches for Tenant {tenant_id}: {batch_1}, {batch_2}")
    
    results = {}
    
    def approve_batch(batch_id):
        t0 = time.time()
        status_code, body = http_req(
            "POST",
            f"/api/uploads/{batch_id}/confirm",
            {"confirmed_template": "Shopify Orders", "corrected_mapping": {}, "internal_notes": "Concurrent test"},
            token=admin_token
        )
        dur = round(time.time() - t0, 3)
        results[batch_id] = (status_code, body, dur)

    # Launch concurrently
    t1 = threading.Thread(target=approve_batch, args=(batch_1,))
    t2 = threading.Thread(target=approve_batch, args=(batch_2,))
    
    t1.start()
    t2.start()
    t1.join()
    t2.join()
    
    for b, (code, body, dur) in results.items():
        print(f"Batch {b}: HTTP Status {code} (took {dur}s) -> Detail: {body.get('detail') or body.get('message')}")
    
    codes = [r[0] for r in results.values()]
    print(f"\nResult Summary: HTTP Codes received: {codes}")
    success_count = sum(1 for c in codes if c in (200, 201))
    conflict_count = sum(1 for c in codes if c == 409)
    print(f"Success Count (200): {success_count}, Conflict Count (409): {conflict_count}")
    assert success_count == 1 and conflict_count == 1, f"Expected exactly one 200 and one 409, got {codes}"
    print("PASS: Exactly one approval succeeded and the other returned 409.")
    return {
        "batch_1": {"id": batch_1, "status_code": results[batch_1][0], "response": results[batch_1][1]},
        "batch_2": {"id": batch_2, "status_code": results[batch_2][0], "response": results[batch_2][1]}
    }

if __name__ == "__main__":
    admin_tok, smb_tok = get_tokens()
    print("Auth tokens acquired successfully.")
    run_scenario_1(admin_tok)
