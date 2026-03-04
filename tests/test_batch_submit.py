"""Tests for scripts/batch_submit.py"""

import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from batch_submit import (
    get_batch_candidates,
    process_entry,
    run_batch,
    show_batch_report,
    validate_candidate,
)


def _make_staged_entry(
    entry_id="test-staged",
    score=7.0,
    track="job",
    status="staged",
    deadline_type="rolling",
    deadline_date=None,
    application_url="https://example.com/apply",
    portal="greenhouse",
    readiness=4,
    name="Test Staged Entry",
    organization="Test Org",
):
    return {
        "id": entry_id,
        "name": name,
        "track": track,
        "status": status,
        "fit": {"score": score, "identity_position": "independent-engineer"},
        "target": {
            "application_url": application_url,
            "portal": portal,
            "organization": organization,
            "location_class": "us-remote",
        },
        "deadline": {"type": deadline_type, "date": deadline_date},
        "submission": {"effort": "standard"},
    }


# --- get_batch_candidates ---


def test_get_batch_candidates_returns_list():
    """get_batch_candidates always returns a list."""
    result = get_batch_candidates()
    assert isinstance(result, list)


def test_get_batch_candidates_only_staged():
    """Only entries with status=staged are returned as candidates."""
    entries = [
        _make_staged_entry(entry_id="staged-1", status="staged"),
        _make_staged_entry(entry_id="drafting-1", status="drafting"),
        _make_staged_entry(entry_id="qualified-1", status="qualified"),
        _make_staged_entry(entry_id="staged-2", status="staged"),
    ]

    with patch("batch_submit.load_entries", return_value=entries):
        with patch("batch_submit.readiness_score", return_value=4):
            candidates = get_batch_candidates(min_readiness=0)

    candidate_ids = [c["id"] for c in candidates]
    assert "staged-1" in candidate_ids
    assert "staged-2" in candidate_ids
    assert "drafting-1" not in candidate_ids
    assert "qualified-1" not in candidate_ids


# --- validate_candidate ---


def test_validate_candidate_valid_entry():
    """A well-formed entry with application_url returns no errors."""
    entry = _make_staged_entry()

    errors, warnings = validate_candidate(entry)
    # The entry has an application_url set, so the "no application_url" error
    # should not appear. There may be other errors from missing profile/content,
    # but the URL error specifically should be absent.
    url_errors = [e for e in errors if "application_url" in e]
    assert len(url_errors) == 0


def test_validate_candidate_missing_url():
    """An entry without application_url produces an error."""
    entry = _make_staged_entry(application_url="")

    errors, warnings = validate_candidate(entry)
    url_errors = [e for e in errors if "application_url" in e]
    assert len(url_errors) > 0


def test_validate_candidate_returns_two_lists():
    """validate_candidate returns a (errors, warnings) tuple of two lists."""
    entry = _make_staged_entry()
    result = validate_candidate(entry)

    assert isinstance(result, tuple)
    assert len(result) == 2
    errors, warnings = result
    assert isinstance(errors, list)
    assert isinstance(warnings, list)


# --- process_entry ---


def test_process_entry_dry_run_ready():
    """Dry-run for a valid entry returns status=ready."""
    entry = _make_staged_entry()

    with patch("batch_submit.check_entry", return_value=([], ["minor warning"])):
        with patch("batch_submit.readiness_score", return_value=4):
            result = process_entry(entry, dry_run=True)

    assert result["status"] == "ready"
    assert result["id"] == "test-staged"
    assert result["readiness"] == 4


def test_process_entry_dry_run_blocked():
    """An entry with errors returns status=blocked."""
    entry = _make_staged_entry()

    with patch("batch_submit.check_entry", return_value=(["no application_url set"], [])):
        result = process_entry(entry, dry_run=True)

    assert result["status"] == "blocked"


