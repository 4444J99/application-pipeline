import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import yaml


class TestResolveHypotheses:
    """Test hypothesis auto-resolution."""

    def test_resolves_cold_app_hypothesis(self, tmp_path):
        hyp_path = tmp_path / "hypotheses.yaml"
        hyp_data = {"hypotheses": [
            {"entry_id": "test-1", "date": "2026-03-02", "outcome": None,
             "category": "timing", "hypothesis": "Tier 1 cold app; referral pathway not established"},
        ]}
        with open(hyp_path, "w") as f:
            yaml.dump(hyp_data, f)

        from resolve_hypotheses import resolve_cold_app_hypotheses
        resolved, unresolved = resolve_cold_app_hypotheses(hyp_path, dry_run=True)
        assert len(resolved) == 1
        assert resolved[0]["outcome"] == "confirmed"
        assert "historical" in resolved[0].get("resolution_evidence", "")

    def test_skips_already_resolved(self, tmp_path):
        hyp_path = tmp_path / "hypotheses.yaml"
        hyp_data = {"hypotheses": [
            {"entry_id": "test-1", "date": "2026-03-02", "outcome": "confirmed",
             "category": "timing", "hypothesis": "Already resolved"},
        ]}
        with open(hyp_path, "w") as f:
            yaml.dump(hyp_data, f)

        from resolve_hypotheses import resolve_cold_app_hypotheses
        resolved, unresolved = resolve_cold_app_hypotheses(hyp_path, dry_run=True)
        assert len(resolved) == 0

    def test_preserves_non_cold_app_hypotheses(self, tmp_path):
        hyp_path = tmp_path / "hypotheses.yaml"
        hyp_data = {"hypotheses": [
            {"entry_id": "test-1", "date": "2026-03-02", "outcome": None,
             "category": "content", "hypothesis": "Resume too generic for this role"},
        ]}
        with open(hyp_path, "w") as f:
            yaml.dump(hyp_data, f)

        from resolve_hypotheses import resolve_cold_app_hypotheses
        resolved, unresolved = resolve_cold_app_hypotheses(hyp_path, dry_run=True)
        assert len(resolved) == 0
        assert len(unresolved) == 1


class TestWriteResolved:
    """Test writing resolved hypotheses back to file."""

    def test_write_updates_file(self, tmp_path):
        hyp_path = tmp_path / "hypotheses.yaml"
        hyp_data = {"hypotheses": [
            {"entry_id": "test-1", "date": "2026-03-02", "outcome": None,
             "category": "timing",
             "hypothesis": "Tier 1 cold app; referral pathway not established"},
            {"entry_id": "test-2", "date": "2026-03-02", "outcome": None,
             "category": "content", "hypothesis": "Resume too generic"},
        ]}
        with open(hyp_path, "w") as f:
            yaml.dump(hyp_data, f)

        from resolve_hypotheses import resolve_cold_app_hypotheses
        resolve_cold_app_hypotheses(hyp_path, dry_run=False)

        with open(hyp_path) as f:
            updated = yaml.safe_load(f)
        hyps = updated["hypotheses"]
        assert hyps[0]["outcome"] == "confirmed"
        assert hyps[1]["outcome"] is None  # non-cold-app unchanged
