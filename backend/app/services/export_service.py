import csv
import io
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple
from fastapi import HTTPException, status

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from app.repositories.dashboard_repository import DashboardRepository
from app.schemas.auth import UserOut
from app.schemas.export import ExportFormat, ExportRequest, ReportType
from app.services.dashboard_service import DashboardService

logger = logging.getLogger("helios.services.export")

# Locate bundled fonts
FONTS_DIR = Path(__file__).resolve().parent.parent / "fonts"
DEJAVU_REGULAR = FONTS_DIR / "DejaVuSans.ttf"
DEJAVU_BOLD = FONTS_DIR / "DejaVuSans-Bold.ttf"


def _ensure_fonts_registered() -> None:
    """Ensure DejaVu Sans TrueType fonts supporting Rupee (₹) glyph are registered."""
    reg = pdfmetrics.getRegisteredFontNames()
    if "DejaVuSans" not in reg and DEJAVU_REGULAR.exists():
        pdfmetrics.registerFont(TTFont("DejaVuSans", str(DEJAVU_REGULAR)))
    if "DejaVuSans-Bold" not in reg and DEJAVU_BOLD.exists():
        pdfmetrics.registerFont(TTFont("DejaVuSans-Bold", str(DEJAVU_BOLD)))


def format_inr(amount: float) -> str:
    """Format numeric amount into Indian Rupee string with Indian digit grouping: ₹12,34,567.50."""
    try:
        val = float(amount)
    except (ValueError, TypeError):
        return "₹0.00"
    s = f"{val:.2f}"
    parts = s.split(".")
    integer_part, decimal_part = parts[0], parts[1]
    is_neg = integer_part.startswith("-")
    if is_neg:
        integer_part = integer_part[1:]
    if len(integer_part) > 3:
        last3 = integer_part[-3:]
        rest = integer_part[:-3]
        groups = []
        while len(rest) > 2:
            groups.insert(0, rest[-2:])
            rest = rest[:-2]
        if rest:
            groups.insert(0, rest)
        integer_formatted = ",".join(groups) + "," + last3
    else:
        integer_formatted = integer_part
    prefix = "-" if is_neg else ""
    return f"₹{prefix}{integer_formatted}.{decimal_part}"


def format_date_in(date_val: Any) -> str:
    """Format date to Indian convention DD/MM/YYYY."""
    if not date_val:
        return ""
    s = str(date_val).strip()
    try:
        if len(s) >= 10 and s[4] == "-" and s[7] == "-":
            dt = datetime.strptime(s[:10], "%Y-%m-%d")
            return dt.strftime("%d/%m/%Y")
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        return dt.strftime("%d/%m/%Y")
    except Exception:
        return s


