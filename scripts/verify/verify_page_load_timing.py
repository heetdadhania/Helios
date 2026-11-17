import asyncio
import json
import os
import sys
import time
from dotenv import load_dotenv
from playwright.async_api import async_playwright

sys.path.insert(0, os.path.abspath("backend"))
load_dotenv("backend/.env")
from app.core import security

admin_user = {
    "id": 1,
    "name": "System Administrator",
    "email": "admin@helios.io",
    "role": "admin",
    "tenant_id": None,
    "must_change_password": False,
}
admin_token = security.create_access_token(
    user_id=admin_user["id"],
    role=admin_user["role"],
    tenant_id=admin_user["tenant_id"],
)

owner_user = {
    "id": 6,
    "name": "Rajesh Patel",
    "email": "smb-owner-1@helios-test.dev",
    "role": "smb_owner",
    "tenant_id": 1,
    "business_name": "Kaveri Textiles & Crafts",
    "must_change_password": False,
}
owner_token = security.create_access_token(
    user_id=owner_user["id"],
    role=owner_user["role"],
    tenant_id=owner_user["tenant_id"],
)

async def test_page_warm_timing(playwright, role_name, token, user, page_path, ready_selector):
    print(f"\n[{role_name.upper()}] Measuring warm load time for {page_path}...")
    browser = await playwright.chromium.launch(headless=True)
    context = await browser.new_context()

    # Pre-inject authentication state in localStorage before navigation
    init_script = f"""
        localStorage.setItem('helios_token', {json.dumps(token)});
        localStorage.setItem('helios_user', {json.dumps(json.dumps(user))});
        if ({json.dumps(user.get("tenant_id"))}) {{
            localStorage.setItem('helios_tenant_id', String({json.dumps(user.get("tenant_id"))}));
        }} else {{
            localStorage.removeItem('helios_tenant_id');
        }}
    """
    await context.add_init_script(init_script)

    page = await context.new_page()
    url = f"http://localhost:5173{page_path}"

    # 1. Warmup navigation: execute once to warm frontend bundles, assets, and backend in-memory cache
    print("  1. Performing initial warmup navigation...")
    t_warmup_start = time.perf_counter()
    await page.goto(url, wait_until="networkidle", timeout=30000)
    await page.wait_for_selector(ready_selector, timeout=15000)
    t_warmup = time.perf_counter() - t_warmup_start
    print(f"     Warmup completed in {t_warmup:.2f}s (bundle loaded, cache populated).")

    # 2. Measure Warm Page Load
    print("  2. Measuring warm reload/navigation time...")
    t0 = time.perf_counter()
    await page.reload(wait_until="domcontentloaded", timeout=15000)
    await page.wait_for_selector(ready_selector, timeout=15000)
    t_warm = time.perf_counter() - t0
    print(f"     Warm load time: {t_warm:.3f}s (selector '{ready_selector}' rendered)")

    await browser.close()
    return t_warm

async def main():
    print("=" * 70)
    print("CHECK 10: VERIFY WARM PAGE-LOAD TIMINGS (< 3.0 SECONDS)")
    print("=" * 70)

    async with async_playwright() as playwright:
        # Admin Home: check for presence of main heading or stat card
        t_admin = await test_page_warm_timing(
            playwright,
            "Admin",
            admin_token,
            admin_user,
            "/admin/home",
            "h1:has-text('Admin Home')",
        )

        # SMB Owner Dashboard: check for presence of dashboard card
        t_owner = await test_page_warm_timing(
            playwright,
            "SMB Owner",
            owner_token,
            owner_user,
            "/client/dashboard",
            "h1:has-text('Store Performance & Analytics')",
        )

        print("\n" + "=" * 70)
        print("VERIFICATION RESULTS (THRESHOLD: < 3.000s):")
        print(f"  • Admin Home:      {t_admin:.3f}s -> {'PASS' if t_admin < 3.0 else 'FAIL'}")
        print(f"  • Owner Dashboard: {t_owner:.3f}s -> {'PASS' if t_owner < 3.0 else 'FAIL'}")
        print("=" * 70)

        assert t_admin < 3.0, f"Admin Home warm load time {t_admin:.3f}s exceeded 3.0s threshold!"
        assert t_owner < 3.0, f"Owner Dashboard warm load time {t_owner:.3f}s exceeded 3.0s threshold!"
        print("ALL CHECK 10 REQUIREMENTS STRICTLY MET!")

if __name__ == "__main__":
    asyncio.run(main())
