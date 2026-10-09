"""
Tests verifying anchored date lookback window behavior for Helios dashboard endpoints.

Requirements verified:
1. Daily summary rows spanning >= 60 days ending on an anchor date >= 100 days before today.
2. days=7, days=30, and all-time return three different totals, each matching the manual sum of only the rows inside that window.
3. A tenant with zero rows returns a valid empty response with data_as_of = None, not an error.
4. The admin oversight dashboard for a tenant returns identical totals and data_as_of as the tenant's own dashboard for the same range.
"""

from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional
import pytest
from fastapi.testclient import TestClient

from app.core.dependencies import get_current_user, get_db_cursor
from app.main import app
from app.schemas.auth import UserOut, UserRole

# -----------------------------------------------------------------------------
# Test Data Generation:
# Anchor date is placed 120 days before today (> 100 days requirement).
# Rows span 65 days (>= 60 days requirement), ending at anchor_date.
# -----------------------------------------------------------------------------
TODAY = date.today()
ANCHOR_DATE_T10 = TODAY - timedelta(days=120)
SPAN_DAYS = 65
START_DATE_T10 = ANCHOR_DATE_T10 - timedelta(days=SPAN_DAYS - 1)

SEEDED_TENANTS = {
    10: {"tenant_id": 10, "business_name": "Anchor Test Goods", "tier": "growth", "is_active": True},
    99: {"tenant_id": 99, "business_name": "Empty Test Tenant", "tier": "starter", "is_active": True},
}

# Seed 65 daily summary rows for Tenant 10
SEEDED_DAILY_SUMMARY: List[Dict[str, Any]] = []
for i in range(SPAN_DAYS):
    cur_date = START_DATE_T10 + timedelta(days=i)
    cur_date_id = int(cur_date.strftime("%Y%m%d"))
    rev = round(100.0 + (i * 12.50), 2)
    ords = 1 + (i % 5)
    qty = ords * 2
    aov = round(rev / ords, 2)
    SEEDED_DAILY_SUMMARY.append({
        "tenant_id": 10,
        "date_id": cur_date_id,
        "full_date": cur_date.strftime("%Y-%m-%d"),
        "date_obj": cur_date,
        "total_revenue": rev,
        "total_orders": ords,
        "avg_order_value": aov,
        "total_quantity": qty,
    })

# Seed top products for Tenant 10
SEEDED_FACT_ORDERS: List[Dict[str, Any]] = []
for i, ds in enumerate(SEEDED_DAILY_SUMMARY):
    SEEDED_FACT_ORDERS.append({
        "tenant_id": 10,
        "order_id": 1000 + i,
        "date_id": ds["date_id"],
        "date_obj": ds["date_obj"],
        "product_id": 101 if i % 2 == 0 else 102,
        "product_name": "Solar Charger" if i % 2 == 0 else "Smart Inverter",
        "category": "CleanTech",
        "total": ds["total_revenue"],
        "quantity": ds["total_quantity"],
        "discount": round(ds["total_revenue"] * 0.1, 2),
        "profit": round(ds["total_revenue"] * 0.4, 2),
    })

# Seed shipments for Tenant 10
SEEDED_SHIPMENTS: List[Dict[str, Any]] = []
for i, ds in enumerate(SEEDED_DAILY_SUMMARY):
    is_late = (i % 4 == 0)
    SEEDED_SHIPMENTS.append({
        "tenant_id": 10,
        "date_id": ds["date_id"],
        "date_obj": ds["date_obj"],
        "late_flag": is_late,
        "shipping_days": 4 if is_late else 2,
        "mode_name": "Express" if i % 2 == 0 else "Standard",
        "status_name": "Delayed" if is_late else "Delivered",
    })


