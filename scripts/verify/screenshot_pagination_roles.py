import asyncio
import base64
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
import websockets
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend"))
sys.stdout.reconfigure(encoding='utf-8')
from app.core import security

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


def make_history_page(page, page_size, total, role_name):
    start_idx = (page - 1) * page_size + 1
    end_idx = min(page * page_size, total)
    items = []
    for i in range(start_idx, end_idx + 1):
        items.append({
            "batch_id": f"BATCH-IN-2026-{i:04d}",
            "tenant_id": 1,
            "tenant": "Kaveri Textiles & Crafts",
            "tenant_name": "Kaveri Textiles & Crafts",
            "source_type": "upload",
            "stage": "gold_transform",
            "current_stage": "gold",
            "stage_status": "completed",
            "status": "completed",
            "created_at": "2026-11-01T10:00:00Z",
            "timestamp": "2026-11-01 10:00:00",
            "user_name": f"{role_name} User",
            "handled_by": "Operations Specialist",
            "error_message": None,
            "row_count": 150,
            "filename": f"orders_batch_{i:04d}.csv",
            "date": "2026-11-01",
            "label": "Gold transformed",
        })
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


global_fetch_handler = None

async def send_cmd(ws, msg_id, method, params=None):
    payload = {'id': msg_id, 'method': method, 'params': params or {}}
    await ws.send(json.dumps(payload))
    while True:
        resp = json.loads(await ws.recv())
        if resp.get('method') == 'Fetch.requestPaused' and global_fetch_handler:
            await global_fetch_handler(resp)
        elif resp.get('id') == msg_id:
            return resp


async def eval_expr(ws, msg_id, expr):
    res = await send_cmd(ws, msg_id, 'Runtime.evaluate', {'expression': expr, 'returnByValue': True})
    return res.get('result', {}).get('result', {}).get('value')


async def capture_screenshot(ws, msg_id, filename):
    res = await send_cmd(ws, msg_id, 'Page.captureScreenshot', {'format': 'png'})
    b64_data = res.get('result', {}).get('data', '')
    img_bytes = base64.b64decode(b64_data)
    out_path = os.path.join(ARTIFACT_DIR, filename)
    with open(out_path, 'wb') as f:
        f.write(img_bytes)
    print(f"  [SCREENSHOT SAVED] -> {out_path} ({len(img_bytes)} bytes)")
    return out_path


