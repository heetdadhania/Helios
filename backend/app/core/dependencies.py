from typing import Any, Callable, Dict, Generator, Optional, Sequence
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import jwt
try:
    from databricks.sql.client import Connection, Cursor
except ImportError:
    Connection = Any  # type: ignore
    Cursor = Any  # type: ignore

from app.core import security
from app.core.tenant_context import TenantContext
from app.db.base import get_databricks_connection
from app.repositories.user_repository import UserRepository
from app.schemas.auth import UserOut, UserRole

security_bearer = HTTPBearer(auto_error=False)


def get_db_connection() -> Generator[Connection, None, None]:
    """Yield a Databricks SQL connection for request lifecycle and ensure cleanup."""
    conn = get_databricks_connection()
    try:
        yield conn
    finally:
        try:
            conn.close()
        except Exception:
            pass


def get_db_cursor(
    conn: Connection = Depends(get_db_connection),
) -> Generator[Cursor, None, None]:
    """Yield an active Databricks SQL cursor scoped to current request."""
    cursor = conn.cursor()
    try:
        yield cursor
    finally:
        try:
            cursor.close()
        except Exception:
            pass


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer),
    cursor: Cursor = Depends(get_db_cursor),
) -> UserOut:
    """
    Extract and validate JWT Bearer token, verify active status in platform.users,
    and return the typed UserOut profile.
    """
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token missing or invalid header format.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = security.decode_access_token(credentials.credentials)
        user_id_str = payload.get("sub")
        if not user_id_str:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token claims: subject missing.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        user_id = int(user_id_str)
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token has expired. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    repo = UserRepository(cursor)
    user_record = repo.get_by_id(user_id)
    if not user_record:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account no longer exists.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user_record.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account has been deactivated.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return UserOut(
        id=int(user_record["user_id"]),
        name=str(user_record["name"]),
        email=str(user_record["email"]),
        role=UserRole(user_record["role"]),
        tenant_id=int(user_record["tenant_id"]) if user_record.get("tenant_id") is not None else None,
    )


def require_role(*roles: str) -> Callable[[UserOut], UserOut]:
    """
    Dependency factory checking that the authenticated user possesses one of the allowed roles.
    
    Examples:
      - SMB Owner-only: Depends(require_role("smb_owner"))
      - Team Member + Admin: Depends(require_role("team_member", "admin"))
      - Admin-only: Depends(require_role("admin"))
    """
    allowed_set = {r.lower() for r in roles}

    def role_checker(current_user: UserOut = Depends(get_current_user)) -> UserOut:
        if current_user.role.value.lower() not in allowed_set:
            roles_str = ", ".join(sorted(allowed_set))
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: Operation requires one of the following roles: [{roles_str}].",
            )
        return current_user

    return role_checker


# Convenient pre-configured role dependencies
require_smb_owner = require_role("smb_owner")
require_team_or_admin = require_role("team_member", "admin")
require_admin = require_role("admin")

# Alias for backwards compatibility across existing endpoints
get_current_active_user = get_current_user


def get_tenant_context(
    current_user: UserOut = Depends(get_current_user),
) -> TenantContext:
    """Provide a TenantContext helper tied to the active authenticated user."""
    return TenantContext(
        tenant_id=current_user.tenant_id,
        user_role=current_user.role.value,
        user_id=current_user.id,
    )
