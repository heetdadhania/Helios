#!/usr/bin/env python3
"""
Verify Demo Data Dashboards across all 10 organizations.
Performs verification for:
  - total revenue
  - order count
  - average order value
  - total profit
  - total discount
  - top 5 products by revenue
  - revenue by category
  - shipments by mode
  - late delivery percent
  - 7 and 30 day revenue relative to the latest order date
Amounts match when the difference is at most ₹0.01.
Prints one table per organization (metric, expected, shown, match)
and a final summary of how many rows matched.
"""

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple
import requests
from dotenv import load_dotenv

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(REPO_ROOT / ".env")

BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")
PASSWORD = os.getenv("TEST_ACCOUNT_PASSWORD", "TestPass123!")

EXPECTED_TOTALS_PATH = REPO_ROOT / "scripts" / "data" / "helios_indian_data" / "expected_totals.json"


def get_owner_token(email: str) -> str:
    resp = requests.post(
        f"{BASE_URL}/api/v1/auth/login",
        json={"email": email, "password": PASSWORD},
        timeout=20,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"Login failed for {email} ({resp.status_code}): {resp.text}")
    return resp.json()["access_token"]


def float_match(val1: float, val2: float, tolerance: float = 0.01) -> bool:
    return abs(float(val1) - float(val2)) <= tolerance


