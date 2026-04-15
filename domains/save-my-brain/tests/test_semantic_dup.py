"""Tests for semantic duplicate detection in database.py."""

import importlib.util
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def db_module(tmp_path: Path, monkeypatch):
    """Load extension/database.py pointed at a tmp SQLite path."""
    monkeypatch.setenv("SC_DATA_DIR", str(tmp_path))
    src = Path(__file__).parent.parent / "extension" / "database.py"
    spec = importlib.util.spec_from_file_location("_sc_smb_db", src)
    module = importlib.util.module_from_spec(spec)
    sys.modules["_sc_smb_db"] = module
    spec.loader.exec_module(module)
    # Initialise the schema
    module.init_db().close()
    return module


@pytest.fixture
def cm(tmp_path: Path):
    c = MagicMock()
    c._root = tmp_path
    return c


# ---------------------------------------------------------------------------
# _norm_merchant
# ---------------------------------------------------------------------------

def test_norm_merchant_lowercase(db_module):
    assert db_module._norm_merchant("Starbucks") == "starbucks"


def test_norm_merchant_strips_punctuation(db_module):
    assert db_module._norm_merchant("McDonald's, Inc.") == "mcdonalds inc"


def test_norm_merchant_collapses_whitespace(db_module):
    assert db_module._norm_merchant("  Smile  Dental  ") == "smile  dental"


def test_norm_merchant_empty(db_module):
    assert db_module._norm_merchant("") == ""
    assert db_module._norm_merchant(None) == ""


# ---------------------------------------------------------------------------
# Transaction duplicate detection
# ---------------------------------------------------------------------------

def _seed_transaction(db_module, cm, merchant, date, amount, filename="seed.jpg"):
    doc_id = db_module.insert_document(cm, {
        "filename": filename,
        "file_hash": f"hash-{merchant}-{date}",
        "file_type": "image",
        "doc_type": "receipt",
        "summary": f"{merchant} receipt",
    })
    db_module.insert_transactions(cm, doc_id, [{
        "date": date,
        "amount": amount,
        "merchant": merchant,
        "category": "dental",
    }])
    return doc_id


def test_transaction_exact_match(db_module, cm):
    _seed_transaction(db_module, cm, "Smile Dental", "2026-03-15", 1200.00)
    match = db_module.find_semantic_duplicate_transaction(
        cm, merchant="Smile Dental", date_str="2026-03-15", amount=1200.00,
    )
    assert match is not None
    assert match["merchant"] == "Smile Dental"


def test_transaction_case_insensitive_match(db_module, cm):
    _seed_transaction(db_module, cm, "Smile Dental", "2026-03-15", 1200.00)
    match = db_module.find_semantic_duplicate_transaction(
        cm, merchant="SMILE DENTAL", date_str="2026-03-15", amount=1200.00,
    )
    assert match is not None


def test_transaction_punctuation_match(db_module, cm):
    _seed_transaction(db_module, cm, "McDonald's", "2026-03-15", 85.00)
    match = db_module.find_semantic_duplicate_transaction(
        cm, merchant="McDonalds", date_str="2026-03-15", amount=85.00,
    )
    assert match is not None


def test_transaction_substring_match(db_module, cm):
    _seed_transaction(db_module, cm, "Smile Dental Clinic", "2026-03-15", 1200.00)
    match = db_module.find_semantic_duplicate_transaction(
        cm, merchant="Smile Dental", date_str="2026-03-15", amount=1200.00,
    )
    assert match is not None


def test_transaction_amount_tolerance(db_module, cm):
    _seed_transaction(db_module, cm, "Starbucks", "2026-03-15", 42.50)
    # Within 0.5 tolerance
    match = db_module.find_semantic_duplicate_transaction(
        cm, merchant="Starbucks", date_str="2026-03-15", amount=42.80,
    )
    assert match is not None


def test_transaction_amount_outside_tolerance(db_module, cm):
    _seed_transaction(db_module, cm, "Starbucks", "2026-03-15", 42.50)
    # Outside 0.5 tolerance
    match = db_module.find_semantic_duplicate_transaction(
        cm, merchant="Starbucks", date_str="2026-03-15", amount=45.00,
    )
    assert match is None


def test_transaction_different_date_no_match(db_module, cm):
    _seed_transaction(db_module, cm, "Smile Dental", "2026-03-15", 1200.00)
    match = db_module.find_semantic_duplicate_transaction(
        cm, merchant="Smile Dental", date_str="2026-03-16", amount=1200.00,
    )
    assert match is None


def test_transaction_different_merchant_no_match(db_module, cm):
    _seed_transaction(db_module, cm, "Smile Dental", "2026-03-15", 1200.00)
    match = db_module.find_semantic_duplicate_transaction(
        cm, merchant="Other Clinic", date_str="2026-03-15", amount=1200.00,
    )
    assert match is None


