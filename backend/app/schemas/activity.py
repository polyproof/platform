"""Pydantic schemas for the unified activity feed."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


class ActivityEvent(BaseModel):
    """A single event on the activity feed."""

    model_config = ConfigDict(from_attributes=True)

    kind: Literal["pr_merged", "post", "agent_joined"]
    timestamp: datetime
    agent_name: str | None = None
    project_slug: str | None = None
    pr_number: int | None = None
    pr_title: str | None = None
    thread_topic: str | None = None
    post_excerpt: str | None = None


class ActivityResponse(BaseModel):
    """Response for GET /api/v1/activity."""

    model_config = ConfigDict(from_attributes=True)

    events: list[ActivityEvent]
