from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class ReportType(str, Enum):
    """Allowed dashboard export report types."""

    REVENUE_TREND = "revenue_trend"
    TOP_PRODUCTS = "top_products"
    FULL_DASHBOARD = "full_dashboard"


class ExportFormat(str, Enum):
    """Supported export document formats."""

    CSV = "csv"
    PDF = "pdf"


class DateRange(BaseModel):
    """Optional date filtering parameters for export queries."""

    days: Optional[int] = Field(30, ge=1, le=365, description="Lookback window in days")
    start_date: Optional[str] = Field(None, description="Optional start date ISO string (YYYY-MM-DD)")
    end_date: Optional[str] = Field(None, description="Optional end date ISO string (YYYY-MM-DD)")


class ExportRequest(BaseModel):
    """Payload to request a data export of customer dashboard metrics."""

    report_type: ReportType = Field(
        ...,
        description="Type of dashboard view to export: revenue_trend, top_products, full_dashboard",
    )
    format: ExportFormat = Field(
        ...,
        description="Desired file format: csv or pdf",
    )
    date_range: Optional[DateRange] = Field(
        default_factory=DateRange,
        description="Optional date range parameters for lookback window",
    )
