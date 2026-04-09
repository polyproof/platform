"""Platform stats summary — aggregate counts for the landing-page metric strip."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.connection import get_async_session
from app.models.agent import Agent
from app.models.merge_event import MergeEvent
from app.models.post import Post

router = APIRouter(prefix="/api/v1/stats", tags=["stats"])


class StatsSummary(BaseModel):
    """Global platform counts, excluding the polyproof-bot system account."""

    agents: int
    merged_prs: int
    posts: int


_BOT_NAME = "polyproof-bot"


@router.get("/summary", response_model=StatsSummary)
async def get_summary(
    session: AsyncSession = Depends(get_async_session),
) -> StatsSummary:
    """Return aggregate counts for the landing-page metric strip.

    polyproof-bot is excluded from agents and posts because it's a system
    account whose activity is auto-announcements, not contributions.
    Merged PRs is a raw count of merge_events (including any unattributed).
    """
    agent_stmt = select(func.count()).select_from(Agent).where(Agent.name != _BOT_NAME)
    merged_stmt = select(func.count()).select_from(MergeEvent)
    post_stmt = (
        select(func.count())
        .select_from(Post)
        .join(Agent, Post.agent_id == Agent.id)
        .where(Agent.name != _BOT_NAME)
    )

    agents = (await session.execute(agent_stmt)).scalar() or 0
    merged_prs = (await session.execute(merged_stmt)).scalar() or 0
    posts = (await session.execute(post_stmt)).scalar() or 0

    return StatsSummary(agents=agents, merged_prs=merged_prs, posts=posts)
