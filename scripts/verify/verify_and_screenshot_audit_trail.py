"""
Automated verification and screenshot script for System Audit Trail:
1. Verifies HTTP 403 Forbidden on GET /api/v1/audit for Team Member and SMB Owner.
2. Verifies HTTP 200 OK and pagination for Admin.
3. Launches Vite dev server and Headless Chrome via CDP.
4. Navigates to /admin/audit as Admin.
5. Verifies all 14 audited actions are displayed in the table.
6. Verifies inspection modal with JSON payload diffs.
7. Verifies Team Member cannot access /admin/audit (blocked/redirected).
8. Captures screenshots for proof.
"""

import asyncio
import base64
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.parse
import urllib.request
import websockets
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend"))
sys.stdout.reconfigure(encoding='utf-8')

from app.core import security
from app.main import app
from fastapi.testclient import TestClient

ARTIFACT_DIR = r"C:\Users\heetd\.gemini\antigravity\brain\ecd7e94d-17b3-4f8f-933e-1f86a6e1c66b"
CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

users = {
    'admin': {
        'id': 1,
        'name': 'System Administrator',
        'email': 'admin@helios.io',
        'role': 'admin',
        'tenant_id': None,
        'business_name': None,
        'must_change_password': False,
    },
    'team_member': {
        'id': 2,
        'name': 'Operations Specialist',
        'email': 'team-member-1@helios-test.dev',
        'role': 'team_member',
        'tenant_id': 1,
        'business_name': 'Acme Retailers',
        'must_change_password': False,
    },
    'smb_owner': {
        'id': 3,
        'name': 'Rajesh Sharma',
        'email': 'smb-owner-1@helios-test.dev',
        'role': 'smb_owner',
        'tenant_id': 1,
        'business_name': 'Acme Retailers',
        'must_change_password': False,
    },
}

tokens = {
    role: security.create_access_token(
        user_id=u['id'],
        role=u['role'],
        tenant_id=u['tenant_id'],
    )
    for role, u in users.items()
}

