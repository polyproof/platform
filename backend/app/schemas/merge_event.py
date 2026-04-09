"""Pydantic schemas for the merge event webhook payload."""

from pydantic import BaseModel, Field


class MergeEventCreate(BaseModel):
    """Request body for POST /api/v1/events/merge (from GitHub Action)."""

    project_slug: str = Field(min_length=1)
    pr_number: int = Field(gt=0)
    pr_type: str = Field(pattern=r"^(pure_fill|needs_review)$")
    github_username: str
    agent_name: str | None = None
    pr_title: str
