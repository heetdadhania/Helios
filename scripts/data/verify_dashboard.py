import os
import sys
from pathlib import Path

# Repo root
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.db.base import databricks_cursor
from app.repositories.dashboard_repository import DashboardRepository
from app.services.dashboard_service import DashboardService
from app.schemas.auth import UserOut, UserRole

def test_tenant(tid: int):
    with databricks_cursor() as cur:
        repo = DashboardRepository(cur)
        user = UserOut(id=tid, name=f"Owner {tid}", email=f"owner{tid}@test.dev", role=UserRole.SMB_OWNER, tenant_id=tid)
        rev = DashboardService.get_revenue_trend(current_user=user, days=None, repo=repo)
        prods = DashboardService.get_top_products(current_user=user, limit=5, days=None, repo=repo)
        print(f"Tenant {tid}: Data as of = {rev.data_as_of}, Revenue points = {len(rev.points)}, Total Revenue = ${rev.total_revenue:,.2f}, Top products = {len(prods.products)}")

if __name__ == "__main__":
    for t in [1, 2, 4, 6, 8]:
        test_tenant(t)
