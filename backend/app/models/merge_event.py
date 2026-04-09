import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.connection import Base


class MergeEvent(Base):
    __tablename__ = "merge_events"
    __table_args__ = (
        UniqueConstraint("project_id", "pr_number"),
        Index("idx_merge_events_agent_time", "agent_id", "merged_at"),
        Index("idx_merge_events_project_time", "project_id", "merged_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    agent_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("agents.id"))
    pr_number: Mapped[int] = mapped_column(Integer, nullable=False)
    pr_type: Mapped[str] = mapped_column(String(20), nullable=False)
    pr_title: Mapped[str | None] = mapped_column(String(500))
    github_username: Mapped[str | None] = mapped_column(String(100))
    merged_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
