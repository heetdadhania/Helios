import unittest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from app.core.dependencies import get_current_user, get_db_cursor
from app.main import app
from app.repositories.dashboard_repository import DashboardRepository
from app.schemas.auth import UserOut, UserRole
from app.schemas.dashboard import (
    DeliveryRiskBreakdownItem,
    DiscountProfitBand,
    DiscountVsProfitResponse,
    LateDeliveryRiskResponse,
    RevenueTrendPoint,
    RevenueTrendResponse,
    ShippingModeComparisonItem,
    ShippingModeComparisonResponse,
    TopProductItem,
    TopProductsResponse,
)
from app.services.dashboard_service import DashboardService


class TestDashboardSchemas(unittest.TestCase):
    """Test data validation and model initialization for dashboard schemas."""

    def test_revenue_trend_schemas(self):
        point = RevenueTrendPoint(
            date="2024-03-01",
            total_revenue=1500.50,
            total_orders=15,
            avg_order_value=100.03,
            total_quantity=35,
        )
        self.assertEqual(point.date, "2024-03-01")
        self.assertEqual(point.total_orders, 15)

        res = RevenueTrendResponse(
            days=30,
            total_revenue=1500.50,
            total_orders=15,
            points=[point],
        )
        self.assertEqual(len(res.points), 1)

    def test_top_products_schemas(self):
        item = TopProductItem(
            product_id=10,
            product_name="Wireless Keyboard",
            category="Electronics",
            total_revenue=2500.0,
            total_units_sold=50,
            total_orders=45,
        )
        res = TopProductsResponse(limit=10, products=[item])
        self.assertEqual(len(res.products), 1)
        self.assertEqual(res.products[0].product_name, "Wireless Keyboard")

    def test_late_delivery_risk_schemas(self):
        item = DeliveryRiskBreakdownItem(
            status_name="In Transit",
            total_shipments=40,
            late_shipments=5,
            late_rate_pct=12.5,
        )
        res = LateDeliveryRiskResponse(
            total_shipments=100,
            late_shipments=10,
            on_time_shipments=90,
            late_rate_pct=10.0,
            avg_shipping_days=3.2,
            status_breakdown=[item],
        )
        self.assertEqual(res.on_time_shipments, 90)
        self.assertEqual(len(res.status_breakdown), 1)

    def test_discount_profit_schemas(self):
        band = DiscountProfitBand(
            band="1-10%",
            total_revenue=5000.0,
            total_discount=250.0,
            total_profit=1500.0,
            profit_margin_pct=30.0,
            order_count=50,
        )
        res = DiscountVsProfitResponse(
            overall_profit_margin_pct=28.5,
            overall_discount_rate_pct=5.0,
            bands=[band],
        )
        self.assertEqual(res.bands[0].profit_margin_pct, 30.0)

    def test_shipping_mode_schemas(self):
        mode = ShippingModeComparisonItem(
            mode_name="Express",
            shipment_count=50,
            avg_shipping_days=1.8,
            late_count=2,
            late_rate_pct=4.0,
            on_time_rate_pct=96.0,
        )
        res = ShippingModeComparisonResponse(modes=[mode])
        self.assertEqual(len(res.modes), 1)


class TestDashboardRepository(unittest.TestCase):
    """Test SQL query construction and parameter scoping in DashboardRepository."""

    def setUp(self):
        self.mock_cursor = MagicMock()
        self.repo = DashboardRepository(self.mock_cursor, catalog="helios")

    def test_get_revenue_trend(self):
        self.mock_cursor.description = [
            ("date_str",),
            ("total_revenue",),
            ("total_orders",),
            ("avg_order_value",),
            ("total_quantity",),
        ]
        self.mock_cursor.fetchall.return_value = [
            ("2024-03-02", 200.0, 2, 100.0, 4),
            ("2024-03-01", 100.0, 1, 100.0, 2),
        ]

        result = self.repo.get_revenue_trend(tenant_id=7, days=7)
        # Should return in chronological ascending order
        self.assertEqual(len(result), 2)
        sql, params = self.mock_cursor.execute.call_args[0]
        self.assertIn("gold`.`fact_orders_daily_summary", sql)
        self.assertEqual(params["tenant_id"], 7)
        self.assertEqual(params["days"], 7)

    def test_get_top_products(self):
        self.mock_cursor.description = [
            ("product_id",),
            ("product_name",),
            ("category",),
            ("total_revenue",),
            ("total_units_sold",),
            ("total_orders",),
        ]
        self.mock_cursor.fetchall.return_value = [
            (1, "Prod A", "General", 500.0, 10, 5),
        ]

        result = self.repo.get_top_products(tenant_id=7, limit=5)
        self.assertEqual(len(result), 1)
        sql, params = self.mock_cursor.execute.call_args[0]
        self.assertIn("gold`.`fact_orders", sql)
        self.assertEqual(params["tenant_id"], 7)
        self.assertEqual(params["limit"], 5)

    def test_get_late_delivery_risk(self):
        # Overview query
        self.mock_cursor.description = [
            ("total_shipments",),
            ("late_shipments",),
            ("on_time_shipments",),
            ("avg_shipping_days",),
        ]
        self.mock_cursor.fetchone.return_value = (50, 5, 45, 2.5)
        # Breakdown query
        self.mock_cursor.fetchall.return_value = [
            ("Delivered", 45, 3, 6.67),
            ("In Transit", 5, 2, 40.0),
        ]

        result = self.repo.get_late_delivery_risk(tenant_id=7)
        self.assertIn("overview", result)
        self.assertIn("breakdown", result)
        self.assertEqual(result["overview"]["total_shipments"], 50)


