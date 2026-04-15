"""Tests for the EYES text extraction layer (Docling + PyMuPDF)."""

import importlib.util
import sys
from pathlib import Path

import pytest


@pytest.fixture
def eyes_module():
    """Load extension/eyes.py in isolation."""
    src = Path(__file__).parent.parent / "extension" / "eyes.py"
    spec = importlib.util.spec_from_file_location("_sc_smb_eyes", src)
    module = importlib.util.module_from_spec(spec)
    sys.modules["_sc_smb_eyes"] = module
    spec.loader.exec_module(module)
    return module


# ---------------------------------------------------------------------------
# EyesResult dataclass
# ---------------------------------------------------------------------------

def test_eyes_result_defaults(eyes_module):
    r = eyes_module.EyesResult()
    assert r.text == ""
    assert r.page_count is None
    assert r.is_scanned is False
    assert r.method == ""


def test_has_enough_text_empty(eyes_module):
    r = eyes_module.EyesResult(text="")
    assert eyes_module.has_enough_text(r) is False


def test_has_enough_text_too_short(eyes_module):
    r = eyes_module.EyesResult(text="hi")
    assert eyes_module.has_enough_text(r) is False


def test_has_enough_text_enough(eyes_module):
    r = eyes_module.EyesResult(text="a" * 200)
    assert eyes_module.has_enough_text(r) is True


def test_has_enough_text_threshold_boundary(eyes_module):
    # At threshold (100 chars stripped) should be True
    r = eyes_module.EyesResult(text="x" * 100)
    assert eyes_module.has_enough_text(r) is True
    r2 = eyes_module.EyesResult(text="x" * 99)
    assert eyes_module.has_enough_text(r2) is False


# ---------------------------------------------------------------------------
# Plain-text path (no PDF, no image)
# ---------------------------------------------------------------------------

def test_extract_plain_text(eyes_module):
    content = b"This is just a plain text file with enough characters to count." * 3
    r = eyes_module.extract_text(content, "text/plain", "notes.txt")
    assert r.method == "plain"
    assert "plain text file" in r.text
    assert r.is_scanned is False


def test_extract_empty_bytes(eyes_module):
    r = eyes_module.extract_text(b"", "text/plain", "empty.txt")
    assert r.method == "failed"
    assert r.text == ""


# ---------------------------------------------------------------------------
# PDF path (requires PyMuPDF, which is a hard dep of the extension)
# ---------------------------------------------------------------------------

def _make_text_pdf() -> bytes:
    """Create a simple 1-page PDF with known text."""
    try:
        import fitz
    except ImportError:
        pytest.skip("PyMuPDF not available")
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Dental receipt Smile Clinic")
    page.insert_text((72, 100), "Date 2026-03-15 Amount HKD 1200.00")
    page.insert_text((72, 130), "Patient Ada Service Cleaning plus Xray")
    data = doc.tobytes()
    doc.close()
    return data


def test_extract_pdf_text_mode(eyes_module):
    pdf = _make_text_pdf()
    r = eyes_module.extract_text(pdf, "application/pdf", "receipt.pdf")
    assert r.method == "pymupdf"
    assert r.page_count == 1
    assert r.is_scanned is False
    assert "Dental" in r.text
    assert "Smile" in r.text
    assert "1200" in r.text


def test_extract_pdf_filename_fallback(eyes_module):
    """mime_type may be octet-stream, but .pdf extension triggers PDF path."""
    pdf = _make_text_pdf()
    r = eyes_module.extract_text(pdf, "application/octet-stream", "receipt.pdf")
    assert r.method == "pymupdf"
    assert "Dental" in r.text


def test_extract_pdf_scanned_flag_when_too_short(eyes_module):
    """A PDF with no text should end up with is_scanned=True."""
    try:
        import fitz
    except ImportError:
        pytest.skip("PyMuPDF not available")
    doc = fitz.open()
    doc.new_page()  # blank page, no text
    pdf = doc.tobytes()
    doc.close()
    r = eyes_module.extract_text(pdf, "application/pdf", "blank.pdf")
    # PyMuPDF returns empty, Docling is not installed → stays empty
    assert r.is_scanned is True
    assert len(r.text.strip()) < eyes_module.MIN_TEXT_LENGTH


# ---------------------------------------------------------------------------
# Image path — Docling not installed in this env, so expect graceful fallback
# ---------------------------------------------------------------------------

def test_extract_image_graceful_fallback(eyes_module):
    """Without Docling, image extraction returns empty text but doesn't crash."""
    fake_png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
    r = eyes_module.extract_text(fake_png, "image/png", "photo.png")
    # Should not raise. is_scanned is True because no text.
    assert r.method == "docling"  # method attempted
    assert r.is_scanned is True
