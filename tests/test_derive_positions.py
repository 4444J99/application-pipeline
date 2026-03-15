"""Tests for scripts/derive_positions.py"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from derive_positions import (
    ORGAN_POSITION_AFFINITY,
    SNAPSHOT_PATH,
    STATIC_EVIDENCE,
    compute_position_scores,
    main,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_snapshot(organs=None, total_repos=100, generated_at="2026-01-01T00:00:00Z"):
    """Build a minimal snapshot dict."""
    if organs is None:
        organs = []
    return {
        "organs": organs,
        "system": {"total_repos": total_repos},
        "generated_at": generated_at,
    }


def _organ(key, repo_count):
    return {"key": key, "repo_count": repo_count}


# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------


def test_organ_position_affinity_keys():
    """All expected organs are present in the affinity map."""
    expected = {"ORGAN-I", "ORGAN-II", "ORGAN-III", "ORGAN-IV",
                "ORGAN-V", "ORGAN-VI", "ORGAN-VII", "META-ORGANVM"}
    assert set(ORGAN_POSITION_AFFINITY.keys()) == expected


def test_organ_position_affinity_values_are_tuples():
    """Each affinity entry is a (str, float) tuple."""
    for organ_key, affinities in ORGAN_POSITION_AFFINITY.items():
        assert isinstance(affinities, list), organ_key
        for item in affinities:
            assert isinstance(item, tuple) and len(item) == 2, organ_key
            position, affinity = item
            assert isinstance(position, str), organ_key
            assert isinstance(affinity, float), organ_key


def test_organ_position_affinity_weights_in_range():
    """All affinity weights are between 0 and 1 inclusive."""
    for organ_key, affinities in ORGAN_POSITION_AFFINITY.items():
        for _, affinity in affinities:
            assert 0.0 <= affinity <= 1.0, f"{organ_key} has out-of-range affinity {affinity}"


def test_static_evidence_keys():
    """Static evidence covers expected long-standing positions."""
    for key in ("documentation-engineer", "educator", "community-practitioner", "systems-artist"):
        assert key in STATIC_EVIDENCE, f"{key!r} missing from STATIC_EVIDENCE"


def test_static_evidence_values_in_range():
    """Static evidence scores are between 0 and 1 inclusive."""
    for position, score in STATIC_EVIDENCE.items():
        assert 0.0 <= score <= 1.0, f"{position} score {score} out of range"


def test_snapshot_path_is_path_object():
    """SNAPSHOT_PATH is a Path instance pointing to system-snapshot.json."""
    assert isinstance(SNAPSHOT_PATH, Path)
    assert SNAPSHOT_PATH.name == "system-snapshot.json"


# ---------------------------------------------------------------------------
# compute_position_scores — return structure
# ---------------------------------------------------------------------------


def test_returns_dict():
    """Return value is a dict."""
    result = compute_position_scores(_make_snapshot())
    assert isinstance(result, dict)


def test_result_values_have_required_keys():
    """Every position entry has score, recommendation, evidence."""
    snap = _make_snapshot(organs=[_organ("ORGAN-I", 20)], total_repos=20)
    result = compute_position_scores(snap)
    for position, data in result.items():
        assert "score" in data, position
        assert "recommendation" in data, position
        assert "evidence" in data, position


def test_scores_are_floats_between_0_and_1():
    """All scores are floats normalized to [0, 1]."""
    snap = _make_snapshot(organs=[_organ("ORGAN-I", 20)], total_repos=20)
    result = compute_position_scores(snap)
    for position, data in result.items():
        score = data["score"]
        assert isinstance(score, float), position
        assert 0.0 <= score <= 1.0, f"{position} score {score} out of bounds"


def test_result_is_sorted_descending_by_score():
    """Positions are sorted highest-score first."""
    snap = _make_snapshot(organs=[_organ("ORGAN-II", 30)], total_repos=30)
    result = compute_position_scores(snap)
    scores = [data["score"] for data in result.values()]
    assert scores == sorted(scores, reverse=True)


def test_evidence_is_list():
    """Evidence field is always a list."""
    snap = _make_snapshot(organs=[_organ("ORGAN-VI", 10)], total_repos=10)
    result = compute_position_scores(snap)
    for position, data in result.items():
        assert isinstance(data["evidence"], list), position


# ---------------------------------------------------------------------------
# compute_position_scores — recommendation levels
# ---------------------------------------------------------------------------


def test_recommendation_strong_for_high_scores():
    """Positions with normalized score >= 0.7 get 'strong' recommendation."""
    snap = _make_snapshot(organs=[_organ("ORGAN-II", 100)], total_repos=100)
    result = compute_position_scores(snap)
    for position, data in result.items():
        if data["score"] >= 0.7:
            assert data["recommendation"] == "strong", (
                f"{position} score={data['score']} expected strong"
            )


def test_recommendation_moderate_for_mid_scores():
    """Positions with normalized score in [0.4, 0.7) get 'moderate'."""
    snap = _make_snapshot(organs=[_organ("ORGAN-V", 50)], total_repos=50)
    result = compute_position_scores(snap)
    for position, data in result.items():
        if 0.4 <= data["score"] < 0.7:
            assert data["recommendation"] == "moderate", (
                f"{position} score={data['score']} expected moderate"
            )


def test_recommendation_emerging_for_low_scores():
    """Positions with normalized score < 0.4 get 'emerging'."""
    snap = _make_snapshot(organs=[_organ("ORGAN-III", 10)], total_repos=10)
    result = compute_position_scores(snap)
    for position, data in result.items():
        if data["score"] < 0.4:
            assert data["recommendation"] == "emerging", (
                f"{position} score={data['score']} expected emerging"
            )


# ---------------------------------------------------------------------------
# compute_position_scores — empty / edge cases
# ---------------------------------------------------------------------------


def test_empty_snapshot_dict():
    """Empty dict is handled gracefully — static evidence still produces results."""
    result = compute_position_scores({})
    # Static evidence covers 4 positions; at minimum those should appear
    assert len(result) >= len(STATIC_EVIDENCE)


def test_empty_organs_list():
    """No organs — only static evidence contributes."""
    snap = _make_snapshot(organs=[], total_repos=100)
    result = compute_position_scores(snap)
    # All static-evidence positions must be present
    for pos in STATIC_EVIDENCE:
        assert pos in result, f"{pos} missing with no organs"


def test_zero_total_repos():
    """total_repos == 0 does not cause ZeroDivisionError."""
    snap = _make_snapshot(organs=[_organ("ORGAN-I", 0)], total_repos=0)
    result = compute_position_scores(snap)
    assert isinstance(result, dict)


def test_single_organ_all_repos():
    """One organ owning all repos — its affinities drive scores."""
    snap = _make_snapshot(organs=[_organ("ORGAN-IV", 100)], total_repos=100)
    result = compute_position_scores(snap)
    # platform-orchestrator has highest ORGAN-IV affinity (0.8)
    assert "platform-orchestrator" in result


def test_missing_system_key():
    """Snapshot with no 'system' key still runs without error."""
    snap = {"organs": [_organ("ORGAN-I", 20)]}
    result = compute_position_scores(snap)
    assert isinstance(result, dict)


def test_missing_organs_key():
    """Snapshot with no 'organs' key still runs without error."""
    snap = {"system": {"total_repos": 50}}
    result = compute_position_scores(snap)
    assert isinstance(result, dict)


def test_organ_with_missing_key_field():
    """Organ dict missing 'key' is skipped gracefully."""
    snap = _make_snapshot(
        organs=[{"repo_count": 20}, _organ("ORGAN-II", 30)],
        total_repos=50,
    )
    result = compute_position_scores(snap)
    # ORGAN-II affinities (systems-artist, creative-technologist) should appear
    assert "systems-artist" in result


def test_organ_with_missing_repo_count():
    """Organ dict missing 'repo_count' defaults to 0."""
    snap = _make_snapshot(
        organs=[{"key": "ORGAN-I"}, _organ("ORGAN-II", 40)],
        total_repos=40,
    )
    result = compute_position_scores(snap)
    assert isinstance(result, dict)


def test_unknown_organ_key():
    """Unknown organ keys produce no affinity contribution but don't crash."""
    snap = _make_snapshot(organs=[_organ("ORGAN-UNKNOWN", 50)], total_repos=50)
    result = compute_position_scores(snap)
    assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# compute_position_scores — score normalization
