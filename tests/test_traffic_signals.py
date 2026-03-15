"""Tests for scripts/traffic_signals.py."""

from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import traffic_signals as ts


def _make_traffic(repo="test/repo", views=0, uniques=0, clones_u=0, referrers=None, daily=None):
    return ts.RepoTraffic(
        repo=repo,
        total_views=views,
        total_uniques=uniques,
        daily=daily or [],
        clones_total=clones_u * 2,
        clones_uniques=clones_u,
        referrers=referrers or [],
    )


def _make_entry(entry_id="test-entry", org="TestCo", submitted_date=None):
    return {
        "id": entry_id,
        "target": {"organization": org},
        "status": "submitted",
        "timeline": {"submitted": submitted_date or date.today().isoformat()},
    }


# --- Referrer signal detection ---


def test_referrer_match_known_company():
    traffic = [_make_traffic(referrers=[{"referrer": "anthropic.com", "count": 3, "uniques": 2}])]
    entries = [_make_entry(entry_id="anthropic-swe", org="Anthropic")]
    signals = ts.detect_referrer_signals(traffic, entries)
    assert len(signals) == 1
    assert signals[0].signal_type == "submission_correlated"
    assert signals[0].org == "Anthropic"
    assert signals[0].entry_id == "anthropic-swe"


def test_referrer_match_no_entry():
    traffic = [_make_traffic(referrers=[{"referrer": "stripe.com", "count": 2, "uniques": 1}])]
    entries = []  # No Stripe entry
    signals = ts.detect_referrer_signals(traffic, entries)
    assert len(signals) == 1
    assert signals[0].signal_type == "organic_interest"
    assert signals[0].org == "Stripe"
    assert signals[0].entry_id == ""


def test_referrer_linkedin():
    traffic = [_make_traffic(referrers=[{"referrer": "linkedin.com", "count": 3, "uniques": 2}])]
    signals = ts.detect_referrer_signals(traffic, [])
    assert len(signals) == 1
    assert signals[0].signal_type == "organic_interest"
    assert "LinkedIn" in signals[0].description


def test_referrer_ats_low_count():
    traffic = [_make_traffic(referrers=[{"referrer": "greenhouse.io", "count": 1, "uniques": 1}])]
    signals = ts.detect_referrer_signals(traffic, [])
    assert len(signals) == 0  # Below threshold (count < 2)


def test_referrer_ats_above_threshold():
    traffic = [_make_traffic(referrers=[{"referrer": "greenhouse.io", "count": 5, "uniques": 3}])]
    signals = ts.detect_referrer_signals(traffic, [])
    assert len(signals) == 1
    assert signals[0].signal_type == "organic_interest"


def test_referrer_unknown_domain():
    traffic = [_make_traffic(referrers=[{"referrer": "randomsite.org", "count": 10, "uniques": 5}])]
    signals = ts.detect_referrer_signals(traffic, [])
    assert len(signals) == 0  # Unknown domain, no match


def test_referrer_empty():
    signals = ts.detect_referrer_signals([], [])
    assert signals == []


# --- Spike detection ---


def test_spike_correlated_with_submission():
    sub_date = (date.today() - timedelta(days=3)).isoformat()
    spike_date = (date.today() - timedelta(days=1)).isoformat()
    traffic = [_make_traffic(daily=[
        ts.TrafficDay(date=spike_date, views=20, uniques=8),
    ])]
    entries = [_make_entry(submitted_date=sub_date)]
    signals = ts.detect_spike_signals(traffic, entries)
    assert len(signals) == 1
    assert signals[0].signal_type == "submission_correlated"


def test_spike_not_correlated():
    sub_date = (date.today() - timedelta(days=20)).isoformat()  # Too old
    spike_date = (date.today() - timedelta(days=1)).isoformat()
    traffic = [_make_traffic(daily=[
        ts.TrafficDay(date=spike_date, views=20, uniques=8),
    ])]
    entries = [_make_entry(submitted_date=sub_date)]
    signals = ts.detect_spike_signals(traffic, entries)
    # Not correlated (>7d gap) — but still a spike if big enough
    assert all(s.signal_type != "submission_correlated" for s in signals)


def test_spike_below_threshold():
    traffic = [_make_traffic(daily=[
        ts.TrafficDay(date=date.today().isoformat(), views=3, uniques=2),
    ])]
    signals = ts.detect_spike_signals(traffic, [])
    assert len(signals) == 0


# --- Clone detection ---


