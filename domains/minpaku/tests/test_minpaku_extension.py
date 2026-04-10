"""Tests for minpaku extension — message handling, staging review, and helpers."""
import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add simply-connect-domains root to sys.path
DOMAINS_ROOT = Path(__file__).parent.parent.parent.parent
if str(DOMAINS_ROOT) not in sys.path:
    sys.path.insert(0, str(DOMAINS_ROOT))


@pytest.fixture
def minpaku_extension(tmp_path: Path):
    """Import minpaku extension module using ext_loader pattern."""
    # Create a minimal deployment that declares the minpaku extension
    deploy_root = tmp_path / "deploy"
    deploy_root.mkdir()
    (deploy_root / "AGENT.md").write_text("# Minpaku\n")
    (deploy_root / "profile.json").write_text(json.dumps({
        "name": "Minpaku",
        "context_files": ["properties", "operations", "pricing"],
        "category_map": {"properties": "properties.md", "operations": "operations.md", "pricing": "pricing.md", "general": "properties.md"},
        "extensions": ["minpaku"],
    }))
    (deploy_root / "context").mkdir()
    (deploy_root / "staging").mkdir()
    
    # Symlink or copy the extension directory into the deployment
    src_ext = Path(__file__).parent.parent / "extension"
    dst_ext = deploy_root / "extension"
    dst_ext.symlink_to(src_ext)
    
    # Add deployment root to sys.path (mimics ext_loader behavior)
    if str(deploy_root) not in sys.path:
        sys.path.insert(0, str(deploy_root))
    
    # Clear any cached minpaku extension modules
    for mod_name in list(sys.modules):
        if "minpaku" in mod_name.lower() and "extension" in mod_name:
            del sys.modules[mod_name]
    
    # Import using the legacy extension module pattern
    import importlib.util
    ext_init = src_ext / "__init__.py"
    ext_tools = src_ext / "tools.py"
    ext_client = src_ext / "client.py"
    
    # Load the client module first
    client_spec = importlib.util.spec_from_file_location("_sc_ext_minpaku.client", ext_client)
    client_mod = importlib.util.module_from_spec(client_spec)
    sys.modules["_sc_ext_minpaku.client"] = client_mod
    client_spec.loader.exec_module(client_mod)
    
    # Load the package
    pkg_spec = importlib.util.spec_from_file_location(
        "_sc_ext_minpaku",
        ext_init if ext_init.exists() else ext_tools,
        submodule_search_locations=[str(src_ext)],
    )
    pkg_mod = importlib.util.module_from_spec(pkg_spec)
    sys.modules["_sc_ext_minpaku"] = pkg_mod
    pkg_spec.loader.exec_module(pkg_mod)
    
    # Load the tools module
    mod_spec = importlib.util.spec_from_file_location("_sc_ext_minpaku.tools", ext_tools)
    mod = importlib.util.module_from_spec(mod_spec)
    sys.modules["_sc_ext_minpaku.tools"] = mod
    mod_spec.loader.exec_module(mod)
    
    return mod


@pytest.fixture
def mock_cm(tmp_path: Path):
    """Create a mock ContextManager for testing."""
    (tmp_path / "context").mkdir()
    (tmp_path / "staging").mkdir()
    (tmp_path / "profile.json").write_text(json.dumps({
        "name": "Minpaku",
        "context_files": ["properties", "operations", "pricing"],
        "category_map": {"properties": "properties.md", "operations": "operations.md", "pricing": "pricing.md", "general": "properties.md"},
    }))
    (tmp_path / "AGENT.md").write_text("# Minpaku\n")
    (tmp_path / "context" / "properties.md").write_text("## Test Property\n")
    (tmp_path / "context" / "operations.md").write_text("## Operations\n")
    (tmp_path / "context" / "pricing.md").write_text("## Pricing\n")

    from simply_connect.context_manager import ContextManager
    return ContextManager(root=tmp_path)


