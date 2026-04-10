"""
Intelligence — document extraction pipeline for save-my-brain.

Uses Claude Vision via Anthropic SDK for structured extraction.
Mirrors the two-phase approach from apps/save-my-brain/backend/services/claude_processor.py:

  Phase A: Classification (Haiku) — doc_type, language, names, currency
  Phase B: Type-specific extraction (Haiku/Sonnet) — structured fields per schema

Uses ANTHROPIC_API_KEY if set, otherwise falls back to docling text extraction.
"""

from __future__ import annotations

import base64
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from . import schemas as S

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


def _image_to_base64(file_bytes: bytes) -> str:
    return base64.standard_b64encode(file_bytes).decode("utf-8")


def _image_content_block(file_bytes: bytes, mime_type: str) -> dict:
    media_type = mime_type if mime_type in (
        "image/jpeg", "image/png", "image/gif", "image/webp"
    ) else "image/jpeg"
    return {
        "type": "image",
        "source": {
            "type": "base64",
            "media_type": media_type,
            "data": _image_to_base64(file_bytes),
        },
    }


# ---------------------------------------------------------------------------
# Phase A — Classify
# ---------------------------------------------------------------------------

def classify_document(file_bytes: bytes, mime_type: str,
                       text_hint: str = "") -> dict:
    """
    Phase A: Use Haiku to classify the doc type + extract names + currency.
    Returns dict with doc_type, detected_names, document_language, currency, etc.
    Falls back to text-only classification if the image can't be processed.
    """
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

    messages: list[dict] = []
    is_image = mime_type.startswith("image/")
    if is_image and file_bytes:
        content = [
            _image_content_block(file_bytes, mime_type),
            {"type": "text", "text": "Classify this document. Detect any person names."},
        ]
        messages = [{"role": "user", "content": content}]
    else:
        messages = [{"role": "user",
                     "content": f"Classify this document:\n\n{text_hint[:3000]}"}]

    try:
        raw = _call_claude(client, S.HAIKU, system, messages, max_tokens=512)
        result = _parse_json(raw)
    except Exception as e:
        log.exception(f"Classification call failed: {e}")
        return _fallback_classification(text_hint)

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
    elif any(kw in text_lower for kw in ("clinic", "doctor", "diagnosis", "醫生")):
        doc_type = "medical"
    return {
        "doc_type": doc_type,
        "detected_names": [],
        "document_language": "en",
        "complexity": "simple",
        "brief_description": "",
        "currency": None,
    }


# ---------------------------------------------------------------------------
# Phase B — Extract structured data
# ---------------------------------------------------------------------------

def extract_structured_data(file_bytes: bytes, mime_type: str, doc_type: str,
                              user_language: str = "en",
                              text_hint: str = "") -> dict:
    """
    Phase B: Extract structured data using the type-specific schema.
    Uses Sonnet for complex types, Haiku for simple types.
    """
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

    is_image = mime_type.startswith("image/")
    if is_image and file_bytes:
        content = [
            _image_content_block(file_bytes, mime_type),
            {"type": "text", "text": "Extract structured information from this document."},
        ]
        messages = [{"role": "user", "content": content}]
    else:
        max_chars = 150_000
        messages = [{"role": "user",
                     "content": f"Document content:\n\n{(text_hint or '')[:max_chars]}"}]

    max_tokens = 8192 if doc_type in ("bank_statement", "credit_card") else 4096

    try:
        raw = _call_claude(client, model, system, messages, max_tokens=max_tokens)
        result = _parse_json(raw)
    except Exception as e:
        log.exception(f"Extraction call failed: {e}")
        return _empty_extraction()

    result.setdefault("summary", "")
    result.setdefault("key_points", [])
    result.setdefault("important_dates", [])
    result.setdefault("red_flags", [])
    result.setdefault("action_items", [])
    return result


def _empty_extraction() -> dict:
    return {
        "summary": "",
        "key_points": [],
        "important_dates": [],
        "red_flags": [],
        "action_items": [],
    }


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def process_document(file_bytes: bytes, filename: str, mime_type: str,
                      user_language: str = "en") -> dict:
    """
    Full pipeline: classify → extract → return structured result.
    Does NOT write to DB — caller handles storage (so duplicate detection
    can happen before this runs).

    Returns a dict with the full extraction result (doc_type, summary,
    key_points, important_dates, red_flags, action_items, transactions,
    policy, medical_record, detected_names, currency, ...)
    """
    if not _has_api_key():
        return {
            "error": "ANTHROPIC_API_KEY not set — cannot use Claude Vision.",
            "doc_type": "other",
            **_empty_extraction(),
        }

    # Phase A: classify
    classification = classify_document(file_bytes, mime_type, text_hint=filename)
    doc_type = classification.get("doc_type", "other")
    log.info(f"Classified as: {doc_type} (names: {classification.get('detected_names', [])})")

    # Phase B: extract
    extraction = extract_structured_data(
        file_bytes, mime_type, doc_type,
        user_language=user_language,
    )

    # Merge classification into extraction
    extraction["doc_type"] = doc_type
    extraction["detected_names"] = classification.get("detected_names", [])
    extraction["document_language"] = classification.get("document_language", "en")
    extraction["currency"] = classification.get("currency")
    extraction["classification"] = classification

    return extraction
