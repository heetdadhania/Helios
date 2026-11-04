"""Common schemas for Helios API responses."""

from typing import Generic, List, TypeVar
from pydantic import BaseModel, Field

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """Standard pagination wrapper for list endpoints."""

    items: List[T] = Field(default_factory=list, description="Items for current page")
    total: int = Field(0, ge=0, description="Total matching items before pagination")
    page: int = Field(1, ge=1, description="Current page number (1-based)")
    page_size: int = Field(20, ge=1, le=100, description="Items per page")

