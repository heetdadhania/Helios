"""Pydantic schemas for data validation and API serialization."""

from app.schemas.token import Token, TokenPayload
from app.schemas.tenant import TenantBase, TenantCreate, TenantUpdate, TenantResponse
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

__all__ = [
    "Token",
    "TokenPayload",
    "TenantBase",
    "TenantCreate",
    "TenantUpdate",
    "TenantResponse",
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
]
