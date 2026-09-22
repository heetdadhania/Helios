from typing import Optional
from pydantic import BaseModel, Field


class Token(BaseModel):
    """Schema for JWT access token response."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int


class TokenPayload(BaseModel):
    """Schema for decoded JWT token payload."""

    sub: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = None
    tenant_id: Optional[str] = None
    exp: Optional[int] = None
