import uuid

from sqlalchemy import CheckConstraint, Enum, ForeignKey, Index, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.models.enums import IssuePriority, IssueStatus, IssueType


class Issue(Base, TimestampMixin):
    __tablename__ = "issues"
    __table_args__ = (
        CheckConstraint(
            "(type = 'story') OR (epic_id IS NULL)",
            name="chk_issues_epic_only_for_story",
        ),
        CheckConstraint(
            "(type != 'story') OR (parent_id IS NULL)",
            name="chk_issues_parent_not_for_story",
        ),
        CheckConstraint(
            "story_points IS NULL OR (story_points >= 0 AND story_points <= 100)",
            name="chk_issues_story_points_range",
        ),
        Index("idx_issues_project_backlog_rank", "project_id", "backlog_rank"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    epic_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("epics.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    sprint_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sprints.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("issues.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    type: Mapped[IssueType] = mapped_column(
        Enum(IssueType, name="issue_type_enum"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[IssueStatus] = mapped_column(
        Enum(IssueStatus, name="issue_status_enum"),
        nullable=False,
        default=IssueStatus.backlog,
    )
    priority: Mapped[IssuePriority] = mapped_column(
        Enum(IssuePriority, name="issue_priority_enum"),
        nullable=False,
        default=IssuePriority.medium,
    )
    story_points: Mapped[int | None] = mapped_column(Integer, nullable=True)
    assignee_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    reporter_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    backlog_rank: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    project: Mapped["Project"] = relationship("Project", back_populates="issues", lazy="raise")
    epic: Mapped["Epic | None"] = relationship("Epic", back_populates="issues", lazy="raise")
    sprint: Mapped["Sprint | None"] = relationship("Sprint", back_populates="issues", lazy="raise")
    parent: Mapped["Issue | None"] = relationship(
        "Issue",
        remote_side="Issue.id",
        lazy="raise",
    )
    comments: Mapped[list["Comment"]] = relationship(
        "Comment", back_populates="issue", lazy="raise", cascade="all, delete-orphan"
    )
    status_history: Mapped[list["IssueStatusHistory"]] = relationship(
        "IssueStatusHistory",
        back_populates="issue",
        lazy="raise",
        cascade="all, delete-orphan",
    )
