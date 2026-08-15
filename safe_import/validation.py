import re

from .models import REQUIRED_TARGET_FIELDS, MappingProposal

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MAX_EMAIL_SAMPLES = 5

NO_CREDIBLE_EMAIL = "no credible email column"


def apply_gate(
    proposal: MappingProposal, headers: list[str], sample_rows: list[list[str]]
) -> tuple[str, str | None, list[str]]:
    """Deterministic decision: returns (decision, blocked_reason, warnings).

    The gate, not the model's `recommendation`, owns proposal vs blocked.
    """
    warnings: list[str] = []
    targets = [m.target_field for m in proposal.mappings]

    for mapping in proposal.mappings:
        if mapping.source_field not in headers:
            return (
                "blocked",
                f"mapped source column does not exist: {mapping.source_field!r}",
                warnings,
            )

    duplicates = sorted({t for t in targets if targets.count(t) > 1})
    if duplicates:
        return (
            "blocked",
            f"duplicate mappings to target field(s): {', '.join(duplicates)}",
            warnings,
        )

    for required in REQUIRED_TARGET_FIELDS:
        if required not in targets:
            if required == "email":
                return "blocked", NO_CREDIBLE_EMAIL, warnings
            return "blocked", f"missing required mapping to {required}", warnings

    email_source = next(
        m.source_field for m in proposal.mappings if m.target_field == "email"
    )
    column = headers.index(email_source)
    samples = [
        row[column].strip()
        for row in sample_rows
        if column < len(row) and row[column].strip()
    ][:MAX_EMAIL_SAMPLES]
    email_shaped = [s for s in samples if EMAIL_RE.match(s)]

    if not email_shaped:
        return "blocked", NO_CREDIBLE_EMAIL, warnings

    if len(email_shaped) < len(samples):
        warnings.append(
            "data quality: "
            f"{len(samples) - len(email_shaped)} of {len(samples)} "
            f"samples in {email_source!r} are not email-shaped"
        )
    return "proposal", None, warnings
