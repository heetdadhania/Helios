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
from app.core import security

ARTIFACT_DIR = r"C:\Users\heetd\.gemini\antigravity\brain\ecd7e94d-17b3-4f8f-933e-1f86a6e1c66b"
CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

admin_user = {
    'id': 1,
    'name': 'System Administrator',
    'email': 'admin@helios.io',
    'role': 'admin',
    'tenant_id': None,
    'business_name': None,
    'must_change_password': False,
}
admin_token = security.create_access_token(user_id=1, role='admin')

mock_dq_logs = [
    {
        "id": "dql-1001",
        "batch_id": "batch-org1-orders-demo-001",
        "tenant_id": "1",
        "tenant_name": "Kaveri Textiles & Crafts",
        "table_name": "silver.orders_clean",
        "rejection_reason": "invalid_date_fields: order_date (original_value: not-a-date)",
        "timestamp": "2026-10-19T12:00:00Z",
        "error_category": "Type Mismatch",
    },
    {
        "id": "dql-1002",
        "batch_id": "batch-org1-orders-demo-001",
        "tenant_id": "1",
        "tenant_name": "Kaveri Textiles & Crafts",
        "table_name": "silver.orders_clean",
        "rejection_reason": "invalid_quantity: quantity must be greater than zero (original_value: -2)",
        "timestamp": "2026-10-19T12:00:00Z",
        "error_category": "Type Mismatch",
    },
    {
        "id": "dql-1003",
        "batch_id": "batch-org1-orders-demo-001",
        "tenant_id": "1",
        "tenant_name": "Kaveri Textiles & Crafts",
        "table_name": "silver.orders_clean",
        "rejection_reason": "missing_required_key: quantity (original_value: None)",
        "timestamp": "2026-10-19T12:00:00Z",
        "error_category": "Null Threshold Exceeded",
    },
]

mock_pipeline_runs = [
    {
        "batch_id": "batch-org1-orders-demo-001",
        "tenant_id": 1,
        "tenant": "Kaveri Textiles & Crafts",
        "tenant_name": "Kaveri Textiles & Crafts",
        "source_type": "upload",
        "current_stage": "gold",
        "status": "success",
        "rejection_count": 6,
        "started_at": "2026-10-19T12:00:00Z",
        "updated_at": "2026-10-19T12:05:00Z",
    },
    {
        "batch_id": "batch-clean-no-rejections-002",
        "tenant_id": 1,
        "tenant": "Kaveri Textiles & Crafts",
        "tenant_name": "Kaveri Textiles & Crafts",
        "source_type": "upload",
        "current_stage": "gold",
        "status": "success",
        "rejection_count": 0,
        "started_at": "2026-10-19T11:00:00Z",
        "updated_at": "2026-10-19T11:04:00Z",
    },
]

mock_run_with_rejections = {
    "batch_id": "batch-org1-orders-demo-001",
    "tenant_id": 1,
    "tenant": "Kaveri Textiles & Crafts",
    "tenant_name": "Kaveri Textiles & Crafts",
    "source_type": "upload",
    "current_stage": "gold",
    "status": "success",
    "rejection_count": 6,
    "started_at": "2026-10-19T12:00:00Z",
    "updated_at": "2026-10-19T12:05:00Z",
    "stage_history": [
        {"stage": "bronze_ingest", "status": "completed", "duration_seconds": 2.1, "row_count": 266},
        {"stage": "silver_clean", "status": "completed", "duration_seconds": 3.4, "row_count": 260},
        {"stage": "gold_transform", "status": "completed", "duration_seconds": 1.8, "row_count": 260},
    ],
    "audit_logs": [],
}

mock_run_without_rejections = {
    "batch_id": "batch-clean-no-rejections-002",
    "tenant_id": 1,
    "tenant": "Kaveri Textiles & Crafts",
    "tenant_name": "Kaveri Textiles & Crafts",
    "source_type": "upload",
    "current_stage": "gold",
    "status": "success",
    "rejection_count": 0,
    "started_at": "2026-10-19T11:00:00Z",
    "updated_at": "2026-10-19T11:04:00Z",
    "stage_history": [
        {"stage": "bronze_ingest", "status": "completed", "duration_seconds": 1.5, "row_count": 100},
        {"stage": "silver_clean", "status": "completed", "duration_seconds": 2.0, "row_count": 100},
        {"stage": "gold_transform", "status": "completed", "duration_seconds": 1.2, "row_count": 100},
    ],
    "audit_logs": [],
}

mock_organizations = [
    {"tenant_id": 1, "business_name": "Kaveri Textiles & Crafts", "is_active": True},
    {"tenant_id": 2, "business_name": "Malabar Spices & Oils", "is_active": True},
]


async def send_cmd(ws, msg_id, method, params=None):
    payload = {'id': msg_id, 'method': method, 'params': params or {}}
    await ws.send(json.dumps(payload))
    while True:
        resp = json.loads(await ws.recv())
        if resp.get('id') == msg_id:
            return resp


