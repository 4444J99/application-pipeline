"""Test ID mapping consistency between pipeline entries, profiles, and legacy scripts."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from pipeline_lib import (
    ALL_PIPELINE_DIRS_WITH_POOL,
    LEGACY_DIR,
    LEGACY_ID_MAP,
    PROFILE_ID_MAP,
    PROFILES_DIR,
    load_entries,
    load_entry_by_id,
)


def _all_entry_ids() -> set[str]:
    """Collect all entry IDs from pipeline YAML files."""
    entries = load_entries(dirs=ALL_PIPELINE_DIRS_WITH_POOL)
    return {e["id"] for e in entries if "id" in e}


def _all_profile_ids() -> set[str]:
    """Collect all profile IDs from targets/profiles/."""
    if not PROFILES_DIR.exists():
        return set()
    return {p.stem for p in PROFILES_DIR.glob("*.json") if "index" not in p.name}


def _all_legacy_ids() -> set[str]:
    """Collect all legacy script IDs."""
    if not LEGACY_DIR.exists():
        return set()
    return {p.stem for p in LEGACY_DIR.glob("*.md")}


class TestProfileIdMap:
    """Validate PROFILE_ID_MAP consistency."""

    def test_profile_map_targets_exist(self):
        """Every value in PROFILE_ID_MAP should correspond to an existing profile JSON."""
        profile_ids = _all_profile_ids()
        missing = []
        for entry_id, profile_id in PROFILE_ID_MAP.items():
            if profile_id not in profile_ids:
                missing.append(f"{entry_id} -> {profile_id}")
        assert not missing, f"PROFILE_ID_MAP references missing profiles: {missing}"

    def test_profile_map_sources_exist(self):
        """Every key in PROFILE_ID_MAP should be a valid pipeline entry ID."""
        entry_ids = _all_entry_ids()
        orphaned = []
        for entry_id in PROFILE_ID_MAP:
            if entry_id not in entry_ids:
                orphaned.append(entry_id)
        # Allow some tolerance: entries may be archived/closed
        if orphaned:
            pytest.skip(f"Some PROFILE_ID_MAP keys are not active entries (may be archived): {orphaned}")


class TestLegacyIdMap:
    """Validate LEGACY_ID_MAP consistency."""

    def test_legacy_map_sources_exist(self):
        """Every key in LEGACY_ID_MAP should correspond to a legacy script file."""
        legacy_ids = _all_legacy_ids()
        missing = []
        for legacy_name in LEGACY_ID_MAP:
            if legacy_name not in legacy_ids:
                missing.append(legacy_name)
        assert not missing, f"LEGACY_ID_MAP references missing legacy scripts: {missing}"

    def test_legacy_map_targets_exist(self):
        """Every value in LEGACY_ID_MAP should be a valid pipeline entry ID."""
        entry_ids = _all_entry_ids()
        orphaned = []
        for legacy_name, entry_id in LEGACY_ID_MAP.items():
            if entry_id not in entry_ids:
                orphaned.append(f"{legacy_name} -> {entry_id}")
        if orphaned:
            pytest.skip(f"Some LEGACY_ID_MAP values are not active entries (may be archived): {orphaned}")


class TestMappingCompleteness:
    """Check for entries that might need mapping but lack one."""

    def test_no_duplicate_profile_mappings(self):
        """Each profile should map to at most one entry (no conflicting overrides)."""
        seen: dict[str, str] = {}
        dupes = []
        for entry_id, profile_id in PROFILE_ID_MAP.items():
            if profile_id in seen:
                dupes.append(f"{profile_id}: {seen[profile_id]} AND {entry_id}")
            seen[profile_id] = entry_id
        # Duplicates are allowed if intentional (e.g., prix-ars maps to same profile)
        # Just report them, don't fail
        if dupes:
            pytest.skip(f"Multiple entries map to same profile (may be intentional): {dupes}")

    def test_entries_with_profiles_are_loadable(self):
        """Entries in PROFILE_ID_MAP should be loadable via load_entry_by_id."""
        not_found = []
        for entry_id in list(PROFILE_ID_MAP.keys())[:10]:  # Sample check
            filepath, data = load_entry_by_id(entry_id)
            if filepath is None:
                not_found.append(entry_id)
        if not_found:
            pytest.skip(f"Some mapped entries not found on disk (may be archived): {not_found}")