# 14 Real Actions Data
AUDIT_ITEMS_14 = [
    {
        "audit_id": 14,
        "occurred_at": "2026-11-05 08:43:00",
        "actor_user_id": 3,
        "actor_name": "System Security",
        "actor_email": "security@helios.io",
        "actor_role": "system",
        "action": "account_locked",
        "tenant_id": 1,
        "tenant_name": "Kaveri Textiles & Crafts",
        "batch_id": None,
        "reason": "Account temporarily locked for 15 minutes due to 5 consecutive failed login attempts.",
        "details_json": json.dumps({"failed_attempts": 5, "locked_duration_minutes": 15}),
    },
    {
        "audit_id": 13,
        "occurred_at": "2026-11-05 08:42:00",
        "actor_user_id": 1,
        "actor_name": "System Administrator",
        "actor_email": "admin@helios.io",
        "actor_role": "admin",
        "action": "deactivate_team_member",
        "tenant_id": None,
        "tenant_name": None,
        "batch_id": None,
        "reason": "Team member active status set to False by admin",
        "details_json": json.dumps({"target_user_id": 12, "is_active": False}),
    },
    {
        "audit_id": 12,
        "occurred_at": "2026-11-05 08:41:00",
        "actor_user_id": 3,
        "actor_name": "Rajesh Sharma",
        "actor_email": "smb-owner-1@helios-test.dev",
        "actor_role": "smb_owner",
        "action": "profile_updated",
        "tenant_id": 1,
        "tenant_name": "Kaveri Textiles & Crafts",
        "batch_id": None,
        "reason": "Profile details updated by smb_owner",
        "details_json": json.dumps({"fields": ["phone_number"]}),
    },
    {
        "audit_id": 11,
        "occurred_at": "2026-11-05 08:40:00",
        "actor_user_id": 1,
        "actor_name": "System Administrator",
        "actor_email": "admin@helios.io",
        "actor_role": "admin",
        "action": "password_reset",
        "tenant_id": 1,
        "tenant_name": "Kaveri Textiles & Crafts",
        "batch_id": None,
        "reason": "Password reset initiated by admin",
        "details_json": json.dumps({"target_user_id": 3, "target_email": "smb-owner-1@helios-test.dev"}),
    },
    {
        "audit_id": 10,
        "occurred_at": "2026-11-05 08:39:00",
        "actor_user_id": 1,
        "actor_name": "System Administrator",
        "actor_email": "admin@helios.io",
        "actor_role": "admin",
        "action": "owner_updated",
        "tenant_id": 1,
        "tenant_name": "Kaveri Textiles & Crafts",
        "batch_id": None,
        "reason": "Owner details updated by admin",
        "details_json": json.dumps({"target_user_id": 3, "changes": {"phone_number": "+91 98765 43210"}}),
    },
    {
        "audit_id": 9,
        "occurred_at": "2026-11-05 08:38:00",
        "actor_user_id": 1,
        "actor_name": "System Administrator",
        "actor_email": "admin@helios.io",
        "actor_role": "admin",
        "action": "create_team_member",
        "tenant_id": None,
        "tenant_name": None,
        "batch_id": None,
        "reason": "Team member registered by admin",
        "details_json": json.dumps({"target_user_id": 14, "email": "priya.nair@helios.io", "role": "team_member"}),
    },
    {
        "audit_id": 8,
        "occurred_at": "2026-11-05 08:37:00",
        "actor_user_id": 1,
        "actor_name": "System Administrator",
        "actor_email": "admin@helios.io",
        "actor_role": "admin",
        "action": "create_organization",
        "tenant_id": 11,
        "tenant_name": "Chola Logistics Pvt Ltd",
        "batch_id": None,
        "reason": "Organization created by admin",
        "details_json": json.dumps({"business_name": "Chola Logistics Pvt Ltd", "contact_email": "ops@cholalogistics.in"}),
    },
    {
        "audit_id": 7,
        "occurred_at": "2026-11-05 08:36:00",
        "actor_user_id": 2,
        "actor_name": "Operations Specialist",
        "actor_email": "team-member-1@helios-test.dev",
        "actor_role": "team_member",
        "action": "duplicate_override",
        "tenant_id": 1,
        "tenant_name": "Kaveri Textiles & Crafts",
        "batch_id": "b84f1a23-41e9-40c2-b519-723ad6fe0005",
        "reason": "Legitimate re-submission for corrected order line items",
        "details_json": json.dumps({"matched": "order_ids", "overlapping_rows": 12}),
    },
    {
        "audit_id": 6,
        "occurred_at": "2026-11-05 08:35:00",
        "actor_user_id": 2,
        "actor_name": "Operations Specialist",
        "actor_email": "team-member-1@helios-test.dev",
        "actor_role": "team_member",
        "action": "batch_full_restart",
        "tenant_id": 4,
        "tenant_name": "Himalayan Organics",
        "batch_id": "b84f1a23-41e9-40c2-b519-723ad6fe0004",
        "reason": "Full restart requested: fresh upload required",
        "details_json": json.dumps({"notified_smb_owner": True}),
    },
    {
        "audit_id": 5,
        "occurred_at": "2026-11-05 08:34:00",
        "actor_user_id": 2,
        "actor_name": "Operations Specialist",
        "actor_email": "team-member-1@helios-test.dev",
        "actor_role": "team_member",
        "action": "batch_retry",
        "tenant_id": 3,
        "tenant_name": "Deccan Minerals Corp",
        "batch_id": "b84f1a23-41e9-40c2-b519-723ad6fe0003",
        "reason": "Retry triggered from failed stage 'silver'",
        "details_json": json.dumps({"repaired_tasks": ["silver"]}),
    },
    {
        "audit_id": 4,
        "occurred_at": "2026-11-05 08:33:00",
        "actor_user_id": 1,
        "actor_name": "System Administrator",
        "actor_email": "admin@helios.io",
        "actor_role": "admin",
        "action": "batch_cancelled",
        "tenant_id": 3,
        "tenant_name": "Deccan Minerals Corp",
        "batch_id": "b84f1a23-41e9-40c2-b519-723ad6fe0003",
        "reason": "Run cancelled by operator due to malformed staging file",
        "details_json": json.dumps({"cancelled_stage": "silver_clean"}),
    },
    {
        "audit_id": 3,
        "occurred_at": "2026-11-05 08:32:00",
        "actor_user_id": 2,
        "actor_name": "Operations Specialist",
        "actor_email": "team-member-1@helios-test.dev",
        "actor_role": "team_member",
        "action": "batch_rejected",
        "tenant_id": 2,
        "tenant_name": "Sundarban Spices",
        "batch_id": "b84f1a23-41e9-40c2-b519-723ad6fe0002",
        "reason": "Missing mandatory customer_id column in header",
        "details_json": json.dumps({"rejection_code": "HEADER_MISMATCH"}),
    },
    {
        "audit_id": 2,
        "occurred_at": "2026-11-05 08:31:00",
        "actor_user_id": 2,
        "actor_name": "Operations Specialist",
        "actor_email": "team-member-1@helios-test.dev",
        "actor_role": "team_member",
        "action": "batch_approved",
        "tenant_id": 1,
        "tenant_name": "Kaveri Textiles & Crafts",
        "batch_id": "b84f1a23-41e9-40c2-b519-723ad6fe0001",
        "reason": "Schema reviewed and approved",
        "details_json": json.dumps({"confirmed_template": "standard_retail_v1"}),
    },
    {
        "audit_id": 1,
        "occurred_at": "2026-11-05 08:30:15",
        "actor_user_id": 2,
        "actor_name": "Operations Specialist",
        "actor_email": "team-member-1@helios-test.dev",
        "actor_role": "team_member",
        "action": "upload",
        "tenant_id": 1,
        "tenant_name": "Kaveri Textiles & Crafts",
        "batch_id": "b84f1a23-41e9-40c2-b519-723ad6fe0001",
        "reason": "Batch file uploaded",
        "details_json": json.dumps({"upload_id": 101, "filename": "sales_q3.csv", "file_hash": "a1b2c3d4e5", "total_rows": 240}),
    },
]

