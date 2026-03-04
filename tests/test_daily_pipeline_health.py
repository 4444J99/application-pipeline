"""Tests for scripts/daily_pipeline_health.py"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from daily_pipeline_health import StepResult, _email_report, _format_report


def test_format_report_summary():
    results = [
        StepResult("step-a", ["python", "a.py"], 0, "ok", ""),
        StepResult("step-b", ["python", "b.py"], 1, "", "boom"),
    ]
    report = _format_report(results, dry_run=True, email_status="skipped")
    assert "Summary: 1 ok | 1 failed" in report
    assert "## OK — step-a" in report
    assert "## FAIL — step-b" in report


def test_email_report_missing_host(monkeypatch):
    monkeypatch.delenv("PIPELINE_SMTP_HOST", raising=False)
    ok, detail = _email_report("body", ["x@example.com"], "subject")
    assert ok is False
    assert "PIPELINE_SMTP_HOST" in detail


def test_email_report_no_recipients():
    ok, detail = _email_report("body", [], "subject")
    assert ok is True
    assert "no recipients" in detail
