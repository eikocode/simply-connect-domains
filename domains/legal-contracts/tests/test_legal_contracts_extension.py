"""Tests for legal-contracts extension — message handling, staging review, and helpers."""
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def mock_cm(tmp_path: Path):
    """Create a mock ContextManager for testing."""
    (tmp_path / "context").mkdir()
    (tmp_path / "staging").mkdir()
    (tmp_path / "profile.json").write_text(json.dumps({
        "name": "Legal Contracts",
        "context_files": ["contracts", "clause_library", "counterparties", "compliance", "products"],
        "category_map": {
            "contracts": "contracts.md",
            "clause_library": "clause_library.md",
            "counterparties": "counterparties.md",
            "compliance": "compliance.md",
            "products": "products.md",
            "general": "contracts.md"
        },
    }))
    (tmp_path / "AGENT.md").write_text("# Legal Contracts\n")
    
    from simply_connect.context_manager import ContextManager
    return ContextManager(root=tmp_path)


@pytest.fixture
def legal_ext_module():
    """Import legal-contracts extension directly from domains source."""
    legal_contracts_dir = Path("/Users/andrew/backup/work/simply-connect-workspace/simply-connect-domains/domains/legal-contracts")
    ext_dir = legal_contracts_dir / "extension"
    
    if str(legal_contracts_dir) not in sys.path:
        sys.path.insert(0, str(legal_contracts_dir))
    
    import importlib.util
    spec = importlib.util.spec_from_file_location("legal_contracts_tools", ext_dir / "tools.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["legal_contracts_tools"] = mod
    spec.loader.exec_module(mod)
    
    return mod


class TestLegalContractsRoleDetection:
    def test_is_operator_role_returns_true_for_operator(self, legal_ext_module):
        assert legal_ext_module._is_operator_role("operator") is True

    def test_is_operator_role_returns_true_for_admin(self, legal_ext_module):
        assert legal_ext_module._is_operator_role("admin") is True

    def test_is_operator_role_returns_false_for_counsel(self, legal_ext_module):
        assert legal_ext_module._is_operator_role("counsel") is False

    def test_is_operator_role_returns_false_for_reviewer(self, legal_ext_module):
        assert legal_ext_module._is_operator_role("reviewer") is False


class TestLegalContractsClausePatterns:
    def test_detects_uncapped_liability_pattern(self, legal_ext_module):
        result = legal_ext_module._parse_clause_pattern("Supplier shall have uncapped liability for all damages")
        assert result is not None
        assert result["category"] == "liability"
        assert result["label"] == "Uncapped Liability"

    def test_detects_unlimited_liability_pattern(self, legal_ext_module):
        result = legal_ext_module._parse_clause_pattern("Parties agree to unlimited liability under this agreement")
        assert result is not None
        assert result["category"] == "liability"

    def test_detects_perpetual_term_pattern(self, legal_ext_module):
        result = legal_ext_module._parse_clause_pattern("This agreement shall have a perpetual term")
        assert result is not None
        assert result["category"] == "termination"
        assert result["label"] == "Perpetual Term"

    def test_detects_joint_ownership_pattern(self, legal_ext_module):
        result = legal_ext_module._parse_clause_pattern("The parties shall have joint ownership of all IP")
        assert result is not None
        assert result["category"] == "ip"
        assert result["label"] == "Joint Ownership"

    def test_returns_none_for_clean_clause(self, legal_ext_module):
        result = legal_ext_module._parse_clause_pattern("Standard payment terms apply")
        assert result is None


class TestLegalContractsRiskCategories:
    def test_extracts_liability_category(self, legal_ext_module):
        categories = legal_ext_module._extract_risk_categories("This clause relates to liability and indemnification")
        assert "liability" in categories

    def test_extracts_ip_category(self, legal_ext_module):
        categories = legal_ext_module._extract_risk_categories("The IP ownership and invention provisions apply")
        assert "ip" in categories

    def test_extracts_data_category(self, legal_ext_module):
        categories = legal_ext_module._extract_risk_categories("Data privacy and GDPR compliance is required")
        assert "data" in categories


class TestLegalContractsContractReference:
    def test_parses_contract_id_format(self, legal_ext_module):
        result = legal_ext_module._parse_contract_reference("Review HSA-2026-001-HK for liability issues")
        assert result["type"] == "contract_id"
        assert "HSA" in result["value"]

    def test_parses_contract_type_hardware(self, legal_ext_module):
        result = legal_ext_module._parse_contract_reference("Review hardware supplier agreement")
        assert result["type"] == "contract_type"
        assert result["value"] == "hardware supplier"

    def test_parses_contract_type_ip_license(self, legal_ext_module):
        result = legal_ext_module._parse_contract_reference("Check the IP license agreement")
        assert result["type"] == "contract_type"
        assert result["value"] == "ip license"

    def test_returns_empty_for_unrecognized(self, legal_ext_module):
        result = legal_ext_module._parse_contract_reference("Hello world")
        assert result == {}


class TestLegalContractsMaybeHandleMessage:
    def test_returns_none_for_non_operator_role(self, mock_cm, legal_ext_module):
        result = legal_ext_module.maybe_handle_message("show contracts", mock_cm, role_name="counsel")
        assert result is None

    def test_returns_none_for_empty_message(self, mock_cm, legal_ext_module):
        result = legal_ext_module.maybe_handle_message("", mock_cm, role_name="operator")
        assert result is None

    def test_handles_risk_check_query(self, mock_cm, legal_ext_module):
        result = legal_ext_module.maybe_handle_message("check for high risk clauses in HSA-2026-001", mock_cm, role_name="operator")
        assert result is not None
        assert "risk" in result.lower()

    def test_handles_show_contracts_query(self, mock_cm, legal_ext_module):
        mock_cm._committed = {"contracts": "## Active Contracts\n- HSA-2026-001\n"}
        result = legal_ext_module.maybe_handle_message("show active contracts", mock_cm, role_name="operator")
        assert result is not None

    def test_handles_clause_library_query(self, mock_cm, legal_ext_module):
        mock_cm._committed = {"clause_library": "### Approved\n- IP Assignment"}
        result = legal_ext_module.maybe_handle_message("show clause library", mock_cm, role_name="operator")
        assert result is not None


class TestLegalContractsStagingReview:
    def test_returns_none_for_non_contract_category(self, mock_cm, legal_ext_module):
        entry = {"content": "Random content", "category": "general"}
        result = legal_ext_module.review_staging_entry(mock_cm, entry)
        assert result is None

    def test_defers_on_flagged_pattern(self, mock_cm, legal_ext_module):
        entry = {
            "content": "Supplier shall have uncapped liability for all damages",
            "category": "contracts"
        }
        result = legal_ext_module.review_staging_entry(mock_cm, entry)
        assert result is not None
        assert result["recommendation"] == "defer"
        assert result["conflicts"]

    def test_defers_on_gdpr_violation(self, mock_cm, legal_ext_module):
        entry = {
            "content": "In case of a data breach, Supplier must notify Buyer within 72 hours",
            "category": "compliance"
        }
        result = legal_ext_module.review_staging_entry(mock_cm, entry)
        assert result is not None
        assert result["recommendation"] == "defer"
        assert any("24" in c or "notification" in c.lower() for c in result["conflicts"])


class TestLegalContractsOnStagingApproved:
    def test_updates_contracts_on_contract_category(self, mock_cm, legal_ext_module):
        mock_cm._committed = {"contracts": "# Contracts\n"}
        
        entry = {
            "content": "Contract HSA-2026-001 status updated",
            "category": "contracts",
            "captured": "2026-03-29T10:00:00"
        }
        result = legal_ext_module.on_staging_approved(mock_cm, entry)
        assert result is not None
        assert result.get("ok") is True