async def eval_expr(ws, msg_id, expr):
    res = await send_cmd(ws, msg_id, 'Runtime.evaluate', {'expression': expr, 'returnByValue': True})
    return res.get('result', {}).get('result', {}).get('value')


async def capture_screenshot(ws, msg_id, filename):
    shot = await send_cmd(ws, msg_id, 'Page.captureScreenshot', {'format': 'png'})
    img_data = base64.b64decode(shot['result']['data'])
    path = os.path.join(ARTIFACT_DIR, filename)
    with open(path, 'wb') as f:
        f.write(img_data)
    print(f"Captured screenshot: {filename} ({len(img_data)} bytes)")
    return path


async def main():
    temp_dir = tempfile.mkdtemp(prefix="helios_proof_")
    chrome_proc = subprocess.Popen([
        CHROME_PATH,
        '--headless',
        '--remote-debugging-port=9227',
        f'--user-data-dir={temp_dir}',
        '--disable-gpu',
        '--no-first-run',
        '--no-default-browser-check',
        '--window-size=1440,900',
        'about:blank',
    ])
    time.sleep(2)

    try:
        with urllib.request.urlopen('http://127.0.0.1:9227/json') as resp:
            tabs = json.loads(resp.read().decode())
        page_tabs = [t for t in tabs if t.get('type') == 'page']
        ws_url = page_tabs[0]['webSocketDebuggerUrl']

        async with websockets.connect(ws_url, max_size=30 * 1024 * 1024) as ws:
            # Enable domains
            await send_cmd(ws, 1, 'Page.enable')
            await send_cmd(ws, 2, 'Runtime.enable')
            await send_cmd(ws, 3, 'Fetch.enable', {
                'patterns': [{'urlPattern': '*api*', 'requestStage': 'Request'}]
            })

            # Task loop for handling Fetch requests
            async def handle_fetch(msg):
                if msg.get('method') == 'Fetch.requestPaused':
                    req_id = msg['params']['requestId']
                    url = msg['params']['request']['url']
                    status_code = 200
                    body = None

                    if "/data-quality/logs" in url:
                        body = json.dumps(mock_dq_logs)
                    elif "/tenants" in url or "/organizations" in url:
                        body = json.dumps(mock_organizations)
                    elif "/pipeline/runs/batch-org1-orders-demo-001" in url:
                        body = json.dumps(mock_run_with_rejections)
                    elif "/pipeline/runs/batch-clean-no-rejections-002" in url:
                        body = json.dumps(mock_run_without_rejections)
                    elif "/pipeline/runs" in url:
                        body = json.dumps(mock_pipeline_runs)

                    if body is not None:
                        headers = [
                            {'name': 'Content-Type', 'value': 'application/json'},
                            {'name': 'Access-Control-Allow-Origin', 'value': '*'},
                        ]
                        b64_body = base64.b64encode(body.encode('utf-8')).decode('utf-8')
                        fulfill_payload = {
                            'requestId': req_id,
                            'responseCode': status_code,
                            'responseHeaders': headers,
                            'body': b64_body,
                        }
                        await ws.send(json.dumps({'id': 9999, 'method': 'Fetch.fulfillRequest', 'params': fulfill_payload}))
                    else:
                        await ws.send(json.dumps({'id': 9999, 'method': 'Fetch.continueRequest', 'params': {'requestId': req_id}}))

            # Helper for receiving while processing fetch requests
            async def send_cmd_with_fetch(cmd_id, method, params=None):
                payload = {'id': cmd_id, 'method': method, 'params': params or {}}
                await ws.send(json.dumps(payload))
                while True:
                    raw = await ws.recv()
                    data = json.loads(raw)
                    if data.get('method') == 'Fetch.requestPaused':
                        await handle_fetch(data)
                    elif data.get('id') == cmd_id:
                        return data

            # Establish session origin
            await send_cmd_with_fetch(10, 'Page.navigate', {'url': 'http://localhost:5173/login'})
            await asyncio.sleep(1)

            # Inject Admin auth
            script = f"""
            localStorage.setItem('helios_token', '{admin_token}');
            localStorage.setItem('helios_user', JSON.stringify({json.dumps(admin_user)}));
            localStorage.removeItem('helios_tenant_id');
            """
            await send_cmd_with_fetch(11, 'Runtime.evaluate', {'expression': script})

            # -------------------------------------------------------------
            # Screenshot 1: Data Quality Log Table with "Download rejected rows" button on rows
            # -------------------------------------------------------------
            print("\n--- Capturing Data Quality Log Table ---")
            await send_cmd_with_fetch(20, 'Page.navigate', {'url': 'http://localhost:5173/admin/data-quality'})

            # Pump fetch events for 2.5 seconds
            t_end = time.time() + 3.0
            while time.time() < t_end:
                try:
                    raw = await asyncio.wait_for(ws.recv(), timeout=0.2)
                    data = json.loads(raw)
                    if data.get('method') == 'Fetch.requestPaused':
                        await handle_fetch(data)
                except asyncio.TimeoutError:
                    pass

            await capture_screenshot(ws, 25, 'data_quality_row_with_download_button.png')

            # Verify visible button text
            btn_texts = await eval_expr(ws, 26, 'Array.from(document.querySelectorAll("button")).map(b => b.textContent.trim()).filter(t => t.includes("Download rejected"))')
            print(f"  Found '{len(btn_texts)}' Download rejected rows buttons on page: {btn_texts[:2]}")
            assert len(btn_texts) > 0, "Download rejected rows button not visible on Data Quality table!"

            # -------------------------------------------------------------
            # Screenshot 2: Data Quality Modal with "Download rejected rows" button
            # -------------------------------------------------------------
            print("\n--- Clicking Data Quality row to open detail modal ---")
            await send_cmd_with_fetch(30, 'Runtime.evaluate', {'expression': 'document.querySelector("tbody tr").click()'})
            await asyncio.sleep(1.0)
            await capture_screenshot(ws, 35, 'data_quality_modal_with_download_button.png')

            # Close modal
            await send_cmd_with_fetch(36, 'Runtime.evaluate', {'expression': 'document.querySelector(".fixed button").click()'})
            await asyncio.sleep(0.5)

            # -------------------------------------------------------------
            # Screenshot 3: Pipeline Health Run Detail View WITH Rejections (Button shown)
            # -------------------------------------------------------------
            print("\n--- Capturing Pipeline Health Run Detail View (WITH rejections) ---")
            await send_cmd_with_fetch(40, 'Page.navigate', {'url': 'http://localhost:5173/admin/pipeline-health'})

            # Pump fetch events for 3.0 seconds
            t_end = time.time() + 3.0
            while time.time() < t_end:
                try:
                    raw = await asyncio.wait_for(ws.recv(), timeout=0.2)
                    data = json.loads(raw)
                    if data.get('method') == 'Fetch.requestPaused':
                        await handle_fetch(data)
                except asyncio.TimeoutError:
                    pass

            # Click on the first run (batch-org1-orders-demo-001 which has rejections)
            print("  Clicking run batch-org1-orders-demo-001 (rejection_count = 6)...")
            await send_cmd_with_fetch(45, 'Runtime.evaluate', {'expression': 'document.querySelectorAll("tbody tr")[0].click()'})

            # Pump fetch events for detail load
            t_end = time.time() + 2.5
            while time.time() < t_end:
                try:
                    raw = await asyncio.wait_for(ws.recv(), timeout=0.2)
                    data = json.loads(raw)
                    if data.get('method') == 'Fetch.requestPaused':
                        await handle_fetch(data)
                except asyncio.TimeoutError:
                    pass

            await capture_screenshot(ws, 50, 'pipeline_run_detail_with_rejections.png')

            detail_btns = await eval_expr(ws, 51, 'Array.from(document.querySelectorAll("button")).map(b => b.textContent.trim()).filter(t => t.includes("Download rejected"))')
            print(f"  Visible Download rejected rows buttons in detail view: {detail_btns}")
            assert len(detail_btns) > 0, "Download rejected rows button MUST be visible on run detail view with rejections!"

            # Close modal
            await send_cmd_with_fetch(52, 'Runtime.evaluate', {'expression': 'document.querySelector("div.fixed button").click()'})
            await asyncio.sleep(0.5)

            # -------------------------------------------------------------
            # Screenshot 4: Pipeline Health Run Detail View WITHOUT Rejections (Button NOT shown)
            # -------------------------------------------------------------
            print("\n--- Capturing Pipeline Health Run Detail View (WITHOUT rejections) ---")
            # Click on second run (batch-clean-no-rejections-002 which has 0 rejections)
            await send_cmd_with_fetch(60, 'Runtime.evaluate', {'expression': 'document.querySelectorAll("tbody tr")[1].click()'})

            # Pump fetch events for detail load
            t_end = time.time() + 2.5
            while time.time() < t_end:
                try:
                    raw = await asyncio.wait_for(ws.recv(), timeout=0.2)
                    data = json.loads(raw)
                    if data.get('method') == 'Fetch.requestPaused':
                        await handle_fetch(data)
                except asyncio.TimeoutError:
                    pass

            await capture_screenshot(ws, 65, 'pipeline_run_detail_without_rejections.png')

            no_detail_btns = await eval_expr(ws, 66, 'Array.from(document.querySelectorAll("button")).map(b => b.textContent.trim()).filter(t => t.includes("Download rejected"))')
            print(f"  Download rejected rows buttons on zero-rejection run: {no_detail_btns}")
            assert len(no_detail_btns) == 0, "Download rejected rows button MUST NOT be visible on zero-rejection run!"
            print("  Verified: Button is hidden when batch has 0 rejections!")

            print("\n" + "=" * 80)
            print("ALL PROOF SCREENSHOTS CAPTURED AND UI ASSERTIONS VERIFIED!")
            print("=" * 80)
    finally:
        chrome_proc.terminate()
        try:
            shutil.rmtree(temp_dir, ignore_errors=True)
        except Exception:
            pass

if __name__ == "__main__":
    asyncio.run(main())