# ---------------------------------------------------------------------------


def test_max_score_is_always_1():
    """After normalization the highest score is exactly 1.0."""
    snap = _make_snapshot(
        organs=[
            _organ("ORGAN-I", 20),
            _organ("ORGAN-II", 30),
            _organ("ORGAN-III", 28),
            _organ("ORGAN-IV", 7),
            _organ("ORGAN-V", 5),
            _organ("ORGAN-VI", 6),
            _organ("ORGAN-VII", 4),
            _organ("META-ORGANVM", 8),
        ],
        total_repos=108,
    )
    result = compute_position_scores(snap)
    max_score = max(data["score"] for data in result.values())
    assert max_score == 1.0


def test_static_evidence_contributes_without_organs():
    """documentation-engineer score > 0 even with no organ data."""
    snap = _make_snapshot(organs=[], total_repos=1)
    result = compute_position_scores(snap)
    assert result["documentation-engineer"]["score"] > 0


def test_static_evidence_added_on_top_of_organ_contribution():
    """systems-artist score reflects both ORGAN-II affinity AND static base."""
    # With only ORGAN-II we expect systems-artist to be boosted by both
    snap = _make_snapshot(organs=[_organ("ORGAN-II", 100)], total_repos=100)
    result = compute_position_scores(snap)
    assert result["systems-artist"]["score"] > 0


