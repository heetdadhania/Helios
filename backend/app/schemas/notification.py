from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class NotificationType(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    APPROVAL_REQUIRED = "approval_required"
    PIPELINE_SUCCESS = "pipeline_success"


class NotificationBase(BaseModel):
    tenant_id: Optional[int] = Field(None, description="Target tenant organization ID")
    user_id: Optional[int] = Field(None, description="Target user ID (NULL for tenant-wide broadcast)")
    message: str = Field(..., min_length=1, description="Notification body")
    type: str = Field(default="info", description="Notification category (info, warning, error, pipeline_success)")


class NotificationCreate(NotificationBase):
    pass


class NotificationOut(NotificationBase):
    notification_id: int = Field(..., description="Unique notification log ID")
    is_read: bool = Field(default=False, description="Read state indicator")
    created_at: Optional[datetime] = Field(default=None, description="Creation timestamp")

    model_config = ConfigDict(from_attributes=True)


class NotificationReadResponse(BaseModel):
    notification_id: int
    is_read: bool
    message: str = "Notification marked as read."
