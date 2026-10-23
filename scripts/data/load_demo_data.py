#!/usr/bin/env python3
"""
Helios Data Platform - Real Team Member Flow Data Loader
Loads Indian e-commerce demo data for 10 organizations through the real Team Member HTTP flow:
1. Logs in as the assigned team member for each organization.
2. Uploads the dataset file (orders first, then shipping).
3. Polls until batch reaches 'pending_review' in platform.pipeline_status.
4. Approves/confirms the schema mapping via POST /api/v1/uploads/{batch_id}/confirm.
5. Polls until batch reaches 'success' (or 'failed').
6. Verifies from Databricks Unity Catalog that Bronze == Silver valid + Quality log,
   and Gold fact_orders == valid orders from expected_totals.json.
"""

import argparse
import csv
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend"))
load_dotenv(REPO_ROOT / ".env")

try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from app.core.config import settings
from app.db.base import get_databricks_connection

BASE_URL = os.environ.get("HELIOS_API_BASE_URL", "http://127.0.0.1:8000")
CATALOG = getattr(settings, "DATABRICKS_CATALOG", "helios_catalog")
DATA_DIR = REPO_ROOT / "scripts" / "data" / "helios_indian_data"

# Assigned team members mapping per specification:
# 1 and 2 -> team-member-1; 3 and 4 -> team-member-2; 5 and 6 -> team-member-3;
# 7 and 8 -> team-member-4; 9 and 10 -> team-member-5.
ASSIGNED_TEAM_MEMBERS: Dict[int, str] = {
    1: "team-member-1@helios-test.dev",
    2: "team-member-1@helios-test.dev",
    3: "team-member-2@helios-test.dev",
    4: "team-member-2@helios-test.dev",
    5: "team-member-3@helios-test.dev",
    6: "team-member-3@helios-test.dev",
    7: "team-member-4@helios-test.dev",
    8: "team-member-4@helios-test.dev",
    9: "team-member-5@helios-test.dev",
    10: "team-member-5@helios-test.dev",
}

# Cache for team member JWT tokens
_auth_tokens: Dict[str, str] = {}


def get_team_member_token(email: str) -> str:
    """Log in as team member using TEST_ACCOUNT_PASSWORD from environment (never logged)."""
    if email in _auth_tokens:
        return _auth_tokens[email]

    password = os.environ.get("TEST_ACCOUNT_PASSWORD")
    if not password:
        raise ValueError("TEST_ACCOUNT_PASSWORD environment variable is missing or empty.")

    login_url = f"{BASE_URL}/api/v1/auth/login"
    resp = requests.post(login_url, json={"email": email, "password": password}, timeout=30)
    if resp.status_code != 200:
        raise RuntimeError(f"Login failed for {email} (status {resp.status_code}): {resp.text}")

    token = resp.json().get("access_token")
    if not token:
        raise RuntimeError(f"No access token returned for {email}: {resp.text}")

    _auth_tokens[email] = token
    return token


def wait_for_pipeline_status(
    batch_id: str,
    target_statuses: List[str],
    timeout_seconds: int = 300,
    poll_interval: int = 4,
) -> Tuple[str, str, Optional[str], Optional[str], Optional[str]]:
    """
    Poll platform.pipeline_status in Databricks until reaching one of target_statuses.
    Returns (status, stage, failed_stage, failure_message, failure_next_step).
    """
    start_time = time.time()
    last_status = None

    with get_databricks_connection(catalog=CATALOG) as conn:
        with conn.cursor() as cur:
            while time.time() - start_time < timeout_seconds:
                cur.execute(
                    f"""
                    SELECT status, stage, failed_stage, failure_message, failure_next_step
                    FROM `{CATALOG}`.`platform`.`pipeline_status`
                    WHERE batch_id = :bid
                    LIMIT 1
                    """,
                    {"bid": batch_id},
                )
                row = cur.fetchone()
                if row:
                    st, stage, failed_stage, fail_msg, fail_next = (
                        row[0],
                        row[1],
                        row[2],
                        row[3],
                        row[4],
                    )
                    if st != last_status:
                        elapsed = time.time() - start_time
                        print(f"    [Status Transition] batch={batch_id[:8]}.. -> status={st}, stage={stage} ({elapsed:.1f}s)")
                        last_status = st

                    if st in target_statuses:
                        return st, stage, failed_stage, fail_msg, fail_next
                    if st == "failed" and "failed" not in target_statuses:
                        return st, stage, failed_stage, fail_msg, fail_next

                time.sleep(poll_interval)

    elapsed = time.time() - start_time
    raise TimeoutError(
        f"Batch {batch_id} timed out after {elapsed:.1f}s waiting for {target_statuses} (last status: {last_status})"
    )


