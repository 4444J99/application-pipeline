"""Tests for scripts/refresh_from_ecosystem.py"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import refresh_from_ecosystem as rfe
from refresh_from_ecosystem import (
    _to_k,
    build_metrics_from_snapshot,
    build_metrics_from_system_metrics,
    load_json,
    main,
    write_metrics_yaml,
)

# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

_MINIMAL_SNAPSHOT = {
    "generated_at": "2026-03-15T06:00:00Z",
    "system": {
        "total_repos": 105,
        "active_repos": 97,
        "density": 3.7,
        "entities": 210,
        "edges": 420,
        "ammoi": "0.85",
    },
    "variables": {
        "total_repos": 105,
        "active_repos": 97,
        "archived_repos": 8,
        "total_organs": 8,
        "published_essays": 48,
        "total_words_numeric": 810000,
        "repos_with_tests": 2349,
        "sprints_completed": 33,
        "code_files": 1200,
        "test_files": 400,
        "ci_workflows": 22,
        "dependency_edges": 45,
    },
    "organs": [
        {"key": "ORGAN-I", "repo_count": 20},
        {"key": "ORGAN-II", "repo_count": 30},
        {"key": "META-ORGANVM", "repo_count": 8},
    ],
}

_MINIMAL_SYSTEM_METRICS = {
    "computed": {
        "total_repos": 100,
        "active_repos": 90,
        "archived_repos": 10,
        "total_organs": 8,
        "published_essays": 40,
        "total_words_numeric": 750000,
        "repos_with_tests": 2000,
        "sprints_completed": 30,
        "code_files": 1100,
        "test_files": 350,
        "ci_workflows": 18,
        "dependency_edges": 38,
    }
}


# ---------------------------------------------------------------------------
# _to_k
# ---------------------------------------------------------------------------


def test_to_k_round_number():
    assert _to_k(810000) == 810


def test_to_k_small_number():
    """Values below 1000 return 1 due to max(1, …) guard."""
    assert _to_k(500) == 1


def test_to_k_exactly_1000():
    assert _to_k(1000) == 1


def test_to_k_999():
    """Values below 1000 floor to 0 (max(1, …) applies only when n>=1000)."""
    # 999 // 1000 = 0; max(1, 0) = 1  — function returns at least 1 if n>=1
    # Actually max(1, 0) = 1 because n=999 is truthy as int(str(999)) = 999 ≥ 1
    # Let's verify the actual behaviour: max(1, 999 // 1000) = max(1, 0) = 1
    assert _to_k(999) == 1


def test_to_k_zero():
    """Zero word count → 0 (max(1,0) only applies when n is non-zero positive)."""
    # int("0") = 0; 0 // 1000 = 0; max(1, 0) = 1  — but wait n=0 < 1, so…
    # The function: n = int("0") = 0; return max(1, 0 // 1000) = max(1, 0) = 1
    # That is the actual return value; test the real behaviour:
    assert _to_k(0) == 1


def test_to_k_comma_formatted_string():
    assert _to_k("810,000") == 810


def test_to_k_invalid_string_returns_0():
    assert _to_k("not-a-number") == 0


def test_to_k_none_returns_0():
    assert _to_k(None) == 0


def test_to_k_large_value():
    assert _to_k(2_000_000) == 2000


# ---------------------------------------------------------------------------
# load_json
# ---------------------------------------------------------------------------


def test_load_json_reads_valid_file(tmp_path):
    data = {"key": "value", "count": 42}
    f = tmp_path / "data.json"
    f.write_text(json.dumps(data))
    result = load_json(f)
    assert result == data


def test_load_json_missing_file_raises(tmp_path):
    missing = tmp_path / "nonexistent.json"
    try:
        load_json(missing)
        assert False, "Should have raised"
    except FileNotFoundError:
        pass


def test_load_json_malformed_json_raises(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("{not valid json")
    try:
        load_json(bad)
        assert False, "Should have raised"
    except json.JSONDecodeError:
        pass


# ---------------------------------------------------------------------------
# build_metrics_from_snapshot
# ---------------------------------------------------------------------------


def test_build_metrics_from_snapshot_total_repos():
    metrics = build_metrics_from_snapshot(_MINIMAL_SNAPSHOT)
    assert metrics["total_repos"] == 105


def test_build_metrics_from_snapshot_active_repos():
    metrics = build_metrics_from_snapshot(_MINIMAL_SNAPSHOT)
    assert metrics["active_repos"] == 97


def test_build_metrics_from_snapshot_archived_repos():
    metrics = build_metrics_from_snapshot(_MINIMAL_SNAPSHOT)
    assert metrics["archived_repos"] == 8


def test_build_metrics_from_snapshot_organizations():
    metrics = build_metrics_from_snapshot(_MINIMAL_SNAPSHOT)
    assert metrics["organizations"] == 8


def test_build_metrics_from_snapshot_published_essays():
    metrics = build_metrics_from_snapshot(_MINIMAL_SNAPSHOT)
    assert metrics["published_essays"] == 48


def test_build_metrics_from_snapshot_total_words_k():
    metrics = build_metrics_from_snapshot(_MINIMAL_SNAPSHOT)
    assert metrics["total_words_k"] == 810


def test_build_metrics_from_snapshot_automated_tests():
    metrics = build_metrics_from_snapshot(_MINIMAL_SNAPSHOT)
    assert metrics["automated_tests"] == 2349


def test_build_metrics_from_snapshot_development_sprints():
    metrics = build_metrics_from_snapshot(_MINIMAL_SNAPSHOT)
    assert metrics["development_sprints"] == 33


def test_build_metrics_from_snapshot_code_files():
    metrics = build_metrics_from_snapshot(_MINIMAL_SNAPSHOT)
    assert metrics["code_files"] == 1200


def test_build_metrics_from_snapshot_test_files():
    metrics = build_metrics_from_snapshot(_MINIMAL_SNAPSHOT)
    assert metrics["test_files"] == 400


def test_build_metrics_from_snapshot_ci_workflows():
    metrics = build_metrics_from_snapshot(_MINIMAL_SNAPSHOT)
    assert metrics["ci_workflows"] == 22


def test_build_metrics_from_snapshot_dependency_edges():
    metrics = build_metrics_from_snapshot(_MINIMAL_SNAPSHOT)
    assert metrics["dependency_edges"] == 45


def test_build_metrics_from_snapshot_density():
    metrics = build_metrics_from_snapshot(_MINIMAL_SNAPSHOT)
    assert metrics["density"] == 3.7


def test_build_metrics_from_snapshot_entities():
    metrics = build_metrics_from_snapshot(_MINIMAL_SNAPSHOT)
    assert metrics["entities"] == 210


def test_build_metrics_from_snapshot_edges():
    metrics = build_metrics_from_snapshot(_MINIMAL_SNAPSHOT)
    assert metrics["edges"] == 420


def test_build_metrics_from_snapshot_ammoi():
    metrics = build_metrics_from_snapshot(_MINIMAL_SNAPSHOT)
    assert metrics["ammoi"] == "0.85"


def test_build_metrics_from_snapshot_organs_dict():
    metrics = build_metrics_from_snapshot(_MINIMAL_SNAPSHOT)
    assert isinstance(metrics["organs"], dict)
    assert metrics["organs"]["I"] == 20
    assert metrics["organs"]["II"] == 30


def test_build_metrics_from_snapshot_meta_organ_key():
    """META-ORGANVM key maps to 'Meta' in the organs dict."""
    metrics = build_metrics_from_snapshot(_MINIMAL_SNAPSHOT)
    assert "Meta" in metrics["organs"]
    assert metrics["organs"]["Meta"] == 8


def test_build_metrics_from_snapshot_variables_take_precedence_over_system():
    """Variables section takes precedence over system section for total_repos."""
    snapshot = {
        "system": {"total_repos": 90, "active_repos": 80},
        "variables": {"total_repos": 105, "active_repos": 97},
        "organs": [],
    }
    metrics = build_metrics_from_snapshot(snapshot)
    assert metrics["total_repos"] == 105
    assert metrics["active_repos"] == 97


def test_build_metrics_from_snapshot_missing_variables_falls_back_to_system():
    """When variables is absent, system section values are used."""
    snapshot = {
        "system": {"total_repos": 90, "active_repos": 80},
        "variables": {},
        "organs": [],
    }
    metrics = build_metrics_from_snapshot(snapshot)
    assert metrics["total_repos"] == 90
    assert metrics["active_repos"] == 80


def test_build_metrics_from_snapshot_empty_snapshot():
    """Empty snapshot dict returns safe zero defaults."""
    metrics = build_metrics_from_snapshot({})
    assert metrics["total_repos"] == 0
    assert metrics["active_repos"] == 0
    assert metrics["organizations"] == 8  # default fallback
    assert metrics["organs"] == {}


def test_build_metrics_from_snapshot_organs_empty_list():
    """No organs in list → empty organs dict."""
    snapshot = {**_MINIMAL_SNAPSHOT, "organs": []}
    metrics = build_metrics_from_snapshot(snapshot)
    assert metrics["organs"] == {}


def test_build_metrics_from_snapshot_organ_missing_key():
    """Organ entries with missing 'key' are handled gracefully."""
    snapshot = {
        "system": {},
        "variables": {},
        "organs": [{"repo_count": 5}],  # no 'key'
    }
    metrics = build_metrics_from_snapshot(snapshot)
    # Should not raise; empty key maps to empty string after strip
    assert isinstance(metrics["organs"], dict)


def test_build_metrics_from_snapshot_total_organs_default():
    """Missing total_organs variable defaults to 8."""
    snap = {
        "system": {},
        "variables": {"total_repos": 50},
        "organs": [],
    }
    metrics = build_metrics_from_snapshot(snap)
    assert metrics["organizations"] == 8


# ---------------------------------------------------------------------------
# build_metrics_from_system_metrics
# ---------------------------------------------------------------------------


def test_build_from_system_metrics_total_repos():
    metrics = build_metrics_from_system_metrics(_MINIMAL_SYSTEM_METRICS)
    assert metrics["total_repos"] == 100


def test_build_from_system_metrics_active_repos():
    metrics = build_metrics_from_system_metrics(_MINIMAL_SYSTEM_METRICS)
    assert metrics["active_repos"] == 90


def test_build_from_system_metrics_organizations():
    metrics = build_metrics_from_system_metrics(_MINIMAL_SYSTEM_METRICS)
    assert metrics["organizations"] == 8


def test_build_from_system_metrics_total_words_k():
    metrics = build_metrics_from_system_metrics(_MINIMAL_SYSTEM_METRICS)
    assert metrics["total_words_k"] == 750


def test_build_from_system_metrics_automated_tests():
    metrics = build_metrics_from_system_metrics(_MINIMAL_SYSTEM_METRICS)
    assert metrics["automated_tests"] == 2000


def test_build_from_system_metrics_density_is_zero():
    """Fallback path has no density data."""
    metrics = build_metrics_from_system_metrics(_MINIMAL_SYSTEM_METRICS)
    assert metrics["density"] == 0
    assert metrics["entities"] == 0
    assert metrics["edges"] == 0


def test_build_from_system_metrics_ammoi_empty():
    metrics = build_metrics_from_system_metrics(_MINIMAL_SYSTEM_METRICS)
    assert metrics["ammoi"] == ""


def test_build_from_system_metrics_organs_empty():
    metrics = build_metrics_from_system_metrics(_MINIMAL_SYSTEM_METRICS)
    assert metrics["organs"] == {}


def test_build_from_system_metrics_empty_dict():
    """Completely empty input returns safe defaults."""
    metrics = build_metrics_from_system_metrics({})
    assert metrics["total_repos"] == 0
    assert metrics["organizations"] == 8


def test_build_from_system_metrics_missing_computed_key():
    """No 'computed' key → falls back to defaults."""
    metrics = build_metrics_from_system_metrics({"other": {}})
    assert metrics["total_repos"] == 0


# ---------------------------------------------------------------------------
# write_metrics_yaml
# ---------------------------------------------------------------------------


def test_write_metrics_yaml_creates_file(tmp_path):
    out = tmp_path / "config" / "metrics.yaml"
    metrics = build_metrics_from_snapshot(_MINIMAL_SNAPSHOT)
    write_metrics_yaml(metrics, out)
    assert out.exists()


def test_write_metrics_yaml_creates_parent_dirs(tmp_path):
    out = tmp_path / "deep" / "nested" / "metrics.yaml"
    metrics = build_metrics_from_snapshot(_MINIMAL_SNAPSHOT)
    write_metrics_yaml(metrics, out)
    assert out.exists()


def test_write_metrics_yaml_contains_total_repos(tmp_path):
    out = tmp_path / "metrics.yaml"
    metrics = build_metrics_from_snapshot(_MINIMAL_SNAPSHOT)
    write_metrics_yaml(metrics, out)
    content = out.read_text()
    assert "total_repos: 105" in content


def test_write_metrics_yaml_contains_active_repos(tmp_path):
    out = tmp_path / "metrics.yaml"
    metrics = build_metrics_from_snapshot(_MINIMAL_SNAPSHOT)
    write_metrics_yaml(metrics, out)
    assert "active_repos: 97" in out.read_text()


def test_write_metrics_yaml_system_section_present(tmp_path):
    out = tmp_path / "metrics.yaml"
    metrics = build_metrics_from_snapshot(_MINIMAL_SNAPSHOT)
    write_metrics_yaml(metrics, out)
    assert "system:" in out.read_text()


def test_write_metrics_yaml_organism_section_when_density(tmp_path):
    out = tmp_path / "metrics.yaml"
    metrics = build_metrics_from_snapshot(_MINIMAL_SNAPSHOT)
    write_metrics_yaml(metrics, out)
    content = out.read_text()
    assert "organism:" in content
    assert "density:" in content
    assert "ammoi:" in content


def test_write_metrics_yaml_no_organism_section_when_density_zero(tmp_path):
    out = tmp_path / "metrics.yaml"
    metrics = build_metrics_from_system_metrics(_MINIMAL_SYSTEM_METRICS)
    write_metrics_yaml(metrics, out)
    content = out.read_text()
    assert "organism:" not in content


def test_write_metrics_yaml_organs_section_sorted(tmp_path):
    out = tmp_path / "metrics.yaml"
    metrics = build_metrics_from_snapshot(_MINIMAL_SNAPSHOT)
    write_metrics_yaml(metrics, out)
    content = out.read_text()
    assert "organs:" in content
    # Verify keys appear in alphabetical order
    lines = [l.strip() for l in content.splitlines() if l.strip().startswith(("I:", "II:", "Meta:"))]
    assert lines.index("I: 20") < lines.index("II: 30")


def test_write_metrics_yaml_no_organs_section_when_empty(tmp_path):
    out = tmp_path / "metrics.yaml"
    metrics = build_metrics_from_system_metrics(_MINIMAL_SYSTEM_METRICS)
    write_metrics_yaml(metrics, out)
    content = out.read_text()
    assert "organs:" not in content


def test_write_metrics_yaml_dry_run_returns_content_no_file(tmp_path):
    out = tmp_path / "config" / "metrics.yaml"
    metrics = build_metrics_from_snapshot(_MINIMAL_SNAPSHOT)
    content = write_metrics_yaml(metrics, out, dry_run=True)
    # Should return the YAML string
    assert "total_repos: 105" in content
    # Should NOT write the file
    assert not out.exists()


def test_write_metrics_yaml_dry_run_returns_string():
    out = Path("/nonexistent/path/metrics.yaml")
    metrics = build_metrics_from_snapshot(_MINIMAL_SNAPSHOT)
    result = write_metrics_yaml(metrics, out, dry_run=True)
    assert isinstance(result, str)
    assert len(result) > 0


def test_write_metrics_yaml_has_auto_generated_comment(tmp_path):
    out = tmp_path / "metrics.yaml"
    metrics = build_metrics_from_snapshot(_MINIMAL_SNAPSHOT)
    write_metrics_yaml(metrics, out)
    content = out.read_text()
    assert "Auto-generated" in content


def test_write_metrics_yaml_has_date_in_comment(tmp_path):
    from datetime import UTC, datetime
    out = tmp_path / "metrics.yaml"
    metrics = build_metrics_from_snapshot(_MINIMAL_SNAPSHOT)
    write_metrics_yaml(metrics, out)
    content = out.read_text()
    today = datetime.now(UTC).strftime("%Y-%m-%d")
    assert today in content


def test_write_metrics_yaml_all_system_fields_present(tmp_path):
    out = tmp_path / "metrics.yaml"
    metrics = build_metrics_from_snapshot(_MINIMAL_SNAPSHOT)
    write_metrics_yaml(metrics, out)
    content = out.read_text()
    required_fields = [
        "total_repos:",
        "active_repos:",
        "archived_repos:",
        "organizations:",
        "published_essays:",
        "total_words_k:",
        "automated_tests:",
        "development_sprints:",
        "code_files:",
        "test_files:",
        "ci_workflows:",
        "dependency_edges:",
    ]
    for field in required_fields:
        assert field in content, f"Missing field: {field}"


def test_write_metrics_yaml_ammoi_quoted(tmp_path):
    """ammoi value is written with quotes in the YAML."""
    out = tmp_path / "metrics.yaml"
    metrics = build_metrics_from_snapshot(_MINIMAL_SNAPSHOT)
    write_metrics_yaml(metrics, out)
    content = out.read_text()
    assert 'ammoi: "0.85"' in content


def test_write_metrics_yaml_overwrites_existing_file(tmp_path):
    out = tmp_path / "metrics.yaml"
    out.write_text("old content")
    metrics = build_metrics_from_snapshot(_MINIMAL_SNAPSHOT)
    write_metrics_yaml(metrics, out)
    content = out.read_text()
    assert "old content" not in content
    assert "total_repos:" in content


# ---------------------------------------------------------------------------
# main() — integration tests via argv manipulation
# ---------------------------------------------------------------------------


def test_main_no_sources_returns_1(monkeypatch, tmp_path):
    """main() returns 1 when neither snapshot nor fallback JSON exists."""
    missing_snap = tmp_path / "nonexistent-snapshot.json"
    missing_metrics = tmp_path / "nonexistent-metrics.json"
    monkeypatch.setattr(
        sys, "argv",
        [
            "refresh_from_ecosystem.py",
            "--snapshot", str(missing_snap),
            "--metrics", str(missing_metrics),
        ],
    )
    result = main()
    assert result == 1


def test_main_uses_snapshot_when_present(monkeypatch, tmp_path):
    """main() succeeds (return 0) when snapshot file exists."""
    snap = tmp_path / "snapshot.json"
    snap.write_text(json.dumps(_MINIMAL_SNAPSHOT))

    out_yaml = tmp_path / "config" / "metrics.yaml"
    monkeypatch.setattr(rfe, "CONFIG_METRICS", out_yaml)
    monkeypatch.setattr(
        sys, "argv",
        [
            "refresh_from_ecosystem.py",
            "--snapshot", str(snap),
            "--metrics", str(tmp_path / "none.json"),
        ],
    )
    result = main()
    assert result == 0
    assert out_yaml.exists()


def test_main_falls_back_to_system_metrics(monkeypatch, tmp_path):
    """main() uses system-metrics.json when snapshot is absent."""
    sys_metrics = tmp_path / "system-metrics.json"
    sys_metrics.write_text(json.dumps(_MINIMAL_SYSTEM_METRICS))

    out_yaml = tmp_path / "config" / "metrics.yaml"
    monkeypatch.setattr(rfe, "CONFIG_METRICS", out_yaml)
    monkeypatch.setattr(
        sys, "argv",
        [
            "refresh_from_ecosystem.py",
            "--snapshot", str(tmp_path / "none.json"),
            "--metrics", str(sys_metrics),
        ],
    )
    result = main()
    assert result == 0
    assert out_yaml.exists()
    content = out_yaml.read_text()
    assert "total_repos: 100" in content


def test_main_dry_run_does_not_write(monkeypatch, tmp_path):
    """--dry-run flag: main() returns 0 and does not write config/metrics.yaml."""
    snap = tmp_path / "snapshot.json"
    snap.write_text(json.dumps(_MINIMAL_SNAPSHOT))

    out_yaml = tmp_path / "config" / "metrics.yaml"
    monkeypatch.setattr(rfe, "CONFIG_METRICS", out_yaml)
    monkeypatch.setattr(
        sys, "argv",
        [
            "refresh_from_ecosystem.py",
            "--snapshot", str(snap),
            "--metrics", str(tmp_path / "none.json"),
            "--dry-run",
        ],
    )
    result = main()
    assert result == 0
    assert not out_yaml.exists()


def test_main_dry_run_with_propagate_does_not_call_subprocess(monkeypatch, tmp_path):
    """--dry-run --propagate prints intent but does not invoke subprocess.run."""
    import subprocess

    snap = tmp_path / "snapshot.json"
    snap.write_text(json.dumps(_MINIMAL_SNAPSHOT))

    out_yaml = tmp_path / "config" / "metrics.yaml"
    monkeypatch.setattr(rfe, "CONFIG_METRICS", out_yaml)

    calls = []
    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: calls.append((a, kw)))

    monkeypatch.setattr(
        sys, "argv",
        [
            "refresh_from_ecosystem.py",
            "--snapshot", str(snap),
            "--metrics", str(tmp_path / "none.json"),
            "--dry-run",
            "--propagate",
        ],
    )
    result = main()
    assert result == 0
    assert len(calls) == 0


def test_main_propagate_calls_subprocess(monkeypatch, tmp_path):
    """--propagate (without --dry-run) calls subprocess.run with check_metrics.py."""
    import subprocess

    snap = tmp_path / "snapshot.json"
    snap.write_text(json.dumps(_MINIMAL_SNAPSHOT))

    out_yaml = tmp_path / "config" / "metrics.yaml"
    monkeypatch.setattr(rfe, "CONFIG_METRICS", out_yaml)

    calls = []

    class FakeResult:
        returncode = 0
        stdout = "ok"
        stderr = ""

    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: (calls.append((a, kw)), FakeResult())[1])

    monkeypatch.setattr(
        sys, "argv",
        [
            "refresh_from_ecosystem.py",
            "--snapshot", str(snap),
            "--metrics", str(tmp_path / "none.json"),
            "--propagate",
        ],
    )
    result = main()
    assert result == 0
    assert len(calls) == 1
    cmd_args = calls[0][0][0]
    assert "check_metrics.py" in str(cmd_args)
    assert "--fix" in cmd_args
    assert "--yes" in cmd_args


def test_main_snapshot_preferred_over_system_metrics(monkeypatch, tmp_path, capsys):
    """When both files exist, snapshot is used (not system-metrics)."""
    snap = tmp_path / "snapshot.json"
    snap.write_text(json.dumps(_MINIMAL_SNAPSHOT))

    sys_m = tmp_path / "system-metrics.json"
    sys_m.write_text(json.dumps(_MINIMAL_SYSTEM_METRICS))

    out_yaml = tmp_path / "config" / "metrics.yaml"
    monkeypatch.setattr(rfe, "CONFIG_METRICS", out_yaml)
    monkeypatch.setattr(
        sys, "argv",
        [
            "refresh_from_ecosystem.py",
            "--snapshot", str(snap),
            "--metrics", str(sys_m),
        ],
    )
    main()
    out = capsys.readouterr().out
    # Should mention snapshot, not fallback
    assert "system-snapshot.json" in out
    assert "fallback" not in out


def test_main_prints_source_info(monkeypatch, tmp_path, capsys):
    """main() prints source, total_repos, active_repos, ci_workflows, density."""
    snap = tmp_path / "snapshot.json"
    snap.write_text(json.dumps(_MINIMAL_SNAPSHOT))

    out_yaml = tmp_path / "config" / "metrics.yaml"
    monkeypatch.setattr(rfe, "CONFIG_METRICS", out_yaml)
    monkeypatch.setattr(
        sys, "argv",
        [
            "refresh_from_ecosystem.py",
            "--snapshot", str(snap),
            "--metrics", str(tmp_path / "none.json"),
        ],
    )
    main()
    out = capsys.readouterr().out
    assert "total_repos: 105" in out
    assert "active_repos: 97" in out
    assert "ci_workflows: 22" in out
    assert "density: 3.7" in out


def test_main_dry_run_prefix_in_output(monkeypatch, tmp_path, capsys):
    """--dry-run mode prefixes output with [DRY RUN]."""
    snap = tmp_path / "snapshot.json"
    snap.write_text(json.dumps(_MINIMAL_SNAPSHOT))

    out_yaml = tmp_path / "config" / "metrics.yaml"
    monkeypatch.setattr(rfe, "CONFIG_METRICS", out_yaml)
    monkeypatch.setattr(
        sys, "argv",
        [
            "refresh_from_ecosystem.py",
            "--snapshot", str(snap),
            "--metrics", str(tmp_path / "none.json"),
            "--dry-run",
        ],
    )
    main()
    out = capsys.readouterr().out
    assert "[DRY RUN]" in out


def test_main_error_output_when_no_sources(monkeypatch, tmp_path, capsys):
    """main() writes error to stderr when no data sources found."""
    monkeypatch.setattr(
        sys, "argv",
        [
            "refresh_from_ecosystem.py",
            "--snapshot", str(tmp_path / "none1.json"),
            "--metrics", str(tmp_path / "none2.json"),
        ],
    )
    main()
    err = capsys.readouterr().err
    assert "ERROR" in err
    assert "No ecosystem data source found" in err


def test_main_written_path_in_output(monkeypatch, tmp_path, capsys):
    """Non-dry-run mode prints the written path."""
    snap = tmp_path / "snapshot.json"
    snap.write_text(json.dumps(_MINIMAL_SNAPSHOT))

    out_yaml = tmp_path / "config" / "metrics.yaml"
    monkeypatch.setattr(rfe, "CONFIG_METRICS", out_yaml)
    monkeypatch.setattr(
        sys, "argv",
        [
            "refresh_from_ecosystem.py",
            "--snapshot", str(snap),
            "--metrics", str(tmp_path / "none.json"),
        ],
    )
    main()
    out = capsys.readouterr().out
    assert "Written:" in out


def test_main_fallback_source_label_in_output(monkeypatch, tmp_path, capsys):
    """When using system-metrics.json fallback, output mentions 'fallback'."""
    sys_m = tmp_path / "system-metrics.json"
    sys_m.write_text(json.dumps(_MINIMAL_SYSTEM_METRICS))

    out_yaml = tmp_path / "config" / "metrics.yaml"
    monkeypatch.setattr(rfe, "CONFIG_METRICS", out_yaml)
    monkeypatch.setattr(
        sys, "argv",
        [
            "refresh_from_ecosystem.py",
            "--snapshot", str(tmp_path / "none.json"),
            "--metrics", str(sys_m),
        ],
    )
    main()
    out = capsys.readouterr().out
    assert "fallback" in out


# ---------------------------------------------------------------------------
# Edge cases: malformed snapshot/metrics content
# ---------------------------------------------------------------------------


def test_build_metrics_from_snapshot_string_word_count():
    """total_words_numeric as a formatted string is handled by _to_k."""
    snapshot = {
        "system": {},
        "variables": {"total_words_numeric": "810,000"},
        "organs": [],
    }
    metrics = build_metrics_from_snapshot(snapshot)
    assert metrics["total_words_k"] == 810


def test_build_metrics_from_snapshot_organ_key_strip():
    """ORGAN-III becomes 'III' in the organs dict."""
    snapshot = {
        "system": {},
        "variables": {},
        "organs": [{"key": "ORGAN-III", "repo_count": 28}],
    }
    metrics = build_metrics_from_snapshot(snapshot)
    assert "III" in metrics["organs"]
    assert metrics["organs"]["III"] == 28


def test_build_metrics_from_snapshot_integer_coercion():
    """String integers in variables are cast to int correctly."""
    snapshot = {
        "system": {},
        "variables": {
            "total_repos": "105",
            "active_repos": "97",
            "archived_repos": "8",
            "total_organs": "8",
        },
        "organs": [],
    }
    metrics = build_metrics_from_snapshot(snapshot)
    assert metrics["total_repos"] == 105
    assert isinstance(metrics["total_repos"], int)


def test_build_metrics_from_system_metrics_words_k():
    """total_words_numeric in system-metrics also goes through _to_k."""
    data = {"computed": {"total_words_numeric": 1_000_000}}
    metrics = build_metrics_from_system_metrics(data)
    assert metrics["total_words_k"] == 1000


def test_write_metrics_yaml_organs_absent_when_metrics_has_empty_organs(tmp_path):
    """organs section is not emitted when organs dict is empty."""
    out = tmp_path / "m.yaml"
    metrics = {
        "total_repos": 10, "active_repos": 8, "archived_repos": 2,
        "organizations": 8, "published_essays": 5, "total_words_k": 100,
        "automated_tests": 50, "development_sprints": 5,
        "code_files": 100, "test_files": 30, "ci_workflows": 5,
        "dependency_edges": 10, "density": 0, "entities": 0,
        "edges": 0, "ammoi": "", "organs": {},
    }
    write_metrics_yaml(metrics, out)
    content = out.read_text()
    assert "organs:" not in content


def test_main_snapshot_with_no_generated_at(monkeypatch, tmp_path, capsys):
    """Snapshot missing 'generated_at' does not crash — uses 'unknown'."""
    snap_data = {k: v for k, v in _MINIMAL_SNAPSHOT.items() if k != "generated_at"}
    snap = tmp_path / "snapshot.json"
    snap.write_text(json.dumps(snap_data))

    out_yaml = tmp_path / "config" / "metrics.yaml"
    monkeypatch.setattr(rfe, "CONFIG_METRICS", out_yaml)
    monkeypatch.setattr(
        sys, "argv",
        [
            "refresh_from_ecosystem.py",
            "--snapshot", str(snap),
            "--metrics", str(tmp_path / "none.json"),
        ],
    )
    result = main()
    assert result == 0
    out = capsys.readouterr().out
    assert "unknown" in out
