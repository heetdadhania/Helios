"""
Tests verifying date range filtering for Helios dashboard endpoints.

Specifically verifies:
1. GET /api/dashboard/revenue-trend with days=7, days=30, and no range (all-time)
   returns non-identical, arithmetically consistent totals.
2. GET /api/dashboard/top-products with days=7, days=30, and no range (all-time)
   returns non-identical, arithmetically consistent product totals.
"""

from datetime import date, datetime
from typing import Any, Dict, List, Optional
import pytest
from fastapi.testclient import TestClient

from app.core.dependencies import get_current_user, get_db_cursor
from app.main import app
from app.schemas.auth import UserOut, UserRole


# --- Seed Data spanning > 30 days (anchored at 2024-03-31, span: 41 days) ---
# Anchor date is 2024-03-31 (date_id: 20240331)
# 7-day window  (2024-03-25 to 2024-03-31): date_id >= 20240325
# 30-day window (2024-03-02 to 2024-03-31): date_id >= 20240302
# All-time window: all records

SEEDED_DAILY_SUMMARY = [
    # Within 7 days
    {"tenant_id": 1, "date_id": 20240331, "full_date": "2024-03-31", "total_revenue": 100.0, "total_orders": 1, "avg_order_value": 100.0, "total_quantity": 2},
    {"tenant_id": 1, "date_id": 20240327, "full_date": "2024-03-27", "total_revenue": 200.0, "total_orders": 2, "avg_order_value": 100.0, "total_quantity": 4},
    # Within 30 days, outside 7 days
    {"tenant_id": 1, "date_id": 20240315, "full_date": "2024-03-15", "total_revenue": 300.0, "total_orders": 3, "avg_order_value": 100.0, "total_quantity": 6},
    {"tenant_id": 1, "date_id": 20240305, "full_date": "2024-03-05", "total_revenue": 400.0, "total_orders": 4, "avg_order_value": 100.0, "total_quantity": 8},
    # Older than 30 days (41 days prior to anchor)
    {"tenant_id": 1, "date_id": 20240219, "full_date": "2024-02-19", "total_revenue": 500.0, "total_orders": 5, "avg_order_value": 100.0, "total_quantity": 10},
]

SEEDED_FACT_ORDERS = [
    # Within 7 days
    {"tenant_id": 1, "order_id": 1, "date_id": 20240330, "product_id": 101, "product_name": "Pro Keyboard", "category": "Electronics", "total": 150.0, "quantity": 1, "discount": 0.0, "profit": 50.0},
    {"tenant_id": 1, "order_id": 2, "date_id": 20240328, "product_id": 102, "product_name": "Ergo Mouse", "category": "Electronics", "total": 50.0, "quantity": 1, "discount": 0.0, "profit": 20.0},
    # Within 30 days, outside 7 days
    {"tenant_id": 1, "order_id": 3, "date_id": 20240315, "product_id": 101, "product_name": "Pro Keyboard", "category": "Electronics", "total": 300.0, "quantity": 2, "discount": 0.0, "profit": 100.0},
    {"tenant_id": 1, "order_id": 4, "date_id": 20240310, "product_id": 102, "product_name": "Ergo Mouse", "category": "Electronics", "total": 100.0, "quantity": 2, "discount": 0.0, "profit": 40.0},
    # Older than 30 days
    {"tenant_id": 1, "order_id": 5, "date_id": 20240215, "product_id": 103, "product_name": "Desk Mat", "category": "Accessories", "total": 200.0, "quantity": 4, "discount": 0.0, "profit": 80.0},
]