class AnchoredTestMockCursor:
    """Mock database cursor routing queries against anchored seed data."""

    def __init__(self):
        self.description = []
        self._results = []

    def execute(self, query: str, params: Optional[Dict[str, Any]] = None):
        params = params or {}
        tenant_id = params.get("tenant_id")
        start_date_id = params.get("start_date_id")
        end_date_id = params.get("end_date_id")

        q_lower = " ".join(query.split()).lower()

        # 1. get_latest_data_date: SELECT max(d.full_date) AS max_date FROM ... WHERE s.tenant_id = :tenant_id
        if "select max(" in q_lower and "tenant_id" in q_lower:
            tenant_rows = [r for r in SEEDED_DAILY_SUMMARY if r["tenant_id"] == tenant_id]
            max_date = max((r["full_date"] for r in tenant_rows), default=None)
            self.description = [("max_date",)]
            self._results = [(max_date,)] if max_date else []
            return

        # 2. get_tenant_by_id: SELECT tenant_id, business_name, ... FROM platform.tenants WHERE tenant_id = :tenant_id
        if "platform" in q_lower and "tenants" in q_lower and "tenant_id = :tenant_id" in q_lower:
            t = SEEDED_TENANTS.get(tenant_id)
            if t:
                self.description = [("tenant_id",), ("business_name",), ("slug",), ("tier",), ("is_active",)]
                self._results = [(t["tenant_id"], t["business_name"], f"slug-{t['tenant_id']}", t["tier"], t["is_active"])]
            else:
                self.description = [("tenant_id",), ("business_name",), ("slug",), ("tier",), ("is_active",)]
                self._results = []
            return

        # 3. get_revenue_trend: FROM daily_summary ...
        if "fact_orders_daily_summary" in q_lower:
            rows = [r for r in SEEDED_DAILY_SUMMARY if r["tenant_id"] == tenant_id]
            if start_date_id is not None:
                rows = [r for r in rows if r["date_id"] >= start_date_id]
            if end_date_id is not None:
                rows = [r for r in rows if r["date_id"] <= end_date_id]

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

        # 4. get_top_products: FROM fact_orders ... JOIN dim_product
        if "fact_orders" in q_lower and "dim_product" in q_lower:
            rows = [r for r in SEEDED_FACT_ORDERS if r["tenant_id"] == tenant_id]
            if start_date_id is not None:
                rows = [r for r in rows if r["date_id"] >= start_date_id]
            if end_date_id is not None:
                rows = [r for r in rows if r["date_id"] <= end_date_id]

            agg: Dict[int, Dict[str, Any]] = {}
            for r in rows:
                pid = r["product_id"]
                if pid not in agg:
                    agg[pid] = {
                        "product_id": pid,
                        "product_name": r["product_name"],
                        "category": r["category"],
                        "total_revenue": 0.0,
                        "total_units_sold": 0,
                        "total_orders": 0,
                    }
                agg[pid]["total_revenue"] += r["total"]
                agg[pid]["total_units_sold"] += r["quantity"]
                agg[pid]["total_orders"] += 1

            sorted_prods = sorted(agg.values(), key=lambda p: p["total_revenue"], reverse=True)
            limit = params.get("limit", 10)
            sorted_prods = sorted_prods[:limit]

            self.description = [
                ("product_id",),
                ("product_name",),
                ("category",),
                ("total_revenue",),
                ("total_units_sold",),
                ("total_orders",),
            ]
            self._results = [
                (p["product_id"], p["product_name"], p["category"], round(p["total_revenue"], 2), p["total_units_sold"], p["total_orders"])
                for p in sorted_prods
            ]
            return

        # 5. get_shipping_mode_comparison: FROM fact_shipments ... JOIN dim_shipping_mode
        if "dim_shipping_mode" in q_lower:
            rows = [r for r in SEEDED_SHIPMENTS if r["tenant_id"] == tenant_id]
            if start_date_id is not None:
                rows = [r for r in rows if r["date_id"] >= start_date_id]
            if end_date_id is not None:
                rows = [r for r in rows if r["date_id"] <= end_date_id]

            modes_agg: Dict[str, List[Dict[str, Any]]] = {}
            for r in rows:
                m_name = r.get("mode_name", "Standard")
                modes_agg.setdefault(m_name, []).append(r)

            self.description = [
                ("mode_name",),
                ("shipment_count",),
                ("avg_shipping_days",),
                ("late_count",),
                ("late_rate_pct",),
                ("on_time_rate_pct",),
            ]
            self._results = []
            for m_name, m_rows in modes_agg.items():
                m_tot = len(m_rows)
                m_late = sum(1 for x in m_rows if x["late_flag"])
                m_avg = round(sum(x["shipping_days"] for x in m_rows) / m_tot, 2) if m_tot > 0 else 0.0
                m_late_pct = round(m_late / m_tot * 100.0, 2) if m_tot > 0 else 0.0
                m_ontime_pct = round((m_tot - m_late) / m_tot * 100.0, 2) if m_tot > 0 else 0.0
                self._results.append((m_name, m_tot, m_avg, m_late, m_late_pct, m_ontime_pct))
            return

        # 6. get_late_delivery_risk overview: FROM fact_shipments ...
        if "fact_shipments" in q_lower and "count(*)" in q_lower:
            rows = [r for r in SEEDED_SHIPMENTS if r["tenant_id"] == tenant_id]
            if start_date_id is not None:
                rows = [r for r in rows if r["date_id"] >= start_date_id]
            if end_date_id is not None:
                rows = [r for r in rows if r["date_id"] <= end_date_id]

            tot = len(rows)
            late = sum(1 for r in rows if r["late_flag"])
            on_time = tot - late
            avg_days = round(sum(r["shipping_days"] for r in rows) / tot, 2) if tot > 0 else 0.0

            if "group by" in q_lower and "status_name" in q_lower:
                self.description = [("status_name",), ("total_shipments",), ("late_shipments",), ("late_rate_pct",)]
                self._results = [("Delivered", on_time, 0, 0.0), ("Delayed", late, late, 100.0)] if tot > 0 else []
            else:
                self.description = [("total_shipments",), ("late_shipments",), ("on_time_shipments",), ("avg_shipping_days",)]
                self._results = [(tot, late, on_time, avg_days)] if tot > 0 else []
            return

        # 7. get_discount_vs_profit
        if "discount_tier" in q_lower or "band" in q_lower:
            self.description = [("band",), ("total_revenue",), ("total_discount",), ("total_profit",), ("order_count",)]
            self._results = []
            return

        self.description = []
        self._results = []

    def fetchone(self):
        return self._results[0] if self._results else None

    def fetchall(self):
        return self._results


