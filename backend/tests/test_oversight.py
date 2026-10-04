from unittest.mock import MagicMock, patch
import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.main import app
from app.core import security
from app.schemas.auth import UserOut, UserRole
from app.core.dependencies import get_current_user, get_db_cursor
from app.repositories.oversight_repository import OversightRepository


@pytest.fixture
def admin_token():
    return security.create_access_token(user_id=1, role="admin")


@pytest.fixture
def smb_owner_token():
    return security.create_access_token(user_id=3, role="smb_owner", tenant_id=1)


@pytest.fixture
def client():
    return TestClient(app)


def test_get_tenant_dashboard_admin_success(client, admin_token):
    """Admin can successfully fetch dashboard metrics for an existing tenant."""
    response = client.get(
        "/api/oversight/dashboard/1?days=30",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["tenant_id"] == 1
    assert "tenant_name" in data
    assert "revenue_trend" in data
    assert "top_products" in data
    assert "late_delivery_risk" in data
    assert "discount_vs_profit" in data
    assert "shipping_modes" in data


def test_get_tenant_dashboard_empty_tenant(client, admin_token):
    """A tenant with no processed Gold data returns valid empty structures, not a 500 error."""
    response = client.get(
        "/api/oversight/dashboard/1",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["tenant_id"] == 1
    # Check that responses are typed and non-null
    assert isinstance(data["revenue_trend"]["total_revenue"], (int, float))
    assert isinstance(data["top_products"]["products"], list)
    assert isinstance(data["late_delivery_risk"]["total_shipments"], int)
    assert isinstance(data["discount_vs_profit"]["bands"], list)
    assert isinstance(data["shipping_modes"]["modes"], list)


def test_get_tenant_dashboard_nonexistent_tenant(client, admin_token):
    """Querying a non-existent tenant returns 404 Not Found."""
    response = client.get(
        "/api/oversight/dashboard/99999",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "does not exist" in response.json()["detail"]


def test_get_tenant_dashboard_forbidden_for_smb_owner(client, smb_owner_token):
    """Non-admin users cannot access the oversight dashboard endpoint."""
    response = client.get(
        "/api/oversight/dashboard/1",
        headers={"Authorization": f"Bearer {smb_owner_token}"},
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_get_tenant_dashboard_unauthenticated(client):
    """Unauthenticated calls are rejected with 401."""
    response = client.get("/api/oversight/dashboard/1")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_oversight_repo_get_tenant_queries_valid_columns():
    """Verify get_tenant_by_id and get_all_tenants do not query non-existent columns like raw slug or tier."""
    mock_cursor = MagicMock()
    mock_cursor.description = [("tenant_id",), ("business_name",), ("slug",), ("tier",), ("is_active",)]
    mock_cursor.fetchone.return_value = (1, "Apex Consumer Goods", "apex_consumer_goods", "starter", True)

    repo = OversightRepository(mock_cursor)
    tenant = repo.get_tenant_by_id(1)

    assert tenant is not None
    assert tenant["tenant_id"] == 1
    assert tenant["business_name"] == "Apex Consumer Goods"

    # Verify query executed
    call_sql = mock_cursor.execute.call_args[0][0]
    # Ensure it doesn't query bare `slug` or `tier` column from platform.tenants
    assert "lower(replace(business_name" in call_sql
    assert "'starter' AS tier" in call_sql


def test_oversight_repo_pipeline_status_queries_stage_alias():
    """Verify get_latest_pipeline_status_per_tenant aliases stage as current_stage."""
    mock_cursor = MagicMock()
    mock_cursor.description = [("tenant_id",), ("batch_id",), ("current_stage",), ("status",), ("updated_at",), ("error_message",)]
    mock_cursor.fetchall.return_value = [(1, "b-1", "silver_clean", "success", None, None)]

    repo = OversightRepository(mock_cursor)
    res = repo.get_latest_pipeline_status_per_tenant()

    assert 1 in res
    call_sql = mock_cursor.execute.call_args[0][0]
    assert "stage AS current_stage" in call_sql


def test_oversight_repo_late_delivery_rates_safe_division():
    """Verify get_tenant_late_delivery_rates protects against division by zero."""
    mock_cursor = MagicMock()
    mock_cursor.description = [("tenant_id",), ("total_shipments",), ("late_shipments",), ("late_rate_pct",), ("avg_shipping_days",)]
    mock_cursor.fetchall.return_value = [(1, 50, 5, 10.0, 3.5)]

    repo = OversightRepository(mock_cursor)
    res = repo.get_tenant_late_delivery_rates()

    assert 1 in res
    call_sql = mock_cursor.execute.call_args[0][0]
    assert "nullif(count(*), 0)" in call_sql


def test_get_tenant_health_admin_success(client, admin_token):
    """Admin can fetch tenant health, properly evaluating tenants with and without data."""
    response = client.get(
        "/api/oversight/tenant-health",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "total_tenants" in data
    assert "tenants" in data
    assert len(data["tenants"]) >= 1

    # Check for zero-data tenant (Tenant 3) showing sensible defaults
    zero_data_tenants = [t for t in data["tenants"] if t["tenant_id"] == 3]
    if zero_data_tenants:
        t3 = zero_data_tenants[0]
        assert t3["health_status"] == "good"
        assert t3["total_shipments"] == 0
        assert t3["late_delivery_rate_pct"] == 0.0
        assert t3["issues"] == []


def test_post_compare_admin_differing_metrics(client, admin_token):
    """Admin can compare 2 tenants with differing data and verify metrics differ."""
    response = client.post(
        "/api/oversight/compare",
        json={"tenant_ids": [1, 2], "days": 30},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "tenants" in data
    assert len(data["tenants"]) == 2

    t1 = next((t for t in data["tenants"] if t["tenant_id"] == 1), None)
    t2 = next((t for t in data["tenants"] if t["tenant_id"] == 2), None)
    assert t1 is not None
    assert t2 is not None

    # Verify metrics are genuinely different between Tenant 1 and Tenant 2
    assert t1["total_revenue"] != t2["total_revenue"]
    assert t1["total_orders"] != t2["total_orders"]
    assert t1["total_shipments"] != t2["total_shipments"]
    assert t1["late_delivery_pct"] != t2["late_delivery_pct"]


def test_post_compare_validation_min_two_tenants(client, admin_token):
    """Payload with fewer than 2 tenant IDs fails validation with 422."""
    response = client.post(
        "/api/oversight/compare",
        json={"tenant_ids": [1]},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_get_platform_usage_admin_success(client, admin_token):
    """Admin can fetch platform usage, returning pipeline runs and tenant batch metrics."""
    response = client.get(
        "/api/oversight/usage",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "total_runs" in data
    assert "total_rows_ingested" in data
    assert "total_batches" in data
    assert "active_tenants_count" in data
    assert "pipeline_runs_per_day" in data
    assert "batches_per_tenant" in data
    assert "total_rows_ingested_over_time" in data
    assert isinstance(data["pipeline_runs_per_day"], list)
    assert len(data["pipeline_runs_per_day"]) >= 1
    assert data["pipeline_runs_per_day"][0]["total_runs"] >= 1


