"""Tests for super-landlord extension — message handling, dispatch, staging review, and helpers."""
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def sl_extension(tmp_path: Path):
    """Import super-landlord extension module using ext_loader pattern."""
    # Create a minimal deployment
    deploy_root = tmp_path / "deploy"
    deploy_root.mkdir()
    (deploy_root / "AGENT.md").write_text("# Super-Landlord\n")
    (deploy_root / "profile.json").write_text(json.dumps({
        "name": "Super-Landlord",
        "context_files": ["properties", "tenants", "utilities", "debit_notes", "minpaku_handoffs"],
        "category_map": {"properties": "properties.md", "tenants": "tenants.md", "utilities": "utilities.md", "debit_notes": "debit_notes.md", "minpaku_handoffs": "minpaku_handoffs.md", "general": "properties.md"},
        "extensions": ["super-landlord"],
    }))
    (deploy_root / "context").mkdir()
    (deploy_root / "staging").mkdir()
    
    # Symlink the extension directory
    src_ext = Path(__file__).parent.parent / "extension"
    dst_ext = deploy_root / "extension"
    dst_ext.symlink_to(src_ext)
    
    # Add deployment root to sys.path
    if str(deploy_root) not in sys.path:
        sys.path.insert(0, str(deploy_root))
    
    # Clear any cached super-landlord extension modules
    for mod_name in list(sys.modules):
        if "super" in mod_name.lower() and "landlord" in mod_name.lower():
            del sys.modules[mod_name]
    
    # Import using the legacy extension module pattern
    import importlib.util
    ext_init = src_ext / "__init__.py"
    ext_tools = src_ext / "tools.py"
    ext_client = src_ext / "client.py"
    
    # Load the client module first
    client_spec = importlib.util.spec_from_file_location("_sc_ext_sl.client", ext_client)
    client_mod = importlib.util.module_from_spec(client_spec)
    sys.modules["_sc_ext_sl.client"] = client_mod
    client_spec.loader.exec_module(client_mod)
    
    # Load the package
    pkg_spec = importlib.util.spec_from_file_location(
        "_sc_ext_sl",
        ext_init if ext_init.exists() else ext_tools,
        submodule_search_locations=[str(src_ext)],
    )
    pkg_mod = importlib.util.module_from_spec(pkg_spec)
    sys.modules["_sc_ext_sl"] = pkg_mod
    pkg_spec.loader.exec_module(pkg_mod)
    
    # Load the tools module
    mod_spec = importlib.util.spec_from_file_location("_sc_ext_sl.tools", ext_tools)
    mod = importlib.util.module_from_spec(mod_spec)
    sys.modules["_sc_ext_sl.tools"] = mod
    mod_spec.loader.exec_module(mod)
    
    return mod


@pytest.fixture
def mock_cm(tmp_path: Path):
    """Create a mock ContextManager for testing."""
    (tmp_path / "context").mkdir()
    (tmp_path / "staging").mkdir()
    (tmp_path / "profile.json").write_text(json.dumps({
        "name": "Super-Landlord",
        "context_files": ["properties", "tenants", "utilities", "debit_notes", "minpaku_handoffs"],
        "category_map": {"properties": "properties.md", "tenants": "tenants.md", "utilities": "utilities.md", "debit_notes": "debit_notes.md", "minpaku_handoffs": "minpaku_handoffs.md", "general": "properties.md"},
    }))
    (tmp_path / "AGENT.md").write_text("# Super-Landlord\n")
    (tmp_path / "context" / "properties.md").write_text("# Properties\n\n## 12 Harbour View Road, Unit A & B\n- Unit: Unit A & B\n- Building: Harbour View\n")
    (tmp_path / "context" / "tenants.md").write_text("# Tenants\n")
    (tmp_path / "context" / "utilities.md").write_text("# Utilities\n")
    (tmp_path / "context" / "debit_notes.md").write_text("# Debit Notes\n")
    (tmp_path / "context" / "minpaku_handoffs.md").write_text("# Minpaku Handoffs\n")
    (tmp_path / "context" / "properties.md").write_text("# Properties\n\n## 12 Harbour View Road, Unit A & B\n- Unit: Unit A & B\n- Building: Harbour View\n")

    from simply_connect.context_manager import ContextManager
    return ContextManager(root=tmp_path)


