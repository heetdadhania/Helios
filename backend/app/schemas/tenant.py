from datetime import datetime
import re
from typing import Any, Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator


class TenantBase(BaseModel):
    """Base schema attributes for tenant organization identification."""

    business_name: str = Field(..., min_length=2, max_length=150, description="Legal or trading name of the business")
    industry: str = Field(..., min_length=2, max_length=100, description="Industry vertical (e.g. Apparel, Electronics, Retail)")
    contact_person_name: str = Field(..., min_length=2, max_length=150, description="Full name of primary contact person")
    contact_email: EmailStr = Field(..., description="Primary administrative point-of-contact email address")
    phone_number: str = Field(..., min_length=7, max_length=20, description="Primary contact phone number (7-20 chars)")
    address_line1: str = Field(..., min_length=2, max_length=255, description="Street address line 1")
    city: str = Field(..., min_length=2, max_length=100, description="City or municipality")
    state: str = Field(..., min_length=2, max_length=100, description="State, province, or region")
    postal_code: str = Field(..., min_length=2, max_length=20, description="Postal / ZIP code")
    country: str = Field(..., min_length=2, max_length=100, description="Country name or ISO code")

    # Optional fields
    address_line2: Optional[str] = Field(None, max_length=255, description="Address line 2 (suite, unit, floor)")
    website_url: Optional[str] = Field(None, max_length=255, description="Official company website URL")
    tax_id: Optional[str] = Field(None, max_length=100, description="Corporate Tax ID, EIN, or VAT registration")
    assigned_team_member_id: Optional[int] = Field(None, description="User ID of assigned internal team member")

    @field_validator("phone_number")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        trimmed = v.strip()
        if not re.match(r"^[0-9+\-() ]{7,20}$", trimmed):
            raise ValueError("Phone number must contain only digits, spaces, plus, dash, and parentheses, and be 7-20 characters long.")
        return trimmed

    @field_validator("website_url")
    @classmethod
    def validate_website(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v.strip():
            trimmed = v.strip()
            if not (trimmed.startswith("http://") or trimmed.startswith("https://")):
                raise ValueError("website_url must start with http:// or https://")
            return trimmed
        return None


class TenantCreate(TenantBase):
    """Schema for tenant onboarding creation request."""

    # Optional dedicated SMB owner login email; defaults to contact_email if omitted
    owner_email: Optional[EmailStr] = Field(None, description="Email for the provisioned SMB Owner account")

    # Legacy compatibility fields
    name: Optional[str] = None
    slug: Optional[str] = None
    catalog_name: Optional[str] = None
    schema_name: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def normalize_incoming_data(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # If legacy "name" provided instead of "business_name", map it
            if "business_name" not in data and "name" in data:
                data["business_name"] = data["name"]
        return data


class TenantUpdate(BaseModel):
    """Schema for updating existing tenant details."""

    business_name: Optional[str] = Field(None, min_length=2, max_length=150)
    industry: Optional[str] = Field(None, min_length=2, max_length=100)
    contact_person_name: Optional[str] = Field(None, min_length=2, max_length=150)
    contact_email: Optional[EmailStr] = None
    phone_number: Optional[str] = None
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None
    website_url: Optional[str] = None
    tax_id: Optional[str] = None
    assigned_team_member_id: Optional[int] = None
    is_active: Optional[bool] = None


class TenantOut(BaseModel):
    """Public tenant representation returned in API responses."""

    tenant_id: int = Field(..., description="Unique tenant identifier")
    business_name: str = Field(..., description="Legal business name")
    industry: Optional[str] = Field(None, description="Industry sector")
    contact_person_name: Optional[str] = Field(None, description="Primary contact full name")
    contact_email: str = Field(..., description="Primary contact email")
    phone_number: Optional[str] = Field(None, description="Contact phone number")
    address_line1: Optional[str] = Field(None, description="Street address line 1")
    address_line2: Optional[str] = Field(None, description="Address line 2")
    city: Optional[str] = Field(None, description="City")
    state: Optional[str] = Field(None, description="State / Province")
    postal_code: Optional[str] = Field(None, description="Postal / ZIP code")
    country: Optional[str] = Field(None, description="Country")
    website_url: Optional[str] = Field(None, description="Official website")
    tax_id: Optional[str] = Field(None, description="Tax ID / EIN")
    assigned_team_member_id: Optional[int] = Field(None, description="Assigned team member ID")
    created_by: Optional[int] = Field(None, description="Creator user ID")
    created_at: Optional[datetime] = Field(None, description="Creation timestamp")
    is_active: bool = Field(default=True, description="Tenant active status")

    # One-time credentials generated upon onboarding creation
    temporary_password: Optional[str] = Field(None, description="One-time temporary password for initial SMB Owner login")
    owner_email: Optional[str] = Field(None, description="Email for the provisioned SMB Owner account")

    # Compatibility aliases
    id: Optional[int] = None
    name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True, extra="allow")

    @model_validator(mode="before")
    @classmethod
    def populate_aliases(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # Sync tenant_id <-> id
            if "tenant_id" in data and ("id" not in data or data.get("id") is None):
                data["id"] = data["tenant_id"]
            elif "id" in data and ("tenant_id" not in data or data.get("tenant_id") is None):
                data["tenant_id"] = data["id"]
            # Sync business_name <-> name
            if "business_name" in data and ("name" not in data or data.get("name") is None):
                data["name"] = data["business_name"]
            elif "name" in data and ("business_name" not in data or data.get("business_name") is None):
                data["business_name"] = data["name"]
        return data


# Backwards compatibility alias
TenantResponse = TenantOut
