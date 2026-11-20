import os
import sys
import time
import requests
from pathlib import Path
from dotenv import load_dotenv

REPO_ROOT = Path(r"C:\Project\Helios")
sys.path.insert(0, str(REPO_ROOT / "backend"))
from app.core import security
from app.db.base import databricks_cursor

load_dotenv(REPO_ROOT / ".env")
BASE_URL = "http://127.0.0.1:8000/api/v1"
TENANT_ID = 16
PACK_DIR = REPO_ROOT / "scripts" / "data" / "faculty_packs"

token = security.create_access_token(user_id=16, role="team_member", tenant_id=None)
headers = {"Authorization": f"Bearer {token}"}

THREE_PACKS = [
    ("clean_10_orders.csv", "Clean 10 Orders Benchmark"),
    ("err01_blank_quantity_orders.csv", "Blank Quantity Quality Rule"),
    ("err08_arithmetic_mismatch_orders.csv", "Arithmetic Mismatch Quality Rule"),
]

def run_pack(file_name, desc):
    print(f"\n=======================================================")
    print(f"RUNNING PACK: {file_name} ({desc})")
    print(f"=======================================================")
    file_path = PACK_DIR / file_name
    with open(file_path, "rb") as f:
        files = {"file": (file_name, f, "text/csv")}
        data = {
            "tenant_id": TENANT_ID,
            "override_duplicate": "true",
            "override_reason": f"Demonstration verification for {file_name}",
        }
        resp = requests.post(f"{BASE_URL}/uploads", files=files, data=data, headers=headers)

    res_json = resp.json()
    batch_id = res_json.get("batch_id")
    print(f"  Upload: HTTP {resp.status_code}, Batch ID: {batch_id}")

    # Wait for pending_review
    for _ in range(25):
        time.sleep(1.5)
        st_resp = requests.get(f"{BASE_URL}/pipeline/runs/{batch_id}", headers=headers)
        if st_resp.status_code == 200 and st_resp.json().get("status") == "pending_review":
            break

    # Confirm
    conf_resp = requests.post(
        f"{BASE_URL}/uploads/{batch_id}/confirm",
        json={"confirmed_template": "template_orders", "corrected_mapping": None, "internal_notes": f"Verified {file_name}"},
        headers=headers,
    )
    print(f"  Confirmation: HTTP {conf_resp.status_code}")

    # Wait for completion
    for _ in range(30):
        time.sleep(2)
        st_resp = requests.get(f"{BASE_URL}/pipeline/runs/{batch_id}", headers=headers)
        if st_resp.status_code == 200:
            st_data = st_resp.json()
            if st_data.get("status") in ("success", "failed"):
                print(f"  Pipeline Finished: Stage={st_data.get('current_stage')}, Status={st_data.get('status')}")
                break

    # Query Databricks
    with databricks_cursor() as cursor:
        cursor.execute(f"SELECT COUNT(1) FROM bronze.raw_orders WHERE batch_id = '{batch_id}'")
        bronze_cnt = cursor.fetchone()[0]
        cursor.execute(f"SELECT COUNT(1) FROM silver.orders_clean WHERE batch_id = '{batch_id}'")
        silver_cnt = cursor.fetchone()[0]
        cursor.execute(f"SELECT COUNT(1) FROM gold.fact_orders WHERE batch_id = '{batch_id}'")
        gold_cnt = cursor.fetchone()[0]
        cursor.execute(f"SELECT row_identifier, rejection_reason FROM meta.data_quality_log WHERE batch_id = '{batch_id}'")
        rej_rows = cursor.fetchall()

    print(f"  >>> COUNTS: Bronze={bronze_cnt} | Silver Clean={silver_cnt} | Rejected={len(rej_rows)} | Gold Fact={gold_cnt}")
    if rej_rows:
        print("  >>> Rejection Reasons:")
        for r in rej_rows:
            print(f"      * {r[0]}: {r[1]}")

def main():
    for fn, desc in THREE_PACKS:
        run_pack(fn, desc)

if __name__ == "__main__":
    main()
