"""Project listing endpoint."""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.connection import get_async_session
from app.models.project import Project
from app.schemas.project import ProjectResponse

router = APIRouter(prefix="/api/v1/projects", tags=["projects"])


@router.get("", response_model=list[ProjectResponse])
async def list_projects(
    session: AsyncSession = Depends(get_async_session),
) -> list[Project]:
    """List all projects. Public, no auth required."""
    result = await session.execute(select(Project).order_by(Project.name))
    return list(result.scalars().all())
