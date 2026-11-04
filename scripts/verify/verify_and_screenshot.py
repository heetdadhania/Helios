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


async def run_scenario(ws, role, navigate_to, screenshot_name, expect_redirect=None):
    msg_id = int(time.time() * 1000) % 100000

    # 1. First navigate to login to establish origin for localStorage
    msg_id += 1
    await send_cmd(ws, msg_id, 'Page.navigate', {'url': 'http://localhost:5173/login'})
    await asyncio.sleep(1)

    # 2. Inject localStorage
    u = users[role]
    tok = tokens[role]
    script = f"""
    localStorage.setItem('helios_token', '{tok}');
    localStorage.setItem('helios_user', JSON.stringify({json.dumps(u)}));
    if ({json.dumps(u.get('tenant_id'))}) {{
        localStorage.setItem('helios_tenant_id', '{u.get("tenant_id")}');
    }} else {{
        localStorage.removeItem('helios_tenant_id');
    }}
    """
    msg_id += 1
    await eval_expr(ws, msg_id, script)

    # 3. Navigate to target URL
    msg_id += 1
    target_url = f'http://localhost:5173{navigate_to}'
    await send_cmd(ws, msg_id, 'Page.navigate', {'url': target_url})

    # 4. Wait for page load and any client redirects
    await asyncio.sleep(2.5)

    # 5. Check current URL and sidebar links
    msg_id += 1
    curr_url = await eval_expr(ws, msg_id, 'window.location.href')
    msg_id += 1
    links = await eval_expr(ws, msg_id, 'Array.from(document.querySelectorAll("aside a")).map(e => e.textContent.trim())')
    print(f"[{role}] Target: {navigate_to} -> Landed: {curr_url}")
    print(f"  Sidebar links: {links}")

    if expect_redirect:
        assert expect_redirect in curr_url, f"Expected redirect to contain '{expect_redirect}', got '{curr_url}'"
        print(f"  Verified redirect: {navigate_to} -> {curr_url}")

    # 6. Capture full screenshot
    msg_id += 1
    shot_resp = await send_cmd(ws, msg_id, 'Page.captureScreenshot', {'format': 'png'})
    img_data = base64.b64decode(shot_resp['result']['data'])

    out_path = os.path.join(ARTIFACT_DIR, screenshot_name)
    with open(out_path, 'wb') as f:
        f.write(img_data)
    print(f"  Saved screenshot to: {out_path} ({len(img_data)} bytes)")
    return curr_url, links


async def main():
    temp_dir = tempfile.mkdtemp(prefix='helios_chrome_')
    chrome_proc = subprocess.Popen([
        CHROME_PATH,
        '--headless',
        '--remote-debugging-port=9225',
        f'--user-data-dir={temp_dir}',
        '--disable-gpu',
        '--no-first-run',
        '--no-default-browser-check',
        '--window-size=1440,900',
        'about:blank',
    ])
    time.sleep(2)

    try:
        with urllib.request.urlopen('http://127.0.0.1:9225/json') as resp:
            tabs = json.loads(resp.read().decode())
        page_tabs = [t for t in tabs if t.get('type') == 'page']
        ws_url = page_tabs[0]['webSocketDebuggerUrl']

        async with websockets.connect(ws_url, max_size=25 * 1024 * 1024) as ws:
            await send_cmd(ws, 1, 'Page.enable')
            await send_cmd(ws, 2, 'Runtime.enable')

            # 1. Admin Sidebar at /admin/home
            print('\n--- 1. Admin Sidebar ---')
            _, admin_links = await run_scenario(ws, 'admin', '/admin/home', 'admin_sidebar.png')
            assert 'Connect Database' not in admin_links, "Admin sidebar must NOT contain 'Connect Database'"

            # 2. Team Member Sidebar at /team/home
            print('\n--- 2. Team Member Sidebar ---')
            _, team_links = await run_scenario(ws, 'team_member', '/team/home', 'team_sidebar.png')
            assert 'Connect Database' not in team_links, "Team Member sidebar must NOT contain 'Connect Database'"

            # 3. Organization Owner Sidebar at /client/home
            print('\n--- 3. Organization Owner Sidebar ---')
            _, owner_links = await run_scenario(ws, 'smb_owner', '/client/home', 'owner_sidebar.png')
            assert 'Connect Database' not in owner_links, "Organization Owner sidebar must NOT contain 'Connect Database'"

            # 4. Admin Old URL Redirect: /admin/connect-db -> /admin/home
            print('\n--- 4. Admin Old URL Redirect ---')
            await run_scenario(ws, 'admin', '/admin/connect-db', 'admin_old_url_redirect.png', expect_redirect='/admin/home')

            # 5. Team Member Old URL Redirect: /team/connect-db -> /team/home
            print('\n--- 5. Team Member Old URL Redirect ---')
            await run_scenario(ws, 'team_member', '/team/connect-db', 'team_old_url_redirect.png', expect_redirect='/team/home')

            # 6. Organization Owner Old URL Redirect: /client/connect-db -> /client/home
            print('\n--- 6. Organization Owner Old URL Redirect ---')
            await run_scenario(ws, 'smb_owner', '/client/connect-db', 'owner_old_url_redirect.png', expect_redirect='/client/home')

            # 7. Admin Pending Uploads Source Filter
            print('\n--- 7. Admin Pending Uploads Source Filter ---')
            await run_scenario(ws, 'admin', '/admin/uploads', 'admin_pending_uploads.png')
            opts = await eval_expr(ws, 9999, 'Array.from(document.querySelectorAll("select option")).map(o => o.textContent.trim())')
            print('  Filter options:', opts)
            assert 'Database Connectors' not in opts and 'Database' not in opts, "Source filter must not contain Database options"

            print('\n' + '=' * 60)
            print('ALL VISIBLE VERIFICATION CHECKS AND SCREENSHOTS PASSED!')
            print('=' * 60)
    finally:
        chrome_proc.terminate()
        try:
            shutil.rmtree(temp_dir, ignore_errors=True)
        except Exception:
            pass


if __name__ == '__main__':
    asyncio.run(main())
