"""Tests for scripts/smart_triage.py"""

import sys
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from smart_triage import (
    auto_archive,
    compute_decay_score,
    show_triage_report,
    triage_entries,
)


def _make_entry(
    entry_id="test-entry",
    score=7.0,
    track="job",
    effort="standard",
    posting_date=None,
    status="research",
    name="Test Entry",
    organization="Test Org",
    application_url="https://example.com",
):
    """Build a minimal pipeline entry dict for triage tests."""
    entry = {
        "id": entry_id,
        "name": name,
        "track": track,
        "status": status,
        "fit": {"score": score},
        "submission": {"effort_level": effort},
        "target": {"organization": organization, "application_url": application_url},
    }
    if posting_date:
        entry["timeline"] = {"posting_date": posting_date}
    return entry


# --- compute_decay_score tests ---


def test_compute_decay_score_base():
    """Entry with score 7.0, no date -> ~3.5 (7.0 * 0.5 neutral decay)."""
    entry = _make_entry(score=7.0)
    result = compute_decay_score(entry)
    assert abs(result - 3.5) < 0.01, f"Expected ~3.5, got {result}"


def test_compute_decay_score_fresh():
    """Entry posted today -> score * 1.0 decay."""
    today = date.today().isoformat()
    entry = _make_entry(score=8.0, posting_date=today)
    result = compute_decay_score(entry)
    # 8.0 * 1.0 + 0 (standard effort) + 0 (job track) = 8.0
    assert abs(result - 8.0) < 0.01, f"Expected ~8.0, got {result}"


def test_compute_decay_score_old():
    """Entry 180+ days old -> score * ~0 decay."""
    old_date = (date.today() - timedelta(days=200)).isoformat()
    entry = _make_entry(score=8.0, posting_date=old_date)
    result = compute_decay_score(entry)
    # 8.0 * max(0, 1 - 200/180) = 8.0 * 0 = 0.0
    assert result < 0.5, f"Expected near 0, got {result}"


def test_compute_decay_score_effort_quick():
    """Quick effort gets +0.5 bonus."""
    entry_quick = _make_entry(score=5.0, effort="quick")
    entry_standard = _make_entry(score=5.0, effort="standard")
    result_quick = compute_decay_score(entry_quick)
    result_standard = compute_decay_score(entry_standard)
    assert abs(result_quick - result_standard - 0.5) < 0.01, (
        f"Quick should be +0.5 over standard: quick={result_quick}, standard={result_standard}"
    )


def test_compute_decay_score_effort_intensive():
    """Intensive effort gets -0.5 penalty."""
    entry_intensive = _make_entry(score=5.0, effort="intensive")
    entry_standard = _make_entry(score=5.0, effort="standard")
    result_intensive = compute_decay_score(entry_intensive)
    result_standard = compute_decay_score(entry_standard)
    assert abs(result_standard - result_intensive - 0.5) < 0.01, (
        f"Intensive should be -0.5 from standard: intensive={result_intensive}, standard={result_standard}"
    )


def test_compute_decay_score_art_track_bonus():
    """Grant/residency/fellowship/prize tracks get +0.3 bonus."""
    for art_track in ("grant", "residency", "fellowship", "prize"):
        entry_art = _make_entry(score=5.0, track=art_track)
        entry_job = _make_entry(score=5.0, track="job")
        result_art = compute_decay_score(entry_art)
        result_job = compute_decay_score(entry_job)
        assert abs(result_art - result_job - 0.3) < 0.01, (
            f"Track '{art_track}' should be +0.3 over 'job': art={result_art}, job={result_job}"
        )


def test_compute_decay_score_clamps_to_zero():
    """Very old low-score entry doesn't go below 0."""
    old_date = (date.today() - timedelta(days=365)).isoformat()
    entry = _make_entry(score=0.5, posting_date=old_date, effort="intensive")
    result = compute_decay_score(entry)
    assert result >= 0.0, f"Score should not go below 0, got {result}"


def test_compute_decay_score_clamps_to_ten():
    """High score doesn't exceed 10."""
    today = date.today().isoformat()
    entry = _make_entry(score=10.0, posting_date=today, effort="quick", track="grant")
    result = compute_decay_score(entry)
    assert result <= 10.0, f"Score should not exceed 10, got {result}"
    # 10.0 * 1.0 + 0.5 + 0.3 = 10.8 -> clamped to 10.0
    assert result == 10.0, f"Expected exactly 10.0 (clamped), got {result}"


def test_compute_decay_score_half_life():
    """Entry at 90 days (half of 180) should have ~0.5 decay."""
    half_date = (date.today() - timedelta(days=90)).isoformat()
    entry = _make_entry(score=10.0, posting_date=half_date)
    result = compute_decay_score(entry)
    # 10.0 * 0.5 = 5.0
    assert abs(result - 5.0) < 0.01, f"Expected ~5.0, got {result}"


# --- triage_entries tests ---


def test_triage_entries_three_tiers():
    """Returns dict with top/hold/archive keys."""
    entries = [_make_entry(score=8.0), _make_entry(score=5.0), _make_entry(score=1.0)]
    result = triage_entries(entries)
    assert "top" in result
    assert "hold" in result
    assert "archive" in result
    assert "total" in result