@pytest.fixture
def mock_minpaku_client():
    """Create a mock MinpakuClient."""
    client = MagicMock()
    client.list_properties.return_value = [
        {
            "id": "prop-1",
            "title": "Harbour View Unit A",
            "location": {"city": "Hong Kong", "country": "HK"},
            "maxGuests": 4,
            "nightlyPrice": 1000,
            "currency": "HKD",
        },
        {
            "id": "prop-2",
            "title": "Harbour View Unit B",
            "location": {"city": "Hong Kong", "country": "HK"},
            "maxGuests": 2,
            "nightlyPrice": 800,
            "currency": "HKD",
        },
    ]
    client.search_properties.return_value = [
        {
            "id": "prop-1",
            "title": "Harbour View Unit A",
            "location": {"city": "Hong Kong", "country": "HK"},
            "maxGuests": 4,
            "nightlyPrice": 1000,
            "currency": "HKD",
        },
    ]
    client.get_property.return_value = {
        "id": "prop-1",
        "title": "Harbour View Unit A",
        "location": {"city": "Hong Kong", "country": "HK"},
        "maxGuests": 4,
        "nightlyPrice": 1000,
        "currency": "HKD",
    }
    client.get_bookings_by_property.return_value = {
        "bookings": [
            {"id": "bk-1", "status": "PENDING", "guest": {"name": "John"}, "checkIn": "2024-01-01", "checkOut": "2024-01-05"},
            {"id": "bk-2", "status": "CONFIRMED", "guest": {"name": "Jane"}, "checkIn": "2024-02-01", "checkOut": "2024-02-05"},
        ]
    }
    client.list_listings.return_value = [
        {"id": "list-1", "propertyId": "prop-1", "platform": "airbnb", "title": "Harbour View A", "status": "active"},
    ]
    client.update_property.return_value = {"success": True}
    client.confirm_booking.return_value = {
        "ok": True,
        "booking": {"id": "bk-1", "status": "CONFIRMED"},
        "confirmation": {"confirmationId": "CONF-123"},
        "paymentIntent": {"status": "SUCCEEDED"},
    }
    return client


# ---------------------------------------------------------------------------
# maybe_handle_message — operator role
# ---------------------------------------------------------------------------

class TestMaybeHandleMessage:
    def test_non_operator_returns_none(self, minpaku_extension, mock_cm):
        assert minpaku_extension.maybe_handle_message("test", mock_cm, role_name="guest") is None
        assert minpaku_extension.maybe_handle_message("test", mock_cm, role_name="housekeeping") is None

    def test_empty_message_returns_none(self, minpaku_extension, mock_cm):
        assert minpaku_extension.maybe_handle_message("", mock_cm) is None
        assert minpaku_extension.maybe_handle_message("   ", mock_cm) is None

    def test_show_all_properties(self, minpaku_extension, mock_cm, mock_minpaku_client, monkeypatch):
        monkeypatch.setenv("MINPAKU_API_URL", "https://test.minpaku.com")
        with patch.object(minpaku_extension, "MinpakuClient", return_value=mock_minpaku_client):
            reply = minpaku_extension.maybe_handle_message("Show all properties.", mock_cm)
        assert reply is not None
        assert "Harbour View Unit A" in reply
        assert "prop-1" in reply
        assert "2 total" in reply

    def test_show_all_properties_empty(self, minpaku_extension, mock_cm, mock_minpaku_client, monkeypatch):
        monkeypatch.setenv("MINPAKU_API_URL", "https://test.minpaku.com")
        mock_minpaku_client.list_properties.return_value = []
        with patch.object(minpaku_extension, "MinpakuClient", return_value=mock_minpaku_client):
            reply = minpaku_extension.maybe_handle_message("Show all properties.", mock_cm)
        assert reply is not None
        assert "count: 0" in reply

    def test_show_bookings_needing_payment_confirmation(self, minpaku_extension, mock_cm, mock_minpaku_client, monkeypatch):
        monkeypatch.setenv("MINPAKU_API_URL", "https://test.minpaku.com")
        with patch.object(minpaku_extension, "MinpakuClient", return_value=mock_minpaku_client):
            reply = minpaku_extension.maybe_handle_message("Show bookings needing payment confirmation.", mock_cm)
        assert reply is not None
        assert "bk-1" in reply
        assert "PENDING" in reply
        assert "confirm booking" in reply.lower()

    def test_show_bookings_none_pending(self, minpaku_extension, mock_cm, mock_minpaku_client, monkeypatch):
        monkeypatch.setenv("MINPAKU_API_URL", "https://test.minpaku.com")
        mock_minpaku_client.get_bookings_by_property.return_value = {
            "bookings": [
                {"id": "bk-1", "status": "CONFIRMED"},
            ]
        }
        with patch.object(minpaku_extension, "MinpakuClient", return_value=mock_minpaku_client):
            reply = minpaku_extension.maybe_handle_message("Show bookings needing payment confirmation.", mock_cm)
        assert reply is not None
        assert "no live bookings" in reply.lower()

    def test_show_all_listings(self, minpaku_extension, mock_cm, mock_minpaku_client, monkeypatch):
        monkeypatch.setenv("MINPAKU_API_URL", "https://test.minpaku.com")
        with patch.object(minpaku_extension, "MinpakuClient", return_value=mock_minpaku_client):
            reply = minpaku_extension.maybe_handle_message("Show all listings.", mock_cm)
        assert reply is not None
        assert "list-1" in reply
        assert "airbnb" in reply

    def test_unrecognised_message_returns_none(self, minpaku_extension, mock_cm):
        assert minpaku_extension.maybe_handle_message("What is the weather?", mock_cm) is None


