"""
Helios Platform - Shared Domain Exceptions

Defines standardized domain exceptions with associated HTTP status codes and detail payloads.
"""

from typing import Any, Dict, Optional
from fastapi import status


class HeliosException(Exception):
    """Base exception for all domain and platform errors in Helios."""

    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.details = details or {}


class NotFoundException(HeliosException):
    """Raised when a requested resource (tenant, user, upload, run) does not exist."""

    def __init__(
        self,
        message: str = "Resource not found",
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(
            message=message,
            status_code=status.HTTP_404_NOT_FOUND,
            details=details,
        )


class DuplicateException(HeliosException):
    """Raised when creating a duplicate entity that violates uniqueness constraints."""

    def __init__(
        self,
        message: str = "Resource already exists",
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(
            message=message,
            status_code=status.HTTP_409_CONFLICT,
            details=details,
        )


class ValidationException(HeliosException):
    """Raised when domain or schema validation fails."""

    def __init__(
        self,
        message: str = "Validation failed",
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(
            message=message,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details=details,
        )


class TenantMismatchException(HeliosException):
    """Raised when a user attempts to access or mutate resources outside their assigned tenant."""

    def __init__(
        self,
        message: str = "Tenant access forbidden",
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(
            message=message,
            status_code=status.HTTP_403_FORBIDDEN,
            details=details,
        )


class PipelineStageException(HeliosException):
    """Raised when a stage in Bronze, Silver, or Gold pipeline execution fails."""

    def __init__(
        self,
        message: str = "Pipeline stage execution failed",
        stage: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        stage_details = details.copy() if details else {}
        if stage:
            stage_details["stage"] = stage
        super().__init__(
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
            details=stage_details,
        )


class CredentialSecurityException(HeliosException):
    """Raised when credential storage, retrieval, encryption, or decryption encounters an error."""

    def __init__(
        self,
        message: str = "Credential security operation failed",
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details,
        )
