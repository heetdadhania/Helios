from datetime import datetime
import re
from typing import Any, List, Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator
from app.schemas.auth import UserRole


class TeamMemberCreate(BaseModel):
    """Schema for registering a new internal team member or admin."""

    name: str = Field(..., min_length=2, max_length=150, description="Full display name")
    email: EmailStr = Field(..., description="Unique corporate email address")
    phone_number: str = Field(..., min_length=7, max_length=20, description="Contact phone number (7-20 chars)")
    role: UserRole = Field(..., description="Role limited to team_member or admin")
    staff_id: Optional[str] = Field(None, max_length=100, description="Staff employee or badge ID")
    designation: Optional[str] = Field(None, max_length=150, description="Job title or designation")
    tenant_ids: Optional[List[int]] = Field(default_factory=list, description="List of tenant IDs assigned to this member")

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: UserRole) -> UserRole:
        if v not in (UserRole.TEAM_MEMBER, UserRole.ADMIN):
            raise ValueError("Role must be either 'team_member' or 'admin'.")
        return v

    @field_validator("phone_number")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        trimmed = v.strip()
        if not re.match(r"^[0-9+\-() ]{7,20}$", trimmed):
            raise ValueError("Phone number must contain only digits, spaces, plus, dash, and parentheses, and be 7-20 characters long.")
        return trimmed


class TeamMemberOut(BaseModel):
    """Public representation of an operations team member or admin. Never includes any password field."""

    user_id: int = Field(..., description="Unique user identifier")
    name: str = Field(..., description="Full display name")
    email: EmailStr = Field(..., description="Corporate email address")
    phone_number: Optional[str] = Field(None, description="Contact phone number")
    role: str = Field(..., description="Assigned platform role (team_member or admin)")
    staff_id: Optional[str] = Field(None, description="Staff employee ID")
    designation: Optional[str] = Field(None, description="Job title or designation")
    is_active: Optional[bool] = Field(default=True, description="Account active status")
    created_at: Optional[datetime] = Field(None, description="Account creation timestamp")
    tenant_ids: List[int] = Field(default_factory=list, description="List of currently assigned tenant IDs")
    assigned_tenants: List[int] = Field(default_factory=list, description="Alias for assigned tenant IDs")
    must_change_password: Optional[bool] = Field(default=False, description="Flag indicating if user must change password upon next login")
    failed_login_count: Optional[int] = Field(default=0, description="Count of failed logins")

    # Compatibility alias
    id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True, extra="allow")

    @model_validator(mode="before")
    @classmethod
    def sync_id_and_tenants(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "user_id" in data and ("id" not in data or data.get("id") is None):
                data["id"] = data["user_id"]
            elif "id" in data and ("user_id" not in data or data.get("user_id") is None):
                data["user_id"] = data["id"]
            if "tenant_ids" in data and not data.get("assigned_tenants"):
                data["assigned_tenants"] = data["tenant_ids"]
            elif "assigned_tenants" in data and not data.get("tenant_ids"):
                data["tenant_ids"] = data["assigned_tenants"]
            if data.get("must_change_password") is None:
                data["must_change_password"] = False
            if data.get("is_active") is None:
                data["is_active"] = True
            if data.get("failed_login_count") is None:
                data["failed_login_count"] = 0
        return data


class TeamMemberCreatedResponse(TeamMemberOut):
    """Response returned ONCE upon team member creation containing the generated temporary password."""

    temporary_password: str = Field(..., description="Generated one-time temporary password (never shown again)")


class ReplaceAssignmentsRequest(BaseModel):
    """Payload schema for replacing the assignment list of a team member."""

    tenant_ids: List[int] = Field(..., description="New list of assigned tenant IDs")


class ToggleActiveRequest(BaseModel):
    """Payload schema for activating or deactivating a team member."""

    is_active: bool = Field(..., description="New active status")