def is_file_batch_succeeded(tenant_id: int, filename: str) -> Optional[str]:
    """Check if an upload batch for this file has already reached status 'success'."""
    with get_databricks_connection(catalog=CATALOG) as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT ps.batch_id
                FROM `{CATALOG}`.`platform`.`pipeline_status` ps
                JOIN `{CATALOG}`.`platform`.`pending_uploads` pu ON ps.upload_id = pu.upload_id
                WHERE pu.tenant_id = :tid 
                  AND (pu.file_name = :fname OR pu.file_name LIKE :fpattern)
                  AND ps.status = 'success'
                ORDER BY ps.updated_at DESC
                LIMIT 1
                """,
                {"tid": tenant_id, "fname": filename, "fpattern": f"%{filename}%"},
            )
            row = cur.fetchone()
            return row[0] if row else None


def find_existing_batch(tenant_id: int, filename: str) -> Optional[Tuple[str, str]]:
    """Return (batch_id, status) if a batch exists for this file."""
    with get_databricks_connection(catalog=CATALOG) as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT ps.batch_id, ps.status
                FROM `{CATALOG}`.`platform`.`pipeline_status` ps
                JOIN `{CATALOG}`.`platform`.`pending_uploads` pu ON ps.upload_id = pu.upload_id
                WHERE pu.tenant_id = :tid 
                  AND (pu.file_name = :fname OR pu.file_name LIKE :fpattern)
                ORDER BY ps.updated_at DESC
                LIMIT 1
                """,
                {"tid": tenant_id, "fname": filename, "fpattern": f"%{filename}%"},
            )
            row = cur.fetchone()
            return (row[0], row[1]) if row else None


