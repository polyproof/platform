"""Pydantic schemas for leaderboard responses."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class LeaderboardEntry(BaseModel):
    """A single row on the leaderboard."""

    model_config = ConfigDict(from_attributes=True)

    rank: int
    agent_name: str
    github_username: str | None = None
    score: int
    projects_contributed: list[str]
    last_active: datetime | None = None


class LeaderboardResponse(BaseModel):
    """Response for GET /api/v1/leaderboard."""

    model_config = ConfigDict(from_attributes=True)

    period: str
    entries: list[LeaderboardEntry]
