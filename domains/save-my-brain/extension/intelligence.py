"""
Intelligence — hybrid document extraction pipeline for save-my-brain.

Strategy (cheapest path first):

  1. EYES: Docling / PyMuPDF extracts raw text from the file (local, free)
  2. If text is substantial (>100 chars) → Claude TEXT mode (cheap)
  3. If text is empty/short → Claude VISION mode (expensive fallback)

Two-phase Claude analysis, same as apps/save-my-brain/backend/services/claude_processor.py:

  Phase A: Classification (Haiku) — doc_type, language, names, currency
  Phase B: Type-specific extraction (Haiku/Sonnet) — structured fields per schema

This cuts cost by ~20× for text-heavy documents (receipts, statements, contracts)
while still handling pure-image cases via Vision fallback.
"""

from __future__ import annotations

import base64
import json
import logging
import os
from datetime import datetime
from typing import Any

from . import schemas as S
from . import eyes

log = logging.getLogger(__name__)


def _has_api_key() -> bool:
    return bool(os.getenv("ANTHROPIC_API_KEY", "").strip())


def _claude_client():
    import anthropic
    return anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))


def _call_claude(client, model: str, system: str, messages: list[dict],
                 max_tokens: int = 4096) -> str:
    response = client.messages.create(
        model=model, max_tokens=max_tokens, system=system, messages=messages,
    )
    return response.content[0].text


def _parse_json(raw: str) -> dict:
    """Parse Claude's JSON reply, stripping markdown fences."""
    try:
        clean = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
        return json.loads(clean)
    except json.JSONDecodeError:
        log.warning(f"Could not parse Claude JSON. Raw: {raw[:300]}")
        return {}


def _image_content_block(file_bytes: bytes, mime_type: str) -> dict:
    media_type = mime_type if mime_type in (
        "image/jpeg", "image/png", "image/gif", "image/webp"
    ) else "image/jpeg"
    return {
        "type": "image",
        "source": {
            "type": "base64",
            "media_type": media_type,
            "data": base64.standard_b64encode(file_bytes).decode("utf-8"),
        },
    }


# ---------------------------------------------------------------------------
# Phase A — Classify
# ---------------------------------------------------------------------------

def classify_text(text: str) -> dict:
    """Cheap path: classify from extracted text (Haiku, text only)."""
    today = datetime.utcnow().strftime("%Y-%m-%d")
    system = f"""You are a document classifier for Save My Brain AI.
Today's date is {today}.
Classify this document and detect any person names mentioned.
Return ONLY this JSON:
{S.CLASSIFY_SCHEMA}"""

    try:
        client = _claude_client()
    except Exception as e:
        log.warning(f"Could not init Claude client: {e}")
        return _fallback_classification(text)

    messages = [{"role": "user",
                 "content": f"Classify this document:\n\n{text[:3000]}"}]

    try:
        raw = _call_claude(client, S.HAIKU, system, messages, max_tokens=512)
        result = _parse_json(raw)
    except Exception as e:
        log.exception(f"Classification call failed: {e}")
        return _fallback_classification(text)

    return _fill_classification_defaults(result)


def classify_image(file_bytes: bytes, mime_type: str, text_hint: str = "") -> dict:
    """Expensive fallback: classify from the raw image (Claude Vision)."""
    today = datetime.utcnow().strftime("%Y-%m-%d")
    system = f"""You are a document classifier for Save My Brain AI.
Today's date is {today}.
Classify this document and detect any person names mentioned.
Return ONLY this JSON:
{S.CLASSIFY_SCHEMA}"""

    try:
        client = _claude_client()
    except Exception as e:
        log.warning(f"Could not init Claude client: {e}")
        return _fallback_classification(text_hint)

    content = [
        _image_content_block(file_bytes, mime_type),
        {"type": "text", "text": "Classify this document image. Detect any person names."},
    ]
    messages = [{"role": "user", "content": content}]

    try:
        raw = _call_claude(client, S.HAIKU, system, messages, max_tokens=512)
        result = _parse_json(raw)
    except Exception as e:
        log.exception(f"Vision classification failed: {e}")
        return _fallback_classification(text_hint)

    return _fill_classification_defaults(result)


def _fill_classification_defaults(result: dict) -> dict:
    result.setdefault("doc_type", "other")
    result.setdefault("detected_names", [])
    result.setdefault("document_language", "en")
    result.setdefault("complexity", "simple")
    result.setdefault("brief_description", "")
    result.setdefault("currency", None)
    return result


def _fallback_classification(text: str) -> dict:
    """Minimal classification when Claude API is not available."""
    text_lower = (text or "").lower()
    doc_type = "other"
    if any(kw in text_lower for kw in ("receipt", "收據", "total", "subtotal")):
        doc_type = "receipt"
    elif any(kw in text_lower for kw in ("insurance", "policy", "premium", "保單")):
        doc_type = "insurance"
    elif any(kw in text_lower for kw in ("statement", "balance", "帳戶")):
        doc_type = "bank_statement"
    elif any(kw in text_lower for kw in ("clinic", "doctor", "diagnosis", "醫生", "dental")):
        doc_type = "medical"
    return _fill_classification_defaults({"doc_type": doc_type})


# ---------------------------------------------------------------------------
# Phase B — Extract structured data
# ---------------------------------------------------------------------------

