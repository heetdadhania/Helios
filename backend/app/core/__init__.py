"""Core package providing configuration, credential security, exceptions, and API response wrappers."""

from app.core.config import settings
from app.core.exceptions import (
    CredentialSecurityException,
    DuplicateException,
    HeliosException,
    NotFoundException,
    PipelineStageException,
    TenantMismatchException,
    ValidationException,
)
from app.core.response import (
    ApiResponse,
    error_response,
    success_response,
)
from app.core.secrets_manager import (
    decode_secret_value,
    decrypt_field,
    encrypt_field,
    get_databricks_workspace_client,
    retrieve_db_credential,
    sanitize_error_message,
    store_db_credential,
)
from app.core.api_key_security import (
    generate_api_key,
    hash_api_key,
    mask_api_key,
    verify_api_key,
)

__all__ = [
    "settings",
    "HeliosException",
    "NotFoundException",
    "DuplicateException",
    "ValidationException",
    "TenantMismatchException",
    "PipelineStageException",
    "CredentialSecurityException",
    "ApiResponse",
    "success_response",
    "error_response",
    "store_db_credential",
    "retrieve_db_credential",
    "encrypt_field",
    "decrypt_field",
    "sanitize_error_message",
    "decode_secret_value",
    "get_databricks_workspace_client",
    "generate_api_key",
    "hash_api_key",
    "verify_api_key",
    "mask_api_key",
]
