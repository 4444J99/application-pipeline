"""Tests for scripts/generate_project_blocks.py naming and filtering helpers."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from generate_project_blocks import relevance_level, repo_to_block_name, should_skip


def test_repo_to_block_name_uses_override_when_present():
    assert repo_to_block_name("recursive-engine--generative-entity") == "recursive-engine"


def test_repo_to_block_name_normalizes_repeated_and_trailing_dashes():
    assert repo_to_block_name("my-repo---") == "my-repo"


def test_relevance_level_extracts_tier_prefix():
    assert relevance_level("HIGH - excellent fit") == "HIGH"
    assert relevance_level("") == "NONE"


def test_should_skip_matches_archive_and_infrastructure_rules():
    assert should_skip({"tier": "infrastructure", "implementation_status": "ACTIVE"}) == "infrastructure tier"
    assert should_skip({"tier": "archive", "implementation_status": "ACTIVE"}) == "archive tier"
    assert should_skip({"tier": "standard", "implementation_status": "ARCHIVED"}) == "archived status"
    assert should_skip({"tier": "standard", "implementation_status": "ACTIVE"}) is None
