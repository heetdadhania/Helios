"""Pydantic schemas for data validation and API serialization."""

from app.schemas.token import Token, TokenPayload
from app.schemas.tenant import TenantBase, TenantCreate, TenantUpdate, TenantResponse, TenantOut
from app.schemas.user import UserBase, UserCreate, UserLogin, UserResponse, UserRole
from app.schemas.dataset import (
    ColumnSchema,
    DatasetInspectRequest,
    DatasetResponse,
    DataCleanRequest,
    DataCleanResponse,
)
from app.schemas.db_connection import (
    DbConnectionBase,
    DbConnectionCreate,
    DbConnectionOut,
    DbConnectionSyncResponse,
    DbConnectionTestResult,
)
from app.schemas.api_ingest import (
    ApiIngestPayload,
    ApiIngestResponse,
    ApiKeyOut,
    ApiKeyGeneratedOut,
)

from app.schemas.confirmation import (
    PendingUploadOut,
    SchemaPreviewOut,
    ConfirmRequest,
    ConfirmResponse,
    CompletenessResponse,
)
from app.schemas.dashboard import (
    RevenueTrendPoint,
    RevenueTrendResponse,
    TopProductItem,
    TopProductsResponse,
    DeliveryRiskBreakdownItem,
    LateDeliveryRiskResponse,
    DiscountProfitBand,
    DiscountVsProfitResponse,
    ShippingModeComparisonItem,
    ShippingModeComparisonResponse,
)
from app.schemas.pipeline_health import (
    EtlAuditLogOut,
    PipelineRunDetailOut,
    PipelineRunOut,
    RestartResponse,
    RetryRequest,
    RetryResponse,
    StageHistoryItem,
)
from app.schemas.export import (
    DateRange,
    ExportFormat,
    ExportRequest,
    ReportType,
)
from app.schemas.history import (
    SmbHistoryOut,
    TeamHistoryOut,
    AdminHistoryOut,
)
from app.schemas.notification import (
    NotificationBase,
    NotificationCreate,
    NotificationOut,
    NotificationReadResponse,
    NotificationType,
)

__all__ = [
    "Token",
    "TokenPayload",
    "TenantBase",
    "TenantCreate",
    "TenantUpdate",
    "TenantResponse",
    "TenantOut",
    "UserBase",
    "UserCreate",
    "UserLogin",
    "UserResponse",
    "UserRole",
    "ColumnSchema",
    "DatasetInspectRequest",
    "DatasetResponse",
    "DataCleanRequest",
    "DataCleanResponse",
    "DbConnectionBase",
    "DbConnectionCreate",
    "DbConnectionOut",
    "DbConnectionSyncResponse",
    "DbConnectionTestResult",
    "ApiIngestPayload",
    "ApiIngestResponse",
    "ApiKeyOut",
    "ApiKeyGeneratedOut",
    "PendingUploadOut",
    "SchemaPreviewOut",
    "ConfirmRequest",
    "ConfirmResponse",
    "CompletenessResponse",
    "RevenueTrendPoint",
    "RevenueTrendResponse",
    "TopProductItem",
    "TopProductsResponse",
    "DeliveryRiskBreakdownItem",
    "LateDeliveryRiskResponse",
    "DiscountProfitBand",
    "DiscountVsProfitResponse",
    "ShippingModeComparisonItem",
    "ShippingModeComparisonResponse",
    "PipelineRunOut",
    "EtlAuditLogOut",
    "StageHistoryItem",
    "PipelineRunDetailOut",
    "RetryRequest",
    "RetryResponse",
    "RestartResponse",
    "DateRange",
    "ExportFormat",
    "ExportRequest",
    "ReportType",
    "SmbHistoryOut",
    "TeamHistoryOut",
    "AdminHistoryOut",
]