# --- User contexts ---
USER_T10 = UserOut(
    id=10,
    name="T10 Owner",
    email="owner@tenant10.com",
    role=UserRole.SMB_OWNER,
    tenant_id=10,
)

USER_T99 = UserOut(
    id=99,
    name="Empty Tenant Owner",
    email="owner@tenant99.com",
    role=UserRole.SMB_OWNER,
    tenant_id=99,
)

USER_ADMIN = UserOut(
    id=1,
    name="Platform Admin",
    email="admin@helios.io",
    role=UserRole.ADMIN,
    tenant_id=None,
)

_active_user: Dict[str, Optional[UserOut]] = {"user": None}


def set_user(user: UserOut):
    _active_user["user"] = user


@pytest.fixture
def client():
    mock_cursor = AnchoredTestMockCursor()
    c = TestClient(app)
    app.dependency_overrides[get_db_cursor] = lambda: mock_cursor
    app.dependency_overrides[get_current_user] = lambda: _active_user["user"]
    yield c
    app.dependency_overrides.clear()


# =============================================================================
# VERIFICATION TESTS
# =============================================================================

def test_anchored_dates_three_different_totals(client):
    """
    Assert that days=7, days=30, and all-time:
    1. Return three different totals.
    2. Each total equals the manually computed sum of only the rows inside that window.
    3. data_as_of reflects the tenant's own latest business date (>= 100 days before today).
    """
    # Verify test fixture preconditions
    assert (TODAY - ANCHOR_DATE_T10).days >= 100, "Anchor date must be at least 100 days before today"
    assert SPAN_DAYS >= 60, "Seed rows must span at least 60 days"

    set_user(USER_T10)

    # 1. days=7 query
    res_7 = client.get("/api/dashboard/revenue-trend?days=7")
    assert res_7.status_code == 200, res_7.text
    data_7 = res_7.json()

    # 2. days=30 query
    res_30 = client.get("/api/dashboard/revenue-trend?days=30")
    assert res_30.status_code == 200, res_30.text
    data_30 = res_30.json()

    # 3. all-time (no range) query
    res_all = client.get("/api/dashboard/revenue-trend")
    assert res_all.status_code == 200, res_all.text
    data_all = res_all.json()

    # --- Verification 1: Three different totals ---
    tot_7 = data_7["total_revenue"]
    tot_30 = data_30["total_revenue"]
    tot_all = data_all["total_revenue"]

    assert tot_7 != tot_30, f"Expected days=7 total ({tot_7}) != days=30 total ({tot_30})"
    assert tot_30 != tot_all, f"Expected days=30 total ({tot_30}) != all-time total ({tot_all})"
    assert tot_7 != tot_all, f"Expected days=7 total ({tot_7}) != all-time total ({tot_all})"

    # --- Verification 2: Each equals manually computed sum of only rows inside that window ---
    # days=7: [anchor_date - 6 days, anchor_date] (7 inclusive calendar days)
    start_7 = ANCHOR_DATE_T10 - timedelta(days=6)
    expected_7_rows = [r for r in SEEDED_DAILY_SUMMARY if r["tenant_id"] == 10 and start_7 <= r["date_obj"] <= ANCHOR_DATE_T10]
    expected_7_sum = round(sum(r["total_revenue"] for r in expected_7_rows), 2)
    expected_7_orders = sum(r["total_orders"] for r in expected_7_rows)

    assert data_7["total_revenue"] == pytest.approx(expected_7_sum, 0.01)
    assert data_7["total_orders"] == expected_7_orders
    assert len(data_7["points"]) == 7

    # days=30: [anchor_date - 29 days, anchor_date] (30 inclusive calendar days)
    start_30 = ANCHOR_DATE_T10 - timedelta(days=29)
    expected_30_rows = [r for r in SEEDED_DAILY_SUMMARY if r["tenant_id"] == 10 and start_30 <= r["date_obj"] <= ANCHOR_DATE_T10]
    expected_30_sum = round(sum(r["total_revenue"] for r in expected_30_rows), 2)
    expected_30_orders = sum(r["total_orders"] for r in expected_30_rows)

    assert data_30["total_revenue"] == pytest.approx(expected_30_sum, 0.01)
    assert data_30["total_orders"] == expected_30_orders
    assert len(data_30["points"]) == 30

    # all-time: all 65 rows
    expected_all_rows = [r for r in SEEDED_DAILY_SUMMARY if r["tenant_id"] == 10]
    expected_all_sum = round(sum(r["total_revenue"] for r in expected_all_rows), 2)
    expected_all_orders = sum(r["total_orders"] for r in expected_all_rows)

    assert data_all["total_revenue"] == pytest.approx(expected_all_sum, 0.01)
    assert data_all["total_orders"] == expected_all_orders
    assert len(data_all["points"]) == SPAN_DAYS

    # --- Verification 3: data_as_of field is populated with anchor date ISO string ---
    assert data_7["data_as_of"] == ANCHOR_DATE_T10.isoformat()
    assert data_30["data_as_of"] == ANCHOR_DATE_T10.isoformat()
    assert data_all["data_as_of"] == ANCHOR_DATE_T10.isoformat()


