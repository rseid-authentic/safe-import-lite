from .main import run_preview
from .runner import RunnerError

CASES = ("exact_headers", "common_aliases", "missing_email")
PROPOSAL_SUMMARY = "required mappings and samples valid"


def main() -> int:
    failures = 0
    for fixture_id in CASES:
        try:
            response = run_preview(fixture_id)
        except RunnerError as exc:
            print(f"{fixture_id:<16}{'error':<10}{exc}")
            failures += 1
            continue
        if response.decision == "blocked":
            summary = response.blocked_reason
        else:
            summary = PROPOSAL_SUMMARY
        print(f"{fixture_id:<16}{response.decision:<10}{summary}")
    return failures


if __name__ == "__main__":
    raise SystemExit(main())
