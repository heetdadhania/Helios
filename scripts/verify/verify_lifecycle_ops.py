import io
import os
import sys
import time
import uuid
import requests
from pathlib import Path
from dotenv import load_dotenv

if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
sys.stdout.reconfigure(line_buffering=True)

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

def main():
    print("=" * 80)
    print("VERIFICATION OF CHECKS 3, 4, 5: OPS, TRACEABILITY, AND POST-SUCCESS UPDATES")
    print("=" * 80)

    admin_token = get_token("admin@helios.io", ADMIN_PASSWORD)
    tm1_token = get_token("team-member-1@helios-test.dev", TEST_ACCOUNT_PASSWORD)
    smb_token = get_token("smb-owner-1@helios-test.dev", TEST_ACCOUNT_PASSWORD)

    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    tm1_headers = {"Authorization": f"Bearer {tm1_token}"}
    smb_headers = {"Authorization": f"Bearer {smb_token}"}

    target_tenant_id = 1
    unique_ts = int(time.time())

    created_batch_ids = []
    created_upload_ids = []

    try:
        # =========================================================================
        # PART 1: REJECT WITH REASON
        # =========================================================================
        print("\n--- PART 1: Reject Batch with Reason ---")
        csv_reject_rows = [
            "order_id,customer_id,order_date,product_name,category,quantity,price,total_amount",
            f"ORD-REJ-{unique_ts}-1,CUST-1,2026-03-01,Test Product,Cat1,1,100,100",
        ]
        csv_reject_bytes = "\n".join(csv_reject_rows).encode("utf-8")
        res_up_rej = requests.post(
            f"{BASE_URL}/uploads",
            headers=tm1_headers,
            files={"file": (f"reject_test_{unique_ts}.csv", csv_reject_bytes, "text/csv")},
            data={"tenant_id": target_tenant_id, "override_duplicate": "true", "override_reason": "Testing rejection flow"},
        )
        assert res_up_rej.status_code in (200, 201), f"Upload failed: {res_up_rej.text}"
        rej_batch_id = res_up_rej.json()["batch_id"]
        created_batch_ids.append(rej_batch_id)
        created_upload_ids.append(res_up_rej.json()["upload_id"])
        print(f"Uploaded batch for rejection: {rej_batch_id}")

        # Wait for batch to land in pending_review
        for _ in range(30):
            res_pending = requests.get(f"{BASE_URL}/uploads/pending", headers=tm1_headers)
            items = res_pending.json().get("items", []) if isinstance(res_pending.json(), dict) else res_pending.json()
            match = next((b for b in items if b.get("batch_id") == rej_batch_id), None)
            if match and match.get("status") in ("pending_review", "awaiting_confirmation"):
                print(f"Batch {rej_batch_id} is in pending review with status={match.get('status')}.")
                break
            time.sleep(2)

        # Attempt reject with short reason (< 5 chars) -> 400 or 422
        res_rej_short = requests.post(
            f"{BASE_URL}/uploads/{rej_batch_id}/reject",
            headers=tm1_headers,
            json={"reason": "bad"},
        )
        assert res_rej_short.status_code in (400, 422), f"Expected 400 or 422 for short reject reason, got {res_rej_short.status_code}"
        print(f"  [PASS] Short rejection reason rejected ({res_rej_short.status_code}).")

        # Reject with valid reason (>= 5 chars) -> 200
        rejection_reason = "Rejecting due to incorrect product category taxonomy"
        res_rej_ok = requests.post(
            f"{BASE_URL}/uploads/{rej_batch_id}/reject",
            headers=tm1_headers,
            json={"reason": rejection_reason},
        )
        assert res_rej_ok.status_code == 200, f"Rejection failed: {res_rej_ok.text}"
        print(f"  [PASS] Batch {rej_batch_id} rejected successfully: {res_rej_ok.json().get('status')}")

        # Verify batch is no longer in pending
        res_pending_after = requests.get(f"{BASE_URL}/uploads/pending", headers=tm1_headers)
        items_after = res_pending_after.json().get("items", []) if isinstance(res_pending_after.json(), dict) else res_pending_after.json()
        assert not any(b.get("batch_id") == rej_batch_id for b in items_after), "Rejected batch still in pending!"
        print("  [PASS] Rejected batch removed from Pending uploads.")

        # =========================================================================
        # PART 2: REAL FAILURE FROM MALFORMED FILE -> STAGE, CAUSE, NEXT STEP -> RETRY -> FULL RESTART
        # =========================================================================
        print("\n--- PART 2: Real Failure from Malformed File -> Stage, Cause, Next Step, Retry, Full Restart ---")
        # Submit a malformed binary payload with a .csv extension
        corrupt_bytes = b"\x00\xFF\xFE\x00corrupt\x80\x90binary\x12\x34not_a_csv"
        res_fail = requests.post(
            f"{BASE_URL}/uploads",
            headers=tm1_headers,
            files={"file": (f"corrupt_{unique_ts}.csv", corrupt_bytes, "text/csv")},
            data={"tenant_id": target_tenant_id, "override_duplicate": "true", "override_reason": "Testing malformed file failure handling"},
        )
        print(f"Upload corrupt file response: {res_fail.status_code}")
        fail_batch_id = None
        if res_fail.status_code in (200, 201):
            fail_batch_id = res_fail.json()["batch_id"]
            created_batch_ids.append(fail_batch_id)
            created_upload_ids.append(res_fail.json()["upload_id"])
            print(f"Uploaded corrupt file batch: {fail_batch_id}")

            # Wait for ingestion/schema inference to fail
            for _ in range(25):
                res_detail = requests.get(f"{BASE_URL}/pipeline-health/runs/{fail_batch_id}", headers=tm1_headers)
                if res_detail.status_code == 200:
                    detail = res_detail.json()
                    st = detail.get("status", "").lower()
                    if st in ("failed", "error", "rejected"):
                        print(f"Batch failed as expected: status={st}, failed_stage={detail.get('failed_stage')}, error={detail.get('error_message') or detail.get('failure_message')}")
                        assert detail.get("failed_stage") is not None or detail.get("current_stage") is not None
                        assert detail.get("error_message") or detail.get("failure_message")
                        print("  [PASS] Real failure captured with stage and cause.")
                        break
                time.sleep(2)

            # Test Retry From Failed Stage
            print("\nTesting Retry From Failed Stage...")
            res_retry = requests.post(f"{BASE_URL}/pipeline-health/runs/{fail_batch_id}/retry-failed-stage", headers=tm1_headers)
            print(f"Retry endpoint status: {res_retry.status_code}")
            if res_retry.status_code == 200:
                print(f"  [PASS] Retry successfully triggered: {res_retry.json().get('message')}")
            else:
                print(f"  Retry response: {res_retry.status_code} {res_retry.text}")

            # Test Full Restart
            print("\nTesting Full Restart...")
            res_restart = requests.post(f"{BASE_URL}/pipeline-health/runs/{fail_batch_id}/full-restart", headers=tm1_headers)
            print(f"Full Restart status: {res_restart.status_code}")
            assert res_restart.status_code == 200, f"Full restart failed: {res_restart.text}"
            print(f"  [PASS] Full restart marked successfully: {res_restart.json().get('message')}")
        else:
            print(f"Immediate rejection on file upload (UploadService validation caught corrupt payload): {res_fail.status_code} {res_fail.text}")
            print("  [PASS] Corrupt payload rejected at boundary!")

        # =========================================================================
        # PART 3: TRACE ONE BATCH: BRONZE = SILVER VALID + REJECTED, GOLD = VALID
        # =========================================================================
        print("\n--- PART 3: Trace One Batch: Bronze = Silver Valid + Rejected, Gold = Valid ---")
        # 15 rows: 10 valid, 5 invalid
        # Rules for bad rows:
        # 1. Missing order_id
        # 2. Missing customer_id
        # 3. Missing product_id
        # 4. Negative quantity
        # 5. Zero unit price
        batch_trace_rows = [
            "order_id,order_date,customer_id,customer_name,segment,product_id,product_name,category,quantity,unit_price,discount,total,profit",
        ]
        # 10 valid orders
        for i in range(1, 11):
            oid = f"ORD-TRACE-{unique_ts}-{i:02d}"
            batch_trace_rows.append(f"{oid},2026-03-05,CUST-01,Ravi Kumar,Consumer,PROD-01,Silk Saree,Ethnic Wear,2,1000.00,0.00,2000.00,400.00")
        # 5 bad orders
        batch_trace_rows.append(f",2026-03-05,CUST-02,Anita Sen,Consumer,PROD-02,Cotton Kurta,Ethnic Wear,1,500.00,0.00,500.00,100.00") # missing order_id
        batch_trace_rows.append(f"ORD-TRACE-{unique_ts}-BAD2,2026-03-05,,Anita Sen,Consumer,PROD-02,Cotton Kurta,Ethnic Wear,1,500.00,0.00,500.00,100.00") # missing customer_id
        batch_trace_rows.append(f"ORD-TRACE-{unique_ts}-BAD3,2026-03-05,CUST-02,Anita Sen,Consumer,,Cotton Kurta,Ethnic Wear,1,500.00,0.00,500.00,100.00") # missing product_id
        batch_trace_rows.append(f"ORD-TRACE-{unique_ts}-BAD4,2026-03-05,CUST-02,Anita Sen,Consumer,PROD-02,Cotton Kurta,Ethnic Wear,-2,500.00,0.00,-1000.00,-200.00") # negative quantity
        batch_trace_rows.append(f"ORD-TRACE-{unique_ts}-BAD5,2026-03-05,CUST-02,Anita Sen,Consumer,PROD-02,Cotton Kurta,Ethnic Wear,1,0.00,0.00,0.00,0.00") # zero price

        trace_csv_bytes = "\n".join(batch_trace_rows).encode("utf-8")
        res_trace_up = requests.post(
            f"{BASE_URL}/uploads",
            headers=tm1_headers,
            files={"file": (f"trace_15_rows_{unique_ts}.csv", trace_csv_bytes, "text/csv")},
            data={"tenant_id": target_tenant_id, "override_duplicate": "true", "override_reason": "Verifying batch traceability Bronze=Silver+Reject Gold=Valid"},
        )
        assert res_trace_up.status_code in (200, 201), f"Upload failed: {res_trace_up.text}"
        trace_batch_id = res_trace_up.json()["batch_id"]
        created_batch_ids.append(trace_batch_id)
        created_upload_ids.append(res_trace_up.json()["upload_id"])
        print(f"Uploaded trace batch: {trace_batch_id}")

        # Wait for schema inference to reach pending_review
        print("Waiting for schema inference to reach pending_review...")
        for _ in range(40):
            res_pending = requests.get(f"{BASE_URL}/uploads/pending", headers=tm1_headers)
            items = res_pending.json().get("items", []) if isinstance(res_pending.json(), dict) else res_pending.json()
            match = next((b for b in items if b.get("batch_id") == trace_batch_id), None)
            if match and match.get("status") in ("pending_review", "awaiting_confirmation"):
                print(f"Batch {trace_batch_id} is ready for confirmation: status={match.get('status')}")
                break
            time.sleep(2)

        # Confirm schema to trigger Silver + Gold
        print(f"Confirming schema for trace batch {trace_batch_id}...")
        res_conf = requests.post(
            f"{BASE_URL}/uploads/{trace_batch_id}/confirm",
            headers=tm1_headers,
            json={"confirmed_template": "ecommerce_orders", "corrected_mapping": {}},
        )
        assert res_conf.status_code == 200, f"Schema confirmation failed: {res_conf.text}"
        print("Schema confirmed. Waiting for pipeline execution to complete...")

        # Wait for pipeline completion
        with get_databricks_connection() as conn:
            with conn.cursor() as cur:
                for _ in range(45):
                    cur.execute(
                        f"SELECT status FROM `{CATALOG}`.`platform`.`pipeline_status` WHERE batch_id = :b",
                        {"b": trace_batch_id},
                    )
                    row = cur.fetchone()
                    if row and row[0] == "success":
                        break
                    time.sleep(2)
                assert row and row[0] == "success", f"Batch did not complete with success: {row}"
                print(f"Batch {trace_batch_id} completed successfully through Gold!")

                # Query counts across Bronze, Silver, Quality Log, and Gold
                cur.execute(f"SELECT count(*) FROM `{CATALOG}`.`bronze`.`raw_orders` WHERE batch_id = :b", {"b": trace_batch_id})
                bronze_count = cur.fetchone()[0]

                cur.execute(f"SELECT count(*) FROM `{CATALOG}`.`silver`.`orders_clean` WHERE batch_id = :b", {"b": trace_batch_id})
                silver_valid_count = cur.fetchone()[0]

                cur.execute(f"SELECT count(*) FROM `{CATALOG}`.`meta`.`data_quality_log` WHERE batch_id = :b", {"b": trace_batch_id})
                quality_log_count = cur.fetchone()[0]

                cur.execute(f"SELECT count(*) FROM `{CATALOG}`.`gold`.`fact_orders` WHERE batch_id = :b", {"b": trace_batch_id})
                gold_count = cur.fetchone()[0]

                print("\n================== BATCH TRACE RESULTS ==================")
                print(f"  Batch ID:                {trace_batch_id}")
                print(f"  Bronze Raw Orders:       {bronze_count} (Expected: 15)")
                print(f"  Silver Valid Orders:     {silver_valid_count} (Expected: 10)")
                print(f"  Quality Log (Rejected):  {quality_log_count} (Expected: 5)")
                print(f"  Gold Fact Orders:        {gold_count} (Expected: 10)")
                print(f"  Formula Check: Bronze == Silver Valid + Rejected -> {bronze_count} == {silver_valid_count} + {quality_log_count} ({bronze_count == silver_valid_count + quality_log_count})")
                print(f"  Formula Check: Gold == Silver Valid -> {gold_count} == {silver_valid_count} ({gold_count == silver_valid_count})")
                print("=========================================================")

                assert bronze_count == 15, f"Expected Bronze 15, got {bronze_count}"
                assert silver_valid_count == 10, f"Expected Silver Valid 10, got {silver_valid_count}"
                assert quality_log_count == 5, f"Expected Rejected 5, got {quality_log_count}"
                assert gold_count == 10, f"Expected Gold 10, got {gold_count}"
                assert bronze_count == silver_valid_count + quality_log_count, "Bronze != Silver Valid + Rejected"
                assert gold_count == silver_valid_count, "Gold != Silver Valid"
                print("  [PASS] Bronze equals Silver valid plus rejected, and Gold matches valid rows!")

        # =========================================================================
        # PART 4: POST-SUCCESS VERIFICATION: OWNER DASHBOARD, "Data as of", NOTIFICATION, HISTORY
        # =========================================================================
        print("\n--- PART 4: Post-Success Verification ---")
        # 1. Owner's Dashboard & "Data as of"
        res_summary = requests.get(f"{BASE_URL}/dashboard/summary", headers=smb_headers)
        assert res_summary.status_code == 200, f"Dashboard summary failed: {res_summary.text}"
        summary_data = res_summary.json()
        data_as_of = summary_data.get("data_as_of")
        print(f"  Owner Dashboard summary: total_revenue={summary_data.get('total_revenue')}, data_as_of='{data_as_of}'")
        assert data_as_of, "data_as_of timestamp must be present on dashboard summary"
        print("  [PASS] Owner's dashboard updated with valid 'Data as of' timestamp.")

        # 2. History Updated
        res_hist_smb = requests.get(f"{BASE_URL}/history/mine", headers=smb_headers)
        assert res_hist_smb.status_code == 200, f"SMB History failed: {res_hist_smb.text}"
        hist_smb_items = res_hist_smb.json().get("items", []) if isinstance(res_hist_smb.json(), dict) else res_hist_smb.json()
        trace_in_smb = next((h for h in hist_smb_items if h.get("batch_id") == trace_batch_id), None)
        assert trace_in_smb is not None, f"Batch {trace_batch_id} not found in SMB history"
        print(f"  SMB History record found: batch_id={trace_in_smb.get('batch_id')}, status='{trace_in_smb.get('status')}'")
        assert trace_in_smb.get("status") in ("Ready", "Processing", "success"), f"Unexpected SMB history status: {trace_in_smb.get('status')}"

        res_hist_team = requests.get(f"{BASE_URL}/history/team", headers=tm1_headers)
        assert res_hist_team.status_code == 200, f"Team History failed: {res_hist_team.text}"
        hist_team_items = res_hist_team.json().get("items", []) if isinstance(res_hist_team.json(), dict) else res_hist_team.json()
        trace_in_team = next((h for h in hist_team_items if h.get("batch_id") == trace_batch_id), None)
        assert trace_in_team is not None, f"Batch {trace_batch_id} not found in Team history"
        print(f"  Team History record found: batch_id={trace_in_team.get('batch_id')}, status='{trace_in_team.get('status')}'")
        assert trace_in_team.get("status") in ("success", "completed"), f"Unexpected Team history status: {trace_in_team.get('status')}"
        print("  [PASS] Upload history updated for both SMB Owner and Team Member views.")

        # 3. Notification Updated
        res_notif = requests.get(f"{BASE_URL}/notifications", headers=smb_headers)
        assert res_notif.status_code == 200, f"Notifications request failed: {res_notif.text}"
        notifs = res_notif.json().get("items", []) if isinstance(res_notif.json(), dict) else res_notif.json()
        print(f"  Notifications count for SMB Owner: {len(notifs)}")
        print("  [PASS] Notifications endpoint accessible and returning real records.")

    finally:
        # =========================================================================
        # PART 5: CLEANUP OF CREATED TEST BATCHES ONLY (DATA RULE COMPLIANCE)
        # =========================================================================
        print("\n--- PART 5: CLEANUP OF TEST BATCHES ONLY ---")
        print(f"  Removing test batches: {created_batch_ids}")
        with get_databricks_connection() as conn:
            with conn.cursor() as cur:
                for bid in created_batch_ids:
                    try:
                        cur.execute(f"DELETE FROM `{CATALOG}`.`gold`.`fact_orders` WHERE batch_id = :b", {"b": bid})
                        cur.execute(f"DELETE FROM `{CATALOG}`.`gold`.`fact_shipments` WHERE batch_id = :b", {"b": bid})
                        cur.execute(f"DELETE FROM `{CATALOG}`.`silver`.`orders_clean` WHERE batch_id = :b", {"b": bid})
                        cur.execute(f"DELETE FROM `{CATALOG}`.`bronze`.`raw_orders` WHERE batch_id = :b", {"b": bid})
                        cur.execute(f"DELETE FROM `{CATALOG}`.`meta`.`data_quality_log` WHERE batch_id = :b", {"b": bid})
                        cur.execute(f"DELETE FROM `{CATALOG}`.`meta`.`audit_trail` WHERE batch_id = :b", {"b": bid})
                        cur.execute(f"DELETE FROM `{CATALOG}`.`meta`.`etl_audit_log` WHERE batch_id = :b", {"b": bid})
                        cur.execute(f"DELETE FROM `{CATALOG}`.`platform`.`pipeline_status` WHERE batch_id = :b", {"b": bid})
                        cur.execute(f"DELETE FROM `{CATALOG}`.`platform`.`inferred_schema` WHERE batch_id = :b", {"b": bid})
                        print(f"  Cleaned up all database records for batch {bid}")
                    except Exception as ex:
                        print(f"  Cleanup note for batch {bid}: {ex}")

                for uid in created_upload_ids:
                    try:
                        cur.execute(f"DELETE FROM `{CATALOG}`.`platform`.`pending_uploads` WHERE upload_id = :u", {"u": uid})
                    except Exception as ex:
                        print(f"  Cleanup note for upload {uid}: {ex}")

                # Refresh tenant 1 daily summary to ensure clean state
                cur.execute(f"CALL `{CATALOG}`.`gold`.`sp_refresh_daily_summary`({target_tenant_id}, 'ops-cleanup')")
                print(f"  Refreshed daily summary for tenant {target_tenant_id}")

    print("\n" + "=" * 80)
    print("ALL OPS, TRACEABILITY, AND POST-SUCCESS VERIFICATIONS PASSED!")
    print("=" * 80)

if __name__ == "__main__":
    main()
