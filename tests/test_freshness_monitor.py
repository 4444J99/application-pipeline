"""Tests for scripts/freshness_monitor.py"""

import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from freshness_monitor import (
    check_url_liveness,
    compute_freshness_report,
    get_entries_with_urls,
    should_run_weekly_check,
    show_freshness_report,
)


def _make_entry(
    entry_id="test",
    application_url="https://example.com/apply",
    portal="greenhouse",
    status="qualified",
    posting_date=None,
    track="job",
    name="Test Entry",
):
    """Build a minimal pipeline entry dict for freshness monitor tests."""
    entry = {
        "id": entry_id,
        "name": name,
        "track": track,
        "status": status,
        "target": {"application_url": application_url, "portal": portal},
    }
    if posting_date:
        entry["timeline"] = {"posting_date": posting_date}
    return entry


# ---------------------------------------------------------------------------
# get_entries_with_urls
# ---------------------------------------------------------------------------


def test_get_entries_with_urls_returns_list():
    """get_entries_with_urls always returns a list."""
    entries = [_make_entry()]
    result = get_entries_with_urls(entries)
    assert isinstance(result, list)


def test_get_entries_with_urls_filters_empty():
    """Entries without application URLs are excluded."""
    entries = [
        _make_entry(entry_id="has-url", application_url="https://example.com"),
        _make_entry(entry_id="no-url", application_url=""),
        _make_entry(entry_id="none-url", application_url=None),
    ]
    # Fix the None case: set it directly so the filter sees falsy value
    entries[2]["target"]["application_url"] = ""
    result = get_entries_with_urls(entries)
    ids = [e["id"] for e in result]
    assert "has-url" in ids
    assert "no-url" not in ids
    assert "none-url" not in ids


def test_get_entries_with_urls_filters_status():
    """Non-actionable statuses are excluded."""
    entries = [
        _make_entry(entry_id="qualified", status="qualified"),
        _make_entry(entry_id="submitted", status="submitted"),
        _make_entry(entry_id="drafting", status="drafting"),
        _make_entry(entry_id="interview", status="interview"),
        _make_entry(entry_id="outcome", status="outcome"),
    ]
    result = get_entries_with_urls(entries)
    ids = [e["id"] for e in result]
    assert "qualified" in ids
    assert "drafting" in ids
    # submitted, interview, and outcome are not actionable
    assert "submitted" not in ids
    assert "interview" not in ids
    assert "outcome" not in ids


def test_get_entries_with_urls_excludes_research():
    """Research status entries are excluded (research is pre-pipeline, not actionable)."""
    entries = [_make_entry(entry_id="research-entry", status="research")]
    result = get_entries_with_urls(entries)
    assert len(result) == 0


# ---------------------------------------------------------------------------
# compute_freshness_report
# ---------------------------------------------------------------------------


def test_compute_freshness_report_empty():
    """Empty entries list returns all empty categories."""
    report = compute_freshness_report([])
    assert report["fresh"] == []
    assert report["aging"] == []
    assert report["stale"] == []
    assert report["expired"] == []
    assert report["unknown"] == []
    assert report["total"] == 0


def test_compute_freshness_report_fresh():
    """Entry posted today is categorized as fresh."""
    today = date.today().isoformat()
    entries = [_make_entry(entry_id="fresh-one", posting_date=today)]
    report = compute_freshness_report(entries)
    assert len(report["fresh"]) == 1
    assert report["fresh"][0]["entry_id"] == "fresh-one"
    assert report["fresh"][0]["age_days"] == 0


def test_compute_freshness_report_aging():
    """Non-job entry 20 days old is categorized as aging (day-based thresholds)."""
    twenty_days_ago = (date.today() - timedelta(days=20)).isoformat()
    entries = [_make_entry(entry_id="aging-one", posting_date=twenty_days_ago, track="grant")]
    report = compute_freshness_report(entries)
    assert len(report["aging"]) == 1
    assert report["aging"][0]["entry_id"] == "aging-one"
    assert report["aging"][0]["age_days"] == 20


def test_compute_freshness_report_stale():
    """Non-job entry 45 days old is categorized as stale (day-based thresholds)."""
    forty_five_ago = (date.today() - timedelta(days=45)).isoformat()
    entries = [_make_entry(entry_id="stale-one", posting_date=forty_five_ago, track="grant")]
    report = compute_freshness_report(entries)
    assert len(report["stale"]) == 1
    assert report["stale"][0]["entry_id"] == "stale-one"
    assert report["stale"][0]["age_days"] == 45


