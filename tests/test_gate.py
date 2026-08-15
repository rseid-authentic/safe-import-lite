from safe_import.models import FieldMapping, MappingProposal
from safe_import.validation import NO_CREDIBLE_EMAIL, apply_gate

EXACT_HEADERS = ["external_id", "email", "first_name", "last_name", "phone", "signup_date"]
EXACT_ROWS = [
    ["1001", "alice@example.com", "Alice", "Anderson", "555-0101", "2026-01-05"],
    ["1002", "bob@example.com", "Bob", "Baker", "555-0102", "2026-01-12"],
]

ALIAS_HEADERS = ["contact_id", "email_address", "fname", "lname", "phone", "signup_date"]
ALIAS_ROWS = [
    ["2001", "frank@example.com", "Frank", "Foster", "555-0201", "2026-01-08"],
    ["2002", "gina@example.com", "Gina", "Garcia", "555-0202", "2026-01-19"],
]

MISSING_EMAIL_HEADERS = ["contact_id", "phone", "notes", "fname", "lname"]
MISSING_EMAIL_ROWS = [
    ["3001", "555-0301", "prefers evening calls", "Kara", "Kim"],
    ["3002", "555-0302", "do not text", "Liam", "Lopez"],
]


def proposal(*mappings: tuple[str, str]) -> MappingProposal:
    return MappingProposal(
        mappings=[
            FieldMapping(
                source_field=source, target_field=target, confidence=0.9, reason="test"
            )
            for source, target in mappings
        ],
        unmapped_required_fields=[],
        warnings=[],
        recommendation="ready_for_review",
    )


def test_exact_headers_pass():
    decision, blocked_reason, warnings = apply_gate(
        proposal(("external_id", "external_id"), ("email", "email")),
        EXACT_HEADERS,
        EXACT_ROWS,
    )
    assert (decision, blocked_reason, warnings) == ("proposal", None, [])


def test_common_aliases_pass():
    decision, blocked_reason, warnings = apply_gate(
        proposal(("contact_id", "external_id"), ("email_address", "email")),
        ALIAS_HEADERS,
        ALIAS_ROWS,
    )
    assert (decision, blocked_reason, warnings) == ("proposal", None, [])


def test_notes_to_email_blocked_by_samples():
    decision, blocked_reason, _ = apply_gate(
        proposal(("contact_id", "external_id"), ("notes", "email")),
        MISSING_EMAIL_HEADERS,
        MISSING_EMAIL_ROWS,
    )
    assert decision == "blocked"
    assert blocked_reason == NO_CREDIBLE_EMAIL


def test_missing_email_mapping_blocked():
    decision, blocked_reason, _ = apply_gate(
        proposal(("contact_id", "external_id")),
        MISSING_EMAIL_HEADERS,
        MISSING_EMAIL_ROWS,
    )
    assert decision == "blocked"
    assert blocked_reason == NO_CREDIBLE_EMAIL


def test_missing_external_id_mapping_blocked():
    decision, blocked_reason, _ = apply_gate(
        proposal(("email", "email")), EXACT_HEADERS, EXACT_ROWS
    )
    assert decision == "blocked"
    assert blocked_reason == "missing required mapping to external_id"


def test_nonexistent_source_column_blocked():
    decision, blocked_reason, _ = apply_gate(
        proposal(("external_id", "external_id"), ("emali", "email")),
        EXACT_HEADERS,
        EXACT_ROWS,
    )
    assert decision == "blocked"
    assert "does not exist" in blocked_reason


def test_duplicate_target_mappings_blocked():
    decision, blocked_reason, _ = apply_gate(
        proposal(
            ("external_id", "external_id"),
            ("email", "email"),
            ("first_name", "email"),
        ),
        EXACT_HEADERS,
        EXACT_ROWS,
    )
    assert decision == "blocked"
    assert "duplicate" in blocked_reason


def test_mixed_email_samples_warn_but_pass():
    rows = [
        ["1001", "alice@example.com", "Alice", "Anderson", "555-0101", "2026-01-05"],
        ["1002", "not-an-email", "Bob", "Baker", "555-0102", "2026-01-12"],
    ]
    decision, blocked_reason, warnings = apply_gate(
        proposal(("external_id", "external_id"), ("email", "email")),
        EXACT_HEADERS,
        rows,
    )
    assert (decision, blocked_reason) == ("proposal", None)
    assert len(warnings) == 1
    assert "data quality" in warnings[0]


def test_all_empty_email_samples_blocked():
    rows = [
        ["1001", "", "Alice", "Anderson", "555-0101", "2026-01-05"],
        ["1002", "", "Bob", "Baker", "555-0102", "2026-01-12"],
    ]
    decision, blocked_reason, _ = apply_gate(
        proposal(("external_id", "external_id"), ("email", "email")),
        EXACT_HEADERS,
        rows,
    )
    assert decision == "blocked"
    assert blocked_reason == NO_CREDIBLE_EMAIL
