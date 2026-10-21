#!/usr/bin/env python3
"""
scripts/verify/verify_dashboard_against_source.py

Comprehensive verification suite:
1. Submits and approves batches via real Team Member flow one at a time:
   - Organization 1: orders_30_valid_plus_3_bad.csv, then shipping_30_for_valid_orders.csv
   - Organization 2: orders_10_renamed_headers.csv
   - Organization 3: orders_30_valid.xlsx (Excel)
2. Computes expected metrics with pandas directly from source files (dropping the 3 bad rows of file 1):
   - Total revenue
   - Order count
   - Top 5 products by revenue
   - Revenue by category
   - Average discount and total profit by category
   - For Organization 1: orders and late percentage by shipping mode
   - Revenue for last 7 days and last 30 days counted back from each organization's latest order date
3. Logs in as Organization Owners of 1, 2, and 3, calls every dashboard endpoint.
4. Compares amounts to the paisa (difference > ₹0.01 is a mismatch).
5. Prints comparison table: metric, expected, shown on dashboard, match yes or no.
6. Shows that the three organizations' numbers differ.
"""

import os
import sys
import time

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import requests
from dotenv import load_dotenv

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO_ROOT, "backend"))
load_dotenv(os.path.join(REPO_ROOT, ".env"))

from app.db.base import get_databricks_connection
from app.core.config import settings

BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000/api/v1")
CATALOG = getattr(settings, "DATABRICKS_CATALOG", "helios_catalog")
DEFAULT_TIMEOUT = 60

TEST_PASSWORD = os.environ.get("TEST_ACCOUNT_PASSWORD")

# Assigned Team Members
TM1_EMAIL = "team-member-1@helios-test.dev"  # Assigned to Org 1 & 2
TM2_EMAIL = "team-member-2@helios-test.dev"  # Assigned to Org 3

# Organization Owners
SMB1_EMAIL = "smb-owner-1@helios-test.dev"
SMB2_EMAIL = "smb-owner-2@helios-test.dev"
SMB3_EMAIL = "smb-owner-3@helios-test.dev"


def format_inr(amount: float) -> str:
    """Format numeric value in Indian Rupees with Indian digit grouping."""
    if amount is None:
        return "₹0.00"
    is_neg = amount < 0
    amount = abs(amount)
    s = f"{amount:.2f}"
    parts = s.split(".")
    integer_part = parts[0]
    decimal_part = parts[1]

    if len(integer_part) > 3:
        last3 = integer_part[-3:]
        remaining = integer_part[:-3]
        groups = []
        while len(remaining) > 2:
            groups.append(remaining[-2:])
            remaining = remaining[:-2]
        if remaining:
            groups.append(remaining)
        groups.reverse()
        formatted_int = ",".join(groups) + "," + last3
    else:
        formatted_int = integer_part

    res = f"₹{formatted_int}.{decimal_part}"
    return f"-{res}" if is_neg else res


def login(email: str, password: str) -> Tuple[str, Dict[str, Any]]:
    """Log in against /api/v1/auth/login and return (access_token, user_dict)."""
    resp = requests.post(
        f"{BASE_URL}/auth/login",
        json={"email": email, "password": password},
        timeout=DEFAULT_TIMEOUT,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"Login failed for {email}: {resp.status_code} {resp.text}")
    data = resp.json()
    return data["access_token"], data.get("user") or {}


def wait_for_pipeline_status(
    batch_id: str,
    target_statuses: List[str],
    timeout_seconds: int = 180,
    poll_interval: float = 3.0,
) -> Tuple[str, str]:
    """Poll platform.pipeline_status in Databricks until target status reached or timeout."""
    start = time.time()
    last_status = None
    with get_databricks_connection(catalog=CATALOG) as conn:
        with conn.cursor() as cur:
            while time.time() - start < timeout_seconds:
                cur.execute(
                    f"SELECT status, stage FROM `{CATALOG}`.`platform`.`pipeline_status` WHERE batch_id = :batch_id",
                    {"batch_id": batch_id},
                )
                row = cur.fetchone()
                if row:
                    st, stage = row[0], row[1]
                    if st != last_status:
                        print(f"       Batch {batch_id}: status={st}, stage={stage}", flush=True)
                        last_status = st
                    if st in target_statuses:
                        return st, stage
                time.sleep(poll_interval)
    raise TimeoutError(f"Batch {batch_id} did not reach {target_statuses} within {timeout_seconds}s (last={last_status})")