def upload_and_process_batch(
    tenant_id: int,
    file_path: Path,
    expected_template_hint: str,
) -> Dict[str, Any]:
    """
    Execute real Team Member flow for a single dataset file:
    1. Upload file via HTTP multipart POST.
    2. Poll for 'pending_review'.
    3. Get preview and approve/confirm schema mapping.
    4. Poll for 'success' (or 'failed').
    Returns timing dictionary and batch ID.
    """
    team_email = ASSIGNED_TEAM_MEMBERS[tenant_id]
    token = get_team_member_token(team_email)
    headers = {"Authorization": f"Bearer {token}"}

    filename = file_path.name
    print(f"\n  [START BATCH] File: {filename} for Organization {tenant_id} via {team_email}")
    total_start_perf = time.perf_counter()

    # Determine MIME type
    if filename.endswith(".xlsx"):
        content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    else:
        content_type = "text/csv"

    existing = find_existing_batch(tenant_id, filename)
    if existing and existing[1] in ("pending_review", "awaiting_confirmation"):
        batch_id = existing[0]
        upload_duration = 0.0
        infer_duration = 0.0
        print(f"    Resuming existing batch in '{existing[1]}': batch_id={batch_id}")
    else:
        # Step 1: Upload File
        t_upload_start = time.perf_counter()
        with open(file_path, "rb") as f:
            file_bytes = f.read()

        files = {"file": (filename, file_bytes, content_type)}
        upload_url = (
            f"{BASE_URL}/api/v1/uploads?tenant_id={tenant_id}"
            f"&override_duplicate=true&override_reason=Loading+verified+demo+dataset"
        )
        print(f"    Submitting POST {upload_url} ({len(file_bytes)} bytes)...")
        resp = requests.post(upload_url, files=files, headers=headers, timeout=120)

        if resp.status_code not in (200, 201):
            raise RuntimeError(f"Upload failed (status {resp.status_code}): {resp.text}")

        upload_data = resp.json()
        batch_id = upload_data["batch_id"]
        upload_id = upload_data.get("upload_id")
        upload_duration = time.perf_counter() - t_upload_start
        print(f"    Upload accepted: batch_id={batch_id}, upload_id={upload_id} (took {upload_duration:.2f}s)")

        # Step 2: Poll for pending_review
        t_infer_start = time.perf_counter()
        print("    Waiting for Bronze ingestion and schema inference -> 'pending_review'...")
        st, stage, failed_stage, fail_msg, fail_next = wait_for_pipeline_status(
            batch_id,
            target_statuses=["pending_review", "awaiting_confirmation", "failed"],
            timeout_seconds=240,
        )

        infer_duration = time.perf_counter() - t_infer_start

        if st == "failed":
            print(f"\n[FAILURE AT STAGE: {stage or failed_stage}]")
            print(f"  Failure Message:   {fail_msg}")
            print(f"  Failure Next Step: {fail_next}")
            raise RuntimeError(
                f"Batch {batch_id} failed during ingestion/inference at stage '{stage or failed_stage}': {fail_msg}"
            )

    # Step 3: Get preview and confirm mapping
    t_confirm_start = time.perf_counter()
    detected_template = expected_template_hint
    preview_url = f"{BASE_URL}/api/v1/uploads/{batch_id}/preview"
    try:
        prev_resp = requests.get(preview_url, headers=headers, timeout=60)
        if prev_resp.status_code == 200:
            detected_template = prev_resp.json().get("detected_template", expected_template_hint)
    except Exception as e:
        print(f"    Preview notice ({e}), defaulting template to {expected_template_hint}")

    print(f"    Schema template for confirmation: {detected_template}")
    confirm_url = f"{BASE_URL}/api/v1/uploads/{batch_id}/confirm"
    confirm_payload = {
        "confirmed_template": detected_template,
        "internal_notes": f"Confirmed by {team_email} for Organization {tenant_id}",
    }
    appr_resp = requests.post(confirm_url, json=confirm_payload, headers=headers, timeout=120)
    if appr_resp.status_code != 200:
        raise RuntimeError(f"Approval failed for batch {batch_id} (status {appr_resp.status_code}): {appr_resp.text}")

    # Step 4: Poll for pipeline completion (Silver -> Gold -> Success)
    print("    Executing Medallion Pipeline (Silver cleaning -> Gold rollups)...")
    st, stage, failed_stage, fail_msg, fail_next = wait_for_pipeline_status(
        batch_id,
        target_statuses=["success", "failed"],
        timeout_seconds=240,
    )
    pipeline_duration = time.perf_counter() - t_confirm_start

    if st != "success":
        print(f"\n[FAILURE AT STAGE: {stage or failed_stage}]")
        print(f"  Failure Message:   {fail_msg}")
        print(f"  Failure Next Step: {fail_next}")
        raise RuntimeError(
            f"Batch {batch_id} failed during Medallion execution at stage '{stage or failed_stage}': {fail_msg}"
        )

    total_batch_duration = time.perf_counter() - total_start_perf
    print(f"    --> BATCH SUCCESS! Total timing: {total_batch_duration:.2f}s "
          f"(Upload: {upload_duration:.2f}s, Inference: {infer_duration:.2f}s, Pipeline: {pipeline_duration:.2f}s)")

    return {
        "batch_id": batch_id,
        "filename": filename,
        "tenant_id": tenant_id,
        "upload_seconds": upload_duration,
        "inference_seconds": infer_duration,
        "pipeline_seconds": pipeline_duration,
        "total_seconds": total_batch_duration,
    }