def test_tenant_with_zero_rows_returns_valid_empty_response(client):
    """
    Assert that a tenant with zero rows returns a valid empty response with data_as_of = null,
    and NEVER raises an HTTP 500 or 400 error across all dashboard endpoints.
    """
    set_user(USER_T99)

    # 1. revenue-trend
    res = client.get("/api/dashboard/revenue-trend?days=30")
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["total_revenue"] == 0.0
    assert data["total_orders"] == 0
    assert data["points"] == []
    assert data["data_as_of"] is None

    # 2. top-products
    res_prod = client.get("/api/dashboard/top-products?days=30")
    assert res_prod.status_code == 200, res_prod.text
    data_prod = res_prod.json()
    assert data_prod["products"] == []
    assert data_prod["data_as_of"] is None

    # 3. late-delivery-risk
    res_risk = client.get("/api/dashboard/late-delivery-risk?days=30")
    assert res_risk.status_code == 200, res_risk.text
    data_risk = res_risk.json()
    assert data_risk["total_shipments"] == 0
    assert data_risk["late_rate_pct"] == 0.0
    assert data_risk["status_breakdown"] == []
    assert data_risk["data_as_of"] is None

    # 4. discount-vs-profit
    res_disc = client.get("/api/dashboard/discount-vs-profit?days=30")
    assert res_disc.status_code == 200, res_disc.text
    data_disc = res_disc.json()
    assert data_disc["bands"] == []
    assert data_disc["data_as_of"] is None

    # 5. shipping-mode-comparison
    res_ship = client.get("/api/dashboard/shipping-mode-comparison?days=30")
    assert res_ship.status_code == 200, res_ship.text
    data_ship = res_ship.json()
    assert data_ship["modes"] == []
    assert data_ship["data_as_of"] is None