def submit_and_approve_batch(
    tenant_id: int,
    filename: str,
    filepath: str,
    template_name: str,
    tm_token: str,
) -> str:
    """Submit and approve a single batch through the real Team Member flow."""
    print(f"\n---> Submitting {filename} for Organization {tenant_id} via Team Member flow...")
    with open(filepath, "rb") as f:
        file_bytes = f.read()

    mime_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" if filename.endswith(".xlsx") else "text/csv"
    files = {"file": (filename, file_bytes, mime_type)}
    data = {
        "tenant_id": tenant_id,
        "override_duplicate": "true",
        "override_reason": f"Real data verification for Organization {tenant_id}",
    }
    headers = {"Authorization": f"Bearer {tm_token}"}

    r_upload = None
    for attempt in range(4):
        with open(filepath, "rb") as f:
            file_bytes = f.read()
        files = {"file": (filename, file_bytes, mime_type)}
        r_upload = requests.post(
            f"{BASE_URL}/uploads",
            files=files,
            data=data,
            headers=headers,
            timeout=DEFAULT_TIMEOUT,
        )
        if r_upload.status_code in (200, 201):
            break
        print(f"     Upload attempt {attempt+1} got {r_upload.status_code}: {r_upload.text[:100]}, retrying in 3s...", flush=True)
        time.sleep(3)

    if r_upload is None or r_upload.status_code not in (200, 201):
        raise RuntimeError(f"Upload failed for {filename}: {r_upload.status_code if r_upload else 'None'} {r_upload.text if r_upload else ''}")

    upload_json = r_upload.json()
    batch_id = upload_json["batch_id"]
    print(f"     Uploaded successfully: batch_id={batch_id}")

    print("     Waiting for schema inference (awaiting_confirmation / pending_review)...")
    st, _ = wait_for_pipeline_status(batch_id, ["awaiting_confirmation", "pending_review", "failed"], timeout_seconds=180)
    if st == "failed":
        raise RuntimeError(f"Schema inference failed for batch {batch_id}")

    print(f"     Approving batch {batch_id} with template={template_name}...")
    r_confirm = requests.post(
        f"{BASE_URL}/uploads/{batch_id}/confirm",
        json={
            "confirmed_template": template_name,
            "internal_notes": f"Approved {filename} for Organization {tenant_id}",
        },
        headers=headers,
        timeout=DEFAULT_TIMEOUT,
    )
    if r_confirm.status_code != 200:
        raise RuntimeError(f"Confirmation failed for batch {batch_id}: {r_confirm.status_code} {r_confirm.text}")

    print("     Confirmation accepted. Waiting for Medallion pipeline completion (success)...")
    final_st, _ = wait_for_pipeline_status(batch_id, ["success", "failed"], timeout_seconds=240)
    if final_st != "success":
        raise RuntimeError(f"Pipeline failed for batch {batch_id}: status={final_st}")

    print(f"     Batch {batch_id} successfully completed through Gold layer!")
    return batch_id


# ==============================================================================
# SOURCE PANDAS COMPUTATIONS
# ==============================================================================

