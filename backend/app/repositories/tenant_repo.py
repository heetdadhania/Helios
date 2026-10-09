"""
Legacy tenant repository module - re-exports comprehensive TenantRepository from tenant_repository.
"""
from app.repositories.tenant_repository import TenantRepository

__all__ = ["TenantRepository"]