def test_clone_spike(monkeypatch):
    monkeypatch.setattr(ts, "_estimate_ci_clones", lambda repo: 0)
    traffic = [_make_traffic(clones_u=25)]
    signals = ts.detect_clone_signals(traffic)
    assert len(signals) == 1
    assert signals[0].signal_type == "clone_spike"
    assert signals[0].strength == "high"


def test_clone_moderate(monkeypatch):
    monkeypatch.setattr(ts, "_estimate_ci_clones", lambda repo: 0)
    traffic = [_make_traffic(clones_u=5)]
    signals = ts.detect_clone_signals(traffic)
    assert len(signals) == 1
    assert signals[0].strength == "medium"


def test_clone_below_threshold(monkeypatch):
    monkeypatch.setattr(ts, "_estimate_ci_clones", lambda repo: 0)
    traffic = [_make_traffic(clones_u=1)]
    signals = ts.detect_clone_signals(traffic)
    assert len(signals) == 0


def test_clone_ci_subtraction(monkeypatch):
    """CI clones should be subtracted — 50 raw but 40 are CI = 10 net."""
    monkeypatch.setattr(ts, "_estimate_ci_clones", lambda repo: 40)
    traffic = [_make_traffic(clones_u=50)]
    signals = ts.detect_clone_signals(traffic)
    assert len(signals) == 1
    assert signals[0].metric_value == 10  # 50 - 40


def test_clone_all_ci(monkeypatch):
    """If all clones are CI, no signal."""
    monkeypatch.setattr(ts, "_estimate_ci_clones", lambda repo: 100)
    traffic = [_make_traffic(clones_u=50)]
    signals = ts.detect_clone_signals(traffic)
    assert len(signals) == 0


# --- Helper functions ---


def test_match_referrer_to_org():
    assert ts._match_referrer_to_org("anthropic.com") == "Anthropic"
    assert ts._match_referrer_to_org("www.stripe.com/careers") == "Stripe"
    assert ts._match_referrer_to_org("randomsite.org") == ""
    assert ts._match_referrer_to_org("greenhouse.io") == "_ATS_"


def test_find_entry_for_org():
    entries = [_make_entry(entry_id="a", org="Anthropic"), _make_entry(entry_id="b", org="Stripe")]
    assert ts._find_entry_for_org("Anthropic", entries) == "a"
    assert ts._find_entry_for_org("Stripe", entries) == "b"
    assert ts._find_entry_for_org("Google", entries) == ""


# --- Signal saving ---


def test_save_signals(tmp_path, monkeypatch):
    monkeypatch.setattr(ts, "SIGNALS_PATH", tmp_path / "traffic-signals.yaml")
    monkeypatch.setattr(ts, "SIGNALS_DIR", tmp_path)

    signals = [ts.TrafficSignal(
        signal_type="test", repo="test/repo", date=date.today().isoformat(),
        description="test signal", org="TestCo", entry_id="test-1",
        strength="high", referrer="test.com", metric_value=10,
    )]
    ts.save_signals(signals)

    saved = yaml.safe_load((tmp_path / "traffic-signals.yaml").read_text())
    assert len(saved) == 1
    assert saved[0]["signal_type"] == "test"


def test_save_signals_appends(tmp_path, monkeypatch):
    sig_path = tmp_path / "traffic-signals.yaml"
    monkeypatch.setattr(ts, "SIGNALS_PATH", sig_path)
    monkeypatch.setattr(ts, "SIGNALS_DIR", tmp_path)

    existing = [{"signal_type": "old", "date": date.today().isoformat()}]
    sig_path.write_text(yaml.dump(existing))

    signals = [ts.TrafficSignal(
        signal_type="new", repo="r", date=date.today().isoformat(),
        description="d", org="", entry_id="", strength="low", referrer="", metric_value=1,
    )]
    ts.save_signals(signals)

    saved = yaml.safe_load(sig_path.read_text())
    assert len(saved) == 2


# --- Report formatting ---


def test_format_report_no_signals():
    report = ts.format_report([], [_make_traffic()])
    assert "No actionable signals" in report


def test_format_report_with_signals():
    signals = [ts.TrafficSignal(
        signal_type="submission_correlated", repo="test/repo", date="2026-03-15",
        description="Anthropic visited", org="Anthropic", entry_id="anthropic-swe",
        strength="high", referrer="anthropic.com", metric_value=5,
    )]
    report = ts.format_report(signals, [_make_traffic()])
    assert "SUBMISSION CORRELATED" in report
    assert "Anthropic visited" in report
