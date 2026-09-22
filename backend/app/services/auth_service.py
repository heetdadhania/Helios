from typing import Any, Dict, Optional
from fastapi import HTTPException, status
from databricks.sql.client import Cursor
from app.core import security
from app.repositories.user_repository import UserRepository
from app.schemas.auth import TokenResponse, UserOut


class AuthService:
    """Business service orchestrating authentication, password verification, and JWT issuance."""

    @staticmethod
    def verify_password(plain_password: str, password_hash: str) -> bool:
        """Validate plaintext password against stored bcrypt hash."""
        return security.verify_password(plain_password, password_hash)

    @staticmethod
    def create_access_token(user: Dict[str, Any]) -> str:
        """Generate a signed JWT bearer token containing user identity and tenant claims."""
        user_id = user["user_id"]
        role = user["role"]
        tenant_id = user.get("tenant_id")
        return security.create_access_token(
            user_id=user_id,
            role=role,
            tenant_id=tenant_id,
        )

    @classmethod
    def authenticate_user(
        cls,
        cursor: Cursor,
        email: str,
        password: str,
    ) -> Dict[str, Any]:
        """
        Authenticate user credentials against Databricks platform.users table.
        
        Raises HTTP 401 if user does not exist, password does not match, or account is disabled.
        """
        repo = UserRepository(cursor)
        user = repo.get_by_email(email)

        if not user or not cls.verify_password(password, str(user.get("password_hash", ""))):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not user.get("is_active", True):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account has been deactivated. Contact your administrator.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return user

    @classmethod
    def build_token_response(cls, user: Dict[str, Any]) -> TokenResponse:
        """Package authenticated user record into TokenResponse schema."""
        token = cls.create_access_token(user)
        user_out = UserOut(
            id=int(user["user_id"]),
            name=str(user["name"]),
            email=str(user["email"]),
            role=user["role"],
            tenant_id=int(user["tenant_id"]) if user.get("tenant_id") is not None else None,
        )
        return TokenResponse(
            access_token=token,
            token_type="bearer",
            user=user_out,
        )
