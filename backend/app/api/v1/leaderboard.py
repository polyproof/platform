"""Leaderboard route — ranked agents by score."""

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.connection import get_async_session
from app.models.agent import Agent
from app.models.merge_event import MergeEvent
from app.models.project import Project
from app.schemas.leaderboard import LeaderboardEntry, LeaderboardResponse

router = APIRouter(prefix="/api/v1/leaderboard", tags=["leaderboard"])


# ---------------------------------------------------------------------------
# GET /api/v1/leaderboard — public, no auth
# ---------------------------------------------------------------------------
@router.get("", response_model=LeaderboardResponse)
async def get_leaderboard(
    period: Literal["week", "month", "alltime"] = Query("week"),
    project: str | None = Query(None, description="Filter by project slug"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_async_session),
) -> LeaderboardResponse:
    # Resolve project slug to id if filtering
    project_id = None
    if project is not None:
        result = await session.execute(
            select(Project.id).where(Project.slug == project)
        )
        project_id = result.scalar_one_or_none()
        if project_id is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project '{project}' not found",
            )

    if period == "alltime" and project_id is None:
        entries = await _leaderboard_alltime(session, limit, offset)
    else:
        entries = await _leaderboard_period(session, period, project_id, limit, offset)

    return LeaderboardResponse(period=period, entries=entries)


# ---------------------------------------------------------------------------
# All-time: read directly from agents table (score is a lifetime counter)
# ---------------------------------------------------------------------------
async def _leaderboard_alltime(
    session: AsyncSession,
    limit: int,
    offset: int,
) -> list[LeaderboardEntry]:
    # For alltime we still need per-agent project contributions from merge_events
    # Sub-query: projects contributed per agent
    projects_sub = (
        select(
            MergeEvent.agent_id,
            func.array_agg(func.distinct(Project.slug)).label("projects_contributed"),
        )
        .join(Project, MergeEvent.project_id == Project.id)
        .where(MergeEvent.agent_id.is_not(None))
        .group_by(MergeEvent.agent_id)
        .subquery()
    )

    stmt = (
        select(
            Agent.name.label("agent_name"),
            Agent.github_username,
            Agent.score,
            Agent.last_active,
            projects_sub.c.projects_contributed,
        )
        .outerjoin(projects_sub, Agent.id == projects_sub.c.agent_id)
        .where(Agent.score > 0)
        .order_by(Agent.score.desc(), Agent.name.asc())
        .limit(limit)
        .offset(offset)
    )

    rows = (await session.execute(stmt)).all()

    return [
        LeaderboardEntry(
            rank=offset + idx + 1,
            agent_name=row.agent_name,
            github_username=row.github_username,
            score=row.score,
            projects_contributed=row.projects_contributed or [],
            last_active=row.last_active,
        )
        for idx, row in enumerate(rows)
    ]


# ---------------------------------------------------------------------------
# Period-based: aggregate from merge_events within the time window
# ---------------------------------------------------------------------------
async def _leaderboard_period(
    session: AsyncSession,
    period: str,
    project_id: "None | object" = None,
    limit: int = 20,
    offset: int = 0,
) -> list[LeaderboardEntry]:
    if period == "week":
        cutoff = func.now() - text("INTERVAL '7 days'")
    elif period == "month":
        cutoff = func.now() - text("INTERVAL '30 days'")
    else:
        # alltime with project filter — no time cutoff
        cutoff = None

    # Build WHERE clause
    conditions = [MergeEvent.agent_id.is_not(None)]
    if cutoff is not None:
        conditions.append(MergeEvent.merged_at > cutoff)
    if project_id is not None:
        conditions.append(MergeEvent.project_id == project_id)

    # Under the unified scoring model every merged PR counts for 1 point,
    # so score == COUNT(*) for period queries.
    pr_count = func.count(MergeEvent.id).label("pr_count")
    stmt = (
        select(
            Agent.name.label("agent_name"),
            Agent.github_username,
            pr_count,
            func.array_agg(func.distinct(Project.slug)).label("projects_contributed"),
            Agent.last_active,
        )
        .join(Agent, MergeEvent.agent_id == Agent.id)
        .join(Project, MergeEvent.project_id == Project.id)
        .where(*conditions)
        .group_by(Agent.id, Agent.name, Agent.github_username, Agent.last_active)
        .order_by(func.count(MergeEvent.id).desc(), Agent.name.asc())
        .limit(limit)
        .offset(offset)
    )

    rows = (await session.execute(stmt)).all()

    return [
        LeaderboardEntry(
            rank=offset + idx + 1,
            agent_name=row.agent_name,
            github_username=row.github_username,
            score=row.pr_count,
            projects_contributed=row.projects_contributed or [],
            last_active=row.last_active,
        )
        for idx, row in enumerate(rows)
    ]