# ---------------------------------------------------------------------------
# compute_position_scores — evidence threshold
# ---------------------------------------------------------------------------


def test_evidence_only_includes_contributions_above_threshold():
    """Evidence strings only appear when weight * affinity > 0.02."""
    # organ with tiny weight — should produce no evidence for small-affinity positions
    snap = _make_snapshot(organs=[_organ("ORGAN-VII", 1)], total_repos=1000)
    result = compute_position_scores(snap)
    # ORGAN-VII has founder-operator (0.3) and creative-technologist (0.2)
    # weight = 1/1000 = 0.001; 0.001 * 0.3 = 0.0003 < 0.02 → no evidence
    for position, data in result.items():
        for ev_string in data["evidence"]:
            assert "ORGAN-VII" not in ev_string, (
                f"ORGAN-VII evidence should not appear at weight 0.001, got: {ev_string}"
            )


def test_evidence_present_for_large_weight_organs():
    """When organ weight is significant, evidence strings are generated."""
    snap = _make_snapshot(organs=[_organ("ORGAN-II", 80)], total_repos=100)
    result = compute_position_scores(snap)
    # systems-artist has affinity 0.8; weight=0.8 → contribution 0.64 >> 0.02
    sa_evidence = result.get("systems-artist", {}).get("evidence", [])
    assert any("ORGAN-II" in ev for ev in sa_evidence)


def test_evidence_format_contains_organ_key_and_affinity():
    """Evidence strings mention the organ key and affinity."""
    snap = _make_snapshot(organs=[_organ("ORGAN-VI", 50)], total_repos=50)
    result = compute_position_scores(snap)
    cp = result.get("community-practitioner", {})
    for ev in cp.get("evidence", []):
        assert "ORGAN-VI" in ev
        assert "affinity" in ev


# ---------------------------------------------------------------------------
# compute_position_scores — multi-organ integration
# ---------------------------------------------------------------------------


