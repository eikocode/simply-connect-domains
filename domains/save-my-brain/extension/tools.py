"""
Save My Brain — Extension Tools

MCP tools for document search, task management, financial summaries,
and expiry date tracking. All data comes from committed context files.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, date
from typing import Any


# ---------------------------------------------------------------------------
# Tool Definitions (MCP schema)
# ---------------------------------------------------------------------------

TOOLS: list[dict] = [
    {
        "name": "search_documents",
        "description": "Search across all processed documents by keyword, type, or date range. Returns matching document summaries.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search keyword or phrase",
                },
                "doc_type": {
                    "type": "string",
                    "description": "Optional filter: receipt, bank_statement, insurance, medical, contract, utility, tax, school, travel, hotel, event, id_document",
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "list_expiry_dates",
        "description": "List all tracked expiry dates and deadlines, sorted by urgency. Shows what needs attention soon.",
        "input_schema": {
            "type": "object",
            "properties": {
                "days_ahead": {
                    "type": "integer",
                    "description": "Show deadlines within this many days (default: 90)",
                },
            },
        },
    },
    {
        "name": "list_tasks",
        "description": "List all tasks by priority. P1 = urgent (≤7 days), P2 = soon (≤30 days), P3 = upcoming (≤90 days).",
        "input_schema": {
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "description": "Filter: pending, done, or all (default: pending)",
                },
            },
        },
    },
    {
        "name": "get_financial_summary",
        "description": "Get a spending summary for a given period. Shows totals by category.",
        "input_schema": {
            "type": "object",
            "properties": {
                "period": {
                    "type": "string",
                    "description": "Period to summarize: 'this_month', 'last_month', or 'YYYY-MM' (default: this_month)",
                },
            },
        },
    },
    {
        "name": "list_family_members",
        "description": "List all family members and their document counts.",
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
]


# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------

def dispatch(name: str, args: dict[str, Any], cm) -> str:
    """Route a tool call to the appropriate handler."""
    if name == "search_documents":
        return _search_documents(args.get("query", ""), args.get("doc_type"), cm)
    elif name == "list_expiry_dates":
        return _list_expiry_dates(args.get("days_ahead", 90), cm)
    elif name == "list_tasks":
        return _list_tasks(args.get("status", "pending"), cm)
    elif name == "get_financial_summary":
        return _get_financial_summary(args.get("period", "this_month"), cm)
    elif name == "list_family_members":
        return _list_family_members(cm)
    raise ValueError(f"Unknown tool: {name}")


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------

def _search_documents(query: str, doc_type: str | None, cm) -> str:
    """Search committed document summaries by keyword and optional type filter."""
    committed = cm.load_committed()
    docs_text = committed.get("documents", "")

    if not docs_text or not query:
        return json.dumps({"matches": [], "count": 0, "query": query})

    # Split into document sections (## headers)
    sections = re.split(r'\n(?=## )', docs_text)
    query_lower = query.lower()

    matches = []
    for section in sections:
        if query_lower in section.lower():
            if doc_type and doc_type.lower() not in section.lower():
                continue
            # Extract first line as title
            title = section.strip().split("\n")[0].lstrip("# ").strip()
            matches.append({"title": title, "excerpt": section.strip()[:300]})

    return json.dumps({
        "query": query,
        "doc_type_filter": doc_type,
        "matches": matches[:10],
        "count": len(matches),
    })


def _list_expiry_dates(days_ahead: int, cm) -> str:
    """Extract dates from calendar context, filter by days_ahead."""
    committed = cm.load_committed()
    calendar_text = committed.get("calendar", "")

    if not calendar_text:
        return json.dumps({"dates": [], "count": 0, "message": "No dates tracked yet."})

    today = date.today()
    dates = []

    # Parse date entries (format: - YYYY-MM-DD: label)
    for match in re.finditer(r'(\d{4}-\d{2}-\d{2})[:\s]+(.+?)(?:\n|$)', calendar_text):
        try:
            d = datetime.strptime(match.group(1), "%Y-%m-%d").date()
            days_until = (d - today).days
            if 0 <= days_until <= days_ahead:
                priority = "P1" if days_until <= 7 else "P2" if days_until <= 30 else "P3" if days_until <= 90 else "P4"
                dates.append({
                    "date": match.group(1),
                    "label": match.group(2).strip(),
                    "days_until": days_until,
                    "priority": priority,
                })
        except ValueError:
            continue

    dates.sort(key=lambda x: x["days_until"])
    return json.dumps({"dates": dates, "count": len(dates), "days_ahead": days_ahead})


def _list_tasks(status_filter: str, cm) -> str:
    """Extract tasks from tasks context file."""
    committed = cm.load_committed()
    tasks_text = committed.get("tasks", "")

    if not tasks_text:
        return json.dumps({"tasks": [], "count": 0, "message": "No tasks yet."})

    tasks = []
    # Parse task entries (format: - [x] or - [ ] P1: task description)
    for match in re.finditer(r'-\s*\[([ xX])\]\s*(P[1-4])?\s*:?\s*(.+?)(?:\n|$)', tasks_text):
        done = match.group(1).lower() == "x"
        status = "done" if done else "pending"
        priority = match.group(2) or "P3"
        description = match.group(3).strip()

        if status_filter == "all" or status_filter == status:
            tasks.append({
                "description": description,
                "priority": priority,
                "status": status,
            })

    # Sort by priority
    priority_order = {"P1": 0, "P2": 1, "P3": 2, "P4": 3}
    tasks.sort(key=lambda t: priority_order.get(t["priority"], 9))

    return json.dumps({"tasks": tasks, "count": len(tasks), "filter": status_filter})


def _get_financial_summary(period: str, cm) -> str:
    """Aggregate spending from finances context file."""
    committed = cm.load_committed()
    finances_text = committed.get("finances", "")

    if not finances_text:
        return json.dumps({"summary": {}, "total": 0, "message": "No financial records yet."})

    # Determine target month
    if period == "this_month":
        target = date.today().strftime("%Y-%m")
    elif period == "last_month":
        today = date.today()
        if today.month == 1:
            target = f"{today.year - 1}-12"
        else:
            target = f"{today.year}-{today.month - 1:02d}"
    else:
        target = period  # Assume YYYY-MM format

    # Parse transactions (format: | date | amount | merchant | category | description |)
    categories = {}
    total = 0.0
    for match in re.finditer(
        r'\|\s*(\d{4}-\d{2}-\d{2})\s*\|\s*([-\d,.]+)\s*\|\s*(.+?)\s*\|\s*(\w+)\s*\|',
        finances_text
    ):
        tx_date = match.group(1)
        if not tx_date.startswith(target):
            continue
        try:
            amount = float(match.group(2).replace(",", ""))
        except ValueError:
            continue
        category = match.group(4).strip()
        categories[category] = categories.get(category, 0) + amount
        total += amount

    return json.dumps({
        "period": target,
        "by_category": categories,
        "total": round(total, 2),
        "transaction_count": sum(1 for _ in re.finditer(r'\|\s*' + re.escape(target), finances_text)),
    })


def _list_family_members(cm) -> str:
    """Extract family members from family context file."""
    committed = cm.load_committed()
    family_text = committed.get("family", "")

    if not family_text:
        return json.dumps({"members": [], "count": 0, "message": "No family members added yet."})

    members = []
    # Parse member entries (format: ## Name\n- Relationship: ...)
    for match in re.finditer(r'## (.+?)\n(.*?)(?=\n## |\Z)', family_text, re.DOTALL):
        name = match.group(1).strip()
        details = match.group(2).strip()
        relationship = ""
        rel_match = re.search(r'Relationship:\s*(.+?)(?:\n|$)', details)
        if rel_match:
            relationship = rel_match.group(1).strip()
        members.append({"name": name, "relationship": relationship})

    return json.dumps({"members": members, "count": len(members)})


# ---------------------------------------------------------------------------
# Optional: Message Interception
# ---------------------------------------------------------------------------

def maybe_handle_message(
    message: str,
    cm,
    role_name: str = "operator",
    history: list[dict] | None = None,
) -> str | None:
    """Deterministically handle specific commands without calling Claude."""
    # No deterministic handlers for now — let Claude handle everything
    # Can add fast-path commands here later (e.g., "tasks", "deadlines")
    return None
