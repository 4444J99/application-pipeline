"""Tests for material_builder.py — LLM-powered material generation."""

import sys
from dataclasses import asdict
from pathlib import Path
from unittest.mock import patch

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from material_builder import (
    RESUME_MAP,
    BuildResult,
    MaterialDraft,
    _log_build_result,
    _save_draft,
    build_materials,
    generate_cover_letter,
    select_blocks_for_entry,
    wire_resume,
)


class TestDataclasses:
    def test_build_result_fields(self):
        r = BuildResult(
            entries_processed=["a"],
            cover_letters_generated=1,
            answers_generated=0,
            resumes_wired=1,
            blocks_selected=3,
            errors=[],
        )
        assert r.cover_letters_generated == 1

    def test_material_draft_fields(self):
        d = MaterialDraft(
            entry_id="test",
            component="cover_letter",
            content="Dear...",
            status="draft",
            generated_at="2026-03-14T10:00:00",
            model_used="gemini-2.5-pro",
            identity_position="independent-engineer",
        )
        assert d.status == "draft"

    def test_build_result_serializes(self):
        r = BuildResult()
        d = asdict(r)
        assert "cover_letters_generated" in d

    def test_default_factory(self):
        r = BuildResult()
        assert r.entries_processed == []
        assert r.errors == []


class TestSelectBlocks:
    def test_selects_blocks_for_identity(self):
        """Selects blocks matching identity position."""
        entry = {
            "id": "test-co",
            "identity_position": "independent-engineer",
            "target": {"organization": "TestCo"},
        }
        with patch("material_builder.load_block") as mock_load:
            mock_load.return_value = "Block content"
            result = select_blocks_for_entry(entry)
            assert isinstance(result, dict)
            assert len(result) > 0

    def test_returns_empty_for_no_blocks_dir(self, monkeypatch):
        """Returns empty dict when blocks directory doesn't exist."""
        monkeypatch.setattr("material_builder.BLOCKS_DIR", Path("/nonexistent"))
        entry = {"id": "test", "identity_position": "independent-engineer"}
        result = select_blocks_for_entry(entry)
        assert result == {}

    def test_uses_correct_position_slots(self):
        """Systems-artist gets different slots than engineer."""
        entry_artist = {"id": "art", "identity_position": "systems-artist"}
        entry_eng = {"id": "eng", "identity_position": "independent-engineer"}
        with patch("material_builder.load_block", return_value="content"):
            artist_blocks = select_blocks_for_entry(entry_artist)
            eng_blocks = select_blocks_for_entry(entry_eng)
            # Engineer has methodology slot, artist doesn't
            assert "methodology" in eng_blocks
            assert "methodology" not in artist_blocks

    def test_skips_missing_blocks(self):
        """Slots with missing block files are excluded."""
        entry = {"id": "test", "identity_position": "independent-engineer"}
        call_count = [0]

        def mock_load(path):
            call_count[0] += 1
            return "content" if call_count[0] <= 2 else None

        with patch("material_builder.load_block", side_effect=mock_load):
            result = select_blocks_for_entry(entry)
            assert len(result) == 2


class TestGenerateCoverLetter:
    def test_generates_from_blocks(self):
        """Cover letter generation produces non-empty string."""
        with patch("material_builder._call_llm") as mock_llm:
            mock_llm.return_value = "Dear Hiring Manager, I bring 113 repositories..."
            entry = {
                "id": "test-co",
                "identity_position": "independent-engineer",
                "target": {"organization": "TestCo", "title": "Engineer"},
            }
            result = generate_cover_letter(entry, ["Block content here"], "Job posting text")
            assert len(result) > 0
            mock_llm.assert_called_once()

    def test_fallback_when_no_llm(self):
        """Falls back to template cover letter when LLM unavailable."""
        with patch("material_builder._call_llm", side_effect=ImportError("no genai")):
            entry = {
                "id": "test",
                "identity_position": "independent-engineer",
                "target": {"organization": "Co", "title": "Eng"},
            }
            result = generate_cover_letter(entry, ["Block"], "Posting")
            # Template fallback produces a real cover letter, not a prompt
            assert "Co" in result
            assert "Sincerely" in result or "Dear" in result

    def test_includes_identity_in_prompt(self):
        """System prompt includes identity position."""
        captured = {}

        def mock_llm(system, user):
            captured["system"] = system
            return "Generated letter"

        with patch("material_builder._call_llm", side_effect=mock_llm):
            entry = {
                "id": "test",
                "identity_position": "systems-artist",
                "target": {"organization": "Gallery", "title": "Artist"},
            }
            generate_cover_letter(entry, ["Block"], "Posting")
            assert "systems-artist" in captured["system"]


