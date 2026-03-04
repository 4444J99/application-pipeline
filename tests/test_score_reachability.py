"""Direct tests for scripts/score_reachability.py."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import score_reachability


def test_analyze_reachability_returns_levels():
    result = score_reachability.analyze_reachability(
        {"id": "e1", "track": "job"},
        [],
        threshold=9.0,
        compute_dimensions=lambda _entry, _all: {"network_proximity": 1},
        compute_composite=lambda dims, _track: float(dims["network_proximity"]),
    )
    assert result["entry_id"] == "e1"
    assert result["current_network"] == 1
    assert any(s["level"] == "internal" for s in result["scenarios"])


def test_run_reachable_no_actionable(capsys):
    score_reachability.run_reachable(
        threshold=9.0,
        load_entries_raw=lambda **_kwargs: [{"status": "deferred"}],
        all_pipeline_dirs_with_pool=[],
        analyze_reachability_fn=lambda *_args, **_kwargs: {},
    )
    captured = capsys.readouterr()
    assert "No actionable entries found." in captured.out


def test_run_triage_staged_no_entries(capsys):
    score_reachability.run_triage_staged(
        dry_run=True,
        yes=False,
        load_entries_raw=lambda **_kwargs: [],
        all_pipeline_dirs_with_pool=[],
        compute_dimensions=lambda _entry, _all: {},
        compute_composite=lambda _dims, _track: 0.0,
        analyze_reachability_fn=lambda *_args, **_kwargs: {},
        update_yaml_field=lambda content, _key, _value: content,
        update_last_touched=lambda content: content,
        atomic_write=lambda _path, _content: None,
    )
    captured = capsys.readouterr()
    assert "No staged entries found." in captured.out
