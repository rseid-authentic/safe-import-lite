import csv
from pathlib import Path

class FixtureDataError(RuntimeError):
    """An approved fixture's file is missing, unreadable, or empty."""


FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"

# Hardcoded allowlist: opaque fixture IDs -> files owned by the application.
# The model never supplies or sees a filesystem path.
FIXTURE_FILES = {
    "exact_headers": FIXTURES_DIR / "exact_headers.csv",
    "common_aliases": FIXTURES_DIR / "common_aliases.csv",
    "missing_email": FIXTURES_DIR / "missing_email.csv",
}

TARGET_SCHEMA = {
    "required": ["external_id", "email"],
    "optional": ["first_name", "last_name", "phone", "signup_date"],
}

MAX_SAMPLE_ROWS = 5


def inspect_import_context(fixture_id: str) -> dict:
    if fixture_id not in FIXTURE_FILES:
        raise KeyError(f"unknown fixture_id: {fixture_id!r}")
    path = FIXTURE_FILES[fixture_id]
    try:
        with path.open(newline="") as f:
            reader = csv.reader(f)
            try:
                headers = next(reader)
            except StopIteration:
                raise FixtureDataError(f"fixture {fixture_id!r} file is empty")
            sample_rows = [row for _, row in zip(range(MAX_SAMPLE_ROWS), reader)]
    except OSError as exc:
        raise FixtureDataError(
            f"fixture {fixture_id!r} file is missing or unreadable: {exc}"
        ) from exc
    return {
        "headers": headers,
        "sample_rows": sample_rows,
        "target_schema": TARGET_SCHEMA,
    }
