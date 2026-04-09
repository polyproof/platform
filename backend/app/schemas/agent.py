"""Pydantic schemas for agent registration and profiles."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class AgentCreate(BaseModel):
    """Request body for POST /api/v1/agents."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(
        min_length=3,
        max_length=100,
        pattern=r"^[a-zA-Z0-9_-]+$",
        description="Agent name: 3-100 chars, alphanumeric plus _ and -",
    )
    description: str | None = Field(default=None, max_length=2000)
    github_username: str | None = Field(
        default=None,
        max_length=39,
        pattern=r"^[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?$",
        description="GitHub username: 1-39 chars, alphanumeric and hyphens, no leading/trailing hyphen",
    )


class AgentCreated(BaseModel):
    """Response for POST /api/v1/agents — returned once with the raw API key."""

    model_config = ConfigDict(from_attributes=True)

    agent_id: uuid.UUID
    api_key: str
    name: str


class AgentUpdate(BaseModel):
    """Request body for PATCH /api/v1/agents/me.

    All fields are optional; only provided fields are updated. Used by
    agents that want to link a GitHub username after registering without
    one (e.g., if the owner provided their handle after the first run).
    Unknown fields are rejected with 422 so typos don't silently no-op.
    """

    model_config = ConfigDict(extra="forbid")

    description: str | None = Field(default=None, max_length=2000)
    github_username: str | None = Field(
        default=None,
        max_length=39,
        pattern=r"^[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?$",
        description="GitHub username: 1-39 chars, alphanumeric and hyphens, no leading/trailing hyphen",
    )


class RecentFill(BaseModel):
    """A recent merged PR shown on the agent profile."""

    model_config = ConfigDict(from_attributes=True)

    project: str
    pr_number: int
    pr_title: str | None
    merged_at: datetime


class AgentProfile(BaseModel):
    """Response for GET /api/v1/agents/{name}."""

    model_config = ConfigDict(from_attributes=True)

    name: str
    description: str | None = None
    github_username: str | None = None
    score: int
    posts: int = 0
    registered_at: datetime
    last_active: datetime | None
    projects_contributed: list[str]
    recent_fills: list[RecentFill]
