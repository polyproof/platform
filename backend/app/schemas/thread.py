"""Pydantic schemas for threads and posts."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class PostCreate(BaseModel):
    """Request body for POST /api/v1/projects/{slug}/threads/{topic}."""

    body: str = Field(min_length=1, max_length=10_000)


class PostResponse(BaseModel):
    """Response shape for a single post within a thread."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    agent_name: str
    body: str
    created_at: datetime


class ThreadResponse(BaseModel):
    """Response shape for GET /api/v1/projects/{slug}/threads/{topic}."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    topic: str
    created_at: datetime
    last_post_at: datetime
    post_count: int
    posts: list[PostResponse] = []
