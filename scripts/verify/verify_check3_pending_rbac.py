import io
import os
import sys
import time
import openpyxl
import requests
from pathlib import Path
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend"))
load_dotenv(REPO_ROOT / ".env")

from app.core.config import settings
from app.db.base import get_databricks_connection

BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000/api/v1")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD")
TEST_ACCOUNT_PASSWORD = os.environ.get("TEST_ACCOUNT_PASSWORD")
CATALOG = getattr(settings, "DATABRICKS_CATALOG", "helios_catalog")

def get_token(email: str, password: str) -> str:
    res = requests.post(f"{BASE_URL}/auth/login", json={"email": email, "password": password})
    if res.status_code != 200:
        raise RuntimeError(f"Login failed for {email}: {res.status_code} {res.text}")
    return res.json()["access_token"]

def create_excel_bytes(rows: list) -> bytes:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Orders"
    for row in rows:
        ws.append(row)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()

def main():
    print("=" * 75)
    print("CHECK 3: SUBMIT CSV & EXCEL FOR AN ORG -> PENDING RBAC VERIFICATION")
    print("=" * 75)

    admin_token = get_token("admin@helios.io", ADMIN_PASSWORD)
    tm1_token = get_token("team-member-1@helios-test.dev", TEST_ACCOUNT_PASSWORD)
    tm2_token = get_token("team-member-2@helios-test.dev", TEST_ACCOUNT_PASSWORD)

    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    tm1_headers = {"Authorization": f"Bearer {tm1_token}"}
    tm2_headers = {"Authorization": f"Bearer {tm2_token}"}

    target_tenant_id = 1
    unique_ts = int(time.time())

    # 1. Prepare CSV Content
    csv_rows = [
        "order_id,customer_id,order_date,product_name,category,quantity,price,total_amount",
        f"ORD-C3-CSV-{unique_ts}-1,CUST-1,2026-03-01,Product A,Category 1,2,500,1000",
        f"ORD-C3-CSV-{unique_ts}-2,CUST-2,2026-03-01,Product B,Category 2,1,750,750",
        f"ORD-C3-CSV-{unique_ts}-3,CUST-3,2026-03-02,Product C,Category 1,3,300,900",
        f"ORD-C3-CSV-{unique_ts}-4,CUST-4,2026-03-02,Product D,Category 3,1,1200,1200",
        f"ORD-C3-CSV-{unique_ts}-5,CUST-5,2026-03-03,Product E,Category 2,2,400,800",
    ]
    csv_bytes = "\n".join(csv_rows).encode("utf-8")

    # 2. Prepare Excel Content
    xlsx_data = [
        ["order_id", "customer_id", "order_date", "product_name", "category", "quantity", "price", "total_amount"],
        [f"ORD-C3-XLSX-{unique_ts}-1", "CUST-1", "2026-03-01", "Product A", "Category 1", 2, 500, 1000],
        [f"ORD-C3-XLSX-{unique_ts}-2", "CUST-2", "2026-03-01", "Product B", "Category 2", 1, 750, 750],
        [f"ORD-C3-XLSX-{unique_ts}-3", "CUST-3", "2026-03-02", "Product C", "Category 1", 3, 300, 900],
        [f"ORD-C3-XLSX-{unique_ts}-4", "CUST-4", "2026-03-02", "Product D", "Category 3", 1, 1200, 1200],
        [f"ORD-C3-XLSX-{unique_ts}-5", "CUST-5", "2026-03-03", "Product E", "Category 2", 2, 400, 800],
    ]
    xlsx_bytes = create_excel_bytes(xlsx_data)

    csv_batch_id = None
    xlsx_batch_id = None
    created_upload_ids = []

    try:
        # Step 1: Submit CSV file by assigned team member
        print("\n--- STEP 1: Submit CSV file for Tenant 1 ---")
        csv_filename = f"check3_orders_{unique_ts}.csv"
        res_csv = requests.post(
            f"{BASE_URL}/uploads",
            headers=tm1_headers,
            files={"file": (csv_filename, csv_bytes, "text/csv")},
            data={"tenant_id": target_tenant_id},
        )
        print(f"CSV Upload Status: {res_csv.status_code}")
        assert res_csv.status_code in (200, 201), f"CSV upload failed: {res_csv.text}"
        csv_data = res_csv.json()
        csv_batch_id = csv_data["batch_id"]
        created_upload_ids.append(csv_data["upload_id"])
        print(f"CSV uploaded: batch_id={csv_batch_id}, upload_id={csv_data['upload_id']}")

        # Step 2: Submit Excel file for Tenant 1
        print("\n--- STEP 2: Submit Excel file for Tenant 1 ---")
        xlsx_filename = f"check3_orders_{unique_ts}.xlsx"
        res_xlsx = requests.post(
            f"{BASE_URL}/uploads",
            headers=tm1_headers,
            files={"file": (xlsx_filename, xlsx_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
            data={"tenant_id": target_tenant_id},
        )
        print(f"Excel Upload Status: {res_xlsx.status_code}")
        assert res_xlsx.status_code in (200, 201), f"Excel upload failed: {res_xlsx.text}"
        xlsx_data = res_xlsx.json()
        xlsx_batch_id = xlsx_data["batch_id"]
        created_upload_ids.append(xlsx_data["upload_id"])
        print(f"Excel uploaded: batch_id={xlsx_batch_id}, upload_id={xlsx_data['upload_id']}")

        # Step 3: Wait up to 15 seconds for schema inference / pending status
        print("\n--- STEP 3: Verifying Status in Pipeline ---")
        # Step 3: Wait for both batches to appear in Pending
        print("\n--- STEP 3: Waiting for Batches to be ready in Pending ---")
        tm1_batches = []
        admin_batches = []
        for attempt in range(1, 15):
            res_tm1 = requests.get(f"{BASE_URL}/uploads/pending", headers=tm1_headers)
            res_admin = requests.get(f"{BASE_URL}/uploads/pending", headers=admin_headers)
            if res_tm1.status_code == 200 and res_admin.status_code == 200:
                tm1_batches = [item["batch_id"] for item in res_tm1.json()]
                admin_batches = [item["batch_id"] for item in res_admin.json()]
                if csv_batch_id in tm1_batches and xlsx_batch_id in tm1_batches and csv_batch_id in admin_batches and xlsx_batch_id in admin_batches:
                    print(f"Batches visible in Pending after attempt {attempt}")
                    break
            time.sleep(2)

        # Step 4: Check Pending List for Assigned Team Member (team-member-1)
        print("\n--- STEP 4: Query Pending as Assigned Team Member (team-member-1) ---")
        assert csv_batch_id in tm1_batches, f"CSV batch {csv_batch_id} not visible to assigned TM1"
        assert xlsx_batch_id in tm1_batches, f"Excel batch {xlsx_batch_id} not visible to assigned TM1"
        print(f"[PASS] Both CSV ({csv_batch_id}) and Excel ({xlsx_batch_id}) appear in Pending for assigned Team Member 1.")

        # Step 5: Check Pending List for Admin (admin@helios.io)
        print("\n--- STEP 5: Query Pending as Admin ---")
        assert csv_batch_id in admin_batches, f"CSV batch {csv_batch_id} not visible to Admin"
        assert xlsx_batch_id in admin_batches, f"Excel batch {xlsx_batch_id} not visible to Admin"
        print(f"[PASS] Both CSV ({csv_batch_id}) and Excel ({xlsx_batch_id}) appear in Pending for Admin.")

        # Step 6: Check Pending List for Unassigned Team Member (team-member-2)
        print("\n--- STEP 6: Query Pending as Unassigned Team Member (team-member-2) ---")
        res_tm2 = requests.get(f"{BASE_URL}/uploads/pending", headers=tm2_headers)
        print(f"GET /uploads/pending (TM2 Unassigned) Status: {res_tm2.status_code}")
        assert res_tm2.status_code == 200
        tm2_batches = [item["batch_id"] for item in res_tm2.json()]
        print(f"Total Pending Batches visible to TM2: {len(tm2_batches)}")
        assert csv_batch_id not in tm2_batches, f"Security Violation: CSV batch {csv_batch_id} visible to unassigned TM2!"
        assert xlsx_batch_id not in tm2_batches, f"Security Violation: Excel batch {xlsx_batch_id} visible to unassigned TM2!"
        print(f"[PASS] Neither CSV nor Excel appears in Pending for unassigned Team Member 2.")

    finally:
        # Step 7: Cleanup test batches only
        print("\n--- STEP 7: CLEANUP OF TEST BATCHES ONLY ---")
        test_batches = [b for b in [csv_batch_id, xlsx_batch_id, "127903a3-7764-4e1d-8b40-3d9c781ee59d", "80c09718-2696-4ef0-a56a-a9cefdcf7814"] if b]
        with get_databricks_connection() as conn:
            with conn.cursor() as cur:
                for b in test_batches:
                    try:
                        cur.execute(f"DELETE FROM `{CATALOG}`.`platform`.`pipeline_status` WHERE batch_id = :b", {"b": b})
                        cur.execute(f"DELETE FROM `{CATALOG}`.`platform`.`inferred_schema` WHERE batch_id = :b", {"b": b})
                        cur.execute(f"DELETE FROM `{CATALOG}`.`bronze`.`raw_orders` WHERE batch_id = :b", {"b": b})
                        cur.execute(f"DELETE FROM `{CATALOG}`.`meta`.`etl_audit_log` WHERE batch_id = :b", {"b": b})
                        print(f"Deleted pipeline and bronze rows for batch {b}")
                    except Exception as ex:
                        print(f"Cleanup note for batch {b}: {ex}")
                all_uids = list(set(created_upload_ids + [170, 171]))
                for u in all_uids:
                    try:
                        cur.execute(f"DELETE FROM `{CATALOG}`.`platform`.`pending_uploads` WHERE upload_id = :u", {"u": u})
                        print(f"Deleted pending_uploads row for upload {u}")
                    except Exception as ex:
                        print(f"Cleanup note for upload {u}: {ex}")

    print("\n" + "=" * 75)
    print("CHECK 3 COMPLETED SUCCESSFULLY AND CLEANED UP!")
    print("=" * 75)

if __name__ == "__main__":
    main()