@pytest.fixture
def mock_sl_client():
    """Create a mock SuperLandlordMinpakuClient."""
    client = MagicMock()
    client.create_property.return_value = {"success": True, "property": {"id": "prop-sla-1"}}
    client.delete_property.return_value = {"success": True}
    client.list_listings.return_value = []
    client.delete_listing.return_value = {"success": True}
    client.search_properties.return_value = [
        {"id": "prop-sla-1", "title": "12 Harbour View Road, Unit A & B", "hostId": "host-1"},
    ]
    return client


# ---------------------------------------------------------------------------
# dispatch — prepare_minpaku_handoff
# ---------------------------------------------------------------------------

class TestDispatch:
    def test_prepare_handoff_success(self, sl_extension, mock_cm):
        result = json.loads(sl_extension.dispatch("prepare_minpaku_handoff", {
            "source_property_ref": "12 Harbour View Road, Unit A & B",
            "availability": "available",
        }, mock_cm))
        assert result["ok"] is True
        assert result["staged"] is True
        assert result["handoff"]["source_property_ref"] == "12 Harbour View Road, Unit A & B"
        assert result["handoff"]["availability"] == "available"
        entries = mock_cm.list_staging(status="unconfirmed")
        assert len(entries) == 1

    def test_prepare_handoff_missing_fields(self, sl_extension, mock_cm):
        result = json.loads(sl_extension.dispatch("prepare_minpaku_handoff", {}, mock_cm))
        assert result["ok"] is False
        assert "source property reference" in result["missing_fields"]
        assert any("availability" in f for f in result["missing_fields"])

    def test_prepare_handoff_invalid_availability(self, sl_extension, mock_cm):
        result = json.loads(sl_extension.dispatch("prepare_minpaku_handoff", {
            "source_property_ref": "Test",
            "availability": "maybe",
        }, mock_cm))
        assert result["ok"] is False
        assert any("availability" in f for f in result["missing_fields"])

    def test_dispatch_unknown_tool(self, sl_extension, mock_cm):
        with pytest.raises(ValueError, match="Unknown tool"):
            sl_extension.dispatch("nonexistent_tool", {}, mock_cm)


# ---------------------------------------------------------------------------
# maybe_handle_message — operator role
# ---------------------------------------------------------------------------

class TestMaybeHandleMessage:
    def test_non_operator_returns_none(self, sl_extension, mock_cm):
        assert sl_extension.maybe_handle_message("test", mock_cm, role_name="guest") is None

    def test_empty_message_returns_none(self, sl_extension, mock_cm):
        assert sl_extension.maybe_handle_message("", mock_cm) is None

    def test_show_all_properties(self, sl_extension, mock_cm):
        reply = sl_extension.maybe_handle_message("show all properties.", mock_cm)
        assert reply is not None
        assert "12 Harbour View Road" in reply

    def test_show_all_properties_empty(self, sl_extension, tmp_path):
        (tmp_path / "context").mkdir()
        (tmp_path / "staging").mkdir()
        (tmp_path / "profile.json").write_text(json.dumps({
            "name": "Super-Landlord",
            "context_files": ["properties"],
            "category_map": {"properties": "properties.md", "general": "properties.md"},
        }))
        (tmp_path / "AGENT.md").write_text("# Test\n")
        (tmp_path / "context" / "properties.md").write_text("# Properties\n")
        from simply_connect.context_manager import ContextManager
        empty_cm = ContextManager(root=tmp_path)
        reply = sl_extension.maybe_handle_message("show all properties.", empty_cm)
        assert reply is not None
        assert "no properties" in reply.lower()

    def test_unrecognised_message_returns_none(self, sl_extension, mock_cm):
        assert sl_extension.maybe_handle_message("What is the weather?", mock_cm) is None


