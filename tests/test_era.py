"""Tests for era derivation (Tier 4J)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from pipeline_lib import PRECISION_PIVOT_DATE, get_entry_era


class TestGetEntryEra:
    def test_get_entry_era_volume(self):
        """Entry submitted before pivot date is 'volume' era."""
        entry = {"timeline": {"submitted": "2026-03-01"}}
        assert get_entry_era(entry) == "volume"

    def test_get_entry_era_precision(self):
        """Entry submitted after pivot date is 'precision' era."""
        entry = {"timeline": {"submitted": "2026-03-10"}}
        assert get_entry_era(entry) == "precision"

    def test_get_entry_era_pivot_date_is_precision(self):
        """Entry submitted on pivot date is 'precision' era."""
        entry = {"timeline": {"submitted": PRECISION_PIVOT_DATE}}
        assert get_entry_era(entry) == "precision"

    def test_get_entry_era_no_submission(self):
        """Entry without submission date defaults to 'precision'."""
        entry = {"timeline": {"researched": "2026-02-01"}}
        assert get_entry_era(entry) == "precision"

    def test_get_entry_era_no_timeline(self):
        """Entry without timeline defaults to 'precision'."""
        entry = {"id": "test"}
        assert get_entry_era(entry) == "precision"

    def test_get_entry_era_quoted_date(self):
        """Entry with quoted date string is handled correctly."""
        entry = {"timeline": {"submitted": '"2026-03-01"'}}
        assert get_entry_era(entry) == "volume"
