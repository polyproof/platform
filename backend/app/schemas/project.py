"""Pydantic schemas for project responses."""

from pydantic import BaseModel, ConfigDict


class ProjectResponse(BaseModel):
    """Response shape for GET /api/v1/projects."""

    model_config = ConfigDict(from_attributes=True)

    slug: str
    name: str
    fork_repo: str
    blueprint_url: str | None
    project_md_url: str | None