def test_all_organs_produce_all_expected_positions():
    """Running all organs together includes known positions in output."""
    snap = _make_snapshot(
        organs=[
            _organ("ORGAN-I", 20),
            _organ("ORGAN-II", 21),
            _organ("ORGAN-III", 26),
            _organ("ORGAN-IV", 7),
            _organ("ORGAN-V", 5),
            _organ("ORGAN-VI", 6),
            _organ("ORGAN-VII", 4),
            _organ("META-ORGANVM", 5),
        ],
        total_repos=94,
    )
    result = compute_position_scores(snap)
    expected_positions = {
        "independent-engineer", "systems-artist", "creative-technologist",
        "platform-orchestrator", "governance-architect", "community-practitioner",
        "educator", "documentation-engineer", "founder-operator",
    }
    for pos in expected_positions:
        assert pos in result, f"Expected position {pos!r} missing from result"


def test_organ_with_high_repo_fraction_dominates():
    """Organ owning most repos amplifies its affinity positions."""
    # ORGAN-III owns 90% → independent-engineer and founder-operator should rank high
    snap = _make_snapshot(
        organs=[
            _organ("ORGAN-III", 90),
            _organ("ORGAN-I", 10),
        ],
        total_repos=100,
    )
    result = compute_position_scores(snap)
    positions = list(result.keys())
    # independent-engineer should be high (ORGAN-III affinity 0.5, ORGAN-I 0.3)
    ie_rank = positions.index("independent-engineer") if "independent-engineer" in positions else 99
    # At least in top half of results
    assert ie_rank < len(positions) // 2 + 2


def test_organ_vi_boosts_community_practitioner():
    """ORGAN-VI (community-practitioner affinity 0.8) boosts that position."""
    snap = _make_snapshot(organs=[_organ("ORGAN-VI", 100)], total_repos=100)
    result = compute_position_scores(snap)
    assert "community-practitioner" in result


def test_meta_organvm_boosts_governance_and_platform():
    """META-ORGANVM drives platform-orchestrator and governance-architect."""
    snap = _make_snapshot(organs=[_organ("META-ORGANVM", 100)], total_repos=100)
    result = compute_position_scores(snap)
    assert "platform-orchestrator" in result
    assert "governance-architect" in result


# ---------------------------------------------------------------------------
# main() — CLI
# ---------------------------------------------------------------------------


def test_main_missing_snapshot_returns_1(tmp_path, monkeypatch, capsys):
    """main() returns 1 when snapshot file does not exist."""
    missing = tmp_path / "no-such-file.json"
    monkeypatch.setattr("sys.argv", ["derive_positions.py", "--snapshot", str(missing)])
    rc = main()
    assert rc == 1
    err = capsys.readouterr().err
    assert "ERROR" in err


def test_main_json_output(tmp_path, monkeypatch, capsys):
    """--json flag produces valid JSON output."""
    snap_data = _make_snapshot(organs=[_organ("ORGAN-I", 20)], total_repos=20)
    snap_file = tmp_path / "snapshot.json"
    snap_file.write_text(json.dumps(snap_data))

    monkeypatch.setattr(
        "sys.argv",
        ["derive_positions.py", "--snapshot", str(snap_file), "--json"],
    )
    rc = main()
    assert rc == 0
    out = capsys.readouterr().out
    parsed = json.loads(out)
    assert isinstance(parsed, dict)
    # Each value should have score/recommendation/evidence
    for position, data in parsed.items():
        assert "score" in data
        assert "recommendation" in data
        assert "evidence" in data


def test_main_human_output(tmp_path, monkeypatch, capsys):
    """Default (non-JSON) output contains human-readable header."""
    snap_data = _make_snapshot(
        organs=[_organ("ORGAN-II", 50)],
        total_repos=50,
        generated_at="2026-03-15T12:00:00Z",
    )
    snap_file = tmp_path / "snapshot.json"
    snap_file.write_text(json.dumps(snap_data))

    monkeypatch.setattr(
        "sys.argv",
        ["derive_positions.py", "--snapshot", str(snap_file)],
    )
    rc = main()
    assert rc == 0
    out = capsys.readouterr().out
    assert "Identity Position Relevance" in out
    assert "Score" in out
    assert "Evidence" in out


