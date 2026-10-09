import logging
from typing import Any, Dict, Optional
from fastapi import HTTPException, status
from databricks.sql.client import Cursor
from app.core import security
from app.repositories.user_repository import UserRepository
from app.schemas.auth import TokenResponse, UserOut

logger = logging.getLogger(__name__)


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
        
        Handles distinct failure outcomes with structured logging:
          1. Database/connection error -> HTTP 503 (Service Unavailable)
          2. User not found -> HTTP 401 (Invalid email or password)
          3. Password mismatch -> HTTP 401 (Invalid email or password)
          4. User deactivated -> HTTP 401 (Account deactivated)
        """
        clean_email = email.strip().lower()
        repo = UserRepository(cursor)

        try:
            user = repo.get_by_email(clean_email)
        except Exception as exc:
            # Outcome: Database / Connection Error (e.g. warehouse cold start / wake-up timeout)
            logger.error(
                "Login failure: database/connection error while retrieving user record [email=%s]: %s",
                clean_email,
                exc,
                exc_info=True,
                extra={
                    "event": "auth_login_error",
                    "outcome": "database_connection_error",
                    "email": clean_email,
                    "error": str(exc),
                },
            )
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Service temporarily unavailable, please try again.",
            )

        # Outcome: User Not Found
        if not user:
            logger.warning(
                "Login failure: user record not found in platform.users [email=%s]",
                clean_email,
                extra={
                    "event": "auth_login_failure",
                    "outcome": "user_not_found",
                    "email": clean_email,
                },
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Outcome: Password Mismatch (Verification is NOT retried)
        stored_hash = str(user.get("password_hash", ""))
        if not cls.verify_password(password, stored_hash):
            logger.warning(
                "Login failure: password mismatch for user [email=%s, user_id=%s]",
                clean_email,
                user.get("user_id"),
                extra={
                    "event": "auth_login_failure",
                    "outcome": "password_mismatch",
                    "email": clean_email,
                    "user_id": user.get("user_id"),
                },
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Outcome: Account Deactivated
        if not user.get("is_active", True):
            logger.warning(
                "Login failure: user account is deactivated [email=%s, user_id=%s]",
                clean_email,
                user.get("user_id"),
                extra={
                    "event": "auth_login_failure",
                    "outcome": "account_deactivated",
                    "email": clean_email,
                    "user_id": user.get("user_id"),
                },
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account has been deactivated. Contact your administrator.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Outcome: Successful Authentication
        logger.info(
            "Login success: user authenticated successfully [email=%s, user_id=%s, role=%s]",
            clean_email,
            user.get("user_id"),
            user.get("role"),
            extra={
                "event": "auth_login_success",
                "outcome": "login_success",
                "email": clean_email,
                "user_id": user.get("user_id"),
                "role": user.get("role"),
            },
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
            must_change_password=bool(user.get("must_change_password", False)),
        )
        return TokenResponse(
            access_token=token,
            token_type="bearer",
            user=user_out,
        )
