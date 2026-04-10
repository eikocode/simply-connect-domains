"""Tests for family management tools: list/add/remove/rename."""

import json

import pytest


def _seed_family(deploy_root, primary_name="Ada", members=None):
    """Write a family.md with given primary user and members."""
    members = members or []
    lines = ["# Family\n"]
    lines.append("> Household members. Names only — relationships can be added later.\n")
    lines.append(f"## {primary_name}")
    lines.append("- Role: primary user")
    lines.append("")
    for name in members:
        lines.append(f"## {name}")
        lines.append("- Relationship: household member")
        lines.append("")
    (deploy_root / "context" / "family.md").write_text("\n".join(lines), encoding="utf-8")


# ---------------------------------------------------------------------------
# list_family_members
# ---------------------------------------------------------------------------

class TestListFamilyMembers:
    def test_empty_family(self, tools_module, mock_cm, deploy_root):
        result = json.loads(tools_module._list_family_members(mock_cm))
        assert result["primary_user"]["name"] == "unknown"
        assert result["household_members"] == []
        assert result["total_count"] == 0

    def test_primary_only(self, tools_module, mock_cm, deploy_root):
        _seed_family(deploy_root, "Ada")
        result = json.loads(tools_module._list_family_members(mock_cm))
        assert result["primary_user"]["name"] == "Ada"
        assert result["household_members"] == []
        assert result["total_count"] == 1

    def test_primary_plus_members(self, tools_module, mock_cm, deploy_root):
        _seed_family(deploy_root, "Ada", ["Sam", "Jen"])
        result = json.loads(tools_module._list_family_members(mock_cm))
        assert result["primary_user"]["name"] == "Ada"
        assert len(result["household_members"]) == 2
        names = [m["name"] for m in result["household_members"]]
        assert "Sam" in names
        assert "Jen" in names

    def test_primary_user_note_present(self, tools_module, mock_cm, deploy_root):
        """REGRESSION: Claude was asking about primary user — the 'note' field
        tells Claude not to ask."""
        _seed_family(deploy_root, "Ada")
        result = json.loads(tools_module._list_family_members(mock_cm))
        assert "note" in result["primary_user"]
        assert "not ask" in result["primary_user"]["note"].lower()


# ---------------------------------------------------------------------------
# add_family_member
# ---------------------------------------------------------------------------

class TestAddFamilyMember:
    def test_add_to_empty(self, tools_module, mock_cm, deploy_root):
        _seed_family(deploy_root, "Ada")
        result = json.loads(tools_module._add_family_member("Sam", mock_cm))
        assert result["success"] is True
        assert "Sam" in result["members"]

    def test_add_multiple(self, tools_module, mock_cm, deploy_root):
        _seed_family(deploy_root, "Ada")
        tools_module._add_family_member("Sam", mock_cm)
        result = json.loads(tools_module._add_family_member("Jen", mock_cm))
        assert result["success"] is True
        assert set(result["members"]) == {"Sam", "Jen"}

    def test_reject_duplicate(self, tools_module, mock_cm, deploy_root):
        _seed_family(deploy_root, "Ada", ["Sam"])
        result = json.loads(tools_module._add_family_member("Sam", mock_cm))
        assert result["success"] is False
        assert "already" in result["error"].lower()

    def test_reject_duplicate_case_insensitive(self, tools_module, mock_cm, deploy_root):
        _seed_family(deploy_root, "Ada", ["Sam"])
        result = json.loads(tools_module._add_family_member("sam", mock_cm))
        assert result["success"] is False

    def test_reject_duplicate_of_primary(self, tools_module, mock_cm, deploy_root):
        _seed_family(deploy_root, "Ada")
        result = json.loads(tools_module._add_family_member("Ada", mock_cm))
        assert result["success"] is False

    def test_reject_empty_name(self, tools_module, mock_cm, deploy_root):
        _seed_family(deploy_root, "Ada")
        result = json.loads(tools_module._add_family_member("", mock_cm))
        assert result["success"] is False

    def test_max_7_limit(self, tools_module, mock_cm, deploy_root):
        _seed_family(deploy_root, "Ada", ["M1", "M2", "M3", "M4", "M5", "M6", "M7"])
        result = json.loads(tools_module._add_family_member("M8", mock_cm))
        assert result["success"] is False
        assert "full" in result["error"].lower() or "max" in result["error"].lower()


# ---------------------------------------------------------------------------
# remove_family_member
# ---------------------------------------------------------------------------

