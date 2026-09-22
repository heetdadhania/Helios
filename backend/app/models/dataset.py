from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import TimestampedModel


class DatasetMetadata(TimestampedModel):
    """Metadata tracking Delta Lake tables and schemas per tenant in Unity Catalog."""

    __tablename__ = "dataset_metadata"

    table_name: Mapped[str] = mapped_column(String(150), nullable=False)
    catalog: Mapped[str] = mapped_column(String(100), nullable=False)
    schema_name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    inferred_schema_json: Mapped[str] = mapped_column(Text, nullable=True)
    tenant_id: Mapped[int] = mapped_column(Integer, ForeignKey("tenants.id"), index=True, nullable=False)
