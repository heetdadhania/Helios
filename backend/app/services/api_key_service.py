from datetime import datetime, timezone
from typing import Optional

from app.core.api_key_security import (
    API_KEY_PREFIX,
    generate_api_key as core_generate_api_key,
    hash_api_key as core_hash_api_key,
    mask_api_key as core_mask_api_key,
    verify_api_key as core_verify_api_key,
)
from app.repositories.api_key_repository import ApiKeyRepository
from app.schemas.api_ingest import ApiKeyGeneratedOut, ApiKeyOut


class ApiKeyService:
    """Service handling cryptographic generation, hashing, and management of tenant API keys."""

    @staticmethod
    def generate_api_key() -> str:
        """Generate a cryptographically secure random API key with standard prefix."""
        return core_generate_api_key(prefix=API_KEY_PREFIX)

    @staticmethod
    def hash_api_key(raw_key: str) -> str:
        """Compute one-way SHA-256 cryptographic hash of raw API key for secure persistence."""
        return core_hash_api_key(raw_key)

    @staticmethod
    def mask_api_key(raw_key: str) -> str:
        """Create a masked string displaying only the prefix and the final 4 characters."""
        return core_mask_api_key(raw_key, prefix=API_KEY_PREFIX)

    @classmethod
    def verify_api_key(cls, raw_key: str, stored_hash: str) -> bool:
        """Perform constant-time cryptographic verification of raw API key against stored hash."""
        return core_verify_api_key(raw_key, stored_hash)

    @classmethod
    def get_tenant_api_key(
        cls,
        tenant_id: int,
        repo: ApiKeyRepository,
    ) -> Optional[ApiKeyOut]:
        """Fetch current active API key metadata for tenant (only masked key exposed)."""
        record = repo.get_active_by_tenant(tenant_id)
        if not record:
            return None

        # If key_prefix was stored as masked representation or prefix, use it
        masked = record.get("key_prefix") or f"{API_KEY_PREFIX}••••"

        return ApiKeyOut(
            api_key_id=int(record["api_key_id"]),
            tenant_id=int(record["tenant_id"]),
            masked_key=masked,
            created_at=record.get("created_at"),
            last_used_at=record.get("last_used_at"),
            is_active=bool(record.get("is_active", True)),
        )

    @classmethod
    def regenerate_api_key(
        cls,
        tenant_id: int,
        repo: ApiKeyRepository,
    ) -> ApiKeyGeneratedOut:
        """Invalidate old keys, generate a new cryptographic key, and store only its hash."""
        # 1. Invalidate any active keys for this tenant
        repo.revoke_by_tenant(tenant_id)

        # 2. Generate new raw key and compute hash
        raw_key = cls.generate_api_key()
        key_hash = cls.hash_api_key(raw_key)
        masked_key = cls.mask_api_key(raw_key)

        # 3. Persist only hash and masked prefix
        record = repo.create(
            tenant_id=tenant_id,
            key_hash=key_hash,
            key_prefix=masked_key,
        )

        return ApiKeyGeneratedOut(
            api_key_id=int(record["api_key_id"]),
            tenant_id=int(record["tenant_id"]),
            api_key=raw_key,
            masked_key=masked_key,
            created_at=record.get("created_at") or datetime.now(timezone.utc),
            message="API key generated successfully. Save this key now; it will not be displayed again.",
        )