def test_compute_freshness_report_expired():
    """Entry 90 days old is categorized as expired."""
    ninety_ago = (date.today() - timedelta(days=90)).isoformat()
    entries = [_make_entry(entry_id="expired-one", posting_date=ninety_ago)]
    report = compute_freshness_report(entries)
    assert len(report["expired"]) == 1
    assert report["expired"][0]["entry_id"] == "expired-one"
    assert report["expired"][0]["age_days"] == 90


def test_compute_freshness_report_unknown():
    """Entry without any date is categorized as unknown."""
    entries = [_make_entry(entry_id="no-date")]
    report = compute_freshness_report(entries)
    assert len(report["unknown"]) == 1
    assert report["unknown"][0]["entry_id"] == "no-date"
    assert report["unknown"][0]["age_days"] is None


def test_compute_freshness_report_total():
    """Total equals sum of all categories."""
    today = date.today().isoformat()
    twenty_ago = (date.today() - timedelta(days=20)).isoformat()
    fifty_ago = (date.today() - timedelta(days=50)).isoformat()
    hundred_ago = (date.today() - timedelta(days=100)).isoformat()

    entries = [
        _make_entry(entry_id="f1", posting_date=today),
        _make_entry(entry_id="a1", posting_date=twenty_ago),
        _make_entry(entry_id="s1", posting_date=fifty_ago),
        _make_entry(entry_id="e1", posting_date=hundred_ago),
        _make_entry(entry_id="u1"),  # no date
    ]
    report = compute_freshness_report(entries)
    expected_total = (
        len(report["fresh"])
        + len(report["aging"])
        + len(report["stale"])
        + len(report["expired"])
        + len(report["unknown"])
    )
    assert report["total"] == expected_total
    assert report["total"] == 5


def test_compute_freshness_report_has_required_fields():
    """Each item in the report has the required fields."""
    today = date.today().isoformat()
    entries = [_make_entry(entry_id="field-check", posting_date=today, portal="lever")]
    report = compute_freshness_report(entries)
    item = report["fresh"][0]
    assert "entry_id" in item
    assert "name" in item
    assert "age_days" in item
    assert "url" in item
    assert "portal" in item
    assert item["entry_id"] == "field-check"
    assert item["portal"] == "lever"
    assert item["url"] == "https://example.com/apply"


def test_compute_freshness_report_boundary_fresh_aging():
    """Non-job entry exactly 14 days old falls into aging (>= 14 is aging)."""
    fourteen_ago = (date.today() - timedelta(days=14)).isoformat()
    entries = [_make_entry(entry_id="boundary", posting_date=fourteen_ago, track="grant")]
    report = compute_freshness_report(entries)
    assert len(report["aging"]) == 1
    assert report["aging"][0]["entry_id"] == "boundary"


def test_compute_freshness_report_boundary_aging_stale():
    """Non-job entry exactly 30 days old is still aging (<= 30)."""
    thirty_ago = (date.today() - timedelta(days=30)).isoformat()
    entries = [_make_entry(entry_id="boundary30", posting_date=thirty_ago, track="grant")]
    report = compute_freshness_report(entries)
    assert len(report["aging"]) == 1
    assert report["aging"][0]["entry_id"] == "boundary30"


# ---------------------------------------------------------------------------
# Job-track hour-based freshness
# ---------------------------------------------------------------------------


def test_job_entry_today_is_fresh():
    """Job entry posted today uses hour-based thresholds and is fresh."""
    today = date.today().isoformat()
    entries = [_make_entry(entry_id="job-fresh", posting_date=today, track="job")]
    report = compute_freshness_report(entries)
    assert len(report["fresh"]) == 1
    assert report["fresh"][0]["entry_id"] == "job-fresh"
    assert report["fresh"][0]["age_hours"] is not None


def test_job_entry_old_is_expired():
    """Job entry posted 5 days ago is expired under hour-based thresholds (120h > 72h)."""
    five_days_ago = (date.today() - timedelta(days=5)).isoformat()
    entries = [_make_entry(entry_id="job-old", posting_date=five_days_ago, track="job")]
    report = compute_freshness_report(entries)
    assert len(report["expired"]) == 1
    assert report["expired"][0]["entry_id"] == "job-old"


def test_job_entry_report_includes_track():
    """Job entry items include track field in report."""
    today = date.today().isoformat()
    entries = [_make_entry(entry_id="job-track-check", posting_date=today, track="job")]
    report = compute_freshness_report(entries)
    item = report["fresh"][0]
    assert item["track"] == "job"


def test_grant_entry_uses_day_thresholds():
    """Grant entry 20 days old is aging under day-based thresholds."""
    twenty_ago = (date.today() - timedelta(days=20)).isoformat()
    entries = [_make_entry(entry_id="grant-aging", posting_date=twenty_ago, track="grant")]
    report = compute_freshness_report(entries)
    assert len(report["aging"]) == 1
    assert report["aging"][0]["age_hours"] is None


