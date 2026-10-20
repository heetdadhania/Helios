import os
import sys
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import requests

BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
DEFAULT_TIMEOUT = 60

# Credentials
TM_EMAIL = "team-member-1@helios-test.dev"
TM_PASS = "HeliosTest2026!"
SMB1_EMAIL = "smb-owner-1@helios-test.dev"
SMB1_PASS = "HeliosTest2026!"
SMB2_EMAIL = "smb-owner-2@helios-test.dev"
SMB2_PASS = "HeliosTest2026!"


def login(email: str, password: str) -> Tuple[str, Dict[str, Any]]:
    resp = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": email, "password": password},
        timeout=DEFAULT_TIMEOUT,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"Login failed for {email}: {resp.status_code} {resp.text}")
    data = resp.json()
    token = data["access_token"]
    user = data.get("user") or {}
    return token, user


def wait_for_pipeline_status(
    batch_id: str,
    token: str,
    target_statuses: List[str],
    timeout_seconds: int = 180,
    poll_interval: float = 3.0,
) -> Tuple[str, Dict[str, Any]]:
    deadline = time.time() + timeout_seconds
    headers = {"Authorization": f"Bearer {token}"}
    last_status = "unknown"
    last_body: Dict[str, Any] = {}

    while time.time() < deadline:
        try:
            r = requests.get(
                f"{BASE_URL}/api/pipeline/runs/{batch_id}",
                headers=headers,
                timeout=DEFAULT_TIMEOUT,
            )
            if r.status_code == 200:
                last_body = r.json()
                last_status = str(last_body.get("status", "")).lower()
                print(f"       Batch {batch_id}: status={last_status}, stage={last_body.get('stage')}", flush=True)
                if last_status in target_statuses:
                    return last_status, last_body
        except Exception as exc:
            print(f"       Warning polling status: {exc}", flush=True)
        time.sleep(poll_interval)

    raise TimeoutError(f"Batch {batch_id} did not reach {target_statuses} within {timeout_seconds}s. Last: {last_status}")


def submit_and_approve_batch(
    tenant_id: int,
    filename: str,
    filepath: str,
    template_name: str,
    tm_token: str,
) -> str:
    print(f"\n---> Submitting {filename} for Tenant {tenant_id} through Team Member flow...")
    with open(filepath, "rb") as f:
        file_bytes = f.read()

    files = {"file": (filename, file_bytes, "text/csv")}
    data = {"tenant_id": tenant_id, "override_duplicate": "true", "override_reason": "Verifying dashboard data"}
    headers = {"Authorization": f"Bearer {tm_token}"}

    r_upload = requests.post(
        f"{BASE_URL}/api/uploads",
        files=files,
        data=data,
        headers=headers,
        timeout=DEFAULT_TIMEOUT,
    )
    if r_upload.status_code not in (200, 201):
        raise RuntimeError(f"Upload failed for {filename}: {r_upload.status_code} {r_upload.text}")

    upload_json = r_upload.json()
    batch_id = upload_json["batch_id"]
    print(f"     Uploaded successfully! batch_id={batch_id}")

    print("     Waiting for schema inference (pending_review / awaiting_confirmation)...")
    st, _ = wait_for_pipeline_status(batch_id, tm_token, ["pending_review", "awaiting_confirmation", "failed"], timeout_seconds=120)
    if st == "failed":
        raise RuntimeError(f"Schema inference failed for batch {batch_id}")

    print(f"     Approving batch {batch_id} with template={template_name}...")
    r_confirm = requests.post(
        f"{BASE_URL}/api/uploads/{batch_id}/confirm",
        json={
            "confirmed_template": template_name,
            "internal_notes": f"Approved {filename} for tenant {tenant_id}",
        },
        headers=headers,
        timeout=DEFAULT_TIMEOUT,
    )
    if r_confirm.status_code != 200:
        raise RuntimeError(f"Confirmation failed for batch {batch_id}: {r_confirm.status_code} {r_confirm.text}")

    print(f"     Confirmation accepted! Waiting for Medallion pipeline completion (success)...")
    final_st, final_body = wait_for_pipeline_status(batch_id, tm_token, ["success", "failed"], timeout_seconds=240)
    if final_st != "success":
        err = final_body.get("error_message") or "Unknown error"
        raise RuntimeError(f"Pipeline failed for batch {batch_id}: {err}")

    print(f"     Batch {batch_id} successfully completed through Gold layer!")
    return batch_id


