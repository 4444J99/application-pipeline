"""Tests for the system integrity audit script."""

import json
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from audit_system import (
    _has_source_nearby,
    audit_claims,
    audit_logic,
    audit_wiring,
    format_report,
    run_full_audit,
)


class TestClaimScanning:
    """Verify claim extraction and provenance classification."""

    def test_claim_scan_finds_percentages(self):
        """The claim scanner should find percentage patterns."""
        results = audit_claims()
        # The codebase has many percentage claims (62%, 53%, 8x, etc.)
        assert results["summary"]["sourced"] + results["summary"]["cited"] + results["summary"]["unsourced"] > 0, (
            "Should find at least some statistical claims in the codebase"
        )

    def test_has_source_nearby_url(self):
        """A claim near a URL should be classified as 'sourced'."""
        text = "Studies show 62% rejection rate https://example.com/study and other data"
        assert _has_source_nearby(text, text.index("62%")) == "sourced"

    def test_has_source_nearby_citation(self):
        """A claim near a report name should be classified as 'cited'."""
        text = "According to ResumeGenius, callback rate increased by 53% for tailored resumes"
        assert _has_source_nearby(text, text.index("53%")) == "cited"

    def test_has_source_nearby_none(self):
        """A claim with no nearby source should be 'unsourced'."""
        text = "x" * 400 + " the rate is 42% effective " + "x" * 400
        # The claim is surrounded by filler — no source within window
        pos = text.index("42%")
        assert _has_source_nearby(text, pos) == "unsourced"

    def test_claim_result_structure(self):
        """Each claim entry should have required fields."""
        results = audit_claims()
        if results["claims"]:
            claim = results["claims"][0]
            assert "file" in claim
            assert "line" in claim
            assert "claim" in claim
            assert "context" in claim
            assert "status" in claim
            assert claim["status"] in ("sourced", "cited", "unsourced")


class TestWiringIntegrity:
    """Live checks against actual codebase wiring."""

    def test_wiring_rubric_weights_match_code(self):
        """Rubric YAML weights should match score.py _DEFAULT_WEIGHTS."""
        results = audit_wiring()
        weight_check = next(
            (c for c in results["checks"] if c["id"] == "rubric_weights_match_code"), None
        )
        assert weight_check is not None, "rubric_weights_match_code check should exist"
        assert weight_check["passed"], f"Weights mismatch: {weight_check['detail']}"

    def test_wiring_dimensions_consistent(self):
        """DIMENSION_ORDER == rubric keys == VALID_DIMENSIONS."""
        results = audit_wiring()
        for check_id in ["dimensions_rubric_eq_pipeline", "dimensions_rubric_eq_validate"]:
            check = next((c for c in results["checks"] if c["id"] == check_id), None)
            assert check is not None, f"{check_id} check should exist"
            assert check["passed"], f"Dimension mismatch: {check['detail']}"

    def test_wiring_system_rubric_matches_diagnose(self):
        """System grading rubric dimensions should match diagnose.py lists."""
        results = audit_wiring()
        check = next(
            (c for c in results["checks"] if c["id"] == "system_rubric_matches_diagnose"), None
        )
        assert check is not None, "system_rubric_matches_diagnose check should exist"
        assert check["passed"], f"System rubric/diagnose mismatch: {check['detail']}"

    def test_wiring_high_prestige_ranges(self):
        """All HIGH_PRESTIGE org scores should be in 1-10."""
        results = audit_wiring()
        check = next(
            (c for c in results["checks"] if c["id"] == "high_prestige_ranges"), None
        )
        assert check is not None, "high_prestige_ranges check should exist"
        assert check["passed"], f"Out of range scores: {check['detail']}"

    def test_wiring_role_fit_tier_ranges(self):
        """All ROLE_FIT_TIERS dimension scores should be in 1-10."""
        results = audit_wiring()
        check = next(
            (c for c in results["checks"] if c["id"] == "role_fit_tier_ranges"), None
        )
        assert check is not None, "role_fit_tier_ranges check should exist"
        assert check["passed"], f"Tier score issues: {check['detail']}"