def run_verification() -> int:
    if not EXPECTED_TOTALS_PATH.exists():
        print(f"Error: {EXPECTED_TOTALS_PATH} not found.")
        return 1

    with open(EXPECTED_TOTALS_PATH, "r", encoding="utf-8") as f:
        expected_data = json.load(f)

    total_checks = 0
    total_matches = 0

    print("=" * 80)
    print("HELIOS DEMO DATA DASHBOARDS VERIFICATION (ALL 10 ORGANIZATIONS)")
    print("=" * 80)

    for org_id in range(1, 11):
        org_str = str(org_id)
        if org_str not in expected_data:
            print(f"Skipping Org {org_id}: not in expected_totals.json")
            continue

        exp = expected_data[org_str]
        org_name = exp.get("organization", f"Org {org_id}")
        email = f"smb-owner-{org_id}@helios-test.dev"

        try:
            token = get_owner_token(email)
        except Exception as e:
            print(f"Failed to authenticate as {email}: {e}")
            continue

        headers = {"Authorization": f"Bearer {token}"}

        # 1. Dashboard summary
        sum_resp = requests.get(f"{BASE_URL}/api/v1/dashboard/summary", headers=headers, timeout=60).json()
        # 2. Revenue trend (7 days & 30 days)
        rev7_resp = requests.get(f"{BASE_URL}/api/v1/dashboard/revenue-trend?days=7", headers=headers, timeout=60).json()
        rev30_resp = requests.get(f"{BASE_URL}/api/v1/dashboard/revenue-trend?days=30", headers=headers, timeout=60).json()
        # 3. Discount vs profit
        disc_resp = requests.get(f"{BASE_URL}/api/v1/dashboard/discount-vs-profit", headers=headers, timeout=60).json()
        # 4. Top products (top 5 and top 100 for category rollups)
        top5_resp = requests.get(f"{BASE_URL}/api/v1/dashboard/top-products?limit=5", headers=headers, timeout=60).json()
        top100_resp = requests.get(f"{BASE_URL}/api/v1/dashboard/top-products?limit=100", headers=headers, timeout=60).json()
        # 5. Shipping mode comparison
        ship_resp = requests.get(f"{BASE_URL}/api/v1/dashboard/shipping-mode-comparison", headers=headers, timeout=60).json()
        # 6. Late delivery risk
        late_resp = requests.get(f"{BASE_URL}/api/v1/dashboard/late-delivery-risk", headers=headers, timeout=60).json()

        # Collect metrics
        rows: List[Tuple[str, str, str, bool]] = []

        # Total Revenue
        exp_rev = float(exp["revenue_total"])
        act_rev = float(sum_resp.get("total_revenue", 0.0) or 0.0)
        m = float_match(exp_rev, act_rev)
        rows.append(("Total Revenue", f"₹{exp_rev:,.2f}", f"₹{act_rev:,.2f}", m))

        # Order Count
        exp_cnt = int(exp["valid_orders"])
        act_cnt = int(sum_resp.get("order_count", 0) or 0)
        m = (exp_cnt == act_cnt)
        rows.append(("Order Count", str(exp_cnt), str(act_cnt), m))

        # Average Order Value
        exp_aov = float(exp["avg_order_value"])
        act_aov = float(sum_resp.get("average_order_value", 0.0) or 0.0)
        m = float_match(exp_aov, act_aov)
        rows.append(("Average Order Value", f"₹{exp_aov:,.2f}", f"₹{act_aov:,.2f}", m))

        # Total Profit (from discount-vs-profit bands)
        exp_prof = float(exp["total_profit"])
        act_prof = sum(float(b.get("total_profit", 0.0) or 0.0) for b in disc_resp.get("bands", []))
        m = float_match(exp_prof, act_prof)
        rows.append(("Total Profit", f"₹{exp_prof:,.2f}", f"₹{act_prof:,.2f}", m))

        # Total Discount (from discount-vs-profit bands)
        exp_disc = float(exp["total_discount"])
        act_disc = sum(float(b.get("total_discount", 0.0) or 0.0) for b in disc_resp.get("bands", []))
        m = float_match(exp_disc, act_disc)
        rows.append(("Total Discount", f"₹{exp_disc:,.2f}", f"₹{act_disc:,.2f}", m))

        # 7-Day Revenue
        exp_rev7 = float(exp["revenue_last_7_days"])
        act_rev7 = float(rev7_resp.get("total_revenue", 0.0) or 0.0)
        m = float_match(exp_rev7, act_rev7)
        rows.append(("7-Day Revenue", f"₹{exp_rev7:,.2f}", f"₹{act_rev7:,.2f}", m))

        # 30-Day Revenue
        exp_rev30 = float(exp["revenue_last_30_days"])
        act_rev30 = float(rev30_resp.get("total_revenue", 0.0) or 0.0)
        m = float_match(exp_rev30, act_rev30)
        rows.append(("30-Day Revenue", f"₹{exp_rev30:,.2f}", f"₹{act_rev30:,.2f}", m))

        # Late Delivery Percent
        exp_late = float(exp["late_delivery_percent"])
        act_late = float(sum_resp.get("late_delivery_percentage", 0.0) or 0.0)
        m = float_match(exp_late, act_late)
        rows.append(("Late Delivery Pct", f"{exp_late:.2f}%", f"{act_late:.2f}%", m))

        # Top 5 Products
        act_top_prods = top5_resp.get("products", [])
        for idx, item in enumerate(exp.get("top5_products_by_revenue", []), 1):
            exp_pname, exp_prev_str = item[0], item[1]
            exp_prev = float(exp_prev_str)
            if idx - 1 < len(act_top_prods):
                act_p = act_top_prods[idx - 1]
                act_pname = act_p.get("product_name", "")
                act_prev = float(act_p.get("total_revenue", 0.0) or 0.0)
                m = (exp_pname == act_pname) and float_match(exp_prev, act_prev)
                rows.append((f"Top {idx} Product: {exp_pname}", f"₹{exp_prev:,.2f}", f"{act_pname}: ₹{act_prev:,.2f}", m))
            else:
                rows.append((f"Top {idx} Product: {exp_pname}", f"₹{exp_prev:,.2f}", "Missing", False))

        # Revenue by Category
        act_cat_rev: Dict[str, float] = {}
        for p in top100_resp.get("products", []):
            cat = p.get("category") or "General"
            act_cat_rev[cat] = act_cat_rev.get(cat, 0.0) + float(p.get("total_revenue", 0.0) or 0.0)

        for cat, exp_cat_rev_str in sorted(exp.get("revenue_by_category", {}).items()):
            exp_cat_rev = float(exp_cat_rev_str)
            act_c_rev = act_cat_rev.get(cat, 0.0)
            m = float_match(exp_cat_rev, act_c_rev)
            rows.append((f"Category Rev: {cat}", f"₹{exp_cat_rev:,.2f}", f"₹{act_c_rev:,.2f}", m))

        # Shipments by Mode
        act_modes = {m.get("mode_name"): int(m.get("shipment_count", 0)) for m in ship_resp.get("modes", [])}
        for mode, exp_mode_cnt in sorted(exp.get("shipments_by_mode", {}).items()):
            act_m_cnt = act_modes.get(mode, 0)
            m = (exp_mode_cnt == act_m_cnt)
            rows.append((f"Shipments: {mode}", str(exp_mode_cnt), str(act_m_cnt), m))

        # Print Table for Organization
        print(f"\nORGANIZATION {org_id}: {org_name} ({exp.get('industry', '')})")
        print(f"{'-' * 80}")
        print(f"{'Metric':<34} | {'Expected':<18} | {'Shown':<18} | {'Match':<6}")
        print(f"{'-' * 34}-+-{'-' * 18}-+-{'-' * 18}-+-{'-' * 6}")
        org_matches = 0
        for metric, expected_val, shown_val, is_match in rows:
            status = "PASS" if is_match else "FAIL"
            if is_match:
                org_matches += 1
                total_matches += 1
            total_checks += 1
            print(f"{metric:<34} | {expected_val:<18} | {shown_val:<18} | {status:<6}")

        print(f"{'-' * 80}")
        print(f"Organization {org_id} Result: {org_matches}/{len(rows)} metrics matched ({(org_matches/len(rows))*100:.1f}%)")

    print("\n" + "=" * 80)
    print("FINAL SUMMARY OF DASHBOARD VERIFICATION")
    print(f"Total metrics checked: {total_checks}")
    print(f"Total metrics matched: {total_matches}")
    pct = (total_matches / total_checks * 100) if total_checks else 0.0
    print(f"Match Rate: {pct:.2f}% ({total_matches}/{total_checks})")
    print("=" * 80)

    return 0 if (total_checks > 0 and total_matches == total_checks) else 1


if __name__ == "__main__":
    sys.exit(run_verification())
