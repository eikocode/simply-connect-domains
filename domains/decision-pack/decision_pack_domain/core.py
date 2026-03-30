from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any


SLICE_LABELS = {
    "pmf": "PMF",
    "gtm": "GTM",
    "team": "Team",
    "moat": "Moat",
}


def _as_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _joined_text(source_bundle: dict[str, Any]) -> str:
    parts = []
    for key in ("one_liner",):
        value = str(source_bundle.get(key, "")).strip()
        if value:
            parts.append(value)
    for key in ("deck_bullets", "transcript_snippets", "notes", "metrics", "diligence_questions"):
        parts.extend(_as_list(source_bundle.get(key)))
    return " ".join(parts).lower()


def _coverage_pct(source_bundle: dict[str, Any]) -> int:
    signal_count = sum(
        1
        for key in ("deck_bullets", "transcript_snippets", "notes", "metrics")
        if _as_list(source_bundle.get(key))
    )
    question_bonus = 1 if _as_list(source_bundle.get("diligence_questions")) else 0
    return min(100, int(round(((signal_count + question_bonus) / 5) * 100)))


def _has_any(text: str, phrases: list[str]) -> bool:
    return any(phrase in text for phrase in phrases)


@dataclass
class SliceSignals:
    score: int
    reasons: list[str]
    warnings: list[str]
    strengths: list[str]
    open_questions: list[str]
    tasks: list[dict[str, Any]]
    coverage_pct: int


def _status(score: int, coverage_pct: int) -> str:
    if score >= 70:
        return "pass"
    if coverage_pct < 30:
        return "insufficient_evidence"
    return "needs_work"


def _slice_result(slice_id: str, signals: SliceSignals) -> dict[str, Any]:
    return {
        "slice_id": slice_id,
        "label": SLICE_LABELS[slice_id],
        "status": _status(signals.score, signals.coverage_pct),
        "score": signals.score,
        "threshold": 70,
        "reasons": signals.reasons,
        "warnings": signals.warnings,
        "strengths": signals.strengths,
        "open_questions": signals.open_questions,
        "tasks": signals.tasks,
        "inputs_summary": {
            "coverage_pct": signals.coverage_pct,
        },
    }


def _build_tasks(slice_id: str, entries: list[tuple[str, str, str]]) -> list[dict[str, Any]]:
    tasks: list[dict[str, Any]] = []
    for index, (title, priority, bind) in enumerate(entries, start=1):
        tasks.append(
            {
                "task_id": f"{slice_id}_task_{index}",
                "title": title,
                "status": "open",
                "priority": priority,
                "severity": "blocker" if priority == "high" else "normal",
                "binds_to": [bind],
            }
        )
    return tasks


def _build_question_tasks(diligence_questions: list[str]) -> list[dict[str, Any]]:
    tasks: list[dict[str, Any]] = []
    for index, question in enumerate(diligence_questions, start=1):
        tasks.append(
            {
                "task_id": f"TQ_{index}",
                "title": f"Answer diligence question with receipts: {question}",
                "status": "open",
                "priority": "high",
                "severity": "blocker",
                "binds_to": [f"question:{index}"],
                "question_text": question,
            }
        )
    return tasks


def _generate_pmf(text: str, source_bundle: dict[str, Any], coverage_pct: int) -> dict[str, Any]:
    score = 25
    reasons: list[str] = []
    warnings: list[str] = []
    strengths: list[str] = []
    open_questions: list[str] = []
    metrics = _as_list(source_bundle.get("metrics"))

    if _has_any(text, ["customer", "renew", "retention", "pilot", "usage"]):
        score += 22
        strengths.append("The pack includes early customer pull or retention signals.")
    else:
        reasons.append("The pack does not yet show durable customer pull.")
        open_questions.append("What evidence best shows repeat customer demand?")

    if metrics:
        score += 18
        strengths.append("The pack includes measurable traction evidence.")
    else:
        warnings.append("PMF claims are still weakly grounded in concrete metrics.")

    if _has_any(text, ["problem", "pain", "exception", "workflow"]):
        score += 15
    else:
        reasons.append("The problem being solved is still thinly framed.")

    score += round(coverage_pct * 0.15)
    tasks = _build_tasks(
        "pmf",
        [
            ("Show repeat customer pull", "high", "pmf:customer_pull"),
            ("Bind PMF claims to metrics", "medium", "pmf:claim_coverage"),
        ]
        if score < 70
        else [],
    )
    return _slice_result(
        "pmf",
        SliceSignals(min(score, 100), reasons, warnings, strengths, open_questions, tasks, coverage_pct),
    )


