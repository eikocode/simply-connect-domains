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
    **kwargs,
) -> str | None:
    """Handle onboarding FSM + fast-path commands."""
    user_id = kwargs.get("user_id")
    if user_id is None:
        return None

    # Run onboarding FSM
    reply = _onboarding_step(str(user_id), message, cm)
    if reply is not None:
        return reply

    return None


# ---------------------------------------------------------------------------
# Onboarding FSM
# ---------------------------------------------------------------------------

# i18n messages for onboarding
_ONBOARDING_MESSAGES = {
    "en": {
        "consent": (
            "🧠 *Save My Brain AI*\n\n"
            "I'm your household document assistant.\n"
            "Upload documents, I organize and remember everything.\n\n"
            "🔒 *Privacy:* Documents are processed then deleted. "
            "We never sell your data or use it to train AI.\n\n"
            "Reply:\n"
            "1️⃣ I agree\n"
            "2️⃣ No thanks"
        ),
        "consent_decline": "No problem. Come back anytime! 👋",
        "link": (
            "Hi! Do you have a Save My Brain account from the website?\n\n"
            "Reply:\n"
            "1️⃣ Yes — link my account\n"
            "2️⃣ No — I'm new"
        ),
        "link_email": "Type the email you used to sign up:",
        "link_email_not_found": "Email not found. Reply:\n1️⃣ Try another email\n2️⃣ Start fresh",
        "link_email_linked": "✅ Account linked!",
        "household": (
            "Who do you manage documents for?\n\n"
            "Reply:\n"
            "1️⃣ Just me\n"
            "2️⃣ Me + family"
        ),
        "household_family": (
            "Type your family members, one per line.\n"
            "Include their relationship:\n\n"
            "Example:\n"
            "Sam (spouse)\n"
            "Emily (daughter)\n"
            "Mom"
        ),
        "household_confirm": "👥 Got it:\n{members}\n\nSetting up your brain...",
        "complete": (
            "🎉 *You're all set!*\n\n"
            "Your AI brain is ready:\n\n"
            "📎 Send any document — PDF, photo, screenshot\n"
            "   I'll read it and remember everything.\n\n"
            "💬 Ask anything — \"When does my insurance expire?\"\n\n"
            "🧠 I handle the paperwork. You live your life."
        ),
    },
    "zh-tw": {
        "consent": (
            "🧠 *拯救腦細胞 AI*\n\n"
            "我是你的家庭文件助手。\n"
            "上傳文件，我會整理和記住一切。\n\n"
            "🔒 *隱私:* 文件處理後即刪除。\n"
            "我們不會出售你的資料或用於AI訓練。\n\n"
            "回覆：\n"
            "1️⃣ 我同意\n"
            "2️⃣ 不用了"
        ),
        "consent_decline": "沒問題，隨時回來！👋",
        "link": (
            "你有在網站上註冊過帳號嗎？\n\n"
            "回覆：\n"
            "1️⃣ 有，連結我的帳號\n"
            "2️⃣ 沒有，我是新用戶"
        ),
        "link_email": "請輸入你註冊時使用的電郵：",
        "link_email_not_found": "找不到此電郵。回覆：\n1️⃣ 試另一個電郵\n2️⃣ 重新開始",
        "link_email_linked": "✅ 帳號已連結！",
        "household": (
            "你需要管理誰的文件？\n\n"
            "回覆：\n"
            "1️⃣ 只有我自己\n"
            "2️⃣ 我和家人"
        ),
        "household_family": (
            "請輸入家庭成員，每行一個。\n"
            "請附上關係：\n\n"
            "例如：\n"
            "Sam (配偶)\n"
            "Emily (女兒)\n"
            "媽媽"
        ),
        "household_confirm": "👥 收到：\n{members}\n\n正在設定你的大腦...",
        "complete": (
            "🎉 *設定完成！*\n\n"
            "你的AI大腦已就緒：\n\n"
            "📎 傳送任何文件 — PDF、照片、截圖\n"
            "   我會閱讀並記住所有內容。\n\n"
            "💬 隨時提問 — 「媽媽的保險什麼時候到期？」\n\n"
            "🧠 我負責處理文件，你負責生活。"
        ),
    },
    "ja": {
        "consent": (
            "🧠 *脳細胞救済 AI*\n\n"
            "家庭の書類管理アシスタントです。\n"
            "書類をアップロード、整理して全て記憶します。\n\n"
            "🔒 *プライバシー:* 書類は処理後に削除されます。\n"
            "データの販売やAI訓練への使用は一切ありません。\n\n"
            "返信：\n"
            "1️⃣ 同意します\n"
            "2️⃣ いいえ"
        ),
        "consent_decline": "大丈夫です。いつでもお戻りください！👋",
        "link": (
            "ウェブサイトでアカウントをお持ちですか？\n\n"
            "返信：\n"
            "1️⃣ はい、アカウントを連携\n"
            "2️⃣ いいえ、新規です"
        ),
        "link_email": "登録時のメールアドレスを入力してください：",
        "link_email_not_found": "メールが見つかりません。返信：\n1️⃣ 別のメールを試す\n2️⃣ 新規で始める",
        "link_email_linked": "✅ アカウント連携完了！",
        "household": (
            "誰の書類を管理しますか？\n\n"
            "返信：\n"
            "1️⃣ 自分だけ\n"
            "2️⃣ 自分と家族"
        ),
        "household_family": (
            "家族メンバーを入力してください（1行に1人）。\n"
            "関係を含めてください：\n\n"
            "例：\n"
            "Sam (配偶者)\n"
            "Emily (娘)\n"
            "母"
        ),
        "household_confirm": "👥 了解：\n{members}\n\n設定中...",
        "complete": (
            "🎉 *設定完了！*\n\n"
            "AIブレインの準備ができました：\n\n"
            "📎 書類を送信 — PDF、写真、スクリーンショット\n"
            "   読み取って全て記憶します。\n\n"
            "💬 何でも質問 — 「母の保険はいつ期限切れ？」\n\n"
            "🧠 書類は私に任せて、あなたは生活を楽しんで。"
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


def _onboarding_step(user_id: str, message: str, cm) -> str | None:
    """
    Run the onboarding FSM. Returns a reply string if handling onboarding,
    or None if onboarding is complete (pass through to Claude).
    """
    from datetime import datetime

    state = _load_onboarding_state(user_id, cm)

    # Already completed — pass through
    if state and state.get("completed"):
        return None

    msg = message.strip()

    # New user — detect language, show consent
    if state is None:
        lang = _detect_language(msg)
        state = {
            "step": "consent",
            "language": lang,
            "consent_given": False,
            "name": "",
            "household_mode": None,
            "family_members": [],
            "completed": False,
            "created_at": datetime.now().isoformat(),
        }
        _save_onboarding_state(user_id, state, cm)
        msgs = _ONBOARDING_MESSAGES.get(lang, _ONBOARDING_MESSAGES["en"])
        return msgs["consent"]

    lang = state.get("language", "en")
    msgs = _ONBOARDING_MESSAGES.get(lang, _ONBOARDING_MESSAGES["en"])
    step = state.get("step", "consent")

    # STEP 1: Consent
    if step == "consent":
        if msg in ("1", "1️⃣") or any(w in msg.lower() for w in ["agree", "同意", "はい"]):
            state["consent_given"] = True
            state["step"] = "link"
            _save_onboarding_state(user_id, state, cm)
            return msgs["link"]
        elif msg in ("2", "2️⃣") or any(w in msg.lower() for w in ["no", "不", "いいえ"]):
            # Delete state — user declined
            import os
            path = os.path.join(_get_onboarding_path(cm), f"{user_id}.json")
            if os.path.exists(path):
                os.remove(path)
            return msgs["consent_decline"]
        else:
            # Didn't understand — show consent again
            return msgs["consent"]

    # STEP 2: Account linking
    if step == "link":
        if msg in ("1", "1️⃣") or any(w in msg.lower() for w in ["yes", "有", "はい"]):
            state["step"] = "link_email"
            _save_onboarding_state(user_id, state, cm)
            return msgs["link_email"]
        elif msg in ("2", "2️⃣") or any(w in msg.lower() for w in ["no", "new", "沒", "いいえ", "新"]):
            state["step"] = "household"
            _save_onboarding_state(user_id, state, cm)
            return msgs["household"]
        else:
            return msgs["link"]

    # STEP 2a: Email input for linking
    if step == "link_email":
        if "@" in msg:
            # Future: actually look up and link the account
            # For now, just move on
            state["step"] = "household"
            _save_onboarding_state(user_id, state, cm)
            return msgs["link_email_linked"] + "\n\n" + msgs["household"]
        elif msg in ("1", "1️⃣"):
            return msgs["link_email"]
        elif msg in ("2", "2️⃣"):
            state["step"] = "household"
            _save_onboarding_state(user_id, state, cm)
            return msgs["household"]
        else:
            return msgs["link_email_not_found"]

    # STEP 3: Household
    if step == "household":
        if msg in ("1", "1️⃣") or any(w in msg.lower() for w in ["just me", "只有", "自分"]):
            state["household_mode"] = "solo"
            state["step"] = "complete"
            _save_onboarding_state(user_id, state, cm)
            # Complete onboarding
            return _complete_onboarding(user_id, state, cm, msgs)
        elif msg in ("2", "2️⃣") or any(w in msg.lower() for w in ["family", "家", "家族"]):
            state["household_mode"] = "family"
            state["step"] = "collecting_family"
            _save_onboarding_state(user_id, state, cm)
            return msgs["household_family"]
        else:
            return msgs["household"]

    # STEP 3a: Collecting family members
    if step == "collecting_family":
        # Parse family members from input
        members = []
        for line in msg.split("\n"):
            line = line.strip()
            if not line:
                continue
            # Try to extract name (relationship)
            match = re.match(r'^(.+?)\s*[(\（](.+?)[)\）]\s*$', line)
            if match:
                members.append({"name": match.group(1).strip(), "relationship": match.group(2).strip()})
            else:
                members.append({"name": line, "relationship": "family"})

        if members:
            state["family_members"] = members
            state["step"] = "complete"
            _save_onboarding_state(user_id, state, cm)

            # Format confirmation
            member_list = "\n".join(f"  • {m['name']} ({m['relationship']})" for m in members)
            confirm = msgs["household_confirm"].replace("{members}", member_list)
            complete = _complete_onboarding(user_id, state, cm, msgs)
            return confirm + "\n\n" + complete
        else:
            return msgs["household_family"]

    # Fallback — shouldn't reach here
    return None


def _complete_onboarding(user_id: str, state: dict, cm, msgs: dict) -> str:
    """Mark onboarding as complete and stage family members."""
    state["completed"] = True
    _save_onboarding_state(user_id, state, cm)

    # Stage family members to context if any
    family = state.get("family_members", [])
    if family:
        content_lines = ["# Family\n"]
        for m in family:
            content_lines.append(f"## {m['name']}")
            content_lines.append(f"- Relationship: {m['relationship']}")
            content_lines.append("")

        try:
            cm.create_staging_entry(
                summary=f"Family members from onboarding ({len(family)} members)",
                content="\n".join(content_lines),
                category="family",
                source=f"telegram:{user_id}",
            )
        except Exception:
            pass  # Don't fail onboarding if staging fails

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
