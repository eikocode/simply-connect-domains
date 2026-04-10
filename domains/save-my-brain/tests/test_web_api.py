"""Integration tests for the web API (scripts/web_api.py).

Uses FastAPI's TestClient to hit endpoints without spinning up a real server.
"""

import importlib.util
import io
import json
import sys
from pathlib import Path

import pytest


@pytest.fixture
def web_api_app(deploy_env: Path):
    """Load the web_api module with a temp deployment root."""
    # Point at the deployment's web_api.py
    web_api_path = Path("/Users/eiko/Dev/deployments/save-my-brain/scripts/web_api.py")
    if not web_api_path.exists():
        pytest.skip("web_api.py not found (deployment missing)")

    # Clear cached module
    for mod_name in list(sys.modules):
        if mod_name == "web_api" or mod_name.startswith("scripts.web_api"):
            del sys.modules[mod_name]

    # The web_api module uses DEPLOY_ROOT = Path(__file__).resolve().parent.parent
    # so we can't easily retarget it. Instead, use the real deployment.
    spec = importlib.util.spec_from_file_location("web_api", web_api_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules["web_api"] = module
    spec.loader.exec_module(module)

    # Reset cached context manager
    module._cm = None
    return module.app


@pytest.fixture
def client(web_api_app):
    from fastapi.testclient import TestClient
    return TestClient(web_api_app)


# ---------------------------------------------------------------------------
# Health endpoint
# ---------------------------------------------------------------------------

class TestHealth:
    def test_health_ok(self, client):
        resp = client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["service"] == "save-my-brain-web-api"

    def test_health_lists_tools(self, client):
        resp = client.get("/api/health")
        data = resp.json()
        assert "tools" in data
        tool_names = data["tools"]
        # All expected tools should be present
        assert "list_family_members" in tool_names
        assert "add_family_member" in tool_names
        assert "rename_family_member" in tool_names
        assert "search_documents" in tool_names

    def test_health_lists_extension(self, client):
        resp = client.get("/api/health")
        assert "save-my-brain" in resp.json()["extensions"]


# ---------------------------------------------------------------------------
# Context endpoints
# ---------------------------------------------------------------------------

class TestContext:
    def test_get_all_context(self, client):
        resp = client.get("/api/context")
        assert resp.status_code == 200
        data = resp.json()
        # Should have all profile categories
        expected = {"documents", "finances", "insurance", "calendar", "family", "tasks"}
        assert expected.issubset(set(data.keys()))

    def test_get_specific_category(self, client):
        resp = client.get("/api/context/family")
        assert resp.status_code == 200
        data = resp.json()
        assert data["category"] == "family"
        assert "content" in data

    def test_get_unknown_category_404(self, client):
        resp = client.get("/api/context/nonexistent")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Tool endpoints
# ---------------------------------------------------------------------------

class TestTools:
    def test_list_tools(self, client):
        resp = client.get("/api/tools")
        assert resp.status_code == 200
        data = resp.json()
        assert "tools" in data
        assert len(data["tools"]) >= 8  # At least all family + doc tools

    def test_call_list_family_members(self, client):
        resp = client.post("/api/tool/list_family_members", json={})
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert "primary_user" in data["result"]

    def test_call_unknown_tool_404(self, client):
        resp = client.post("/api/tool/nonexistent", json={})
        assert resp.status_code == 404

    def test_call_list_tasks(self, client):
        resp = client.post("/api/tool/list_tasks", json={"status": "pending"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert "tasks" in data["result"] or "count" in data["result"]

    def test_call_with_no_body(self, client):
        """Empty body should work for tools with no required args."""
        resp = client.post("/api/tool/list_family_members", json={})
        assert resp.status_code == 200
