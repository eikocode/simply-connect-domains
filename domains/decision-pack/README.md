# decision-pack domain

Phase 1 extraction of the Decision Pack underwriting domain for `simply-connect`.

## Current scope

This domain currently provides a small underwriting core:

- compile a source bundle into a canonical pack
- generate PMF, GTM, Team, and Moat slice assessments
- derive a simple gate result and blocking-slice summary
- persist a lightweight submission record for the founder/investor/evidence loop
- attach investor questions, rerun assessment, and ingest receipts
- run patent intelligence on the shared submission
- log and process material changes into a safe disclosure delta
- add reviewer notes and reviewer disposition on the same submission
- add attorney notes and build an operator overview over the governed submission

It does not yet port the full standalone `decision_pack` runtime, browser workspaces, or persistence model.
It now does include a thin simply-connect extension adapter so initialized projects
can call the extracted submission services through the host extension loader.

## Package layout

- `profile.json`
  domain metadata for `simply-connect`
- `AGENT.md`
  domain-level agent instructions
- `context/`
  context skeleton for shared underwriting state
- `roles/`
  role-specific agent framing
- `decision_pack_domain/`
  Phase 1 and Phase 2 Python underwriting core + lightweight services
- `domains/decision_pack/extension/`
  simply-connect extension shim that exposes the extracted services as host tools
- `tests/`
  parity-oriented smoke tests for the extracted core

## Quick check

```bash
cd /Users/andrew/backup/work/simply-connect-workspace/simply-connect-domains/domains/decision-pack
PYTHONPATH=. python3 -m pytest tests -q
```

## Deploy into simply-connect

```bash
cd /Users/andrew/backup/work/simply-connect-workspace
mkdir -p deployments/decision-pack
cd /Users/andrew/backup/work/simply-connect-workspace/simply-connect
sc-admin --data-dir /Users/andrew/backup/work/simply-connect-workspace/deployments/decision-pack init decision-pack
```

The initialized project now includes:

- `decision_pack_domain/`
  local shared-submission service library
- `domains/decision_pack/extension/tools.py`
  importable simply-connect extension entrypoint
- `.decision_pack_state/`
  runtime state directory created on first tool use

## Example usage

```bash
cd /Users/andrew/backup/work/simply-connect-workspace/simply-connect-domains/domains/decision-pack
PYTHONPATH=. python3 - <<'PY'
from decision_pack_domain.core import assess_bundle

result = assess_bundle({
    "one_liner": "FluxHalo is an AI copilot for warehouse exception handling for 3PL operators.",
    "deck_bullets": [
        "FluxHalo helps 3PL teams resolve warehouse exceptions faster."
    ],
    "notes": [
        "ICP: 3PL warehouse operators"
    ],
    "metrics": [
        "3 pilot customers renewed",
        "31% faster exception resolution"
    ],
    "diligence_questions": [
        "Why will this be defensible against fast followers?"
    ],
})

print(result["summary"])
print(result["canonical_pack"]["slice_assessments"]["gtm"])
PY
```

## Phase 2 service loop

```bash
cd /Users/andrew/backup/work/simply-connect-workspace/simply-connect-domains/domains/decision-pack
PYTHONPATH=. python3 - <<'PY'
from pathlib import Path
from tempfile import TemporaryDirectory

from decision_pack_domain.services import (
    attach_investor_questions,
    create_submission,
    ingest_receipt,
    rerun_underwriting,
)

with TemporaryDirectory() as temp_dir:
    root = Path(temp_dir)
    submission = create_submission(root, {
        "one_liner": "FluxHalo is an AI copilot for warehouse exception handling for 3PL operators.",
        "deck_bullets": ["FluxHalo helps 3PL teams resolve warehouse exceptions faster."],
        "notes": ["ICP: 3PL warehouse operators"],
        "metrics": ["3 pilot customers renewed"],
        "diligence_questions": [],
    })
    submission = attach_investor_questions(
        root,
        submission["submission_id"],
        ["Why will this be defensible against fast followers?"],
        expected_version=submission["version"],
    )
    submission = rerun_underwriting(
        root,
        submission["submission_id"],
        expected_version=submission["version"],
    )
    submission = ingest_receipt(
        root,
        submission["submission_id"],
        "TQ_1",
        "Answer diligence question with receipts: Why will this be defensible against fast followers? evidence summary",
        ["Three pilot customers renewed after 60 days.", "Average exception resolution time improved by 31%."],
        expected_version=submission["version"],
    )
    print(submission["summary"])
PY
```

## Phase 3 side loops

