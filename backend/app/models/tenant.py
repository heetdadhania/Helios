from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import TimestampedModel


class Tenant(TimestampedModel):
    """Multi-tenant account entity representing organizations on Helios platform."""

    __tablename__ = "tenants"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    catalog_name: Mapped[str] = mapped_column(String(100), nullable=False)
    schema_name: Mapped[str] = mapped_column(String(100), default="default", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
