import pytest

from safe_import import inspection
from safe_import.inspection import FixtureDataError, inspect_import_context


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


def test_missing_fixture_file_fails_visibly(monkeypatch, tmp_path):
    monkeypatch.setitem(
        inspection.FIXTURE_FILES, "exact_headers", tmp_path / "gone.csv"
    )
    with pytest.raises(FixtureDataError, match="missing or unreadable"):
        inspect_import_context("exact_headers")


def test_empty_fixture_file_fails_visibly(monkeypatch, tmp_path):
    empty = tmp_path / "empty.csv"
    empty.write_text("")
    monkeypatch.setitem(inspection.FIXTURE_FILES, "exact_headers", empty)
    with pytest.raises(FixtureDataError, match="empty"):
        inspect_import_context("exact_headers")