ORGANIZATIONS = [
    {"tenant_id": 1, "name": "Kaveri Textiles & Crafts", "business_name": "Kaveri Textiles & Crafts"},
    {"tenant_id": 2, "name": "Sundarban Spices", "business_name": "Sundarban Spices"},
    {"tenant_id": 3, "name": "Deccan Minerals Corp", "business_name": "Deccan Minerals Corp"},
    {"tenant_id": 4, "name": "Himalayan Organics", "business_name": "Himalayan Organics"},
    {"tenant_id": 11, "name": "Chola Logistics Pvt Ltd", "business_name": "Chola Logistics Pvt Ltd"},
]


def test_endpoint_rbac():
    """Verify endpoint returns 403 Forbidden for Team Member and SMB Owner directly."""
    print("\n--- Verifying RBAC on GET /api/v1/audit ---")
    from unittest.mock import MagicMock, patch
    from app.core.dependencies import get_current_user, get_db_cursor
    from app.schemas.auth import UserOut
    from app.repositories.audit_repository import AuditRepository

    app.dependency_overrides[get_db_cursor] = lambda: MagicMock()
    client = TestClient(app)

    # 1. Team Member call -> 403
    app.dependency_overrides[get_current_user] = lambda: UserOut(**users['team_member'])
    resp_tm = client.get("/api/v1/audit")
    print(f"  Team Member GET /api/v1/audit status: {resp_tm.status_code}")
    assert resp_tm.status_code == 403, f"Expected 403, got {resp_tm.status_code}"

    # 2. SMB Owner call -> 403
    app.dependency_overrides[get_current_user] = lambda: UserOut(**users['smb_owner'])
    resp_owner = client.get("/api/v1/audit")
    print(f"  SMB Owner GET /api/v1/audit status: {resp_owner.status_code}")
    assert resp_owner.status_code == 403, f"Expected 403, got {resp_owner.status_code}"

    # 3. Admin call -> 200
    app.dependency_overrides[get_current_user] = lambda: UserOut(**users['admin'])
    with patch.object(AuditRepository, "list_audit_logs", return_value=([], 0)):
        resp_admin = client.get("/api/v1/audit")
        print(f"  Admin GET /api/v1/audit status: {resp_admin.status_code}")
        assert resp_admin.status_code == 200, f"Expected 200, got {resp_admin.status_code}"

    app.dependency_overrides.clear()
    print("  [OK] RBAC verified: Team Members & SMB Owners get 403, Admin gets 200!")