# ---------------------------------------------------------------------------
# review_staging_entry — minpaku handoffs
# ---------------------------------------------------------------------------

class TestReviewStagingEntry:
    def test_handoff_with_sync_status_approves(self, sl_extension, mock_cm):
        entry = mock_cm.create_staging_entry(
            summary="Minpaku handoff",
            content="## Minpaku Handoff — Test Property\n- Availability: available\n- Remote property ID: prop-1\n- Sync status: published to Minpaku (pending framework review)\n",
            category="minpaku_handoffs",
        )
        staging_entry = mock_cm.get_staging_entry(entry)
        review = sl_extension.review_staging_entry(mock_cm, staging_entry)
        assert review is not None
        assert review["recommendation"] == "approve"

    def test_handoff_missing_property_defers(self, sl_extension, mock_cm):
        entry = mock_cm.create_staging_entry(
            summary="Minpaku handoff",
            content="## Minpaku Handoff — \n- Availability: available\n",
            category="minpaku_handoffs",
        )
        staging_entry = mock_cm.get_staging_entry(entry)
        review = sl_extension.review_staging_entry(mock_cm, staging_entry)
        assert review is not None
        assert review["recommendation"] == "defer"

    def test_non_handoff_entry_returns_none(self, sl_extension, mock_cm):
        entry = mock_cm.create_staging_entry(
            summary="Test",
            content="Some content",
            category="properties",
        )
        staging_entry = mock_cm.get_staging_entry(entry)
        assert sl_extension.review_staging_entry(mock_cm, staging_entry) is None


# ---------------------------------------------------------------------------
# on_staging_approved — handoffs
# ---------------------------------------------------------------------------

class TestOnStagingApproved:
    def test_approved_handoff_with_sync_status(self, sl_extension, mock_cm, mock_sl_client):
        entry = mock_cm.create_staging_entry(
            summary="Minpaku handoff",
            content="## Minpaku Handoff — Test Property\n- Availability: available\n- Remote property ID: prop-1\n- Sync status: published to Minpaku (pending framework review)\n",
            category="minpaku_handoffs",
        )
        staging_entry = mock_cm.get_staging_entry(entry)
        with patch.object(sl_extension, "SuperLandlordMinpakuClient", return_value=mock_sl_client):
            result = sl_extension.on_staging_approved(mock_cm, staging_entry)
        assert result is not None
        assert result["ok"] is True

    def test_approved_handoff_creates_property(self, sl_extension, mock_cm, mock_sl_client):
        entry = mock_cm.create_staging_entry(
            summary="Minpaku handoff",
            content="## Minpaku Handoff — Test Property\n- Availability: available\n",
            category="minpaku_handoffs",
        )
        staging_entry = mock_cm.get_staging_entry(entry)
        with patch.object(sl_extension, "SuperLandlordMinpakuClient", return_value=mock_sl_client):
            result = sl_extension.on_staging_approved(mock_cm, staging_entry)
        assert result is not None
        assert result["ok"] is True
        assert "prop-sla-1" in result["message"]


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