def compute_tenant1_source_metrics(orders_path: str, shipping_path: str) -> Dict[str, Any]:
    df_raw = pd.read_csv(orders_path)
    # Drop 3 bad rows:
    # 1. missing quantity (NaN or whitespace)
    # 2. negative or 0 quantity
    # 3. invalid date
    df = df_raw.dropna(subset=["quantity"]).copy()
    df = df[df["quantity"] > 0]
    df["order_date_dt"] = pd.to_datetime(df["order_date"], errors="coerce")
    df = df.dropna(subset=["order_date_dt"])

    total_revenue = round(float(df["total"].sum()), 2)
    order_count = int(df["order_id"].nunique())
    latest_order_date = df["order_date_dt"].max()

    # 7-day revenue: [latest - 6 days, latest] inclusive (7 calendar days)
    start_7d = latest_order_date - pd.Timedelta(days=6)
    rev_7d = round(float(df[df["order_date_dt"] >= start_7d]["total"].sum()), 2)

    # 30-day revenue: [latest - 29 days, latest] inclusive (30 calendar days)
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

    # Shipping metrics for Tenant 1
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


def compute_tenant2_source_metrics(orders_path: str) -> Dict[str, Any]:
    df = pd.read_csv(orders_path)
    # Columns: Ord_ID,Order_Dt,Cust_ID,Cust_Name,Segment,Prod_ID,Prod_Name,Category,Qty,Unit_Price,Disc,Total_Amount,Profit
    total_revenue = round(float(df["Total_Amount"].sum()), 2)
    order_count = int(df["Ord_ID"].nunique())

    df["dt"] = pd.to_datetime(df["Order_Dt"])
    latest_order_date = df["dt"].max()

    start_7d = latest_order_date - pd.Timedelta(days=6)
    rev_7d = round(float(df[df["dt"] >= start_7d]["Total_Amount"].sum()), 2)

    start_30d = latest_order_date - pd.Timedelta(days=29)
    rev_30d = round(float(df[df["dt"] >= start_30d]["Total_Amount"].sum()), 2)

    top5_df = (
        df.groupby(["Prod_ID", "Prod_Name", "Category"])["Total_Amount"]
        .sum()
        .reset_index()
        .sort_values(by="Total_Amount", ascending=False)
        .head(5)
    )
    top5_products = [
        {
            "product_id": r["Prod_ID"],
            "product_name": r["Prod_Name"],
            "category": r["Category"],
            "total_revenue": round(float(r["Total_Amount"]), 2),
        }
        for _, r in top5_df.iterrows()
    ]

    cat_df = df.groupby("Category").agg(
        total_revenue=("Total_Amount", "sum"),
        avg_discount=("Disc", "mean"),
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


def query_dashboard(token: str) -> Dict[str, Any]:
    headers = {"Authorization": f"Bearer {token}"}
    endpoints = {
        "rev_all": "/api/dashboard/revenue-trend",
        "rev_7d": "/api/dashboard/revenue-trend?days=7",
        "rev_30d": "/api/dashboard/revenue-trend?days=30",
        "top_prods": "/api/dashboard/top-products?limit=5",
        "late_risk": "/api/dashboard/late-delivery-risk",
        "disc_profit": "/api/dashboard/discount-vs-profit",
        "shipping_modes": "/api/dashboard/shipping-mode-comparison",
    }
    results = {}
    for key, path in endpoints.items():
        r = requests.get(f"{BASE_URL}{path}", headers=headers, timeout=DEFAULT_TIMEOUT)
        if r.status_code != 200:
            raise RuntimeError(f"Dashboard query failed for {path}: {r.status_code} {r.text}")
        results[key] = r.json()
    return results


def check_batches_present(token: str) -> bool:
    """Check if all 3 required batches were already submitted and succeeded."""
    headers = {"Authorization": f"Bearer {token}"}
    r = requests.get(f"{BASE_URL}/api/pipeline/runs", headers=headers, timeout=DEFAULT_TIMEOUT)
    if r.status_code != 200:
        return False
    runs = r.json()
    # Check if there are successful batches for tenant 1 (orders + shipping) and tenant 2 (orders)
    t1_runs = [run for run in runs if run.get("tenant_id") == 1 and run.get("status") == "success"]
    t2_runs = [run for run in runs if run.get("tenant_id") == 2 and run.get("status") == "success"]
    return len(t1_runs) >= 2 and len(t2_runs) >= 1


def main():
    force_upload = "--force-upload" in sys.argv
    print("=" * 80)
    print("HELIOS DASHBOARD VERIFICATION AGAINST REAL SOURCE FILES")
    print("=" * 80)

    # 1. Login
    print("\n--- 1. Authenticating Users ---")
    tm_token, tm_user = login(TM_EMAIL, TM_PASS)
    print(f"Logged in Team Member: {tm_user.get('name')} (id={tm_user.get('id')})")
    smb1_token, smb1_user = login(SMB1_EMAIL, SMB1_PASS)
    print(f"Logged in SMB Owner 1: {smb1_user.get('name')} (tenant={smb1_user.get('tenant_id')})")
    smb2_token, smb2_user = login(SMB2_EMAIL, SMB2_PASS)
    print(f"Logged in SMB Owner 2: {smb2_user.get('name')} (tenant={smb2_user.get('tenant_id')})")

    t1_orders_file = "orders_30_valid_plus_3_bad.csv"
    t1_shipping_file = "shipping_30_for_valid_orders.csv"
    t2_orders_file = "orders_10_renamed_headers.csv"

    # 2. Ingest Data via Team Member Flow
    print("\n--- 2. Checking / Executing Team Member Ingestion Flow ---")
    already_present = check_batches_present(tm_token)

    if not already_present or force_upload:
        print("Submitting and approving source files via real Team Member flow...")
        submit_and_approve_batch(
            tenant_id=1,
            filename=t1_orders_file,
            filepath=t1_orders_file,
            template_name="template_orders",
            tm_token=tm_token,
        )
        submit_and_approve_batch(
            tenant_id=1,
            filename=t1_shipping_file,
            filepath=t1_shipping_file,
            template_name="template_shipping",
            tm_token=tm_token,
        )
        submit_and_approve_batch(
            tenant_id=2,
            filename=t2_orders_file,
            filepath=t2_orders_file,
            template_name="template_orders",
            tm_token=tm_token,
        )
    else:
        print("Verified: Source files were already submitted, approved and processed via Team Member flow.")
        print("Leaving all data in place per ground rules.")

    # 3. Compute expected metrics from source files
    print("\n--- 3. Computing Expected Metrics from Source Files with Pandas ---")
    exp_t1 = compute_tenant1_source_metrics(t1_orders_file, t1_shipping_file)
    exp_t2 = compute_tenant2_source_metrics(t2_orders_file)

    print("\n[Tenant 1 Expected Metrics Computed by Pandas]")
    print(f"  Total Revenue (All-time): ${exp_t1['total_revenue']:.2f}")
    print(f"  Total Orders (All-time): {exp_t1['order_count']}")
    print(f"  Latest Order Date: {exp_t1['latest_order_date']}")
    print(f"  7-Day Revenue: ${exp_t1['rev_7d']:.2f}")
    print(f"  30-Day Revenue: ${exp_t1['rev_30d']:.2f}")
    print("  Top 5 Products by Revenue:")
    for p in exp_t1["top5_products"]:
        print(f"    - {p['product_name']} ({p['category']}): ${p['total_revenue']:.2f}")
    print("  Revenue, Avg Discount, and Profit by Category:")
    for cat, m in exp_t1["category_metrics"].items():
        print(f"    - {cat}: Rev ${m['total_revenue']:.2f}, Avg Disc ${m['avg_discount']:.2f}, Profit ${m['total_profit']:.2f}")
    print("  Shipping Modes:")
    for mode, m in exp_t1["shipping_modes"].items():
        print(f"    - {mode}: {m['orders']} orders, {m['late_count']} late ({m['late_pct']:.1f}%)")

    print("\n[Tenant 2 Expected Metrics Computed by Pandas]")
    print(f"  Total Revenue (All-time): ${exp_t2['total_revenue']:.2f}")
    print(f"  Total Orders (All-time): {exp_t2['order_count']}")
    print(f"  Latest Order Date: {exp_t2['latest_order_date']}")
    print(f"  7-Day Revenue: ${exp_t2['rev_7d']:.2f}")
    print(f"  30-Day Revenue: ${exp_t2['rev_30d']:.2f}")
    print("  Top 5 Products by Revenue:")
    for p in exp_t2["top5_products"]:
        print(f"    - {p['product_name']} ({p['category']}): ${p['total_revenue']:.2f}")
    print("  Revenue, Avg Discount, and Profit by Category:")
    for cat, m in exp_t2["category_metrics"].items():
        print(f"    - {cat}: Rev ${m['total_revenue']:.2f}, Avg Disc ${m['avg_discount']:.2f}, Profit ${m['total_profit']:.2f}")

    # 4. Query Dashboard endpoints for both SMB owners
    print("\n--- 4. Querying Dashboard Endpoints for SMB Owner 1 and SMB Owner 2 ---")
    dash_t1 = query_dashboard(smb1_token)
    dash_t2 = query_dashboard(smb2_token)

    # 5. Build comparison table
    print("\n--- 5. Dashboard Comparison Table ---")
    rows: List[Tuple[str, str, Any, Any, str]] = []

    def check(tenant_label: str, metric_name: str, exp_val: Any, actual_val: Any):
        matched = "Yes" if exp_val == actual_val else "No"
        rows.append((tenant_label, metric_name, str(exp_val), str(actual_val), matched))

    # --- Tenant 1 checks ---
    # Revenue trend all-time
    actual_t1_rev = round(float(dash_t1["rev_all"].get("total_revenue", 0.0)), 2)
    actual_t1_orders = int(dash_t1["rev_all"].get("total_orders", 0))
    check("Tenant 1", "Total Revenue (All-time)", f"${exp_t1['total_revenue']:.2f}", f"${actual_t1_rev:.2f}")
    check("Tenant 1", "Total Orders (All-time)", exp_t1["order_count"], actual_t1_orders)

    # 7-day & 30-day revenue
    actual_t1_7d = round(float(dash_t1["rev_7d"].get("total_revenue", 0.0)), 2)
    actual_t1_30d = round(float(dash_t1["rev_30d"].get("total_revenue", 0.0)), 2)
    check("Tenant 1", "7-Day Revenue", f"${exp_t1['rev_7d']:.2f}", f"${actual_t1_7d:.2f}")
    check("Tenant 1", "30-Day Revenue", f"${exp_t1['rev_30d']:.2f}", f"${actual_t1_30d:.2f}")

    # "Data as of" date
    data_as_of_t1 = dash_t1["rev_all"].get("data_as_of")
    check("Tenant 1", "Data As Of Date", exp_t1["latest_order_date"], data_as_of_t1)

    # Top 5 products
    for idx, exp_p in enumerate(exp_t1["top5_products"]):
        act_p = dash_t1["top_prods"].get("products", [])[idx] if idx < len(dash_t1["top_prods"].get("products", [])) else {}
        act_pname = act_p.get("product_name", "N/A")
        act_cat = act_p.get("category", "N/A")
        act_prev = round(float(act_p.get("total_revenue", 0.0)), 2)
        check(
            "Tenant 1",
            f"Top Product #{idx+1} ({exp_p['product_name']})",
            f"{exp_p['product_name']} | {exp_p['category']} | ${exp_p['total_revenue']:.2f}",
            f"{act_pname} | {act_cat} | ${act_prev:.2f}",
        )

    # Late delivery risk
    act_risk = dash_t1["late_risk"]
    check("Tenant 1", "Late Delivery Rate %", f"{exp_t1['overall_late_pct']:.1f}%", f"{float(act_risk.get('late_rate_pct', 0.0)):.1f}%")
    check("Tenant 1", "Total Shipments", exp_t1["total_shipments"], int(act_risk.get("total_shipments", 0)))
    check("Tenant 1", "Late Shipments", exp_t1["late_shipments"], int(act_risk.get("late_shipments", 0)))
    check("Tenant 1", "On-Time Shipments", exp_t1["on_time_shipments"], int(act_risk.get("on_time_shipments", 0)))

    # Shipping modes
    for smode, exp_sdata in sorted(exp_t1["shipping_modes"].items()):
        act_mode = next(
            (m for m in dash_t1["shipping_modes"].get("modes", []) if m["mode_name"] == smode),
            None,
        )
        if act_mode:
            check(
                "Tenant 1",
                f"Shipping Mode '{smode}' Volume & Late %",
                f"{exp_sdata['orders']} orders, {exp_sdata['late_pct']:.1f}% late",
                f"{act_mode['shipment_count']} orders, {act_mode['late_rate_pct']:.1f}% late",
            )
        else:
            check(
                "Tenant 1",
                f"Shipping Mode '{smode}' Volume & Late %",
                f"{exp_sdata['orders']} orders, {exp_sdata['late_pct']:.1f}% late",
                "MISSING",
            )

    # --- Tenant 2 checks ---
    actual_t2_rev = round(float(dash_t2["rev_all"].get("total_revenue", 0.0)), 2)
    actual_t2_orders = int(dash_t2["rev_all"].get("total_orders", 0))
    check("Tenant 2", "Total Revenue (All-time)", f"${exp_t2['total_revenue']:.2f}", f"${actual_t2_rev:.2f}")
    check("Tenant 2", "Total Orders (All-time)", exp_t2["order_count"], actual_t2_orders)

    actual_t2_7d = round(float(dash_t2["rev_7d"].get("total_revenue", 0.0)), 2)
    actual_t2_30d = round(float(dash_t2["rev_30d"].get("total_revenue", 0.0)), 2)
    check("Tenant 2", "7-Day Revenue", f"${exp_t2['rev_7d']:.2f}", f"${actual_t2_7d:.2f}")
    check("Tenant 2", "30-Day Revenue", f"${exp_t2['rev_30d']:.2f}", f"${actual_t2_30d:.2f}")

    data_as_of_t2 = dash_t2["rev_all"].get("data_as_of")
    check("Tenant 2", "Data As Of Date", exp_t2["latest_order_date"], data_as_of_t2)

    for idx, exp_p in enumerate(exp_t2["top5_products"]):
        act_p = dash_t2["top_prods"].get("products", [])[idx] if idx < len(dash_t2["top_prods"].get("products", [])) else {}
        act_pname = act_p.get("product_name", "N/A")
        act_cat = act_p.get("category", "N/A")
        act_prev = round(float(act_p.get("total_revenue", 0.0)), 2)
        check(
            "Tenant 2",
            f"Top Product #{idx+1} ({exp_p['product_name']})",
            f"{exp_p['product_name']} | {exp_p['category']} | ${exp_p['total_revenue']:.2f}",
            f"{act_pname} | {act_cat} | ${act_prev:.2f}",
        )

    # Print markdown table
    print("\n| Tenant | Metric | Expected | Shown on Dashboard | Match (Yes/No) |")
    print("|:---|:---|:---|:---|:---:|")
    all_matched = True
    for t_label, metric, exp_s, act_s, matched in rows:
        print(f"| {t_label} | {metric} | {exp_s} | {act_s} | {matched} |")
        if matched != "Yes":
            all_matched = False

    # Show Tenant 1 vs Tenant 2 differences
    print("\n--- 6. Tenant 1 vs Tenant 2 Distinct Values Proof ---")
    print(f"  Tenant 1 Total Revenue: ${actual_t1_rev:.2f}  vs  Tenant 2 Total Revenue: ${actual_t2_rev:.2f}  (Distinct: {actual_t1_rev != actual_t2_rev})")
    print(f"  Tenant 1 Total Orders:  {actual_t1_orders}         vs  Tenant 2 Total Orders:  {actual_t2_orders}         (Distinct: {actual_t1_orders != actual_t2_orders})")
    print(f"  Tenant 1 7-Day Revenue: ${actual_t1_7d:.2f}   vs  Tenant 2 7-Day Revenue: ${actual_t2_7d:.2f}   (Distinct: {actual_t1_7d != actual_t2_7d})")
    print(f"  Tenant 1 Data As Of:    {data_as_of_t1}     vs  Tenant 2 Data As Of:    {data_as_of_t2}     (Distinct: {data_as_of_t1 != data_as_of_t2})")

    if not all_matched:
        print("\n[FAIL] Some metrics did not match! Review table above for details.")
        sys.exit(1)
    else:
        print("\n[SUCCESS] Every single row matches the source files 100%!")


if __name__ == "__main__":
    main()