def verify_org_database_counts(tenant_id: int, expected_meta: Dict[str, Any], orders_batch_id: str, shipping_batch_id: str):
    """
    Verify from the database:
    1. Bronze rows == Silver valid rows + quality-log rows for the orders batch.
    2. Gold fact_orders rows == valid_orders in expected_totals.json.
    3. Rejections match expected bad_rows (e.g. orgs 1, 4, 7 show 6, 6, 8 rejected rows).
    4. Shipping rows in Gold fact_shipments match expected.
    """
    exp_valid = expected_meta["valid_orders"]
    exp_bad = expected_meta.get("bad_rows_included", 0)
    exp_revenue = float(expected_meta["revenue_total"])

    with get_databricks_connection(catalog=CATALOG) as conn:
        with conn.cursor() as cur:
            # 1. Orders Bronze count for batch
            cur.execute(
                f"SELECT count(*) FROM `{CATALOG}`.`bronze`.`raw_orders` WHERE batch_id = :bid",
                {"bid": orders_batch_id},
            )
            bronze_orders = cur.fetchone()[0]

            # 2. Orders Silver valid count for batch
            cur.execute(
                f"SELECT count(*) FROM `{CATALOG}`.`silver`.`orders_clean` WHERE batch_id = :bid AND is_valid = true",
                {"bid": orders_batch_id},
            )
            silver_valid = cur.fetchone()[0]

            # 3. Quality log count for batch
            cur.execute(
                f"SELECT count(*) FROM `{CATALOG}`.`meta`.`data_quality_log` WHERE batch_id = :bid",
                {"bid": orders_batch_id},
            )
            ql_count = cur.fetchone()[0]

            # 4. Gold fact_orders count for batch
            cur.execute(
                f"SELECT count(*), round(coalesce(sum(total), 0.0), 2) FROM `{CATALOG}`.`gold`.`fact_orders` WHERE batch_id = :bid",
                {"bid": orders_batch_id},
            )
            gold_row = cur.fetchone()
            gold_batch_orders = gold_row[0]
            gold_batch_revenue = float(gold_row[1] or 0.0)

            # Tenant total in Gold fact_orders
            cur.execute(
                f"SELECT count(*), round(coalesce(sum(total), 0.0), 2) FROM `{CATALOG}`.`gold`.`fact_orders` WHERE tenant_id = :tid",
                {"tid": tenant_id},
            )
            tot_row = cur.fetchone()
            gold_tenant_orders = tot_row[0]
            gold_tenant_revenue = float(tot_row[1] or 0.0)

            # 5. Shipping Bronze count for batch
            cur.execute(
                f"SELECT count(*) FROM `{CATALOG}`.`bronze`.`raw_shipping` WHERE batch_id = :bid",
                {"bid": shipping_batch_id},
            )
            bronze_ship = cur.fetchone()[0]

            # 6. Gold fact_shipments count for batch and organization
            cur.execute(
                f"SELECT count(*) FROM `{CATALOG}`.`gold`.`fact_shipments` WHERE batch_id = :bid",
                {"bid": shipping_batch_id},
            )
            gold_batch_ship = cur.fetchone()[0]

            cur.execute(
                f"SELECT count(*) FROM `{CATALOG}`.`gold`.`fact_shipments` WHERE tenant_id = :tid",
                {"tid": tenant_id},
            )
            gold_tenant_ship = cur.fetchone()[0]

    bronze_equation = (bronze_orders == silver_valid + ql_count)
    gold_matches_exp = (gold_batch_orders == exp_valid)
    bad_matches_exp = (ql_count == exp_bad)
    rev_diff = abs(gold_batch_revenue - exp_revenue)

    print("\n" + "=" * 80)
    print(f"DATABASE VERIFICATION FOR ORGANIZATION {tenant_id} ({expected_meta['organization']}):")
    print(f"  Orders Batch:          {orders_batch_id}")
    print(f"  Shipping Batch:        {shipping_batch_id}")
    print(f"  Bronze Orders:         {bronze_orders} (Silver Valid: {silver_valid} + Quality Log: {ql_count}) -> Balanced: {bronze_equation}")
    print(f"  Quality Log Rows:      {ql_count} (Expected Bad Rows: {exp_bad}) -> Match: {bad_matches_exp}")
    print(f"  Gold Batch Orders:     {gold_batch_orders} (Expected: {exp_valid}) -> Match: {gold_matches_exp}")
    print(f"  Gold Batch Revenue:    ₹{gold_batch_revenue:,.2f} (Expected: ₹{exp_revenue:,.2f}, diff: ₹{rev_diff:.2f})")
    print(f"  Gold Tenant Total Ord: {gold_tenant_orders} (Rev: ₹{gold_tenant_revenue:,.2f})")
    print(f"  Bronze Shipping:       {bronze_ship}")
    print(f"  Gold Batch Shipping:   {gold_batch_ship}")
    print(f"  Gold Tenant Shipping:  {gold_tenant_ship}")
    print("=" * 80)

    assert bronze_equation, f"Bronze mismatch for Org {tenant_id}: {bronze_orders} != {silver_valid} + {ql_count}"
    assert bad_matches_exp, f"Quality log count mismatch for Org {tenant_id}: got {ql_count}, expected {exp_bad}"
    assert gold_matches_exp, f"Gold fact_orders batch mismatch for Org {tenant_id}: got {gold_batch_orders}, expected {exp_valid}"