class SeededMockCursor:
    """Mock database cursor that executes against seeded data."""

    def __init__(self):
        self.description = []
        self._results = []

    def execute(self, query: str, params: Optional[Dict[str, Any]] = None):
        params = params or {}
        tenant_id = params.get("tenant_id")
        start_date_id = params.get("start_date_id")

        normalized_query = " ".join(query.split()).lower()

        # 1. Anchor date determination: SELECT max(date_id) FROM ... WHERE tenant_id = :tenant_id
        if "select max(" in normalized_query:
            if "fact_orders_daily_summary" in normalized_query:
                tenant_rows = [r for r in SEEDED_DAILY_SUMMARY if r["tenant_id"] == tenant_id]
            else:
                tenant_rows = [r for r in SEEDED_FACT_ORDERS if r["tenant_id"] == tenant_id]
            max_date = max(r["date_id"] for r in tenant_rows) if tenant_rows else None
            self.description = [("max_date_id",)]
            self._results = [(max_date,)]
            return

        # 2. Revenue Trend Query
        if "fact_orders_daily_summary" in normalized_query:
            rows = [r for r in SEEDED_DAILY_SUMMARY if r["tenant_id"] == tenant_id]
            if start_date_id is not None:
                rows = [r for r in rows if r["date_id"] >= start_date_id]

            # Sort ascending by date_id
            rows.sort(key=lambda r: r["date_id"])

            self.description = [
                ("date_str",),
                ("total_revenue",),
                ("total_orders",),
                ("avg_order_value",),
                ("total_quantity",),
            ]
            self._results = [
                (r["full_date"], r["total_revenue"], r["total_orders"], r["avg_order_value"], r["total_quantity"])
                for r in rows
            ]
            return

        # 3. Top Products Query
        if "dim_product" in normalized_query or "fact_orders" in normalized_query:
            rows = [r for r in SEEDED_FACT_ORDERS if r["tenant_id"] == tenant_id]
            if start_date_id is not None:
                rows = [r for r in rows if r["date_id"] >= start_date_id]

            # Aggregate by product
            aggregated = {}
            for r in rows:
                pid = r["product_id"]
                if pid not in aggregated:
                    aggregated[pid] = {
                        "product_id": pid,
                        "product_name": r["product_name"],
                        "category": r["category"],
                        "total_revenue": 0.0,
                        "total_units_sold": 0,
                        "order_ids": set(),
                    }
                aggregated[pid]["total_revenue"] += r["total"]
                aggregated[pid]["total_units_sold"] += r["quantity"]
                aggregated[pid]["order_ids"].add(r["order_id"])

            res_list = list(aggregated.values())
            res_list.sort(key=lambda x: x["total_revenue"], reverse=True)

            limit = params.get("limit", 10)
            res_list = res_list[:limit]

            self.description = [
                ("product_id",),
                ("product_name",),
                ("category",),
                ("total_revenue",),
                ("total_units_sold",),
                ("total_orders",),
            ]
            self._results = [
                (p["product_id"], p["product_name"], p["category"], round(p["total_revenue"], 2), p["total_units_sold"], len(p["order_ids"]))
                for p in res_list
            ]
            return

        self.description = []
        self._results = []

    def fetchone(self):
        return self._results[0] if self._results else None

    def fetchall(self):
        return self._results


@pytest.fixture
def api_client():
    client = TestClient(app)
    mock_cursor = SeededMockCursor()
    smb_user = UserOut(
        id=1,
        name="Store Owner",
        email="owner@teststore.com",
        role=UserRole.SMB_OWNER,
        tenant_id=1,
    )

    app.dependency_overrides[get_current_user] = lambda: smb_user
    app.dependency_overrides[get_db_cursor] = lambda: mock_cursor
    yield client
    app.dependency_overrides.clear()