async def main():
    print("================================================================")
    print("PROOF RULE: Running real browser screenshot verification for all 3 roles")
    print("================================================================")

    # Launch Chrome headless with remote debugging
    temp_dir = tempfile.mkdtemp(prefix='helios_chrome_pagination_')
    chrome_proc = subprocess.Popen([
        CHROME_PATH,
        '--headless',
        '--remote-debugging-port=9226',
        f'--user-data-dir={temp_dir}',
        '--disable-gpu',
        '--no-first-run',
        '--no-default-browser-check',
        '--window-size=1440,950',
        'about:blank',
    ])
    await asyncio.sleep(2)

    try:
        with urllib.request.urlopen('http://127.0.0.1:9226/json') as resp:
            tabs = json.loads(resp.read().decode())
        page_tabs = [t for t in tabs if t.get('type') == 'page']
        ws_url = page_tabs[0]['webSocketDebuggerUrl']

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
                print(f"  [API FETCH INTERCEPTED] {url}")

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

                body = None
                if "/history/admin" in url:
                    body = json.dumps(make_history_page(req_page, req_page_size, 55, "Admin"))
                elif "/history/team" in url:
                    body = json.dumps(make_history_page(req_page, req_page_size, 48, "Team Member"))
                elif "/history/mine" in url:
                    body = json.dumps(make_history_page(req_page, req_page_size, 42, "Organization Owner"))
                elif "/notifications" in url:
                    body = json.dumps({"items": [], "total": 0, "page": 1, "page_size": 20})
                elif "/tenants" in url:
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

            global global_fetch_handler
            global_fetch_handler = handle_fetch

            async def send_with_fetch_pump(cmd_id, method, params=None):
                await ws.send(json.dumps({'id': cmd_id, 'method': method, 'params': params or {}}))
                while True:
                    raw = await ws.recv()
                    data = json.loads(raw)
                    if data.get('method') == 'Fetch.requestPaused':
                        await handle_fetch(data)
                    elif data.get('id') == cmd_id:
                        return data

            async def pump_events(duration=4.0):
                t_end = time.time() + duration
                while time.time() < t_end:
                    try:
                        raw = await asyncio.wait_for(ws.recv(), timeout=0.2)
                        data = json.loads(raw)
                        if data.get('method') == 'Fetch.requestPaused':
                            await handle_fetch(data)
                        elif data.get('method') in ('Console.messageAdded', 'Runtime.consoleAPICalled'):
                            pass
                    except asyncio.TimeoutError:
                        pass

            # ==============================================================
            # ROLE 1: ADMIN (Admin History with Server-Side Pagination)
            # ==============================================================
            print("\n[ROLE 1: ADMIN] Verifying Admin Submission History Pagination (Page 2)...")
            await send_with_fetch_pump(100, 'Page.navigate', {'url': 'http://localhost:5173/login'})
            await asyncio.sleep(1.0)

            admin_u = users['admin']
            admin_tok = tokens['admin']
            inject_admin = f"""
            localStorage.setItem('helios_token', '{admin_tok}');
            localStorage.setItem('helios_user', JSON.stringify({json.dumps(admin_u)}));
            localStorage.removeItem('helios_tenant_id');
            """
            await send_with_fetch_pump(101, 'Runtime.evaluate', {'expression': inject_admin})

            # Navigate to /admin/history?page=2
            await send_with_fetch_pump(102, 'Page.navigate', {'url': 'http://localhost:5173/admin/history?page=2'})
            await pump_events(3.0)

            admin_url = await eval_expr(ws, 103, 'window.location.href')
            admin_info = await eval_expr(ws, 104, 'document.body.innerText')
            pagination_text = await eval_expr(ws, 105, """
            Array.from(document.querySelectorAll("*"))
                .map(el => el.textContent.trim())
                .find(t => t.includes("Showing") && t.includes("results")) || ""
            """)
            print(f"  Current URL: {admin_url}")
            print(f"  Pagination label: '{pagination_text}'")
            await capture_screenshot(ws, 106, 'admin_paginated_history.png')
            assert "?page=2" in admin_url or "page=2" in admin_url, "URL query string must preserve page=2"
            assert "Showing" in pagination_text, "Pagination results indicator must be visible"

            # ==============================================================
            # ROLE 2: TEAM MEMBER (Team History with Server-Side Pagination)
            # ==============================================================
            print("\n[ROLE 2: TEAM MEMBER] Verifying Team Submission History Pagination (Page 2)...")
            team_u = users['team_member']
            team_tok = tokens['team_member']
            inject_team = f"""
            localStorage.setItem('helios_token', '{team_tok}');
            localStorage.setItem('helios_user', JSON.stringify({json.dumps(team_u)}));
            localStorage.setItem('helios_tenant_id', '1');
            """
            await send_with_fetch_pump(200, 'Runtime.evaluate', {'expression': inject_team})

            await send_with_fetch_pump(201, 'Page.navigate', {'url': 'http://localhost:5173/team/history?page=2'})
            await pump_events(3.0)

            team_url = await eval_expr(ws, 202, 'window.location.href')
            team_pagination_text = await eval_expr(ws, 203, """
            Array.from(document.querySelectorAll("*"))
                .map(el => el.textContent.trim())
                .find(t => t.includes("Showing") && t.includes("results")) || ""
            """)
            print(f"  Current URL: {team_url}")
            print(f"  Pagination label: '{team_pagination_text}'")
            await capture_screenshot(ws, 204, 'team_paginated_history.png')
            assert "page=2" in team_url, "URL query string must preserve page=2"
            assert "Showing" in team_pagination_text, "Pagination results indicator must be visible"

            # ==============================================================
            # ROLE 3: ORGANIZATION OWNER (Client History with Server-Side Pagination)
            # ==============================================================
            print("\n[ROLE 3: ORGANIZATION OWNER] Verifying Organization Owner Submission History Pagination (Page 2)...")
            owner_u = users['smb_owner']
            owner_tok = tokens['smb_owner']
            inject_owner = f"""
            localStorage.setItem('helios_token', '{owner_tok}');
            localStorage.setItem('helios_user', JSON.stringify({json.dumps(owner_u)}));
            localStorage.setItem('helios_tenant_id', '1');
            """
            await send_with_fetch_pump(300, 'Runtime.evaluate', {'expression': inject_owner})

            await send_with_fetch_pump(301, 'Page.navigate', {'url': 'http://localhost:5173/client/history?page=2'})
            await pump_events(3.0)

            owner_url = await eval_expr(ws, 302, 'window.location.href')
            owner_pagination_text = await eval_expr(ws, 303, """
            Array.from(document.querySelectorAll("*"))
                .map(el => el.textContent.trim())
                .find(t => t.includes("Showing") && t.includes("results")) || ""
            """)
            print(f"  Current URL: {owner_url}")
            print(f"  Pagination label: '{owner_pagination_text}'")
            await capture_screenshot(ws, 304, 'owner_paginated_history.png')
            assert "page=2" in owner_url, "URL query string must preserve page=2"
            assert "Showing" in owner_pagination_text, "Pagination results indicator must be visible"

            print("\n================================================================")
            print("SUCCESS: All 3 roles screenshot proofs captured and verified!")
            print("================================================================")

    finally:
        chrome_proc.terminate()
        try:
            shutil.rmtree(temp_dir, ignore_errors=True)
        except Exception:
            pass


if __name__ == '__main__':
    import urllib.parse
    asyncio.run(main())
