import os
import sys
from decimal import Decimal
import pandas as pd

sys.path.insert(0, os.path.abspath('backend'))
from dotenv import load_dotenv
load_dotenv('backend/.env')

from fastapi.testclient import TestClient
from app.main import app
from app.core.security import create_access_token

def print_table(headers, rows):
    col_widths = [len(h) for h in headers]
    for row in rows:
        for idx, val in enumerate(row):
            col_widths[idx] = max(col_widths[idx], len(str(val)))
    
    header_str = " | ".join(f"{h:<{col_widths[i]}}" for i, h in enumerate(headers))
    sep_str = "-+-".join("-" * col_widths[i] for i in range(len(headers)))
    print(header_str)
    print(sep_str)
    for row in rows:
        print(" | ".join(f"{str(val):<{col_widths[i]}}" for i, val in enumerate(row)))

client = TestClient(app)

# We use the admin token with tenant_id parameter so we can test Orgs 1, 4, and 7
admin_token = create_access_token(user_id=1, role="admin", tenant_id=None)
headers = {"Authorization": f"Bearer {admin_token}"}

organizations = [1, 4, 7]
all_passed = True

print("=" * 80)
print("VERIFICATION: PANDAS SOURCE DATA VS GOLD API TELEMETRY (ORGS 1, 4, 7)")
print("=" * 80)

for oid in organizations:
    print(f"\n############################# ORGANIZATION {oid} #############################")
    
    # 1. Source CSV calculation via Pandas (valid rows only)
    csv_path = f"scripts/data/helios_indian_data/org0{oid}_orders.csv"
    df = pd.read_csv(csv_path)
    
    # Valid rows filtering identical to ingestion pipeline
    valid_df = df[
        (df['order_date'] != 'not-a-date') &
        (pd.to_datetime(df['order_date'], errors='coerce').notna()) &
        (pd.to_numeric(df['quantity'], errors='coerce') > 0) &
        (pd.to_numeric(df['total'], errors='coerce') >= 0)
    ].copy()
    valid_df['total_dec'] = valid_df['total'].apply(lambda x: Decimal(str(x)))
    valid_df['month'] = valid_df['order_date'].str.slice(0, 7)
    
    pandas_cat = {k: Decimal(str(v)) for k, v in valid_df.groupby('category')['total_dec'].sum().items()}
    pandas_seg = {k: Decimal(str(v)) for k, v in valid_df.groupby('segment')['total_dec'].sum().items()}
    pandas_month = {k: Decimal(str(v)) for k, v in valid_df.groupby('month')['total_dec'].sum().items()}
    
    # 2. Call API endpoints
    # 2a. Category
    r_cat = client.get(f"/api/v1/dashboard/revenue-by-category?tenant_id={oid}", headers=headers)
    assert r_cat.status_code == 200, f"Failed category: {r_cat.text}"
    api_cat = {item['category']: Decimal(str(item['revenue'])) for item in r_cat.json()['categories']}
    
    # 2b. Segment
    r_seg = client.get(f"/api/v1/dashboard/revenue-by-segment?tenant_id={oid}", headers=headers)
    assert r_seg.status_code == 200, f"Failed segment: {r_seg.text}"
    api_seg = {item['segment']: Decimal(str(item['revenue'])) for item in r_seg.json()['segments']}
    
    # 2c. Monthly
    r_month = client.get(f"/api/v1/dashboard/monthly-revenue?tenant_id={oid}", headers=headers)
    assert r_month.status_code == 200, f"Failed monthly: {r_month.text}"
    api_month = {item['month_key']: Decimal(str(item['revenue'])) for item in r_month.json()['months']}
    
    # Print comparison tables
    # Category Table
    cat_rows = []
    all_categories = sorted(set(pandas_cat.keys()) | set(api_cat.keys()))
    for cat in all_categories:
        exp = pandas_cat.get(cat, Decimal('0.00'))
        shown = api_cat.get(cat, Decimal('0.00'))
        diff = abs(exp - shown)
        status = "MATCH" if diff <= Decimal('0.01') else "MISMATCH"
        if status == "MISMATCH":
            all_passed = False
        cat_rows.append([cat, f"₹{exp:,.2f}", f"₹{shown:,.2f}", f"₹{diff:,.2f}", status])
    print(f"\n--- 1. Revenue by Product Category (Org {oid}) ---")
    print_table(["Category", "Expected (Pandas)", "Shown (API)", "Diff", "Status"], cat_rows)
    
    # Segment Table
    seg_rows = []
    all_segments = sorted(set(pandas_seg.keys()) | set(api_seg.keys()))
    for seg in all_segments:
        exp = pandas_seg.get(seg, Decimal('0.00'))
        shown = api_seg.get(seg, Decimal('0.00'))
        diff = abs(exp - shown)
        status = "MATCH" if diff <= Decimal('0.01') else "MISMATCH"
        if status == "MISMATCH":
            all_passed = False
        seg_rows.append([seg, f"₹{exp:,.2f}", f"₹{shown:,.2f}", f"₹{diff:,.2f}", status])
    print(f"\n--- 2. Revenue by Customer Segment (Org {oid}) ---")
    print_table(["Segment", "Expected (Pandas)", "Shown (API)", "Diff", "Status"], seg_rows)
    
    # Monthly Table
    month_rows = []
    all_months = sorted(set(pandas_month.keys()) | set(api_month.keys()))
    for m in all_months:
        exp = pandas_month.get(m, Decimal('0.00'))
        shown = api_month.get(m, Decimal('0.00'))
        diff = abs(exp - shown)
        status = "MATCH" if diff <= Decimal('0.01') else "MISMATCH"
        if status == "MISMATCH":
            all_passed = False
        month_rows.append([m, f"₹{exp:,.2f}", f"₹{shown:,.2f}", f"₹{diff:,.2f}", status])
    print(f"\n--- 3. Month-over-Month Revenue (Org {oid}) ---")
    print_table(["Month", "Expected (Pandas)", "Shown (API)", "Diff", "Status"], month_rows)

print("\n" + "=" * 80)
if all_passed:
    print("ALL CHECKS PASSED: 100% of values match within ₹0.01 for Orgs 1, 4, and 7!")
else:
    print("SOME CHECKS FAILED!")
print("=" * 80)