def _generate_gtm(text: str, source_bundle: dict[str, Any], coverage_pct: int) -> dict[str, Any]:
    score = 20
    reasons: list[str] = []
    warnings: list[str] = []
    strengths: list[str] = []
    open_questions: list[str] = []

    if _has_any(text, ["icp", "buyer", "operator", "warehouse", "3pl"]):
        score += 18
        strengths.append("The pack names a plausible initial customer segment or buyer.")
    else:
        reasons.append("The GTM story lacks a clearly bounded initial customer segment.")

    if _has_any(text, ["channel", "distribution", "sales", "partnership", "outbound"]):
        score += 16
        strengths.append("The pack includes at least one concrete GTM or distribution signal.")
    else:
        reasons.append("The pack does not yet show a concrete acquisition or distribution path.")
        open_questions.append("What is the most credible first channel for reaching repeatable customers?")

    if _has_any(text, ["pricing", "contract", "fee", "pay", "annual"]):
        score += 14
    else:
        warnings.append("The monetization path is still weakly evidenced for the current GTM motion.")
        open_questions.append("What evidence best shows the current buyer will pay through this GTM motion?")

    score += round(coverage_pct * 0.18)
    tasks = _build_tasks(
        "gtm",
        [
            ("Clarify acquisition channel", "high", "gtm:channel_path"),
            ("Bound monetization path", "high", "gtm:pricing_motion"),
            ("Increase GTM evidence coverage", "medium", "gtm:claim_coverage"),
        ]
        if score < 70
        else [],
    )
    return _slice_result(
        "gtm",
        SliceSignals(min(score, 100), reasons, warnings, strengths, open_questions, tasks, coverage_pct),
    )


def _generate_team(text: str, source_bundle: dict[str, Any], coverage_pct: int) -> dict[str, Any]:
    score = 22
    reasons: list[str] = []
    warnings: list[str] = []
    strengths: list[str] = []
    open_questions: list[str] = []

    if _has_any(text, ["founder", "team", "operator", "execution"]):
        score += 18
        strengths.append("The pack includes some indication of execution ownership.")
    else:
        reasons.append("The pack does not yet establish who will execute the plan.")

    if _has_any(text, ["experience", "renewed", "pilot", "customers"]):
        score += 14
    else:
        warnings.append("Founder credibility and operator proof are still lightly evidenced.")

    if _has_any(text, ["hiring", "role", "coverage"]):
        score += 12
    else:
        open_questions.append("What roles or capabilities are still missing from the execution plan?")

    score += round(coverage_pct * 0.16)
    tasks = _build_tasks(
        "team",
        [
            ("Clarify execution ownership", "high", "team:execution_ownership"),
            ("Bound missing team coverage", "medium", "team:role_coverage"),
        ]
        if score < 70
        else [],
    )
    return _slice_result(
        "team",
        SliceSignals(min(score, 100), reasons, warnings, strengths, open_questions, tasks, coverage_pct),
    )


def _generate_moat(text: str, source_bundle: dict[str, Any], coverage_pct: int) -> dict[str, Any]:
    score = 18
    reasons: list[str] = []
    warnings: list[str] = []
    strengths: list[str] = []
    open_questions: list[str] = []

    if _has_any(text, ["defensible", "defensibility", "moat", "novel", "patent", "ip"]):
        score += 18
        strengths.append("The pack acknowledges a defensibility or novelty story.")
    else:
        reasons.append("The pack does not yet establish why fast followers cannot replicate the offer.")
        open_questions.append("Why will this be defensible against fast followers?")

    if _has_any(text, ["workflow", "data", "integration", "embedded"]):
        score += 12
    else:
        warnings.append("The moat story lacks concrete implementation or wedge detail.")

    if _as_list(source_bundle.get("diligence_questions")):
        score += 10

    score += round(coverage_pct * 0.18)
    tasks = _build_tasks(
        "moat",
        [
            ("Clarify defensibility wedge", "high", "moat:defensibility"),
            ("Add novelty or design-around evidence", "medium", "moat:novelty"),
        ]
        if score < 70
        else [],
    )
    return _slice_result(
        "moat",
        SliceSignals(min(score, 100), reasons, warnings, strengths, open_questions, tasks, coverage_pct),
    )


