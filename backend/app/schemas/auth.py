from enum import Enum
from typing import Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field


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

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    """Authentication response payload containing JWT access token and user profile."""

    access_token: str = Field(..., description="Signed JWT bearer access token")
    token_type: str = Field(default="bearer", description="Token scheme identifier")
    user: UserOut = Field(..., description="Public profile of authenticated user")