def test_oversight_dashboard_matches_smb_dashboard(client):
    """
    Assert that the oversight dashboard for a tenant (/api/oversight/dashboard/{tenant_id})
    returns the SAME totals and data_as_of as the tenant's own dashboard for the same range.
    """
    ranges = [7, 30, None]

    for days in ranges:
        param = f"?days={days}" if days is not None else ""

        # Tenant's own SMB dashboard call
        set_user(USER_T10)
        smb_res = client.get(f"/api/dashboard/revenue-trend{param}")
        assert smb_res.status_code == 200, smb_res.text
        smb_data = smb_res.json()

        # Admin View-As oversight dashboard call
        set_user(USER_ADMIN)
        oversight_res = client.get(f"/api/oversight/dashboard/10{param}")
        assert oversight_res.status_code == 200, oversight_res.text
        oversight_data = oversight_res.json()

        # Check identical revenue, order counts, and data_as_of
        oversight_rev = oversight_data["revenue_trend"]
        assert oversight_rev["total_revenue"] == pytest.approx(smb_data["total_revenue"], 0.01)
        assert oversight_rev["total_orders"] == smb_data["total_orders"]
        assert oversight_rev["data_as_of"] == smb_data["data_as_of"]
        assert oversight_data["data_as_of"] == smb_data["data_as_of"]
        assert len(oversight_rev["points"]) == len(smb_data["points"])


def test_oversight_dashboard_empty_tenant_matches_smb(client):
    """
    Assert that oversight dashboard for a zero-data tenant returns empty results with
    data_as_of = None, matching the SMB empty dashboard exactly.
    """
    # SMB endpoint
    set_user(USER_T99)
    smb_res = client.get("/api/dashboard/revenue-trend?days=30")
    assert smb_res.status_code == 200
    smb_data = smb_res.json()

    # Admin oversight endpoint
    set_user(USER_ADMIN)
    oversight_res = client.get("/api/oversight/dashboard/99?days=30")
    assert oversight_res.status_code == 200
    oversight_data = oversight_res.json()

    assert oversight_data["data_as_of"] is None
    assert oversight_data["revenue_trend"]["total_revenue"] == 0.0
    assert oversight_data["revenue_trend"]["data_as_of"] is None
    assert oversight_data["revenue_trend"]["total_revenue"] == smb_data["total_revenue"]