def build_canonical_pack(source_bundle: dict[str, Any]) -> dict[str, Any]:
    coverage_pct = _coverage_pct(source_bundle)
    text = _joined_text(source_bundle)
    narrative = {
        "company_summary": str(source_bundle.get("one_liner", "")).strip(),
        "icp": next((line for line in _as_list(source_bundle.get("notes")) if line.lower().startswith("icp:")), None),
    }
    slice_assessments = {
        "pmf": _generate_pmf(text, source_bundle, coverage_pct),
        "gtm": _generate_gtm(text, source_bundle, coverage_pct),
        "team": _generate_team(text, source_bundle, coverage_pct),
        "moat": _generate_moat(text, source_bundle, coverage_pct),
    }
    tasks = _build_question_tasks(_as_list(source_bundle.get("diligence_questions")))
    for assessment in slice_assessments.values():
        tasks.extend(assessment.get("tasks", []))
    return {
        "meta": {
            "schema_version": "decision-pack-domain-v0",
            "compiled_level": "phase1",
        },
        "narrative": narrative,
        "claims": {
            "diligence_questions": _as_list(source_bundle.get("diligence_questions")),
            "key_claims": _as_list(source_bundle.get("deck_bullets")),
        },
        "evidence": {
            "objects": [{"summary": metric} for metric in _as_list(source_bundle.get("metrics"))],
        },
        "evidence_index": {
            "coverage_summary": {
                "coverage_pct": coverage_pct,
            }
        },
        "evidence_plan": {
            "tasks": tasks,
        },
        "slice_assessments": slice_assessments,
    }


def _preserve_task_statuses(tasks: list[dict[str, Any]], existing_tasks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    status_by_id = {
        str(task.get("task_id")): {
            "status": task.get("status", "open"),
            "completed_at": task.get("completed_at"),
            "receipt_count": task.get("receipt_count", 0),
        }
        for task in existing_tasks
    }
    preserved: list[dict[str, Any]] = []
    for task in tasks:
        existing = status_by_id.get(str(task.get("task_id")))
        if existing:
            preserved.append(
                {
                    **task,
                    "status": existing["status"],
                    "completed_at": existing["completed_at"],
                    "receipt_count": existing["receipt_count"],
                }
            )
        else:
            preserved.append(task)
    return preserved


def assess_submission_record(record: dict[str, Any]) -> dict[str, Any]:
    source_bundle = deepcopy(record.get("source_bundle", {}))
    existing_evidence = deepcopy(record.get("evidence_objects", []))
    existing_receipts = deepcopy(record.get("receipts", []))
    existing_tasks = deepcopy(record.get("canonical_pack", {}).get("evidence_plan", {}).get("tasks", []))

    if existing_receipts:
        metrics = _as_list(source_bundle.get("metrics"))
        metrics.extend(
            [
                receipt.get("summary", "")
                for receipt in existing_receipts
                if str(receipt.get("summary", "")).strip()
            ]
        )
        source_bundle["metrics"] = metrics

    assessed = assess_bundle(source_bundle)
    canonical_pack = assessed["canonical_pack"]
    canonical_pack["evidence"]["objects"] = existing_evidence
    canonical_pack["evidence_plan"]["tasks"] = _preserve_task_statuses(
        canonical_pack["evidence_plan"]["tasks"],
        existing_tasks,
    )
    assessed["canonical_pack"] = canonical_pack
    assessed["summary"]["coverage_pct"] = canonical_pack["evidence_index"]["coverage_summary"]["coverage_pct"]
    return assessed


def _gate_reason(assessment: dict[str, Any]) -> str:
    return (
        (assessment.get("warnings") or [None])[0]
        or (assessment.get("reasons") or [None])[0]
        or "This slice still has unresolved underwriting gaps."
    )


def assess_bundle(source_bundle: dict[str, Any]) -> dict[str, Any]:
    canonical_pack = build_canonical_pack(source_bundle)
    slices = canonical_pack["slice_assessments"]
    blocking = sorted(
        [
            {
                "slice_key": key,
                "label": value["label"],
                "status": value["status"],
                "score": value["score"],
                "threshold": value["threshold"],
                "reason": _gate_reason(value),
            }
            for key, value in slices.items()
            if value["status"] != "pass"
        ],
        key=lambda item: item["score"],
    )
    overall_score = round(sum(value["score"] for value in slices.values()) / len(slices))
    status = "PASS" if not blocking and overall_score >= 70 else "FAIL"
    return {
        "canonical_pack": canonical_pack,
        "gate_result": {
            "status": status,
            "score": overall_score,
            "primary_blocking_slice": blocking[0] if blocking else None,
            "blocking_slices": blocking,
            "reasons": [f"{item['label']}: {item['reason']}" for item in blocking],
            "warnings": [],
        },
        "summary": {
            "final_status": status.lower(),
            "final_score": overall_score,
            "coverage_pct": canonical_pack["evidence_index"]["coverage_summary"]["coverage_pct"],
            "primary_blocking_slice": blocking[0] if blocking else None,
        },
    }
