"""Decision Pack extension tools for simply-connect.

This adapter exposes the extracted shared-submission services through the
host's extension loader so a deployed simply-connect project can mutate and
inspect Decision Pack state directly.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from decision_pack_domain import (
    add_attorney_note,
    attach_investor_questions,
    build_operator_overview,
    create_submission,
    get_latest_submission,
    ingest_receipt,
    log_material_change,
    process_material_changes,
    rerun_underwriting,
    run_patent_intelligence,
    set_reviewer_disposition,
)
from decision_pack_domain.store import SubmissionStore

ROLE_TOOL_ALLOWLIST = {
    "founder": {
        "decision_pack_get_working_state",
        "decision_pack_set_active_submission",
        "decision_pack_focus_task",
        "decision_pack_work_top_blocker",
        "decision_pack_create_and_assess_submission",
        "decision_pack_create_submission",
        "decision_pack_get_latest_submission",
        "decision_pack_attach_investor_questions",
        "decision_pack_rerun_underwriting",
        "decision_pack_ingest_receipt",
        "decision_pack_answer_top_diligence_question",
        "decision_pack_run_patent_intelligence",
        "decision_pack_log_material_change",
        "decision_pack_process_material_changes",
        "decision_pack_process_pricing_change",
        "decision_pack_build_operator_overview",
    },
    "investor": {
        "decision_pack_get_working_state",
        "decision_pack_set_active_submission",
        "decision_pack_get_latest_submission",
        "decision_pack_attach_investor_questions",
    },
    "reviewer": {
        "decision_pack_get_working_state",
        "decision_pack_set_active_submission",
        "decision_pack_get_latest_submission",
        "decision_pack_set_reviewer_disposition",
        "decision_pack_review_material_change_hold",
        "decision_pack_build_operator_overview",
    },
    "attorney": {
        "decision_pack_get_working_state",
        "decision_pack_set_active_submission",
        "decision_pack_get_latest_submission",
        "decision_pack_add_attorney_note",
        "decision_pack_build_operator_overview",
    },
    "operator": {
        "decision_pack_get_working_state",
        "decision_pack_set_active_submission",
        "decision_pack_get_latest_submission",
        "decision_pack_build_operator_overview",
    },
}

TOOLS = [
    {
        "name": "decision_pack_get_working_state",
        "description": "Summarize the current submission, latest version, top blocker task, and likely next step for step-by-step interactive use.",
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "decision_pack_set_active_submission",
        "description": "Set the active submission for follow-up steps so later tool calls can omit submission_id.",
        "input_schema": {
            "type": "object",
            "properties": {
                "submission_id": {"type": "string"},
            },
            "required": ["submission_id"],
        },
    },
    {
        "name": "decision_pack_focus_task",
        "description": "Set the focused task on the active submission so later founder evidence steps can omit task_id.",
        "input_schema": {
            "type": "object",
            "properties": {
                "task_id": {"type": "string"},
                "submission_id": {"type": "string"},
            },
            "required": ["task_id"],
        },
    },
    {
        "name": "decision_pack_work_top_blocker",
        "description": "Focus the current top blocker task on the active submission and return the recommended next founder action.",
        "input_schema": {
            "type": "object",
            "properties": {
                "submission_id": {"type": "string"},
            },
        },
    },
    {
        "name": "decision_pack_create_and_assess_submission",
        "description": "Create a new submission, set it active, and immediately return the working state for the next founder step.",
        "input_schema": {
            "type": "object",
            "properties": {
                "source_bundle": {
                    "type": "object",
                    "description": "Founder-provided source bundle with one_liner, notes, metrics, deck_bullets, and diligence_questions.",
                },
                "actor_role": {"type": "string"},
            },
            "required": ["source_bundle"],
        },
    },
    {
        "name": "decision_pack_create_submission",
        "description": "Create a new canonical Decision Pack submission from a source bundle.",
        "input_schema": {
            "type": "object",
            "properties": {
                "source_bundle": {
                    "type": "object",
                    "description": "Founder-provided source bundle with one_liner, notes, metrics, deck_bullets, and diligence_questions.",
                },
                "actor_role": {
                    "type": "string",
                    "description": "Role creating the submission. Defaults to founder.",
                },
            },
            "required": ["source_bundle"],
        },
    },
    {
        "name": "decision_pack_get_latest_submission",
        "description": "Fetch the latest submission from the local Decision Pack state store.",
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "decision_pack_attach_investor_questions",
        "description": "Attach investor diligence questions to an existing submission and rebuild the canonical pack.",
        "input_schema": {
            "type": "object",
            "properties": {
                "submission_id": {"type": "string"},
                "questions": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "expected_version": {"type": "integer"},
                "actor_role": {"type": "string"},
            },
            "required": ["submission_id", "questions"],
        },
    },
    {
        "name": "decision_pack_rerun_underwriting",
        "description": "Reassess an existing submission and refresh its underwriting state.",
        "input_schema": {
            "type": "object",
            "properties": {
                "submission_id": {"type": "string"},
                "expected_version": {"type": "integer"},
                "actor_role": {"type": "string"},
            },
            "required": ["submission_id"],
        },
    },
    {
        "name": "decision_pack_ingest_receipt",
        "description": "Attach a founder evidence receipt to a task such as TQ_1 and recompute pack state.",
        "input_schema": {
            "type": "object",
            "properties": {
                "submission_id": {"type": "string"},
                "task_id": {"type": "string"},
                "summary": {"type": "string"},
                "excerpt_texts": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "expected_version": {"type": "integer"},
                "actor_role": {"type": "string"},
            },
            "required": ["submission_id", "task_id", "summary", "excerpt_texts"],
        },
    },
    {
        "name": "decision_pack_answer_top_diligence_question",
        "description": "Find the current top diligence blocker on the active submission, focus it, and ingest a receipt against it.",
        "input_schema": {
            "type": "object",
            "properties": {
                "submission_id": {"type": "string"},
                "summary": {"type": "string"},
                "excerpt_texts": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "expected_version": {"type": "integer"},
                "actor_role": {"type": "string"},
            },
            "required": ["summary", "excerpt_texts"],
        },
    },
    {
        "name": "decision_pack_run_patent_intelligence",
        "description": "Run the patent-intelligence side loop on the active submission.",
        "input_schema": {
            "type": "object",
            "properties": {
                "submission_id": {"type": "string"},
                "expected_version": {"type": "integer"},
                "actor_role": {"type": "string"},
            },
            "required": ["submission_id"],
        },
    },
    {
        "name": "decision_pack_log_material_change",
        "description": "Log a pending material change such as a pricing-model update on a submission.",
        "input_schema": {
            "type": "object",
            "properties": {
                "submission_id": {"type": "string"},
                "title": {"type": "string"},
                "summary": {"type": "string"},
                "severity": {"type": "string"},
                "impact_areas": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "disclosure_sensitivity": {"type": "string"},
                "expected_version": {"type": "integer"},
                "actor_role": {"type": "string"},
            },
            "required": ["submission_id", "title", "summary"],
        },
    },
    {
        "name": "decision_pack_process_material_changes",
        "description": "Process pending material changes into a controlled delta and safe disclosure summary.",
        "input_schema": {
            "type": "object",
            "properties": {
                "submission_id": {"type": "string"},
                "expected_version": {"type": "integer"},
                "actor_role": {"type": "string"},
            },
            "required": ["submission_id"],
        },
    },
    {
        "name": "decision_pack_process_pricing_change",
        "description": "Log and process a pricing-related material change on the active submission in one step.",
        "input_schema": {
            "type": "object",
            "properties": {
                "submission_id": {"type": "string"},
                "title": {"type": "string"},
                "summary": {"type": "string"},
                "severity": {"type": "string"},
                "impact_areas": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "disclosure_sensitivity": {"type": "string"},
                "expected_version": {"type": "integer"},
                "actor_role": {"type": "string"},
            },
            "required": ["summary"],
        },
    },
    {
        "name": "decision_pack_set_reviewer_disposition",
        "description": "Save the reviewer gate decision for a submission, such as needs_policy_review.",
        "input_schema": {
            "type": "object",
            "properties": {
                "submission_id": {"type": "string"},
                "status": {"type": "string"},
                "note": {"type": "string"},
                "expected_version": {"type": "integer"},
                "actor_role": {"type": "string"},
            },
            "required": ["submission_id", "status"],
        },
    },
    {
        "name": "decision_pack_review_material_change_hold",
        "description": "Save a reviewer hold disposition on the active material change using a policy-review default.",
        "input_schema": {
            "type": "object",
            "properties": {
                "submission_id": {"type": "string"},
                "note": {"type": "string"},
                "expected_version": {"type": "integer"},
                "actor_role": {"type": "string"},
            },
        },
    },
    {
        "name": "decision_pack_add_attorney_note",
        "description": "Add an attorney review note to the shared submission record.",
        "input_schema": {
            "type": "object",
            "properties": {
                "submission_id": {"type": "string"},
                "title": {"type": "string"},
                "body": {"type": "string"},
                "category": {"type": "string"},
                "expected_version": {"type": "integer"},
                "actor_role": {"type": "string"},
            },
            "required": ["submission_id", "body"],
        },
    },
    {
        "name": "decision_pack_build_operator_overview",
        "description": "Build the operator-facing overview over the latest governed Decision Pack state.",
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
]


def _state_root(cm) -> Path:
    return Path(cm._root) / ".decision_pack_state"


def _json(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)

def _working_state_path(root_dir: Path) -> Path:
    root_dir.mkdir(parents=True, exist_ok=True)
    return root_dir / "working_state.json"


def _read_working_state(root_dir: Path) -> dict[str, Any]:
    path = _working_state_path(root_dir)
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _write_working_state(root_dir: Path, payload: dict[str, Any]) -> dict[str, Any]:
    path = _working_state_path(root_dir)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    return payload


def _store(root_dir: Path) -> SubmissionStore:
    return SubmissionStore(root_dir)


def _get_submission(root_dir: Path, submission_id: str | None) -> dict[str, Any] | None:
    if not submission_id:
        return None
    return _store(root_dir).read_submission(submission_id)


def _pick_top_blocker(record: dict[str, Any] | None) -> dict[str, Any] | None:
    if not record:
        return None
    tasks = record.get("canonical_pack", {}).get("evidence_plan", {}).get("tasks", [])
    return next(
        (
            task for task in tasks
            if task.get("status") != "done" and task.get("severity") == "blocker"
        ),
        None,
    )


def _task_by_id(record: dict[str, Any] | None, task_id: str | None) -> dict[str, Any] | None:
    if not record or not task_id:
        return None
    for task in record.get("canonical_pack", {}).get("evidence_plan", {}).get("tasks", []):
        if task.get("task_id") == task_id:
            return task
    return None


def _refresh_working_state(
    root_dir: Path,
    *,
    active_submission_id: str | None = None,
    focused_task_id: str | None = None,
) -> dict[str, Any]:
    state = _read_working_state(root_dir)
    latest = get_latest_submission(root_dir)
    active_id = active_submission_id or state.get("active_submission_id") or (latest or {}).get("submission_id")
    active_record = _get_submission(root_dir, active_id) or latest

    overview = build_operator_overview(root_dir)
    if not active_record:
        empty = {
            "active_submission_id": None,
            "latest_submission": None,
            "latest_version": None,
            "focused_task_id": None,
            "top_blocker_task": None,
            "next_step": {
                "surface": "founder",
                "label": "Create the first submission.",
                "tool_name": "decision_pack_create_submission",
            },
        }
        return _write_working_state(root_dir, empty)

    candidate_focus = focused_task_id or state.get("focused_task_id")
    focused_task = _task_by_id(active_record, candidate_focus)
    top_blocker = _pick_top_blocker(active_record)
    if focused_task and focused_task.get("status") == "done":
        focused_task = None
    if not focused_task and top_blocker:
        focused_task = top_blocker

    next_step = overview.get("next_step") or {"surface": "founder", "label": "Continue founder work."}
    if focused_task:
        next_step = {
            "surface": "founder",
            "label": f"Work blocker {focused_task['task_id']}: {focused_task['title']}",
            "tool_name": "decision_pack_ingest_receipt" if str(focused_task.get("task_id", "")).startswith("TQ_") else "decision_pack_rerun_underwriting",
        }
    elif active_record.get("latest_material_change_delta") and not active_record.get("reviewer_disposition"):
        next_step = {
            "surface": "reviewer",
            "label": "Set reviewer disposition on the active material change.",
            "tool_name": "decision_pack_set_reviewer_disposition",
        }

    payload = {
        "active_submission_id": active_record.get("submission_id"),
        "latest_submission": {
            "submission_id": active_record.get("submission_id"),
            "summary": active_record.get("summary"),
            "reviewer_disposition": active_record.get("reviewer_disposition"),
        },
        "latest_version": active_record.get("version"),
        "focused_task_id": focused_task.get("task_id") if focused_task else None,
        "focused_task": focused_task,
        "top_blocker_task": top_blocker,
        "next_step": next_step,
    }
    return _write_working_state(root_dir, payload)


def _resolve_submission_id(root_dir: Path, submission_id: Any) -> str:
    explicit = str(submission_id or "").strip()
    if explicit:
        return explicit
    working = _refresh_working_state(root_dir)
    active_id = str(working.get("active_submission_id") or "").strip()
    if active_id:
        return active_id
    raise ValueError("FOUNDER_SUBMISSION_NOT_FOUND")


def _resolve_task_id(root_dir: Path, submission_id: str, task_id: Any) -> str:
    explicit = str(task_id or "").strip()
    if explicit:
        return explicit
    record = _get_submission(root_dir, submission_id)
    working = _refresh_working_state(root_dir, active_submission_id=submission_id)
    focused = _task_by_id(record, working.get("focused_task_id"))
    if focused and focused.get("status") != "done":
        return str(focused["task_id"])
    top = _pick_top_blocker(record)
    if top:
        return str(top["task_id"])
    raise ValueError("TASK_NOT_FOUND")


def _default_receipt_summary(task: dict[str, Any] | None) -> str:
    if not task:
        return "Founder evidence summary"
    title = str(task.get("title") or "Founder evidence").strip()
    return f"{title} evidence summary"


def _session_role(args: dict[str, Any]) -> str | None:
    role = str(args.get("__session_role") or "").strip().lower()
    return role or None


def _assert_role_allowed(name: str, args: dict[str, Any]) -> None:
    role = _session_role(args)
    if not role:
        return
    allowed = ROLE_TOOL_ALLOWLIST.get(role)
    if allowed is None or name in allowed:
        return
    raise ValueError(f"ROLE_ACTION_NOT_ALLOWED:{role}:{name}")


def dispatch(name: str, args: dict[str, Any], cm) -> str:
    root_dir = _state_root(cm)
    try:
        _assert_role_allowed(name, args)
        if name == "decision_pack_get_working_state":
            result = _refresh_working_state(root_dir)
        elif name == "decision_pack_set_active_submission":
            submission_id = _resolve_submission_id(root_dir, args.get("submission_id"))
            if not _get_submission(root_dir, submission_id):
                raise ValueError("FOUNDER_SUBMISSION_NOT_FOUND")
            result = _refresh_working_state(root_dir, active_submission_id=submission_id, focused_task_id=None)
        elif name == "decision_pack_focus_task":
            submission_id = _resolve_submission_id(root_dir, args.get("submission_id"))
            record = _get_submission(root_dir, submission_id)
            task_id = str(args.get("task_id", "")).strip()
            if not _task_by_id(record, task_id):
                raise ValueError("TASK_NOT_FOUND")
            result = _refresh_working_state(root_dir, active_submission_id=submission_id, focused_task_id=task_id)
        elif name == "decision_pack_work_top_blocker":
            submission_id = _resolve_submission_id(root_dir, args.get("submission_id"))
            record = _get_submission(root_dir, submission_id)
            top = _pick_top_blocker(record)
            if not top:
                raise ValueError("NO_ACTIVE_BLOCKER")
            result = _refresh_working_state(root_dir, active_submission_id=submission_id, focused_task_id=top["task_id"])
        elif name == "decision_pack_create_and_assess_submission":
            created = create_submission(
                root_dir,
                args.get("source_bundle", {}),
                actor_role=str(args.get("actor_role") or "founder"),
            )
            working = _refresh_working_state(root_dir, active_submission_id=created["submission_id"])
            result = {
                "submission": created,
                "working_state": working,
            }
        elif name == "decision_pack_create_submission":
            result = create_submission(
                root_dir,
                args.get("source_bundle", {}),
                actor_role=str(args.get("actor_role") or "founder"),
            )
            working = _refresh_working_state(root_dir, active_submission_id=result["submission_id"])
            result["working_state"] = working
        elif name == "decision_pack_get_latest_submission":
            result = get_latest_submission(root_dir)
            if result:
                result["working_state"] = _refresh_working_state(root_dir, active_submission_id=result["submission_id"])
        elif name == "decision_pack_attach_investor_questions":
            submission_id = _resolve_submission_id(root_dir, args.get("submission_id"))
            result = attach_investor_questions(
                root_dir,
                submission_id,
                list(args.get("questions", [])),
                expected_version=args.get("expected_version"),
                actor_role=str(args.get("actor_role") or "investor"),
            )
            result["working_state"] = _refresh_working_state(root_dir, active_submission_id=result["submission_id"])
        elif name == "decision_pack_rerun_underwriting":
            submission_id = _resolve_submission_id(root_dir, args.get("submission_id"))
            result = rerun_underwriting(
                root_dir,
                submission_id,
                expected_version=args.get("expected_version"),
                actor_role=str(args.get("actor_role") or "founder"),
            )
            result["working_state"] = _refresh_working_state(root_dir, active_submission_id=result["submission_id"])
        elif name == "decision_pack_ingest_receipt":
            submission_id = _resolve_submission_id(root_dir, args.get("submission_id"))
            task_id = _resolve_task_id(root_dir, submission_id, args.get("task_id"))
            result = ingest_receipt(
                root_dir,
                submission_id,
                task_id,
                str(args.get("summary", "")),
                list(args.get("excerpt_texts", [])),
                expected_version=args.get("expected_version"),
                actor_role=str(args.get("actor_role") or "founder"),
            )
            result["working_state"] = _refresh_working_state(root_dir, active_submission_id=result["submission_id"])
        elif name == "decision_pack_answer_top_diligence_question":
            submission_id = _resolve_submission_id(root_dir, args.get("submission_id"))
            record = _get_submission(root_dir, submission_id)
            diligence_task = next(
                (
                    task for task in record.get("canonical_pack", {}).get("evidence_plan", {}).get("tasks", [])
                    if str(task.get("task_id", "")).startswith("TQ_") and task.get("status") != "done"
                ),
                None,
            )
            if not diligence_task:
                raise ValueError("NO_ACTIVE_DILIGENCE_TASK")
            focused = _refresh_working_state(root_dir, active_submission_id=submission_id, focused_task_id=diligence_task["task_id"])
            receipt = ingest_receipt(
                root_dir,
                submission_id,
                diligence_task["task_id"],
                str(args.get("summary") or _default_receipt_summary(diligence_task)),
                list(args.get("excerpt_texts", [])),
                expected_version=args.get("expected_version"),
                actor_role=str(args.get("actor_role") or "founder"),
            )
            receipt["working_state"] = _refresh_working_state(root_dir, active_submission_id=receipt["submission_id"])
            result = {
                "focused_task": focused.get("focused_task"),
                "receipt_result": receipt,
            }
        elif name == "decision_pack_run_patent_intelligence":
            submission_id = _resolve_submission_id(root_dir, args.get("submission_id"))
            result = run_patent_intelligence(
                root_dir,
                submission_id,
                expected_version=args.get("expected_version"),
                actor_role=str(args.get("actor_role") or "founder"),
            )
            result["working_state"] = _refresh_working_state(root_dir, active_submission_id=result["submission_id"])
        elif name == "decision_pack_log_material_change":
            submission_id = _resolve_submission_id(root_dir, args.get("submission_id"))
            result = log_material_change(
                root_dir,
                submission_id,
                str(args.get("title", "")),
                str(args.get("summary", "")),
                severity=str(args.get("severity") or "medium"),
                impact_areas=list(args.get("impact_areas", [])),
                disclosure_sensitivity=str(args.get("disclosure_sensitivity") or "restricted"),
                expected_version=args.get("expected_version"),
                actor_role=str(args.get("actor_role") or "founder"),
            )
            result["working_state"] = _refresh_working_state(root_dir, active_submission_id=result["submission_id"])
        elif name == "decision_pack_process_material_changes":
            submission_id = _resolve_submission_id(root_dir, args.get("submission_id"))
            result = process_material_changes(
                root_dir,
                submission_id,
                expected_version=args.get("expected_version"),
                actor_role=str(args.get("actor_role") or "founder"),
            )
            result["working_state"] = _refresh_working_state(root_dir, active_submission_id=result["submission_id"])
        elif name == "decision_pack_process_pricing_change":
            submission_id = _resolve_submission_id(root_dir, args.get("submission_id"))
            working = _refresh_working_state(root_dir, active_submission_id=submission_id)
            logged = log_material_change(
                root_dir,
                submission_id,
                str(args.get("title") or "Pricing model changed"),
                str(args.get("summary", "")),
                severity=str(args.get("severity") or "medium"),
                impact_areas=list(args.get("impact_areas", ["gtm", "moat"])),
                disclosure_sensitivity=str(args.get("disclosure_sensitivity") or "restricted"),
                expected_version=args.get("expected_version", working.get("latest_version")),
                actor_role=str(args.get("actor_role") or "founder"),
            )
            processed = process_material_changes(
                root_dir,
                submission_id,
                expected_version=logged["version"],
                actor_role=str(args.get("actor_role") or "founder"),
            )
            processed["working_state"] = _refresh_working_state(root_dir, active_submission_id=processed["submission_id"])
            result = {
                "logged_change": logged,
                "processed_change": processed,
            }
        elif name == "decision_pack_set_reviewer_disposition":
            submission_id = _resolve_submission_id(root_dir, args.get("submission_id"))
            result = set_reviewer_disposition(
                root_dir,
                submission_id,
                str(args.get("status", "")),
                note=args.get("note"),
                expected_version=args.get("expected_version"),
                actor_role=str(args.get("actor_role") or "reviewer"),
            )
            result["working_state"] = _refresh_working_state(root_dir, active_submission_id=result["submission_id"])
        elif name == "decision_pack_review_material_change_hold":
            submission_id = _resolve_submission_id(root_dir, args.get("submission_id"))
            working = _refresh_working_state(root_dir, active_submission_id=submission_id)
            result = set_reviewer_disposition(
                root_dir,
                submission_id,
                "needs_policy_review",
                note=args.get("note") or "Material change remains under reviewer hold pending disclosure and legal review.",
                expected_version=args.get("expected_version", working.get("latest_version")),
                actor_role=str(args.get("actor_role") or "reviewer"),
            )
            result["working_state"] = _refresh_working_state(root_dir, active_submission_id=result["submission_id"])
        elif name == "decision_pack_add_attorney_note":
            submission_id = _resolve_submission_id(root_dir, args.get("submission_id"))
            result = add_attorney_note(
                root_dir,
                submission_id,
                str(args.get("body", "")),
                title=args.get("title"),
                category=str(args.get("category") or "legal_review"),
                expected_version=args.get("expected_version"),
                actor_role=str(args.get("actor_role") or "attorney"),
            )
            result["working_state"] = _refresh_working_state(root_dir, active_submission_id=result["submission_id"])
        elif name == "decision_pack_build_operator_overview":
            result = build_operator_overview(root_dir)
            _refresh_working_state(root_dir)
        else:
            raise ValueError(f"Unknown tool: {name}")
    except ValueError as exc:
        return _json({"error": str(exc), "tool": name})

    return _json(result)
