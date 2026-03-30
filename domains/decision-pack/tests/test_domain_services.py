from pathlib import Path

from decision_pack_domain.services import (
    add_attorney_note,
    add_reviewer_note,
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


def _source_bundle():
    return {
        "one_liner": "FluxHalo is an AI copilot for warehouse exception handling for 3PL operators.",
        "deck_bullets": [
            "FluxHalo helps 3PL teams resolve warehouse exceptions faster.",
            "The product reduces manual exception triage and follow-up work.",
        ],
        "transcript_snippets": [
            "Founder: Customers use us to cut exception resolution time.",
        ],
        "notes": [
            "Company: FluxHalo",
            "ICP: 3PL warehouse operators",
        ],
        "metrics": [
            "3 pilot customers renewed",
            "31% faster exception resolution",
        ],
        "diligence_questions": [],
    }


def test_phase2_service_loop_create_question_assess_and_receipt(tmp_path: Path):
    record = create_submission(tmp_path, _source_bundle())
    submission_id = record["submission_id"]
    assert get_latest_submission(tmp_path)["submission_id"] == submission_id

    record = attach_investor_questions(
        tmp_path,
        submission_id,
        ["Why will this be defensible against fast followers?"],
        expected_version=record["version"],
    )
    assert record["version"] == 2
    task_ids = [task["task_id"] for task in record["canonical_pack"]["evidence_plan"]["tasks"]]
    assert "TQ_1" in task_ids

    record = rerun_underwriting(
        tmp_path,
        submission_id,
        expected_version=record["version"],
    )
    assert record["version"] == 3

    record = ingest_receipt(
        tmp_path,
        submission_id,
        "TQ_1",
        "Answer diligence question with receipts: Why will this be defensible against fast followers? evidence summary",
        [
            "Three pilot customers renewed after 60 days.",
            "Average exception resolution time improved by 31%.",
        ],
        expected_version=record["version"],
    )
    assert record["version"] == 4
    assert record["receipts"][-1]["task_id"] == "TQ_1"
    tq_task = next(task for task in record["canonical_pack"]["evidence_plan"]["tasks"] if task["task_id"] == "TQ_1")
    assert tq_task["status"] == "done"
    assert record["evidence_objects"][-1]["task_id"] == "TQ_1"


def test_phase3_patent_and_material_change_loops_update_the_shared_submission(tmp_path: Path):
    record = create_submission(tmp_path, _source_bundle())
    submission_id = record["submission_id"]

    record = run_patent_intelligence(
        tmp_path,
        submission_id,
        expected_version=record["version"],
    )
    assert record["latest_patent_intelligence_packet"] is not None
    assert record["latest_safe_patent_intelligence_summary"] is not None

    record = log_material_change(
        tmp_path,
        submission_id,
        "Pricing model changed",
        "FluxHalo moved from usage-based pricing to annual platform contracts with a one-time implementation fee.",
        severity="medium",
        impact_areas=["gtm", "moat"],
        disclosure_sensitivity="restricted",
        expected_version=record["version"],
    )
    assert len(record["material_change_log"]) == 1
    assert record["material_change_log"][0]["processed_at"] is None

    record = process_material_changes(
        tmp_path,
        submission_id,
        expected_version=record["version"],
    )
    assert record["latest_material_change_delta"] is not None
    assert record["latest_safe_material_change_disclosure"] is not None
    assert "under controlled review before wider disclosure" in record["latest_safe_material_change_disclosure"]["summary"]
    assert record["material_change_log"][0]["processed_at"] is not None


def test_phase4_reviewer_governance_records_hold_state_and_notes(tmp_path: Path):
    record = create_submission(tmp_path, _source_bundle())
    submission_id = record["submission_id"]

    record = log_material_change(
        tmp_path,
        submission_id,
        "Pricing model changed",
        "FluxHalo moved from usage-based pricing to annual platform contracts with a one-time implementation fee.",
        severity="medium",
        impact_areas=["gtm", "moat"],
        disclosure_sensitivity="restricted",
        expected_version=record["version"],
    )
    record = process_material_changes(
        tmp_path,
        submission_id,
        expected_version=record["version"],
    )

    record = add_reviewer_note(
        tmp_path,
        submission_id,
        "Forwarding should stay blocked until pricing disclosure language is tightened.",
        title="Pricing disclosure hold",
        category="forwarding",
        expected_version=record["version"],
    )
    assert record["reviewer_notes"][-1]["title"] == "Pricing disclosure hold"

    record = set_reviewer_disposition(
        tmp_path,
        submission_id,
        "needs_policy_review",
        note="Pricing changed materially after initial underwriting. Do not forward until disclosure review is complete.",
        expected_version=record["version"],
    )
    assert record["reviewer_disposition"]["status"] == "needs_policy_review"
    assert record["reviewer_disposition"]["note"].startswith("Pricing changed materially")
    event_types = [event["type"] for event in record["events"]]
    assert "reviewer_note_added" in event_types
    assert "reviewer_disposition_set" in event_types
    assert "reviewer_material_change_re_reviewed" in event_types


def test_phase5_attorney_and_operator_read_the_same_governed_submission(tmp_path: Path):
    record = create_submission(tmp_path, _source_bundle())
    submission_id = record["submission_id"]

    record = run_patent_intelligence(
        tmp_path,
        submission_id,
        expected_version=record["version"],
    )
    record = log_material_change(
        tmp_path,
        submission_id,
        "Pricing model changed",
        "FluxHalo moved from usage-based pricing to annual platform contracts with a one-time implementation fee.",
        severity="medium",
        impact_areas=["gtm", "moat"],
        disclosure_sensitivity="restricted",
        expected_version=record["version"],
    )
    record = process_material_changes(
        tmp_path,
        submission_id,
        expected_version=record["version"],
    )
    record = set_reviewer_disposition(
        tmp_path,
        submission_id,
        "needs_policy_review",
        note="Pricing changed materially after initial underwriting. Do not forward until disclosure review is complete.",
        expected_version=record["version"],
    )
    record = add_attorney_note(
        tmp_path,
        submission_id,
        "Investor-facing materials should clearly disclose the shift to annual contracts and implementation fees.",
        title="Pricing disclosure update required",
        expected_version=record["version"],
    )

    overview = build_operator_overview(tmp_path)
    assert record["attorney_notes"][-1]["title"] == "Pricing disclosure update required"
    assert overview["latest_submission"]["submission_id"] == submission_id
    assert overview["latest_submission"]["reviewer_disposition"]["status"] == "needs_policy_review"
    assert overview["latest_submission"]["material_change_control"]["latest_delta"] is not None
    assert overview["latest_submission"]["priority_handoff"]["surface"] == "reviewer"
    assert overview["latest_submission"]["promotion_eligibility"] == "held"
