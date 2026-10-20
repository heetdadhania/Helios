from datetime import datetime
import re
from typing import Any, Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator


INDIAN_STATES_AND_UTS = {
    "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh", "Goa",
    "Gujarat", "Haryana", "Himachal Pradesh", "Jharkhand", "Karnataka", "Kerala",
    "Madhya Pradesh", "Maharashtra", "Manipur", "Meghalaya", "Mizoram", "Nagaland",
    "Odisha", "Punjab", "Rajasthan", "Sikkim", "Tamil Nadu", "Telangana", "Tripura",
    "Uttar Pradesh", "Uttarakhand", "West Bengal",
    # 8 Union Territories
    "Andaman and Nicobar Islands", "Chandigarh",
    "Dadra and Nagar Haveli and Daman and Diu", "Delhi", "Jammu and Kashmir",
    "Ladakh", "Lakshadweep", "Puducherry",
}

PIN_CODE_REGEX = re.compile(r"^[1-9][0-9]{5}$")
GSTIN_REGEX = re.compile(r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]$")


def validate_indian_phone(v: Optional[str]) -> Optional[str]:
    if v is None:
        return None
    trimmed = v.strip()
    if not trimmed:
        return None
    cleaned = re.sub(r"[\s\-()]", "", trimmed)
    if cleaned.startswith("+91"):
        cleaned = cleaned[3:]
    elif cleaned.startswith("91") and len(cleaned) == 12:
        cleaned = cleaned[2:]
    if len(cleaned) != 10 or cleaned[0] not in "6789" or not cleaned.isdigit():
        raise ValueError("Phone number must be a valid 10-digit Indian number starting with 6, 7, 8, or 9 (optional +91).")
    return trimmed


class TenantBase(BaseModel):
    """Base schema attributes for tenant organization identification."""

    business_name: str = Field(..., min_length=2, max_length=150, description="Legal or trading name of the business")
    industry: str = Field(..., min_length=2, max_length=100, description="Industry vertical (e.g. Apparel, Electronics, Retail)")
    contact_person_name: str = Field(..., min_length=2, max_length=150, description="Full name of primary contact person")
    contact_email: EmailStr = Field(..., description="Primary administrative point-of-contact email address")
    phone_number: str = Field(..., min_length=7, max_length=20, description="Primary contact phone number (10 digits starting with 6-9, optional +91)")
    address_line1: str = Field(..., min_length=2, max_length=255, description="Street address line 1")
    city: str = Field(..., min_length=2, max_length=100, description="City or municipality")
    state: str = Field(..., min_length=2, max_length=100, description="State (from 28 Indian States & 8 Union Territories)")
    postal_code: str = Field(..., min_length=6, max_length=6, description="PIN code (6 digits, not starting with 0)")
    country: str = Field(default="India", min_length=2, max_length=100, description="Country (fixed to India)")

    # Optional fields
    address_line2: Optional[str] = Field(None, max_length=255, description="Address line 2 (suite, unit, floor)")
    website_url: Optional[str] = Field(None, max_length=255, description="Official company website URL")
    tax_id: Optional[str] = Field(None, max_length=100, description="GSTIN (15 characters standard format)")
    assigned_team_member_id: Optional[int] = Field(None, description="User ID of assigned internal team member")

    @field_validator("country")
    @classmethod
    def validate_country(cls, v: str) -> str:
        trimmed = v.strip()
        if trimmed.lower() != "india":
            raise ValueError("Country must be India.")
        return "India"

    @field_validator("state")
    @classmethod
    def validate_state(cls, v: str) -> str:
        trimmed = v.strip()
        matched = next((s for s in INDIAN_STATES_AND_UTS if s.lower() == trimmed.lower()), None)
        if not matched:
            raise ValueError(f"State '{v}' must be one of the 28 Indian States or 8 Union Territories.")
        return matched

    @field_validator("postal_code")
    @classmethod
    def validate_postal_code(cls, v: str) -> str:
        trimmed = v.strip()
        if not PIN_CODE_REGEX.match(trimmed):
            raise ValueError("PIN code must be exactly 6 digits and cannot start with 0.")
        return trimmed

    @field_validator("phone_number")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        res = validate_indian_phone(v)
        if res is None:
            raise ValueError("Phone number is required.")
        return res

    @field_validator("tax_id")
    @classmethod
    def validate_tax_id(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v.strip():
            trimmed = v.strip().upper()
            if not GSTIN_REGEX.match(trimmed):
                raise ValueError("GSTIN must be 15 characters matching standard Indian format (e.g. 29ABCDE1234F1Z5).")
            return trimmed
        return None

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

    # Owner profile details
    owner_id: Optional[int] = Field(None, description="SMB Owner user ID")
    owner_name: Optional[str] = Field(None, description="SMB Owner full name")
    owner_email: Optional[str] = Field(None, description="Email for the provisioned SMB Owner account")
    owner_phone: Optional[str] = Field(None, description="SMB Owner contact phone")
    owner_is_active: Optional[bool] = Field(None, description="SMB Owner account active status")

    # One-time credentials generated upon onboarding creation
    temporary_password: Optional[str] = Field(None, description="One-time temporary password for initial SMB Owner login")

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
            if data.get("is_active") is None:
                data["is_active"] = True
        return data


# Backwards compatibility alias
TenantResponse = TenantOut


class EditOwnerRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=150, description="Full name of owner")
    email: EmailStr = Field(..., description="Unique corporate/owner email")
    phone_number: Optional[str] = Field(None, description="Contact phone number (10 digits starting with 6-9, optional +91)")

    @field_validator("phone_number")
    @classmethod
    def validate_phone(cls, v: Optional[str]) -> Optional[str]:
        return validate_indian_phone(v)


class ToggleOwnerActiveRequest(BaseModel):
    is_active: bool = Field(..., description="Desired active status for the owner")


class ReplaceOwnerRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=150, description="Full name of new owner")
    email: EmailStr = Field(..., description="Unique corporate/owner email for new owner")
    phone_number: Optional[str] = Field(None, description="Contact phone number for new owner (10 digits starting with 6-9, optional +91)")

    @field_validator("phone_number")
    @classmethod
    def validate_phone(cls, v: Optional[str]) -> Optional[str]:
        return validate_indian_phone(v)


class OwnerResponse(BaseModel):
    user_id: int = Field(..., description="Owner user identifier")
    tenant_id: int = Field(..., description="Associated tenant ID")
    name: str = Field(..., description="Owner display name")
    email: EmailStr = Field(..., description="Owner email address")
    phone_number: Optional[str] = Field(None, description="Owner phone number")
    is_active: bool = Field(..., description="Owner active status")
    role: str = Field(default="smb_owner", description="User role")
    warning: Optional[str] = Field(None, description="Warning message, e.g., when tenant has no active owner")
    temporary_password: Optional[str] = Field(None, description="Generated temporary password (shown once)")
    must_change_password: Optional[bool] = Field(default=False, description="Flag indicating password change required")
    message: Optional[str] = Field(None, description="Action confirmation message")

    model_config = ConfigDict(from_attributes=True, extra="allow")