# ---------------------------------------------------------------------------
# maybe_handle_message — config check
# ---------------------------------------------------------------------------

class TestConfigCheck:
    def test_missing_api_url_returns_none(self, minpaku_extension, mock_cm, monkeypatch):
        monkeypatch.delenv("MINPAKU_API_URL", raising=False)
        monkeypatch.delenv("MINPAKU_BASE_URL", raising=False)
        reply = minpaku_extension.maybe_handle_message("Show all properties.", mock_cm)
        assert reply is None

    def test_with_api_url_proceeds(self, minpaku_extension, mock_cm, mock_minpaku_client, monkeypatch):
        monkeypatch.setenv("MINPAKU_API_URL", "https://test.minpaku.com")
        with patch.object(minpaku_extension, "MinpakuClient", return_value=mock_minpaku_client):
            reply = minpaku_extension.maybe_handle_message("Show all properties.", mock_cm)
        assert reply is not None


# ---------------------------------------------------------------------------
# review_staging_entry — listing drafts
# ---------------------------------------------------------------------------

class TestReviewStagingEntry:
    def test_listing_draft_with_no_duplicates_approves(self, minpaku_extension, mock_cm, mock_minpaku_client, monkeypatch):
        monkeypatch.setenv("MINPAKU_API_URL", "https://test.minpaku.com")
        mock_minpaku_client.list_listings.return_value = []
        entry = mock_cm.create_staging_entry(
            summary="Listing draft",
            content='```json\n{"title": "Test", "propertyId": "prop-1", "platform": "airbnb", "source_property_ref": "Test Property"}\n```',
            category="listing_publications",
        )
        staging_entry = mock_cm.get_staging_entry(entry)
        with patch.object(minpaku_extension, "MinpakuClient", return_value=mock_minpaku_client):
            review = minpaku_extension.review_staging_entry(mock_cm, staging_entry)
        assert review is not None
        assert review["recommendation"] == "approve"

    def test_listing_draft_with_duplicates_defers(self, minpaku_extension, mock_cm, mock_minpaku_client, monkeypatch):
        monkeypatch.setenv("MINPAKU_API_URL", "https://test.minpaku.com")
        mock_minpaku_client.list_listings.return_value = [
            {"propertyId": "prop-1", "platform": "airbnb"},
            {"propertyId": "prop-1", "platform": "airbnb"},
        ]
        entry = mock_cm.create_staging_entry(
            summary="Listing draft",
            content='```json\n{"title": "Test", "propertyId": "prop-1", "platform": "airbnb", "source_property_ref": "Test Property"}\n```',
            category="listing_publications",
        )
        staging_entry = mock_cm.get_staging_entry(entry)
        with patch.object(minpaku_extension, "MinpakuClient", return_value=mock_minpaku_client):
            review = minpaku_extension.review_staging_entry(mock_cm, staging_entry)
        assert review is not None
        assert review["recommendation"] == "defer"
        assert "duplicate" in review["reason"].lower()

    def test_non_listing_entry_returns_none(self, minpaku_extension, mock_cm):
        entry = mock_cm.create_staging_entry(
            summary="Test",
            content="Some content",
            category="properties",
        )
        staging_entry = mock_cm.get_staging_entry(entry)
        assert minpaku_extension.review_staging_entry(mock_cm, staging_entry) is None


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

