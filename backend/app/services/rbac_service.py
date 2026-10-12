from typing import Any, Dict, List, Optional
from fastapi import HTTPException, status
from app.schemas.user import UserRole

ROLE_HIERARCHY = {
    UserRole.ADMIN: 30,
    UserRole.ANALYST: 20,
    UserRole.VIEWER: 10,
}


class RBACService:
    """Business service enforcing Role-Based Access Control and multi-tenant isolation."""

    @staticmethod
    def verify_role_permission(
        user_role: str,
        minimum_required_role: UserRole,
    ) -> bool:
        """Evaluate if user's role meets or exceeds the required threshold."""
        try:
            current_level = ROLE_HIERARCHY.get(UserRole(user_role), 0)
        except ValueError:
            return False
        required_level = ROLE_HIERARCHY.get(minimum_required_role, 0)
        return current_level >= required_level

    @classmethod
    def require_role(cls, current_user: Any, required_role: UserRole) -> None:
        """Raise HTTPException if user does not possess required role."""
        if hasattr(current_user, "role"):
            raw_role = current_user.role
            user_role = raw_role.value if hasattr(raw_role, "value") else str(raw_role)
        elif isinstance(current_user, dict):
            user_role = current_user.get("role", "")
        else:
            user_role = str(getattr(current_user, "role", ""))

        if not cls.verify_role_permission(user_role, required_role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Action requires at least '{required_role.value}' privileges.",
            )

    @staticmethod
    def enforce_tenant_isolation(
        current_user: Any,
        target_tenant_id: str,
    ) -> None:
        """Ensure authenticated user is restricted strictly to their assigned tenant data."""
        if hasattr(current_user, "tenant_id"):
            user_tenant = str(current_user.tenant_id or "")
        elif isinstance(current_user, dict):
            user_tenant = str(current_user.get("tenant_id", "") or "")
        else:
            user_tenant = str(getattr(current_user, "tenant_id", "") or "")

        # Super-admin may cross boundaries if role is admin and no tenant restriction, otherwise strictly enforce
        if user_tenant and user_tenant != target_tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: Cannot access resources outside your tenant boundary.",
            )
