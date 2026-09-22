from datetime import datetime, timezone
from sqlalchemy import DateTime, Integer
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class TimestampedModel(Base):
    """Abstract base model with primary key and automatic timestamps."""

    __abstract__ = True

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