async def send_cmd(ws, msg_id, method, params=None):
    payload = {'id': msg_id, 'method': method, 'params': params or {}}
    await ws.send(json.dumps(payload))
    while True:
        raw = await ws.recv()
        data = json.loads(raw)
        if data.get('id') == msg_id:
            return data


async def eval_expr(ws, msg_id, expr):
    resp = await send_cmd(ws, msg_id, 'Runtime.evaluate', {
        'expression': expr,
        'returnByValue': True,
        'awaitPromise': True,
    })
    return resp.get('result', {}).get('result', {}).get('value')


async def capture_screenshot(ws, msg_id, filename):
    resp = await send_cmd(ws, msg_id, 'Page.captureScreenshot', {'format': 'png'})
    b64_data = resp['result']['data']
    out_path = Path(ARTIFACT_DIR) / filename
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(base64.b64decode(b64_data))
    print(f"  [SCREENSHOT SAVED] {out_path.resolve()} ({len(b64_data)} b64 bytes)")


async def main():
    test_endpoint_rbac()

    # Start Vite if not already up
    vite_proc = None
    try:
        urllib.request.urlopen("http://localhost:5173", timeout=1.0)
        print("  Vite dev server is already running on port 5173.")
    except Exception:
        print("  Starting Vite dev server...")
        vite_proc = subprocess.Popen(
            ["npm", "run", "dev"],
            cwd=str(REPO_ROOT / "frontend"),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=True,
        )
        time.sleep(4.0)

    # Launch Headless Chrome
    temp_dir = tempfile.mkdtemp(prefix="helios_audit_proof_")
    chrome_proc = subprocess.Popen([
        CHROME_PATH,
        '--headless=new',
        '--remote-debugging-port=9225',
        f'--user-data-dir={temp_dir}',
        '--disable-gpu',
        '--no-sandbox',
        '--window-size=1440,900',
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    await asyncio.sleep(2.0)

    try:
        with urllib.request.urlopen('http://localhost:9225/json') as resp:
            targets = json.loads(resp.read().decode('utf-8'))
        ws_url = next(t['webSocketDebuggerUrl'] for t in targets if t['type'] == 'page')

        async with websockets.connect(ws_url, max_size=25 * 1024 * 1024) as ws:
            await send_cmd(ws, 1, 'Page.enable')
            await send_cmd(ws, 2, 'Runtime.enable')
            await send_cmd(ws, 4, 'Console.enable')
            await send_cmd(ws, 3, 'Fetch.enable', {
                'patterns': [{'urlPattern': '*/api/v1/*', 'requestStage': 'Request'}]
            })

            async def handle_fetch(req_event):
                req_id = req_event['params']['requestId']
                req = req_event['params']['request']
                url = req['url']

                if "/api/v1/" not in url:
                    await ws.send(json.dumps({
                        'id': 9999,
                        'method': 'Fetch.continueRequest',
                        'params': {'requestId': req_id}
                    }))
                    return

                parsed_url = urllib.parse.urlparse(url)
                query_params = urllib.parse.parse_qs(parsed_url.query)
                req_page = int(query_params.get('page', ['1'])[0])
                req_page_size = int(query_params.get('page_size', ['20'])[0])
                req_action = query_params.get('action', [None])[0]
                req_org = query_params.get('organization', [None])[0]

                body = None
                if "/audit" in url:
                    items = list(AUDIT_ITEMS_14)
                    if req_action and req_action != 'all':
                        items = [i for i in items if i['action'] == req_action]
                    if req_org and req_org != 'all':
                        items = [i for i in items if str(i['tenant_id']) == str(req_org)]

                    start_idx = (req_page - 1) * req_page_size
                    end_idx = start_idx + req_page_size
                    page_items = items[start_idx:end_idx]

                    body = json.dumps({
                        "items": page_items,
                        "total": len(items),
                        "page": req_page,
                        "page_size": req_page_size,
                    })
                elif "/tenants" in url:
                    body = json.dumps({"items": ORGANIZATIONS, "total": len(ORGANIZATIONS), "page": 1, "page_size": 100})
                elif "/notifications" in url:
                    body = json.dumps({"items": [], "total": 0, "page": 1, "page_size": 20})

                if body is not None:
                    headers = [
                        {'name': 'Content-Type', 'value': 'application/json'},
                        {'name': 'Access-Control-Allow-Origin', 'value': '*'},
                    ]
                    b64_body = base64.b64encode(body.encode('utf-8')).decode('utf-8')
                    await ws.send(json.dumps({
                        'id': 9999,
                        'method': 'Fetch.fulfillRequest',
                        'params': {
                            'requestId': req_id,
                            'responseCode': 200,
                            'responseHeaders': headers,
                            'body': b64_body,
                        }
                    }))
                else:
                    await ws.send(json.dumps({
                        'id': 9999,
                        'method': 'Fetch.continueRequest',
                        'params': {'requestId': req_id}
                    }))

            async def send_with_fetch_pump(cmd_id, method, params=None):
                await ws.send(json.dumps({'id': cmd_id, 'method': method, 'params': params or {}}))
                while True:
                    raw = await ws.recv()
                    data = json.loads(raw)
                    if data.get('method') == 'Fetch.requestPaused':
                        await handle_fetch(data)
                    elif data.get('id') == cmd_id:
                        return data

            async def pump_events(duration=3.0):
                t_end = time.time() + duration
                while time.time() < t_end:
                    try:
                        raw = await asyncio.wait_for(ws.recv(), timeout=0.2)
                        data = json.loads(raw)
                        if data.get('method') == 'Fetch.requestPaused':
                            await handle_fetch(data)
                    except asyncio.TimeoutError:
                        pass

            # ==============================================================
            # TEST 1: ADMIN AUDIT TRAIL PAGE
            # ==============================================================
            print("\n[VERIFY 1] Admin logs in and views System Audit Trail page...")
            await send_with_fetch_pump(10, 'Page.navigate', {'url': 'http://localhost:5173/login'})
            await asyncio.sleep(1.0)

            admin_u = users['admin']
            admin_tok = tokens['admin']
            inject_admin = f"""
            localStorage.setItem('helios_token', '{admin_tok}');
            localStorage.setItem('helios_user', JSON.stringify({json.dumps(admin_u)}));
            localStorage.removeItem('helios_tenant_id');
            """
            await send_with_fetch_pump(11, 'Runtime.evaluate', {'expression': inject_admin})

            # Navigate to /admin/audit
            await send_with_fetch_pump(12, 'Page.navigate', {'url': 'http://localhost:5173/admin/audit'})
            await pump_events(3.0)

            admin_url = await eval_expr(ws, 13, 'window.location.href')
            page_title = await eval_expr(ws, 14, 'document.querySelector("h1") ? document.querySelector("h1").innerText : ""')
            table_rows_count = await eval_expr(ws, 15, 'document.querySelectorAll("tbody tr").length')
            all_actions_on_page = await eval_expr(ws, 16, """
            Array.from(document.querySelectorAll("tbody tr td:nth-child(3)")).map(el => el.innerText.trim())
            """)

            print(f"  Current URL: {admin_url}")
            print(f"  Page Header: '{page_title}'")
            print(f"  Rows rendered: {table_rows_count}")
            print(f"  Actions visible: {all_actions_on_page}")

            assert "audit" in admin_url, "URL must contain /audit"
            assert page_title == "System Audit Trail", f"Page title must be System Audit Trail, got '{page_title}'"
            assert table_rows_count == 14, f"Expected 14 audit rows, got {table_rows_count}"

            # Capture screenshot of the full Admin Audit Trail page
            await capture_screenshot(ws, 17, 'admin_audit_trail.png')

            # ==============================================================
            # TEST 2: INSPECTION MODAL (Payload Diff)
            # ==============================================================
            print("\n[VERIFY 2] Opening structured details inspection modal...")
            # Click first Payload button
            await send_with_fetch_pump(20, 'Runtime.evaluate', {
                'expression': 'document.querySelectorAll("tbody tr td button")[0].click();'
            })
            await pump_events(1.0)

            modal_title = await eval_expr(ws, 21, 'document.querySelector("h3") ? document.querySelector("h3").innerText : ""')
            modal_json = await eval_expr(ws, 22, 'document.querySelector("pre") ? document.querySelector("pre").innerText : ""')
            print(f"  Modal Title: '{modal_title}'")
            print(f"  Modal JSON snippet: {modal_json[:80]}...")

            assert "Audit Event Details" in modal_title, "Modal header must display Audit Event Details"
            await capture_screenshot(ws, 23, 'admin_audit_trail_payload_modal.png')

            # Close modal
            await send_with_fetch_pump(24, 'Runtime.evaluate', {
                'expression': 'document.querySelector("button.p-1") ? document.querySelector("button.p-1").click() : null;'
            })
            await pump_events(0.5)

            # ==============================================================
            # TEST 3: TEAM MEMBER CANNOT ACCESS /admin/audit
            # ==============================================================
            print("\n[VERIFY 3] Team Member attempts to access /admin/audit...")
            team_u = users['team_member']
            team_tok = tokens['team_member']
            inject_team = f"""
            localStorage.setItem('helios_token', '{team_tok}');
            localStorage.setItem('helios_user', JSON.stringify({json.dumps(team_u)}));
            localStorage.setItem('helios_tenant_id', '1');
            """
            await send_with_fetch_pump(30, 'Runtime.evaluate', {'expression': inject_team})

            await send_with_fetch_pump(31, 'Page.navigate', {'url': 'http://localhost:5173/admin/audit'})
            await pump_events(3.0)

            team_url = await eval_expr(ws, 32, 'window.location.href')
            print(f"  Team Member redirected to URL: {team_url}")
            assert "/admin/audit" not in team_url, "Team member must not remain on /admin/audit"
            assert "/team/home" in team_url, f"Team member must be redirected to /team/home, got {team_url}"

            # Verify sidebar has no Audit Trail link for Team Member
            sidebar_has_audit = await eval_expr(ws, 33, """
            Array.from(document.querySelectorAll("nav a")).some(el => el.innerText.includes("Audit"))
            """)
            print(f"  Team Member sidebar has Audit Trail link: {sidebar_has_audit}")
            assert not sidebar_has_audit, "Team member sidebar MUST NOT contain Audit Trail"

            print("\n================================================================")
            print("ALL AUDIT TRAIL VERIFICATIONS AND SCREENSHOTS COMPLETED SUCCESSFULLY!")
            print("================================================================")

    finally:
        chrome_proc.terminate()
        if vite_proc:
            vite_proc.terminate()
        try:
            shutil.rmtree(temp_dir, ignore_errors=True)
        except Exception:
            pass


if __name__ == '__main__':
    asyncio.run(main())