```bash
cd /Users/andrew/backup/work/simply-connect-workspace/simply-connect-domains/domains/decision-pack
PYTHONPATH=. python3 - <<'PY'
from pathlib import Path
from tempfile import TemporaryDirectory

from decision_pack_domain.services import (
    create_submission,
    log_material_change,
    process_material_changes,
    run_patent_intelligence,
)

with TemporaryDirectory() as temp_dir:
    root = Path(temp_dir)
    submission = create_submission(root, {
        "one_liner": "FluxHalo is an AI copilot for warehouse exception handling for 3PL operators.",
        "deck_bullets": ["FluxHalo helps 3PL teams resolve warehouse exceptions faster."],
        "notes": ["ICP: 3PL warehouse operators"],
        "metrics": ["3 pilot customers renewed"],
        "diligence_questions": [],
    })
    submission = run_patent_intelligence(
        root,
        submission["submission_id"],
        expected_version=submission["version"],
    )
    submission = log_material_change(
        root,
        submission["submission_id"],
        "Pricing model changed",
        "FluxHalo moved from usage-based pricing to annual platform contracts with a one-time implementation fee.",
        severity="medium",
        impact_areas=["gtm", "moat"],
        disclosure_sensitivity="restricted",
        expected_version=submission["version"],
    )
    submission = process_material_changes(
        root,
        submission["submission_id"],
        expected_version=submission["version"],
    )
    print(submission["latest_safe_material_change_disclosure"])
    print(submission["latest_safe_patent_intelligence_summary"])
PY
```

## Phase 4 reviewer governance

```bash
cd /Users/andrew/backup/work/simply-connect-workspace/simply-connect-domains/domains/decision-pack
PYTHONPATH=. python3 - <<'PY'
from pathlib import Path
from tempfile import TemporaryDirectory

from decision_pack_domain.services import (
    add_reviewer_note,
    create_submission,
    log_material_change,
    process_material_changes,
    set_reviewer_disposition,
)

with TemporaryDirectory() as temp_dir:
    root = Path(temp_dir)
    submission = create_submission(root, {
        "one_liner": "FluxHalo is an AI copilot for warehouse exception handling for 3PL operators.",
        "deck_bullets": ["FluxHalo helps 3PL teams resolve warehouse exceptions faster."],
        "notes": ["ICP: 3PL warehouse operators"],
        "metrics": ["3 pilot customers renewed"],
        "diligence_questions": [],
    })
    submission = log_material_change(
        root,
        submission["submission_id"],
        "Pricing model changed",
        "FluxHalo moved from usage-based pricing to annual platform contracts with a one-time implementation fee.",
        severity="medium",
        impact_areas=["gtm", "moat"],
        disclosure_sensitivity="restricted",
        expected_version=submission["version"],
    )
    submission = process_material_changes(
        root,
        submission["submission_id"],
        expected_version=submission["version"],
    )
    submission = add_reviewer_note(
        root,
        submission["submission_id"],
        "Forwarding should stay blocked until pricing disclosure language is tightened.",
        title="Pricing disclosure hold",
        category="forwarding",
        expected_version=submission["version"],
    )
    submission = set_reviewer_disposition(
        root,
        submission["submission_id"],
        "needs_policy_review",
        note="Pricing changed materially after initial underwriting. Do not forward until disclosure review is complete.",
        expected_version=submission["version"],
    )
    print(submission["reviewer_disposition"])
    print([event["type"] for event in submission["events"] if event["type"].startswith("reviewer_")])
PY
```

## Phase 5 attorney and operator

```bash
cd /Users/andrew/backup/work/simply-connect-workspace/simply-connect-domains/domains/decision-pack
PYTHONPATH=. python3 - <<'PY'
from pathlib import Path
from tempfile import TemporaryDirectory

from decision_pack_domain.services import (
    add_attorney_note,
    build_operator_overview,
    create_submission,
    log_material_change,
    process_material_changes,
    set_reviewer_disposition,
)

with TemporaryDirectory() as temp_dir:
    root = Path(temp_dir)
    submission = create_submission(root, {
        "one_liner": "FluxHalo is an AI copilot for warehouse exception handling for 3PL operators.",
        "deck_bullets": ["FluxHalo helps 3PL teams resolve warehouse exceptions faster."],
        "notes": ["ICP: 3PL warehouse operators"],
        "metrics": ["3 pilot customers renewed"],
        "diligence_questions": [],
    })
    submission = log_material_change(
        root,
        submission["submission_id"],
        "Pricing model changed",
        "FluxHalo moved from usage-based pricing to annual platform contracts with a one-time implementation fee.",
        severity="medium",
        impact_areas=["gtm", "moat"],
        disclosure_sensitivity="restricted",
        expected_version=submission["version"],
    )
    submission = process_material_changes(
        root,
        submission["submission_id"],
        expected_version=submission["version"],
    )
    submission = set_reviewer_disposition(
        root,
        submission["submission_id"],
        "needs_policy_review",
        note="Pricing changed materially after initial underwriting. Do not forward until disclosure review is complete.",
        expected_version=submission["version"],
    )
    submission = add_attorney_note(
        root,
        submission["submission_id"],
        "Investor-facing materials should clearly disclose the shift to annual contracts and implementation fees.",
        title="Pricing disclosure update required",
        expected_version=submission["version"],
    )
    overview = build_operator_overview(root)
    print(submission["attorney_notes"][-1])
    print(overview["latest_submission"]["priority_handoff"])
PY
```
