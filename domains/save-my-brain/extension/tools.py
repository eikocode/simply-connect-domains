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
    Handle document uploads directly — process via Claude Vision and return
    a formatted summary. Skips the default staging-for-review flow.

    Returns None (falls through to default) if:
    - User hasn't completed onboarding yet
    - Claude Vision is not available
    """
    user_id = str(kwargs.get("user_id", ""))
    if not user_id:
        return None

    # Only process if onboarding is complete
    state = _load_onboarding_state(user_id, cm)
    if not state or not state.get("completed"):
        return None  # Let default staging handle it (or block via onboarding)

    lang = state.get("language", "en")

    # Use simply-connect's ingestion pipeline (already configured)
    # but format the result as a nice summary instead of staging
    import tempfile
    import os
    from pathlib import Path

    try:
        # Write to temp file
        suffix = ".jpg" if mime_type.startswith("image/") else ".pdf" if mime_type == "application/pdf" else ".bin"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f:
            f.write(file_bytes)
            tmp_path = Path(f.name)

        try:
            from simply_connect.ingestion import ingest_document

            committed = cm.load_committed()
            # Force docling (local, no API key) for save-my-brain
            result = ingest_document(
                tmp_path,
                committed,
                cm._profile,
                parser="docling",
            )

            if not result.get("success"):
                err_msgs = {
                    "en": f"❌ Could not read document: {result.get('error', 'unknown error')}",
                    "zh-tw": f"❌ 無法讀取文件: {result.get('error', '未知錯誤')}",
                    "ja": f"❌ 書類を読み取れませんでした: {result.get('error', '不明なエラー')}",
                }
                return err_msgs.get(lang, err_msgs["en"])

            extractions = result.get("extractions", [])
            if not extractions:
                empty_msgs = {
                    "en": "📄 Document read — no key information found.",
                    "zh-tw": "📄 文件已讀取 — 未找到關鍵資訊。",
                    "ja": "📄 書類を読み取りました — 重要な情報は見つかりませんでした。",
                }
                return empty_msgs.get(lang, empty_msgs["en"])

            # Save to committed context directly (no staging)
            # Format a nice summary for the user
            saved_count = 0
            for item in extractions:
                category = item.get("category", "general")
                content = item.get("content", "")
                summary = item.get("summary", filename)

                # Append to the appropriate context file
                context_file = cm.CATEGORY_MAP.get(category, "documents.md")
                context_path = cm._root / "context" / context_file
                if context_path.exists():
                    existing = context_path.read_text(encoding="utf-8")
                    new_content = existing.rstrip() + f"\n\n## {summary}\n\n{content}\n"
                    context_path.write_text(new_content, encoding="utf-8")
                    saved_count += 1

            # Format reply in user's language
            first = extractions[0]
            reply_lines = []

            if lang == "zh-tw":
                reply_lines.append("📄 *文件已分析*\n")
                reply_lines.append(f"📝 {first.get('summary', filename)}")
                if first.get("content"):
                    preview = first["content"][:500]
                    reply_lines.append(f"\n{preview}")
                reply_lines.append(f"\n✅ 已儲存到 *{category}*")
            elif lang == "ja":
                reply_lines.append("📄 *書類を分析しました*\n")
                reply_lines.append(f"📝 {first.get('summary', filename)}")
                if first.get("content"):
                    preview = first["content"][:500]
                    reply_lines.append(f"\n{preview}")
                reply_lines.append(f"\n✅ *{category}* に保存しました")
            else:
                reply_lines.append("📄 *Document analyzed*\n")
                reply_lines.append(f"📝 {first.get('summary', filename)}")
                if first.get("content"):
                    preview = first["content"][:500]
                    reply_lines.append(f"\n{preview}")
                reply_lines.append(f"\n✅ Saved to *{category}*")

            return "\n".join(reply_lines)

        finally:
            if tmp_path.exists():
                os.unlink(tmp_path)

    except Exception as e:
        log_msgs = {
            "en": f"❌ Error processing document: {str(e)[:100]}",
            "zh-tw": f"❌ 處理文件時發生錯誤: {str(e)[:100]}",
            "ja": f"❌ 書類処理エラー: {str(e)[:100]}",
        }
        return log_msgs.get(lang, log_msgs["en"])


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
        names = []
        for line in raw_lines:
            name = line.strip()
            if name and len(name) < 60:  # Sanity limit
                names.append(name)

        # REJECT if too many — show warning, don't advance
        if len(names) > MAX_FAMILY_MEMBERS:
            return msgs["too_many"].replace("{count}", str(len(names)))

        if names:
            state["family_members"] = [{"name": n} for n in names]
            member_list = "、".join(names) if lang != "en" else ", ".join(names)
            confirm = msgs["household_confirm"].replace("{members}", member_list)
            complete = _complete_onboarding(user_id, state, cm, msgs)
            return confirm + "\n\n" + complete
        else:
            return msgs["household_family"]

    # Fallback
    return None


def _complete_onboarding(user_id: str, state: dict, cm, msgs: dict) -> str:
    """Mark onboarding as complete and write family members to context directly."""
    import os

    state["step"] = "complete"
    state["completed"] = True
    _save_onboarding_state(user_id, state, cm)

    # Write family members directly to context/family.md (no staging)
    family = state.get("family_members", [])
    first_name = state.get("first_name", "")

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
        pass  # Don't fail onboarding if write fails

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