class TestLogicalConsistency:
    """Verify logical soundness of hardcoded values."""

    def test_logical_weight_sums(self):
        """Both weight dicts should sum to 1.0."""
        results = audit_logic()
        for check in results["checks"]:
            if check["id"].startswith("weight_sum_"):
                assert check["passed"], f"Weight sum failure: {check['detail']}"

    def test_logical_threshold_ordering(self):
        """tier1_cutoff > tier2_cutoff > tier3_cutoff."""
        results = audit_logic()
        check = next(
            (c for c in results["checks"] if c["id"] == "threshold_ordering"), None
        )
        assert check is not None, "threshold_ordering check should exist"
        assert check["passed"], f"Threshold ordering: {check['detail']}"

    def test_logical_score_ranges(self):
        """Score range min < max and both positive."""
        results = audit_logic()
        check = next(
            (c for c in results["checks"] if c["id"] == "score_range_valid"), None
        )
        assert check is not None, "score_range_valid check should exist"
        assert check["passed"], f"Score range: {check['detail']}"

    def test_logical_role_tier_ordering(self):
        """tier-1-strong should average higher than tier-4-poor."""
        results = audit_logic()
        check = next(
            (c for c in results["checks"] if c["id"] == "role_tier_ordering"), None
        )
        assert check is not None, "role_tier_ordering check should exist"
        assert check["passed"], f"Tier ordering: {check['detail']}"

    def test_logical_channel_multiplier_sanity(self):
        """Channel multipliers should be in sane range."""
        results = audit_logic()
        check = next(
            (c for c in results["checks"] if c["id"] == "channel_multiplier_sanity"), None
        )
        if check:
            assert check["passed"], f"Channel multiplier issue: {check['detail']}"

    def test_logical_followup_window_ordering(self):
        """Follow-up protocol windows should be sequential."""
        results = audit_logic()
        check = next(
            (c for c in results["checks"] if c["id"] == "followup_window_ordering"), None
        )
        if check:
            assert check["passed"], f"Follow-up window issue: {check['detail']}"


class TestAuditCLI:
    """Smoke tests for CLI interface."""

    def test_audit_cli_runs(self):
        """main() should complete without error."""
        from audit_system import main
        with patch("sys.argv", ["audit_system.py", "--json"]):
            # Capture stdout
            import io
            from contextlib import redirect_stdout
            f = io.StringIO()
            with redirect_stdout(f):
                main()
            output = f.getvalue()
            data = json.loads(output)
            assert "summary" in data
            assert "claims" in data
            assert "wiring" in data
            assert "logic" in data

    def test_audit_json_output_structure(self):
        """JSON output should have the expected top-level keys."""
        audit = run_full_audit()
        assert "claims" in audit
        assert "wiring" in audit
        assert "logic" in audit
        assert "summary" in audit
        s = audit["summary"]
        assert "claims_total" in s
        assert "wiring_passed" in s
        assert "wiring_total" in s
        assert "logic_passed" in s
        assert "logic_total" in s
        assert "all_wiring_ok" in s
        assert "all_logic_ok" in s

    def test_format_report_produces_output(self):
        """format_report() should produce a non-empty string."""
        audit = run_full_audit()
        report = format_report(audit)
        assert len(report) > 100
        assert "SYSTEM INTEGRITY AUDIT" in report
        assert "CLAIMS PROVENANCE" in report
        assert "WIRING INTEGRITY" in report
        assert "LOGICAL CONSISTENCY" in report

    def test_market_json_has_sources(self):
        """Every top-level section in market-intelligence JSON should have source/note."""
        results = audit_wiring()
        check = next(
            (c for c in results["checks"] if c["id"] == "market_json_sourced"), None
        )
        if check:
            assert check["passed"], f"Market JSON missing sources: {check['detail']}"
