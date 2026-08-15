import pytest
from fastapi.testclient import TestClient

import safe_import.main as main
from safe_import.models import FieldMapping, MappingProposal, ToolRequest
from safe_import.runner import RunnerError

client = TestClient(main.app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.parametrize(
    "fixture_id",
    ["nope", "../fixtures/exact_headers.csv", "/etc/passwd", "fixtures/exact_headers.csv"],
)
def test_unknown_or_pathlike_fixture_rejected(fixture_id):
    response = client.post("/imports/preview", json={"fixture_id": fixture_id})
    assert response.status_code == 422


def test_preview_happy_path_with_stubbed_runner(monkeypatch):
    responses = iter(
        [
            ToolRequest(tool="inspect_import_context", fixture_id="exact_headers"),
            MappingProposal(
                mappings=[
                    FieldMapping(
                        source_field="external_id",
                        target_field="external_id",
                        confidence=1.0,
                        reason="exact match",
                    ),
                    FieldMapping(
                        source_field="email",
                        target_field="email",
                        confidence=1.0,
                        reason="exact match",
                    ),
                ],
                unmapped_required_fields=[],
                warnings=[],
                recommendation="ready_for_review",
            ),
        ]
    )
    monkeypatch.setattr(
        main, "run_structured", lambda prompt, model, record_to=None: next(responses)
    )
    response = client.post("/imports/preview", json={"fixture_id": "exact_headers"})
    assert response.status_code == 200
    body = response.json()
    assert body["decision"] == "proposal"
    assert body["fixture_id"] == "exact_headers"
    targets = {m["target_field"] for m in body["proposal"]["mappings"]}
    assert {"external_id", "email"} <= targets


def test_runner_failure_is_visible(monkeypatch):
    def boom(prompt, model, record_to=None):
        raise RunnerError("codex exec failed with exit code 1: outage")

    monkeypatch.setattr(main, "run_structured", boom)
    response = client.post("/imports/preview", json={"fixture_id": "exact_headers"})
    assert response.status_code == 502
    assert "codex exec failed" in response.json()["detail"]
