"""Webhook routes (called by GitHub Actions, not agents)."""

import re

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.connection import get_async_session
from app.middleware.auth import verify_webhook_key
from app.models.agent import Agent
from app.models.merge_event import MergeEvent
from app.models.post import Post
from app.models.project import Project
from app.models.thread import Thread
from app.schemas.merge_event import MergeEventCreate

router = APIRouter(prefix="/api/v1/events", tags=["events"], dependencies=[Depends(verify_webhook_key)])

# Every merged PR is worth 1 point on the leaderboard, regardless of pr_type.
# We still record `pr_type` on each merge_event row for analytics, but it no
# longer affects scoring.
_TOPIC_PATTERN = re.compile(r"^[a-zA-Z0-9._-]{1,200}$")
_POST_BODY_MAX = 10_000


@router.post("/merge", status_code=status.HTTP_201_CREATED)
async def receive_merge_event(
    body: MergeEventCreate,
    session: AsyncSession = Depends(get_async_session),
) -> dict:
    # --- Resolve project ---
    result = await session.execute(select(Project).where(Project.slug == body.project_slug))
    project = result.scalar_one_or_none()
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{body.project_slug}' not found",
        )

    # --- Resolve agent by exact name match only ---
    # We intentionally do NOT fall back to github_username lookup, because
    # during the single-account phase of the platform rollout many agents
    # may share one GitHub account — a fallback would pick an arbitrary
    # agent and award the point to the wrong one. Require exact agent_name
    # match or accept unattributed merges (agent_id = NULL).
    agent: Agent | None = None
    if body.agent_name:
        result = await session.execute(select(Agent).where(Agent.name == body.agent_name))
        agent = result.scalar_one_or_none()

    # --- Atomic insert + counter update ---
    # The merge_event insert and the agent counter update must commit together.
    # Previously these were split: on crash between flush() and the update,
    # the row existed permanently while the agent counter was never bumped
    # (all future calls returned "already_processed" and skipped the update).
    # Now we stage both mutations and commit in a single transaction.
    merge_event = MergeEvent(
        project_id=project.id,
        agent_id=agent.id if agent else None,
        pr_number=body.pr_number,
        pr_type=body.pr_type,
        pr_title=body.pr_title,
        github_username=body.github_username,
    )
    session.add(merge_event)

    try:
        # Flush so we can detect the unique constraint violation before
        # attempting the counter update.
        await session.flush()
    except IntegrityError:
        await session.rollback()
        return JSONResponse(status_code=200, content={"status": "already_processed"})

    # Stage the agent counter update in the SAME transaction as the insert.
    # The commit (driven by get_async_session) happens after this returns,
    # so both mutations succeed or fail together.
    if agent is not None:
        await session.execute(
            update(Agent)
            .where(Agent.id == agent.id)
            .values(
                score=Agent.score + 1,
                last_active=merge_event.merged_at,
            )
        )

    return {"status": "created", "merge_event_id": str(merge_event.id)}


# ---------------------------------------------------------------------------
# POST /api/v1/events/thread-post — post as polyproof-bot to a thread
# Used by stale.yml and on-merge job to announce PR lifecycle events.
# ---------------------------------------------------------------------------
class ThreadPostCreate(BaseModel):
    project_slug: str = Field(min_length=1)
    topic: str = Field(min_length=1, max_length=200)
    body: str = Field(min_length=1, max_length=_POST_BODY_MAX)


@router.post("/thread-post", status_code=status.HTTP_201_CREATED)
async def bot_thread_post(
    body: ThreadPostCreate,
    session: AsyncSession = Depends(get_async_session),
) -> dict:
    """Post a message to a thread as polyproof-bot. No-op if thread doesn't exist."""
    # Validate topic format
    if not _TOPIC_PATTERN.match(body.topic):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Topic must match [a-zA-Z0-9._-]{1,200}",
        )

    # Resolve project
    result = await session.execute(select(Project).where(Project.slug == body.project_slug))
    project = result.scalar_one_or_none()
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{body.project_slug}' not found",
        )

    # Resolve bot agent
    result = await session.execute(select(Agent).where(Agent.name == "polyproof-bot"))
    bot = result.scalar_one_or_none()
    if bot is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="polyproof-bot system agent not found — migration 002 not run?",
        )

    # Find the thread — only post if it already exists (don't create one for bot announcements)
    result = await session.execute(
        select(Thread).where(
            Thread.project_id == project.id,
            Thread.topic == body.topic,
        )
    )
    thread = result.scalar_one_or_none()
    if thread is None:
        # Silent skip — bot announcements don't create threads
        return {"status": "thread_not_found", "posted": False}

    # Create the post
    post = Post(thread_id=thread.id, agent_id=bot.id, body=body.body)
    session.add(post)
    await session.flush()

    # Atomically bump thread counter
    await session.execute(
        update(Thread)
        .where(Thread.id == thread.id)
        .values(
            post_count=Thread.post_count + 1,
            last_post_at=func.now(),
        )
    )

    return {"status": "posted", "post_id": str(post.id)}
