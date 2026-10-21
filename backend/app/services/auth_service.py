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
        simulate_db_error: bool = False,
    ) -> Dict[str, Any]:
        """
        Authenticate user credentials against Databricks platform.users table.
        
        Handles distinct failure outcomes with structured logging:
          1. Database/connection error -> HTTP 503 (Service Unavailable)
             (Never increments failed attempts counter or reports invalid credentials)
          2. User not found -> HTTP 401 (Invalid email or password)
          3. Account locked -> HTTP 423 (Locked for 15 minutes after 5 failed attempts)
          4. Password mismatch -> HTTP 401 (or HTTP 423 if reaching 5 attempts)
          5. User deactivated -> HTTP 401 (Account deactivated)
          6. Success -> Updates last_login_at, resets failed count & lockout
        """
        clean_email = email.strip().lower()
        repo = UserRepository(cursor)

        try:
            if simulate_db_error:
                raise RuntimeError("Simulated Databricks warehouse connection timeout / cold start error.")
            user = repo.get_by_email(clean_email)
        except Exception as exc:
            # Outcome: Database / Connection Error (e.g. warehouse cold start / wake-up timeout)
            # MUST NEVER increase failed attempts counter or be reported as invalid credentials
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
                detail="Authentication service temporarily unavailable due to database error or warehouse cold start. Please retry.",
            )

        # Outcome: User Not Found (Do not reveal whether email exists)
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

        # Outcome: Account Locked
        import json
        from datetime import datetime, timezone
        now_utc = datetime.now(timezone.utc)
        locked_until = user.get("locked_until")
        is_currently_locked = False

        if locked_until is not None:
            if isinstance(locked_until, datetime):
                dt_locked = locked_until.replace(tzinfo=timezone.utc) if locked_until.tzinfo is None else locked_until
                is_currently_locked = dt_locked > now_utc
            else:
                try:
                    dt_parsed = datetime.fromisoformat(str(locked_until).replace("Z", "+00:00"))
                    if dt_parsed.tzinfo is None:
                        dt_parsed = dt_parsed.replace(tzinfo=timezone.utc)
                    is_currently_locked = dt_parsed > now_utc
                except Exception:
                    is_currently_locked = False

        if is_currently_locked:
            logger.warning(
                "Login blocked: account is locked until %s [email=%s, user_id=%s]",
                locked_until,
                clean_email,
                user.get("user_id"),
                extra={
                    "event": "auth_login_blocked_locked",
                    "email": clean_email,
                    "user_id": user.get("user_id"),
                    "locked_until": str(locked_until),
                },
            )
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail="Account is temporarily locked due to 5 consecutive failed login attempts. Please try again in 15 minutes.",
            )

        # Outcome: Password Mismatch (Count ONLY real wrong-password results)
        stored_hash = str(user.get("password_hash", ""))
        user_id = int(user["user_id"])
        user_role = str(user.get("role", "smb_owner"))
        tenant_id = user.get("tenant_id")

        if not cls.verify_password(password, stored_hash):
            # If previous lockout had expired, start fresh count from 0
            current_failed = 0 if (locked_until is not None and not is_currently_locked) else int(user.get("failed_login_count") or 0)
            new_failed = current_failed + 1

            if new_failed >= 5:
                # 5 consecutive failed attempts: Lock account for 15 minutes and create audit row
                try:
                    repo.record_failed_attempt(user_id=user_id, new_count=new_failed, lock_until=True)
                    repo.write_audit_log(
                        actor_user_id=user_id,
                        actor_role=user_role,
                        action="account_locked",
                        tenant_id=tenant_id,
                        reason="Account locked for 15 minutes after 5 consecutive failed login attempts",
                        details_json=json.dumps({
                            "email": clean_email,
                            "failed_login_count": new_failed,
                            "lockout_duration_minutes": 15,
                        }),
                    )
                except Exception as exc:
                    logger.error("Failed to record lockout in database: %s", exc)

                logger.warning(
                    "Login lockout: account locked for 15 minutes after %d failed attempts [email=%s, user_id=%s]",
                    new_failed,
                    clean_email,
                    user_id,
                    extra={
                        "event": "auth_account_locked",
                        "email": clean_email,
                        "user_id": user_id,
                        "failed_count": new_failed,
                    },
                )
                raise HTTPException(
                    status_code=status.HTTP_423_LOCKED,
                    detail="Account is temporarily locked due to 5 consecutive failed login attempts. Please try again in 15 minutes.",
                )
            else:
                try:
                    repo.record_failed_attempt(user_id=user_id, new_count=new_failed, lock_until=False)
                except Exception as exc:
                    logger.error("Failed to increment failed login count: %s", exc)

                logger.warning(
                    "Login failure: password mismatch for user [email=%s, user_id=%s, consecutive_failed=%d]",
                    clean_email,
                    user_id,
                    new_failed,
                    extra={
                        "event": "auth_login_failure",
                        "outcome": "password_mismatch",
                        "email": clean_email,
                        "user_id": user_id,
                        "failed_count": new_failed,
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
        # Update last_login_at and reset failed count & lockout
        try:
            repo.record_login_success(user_id=user_id)
            user["last_login_at"] = now_utc
            user["failed_login_count"] = 0
            user["locked_until"] = None
        except Exception as exc:
            logger.error("Failed to update last_login_at on login success: %s", exc)

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
            business_name=user.get("business_name"),
            must_change_password=bool(user.get("must_change_password", False)),
        )
        return TokenResponse(
            access_token=token,
            token_type="bearer",
            user=user_out,
        )
