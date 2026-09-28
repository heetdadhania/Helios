from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class SupportMessageCreate(BaseModel):
    """Payload to submit a contact or status update request."""

    message: str = Field(
        ...,
        min_length=1,
        max_length=5000,
        description="Text content of the message or update inquiry",
    )


class SupportMessageOut(BaseModel):
    """Support message response representation."""

    message_id: int = Field(..., description="Unique message identifier")
    tenant_id: int = Field(..., description="Tenant context ID")
    tenant_name: Optional[str] = Field(None, description="Tenant business display name")
    from_user_id: int = Field(..., description="Sender user identifier")
    from_user_name: Optional[str] = Field(None, description="Sender display name")
    to_user_id: int = Field(..., description="Routed recipient user identifier")
    to_user_name: Optional[str] = Field(None, description="Routed recipient display name")
    message: str = Field(..., description="Message content")
    status: str = Field("open", description="Message resolution status: open or resolved")
    created_at: datetime = Field(..., description="Timestamp when message was submitted")
    resolved_at: Optional[datetime] = Field(None, description="Timestamp when message was marked resolved")

    model_config = {"from_attributes": True}


class SupportMessageResolveResponse(BaseModel):
    """Response returned when a support message is marked resolved."""

    success: bool = True
    message: str = "Support message marked as resolved."
    message_id: int
    status: str = "resolved"
    resolved_at: datetime
