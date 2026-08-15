import json
from pathlib import Path

from fastapi import FastAPI, HTTPException

from .inspection import FixtureDataError, inspect_import_context
from .models import FixtureId, MappingProposal, PreviewRequest, PreviewResponse, ToolRequest
from .runner import RunnerError, run_structured
from .validation import apply_gate

app = FastAPI(title="Safe Import Lite")

RECORDED_DIR = Path(__file__).resolve().parent.parent / "recorded"

NO_TOOLS = (
    "Do not use any built-in tools: do not run commands, do not read or write "
    "files, do not browse the web. Respond with a single JSON object only, "
    "matching the provided output schema."
)


def _tool_request_prompt(fixture_id: FixtureId) -> str:
    return (
        "You are the column-mapping step of Safe Import Lite, a CSV import "
        f"previewer. {NO_TOOLS} To begin, request inspection of the import "
        f"context for the fixture with ID {fixture_id!r} by naming the "
        "application-owned tool inspect_import_context."
    )


def _proposal_prompt(context: dict) -> str:
    return (
        f"You are the column-mapping step of Safe Import Lite. {NO_TOOLS} "
        "Here is the import context returned by inspect_import_context:\n"
        f"{json.dumps(context)}\n"
        "Propose a mapping from source CSV columns to the target schema. Map a "
        "source column only when its header and sample values credibly match "
        "the target field. List required target fields you could not map in "
        "unmapped_required_fields, and set recommendation to blocked when a "
        "required target field has no credible source column."
    )


def run_preview(fixture_id: FixtureId, record: bool = False) -> PreviewResponse:
    tool_request = run_structured(_tool_request_prompt(fixture_id), ToolRequest)
    if tool_request.fixture_id != fixture_id:
        raise RunnerError(
            f"model requested fixture {tool_request.fixture_id!r}, "
            f"expected {fixture_id!r}"
        )
    context = inspect_import_context(tool_request.fixture_id)
    proposal = run_structured(_proposal_prompt(context), MappingProposal)
    if record:
        # Only the eval path refreshes the replay corpus; serving traffic
        # must not overwrite the committed known-good responses.
        RECORDED_DIR.mkdir(exist_ok=True)
        (RECORDED_DIR / f"{fixture_id}.tool_request.json").write_text(
            tool_request.model_dump_json()
        )
        (RECORDED_DIR / f"{fixture_id}.proposal.json").write_text(
            proposal.model_dump_json()
        )
    decision, blocked_reason, gate_warnings = apply_gate(
        proposal, context["headers"], context["sample_rows"]
    )
    if decision == "blocked":
        return PreviewResponse(
            fixture_id=fixture_id, decision="blocked", blocked_reason=blocked_reason
        )
    # The gate owns the verdict: overwrite the model's own recommendation and
    # unmapped list so the response can't carry a contradictory verdict.
    merged = proposal.model_copy(
        update={
            "warnings": proposal.warnings + gate_warnings,
            "recommendation": "ready_for_review",
            "unmapped_required_fields": [],
        }
    )
    return PreviewResponse(fixture_id=fixture_id, decision="proposal", proposal=merged)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/imports/preview", response_model_exclude_none=True)
def preview(request: PreviewRequest) -> PreviewResponse:
    try:
        return run_preview(request.fixture_id)
    except RunnerError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except FixtureDataError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
