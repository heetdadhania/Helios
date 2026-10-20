from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator


class UserRole(str, Enum):
    """Permitted platform user roles for RBAC enforcement."""

    SMB_OWNER = "smb_owner"
    TEAM_MEMBER = "team_member"
    ADMIN = "admin"


class LoginRequest(BaseModel):
    """Payload schema for user credential authentication."""

    email: EmailStr = Field(..., description="User corporate or store email address")
    password: str = Field(..., min_length=6, description="Plaintext password")


class UserOut(BaseModel):
    """Public user identity representation returned in responses and auth/me."""

    id: int = Field(..., description="Primary user ID from platform.users")
    name: str = Field(..., description="Full user display name")
    email: EmailStr = Field(..., description="User email address")
    role: UserRole = Field(..., description="Assigned platform RBAC role")
    tenant_id: Optional[int] = Field(None, description="Associated tenant organization ID (NULL for admins)")
    must_change_password: Optional[bool] = Field(default=False, description="Flag indicating if user must change password upon next login")
    is_active: Optional[bool] = Field(default=True, description="Account active status")
    failed_login_count: Optional[int] = Field(default=0, description="Count of failed logins")

    model_config = ConfigDict(from_attributes=True, extra="allow")

    @model_validator(mode="before")
    @classmethod
    def handle_nulls(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if data.get("must_change_password") is None:
                data["must_change_password"] = False
            if data.get("is_active") is None:
                data["is_active"] = True
            if data.get("failed_login_count") is None:
                data["failed_login_count"] = 0
        return data


class TokenResponse(BaseModel):
    """Authentication response payload containing JWT access token and user profile."""

    access_token: str = Field(..., description="Signed JWT bearer access token")
    token_type: str = Field(default="bearer", description="Token scheme identifier")
    user: UserOut = Field(..., description="Public profile of authenticated user")


class ChangePasswordRequest(BaseModel):
    """Payload schema for first-login or on-demand user password change."""

    current_password: str = Field(..., min_length=1, description="Current plaintext password")
    new_password: str = Field(..., min_length=10, description="New plaintext password (minimum 10 characters)")


class ResetPasswordResponse(BaseModel):
    """Payload returned upon administrative or team member password reset."""

    temporary_password: str = Field(..., description="High-entropy temporary password shown once")
    must_change_password: bool = Field(default=True, description="Flag indicating password change required")
    message: str = Field(default="Temporary password generated successfully. It will only be shown once.", description="Status message")

