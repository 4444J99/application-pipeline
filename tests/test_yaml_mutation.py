#!/usr/bin/env python3
"""Tests for yaml_mutation.py — round-trip YAML editing."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import yaml
from yaml_mutation import YAMLEditor

SAMPLE_YAML = """\
id: test-entry
status: drafting
target:
  organization: Acme Corp
  portal: greenhouse
submission:
  materials_attached: []
  blocks_used: {}
  variant_ids: {}
fit:
  composite: 8.5
  identity_position: independent-engineer
follow_up: null
last_touched: "2026-03-01"
tags:
  - job
"""


class TestYAMLEditorGet:
    def test_get_top_level(self):
        editor = YAMLEditor(SAMPLE_YAML)
        assert editor.get("id") == "test-entry"
        assert editor.get("status") == "drafting"

    def test_get_nested(self):
        editor = YAMLEditor(SAMPLE_YAML)
        assert editor.get("target", "organization") == "Acme Corp"
        assert editor.get("fit", "composite") == 8.5

    def test_get_missing_returns_default(self):
        editor = YAMLEditor(SAMPLE_YAML)
        assert editor.get("nonexistent") is None
        assert editor.get("nonexistent", default="fallback") == "fallback"
        assert editor.get("target", "missing", default=42) == 42


class TestYAMLEditorSet:
    def test_set_top_level(self):
        editor = YAMLEditor(SAMPLE_YAML)
        editor.set("status", "staged")
        assert editor.get("status") == "staged"
        result = yaml.safe_load(editor.dump())
        assert result["status"] == "staged"

    def test_set_nested_existing(self):
        editor = YAMLEditor(SAMPLE_YAML)
        editor.set("fit", "composite", 9.2)
        assert editor.get("fit", "composite") == 9.2

    def test_set_creates_intermediates(self):
        editor = YAMLEditor(SAMPLE_YAML)
        editor.set("submission", "variant_ids", "cover_letter", "variants/cover.md")
        result = yaml.safe_load(editor.dump())
        assert result["submission"]["variant_ids"]["cover_letter"] == "variants/cover.md"

    def test_set_new_nested_key(self):
        editor = YAMLEditor(SAMPLE_YAML)
        editor.set("fit", "framing", "independent-engineer")
        result = yaml.safe_load(editor.dump())
        assert result["fit"]["framing"] == "independent-engineer"


class TestYAMLEditorSetdefault:
    def test_setdefault_on_null(self):
        editor = YAMLEditor(SAMPLE_YAML)
        assert editor.setdefault("follow_up", []) is True
        result = yaml.safe_load(editor.dump())
        assert result["follow_up"] == []

    def test_setdefault_on_empty_list(self):
        editor = YAMLEditor(SAMPLE_YAML)
        assert editor.setdefault("submission", "materials_attached", ["resume.pdf"]) is True
        result = yaml.safe_load(editor.dump())
        assert result["submission"]["materials_attached"] == ["resume.pdf"]

    def test_setdefault_on_empty_dict(self):
        editor = YAMLEditor(SAMPLE_YAML)
        assert editor.setdefault("submission", "variant_ids", {"cover_letter": "v.md"}) is True
        result = yaml.safe_load(editor.dump())
        assert result["submission"]["variant_ids"]["cover_letter"] == "v.md"

    def test_setdefault_noop_on_populated(self):
        yaml_with_data = SAMPLE_YAML.replace(
            "materials_attached: []",
            "materials_attached:\n    - existing.pdf",
        )
        editor = YAMLEditor(yaml_with_data)
        assert editor.setdefault("submission", "materials_attached", ["new.pdf"]) is False
        result = yaml.safe_load(editor.dump())
        assert result["submission"]["materials_attached"] == ["existing.pdf"]


class TestYAMLEditorAppendToList:
    def test_append_to_null_list(self):
        editor = YAMLEditor(SAMPLE_YAML)
        editor.append_to_list("follow_up", {"date": "2026-03-05", "channel": "email"})
        result = yaml.safe_load(editor.dump())
        assert len(result["follow_up"]) == 1
        assert result["follow_up"][0]["date"] == "2026-03-05"

    def test_append_to_existing_list(self):
        yaml_with_list = SAMPLE_YAML.replace(
            "follow_up: null",
            "follow_up:\n  - date: '2026-03-01'\n    channel: linkedin",
        )
        editor = YAMLEditor(yaml_with_list)
        editor.append_to_list("follow_up", {"date": "2026-03-05", "channel": "email"})
        result = yaml.safe_load(editor.dump())
        assert len(result["follow_up"]) == 2
        assert result["follow_up"][1]["channel"] == "email"


class TestYAMLEditorTouch:
    def test_touch_sets_today(self):
        from datetime import date

        editor = YAMLEditor(SAMPLE_YAML)
        editor.touch()
        result = yaml.safe_load(editor.dump())
        assert result["last_touched"] == date.today().isoformat()


class TestYAMLEditorRoundTrip:
    def test_preserves_comments(self):
        yaml_with_comment = "# Top comment\nid: test\nstatus: drafting  # inline\n"
        editor = YAMLEditor(yaml_with_comment)
        editor.set("status", "staged")
        output = editor.dump()
        assert "# Top comment" in output
        assert "# inline" in output

    def test_preserves_key_order(self):
        editor = YAMLEditor(SAMPLE_YAML)
        editor.set("status", "staged")
        output = editor.dump()
        id_pos = output.index("id:")
        status_pos = output.index("status:")
        target_pos = output.index("target:")
        assert id_pos < status_pos < target_pos

    def test_dump_validates(self):
        editor = YAMLEditor(SAMPLE_YAML)
        editor.set("status", "staged")
        output = editor.dump()
        # Should not raise
        result = yaml.safe_load(output)
        assert result["status"] == "staged"
