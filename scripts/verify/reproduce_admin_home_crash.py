import asyncio
import json
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
    page_errors = []

    # Mock response where tables or lists were converted to paginated { items, total } objects
    # as happened in Step 3!
    paginated_mock_oversight_home = {
        "summary": {
            "organizations_active": 10,
            "organizations_inactive": 0,
            "organizations_total": 10,
            "organization_owners_active": 10,
            "team_members": 2,
            "pending_uploads": 3,
            "running_pipelines": 0,
            "failed_pipelines": 1,
            "open_support_messages": 2,
        },
        "charts": {
            "revenue_by_organization": [
                {"tenant_id": 1, "organization_name": "Acme Retailers", "total_revenue": 500000.0}
            ],
            "pipeline_runs_per_day": [
                {"date": "2026-11-01", "successful_runs": 5, "failed_runs": 1, "total_runs": 6}
            ],
        },
        "tables": {
            # In Step 3, list endpoints were converted to return { items: [...], total: ... }
            "organizations": {
                "items": [
                    {
                        "tenant_id": 1,
                        "name": "Acme Retailers",
                        "owner": "Rajesh Sharma",
                        "assigned_team_member": "Operations Specialist",
                        "last_data_received": "2026-11-01",
                        "is_active": True,
                    }
                ],
                "total": 1,
                "page": 1,
                "page_size": 10,
            },
            "recent_activity": {
                "items": [
                    {
                        "batch_id": "test-batch-uuid",
                        "tenant_id": 1,
                        "tenant_name": "Acme Retailers",
                        "stage": "gold_transform",
                        "status": "success",
                        "error_message": None,
                        "timestamp": "2026-11-01T10:00:00Z",
                    }
                ],
                "total": 1,
                "page": 1,
                "page_size": 10,
            },
        },
    }

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        page.on("console", lambda msg: console_logs.append(f"[{msg.type}] {msg.text}"))
        page.on("pageerror", lambda err: page_errors.append(str(err)))

        # Intercept /api/v1/oversight/home and return the paginated response
        async def handle_oversight(route):
            await route.fulfill(
                status=200,
                content_type="application/json",
                body=json.dumps(paginated_mock_oversight_home),
            )

        await page.route("**/api/v1/oversight/home*", handle_oversight)

        # Set localStorage
        await page.goto("http://localhost:5173/login")
        await page.evaluate(f"""() => {{
            localStorage.setItem('helios_token', '{admin_token}');
            localStorage.setItem('helios_user', JSON.stringify({json.dumps(admin_user)}));
            localStorage.removeItem('helios_tenant_id');
        }}""")

        # Navigate to /admin/home
        print("Navigating to http://localhost:5173/admin/home with Step 3 paginated response...")
        await page.goto("http://localhost:5173/admin/home", wait_until="networkidle")
        await page.wait_for_timeout(2000)

        artifact_path = r"C:\Users\heetd\.gemini\antigravity\brain\ecd7e94d-17b3-4f8f-933e-1f86a6e1c66b\admin_home_crash.png"
        await page.screenshot(path=artifact_path, full_page=True)

        print("\n--- Uncaught Page Errors ---")
        for err in page_errors:
            print("CRASH:", err)

        print("\n--- Console Logs (Error level) ---")
        for l in console_logs:
            if "[error]" in l:
                print(l)

        # Check DOM contents
        body_text = await page.inner_text("body")
        print(f"\nBody text length: {len(body_text.strip())}")
        if len(body_text.strip()) == 0:
            print("THE SCREEN IS COMPLETELY BLANK / BLACK!")
        else:
            print(f"Body text:\n{body_text[:400]}")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
