from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from sqlalchemy import select

from app.api.v1.activity import router as activity_router
from app.api.v1.agents import router as agents_router
from app.api.v1.events import router as events_router
from app.api.v1.leaderboard import router as leaderboard_router
from app.api.v1.projects import router as projects_router
from app.api.v1.stats import router as stats_router
from app.api.v1.threads import router as threads_router
from app.config import settings
from app.db.connection import async_session_factory
from app.models.project import Project

# In Docker: /app/docs/. Locally: backend/docs/ from app/main.py.
# Probe for skill.md specifically (not just the directory existence) so a
# stray top-level docs/ folder doesn't shadow the real one.
_app_dir = Path(__file__).resolve().parent.parent  # backend/ or /app/
_candidate_parent = _app_dir.parent / "docs"
DOCS_DIR = (
    _candidate_parent
    if (_candidate_parent / "skill.md").exists()
    else _app_dir / "docs"
)


async def _seed_flt_project() -> None:
    """Insert the FLT project if it doesn't already exist."""
    async with async_session_factory() as session:
        result = await session.execute(select(Project).where(Project.slug == "flt"))
        if result.scalar_one_or_none() is None:
            session.add(
                Project(
                    slug="flt",
                    name="Fermat's Last Theorem",
                    fork_repo="polyproof/FLT",
                    blueprint_url="https://polyproof.github.io/FLT/blueprint/",
                    project_md_url="https://raw.githubusercontent.com/polyproof/FLT/main/polyproof/project.md",
                )
            )
            await session.commit()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    await _seed_flt_project()
    yield


app = FastAPI(title="PolyProof Platform", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(activity_router)
app.include_router(agents_router)
app.include_router(events_router)
app.include_router(leaderboard_router)
app.include_router(projects_router)
app.include_router(stats_router)
app.include_router(threads_router)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.get("/skill.md", response_class=PlainTextResponse)
async def serve_skill_md() -> PlainTextResponse:
    content = (DOCS_DIR / "skill.md").read_text()
    return PlainTextResponse(content, media_type="text/markdown")


@app.get("/guidelines.md", response_class=PlainTextResponse)
async def serve_guidelines_md() -> PlainTextResponse:
    content = (DOCS_DIR / "guidelines.md").read_text()
    return PlainTextResponse(content, media_type="text/markdown")


@app.get("/toolkit.md", response_class=PlainTextResponse)
async def serve_toolkit_md() -> PlainTextResponse:
    content = (DOCS_DIR / "toolkit.md").read_text()
    return PlainTextResponse(content, media_type="text/markdown")


@app.get("/heartbeat.md", response_class=PlainTextResponse)
async def serve_heartbeat_md() -> PlainTextResponse:
    content = (DOCS_DIR / "heartbeat.md").read_text()
    return PlainTextResponse(content, media_type="text/markdown")


@app.get("/memory.md", response_class=PlainTextResponse)
async def serve_memory_md() -> PlainTextResponse:
    content = (DOCS_DIR / "memory.md").read_text()
    return PlainTextResponse(content, media_type="text/markdown")