class TestHelpers:
    def test_normalize_entity_ref(self, minpaku_extension):
        assert minpaku_extension._normalize_entity_ref("Harbour View  Unit A!") == "harbour view unit a"
        assert minpaku_extension._normalize_entity_ref("PROP-1") == "prop 1"

    def test_count_active_bookings(self, minpaku_extension):
        payload = {"bookings": [
            {"status": "PENDING"},
            {"status": "HOLD"},
            {"status": "CONFIRMED"},
            {"status": "CANCELLED"},
        ]}
        assert minpaku_extension._count_active_or_upcoming_bookings(payload) == 3

    def test_extract_bookings(self, minpaku_extension):
        payload = {"bookings": [{"id": "bk-1"}, {"id": "bk-2"}]}
        result = minpaku_extension._extract_bookings(payload)
        assert len(result) == 2
        assert result[0]["id"] == "bk-1"

    def test_extract_bookings_from_list(self, minpaku_extension):
        payload = [{"id": "bk-1"}, {"id": "bk-2"}]
        result = minpaku_extension._extract_bookings(payload)
        assert len(result) == 2

    def test_extract_location_dict(self, minpaku_extension):
        prop = {"location": {"city": "Tokyo", "country": "JP"}}
        city, country = minpaku_extension._extract_location(prop)
        assert city == "Tokyo"
        assert country == "JP"

    def test_extract_location_string(self, minpaku_extension):
        prop = {"location": "Hong Kong, HK"}
        city, country = minpaku_extension._extract_location(prop)
        assert city == "Hong Kong"
        assert country == "HK"

    def test_resolve_unique_property_match_exact(self, minpaku_extension):
        props = [{"id": "prop-1", "title": "Harbour View"}]
        result = minpaku_extension._resolve_unique_property_match(props, "prop-1")
        assert result is not None
        assert result["id"] == "prop-1"

    def test_resolve_unique_property_match_ambiguous(self, minpaku_extension):
        props = [
            {"id": "prop-1", "title": "Harbour View"},
            {"id": "prop-2", "title": "Harbour View"},
        ]
        assert minpaku_extension._resolve_unique_property_match(props, "harbour view") is None

    def test_parse_price_update_request(self, minpaku_extension):
        result = minpaku_extension._parse_price_update_request("Update Harbour View to $1200 HKD per night")
        assert result is not None
        assert result["target"] == "Harbour View"
        assert result["nightly_price"] == 1200.0
        assert result["currency_hint"] == "HKD"

    def test_parse_price_update_request_no_match(self, minpaku_extension):
        assert minpaku_extension._parse_price_update_request("Show all properties") is None

    def test_parse_property_edit_request_max_guests(self, minpaku_extension):
        result = minpaku_extension._parse_property_edit_request("Update Harbour View to have 6 guests")
        assert result is not None
        assert result["field"] == "maxGuests"
        assert result["value"] == 6

    def test_parse_property_edit_request_rules(self, minpaku_extension):
        result = minpaku_extension._parse_property_edit_request("Update Harbour View rules to No smoking")
        assert result is not None
        assert result["field"] == "rules"
        assert result["value"] == "No smoking"

    def test_build_property_update_payload(self, minpaku_extension):
        prop = {
            "title": "Test Property",
            "location": {"city": "HK", "country": "HK", "coordinates": {"latitude": 22.3, "longitude": 114.1}},
            "amenities": ["wifi"],
            "maxGuests": 4,
            "hostId": "host-1",
        }
        payload = minpaku_extension._build_property_update_payload(prop, 1500, "HKD")
        assert payload["title"] == "Test Property"
        assert payload["nightlyPrice"] == 1500
        assert payload["currency"] == "HKD"
        assert payload["maxGuests"] == 4

    def test_flatten_listing_rows(self, minpaku_extension):
        nested = [{"listings": [{"id": "l1"}, {"id": "l2"}]}]
        result = minpaku_extension._flatten_listing_rows(nested)
        assert len(result) == 1
        assert "listings" in result[0]

    def test_format_listing_action_result_publish(self, minpaku_extension):
        result = minpaku_extension._format_listing_action_result("publish", {
            "ok": True,
            "title": "Test Listing",
            "listing_id": "list-1",
            "property_id": "prop-1",
            "entry_id": "entry-1",
        })
        assert "Published" in result
        assert "list-1" in result

    def test_format_listing_action_result_failure(self, minpaku_extension):
        result = minpaku_extension._format_listing_action_result("publish", {
            "ok": False,
            "error": "API error",
        })
        assert "API error" in result

    def test_format_booking_confirmation_result(self, minpaku_extension):
        result = minpaku_extension._format_booking_confirmation_result({
            "ok": True,
            "booking": {"id": "bk-1", "status": "CONFIRMED"},
            "confirmation": {"confirmationId": "CONF-123"},
            "paymentIntent": {"status": "SUCCEEDED"},
        }, "bk-1")
        assert "Confirmed" in result
        assert "CONFIRMED" in result
        assert "SUCCEEDED" in result

    def test_stage_price_update_note(self, minpaku_extension, mock_cm):
        prop = {"title": "Test Property", "id": "prop-1"}
        entry_id = minpaku_extension._stage_price_update_note(mock_cm, prop, 1500, "HKD")
        assert entry_id is not None
        staging = mock_cm.get_staging_entry(entry_id)
        assert "Price Update" in staging["content"]
        assert "1500" in staging["content"]

    def test_stage_property_edit_note(self, minpaku_extension, mock_cm):
        prop = {"title": "Test Property", "id": "prop-1"}
        entry_id = minpaku_extension._stage_property_edit_note(mock_cm, prop, "maxGuests", 6)
        assert entry_id is not None
        staging = mock_cm.get_staging_entry(entry_id)
        assert "Property Update" in staging["content"]
        assert "maxGuests" in staging["content"]

    def test_parse_property_removal_request(self, minpaku_extension):
        content = """## Property Removal Request

**Requested by:** Host operator
**Date:** 2024-01-01

**Property to remove:**
- ID: `prop-1`
- Title: Test Property
- Location: Hong Kong, HK
- Host ID: `host-1`
- Active or upcoming bookings at request time: 0

**Action required:** Permanently remove this property from the Minpaku portfolio on admin approval."""
        result = minpaku_extension._parse_property_removal_request(content)
        assert result["property_id"] == "prop-1"
        assert result["title"] == "Test Property"
        assert result["active_booking_count"] == 0

    def test_stage_property_removal(self, minpaku_extension, mock_cm):
        prop = {"title": "Test Property", "id": "prop-1", "location": {"city": "HK", "country": "HK"}}
        reply = minpaku_extension._stage_property_removal(mock_cm, prop, 0)
        assert "Removal request logged" in reply
        assert "prop-1" in reply
        assert "No active or upcoming bookings" in reply

    def test_stage_property_removal_with_bookings(self, minpaku_extension, mock_cm):
        prop = {"title": "Test Property", "id": "prop-1"}
        reply = minpaku_extension._stage_property_removal(mock_cm, prop, 2)
        assert "2 active or upcoming booking(s)" in reply

    def test_safe_active_listing_note_success(self, minpaku_extension, mock_minpaku_client):
        mock_minpaku_client.list_listings.return_value = [{"id": "l1"}]
        note = minpaku_extension._safe_active_listing_note(mock_minpaku_client, "prop-1", "Test")
        assert "1" in note

    def test_safe_active_listing_note_no_listings(self, minpaku_extension, mock_minpaku_client):
        mock_minpaku_client.list_listings.return_value = []
        note = minpaku_extension._safe_active_listing_note(mock_minpaku_client, "prop-1", "Test")
        assert "no active listings" in note.lower()

    def test_safe_active_listing_note_exception(self, minpaku_extension, mock_minpaku_client):
        mock_minpaku_client.list_listings.side_effect = Exception("API down")
        note = minpaku_extension._safe_active_listing_note(mock_minpaku_client, "prop-1", "Test")
        assert "unavailable" in note.lower()

    def test_check_config_missing(self, minpaku_extension, monkeypatch):
        monkeypatch.delenv("MINPAKU_API_URL", raising=False)
        monkeypatch.delenv("MINPAKU_BASE_URL", raising=False)
        assert minpaku_extension._check_config() is not None

    def test_check_config_present(self, minpaku_extension, monkeypatch):
        monkeypatch.setenv("MINPAKU_API_URL", "https://test.minpaku.com")
        assert minpaku_extension._check_config() is None
