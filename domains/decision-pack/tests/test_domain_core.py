from decision_pack_domain.core import assess_bundle


def test_assess_bundle_builds_four_slice_assessments():
    result = assess_bundle(
        {
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
                "Positioning: AI copilot for warehouse exception handling",
            ],
            "metrics": [
                "3 pilot customers renewed",
                "31% faster exception resolution",
            ],
            "diligence_questions": [
                "Why will this be defensible against fast followers?",
            ],
        }
    )

    slices = result["canonical_pack"]["slice_assessments"]
    assert set(slices.keys()) == {"pmf", "gtm", "team", "moat"}
    assert result["summary"]["coverage_pct"] > 0
    assert result["gate_result"]["score"] > 0


def test_gtm_and_moat_become_blockers_when_signals_are_thin():
    result = assess_bundle(
        {
            "one_liner": "Tool for operations.",
            "deck_bullets": ["Helps teams work faster."],
            "transcript_snippets": [],
            "notes": [],
            "metrics": [],
            "diligence_questions": [],
        }
    )

    slices = result["canonical_pack"]["slice_assessments"]
    assert slices["gtm"]["status"] != "pass"
    assert slices["moat"]["status"] != "pass"
    assert result["gate_result"]["primary_blocking_slice"] is not None
