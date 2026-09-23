import io
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
from app.schemas.export import DateRange, ExportFormat, ExportRequest, ReportType
from app.services.dashboard_service import DashboardService
from app.services.export_service import ExportService


class TestExportSchemas(unittest.TestCase):
    """Test validation and defaults for Export schemas."""

    def test_export_request_valid(self):
        req = ExportRequest(
            report_type=ReportType.REVENUE_TREND,
            format=ExportFormat.CSV,
            date_range=DateRange(days=14),
        )
        self.assertEqual(req.report_type, ReportType.REVENUE_TREND)
        self.assertEqual(req.format, ExportFormat.CSV)
        self.assertEqual(req.date_range.days, 14)

    def test_export_request_defaults(self):
        req = ExportRequest(
            report_type=ReportType.TOP_PRODUCTS,
            format=ExportFormat.PDF,
        )
        self.assertEqual(req.format, ExportFormat.PDF)
        self.assertEqual(req.date_range.days, 30)


class TestExportService(unittest.TestCase):
    """Test CSV and PDF export generation reusing DashboardService."""

    def setUp(self):
        self.mock_repo = MagicMock(spec=DashboardRepository)
        self.owner_user = UserOut(
            id=10,
            name="SMB Owner",
            email="owner@helios.com",
            role=UserRole.SMB_OWNER,
            tenant_id=42,
        )

    @patch.object(DashboardService, "get_revenue_trend")
    def test_export_revenue_trend_csv(self, mock_trend):
        mock_trend.return_value = RevenueTrendResponse(
            days=30,
            total_revenue=15000.50,
            total_orders=120,
            points=[
                RevenueTrendPoint(
                    date="2026-09-01",
                    total_revenue=1500.0,
                    total_orders=10,
                    avg_order_value=150.0,
                    total_quantity=25,
                )
            ],
        )

        req = ExportRequest(report_type=ReportType.REVENUE_TREND, format=ExportFormat.CSV)
        content, media_type, filename = ExportService.generate_export(
            current_user=self.owner_user,
            request=req,
            repo=self.mock_repo,
        )

        self.assertIn("text/csv", media_type)
        self.assertTrue(filename.startswith("helios_revenue_trend_tenant42_"))
        self.assertTrue(filename.endswith(".csv"))

        decoded = content.decode("utf-8-sig")
        self.assertIn("Date,Total Revenue ($),Total Orders,Avg Order Value ($),Total Quantity", decoded)
        self.assertIn("2026-09-01,1500.00,10,150.00,25", decoded)
        self.assertIn("Summary Total Revenue,15000.50,Total Orders,120", decoded)

    @patch.object(DashboardService, "get_top_products")
    def test_export_top_products_csv(self, mock_products):
        mock_products.return_value = TopProductsResponse(
            limit=50,
            products=[
                TopProductItem(
                    product_id=1,
                    product_name="Trail Running Shoes",
                    category="Footwear",
                    total_revenue=8400.0,
                    total_units_sold=60,
                    total_orders=55,
                )
            ],
        )

        req = ExportRequest(report_type=ReportType.TOP_PRODUCTS, format=ExportFormat.CSV)
        content, media_type, filename = ExportService.generate_export(
            current_user=self.owner_user,
            request=req,
            repo=self.mock_repo,
        )

        self.assertIn("text/csv", media_type)
        decoded = content.decode("utf-8-sig")
        self.assertIn("Rank,Product ID,Product Name,Category,Revenue ($),Units Sold,Orders", decoded)
        self.assertIn("1,1,Trail Running Shoes,Footwear,8400.00,60,55", decoded)

    @patch.object(DashboardService, "get_revenue_trend")
    def test_export_revenue_trend_pdf(self, mock_trend):
        mock_trend.return_value = RevenueTrendResponse(
            days=30,
            total_revenue=5000.0,
            total_orders=40,
            points=[
                RevenueTrendPoint(
                    date="2026-09-10",
                    total_revenue=500.0,
                    total_orders=4,
                    avg_order_value=125.0,
                    total_quantity=8,
                )
            ],
        )

        req = ExportRequest(report_type=ReportType.REVENUE_TREND, format=ExportFormat.PDF)
        content, media_type, filename = ExportService.generate_export(
            current_user=self.owner_user,
            request=req,
            repo=self.mock_repo,
        )

        self.assertEqual(media_type, "application/pdf")
        self.assertTrue(filename.endswith(".pdf"))
        self.assertTrue(content.startswith(b"%PDF-"))
        self.assertGreater(len(content), 500)

    @patch.object(DashboardService, "get_top_products")
    def test_export_top_products_pdf(self, mock_products):
        mock_products.return_value = TopProductsResponse(
            limit=50,
            products=[
                TopProductItem(
                    product_id=2,
                    product_name="Insulated Water Bottle",
                    category="Accessories",
                    total_revenue=2500.0,
                    total_units_sold=100,
                    total_orders=95,
                )
            ],
        )

        req = ExportRequest(report_type=ReportType.TOP_PRODUCTS, format=ExportFormat.PDF)
        content, media_type, filename = ExportService.generate_export(
            current_user=self.owner_user,
            request=req,
            repo=self.mock_repo,
        )

        self.assertEqual(media_type, "application/pdf")
        self.assertTrue(filename.endswith(".pdf"))
        self.assertTrue(content.startswith(b"%PDF-"))

    @patch.object(DashboardService, "get_revenue_trend")
    @patch.object(DashboardService, "get_top_products")
    @patch.object(DashboardService, "get_late_delivery_risk")
    @patch.object(DashboardService, "get_discount_vs_profit")
    @patch.object(DashboardService, "get_shipping_mode_comparison")
    def test_export_full_dashboard_csv_and_pdf(
        self,
        mock_shipping,
        mock_discount,
        mock_risk,
        mock_products,
        mock_trend,
    ):
        mock_trend.return_value = RevenueTrendResponse(days=30, total_revenue=1000.0, total_orders=10, points=[])
        mock_products.return_value = TopProductsResponse(limit=10, products=[])
        mock_risk.return_value = LateDeliveryRiskResponse(
            total_shipments=50,
            late_shipments=5,
            on_time_shipments=45,
            late_rate_pct=10.0,
            avg_shipping_days=3.2,
            status_breakdown=[],
        )
        mock_discount.return_value = DiscountVsProfitResponse(overall_profit_margin_pct=25.0, overall_discount_rate_pct=5.0, bands=[])
        mock_shipping.return_value = ShippingModeComparisonResponse(modes=[])

        # Test CSV full dashboard
        req_csv = ExportRequest(report_type=ReportType.FULL_DASHBOARD, format=ExportFormat.CSV)
        content_csv, _, _ = ExportService.generate_export(self.owner_user, req_csv, self.mock_repo)
        self.assertIn("SECTION 1: REVENUE TREND", content_csv.decode("utf-8-sig"))
        self.assertIn("SECTION 3: FULFILLMENT RISK", content_csv.decode("utf-8-sig"))

        # Test PDF full dashboard
        req_pdf = ExportRequest(report_type=ReportType.FULL_DASHBOARD, format=ExportFormat.PDF)
        content_pdf, _, _ = ExportService.generate_export(self.owner_user, req_pdf, self.mock_repo)
        self.assertTrue(content_pdf.startswith(b"%PDF-"))

    def test_user_without_tenant_raises_400(self):
        user_no_tenant = UserOut(
            id=11,
            name="No Tenant",
            email="notenant@helios.com",
            role=UserRole.SMB_OWNER,
            tenant_id=None,
        )
        from fastapi import HTTPException
        with self.assertRaises(HTTPException) as ctx:
            ExportService.generate_export(
                current_user=user_no_tenant,
                request=ExportRequest(report_type=ReportType.REVENUE_TREND, format=ExportFormat.CSV),
                repo=self.mock_repo,
            )
        self.assertEqual(ctx.exception.status_code, 400)