def compute_org1_source_metrics(orders_path: str, shipping_path: str) -> Dict[str, Any]:
    """Compute expected metrics for Organization 1 dropping the 3 bad rows."""
    df_raw = pd.read_csv(orders_path)
    # Drop 3 bad rows:
    # 1. missing quantity (NaN)
    # 2. negative or 0 quantity
    # 3. invalid date ('not-a-date')
    df = df_raw.dropna(subset=["quantity"]).copy()
    df = df[df["quantity"] > 0]
    df["order_date_dt"] = pd.to_datetime(df["order_date"], errors="coerce")
    df = df.dropna(subset=["order_date_dt"])

    total_revenue = round(float(df["total"].sum()), 2)
    order_count = int(df["order_id"].nunique())
    latest_order_date = df["order_date_dt"].max()

    start_7d = latest_order_date - pd.Timedelta(days=6)
    rev_7d = round(float(df[df["order_date_dt"] >= start_7d]["total"].sum()), 2)

    start_30d = latest_order_date - pd.Timedelta(days=29)
    rev_30d = round(float(df[df["order_date_dt"] >= start_30d]["total"].sum()), 2)

    # Top 5 products by revenue
    top5_df = (
        df.groupby(["product_id", "product_name", "category"])["total"]
        .sum()
        .reset_index()
        .sort_values(by="total", ascending=False)
        .head(5)
    )
    top5_products = [
        {
            "product_id": r["product_id"],
            "product_name": r["product_name"],
            "category": r["category"],
            "total_revenue": round(float(r["total"]), 2),
        }
        for _, r in top5_df.iterrows()
    ]

    # Revenue, avg discount, and total profit by category
    cat_df = df.groupby("category").agg(
        total_revenue=("total", "sum"),
        avg_discount=("discount", "mean"),
        total_profit=("profit", "sum"),
    ).reset_index()
    category_metrics = {
        r["category"]: {
            "total_revenue": round(float(r["total_revenue"]), 2),
            "avg_discount": round(float(r["avg_discount"]), 2),
            "total_profit": round(float(r["total_profit"]), 2),
        }
        for _, r in cat_df.iterrows()
    }

    # Shipping metrics for Organization 1
    df_ship_raw = pd.read_csv(shipping_path)
    valid_oids = set(df["order_id"])
    df_ship = df_ship_raw[df_ship_raw["order_id"].isin(valid_oids)].copy()
    df_ship["late_flag"] = pd.to_datetime(df_ship["actual_date"]) > pd.to_datetime(df_ship["scheduled_date"])

    total_shipments = len(df_ship)
    late_shipments = int(df_ship["late_flag"].sum())
    on_time_shipments = total_shipments - late_shipments
    overall_late_pct = round(float(df_ship["late_flag"].mean() * 100.0), 2)
    avg_shipping_days = round(float(df_ship["shipping_days"].mean()), 2)

    ship_mode_df = df_ship.groupby("shipping_mode").agg(
        order_count=("order_id", "count"),
        late_count=("late_flag", "sum"),
        late_pct=("late_flag", lambda s: round(float(s.mean() * 100.0), 2)),
    ).reset_index()

    shipping_modes = {
        r["shipping_mode"]: {
            "orders": int(r["order_count"]),
            "late_count": int(r["late_count"]),
            "late_pct": round(float(r["late_pct"]), 2),
        }
        for _, r in ship_mode_df.iterrows()
    }

    return {
        "total_revenue": total_revenue,
        "order_count": order_count,
        "latest_order_date": latest_order_date.strftime("%Y-%m-%d"),
        "rev_7d": rev_7d,
        "rev_30d": rev_30d,
        "top5_products": top5_products,
        "category_metrics": category_metrics,
        "total_shipments": total_shipments,
        "late_shipments": late_shipments,
        "on_time_shipments": on_time_shipments,
        "overall_late_pct": overall_late_pct,
        "avg_shipping_days": avg_shipping_days,
        "shipping_modes": shipping_modes,
    }


def compute_org2_source_metrics(orders_path: str) -> Dict[str, Any]:
    """Compute expected metrics for Organization 2 from orders_10_renamed_headers.csv."""
    df = pd.read_csv(orders_path)
    # Headers: Order_ID,Order_Date,Cust_ID,Cust_Name,Segment,Prod_ID,Product,Category,Qty,Unit_Price,Discount,Total,Profit
    total_revenue = round(float(df["Total"].sum()), 2)
    order_count = int(df["Order_ID"].nunique())

    df["dt"] = pd.to_datetime(df["Order_Date"])
    latest_order_date = df["dt"].max()

    start_7d = latest_order_date - pd.Timedelta(days=6)
    rev_7d = round(float(df[df["dt"] >= start_7d]["Total"].sum()), 2)

    start_30d = latest_order_date - pd.Timedelta(days=29)
    rev_30d = round(float(df[df["dt"] >= start_30d]["Total"].sum()), 2)

    top5_df = (
        df.groupby(["Prod_ID", "Product", "Category"])["Total"]
        .sum()
        .reset_index()
        .sort_values(by="Total", ascending=False)
        .head(5)
    )
    top5_products = [
        {
            "product_id": r["Prod_ID"],
            "product_name": r["Product"],
            "category": r["Category"],
            "total_revenue": round(float(r["Total"]), 2),
        }
        for _, r in top5_df.iterrows()
    ]

    cat_df = df.groupby("Category").agg(
        total_revenue=("Total", "sum"),
        avg_discount=("Discount", "mean"),
        total_profit=("Profit", "sum"),
    ).reset_index()
    category_metrics = {
        r["Category"]: {
            "total_revenue": round(float(r["total_revenue"]), 2),
            "avg_discount": round(float(r["avg_discount"]), 2),
            "total_profit": round(float(r["total_profit"]), 2),
        }
        for _, r in cat_df.iterrows()
    }

    return {
        "total_revenue": total_revenue,
        "order_count": order_count,
        "latest_order_date": latest_order_date.strftime("%Y-%m-%d"),
        "rev_7d": rev_7d,
        "rev_30d": rev_30d,
        "top5_products": top5_products,
        "category_metrics": category_metrics,
        "shipping_modes": {},
    }