def test_revenue_trend_date_filtering(api_client):
    """
    Verify GET /api/dashboard/revenue-trend with days=7, days=30, and no range:
    1. Results are NOT identical.
    2. Each result matches the exact arithmetic sum of rows inside that window.
    """
    # 1. Query with days=7
    res_7 = api_client.get("/api/dashboard/revenue-trend?days=7")
    assert res_7.status_code == 200, res_7.text
    data_7 = res_7.json()

    # 2. Query with days=30
    res_30 = api_client.get("/api/dashboard/revenue-trend?days=30")
    assert res_30.status_code == 200, res_30.text
    data_30 = res_30.json()

    # 3. Query with no range (all-time)
    res_all = api_client.get("/api/dashboard/revenue-trend")
    assert res_all.status_code == 200, res_all.text
    data_all = res_all.json()

    # Assert that all three results are NOT identical
    assert data_7["total_revenue"] != data_30["total_revenue"]
    assert data_30["total_revenue"] != data_all["total_revenue"]
    assert data_7["total_orders"] != data_30["total_orders"]
    assert data_30["total_orders"] != data_all["total_orders"]

    # Manual arithmetic sums from seeded data:
    # Anchor date: 2024-03-31
    # 7-day window (2024-03-25 to 2024-03-31):
    #   20240331: rev 100.0, ord 1
    #   20240327: rev 200.0, ord 2
    #   Expected sum: rev 300.0, ord 3
    expected_7_rev = sum(r["total_revenue"] for r in SEEDED_DAILY_SUMMARY if r["date_id"] >= 20240325)
    expected_7_ord = sum(r["total_orders"] for r in SEEDED_DAILY_SUMMARY if r["date_id"] >= 20240325)
    assert data_7["total_revenue"] == pytest.approx(expected_7_rev, 0.01)
    assert data_7["total_orders"] == expected_7_ord
    assert len(data_7["points"]) == 2

    # 30-day window (2024-03-02 to 2024-03-31):
    #   Rows at 20240331, 20240327, 20240315, 20240305
    #   Expected sum: rev 100 + 200 + 300 + 400 = 1000.0, ord 10
    expected_30_rev = sum(r["total_revenue"] for r in SEEDED_DAILY_SUMMARY if r["date_id"] >= 20240302)
    expected_30_ord = sum(r["total_orders"] for r in SEEDED_DAILY_SUMMARY if r["date_id"] >= 20240302)
    assert data_30["total_revenue"] == pytest.approx(expected_30_rev, 0.01)
    assert data_30["total_orders"] == expected_30_ord
    assert len(data_30["points"]) == 4

    # All-time window (no range):
    #   All 5 rows
    #   Expected sum: rev 1000.0 + 500.0 = 1500.0, ord 15
    expected_all_rev = sum(r["total_revenue"] for r in SEEDED_DAILY_SUMMARY)
    expected_all_ord = sum(r["total_orders"] for r in SEEDED_DAILY_SUMMARY)
    assert data_all["total_revenue"] == pytest.approx(expected_all_rev, 0.01)
    assert data_all["total_orders"] == expected_all_ord
    assert len(data_all["points"]) == 5


def test_top_products_date_filtering(api_client):
    """
    Verify GET /api/dashboard/top-products with days=7, days=30, and no range:
    1. Results are NOT identical.
    2. Each result matches the arithmetic sum of product orders inside that window.
    """
    # 1. Query with days=7
    res_7 = api_client.get("/api/dashboard/top-products?days=7")
    assert res_7.status_code == 200, res_7.text
    data_7 = res_7.json()

    # 2. Query with days=30
    res_30 = api_client.get("/api/dashboard/top-products?days=30")
    assert res_30.status_code == 200, res_30.text
    data_30 = res_30.json()

    # 3. Query with no range (all-time)
    res_all = api_client.get("/api/dashboard/top-products")
    assert res_all.status_code == 200, res_all.text
    data_all = res_all.json()

    # Total revenue across top products in each window
    total_rev_7 = sum(p["total_revenue"] for p in data_7["products"])
    total_rev_30 = sum(p["total_revenue"] for p in data_30["products"])
    total_rev_all = sum(p["total_revenue"] for p in data_all["products"])

    # Assert results are NOT identical across windows
    assert total_rev_7 != total_rev_30
    assert total_rev_30 != total_rev_all

    # Arithmetic verification:
    # 7-day window (date_id >= 20240325):
    #   Orders 1 (150.0) & 2 (50.0) -> sum: 200.0
    expected_7_rev = sum(r["total"] for r in SEEDED_FACT_ORDERS if r["date_id"] >= 20240325)
    assert total_rev_7 == pytest.approx(expected_7_rev, 0.01)
    assert len(data_7["products"]) == 2

    # 30-day window (date_id >= 20240302):
    #   Orders 1 (150.0), 2 (50.0), 3 (300.0), 4 (100.0) -> sum: 600.0
    expected_30_rev = sum(r["total"] for r in SEEDED_FACT_ORDERS if r["date_id"] >= 20240302)
    assert total_rev_30 == pytest.approx(expected_30_rev, 0.01)
    assert len(data_30["products"]) == 2

    # All-time window:
    #   All orders (1-5) -> sum: 600.0 + 200.0 = 800.0
    expected_all_rev = sum(r["total"] for r in SEEDED_FACT_ORDERS)
    assert total_rev_all == pytest.approx(expected_all_rev, 0.01)
    assert len(data_all["products"]) == 3
