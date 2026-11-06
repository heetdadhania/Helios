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
    print("EXACT TIMING MEASUREMENT & VISIBLE CONTENT EXTRACTION")
    print("=" * 70)

    temp_dir = tempfile.mkdtemp(prefix='helios_timing_')
    chrome_proc = subprocess.Popen([
        CHROME_PATH,
        '--headless=new',
        '--remote-debugging-port=9228',
        f'--user-data-dir={temp_dir}',
        '--disable-gpu',
        '--no-first-run',
        '--no-default-browser-check',
        '--window-size=1440,1600',
        'about:blank',
    ])
    await asyncio.sleep(2.0)

    try:
        with urllib.request.urlopen('http://127.0.0.1:9228/json') as resp:
            tabs = json.loads(resp.read().decode())
        page_tabs = [t for t in tabs if t.get('type') == 'page']
        ws_url = page_tabs[0]['webSocketDebuggerUrl']

        async with websockets.connect(ws_url, max_size=50 * 1024 * 1024) as ws:
            await send_cmd(ws, 1, 'Page.enable')
            await send_cmd(ws, 2, 'Runtime.enable')

            # Inject auth
            await send_cmd(ws, 10, 'Page.navigate', {'url': 'http://localhost:5173/login'})
            await asyncio.sleep(1.0)
            auth_script = f"""
            localStorage.setItem('helios_token', '{owner_token}');
            localStorage.setItem('helios_user', JSON.stringify({json.dumps(owner_user)}));
            localStorage.setItem('helios_tenant_id', '1');
            """
            await eval_expr(ws, 11, auth_script)

            # Warmup run
            print("Warming up page and backend caches...")
            await send_cmd(ws, 12, 'Page.navigate', {'url': 'http://localhost:5173/client/dashboard'})
            await asyncio.sleep(5.0)

            # Measure timing
            print("\nMeasuring warm dashboard load time...")
            t0 = time.perf_counter()
            await send_cmd(ws, 20, 'Page.navigate', {'url': 'http://localhost:5173/client/dashboard'})
            
            # Poll for DOM elements with generous timeout
            t_first_5 = None
            t_all_8 = None
            
            for step in range(50):
                await asyncio.sleep(0.5)
                dom_info = await eval_expr(ws, 30 + step, """
                (() => {
                    const h3s = Array.from(document.querySelectorAll('h3')).map(e => e.textContent.trim());
                    const skeletonPulse = document.querySelectorAll('.rounded-card.animate-pulse').length;
                    
                    const hasFirst5 = h3s.some(t => t.includes('Top Selling')) || h3s.some(t => t.includes('Discount'));
                    const hasAll8 = h3s.some(t => t.includes('Category')) && 
                                    h3s.some(t => t.includes('Segment')) && 
                                    h3s.some(t => t.includes('Month-over-Month'));
                    
                    return { h3s, skeletonPulse, hasFirst5, hasAll8 };
                })()
                """)
                
                if dom_info:
                    h3s = dom_info.get('h3s', [])
                    skeletonPulse = dom_info.get('skeletonPulse', 0)
                    hasFirst5 = dom_info.get('hasFirst5', False)
                    hasAll8 = dom_info.get('hasAll8', False)
                    
                    if hasFirst5 and t_first_5 is None:
                        t_first_5 = time.perf_counter() - t0
                        print(f"  [Step {step}] Initial 5 charts ready at: {t_first_5:.3f}s (skeleton cards remaining: {skeletonPulse})")
                    
                    if hasAll8 and skeletonPulse == 0:
                        t_all_8 = time.perf_counter() - t0
                        print(f"  [Step {step}] All 8 charts fully rendered at: {t_all_8:.3f}s (skeleton cards remaining: 0)")
                        break

            print(f"\nWarm Dashboard Load Time (Initial 5 charts): {t_first_5:.3f}s" if t_first_5 else "  t_first_5: N/A")
            print(f"Warm Dashboard Load Time (All 8 charts): {t_all_8:.3f}s" if t_all_8 else "  t_all_8: N/A")
            if t_first_5 and t_all_8:
                diff = t_all_8 - t_first_5
                print(f"Incremental load difference: {diff:.3f}s")

            # Extract detailed visible content for each of the 3 charts
            print("\n>>> Extracting Complete Text of the Three New Charts:")
            charts_detail = await eval_expr(ws, 100, """
            (() => {
                const res = {};
                const cards = Array.from(document.querySelectorAll('.rounded-card'));
                
                cards.forEach(card => {
                    const h3 = card.querySelector('h3');
                    if (!h3) return;
                    const title = h3.textContent.trim();
                    if (title.includes('Category')) {
                        res.category = {
                            title: title,
                            rawText: card.innerText.trim()
                        };
                    } else if (title.includes('Customer Segment')) {
                        res.segment = {
                            title: title,
                            rawText: card.innerText.trim()
                        };
                    } else if (title.includes('Month-over-Month')) {
                        res.monthly = {
                            title: title,
                            rawText: card.innerText.trim()
                        };
                    }
                });
                
                return res;
            })()
            """)
            print(json.dumps(charts_detail, indent=2))

            # Take high-resolution screenshot focused on the three new charts
            await eval_expr(ws, 101, """
            (() => {
                const catH3 = Array.from(document.querySelectorAll('h3')).find(e => e.textContent.includes('Category'));
                if (catH3) {
                    catH3.closest('.rounded-card').scrollIntoView({ behavior: 'instant', block: 'start' });
                }
            })()
            """)
            await asyncio.sleep(0.5)

            shot = await send_cmd(ws, 102, 'Page.captureScreenshot', {'format': 'png'})
            img_data = base64.b64decode(shot['result']['data'])
            out_file = os.path.join(ARTIFACT_DIR, 'three_new_dashboard_charts_proof.png')
            with open(out_file, 'wb') as f:
                f.write(img_data)
            print(f"\nSaved proof screenshot to: {out_file} ({len(img_data)} bytes)")

    finally:
        chrome_proc.terminate()
        try:
            chrome_proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            chrome_proc.kill()
        shutil.rmtree(temp_dir, ignore_errors=True)

if __name__ == '__main__':
    asyncio.run(main())
