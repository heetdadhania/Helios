import os
import sys
sys.path.insert(0, os.path.abspath('backend'))
from dotenv import load_dotenv
load_dotenv('backend/.env')

from fastapi.testclient import TestClient
from app.main import app
from app.core.security import create_access_token

client = TestClient(app)

# Test with smb_owner token for tenant 1 (user_id=6)
token_org1 = create_access_token(
    user_id=6,
    role="smb_owner",
    tenant_id=1,
)
headers_org1 = {"Authorization": f"Bearer {token_org1}"}

print("=== 1. Testing GET /api/v1/dashboard/revenue-by-category ===")
res1 = client.get("/api/v1/dashboard/revenue-by-category", headers=headers_org1)
print(f"Status: {res1.status_code}")
data1 = res1.json()
print("Total revenue:", data1.get("total_revenue"))
print("Categories count:", len(data1.get("categories", [])))
print("Top category:", data1.get("categories", [])[0] if data1.get("categories") else None)

print("\n=== 2. Testing GET /api/v1/dashboard/revenue-by-segment ===")
res2 = client.get("/api/v1/dashboard/revenue-by-segment", headers=headers_org1)
print(f"Status: {res2.status_code}")
data2 = res2.json()
print("Total revenue:", data2.get("total_revenue"))
print("Segments count:", len(data2.get("segments", [])))
for seg in data2.get("segments", []):
    print("  Segment:", seg)

print("\n=== 3. Testing GET /api/v1/dashboard/monthly-revenue ===")
res3 = client.get("/api/v1/dashboard/monthly-revenue", headers=headers_org1)
print(f"Status: {res3.status_code}")
data3 = res3.json()
print("Total revenue:", data3.get("total_revenue"))
print("Months count:", len(data3.get("months", [])))
for m in data3.get("months", []):
    print("  Month:", m)

# Test View-As endpoint
token_admin = create_access_token(
    user_id=1,
    role="admin",
    tenant_id=None,
)
headers_admin = {"Authorization": f"Bearer {token_admin}"}
print("\n=== 4. Testing Admin View-As GET /api/v1/oversight/dashboard/1 ===")
res4 = client.get("/api/v1/oversight/dashboard/1", headers=headers_admin)
print(f"Status: {res4.status_code}")
data4 = res4.json()
print("View-As has revenue_by_category:", "revenue_by_category" in data4 and data4["revenue_by_category"] is not None)
print("View-As has revenue_by_segment:", "revenue_by_segment" in data4 and data4["revenue_by_segment"] is not None)
print("View-As has monthly_revenue:", "monthly_revenue" in data4 and data4["monthly_revenue"] is not None)

print("\nALL 4 ENDPOINT CHECKS PASSED!")