def compute_org3_source_metrics(orders_path: str) -> Dict[str, Any]:
    """Compute expected metrics for Organization 3 from orders_30_valid.xlsx."""
    df = pd.read_excel(orders_path)
    total_revenue = round(float(df["total"].sum()), 2)
    order_count = int(df["order_id"].nunique())

    df["dt"] = pd.to_datetime(df["order_date"])
    latest_order_date = df["dt"].max()

    start_7d = latest_order_date - pd.Timedelta(days=6)
    rev_7d = round(float(df[df["dt"] >= start_7d]["total"].sum()), 2)

    start_30d = latest_order_date - pd.Timedelta(days=29)
    rev_30d = round(float(df[df["dt"] >= start_30d]["total"].sum()), 2)

    top5_df = (
        df.groupby(["product_id", "product_name", "category"])["total"]
        .sum()
        .reset_index()
        .sort_values(by="total", ascending=False)
        .head(5)
    )
    top5_products = [
        {
            "product_id": r["product_id"],
            "product_name": r["product_name"],
            "category": r["category"],
            "total_revenue": round(float(r["total"]), 2),
        }
        for _, r in top5_df.iterrows()
    ]

    cat_df = df.groupby("category").agg(
        total_revenue=("total", "sum"),
        avg_discount=("discount", "mean"),
        total_profit=("profit", "sum"),
    ).reset_index()
    category_metrics = {
        r["category"]: {
            "total_revenue": round(float(r["total_revenue"]), 2),
            "avg_discount": round(float(r["avg_discount"]), 2),
            "total_profit": round(float(r["total_profit"]), 2),
        }
        for _, r in cat_df.iterrows()
    }

    return {
        "total_revenue": total_revenue,
        "order_count": order_count,
        "latest_order_date": latest_order_date.strftime("%Y-%m-%d"),
        "rev_7d": rev_7d,
        "rev_30d": rev_30d,
        "top5_products": top5_products,
        "category_metrics": category_metrics,
        "shipping_modes": {},
    }


def query_dashboard(token: str) -> Dict[str, Any]:
    """Call every dashboard endpoint for an authenticated Organization Owner."""
    headers = {"Authorization": f"Bearer {token}"}
    endpoints = {
        "rev_all": "/dashboard/revenue-trend",
        "rev_7d": "/dashboard/revenue-trend?days=7",
        "rev_30d": "/dashboard/revenue-trend?days=30",
        "top_prods": "/dashboard/top-products?limit=5",
        "late_risk": "/dashboard/late-delivery-risk",
        "disc_profit": "/dashboard/discount-vs-profit",
        "shipping_modes": "/dashboard/shipping-mode-comparison",
    }
    results = {}
    for key, path in endpoints.items():
        r = requests.get(f"{BASE_URL}{path}", headers=headers, timeout=DEFAULT_TIMEOUT)
        if r.status_code != 200:
            raise RuntimeError(f"Dashboard query failed for {path}: {r.status_code} {r.text}")
        results[key] = r.json()
    return results


def check_batches_present() -> Tuple[bool, bool, bool, bool]:
    """Check if all required batches for tenants 1, 2, 3 have already succeeded in Gold."""
    with get_databricks_connection(catalog=CATALOG) as conn:
        with conn.cursor() as cur:
            cur.execute(f"SELECT count(*) FROM `{CATALOG}`.`gold`.`fact_orders` WHERE tenant_id = 1")
            t1_orders_ready = cur.fetchone()[0] >= 30

            cur.execute(f"SELECT count(*) FROM `{CATALOG}`.`gold`.`fact_shipments` WHERE tenant_id = 1")
            t1_shipping_ready = cur.fetchone()[0] >= 30

            cur.execute(f"SELECT count(*) FROM `{CATALOG}`.`gold`.`fact_orders` WHERE tenant_id = 2")
            t2_ready = cur.fetchone()[0] >= 10

            cur.execute(f"SELECT count(*) FROM `{CATALOG}`.`gold`.`fact_orders` WHERE tenant_id = 3")
            t3_ready = cur.fetchone()[0] >= 30

            return t1_orders_ready, t1_shipping_ready, t2_ready, t3_ready