class TestWireResume:
    def test_selects_base_for_identity(self):
        """Selects correct base resume for identity position."""
        result = wire_resume("independent-engineer")
        assert "independent-engineer" in result

    def test_each_position_has_resume(self):
        """All 5 identity positions map to resume paths."""
        for position in [
            "independent-engineer",
            "systems-artist",
            "educator",
            "creative-technologist",
            "community-practitioner",
        ]:
            result = wire_resume(position)
            assert position in result

    def test_unknown_position_fallback(self):
        """Unknown position falls back to independent-engineer."""
        result = wire_resume("unknown-position")
        assert result == RESUME_MAP["independent-engineer"]


class TestSaveDraft:
    def test_dry_run_returns_none(self):
        """Dry run doesn't write files."""
        draft = MaterialDraft(
            entry_id="test",
            component="cover_letter",
            content="content",
            status="draft",
            generated_at="2026-03-14",
            model_used="test",
            identity_position="independent-engineer",
        )
        assert _save_draft(draft, dry_run=True) is None

    def test_writes_file(self, tmp_path, monkeypatch):
        """Non-dry-run writes file with frontmatter."""
        monkeypatch.setattr("material_builder.DRAFTS_DIR", tmp_path)
        draft = MaterialDraft(
            entry_id="test-co",
            component="cover_letter",
            content="Dear Hiring Manager...",
            status="draft",
            generated_at="2026-03-14T10:00:00",
            model_used="gemini-2.5-pro",
            identity_position="independent-engineer",
        )
        path = _save_draft(draft, dry_run=False)
        assert path is not None
        assert path.exists()
        content = path.read_text()
        assert "entry_id: test-co" in content
        assert "Dear Hiring Manager" in content


class TestBuildMaterials:
    def test_dry_run_no_writes(self):
        """Dry run processes but doesn't write."""
        with patch("material_builder._load_buildable_entries", return_value=[]):
            result = build_materials(dry_run=True)
            assert isinstance(result, BuildResult)
            assert result.entries_processed == []

    def test_processes_qualified_entries(self):
        """Processes entries with qualified status missing materials."""
        entry = {
            "id": "test-co",
            "status": "qualified",
            "identity_position": "independent-engineer",
            "target": {"organization": "TestCo", "title": "Eng"},
            "submission": {},
        }
        with patch("material_builder._load_buildable_entries", return_value=[entry]), \
             patch("material_builder.select_blocks_for_entry", return_value={"identity": "identity/2min"}), \
             patch("material_builder.load_block", return_value="Block content"), \
             patch("material_builder.generate_cover_letter", return_value="Dear..."):
            result = build_materials(dry_run=True)
            assert len(result.entries_processed) == 1
            assert result.cover_letters_generated == 1
            assert result.resumes_wired == 1

    def test_component_filter(self):
        """components parameter limits what gets built."""
        entry = {
            "id": "test",
            "status": "qualified",
            "identity_position": "independent-engineer",
            "target": {"organization": "Co", "title": "Eng"},
            "submission": {},
        }
        with patch("material_builder._load_buildable_entries", return_value=[entry]), \
             patch("material_builder.select_blocks_for_entry", return_value={}):
            result = build_materials(dry_run=True, components=["resume"])
            assert result.resumes_wired == 1
            assert result.cover_letters_generated == 0

    def test_handles_errors_gracefully(self):
        """Entry errors are captured, not raised."""
        entry = {
            "id": "bad-entry",
            "status": "qualified",
            "identity_position": "independent-engineer",
            "target": {"organization": "Co", "title": "Eng"},
            "submission": {},
        }
        with patch("material_builder._load_buildable_entries", return_value=[entry]), \
             patch("material_builder.select_blocks_for_entry", side_effect=Exception("boom")):
            result = build_materials(dry_run=True)
            assert len(result.errors) == 1
            assert "bad-entry" in result.errors[0]


class TestBuildHistory:
    def test_log_entry_format(self, tmp_path):
        """Build history log has expected fields."""
        log_path = tmp_path / "build-history.yaml"
        result = BuildResult(
            entries_processed=["a"],
            cover_letters_generated=1,
            resumes_wired=1,
        )
        _log_build_result(result, log_path)
        entries = yaml.safe_load(log_path.read_text())
        assert len(entries) == 1
        assert entries[0]["cover_letters"] == 1
        assert "date" in entries[0]
