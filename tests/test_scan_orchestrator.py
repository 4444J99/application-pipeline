"""Tests for scan_orchestrator.py — unified job scan across all APIs."""

import sys
from dataclasses import asdict
from pathlib import Path
from unittest.mock import patch

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from scan_orchestrator import ScanResult, _log_scan_result, scan_all, scan_ats, scan_free


class TestScanResult:
    def test_dataclass_fields(self):
        """ScanResult has all required fields."""
        r = ScanResult(
            new_entries=["test-entry"],
            duplicates_skipped=5,
            errors=[],
            sources_queried=3,
            total_fetched=10,
            total_qualified=2,
            scan_duration_seconds=1.5,
        )
        assert r.new_entries == ["test-entry"]
        assert r.total_fetched == 10

    def test_to_dict(self):
        """ScanResult serializes to dict."""
        r = ScanResult(
            new_entries=[],
            duplicates_skipped=0,
            errors=[],
            sources_queried=0,
            total_fetched=0,
            total_qualified=0,
            scan_duration_seconds=0.0,
        )
        d = asdict(r)
        assert "new_entries" in d
        assert "scan_duration_seconds" in d

    def test_default_factory(self):
        """ScanResult defaults to empty lists."""
        r = ScanResult()
        assert r.new_entries == []
        assert r.errors == []
        assert r.total_fetched == 0


class TestScanAll:
    def test_dry_run_returns_result(self):
        """Dry run scan returns ScanResult without writing files."""
        with patch("scan_orchestrator.scan_ats") as mock_ats, \
             patch("scan_orchestrator.scan_free") as mock_free, \
             patch("scan_orchestrator._dedup_and_filter", return_value=[]):
            mock_ats.return_value = ([], 0, [])
            mock_free.return_value = ([], 0, [])
            result = scan_all(dry_run=True)
            assert isinstance(result, ScanResult)
            assert result.new_entries == []

    def test_sources_filter_ats_only(self):
        """sources=['ats'] skips free APIs."""
        with patch("scan_orchestrator.scan_ats") as mock_ats, \
             patch("scan_orchestrator.scan_free") as mock_free, \
             patch("scan_orchestrator._dedup_and_filter", return_value=[]):
            mock_ats.return_value = ([], 0, [])
            mock_free.return_value = ([], 0, [])
            scan_all(dry_run=True, sources=["ats"])
            mock_ats.assert_called_once()
            mock_free.assert_not_called()

    def test_sources_filter_free_only(self):
        """sources=['free'] skips ATS APIs."""
        with patch("scan_orchestrator.scan_ats") as mock_ats, \
             patch("scan_orchestrator.scan_free") as mock_free, \
             patch("scan_orchestrator._dedup_and_filter", return_value=[]):
            mock_ats.return_value = ([], 0, [])
            mock_free.return_value = ([], 0, [])
            scan_all(dry_run=True, sources=["free"])
            mock_free.assert_called_once()
            mock_ats.assert_not_called()

    def test_max_entries_caps_output(self):
        """Scan respects max_entries limit."""
        fake_jobs = [
            {"title": f"Job {i}", "company": f"Co{i}", "url": f"https://example.com/{i}"}
            for i in range(20)
        ]
        with patch("scan_orchestrator.scan_ats") as mock_ats, \
             patch("scan_orchestrator.scan_free") as mock_free, \
             patch("scan_orchestrator._dedup_and_filter", return_value=fake_jobs), \
             patch("scan_orchestrator.pre_score", return_value=5.0), \
             patch("scan_orchestrator.create_pipeline_entry", side_effect=lambda j: (f"id-{j['title']}", {})):
            mock_ats.return_value = (fake_jobs, 3, [])
            mock_free.return_value = ([], 0, [])
            result = scan_all(dry_run=True, max_entries=5)
            assert result.total_qualified <= 5
            assert len(result.new_entries) <= 5

    def test_aggregates_errors(self):
        """Errors from both sources are aggregated."""
        with patch("scan_orchestrator.scan_ats") as mock_ats, \
             patch("scan_orchestrator.scan_free") as mock_free, \
             patch("scan_orchestrator._dedup_and_filter", return_value=[]):
            mock_ats.return_value = ([], 1, ["ats error"])
            mock_free.return_value = ([], 1, ["free error"])
            result = scan_all(dry_run=True)
            assert len(result.errors) == 2

    def test_counts_sources(self):
        """Total sources is sum of ats + free source counts."""
        with patch("scan_orchestrator.scan_ats") as mock_ats, \
             patch("scan_orchestrator.scan_free") as mock_free, \
             patch("scan_orchestrator._dedup_and_filter", return_value=[]):
            mock_ats.return_value = ([], 5, [])
            mock_free.return_value = ([], 2, [])
            result = scan_all(dry_run=True)
            assert result.sources_queried == 7


class TestScanATS:
    def test_returns_tuple(self):
        """scan_ats returns (jobs, sources_count, errors)."""
        with patch("scan_orchestrator.load_sources", return_value={"companies": []}):
            jobs, count, errors = scan_ats(fresh_only=True)
            assert isinstance(jobs, list)
            assert isinstance(count, int)
            assert isinstance(errors, list)

    def test_missing_config_returns_error(self):
        """Missing .job-sources.yaml returns error."""
        with patch("scan_orchestrator.load_sources", side_effect=FileNotFoundError):
            jobs, count, errors = scan_ats()
            assert len(errors) == 1
            assert "not found" in errors[0].lower()


class TestScanFree:
    def test_returns_tuple(self):
        """scan_free returns (jobs, sources_count, errors)."""
        with patch("scan_orchestrator.fetch_remotive", return_value=[]), \
             patch("scan_orchestrator.fetch_himalayas", return_value=[]), \
             patch("scan_orchestrator.time.sleep"):
            jobs, count, errors = scan_free()
            assert isinstance(jobs, list)
            assert isinstance(count, int)
            assert count == 2  # remotive + himalayas

    def test_handles_api_failure(self):
        """API failure captured in errors, not raised."""
        with patch("scan_orchestrator.fetch_remotive", side_effect=Exception("timeout")), \
             patch("scan_orchestrator.fetch_himalayas", return_value=[]), \
             patch("scan_orchestrator.time.sleep"):
            jobs, count, errors = scan_free()
            assert len(errors) == 1
            assert "remotive" in errors[0]


class TestScanHistory:
    def test_log_entry_format(self, tmp_path):
        """Scan history log has expected fields."""
        log_path = tmp_path / "scan-history.yaml"
        result = ScanResult(
            new_entries=["a", "b"],
            duplicates_skipped=5,
            errors=[],
            sources_queried=8,
            total_fetched=50,
            total_qualified=2,
            scan_duration_seconds=30.1,
        )
        _log_scan_result(result, log_path)
        entries = yaml.safe_load(log_path.read_text())
        assert len(entries) == 1
        assert entries[0]["sources_queried"] == 8
        assert entries[0]["new_entries"] == 2
        assert "date" in entries[0]

    def test_appends_to_existing(self, tmp_path):
        """Log appends to existing entries."""
        log_path = tmp_path / "scan-history.yaml"
        log_path.write_text(yaml.dump([{"date": "2026-03-13", "sources_queried": 1}]))
        result = ScanResult(sources_queried=5)
        _log_scan_result(result, log_path)
        entries = yaml.safe_load(log_path.read_text())
        assert len(entries) == 2
