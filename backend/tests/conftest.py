"""Test fixtures: async test DB, test client, agent creation helpers."""

# Set test environment variables BEFORE importing any app modules,
# since app.config.settings is created at import time.
import os

os.environ.setdefault("WEBHOOK_KEY", "test-webhook-secret")
os.environ.setdefault("API_ENV", "development")

import hashlib
import secrets
from collections.abc import AsyncGenerator
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.connection import Base, get_async_session
from app.main import app
from app.models.agent import Agent
from app.models.merge_event import MergeEvent
from app.models.project import Project

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://localhost:5432/polyproof_platform_test",
)


@pytest.fixture(scope="session")
def event_loop_policy():
    import asyncio

    return asyncio.DefaultEventLoopPolicy()


@pytest.fixture(scope="function")
async def engine():
    eng = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with eng.begin() as conn:
        await conn.execute(sa_text("DROP SCHEMA IF EXISTS public CASCADE"))
        await conn.execute(sa_text("CREATE SCHEMA public"))
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    async with eng.begin() as conn:
        await conn.execute(sa_text("DROP SCHEMA IF EXISTS public CASCADE"))
        await conn.execute(sa_text("CREATE SCHEMA public"))
    await eng.dispose()


@pytest.fixture
async def db_session(engine) -> AsyncGenerator[AsyncSession, None]:
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session


@pytest.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_session():
        yield db_session

    app.dependency_overrides[get_async_session] = override_get_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture
async def seed_agent(db_session: AsyncSession) -> dict:
    """Create an agent directly in the DB; return agent + raw API key."""
    raw_key = "pp_" + secrets.token_hex(32)
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    agent = Agent(
        id=uuid4(),
        name="test-agent-" + secrets.token_hex(4),
        api_key_hash=key_hash,
        description="A test agent",
    )
    db_session.add(agent)
    await db_session.flush()
    return {"agent": agent, "api_key": raw_key}


@pytest.fixture
def auth_headers(seed_agent: dict) -> dict:
    return {"Authorization": f"Bearer {seed_agent['api_key']}"}


@pytest.fixture
async def seed_project(db_session: AsyncSession) -> Project:
    """Insert FLT project for tests that need it."""
    project = Project(
        id=uuid4(),
        slug="flt",
        name="Fermat's Last Theorem",
        fork_repo="polyproof/FLT",
        blueprint_url="https://polyproof.github.io/FLT/blueprint/",
        project_md_url="https://raw.githubusercontent.com/polyproof/FLT/main/polyproof/project.md",
    )
    db_session.add(project)
    await db_session.flush()
    return project


@pytest.fixture
async def seed_merge_event(
    db_session: AsyncSession, seed_agent: dict, seed_project: Project
) -> MergeEvent:
    """Insert a merge event for the seed agent on the seed project."""
    agent = seed_agent["agent"]
    event = MergeEvent(
        id=uuid4(),
        project_id=seed_project.id,
        agent_id=agent.id,
        pr_number=1,
        pr_type="pure_fill",
        pr_title="Fill sorry in galoisRepresentation",
        github_username="testuser",
    )
    db_session.add(event)
    await db_session.flush()

    # Update agent counter to match (simulating what the endpoint does)
    agent.score = 1
    await db_session.flush()

    return event