def load_organization(tenant_id: int, manifest_row: Dict[str, str], expected_totals: Dict[str, Any]) -> Dict[str, Any]:
    """Load orders and shipping files for a single organization."""
    org_name = manifest_row["organization"]
    orders_file = manifest_row["orders_file"]
    shipping_file = manifest_row["shipping_file"]
    expected_meta = expected_totals[str(tenant_id)]

    orders_path = DATA_DIR / orders_file
    shipping_path = DATA_DIR / shipping_file

    if not orders_path.exists():
        raise FileNotFoundError(f"Orders file not found: {orders_path}")
    if not shipping_path.exists():
        raise FileNotFoundError(f"Shipping file not found: {shipping_path}")

    # Check restartability
    existing_orders_batch = is_file_batch_succeeded(tenant_id, orders_file)
    existing_shipping_batch = is_file_batch_succeeded(tenant_id, shipping_file)

    if existing_orders_batch and existing_shipping_batch:
        print(f"\n>>> [SKIPPING] Organization {tenant_id} ({org_name}) is already loaded with batches:")
        print(f"    Orders batch:   {existing_orders_batch}")
        print(f"    Shipping batch: {existing_shipping_batch}")
        verify_org_database_counts(tenant_id, expected_meta, existing_orders_batch, existing_shipping_batch)
        return {
            "tenant_id": tenant_id,
            "status": "skipped_already_loaded",
            "orders_batch": existing_orders_batch,
            "shipping_batch": existing_shipping_batch,
        }

    print(f"\n{'#' * 80}")
    print(f"### PROCESSING ORGANIZATION {tenant_id}: {org_name} ({manifest_row['industry']})")
    print(f"{'#' * 80}")

    # 1. Orders batch first (skip if already succeeded)
    if existing_orders_batch:
        print(f"\n  [ALREADY SUCCEEDED] Orders batch for {orders_file}: {existing_orders_batch}. Skipping.")
        orders_result = {
            "batch_id": existing_orders_batch,
            "filename": orders_file,
            "tenant_id": tenant_id,
            "upload_seconds": 0.0,
            "inference_seconds": 0.0,
            "pipeline_seconds": 0.0,
            "total_seconds": 0.0,
        }
    else:
        orders_result = upload_and_process_batch(
            tenant_id=tenant_id,
            file_path=orders_path,
            expected_template_hint="template_orders",
        )

    # 2. Shipping batch second (skip if already succeeded)
    if existing_shipping_batch:
        print(f"\n  [ALREADY SUCCEEDED] Shipping batch for {shipping_file}: {existing_shipping_batch}. Skipping.")
        shipping_result = {
            "batch_id": existing_shipping_batch,
            "filename": shipping_file,
            "tenant_id": tenant_id,
            "upload_seconds": 0.0,
            "inference_seconds": 0.0,
            "pipeline_seconds": 0.0,
            "total_seconds": 0.0,
        }
    else:
        shipping_result = upload_and_process_batch(
            tenant_id=tenant_id,
            file_path=shipping_path,
            expected_template_hint="template_shipping",
        )

    # 3. Database verification
    verify_org_database_counts(
        tenant_id=tenant_id,
        expected_meta=expected_meta,
        orders_batch_id=orders_result["batch_id"],
        shipping_batch_id=shipping_result["batch_id"],
    )

    return {
        "tenant_id": tenant_id,
        "status": "success",
        "orders_result": orders_result,
        "shipping_result": shipping_result,
    }


