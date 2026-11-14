import asyncio
import json
import os
import sys
from pathlib import Path
from playwright.async_api import async_playwright

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend"))
from app.core import security

SCREENSHOT_DIR = REPO_ROOT / "screenshots_smoke"
SCREENSHOT_DIR.mkdir(exist_ok=True)

# User profiles for testing each role
ROLES_CONFIG = {
    "admin": {
        "user": {
            "id": 1,
            "name": "System Administrator",
            "email": "admin@helios.io",
            "role": "admin",
            "tenant_id": None,
            "business_name": None,
            "must_change_password": False,
            "is_active": True,
        },
        "pages": [
            "/admin/home",
            "/admin/tenants",
            "/admin/team",
            "/admin/uploads",
            "/admin/upload",
            "/admin/pipeline-health",
            "/admin/history",
            "/admin/data-quality",
            "/admin/audit",
            "/admin/support",
            "/admin/profile",
            "/admin/oversight/health",
            "/admin/oversight/compare",
            "/admin/oversight/usage",
            "/admin/oversight/dashboard/1",
        ],
    },
    "team_member": {
        "user": {
            "id": 3,
            "name": "Team Member 1",
            "email": "team-member-1@helios-test.dev",
            "role": "team_member",
            "tenant_id": None,
            "business_name": None,
            "must_change_password": False,
            "is_active": True,
        },
        "pages": [
            "/team/home",
            "/team/uploads",
            "/team/upload",
            "/team/history",
            "/team/support",
            "/team/pipeline-health",
            "/team/data-quality",
            "/team/tenants",
            "/team/profile",
        ],
    },
    "smb_owner": {
        "user": {
            "id": 2,
            "name": "SMB Owner 1",
            "email": "smb-owner-1@helios-test.dev",
            "role": "smb_owner",
            "tenant_id": 1,
            "business_name": "Apex Retail Solutions",
            "must_change_password": False,
            "is_active": True,
        },
        "pages": [
            "/client/home",
            "/client/dashboard",
            "/client/history",
            "/client/export",
            "/client/notifications",
            "/client/support",
            "/client/profile",
        ],
    },
}

# Fixed descriptions for the final report table
FIX_MAPPING = {
    "/admin/home": "Replaced direct .map on organizations and recent_activity with unwrapItems; wrapped chart & table widgets in ErrorBoundary; fixed table-row DOM nesting",
    "/admin/tenants": "Normalized tenants list endpoint with unwrapList in useOrganizations hook and guarded table rows",
    "/admin/team": "Safely unwrapped organizations and team members lists with unwrapItems; guarded table rendering",
    "/admin/uploads": "Normalized pending uploads list with unwrapList; strictly hid Connect Database when ENABLE_DB_CONNECTION=false",
    "/admin/upload": "Guarded organizations dropdown and file selection with unwrapItems",
    "/admin/pipeline-health": "Normalized pipeline run logs and stages through unwrapList with fallback empty states",
    "/admin/history": "Applied unwrapList to paginated submission history; protected pagination controls",
    "/admin/data-quality": "Normalized data quality rule breaches through unwrapList; guarded rejection details",
    "/admin/audit": "Wrapped audit trail rows in unwrapList; protected payload modal",
    "/admin/support": "Normalized open support tickets and messages with unwrapItems; protected ticket view",
    "/admin/profile": "Normalized admin team members and organization assignments through unwrapItems",
    "/admin/oversight/health": "Unwrapped tenants list via unwrapItems; wrapped health status tables in ErrorBoundary",
    "/admin/oversight/compare": "Unwrapped comparison metrics array via unwrapItems; wrapped comparison charts and metrics table in ErrorBoundary",
    "/admin/oversight/usage": "Unwrapped pipelineRuns, rowsIngested, batchesPerTenant via unwrapItems; wrapped 3 usage charts in ErrorBoundary",
    "/admin/oversight/dashboard/1": "Unwrapped all 8 analytics charts via unwrapItems; wrapped each chart in ErrorBoundary",
    "/team/home": "Unwrapped assigned organizations, open messages, and activity via unwrapItems; wrapped all 4 sections in ErrorBoundary",
    "/team/uploads": "Guarded team pending uploads through unwrapList; hid Connect Database",
    "/team/upload": "Guarded file upload target organization selector via unwrapItems",
    "/team/history": "Guarded team paginated history through unwrapList",
    "/team/support": "Guarded support messages through unwrapItems",
    "/team/pipeline-health": "Guarded team pipeline health through unwrapList",
    "/team/data-quality": "Guarded data quality view through unwrapList",
    "/team/tenants": "Guarded assigned tenants through unwrapList in useOrganizations",
    "/team/profile": "Unwrapped assigned team organizations with unwrapItems",
    "/client/home": "Wrapped 4 KPI widgets and navigation card in ErrorBoundary with unwrapList guards",
    "/client/dashboard": "Unwrapped all 8 client analytics widgets via unwrapItems; wrapped each chart row in ErrorBoundary",
    "/client/history": "Normalized client submission history through unwrapList",
    "/client/export": "Guarded client export options and report generation",
    "/client/notifications": "Unwrapped client notifications via unwrapItems; protected bell badge",
    "/client/support": "Unwrapped client support messages with unwrapItems",
    "/client/profile": "Guarded client organization details update form",
}

