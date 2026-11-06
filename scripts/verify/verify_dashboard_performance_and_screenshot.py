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

sys.path.insert(0, os.path.abspath('backend'))
from dotenv import load_dotenv
load_dotenv('backend/.env')

from app.core import security

ARTIFACT_DIR = r"C:\Users\heetd\.gemini\antigravity\brain\ecd7e94d-17b3-4f8f-933e-1f86a6e1c66b"
CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

owner_user = {
    'id': 6,
    'name': 'Rajesh Patel',
    'email': 'smb-owner-1@helios-test.dev',
    'role': 'smb_owner',
    'tenant_id': 1,
    'business_name': 'Kaveri Textiles & Crafts',
    'must_change_password': False,
}

owner_token = security.create_access_token(
    user_id=owner_user['id'],
    role=owner_user['role'],
    tenant_id=owner_user['tenant_id'],
)

admin_user = {
    'id': 1,
    'name': 'System Administrator',
    'email': 'admin@helios.io',
    'role': 'admin',
    'tenant_id': None,
    'business_name': None,
    'must_change_password': False,
}

admin_token = security.create_access_token(
    user_id=admin_user['id'],
    role=admin_user['role'],
    tenant_id=None,
)

async def send_cmd(ws, msg_id, method, params=None):
    payload = {'id': msg_id, 'method': method, 'params': params or {}}
    await ws.send(json.dumps(payload))
    while True:
        resp = json.loads(await ws.recv())
        if resp.get('id') == msg_id:
            return resp

async def eval_expr(ws, msg_id, expr):
    res = await send_cmd(ws, msg_id, 'Runtime.evaluate', {
        'expression': expr,
        'returnByValue': True,
        'awaitPromise': True,
    })
    return res.get('result', {}).get('result', {}).get('value')