class TestRemoveFamilyMember:
    def test_remove_existing(self, tools_module, mock_cm, deploy_root):
        _seed_family(deploy_root, "Ada", ["Sam", "Jen"])
        result = json.loads(tools_module._remove_family_member("Sam", mock_cm))
        assert result["success"] is True
        assert "Sam" not in result["members"]
        assert "Jen" in result["members"]

    def test_remove_not_found(self, tools_module, mock_cm, deploy_root):
        _seed_family(deploy_root, "Ada", ["Sam"])
        result = json.loads(tools_module._remove_family_member("Bob", mock_cm))
        assert result["success"] is False
        assert "not in" in result["error"].lower()

    def test_cannot_remove_primary(self, tools_module, mock_cm, deploy_root):
        _seed_family(deploy_root, "Ada", ["Sam"])
        result = json.loads(tools_module._remove_family_member("Ada", mock_cm))
        assert result["success"] is False
        assert "primary" in result["error"].lower() or "you" in result["error"].lower()

    def test_remove_case_insensitive(self, tools_module, mock_cm, deploy_root):
        _seed_family(deploy_root, "Ada", ["Sam"])
        result = json.loads(tools_module._remove_family_member("sam", mock_cm))
        assert result["success"] is True


# ---------------------------------------------------------------------------
# rename_family_member
# ---------------------------------------------------------------------------

class TestRenameFamilyMember:
    def test_rename_member(self, tools_module, mock_cm, deploy_root):
        """REGRESSION: Eiko's 'replace Jen with Susan' use case."""
        _seed_family(deploy_root, "Ada", ["Sam", "Jen"])
        result = json.loads(tools_module._rename_family_member("Jen", "Susan", mock_cm))
        assert result["success"] is True
        assert "Susan" in result["members"]
        assert "Jen" not in result["members"]

    def test_rename_case_insensitive(self, tools_module, mock_cm, deploy_root):
        _seed_family(deploy_root, "Ada", ["Sam"])
        result = json.loads(tools_module._rename_family_member("sam", "Samuel", mock_cm))
        assert result["success"] is True
        assert "Samuel" in result["members"]

    def test_rename_primary_user(self, tools_module, mock_cm, deploy_root):
        """Primary user can be renamed too."""
        _seed_family(deploy_root, "Ada")
        result = json.loads(tools_module._rename_family_member("Ada", "Adelaine", mock_cm))
        assert result["success"] is True

    def test_rename_not_found(self, tools_module, mock_cm, deploy_root):
        _seed_family(deploy_root, "Ada", ["Sam"])
        result = json.loads(tools_module._rename_family_member("Bob", "Robert", mock_cm))
        assert result["success"] is False

    def test_rename_empty_args(self, tools_module, mock_cm, deploy_root):
        _seed_family(deploy_root, "Ada", ["Sam"])
        result = json.loads(tools_module._rename_family_member("", "Susan", mock_cm))
        assert result["success"] is False
        result = json.loads(tools_module._rename_family_member("Sam", "", mock_cm))
        assert result["success"] is False

    def test_rename_persists_to_file(self, tools_module, mock_cm, deploy_root):
        """File should be updated, not just the return value."""
        _seed_family(deploy_root, "Ada", ["Sam", "Jen"])
        tools_module._rename_family_member("Jen", "Susan", mock_cm)
        family_md = (deploy_root / "context" / "family.md").read_text()
        assert "Susan" in family_md
        assert "Jen" not in family_md
        assert "Sam" in family_md
        assert "Ada" in family_md


# ---------------------------------------------------------------------------
# Dispatch (MCP tool name routing)
# ---------------------------------------------------------------------------

class TestDispatch:
    def test_list_family_members_dispatch(self, tools_module, mock_cm, deploy_root):
        _seed_family(deploy_root, "Ada", ["Sam"])
        result = tools_module.dispatch("list_family_members", {}, mock_cm)
        data = json.loads(result)
        assert data["primary_user"]["name"] == "Ada"

    def test_add_family_member_dispatch(self, tools_module, mock_cm, deploy_root):
        _seed_family(deploy_root, "Ada")
        result = tools_module.dispatch("add_family_member", {"name": "Sam"}, mock_cm)
        assert json.loads(result)["success"] is True

    def test_rename_family_member_dispatch(self, tools_module, mock_cm, deploy_root):
        _seed_family(deploy_root, "Ada", ["Sam"])
        result = tools_module.dispatch(
            "rename_family_member",
            {"old_name": "Sam", "new_name": "Samuel"},
            mock_cm,
        )
        assert json.loads(result)["success"] is True

    def test_unknown_tool_raises(self, tools_module, mock_cm, deploy_root):
        with pytest.raises(ValueError, match="Unknown tool"):
            tools_module.dispatch("nonexistent_tool", {}, mock_cm)

    def test_all_tools_declared(self, tools_module):
        """Sanity check — all TOOLS must have a dispatch handler."""
        tool_names = {t["name"] for t in tools_module.TOOLS}
        expected = {
            "search_documents",
            "list_expiry_dates",
            "list_tasks",
            "get_financial_summary",
            "list_family_members",
            "add_family_member",
            "remove_family_member",
            "rename_family_member",
        }
        assert expected.issubset(tool_names)
