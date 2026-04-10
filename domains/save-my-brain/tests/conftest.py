"""Shared fixtures for save-my-brain extension tests."""

import importlib.util
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def deploy_root(tmp_path: Path) -> Path:
    """Create a minimal deployment directory with profile + context files."""
    root = tmp_path / "deploy"
    root.mkdir()

    # AGENT.md
    (root / "AGENT.md").write_text("# Save My Brain\n")

    # profile.json
    (root / "profile.json").write_text(json.dumps({
        "name": "Save My Brain",
        "context_files": ["documents", "finances", "insurance", "calendar", "family", "tasks"],
        "category_map": {
            "documents": "documents.md",
            "finances": "finances.md",
            "insurance": "insurance.md",
            "calendar": "calendar.md",
            "family": "family.md",
            "tasks": "tasks.md",
            "general": "documents.md",
        },
        "extensions": ["save-my-brain"],
        "roles": {"operator": {"context_filter": ["documents", "finances", "insurance", "calendar", "family", "tasks"]}},
    }))

    # Empty context files
    ctx = root / "context"
    ctx.mkdir()
    for name in ("documents", "finances", "insurance", "calendar", "family", "tasks"):
        (ctx / f"{name}.md").write_text(f"# {name.title()}\n")

    # Staging + data dirs
    (root / "staging").mkdir()
    (root / "data").mkdir()
    (root / "data" / "onboarding").mkdir()

    return root


@pytest.fixture
def tools_module(deploy_root: Path):
    """Load the save-my-brain extension tools module in isolation."""
    # Clear any cached modules
    for mod_name in list(sys.modules):
        if mod_name.startswith("_sc_smb") or mod_name.startswith("save_my_brain"):
            del sys.modules[mod_name]

    src_ext = Path(__file__).parent.parent / "extension"
    ext_tools = src_ext / "tools.py"

    # Load as standalone module
    spec = importlib.util.spec_from_file_location("_sc_smb_tools", ext_tools)
    module = importlib.util.module_from_spec(spec)
    sys.modules["_sc_smb_tools"] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def mock_cm(deploy_root: Path):
    """A mock ContextManager that reads/writes real files from deploy_root."""
    cm = MagicMock()
    cm._root = deploy_root
    cm.CATEGORY_MAP = {
        "documents": "documents.md",
        "finances": "finances.md",
        "insurance": "insurance.md",
        "calendar": "calendar.md",
        "family": "family.md",
        "tasks": "tasks.md",
        "general": "documents.md",
    }

    def load_committed():
        """Load all context files as dict of {stem: content}."""
        result = {}
        for f in (deploy_root / "context").glob("*.md"):
            result[f.stem] = f.read_text(encoding="utf-8")
        return result

    cm.load_committed = load_committed

    # Staging entry mock — writes to a list we can inspect
    cm._staging_entries = []

    def create_staging_entry(summary, content, category, source=""):
        entry = {"summary": summary, "content": content, "category": category, "source": source}
        cm._staging_entries.append(entry)
        return len(cm._staging_entries)

    cm.create_staging_entry = create_staging_entry

    return cm


@pytest.fixture
def deploy_env(deploy_root: Path, monkeypatch):
    """Set SC_DATA_DIR to the deploy root."""
    monkeypatch.setenv("SC_DATA_DIR", str(deploy_root))
    return deploy_root
