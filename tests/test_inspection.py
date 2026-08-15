import pytest

from safe_import.inspection import inspect_import_context


def test_exact_headers_context():
    context = inspect_import_context("exact_headers")
    assert context["headers"][:2] == ["external_id", "email"]
    assert len(context["sample_rows"]) == 5
    assert context["target_schema"]["required"] == ["external_id", "email"]


@pytest.mark.parametrize(
    "fixture_id", ["nope", "../fixtures/exact_headers.csv", "/etc/passwd"]
)
def test_unknown_or_pathlike_id_rejected_before_file_access(fixture_id):
    with pytest.raises(KeyError):
        inspect_import_context(fixture_id)