class TestHelpers:
    def test_parse_handoff(self, sl_extension):
        content = "## Minpaku Handoff — Test Property\n- Availability: available\n- Landlord note: Test note\n- Remote property ID: prop-1\n- Remote host ID: host-1\n- Sync status: published\n"
        result = sl_extension._parse_handoff(content)
        assert result["source_property_ref"] == "Test Property"
        assert result["availability"] == "available"
        assert result["landlord_note"] == "Test note"
        assert result["remote_property_id"] == "prop-1"

    def test_extract_property_details(self, sl_extension, mock_cm):
        markdown = "## 12 Harbour View Road, Unit A & B\n- Unit: Unit A & B\n- Building: Harbour View\n"
        result = sl_extension._extract_property_details(markdown, "12 Harbour View Road, Unit A & B")
        assert result is not None
        assert "Unit A & B" in result

    def test_normalize_property_ref(self, sl_extension):
        assert sl_extension._normalize_property_ref("12 Harbour View Road!") == "12 harbour view road"

    def test_resolve_property_reference_exact(self, sl_extension, mock_cm):
        result = sl_extension._resolve_property_reference(mock_cm, "12 Harbour View Road, Unit A & B")
        assert result["status"] == "exact"
        assert result["resolved"] == "12 Harbour View Road, Unit A & B"

    def test_resolve_property_reference_none(self, sl_extension, mock_cm):
        result = sl_extension._resolve_property_reference(mock_cm, "Nonexistent Property")
        assert result["status"] == "none"
        assert result["resolved"] is None

    def test_iter_property_sections(self, sl_extension, mock_cm):
        markdown = "## Property A\n- Unit: A\n\n## Property B\n- Unit: B\n"
        sections = sl_extension._iter_property_sections(markdown)
        assert len(sections) == 2
        assert "Property A" in sections[0]
        assert "Property B" in sections[1]

    def test_parse_property_removal_request(self, sl_extension):
        content = "## Property Removal Request\n\n- Property: Test Property\n- Full service address: Test Address\n"
        result = sl_extension._parse_property_removal_request(content)
        assert result["is_removal"] == "yes"
        assert result["property_ref"] == "Test Property"

    def test_parse_property_candidate_blob(self, sl_extension):
        blob = """Extracted property from the utility bill:
- Unit: `Flat 12A`
- Building: `Harbour View`
- Full service address: `Flat 12A, Harbour View, Hong Kong`
"""
        result = sl_extension._parse_property_candidate_blob(blob)
        assert result is not None
        assert "Flat 12A" in result["unit"]

    def test_stage_property_candidate(self, sl_extension, mock_cm):
        candidate = {"property_ref": "Test Property", "unit": "Unit A", "building": "Building B", "full_address": "Unit A, Building B"}
        result = sl_extension._stage_property_candidate(mock_cm, candidate)
        assert result["entry_id"] is not None
        assert result["property_ref"] == "Test Property"
        entries = mock_cm.list_staging(status="unconfirmed")
        assert len(entries) == 1

    def test_has_existing_property_candidate(self, sl_extension, mock_cm):
        candidate = {"property_ref": "12 Harbour View Road, Unit A & B", "unit": "Unit A & B", "building": "Harbour View", "full_address": "12 Harbour View Road, Unit A & B"}
        assert sl_extension._has_existing_property_candidate(mock_cm, candidate) is True

    def test_find_pending_property_staging(self, sl_extension, mock_cm):
        sl_extension._stage_property_candidate(mock_cm, {
            "property_ref": "New Property",
            "unit": "Unit X",
            "building": "Building Y",
            "full_address": "Unit X, Building Y",
        })
        result = sl_extension._find_pending_property_staging(mock_cm)
        assert len(result) >= 1

    def test_stage_property_removal(self, sl_extension, mock_cm):
        result = sl_extension._stage_property_removal(mock_cm, "12 Harbour View Road, Unit A & B")
        assert result["entry_id"] is not None
        assert result["property_ref"] == "12 Harbour View Road, Unit A & B"

    def test_find_pending_property_removals(self, sl_extension, mock_cm):
        sl_extension._stage_property_removal(mock_cm, "Test Property")
        result = sl_extension._find_pending_property_removals(mock_cm)
        assert len(result) >= 1
        assert result[0]["property_ref"] == "Test Property"

    def test_find_matching_pending_property_removal(self, sl_extension, mock_cm):
        sl_extension._stage_property_removal(mock_cm, "Test Property")
        result = sl_extension._find_matching_pending_property_removal(mock_cm, "Test Property")
        assert result is not None
        assert result["property_ref"] == "Test Property"

    def test_property_matches_removal_target(self, sl_extension):
        assert sl_extension._property_matches_removal_target("Test Property", "Test Property") is True
        assert sl_extension._property_matches_removal_target("Test Property, Unit A", "Test Property") is True
        assert sl_extension._property_matches_removal_target("Other Property", "Test Property") is False

    def test_determine_location(self, sl_extension, monkeypatch):
        city, country = sl_extension._determine_location("Flat 12A, Harbour View")
        assert "Harbour View" in city or city == "Hong Kong"

    def test_reply_all_properties(self, sl_extension, mock_cm):
        reply = sl_extension._reply_all_properties(mock_cm)
        assert "12 Harbour View Road" in reply

    def test_visible_committed_property_titles(self, sl_extension, mock_cm):
        titles = sl_extension._visible_committed_property_titles(mock_cm)
        assert "12 Harbour View Road, Unit A & B" in titles

    def test_extract_debit_note_field(self, sl_extension):
        section = "## DN-2024-001\n- Tenant: John Doe\n- Amount: HKD 500.00\n- Status: Unpaid\n"
        assert sl_extension._extract_debit_note_field(section, "Tenant") == "John Doe"
        assert sl_extension._extract_debit_note_field(section, "Amount") == "HKD 500.00"

    def test_increment_debit_note_reference(self, sl_extension):
        assert sl_extension._increment_debit_note_reference("DN-2024-001") == "DN-2024-002"
        assert sl_extension._increment_debit_note_reference("DN-2024-099") == "DN-2024-100"

    def test_extract_latest_debit_note_draft(self, sl_extension):
        history = [
            {"role": "assistant", "content": """Debit Note Draft
`Reference`: `DN-2024-001`
`Issue date`: 2024-01-15
`Property`: 12 Harbour View Road
`Billed to`: John Doe
`Billing period`: January 2024
`Utility`: Water
`Amount due from John Doe`: **HKD 500.00**
"""},
        ]
        result = sl_extension._extract_latest_debit_note_draft(history)
        assert result is not None
        assert result["reference"] == "DN-2024-001"
        assert result["billed_to"] == "John Doe"

    def test_extract_latest_debit_note_draft_no_match(self, sl_extension):
        assert sl_extension._extract_latest_debit_note_draft(None) is None
        assert sl_extension._extract_latest_debit_note_draft([]) is None
        assert sl_extension._extract_latest_debit_note_draft([{"role": "user", "content": "test"}]) is None

    def test_stage_issued_debit_note_from_history(self, sl_extension, mock_cm):
        history = [
            {"role": "assistant", "content": """Debit Note Draft
`Reference`: `DN-2024-001`
`Issue date`: 2024-01-15
`Property`: 12 Harbour View Road
`Billed to`: John Doe
`Billing period`: January 2024
`Utility`: Water
`Amount due from John Doe`: **HKD 500.00**
"""},
        ]
        result = sl_extension._stage_issued_debit_note_from_history(mock_cm, history)
        assert result is not None
        assert result["reference"] == "DN-2024-001"
        assert result["next_reference"] == "DN-2024-002"
        entries = mock_cm.list_staging(status="unconfirmed")
        assert len(entries) == 1

    def test_build_remote_payload(self, sl_extension, mock_cm):
        handoff = {
            "source_property_ref": "12 Harbour View Road, Unit A & B",
            "availability": "available",
            "landlord_note": "Test note",
        }
        payload = sl_extension._build_remote_payload(mock_cm, handoff)
        assert payload["title"] == "12 Harbour View Road, Unit A & B"
        assert "Test note" in payload["description"]

    def test_build_synced_handoff_block(self, sl_extension):
        block = sl_extension._build_synced_handoff_block(
            source_property_ref="Test Property",
            availability="available",
            remote_property_id="prop-1",
            remote_host_id="host-1",
            landlord_note="Test note",
            sync_status="published to Minpaku",
        )
        assert "Test Property" in block
        assert "prop-1" in block
        assert "host-1" in block

    def test_iter_debit_note_sections(self, sl_extension):
        markdown = "## DN-2024-001\n- Tenant: John\n\n## DN-2024-002\n- Tenant: Jane\n"
        sections = sl_extension._iter_debit_note_sections(markdown)
        assert len(sections) == 2
        assert "DN-2024-001" in sections[0]
        assert "DN-2024-002" in sections[1]

    def test_matches_debit_note_target(self, sl_extension):
        assert sl_extension._matches_debit_note_target("John Doe", "john") is True
        assert sl_extension._matches_debit_note_target("Jane Smith", "john") is False

    def test_find_outstanding_committed_debit_notes(self, sl_extension, tmp_path):
        (tmp_path / "context").mkdir()
        (tmp_path / "staging").mkdir()
        (tmp_path / "profile.json").write_text(json.dumps({
            "name": "Super-Landlord",
            "context_files": ["debit_notes"],
            "category_map": {"debit_notes": "debit_notes.md", "general": "debit_notes.md"},
        }))
        (tmp_path / "AGENT.md").write_text("# Test\n")
        (tmp_path / "context" / "debit_notes.md").write_text("""# Debit Notes

## DN-2024-001
- Tenant: John Doe
- Property: 12 Harbour View Road
- Amount: HKD 500.00
- Status: Unpaid
""")
        from simply_connect.context_manager import ContextManager
        cm = ContextManager(root=tmp_path)
        result = sl_extension._find_outstanding_committed_debit_notes(cm, "John")
        assert len(result) == 1
        assert result[0]["reference"] == "DN-2024-001"

    def test_reply_outstanding_debit_notes(self, sl_extension, tmp_path):
        (tmp_path / "context").mkdir()
        (tmp_path / "staging").mkdir()
        (tmp_path / "profile.json").write_text(json.dumps({
            "name": "Super-Landlord",
            "context_files": ["debit_notes"],
            "category_map": {"debit_notes": "debit_notes.md", "general": "debit_notes.md"},
        }))
        (tmp_path / "AGENT.md").write_text("# Test\n")
        (tmp_path / "context" / "debit_notes.md").write_text("""# Debit Notes

## DN-2024-001
- Tenant: John Doe
- Property: 12 Harbour View Road
- Amount: HKD 500.00
- Status: Unpaid
""")
        from simply_connect.context_manager import ContextManager
        cm = ContextManager(root=tmp_path)
        reply = sl_extension._reply_outstanding_debit_notes(cm, "John")
        assert reply is not None
        assert "DN-2024-001" in reply

    def test_reply_outstanding_debit_notes_no_match(self, sl_extension, mock_cm):
        reply = sl_extension._reply_outstanding_debit_notes(mock_cm, "Nonexistent")
        assert reply is None

    def test_reply_blocked_debit_note_for_removed_property(self, sl_extension, mock_cm):
        sl_extension._stage_property_removal(mock_cm, "12 Harbour View Road, Unit A & B")
        reply = sl_extension._reply_blocked_debit_note_for_removed_property(mock_cm, "12 Harbour View Road, Unit A & B")
        assert reply is not None
        assert "can't generate a debit note" in reply.lower()

    def test_reply_blocked_debit_note_without_active_property(self, sl_extension, mock_cm):
        sl_extension._stage_property_removal(mock_cm, "12 Harbour View Road, Unit A & B")
        reply = sl_extension._reply_blocked_debit_note_without_active_property(mock_cm)
        assert reply is not None
        assert "no active properties" in reply.lower()

    def test_strip_pending_framework_review(self, sl_extension):
        assert sl_extension._strip_pending_framework_review("published (pending framework review)") == "published"
        assert sl_extension._strip_pending_framework_review(None) is None
