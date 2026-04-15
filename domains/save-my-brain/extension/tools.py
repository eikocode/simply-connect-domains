"""
Save My Brain — Extension Tools

MCP tools for document search, task management, financial summaries,
and expiry date tracking. Data is stored in SQLite (DataOS pattern from
apps/save-my-brain/) at data/smb.db, with human-readable summaries
mirrored to context/documents.md for Claude's committed context.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, date
from typing import Any

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Tool Definitions (MCP schema)
# ---------------------------------------------------------------------------

TOOLS: list[dict] = [
    {
        "name": "search_documents",
        "description": "Search stored documents by keyword or type. Returns matching document summaries from the SQLite database. Empty query lists all documents.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search keyword or phrase (optional — empty lists all)",
                },
                "doc_type": {
                    "type": "string",
                    "description": "Optional filter: receipt, bank_statement, insurance, medical, contract, utility, tax, school, travel, hotel, event, id_document",
                },
            },
        },
    },
    {
        "name": "sum_expenses_by_category",
        "description": "Sum expenses by category for a given period. Use this when the user asks 'how much did I spend on X?' or 'what are my medical/dental/dining expenses?'. Returns total plus itemized list.",
        "input_schema": {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "description": "Expense category: medical, dental, pharmacy, dining, groceries, transport, utilities, shopping, entertainment, education, beauty, fitness, pets, other",
                },
                "period": {
                    "type": "string",
                    "description": "Period: 'this_month', 'last_month', or 'YYYY-MM' (default: this_month)",
                },
            },
            "required": ["category"],
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
        "description": "List all family members in the user's household. Call this FIRST whenever the user mentions a family member by name, or asks about adding/removing/renaming anyone.",
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "add_family_member",
        "description": "Add a new person to the user's household list. Use when the user says 'add X to my family', 'X is my spouse', or similar.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "The name of the person to add",
                },
            },
            "required": ["name"],
        },
    },
    {
        "name": "remove_family_member",
        "description": "Remove a person from the user's household list. Use when the user says 'remove X', 'X is no longer in my household', etc.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "The name of the person to remove",
                },
            },
            "required": ["name"],
        },
    },
    {
        "name": "rename_family_member",
        "description": "Rename/replace a family member. Use when the user says 'replace X with Y', 'rename X to Y', 'X should be Y'.",
        "input_schema": {
            "type": "object",
            "properties": {
                "old_name": {
                    "type": "string",
                    "description": "Current name of the person",
                },
                "new_name": {
                    "type": "string",
                    "description": "New name for the person",
                },
            },
            "required": ["old_name", "new_name"],
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
    elif name == "sum_expenses_by_category":
        return _sum_expenses_by_category(
            args.get("category", ""),
            args.get("period", "this_month"),
            cm,
        )
    elif name == "list_family_members":
        return _list_family_members(cm)
    elif name == "add_family_member":
        return _add_family_member(args.get("name", ""), cm)
    elif name == "remove_family_member":
        return _remove_family_member(args.get("name", ""), cm)
    elif name == "rename_family_member":
        return _rename_family_member(args.get("old_name", ""), args.get("new_name", ""), cm)
    raise ValueError(f"Unknown tool: {name}")


# ---------------------------------------------------------------------------
# DB import helper (works both as package and flat module)
# ---------------------------------------------------------------------------

def _get_db():
    """Import the database helper module lazily."""
    try:
        from . import database as db
        return db
    except ImportError:
        pass
    import importlib, sys
    from pathlib import Path as _P
    ext_dir = _P(__file__).parent
    if str(ext_dir) not in sys.path:
        sys.path.insert(0, str(ext_dir))
    import database as db  # type: ignore
    return db


def _resolve_period(period: str) -> str:
    """Turn 'this_month' / 'last_month' / 'YYYY-MM' into a YYYY-MM string."""
    if period == "this_month":
        return date.today().strftime("%Y-%m")
    if period == "last_month":
        today = date.today()
        if today.month == 1:
            return f"{today.year - 1}-12"
        return f"{today.year}-{today.month - 1:02d}"
    return period  # Assume YYYY-MM


# ---------------------------------------------------------------------------
# Handlers — SQL-backed (DataOS pattern)
# ---------------------------------------------------------------------------

def _search_documents(query: str, doc_type: str | None, cm) -> str:
    """SQL search across smb_documents by filename, summary, or extracted text."""
    db = _get_db()
    conn = db.get_connection(cm)
    try:
        sql = """
            SELECT id, filename, doc_type, summary, uploaded_at
            FROM smb_documents
            WHERE 1=1
        """
        params: list = []
        if query:
            sql += " AND (filename LIKE ? OR summary LIKE ? OR extracted_text LIKE ?)"
            like = f"%{query}%"
            params.extend([like, like, like])
        if doc_type:
            sql += " AND doc_type = ?"
            params.append(doc_type)
        sql += " ORDER BY uploaded_at DESC LIMIT 20"
        rows = conn.execute(sql, params).fetchall()
        matches = [
            {
                "id": r["id"],
                "title": r["filename"],
                "doc_type": r["doc_type"],
                "excerpt": (r["summary"] or "")[:300],
                "uploaded_at": r["uploaded_at"],
            }
            for r in rows
        ]
        return json.dumps({
            "query": query,
            "doc_type_filter": doc_type,
            "matches": matches,
            "count": len(matches),
        }, ensure_ascii=False)
    finally:
        conn.close()


def _list_expiry_dates(days_ahead: int, cm) -> str:
    """Pull upcoming dates from smb_documents (JSON-encoded) + smb_policies.expiry_date."""
    db = _get_db()
    conn = db.get_connection(cm)
    today = date.today()
    upcoming: list[dict] = []

    try:
        # 1. Scan smb_documents.important_dates (JSON array)
        rows = conn.execute(
            "SELECT id, filename, doc_type, important_dates FROM smb_documents "
            "WHERE important_dates IS NOT NULL AND important_dates != '[]'"
        ).fetchall()
        for r in rows:
            try:
                dates_list = json.loads(r["important_dates"] or "[]")
            except json.JSONDecodeError:
                continue
            for d in dates_list:
                date_str = d.get("date", "")
                try:
                    parsed = datetime.strptime(date_str, "%Y-%m-%d").date()
                except ValueError:
                    continue
                days_until = (parsed - today).days
                if 0 <= days_until <= days_ahead:
                    upcoming.append({
                        "date": date_str,
                        "label": d.get("label", ""),
                        "days_until": days_until,
                        "priority": _priority_for_days(days_until),
                        "source": f"{r['doc_type']}: {r['filename']}",
                    })

        # 2. Add insurance policy expiry dates
        policy_rows = conn.execute(
            "SELECT id, insurer, policy_type, expiry_date FROM smb_policies "
            "WHERE expiry_date IS NOT NULL"
        ).fetchall()
        for r in policy_rows:
            try:
                parsed = datetime.strptime(r["expiry_date"], "%Y-%m-%d").date()
            except (ValueError, TypeError):
                continue
            days_until = (parsed - today).days
            if 0 <= days_until <= days_ahead:
                upcoming.append({
                    "date": r["expiry_date"],
                    "label": f"{r['insurer'] or 'Insurance'} ({r['policy_type'] or ''}) expires",
                    "days_until": days_until,
                    "priority": _priority_for_days(days_until),
                    "source": f"policy #{r['id']}",
                })

        upcoming.sort(key=lambda x: x["days_until"])
        return json.dumps({
            "dates": upcoming,
            "count": len(upcoming),
            "days_ahead": days_ahead,
        }, ensure_ascii=False)
    finally:
        conn.close()


def _priority_for_days(days: int) -> str:
    if days <= 7:
        return "P1"
    if days <= 30:
        return "P2"
    if days <= 90:
        return "P3"
    return "P4"


def _list_tasks(status_filter: str, cm) -> str:
    """Tasks come from document action_items (JSON arrays) — SQL query."""
    db = _get_db()
    conn = db.get_connection(cm)
    tasks: list[dict] = []
    try:
        rows = conn.execute(
            "SELECT id, filename, doc_type, action_items, important_dates "
            "FROM smb_documents "
            "WHERE action_items IS NOT NULL AND action_items != '[]'"
        ).fetchall()
        for r in rows:
            try:
                items = json.loads(r["action_items"] or "[]")
                dates_list = json.loads(r["important_dates"] or "[]")
            except json.JSONDecodeError:
                continue
            # Derive priority from the earliest important date
            priority = "P3"
            if dates_list:
                min_days = min(
                    (d.get("days_until", 365) for d in dates_list if d.get("days_until", -1) >= 0),
                    default=365,
                )
                priority = _priority_for_days(min_days)
            for item in items:
                tasks.append({
                    "description": item if isinstance(item, str) else str(item),
                    "priority": priority,
                    "status": "pending",
                    "source": f"{r['doc_type']}: {r['filename']}",
                })

        # Sort by priority
        priority_order = {"P1": 0, "P2": 1, "P3": 2, "P4": 3}
        tasks.sort(key=lambda t: priority_order.get(t["priority"], 9))

        return json.dumps({
            "tasks": tasks,
            "count": len(tasks),
            "filter": status_filter,
        }, ensure_ascii=False)
    finally:
        conn.close()


def _get_financial_summary(period: str, cm) -> str:
    """SUM expenses by category using SQL. Accepts 'this_month', 'last_month', 'YYYY-MM'."""
    db = _get_db()
    target = _resolve_period(period)
    conn = db.get_connection(cm)
    try:
        rows = conn.execute(
            """SELECT category, SUM(amount) as total, COUNT(*) as cnt
               FROM smb_transactions
               WHERE date LIKE ? AND is_income = 0
               GROUP BY category
               ORDER BY total DESC""",
            (f"{target}%",),
        ).fetchall()
        by_category = {r["category"] or "other": round(r["total"] or 0, 2) for r in rows}
        txn_count = sum(r["cnt"] for r in rows)
        total = round(sum(by_category.values()), 2)

        # Also grab income
        income_row = conn.execute(
            "SELECT COALESCE(SUM(amount), 0) as total FROM smb_transactions "
            "WHERE date LIKE ? AND is_income = 1",
            (f"{target}%",),
        ).fetchone()
        income = round(income_row["total"] or 0, 2)

        return json.dumps({
            "period": target,
            "by_category": by_category,
            "total_expenses": total,
            "total_income": income,
            "transaction_count": txn_count,
        }, ensure_ascii=False)
    finally:
        conn.close()


def _sum_expenses_by_category(category: str, period: str, cm) -> str:
    """Fast path: 'what are my medical expenses this month?'"""
    db = _get_db()
    target = _resolve_period(period)
    conn = db.get_connection(cm)
    try:
        rows = conn.execute(
            """SELECT date, amount, merchant, description, currency
               FROM smb_transactions
               WHERE category = ? AND date LIKE ? AND is_income = 0
               ORDER BY date DESC""",
            (category, f"{target}%"),
        ).fetchall()
        items = [
            {
                "date": r["date"],
                "amount": abs(r["amount"] or 0),
                "merchant": r["merchant"],
                "description": r["description"],
                "currency": r["currency"] or "HKD",
            }
            for r in rows
        ]
        total = round(sum(i["amount"] for i in items), 2)
        return json.dumps({
            "category": category,
            "period": target,
            "total": total,
            "count": len(items),
            "items": items[:20],
        }, ensure_ascii=False)
    finally:
        conn.close()


def _list_family_members(cm) -> str:
    """Extract family members from family context file.

    Returns a clear structure distinguishing the primary_user (the person
    talking to the AI) from other household members.
    """
    primary_name, members = _parse_family_md(cm)

    result = {
        "primary_user": {
            "name": primary_name or "unknown",
            "note": "This is the user you are talking to. Do NOT ask them about their own name or relationship.",
        },
        "household_members": [{"name": m["name"]} for m in members],
        "total_count": (1 if primary_name else 0) + len(members),
    }
    return json.dumps(result, ensure_ascii=False)


def _parse_family_md(cm) -> tuple[str, list[dict]]:
    """Parse family.md into (primary_user_line, member_list). Returns ('', []) if missing."""
    family_path = cm._root / "context" / "family.md"
    if not family_path.exists():
        return "", []
    text = family_path.read_text(encoding="utf-8")
    members = []
    primary_name = ""
    primary_role = ""
    for match in re.finditer(r'## (.+?)\n(.*?)(?=\n## |\Z)', text, re.DOTALL):
        name = match.group(1).strip()
        details = match.group(2).strip()
        is_primary = "primary user" in details.lower() or "role: primary" in details.lower()
        if is_primary and not primary_name:
            primary_name = name
            primary_role = "primary user"
        else:
            members.append({"name": name, "details": details})
    return primary_name, members


def _write_family_md(cm, primary_name: str, members: list[dict]):
    """Rewrite family.md from structured data."""
    family_path = cm._root / "context" / "family.md"
    lines = ["# Family\n"]
    lines.append("> Household members. Names only — relationships can be added later.\n")
    if primary_name:
        lines.append(f"## {primary_name}")
        lines.append("- Role: primary user")
        lines.append("")
    for m in members:
        lines.append(f"## {m['name']}")
        lines.append("- Relationship: household member")
        lines.append("")
    family_path.write_text("\n".join(lines), encoding="utf-8")


def _add_family_member(name: str, cm) -> str:
    """Add a new member to family.md."""
    name = (name or "").strip()
    if not name:
        return json.dumps({"success": False, "error": "Name is required"})

    primary, members = _parse_family_md(cm)

    # Check if already exists (case-insensitive)
    existing = [m["name"] for m in members]
    if any(n.lower() == name.lower() for n in existing) or (primary and primary.lower() == name.lower()):
        return json.dumps({
            "success": False,
            "error": f"{name} is already in your household",
            "members": existing,
        })

    # Enforce max 7
    if len(members) >= MAX_FAMILY_MEMBERS:
        return json.dumps({
            "success": False,
            "error": f"Household is full (max {MAX_FAMILY_MEMBERS} people besides yourself)",
            "members": existing,
        })

    members.append({"name": name, "details": "- Relationship: household member"})
    _write_family_md(cm, primary, members)

    return json.dumps({
        "success": True,
        "message": f"Added {name} to household",
        "members": [m["name"] for m in members],
    })


def _remove_family_member(name: str, cm) -> str:
    """Remove a member from family.md by name (case-insensitive)."""
    name = (name or "").strip()
    if not name:
        return json.dumps({"success": False, "error": "Name is required"})

    primary, members = _parse_family_md(cm)

    # Don't allow removing primary user
    if primary and primary.lower() == name.lower():
        return json.dumps({
            "success": False,
            "error": f"Cannot remove {primary} — that's you (the primary user)",
        })

    # Find and remove (case-insensitive)
    filtered = [m for m in members if m["name"].lower() != name.lower()]
    if len(filtered) == len(members):
        return json.dumps({
            "success": False,
            "error": f"{name} is not in your household",
            "members": [m["name"] for m in members],
        })

    _write_family_md(cm, primary, filtered)

    return json.dumps({
        "success": True,
        "message": f"Removed {name} from household",
        "members": [m["name"] for m in filtered],
    })


def _rename_family_member(old_name: str, new_name: str, cm) -> str:
    """Rename a family member (case-insensitive match on old name)."""
    old_name = (old_name or "").strip()
    new_name = (new_name or "").strip()
    if not old_name or not new_name:
        return json.dumps({"success": False, "error": "Both old_name and new_name are required"})

    primary, members = _parse_family_md(cm)

    # Check if old_name is primary user (can rename self)
    if primary and primary.lower() == old_name.lower():
        _write_family_md(cm, new_name, members)
        return json.dumps({
            "success": True,
            "message": f"Renamed {old_name} → {new_name} (primary user)",
        })

    # Find in members list
    found = False
    for m in members:
        if m["name"].lower() == old_name.lower():
            m["name"] = new_name
            found = True
            break

    if not found:
        return json.dumps({
            "success": False,
            "error": f"{old_name} is not in your household",
            "members": [m["name"] for m in members],
        })

    _write_family_md(cm, primary, members)

    return json.dumps({
        "success": True,
        "message": f"Renamed {old_name} → {new_name}",
        "members": [m["name"] for m in members],
    })


# ---------------------------------------------------------------------------
# Optional: Message Interception
# ---------------------------------------------------------------------------

def maybe_handle_message(
    message: str,
    cm,
    role_name: str = "operator",
    history: list[dict] | None = None,
    **kwargs,
) -> str | None:
    """Handle onboarding FSM + fast-path commands."""
    user_id = kwargs.get("user_id")
    if user_id is None:
        return None

    first_name = kwargs.get("first_name", "")

    # Run onboarding FSM
    reply = _onboarding_step(str(user_id), message, cm, first_name=first_name)
    if reply is not None:
        return reply

    return None


def maybe_handle_document(
    file_bytes: bytes,
    filename: str,
    mime_type: str,
    caption: str,
    cm,
    role_name: str = "operator",
    **kwargs,
) -> str | None:
    """
    Handle document uploads with the full AIOS-style intelligence pipeline:
      1. Hash check — detect duplicates before spending Claude tokens
      2. Classify (Claude Haiku) — doc_type, names, currency
      3. Extract (Claude Haiku/Sonnet) — structured data per schema
      4. Write to SQLite tables (smb_documents, smb_transactions, etc.)
      5. Append summary to context/documents.md for Claude's context window
      6. Return formatted response with smart categorization

    Returns None (falls through to default staging) only if onboarding isn't done.
    """
    user_id = str(kwargs.get("user_id", ""))
    if not user_id:
        return None

    # Only process if onboarding is complete
    state = _load_onboarding_state(user_id, cm)
    if not state or not state.get("completed"):
        return None  # Let default staging handle it

    lang = state.get("language", "en")

    try:
        from . import database as db
        from . import intelligence as intel
    except ImportError:
        # Package-style import failed (extension loaded flat) — use sys.modules fallback
        import importlib, sys
        pkg_name = __name__.rsplit(".", 1)[0] if "." in __name__ else None
        try:
            if pkg_name:
                db = importlib.import_module(f"{pkg_name}.database")
                intel = importlib.import_module(f"{pkg_name}.intelligence")
            else:
                from pathlib import Path as _P
                ext_dir = _P(__file__).parent
                if str(ext_dir) not in sys.path:
                    sys.path.insert(0, str(ext_dir))
                import database as db
                import intelligence as intel
        except Exception as e:
            log.exception(f"Could not import database/intelligence: {e}")
            return _error_reply(lang, str(e))

    # Step 1: Hash check — duplicate detection
    file_hash = db.compute_file_hash(file_bytes)
    existing = db.find_document_by_hash(cm, file_hash)
    if existing:
        return _dup_reply(
            lang,
            existing_doc_type=existing.get("doc_type", "unknown"),
            uploaded_at=existing.get("uploaded_at", ""),
            summary=existing.get("summary", ""),
        )

    # Step 2 + 3: Classify and extract via Claude
    try:
        extraction = intel.process_document(
            file_bytes, filename, mime_type, user_language=lang,
        )
    except Exception as e:
        log.exception(f"Intelligence pipeline failed: {e}")
        return _error_reply(lang, str(e))

    if extraction.get("error"):
        return _error_reply(lang, extraction["error"])

    doc_type = extraction.get("doc_type", "other")

    # Step 3.5: Semantic duplicate check (e.g. re-photographed receipt)
    # Byte-hash dup is already caught above; this catches a different shot of
    # the same real-world document by matching (merchant, date, amount) or
    # (insurer, policy_number) or (doctor, date).
    try:
        sem_dup = db.find_semantic_duplicate(cm, doc_type, extraction)
    except Exception as e:
        log.warning(f"Semantic dup check failed (non-fatal): {e}")
        sem_dup = None
    if sem_dup:
        return _semantic_dup_reply(lang, sem_dup["kind"], sem_dup["match"], extraction)

    # Step 4: Auto-tag family member from detected names
    family_member_id = None
    detected_names = extraction.get("detected_names", [])
    for name in detected_names:
        fm_id = db.find_family_member_id(cm, name)
        if fm_id:
            family_member_id = fm_id
            break

    # Step 5: Insert into SQLite
    file_type = "pdf" if mime_type == "application/pdf" else (
        "image" if mime_type.startswith("image/") else "other"
    )
    doc_id = db.insert_document(cm, {
        "filename": filename,
        "file_hash": file_hash,
        "file_type": file_type,
        "doc_type": doc_type,
        "summary": extraction.get("summary", ""),
        "key_points": extraction.get("key_points", []),
        "important_dates": extraction.get("important_dates", []),
        "red_flags": extraction.get("red_flags", []),
        "action_items": extraction.get("action_items", []),
        "family_member_id": family_member_id,
        "currency": extraction.get("currency"),
    })

    # Step 6: Insert type-specific structured data
    txn_count = 0
    transactions = extraction.get("transactions", [])
    if transactions:
        txn_count = db.insert_transactions(
            cm, doc_id, transactions, family_member_id,
            extraction.get("currency") or "HKD",
        )

    if doc_type == "insurance" and extraction.get("policy"):
        db.insert_policy(cm, doc_id, extraction["policy"], family_member_id)

    if doc_type == "medical" and extraction.get("medical_record"):
        db.insert_medical(cm, doc_id, extraction["medical_record"], family_member_id)

    # Step 7: Mirror summary to context/documents.md so Claude can see it
    try:
        doc_md = cm._root / "context" / "documents.md"
        if doc_md.exists():
            existing_md = doc_md.read_text(encoding="utf-8")
            new_entry = _format_doc_md_entry(filename, doc_type, extraction, transactions)
            doc_md.write_text(existing_md.rstrip() + "\n\n" + new_entry + "\n", encoding="utf-8")
    except Exception as e:
        log.warning(f"Could not mirror to documents.md: {e}")

    # Step 8: Format user-facing response
    return _format_success_reply(lang, doc_type, extraction, transactions, txn_count)


# ---------------------------------------------------------------------------
# Reply formatters
# ---------------------------------------------------------------------------

_DOC_TYPE_EMOJI = {
    "receipt": "🧾", "bank_statement": "🏦", "credit_card": "💳",
    "insurance": "🛡️", "medical": "🏥", "dental": "🦷",
    "legal": "⚖️", "contract": "📋", "mortgage": "🏠",
    "utility": "💡", "id_document": "🪪", "tax": "📊",
    "school": "🎓", "travel": "✈️", "hotel": "🏨", "event": "📅",
    "other": "📄",
}

_DOC_TYPE_LABELS = {
    "en": {
        "receipt": "Receipt", "bank_statement": "Bank Statement",
        "credit_card": "Credit Card", "insurance": "Insurance Policy",
        "medical": "Medical Record", "legal": "Legal Document",
        "contract": "Contract", "mortgage": "Mortgage",
        "utility": "Utility Bill", "id_document": "ID Document",
        "tax": "Tax Document", "school": "School Notice",
        "travel": "Travel Booking", "hotel": "Hotel Booking",
        "event": "Event", "other": "Document",
    },
    "zh-tw": {
        "receipt": "收據", "bank_statement": "銀行對帳單",
        "credit_card": "信用卡帳單", "insurance": "保單",
        "medical": "醫療記錄", "legal": "法律文件",
        "contract": "合約", "mortgage": "按揭文件",
        "utility": "水電費單", "id_document": "身份證明文件",
        "tax": "稅務文件", "school": "學校通知",
        "travel": "旅遊訂單", "hotel": "酒店訂單",
        "event": "活動", "other": "文件",
    },
    "ja": {
        "receipt": "レシート", "bank_statement": "銀行明細",
        "credit_card": "クレジット明細", "insurance": "保険証書",
        "medical": "医療記録", "legal": "法律文書",
        "contract": "契約書", "mortgage": "住宅ローン",
        "utility": "公共料金", "id_document": "身分証明書",
        "tax": "税務書類", "school": "学校通知",
        "travel": "旅行予約", "hotel": "ホテル予約",
        "event": "イベント", "other": "書類",
    },
}


def _format_success_reply(lang: str, doc_type: str, extraction: dict,
                          transactions: list, txn_count: int) -> str:
    emoji = _DOC_TYPE_EMOJI.get(doc_type, "📄")
    type_label = _DOC_TYPE_LABELS.get(lang, _DOC_TYPE_LABELS["en"]).get(doc_type, doc_type)

    headers = {
        "en":    {"type": "Document Type", "summary": "Summary",
                  "dates": "Important Dates", "flags": "⚠️ Red Flags",
                  "actions": "Action Items", "amount": "Amount",
                  "processed": "✅ Saved"},
        "zh-tw": {"type": "文件類型", "summary": "摘要",
                  "dates": "重要日期", "flags": "⚠️ 注意事項",
                  "actions": "建議行動", "amount": "金額",
                  "processed": "✅ 已儲存"},
        "ja":    {"type": "書類の種類", "summary": "要約",
                  "dates": "重要な日付", "flags": "⚠️ 注意事項",
                  "actions": "推奨アクション", "amount": "金額",
                  "processed": "✅ 保存しました"},
    }
    h = headers.get(lang, headers["en"])

    lines = [f"{emoji} *{h['type']}:* {type_label}", ""]

    summary = extraction.get("summary", "")
    if summary:
        lines.append(f"*{h['summary']}*")
        lines.append(summary)
        lines.append("")

    # Transaction summary (receipts / bank / utility)
    if transactions:
        currency = extraction.get("currency") or "HKD"
        total = sum(abs(float(t.get("amount", 0) or 0)) for t in transactions)
        if len(transactions) == 1:
            t = transactions[0]
            cat = t.get("category", "other")
            merch = t.get("merchant", "")
            amt = abs(float(t.get("amount", 0) or 0))
            lines.append(f"💰 *{h['amount']}:* {currency} {amt:,.2f}")
            if merch:
                lines.append(f"   {merch} · _{cat}_")
        else:
            lines.append(f"💰 *{h['amount']}:* {currency} {total:,.2f} ({len(transactions)} txns)")
        lines.append("")

    dates = extraction.get("important_dates", [])
    if dates:
        lines.append(f"*{h['dates']}*")
        for d in dates[:5]:
            days = d.get("days_until", -1)
            label = d.get("label", "")
            date_str = d.get("date", "")
            urgency = " 🔴" if 0 <= days <= 7 else " 🟡" if 0 <= days <= 30 else ""
            if days >= 0:
                lines.append(f"• {label}: {date_str} ({days}d){urgency}")
            else:
                lines.append(f"• {label}: {date_str}")
        lines.append("")

    flags = extraction.get("red_flags", [])
    if flags:
        lines.append(f"*{h['flags']}*")
        for f in flags[:3]:
            sev = f.get("severity", "medium")
            sev_emoji = "🔴" if sev == "high" else "🟡"
            lines.append(f"{sev_emoji} {f.get('clause', '')}")
        lines.append("")

    actions = extraction.get("action_items", [])
    if actions:
        lines.append(f"*{h['actions']}*")
        for a in actions[:3]:
            lines.append(f"→ {a}")
        lines.append("")

    # Show category tag for receipts/bills
    if transactions and len(transactions) == 1:
        cat = transactions[0].get("category", "other")
        lines.append(f"{h['processed']} · 🏷️ *{cat}*")
    else:
        lines.append(f"{h['processed']} · {emoji} *{type_label}*")

    return "\n".join(lines)


def _dup_reply(lang: str, existing_doc_type: str, uploaded_at: str, summary: str) -> str:
    # Format the timestamp for display (show date only)
    when = (uploaded_at or "").split(" ")[0] if uploaded_at else "earlier"
    preview = (summary or "").strip()[:120]

    templates = {
        "en": (
            "♻️ *Duplicate detected*\n\n"
            "I already have this exact {type} (uploaded {when}).\n"
            "No need to upload it again — it's already saved.\n\n"
            "{preview}"
        ),
        "zh-tw": (
            "♻️ *發現重複文件*\n\n"
            "這份 {type} 已經存在（{when} 上傳）。\n"
            "不需要再上傳 — 已經儲存了。\n\n"
            "{preview}"
        ),
        "ja": (
            "♻️ *重複を検出*\n\n"
            "この{type}はすでに登録されています（{when}）。\n"
            "再アップロードは不要です。\n\n"
            "{preview}"
        ),
    }
    tpl = templates.get(lang, templates["en"])
    type_label = _DOC_TYPE_LABELS.get(lang, _DOC_TYPE_LABELS["en"]).get(
        existing_doc_type, existing_doc_type
    )
    return tpl.replace("{type}", type_label).replace("{when}", when).replace("{preview}", preview)


def _semantic_dup_reply(lang: str, kind: str, match: dict, extraction: dict) -> str:
    """
    Soft warning when a semantic duplicate is detected (same real-world document,
    different bytes — e.g. re-photographed receipt).

    We do NOT insert into the database. User can reupload with a clarification
    caption if they want to force a new entry (future: explicit "force" tool).
    """
    when = (match.get("uploaded_at") or "").split(" ")[0] or "earlier"
    existing_file = match.get("filename") or "previous upload"

    # Build a 1-line "details" string describing the match
    if kind == "transaction":
        merchant = match.get("merchant") or ""
        date = match.get("date") or ""
        amount = match.get("amount") or 0
        currency = match.get("currency") or "HKD"
        details = f"{merchant} · {date} · {currency} {float(amount):,.2f}"
    elif kind == "policy":
        insurer = match.get("insurer") or ""
        pnum = match.get("policy_number") or ""
        details = f"{insurer} · policy #{pnum}"
    elif kind == "medical":
        doctor = match.get("doctor") or match.get("provider") or ""
        date = match.get("date") or ""
        details = f"{doctor} · {date}"
    else:
        details = ""

    templates = {
        "en": (
            "♻️ *Looks like a duplicate*\n\n"
            "I already have a record that matches this one:\n"
            "• {details}\n"
            "• From: {file} (uploaded {when})\n\n"
            "I've *not* added it again. If this is actually a *different* "
            "document, just re-send with a short caption explaining (e.g. "
            "\"different visit\") and I'll save it as new."
        ),
        "zh-tw": (
            "♻️ *看起來是重複文件*\n\n"
            "我已經有一筆符合的記錄：\n"
            "• {details}\n"
            "• 來自：{file}（{when} 上傳）\n\n"
            "我*沒有*再次儲存。如果這其實是*不同*的文件，"
            "請重新上傳並加上簡短說明（例如「不同次看診」），我就會儲存為新記錄。"
        ),
        "ja": (
            "♻️ *重複の可能性*\n\n"
            "すでに一致する記録があります：\n"
            "• {details}\n"
            "• ファイル：{file}（{when}）\n\n"
            "重複のため登録しませんでした。*別の*書類であれば、"
            "短いキャプション（例：「別の診察」）を付けて再送してください。"
        ),
    }
    tpl = templates.get(lang, templates["en"])
    return (
        tpl.replace("{details}", details)
           .replace("{file}", existing_file)
           .replace("{when}", when)
    )


def _error_reply(lang: str, detail: str) -> str:
    templates = {
        "en": f"❌ Could not process document: {detail[:120]}",
        "zh-tw": f"❌ 無法處理文件: {detail[:120]}",
        "ja": f"❌ 書類を処理できませんでした: {detail[:120]}",
    }
    return templates.get(lang, templates["en"])


def _format_doc_md_entry(filename: str, doc_type: str, extraction: dict,
                          transactions: list) -> str:
    """Format a single document entry for context/documents.md (Claude's view)."""
    today = datetime.now().strftime("%Y-%m-%d")
    lines = [f"## {filename} — {doc_type} — {today}"]

    summary = extraction.get("summary", "")
    if summary:
        lines.append("")
        lines.append(summary)

    if transactions:
        currency = extraction.get("currency") or "HKD"
        lines.append("")
        for t in transactions[:10]:
            amt = abs(float(t.get("amount", 0) or 0))
            lines.append(
                f"- {t.get('date', '')}: {t.get('merchant', '')} — "
                f"{currency} {amt:,.2f} _({t.get('category', 'other')})_"
            )

    dates = extraction.get("important_dates", [])
    if dates:
        lines.append("")
        lines.append("**Important dates:**")
        for d in dates[:5]:
            lines.append(f"- {d.get('date', '')}: {d.get('label', '')}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Onboarding FSM (simplified v2)
# ---------------------------------------------------------------------------
#
# Steps:
#   1. Consent — "I agree / No thanks"
#   2. Household — "Just me / Me + family"
#   3. Names (if family) — free-form names, one per line, max 7
#   4. Complete — "You're all set!"
#
# Design principles:
# - No relationships collected (just names — Claude can ask later if unclear)
# - No explicit "DONE" keyword — user just presses Send
# - Max 7 family members (+ yourself = 8 total)
# - Personalized greeting using Telegram first_name
# - Example names are culturally appropriate per language
# - User can add/delete anytime after onboarding by talking to the bot

MAX_FAMILY_MEMBERS = 7  # Max 7 OTHER members; self is implicit

_ONBOARDING_MESSAGES = {
    "en": {
        "consent": (
            "🧠 *Save My Brain AI*\n\n"
            "Hi{name_greeting}! 👋\n\n"
            "I'm your household document assistant.\n"
            "Upload any document — I'll organize it and remember everything.\n\n"
            "🔒 *Privacy:* Documents are processed then deleted.\n"
            "No selling your data, no AI training.\n\n"
            "Reply:\n"
            "1️⃣ I agree\n"
            "2️⃣ No thanks"
        ),
        "consent_decline": "No problem. Come back anytime! 👋",
        "privacy_detail": (
            "🔒 *Save My Brain Privacy Policy*\n\n"
            "*What I collect:*\n"
            "• Documents you upload (photos, PDFs)\n"
            "• Extracted information (dates, amounts, names)\n"
            "• Your conversation history\n\n"
            "*What I do with it:*\n"
            "• Process documents with Claude AI to extract key info\n"
            "• Store summaries to help you find things later\n"
            "• Original files are *deleted* after processing\n\n"
            "*What I don't do:*\n"
            "• ❌ Sell your data to anyone\n"
            "• ❌ Use your data to train AI\n"
            "• ❌ Share with third parties (except Anthropic Claude for processing)\n\n"
            "*Your rights:*\n"
            "• Delete all your data anytime — just say \"delete everything\"\n"
            "• Export your data anytime\n"
            "• Stop using the service anytime\n\n"
            "Ready to continue?\n"
            "1️⃣ I agree\n"
            "2️⃣ No thanks"
        ),
        "help_consent": (
            "I didn't quite catch that. To continue, please reply:\n\n"
            "1️⃣ I agree — to start using Save My Brain\n"
            "2️⃣ No thanks — if you're not ready\n\n"
            "Or ask me about:\n"
            "• \"privacy\" — to see the privacy policy\n"
            "• \"what does this do\" — to learn more"
        ),
        "help_general": (
            "Save My Brain is your AI household document assistant.\n\n"
            "📄 Upload any document (photo, PDF, screenshot)\n"
            "🧠 I read, organize, and remember everything\n"
            "💬 Ask me anything: \"When does my insurance expire?\"\n\n"
            "Ready to start?\n"
            "1️⃣ I agree\n"
            "2️⃣ No thanks"
        ),
        "household": (
            "👨‍👩‍👧‍👦 Who do you manage documents for?\n\n"
            "Reply:\n"
            "1️⃣ Just me\n"
            "2️⃣ Me + family"
        ),
        "household_family": (
            "👥 Who's in your household?\n\n"
            "Type their names, separated by commas. Up to 7 people.\n\n"
            "For example:\n"
            "John, Mary"
        ),
        "household_confirm": (
            "✅ Added: {members}\n\n"
            "You can add or delete anytime — just tell me."
        ),
        "too_many": (
            "⚠️ You sent {count} names, but I can only add up to 7 people.\n\n"
            "Please send a shorter list (up to 7 names, one per line)."
        ),
        "dup_note": (
            "ℹ️ I noticed duplicate names and kept only one of each: *{dups}*"
        ),
        "complete": (
            "🎉 *You're all set!*\n\n"
            "🧠 Your AI brain is ready.\n\n"
            "📎 Send any document — PDF, photo, screenshot\n"
            "   I'll read it and remember everything.\n\n"
            "💬 Ask anything — \"When does my insurance expire?\"\n\n"
            "You can add or delete household members anytime — just tell me."
        ),
    },
    "zh-tw": {
        "consent": (
            "🧠 *拯救腦細胞 AI*\n\n"
            "你好{name_greeting}！👋\n\n"
            "我是你的家庭文件助手。\n"
            "上傳任何文件 — 我會整理並記住一切。\n\n"
            "🔒 *隱私：* 文件處理後即刪除。\n"
            "不出售資料、不用於AI訓練。\n\n"
            "回覆：\n"
            "1️⃣ 我同意\n"
            "2️⃣ 不用了"
        ),
        "consent_decline": "沒問題，隨時回來！👋",
        "privacy_detail": (
            "🔒 *拯救腦細胞 隱私政策*\n\n"
            "*我會收集什麼：*\n"
            "• 你上傳的文件（照片、PDF）\n"
            "• 提取的資訊（日期、金額、姓名）\n"
            "• 你的對話記錄\n\n"
            "*我怎麼處理：*\n"
            "• 用Claude AI分析文件提取重點\n"
            "• 儲存摘要方便你日後查找\n"
            "• 原始檔案處理後*即刪除*\n\n"
            "*我不會做的事：*\n"
            "• ❌ 出售你的資料\n"
            "• ❌ 用你的資料訓練AI\n"
            "• ❌ 分享給第三方（除了Anthropic Claude用於處理）\n\n"
            "*你的權利：*\n"
            "• 隨時刪除所有資料 — 只需說「刪除全部」\n"
            "• 隨時匯出你的資料\n"
            "• 隨時停止使用服務\n\n"
            "準備好了嗎？\n"
            "1️⃣ 我同意\n"
            "2️⃣ 不用了"
        ),
        "help_consent": (
            "我沒理解你的意思。請回覆：\n\n"
            "1️⃣ 我同意 — 開始使用拯救腦細胞\n"
            "2️⃣ 不用了 — 如果你還沒準備好\n\n"
            "或者問我：\n"
            "• 「隱私」— 查看隱私政策\n"
            "• 「這是什麼」— 了解更多"
        ),
        "help_general": (
            "拯救腦細胞是你的AI家庭文件助手。\n\n"
            "📄 上傳任何文件（照片、PDF、截圖）\n"
            "🧠 我會閱讀、整理並記住一切\n"
            "💬 隨時提問：「我的保險什麼時候到期？」\n\n"
            "準備好了嗎？\n"
            "1️⃣ 我同意\n"
            "2️⃣ 不用了"
        ),
        "household": (
            "👨‍👩‍👧‍👦 你需要管理誰的文件？\n\n"
            "回覆：\n"
            "1️⃣ 只有我自己\n"
            "2️⃣ 我和家人"
        ),
        "household_family": (
            "👥 你家裡有誰？\n\n"
            "請輸入他們的名字，用逗號分隔。最多7人。\n\n"
            "例如：\n"
            "大明、美美"
        ),
        "household_confirm": (
            "✅ 已加入：{members}\n\n"
            "你隨時可以告訴我新增或刪除。"
        ),
        "too_many": (
            "⚠️ 你輸入了 {count} 個名字，最多只能加入 7 人。\n\n"
            "請傳送較短的名單（最多 7 人，每行一個）。"
        ),
        "dup_note": (
            "ℹ️ 我發現有重複的名字，每個只保留一個：*{dups}*"
        ),
        "complete": (
            "🎉 *設定完成！*\n\n"
            "🧠 你的AI大腦已就緒。\n\n"
            "📎 傳送任何文件 — PDF、照片、截圖\n"
            "   我會閱讀並記住所有內容。\n\n"
            "💬 隨時提問 — 「我的保險什麼時候到期？」\n\n"
            "你隨時可以告訴我新增或刪除家庭成員。"
        ),
    },
    "ja": {
        "consent": (
            "🧠 *脳細胞救済 AI*\n\n"
            "こんにちは{name_greeting}！👋\n\n"
            "家庭の書類管理アシスタントです。\n"
            "どんな書類でもアップロード — 整理して全て記憶します。\n\n"
            "🔒 *プライバシー：* 書類は処理後に削除されます。\n"
            "データの販売やAI訓練への使用はありません。\n\n"
            "返信：\n"
            "1️⃣ 同意します\n"
            "2️⃣ いいえ"
        ),
        "consent_decline": "大丈夫です。いつでもお戻りください！👋",
        "privacy_detail": (
            "🔒 *脳細胞救済 プライバシーポリシー*\n\n"
            "*収集する情報：*\n"
            "• アップロードした書類（写真、PDF）\n"
            "• 抽出された情報（日付、金額、名前）\n"
            "• 会話履歴\n\n"
            "*使用目的：*\n"
            "• Claude AIで書類を分析\n"
            "• 後で見つけやすいように要約を保存\n"
            "• 元のファイルは処理後*削除*\n\n"
            "*行わないこと：*\n"
            "• ❌ データの販売\n"
            "• ❌ AI訓練への使用\n"
            "• ❌ 第三者との共有（処理のためのAnthropic Claude以外）\n\n"
            "*あなたの権利：*\n"
            "• いつでも全データ削除 — 「全て削除」と伝えてください\n"
            "• いつでもデータエクスポート\n"
            "• いつでもサービス利用停止\n\n"
            "続けますか？\n"
            "1️⃣ 同意します\n"
            "2️⃣ いいえ"
        ),
        "help_consent": (
            "理解できませんでした。返信してください：\n\n"
            "1️⃣ 同意します — 脳細胞救済を始める\n"
            "2️⃣ いいえ — まだ準備できていない\n\n"
            "または質問：\n"
            "• 「プライバシー」— プライバシーポリシーを確認\n"
            "• 「これは何？」— 詳細を知る"
        ),
        "help_general": (
            "脳細胞救済はAI家庭書類アシスタントです。\n\n"
            "📄 どんな書類でもアップロード（写真、PDF、スクリーンショット）\n"
            "🧠 読み取り、整理、全て記憶\n"
            "💬 何でも質問：「保険はいつ期限切れ？」\n\n"
            "始めますか？\n"
            "1️⃣ 同意します\n"
            "2️⃣ いいえ"
        ),
        "household": (
            "👨‍👩‍👧‍👦 誰の書類を管理しますか？\n\n"
            "返信：\n"
            "1️⃣ 自分だけ\n"
            "2️⃣ 自分と家族"
        ),
        "household_family": (
            "👥 ご家族の名前を教えてください\n\n"
            "名前をカンマで区切って入力してください。最大7人。\n\n"
            "例：\n"
            "三郎、雅美"
        ),
        "household_confirm": (
            "✅ 追加しました：{members}\n\n"
            "いつでも追加や削除をお伝えください。"
        ),
        "too_many": (
            "⚠️ {count} 人の名前が送られましたが、最大 7 人までです。\n\n"
            "短いリストを送ってください（最大 7 人、1行に1人）。"
        ),
        "dup_note": (
            "ℹ️ 重複した名前が見つかりました。それぞれ1つだけ残しました：*{dups}*"
        ),
        "complete": (
            "🎉 *設定完了！*\n\n"
            "🧠 AIブレインの準備ができました。\n\n"
            "📎 書類を送信 — PDF、写真、スクリーンショット\n"
            "   読み取って全て記憶します。\n\n"
            "💬 何でも質問 — 「保険はいつ期限切れ？」\n\n"
            "家族の追加や削除はいつでもお伝えください。"
        ),
    },
}


def _detect_language(text: str) -> str:
    """Detect language from text using Unicode character ranges."""
    jp_chars = len(re.findall(r'[\u3040-\u309f\u30a0-\u30ff]', text))
    cjk_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
    total = len(text.replace(" ", ""))
    if total == 0:
        return "en"
    if jp_chars / max(total, 1) > 0.1:
        return "ja"
    if cjk_chars / max(total, 1) > 0.15:
        return "zh-tw"
    return "en"


def _get_onboarding_path(cm) -> str:
    """Return path to onboarding state directory."""
    import os
    data_dir = os.getenv("SC_DATA_DIR", str(cm._root))
    path = os.path.join(data_dir, "data", "onboarding")
    os.makedirs(path, exist_ok=True)
    return path


def _load_onboarding_state(user_id: str, cm) -> dict | None:
    """Load onboarding state for a user. Returns None if no state."""
    import os
    path = os.path.join(_get_onboarding_path(cm), f"{user_id}.json")
    if not os.path.exists(path):
        return None
    try:
        return json.loads(open(path).read())
    except (json.JSONDecodeError, OSError):
        return None


def _save_onboarding_state(user_id: str, state: dict, cm):
    """Save onboarding state for a user."""
    import os
    path = os.path.join(_get_onboarding_path(cm), f"{user_id}.json")
    with open(path, "w") as f:
        f.write(json.dumps(state, ensure_ascii=False, indent=2))


def _onboarding_step(user_id: str, message: str, cm, first_name: str = "") -> str | None:
    """
    Run the simplified 3-step onboarding FSM.

    Steps: consent → household → (family names if applicable) → complete

    Returns a reply string if handling onboarding, or None if already complete.
    """
    from datetime import datetime

    state = _load_onboarding_state(user_id, cm)

    # Already completed — pass through
    if state and state.get("completed"):
        return None

    msg = message.strip()

    # New user — detect language, show consent with personalized greeting
    if state is None:
        lang = _detect_language(msg)
        state = {
            "step": "consent",
            "language": lang,
            "first_name": first_name,
            "consent_given": False,
            "household_mode": None,
            "family_members": [],
            "completed": False,
            "created_at": datetime.now().isoformat(),
        }
        _save_onboarding_state(user_id, state, cm)
        msgs = _ONBOARDING_MESSAGES.get(lang, _ONBOARDING_MESSAGES["en"])
        name_greeting = f" {first_name}" if first_name else ""
        return msgs["consent"].replace("{name_greeting}", name_greeting)

    lang = state.get("language", "en")
    msgs = _ONBOARDING_MESSAGES.get(lang, _ONBOARDING_MESSAGES["en"])
    step = state.get("step", "consent")
    msg_lower = msg.lower().strip()

    # Detect "agree" — exact match or clear intent (not substring)
    def _is_agree(m: str) -> bool:
        m = m.strip().lower()
        if m in ("1", "1️⃣", "1.", "#1"):
            return True
        # Exact phrases (strict — avoid matching "agreement" etc.)
        exact_agree = {"yes", "ok", "okay", "sure", "agree", "i agree",
                       "同意", "好", "好的", "可以",
                       "はい", "同意します", "同意する"}
        return m in exact_agree

    def _is_decline(m: str) -> bool:
        m = m.strip().lower()
        if m in ("2", "2️⃣", "2.", "#2"):
            return True
        exact_decline = {"no", "no thanks", "nope", "not now",
                         "不", "不用", "不用了", "不要",
                         "いいえ", "結構です"}
        return m in exact_decline

    def _is_privacy_query(m: str) -> bool:
        m = m.lower()
        return any(kw in m for kw in [
            "privacy", "policy", "data", "gdpr",
            "隱私", "政策", "資料",
            "プライバシー", "ポリシー", "データ",
        ])

    def _is_help_query(m: str) -> bool:
        m = m.lower()
        return any(kw in m for kw in [
            "what is this", "what does", "how does", "help", "how do i",
            "這是什麼", "怎麼用", "幫助",
            "これは何", "使い方", "ヘルプ",
        ])

    # STEP 1: Consent
    if step == "consent":
        if _is_agree(msg):
            state["consent_given"] = True
            state["step"] = "household"
            _save_onboarding_state(user_id, state, cm)
            return msgs["household"]
        if _is_decline(msg):
            import os
            path = os.path.join(_get_onboarding_path(cm), f"{user_id}.json")
            if os.path.exists(path):
                os.remove(path)
            return msgs["consent_decline"]
        # Show privacy policy if asked
        if _is_privacy_query(msg):
            return msgs["privacy_detail"]
        # Show help if asked
        if _is_help_query(msg):
            return msgs["help_general"]
        # Anything else — show help
        return msgs["help_consent"]

    # STEP 2: Household
    if step == "household":
        if _is_agree(msg):  # "1" / "Just me"
            state["household_mode"] = "solo"
            return _complete_onboarding(user_id, state, cm, msgs)
        if _is_decline(msg):  # "2" / "Me + family"
            state["household_mode"] = "family"
            state["step"] = "collecting_family"
            _save_onboarding_state(user_id, state, cm)
            return msgs["household_family"]
        # Explicit keyword match for natural language
        if any(kw in msg_lower for kw in ["just me", "only me", "只有我", "自分だけ"]):
            state["household_mode"] = "solo"
            return _complete_onboarding(user_id, state, cm, msgs)
        if any(kw in msg_lower for kw in ["me + family", "with family", "我和家人", "家族"]):
            state["household_mode"] = "family"
            state["step"] = "collecting_family"
            _save_onboarding_state(user_id, state, cm)
            return msgs["household_family"]
        # Privacy question
        if _is_privacy_query(msg):
            return msgs["privacy_detail"]
        # Didn't understand — re-show step
        return msgs["household"]

    # STEP 3: Collecting family names (no relationships — just names)
    if step == "collecting_family":
        # Parse names from input — split on newline, comma (EN/CN), Japanese mark,
        # and natural conjunctions: "and", "&", "及", "と"
        raw_lines = re.split(
            r'[\n,，、&]|\s+and\s+|\s+及\s+|\s*と\s*',
            msg,
            flags=re.IGNORECASE,
        )
        raw_names = []
        for line in raw_lines:
            name = line.strip()
            if name and len(name) < 60:  # Sanity limit
                raw_names.append(name)

        # Dedup case-insensitively, preserving first-seen order
        seen = set()
        names = []
        dropped_duplicates = []
        for name in raw_names:
            key = name.lower()
            if key in seen:
                dropped_duplicates.append(name)
            else:
                seen.add(key)
                names.append(name)

        # REJECT if too many (count deduped names) — show warning, don't advance
        if len(names) > MAX_FAMILY_MEMBERS:
            return msgs["too_many"].replace("{count}", str(len(names)))

        if names:
            state["family_members"] = [{"name": n} for n in names]
            member_list = "、".join(names) if lang != "en" else ", ".join(names)
            confirm = msgs["household_confirm"].replace("{members}", member_list)

            # Add a note if we dropped duplicates
            if dropped_duplicates:
                dup_list = ", ".join(dropped_duplicates)
                dup_note = msgs.get("dup_note", "").replace("{dups}", dup_list)
                if dup_note:
                    confirm = dup_note + "\n\n" + confirm

            complete = _complete_onboarding(user_id, state, cm, msgs)
            return confirm + "\n\n" + complete
        else:
            return msgs["household_family"]

    # Fallback
    return None


def _complete_onboarding(user_id: str, state: dict, cm, msgs: dict) -> str:
    """Mark onboarding as complete and write family members to context + SQL."""
    import os

    state["step"] = "complete"
    state["completed"] = True
    _save_onboarding_state(user_id, state, cm)

    family = state.get("family_members", [])
    first_name = state.get("first_name", "")

    # 1. Write to family.md (human-readable + Claude's context)
    try:
        family_path = cm._root / "context" / "family.md"
        if family_path.exists():
            lines = ["# Family\n"]
            lines.append("> Household members. Names only — relationships can be added later.\n")
            lines.append(f"## {first_name or 'You'}")
            lines.append("- Role: primary user")
            lines.append("")
            for m in family:
                lines.append(f"## {m['name']}")
                lines.append("- Relationship: household member")
                lines.append("")
            family_path.write_text("\n".join(lines), encoding="utf-8")
    except Exception:
        pass

    # 2. Write to SQL database (for auto-tagging documents by name)
    try:
        db = _get_db()
        if first_name:
            db.sync_family_member(cm, first_name, is_primary=True)
        for m in family:
            db.sync_family_member(cm, m["name"], is_primary=False)
    except Exception as e:
        log.warning(f"Could not sync family members to SQL: {e}")

    return msgs["complete"]


# ---------------------------------------------------------------------------
# Billing Gate (for future use)
# ---------------------------------------------------------------------------

def check_billing(telegram_user_id: str, data_dir: str | None = None) -> dict:
    """
    Check if a user has an active plan.

    Returns:
        {"allowed": True/False, "plan": "trial|annual|lifetime", "message": "..."}

    Plans are stored in data/plans.json. If no entry exists for the user,
    they get a 14-day trial with 5 document limit.

    Currently NOT enforced — returns allowed=True for all users.
    To activate, integrate into relay.py's message handler.
    """
    import os
    from pathlib import Path
    from datetime import datetime, timedelta

    plans_path = Path(data_dir or os.getenv("SC_DATA_DIR", ".")) / "data" / "plans.json"

    if not plans_path.exists():
        return {"allowed": True, "plan": "trial", "message": "No billing configured"}

    try:
        plans = json.loads(plans_path.read_text())
    except (json.JSONDecodeError, OSError):
        return {"allowed": True, "plan": "trial", "message": "Plans file unreadable"}

    user_key = f"telegram_{telegram_user_id}"
    user_plan = plans.get("users", {}).get(user_key)

    if not user_plan:
        # New user — auto-create trial
        return {"allowed": True, "plan": "trial", "message": "Free trial active"}

    plan_type = user_plan.get("plan", "trial")
    expires = user_plan.get("expires")

    if plan_type == "lifetime":
        return {"allowed": True, "plan": "lifetime", "message": "Lifetime plan"}

    if expires:
        try:
            exp_date = datetime.fromisoformat(expires)
            if datetime.now() > exp_date:
                return {
                    "allowed": False,
                    "plan": plan_type,
                    "message": "Plan expired. Subscribe at savemybrain.ai",
                }
        except ValueError:
            pass

    return {"allowed": True, "plan": plan_type, "message": f"{plan_type} plan active"}
