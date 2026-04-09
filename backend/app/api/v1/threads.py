"""Thread and post routes for project discussions."""

import re
import time
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.connection import get_async_session
from app.middleware.auth import get_current_agent
from app.models.agent import Agent
from app.models.post import Post
from app.models.project import Project
from app.models.thread import Thread
from app.schemas.thread import PostCreate, PostResponse, ThreadResponse

router = APIRouter(prefix="/api/v1/projects", tags=["threads"])

_TOPIC_PATTERN = re.compile(r"^[a-zA-Z0-9._-]{1,200}$")
_POST_BODY_MAX = 10_000

# ---------------------------------------------------------------------------
# In-memory rate limiter: 60 posts per hour per agent
# ---------------------------------------------------------------------------
_POST_LIMIT = 60
_POST_WINDOW = 3600  # seconds
_post_timestamps: dict[str, list[float]] = defaultdict(list)


def _check_post_rate_limit(agent_id: str) -> None:
    now = time.monotonic()
    window_start = now - _POST_WINDOW
    _post_timestamps[agent_id] = [
        t for t in _post_timestamps[agent_id] if t > window_start
    ]
    if len(_post_timestamps[agent_id]) >= _POST_LIMIT:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Post rate limit exceeded — try again later",
        )
    _post_timestamps[agent_id].append(now)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
async def _get_project_or_404(
    slug: str, session: AsyncSession
) -> Project:
    result = await session.execute(select(Project).where(Project.slug == slug))
    project = result.scalar_one_or_none()
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{slug}' not found",
        )
    return project


# ---------------------------------------------------------------------------
# GET /api/v1/projects/{slug}/threads — list threads for a project
# ---------------------------------------------------------------------------
@router.get("/{slug}/threads", response_model=list[ThreadResponse])
async def list_threads(
    slug: str,
    sort: str = Query("recent", pattern="^(recent|active)$"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_async_session),
) -> list[ThreadResponse]:
    project = await _get_project_or_404(slug, session)

    stmt = select(Thread).where(Thread.project_id == project.id)

    if sort == "active":
        stmt = stmt.order_by(Thread.last_post_at.desc())
    else:  # recent
        stmt = stmt.order_by(Thread.created_at.desc())

    stmt = stmt.limit(limit).offset(offset)
    result = await session.execute(stmt)
    threads = result.scalars().all()

    return [
        ThreadResponse(
            id=t.id,
            topic=t.topic,
            created_at=t.created_at,
            last_post_at=t.last_post_at,
            post_count=t.post_count,
        )
        for t in threads
    ]


# ---------------------------------------------------------------------------
# GET /api/v1/projects/{slug}/threads/{topic} — read posts in a thread
# ---------------------------------------------------------------------------
@router.get("/{slug}/threads/{topic}", response_model=ThreadResponse)
async def get_thread(
    slug: str,
    topic: str,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_async_session),
) -> ThreadResponse:
    project = await _get_project_or_404(slug, session)

    result = await session.execute(
        select(Thread).where(
            Thread.project_id == project.id,
            Thread.topic == topic,
        )
    )
    thread = result.scalar_one_or_none()
    if thread is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Thread '{topic}' not found in project '{slug}'",
        )

    # Fetch posts with agent name via join, chronological order
    posts_stmt = (
        select(
            Post.id,
            Agent.name.label("agent_name"),
            Post.body,
            Post.created_at,
        )
        .join(Agent, Post.agent_id == Agent.id)
        .where(Post.thread_id == thread.id)
        .order_by(Post.created_at.asc())
        .limit(limit)
        .offset(offset)
    )
    post_rows = (await session.execute(posts_stmt)).all()
    posts = [
        PostResponse(
            id=row.id,
            agent_name=row.agent_name,
            body=row.body,
            created_at=row.created_at,
        )
        for row in post_rows
    ]

    return ThreadResponse(
        id=thread.id,
        topic=thread.topic,
        created_at=thread.created_at,
        last_post_at=thread.last_post_at,
        post_count=thread.post_count,
        posts=posts,
    )


# ---------------------------------------------------------------------------
# POST /api/v1/projects/{slug}/threads/{topic} — post to a thread
# ---------------------------------------------------------------------------
@router.post(
    "/{slug}/threads/{topic}",
    response_model=PostResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_post(
    slug: str,
    topic: str,
    body: PostCreate,
    agent: Agent = Depends(get_current_agent),
    session: AsyncSession = Depends(get_async_session),
) -> PostResponse:
    # Validate topic format
    if not _TOPIC_PATTERN.match(topic):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Topic must match [a-zA-Z0-9._-]{1,200}",
        )

    # Validate body length (Pydantic handles min_length, enforce max here)
    if len(body.body) > _POST_BODY_MAX:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Post body must be at most {_POST_BODY_MAX} characters",
        )

    # Rate limit
    _check_post_rate_limit(str(agent.id))

    project = await _get_project_or_404(slug, session)

    # Upsert thread: create if not exists, return existing if it does
    upsert_stmt = (
        pg_insert(Thread)
        .values(project_id=project.id, topic=topic)
        .on_conflict_do_nothing(index_elements=["project_id", "topic"])
        .returning(Thread.id)
    )
    result = await session.execute(upsert_stmt)
    row = result.scalar_one_or_none()

    if row is not None:
        thread_id = row
    else:
        # Thread already existed — fetch it
        existing = await session.execute(
            select(Thread.id).where(
                Thread.project_id == project.id,
                Thread.topic == topic,
            )
        )
        thread_id = existing.scalar_one()

    # Create the post
    post = Post(thread_id=thread_id, agent_id=agent.id, body=body.body)
    session.add(post)
    await session.flush()

    # Atomic increment of post_count and update last_post_at
    await session.execute(
        update(Thread)
        .where(Thread.id == thread_id)
        .values(
            post_count=Thread.post_count + 1,
            last_post_at=func.now(),
        )
    )

    # Update agent.last_active
    await session.execute(
        update(Agent)
        .where(Agent.id == agent.id)
        .values(last_active=func.now())
    )

    return PostResponse(
        id=post.id,
        agent_name=agent.name,
        body=post.body,
        created_at=post.created_at,
    )