class TestExportAPI(unittest.TestCase):
    """Integration and authorization tests for POST /api/export."""

    def setUp(self):
        self.client = TestClient(app)
        self.mock_cursor = MagicMock()
        app.dependency_overrides[get_db_cursor] = lambda: self.mock_cursor

    def tearDown(self):
        app.dependency_overrides.clear()

    def test_team_member_forbidden(self):
        team_user = UserOut(
            id=2,
            name="Team Member",
            email="team@helios.com",
            role=UserRole.TEAM_MEMBER,
            tenant_id=None,
        )
        app.dependency_overrides[get_current_user] = lambda: team_user

        response = self.client.post(
            "/api/export",
            json={"report_type": "revenue_trend", "format": "csv"},
        )
        self.assertEqual(response.status_code, 403)

    @patch.object(ExportService, "generate_export")
    def test_smb_owner_success(self, mock_generate):
        mock_generate.return_value = (
            b"Date,Revenue\n2026-09-01,100.00\n",
            "text/csv; charset=utf-8",
            "helios_export_test.csv",
        )

        owner_user = UserOut(
            id=1,
            name="SMB Owner",
            email="owner@helios.com",
            role=UserRole.SMB_OWNER,
            tenant_id=10,
        )
        app.dependency_overrides[get_current_user] = lambda: owner_user

        response = self.client.post(
            "/api/export",
            json={"report_type": "revenue_trend", "format": "csv", "date_range": {"days": 30}},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/csv", response.headers["content-type"])
        self.assertIn('attachment; filename="helios_export_test.csv"', response.headers["content-disposition"])
        self.assertIn("2026-09-01,100.00", response.text)
