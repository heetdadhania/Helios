"""
Versioned /api/v1/tenants endpoints.
Re-exports the full tenant management router from app.api.tenants for consistency.
"""
from app.api.tenants import router

__all__ = ["router"]
