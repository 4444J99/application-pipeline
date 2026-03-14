# tests/test_phase_analytics.py
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import yaml


class TestPhaseClassification:
    """Test Phase 1 vs Phase 2 classification."""

    def test_linkedin_is_phase1(self):
        from phase_analytics import classify_phase
        assert classify_phase("linkedin-easy-apply", "2024-11-20") == 1

    def test_applyall_is_phase1(self):
        from phase_analytics import classify_phase
        assert classify_phase("applyall-blast", "2025-03-15") == 1

    def test_direct_2026_is_phase2(self):
        from phase_analytics import classify_phase
        assert classify_phase("direct", "2026-02-24") == 2


class TestVelocityCurve:
    """Test monthly velocity computation."""

    def test_computes_monthly_counts(self):
        from phase_analytics import compute_monthly_velocity
        records = [
            {"applied_date": "2024-11-01", "channel": "linkedin-easy-apply"},
            {"applied_date": "2024-11-15", "channel": "linkedin-easy-apply"},
            {"applied_date": "2024-12-01", "channel": "linkedin-easy-apply"},
        ]
        velocity = compute_monthly_velocity(records)
        assert velocity["2024-11"] == 2
        assert velocity["2024-12"] == 1


class TestPhaseComparison:
    """Test Phase 1 vs Phase 2 aggregate comparison."""

    def test_comparison_structure(self, tmp_path, monkeypatch):
        import phase_analytics
        # Mock historical data
        hist_path = tmp_path / "historical-outcomes.yaml"
        with open(hist_path, "w") as f:
            yaml.dump({"entries": [
                {"company": "A", "title": "Dev", "applied_date": "2024-11-20",
                 "channel": "linkedin-easy-apply", "portal": "linkedin",
                 "outcome": "expired", "outcome_reason": "no_response"},
            ]}, f)
        monkeypatch.setattr(phase_analytics, "HISTORICAL_PATH", hist_path)
        # Mock conversion log
        conv_path = tmp_path / "conversion-log.yaml"
        with open(conv_path, "w") as f:
            yaml.dump({"entries": [
                {"id": "test-1", "submitted": "2026-02-24", "channel": "direct",
                 "portal": "greenhouse", "outcome": "rejected"},
            ]}, f)
        monkeypatch.setattr(phase_analytics, "CONVERSION_LOG_PATH", conv_path)

        comparison = phase_analytics.compute_phase_comparison()
        assert "phase_1" in comparison
        assert "phase_2" in comparison
        assert comparison["phase_1"]["total"] == 1
        assert comparison["phase_2"]["total"] == 1