def test_transaction_none_inputs(db_module, cm):
    assert db_module.find_semantic_duplicate_transaction(
        cm, merchant=None, date_str="2026-03-15", amount=100,
    ) is None
    assert db_module.find_semantic_duplicate_transaction(
        cm, merchant="X", date_str=None, amount=100,
    ) is None
    assert db_module.find_semantic_duplicate_transaction(
        cm, merchant="X", date_str="2026-03-15", amount=None,
    ) is None


# ---------------------------------------------------------------------------
# Policy duplicate detection
# ---------------------------------------------------------------------------

def _seed_policy(db_module, cm, insurer, policy_number):
    doc_id = db_module.insert_document(cm, {
        "filename": "policy.pdf",
        "file_hash": f"pol-{policy_number}",
        "file_type": "pdf",
        "doc_type": "insurance",
        "summary": f"{insurer} policy",
    })
    db_module.insert_policy(cm, doc_id, {
        "insurer": insurer,
        "policy_number": policy_number,
        "policy_type": "health",
    })
    return doc_id


def test_policy_exact_match(db_module, cm):
    _seed_policy(db_module, cm, "AIA", "POL-123-456")
    match = db_module.find_semantic_duplicate_policy(
        cm, insurer="AIA", policy_number="POL-123-456",
    )
    assert match is not None
    assert match["policy_number"] == "POL-123-456"


def test_policy_different_insurer_no_match(db_module, cm):
    _seed_policy(db_module, cm, "AIA", "POL-123-456")
    match = db_module.find_semantic_duplicate_policy(
        cm, insurer="Prudential", policy_number="POL-123-456",
    )
    assert match is None


def test_policy_missing_policy_number(db_module, cm):
    _seed_policy(db_module, cm, "AIA", "POL-123-456")
    match = db_module.find_semantic_duplicate_policy(
        cm, insurer="AIA", policy_number=None,
    )
    assert match is None


# ---------------------------------------------------------------------------
# Medical duplicate detection
# ---------------------------------------------------------------------------

def _seed_medical(db_module, cm, doctor, date, provider=None):
    doc_id = db_module.insert_document(cm, {
        "filename": "med.pdf",
        "file_hash": f"med-{doctor}-{date}",
        "file_type": "pdf",
        "doc_type": "medical",
        "summary": f"{doctor} visit",
    })
    db_module.insert_medical(cm, doc_id, {
        "doctor": doctor,
        "date": date,
        "provider": provider,
    })
    return doc_id


def test_medical_doctor_date_match(db_module, cm):
    _seed_medical(db_module, cm, "Dr Wong", "2026-03-15")
    match = db_module.find_semantic_duplicate_medical(
        cm, doctor="Dr Wong", date_str="2026-03-15",
    )
    assert match is not None


def test_medical_provider_date_match(db_module, cm):
    _seed_medical(db_module, cm, None, "2026-03-15", provider="HK Sanatorium")
    match = db_module.find_semantic_duplicate_medical(
        cm, doctor=None, date_str="2026-03-15", provider="HK Sanatorium",
    )
    assert match is not None


def test_medical_no_doctor_or_provider(db_module, cm):
    assert db_module.find_semantic_duplicate_medical(
        cm, doctor=None, date_str="2026-03-15",
    ) is None


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------

def test_dispatcher_receipt_routes_to_transaction(db_module, cm):
    _seed_transaction(db_module, cm, "Smile Dental", "2026-03-15", 1200.00)
    result = db_module.find_semantic_duplicate(cm, "receipt", {
        "transactions": [{
            "merchant": "Smile Dental",
            "date": "2026-03-15",
            "amount": 1200.00,
        }],
    })
    assert result is not None
    assert result["kind"] == "transaction"
    assert result["match"]["merchant"] == "Smile Dental"


def test_dispatcher_insurance_routes_to_policy(db_module, cm):
    _seed_policy(db_module, cm, "AIA", "POL-999")
    result = db_module.find_semantic_duplicate(cm, "insurance", {
        "policy": {"insurer": "AIA", "policy_number": "POL-999"},
    })
    assert result is not None
    assert result["kind"] == "policy"


def test_dispatcher_medical_routes_to_medical(db_module, cm):
    _seed_medical(db_module, cm, "Dr Chan", "2026-03-15")
    result = db_module.find_semantic_duplicate(cm, "medical", {
        "medical_record": {"doctor": "Dr Chan", "date": "2026-03-15"},
    })
    assert result is not None
    assert result["kind"] == "medical"


def test_dispatcher_unknown_doc_type_returns_none(db_module, cm):
    result = db_module.find_semantic_duplicate(cm, "other", {})
    assert result is None


def test_dispatcher_empty_extraction_returns_none(db_module, cm):
    result = db_module.find_semantic_duplicate(cm, "receipt", {"transactions": []})
    assert result is None


def test_dispatcher_no_seed_returns_none(db_module, cm):
    # Empty database
    result = db_module.find_semantic_duplicate(cm, "receipt", {
        "transactions": [{
            "merchant": "Never Seen",
            "date": "2026-03-15",
            "amount": 99.00,
        }],
    })
    assert result is None
