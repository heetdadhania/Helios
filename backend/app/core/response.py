"""
Helios Platform - Standard API Response Wrapper
"""

from typing import Any, Generic, Optional, TypeVar
from pydantic import BaseModel, Field

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    """Standard API response wrapper ensuring consistent JSON contract across endpoints."""

    success: bool = Field(default=True, description="Indicates if the operation succeeded")
    data: Optional[T] = Field(default=None, description="The response data payload")
    message: str = Field(
        default="Operation completed successfully",
        description="Informational or status message",
    )


def success_response(
    data: Optional[Any] = None,
    message: str = "Operation completed successfully",
) -> ApiResponse[Any]:
    """Helper to construct a successful ApiResponse wrapper."""
    return ApiResponse[Any](success=True, data=data, message=message)


def error_response(
    message: str = "An error occurred",
    data: Optional[Any] = None,
) -> ApiResponse[Any]:
    """Helper to construct an error ApiResponse wrapper."""
    return ApiResponse[Any](success=False, data=data, message=message)
