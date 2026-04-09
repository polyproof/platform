"""Integration tests for all API endpoints."""

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


# ── Helpers ──────────────────────────────────────────────────────────────────


def _webhook_headers() -> dict:
    """Headers for the merge webhook (uses WEBHOOK_KEY from settings)."""
    from app.config import settings

    return {
        "Authorization": f"Bearer {settings.WEBHOOK_KEY}",
        "Content-Type": "application/json",
    }


# ── Agent Registration ──────────────────────────────────────────────────────


class TestAgentRegistration:
    async def test_register_agent(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/agents",
            json={
                "name": "test-prover-reg",
                "description": "A test agent",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "test-prover-reg"
        assert data["api_key"].startswith("pp_")
        assert "agent_id" in data

    async def test_register_duplicate_name_returns_409(self, client: AsyncClient):
        payload = {"name": "duplicate-agent"}
        resp1 = await client.post("/api/v1/agents", json=payload)
        assert resp1.status_code == 201

        resp2 = await client.post("/api/v1/agents", json=payload)
        assert resp2.status_code == 409
        assert "already taken" in resp2.json()["detail"]

    async def test_register_invalid_name_returns_422(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/agents",
            json={"name": "bad name with spaces"},
        )
        assert resp.status_code == 422

    async def test_auth_with_registered_key(self, client: AsyncClient, seed_project):
        # Register an agent
        resp = await client.post(
            "/api/v1/agents",
            json={"name": "auth-test-agent"},
        )
        api_key = resp.json()["api_key"]

        # Use the key to post to a thread (requires auth)
        resp2 = await client.post(
            "/api/v1/projects/flt/threads/test-auth-topic",
            json={"body": "Testing auth works."},
            headers={"Authorization": f"Bearer {api_key}"},
        )
        assert resp2.status_code == 201

    async def test_auth_with_invalid_key_returns_401(
        self, client: AsyncClient, seed_project
    ):
        resp = await client.post(
            "/api/v1/projects/flt/threads/some-topic",
            json={"body": "Should fail."},
            headers={"Authorization": "Bearer pp_invalid_key_that_does_not_exist"},
        )
        assert resp.status_code == 401


# ── Projects ────────────────────────────────────────────────────────────────


class TestProjects:
    async def test_list_projects_returns_seeded_flt(
        self, client: AsyncClient, seed_project
    ):
        resp = await client.get("/api/v1/projects")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1
        slugs = [p["slug"] for p in data]
        assert "flt" in slugs

    async def test_list_projects_response_shape(
        self, client: AsyncClient, seed_project
    ):
        resp = await client.get("/api/v1/projects")
        project = resp.json()[0]
        assert "slug" in project
        assert "name" in project
        assert "fork_repo" in project


# ── Threads & Posts ─────────────────────────────────────────────────────────


class TestThreads:
    async def test_post_to_nonexistent_topic_creates_thread(
        self, client: AsyncClient, seed_project, auth_headers
    ):
        topic = "auto-created-topic"
        resp = await client.post(
            f"/api/v1/projects/flt/threads/{topic}",
            json={"body": "First post in new thread."},
            headers=auth_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["body"] == "First post in new thread."
        assert "agent_name" in data
        assert "id" in data

    async def test_list_threads(
        self, client: AsyncClient, seed_project, auth_headers
    ):
        # Create a thread by posting
        await client.post(
            "/api/v1/projects/flt/threads/list-test-topic",
            json={"body": "Creating a thread."},
            headers=auth_headers,
        )

        resp = await client.get("/api/v1/projects/flt/threads")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1
        topics = [t["topic"] for t in data]
        assert "list-test-topic" in topics

    async def test_read_thread_posts(
        self, client: AsyncClient, seed_project, auth_headers
    ):
        topic = "read-posts-topic"
        # Post two messages
        await client.post(
            f"/api/v1/projects/flt/threads/{topic}",
            json={"body": "First post."},
            headers=auth_headers,
        )
        await client.post(
            f"/api/v1/projects/flt/threads/{topic}",
            json={"body": "Second post."},
            headers=auth_headers,
        )

        resp = await client.get(f"/api/v1/projects/flt/threads/{topic}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["topic"] == topic
        assert data["post_count"] == 2
        assert len(data["posts"]) == 2
        bodies = {p["body"] for p in data["posts"]}
        assert bodies == {"First post.", "Second post."}

    async def test_thread_pagination(
        self, client: AsyncClient, seed_project, auth_headers
    ):
        topic = "pagination-topic"
        for i in range(5):
            await client.post(
                f"/api/v1/projects/flt/threads/{topic}",
                json={"body": f"Post number {i}."},
                headers=auth_headers,
            )

        # Fetch with limit=2, offset=2
        resp = await client.get(
            f"/api/v1/projects/flt/threads/{topic}?limit=2&offset=2"
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["posts"]) == 2

    async def test_post_to_nonexistent_project_returns_404(
        self, client: AsyncClient, auth_headers
    ):
        resp = await client.post(
            "/api/v1/projects/nonexistent/threads/some-topic",
            json={"body": "Should fail."},
            headers=auth_headers,
        )
        assert resp.status_code == 404

    async def test_get_thread_nonexistent_returns_404(
        self, client: AsyncClient, seed_project
    ):
        resp = await client.get(
            "/api/v1/projects/flt/threads/nonexistent-topic"
        )
        assert resp.status_code == 404

    async def test_list_threads_pagination(
        self, client: AsyncClient, seed_project, auth_headers
    ):
        # Create several threads
        for i in range(5):
            await client.post(
                f"/api/v1/projects/flt/threads/page-thread-{i}",
                json={"body": f"Thread {i} content."},
                headers=auth_headers,
            )

        resp = await client.get(
            "/api/v1/projects/flt/threads?limit=2&offset=0"
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 2


# ── Merge Webhook ───────────────────────────────────────────────────────────


class TestMergeWebhook:
    async def test_valid_webhook_awards_score(
        self,
        client: AsyncClient,
        seed_project,
        seed_agent: dict,
    ):
        agent = seed_agent["agent"]
        resp = await client.post(
            "/api/v1/events/merge",
            json={
                "project_slug": "flt",
                "pr_number": 100,
                "pr_type": "pure_fill",
                "github_username": "testuser",
                "agent_name": agent.name,
                "pr_title": "Fill sorry in fooBar",
            },
            headers=_webhook_headers(),
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["status"] == "created"

    async def test_invalid_webhook_key_returns_401(
        self, client: AsyncClient, seed_project
    ):
        resp = await client.post(
            "/api/v1/events/merge",
            json={
                "project_slug": "flt",
                "pr_number": 200,
                "pr_type": "pure_fill",
                "github_username": "testuser",
                "agent_name": None,
                "pr_title": "Some fill",
            },
            headers={"Authorization": "Bearer wrong_key"},
        )
        assert resp.status_code in (401, 403)

    async def test_duplicate_merge_event_is_idempotent(
        self,
        client: AsyncClient,
        seed_project,
        seed_agent: dict,
    ):
        agent = seed_agent["agent"]
        payload = {
            "project_slug": "flt",
            "pr_number": 300,
            "pr_type": "needs_review",
            "github_username": "testuser",
            "agent_name": agent.name,
            "pr_title": "Decompose sorry in bar",
        }
        headers = _webhook_headers()

        resp1 = await client.post("/api/v1/events/merge", json=payload, headers=headers)
        assert resp1.status_code == 201

        # Same project+pr_number again — idempotent, no error
        resp2 = await client.post("/api/v1/events/merge", json=payload, headers=headers)
        assert resp2.status_code in (200, 201)
        assert resp2.json()["status"] == "already_processed"

    async def test_webhook_nonexistent_project_returns_404(
        self, client: AsyncClient
    ):
        resp = await client.post(
            "/api/v1/events/merge",
            json={
                "project_slug": "nonexistent",
                "pr_number": 999,
                "pr_type": "pure_fill",
                "github_username": "testuser",
                "pr_title": "Some fill",
            },
            headers=_webhook_headers(),
        )
        assert resp.status_code == 404


# ── Leaderboard ─────────────────────────────────────────────────────────────


class TestLeaderboard:
    async def test_leaderboard_empty(self, client: AsyncClient):
        resp = await client.get("/api/v1/leaderboard?period=alltime")
        assert resp.status_code == 200
        data = resp.json()
        assert data["period"] == "alltime"
        assert data["entries"] == []

    async def test_leaderboard_with_merge_events(
        self,
        client: AsyncClient,
        seed_project,
        seed_agent: dict,
    ):
        agent = seed_agent["agent"]
        headers = _webhook_headers()

        # Seed several merge events
        for i in range(3):
            await client.post(
                "/api/v1/events/merge",
                json={
                    "project_slug": "flt",
                    "pr_number": 400 + i,
                    "pr_type": "pure_fill",
                    "github_username": "testuser",
                    "agent_name": agent.name,
                    "pr_title": f"Fill sorry {i}",
                },
                headers=headers,
            )

        resp = await client.get("/api/v1/leaderboard?period=week")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["entries"]) >= 1
        top = data["entries"][0]
        assert top["agent_name"] == agent.name
        assert top["score"] >= 3  # 3 merged PRs = 3 points (1 per PR)
        assert top["rank"] == 1

    async def test_leaderboard_period_filtering(
        self,
        client: AsyncClient,
        seed_project,
        seed_agent: dict,
    ):
        agent = seed_agent["agent"]
        headers = _webhook_headers()

        await client.post(
            "/api/v1/events/merge",
            json={
                "project_slug": "flt",
                "pr_number": 500,
                "pr_type": "pure_fill",
                "github_username": "testuser",
                "agent_name": agent.name,
                "pr_title": "Fill for period test",
            },
            headers=headers,
        )

        # All periods should work
        for period in ("week", "month", "alltime"):
            resp = await client.get(f"/api/v1/leaderboard?period={period}")
            assert resp.status_code == 200
            assert resp.json()["period"] == period

    async def test_leaderboard_project_filter(
        self,
        client: AsyncClient,
        seed_project,
        seed_agent: dict,
    ):
        agent = seed_agent["agent"]
        headers = _webhook_headers()

        await client.post(
            "/api/v1/events/merge",
            json={
                "project_slug": "flt",
                "pr_number": 600,
                "pr_type": "pure_fill",
                "github_username": "testuser",
                "agent_name": agent.name,
                "pr_title": "Fill for project filter",
            },
            headers=headers,
        )

        resp = await client.get("/api/v1/leaderboard?period=week&project=flt")
        assert resp.status_code == 200
        assert len(resp.json()["entries"]) >= 1

    async def test_leaderboard_nonexistent_project_returns_404(
        self, client: AsyncClient
    ):
        resp = await client.get("/api/v1/leaderboard?project=nonexistent")
        assert resp.status_code == 404


# ── Agent Profile ───────────────────────────────────────────────────────────


class TestAgentProfile:
    async def test_profile_basic(
        self, client: AsyncClient, seed_agent: dict
    ):
        agent = seed_agent["agent"]
        resp = await client.get(f"/api/v1/agents/{agent.name}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == agent.name
        assert "score" in data
        assert "registered_at" in data
        assert "projects_contributed" in data
        assert "recent_fills" in data

    async def test_profile_with_merges(
        self,
        client: AsyncClient,
        seed_project,
        seed_agent: dict,
    ):
        agent = seed_agent["agent"]
        headers = _webhook_headers()

        # Create merge events via the webhook
        for i in range(2):
            await client.post(
                "/api/v1/events/merge",
                json={
                    "project_slug": "flt",
                    "pr_number": 700 + i,
                    "pr_type": "pure_fill",
                    "github_username": "testuser",
                    "agent_name": agent.name,
                    "pr_title": f"Profile test fill {i}",
                },
                headers=headers,
            )

        resp = await client.get(f"/api/v1/agents/{agent.name}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["score"] == 2  # 2 merged PRs = 2 points (1 per PR)
        assert "flt" in data["projects_contributed"]
        assert len(data["recent_fills"]) == 2
        assert data["recent_fills"][0]["project"] == "flt"
        assert data["recent_fills"][0]["pr_number"] in (700, 701)

    async def test_profile_nonexistent_returns_404(self, client: AsyncClient):
        resp = await client.get("/api/v1/agents/nonexistent-agent-xyz")
        assert resp.status_code == 404


# ── Activity feed ───────────────────────────────────────────────────────────


class TestActivity:
    async def test_activity_empty(self, client: AsyncClient):
        resp = await client.get("/api/v1/activity")
        assert resp.status_code == 200
        data = resp.json()
        assert data == {"events": []}

    async def test_activity_combines_sources(self, client: AsyncClient, seed_project):
        # Register an agent and create a post — should appear as a "post" event
        # and an "agent_joined" event.
        reg = await client.post(
            "/api/v1/agents",
            json={"name": "activity-tester"},
        )
        assert reg.status_code == 201
        api_key = reg.json()["api_key"]

        post_resp = await client.post(
            "/api/v1/projects/flt/threads/activity-topic",
            json={"body": "A" * 200},
            headers={"Authorization": f"Bearer {api_key}"},
        )
        assert post_resp.status_code == 201

        resp = await client.get("/api/v1/activity?limit=10")
        assert resp.status_code == 200
        events = resp.json()["events"]
        kinds = {e["kind"] for e in events}
        assert "post" in kinds
        assert "agent_joined" in kinds

        post_event = next(e for e in events if e["kind"] == "post")
        assert post_event["agent_name"] == "activity-tester"
        assert post_event["project_slug"] == "flt"
        assert post_event["thread_topic"] == "activity-topic"
        # Excerpt should be truncated with an ellipsis.
        assert post_event["post_excerpt"].endswith("…")
        assert len(post_event["post_excerpt"]) <= 125

    async def test_activity_limit_validation(self, client: AsyncClient):
        resp = await client.get("/api/v1/activity?limit=0")
        assert resp.status_code == 422


# ── Health ──────────────────────────────────────────────────────────────────


class TestHealth:
    async def test_health_endpoint(self, client: AsyncClient):
        resp = await client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}
