import os
import yaml
from pathlib import Path
import pytest
from scripts.generate_from_templates import render_template

def test_render_template():
    metrics = {
        "system": {
            "total_repos": 100,
            "published_essays": 40
        },
        "organs": {
            "I": 10
        }
    }
    
    template = "Repos: {{ system.total_repos }}, Essays: {{ system.published_essays }}, Organ I: {{ organs.I }}"
    expected = "Repos: 100, Essays: 40, Organ I: 10"
    
    rendered = render_template(template, metrics)
    assert rendered == expected

def test_render_template_missing_key():
    metrics = {"system": {"total": 10}}
    template = "Missing: {{ system.none }}"
    rendered = render_template(template, metrics)
    assert "MISSING_none" in rendered

def test_generation_workflow(tmp_path, monkeypatch):
    # Mock REPO_ROOT and other paths
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / "scripts").mkdir()
    (repo_root / "config").mkdir()
    (repo_root / "templates" / "blocks").mkdir(parents=True)
    
    metrics_file = repo_root / "config" / "metrics.yaml"
    metrics_data = {"system": {"total": 50}}
    metrics_file.write_text(yaml.dump(metrics_data))
    
    template_file = repo_root / "templates" / "blocks" / "test.md.j2"
    template_file.write_text("Total: {{ system.total }}")
    
    from scripts.generate_from_templates import generate_all
    
    # Patch the constants in the script
    monkeypatch.setattr("scripts.generate_from_templates.REPO_ROOT", repo_root)
    monkeypatch.setattr("scripts.generate_from_templates.TEMPLATES_DIR", repo_root / "templates")
    monkeypatch.setattr("scripts.generate_from_templates.METRICS_FILE", metrics_file)
    
    generate_all()
    
    output_file = repo_root / "blocks" / "test.md"
    assert output_file.exists()
    assert output_file.read_text() == "Total: 50"