class ExportService:
    """Service generating CSV and PDF exports by reusing Gold-layer dashboard queries."""

    @staticmethod
    def _validate_tenant(current_user: UserOut) -> int:
        """Validate authenticated organization association."""
        if current_user.tenant_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User account is not linked to any organization.",
            )
        return int(current_user.tenant_id)

    @classmethod
    def generate_export(
        cls,
        current_user: UserOut,
        request: ExportRequest,
        repo: DashboardRepository,
    ) -> Tuple[bytes, str, str]:
        """
        Main entry point for generating dashboard exports.
        Returns tuple of (file_bytes, media_type, filename).
        """
        tenant_id = cls._validate_tenant(current_user)
        report_type = request.report_type
        days = request.date_range.days if (request.date_range and request.date_range.days) else 30
        timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

        # Fetch dashboard analytics data by reusing DashboardService
        data = cls._fetch_dashboard_data(current_user, report_type, days, repo)

        # Generate CSV or PDF
        if request.format == ExportFormat.CSV:
            csv_str = cls._build_csv(report_type, tenant_id, data)
            content = csv_str.encode("utf-8-sig")  # UTF-8 BOM for Excel
            filename = f"helios_{report_type.value}_org{tenant_id}_{timestamp_str}.csv"
            return content, "text/csv; charset=utf-8", filename

        pdf_bytes = cls._build_pdf(report_type, tenant_id, data)
        filename = f"helios_{report_type.value}_org{tenant_id}_{timestamp_str}.pdf"
        return pdf_bytes, "application/pdf", filename

    @classmethod
    def _fetch_dashboard_data(
        cls,
        current_user: UserOut,
        report_type: ReportType,
        days: int,
        repo: DashboardRepository,
    ) -> Dict[str, Any]:
        """Fetch report data by reusing DashboardService methods."""
        if report_type == ReportType.REVENUE_TREND:
            return {"revenue_trend": DashboardService.get_revenue_trend(current_user, days, repo)}
        if report_type == ReportType.TOP_PRODUCTS:
            return {"top_products": DashboardService.get_top_products(current_user, 50, repo)}

        # Full dashboard view
        return {
            "revenue_trend": DashboardService.get_revenue_trend(current_user, days, repo),
            "top_products": DashboardService.get_top_products(current_user, 10, repo),
            "delivery_risk": DashboardService.get_late_delivery_risk(current_user, repo),
            "discount_profit": DashboardService.get_discount_vs_profit(current_user, repo),
            "shipping_modes": DashboardService.get_shipping_mode_comparison(current_user, repo),
        }

    @classmethod
    def _build_csv(
        cls,
        report_type: ReportType,
        tenant_id: int,
        data: Dict[str, Any],
    ) -> str:
        """Serialize report data to structured CSV string."""
        output = io.StringIO()
        writer = csv.writer(output, lineterminator="\n")

        if report_type == ReportType.REVENUE_TREND:
            cls._write_revenue_csv(writer, data["revenue_trend"])
        elif report_type == ReportType.TOP_PRODUCTS:
            cls._write_top_products_csv(writer, data["top_products"])
        else:
            cls._write_full_dashboard_csv(writer, data)

        return output.getvalue()

    @staticmethod
    def _write_revenue_csv(writer: Any, trend: Any) -> None:
        """Write revenue trend rows to CSV with plain numbers and INR unit headers."""
        writer.writerow(["Date (DD/MM/YYYY)", "Total Revenue (INR)", "Total Orders", "Avg Order Value (INR)", "Total Quantity"])
        for p in trend.points:
            writer.writerow([
                format_date_in(p.date),
                f"{p.total_revenue:.2f}",
                p.total_orders,
                f"{p.avg_order_value:.2f}",
                p.total_quantity,
            ])
        writer.writerow([])
        writer.writerow(["Summary Total Revenue (INR)", f"{trend.total_revenue:.2f}", "Total Orders", trend.total_orders])

    @staticmethod
    def _write_top_products_csv(writer: Any, top_prod: Any) -> None:
        """Write top products rows to CSV with plain numbers and INR unit headers."""
        writer.writerow(["Rank", "Product ID", "Product Name", "Category", "Revenue (INR)", "Units Sold", "Orders"])
        for idx, prod in enumerate(top_prod.products, start=1):
            writer.writerow([
                idx,
                prod.product_id,
                prod.product_name,
                prod.category or "General",
                f"{prod.total_revenue:.2f}",
                prod.total_units_sold,
                prod.total_orders,
            ])

    @classmethod
    def _write_full_dashboard_csv(cls, writer: Any, data: Dict[str, Any]) -> None:
        """Write combined full dashboard sections to CSV."""
        writer.writerow(["=== SECTION 1: REVENUE TREND ==="])
        cls._write_revenue_csv(writer, data["revenue_trend"])
        writer.writerow([])
        writer.writerow(["=== SECTION 2: TOP PRODUCTS ==="])
        cls._write_top_products_csv(writer, data["top_products"])
        writer.writerow([])
        writer.writerow(["=== SECTION 3: FULFILLMENT RISK ==="])
        risk = data["delivery_risk"]
        writer.writerow(["Total Shipments", risk.total_shipments, "Late Shipments", risk.late_shipments, "Late Rate (%)", f"{risk.late_rate_pct:.2f}%"])

    @classmethod
    def _build_pdf(
        cls,
        report_type: ReportType,
        tenant_id: int,
        data: Dict[str, Any],
    ) -> bytes:
        """Construct lightweight PDF document using reportlab and embedded DejaVu Sans font."""
        _ensure_fonts_registered()
        reg_fonts = pdfmetrics.getRegisteredFontNames()
        bold_font = "DejaVuSans-Bold" if "DejaVuSans-Bold" in reg_fonts else "Helvetica-Bold"
        regular_font = "DejaVuSans" if "DejaVuSans" in reg_fonts else "Helvetica"

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=36,
            leftMargin=36,
            topMargin=36,
            bottomMargin=36,
        )

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "ReportTitle",
            parent=styles["Heading1"],
            fontName=bold_font,
            fontSize=16,
            leading=20,
            textColor=colors.HexColor("#0f172a"),
        )
        subtitle_style = ParagraphStyle(
            "ReportSubtitle",
            parent=styles["Normal"],
            fontName=regular_font,
            fontSize=9,
            leading=12,
            textColor=colors.HexColor("#64748b"),
        )

        elements: List[Any] = []
        gen_time = datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M:%S UTC")
        title_text = f"Helios Analytics Report: {report_type.value.replace('_', ' ').title()}"

        elements.append(Paragraph(title_text, title_style))
        elements.append(Paragraph(f"Organization ID: {tenant_id} | Generated: {gen_time}", subtitle_style))
        elements.append(Spacer(1, 16))

        if report_type == ReportType.REVENUE_TREND:
            cls._append_revenue_pdf_table(elements, data["revenue_trend"], styles, bold_font, regular_font)
        elif report_type == ReportType.TOP_PRODUCTS:
            cls._append_top_products_pdf_table(elements, data["top_products"], styles, bold_font, regular_font)
        else:
            cls._append_full_dashboard_pdf_tables(elements, data, styles, bold_font, regular_font)

        doc.build(elements)
        return buffer.getvalue()

    @staticmethod
    def _append_revenue_pdf_table(elements: List[Any], trend: Any, styles: Any, bold_font: str, regular_font: str) -> None:
        """Append revenue trend table to PDF story."""
        table_data = [["Date (DD/MM/YYYY)", "Revenue", "Orders", "AOV", "Units"]]
        for p in trend.points[-20:]:  # Last 20 days for compact fit
            table_data.append([
                format_date_in(p.date),
                format_inr(p.total_revenue),
                str(p.total_orders),
                format_inr(p.avg_order_value),
                str(p.total_quantity),
            ])

        table = Table(table_data, colWidths=[110, 110, 70, 110, 70])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
            ("FONTNAME", (0, 0), (-1, 0), bold_font),
            ("FONTNAME", (0, 1), (-1, -1), regular_font),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ]))
        elements.append(table)

    @staticmethod
    def _append_top_products_pdf_table(elements: List[Any], top_prod: Any, styles: Any, bold_font: str, regular_font: str) -> None:
        """Append top products table to PDF story."""
        table_data = [["Rank", "Product Name", "Category", "Revenue", "Units", "Orders"]]
        cell_style = ParagraphStyle("CellNormal", parent=styles["Normal"], fontName=regular_font, fontSize=8, leading=10)
        for idx, prod in enumerate(top_prod.products[:15], start=1):
            name_p = Paragraph(prod.product_name[:35], cell_style)
            table_data.append([
                str(idx),
                name_p,
                prod.category or "General",
                format_inr(prod.total_revenue),
                str(prod.total_units_sold),
                str(prod.total_orders),
            ])

        table = Table(table_data, colWidths=[35, 175, 80, 100, 40, 40])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
            ("FONTNAME", (0, 0), (-1, 0), bold_font),
            ("FONTNAME", (0, 1), (-1, -1), regular_font),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("ALIGN", (3, 0), (-1, -1), "RIGHT"),
        ]))
        elements.append(table)

    @classmethod
    def _append_full_dashboard_pdf_tables(cls, elements: List[Any], data: Dict[str, Any], styles: Any, bold_font: str, regular_font: str) -> None:
        """Append multi-section full dashboard tables to PDF story."""
        h2_style = ParagraphStyle("H2", parent=styles["Heading2"], fontName=bold_font, fontSize=12, leading=14, textColor=colors.HexColor("#1e293b"))
        elements.append(Paragraph("1. Daily Revenue Trend", h2_style))
        elements.append(Spacer(1, 6))
        cls._append_revenue_pdf_table(elements, data["revenue_trend"], styles, bold_font, regular_font)
        elements.append(Spacer(1, 14))
        elements.append(Paragraph("2. Top Performing Products", h2_style))
        elements.append(Spacer(1, 6))
        cls._append_top_products_pdf_table(elements, data["top_products"], styles, bold_font, regular_font)
