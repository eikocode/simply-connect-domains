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


def maybe_handle_message(message: str, cm, role_name: str = "operator") -> str | None:
    """Deterministically handle obvious Minpaku handoff commands.

    This avoids depending on model tool choice for simple landlord intent updates.
    """
    if role_name != "operator":
        return None

    text = " ".join(message.strip().split())
    if not text:
        return None

    lowered = text.lower()
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
        r"mark\s+(?P<property>.+?)\s+(?:as\s+)?(?P<availability>available|unavailable)\s+for\s+minpaku\b",
        text,
        re.IGNORECASE,
    )
    if not match:
        return None

    source_property_ref = match.group("property").strip(" .")
    result = _stage_immediate_handoff(cm, source_property_ref, availability, landlord_note=None)
    if not result.get("ok"):
        return None

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
            "Staged and synced — run sc-admin review to commit.",
        ]
    )
    return "\n".join(lines)