async def main():
    print("=" * 70)
    print("VERIFICATION & PROOF: ORGANISATION OWNER & ADMIN VIEW-AS DASHBOARDS")
    print("=" * 70)

    temp_dir = tempfile.mkdtemp(prefix='helios_dash_proof_')
    chrome_proc = subprocess.Popen([
        CHROME_PATH,
        '--headless=new',
        '--remote-debugging-port=9227',
        f'--user-data-dir={temp_dir}',
        '--disable-gpu',
        '--no-first-run',
        '--no-default-browser-check',
        '--window-size=1440,1800',
        'about:blank',
    ])
    await asyncio.sleep(2.0)

    try:
        with urllib.request.urlopen('http://127.0.0.1:9227/json') as resp:
            tabs = json.loads(resp.read().decode())
        page_tabs = [t for t in tabs if t.get('type') == 'page']
        ws_url = page_tabs[0]['webSocketDebuggerUrl']

        async with websockets.connect(ws_url, max_size=50 * 1024 * 1024) as ws:
            await send_cmd(ws, 1, 'Page.enable')
            await send_cmd(ws, 2, 'Runtime.enable')

            # -----------------------------------------------------------------
            # 1. Warm Dashboard Performance Measurement
            # -----------------------------------------------------------------
            print("\n>>> Navigating to Organization Owner Dashboard (/client/dashboard)...")
            # Navigate to login to set localStorage
            await send_cmd(ws, 10, 'Page.navigate', {'url': 'http://localhost:5173/login'})
            await asyncio.sleep(1.0)

            auth_script = f"""
            localStorage.setItem('helios_token', '{owner_token}');
            localStorage.setItem('helios_user', JSON.stringify({json.dumps(owner_user)}));
            localStorage.setItem('helios_tenant_id', '1');
            """
            await eval_expr(ws, 11, auth_script)

            # Warm run 1 (populate caches/connection pool)
            print("  Warming connection and caches...")
            t_nav_start = time.perf_counter()
            await send_cmd(ws, 12, 'Page.navigate', {'url': 'http://localhost:5173/client/dashboard'})
            
            # Wait for all widgets to settle
            t_first_5_done = None
            t_all_done = None
            for i in range(40):
                await asyncio.sleep(0.5)
                status = await eval_expr(ws, 21 + i, """
                (() => {
                    const h3s = Array.from(document.querySelectorAll('h3')).map(e => e.textContent.trim());
                    const hasTrend = document.querySelector('.recharts-responsive-container') !== null;
                    const hasPulse = document.querySelectorAll('.animate-pulse').length;
                    
                    const hasCat = h3s.some(t => t.includes('Revenue by Product Category'));
                    const hasSeg = h3s.some(t => t.includes('Revenue by Customer Segment'));
                    const hasMoM = h3s.some(t => t.includes('Month-over-Month Revenue'));
                    
                    // Check if first 5 are loaded (Row 1-3 have containers and not pulse)
                    const first5Loaded = h3s.some(t => t.includes('Top Selling Products')) && 
                                         h3s.some(t => t.includes('Late Delivery Risk')) && 
                                         h3s.some(t => t.includes('Discount vs Profit'));
                    
                    const all8Loaded = hasCat && hasSeg && hasMoM && (hasPulse === 0);
                    
                    return {
                        url: window.location.href,
                        title: document.querySelector('h1')?.textContent?.trim(),
                        h3s: h3s,
                        pulseCount: hasPulse,
                        first5Loaded: first5Loaded,
                        all8Loaded: all8Loaded
                    };
                })()
                """)
                
                if status and status.get('first5Loaded') and t_first_5_done is None:
                    t_first_5_done = time.perf_counter() - t_nav_start
                if status and status.get('all8Loaded'):
                    t_all_done = time.perf_counter() - t_nav_start
                    break

            print(f"  Initial 5 charts load duration: {t_first_5_done if t_first_5_done else 'N/A'}s")
            print(f"  All 8 charts full load duration: {t_all_done if t_all_done else 'N/A'}s")
            if t_first_5_done and t_all_done:
                growth = t_all_done - t_first_5_done
                print(f"  Incremental load difference: {growth:.3f}s")

            # -----------------------------------------------------------------
            # 2. Extract Visible Information
            # -----------------------------------------------------------------
            print("\n>>> Extracting Visible Telemetry on Organization Owner Dashboard:")
            visible_info = await eval_expr(ws, 30, """
            (() => {
                const results = {};
                
                // Get page title & subtitle
                results.title = document.querySelector('h1')?.textContent?.trim();
                
                // Find all chart cards
                const cardHeaders = Array.from(document.querySelectorAll('h3')).map(e => e.textContent.trim());
                results.cardHeaders = cardHeaders;
                
                // Extract category revenue items
                const catHeader = Array.from(document.querySelectorAll('h3')).find(e => e.textContent.includes('Revenue by Product Category'));
                if (catHeader) {
                    const card = catHeader.closest('.rounded-card');
                    results.categoryCard = {
                        title: catHeader.textContent.trim(),
                        badge: card?.querySelector('span.rounded-full')?.textContent?.trim(),
                        items: Array.from(card?.querySelectorAll('.space-y-1\\.5 > div') || []).map(r => r.textContent.trim())
                    };
                }
                
                // Extract customer segment items
                const segHeader = Array.from(document.querySelectorAll('h3')).find(e => e.textContent.includes('Revenue by Customer Segment'));
                if (segHeader) {
                    const card = segHeader.closest('.rounded-card');
                    results.segmentCard = {
                        title: segHeader.textContent.trim(),
                        badge: card?.querySelector('span.rounded-full')?.textContent?.trim(),
                        legend: Array.from(card?.querySelectorAll('.recharts-legend-item-text') || []).map(r => r.textContent.trim()),
                        items: Array.from(card?.querySelectorAll('.space-y-1\\.5 > div') || []).map(r => r.textContent.trim())
                    };
                }
                
                // Extract monthly revenue items
                const monthHeader = Array.from(document.querySelectorAll('h3')).find(e => e.textContent.includes('Month-over-Month Revenue'));
                if (monthHeader) {
                    const card = monthHeader.closest('.rounded-card');
                    results.monthlyCard = {
                        title: monthHeader.textContent.trim(),
                        badge: card?.querySelector('span.rounded-full')?.textContent?.trim(),
                        months: Array.from(card?.querySelectorAll('.grid > div') || []).map(r => r.textContent.trim().replace(/\\s+/g, ' '))
                    };
                }
                
                return results;
            })()
            """)
            print(json.dumps(visible_info, indent=2))

            # -----------------------------------------------------------------
            # 3. Take Proof Screenshots
            # -----------------------------------------------------------------
            print("\n>>> Capturing Proof Screenshots...")
            
            # 3a. Full Owner Dashboard
            shot_full = await send_cmd(ws, 40, 'Page.captureScreenshot', {
                'format': 'png',
                'captureBeyondViewport': True
            })
            img_data = base64.b64decode(shot_full['result']['data'])
            full_path = os.path.join(ARTIFACT_DIR, 'owner_dashboard_full.png')
            with open(full_path, 'wb') as f:
                f.write(img_data)
            print(f"  Saved Full Dashboard Screenshot: {full_path} ({len(img_data)} bytes)")

            # 3b. Scroll down to the 3 new charts and capture focused screenshot
            await eval_expr(ws, 41, """
            (() => {
                const catHeader = Array.from(document.querySelectorAll('h3')).find(e => e.textContent.includes('Revenue by Product Category'));
                if (catHeader) {
                    catHeader.scrollIntoView({ behavior: 'instant', block: 'start' });
                }
            })()
            """)
            await asyncio.sleep(0.5)

            shot_focused = await send_cmd(ws, 42, 'Page.captureScreenshot', {
                'format': 'png',
            })
            img_focused_data = base64.b64decode(shot_focused['result']['data'])
            focused_path = os.path.join(ARTIFACT_DIR, 'owner_dashboard_three_new_charts.png')
            with open(focused_path, 'wb') as f:
                f.write(img_focused_data)
            print(f"  Saved Three New Charts Focused Screenshot: {focused_path} ({len(img_focused_data)} bytes)")

            # -----------------------------------------------------------------
            # 4. Admin View-As Dashboard Verification & Screenshot
            # -----------------------------------------------------------------
            print("\n>>> Verifying Admin View-As Dashboard (/admin/oversight/dashboard/1)...")
            admin_script = f"""
            localStorage.setItem('helios_token', '{admin_token}');
            localStorage.setItem('helios_user', JSON.stringify({json.dumps(admin_user)}));
            localStorage.removeItem('helios_tenant_id');
            """
            await eval_expr(ws, 50, admin_script)

            await send_cmd(ws, 51, 'Page.navigate', {'url': 'http://localhost:5173/admin/oversight/dashboard/1'})
            
            # Wait for admin view to load
            for _ in range(30):
                await asyncio.sleep(0.5)
                is_admin_loaded = await eval_expr(ws, 52, """
                (() => {
                    const categoryChart = Array.from(document.querySelectorAll('h3')).find(e => e.textContent.includes('Revenue by Product Category'));
                    const segmentChart = Array.from(document.querySelectorAll('h3')).find(e => e.textContent.includes('Revenue by Customer Segment'));
                    const monthlyChart = Array.from(document.querySelectorAll('h3')).find(e => e.textContent.includes('Month-over-Month Revenue'));
                    const anyPulse = document.querySelectorAll('.animate-pulse').length;
                    return categoryChart && segmentChart && monthlyChart && (anyPulse === 0);
                })()
                """)
                if is_admin_loaded:
                    break

            admin_visible_info = await eval_expr(ws, 53, """
            (() => {
                return {
                    title: document.querySelector('h1')?.textContent?.trim(),
                    badge: document.querySelector('.inline-flex')?.textContent?.trim(),
                    cardHeaders: Array.from(document.querySelectorAll('h3')).map(e => e.textContent.trim())
                };
            })()
            """)
            print(f"  Admin View-As Landed: {admin_visible_info}")

            # Scroll to the 3 new charts in Admin View
            await eval_expr(ws, 54, """
            (() => {
                const catHeader = Array.from(document.querySelectorAll('h3')).find(e => e.textContent.includes('Revenue by Product Category'));
                if (catHeader) {
                    catHeader.scrollIntoView({ behavior: 'instant', block: 'start' });
                }
            })()
            """)
            await asyncio.sleep(0.5)

            shot_admin = await send_cmd(ws, 55, 'Page.captureScreenshot', {
                'format': 'png',
            })
            img_admin_data = base64.b64decode(shot_admin['result']['data'])
            admin_path = os.path.join(ARTIFACT_DIR, 'admin_view_as_dashboard_org1.png')
            with open(admin_path, 'wb') as f:
                f.write(img_admin_data)
            print(f"  Saved Admin View-As Screenshot: {admin_path} ({len(img_admin_data)} bytes)")

    finally:
        chrome_proc.terminate()
        try:
            chrome_proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            chrome_proc.kill()
        shutil.rmtree(temp_dir, ignore_errors=True)

if __name__ == '__main__':
    asyncio.run(main())
