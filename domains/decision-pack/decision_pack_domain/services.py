from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .core import assess_submission_record
from .store import SubmissionStore


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _submission_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")


def _ensure_list(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    return [str(value).strip() for value in values if str(value).strip()]


def _version(record: dict[str, Any]) -> int:
    return int(record.get("version", 0))


def _check_version(record: dict[str, Any], expected_version: int | None) -> None:
    if expected_version is None:
        return
    if _version(record) != expected_version:
        raise ValueError("SUBMISSION_VERSION_CONFLICT")


def _impact_area_labels(impact_areas: list[str]) -> str:
    if not impact_areas:
        return "underwriting posture"
    return ", ".join(area.upper() for area in impact_areas)


def _normalize_impact_areas(values: Any) -> list[str]:
    allowed = {"pmf", "gtm", "team", "moat", "narrative", "evidence", "risk", "legal"}
    normalized = []
    for value in _ensure_list(values):
        lowered = value.lower()
        if lowered in allowed and lowered not in normalized:
            normalized.append(lowered)
    return normalized


def _normalize_severity(value: Any) -> str:
    lowered = str(value or "").strip().lower()
    return lowered if lowered in {"high", "medium", "low"} else "medium"


def _normalize_disclosure_sensitivity(value: Any) -> str:
    lowered = str(value or "").strip().lower()
    return lowered if lowered in {"restricted", "safe"} else "restricted"


def _new_change_id(existing_changes: list[dict[str, Any]]) -> str:
    return f"mc_{len(existing_changes) + 1}_{int(datetime.now(timezone.utc).timestamp())}"


def _new_delta_id() -> str:
    return f"delta_{int(datetime.now(timezone.utc).timestamp())}"


def _new_packet_id() -> str:
    return f"ip_delta_{int(datetime.now(timezone.utc).timestamp())}"


def _append_event(record: dict[str, Any], *, event_type: str, actor_role: str, summary: str, details: dict[str, Any] | None = None) -> None:
    record.setdefault("events", []).append(
        {
            "type": event_type,
            "actor_role": actor_role,
            "created_at": record["updated_at"],
            "summary": summary,
            **({"details": details} if details else {}),
        }
    )


def _base_record(submission_id: str, source_bundle: dict[str, Any], actor_role: str) -> dict[str, Any]:
    timestamp = _now_iso()
    assessed = assess_submission_record(
        {
            "source_bundle": deepcopy(source_bundle),
            "evidence_objects": [],
            "receipts": [],
            "canonical_pack": {"evidence_plan": {"tasks": []}},
        }
    )
    return {
        "submission_id": submission_id,
        "created_at": timestamp,
        "updated_at": timestamp,
        "version": 1,
        "source_bundle": deepcopy(source_bundle),
        "canonical_pack": assessed["canonical_pack"],
        "gate_result": assessed["gate_result"],
        "summary": assessed["summary"],
        "evidence_objects": [],
        "receipts": [],
        "material_change_log": [],
        "material_change_deltas": [],
        "latest_material_change_delta": None,
        "latest_safe_material_change_disclosure": None,
        "patent_intelligence_packets": [],
        "latest_patent_intelligence_packet": None,
        "latest_safe_patent_intelligence_summary": None,
        "reviewer_disposition": None,
        "reviewer_notes": [],
        "attorney_notes": [],
        "events": [
            {
                "type": "founder_intake_created",
                "actor_role": actor_role,
                "created_at": timestamp,
                "summary": "Founder submission created and initial canonical pack compiled.",
            }
        ],
    }


def create_submission(root_dir: str | Path, source_bundle: dict[str, Any], actor_role: str = "founder") -> dict[str, Any]:
    store = SubmissionStore(root_dir)
    record = _base_record(_submission_id(), source_bundle, actor_role)
    return store.create_submission(record)


def get_latest_submission(root_dir: str | Path) -> dict[str, Any] | None:
    return SubmissionStore(root_dir).read_latest_submission()


def attach_investor_questions(
    root_dir: str | Path,
    submission_id: str,
    questions: list[str],
    *,
    expected_version: int | None = None,
    actor_role: str = "investor",
) -> dict[str, Any]:
    normalized_questions = _ensure_list(questions)
    if not normalized_questions:
      raise ValueError("INVESTOR_QUESTION_VALIDATION_FAILED")

    store = SubmissionStore(root_dir)
    record = store.read_submission(submission_id)
    if not record:
        raise ValueError("FOUNDER_SUBMISSION_NOT_FOUND")
    _check_version(record, expected_version)

    source_bundle = deepcopy(record["source_bundle"])
    merged = []
    seen = set()
    for question in _ensure_list(source_bundle.get("diligence_questions")) + normalized_questions:
        lowered = question.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        merged.append(question)
    source_bundle["diligence_questions"] = merged

    next_record = deepcopy(record)
    next_record["source_bundle"] = source_bundle
    assessed = assess_submission_record(next_record)
    next_record["canonical_pack"] = assessed["canonical_pack"]
    next_record["gate_result"] = assessed["gate_result"]
    next_record["summary"] = assessed["summary"]
    next_record["version"] = _version(record) + 1
    next_record["updated_at"] = _now_iso()
    next_record["events"].append(
        {
            "type": "investor_questions_attached",
            "actor_role": actor_role,
            "created_at": next_record["updated_at"],
            "summary": f"Investor questions attached: {len(normalized_questions)} added.",
            "details": {
                "latest_batch": normalized_questions,
                "total_questions": len(merged),
            },
        }
    )
    return store.update_submission(submission_id, next_record)


def add_attorney_note(
    root_dir: str | Path,
    submission_id: str,
    body: str,
    *,
    title: str | None = None,
    category: str = "legal_review",
    expected_version: int | None = None,
    actor_role: str = "attorney",
) -> dict[str, Any]:
    normalized_body = str(body or "").strip()
    normalized_title = str(title or "").strip() or None
    normalized_category = str(category or "legal_review").strip() or "legal_review"
    if not normalized_body:
        raise ValueError("ATTORNEY_NOTE_VALIDATION_FAILED")

    store = SubmissionStore(root_dir)
    record = store.read_submission(submission_id)
    if not record:
        raise ValueError("FOUNDER_SUBMISSION_NOT_FOUND")
    _check_version(record, expected_version)

    next_record = deepcopy(record)
    next_record.setdefault("attorney_notes", []).append(
        {
            "note_id": f"attorney_note_{int(datetime.now(timezone.utc).timestamp())}",
            "created_at": _now_iso(),
            "title": normalized_title,
            "body": normalized_body,
            "category": normalized_category,
            "author_role": actor_role,
        }
    )
    next_record["version"] = _version(record) + 1
    next_record["updated_at"] = _now_iso()
    _append_event(
        next_record,
        event_type="attorney_note_added",
        actor_role=actor_role,
        summary=f"Attorney note added: {normalized_title}." if normalized_title else "Attorney note added.",
        details={"title": normalized_title, "category": normalized_category},
    )
    return store.update_submission(submission_id, next_record)


def build_operator_overview(root_dir: str | Path) -> dict[str, Any]:
    store = SubmissionStore(root_dir)
    latest = store.read_latest_submission()
    if not latest:
        return {
            "latest_submission": None,
            "next_step": None,
        }

    reviewer_disposition = latest.get("reviewer_disposition")
    latest_delta = latest.get("latest_material_change_delta")
    latest_disclosure = latest.get("latest_safe_material_change_disclosure")
    latest_patent = latest.get("latest_safe_patent_intelligence_summary")

    if reviewer_disposition and reviewer_disposition.get("status") == "needs_policy_review":
        next_step = {
            "surface": "reviewer",
            "label": "Escalate re-reviewed change-control hold in Reviewer Workspace",
        }
    elif latest_delta and not reviewer_disposition:
        next_step = {
            "surface": "reviewer",
            "label": "Review change-control hold in Reviewer Workspace",
        }
    elif latest_patent:
        next_step = {
            "surface": "attorney",
            "label": "Review IP and disclosure context in Attorney Workspace",
        }
    else:
        next_step = {
            "surface": "founder",
            "label": "Open Founder Workspace",
        }

    return {
        "latest_submission": {
            "submission_id": latest["submission_id"],
            "updated_at": latest.get("updated_at"),
            "final_status": latest.get("summary", {}).get("final_status"),
            "final_score": latest.get("summary", {}).get("final_score"),
            "coverage_pct": latest.get("summary", {}).get("coverage_pct"),
            "reviewer_disposition": reviewer_disposition,
            "material_change_control": {
                "latest_delta": latest_delta,
                "latest_disclosure": latest_disclosure,
                "pending_count": len([change for change in latest.get("material_change_log", []) if not change.get("processed_at")]),
            },
            "latest_patent_intelligence_summary": latest_patent,
            "attorney_notes": latest.get("attorney_notes", []),
            "priority_handoff": next_step,
            "promotion_eligibility": "held" if reviewer_disposition and reviewer_disposition.get("status") == "needs_policy_review" else "unreviewed",
        },
        "next_step": next_step,
    }


def set_reviewer_disposition(
    root_dir: str | Path,
    submission_id: str,
    status: str,
    *,
    note: str | None = None,
    expected_version: int | None = None,
    actor_role: str = "reviewer",
) -> dict[str, Any]:
    normalized_status = str(status or "").strip()
    normalized_note = str(note or "").strip() or None
    if not normalized_status:
        raise ValueError("REVIEWER_DISPOSITION_VALIDATION_FAILED")

    store = SubmissionStore(root_dir)
    record = store.read_submission(submission_id)
    if not record:
        raise ValueError("FOUNDER_SUBMISSION_NOT_FOUND")
    _check_version(record, expected_version)

    next_record = deepcopy(record)
    next_record["reviewer_disposition"] = {
        "updated_at": _now_iso(),
        "status": normalized_status,
        "note": normalized_note,
    }
    next_record["version"] = _version(record) + 1
    next_record["updated_at"] = _now_iso()
    _append_event(
        next_record,
        event_type="reviewer_disposition_set",
        actor_role=actor_role,
        summary=f"Reviewer disposition set to {normalized_status}.",
        details={"status": normalized_status, "note": normalized_note},
    )
    latest_delta = next_record.get("latest_material_change_delta")
    if latest_delta:
        _append_event(
            next_record,
            event_type="reviewer_material_change_re_reviewed" if normalized_status == "needs_policy_review" else "reviewer_material_change_cleared",
            actor_role=actor_role,
            summary=(
                f"Reviewer kept material change delta {latest_delta['delta_id']} in policy review."
                if normalized_status == "needs_policy_review"
                else f"Reviewer cleared material change delta {latest_delta['delta_id']} while setting disposition {normalized_status}."
            ),
            details={
                "latest_delta_id": latest_delta["delta_id"],
                "disposition_status": normalized_status,
                "note": normalized_note,
            },
        )
    return store.update_submission(submission_id, next_record)


def add_reviewer_note(
    root_dir: str | Path,
    submission_id: str,
    body: str,
    *,
    title: str | None = None,
    category: str = "general",
    expected_version: int | None = None,
    actor_role: str = "reviewer",
) -> dict[str, Any]:
    normalized_body = str(body or "").strip()
    normalized_title = str(title or "").strip() or None
    normalized_category = str(category or "general").strip() or "general"
    if not normalized_body:
        raise ValueError("REVIEWER_NOTE_VALIDATION_FAILED")
    if normalized_category not in {"general", "risk", "evidence_quality", "forwarding"}:
        raise ValueError("REVIEWER_NOTE_VALIDATION_FAILED")

    store = SubmissionStore(root_dir)
    record = store.read_submission(submission_id)
    if not record:
        raise ValueError("FOUNDER_SUBMISSION_NOT_FOUND")
    _check_version(record, expected_version)

    next_record = deepcopy(record)
    next_record.setdefault("reviewer_notes", []).append(
        {
            "note_id": f"reviewer_note_{int(datetime.now(timezone.utc).timestamp())}",
            "created_at": _now_iso(),
            "title": normalized_title,
            "body": normalized_body,
            "category": normalized_category,
            "author_role": actor_role,
        }
    )
    next_record["version"] = _version(record) + 1
    next_record["updated_at"] = _now_iso()
    _append_event(
        next_record,
        event_type="reviewer_note_added",
        actor_role=actor_role,
        summary=f"Reviewer note added: {normalized_title}." if normalized_title else "Reviewer note added.",
        details={"title": normalized_title, "category": normalized_category},
    )
    return store.update_submission(submission_id, next_record)


def run_patent_intelligence(
    root_dir: str | Path,
    submission_id: str,
    *,
    expected_version: int | None = None,
    actor_role: str = "founder",
) -> dict[str, Any]:
    store = SubmissionStore(root_dir)
    record = store.read_submission(submission_id)
    if not record:
        raise ValueError("FOUNDER_SUBMISSION_NOT_FOUND")
    _check_version(record, expected_version)

    next_record = deepcopy(record)
    text = " ".join(
        [
            str(next_record.get("source_bundle", {}).get("one_liner", "")).strip(),
            *next_record.get("source_bundle", {}).get("deck_bullets", []),
            *next_record.get("source_bundle", {}).get("notes", []),
            *next_record.get("source_bundle", {}).get("diligence_questions", []),
        ]
    ).lower()
    recommendation = "file" if any(token in text for token in ["defensible", "patent", "novel", "ip"]) else "hold"
    packet = {
        "packet_id": _new_packet_id(),
        "created_at": _now_iso(),
        "recommendation": recommendation,
        "hypothesis_map": [
            phrase for phrase in [
                str(next_record.get("source_bundle", {}).get("one_liner", "")).strip(),
                *next_record.get("source_bundle", {}).get("deck_bullets", []),
            ] if str(phrase).strip()
        ][:3],
        "novelty_delta_bullets": [
            "Current moat claims still need clearer novelty support against the closest substitute."
        ],
        "routing_actions": [
            "update moat risk register",
            "attach IP memo or filing rationale",
            "re-run underwriting with refreshed moat context",
        ],
    }
    safe_summary = {
        "packet_id": packet["packet_id"],
        "created_at": packet["created_at"],
        "headline": f"Patent intelligence {recommendation} recommendation",
        "summary": f"IP review refreshed the moat story and currently recommends {recommendation} while closer novelty support is collected.",
        "recommendation": recommendation,
        "highest_priority_slice": "moat",
    }
    next_record.setdefault("patent_intelligence_packets", []).append(packet)
    next_record["latest_patent_intelligence_packet"] = packet
    next_record["latest_safe_patent_intelligence_summary"] = safe_summary
    next_record["version"] = _version(record) + 1
    next_record["updated_at"] = _now_iso()
    _append_event(
        next_record,
        event_type="founder_patent_intelligence_ran",
        actor_role=actor_role,
        summary="Founder ran patent intelligence and refreshed the IP delta packet.",
        details={"latest_packet_id": packet["packet_id"], "recommendation": recommendation},
    )
    return store.update_submission(submission_id, next_record)


def log_material_change(
    root_dir: str | Path,
    submission_id: str,
    title: str,
    summary: str,
    *,
    severity: str = "medium",
    impact_areas: list[str] | None = None,
    disclosure_sensitivity: str = "restricted",
    expected_version: int | None = None,
    actor_role: str = "founder",
) -> dict[str, Any]:
    if not str(title).strip() or not str(summary).strip():
        raise ValueError("MATERIAL_CHANGE_VALIDATION_FAILED")

    store = SubmissionStore(root_dir)
    record = store.read_submission(submission_id)
    if not record:
        raise ValueError("FOUNDER_SUBMISSION_NOT_FOUND")
    _check_version(record, expected_version)

    next_record = deepcopy(record)
    existing_changes = next_record.setdefault("material_change_log", [])
    change = {
        "change_id": _new_change_id(existing_changes),
        "title": str(title).strip(),
        "summary": str(summary).strip(),
        "severity": _normalize_severity(severity),
        "impact_areas": _normalize_impact_areas(impact_areas or []),
        "disclosure_sensitivity": _normalize_disclosure_sensitivity(disclosure_sensitivity),
        "created_at": _now_iso(),
        "processed_at": None,
        "status": "logged",
    }
    existing_changes.append(change)
    next_record["version"] = _version(record) + 1
    next_record["updated_at"] = _now_iso()
    _append_event(
        next_record,
        event_type="material_change_logged",
        actor_role=actor_role,
        summary=f"Material change logged: {change['title']}.",
        details={
            "change_id": change["change_id"],
            "severity": change["severity"],
            "impact_areas": change["impact_areas"],
            "disclosure_sensitivity": change["disclosure_sensitivity"],
        },
    )
    return store.update_submission(submission_id, next_record)


def process_material_changes(
    root_dir: str | Path,
    submission_id: str,
    *,
    expected_version: int | None = None,
    actor_role: str = "founder",
) -> dict[str, Any]:
    store = SubmissionStore(root_dir)
    record = store.read_submission(submission_id)
    if not record:
        raise ValueError("FOUNDER_SUBMISSION_NOT_FOUND")
    _check_version(record, expected_version)

    next_record = deepcopy(record)
    pending_changes = [change for change in next_record.get("material_change_log", []) if not change.get("processed_at")]
    if not pending_changes:
        raise ValueError("NO_PENDING_MATERIAL_CHANGES")

    processed_at = _now_iso()
    impact_areas = []
    for change in pending_changes:
        for area in _normalize_impact_areas(change.get("impact_areas", [])):
            if area not in impact_areas:
                impact_areas.append(area)
    highest = "low"
    rank = {"low": 1, "medium": 2, "high": 3}
    for change in pending_changes:
        severity = _normalize_severity(change.get("severity"))
        if rank[severity] > rank[highest]:
            highest = severity
    restricted_count = sum(1 for change in pending_changes if change.get("disclosure_sensitivity") == "restricted")
    safe_disclosure = {
        "delta_id": _new_delta_id(),
        "created_at": processed_at,
        "headline": f"Material change review active ({highest})",
        "summary": (
            f"A restricted material change affecting {_impact_area_labels(impact_areas)} is under controlled review before wider disclosure."
            if restricted_count > 0
            else f"A material change affecting {_impact_area_labels(impact_areas)} is under review and may change underwriting posture."
        ),
        "impact_areas": impact_areas,
        "highest_severity": highest,
        "restricted_change_count": restricted_count,
    }
    delta = {
        "delta_id": safe_disclosure["delta_id"],
        "created_at": processed_at,
        "highest_severity": highest,
        "impact_areas": impact_areas,
        "change_ids": [change["change_id"] for change in pending_changes],
        "publish_restrictions": {
            "investor_forward": "restricted_pending_delta_review",
            "public_release": "restricted_pending_delta_review",
        },
        "safe_disclosure_summary": safe_disclosure,
    }
    for change in next_record.get("material_change_log", []):
        if change["change_id"] in delta["change_ids"]:
            change["processed_at"] = processed_at
            change["status"] = "processed"
    next_record.setdefault("material_change_deltas", []).append(delta)
    next_record["latest_material_change_delta"] = delta
    next_record["latest_safe_material_change_disclosure"] = safe_disclosure
    next_record["version"] = _version(record) + 1
    next_record["updated_at"] = _now_iso()
    _append_event(
        next_record,
        event_type="founder_material_change_processed",
        actor_role=actor_role,
        summary="Founder processed pending material changes into a delta packet.",
        details={
            "latest_delta_id": delta["delta_id"],
            "impact_areas": impact_areas,
            "highest_severity": highest,
        },
    )
    return store.update_submission(submission_id, next_record)


def rerun_underwriting(
    root_dir: str | Path,
    submission_id: str,
    *,
    expected_version: int | None = None,
    actor_role: str = "founder",
) -> dict[str, Any]:
    store = SubmissionStore(root_dir)
    record = store.read_submission(submission_id)
    if not record:
        raise ValueError("FOUNDER_SUBMISSION_NOT_FOUND")
    _check_version(record, expected_version)

    next_record = deepcopy(record)
    assessed = assess_submission_record(next_record)
    next_record["canonical_pack"] = assessed["canonical_pack"]
    next_record["gate_result"] = assessed["gate_result"]
    next_record["summary"] = assessed["summary"]
    next_record["version"] = _version(record) + 1
    next_record["updated_at"] = _now_iso()
    next_record["events"].append(
        {
            "type": "flow2_assessment_ran",
            "actor_role": actor_role,
            "created_at": next_record["updated_at"],
            "summary": f"Flow 2 assessment ran with {assessed['gate_result']['status']} at {assessed['gate_result']['score']}.",
        }
    )
    return store.update_submission(submission_id, next_record)


def ingest_receipt(
    root_dir: str | Path,
    submission_id: str,
    task_id: str,
    summary: str,
    excerpt_texts: list[str],
    *,
    expected_version: int | None = None,
    actor_role: str = "founder",
) -> dict[str, Any]:
    if not str(task_id).strip() or not str(summary).strip():
        raise ValueError("RECEIPT_INGESTION_VALIDATION_FAILED")

    store = SubmissionStore(root_dir)
    record = store.read_submission(submission_id)
    if not record:
        raise ValueError("FOUNDER_SUBMISSION_NOT_FOUND")
    _check_version(record, expected_version)

    next_record = deepcopy(record)
    tasks = next_record.get("canonical_pack", {}).get("evidence_plan", {}).get("tasks", [])
    matched = None
    for task in tasks:
        if str(task.get("task_id")) == str(task_id):
            matched = task
            break
    if not matched:
        raise ValueError("TASK_NOT_FOUND")

    evidence_id = f"E_{len(next_record.get('evidence_objects', [])) + 1}"
    receipt = {
        "receipt_id": f"R_{len(next_record.get('receipts', [])) + 1}",
        "task_id": task_id,
        "summary": str(summary).strip(),
        "excerpt_texts": _ensure_list(excerpt_texts),
        "created_at": _now_iso(),
    }
    evidence_object = {
        "evidence_id": evidence_id,
        "task_id": task_id,
        "summary": receipt["summary"],
        "excerpts": receipt["excerpt_texts"],
        "created_at": receipt["created_at"],
    }
    next_record.setdefault("receipts", []).append(receipt)
    next_record.setdefault("evidence_objects", []).append(evidence_object)

    assessed = assess_submission_record(next_record)
    canonical_pack = assessed["canonical_pack"]
    for task in canonical_pack.get("evidence_plan", {}).get("tasks", []):
        if str(task.get("task_id")) == str(task_id):
            task["status"] = "done"
            task["completed_at"] = receipt["created_at"]
            task["receipt_count"] = int(task.get("receipt_count", 0)) + 1
    next_record["canonical_pack"] = canonical_pack
    next_record["gate_result"] = assessed["gate_result"]
    next_record["summary"] = assessed["summary"]
    next_record["version"] = _version(record) + 1
    next_record["updated_at"] = _now_iso()
    next_record["events"].append(
        {
            "type": "receipt_ingested",
            "actor_role": actor_role,
            "created_at": next_record["updated_at"],
            "summary": f"Receipt ingested for task {task_id}.",
            "details": {
                "task_id": task_id,
                "evidence_id": evidence_id,
            },
        }
    )
    return store.update_submission(submission_id, next_record)