class TestDashboardService(unittest.TestCase):
    """Test service aggregation and formatting logic."""

    def setUp(self):
        self.mock_repo = MagicMock(spec=DashboardRepository)
        self.smb_user = UserOut(
            id=10,
            name="John Owner",
            email="john@store.com",
            role=UserRole.SMB_OWNER,
            tenant_id=42,
        )

    def test_validate_tenant_rejects_none(self):
        user_no_tenant = UserOut(
            id=11,
            name="No Tenant",
            email="user@helios.internal",
            role=UserRole.SMB_OWNER,
            tenant_id=None,
        )
        with self.assertRaises(Exception) as cm:
            DashboardService.get_revenue_trend(user_no_tenant, 30, self.mock_repo)
        self.assertEqual(cm.exception.status_code, 400)

    def test_get_revenue_trend_service(self):
        self.mock_repo.get_revenue_trend.return_value = [
            {"date_str": "2024-03-01", "total_revenue": 100.0, "total_orders": 2, "avg_order_value": 50.0, "total_quantity": 4},
            {"date_str": "2024-03-02", "total_revenue": 300.0, "total_orders": 3, "avg_order_value": 100.0, "total_quantity": 6},
        ]
        res = DashboardService.get_revenue_trend(self.smb_user, 30, self.mock_repo)
        self.assertEqual(res.total_revenue, 400.0)
        self.assertEqual(res.total_orders, 5)
        self.assertEqual(len(res.points), 2)

    def test_get_discount_vs_profit_service(self):
        self.mock_repo.get_discount_vs_profit.return_value = [
            {"band": "0%", "total_revenue": 1000.0, "total_discount": 0.0, "total_profit": 300.0, "order_count": 10},
            {"band": "1-10%", "total_revenue": 500.0, "total_discount": 50.0, "total_profit": 100.0, "order_count": 5},
        ]
        res = DashboardService.get_discount_vs_profit(self.smb_user, self.mock_repo)
        self.assertEqual(len(res.bands), 2)
        self.assertEqual(res.bands[0].profit_margin_pct, 30.0)
        self.assertEqual(res.bands[1].profit_margin_pct, 20.0)
        self.assertGreater(res.overall_profit_margin_pct, 0.0)


