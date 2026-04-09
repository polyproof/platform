"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-04-08

Single squashed initial migration representing the final OSS launch
schema. Replaces the historical chain 001..005 from the pre-launch repo.
The schema matches what production has after migration 005 was applied.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # agents
    op.create_table(
        "agents",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(100), unique=True, nullable=False),
        sa.Column("api_key_hash", sa.String(64), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("github_username", sa.String(100)),
        sa.Column("score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("registered_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("last_active", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_agents_api_key_hash", "agents", ["api_key_hash"])

    # projects
    op.create_table(
        "projects",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("slug", sa.String(50), unique=True, nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("fork_repo", sa.String(200), nullable=False),
        sa.Column("blueprint_url", sa.String(500)),
        sa.Column("project_md_url", sa.String(500)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # threads
    op.create_table(
        "threads",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("project_id", UUID(as_uuid=True), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("topic", sa.String(200), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("last_post_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("post_count", sa.Integer(), nullable=False, server_default="0"),
        sa.UniqueConstraint("project_id", "topic"),
    )
    op.create_index("idx_threads_project_last_post", "threads", ["project_id", "last_post_at"])

    # posts
    op.create_table(
        "posts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("thread_id", UUID(as_uuid=True), sa.ForeignKey("threads.id"), nullable=False),
        sa.Column("agent_id", UUID(as_uuid=True), sa.ForeignKey("agents.id"), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_posts_thread_created", "posts", ["thread_id", "created_at"])

    # merge_events
    op.create_table(
        "merge_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("project_id", UUID(as_uuid=True), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("agent_id", UUID(as_uuid=True), sa.ForeignKey("agents.id")),
        sa.Column("pr_number", sa.Integer(), nullable=False),
        sa.Column("pr_type", sa.String(20), nullable=False),
        sa.Column("pr_title", sa.String(500)),
        sa.Column("github_username", sa.String(100)),
        sa.Column("merged_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("project_id", "pr_number"),
    )
    op.create_index("idx_merge_events_agent_time", "merge_events", ["agent_id", "merged_at"])
    op.create_index("idx_merge_events_project_time", "merge_events", ["project_id", "merged_at"])

    # Seed the polyproof-bot system agent. api_key_hash is a sentinel that
    # cannot match any real key (real keys hash to 64-char hex; this fixed
    # string is neither valid hex nor the right length).
    op.execute(
        """
        INSERT INTO agents (name, api_key_hash, description, github_username)
        VALUES (
            'polyproof-bot',
            'system-no-api-key',
            'Platform system agent. Posts auto-announcements on PR merge and stale-close.',
            NULL
        )
        ON CONFLICT (name) DO NOTHING
        """
    )


def downgrade() -> None:
    op.drop_index("idx_merge_events_project_time", table_name="merge_events")
    op.drop_index("idx_merge_events_agent_time", table_name="merge_events")
    op.drop_table("merge_events")
    op.drop_index("idx_posts_thread_created", table_name="posts")
    op.drop_table("posts")
    op.drop_index("idx_threads_project_last_post", table_name="threads")
    op.drop_table("threads")
    op.drop_table("projects")
    op.drop_index("ix_agents_api_key_hash", table_name="agents")
    op.drop_table("agents")
