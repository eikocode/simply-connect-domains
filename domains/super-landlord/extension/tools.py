"""
Super-Landlord extension tools.

This deployment only prepares Minpaku availability handoffs.
Listing-specific publish/update/unlist actions belong to the Minpaku deployment.
"""

from __future__ import annotations

import json
import os
import re

from .client import SuperLandlordMinpakuClient

TOOLS = [
    {
        "name": "prepare_minpaku_handoff",
        "description": (
            "Prepare and stage a Minpaku availability handoff for a landlord property. "
            "Use this when the landlord wants to make a property available or unavailable for Minpaku. "
            "Do not use this for listing title, pricing, max guests, or guest-facing rules."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "source_property_ref": {
                    "type": "string",
                    "description": "The landlord-side property or unit reference.",
                },
                "availability": {
                    "type": "string",
                    "enum": ["available", "unavailable"],
                    "description": "Whether the property should be available to Minpaku.",
                },
                "landlord_note": {
                    "type": "string",
                    "description": "Optional landlord note or restriction for the Minpaku operator.",
                },
            },
            "required": ["source_property_ref"],
        },
    }
]


def _parse_handoff(content: str) -> dict[str, str | None]:
    heading = re.search(r"^## Minpaku Handoff — (.+)$", content, re.MULTILINE)
    availability = re.search(r"^- Availability:\s*(.+)$", content, re.MULTILINE)
    landlord_note = re.search(r"^- Landlord note:\s*(.+)$", content, re.MULTILINE)
    remote_property_id = re.search(r"^- Remote property ID:\s*(.+)$", content, re.MULTILINE)
    remote_host_id = re.search(r"^- Remote host ID:\s*(.+)$", content, re.MULTILINE)
    sync_status = re.search(r"^- Sync status:\s*(.+)$", content, re.MULTILINE)
    return {
        "source_property_ref": heading.group(1).strip() if heading else None,
        "availability": availability.group(1).strip().lower() if availability else None,
        "landlord_note": landlord_note.group(1).strip() if landlord_note else None,
        "remote_property_id": remote_property_id.group(1).strip() if remote_property_id else None,
        "remote_host_id": remote_host_id.group(1).strip() if remote_host_id else None,
        "sync_status": sync_status.group(1).strip() if sync_status else None,
    }


def _extract_property_details(properties_markdown: str, source_property_ref: str) -> str | None:
    if not properties_markdown.strip():
        return None
    sections = re.split(r"(?=^## )", properties_markdown, flags=re.MULTILINE)
    for section in sections:
        if not section.strip().startswith("## "):
            continue
        title = section.splitlines()[0][3:].strip()
        if title == source_property_ref:
            return section.strip()
    return None


def _iter_property_sections(markdown: str) -> list[str]:
    parts = re.split(r"(?=^##\s+)", markdown, flags=re.MULTILINE)
    return [part.strip() for part in parts if part.strip().startswith("## ")]


def _rewrite_committed_properties(cm, new_sections: list[str]) -> None:
    target_path = cm._root / "context" / "properties.md"
    body = "# Properties"
    if new_sections:
        body += "\n\n" + "\n\n".join(section.strip() for section in new_sections)
    body += "\n"
    target_path.write_text(body, encoding="utf-8")


