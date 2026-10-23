import re
from typing import Any, List, Optional, Union
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.schemas.tenant import (
    GSTIN_REGEX,
    INDIAN_STATES_AND_UTS,
    PIN_CODE_REGEX,
    validate_indian_phone,
)


class UserMe(BaseModel):
    name: str
    email: str
    phone: Optional[str] = None
    last_login: Optional[str] = None
    staff_id: Optional[str] = None
    designation: Optional[str] = None


class OrganizationProfile(BaseModel):
    business_name: str
    industry: Optional[str] = None
    contact_person: Optional[str] = None
    contact_email: Optional[str] = None
    phone: Optional[str] = None
    full_address: Optional[str] = None
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pin_code: Optional[str] = None
    website: Optional[str] = None
    gstin: Optional[str] = None
    created_date: Optional[str] = None


class TeamMemberContact(BaseModel):
    name: str
    email: str
    phone: Optional[str] = None
    designation: Optional[str] = None


class AdminContact(BaseModel):
    name: str
    email: str
    phone: Optional[str] = None


class AssignedOrgSummary(BaseModel):
    tenant_id: int
    business_name: str
    industry: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    contact_person: Optional[str] = None
    owner_name: Optional[str] = None
    owner_email: Optional[str] = None
    owner_phone: Optional[str] = None
    last_data_date: Optional[str] = None


class PlatformSummary(BaseModel):
    active_organizations: int = 0
    active_owners: int = 0
    active_team_members: int = 0


class TeamMemberSummary(BaseModel):
    user_id: int
    name: str
    email: str
    phone: Optional[str] = None
    designation: Optional[str] = None
    assigned_organizations_count: int = 0


class OwnerProfileResponse(BaseModel):
    role: str = "smb_owner"
    me: UserMe
    organization: Optional[OrganizationProfile] = None
    assigned_team_member: Optional[TeamMemberContact] = None
    admin_contact: Optional[AdminContact] = None


class TeamMemberProfileResponse(BaseModel):
    role: str = "team_member"
    me: UserMe
    assigned_organizations: List[AssignedOrgSummary] = Field(default_factory=list)
    admin_contact: Optional[AdminContact] = None


class AdminProfileResponse(BaseModel):
    role: str = "admin"
    me: UserMe
    platform_summary: PlatformSummary
    team_members: List[TeamMemberSummary] = Field(default_factory=list)


ProfileResponse = Union[OwnerProfileResponse, TeamMemberProfileResponse, AdminProfileResponse]


class ProfileUpdateMe(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None

    model_config = ConfigDict(extra="forbid")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            trimmed = v.strip()
            if len(trimmed) > 200:
                raise ValueError("Name cannot exceed 200 characters.")
            if len(trimmed) < 2 or len(trimmed) > 100:
                raise ValueError("Name must be between 2 and 100 characters.")
            return trimmed
        return None

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            trimmed = v.strip()
            if not trimmed:
                return None
            if len(trimmed) > 200:
                raise ValueError("Phone number cannot exceed 200 characters.")
            return validate_indian_phone(trimmed)
        return None


class ProfileUpdateEmail(BaseModel):
    new_email: EmailStr
    current_password: str = Field(..., min_length=1, max_length=200)

    model_config = ConfigDict(extra="forbid")

    @field_validator("new_email")
    @classmethod
    def validate_new_email(cls, v: EmailStr) -> str:
        trimmed = str(v).strip().lower()
        if len(trimmed) > 200:
            raise ValueError("Email cannot exceed 200 characters.")
        return trimmed


class ProfileUpdateOrganization(BaseModel):
    contact_person_name: Optional[str] = None
    phone_number: Optional[str] = None
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    website_url: Optional[str] = None
    tax_id: Optional[str] = None
    tenant_id: Optional[Any] = None  # Ignored if provided

    model_config = ConfigDict(extra="ignore")

    @field_validator("contact_person_name")
    @classmethod
    def validate_contact_name(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            trimmed = v.strip()
            if not trimmed:
                return None
            if len(trimmed) > 200:
                raise ValueError("Contact person name cannot exceed 200 characters.")
            if len(trimmed) < 2 or len(trimmed) > 100:
                raise ValueError("Contact person name must be between 2 and 100 characters.")
            return trimmed
        return None

    @field_validator("phone_number")
    @classmethod
    def validate_phone_number(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            trimmed = v.strip()
            if not trimmed:
                return None
            if len(trimmed) > 200:
                raise ValueError("Phone number cannot exceed 200 characters.")
            return validate_indian_phone(trimmed)
        return None

    @field_validator("address_line1")
    @classmethod
    def validate_address_line1(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            trimmed = v.strip()
            if not trimmed:
                return None
            if len(trimmed) > 200:
                raise ValueError("Address Line 1 cannot exceed 200 characters.")
            if len(trimmed) < 2:
                raise ValueError("Address Line 1 must be at least 2 characters.")
            return trimmed
        return None

    @field_validator("address_line2")
    @classmethod
    def validate_address_line2(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            trimmed = v.strip()
            if not trimmed:
                return None
            if len(trimmed) > 200:
                raise ValueError("Address Line 2 cannot exceed 200 characters.")
            return trimmed
        return None

    @field_validator("city")
    @classmethod
    def validate_city(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            trimmed = v.strip()
            if not trimmed:
                return None
            if len(trimmed) > 200:
                raise ValueError("City cannot exceed 200 characters.")
            if len(trimmed) < 2:
                raise ValueError("City must be at least 2 characters.")
            return trimmed
        return None

    @field_validator("state")
    @classmethod
    def validate_state(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            trimmed = v.strip()
            if not trimmed:
                return None
            matched = next((s for s in INDIAN_STATES_AND_UTS if s.lower() == trimmed.lower()), None)
            if not matched:
                raise ValueError(f"State '{v}' must be one of the 28 Indian States or 8 Union Territories.")
            return matched
        return None

    @field_validator("postal_code")
    @classmethod
    def validate_postal_code(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            trimmed = v.strip()
            if not trimmed:
                return None
            if not PIN_CODE_REGEX.match(trimmed):
                raise ValueError("PIN code must be exactly 6 digits and cannot start with 0.")
            return trimmed
        return None

    @field_validator("website_url")
    @classmethod
    def validate_website(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            trimmed = v.strip()
            if not trimmed:
                return None
            if len(trimmed) > 200:
                raise ValueError("Website URL cannot exceed 200 characters.")
            if not (trimmed.startswith("http://") or trimmed.startswith("https://")):
                raise ValueError("Website URL must start with http:// or https://")
            return trimmed
        return None

    @field_validator("tax_id")
    @classmethod
    def validate_tax_id(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            trimmed = v.strip().upper()
            if not trimmed:
                return None
            if len(trimmed) > 200:
                raise ValueError("Tax ID cannot exceed 200 characters.")
            if not GSTIN_REGEX.match(trimmed):
                raise ValueError("GSTIN must match the standard Indian format (e.g. 29ABCDE1234F1Z5).")
            return trimmed
        return None