class TestDashboardEndpoints(unittest.TestCase):
    """Test API endpoints authentication, RBAC, and response status."""

    def setUp(self):
        self.client = TestClient(app)
        self.smb_user = UserOut(
            id=10,
            name="John Owner",
            email="john@store.com",
            role=UserRole.SMB_OWNER,
            tenant_id=42,
        )
        self.team_user = UserOut(
            id=20,
            name="Alice Support",
            email="alice@helios.internal",
            role=UserRole.TEAM_MEMBER,
            tenant_id=None,
        )

    def tearDown(self):
        app.dependency_overrides.clear()

    def test_endpoints_require_auth(self):
        app.dependency_overrides[get_db_cursor] = lambda: MagicMock()
        endpoints = [
            "/api/dashboard/revenue-trend",
            "/api/dashboard/top-products",
            "/api/dashboard/late-delivery-risk",
            "/api/dashboard/discount-vs-profit",
            "/api/dashboard/shipping-mode-comparison",
        ]
        for ep in endpoints:
            res = self.client.get(ep)
            self.assertEqual(res.status_code, 401, f"Endpoint {ep} should require authentication")

    def test_endpoints_require_smb_owner_role(self):
        app.dependency_overrides[get_current_user] = lambda: self.team_user
        app.dependency_overrides[get_db_cursor] = lambda: MagicMock()

        endpoints = [
            "/api/dashboard/revenue-trend",
            "/api/dashboard/top-products",
            "/api/dashboard/late-delivery-risk",
            "/api/dashboard/discount-vs-profit",
            "/api/dashboard/shipping-mode-comparison",
        ]
        for ep in endpoints:
            res = self.client.get(ep)
            self.assertEqual(res.status_code, 403, f"Endpoint {ep} should reject non-smb_owner")

    @patch.object(DashboardService, "get_revenue_trend")
    def test_get_revenue_trend_endpoint_success(self, mock_service):
        app.dependency_overrides[get_current_user] = lambda: self.smb_user
        app.dependency_overrides[get_db_cursor] = lambda: MagicMock()

        mock_service.return_value = RevenueTrendResponse(
            days=30,
            total_revenue=2500.0,
            total_orders=25,
            points=[
                RevenueTrendPoint(date="2024-03-01", total_revenue=2500.0, total_orders=25, avg_order_value=100.0, total_quantity=50)
            ],
        )

        res = self.client.get("/api/dashboard/revenue-trend?days=30")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["days"], 30)
        self.assertEqual(data["total_revenue"], 2500.0)
        self.assertEqual(len(data["points"]), 1)

    @patch.object(DashboardService, "get_top_products")
    def test_get_top_products_endpoint_success(self, mock_service):
        app.dependency_overrides[get_current_user] = lambda: self.smb_user
        app.dependency_overrides[get_db_cursor] = lambda: MagicMock()

        mock_service.return_value = TopProductsResponse(
            limit=5,
            products=[
                TopProductItem(product_id=1, product_name="Keyboard", category="Tech", total_revenue=1200.0, total_units_sold=20, total_orders=18)
            ],
        )

        res = self.client.get("/api/dashboard/top-products?limit=5")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["limit"], 5)
        self.assertEqual(len(data["products"]), 1)

    @patch.object(DashboardService, "get_late_delivery_risk")
    def test_get_late_delivery_risk_endpoint_success(self, mock_service):
        app.dependency_overrides[get_current_user] = lambda: self.smb_user
        app.dependency_overrides[get_db_cursor] = lambda: MagicMock()

        mock_service.return_value = LateDeliveryRiskResponse(
            total_shipments=50,
            late_shipments=5,
            on_time_shipments=45,
            late_rate_pct=10.0,
            avg_shipping_days=3.0,
            status_breakdown=[],
        )

        res = self.client.get("/api/dashboard/late-delivery-risk")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["total_shipments"], 50)
        self.assertEqual(data["late_rate_pct"], 10.0)

    @patch.object(DashboardService, "get_discount_vs_profit")
    def test_get_discount_vs_profit_endpoint_success(self, mock_service):
        app.dependency_overrides[get_current_user] = lambda: self.smb_user
        app.dependency_overrides[get_db_cursor] = lambda: MagicMock()

        mock_service.return_value = DiscountVsProfitResponse(
            overall_profit_margin_pct=30.0,
            overall_discount_rate_pct=5.0,
            bands=[],
        )

        res = self.client.get("/api/dashboard/discount-vs-profit")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["overall_profit_margin_pct"], 30.0)

    @patch.object(DashboardService, "get_shipping_mode_comparison")
    def test_get_shipping_mode_comparison_endpoint_success(self, mock_service):
        app.dependency_overrides[get_current_user] = lambda: self.smb_user
        app.dependency_overrides[get_db_cursor] = lambda: MagicMock()

        mock_service.return_value = ShippingModeComparisonResponse(
            modes=[
                ShippingModeComparisonItem(
                    mode_name="Express",
                    shipment_count=20,
                    avg_shipping_days=1.5,
                    late_count=1,
                    late_rate_pct=5.0,
                    on_time_rate_pct=95.0,
                )
            ]
        )

        res = self.client.get("/api/dashboard/shipping-mode-comparison")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(len(data["modes"]), 1)
        self.assertEqual(data["modes"][0]["mode_name"], "Express")


if __name__ == "__main__":
    unittest.main()
