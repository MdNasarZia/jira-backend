import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import IssueStatus


class IssueStatusHistory(Base):
    __tablename__ = "issue_status_history"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    issue_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("issues.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    changed_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    from_status: Mapped[IssueStatus | None] = mapped_column(
        Enum(IssueStatus, name="issue_status_enum", create_type=False),
        nullable=True,
    )
    to_status: Mapped[IssueStatus] = mapped_column(
        Enum(IssueStatus, name="issue_status_enum", create_type=False),
        nullable=False,
    )
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    issue: Mapped["Issue"] = relationship("Issue", back_populates="status_history", lazy="raise")