def test_triage_entries_sorting():
    """Each tier is sorted by score descending."""
    entries = [
        _make_entry(entry_id="a", score=6.5),
        _make_entry(entry_id="b", score=9.0),
        _make_entry(entry_id="c", score=7.0),
    ]
    # All fresh entries (no date -> 0.5 decay), so scores are base*0.5
    # a: 3.25, b: 4.5, c: 3.5 -> all in hold tier
    result = triage_entries(entries)
    hold_scores = [item["decay_score"] for item in result["hold"]]
    assert hold_scores == sorted(hold_scores, reverse=True), (
        f"Hold tier not sorted descending: {hold_scores}"
    )


def test_triage_entries_total_count():
    """Total matches input length."""
    entries = [_make_entry(score=i) for i in range(5)]
    result = triage_entries(entries)
    assert result["total"] == 5


def test_triage_entries_high_scores_in_top():
    """Fresh entries with score >= ~6.0 appear in top tier."""
    today = date.today().isoformat()
    entry_high = _make_entry(score=8.0, posting_date=today, entry_id="high")
    entry_low = _make_entry(score=2.0, posting_date=today, entry_id="low")
    result = triage_entries([entry_high, entry_low])
    top_ids = [item["entry"]["id"] for item in result["top"]]
    assert "high" in top_ids, f"High-score entry should be in top: {top_ids}"
    assert "low" not in top_ids, f"Low-score entry should not be in top: {top_ids}"


def test_triage_entries_low_scores_in_archive():
    """Entries with decay score < 3.0 appear in archive tier."""
    old_date = (date.today() - timedelta(days=200)).isoformat()
    entry_dead = _make_entry(score=2.0, posting_date=old_date, entry_id="dead")
    result = triage_entries([entry_dead])
    archive_ids = [item["entry"]["id"] for item in result["archive"]]
    assert "dead" in archive_ids, f"Low-scoring old entry should be in archive: {archive_ids}"


def test_triage_entries_empty_input():
    """Empty list returns empty tiers with total=0."""
    result = triage_entries([])
    assert result["top"] == []
    assert result["hold"] == []
    assert result["archive"] == []
    assert result["total"] == 0


def test_triage_custom_threshold():
    """Custom threshold=5.0 changes the archive boundary."""
    today = date.today().isoformat()
    # Score 4.0: decay_score = 4.0 * 1.0 = 4.0 -> below 5.0 threshold
    entry = _make_entry(score=4.0, posting_date=today, entry_id="mid")
    result_default = triage_entries([entry], archive_threshold=3.0)
    result_custom = triage_entries([entry], archive_threshold=5.0)

    # With default threshold (3.0), score 4.0 is in hold
    default_archive_ids = [item["entry"]["id"] for item in result_default["archive"]]
    assert "mid" not in default_archive_ids, "Score 4.0 should not be archived at threshold 3.0"

    # With custom threshold (5.0), score 4.0 is in archive
    custom_archive_ids = [item["entry"]["id"] for item in result_custom["archive"]]
    assert "mid" in custom_archive_ids, "Score 4.0 should be archived at threshold 5.0"


# --- auto_archive tests ---


def test_auto_archive_dry_run(tmp_path):
    """Dry run returns list without actually moving files."""
    # Create a fake YAML file
    active_dir = tmp_path / "active"
    active_dir.mkdir()
    pool_dir = tmp_path / "research_pool"
    pool_dir.mkdir()

    fake_file = active_dir / "low-entry.yaml"
    fake_file.write_text("id: low-entry\nstatus: research\n")

    entry = _make_entry(entry_id="low-entry", score=1.0)
    entry["_filepath"] = fake_file

    with patch("smart_triage.PIPELINE_DIR_ACTIVE", active_dir), \
         patch("smart_triage.PIPELINE_DIR_RESEARCH_POOL", pool_dir):
        result = auto_archive([entry], threshold=5.0, dry_run=True)

    # File should still exist in active/
    assert fake_file.exists(), "Dry run should not move files"
    assert len(result) > 0, "Should return at least one summary"
    assert result[0]["action"] == "would_archive"


def test_auto_archive_executes_move(tmp_path):
    """When dry_run=False, files are moved to research_pool/."""
    active_dir = tmp_path / "active"
    active_dir.mkdir()
    pool_dir = tmp_path / "research_pool"
    pool_dir.mkdir()

    fake_file = active_dir / "low-entry.yaml"
    fake_file.write_text("id: low-entry\nstatus: research\n")

    entry = _make_entry(entry_id="low-entry", score=1.0)
    entry["_filepath"] = fake_file

    with patch("smart_triage.PIPELINE_DIR_ACTIVE", active_dir), \
         patch("smart_triage.PIPELINE_DIR_RESEARCH_POOL", pool_dir):
        result = auto_archive([entry], threshold=5.0, dry_run=False)

    assert not fake_file.exists(), "File should have been moved"
    assert (pool_dir / "low-entry.yaml").exists(), "File should be in research_pool/"
    assert result[0]["action"] == "archived"


# --- show_triage_report test ---


def test_show_triage_report_prints_output(capsys):
    """show_triage_report prints formatted output to stdout."""
    entries = [
        _make_entry(entry_id="top-1", score=9.0),
        _make_entry(entry_id="mid-1", score=5.0),
        _make_entry(entry_id="low-1", score=1.0),
    ]
    result = triage_entries(entries)
    result["_threshold"] = 3.0
    show_triage_report(result)
    captured = capsys.readouterr()
    assert "SMART TRIAGE REPORT" in captured.out
    assert "TOP OPPORTUNITIES" in captured.out
    assert "HOLD" in captured.out
    assert "ARCHIVE CANDIDATES" in captured.out