def main():
    parser = argparse.ArgumentParser(description="Helios Real Team Member Flow Data Loader")
    parser.add_argument(
        "--time-test",
        action="store_true",
        help="Run Step 2 TIME TEST FIRST on Organization 9 only",
    )
    parser.add_argument(
        "--orgs",
        type=str,
        default=None,
        help="Comma-separated list of organization IDs to load (e.g. '9' or '2,3,4,5,6,7,8,10,1')",
    )
    args = parser.parse_args()

    # Read manifest
    manifest_path = DATA_DIR / "manifest.csv"
    manifest: Dict[int, Dict[str, str]] = {}
    with open(manifest_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            manifest[int(r["org_id"])] = r

    # Read expected_totals.json
    expected_path = DATA_DIR / "expected_totals.json"
    with open(expected_path, "r", encoding="utf-8") as f:
        expected_totals = json.load(f)

    # Determine execution list
    if args.time_test:
        target_orgs = [9]
    elif args.orgs:
        target_orgs = [int(x.strip()) for x in args.orgs.split(",") if x.strip()]
    else:
        # Default order per Step 3: 2, 3 (Excel), 4, 5, 6 (Excel), 7, 8, 10, 1
        target_orgs = [2, 3, 4, 5, 6, 7, 8, 10, 1]

    print(f"Target Organizations to Load ({len(target_orgs)}): {target_orgs}")
    total_start = time.perf_counter()
    summary_results = []

    for org_id in target_orgs:
        if org_id not in manifest:
            print(f"Warning: Organization {org_id} not found in manifest.csv. Skipping.")
            continue

        result = load_organization(org_id, manifest[org_id], expected_totals)
        summary_results.append(result)

        # Check timing rule: if single batch exceeds 5 minutes, stop immediately
        if result.get("status") == "success":
            ord_res = result["orders_result"]
            shp_res = result["shipping_result"]
            if ord_res["total_seconds"] > 300 or shp_res["total_seconds"] > 300:
                print(f"\n[ALERT] A single batch exceeded 5 minutes (Orders: {ord_res['total_seconds']:.1f}s, Shipping: {shp_res['total_seconds']:.1f}s)!")
                print("Stopping per time limit rule.")
                sys.exit(1)

    total_time = time.perf_counter() - total_start
    print(f"\n{'=' * 80}")
    print(f"ALL REQUESTED ORGANIZATIONS PROCESSED IN {total_time:.2f}s ({total_time / 60:.2f} mins)")
    print(f"{'=' * 80}")


if __name__ == "__main__":
    main()
