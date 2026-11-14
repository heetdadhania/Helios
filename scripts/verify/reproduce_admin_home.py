import asyncio
import json
import os
import sys
from pathlib import Path
from playwright.async_api import async_playwright

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend"))
from app.core import security

async def main():
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
        tenant_id=admin_user['tenant_id'],
    )

    console_logs = []
    errors = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        page.on("console", lambda msg: console_logs.append(f"[{msg.type}] {msg.text}"))
        page.on("pageerror", lambda err: errors.append(str(err)))

        # Navigate to login to set localStorage on origin
        await page.goto("http://localhost:5173/login")
        await page.evaluate(f"""() => {{
            localStorage.setItem('helios_token', '{admin_token}');
            localStorage.setItem('helios_user', JSON.stringify({json.dumps(admin_user)}));
            localStorage.removeItem('helios_tenant_id');
        }}""")

        # Navigate to /admin/home
        print("Navigating to http://localhost:5173/admin/home ...")
        await page.goto("http://localhost:5173/admin/home", wait_until="networkidle")
        await page.wait_for_timeout(3000)

        artifact_path = r"C:\Users\heetd\.gemini\antigravity\brain\ecd7e94d-17b3-4f8f-933e-1f86a6e1c66b\admin_home_reproduce.png"
        await page.screenshot(path=artifact_path, full_page=True)
        print(f"Screenshot saved to {artifact_path}")

        print("\n--- Console logs ---")
        for log in console_logs:
            print(log)

        print("\n--- Page Errors / Uncaught Exceptions ---")
        if not errors:
            print("No uncaught page errors detected.")
        else:
            for err in errors:
                print("ERROR:", err)

        # Check DOM contents
        html_title = await page.title()
        body_text = await page.inner_text("body")
        print(f"\nDocument Title: {html_title}")
        print(f"Body text snippet (first 300 chars):\n{body_text[:300]}")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