def test_main_human_output_shows_positions(tmp_path, monkeypatch, capsys):
    """Human output lists at least one known position."""
    snap_data = _make_snapshot(organs=[_organ("ORGAN-VI", 10)], total_repos=10)
    snap_file = tmp_path / "snapshot.json"
    snap_file.write_text(json.dumps(snap_data))

    monkeypatch.setattr(
        "sys.argv",
        ["derive_positions.py", "--snapshot", str(snap_file)],
    )
    main()
    out = capsys.readouterr().out
    assert "community-practitioner" in out


def test_main_human_output_shows_generated_at(tmp_path, monkeypatch, capsys):
    """Human output includes the snapshot generation timestamp."""
    snap_data = _make_snapshot(
        organs=[],
        generated_at="2026-03-15T09:30:00Z",
    )
    snap_file = tmp_path / "snapshot.json"
    snap_file.write_text(json.dumps(snap_data))

    monkeypatch.setattr(
        "sys.argv",
        ["derive_positions.py", "--snapshot", str(snap_file)],
    )
    main()
    out = capsys.readouterr().out
    assert "2026-03-15" in out


def test_main_human_output_shows_static_label(tmp_path, monkeypatch, capsys):
    """Positions with no dynamic evidence show '(static)' marker."""
    snap_data = _make_snapshot(organs=[], total_repos=1)
    snap_file = tmp_path / "snapshot.json"
    snap_file.write_text(json.dumps(snap_data))

    monkeypatch.setattr(
        "sys.argv",
        ["derive_positions.py", "--snapshot", str(snap_file)],
    )
    main()
    out = capsys.readouterr().out
    assert "(static)" in out


def test_main_returns_0_on_success(tmp_path, monkeypatch):
    """main() returns 0 on successful run."""
    snap_data = _make_snapshot(organs=[_organ("ORGAN-I", 5)], total_repos=5)
    snap_file = tmp_path / "snap.json"
    snap_file.write_text(json.dumps(snap_data))

    monkeypatch.setattr(
        "sys.argv",
        ["derive_positions.py", "--snapshot", str(snap_file)],
    )
    rc = main()
    assert rc == 0


def test_main_json_output_is_sorted_by_score(tmp_path, monkeypatch, capsys):
    """JSON output preserves descending score order."""
    snap_data = _make_snapshot(
        organs=[
            _organ("ORGAN-II", 50),
            _organ("ORGAN-IV", 50),
        ],
        total_repos=100,
    )
    snap_file = tmp_path / "snap.json"
    snap_file.write_text(json.dumps(snap_data))

    monkeypatch.setattr(
        "sys.argv",
        ["derive_positions.py", "--snapshot", str(snap_file), "--json"],
    )
    main()
    parsed = json.loads(capsys.readouterr().out)
    scores = [v["score"] for v in parsed.values()]
    assert scores == sorted(scores, reverse=True)


def test_main_empty_organs_json(tmp_path, monkeypatch, capsys):
    """Empty organs list still produces valid JSON from static evidence."""
    snap_data = _make_snapshot(organs=[], total_repos=0)
    snap_file = tmp_path / "snap.json"
    snap_file.write_text(json.dumps(snap_data))

    monkeypatch.setattr(
        "sys.argv",
        ["derive_positions.py", "--snapshot", str(snap_file), "--json"],
    )
    rc = main()
    assert rc == 0
    parsed = json.loads(capsys.readouterr().out)
    for pos in STATIC_EVIDENCE:
        assert pos in parsed


def test_main_snapshot_without_generated_at(tmp_path, monkeypatch, capsys):
    """Snapshot missing generated_at shows 'unknown' instead of crashing."""
    snap_data = {"organs": [], "system": {"total_repos": 10}}
    snap_file = tmp_path / "snap.json"
    snap_file.write_text(json.dumps(snap_data))

    monkeypatch.setattr(
        "sys.argv",
        ["derive_positions.py", "--snapshot", str(snap_file)],
    )
    rc = main()
    assert rc == 0
    out = capsys.readouterr().out
    assert "unknown" in out
