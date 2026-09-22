from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field


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
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