def test_process_entry_blocked_has_errors():
    """A blocked result includes the error list from check_entry."""
    entry = _make_staged_entry()
    expected_errors = ["no application_url set", "material not found: resume.pdf"]

    with patch("batch_submit.check_entry", return_value=(expected_errors, [])):
        result = process_entry(entry, dry_run=True)

    assert result["status"] == "blocked"
    assert result["errors"] == expected_errors


def test_process_entry_includes_id():
    """Every result dict includes the entry id."""
    entry = _make_staged_entry(entry_id="my-unique-id")

    with patch("batch_submit.check_entry", return_value=([], [])):
        with patch("batch_submit.readiness_score", return_value=3):
            result = process_entry(entry, dry_run=True)

    assert "id" in result
    assert result["id"] == "my-unique-id"


def test_process_entry_execute_requires_review():
    """Execute mode blocks staged entries without governance review approval."""
    entry = _make_staged_entry()
    entry["status_meta"] = {}
    entry["_filepath"] = Path("/tmp/nonexistent.yaml")

    with patch("batch_submit.check_entry", return_value=([], [])):
        result = process_entry(entry, dry_run=False)

    assert result["status"] == "blocked"
    assert any("governance review" in e for e in result["errors"])


# --- show_batch_report ---


def test_show_batch_report_no_candidates(capsys):
    """Empty candidate list prints 'no candidates' message."""
    show_batch_report([])
    captured = capsys.readouterr()
    assert "no candidates" in captured.out.lower()


def test_show_batch_report_with_candidates(capsys):
    """Candidates are printed with name, org, score, and URL details."""
    entry = _make_staged_entry(
        entry_id="report-test",
        name="Report Test Entry",
        organization="Report Org",
        score=8.5,
        application_url="https://example.com/report",
    )
    entry["_readiness"] = 4

    show_batch_report([entry])
    captured = capsys.readouterr()

    assert "Report Test Entry" in captured.out
    assert "Report Org" in captured.out
    assert "8.5" in captured.out
    assert "https://example.com/report" in captured.out
    assert "BATCH CANDIDATES" in captured.out


# --- run_batch ---


def test_run_batch_dry_run(capsys):
    """Dry run returns results without calling record_submission."""
    entries = [
        _make_staged_entry(entry_id="batch-1", name="Batch Entry 1"),
        _make_staged_entry(entry_id="batch-2", name="Batch Entry 2"),
    ]

    with patch("batch_submit.get_batch_candidates", return_value=entries):
        with patch("batch_submit.check_entry", return_value=([], [])):
            with patch("batch_submit.readiness_score", return_value=4):
                with patch("batch_submit.record_submission") as mock_record:
                    results = run_batch(dry_run=True)

    # Should not have called record_submission in dry-run
    mock_record.assert_not_called()
    assert len(results) == 2
    assert all(r["status"] == "ready" for r in results)

    captured = capsys.readouterr()
    assert "DRY RUN" in captured.out


def test_run_batch_limit(capsys):
    """Limit parameter caps the number of entries processed."""
    entries = [
        _make_staged_entry(entry_id=f"limit-{i}", name=f"Limit Entry {i}")
        for i in range(10)
    ]

    with patch("batch_submit.get_batch_candidates", return_value=entries):
        with patch("batch_submit.check_entry", return_value=([], [])):
            with patch("batch_submit.readiness_score", return_value=4):
                results = run_batch(dry_run=True, limit=3)

    assert len(results) == 3


# --- Sorting ---


def test_batch_candidates_sorted_by_score():
    """Candidates are sorted by readiness desc, then fit score desc."""
    entries = [
        _make_staged_entry(entry_id="low", score=5.0),
        _make_staged_entry(entry_id="high", score=9.0),
        _make_staged_entry(entry_id="mid", score=7.0),
    ]

    # All same readiness, so sorting falls through to score
    with patch("batch_submit.load_entries", return_value=entries):
        with patch("batch_submit.readiness_score", return_value=4):
            candidates = get_batch_candidates(min_readiness=0)

    ids = [c["id"] for c in candidates]
    assert ids == ["high", "mid", "low"]
