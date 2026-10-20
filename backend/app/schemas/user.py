from datetime import datetime
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator


class UserRole(str, Enum):
    """Supported platform user roles for RBAC enforcement."""

    ADMIN = "admin"
    ANALYST = "analyst"
    VIEWER = "viewer"


class UserBase(BaseModel):
    """Base schema attributes for a platform user."""

    email: EmailStr
    full_name: Optional[str] = None
    role: UserRole = UserRole.ANALYST
    tenant_id: int


class UserCreate(UserBase):
    """Schema for registering a new user."""

    password: str = Field(..., min_length=8, description="User password (min 8 characters)")


class UserLogin(BaseModel):
    """Schema for user credentials authentication."""

    email: EmailStr
    password: str
    tenant_id: Optional[int] = None


class UserResponse(UserBase):
    """Schema for user public details response."""

    id: int
    is_active: Optional[bool] = Field(default=True)
    created_at: Optional[datetime] = None
    must_change_password: Optional[bool] = Field(default=False)
    failed_login_count: Optional[int] = Field(default=0)

    model_config = ConfigDict(from_attributes=True, extra="allow")

    @model_validator(mode="before")
    @classmethod
    def handle_nulls(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if data.get("is_active") is None:
                data["is_active"] = True
            if data.get("must_change_password") is None:
                data["must_change_password"] = False
            if data.get("failed_login_count") is None:
                data["failed_login_count"] = 0
        return data
