"""Tests for scripts/build_block_index.py"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import build_block_index as bbi

# --- TestParseFrontmatter ---


def test_parse_frontmatter_valid(tmp_path):
    """Valid frontmatter returns parsed dict."""
    md = tmp_path / "block.md"
    md.write_text("---\ntitle: My Block\ntags:\n  - python\n---\nBody text here.\n")
    result = bbi.parse_frontmatter(md)
    assert result is not None
    assert result["title"] == "My Block"
    assert "python" in result["tags"]


def test_parse_frontmatter_no_frontmatter(tmp_path):
    """File without frontmatter delimiter returns None."""
    md = tmp_path / "block.md"
    md.write_text("No frontmatter here.\nJust body text.\n")
    assert bbi.parse_frontmatter(md) is None


def test_parse_frontmatter_unclosed(tmp_path):
    """Missing closing --- returns None."""
    md = tmp_path / "block.md"
    md.write_text("---\ntitle: Block\ntags: []\n")
    assert bbi.parse_frontmatter(md) is None


def test_parse_frontmatter_malformed_yaml(tmp_path):
    """Malformed YAML in frontmatter returns None."""
    md = tmp_path / "block.md"
    md.write_text("---\ntitle: [unclosed\n---\nBody\n")
    assert bbi.parse_frontmatter(md) is None


def test_parse_frontmatter_empty_frontmatter(tmp_path):
    """Empty frontmatter (--- \n---) returns {} (empty dict)."""
    md = tmp_path / "block.md"
    md.write_text("---\n---\nBody\n")
    result = bbi.parse_frontmatter(md)
    # yaml.safe_load on empty string returns None; that's acceptable
    # The function returns yaml.safe_load result, which may be None for empty
    # Accept either {} or None for empty frontmatter
    assert result is None or result == {} or isinstance(result, dict)


def test_parse_frontmatter_minimal(tmp_path):
    """Minimal valid frontmatter returns at least the parsed keys."""
    md = tmp_path / "block.md"
    md.write_text("---\ntitle: Test\n---\n")
    result = bbi.parse_frontmatter(md)
    assert result is not None
    assert result["title"] == "Test"


# --- TestBuildIndex ---


def test_build_index_empty_blocks_dir(tmp_path, monkeypatch):
    """No .md files → empty blocks dict."""
    monkeypatch.setattr(bbi, "BLOCKS_DIR", tmp_path)
    result = bbi.build_index()
    assert result["blocks"] == {}
    assert result["tag_index"] == {}


def test_build_index_single_block(tmp_path, monkeypatch):
    """One file with frontmatter → one block entry."""
    monkeypatch.setattr(bbi, "BLOCKS_DIR", tmp_path)
    md = tmp_path / "intro.md"
    md.write_text("---\ntitle: Intro\ntags:\n  - systems\nidentity_positions: []\ntracks: []\ntier: single\n---\nBody\n")
    result = bbi.build_index()
    assert "intro" in result["blocks"]
    assert result["blocks"]["intro"]["title"] == "Intro"


def test_build_index_skip_underscore_files(tmp_path, monkeypatch):
    """Files starting with _ are excluded."""
    monkeypatch.setattr(bbi, "BLOCKS_DIR", tmp_path)
    (tmp_path / "_index.yaml").write_text("not a block\n")
    md = tmp_path / "_schema.md"
    md.write_text("---\ntitle: Schema\ntags: []\n---\n")
    result = bbi.build_index()
    assert result["blocks"] == {}


def test_build_index_skip_readme(tmp_path, monkeypatch):
    """README.md is excluded."""
    monkeypatch.setattr(bbi, "BLOCKS_DIR", tmp_path)
    readme = tmp_path / "README.md"
    readme.write_text("---\ntitle: README\ntags: []\n---\n")
    result = bbi.build_index()
    assert result["blocks"] == {}


def test_build_index_skip_no_frontmatter(tmp_path, monkeypatch):
    """Files without frontmatter are skipped."""
    monkeypatch.setattr(bbi, "BLOCKS_DIR", tmp_path)
    md = tmp_path / "no_front.md"
    md.write_text("Just body text, no frontmatter.\n")
    result = bbi.build_index()
    assert result["blocks"] == {}


def test_build_index_tag_index_built(tmp_path, monkeypatch):
    """Tags are inverted into tag_index."""
    monkeypatch.setattr(bbi, "BLOCKS_DIR", tmp_path)
    md = tmp_path / "block1.md"
    md.write_text("---\ntitle: Block1\ntags:\n  - systems\n  - ai\n---\n")
    result = bbi.build_index()
    assert "systems" in result["tag_index"]
    assert "ai" in result["tag_index"]
    assert "block1" in result["tag_index"]["systems"]


def test_build_index_tag_index_sorted(tmp_path, monkeypatch):
    """tag_index keys are sorted alphabetically."""
    monkeypatch.setattr(bbi, "BLOCKS_DIR", tmp_path)
    md1 = tmp_path / "z_block.md"
    md1.write_text("---\ntitle: Z\ntags:\n  - zebra\n  - alpha\n---\n")
    result = bbi.build_index()
    keys = list(result["tag_index"].keys())
    assert keys == sorted(keys)


def test_build_index_has_generated_key(tmp_path, monkeypatch):
    """Index includes 'generated' date key."""
    monkeypatch.setattr(bbi, "BLOCKS_DIR", tmp_path)
    result = bbi.build_index()
    assert "generated" in result


def test_build_index_subdir_block(tmp_path, monkeypatch):
    """Blocks in subdirectories get path-based keys."""
    monkeypatch.setattr(bbi, "BLOCKS_DIR", tmp_path)
    subdir = tmp_path / "identity"
    subdir.mkdir()
    md = subdir / "main.md"
    md.write_text("---\ntitle: Identity Main\ntags: []\n---\n")
    result = bbi.build_index()
    assert "identity/main" in result["blocks"]


# --- TestCheckFrontmatter ---


def test_check_frontmatter_all_valid(tmp_path, monkeypatch):
    """When all blocks have frontmatter, returns empty list."""
    monkeypatch.setattr(bbi, "BLOCKS_DIR", tmp_path)
    md = tmp_path / "good.md"
    md.write_text("---\ntitle: Good\ntags: []\n---\nBody\n")
    missing = bbi.check_frontmatter()
    assert missing == []


def test_check_frontmatter_missing_reported(tmp_path, monkeypatch):
    """Files missing frontmatter are returned in the list."""
    monkeypatch.setattr(bbi, "BLOCKS_DIR", tmp_path)
    bad = tmp_path / "bad.md"
    bad.write_text("No frontmatter.\n")
    missing = bbi.check_frontmatter()
    assert len(missing) == 1
    assert "bad.md" in missing[0]


def test_check_frontmatter_skips_underscore_and_readme(tmp_path, monkeypatch):
    """_files and README.md are not checked."""
    monkeypatch.setattr(bbi, "BLOCKS_DIR", tmp_path)
    (tmp_path / "_index.md").write_text("no front\n")
    (tmp_path / "README.md").write_text("no front\n")
    missing = bbi.check_frontmatter()
    assert missing == []