def _normalize_property_ref(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def _list_property_titles(cm) -> list[str]:
    titles = []
    for section in _iter_property_sections(cm.load_committed().get("properties", "")):
        if _parse_property_removal_request(section).get("is_removal") == "yes":
            continue
        titles.append(section.splitlines()[0].replace("##", "").strip())
    return titles


def _resolve_property_reference(cm, raw_ref: str) -> dict[str, str | list[str] | None]:
    query = raw_ref.strip()
    if not query:
        return {"status": "none", "resolved": None, "matches": []}

    titles = _list_property_titles(cm)
    normalized_query = _normalize_property_ref(query)

    exact_matches = [title for title in titles if _normalize_property_ref(title) == normalized_query]
    if len(exact_matches) == 1:
        return {"status": "exact", "resolved": exact_matches[0], "matches": exact_matches}
    if len(exact_matches) > 1:
        return {"status": "ambiguous", "resolved": None, "matches": exact_matches}

    partial_matches = []
    for title in titles:
        normalized_title = _normalize_property_ref(title)
        if normalized_query and (normalized_query in normalized_title or normalized_title.startswith(normalized_query)):
            partial_matches.append(title)

    unique_partial_matches = list(dict.fromkeys(partial_matches))
    if len(unique_partial_matches) == 1:
        return {"status": "unique_partial", "resolved": unique_partial_matches[0], "matches": unique_partial_matches}
    if len(unique_partial_matches) > 1:
        return {"status": "ambiguous", "resolved": None, "matches": unique_partial_matches}
    return {"status": "none", "resolved": None, "matches": []}


def _extract_property_field(section: str, label: str) -> str | None:
    match = re.search(rf"^- {re.escape(label)}:\s*(.+)$", section, re.MULTILINE)
    return match.group(1).strip() if match else None


def _parse_property_candidate_blob(blob: str) -> dict[str, str] | None:
    full_address = None
    unit = None
    building = None

    full_match = re.search(r"(?:Full service address|Service address|Address):\s*`?(.+?)`?$", blob, re.MULTILINE)
    if full_match:
        full_address = full_match.group(1).strip()

    unit_match = re.search(r"(?:Unit):\s*`?(.+?)`?$", blob, re.MULTILINE)
    if unit_match:
        unit = unit_match.group(1).strip()

    building_match = re.search(r"(?:Building):\s*`?(.+?)`?$", blob, re.MULTILINE)
    if building_match:
        building = building_match.group(1).strip()

    if not full_address:
        summary_match = re.search(r"bill\s*\((.+?)\)", blob, re.IGNORECASE)
        if summary_match:
            full_address = summary_match.group(1).strip()
        else:
            summary_match = re.search(r"\bfor\s+(.+?)(?:\s+-\s+|, billing period|$)", blob, re.IGNORECASE)
            if summary_match:
                full_address = summary_match.group(1).strip()

    if not unit and full_address:
        unit_building_match = re.match(r"^(Flat[^,]*,\s*[^,]*?(?:,\s*Tower\s*\d+)?)(?:,\s*(.+))?$", full_address, re.IGNORECASE)
        if unit_building_match:
            unit = unit_building_match.group(1).strip()
            if unit_building_match.group(2):
                building = unit_building_match.group(2).split(",")[0].strip()
        else:
            unit_building_match = re.match(r"^(Flat\s+.+?Tower\s*\d+)\s+(.+)$", full_address, re.IGNORECASE)
            if unit_building_match:
                unit = unit_building_match.group(1).strip()
                building = unit_building_match.group(2).split(",")[0].strip()

    if not full_address and unit and building:
        full_address = f"{unit}, {building}"

    if not building and full_address:
        comma_parts = [part.strip() for part in full_address.split(",") if part.strip()]
        if len(comma_parts) >= 2:
            building = comma_parts[min(2, len(comma_parts) - 1)]

    if not full_address:
        return None

    property_ref = full_address
    if unit and building:
        property_ref = f"{unit}, {building}"
    elif building:
        property_ref = building

    return {
        "property_ref": property_ref,
        "unit": unit or "(not parsed)",
        "building": building or "(not parsed)",
        "full_address": full_address,
    }


def _extract_property_candidate_from_history_or_staging(cm, history: list[dict] | None) -> dict[str, str] | None:
    if history:
        for turn in reversed(history):
            if turn.get("role") != "assistant":
                continue
            blob = str(turn.get("content") or "")
            if "Extracted property from the utility bill" in blob or "Extracted bill summary" in blob:
                candidate = _parse_property_candidate_blob(blob)
                if candidate:
                    return candidate

    for entry in reversed(cm.list_staging(status="unconfirmed")):
        if entry.get("category") != "utilities":
            continue
        blob = f"{entry.get('summary', '')}\n{entry.get('content', '')}"
        candidate = _parse_property_candidate_blob(blob)
        if candidate:
            return candidate
    return None


def _extract_property_candidate_from_entries(cm, entry_ids: list[str]) -> dict[str, str] | None:
    for entry_id in reversed(entry_ids):
        entry = cm.get_staging_entry(entry_id)
        if not entry or entry.get("category") != "utilities":
            continue
        blob = f"{entry.get('summary', '')}\n{entry.get('content', '')}"
        candidate = _parse_property_candidate_blob(blob)
        if candidate:
            return candidate
    return None


def _has_existing_property_candidate(cm, candidate: dict[str, str]) -> bool:
    property_ref = candidate.get("property_ref", "").strip()
    full_address = candidate.get("full_address", "").strip()
    normalized_refs = {_normalize_property_ref(property_ref), _normalize_property_ref(full_address)}
    normalized_refs.discard("")

    for title in _list_property_titles(cm):
        if _normalize_property_ref(title) in normalized_refs:
            return True

    for item in _find_pending_property_staging(cm):
        if _normalize_property_ref(item.get("title", "")) in normalized_refs:
            return True
        if _normalize_property_ref(item.get("full_address", "")) in normalized_refs:
            return True

    return False


def _stage_property_candidate(cm, candidate: dict[str, str]) -> dict[str, str]:
    summary = f"Property record for {candidate['property_ref']}"
    content = "\n".join(
        [
            f"## {candidate['property_ref']}",
            "- Source: utility bill extraction",
            f"- Unit: {candidate['unit']}",
            f"- Building: {candidate['building']}",
            f"- Full service address: {candidate['full_address']}",
        ]
    )
    entry_id = cm.create_staging_entry(
        summary=summary,
        content=content,
        category="properties",
        source="operator",
    )
    return {"entry_id": entry_id, **candidate}


def on_ingest_to_staging(cm, filepath, result: dict) -> dict | None:
    entries = result.get("entries", [])
    utility_entry_ids = [str(item.get("entry_id") or "") for item in entries if item.get("category") == "utilities"]
    if not utility_entry_ids:
        return None

    candidate = _extract_property_candidate_from_entries(cm, utility_entry_ids)
    if not candidate or _has_existing_property_candidate(cm, candidate):
        return None

    staged_property = _stage_property_candidate(cm, candidate)
    property_entry = {
        "entry_id": staged_property["entry_id"],
        "summary": f"Property record for {staged_property['property_ref']}",
        "category": "properties",
    }
    result.setdefault("entries", []).append(property_entry)
    return {
        "ok": True,
        "message": (
            f"Also staged a property candidate for {staged_property['property_ref']} from the utility bill."
        ),
        "property_ref": staged_property["property_ref"],
        "entry_id": staged_property["entry_id"],
    }


def _find_pending_property_staging(cm) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for entry in cm.list_staging(status="unconfirmed"):
        if entry.get("category") != "properties":
            continue
        content = entry.get("content", "")
        if _parse_property_removal_request(content).get("is_removal") == "yes":
            continue
        title_match = re.search(r"^##\s+(.+)$", content, re.MULTILINE)
        rows.append(
            {
                "entry_id": str(entry.get("id") or ""),
                "title": title_match.group(1).strip() if title_match else entry.get("summary", "(pending property)"),
                "unit": _extract_property_field(content, "Unit") or "(not parsed)",
                "building": _extract_property_field(content, "Building") or "(not parsed)",
                "full_address": _extract_property_field(content, "Full service address") or "(not parsed)",
            }
        )
    return rows


def _parse_property_removal_request(content: str) -> dict[str, str | None]:
    heading = re.search(r"^##\s+Property Removal Request$", content, re.MULTILINE)
    target = re.search(r"- Property:\s*`?(.+?)`?$", content, re.MULTILINE)
    full_address = re.search(r"- Full service address:\s*`?(.+?)`?$", content, re.MULTILINE)
    return {
        "is_removal": "yes" if heading else None,
        "property_ref": target.group(1).strip() if target else None,
        "full_address": full_address.group(1).strip() if full_address else None,
    }


def _apply_approved_property_removal(cm, property_ref: str) -> bool:
    properties_markdown = cm.load_committed().get("properties", "")
    sections = _iter_property_sections(properties_markdown)
    kept_sections: list[str] = []
    changed = False
    for section in sections:
        title = section.splitlines()[0].replace("##", "").strip()
        parsed_removal = _parse_property_removal_request(section)
        if parsed_removal.get("is_removal") == "yes":
            changed = True
            continue
        if _property_matches_removal_target(title, property_ref):
            changed = True
            continue
        kept_sections.append(section)
    if changed:
        _rewrite_committed_properties(cm, kept_sections)
    return changed


def _find_pending_property_removals(cm) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for entry in cm.list_staging(status="unconfirmed"):
        if entry.get("category") != "properties":
            continue
        parsed = _parse_property_removal_request(entry.get("content", ""))
        if parsed.get("is_removal") != "yes" or not parsed.get("property_ref"):
            continue
        rows.append(
            {
                "entry_id": str(entry.get("id") or ""),
                "property_ref": str(parsed.get("property_ref") or ""),
                "full_address": str(parsed.get("full_address") or ""),
            }
        )
    return rows


def _find_matching_pending_property_removal(cm, raw_ref: str) -> dict[str, str] | None:
    query = raw_ref.strip()
    if not query:
        return None

    normalized_query = _normalize_property_ref(query)
    exact: list[dict[str, str]] = []
    partial: list[dict[str, str]] = []

    for item in _find_pending_property_removals(cm):
        target = item.get("property_ref", "")
        normalized_target = _normalize_property_ref(target)
        if not normalized_target:
            continue
        if normalized_target == normalized_query:
            exact.append(item)
            continue
        if normalized_query and (
            normalized_query in normalized_target or normalized_target.startswith(normalized_query)
        ):
            partial.append(item)

    if len(exact) == 1:
        return exact[0]
    if len(exact) > 1:
        return None
    if len(partial) == 1:
        return partial[0]
    return None


def _stage_property_removal(cm, property_ref: str) -> dict[str, str]:
    content = "\n".join(
        [
            "## Property Removal Request",
            "",
            f"- Property: {property_ref}",
            f"- Full service address: {property_ref}",
            "",
            "This property should be removed from the operator working set immediately.",
            "Framework approval is still required before the committed property registry is updated.",
        ]
    )
    entry_id = cm.create_staging_entry(
        summary=f"Remove property {property_ref}",
        content=content,
        category="properties",
        source="operator",
    )
    return {"entry_id": entry_id, "property_ref": property_ref}


def _property_matches_removal_target(committed_title: str, removal_target: str) -> bool:
    committed = committed_title.strip().lower()
    target = removal_target.strip().lower()
    return committed == target or committed.startswith(target + ",") or target in committed


def _reply_all_properties(cm) -> str:
    committed_sections = _iter_property_sections(cm.load_committed().get("properties", ""))
    staged_properties = _find_pending_property_staging(cm)
    staged_removals = _find_pending_property_removals(cm)

    lines = []
    visible_committed_sections = _visible_committed_property_titles(cm)
    visible_committed_norms = {_normalize_property_ref(title) for title in visible_committed_sections}
    active_staged_properties = [
        item
        for item in staged_properties
        if _normalize_property_ref(item["title"]) not in visible_committed_norms
    ]

    if visible_committed_sections or active_staged_properties:
        lines.append("Active properties in the operator working set:")
        for title in visible_committed_sections:
            lines.append(f"- `{title}`")
        for item in active_staged_properties:
            lines.append(f"- `{item['title']}` *(pending framework approval)*")
    else:
        if committed_sections and staged_removals:
            lines.append("There are currently no active properties in the operator working set.")
        else:
            lines.append("There are currently no properties in committed context.")

    if staged_properties:
        lines.append("")
        lines.append("Pending staged properties:")
        for item in staged_properties:
            lines.append(f"- `{item['title']}` — staging entry `{item['entry_id']}`")
            lines.append(f"  Full service address: {item['full_address']}")
        lines.append("")
        lines.append("These staged property records are available to the operator as pending context and still need `sc-admin review` to become committed.")

    if staged_removals:
        lines.append("")
        lines.append("Pending staged property removals:")
        for item in staged_removals:
            lines.append(f"- `{item['property_ref']}` — staging entry `{item['entry_id']}`")
        lines.append("")
        lines.append("These properties are hidden from the operator working set immediately, but framework approval via `sc-admin review` is still required before committed context is updated.")

    return "\n".join(lines)


def _visible_committed_property_titles(cm) -> list[str]:
    committed_sections = _iter_property_sections(cm.load_committed().get("properties", ""))
    staged_removals = _find_pending_property_removals(cm)
    visible_titles: list[str] = []
    for section in committed_sections:
        if _parse_property_removal_request(section).get("is_removal") == "yes":
            continue
        title = section.splitlines()[0].replace("##", "").strip()
        if not any(_property_matches_removal_target(title, item["property_ref"]) for item in staged_removals):
            visible_titles.append(title)
    return visible_titles


def _reply_blocked_debit_note_for_removed_property(cm, target: str) -> str | None:
    removal = _find_matching_pending_property_removal(cm, target)
    if not removal:
        return None
    return "\n".join(
        [
            f"I can't generate a debit note for `{target}` right now because that property is hidden from the operator working set by a pending staged removal.",
            "",
            f"- Pending staged removal: `{removal['property_ref']}`",
            f"- Staging entry ID: `{removal['entry_id']}`",
            "",
            "Next step: either approve/reject the removal in `sc-admin review`, or use an active property that is still in the working set.",
        ]
    )


def _reply_blocked_debit_note_without_active_property(cm) -> str | None:
    if _visible_committed_property_titles(cm):
        return None
    pending_removals = _find_pending_property_removals(cm)
    if not pending_removals:
        return None
    lines = [
        "I can't generate a debit note right now because there are no active properties in the operator working set.",
        "",
        "Pending staged property removals:",
    ]
    for item in pending_removals:
        lines.append(f"- `{item['property_ref']}` — staging entry `{item['entry_id']}`")
    lines.extend(
        [
            "",
            "Next step: either approve/reject the removal in `sc-admin review`, or restore an active property before generating debit notes.",
        ]
    )
    return "\n".join(lines)


def _determine_location(source_property_ref: str) -> tuple[str, str]:
    if "," in source_property_ref:
        parts = [part.strip() for part in source_property_ref.split(",") if part.strip()]
        if len(parts) >= 2:
            return parts[-1], os.getenv("MINPAKU_DEFAULT_COUNTRY", parts[-1])
    return (
        os.getenv("MINPAKU_DEFAULT_CITY", "Hong Kong"),
        os.getenv("MINPAKU_DEFAULT_COUNTRY", "Hong Kong"),
    )


def _find_committed_host_id(cm) -> str | None:
    handoffs_markdown = cm.load_committed().get("minpaku_handoffs", "")
    if not handoffs_markdown.strip():
        return None
    matches = re.findall(r"^- Remote host ID:\s*(.+)$", handoffs_markdown, re.MULTILINE)
    if matches:
        return matches[-1].strip()
    return None


def _find_committed_handoff(cm, source_property_ref: str) -> dict[str, str | None] | None:
    handoffs_markdown = cm.load_committed().get("minpaku_handoffs", "")
    if not handoffs_markdown.strip():
        return None
    sections = re.split(r"(?=^## Minpaku Handoff — )", handoffs_markdown, flags=re.MULTILINE)
    for section in reversed(sections):
        parsed = _parse_handoff(section)
        if parsed.get("source_property_ref") == source_property_ref:
            return parsed
    return None


def _find_latest_linked_handoff(cm, source_property_ref: str) -> dict[str, str | None] | None:
    handoffs_markdown = cm.load_committed().get("minpaku_handoffs", "")
    if not handoffs_markdown.strip():
        return None
    sections = re.split(r"(?=^## Minpaku Handoff — )", handoffs_markdown, flags=re.MULTILINE)
    for section in reversed(sections):
        parsed = _parse_handoff(section)
        if parsed.get("source_property_ref") != source_property_ref:
            continue
        if parsed.get("remote_property_id") or parsed.get("remote_host_id"):
            return parsed
    return None


def _has_other_linked_handoff(cm, source_property_ref: str) -> bool:
    handoffs_markdown = cm.load_committed().get("minpaku_handoffs", "")
    if not handoffs_markdown.strip():
        return False
    sections = re.split(r"(?=^## Minpaku Handoff — )", handoffs_markdown, flags=re.MULTILINE)
    for section in reversed(sections):
        parsed = _parse_handoff(section)
        if parsed.get("source_property_ref") == source_property_ref:
            continue
        if parsed.get("remote_property_id") or parsed.get("remote_host_id"):
            return True
    return False


def _recover_remote_property_linkage(client: SuperLandlordMinpakuClient, source_property_ref: str, remote_host_id: str | None) -> tuple[str | None, str | None]:
    if not hasattr(client, "search_properties"):
        return None, remote_host_id
    matches = client.search_properties(source_property_ref)
    if remote_host_id:
        host_filtered = [
            prop for prop in matches
            if str(prop.get("hostId") or prop.get("host_id") or "").strip() == remote_host_id
        ]
        if host_filtered:
            matches = host_filtered
    if len(matches) == 1:
        prop = matches[0]
        return (
            str(prop.get("id") or prop.get("property_id") or "").strip() or None,
            str(prop.get("hostId") or prop.get("host_id") or "").strip() or remote_host_id,
        )
    return None, remote_host_id


def _delete_remote_listings_for_property(client: SuperLandlordMinpakuClient, property_id: str) -> int:
    if not property_id or not hasattr(client, "list_listings") or not hasattr(client, "delete_listing"):
        return 0
    deleted = 0
    for listing in client.list_listings(property_id=property_id):
        listing_id = str(listing.get("id") or "").strip()
        if not listing_id:
            continue
        client.delete_listing(listing_id)
        deleted += 1
    return deleted


def _default_host_id(cm, source_property_ref: str) -> str:
    committed = _find_committed_host_id(cm)
    if committed:
        return committed
    configured = os.getenv("MINPAKU_HOST_ID") or os.getenv("MINPAKU_DEFAULT_HOST_ID")
    if configured:
        return configured
    slug = re.sub(r"[^a-z0-9]+", "-", source_property_ref.lower()).strip("-")
    return f"host-sla-{slug[:24] or 'default'}"


def _build_remote_payload(cm, handoff: dict[str, str | None]) -> dict:
    source_property_ref = handoff["source_property_ref"] or "Unnamed property"
    property_section = _extract_property_details(cm.load_committed().get("properties", ""), source_property_ref)
    city, country = _determine_location(source_property_ref)
    note = handoff.get("landlord_note")
    description_parts = [f"Landlord-approved Minpaku availability handoff for {source_property_ref}."]
    if property_section:
        description_parts.append(property_section.replace("## ", "").strip())
    if note and note.lower() != "none":
        description_parts.append(f"Landlord note: {note}")
    return {
        "title": source_property_ref,
        "description": "\n\n".join(description_parts),
        "city": city,
        "country": country,
        "nightlyPrice": float(os.getenv("MINPAKU_DEFAULT_NIGHTLY_PRICE", "0") or 0),
        "currency": os.getenv("MINPAKU_DEFAULT_CURRENCY", "HKD"),
        "amenities": [],
        "maxGuests": int(os.getenv("MINPAKU_DEFAULT_MAX_GUESTS", "1") or 1),
        "rules": note if note and note.lower() != "none" else None,
        "hostId": _default_host_id(cm, source_property_ref),
        "photos": [],
        "contact": None,
    }


def _build_synced_handoff_block(source_property_ref: str, availability: str, remote_property_id: str | None, remote_host_id: str | None, landlord_note: str | None, sync_status: str) -> str:
    lines = [
        f"## Minpaku Handoff — {source_property_ref}",
        f"- Availability: {availability}",
    ]
    if landlord_note and landlord_note.lower() != "none":
        lines.append(f"- Landlord note: {landlord_note}")
    if remote_property_id:
        lines.append(f"- Remote property ID: {remote_property_id}")
    if remote_host_id:
        lines.append(f"- Remote host ID: {remote_host_id}")
    lines.append(f"- Sync status: {sync_status}")
    lines.extend(
        [
            "",
            "This handoff indicates landlord intent only.",
            "Listing title, nightly price, max guests, amenities, and guest-facing rules must be handled in the Minpaku deployment.",
        ]
    )
    return "\n".join(lines)


def _iter_debit_note_sections(markdown: str) -> list[str]:
    parts = re.split(r"(?=^##\s+DN-)", markdown, flags=re.MULTILINE)
    return [part.strip() for part in parts if part.strip().startswith("## DN-")]


def _extract_debit_note_field(section: str, label: str) -> str | None:
    match = re.search(rf"^- {re.escape(label)}:\s*(.+)$", section, re.MULTILINE)
    return match.group(1).strip() if match else None


def _matches_debit_note_target(text: str, target: str) -> bool:
    return target.lower() in text.lower()


def _find_outstanding_committed_debit_notes(cm, target: str) -> list[dict[str, str]]:
    markdown = cm.load_committed().get("debit_notes", "")
    matches: list[dict[str, str]] = []
    for section in _iter_debit_note_sections(markdown):
        status = (_extract_debit_note_field(section, "Status") or "").lower()
        if status not in {"unpaid", "outstanding", "pending"}:
            continue
        haystack = "\n".join(
            filter(
                None,
                [
                    section,
                    _extract_debit_note_field(section, "Tenant"),
                    _extract_debit_note_field(section, "Property"),
                    _extract_debit_note_field(section, "Description"),
                ],
            )
        )
        if not _matches_debit_note_target(haystack, target):
            continue
        matches.append(
            {
                "reference": section.splitlines()[0].replace("##", "").strip(),
                "tenant": _extract_debit_note_field(section, "Tenant") or "(unknown tenant)",
                "amount": _extract_debit_note_field(section, "Amount") or "(unknown amount)",
                "status": _extract_debit_note_field(section, "Status") or "Unpaid",
            }
        )
    return matches


def _find_pending_debit_note_staging(cm, target: str) -> list[dict[str, str]]:
    matches: list[dict[str, str]] = []
    for entry in cm.list_staging(status="unconfirmed"):
        content = entry.get("content", "")
        summary = entry.get("summary", "")
        blob = f"{summary}\n{content}"
        if "debit note" not in blob.lower() and "dn-" not in blob.lower():
            continue
        if not _matches_debit_note_target(blob, target):
            continue
        reference_match = re.search(r"\bDN-\d{4}-\d+\b", blob)
        amount_match = re.search(r"\bHKD\s*[0-9,]+(?:\.\d{2})?\b", content)
        matches.append(
            {
                "entry_id": str(entry.get("id") or ""),
                "category": str(entry.get("category") or "general"),
                "reference": reference_match.group(0) if reference_match else "(pending reference)",
                "summary": summary or "Pending debit note update",
                "amount": amount_match.group(0) if amount_match else "(amount not parsed)",
            }
        )
    return matches


def _reply_outstanding_debit_notes(cm, target: str) -> str | None:
    committed_matches = _find_outstanding_committed_debit_notes(cm, target)
    staged_matches = _find_pending_debit_note_staging(cm, target)

    if not committed_matches and not staged_matches:
        return None

    lines = []
    if committed_matches:
        lines.append(f"Outstanding committed debit notes for {target}:")
        for item in committed_matches:
            lines.append(f"- `{item['reference']}` — {item['tenant']} — {item['amount']} — {item['status']}")
    else:
        lines.append(f"There are no committed outstanding debit notes for {target} yet.")

    if staged_matches:
        lines.append("")
        lines.append(f"Pending staged debit-note updates for {target}:")
        for item in staged_matches:
            lines.append(
                f"- `{item['reference']}` — {item['amount']} — category `{item['category']}` — staging entry `{item['entry_id']}`"
            )
        lines.append("")
        lines.append("These staged debit-note updates still need framework approval via `sc-admin review`.")

    return "\n".join(lines)


def _increment_debit_note_reference(reference: str) -> str | None:
    match = re.match(r"^(DN-\d{4}-)(\d+)$", reference.strip())
    if not match:
        return None
    prefix, num = match.groups()
    return f"{prefix}{int(num) + 1:03d}"


def _extract_latest_debit_note_draft(history: list[dict] | None) -> dict[str, str] | None:
    if not history:
        return None
    for turn in reversed(history):
        if turn.get("role") != "assistant":
            continue
        content = str(turn.get("content") or "")
        if "Debit Note Draft" in content:
            reference = re.search(r"`Reference`:\s*`?([A-Z]{2}-\d{4}-\d+)`?", content)
            issue_date = re.search(r"`Issue date`:\s*([0-9-]+)", content)
            property_ref = re.search(r"`Property`:\s*(.+)", content)
            billed_to = re.search(r"`Billed to`:\s*(.+)", content)
            billing_period = re.search(r"`Billing period`:\s*(.+)", content)
            utility = re.search(r"`Utility`:\s*([^\n`]+)", content)
            amount_due = re.search(r"`Amount due from [^`]+`:\s*\*+\s*(HKD\s*[0-9,]+(?:\.\d{2})?)", content)
            if all([reference, issue_date, property_ref, billed_to, billing_period, amount_due]):
                return {
                    "reference": reference.group(1).strip(),
                    "issue_date": issue_date.group(1).strip(),
                    "property": property_ref.group(1).strip(),
                    "billed_to": billed_to.group(1).strip(),
                    "billing_period": billing_period.group(1).strip(),
                    "utility": utility.group(1).strip() if utility else "Utility",
                    "amount_due": amount_due.group(1).strip(),
                }

        if "DEBIT NOTE" not in content:
            continue
        reference = re.search(r"Reference No\.\s*:\s*([A-Z]{2}-\d{4}-\d+)", content)
        issue_date = re.search(r"Date:\s*([0-9-]+)", content)
        property_ref = re.search(r"Property\s*/\s*Service Account:\s*\n([^\n]+)", content)
        billed_to = re.search(r"To:\s*([^\n]+)", content)
        billing_period = re.search(r"Billing Period:\s*([^\n]+)", content)
        utility = re.search(r"Utility:\s*([^\n]+)", content)
        amount_due = re.search(r"Amount Due:\s*\**\s*(HKD\s*[0-9,]+(?:\.\d{2})?)", content)
        if not all([reference, issue_date, property_ref, billed_to, billing_period, amount_due]):
            continue
        return {
            "reference": reference.group(1).strip(),
            "issue_date": issue_date.group(1).strip(),
            "property": property_ref.group(1).strip(),
            "billed_to": billed_to.group(1).strip(),
            "billing_period": billing_period.group(1).strip(),
            "utility": utility.group(1).strip() if utility else "Utility",
            "amount_due": amount_due.group(1).strip(),
        }
    return None


def _stage_issued_debit_note_from_history(cm, history: list[dict] | None) -> dict | None:
    draft = _extract_latest_debit_note_draft(history)
    if not draft:
        return None
    next_reference = _increment_debit_note_reference(draft["reference"]) or draft["reference"]
    summary = f"Issued debit note {draft['reference']} for {draft['billed_to']}, {draft['amount_due']}"
    content = "\n".join(
        [
            f"## {draft['reference']}",
            f"- Date: {draft['issue_date']}",
            f"- Tenant: {draft['billed_to']}",
            f"- Property: {draft['property']}",
            f"- Description: {draft['utility']} charges — {draft['billing_period']}",
            f"- Amount: {draft['amount_due']}",
            "- Status: Unpaid",
            "",
            f"## Next reference number: {next_reference}",
        ]
    )
    entry_id = cm.create_staging_entry(
        summary=summary,
        content=content,
        category="debit_notes",
        source="operator",
    )
    return {
        "entry_id": entry_id,
        "reference": draft["reference"],
        "amount_due": draft["amount_due"],
        "billed_to": draft["billed_to"],
        "next_reference": next_reference,
    }


def _strip_pending_framework_review(sync_status: str | None) -> str | None:
    if not sync_status:
        return sync_status
    return sync_status.replace(" (pending framework review)", "").strip()


def _replace_committed_handoff(cm, entry_id: str, new_block: str) -> None:
    entry = cm.get_staging_entry(entry_id)
    if not entry:
        return
    existing_block = entry.get("content", "").strip()
    target_path = cm._root / "context" / "minpaku_handoffs.md"
    current = target_path.read_text(encoding="utf-8") if target_path.exists() else ""
    if existing_block and existing_block in current:
        updated = current.replace(existing_block, new_block.strip())
    else:
        updated = current.rstrip() + "\n\n" + new_block.strip() + "\n"
    target_path.write_text(updated.rstrip() + "\n", encoding="utf-8")


def _same_text(a: str | None, b: str | None) -> bool:
    return (a or "").strip().lower() == (b or "").strip().lower()


def review_staging_entry(cm, entry: dict) -> dict | None:
    if entry.get("category") != "minpaku_handoffs":
        return None

    handoff = _parse_handoff(entry.get("content", ""))
    source_property_ref = handoff.get("source_property_ref")
    availability = (handoff.get("availability") or "").lower()
    sync_status = handoff.get("sync_status") or ""
    if not source_property_ref or availability not in {"available", "unavailable"}:
        return {
            "recommendation": "defer",
            "reason": "The Minpaku handoff is missing a valid property reference or availability state.",
            "conflicts": ["Handoff must include a property reference and either 'available' or 'unavailable'."],
            "confidence": 0.98,
        }

    if "pending framework review" in sync_status.lower():
        return {
            "recommendation": "approve",
            "reason": (
                f"This handoff has already been synced to Minpaku for {source_property_ref}; "
                "framework approval is now only deciding whether that synced record becomes committed context."
            ),
            "conflicts": [],
            "confidence": 0.99,
        }

    latest_same = _find_committed_handoff(cm, source_property_ref)
    latest_linked = _find_latest_linked_handoff(cm, source_property_ref)

    if availability == "available":
        if latest_same and _same_text(latest_same.get("availability"), "available"):
            if latest_same.get("remote_property_id"):
                return {
                    "recommendation": "defer",
                    "reason": (
                        f"A published Minpaku handoff already exists for {source_property_ref}. "
                        "This staged entry looks like an exact re-publish of the same scope."
                    ),
                    "conflicts": [
                        f"Committed handoff already links {source_property_ref} to {latest_same.get('remote_property_id')}."
                    ],
                    "confidence": 0.92,
                }
            return {
                "recommendation": "approve",
                "reason": (
                    f"This is a valid availability handoff for {source_property_ref}. "
                    "Remote property ID, host ID, and sync status are expected to be absent before approval; "
                    "they are added during post-approval Minpaku sync."
                ),
                "conflicts": [],
                "confidence": 0.95,
            }

        live_conflicts: list[str] = []
        try:
            client = SuperLandlordMinpakuClient()
            live_matches = client.search_properties(source_property_ref)
            exact_matches = [
                prop for prop in live_matches
                if _same_text(str(prop.get("title") or prop.get("name") or ""), source_property_ref)
            ]
            if exact_matches:
                ids = ", ".join(str(prop.get("id") or prop.get("property_id") or "(unknown)") for prop in exact_matches)
                live_conflicts.append(
                    f"Live Minpaku already has exact property match(es) for {source_property_ref}: {ids}."
                )
        except Exception:
            pass

        if live_conflicts:
            return {
                "recommendation": "defer",
                "reason": (
                    f"{source_property_ref} appears to already exist as a live Minpaku property. "
                    "Review whether this is meant to update the existing property or create a separate scope."
                ),
                "conflicts": live_conflicts,
                "confidence": 0.88,
            }

        sibling_note = ""
        if _has_other_linked_handoff(cm, source_property_ref):
            sibling_note = (
                " This appears to be a different unit/scope than the latest linked Minpaku handoff, "
                "which is allowed as a new landlord intent."
            )

        return {
            "recommendation": "approve",
            "reason": (
                f"This is a valid availability handoff for {source_property_ref}. "
                "Remote property ID, host ID, and sync status are expected to be absent before approval; "
                "they are added during post-approval Minpaku sync."
                + sibling_note
            ),
            "conflicts": [],
            "confidence": 0.95,
        }

    if latest_same and _same_text(latest_same.get("availability"), "unavailable"):
        return {
            "recommendation": "defer",
            "reason": f"{source_property_ref} is already marked unavailable in the latest committed handoff.",
            "conflicts": [f"Latest committed handoff for {source_property_ref} is already unavailable."],
            "confidence": 0.9,
        }

    return {
        "recommendation": "approve",
        "reason": (
            f"This is a valid landlord intent change marking {source_property_ref} unavailable for Minpaku."
        ),
        "conflicts": [],
        "confidence": 0.95,
    }


def on_staging_approved(cm, entry: dict) -> dict | None:
    if entry.get("category") == "properties":
        parsed_removal = _parse_property_removal_request(entry.get("content", ""))
        if parsed_removal.get("is_removal") == "yes" and parsed_removal.get("property_ref"):
            changed = _apply_approved_property_removal(cm, str(parsed_removal.get("property_ref") or ""))
            return {
                "ok": True,
                "message": (
                    "Committed property removal applied."
                    if changed
                    else "No committed property matched the approved removal request."
                ),
            }
        return None

    if entry.get("category") != "minpaku_handoffs":
        return None

    handoff = _parse_handoff(entry.get("content", ""))
    source_property_ref = handoff.get("source_property_ref")
    availability = (handoff.get("availability") or "").lower()
    sync_status = handoff.get("sync_status") or ""
    if not source_property_ref or availability not in {"available", "unavailable"}:
        return {
            "ok": False,
            "error": "Approved Minpaku handoff is missing a valid property reference or availability state.",
        }

    if "pending framework review" in sync_status.lower():
        final_status = _strip_pending_framework_review(sync_status) or sync_status
        new_block = _build_synced_handoff_block(
            source_property_ref=source_property_ref,
            availability=availability,
            remote_property_id=handoff.get("remote_property_id"),
            remote_host_id=handoff.get("remote_host_id"),
            landlord_note=handoff.get("landlord_note"),
            sync_status=final_status,
        )
        _replace_committed_handoff(cm, entry["id"], new_block)
        return {
            "ok": True,
            "message": "Already synced to Minpaku before framework approval.",
            "property_id": handoff.get("remote_property_id"),
            "host_id": handoff.get("remote_host_id"),
        }

    client = SuperLandlordMinpakuClient()

    if availability == "available":
        payload = _build_remote_payload(cm, handoff)
        response = client.create_property(payload)
        property_info = response.get("property", {})
        new_block = _build_synced_handoff_block(
            source_property_ref=source_property_ref,
            availability=availability,
            remote_property_id=property_info.get("id"),
            remote_host_id=payload.get("hostId"),
            landlord_note=handoff.get("landlord_note"),
            sync_status="published to Minpaku",
        )
        _replace_committed_handoff(cm, entry["id"], new_block)
        return {
            "ok": True,
            "message": (
                f"Published to Minpaku as {property_info.get('id', '(unknown property id)')} "
                f"using host id {payload.get('hostId', '(unknown host id)')}."
            ),
            "property_id": property_info.get("id"),
            "host_id": payload.get("hostId"),
        }

    committed_handoff = _find_committed_handoff(cm, source_property_ref)
    linked_handoff = _find_latest_linked_handoff(cm, source_property_ref)
    remote_property_id = (
        handoff.get("remote_property_id")
        or (committed_handoff or {}).get("remote_property_id")
        or (linked_handoff or {}).get("remote_property_id")
    )
    remote_host_id = (
        handoff.get("remote_host_id")
        or (committed_handoff or {}).get("remote_host_id")
        or (linked_handoff or {}).get("remote_host_id")
    )
    if remote_property_id:
        try:
            deleted_listings = _delete_remote_listings_for_property(client, remote_property_id)
            client.delete_property(remote_property_id, host_id=remote_host_id)
            sync_status = "unlisted from Minpaku"
            message = (
                f"{sync_status}"
                + (f" after deleting {deleted_listings} live listing(s)" if deleted_listings else "")
                + "."
            )
        except Exception as exc:
            if "404" in str(exc):
                recovered_property_id, recovered_host_id = _recover_remote_property_linkage(
                    client,
                    source_property_ref=source_property_ref,
                    remote_host_id=remote_host_id,
                )
                if recovered_property_id:
                    deleted_listings = _delete_remote_listings_for_property(client, recovered_property_id)
                    client.delete_property(recovered_property_id, host_id=recovered_host_id)
                    remote_property_id = recovered_property_id
                    remote_host_id = recovered_host_id
                    sync_status = "recovered remote property id and unlisted from Minpaku"
                    message = (
                        f"{sync_status}"
                        + (f" after deleting {deleted_listings} live listing(s)" if deleted_listings else "")
                        + "."
                    )
                else:
                    sync_status = "already absent from Minpaku"
                    message = f"{sync_status}; local linkage marked unavailable."
            else:
                raise
    else:
        sync_status = "marked unavailable locally (no remote property id recorded)"
        message = sync_status + "."
    new_block = _build_synced_handoff_block(
        source_property_ref=source_property_ref,
        availability=availability,
        remote_property_id=remote_property_id,
        remote_host_id=remote_host_id,
        landlord_note=handoff.get("landlord_note"),
        sync_status=sync_status,
    )
    _replace_committed_handoff(cm, entry["id"], new_block)
    return {"ok": True, "message": message, "host_id": remote_host_id}


def _stage_immediate_handoff(cm, source_property_ref: str, availability: str, landlord_note: str | None) -> dict:
    latest_same = _find_committed_handoff(cm, source_property_ref)
    if availability == "available" and latest_same and _same_text(latest_same.get("availability"), "available") and latest_same.get("remote_property_id"):
        return {
            "ok": True,
            "already_live": True,
            "source_property_ref": source_property_ref,
            "availability": availability,
            "property_id": latest_same.get("remote_property_id"),
            "host_id": latest_same.get("remote_host_id"),
            "message": f"{source_property_ref} is already live in Minpaku as {latest_same.get('remote_property_id')}.",
        }

    client = SuperLandlordMinpakuClient()
    remote_property_id = None
    remote_host_id = None

    if availability == "available":
        payload = _build_remote_payload(
            cm,
            {
                "source_property_ref": source_property_ref,
                "availability": availability,
                "landlord_note": landlord_note,
            },
        )
        response = client.create_property(payload)
        property_info = response.get("property", {})
        remote_property_id = property_info.get("id")
        remote_host_id = payload.get("hostId")
        sync_status = "published to Minpaku (pending framework review)"
        message = (
            f"Made {source_property_ref} available in Minpaku immediately as "
            f"{remote_property_id or '(unknown property id)'} using host id {remote_host_id or '(unknown host id)'}."
        )
    else:
        committed_handoff = _find_committed_handoff(cm, source_property_ref)
        linked_handoff = _find_latest_linked_handoff(cm, source_property_ref)
        remote_property_id = (
            (committed_handoff or {}).get("remote_property_id")
            or (linked_handoff or {}).get("remote_property_id")
        )
        remote_host_id = (
            (committed_handoff or {}).get("remote_host_id")
            or (linked_handoff or {}).get("remote_host_id")
        )
        if remote_property_id:
            try:
                deleted_listings = _delete_remote_listings_for_property(client, remote_property_id)
                client.delete_property(remote_property_id, host_id=remote_host_id)
                sync_status = "unlisted from Minpaku (pending framework review)"
                message = (
                    f"Marked {source_property_ref} unavailable in Minpaku immediately"
                    + (f" after deleting {deleted_listings} live listing(s)" if deleted_listings else "")
                    + "."
                )
            except Exception as exc:
                if "404" in str(exc):
                    recovered_property_id, recovered_host_id = _recover_remote_property_linkage(
                        client,
                        source_property_ref=source_property_ref,
                        remote_host_id=remote_host_id,
                    )
                    if recovered_property_id:
                        deleted_listings = _delete_remote_listings_for_property(client, recovered_property_id)
                        client.delete_property(recovered_property_id, host_id=recovered_host_id)
                        remote_property_id = recovered_property_id
                        remote_host_id = recovered_host_id
                        sync_status = "recovered remote property id and unlisted from Minpaku (pending framework review)"
                        message = (
                            f"Recovered the live Minpaku property for {source_property_ref} and marked it unavailable"
                            + (f" after deleting {deleted_listings} live listing(s)" if deleted_listings else "")
                            + "."
                        )
                    else:
                        sync_status = "already absent from Minpaku (pending framework review)"
                        message = f"{source_property_ref} was already absent from Minpaku."
                else:
                    raise
        else:
            sync_status = "marked unavailable locally (no remote property id recorded) (pending framework review)"
            message = f"Marked {source_property_ref} unavailable locally; no linked Minpaku property id was on file."

    body = _build_synced_handoff_block(
        source_property_ref=source_property_ref,
        availability=availability,
        remote_property_id=remote_property_id,
        remote_host_id=remote_host_id,
        landlord_note=landlord_note,
        sync_status=sync_status,
    )
    summary = f"Minpaku handoff for {source_property_ref} ({availability})"
    entry_id = cm.create_staging_entry(
        summary=summary,
        content=body,
        category="minpaku_handoffs",
        source="operator",
    )
    return {
        "ok": True,
        "entry_id": entry_id,
        "source_property_ref": source_property_ref,
        "availability": availability,
        "property_id": remote_property_id,
        "host_id": remote_host_id,
        "message": message,
    }


def dispatch(name: str, args: dict, cm) -> str:
    if name != "prepare_minpaku_handoff":
        raise ValueError(f"Unknown tool: {name}")

    source_property_ref = str(args.get("source_property_ref", "")).strip()
    availability = str(args.get("availability", "")).strip().lower()
    landlord_note = str(args.get("landlord_note", "")).strip()

    missing = []
    if not source_property_ref:
        missing.append("source property reference")
    if availability not in {"available", "unavailable"}:
        missing.append("availability state (`available` or `unavailable`)")

    if missing:
        return json.dumps(
            {
                "ok": False,
                "missing_fields": missing,
                "next_prompt": (
                    "Please provide the missing Minpaku handoff fields in one message: "
                    + ", ".join(missing)
                    + "."
                ),
                "handoff": {
                    "source_property_ref": source_property_ref,
                    "availability": availability if availability in {"available", "unavailable"} else None,
                    "landlord_note": landlord_note or None,
                },
            },
            ensure_ascii=False,
        )

    lines = [
        f"## Minpaku Handoff — {source_property_ref}",
        f"- Availability: {availability}",
    ]
    if landlord_note:
        lines.append(f"- Landlord note: {landlord_note}")
    lines.extend(
        [
            "",
            "This handoff indicates landlord intent only.",
            "Listing title, nightly price, max guests, amenities, and guest-facing rules must be handled in the Minpaku deployment.",
        ]
    )
    body = "\n".join(lines)
    summary = f"Minpaku handoff for {source_property_ref} ({availability})"
    entry_id = cm.create_staging_entry(
        summary=summary,
        content=body,
        category="minpaku_handoffs",
        source="operator",
    )
    return json.dumps(
        {
            "ok": True,
            "staged": True,
            "entry_id": entry_id,
            "summary": summary,
            "handoff": {
                "source_property_ref": source_property_ref,
                "availability": availability,
                "landlord_note": landlord_note or None,
            },
        },
        ensure_ascii=False,
    )


def maybe_handle_message(message: str, cm, role_name: str = "operator", history: list[dict] | None = None) -> str | None:
    """Deterministically handle obvious Minpaku handoff commands.

    This avoids depending on model tool choice for simple operator intent updates.
    """
    if role_name != "operator":
        return None

    text = " ".join(message.strip().split())
    if not text:
        return None

    lowered = text.lower()

    if re.fullmatch(r"(show|list)\s+all\s+properties\.?", lowered):
        return _reply_all_properties(cm)

    if "extract" in lowered and "property" in lowered and "bill" in lowered:
        candidate = _extract_property_candidate_from_history_or_staging(cm, history)
        if not candidate:
            return None
        return "\n".join(
            [
                "Extracted property from the utility bill:",
                "",
                f"- Unit: `{candidate['unit']}`",
                f"- Building: `{candidate['building']}`",
                f"- Full service address: `{candidate['full_address']}`",
                "",
                "If you want, I can also capture this as a property record for admin review.",
            ]
        )

    if (
        ("capture" in lowered and "property" in lowered and ("bill" in lowered or "extracted" in lowered))
        or ("stage" in lowered and "property" in lowered and "bill" in lowered)
        or ("add" in lowered and "property" in lowered and "bill" in lowered)
    ):
        candidate = _extract_property_candidate_from_history_or_staging(cm, history)
        if not candidate:
            return None
        try:
            staged_property = _stage_property_candidate(cm, candidate)
        except Exception as exc:
            return f"I found the property candidate from the utility bill, but staging it failed: {exc}"
        return "\n".join(
            [
                "Captured. I staged the extracted property record for review.",
                "",
                f"- Staging entry ID: `{staged_property['entry_id']}`",
                "- Status: `pending` (not committed yet)",
                f"- Property: `{staged_property['property_ref']}`",
                "",
                "Next step: run `sc-admin review` to commit it into authoritative context.",
            ]
        )

    remove_match = re.fullmatch(r"(?:remove|delete)\s+(.+?)[\.\?]?", text, re.IGNORECASE)
    if remove_match:
        raw_property_ref = remove_match.group(1).strip(" `")
        resolution = _resolve_property_reference(cm, raw_property_ref)
        if resolution["status"] not in {"exact", "unique_partial"}:
            return None
        property_ref = str(resolution["resolved"] or raw_property_ref)
        staged = _stage_property_removal(cm, property_ref)
        return "\n".join(
            [
                f"Done — I staged the removal of `{staged['property_ref']}` from the operator working set.",
                "",
                f"- Staging entry ID: `{staged['entry_id']}`",
                "- Status: `pending` (not committed yet)",
                "",
                "The property will be hidden in `show all properties` immediately, and `sc-admin review` will decide whether to commit that removal to authoritative context.",
            ]
        )

    outstanding_match = re.search(
        r"\b(?:show|list|what are)\s+outstanding\s+debit\s+notes\s+for\s+(?P<target>.+?)[\?\.]?$",
        text,
        re.IGNORECASE,
    )
    if outstanding_match:
        target = outstanding_match.group("target").strip(" .?")
        reply = _reply_outstanding_debit_notes(cm, target)
        if reply:
            return reply
        return None

    debit_note_match = re.search(
        r"\b(?:generate|draft|prepare)\s+(?:(?:a|an|the)\s+)?debit\s+note(?:s)?\s+for\s+(?P<target>.+?)[\?\.]?$",
        text,
        re.IGNORECASE,
    )
    if debit_note_match:
        target = debit_note_match.group("target").strip(" .?")
        blocked_reply = _reply_blocked_debit_note_for_removed_property(cm, target)
        if blocked_reply:
            return blocked_reply

    if re.fullmatch(r"(?:generate|draft|prepare)\s+(?:(?:a|an|the)\s+)?debit\s+note(?:s)?(?:\s+for)?[\?\.]?", text, re.IGNORECASE):
        blocked_reply = _reply_blocked_debit_note_without_active_property(cm)
        if blocked_reply:
            return blocked_reply

    if re.search(r"\brecord\s+(?:the\s+)?debit\s+note\b", lowered) and "framework approval" in lowered:
        try:
            staged = _stage_issued_debit_note_from_history(cm, history)
        except Exception as exc:
            return f"I found the debit note draft, but staging the issued-note update failed: {exc}"
        if staged:
            return "\n".join(
                [
                    "Done — I staged the context update only (no committed context was changed).",
                    "",
                    f"- Staging entry ID: `{staged['entry_id']}`",
                    "- Status: `pending` (awaiting framework/admin approval)",
                    "- Captured update includes:",
                    f"  - Mark `{staged['reference']}` as issued",
                    f"  - Full debit note details ({staged['billed_to']}, amount {staged['amount_due']})",
                    f"  - Request to advance next reference to `{staged['next_reference']}` after approval",
                    "",
                    "You can now commit this staged record via `sc-admin review`.",
                ]
            )
        return None

    if "minpaku" not in lowered:
        return None

    availability = None
    if " unavailable " in f" {lowered} " or " unavailable for minpaku" in lowered:
        availability = "unavailable"
    elif " available " in f" {lowered} " or " available for minpaku" in lowered:
        availability = "available"

    if availability is None:
        return None

    match = re.search(
        r"(?:mark|make)\s+(?P<property>.+?)\s+(?:become\s+|as\s+)?(?P<availability>available|unavailable)\s+(?:for|in)\s+minpaku\b",
        text,
        re.IGNORECASE,
    )
    if not match:
        return None

    raw_property_ref = match.group("property").strip(" .")
    resolution = _resolve_property_reference(cm, raw_property_ref)
    if resolution["status"] not in {"exact", "unique_partial"}:
        return None
    source_property_ref = str(resolution["resolved"] or raw_property_ref)
    try:
        result = _stage_immediate_handoff(cm, source_property_ref, availability, landlord_note=None)
    except Exception as exc:
        return f"I found `{source_property_ref}`, but the immediate Minpaku handoff failed: {exc}"
    if not result.get("ok"):
        return f"I found `{source_property_ref}`, but the immediate Minpaku handoff failed."

    lines = []
    if result.get("already_live"):
        lines.extend(
            [
                result["message"],
                "",
                "No new handoff was staged because the property is already linked live in Minpaku.",
            ]
        )
        return "\n".join(lines)

    lines.extend(
        [
            result["message"],
            "",
            "Framework review is still required before this becomes committed context.",
            f"- Property: {result['source_property_ref']}",
            f"- Availability: {result['availability']}",
        ]
    )
    if result.get("host_id"):
        lines.append(f"- Remote host ID: {result['host_id']}")
    if result.get("property_id"):
        lines.append(f"- Remote property ID: {result['property_id']}")
    lines.extend(
        [
            "",
            "The Minpaku deployment will handle listing title, nightly price, max guests, amenities, and guest-facing rules.",
            "",
            "Staged and synced — run `sc-admin review` to commit.",
        ]
    )
    return "\n".join(lines)