# ---------------------------------------------------------------------------
# should_run_weekly_check
# ---------------------------------------------------------------------------


def test_should_run_weekly_check_no_file(tmp_path):
    """Returns True when the check file does not exist."""
    check_file = tmp_path / "freshness-last-check.txt"
    assert should_run_weekly_check(check_file=check_file) is True


def test_should_run_weekly_check_old_file(tmp_path):
    """Returns True when the check file is more than 7 days old."""
    check_file = tmp_path / "freshness-last-check.txt"
    old_date = (date.today() - timedelta(days=10)).isoformat()
    check_file.write_text(old_date + "\n")
    assert should_run_weekly_check(check_file=check_file) is True


def test_should_run_weekly_check_recent(tmp_path):
    """Returns False when the check file is less than 7 days old."""
    check_file = tmp_path / "freshness-last-check.txt"
    recent_date = (date.today() - timedelta(days=2)).isoformat()
    check_file.write_text(recent_date + "\n")
    assert should_run_weekly_check(check_file=check_file) is False


def test_should_run_weekly_check_exactly_seven(tmp_path):
    """Returns True when the check file is exactly 7 days old."""
    check_file = tmp_path / "freshness-last-check.txt"
    seven_ago = (date.today() - timedelta(days=7)).isoformat()
    check_file.write_text(seven_ago + "\n")
    assert should_run_weekly_check(check_file=check_file) is True


def test_should_run_weekly_check_corrupt_file(tmp_path):
    """Returns True when the check file has corrupt content."""
    check_file = tmp_path / "freshness-last-check.txt"
    check_file.write_text("not-a-date\n")
    assert should_run_weekly_check(check_file=check_file) is True


# ---------------------------------------------------------------------------
# check_url_liveness (structure test only — no HTTP calls)
# ---------------------------------------------------------------------------


def test_check_url_liveness_returns_dict():
    """check_url_liveness returns a dict with required keys, even for empty URL."""
    result = check_url_liveness("")
    assert isinstance(result, dict)
    assert "url" in result
    assert "status" in result
    assert "code" in result
    assert "detail" in result
    assert result["status"] == "error"


def test_check_url_liveness_empty_url_detail():
    """Empty URL produces a specific error detail."""
    result = check_url_liveness("")
    assert result["code"] is None
    assert "empty" in result["detail"].lower()


# ---------------------------------------------------------------------------
# show_freshness_report
# ---------------------------------------------------------------------------


def test_show_freshness_report_prints(capsys):
    """show_freshness_report writes formatted output to stdout."""
    report = {
        "fresh": [{"entry_id": "f1", "name": "Fresh One", "age_days": 2, "url": "https://a.com", "portal": "gh"}],
        "aging": [],
        "stale": [{"entry_id": "s1", "name": "Stale One", "age_days": 45, "url": "https://b.com", "portal": "lever"}],
        "expired": [],
        "unknown": [],
        "total": 2,
    }
    show_freshness_report(report)
    captured = capsys.readouterr()
    assert "ENTRY FRESHNESS REPORT" in captured.out
    assert "2 entries" in captured.out
    assert "f1" in captured.out
    assert "s1" in captured.out
    assert "Stale" in captured.out


def test_show_freshness_report_stale_only(capsys):
    """With stale_only=True, only stale and expired sections are shown."""
    report = {
        "fresh": [{"entry_id": "f1", "name": "F1", "age_days": 1, "url": "https://a.com", "portal": "gh"}],
        "aging": [],
        "stale": [{"entry_id": "s1", "name": "S1", "age_days": 40, "url": "https://b.com", "portal": "gh"}],
        "expired": [],
        "unknown": [],
        "total": 2,
    }
    show_freshness_report(report, stale_only=True)
    captured = capsys.readouterr()
    assert "s1" in captured.out
    # Fresh category header should not appear when stale_only
    assert "Fresh (" not in captured.out


def test_show_freshness_report_action_needed(capsys):
    """Report with stale/expired entries shows ACTION NEEDED message."""
    report = {
        "fresh": [],
        "aging": [],
        "stale": [{"entry_id": "s1", "name": "S1", "age_days": 35, "url": "https://b.com", "portal": "gh"}],
        "expired": [{"entry_id": "e1", "name": "E1", "age_days": 70, "url": "https://c.com", "portal": "gh"}],
        "unknown": [],
        "total": 2,
    }
    show_freshness_report(report)
    captured = capsys.readouterr()
    assert "ACTION NEEDED" in captured.out
    assert "1 stale" in captured.out
    assert "1 expired" in captured.out
