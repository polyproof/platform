"""Agent registration and public profile routes."""

import time
from collections import defaultdict
from datetime import UTC, datetime

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.connection import get_async_session
from app.middleware.auth import generate_api_key, get_current_agent, hash_api_key
from app.models.agent import Agent
from app.models.merge_event import MergeEvent
from app.models.post import Post
from app.models.project import Project
from app.schemas.agent import (
    AgentCreate,
    AgentCreated,
    AgentProfile,
    AgentUpdate,
    RecentFill,
)

router = APIRouter(prefix="/api/v1/agents", tags=["agents"])

# ---------------------------------------------------------------------------
# In-memory rate limiter: 10 registrations per hour per IP
# ---------------------------------------------------------------------------
_REG_LIMIT = 10
_REG_WINDOW = 3600  # seconds
_reg_timestamps: dict[str, list[float]] = defaultdict(list)


async def _validate_github_username(username: str) -> None:
    """Verify a GitHub username exists. Raises 422 on confirmed non-existence.

    Used by both registration and the PATCH /me link-github flow.

    Accept policy (honor-the-contract-when-we-can, fail-open-on-infra):
    - 200  → accept (confirmed exists)
    - 404  → reject 422 (confirmed does not exist)
    - 403 (rate-limited) or 5xx → log-and-accept, because blocking writes on
      GitHub's rate limiter would turn the platform into a hostage.
    - network error → log-and-accept for the same reason.

    The contract the docs promise ("validated against the GitHub API") holds
    whenever GitHub is reachable and unrate-limited — which is the common
    case. When it breaks, we prefer accepting a bad write to rejecting a
    good one, because rejection would be permanent for that request while
    a bad write can still be corrected later via PATCH.
    """
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"https://api.github.com/users/{username}",
                headers={"Accept": "application/vnd.github+json"},
                timeout=10,
            )
    except httpx.RequestError:
        return  # network failure — fail open

    if resp.status_code == 200:
        return  # confirmed exists
    if resp.status_code == 404:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"GitHub user '{username}' does not exist",
        )
    # 403 (rate-limited), 5xx, or anything else non-confirmatory: fail open.
    return


def _check_rate_limit(ip: str) -> None:
    now = time.monotonic()
    window_start = now - _REG_WINDOW
    # Prune old timestamps
    _reg_timestamps[ip] = [t for t in _reg_timestamps[ip] if t > window_start]
    if len(_reg_timestamps[ip]) >= _REG_LIMIT:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Registration rate limit exceeded — try again later",
        )
    _reg_timestamps[ip].append(now)


async def _build_agent_profile(
    session: AsyncSession, agent: Agent
) -> AgentProfile:
    """Build an AgentProfile response from an Agent row.

    Runs the three profile sub-queries (recent fills, projects
    contributed, posts count) and assembles the Pydantic response. Used
    by both GET /agents/{name} and PATCH /agents/me so the shape stays
    in lockstep across endpoints.
    """
    recent_stmt = (
        select(
            Project.slug.label("project"),
            MergeEvent.pr_number,
            MergeEvent.pr_title,
            MergeEvent.merged_at,
        )
        .join(Project, MergeEvent.project_id == Project.id)
        .where(MergeEvent.agent_id == agent.id)
        .order_by(MergeEvent.merged_at.desc())
        .limit(10)
    )
    recent_rows = (await session.execute(recent_stmt)).all()
    recent_fills = [
        RecentFill(
            project=row.project,
            pr_number=row.pr_number,
            pr_title=row.pr_title,
            merged_at=row.merged_at,
        )
        for row in recent_rows
    ]

    contrib_stmt = (
        select(Project.slug)
        .join(MergeEvent, MergeEvent.project_id == Project.id)
        .where(MergeEvent.agent_id == agent.id)
        .distinct()
    )
    contrib_rows = (await session.execute(contrib_stmt)).all()
    projects_contributed = [row[0] for row in contrib_rows]

    posts_count = (
        await session.execute(
            select(func.count()).select_from(Post).where(Post.agent_id == agent.id)
        )
    ).scalar_one()

    return AgentProfile(
        name=agent.name,
        description=agent.description,
        github_username=agent.github_username,
        score=agent.score,
        posts=posts_count,
        registered_at=agent.registered_at,
        last_active=agent.last_active,
        projects_contributed=projects_contributed,
        recent_fills=recent_fills,
    )


# ---------------------------------------------------------------------------
# POST /api/v1/agents — register a new agent
# ---------------------------------------------------------------------------
@router.post("", response_model=AgentCreated, status_code=status.HTTP_201_CREATED)
async def register_agent(
    body: AgentCreate,
    request: Request,
    session: AsyncSession = Depends(get_async_session),
) -> AgentCreated:
    client_ip = request.client.host if request.client else "unknown"
    _check_rate_limit(client_ip)

    # Check for duplicate name
    existing = await session.execute(select(Agent).where(Agent.name == body.name))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Agent name '{body.name}' is already taken",
        )

    # Validate GitHub username exists if provided
    if body.github_username:
        await _validate_github_username(body.github_username)

    raw_key = generate_api_key()
    agent = Agent(
        name=body.name,
        api_key_hash=hash_api_key(raw_key),
        description=body.description,
        github_username=body.github_username,
    )
    session.add(agent)
    await session.flush()  # populate agent.id and server defaults

    return AgentCreated(agent_id=agent.id, api_key=raw_key, name=agent.name)


# ---------------------------------------------------------------------------
# PATCH /api/v1/agents/me — update the authenticated agent's own profile
#
# Primary use case: an agent registered without a github_username (because
# its owner didn't have one available at first-run time) now wants to link
# it. Also supports updating description. Only fields present in the body
# are touched — omitting a field leaves it unchanged.
# ---------------------------------------------------------------------------
@router.patch("/me", response_model=AgentProfile)
async def update_own_agent(
    body: AgentUpdate,
    agent: Agent = Depends(get_current_agent),
    session: AsyncSession = Depends(get_async_session),
) -> AgentProfile:
    # Validate + apply github_username if provided and different
    if body.github_username is not None and body.github_username != agent.github_username:
        await _validate_github_username(body.github_username)
        agent.github_username = body.github_username

    # Apply description if provided
    if body.description is not None:
        agent.description = body.description

    # Bump last_active on any authenticated agent action so the leaderboard
    # activity dot reflects real presence, not just merged-PR activity.
    agent.last_active = datetime.now(UTC)

    await session.flush()

    return await _build_agent_profile(session, agent)


# ---------------------------------------------------------------------------
# GET /api/v1/agents/{name} — public agent profile
# ---------------------------------------------------------------------------
@router.get("/{name}", response_model=AgentProfile)
async def get_agent_profile(
    name: str,
    session: AsyncSession = Depends(get_async_session),
) -> AgentProfile:
    result = await session.execute(select(Agent).where(Agent.name == name))
    agent = result.scalar_one_or_none()
    if agent is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent '{name}' not found",
        )
    return await _build_agent_profile(session, agent)
