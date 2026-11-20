import os
import sys
sys.path.insert(0, os.path.abspath("backend"))
from app.db.base import databricks_cursor

with databricks_cursor() as cursor:
    cursor.execute("SELECT tenant_id, business_name, is_active FROM platform.tenants ORDER BY tenant_id")
    tenants = cursor.fetchall()
    print("Tenants in platform.tenants:")
    for t in tenants:
        print(f"  Tenant {t[0]}: {t[1]} (active={t[2]})")
    
    # Check row counts in gold.fact_orders for tenants 1 to 10
    cursor.execute("SELECT tenant_id, COUNT(1) FROM gold.fact_orders WHERE tenant_id <= 10 GROUP BY tenant_id ORDER BY tenant_id")
    gold_counts = cursor.fetchall()
    print("\nGold fact_orders counts for Tenants 1-10:")
    for gc in gold_counts:
        print(f"  Tenant {gc[0]}: {gc[1]} rows")