def extract_text_mode(text: str, doc_type: str, user_language: str = "en") -> dict:
    """Cheap path: extract from text (Claude Haiku/Sonnet text mode)."""
    today = datetime.utcnow().strftime("%Y-%m-%d")
    schema = S.EXTRACTION_SCHEMAS.get(doc_type, S.DEFAULT_EXTRACTION_SCHEMA)
    model = S.SONNET if doc_type in S.COMPLEX_DOC_TYPES else S.HAIKU

    lang_instruction = {
        "en":    "Write summary, key_points, and action_items in English.",
        "zh-tw": "請以繁體中文撰寫 summary、key_points 和 action_items。",
        "ja":    "summary、key_points、action_items は日本語で記述してください。",
    }.get(user_language, "Write in English.")

    system = f"""You are a document intelligence AI for Save My Brain AI.
Today's date is {today}.
{lang_instruction}

This document has been classified as: {doc_type}

Extract structured information. Return ONLY this JSON (no markdown, no explanation):
{schema}

IMPORTANT DATES — calculate days_until from today ({today}). Use -1 if past date."""

    try:
        client = _claude_client()
    except Exception:
        return _empty_extraction()

    max_chars = 150_000
    messages = [{"role": "user",
                 "content": f"Document content:\n\n{(text or '')[:max_chars]}"}]
    max_tokens = 8192 if doc_type in ("bank_statement", "credit_card") else 4096

    try:
        raw = _call_claude(client, model, system, messages, max_tokens=max_tokens)
        result = _parse_json(raw)
    except Exception as e:
        log.exception(f"Text extraction call failed: {e}")
        return _empty_extraction()

    return _fill_extraction_defaults(result)


def extract_vision_mode(file_bytes: bytes, mime_type: str, doc_type: str,
                        user_language: str = "en") -> dict:
    """Expensive fallback: extract from the raw image (Claude Vision)."""
    today = datetime.utcnow().strftime("%Y-%m-%d")
    schema = S.EXTRACTION_SCHEMAS.get(doc_type, S.DEFAULT_EXTRACTION_SCHEMA)
    model = S.SONNET if doc_type in S.COMPLEX_DOC_TYPES else S.HAIKU

    lang_instruction = {
        "en":    "Write summary, key_points, and action_items in English.",
        "zh-tw": "請以繁體中文撰寫 summary、key_points 和 action_items。",
        "ja":    "summary、key_points、action_items は日本語で記述してください。",
    }.get(user_language, "Write in English.")

    system = f"""You are a document intelligence AI for Save My Brain AI.
Today's date is {today}.
{lang_instruction}

This document has been classified as: {doc_type}

Extract structured information. Return ONLY this JSON (no markdown, no explanation):
{schema}

IMPORTANT DATES — calculate days_until from today ({today}). Use -1 if past date."""

    try:
        client = _claude_client()
    except Exception:
        return _empty_extraction()

    content = [
        _image_content_block(file_bytes, mime_type),
        {"type": "text", "text": "Extract structured information from this document."},
    ]
    messages = [{"role": "user", "content": content}]
    max_tokens = 8192 if doc_type in ("bank_statement", "credit_card") else 4096

    try:
        raw = _call_claude(client, model, system, messages, max_tokens=max_tokens)
        result = _parse_json(raw)
    except Exception as e:
        log.exception(f"Vision extraction failed: {e}")
        return _empty_extraction()

    return _fill_extraction_defaults(result)


def _fill_extraction_defaults(result: dict) -> dict:
    result.setdefault("summary", "")
    result.setdefault("key_points", [])
    result.setdefault("important_dates", [])
    result.setdefault("red_flags", [])
    result.setdefault("action_items", [])
    return result


def _empty_extraction() -> dict:
    return _fill_extraction_defaults({})


# ---------------------------------------------------------------------------
# Main pipeline — hybrid text-first, vision fallback
# ---------------------------------------------------------------------------

def process_document(file_bytes: bytes, filename: str, mime_type: str,
                      user_language: str = "en") -> dict:
    """
    Full hybrid pipeline:
      1. EYES extracts text via Docling/PyMuPDF (local, free)
      2. If text is substantial → Claude text mode (~20× cheaper than vision)
      3. Otherwise → Claude vision fallback
      4. Two-phase analysis (classify → extract structured data)

    Returns a dict with:
      doc_type, summary, key_points, important_dates, red_flags, action_items,
      transactions, policy/medical_record, detected_names, currency, classification,
      extracted_text, _extraction_method (for debugging)
    """
    if not _has_api_key():
        return {
            "error": "ANTHROPIC_API_KEY not set — cannot run intelligence pipeline.",
            "doc_type": "other",
            **_empty_extraction(),
        }

    # Step 1: Extract text via EYES
    eyes_result = eyes.extract_text(file_bytes, mime_type, filename)
    log.info(
        f"EYES: method={eyes_result.method} "
        f"text_len={len(eyes_result.text)} "
        f"scanned={eyes_result.is_scanned}"
    )

    use_text_mode = eyes.has_enough_text(eyes_result)
    extraction_method = "text" if use_text_mode else "vision"

    # Step 2: Classify
    if use_text_mode:
        classification = classify_text(eyes_result.text)
    else:
        classification = classify_image(file_bytes, mime_type, text_hint=filename)
    doc_type = classification.get("doc_type", "other")
    log.info(f"Classified as: {doc_type} (method={extraction_method})")

    # Step 3: Extract structured data
    if use_text_mode:
        extraction = extract_text_mode(eyes_result.text, doc_type, user_language)
    else:
        extraction = extract_vision_mode(file_bytes, mime_type, doc_type, user_language)

    # Merge classification into extraction
    extraction["doc_type"] = doc_type
    extraction["detected_names"] = classification.get("detected_names", [])
    extraction["document_language"] = classification.get("document_language", "en")
    extraction["currency"] = classification.get("currency")
    extraction["classification"] = classification
    extraction["extracted_text"] = eyes_result.text
    extraction["_extraction_method"] = extraction_method
    extraction["_eyes_method"] = eyes_result.method

    return extraction
