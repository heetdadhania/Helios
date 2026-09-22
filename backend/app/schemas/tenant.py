from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class TenantBase(BaseModel):
    """Base schema attributes for a tenant."""

    name: str = Field(..., min_length=2, max_length=100, description="Organization or customer name")
    slug: str = Field(..., min_length=2, max_length=100, description="URL and catalog safe identifier")
    catalog_name: str = Field(..., description="Unity Catalog namespace for this tenant")
    schema_name: str = Field(default="default", description="Default Unity Catalog schema")


class TenantCreate(TenantBase):
    """Schema for tenant creation request."""
    pass


class TenantUpdate(BaseModel):
    """Schema for updating tenant configuration."""

    name: Optional[str] = Field(None, min_length=2, max_length=100)
    catalog_name: Optional[str] = None
    schema_name: Optional[str] = None
    is_active: Optional[bool] = None


class TenantResponse(TenantBase):
    """Schema for tenant response."""

    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
