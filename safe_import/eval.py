from pathlib import Path

from .inspection import FixtureDataError
from .main import run_pipeline
from .models import MappingProposal, ToolRequest
from .runner import RunnerError

RECORDED_DIR = Path(__file__).resolve().parent.parent / "recorded"

EXPECTED_DECISIONS = {
    "exact_headers": "proposal",
    "common_aliases": "proposal",
    "missing_email": "blocked",
}
PROPOSAL_SUMMARY = "required mappings and samples valid"


def _record(
    fixture_id: str, tool_request: ToolRequest, proposal: MappingProposal
) -> None:
    RECORDED_DIR.mkdir(exist_ok=True)
    (RECORDED_DIR / f"{fixture_id}.tool_request.json").write_text(
        tool_request.model_dump_json()
    )
    (RECORDED_DIR / f"{fixture_id}.proposal.json").write_text(
        proposal.model_dump_json()
    )


def main() -> int:
    failures = 0
    for fixture_id, expected in EXPECTED_DECISIONS.items():
        try:
            tool_request, proposal, response = run_pipeline(fixture_id)
        except (RunnerError, FixtureDataError) as exc:
            print(f"{fixture_id:<16}{'error':<10}{exc}")
            failures += 1
            continue
        if response.decision == "blocked":
            summary = response.blocked_reason
        else:
            summary = PROPOSAL_SUMMARY
        if response.decision == expected:
            # Only expected outcomes refresh the replay corpus.
            _record(fixture_id, tool_request, proposal)
        else:
            failures += 1
            summary = f"{summary} (UNEXPECTED: wanted {expected})"
        print(f"{fixture_id:<16}{response.decision:<10}{summary}")
    return failures


if __name__ == "__main__":
    raise SystemExit(main())
