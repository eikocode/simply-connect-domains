"""
Minpaku extension — live inventory, booking, and listing-management tools.
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from typing import Any

from .client import MinpakuClient


def _is_operator_role(role_name: str) -> bool:
    return role_name in {"operator", "host"}

TOOLS = [
    {
        "name": "list_properties",
        "description": (
            "List all vacation rental properties from the Minpaku API. "
            "Returns property IDs, names, and key details."
        ),
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "search_properties",
        "description": (
            "Search vacation rental properties by name or property ID. "
            "Returns matching properties from the Minpaku API."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search string to match against property name or ID."}
            },
            "required": ["query"],
        },
    },
    {
        "name": "get_bookings_by_property",
        "description": (
            "Get all bookings for a specific vacation rental property from the Minpaku API."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "property_id": {"type": "string", "description": "The property ID to retrieve bookings for."}
            },
            "required": ["property_id"],
        },
    },
    {
        "name": "list_listings",
        "description": (
            "List all Minpaku listings. Listings are channel-facing publications layered on top of properties."
        ),
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "search_listings",
        "description": (
            "Search Minpaku listings by listing ID, property ID, platform, title, or source property reference."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search string to match against listing fields."}
            },
            "required": ["query"],
        },
    },
    {
        "name": "prepare_minpaku_listing",
        "description": (
            "Prepare and stage a Minpaku listing draft for an existing property. "
            "Use this in the Minpaku operator workflow to gather listing-specific fields such as platform, title, description, and channel price before publishing."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "property_id": {"type": "string"},
                "source_property_ref": {"type": "string"},
                "platform": {"type": "string"},
                "external_id": {"type": "string"},
                "title": {"type": "string"},
                "description": {"type": "string"},
                "nightly_price": {"type": "number"},
                "currency": {"type": "string"},
                "status": {"type": "string"},
                "contact": {"type": "string"},
            },
            "required": ["source_property_ref"],
        },
    },
]


def _extract_location(prop: dict[str, Any]) -> tuple[str, str]:
    location = prop.get("location")
    if isinstance(location, dict):
        return str(location.get("city") or ""), str(location.get("country") or "")
    if isinstance(location, str) and "," in location:
        parts = [part.strip() for part in location.split(",") if part.strip()]
        if len(parts) >= 2:
            return parts[0], parts[1]
    return str(location or ""), ""


def _count_active_or_upcoming_bookings(bookings_payload: Any) -> int:
    if isinstance(bookings_payload, dict):
        if isinstance(bookings_payload.get("bookings"), list):
            bookings = bookings_payload["bookings"]
        else:
            bookings = []
    elif isinstance(bookings_payload, list):
        bookings = bookings_payload
    else:
        bookings = []
    active_statuses = {"PENDING", "HOLD", "CONFIRMED"}
    return sum(1 for booking in bookings if str(booking.get("status", "")).upper() in active_statuses)


def _extract_bookings(bookings_payload: Any) -> list[dict[str, Any]]:
    if isinstance(bookings_payload, dict):
        bookings = bookings_payload.get("bookings", [])
        return bookings if isinstance(bookings, list) else []
    if isinstance(bookings_payload, list):
        return [booking for booking in bookings_payload if isinstance(booking, dict)]
    return []


def _normalize_entity_ref(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def _resolve_unique_property_match(properties: list[dict[str, Any]], query: str) -> dict[str, Any] | None:
    if not properties:
        return None

    normalized_query = _normalize_entity_ref(query)
    if not normalized_query:
        return None

    exact = []
    partial = []
    for prop in properties:
        property_id = str(prop.get("id") or prop.get("property_id") or "").strip()
        title = str(prop.get("title") or prop.get("name") or "").strip()
        candidates = [value for value in (property_id, title) if value]
        normalized_candidates = [_normalize_entity_ref(value) for value in candidates]
        if normalized_query in normalized_candidates:
            exact.append(prop)
            continue
        if any(normalized_query in candidate or candidate in normalized_query for candidate in normalized_candidates):
            partial.append(prop)

    exact = list(dict.fromkeys(id(prop) for prop in exact))
    if len(exact) == 1:
        target_id = exact[0]
        for prop in properties:
            if id(prop) == target_id:
                return prop
    if len(exact) > 1:
        return None

    partial = list(dict.fromkeys(id(prop) for prop in partial))
    if len(partial) == 1:
        target_id = partial[0]
        for prop in properties:
            if id(prop) == target_id:
                return prop
    return None


def _find_property_for_query(client: MinpakuClient, query: str) -> tuple[dict[str, Any] | None, bool]:
    matches = client.search_properties(query)
    if matches:
        resolved = _resolve_unique_property_match(matches, query)
        if resolved is None:
            return None, True
        return resolved, True
    properties = client.list_properties()
    return _resolve_unique_property_match(properties, query), False


def _load_full_property_record(client: MinpakuClient, prop: dict[str, Any]) -> dict[str, Any]:
    property_id = str(prop.get("id") or prop.get("property_id") or "").strip()
    if not property_id:
        return prop
    try:
        full = client.get_property(property_id)
    except Exception:
        return prop
    return full if isinstance(full, dict) and full else prop


def _search_property_matches(client: MinpakuClient, query: str) -> tuple[list[dict[str, Any]], bool]:
    matches = client.search_properties(query)
    if matches:
        return matches, True
    return client.list_properties(), False


def _parse_price_update_request(text: str) -> dict[str, Any] | None:
    match = re.search(
        r"^(?:update|change|set)\s+(?P<target>.+?)\s+(?:to|at)\s+(?P<price>(?:[$€£¥]\s*)?\d+(?:\.\d+)?)\s*(?P<currency>[A-Za-z]{3})?\s*/?\s*(?:per\s*)?night\b",
        text.strip(),
        flags=re.IGNORECASE,
    )
    if not match:
        return None
    price_token = match.group("price").replace(" ", "")
    numeric = re.sub(r"^[^0-9]+", "", price_token)
    if not numeric:
        return None
    return {
        "target": match.group("target").strip(" `."),
        "nightly_price": float(numeric),
        "currency_hint": (match.group("currency") or "").upper() or None,
        "symbol": price_token[0] if price_token and not price_token[0].isdigit() else None,
    }


def _parse_property_edit_request(text: str) -> dict[str, Any] | None:
    stripped = text.strip()
    patterns: list[tuple[str, str]] = [
        ("maxGuests", r"^(?:update|change|set)\s+(?P<target>.+?)\s+(?:to have|to|at)\s+(?P<value>\d+)\s+(?:guests?|people)\b"),
        ("rules", r"^(?:update|change|set)\s+(?P<target>.+?)\s+(?:rules?|house rules?)\s+to\s+(?P<value>.+)$"),
        ("description", r"^(?:update|change|set)\s+(?P<target>.+?)\s+description\s+to\s+(?P<value>.+)$"),
        ("title", r"^(?:rename|retitle|change title of|set title of)\s+(?P<target>.+?)\s+to\s+(?P<value>.+)$"),
    ]
    for field, pattern in patterns:
        match = re.search(pattern, stripped, flags=re.IGNORECASE)
        if not match:
            continue
        value = match.group("value").strip(" `.")
        if not value:
            return None
        return {
            "field": field,
            "target": match.group("target").strip(" `."),
            "value": int(value) if field == "maxGuests" else value,
        }
    return None


def _build_property_update_payload(prop: dict[str, Any], nightly_price: float, currency: str) -> dict[str, Any]:
    location = prop.get("location") or {}
    coordinates = location.get("coordinates") if isinstance(location, dict) else {}
    return {
        "title": str(prop.get("title") or prop.get("name") or "").strip(),
        "description": prop.get("description"),
        "city": str(location.get("city") or "") if isinstance(location, dict) else "",
        "country": str(location.get("country") or "") if isinstance(location, dict) else "",
        "latitude": coordinates.get("latitude") if isinstance(coordinates, dict) else None,
        "longitude": coordinates.get("longitude") if isinstance(coordinates, dict) else None,
        "nightlyPrice": nightly_price,
        "currency": currency,
        "amenities": prop.get("amenities") or [],
        "maxGuests": prop.get("maxGuests") or prop.get("capacity") or 1,
        "rules": prop.get("rules"),
        "hostId": prop.get("hostId") or prop.get("host_id"),
        "photos": prop.get("photos") or [],
    }


def _build_property_update_payload_from_changes(prop: dict[str, Any], changes: dict[str, Any]) -> dict[str, Any]:
    location = prop.get("location") or {}
    coordinates = location.get("coordinates") if isinstance(location, dict) else {}
    return {
        "title": str(changes.get("title", prop.get("title") or prop.get("name") or "")).strip(),
        "description": changes.get("description", prop.get("description")),
        "city": str(location.get("city") or "") if isinstance(location, dict) else "",
        "country": str(location.get("country") or "") if isinstance(location, dict) else "",
        "latitude": coordinates.get("latitude") if isinstance(coordinates, dict) else None,
        "longitude": coordinates.get("longitude") if isinstance(coordinates, dict) else None,
        "nightlyPrice": changes.get("nightlyPrice", prop.get("nightlyPrice") or prop.get("price") or 0),
        "currency": changes.get("currency", prop.get("currency") or "HKD"),
        "amenities": prop.get("amenities") or [],
        "maxGuests": changes.get("maxGuests", prop.get("maxGuests") or prop.get("capacity") or 1),
        "rules": changes.get("rules", prop.get("rules")),
        "hostId": prop.get("hostId") or prop.get("host_id"),
        "photos": prop.get("photos") or [],
    }


def _stage_price_update_note(cm, prop: dict[str, Any], nightly_price: float, currency: str) -> str:
    title = str(prop.get("title") or prop.get("name") or prop.get("id") or "Unknown property")
    property_id = str(prop.get("id") or prop.get("property_id") or "").strip()
    content = "\n".join(
        [
            f"## Price Update — {title}",
            f"- Property ID: `{property_id}`",
            f"- New nightly price: `{currency} {nightly_price:.0f}/night`",
            f"- Updated at: `{datetime.now(timezone.utc).isoformat()}`",
        ]
    )
    return cm.create_staging_entry(
        summary=f"Price update for {title}",
        content=content,
        category="pricing",
        source="operator",
    )


def _stage_property_edit_note(cm, prop: dict[str, Any], field_label: str, value: Any) -> str:
    title = str(prop.get("title") or prop.get("name") or prop.get("id") or "Unknown property")
    property_id = str(prop.get("id") or prop.get("property_id") or "").strip()
    content = "\n".join(
        [
            f"## Property Update — {title}",
            f"- Property ID: `{property_id}`",
            f"- Field updated: `{field_label}`",
            f"- New value: `{value}`",
            f"- Updated at: `{datetime.now(timezone.utc).isoformat()}`",
        ]
    )
    return cm.create_staging_entry(
        summary=f"{field_label} update for {title}",
        content=content,
        category="properties",
        source="operator",
    )


def _safe_active_listing_note(client: MinpakuClient, property_id: str, target: str) -> str:
    try:
        live_listings = _flatten_listing_rows(client.list_listings(property_id=property_id, status="active"))
    except Exception as exc:
        return f"- Note: live listing check was unavailable after the property update ({exc})."
    if live_listings:
        return f"- Active listing count touched: `{len(live_listings)}`"
    return f"- Note: there are currently no active listings found for “{target}”, so no listing-level price was directly changed yet."


def _stage_property_removal(cm, prop: dict[str, Any], active_booking_count: int) -> str:
    city, country = _extract_location(prop)
    title = str(prop.get("title") or prop.get("name") or prop.get("id") or "Unknown property")
    property_id = str(prop.get("id") or prop.get("property_id") or "").strip()
    host_id = str(prop.get("hostId") or prop.get("host_id") or "").strip()
    summary = f"Remove property {property_id} ({title})"
    lines = [
        "## Property Removal Request",
        "",
        "**Requested by:** Host operator  ",
        f"**Date:** {datetime.now(timezone.utc).date().isoformat()}",
        "",
        "**Property to remove:**",
        f"- ID: `{property_id}`",
        f"- Title: {title}",
    ]
    if city or country:
        lines.append(f"- Location: {', '.join(part for part in [city, country] if part)}")
    if host_id:
        lines.append(f"- Host ID: `{host_id}`")
    lines.extend(
        [
            f"- Active or upcoming bookings at request time: {active_booking_count}",
            "",
            "**Action required:** Permanently remove this property from the Minpaku portfolio on admin approval.",
        ]
    )
    content = "\n".join(lines)
    entry_id = cm.create_staging_entry(
        summary=summary,
        content=content,
        category="properties",
        source="operator",
    )
    booking_note = (
        "No active or upcoming bookings on this property."
        if active_booking_count == 0
        else f"{active_booking_count} active or upcoming booking(s) still exist."
    )
    return "\n".join(
        [
            f"Removal request logged to staging (`{entry_id[:8]}`). Summary:",
            "",
            f"- **Property:** {title} (`{property_id}`)",
            "- **Status:** Pending admin review — approval will execute the Minpaku property delete.",
            f"- **Bookings check:** {booking_note}",
            f"- **Staging ID:** `{entry_id}`",
        ]
    )


def _parse_property_removal_request(content: str) -> dict[str, str | int | None]:
    property_id = re.search(r"- ID:\s*`([^`]+)`", content)
    title = re.search(r"- Title:\s*(.+)", content)
    location = re.search(r"- Location:\s*(.+)", content)
    host_id = re.search(r"- Host ID:\s*`([^`]+)`", content)
    booking_count = re.search(r"- Active or upcoming bookings at request time:\s*(\d+)", content)
    return {
        "property_id": property_id.group(1).strip() if property_id else None,
        "title": title.group(1).strip() if title else None,
        "location": location.group(1).strip() if location else None,
        "host_id": host_id.group(1).strip() if host_id else None,
        "active_booking_count": int(booking_count.group(1)) if booking_count else None,
    }


def _parse_listing_draft_for_review(entry: dict[str, Any]) -> dict[str, Any] | None:
    if entry.get("category") != "listing_publications":
        return None
    try:
        return _extract_listing_payload(entry.get("content", ""))
    except Exception:
        return None


def _normalize_match_key(prop: dict[str, Any]) -> tuple[str, str, str]:
    title = str(prop.get("title") or prop.get("name") or "").strip().lower()
    city, country = _extract_location(prop)
    return title, city.strip().lower(), country.strip().lower()


def _resolve_listing_property_id(client: MinpakuClient, payload: dict[str, Any]) -> tuple[str | None, str | None]:
    property_id = str(payload.get("propertyId") or "").strip()
    if property_id:
        return property_id, None
    source_ref = str(payload.get("source_property_ref") or "").strip()
    if not source_ref:
        return None, "Please provide either property_id or source_property_ref for the listing."
    matches = client.search_properties(source_ref)
    if not matches:
        return None, f"No Minpaku property matched '{source_ref}'."
    if len(matches) > 1:
        return None, f"Multiple properties matched '{source_ref}'. Please provide property_id."
    resolved = str(matches[0].get("id") or matches[0].get("property_id") or "").strip()
    if not resolved:
        return None, f"Matched property for '{source_ref}' is missing an ID."
    return resolved, None


def _flatten_listing_rows(rows: Any) -> list[dict[str, Any]]:
    flattened: list[dict[str, Any]] = []

    def _walk(value: Any) -> None:
        if isinstance(value, dict):
            flattened.append(value)
            return
        if isinstance(value, list):
            for item in value:
                _walk(item)

    _walk(rows)
    return flattened


def _format_listing_action_result(action: str, result: dict[str, Any]) -> str:
    if not result.get("ok"):
        return str(result.get("error") or f"Minpaku {action} failed.")
    title = str(result.get("title") or "listing")
    listing_id = str(result.get("listing_id") or "(unknown)")
    property_id = str(result.get("property_id") or "(unknown)")
    if action == "publish":
        return (
            f"Published `{title}` live in Minpaku.\n\n"
            f"- Listing ID: `{listing_id}`\n"
            f"- Property ID: `{property_id}`\n"
            f"- Draft entry: `{result.get('entry_id')}`"
        )
    if action == "update":
        return (
            f"Updated the live Minpaku listing for `{title}`.\n\n"
            f"- Listing ID: `{listing_id}`\n"
            f"- Property ID: `{property_id}`\n"
            f"- Draft entry: `{result.get('entry_id')}`"
        )
    return (
        f"Unlisted `{title}` from Minpaku.\n\n"
        f"- Listing ID: `{listing_id}`\n"
        f"- Property ID: `{property_id}`\n"
        f"- Draft entry: `{result.get('entry_id')}`"
    )


def _format_booking_confirmation_result(result: dict[str, Any], booking_id: str) -> str:
    if result.get("ok") is False:
        return (
            "Booking confirmation is a Minpaku operator approval.\n\n"
            f"I couldn't confirm booking `{booking_id}`: {result.get('error', 'Unknown error')}"
        )
    booking = result.get("booking", {})
    confirmation = result.get("confirmation", {})
    payment_intent = result.get("paymentIntent", {})
    confirmed_id = booking.get("id") or booking_id
    status = booking.get("status") or "CONFIRMED"
    payment_status = payment_intent.get("status") or "SUCCEEDED"
    confirmation_id = confirmation.get("confirmationId") or f"CONF-{confirmed_id}"
    return (
        f"Confirmed booking `{confirmed_id}` after payment verification.\n\n"
        f"- Status: `{status}`\n"
        f"- Payment: `{payment_status}`\n"
        f"- Confirmation ID: `{confirmation_id}`"
    )


def maybe_handle_message(message: str, cm, role_name: str = "operator") -> str | None:
    if not _is_operator_role(role_name):
        return None
    text = " ".join(message.strip().split())
    lowered = text.lower()
    if not text:
        return None

    config_error = _check_config()
    if config_error:
        return None

    price_update = _parse_price_update_request(text)
    if price_update:
        try:
            client = MinpakuClient()
            prop, found_via_search = _find_property_for_query(client, price_update["target"])
            if prop is None:
                return f"I couldn't find a Minpaku property matching '{price_update['target']}'."
            property_id = str(prop.get("id") or prop.get("property_id") or "").strip()
            full_prop = _load_full_property_record(client, prop)
            currency = (
                price_update["currency_hint"]
                or str(full_prop.get("currency") or prop.get("currency") or "HKD")
            )
            update_payload = _build_property_update_payload(full_prop, price_update["nightly_price"], currency)
            client.update_property(property_id, update_payload)
            stage_id = _stage_price_update_note(cm, full_prop, price_update["nightly_price"], currency)
            note = _safe_active_listing_note(client, property_id, price_update["target"])
            title = str(full_prop.get("title") or prop.get("title") or prop.get("name") or property_id)
            return "\n".join(
                [
                    f"Done — I updated the live property price for `{title}` to `{currency} {price_update['nightly_price']:.0f}/night`.",
                    "",
                    f"- Property matched: `{title}` (`{property_id}`)",
                    f"- Match source: `{'search' if found_via_search else 'inventory fallback'}`",
                    f"- Staged update ID: `{stage_id}`",
                    note,
                ]
            )
        except Exception as exc:
            return f"I found the Minpaku property, but the live property price update failed: {exc}"

    property_edit = _parse_property_edit_request(text)
    if property_edit:
        try:
            client = MinpakuClient()
            prop, found_via_search = _find_property_for_query(client, property_edit["target"])
            if prop is None:
                return f"I couldn't find a Minpaku property matching '{property_edit['target']}'."
            property_id = str(prop.get("id") or prop.get("property_id") or "").strip()
            full_prop = _load_full_property_record(client, prop)
            field = property_edit["field"]
            value = property_edit["value"]
            changes: dict[str, Any] = {field: value}
            payload = _build_property_update_payload_from_changes(full_prop, changes)
            client.update_property(property_id, payload)
            stage_id = _stage_property_edit_note(cm, full_prop, field, value)
            title = str(full_prop.get("title") or prop.get("title") or prop.get("name") or property_id)
            return "\n".join(
                [
                    f"Done — I updated the live property `{title}`.",
                    "",
                    f"- Property matched: `{title}` (`{property_id}`)",
                    f"- Match source: `{'search' if found_via_search else 'inventory fallback'}`",
                    f"- Field changed: `{field}`",
                    f"- New value: `{value}`",
                    f"- Staged update ID: `{stage_id}`",
                ]
            )
        except Exception as exc:
            return f"I found the Minpaku property, but the live property update failed: {exc}"

    if (
        "show bookings needing payment confirmation" in lowered
        or "show bookings awaiting payment confirmation" in lowered
        or "show bookings awaiting confirmation" in lowered
    ):
        try:
            client = MinpakuClient()
            properties = client.list_properties()
            pending_rows: list[str] = []
            for prop in properties:
                property_id = str(prop.get("id") or prop.get("property_id") or "").strip()
                if not property_id:
                    continue
                property_title = str(prop.get("title") or prop.get("name") or property_id)
                payload = client.get_bookings_by_property(property_id)
                for booking in _extract_bookings(payload):
                    status = str(booking.get("status") or "").upper()
                    if status not in {"PENDING", "HOLD"}:
                        continue
                    booking_id = str(booking.get("id") or "").strip() or "(unknown)"
                    guest = booking.get("guest") or {}
                    guest_name = str(guest.get("name") or "Unknown guest")
                    check_in = str(booking.get("checkIn") or "?")
                    check_out = str(booking.get("checkOut") or "?")
                    pending_rows.append(
                        f"- `{booking_id}` — {property_title} | guest `{guest_name}` | {check_in} to {check_out} | status `{status}`"
                    )
            if pending_rows:
                return "\n".join(
                    [
                        f"Bookings needing operator confirmation ({len(pending_rows)} total):",
                        "",
                        *pending_rows,
                        "",
                        "Next: say `confirm booking <booking-id> after payment verified` for the one you want to confirm.",
                    ]
                )
            return (
                "There are no live bookings currently waiting for payment confirmation.\n\n"
                "When a booking is in `PENDING` or `HOLD`, ask me again with `show bookings needing payment confirmation`."
            )
        except Exception:
            return None

    if "show all property" in lowered or "show all properties" in lowered:
        try:
            client = MinpakuClient()
            properties = client.list_properties()
            if properties:
                lines = [f"Here are all properties ({len(properties)} total):", ""]
                for prop in properties:
                    property_id = str(prop.get("id") or prop.get("property_id") or "(unknown)")
                    title = str(prop.get("title") or prop.get("name") or "(untitled property)")
                    city, country = _extract_location(prop)
                    location = ", ".join(part for part in [city, country] if part) or "(unknown location)"
                    guests = prop.get("maxGuests") or prop.get("capacity") or "?"
                    nightly = prop.get("nightlyPrice") or prop.get("price") or "?"
                    currency = prop.get("currency") or "HKD"
                    lines.append(
                        f"- `{property_id}` — {title} (`{location}`) — {guests} guest{'s' if str(guests) != '1' else ''} — `{currency} {nightly}/night`"
                    )
                return "\n".join(lines)
            return "No live Minpaku properties right now (`count: 0`)."
        except Exception:
            return None

    if "show all listing" in lowered or "show all listings" in lowered:
        try:
            client = MinpakuClient()
            listings = _flatten_listing_rows(client.list_listings())
            if listings:
                lines = [f"Here are all live listings ({len(listings)} total):", ""]
                for listing in listings:
                    title = str(listing.get("title") or "(untitled listing)")
                    listing_id = str(listing.get("id") or "(unknown)")
                    property_id = str(listing.get("propertyId") or "(unknown)")
                    platform = str(listing.get("platform") or "direct")
                    status = str(listing.get("status") or "active")
                    lines.append(
                        f"- `{listing_id}` — {title} | property `{property_id}` | platform `{platform}` | status `{status}`"
                    )
                approved = [
                    entry for entry in cm.list_staging()
                    if entry.get("category") == "listing_publications" and entry.get("status") == "approved"
                ]
                if approved:
                    lines.extend(
                        [
                            "",
                            f"You also have {len(approved)} staged listing draft(s). Say `publish the latest listing draft` to publish the next one from this operator session.",
                        ]
                    )
                return "\n".join(lines)

            approved = [
                entry for entry in cm.list_staging()
                if entry.get("category") == "listing_publications" and entry.get("status") == "approved"
            ]
            unconfirmed = [
                entry for entry in cm.list_staging()
                if entry.get("category") == "listing_publications" and entry.get("status") == "unconfirmed"
            ]
            lines = ["No live listings right now (`count: 0`).", ""]
            if approved:
                lines.append(
                    f"You have {len(approved)} staged listing draft(s). Next: say `publish the latest listing draft` to make the next one live."
                )
            elif unconfirmed:
                lines.append(
                    f"You have {len(unconfirmed)} unconfirmed listing draft(s). They are already available for Minpaku operator work. Next: say `publish the latest listing draft` to make the next one live."
                )
            else:
                lines.append("Next: prepare a listing draft in `sc`, then say `publish the latest listing draft` here.")
            return "\n".join(lines)
        except Exception:
            return None

    if "publish" in lowered and "listing" in lowered:
        actionable = _actionable_listing_entries(cm)
        if actionable:
            target_query = _extract_listing_action_target(text, lowered, "publish")
            if target_query:
                target = _resolve_listing_target_by_query(cm, target_query)
                if target is None:
                    return None
                return _format_listing_action_result("publish", publish_minpaku_listing(cm, target["id"]))
            latest = actionable[-1]
            return _format_listing_action_result("publish", publish_minpaku_listing(cm, latest["id"]))
        return (
            "There is no listing draft ready to publish yet.\n\n"
            "Next: prepare a listing draft in `sc`, then say `publish the latest listing draft`."
        )

    if "update" in lowered and "listing" in lowered:
        actionable = _actionable_listing_entries(cm)
        if actionable:
            target_query = _extract_listing_action_target(text, lowered, "update")
            if target_query:
                target = _resolve_listing_target_by_query(cm, target_query)
                if target is None:
                    return None
                return _format_listing_action_result("update", update_minpaku_listing(cm, target["id"]))
            latest = actionable[-1]
            return _format_listing_action_result("update", update_minpaku_listing(cm, latest["id"]))
        return (
            "There is no listing draft ready to update yet.\n\n"
            "Next: stage the listing change in `sc`, then say `update the latest listing draft`."
        )

    if ("unlist" in lowered or ("remove" in lowered and "listing" in lowered) or ("delete" in lowered and "listing" in lowered)) and "property" not in lowered:
        actionable = _actionable_listing_entries(cm)
        if actionable:
            target_query = _extract_listing_action_target(text, lowered, "unlist")
            if target_query:
                target = _resolve_listing_target_by_query(cm, target_query)
                if target is None:
                    return None
                return _format_listing_action_result("unlist", delete_minpaku_listing(cm, target["id"]))
            latest = actionable[-1]
            return _format_listing_action_result("unlist", delete_minpaku_listing(cm, latest["id"]))
        return (
            "There is no listing draft ready to unlist.\n\n"
            "Next: stage the unlisting change in `sc`, then say `unlist the latest listing draft`."
        )

    if "confirm" in lowered and "booking" in lowered:
        booking_match = re.search(
            r"\bconfirm\s+booking(?:\s+id)?\s+(?P<booking_id>[A-Za-z0-9-]{6,})\b",
            text,
            flags=re.IGNORECASE,
        )
        if booking_match and "payment" in lowered and any(token in lowered for token in ("verified", "received", "cleared")):
            booking_id = booking_match.group("booking_id")
            try:
                result = MinpakuClient().confirm_booking(booking_id)
            except Exception as exc:
                return _format_booking_confirmation_result({"ok": False, "error": str(exc)}, booking_id)
            return _format_booking_confirmation_result(result, booking_id)
        if "payment" in lowered and any(token in lowered for token in ("verified", "received", "cleared")):
            return (
                "Booking confirmation is a Minpaku operator approval, not a simply-connect framework approval.\n\n"
                "If payment has been verified, this booking is ready for operator confirmation.\n"
                "If you already have the booking ID, say `confirm booking <booking-id> after payment verified`.\n"
                "Use `show bookings for <property>` if you want me to review the live booking details before you confirm it."
            )
        return (
            "Booking confirmation is a Minpaku operator approval.\n\n"
            "Confirm a booking only after payment is verified. If payment is still pending, keep the booking on hold.\n"
            "Once you have the booking ID, say `confirm booking <booking-id> after payment verified`."
        )

    if not any(keyword in lowered for keyword in ("remove ", "delete ")):
        return None
    if "property" not in lowered and "harbour" not in lowered and "prop-" not in lowered:
        return None

    query = re.sub(r"^(remove|delete)\s+", "", text, flags=re.IGNORECASE).strip(" .")
    try:
        client = MinpakuClient()
        properties, _found_via_search = _search_property_matches(client, query)
        if not properties:
            return f"I couldn't find a Minpaku property matching '{query}'."
        prop = _resolve_unique_property_match(properties, query)
        if prop is None:
            return None
        property_id = str(prop.get("id") or prop.get("property_id") or "").strip()
        bookings_payload = client.get_bookings_by_property(property_id)
        active_booking_count = _count_active_or_upcoming_bookings(bookings_payload)
        return _stage_property_removal(cm, prop, active_booking_count)
    except Exception:
        return None


def review_staging_entry(cm, entry: dict) -> dict[str, Any] | None:
    listing_payload = _parse_listing_draft_for_review(entry)
    if listing_payload is not None:
        config_error = _check_config()
        if config_error:
            return {
                "recommendation": "defer",
                "reason": config_error,
                "conflicts": [config_error],
                "suggested_category": entry.get("category", "listing_publications"),
                "confidence": 0.95,
            }
        try:
            client = MinpakuClient()
            property_id = str(listing_payload.get("propertyId") or "").strip()
            platform = str(listing_payload.get("platform") or "").strip().lower()
            live_matches = _flatten_listing_rows(
                (
                client.list_listings(property_id=property_id)
                if property_id
                else client.search_listings(listing_payload.get("source_property_ref", ""))
                )
            )
            exact_matches = [
                listing for listing in live_matches
                if str(listing.get("propertyId") or "").strip() == property_id
                and str(listing.get("platform") or "").strip().lower() == platform
            ]
            if len(exact_matches) > 1:
                return {
                    "recommendation": "defer",
                    "reason": "Multiple live Minpaku listings already match this property/platform pair, so approving this draft may create a duplicate listing.",
                    "conflicts": [f"{len(exact_matches)} live Minpaku listings match property {property_id} on platform {platform or '(unspecified)' }."],
                    "suggested_category": entry.get("category", "listing_publications"),
                    "confidence": 0.97,
                }
            return {
                "recommendation": "approve",
                "reason": "No conflicting live duplicate listing was found; historical removed-property notes do not block a new listing draft.",
                "conflicts": [],
                "suggested_category": entry.get("category", "listing_publications"),
                "confidence": 0.97,
            }
        except Exception as exc:
            return {
                "recommendation": "defer",
                "reason": f"Unable to validate live duplicate risk for this listing draft: {exc}",
                "conflicts": [str(exc)],
                "suggested_category": entry.get("category", "listing_publications"),
                "confidence": 0.8,
            }

    if "## Property Removal Request" not in entry.get("content", ""):
        return None

    parsed = _parse_property_removal_request(entry.get("content", ""))
    property_id = parsed.get("property_id")
    if not property_id:
        return {
            "recommendation": "defer",
            "reason": "Property removal request is missing a property ID.",
            "conflicts": ["No property ID was captured for this removal request."],
            "suggested_category": entry.get("category", "properties"),
            "confidence": 0.95,
        }

    config_error = _check_config()
    if config_error:
        return {
            "recommendation": "defer",
            "reason": config_error,
            "conflicts": [config_error],
            "suggested_category": entry.get("category", "properties"),
            "confidence": 0.95,
        }

    try:
        client = MinpakuClient()
        properties = client.search_properties(property_id)
        if not properties:
            return {
                "recommendation": "defer",
                "reason": "The remote Minpaku property could not be found during review.",
                "conflicts": [f"Remote property {property_id} was not found."],
                "suggested_category": entry.get("category", "properties"),
                "confidence": 0.95,
            }
        active_booking_count = parsed.get("active_booking_count")
        if active_booking_count is None:
            bookings_payload = client.get_bookings_by_property(property_id)
            active_booking_count = _count_active_or_upcoming_bookings(bookings_payload)
        if active_booking_count:
            return {
                "recommendation": "defer",
                "reason": "The property still has active or upcoming bookings and should not be deleted yet.",
                "conflicts": [f"{active_booking_count} active or upcoming booking(s) remain on the property."],
                "suggested_category": entry.get("category", "properties"),
                "confidence": 0.98,
            }
        return {
            "recommendation": "approve",
            "reason": "The remote property exists and has no active or upcoming bookings, so deletion is safe.",
            "conflicts": [],
            "suggested_category": entry.get("category", "properties"),
            "confidence": 0.99,
        }
    except Exception as exc:
        return {
            "recommendation": "defer",
            "reason": f"Unable to verify remote property deletion safety: {exc}",
            "conflicts": [str(exc)],
            "suggested_category": entry.get("category", "properties"),
            "confidence": 0.8,
        }


def on_staging_approved(cm, entry: dict) -> dict[str, Any] | None:
    if "## Property Removal Request" not in entry.get("content", ""):
        return None

    parsed = _parse_property_removal_request(entry.get("content", ""))
    property_id = parsed.get("property_id")
    if not property_id:
        return {"ok": False, "error": "Approved property removal request is missing a property ID."}
    config_error = _check_config()
    if config_error:
        return {"ok": False, "error": config_error}
    try:
        MinpakuClient().delete_property(property_id, host_id=parsed.get("host_id"))
        timestamp = datetime.now(timezone.utc).isoformat()
        city_country = parsed.get("location") or "(unknown location)"
        removal_note = "\n".join(
            [
                f"## Removed Property — {parsed.get('title') or property_id}",
                f"- Remote property ID: {property_id}",
                f"- Deleted at: {timestamp}",
                f"- Location: {city_country}",
            ]
        )
        cm.update_committed("properties", removal_note)
        return {
            "ok": True,
            "message": f"Deleted Minpaku property {property_id}.",
            "property_id": property_id,
            "deleted_property_id": property_id,
        }
    except Exception as exc:
        return {"ok": False, "error": f"Minpaku property delete failed: {exc}"}


def _check_config() -> str | None:
    if not os.getenv("MINPAKU_API_URL") and not os.getenv("MINPAKU_BASE_URL"):
        return "MINPAKU_API_URL not configured — set in .env (e.g. MINPAKU_API_URL=https://your-minpaku-instance.com)"
    return None


def _listing_context_block(payload: dict[str, Any], listing_id: str, action_label: str) -> str:
    timestamp = datetime.now(timezone.utc).isoformat()
    lines = [
        f"## {payload['title']}",
        f"- Remote listing ID: {listing_id}",
        f"- Property ID: {payload.get('propertyId')}",
        f"- Source property ref: {payload.get('source_property_ref', '(not provided)')}",
        f"- Platform: {payload.get('platform', 'direct')}",
        f"- {action_label}: {timestamp}",
    ]
    if payload.get("externalId"):
        lines.append(f"- External ID: {payload['externalId']}")
    if payload.get("nightlyPrice") is not None:
        lines.append(f"- Nightly price override: {payload.get('nightlyPrice')} {payload.get('currency')}")
    if payload.get("status"):
        lines.append(f"- Status: {payload.get('status')}")
    if payload.get("contact"):
        lines.append(f"- Contact: {payload['contact']}")
    if payload.get("description"):
        lines.append(f"- Description: {payload['description']}")
    return "\n".join(lines)


def _replace_committed_record(markdown: str, existing_section: str, new_section: str) -> str:
    if existing_section not in markdown:
        return markdown.rstrip() + "\n\n" + new_section.strip() + "\n"
    return markdown.replace(existing_section, new_section.strip())


def _extract_listing_payload(content: str) -> dict[str, Any]:
    match = re.search(r"```json\s*(\{.*?\})\s*```", content, re.DOTALL)
    if not match:
        raise ValueError("Approved listing draft is missing its JSON payload.")
    return json.loads(match.group(1))


def _actionable_listing_entries(cm) -> list[dict[str, Any]]:
    return [
        entry for entry in cm.list_staging()
        if entry.get("category") == "listing_publications" and entry.get("status") in {"unconfirmed", "approved", "published", "updated"}
    ]


def _normalize_listing_ref(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def _resolve_listing_target_by_query(cm, query: str) -> dict[str, Any] | None:
    listing_entries = _actionable_listing_entries(cm)
    if not listing_entries:
        return None
    normalized_query = _normalize_listing_ref(query)
    if not normalized_query:
        return None

    exact_matches: list[dict[str, Any]] = []
    partial_matches: list[dict[str, Any]] = []

    for entry in listing_entries:
        payload = _extract_listing_payload(entry["content"])
        candidates = [
            str(entry.get("id") or ""),
            str(payload.get("title") or ""),
            str(payload.get("propertyId") or ""),
            str(payload.get("source_property_ref") or ""),
            str(entry.get("summary") or ""),
        ]
        normalized_candidates = [_normalize_listing_ref(candidate) for candidate in candidates if candidate]
        if normalized_query in normalized_candidates:
            exact_matches.append(entry)
            continue
        if any(normalized_query in candidate or candidate in normalized_query for candidate in normalized_candidates):
            partial_matches.append(entry)

    if len(exact_matches) == 1:
        return exact_matches[0]
    if len(exact_matches) > 1:
        return None
    if len(partial_matches) == 1:
        return partial_matches[0]
    return None


def _extract_listing_action_target(text: str, lowered: str, action: str) -> str | None:
    if "latest approved listing" in lowered or "latest listing draft" in lowered:
        return None
    patterns = {
        "publish": r"\bpublish\b\s+(?:the\s+)?(?:approved\s+)?listing(?:\s+draft)?(?:\s+for)?\s+(?P<target>.+)$",
        "update": r"\bupdate\b\s+(?:the\s+)?(?:approved\s+)?listing(?:\s+draft)?(?:\s+for)?\s+(?P<target>.+)$",
        "unlist": r"\b(?:unlist|remove|delete)\b\s+(?:the\s+)?(?:approved\s+)?listing(?:\s+draft)?(?:\s+for)?\s+(?P<target>.+)$",
    }
    match = re.search(patterns[action], text, re.IGNORECASE)
    if not match:
        return None
    return match.group("target").strip(" `.?")


def _resolve_listing_target(cm, entry_id: str | None = None) -> tuple[dict[str, Any] | None, list[dict[str, str]]]:
    listing_entries = _actionable_listing_entries(cm)
    available_entries = [{"id": entry["id"], "summary": entry.get("summary", "")} for entry in listing_entries]
    if not listing_entries:
        return None, available_entries
    if entry_id:
        for entry in listing_entries:
            if entry["id"] == entry_id:
                return entry, available_entries
        return None, available_entries
    listing_entries.sort(key=lambda entry: entry.get("captured", ""))
    return listing_entries[-1], available_entries


def _find_committed_listing_record(markdown: str, payload: dict[str, Any]) -> dict[str, str] | None:
    if not markdown.strip():
        return None
    sections = re.split(r"(?=^## )", markdown, flags=re.MULTILINE)
    source_ref = payload.get("source_property_ref", "")
    title = payload.get("title", "")
    for section in sections:
        if not section.strip().startswith("## "):
            continue
        title_line = section.splitlines()[0][3:].strip()
        remote_match = re.search(r"- Remote listing ID:\s*(.+)", section)
        property_match = re.search(r"- Property ID:\s*(.+)", section)
        source_match = re.search(r"- Source property ref:\s*(.+)", section)
        platform_match = re.search(r"- Platform:\s*(.+)", section)
        if not remote_match:
            continue
        remote_listing_id = remote_match.group(1).strip()
        property_id = property_match.group(1).strip() if property_match else ""
        source_value = source_match.group(1).strip() if source_match else ""
        platform_value = platform_match.group(1).strip() if platform_match else ""
        if source_ref and source_value == source_ref and platform_value == payload.get("platform", "direct"):
            return {"remote_listing_id": remote_listing_id, "property_id": property_id, "title": title_line, "section": section}
        if title and title_line == title:
            return {"remote_listing_id": remote_listing_id, "property_id": property_id, "title": title_line, "section": section}
    return None


def _parse_committed_listing_section(section: str) -> dict[str, Any]:
    title_line = section.splitlines()[0][3:].strip()
    property_match = re.search(r"- Property ID:\s*(.+)", section)
    platform_match = re.search(r"- Platform:\s*(.+)", section)
    external_match = re.search(r"- External ID:\s*(.+)", section)
    nightly_match = re.search(r"- Nightly price override:\s*([0-9.]+)\s+(.+)", section)
    status_match = re.search(r"- Status:\s*(.+)", section)
    contact_match = re.search(r"- Contact:\s*(.+)", section)
    description_match = re.search(r"- Description:\s*(.+)", section)
    return {
        "title": title_line,
        "propertyId": property_match.group(1).strip() if property_match else None,
        "platform": platform_match.group(1).strip() if platform_match else None,
        "externalId": external_match.group(1).strip() if external_match else None,
        "nightlyPrice": float(nightly_match.group(1)) if nightly_match else None,
        "currency": nightly_match.group(2).strip() if nightly_match else None,
        "status": status_match.group(1).strip() if status_match else None,
        "contact": contact_match.group(1).strip() if contact_match else None,
        "description": description_match.group(1).strip() if description_match else None,
    }


def _is_equivalent_listing_payload(payload: dict[str, Any], section: str) -> bool:
    committed = _parse_committed_listing_section(section)
    return (
        committed["title"] == payload.get("title")
        and committed["propertyId"] == payload.get("propertyId")
        and committed["platform"] == payload.get("platform")
        and (committed["externalId"] or None) == (payload.get("externalId") or None)
        and committed["nightlyPrice"] == payload.get("nightlyPrice")
        and committed["currency"] == payload.get("currency")
        and (committed["status"] or None) == (payload.get("status") or None)
        and (committed["contact"] or None) == (payload.get("contact") or None)
        and (committed["description"] or None) == (payload.get("description") or None)
    )


def _payload_from_args(args: dict[str, Any]) -> dict[str, Any]:
    return {
        "propertyId": str(args.get("property_id") or "").strip() or None,
        "title": str(args.get("title") or "").strip(),
        "description": str(args.get("description") or "").strip() or None,
        "platform": str(args.get("platform") or "direct").strip(),
        "externalId": str(args.get("external_id") or "").strip() or None,
        "nightlyPrice": args.get("nightly_price"),
        "currency": str(args.get("currency") or "JPY"),
        "status": str(args.get("status") or "active").strip(),
        "contact": str(args.get("contact") or "").strip() or None,
        "source_property_ref": str(args.get("source_property_ref") or "").strip(),
    }


def _missing_listing_fields(payload: dict[str, Any]) -> list[str]:
    required = {
        "source property reference": payload.get("source_property_ref") or payload.get("propertyId"),
        "platform": payload.get("platform"),
        "title": payload.get("title"),
    }
    return [label for label, value in required.items() if value in (None, "", [])]


def dispatch(name: str, args: dict, cm) -> str:
    client = MinpakuClient()

    if name not in ("list_properties", "search_properties", "get_bookings_by_property", "list_listings", "search_listings", "prepare_minpaku_listing"):
        raise ValueError(f"Minpaku extension does not handle tool: {name}")

    try:
        if name == "list_properties":
            config_error = _check_config()
            if config_error:
                return json.dumps({"error": config_error})
            result = client.list_properties()
            return json.dumps({"properties": result, "count": len(result)}, ensure_ascii=False)

        if name == "search_properties":
            config_error = _check_config()
            if config_error:
                return json.dumps({"error": config_error})
            query = args.get("query", "")
            result = client.search_properties(query)
            return json.dumps({"properties": result, "count": len(result), "query": query}, ensure_ascii=False)

        if name == "get_bookings_by_property":
            config_error = _check_config()
            if config_error:
                return json.dumps({"error": config_error})
            property_id = args.get("property_id", "")
            result = client.get_bookings_by_property(property_id)
            return json.dumps({"bookings": result, "property_id": property_id}, ensure_ascii=False)

        if name == "list_listings":
            config_error = _check_config()
            if config_error:
                return json.dumps({"error": config_error})
            result = _flatten_listing_rows(client.list_listings())
            return json.dumps({"listings": result, "count": len(result)}, ensure_ascii=False)

        if name == "search_listings":
            config_error = _check_config()
            if config_error:
                return json.dumps({"error": config_error})
            query = args.get("query", "")
            result = _flatten_listing_rows(client.search_listings(query))
            return json.dumps({"listings": result, "count": len(result), "query": query}, ensure_ascii=False)

        payload = _payload_from_args(args)
        missing = _missing_listing_fields(payload)
        if missing:
            return json.dumps(
                {
                    "ok": False,
                    "missing_fields": missing,
                    "next_prompt": "Please provide the missing Minpaku listing fields in one message: " + ", ".join(missing) + ".",
                    "draft": payload,
                },
                ensure_ascii=False,
            )

        property_id, resolution_error = _resolve_listing_property_id(client, payload)
        if resolution_error:
            return json.dumps(
                {
                    "ok": False,
                    "missing_fields": ["property_id"],
                    "next_prompt": resolution_error,
                    "draft": payload,
                },
                ensure_ascii=False,
            )
        payload["propertyId"] = property_id

        current_markdown = cm.load_committed().get("listing_publications", "")
        existing_record = _find_committed_listing_record(current_markdown, payload)
        if existing_record and _is_equivalent_listing_payload(payload, existing_record["section"]):
            return json.dumps(
                {
                    "ok": True,
                    "staged": False,
                    "already_exists": True,
                    "summary": f"An identical Minpaku listing is already committed for {payload['title']}.",
                    "draft": payload,
                    "remote_listing_id": existing_record["remote_listing_id"],
                },
                ensure_ascii=False,
            )

        live_payload = {
            "propertyId": payload["propertyId"],
            "platform": payload["platform"],
            "externalId": payload.get("externalId"),
            "title": payload.get("title"),
            "description": payload.get("description"),
            "nightlyPrice": payload.get("nightlyPrice"),
            "currency": payload.get("currency"),
            "status": "inactive" if str(payload.get("status") or "").strip().lower() == "draft" else payload.get("status"),
            "contact": payload.get("contact"),
        }
        response = client.create_listing(live_payload)

        body = "\n".join(
            [
                f"## Minpaku Listing Draft — {payload['title']}",
                "",
                f"- Property ID: {payload['propertyId']}",
                f"- Source property ref: {payload['source_property_ref']}",
                f"- Platform: {payload['platform']}",
                f"- Status: {payload['status']}",
                f"- Remote listing ID: {response.get('id', '(unknown)')}",
                "",
                "```json",
                json.dumps(payload, indent=2, ensure_ascii=False),
                "```",
            ]
        )
        summary = f"Minpaku listing draft for {payload['title']}"
        entry_id = cm.create_staging_entry(
            summary=summary,
            content=body,
            category="listing_publications",
            source="operator",
        )
        return json.dumps(
            {
                "ok": True,
                "staged": True,
                "entry_id": entry_id,
                "summary": summary,
                "draft": payload,
                "remote_listing_id": response.get("id"),
                "live_status": live_payload.get("status"),
            },
            ensure_ascii=False,
        )
    except Exception as e:
        return json.dumps({"error": f"Minpaku API error: {e}"})


def publish_minpaku_listing(cm, entry_id: str | None = None) -> dict[str, Any]:
    config_error = _check_config()
    if config_error:
        return {"ok": False, "error": config_error}
    target, available_entries = _resolve_listing_target(cm, entry_id)
    if not target:
        return {"ok": False, "error": "No Minpaku listing drafts found.", "available_entries": available_entries}
    if entry_id and not any(entry["id"] == entry_id for entry in available_entries):
        return {"ok": False, "error": "Listing draft not found for that entry ID.", "available_entries": available_entries}
    try:
        payload = _extract_listing_payload(target["content"])
        current_markdown = cm.load_committed().get("listing_publications", "")
        record = _find_committed_listing_record(current_markdown, payload)
        listing_id = None
        if record:
            listing_id = record["remote_listing_id"]
            response = MinpakuClient().update_listing(
                listing_id,
                {
                    "externalId": payload.get("externalId"),
                    "title": payload.get("title"),
                    "description": payload.get("description"),
                    "nightlyPrice": payload.get("nightlyPrice"),
                    "currency": payload.get("currency"),
                    "status": "active",
                    "contact": payload.get("contact"),
                },
            )
            listing_id = response.get("id", listing_id)
            new_section = _listing_context_block(payload | {"status": "active"}, listing_id, "Published at")
            target_path = cm._root / "context" / "listing_publications.md"
            target_path.write_text(_replace_committed_record(current_markdown, record["section"], new_section).rstrip() + "\n", encoding="utf-8")
        else:
            response = MinpakuClient().create_listing(
                {
                    "propertyId": payload["propertyId"],
                    "platform": payload["platform"],
                    "externalId": payload.get("externalId"),
                    "title": payload.get("title"),
                    "description": payload.get("description"),
                    "nightlyPrice": payload.get("nightlyPrice"),
                    "currency": payload.get("currency"),
                    "status": "active",
                    "contact": payload.get("contact"),
                }
            )
            listing_id = response.get("id")
            cm.update_committed("listing_publications", _listing_context_block(payload | {"status": "active"}, listing_id or "(unknown)", "Published at"))
        cm.update_staging_status(target["id"], "published", "admin")
        return {
            "ok": True,
            "entry_id": target["id"],
            "title": payload["title"],
            "listing_id": listing_id,
            "property_id": payload.get("propertyId"),
            "source_property_ref": payload.get("source_property_ref"),
        }
    except Exception as exc:
        return {"ok": False, "error": f"Minpaku publish failed: {exc}", "available_entries": available_entries}


def update_minpaku_listing(cm, entry_id: str | None = None) -> dict[str, Any]:
    config_error = _check_config()
    if config_error:
        return {"ok": False, "error": config_error}
    target, available_entries = _resolve_listing_target(cm, entry_id)
    if not target:
        return {"ok": False, "error": "No Minpaku listing drafts found.", "available_entries": available_entries}
    if entry_id and not any(entry["id"] == entry_id for entry in available_entries):
        return {"ok": False, "error": "Listing draft not found for that entry ID.", "available_entries": available_entries}
    try:
        payload = _extract_listing_payload(target["content"])
        current_markdown = cm.load_committed().get("listing_publications", "")
        record = _find_committed_listing_record(current_markdown, payload)
        if not record:
            return {"ok": False, "error": "No published Minpaku listing record found for this draft. Publish it first.", "available_entries": available_entries}
        response = MinpakuClient().update_listing(
            record["remote_listing_id"],
            {
                "externalId": payload.get("externalId"),
                "title": payload.get("title"),
                "description": payload.get("description"),
                "nightlyPrice": payload.get("nightlyPrice"),
                "currency": payload.get("currency"),
                "status": payload.get("status"),
                "contact": payload.get("contact"),
            },
        )
        new_section = _listing_context_block(payload, response.get("id", record["remote_listing_id"]), "Updated at")
        target_path = cm._root / "context" / "listing_publications.md"
        target_path.write_text(_replace_committed_record(current_markdown, record["section"], new_section).rstrip() + "\n", encoding="utf-8")
        cm.update_staging_status(target["id"], "updated", "admin")
        return {
            "ok": True,
            "entry_id": target["id"],
            "title": payload["title"],
            "listing_id": response.get("id", record["remote_listing_id"]),
            "property_id": payload.get("propertyId"),
            "source_property_ref": payload.get("source_property_ref"),
        }
    except Exception as exc:
        return {"ok": False, "error": f"Minpaku update failed: {exc}", "available_entries": available_entries}


def delete_minpaku_listing(cm, entry_id: str | None = None) -> dict[str, Any]:
    config_error = _check_config()
    if config_error:
        return {"ok": False, "error": config_error}
    target, available_entries = _resolve_listing_target(cm, entry_id)
    if not target:
        return {"ok": False, "error": "No Minpaku listing drafts found.", "available_entries": available_entries}
    if entry_id and not any(entry["id"] == entry_id for entry in available_entries):
        return {"ok": False, "error": "Listing draft not found for that entry ID.", "available_entries": available_entries}
    try:
        payload = _extract_listing_payload(target["content"])
        current_markdown = cm.load_committed().get("listing_publications", "")
        record = _find_committed_listing_record(current_markdown, payload)
        if not record:
            return {"ok": False, "error": "No published Minpaku listing record found for this draft. Publish it first.", "available_entries": available_entries}
        MinpakuClient().delete_listing(record["remote_listing_id"])
        new_section = _listing_context_block(payload, record["remote_listing_id"], "Delisted at")
        target_path = cm._root / "context" / "listing_publications.md"
        target_path.write_text(_replace_committed_record(current_markdown, record["section"], new_section).rstrip() + "\n", encoding="utf-8")
        cm.update_staging_status(target["id"], "deleted", "admin")
        return {
            "ok": True,
            "entry_id": target["id"],
            "title": payload["title"],
            "listing_id": record["remote_listing_id"],
            "property_id": payload.get("propertyId"),
            "source_property_ref": payload.get("source_property_ref"),
        }
    except Exception as exc:
        return {"ok": False, "error": f"Minpaku delete failed: {exc}", "available_entries": available_entries}
