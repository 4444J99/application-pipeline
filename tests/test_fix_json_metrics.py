import json
from pathlib import Path
import pytest
from scripts.fix_json_metrics import fix_json_metrics

def test_fix_json_metrics(tmp_path, monkeypatch):
    # Setup mock directory
    profiles_dir = tmp_path / "profiles"
    profiles_dir.mkdir()
    
    test_json = profiles_dir / "test.json"
    data = {
        "id": "test-entry",
        "description": "I have 42 essays and 33 sprints.",
        "nested": {
            "count": "42",
            "other": 42
        },
        "list": ["val 42", "42"]
    }
    test_json.write_text(json.dumps(data))
    
    # Patch directory and values in script
    monkeypatch.setattr("scripts.fix_json_metrics.PROFILES_DIR", profiles_dir)
    monkeypatch.setattr("scripts.fix_json_metrics.OLD_VAL", "42")
    monkeypatch.setattr("scripts.fix_json_metrics.NEW_VAL", "47")
    
    fix_json_metrics()
    
    with open(test_json) as f:
        updated = json.load(f)
        
    assert updated["description"] == "I have 47 essays and 33 sprints."
    assert updated["nested"]["count"] == "47"
    assert updated["nested"]["other"] == 42 # Integer should NOT be changed if logic is string-only
    assert "val 47" in updated["list"]
    assert "47" in updated["list"]

def test_fix_json_metrics_whole_word(tmp_path, monkeypatch):
    # Ensure it doesn't replace 42 in 420 or 142
    profiles_dir = tmp_path / "profiles"
    profiles_dir.mkdir()
    test_json = profiles_dir / "word.json"
    test_json.write_text(json.dumps({"val": "420 and 142 and 42"}))
    
    monkeypatch.setattr("scripts.fix_json_metrics.PROFILES_DIR", profiles_dir)
    monkeypatch.setattr("scripts.fix_json_metrics.OLD_VAL", "42")
    monkeypatch.setattr("scripts.fix_json_metrics.NEW_VAL", "47")
    
    fix_json_metrics()
    
    with open(test_json) as f:
        updated = json.load(f)
    assert updated["val"] == "420 and 142 and 47"
