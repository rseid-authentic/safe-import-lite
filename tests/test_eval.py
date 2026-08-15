import safe_import.eval as eval_module
from safe_import.models import (
    FieldMapping,
    MappingProposal,
    PreviewResponse,
    ToolRequest,
)


def pipeline_stub(decision_by_fixture):
    def stub(fixture_id):
        tool_request = ToolRequest(
            tool="inspect_import_context", fixture_id=fixture_id
        )
        proposal = MappingProposal(
            mappings=[
                FieldMapping(
                    source_field="external_id",
                    target_field="external_id",
                    confidence=1.0,
                    reason="test",
                )
            ],
            unmapped_required_fields=[],
            warnings=[],
            recommendation="ready_for_review",
        )
        decision = decision_by_fixture[fixture_id]
        response = PreviewResponse(
            fixture_id=fixture_id,
            decision=decision,
            proposal=proposal if decision == "proposal" else None,
            blocked_reason="no credible email column" if decision == "blocked" else None,
        )
        return tool_request, proposal, response

    return stub


def test_expected_decisions_pass_and_record(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(eval_module, "RECORDED_DIR", tmp_path)
    monkeypatch.setattr(
        eval_module,
        "run_pipeline",
        pipeline_stub(
            {
                "exact_headers": "proposal",
                "common_aliases": "proposal",
                "missing_email": "blocked",
            }
        ),
    )
    assert eval_module.main() == 0
    assert (tmp_path / "missing_email.proposal.json").exists()
    assert "UNEXPECTED" not in capsys.readouterr().out


def test_wrong_decision_fails_and_does_not_record(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(eval_module, "RECORDED_DIR", tmp_path)
    monkeypatch.setattr(
        eval_module,
        "run_pipeline",
        pipeline_stub(
            {
                "exact_headers": "blocked",
                "common_aliases": "proposal",
                "missing_email": "blocked",
            }
        ),
    )
    assert eval_module.main() == 1
    assert not (tmp_path / "exact_headers.proposal.json").exists()
    assert (tmp_path / "common_aliases.proposal.json").exists()
    assert "UNEXPECTED: wanted proposal" in capsys.readouterr().out
