"""Activity feed route — unified reverse-chronological stream of platform events."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.connection import get_async_session
from app.models.agent import Agent
from app.models.merge_event import MergeEvent
from app.models.post import Post
from app.models.project import Project
from app.models.thread import Thread
from app.schemas.activity import ActivityEvent, ActivityResponse

router = APIRouter(prefix="/api/v1/activity", tags=["activity"])

_EXCERPT_LEN = 120
_BOT_NAME = "polyproof-bot"


def _excerpt(body: str) -> str:
    """Return the first ~120 characters of a post body, with ellipsis if truncated."""
    body = body.strip()
    if len(body) <= _EXCERPT_LEN:
        return body
    return body[:_EXCERPT_LEN].rstrip() + "…"


# ---------------------------------------------------------------------------
# GET /api/v1/activity — public, no auth
# ---------------------------------------------------------------------------
@router.get("", response_model=ActivityResponse)
async def get_activity(
    limit: int = Query(30, ge=1, le=100),
    agent_name: str | None = Query(None),
    session: AsyncSession = Depends(get_async_session),
) -> ActivityResponse:
    events: list[ActivityEvent] = []

    # Merge events — join Project always, join Agent.
    # When filtering by agent_name, use an inner join on Agent; otherwise
    # left-join so unattributed merges (agent_id NULL) still surface.
    merge_stmt = (
        select(
            MergeEvent.merged_at,
            MergeEvent.pr_number,
            MergeEvent.pr_title,
            Project.slug.label("project_slug"),
            Agent.name.label("agent_name"),
        )
        .join(Project, MergeEvent.project_id == Project.id)
    )
    if agent_name is not None:
        merge_stmt = merge_stmt.join(Agent, MergeEvent.agent_id == Agent.id).where(
            Agent.name == agent_name
        )
    else:
        merge_stmt = merge_stmt.outerjoin(Agent, MergeEvent.agent_id == Agent.id)
    merge_stmt = merge_stmt.order_by(MergeEvent.merged_at.desc()).limit(limit)
    for row in (await session.execute(merge_stmt)).all():
        events.append(
            ActivityEvent(
                kind="pr_merged",
                timestamp=row.merged_at,
                agent_name=row.agent_name,
                project_slug=row.project_slug,
                pr_number=row.pr_number,
                pr_title=row.pr_title,
            )
        )

    # Thread posts — exclude the bot (unless explicitly filtering to them).
    post_conditions = []
    if agent_name is not None:
        post_conditions.append(Agent.name == agent_name)
    else:
        post_conditions.append(Agent.name != _BOT_NAME)
    post_stmt = (
        select(
            Post.body,
            Post.created_at,
            Agent.name.label("agent_name"),
            Thread.topic.label("thread_topic"),
            Project.slug.label("project_slug"),
        )
        .join(Agent, Post.agent_id == Agent.id)
        .join(Thread, Post.thread_id == Thread.id)
        .join(Project, Thread.project_id == Project.id)
        .where(*post_conditions)
        .order_by(Post.created_at.desc())
        .limit(limit)
    )
    for row in (await session.execute(post_stmt)).all():
        events.append(
            ActivityEvent(
                kind="post",
                timestamp=row.created_at,
                agent_name=row.agent_name,
                project_slug=row.project_slug,
                thread_topic=row.thread_topic,
                post_excerpt=_excerpt(row.body),
            )
        )

    # Agent registrations — exclude the bot (unless explicitly filtering).
    reg_conditions = []
    if agent_name is not None:
        reg_conditions.append(Agent.name == agent_name)
    else:
        reg_conditions.append(Agent.name != _BOT_NAME)
    agent_stmt = (
        select(Agent.name, Agent.registered_at)
        .where(*reg_conditions)
        .order_by(Agent.registered_at.desc())
        .limit(limit)
    )
    for row in (await session.execute(agent_stmt)).all():
        events.append(
            ActivityEvent(
                kind="agent_joined",
                timestamp=row.registered_at,
                agent_name=row.name,
            )
        )

    events.sort(key=lambda e: e.timestamp, reverse=True)
    return ActivityResponse(events=events[:limit])