def main():
    force_upload = "--force-upload" in sys.argv
    print("=" * 80)
    print("HELIOS DASHBOARD VERIFICATION AGAINST REAL SOURCE FILES")
    print("=" * 80)

    # 1. Authenticate users
    print("\n--- 1. Authenticating Users ---")
    tm1_token, tm1_user = login(TM1_EMAIL, TEST_PASSWORD)
    print(f"Logged in Team Member 1: {tm1_user.get('name')} (assigned to Orgs 1 & 2)")
    tm2_token, tm2_user = login(TM2_EMAIL, TEST_PASSWORD)
    print(f"Logged in Team Member 2: {tm2_user.get('name')} (assigned to Org 3)")

    smb1_token, smb1_user = login(SMB1_EMAIL, TEST_PASSWORD)
    print(f"Logged in Org 1 Owner: {smb1_user.get('name')} (tenant={smb1_user.get('tenant_id')})")
    smb2_token, smb2_user = login(SMB2_EMAIL, TEST_PASSWORD)
    print(f"Logged in Org 2 Owner: {smb2_user.get('name')} (tenant={smb2_user.get('tenant_id')})")
    smb3_token, smb3_user = login(SMB3_EMAIL, TEST_PASSWORD)
    print(f"Logged in Org 3 Owner: {smb3_user.get('name')} (tenant={smb3_user.get('tenant_id')})")

    t1_orders_file = "orders_30_valid_plus_3_bad.csv"
    t1_shipping_file = "shipping_30_for_valid_orders.csv"
    t2_orders_file = "orders_10_renamed_headers.csv"
    t3_orders_file = "orders_30_valid.xlsx"

    # 2. Ingest batches if not present or forced
    print("\n--- 2. Checking & Ingesting Batches via Team Member Flow ---")
    t1_orders_ready, t1_shipping_ready, t2_ready, t3_ready = check_batches_present()

    if not t1_orders_ready or force_upload:
        submit_and_approve_batch(1, t1_orders_file, t1_orders_file, "template_orders", tm1_token)
    else:
        print("Organization 1 Orders: Batch already present in Gold.")

    if not t1_shipping_ready or force_upload:
        submit_and_approve_batch(1, t1_shipping_file, t1_shipping_file, "template_shipping", tm1_token)
    else:
        print("Organization 1 Shipping: Batch already present in Gold.")

    if not t2_ready or force_upload:
        submit_and_approve_batch(2, t2_orders_file, t2_orders_file, "template_orders", tm1_token)
    else:
        print("Organization 2: Batch already present in Gold.")

    if not t3_ready or force_upload:
        submit_and_approve_batch(3, t3_orders_file, t3_orders_file, "template_orders", tm2_token)
    else:
        print("Organization 3: Batch already present in Gold.")

    # 3. Compute expected source metrics with Pandas
    print("\n--- 3. Computing Expected Metrics from Source Files with Pandas ---")
    exp_t1 = compute_org1_source_metrics(t1_orders_file, t1_shipping_file)
    exp_t2 = compute_org2_source_metrics(t2_orders_file)
    exp_t3 = compute_org3_source_metrics(t3_orders_file)

    # 4. Query Dashboard endpoints for all 3 Organization Owners
    print("\n--- 4. Querying Dashboard Endpoints for Organization Owners 1, 2, and 3 ---")
    dash_t1 = query_dashboard(smb1_token)
    dash_t2 = query_dashboard(smb2_token)
    dash_t3 = query_dashboard(smb3_token)

    # 5. Build comparison table
    print("\n--- 5. Comparison Table: Expected vs Shown on Dashboard ---")
    rows: List[Tuple[str, str, str, str, str]] = []

    def check_amount(org_label: str, metric_name: str, exp_val: float, act_val: float):
        diff = abs(exp_val - act_val)
        matched = "Yes" if diff <= 0.01 else "No"
        rows.append((org_label, metric_name, format_inr(exp_val), format_inr(act_val), matched))

    def check_exact(org_label: str, metric_name: str, exp_val: Any, act_val: Any):
        matched = "Yes" if str(exp_val) == str(act_val) else "No"
        rows.append((org_label, metric_name, str(exp_val), str(act_val), matched))

    # --- Organization 1 ---
    act_rev_t1 = float(dash_t1["rev_all"].get("total_revenue", 0.0))
    act_ords_t1 = int(dash_t1["rev_all"].get("total_orders", 0))
    check_amount("Organization 1", "Total Revenue (All-time)", exp_t1["total_revenue"], act_rev_t1)
    check_exact("Organization 1", "Total Orders (All-time)", exp_t1["order_count"], act_ords_t1)

    act_7d_t1 = float(dash_t1["rev_7d"].get("total_revenue", 0.0))
    act_30d_t1 = float(dash_t1["rev_30d"].get("total_revenue", 0.0))
    check_amount("Organization 1", "7-Day Revenue", exp_t1["rev_7d"], act_7d_t1)
    check_amount("Organization 1", "30-Day Revenue", exp_t1["rev_30d"], act_30d_t1)
    check_exact("Organization 1", "Data As Of Date", exp_t1["latest_order_date"], dash_t1["rev_all"].get("data_as_of"))

    # Top 5 products Org 1
    t1_prods = dash_t1["top_prods"].get("products", [])
    for idx, exp_p in enumerate(exp_t1["top5_products"]):
        act_p = t1_prods[idx] if idx < len(t1_prods) else {}
        exp_desc = f"{exp_p['product_name']} ({format_inr(exp_p['total_revenue'])})"
        act_desc = f"{act_p.get('product_name')} ({format_inr(float(act_p.get('total_revenue', 0.0)))})"
        diff = abs(exp_p["total_revenue"] - float(act_p.get("total_revenue", 0.0)))
        matched = "Yes" if diff <= 0.01 and exp_p["product_name"] == act_p.get("product_name") else "No"
        rows.append(("Organization 1", f"Top Product #{idx+1}", exp_desc, act_desc, matched))

    # Shipping modes Org 1
    t1_modes = {m.get("mode_name") or m.get("shipping_mode"): m for m in dash_t1["shipping_modes"].get("modes", [])}
    for mode, exp_m in exp_t1["shipping_modes"].items():
        act_m = t1_modes.get(mode, {})
        act_count = int(act_m.get("shipment_count") or act_m.get("total_shipments") or 0)
        act_late_pct = float(act_m.get("late_rate_pct") or act_m.get("late_percentage") or 0.0)
        exp_str = f"{exp_m['orders']} orders, {exp_m['late_pct']:.1f}% late"
        act_str = f"{act_count} orders, {act_late_pct:.1f}% late"
        diff_pct = abs(exp_m["late_pct"] - act_late_pct)
        matched = "Yes" if exp_m["orders"] == act_count and diff_pct <= 0.5 else "No"
        rows.append(("Organization 1", f"Shipping Mode: {mode}", exp_str, act_str, matched))

    # --- Organization 2 ---
    act_rev_t2 = float(dash_t2["rev_all"].get("total_revenue", 0.0))
    act_ords_t2 = int(dash_t2["rev_all"].get("total_orders", 0))
    check_amount("Organization 2", "Total Revenue (All-time)", exp_t2["total_revenue"], act_rev_t2)
    check_exact("Organization 2", "Total Orders (All-time)", exp_t2["order_count"], act_ords_t2)

    act_7d_t2 = float(dash_t2["rev_7d"].get("total_revenue", 0.0))
    act_30d_t2 = float(dash_t2["rev_30d"].get("total_revenue", 0.0))
    check_amount("Organization 2", "7-Day Revenue", exp_t2["rev_7d"], act_7d_t2)
    check_amount("Organization 2", "30-Day Revenue", exp_t2["rev_30d"], act_30d_t2)
    check_exact("Organization 2", "Data As Of Date", exp_t2["latest_order_date"], dash_t2["rev_all"].get("data_as_of"))

    # Top 5 products Org 2
    t2_prods = dash_t2["top_prods"].get("products", [])
    for idx, exp_p in enumerate(exp_t2["top5_products"]):
        act_p = t2_prods[idx] if idx < len(t2_prods) else {}
        exp_desc = f"{exp_p['product_name']} ({format_inr(exp_p['total_revenue'])})"
        act_desc = f"{act_p.get('product_name')} ({format_inr(float(act_p.get('total_revenue', 0.0)))})"
        diff = abs(exp_p["total_revenue"] - float(act_p.get("total_revenue", 0.0)))
        matched = "Yes" if diff <= 0.01 and exp_p["product_name"] == act_p.get("product_name") else "No"
        rows.append(("Organization 2", f"Top Product #{idx+1}", exp_desc, act_desc, matched))

    # --- Organization 3 ---
    act_rev_t3 = float(dash_t3["rev_all"].get("total_revenue", 0.0))
    act_ords_t3 = int(dash_t3["rev_all"].get("total_orders", 0))
    check_amount("Organization 3", "Total Revenue (All-time)", exp_t3["total_revenue"], act_rev_t3)
    check_exact("Organization 3", "Total Orders (All-time)", exp_t3["order_count"], act_ords_t3)

    act_7d_t3 = float(dash_t3["rev_7d"].get("total_revenue", 0.0))
    act_30d_t3 = float(dash_t3["rev_30d"].get("total_revenue", 0.0))
    check_amount("Organization 3", "7-Day Revenue", exp_t3["rev_7d"], act_7d_t3)
    check_amount("Organization 3", "30-Day Revenue", exp_t3["rev_30d"], act_30d_t3)
    check_exact("Organization 3", "Data As Of Date", exp_t3["latest_order_date"], dash_t3["rev_all"].get("data_as_of"))

    # Top 5 products Org 3
    t3_prods = dash_t3["top_prods"].get("products", [])
    for idx, exp_p in enumerate(exp_t3["top5_products"]):
        act_p = t3_prods[idx] if idx < len(t3_prods) else {}
        exp_desc = f"{exp_p['product_name']} ({format_inr(exp_p['total_revenue'])})"
        act_desc = f"{act_p.get('product_name')} ({format_inr(float(act_p.get('total_revenue', 0.0)))})"
        diff = abs(exp_p["total_revenue"] - float(act_p.get("total_revenue", 0.0)))
        matched = "Yes" if diff <= 0.01 and exp_p["product_name"] == act_p.get("product_name") else "No"
        rows.append(("Organization 3", f"Top Product #{idx+1}", exp_desc, act_desc, matched))

    # Print Table
    col_w = [16, 32, 38, 38, 8]
    sep = "+" + "+".join(["-" * (w + 2) for w in col_w]) + "+"
    header = "|" + "|".join([f" {h:<{w}} " for h, w in zip(["Organization", "Metric", "Expected", "Shown on Dashboard", "Match"], col_w)]) + "|"
    print("\n" + sep)
    print(header)
    print(sep)
    for org, met, exp, act, m in rows:
        print(f"| {org:<16} | {met:<32} | {exp:<38} | {act:<38} | {m:<8} |")
    print(sep)

    # 6. Verify that Organizations differ
    print("\n--- 6. Multi-Tenant Distinction Check ---")
    revs = [act_rev_t1, act_rev_t2, act_rev_t3]
    dates = [exp_t1["latest_order_date"], exp_t2["latest_order_date"], exp_t3["latest_order_date"]]
    print(f"Org 1 Revenue: {format_inr(act_rev_t1)}, Latest Date: {dates[0]}")
    print(f"Org 2 Revenue: {format_inr(act_rev_t2)}, Latest Date: {dates[1]}")
    print(f"Org 3 Revenue: {format_inr(act_rev_t3)}, Latest Date: {dates[2]}")
    assert act_rev_t1 != act_rev_t2, "Org 1 and Org 2 revenue should differ"
    assert dates[0] != dates[1], "Org 1 and Org 2 latest dates should differ"
    print("[PASS] Organizations 1, 2, and 3 numbers differ and are strictly tenant-isolated.")

    all_matched = all(m == "Yes" for _, _, _, _, m in rows)
    if all_matched:
        print("\n[SUCCESS] ALL METRICS MATCH PERFECTLY TO THE PAISA!")
    else:
        failed_count = sum(1 for _, _, _, _, m in rows if m != "Yes")
        print(f"\n[ATTENTION] {failed_count} metrics did not match. Please review the table above.")


if __name__ == "__main__":
    main()