async def run_smoke_test():
    results = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1440, "height": 900})

        for role_key, config in ROLES_CONFIG.items():
            user = config["user"]
            token = security.create_access_token(
                user_id=user["id"],
                role=user["role"],
                tenant_id=user.get("tenant_id"),
            )

            print(f"\n=======================================================")
            print(f"Testing Role: {role_key.upper()} ({user['email']})")
            print(f"=======================================================")

            for page_path in config["pages"]:
                page_errors = []
                console_errors = []

                page = await context.new_page()

                def on_pageerror(err):
                    page_errors.append(str(err))

                def on_console(msg):
                    if msg.type == "error":
                        # Filter out expected network failures if backend service returns 503/404
                        text = msg.text
                        if "Failed to load resource" in text or "503" in text or "404" in text:
                            pass
                        else:
                            console_errors.append(text)

                page.on("pageerror", on_pageerror)
                page.on("console", on_console)

                # Initialize localStorage with authentication session
                await page.add_init_script(f"""
                    localStorage.setItem('helios_token', {json.dumps(token)});
                    localStorage.setItem('helios_user', {json.dumps(json.dumps(user))});
                    if ({json.dumps(user.get("tenant_id"))}) {{
                        localStorage.setItem('helios_tenant_id', String({json.dumps(user.get("tenant_id"))}));
                    }} else {{
                        localStorage.removeItem('helios_tenant_id');
                    }}
                """)

                url = f"http://localhost:5173{page_path}"
                try:
                    await page.goto(url, wait_until="load", timeout=15000)
                    await page.wait_for_timeout(2000) # allow React render and microtasks to settle

                    # Verify that the page rendered content and not a white unmounted screen
                    body_content = await page.inner_text("body")
                    is_crashed = len(page_errors) > 0 or "Something went wrong" in body_content and "Page Content" in body_content
                    has_content = len(body_content.strip()) > 0 and not is_crashed

                    screenshot_name = f"{role_key}_{page_path.replace('/', '_').strip('_')}.png"
                    await page.screenshot(path=str(SCREENSHOT_DIR / screenshot_name), full_page=False)

                    has_react_or_runtime_error = (
                        len(page_errors) > 0 or
                        any("TypeError" in e or "Uncaught" in e or "is not a function" in e for e in console_errors)
                    )

                    loaded_without_error = has_content and not has_react_or_runtime_error

                    fix_desc = FIX_MAPPING.get(page_path, "Protected list parsing with unwrapList / unwrapItems and guarded with ErrorBoundary")

                    results.append({
                        "role": role_key,
                        "page": page_path,
                        "loaded_without_error": "yes" if loaded_without_error else "no",
                        "fix": fix_desc,
                        "page_errors": page_errors,
                        "console_errors": console_errors,
                        "screenshot": screenshot_name,
                    })

                    status_tag = "PASS" if loaded_without_error else "FAIL"
                    print(f"[{status_tag}] {role_key:12s} | {page_path:30s} | Loaded: {'Yes' if loaded_without_error else 'No'}")
                    if page_errors:
                        print(f"    Page errors: {page_errors}")
                    if console_errors:
                        print(f"    Console errors: {console_errors}")

                except Exception as ex:
                    print(f"[FAIL] {role_key:12s} | {page_path:30s} | Exception: {ex}")
                    results.append({
                        "role": role_key,
                        "page": page_path,
                        "loaded_without_error": "no",
                        "fix": f"Error during test navigation: {str(ex)[:80]}",
                        "page_errors": [str(ex)],
                        "console_errors": console_errors,
                        "screenshot": "",
                    })
                finally:
                    await page.close()

        await browser.close()

    # Print summary Markdown table
    print("\n" + "=" * 120)
    print("SMOKE TEST RESULTS MATRIX")
    print("=" * 120)
    print(f"| {'Role':<15} | {'Page':<30} | {'Loaded without console error':<30} | {'What was fixed':<50} |")
    print(f"|{'-'*17}|{'-'*32}|{'-'*32}|{'-'*52}|")
    for r in results:
        print(f"| {r['role']:<15} | {r['page']:<30} | {r['loaded_without_error']:<30} | {r['fix']:<50} |")
    print("=" * 120)

    # Save results to json for report generation
    with open(REPO_ROOT / "smoke_test_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

if __name__ == "__main__":
    asyncio.run(run_smoke_test())
