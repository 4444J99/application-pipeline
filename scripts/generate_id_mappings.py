#!/usr/bin/env python3
"""Generate ID mapping suggestions from filesystem similarity.

Builds:
- profile_id_map: entry_id -> profile_id (for entries lacking direct profile JSON)
- legacy_id_map: legacy_script_name -> entry_id (for scripts lacking direct entry ID match)

Usage:
    python scripts/generate_id_mappings.py
    python scripts/generate_id_mappings.py --write
    python scripts/generate_id_mappings.py --check
"""

from __future__ import annotations

import argparse
import difflib
import re
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pipeline_lib import (
    ALL_PIPELINE_DIRS,
    LEGACY_DIR,
    PROFILES_DIR,
    REPO_ROOT,
    load_entries,
)
from pipeline_lib import LEGACY_ID_MAP as STATIC_LEGACY_ID_MAP
from pipeline_lib import (
    PROFILE_ID_MAP as STATIC_PROFILE_ID_MAP,
)

OUTPUT_PATH = REPO_ROOT / "strategy" / "id-mappings.generated.yaml"


def _tokens(value: str) -> set[str]:
    clean = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    parts = [p for p in clean.split("-") if p and not p.isdigit()]
    return set(parts)


def _similarity(a: str, b: str) -> float:
    seq = difflib.SequenceMatcher(None, a, b).ratio()
    ta = _tokens(a)
    tb = _tokens(b)
    if not ta and not tb:
        return seq
    jaccard = len(ta & tb) / max(1, len(ta | tb))
    return max(seq, jaccard)


def _best_match(source: str, candidates: list[str], threshold: float = 0.45) -> tuple[str | None, float]:
    ranked = sorted(
        ((cand, _similarity(source, cand)) for cand in candidates),
        key=lambda x: x[1],
        reverse=True,
    )
    if not ranked:
        return None, 0.0

    best, score = ranked[0]
    # Skip ambiguous low-confidence matches.
    second_score = ranked[1][1] if len(ranked) > 1 else 0.0
    if score < threshold:
        return None, score
    if score - second_score < 0.05 and second_score >= threshold:
        return None, score
    return best, score


def generate_profile_map() -> dict[str, str]:
    entries = load_entries(dirs=ALL_PIPELINE_DIRS)
    entry_ids = sorted({e.get("id", "") for e in entries if e.get("id")})

    profile_ids = sorted(
        p.stem for p in PROFILES_DIR.glob("*.json")
        if "index" not in p.name
    )

    # Seed with curated canonical overrides when they still resolve.
    result: dict[str, str] = {
        entry_id: profile_id
        for entry_id, profile_id in STATIC_PROFILE_ID_MAP.items()
        if entry_id in entry_ids and profile_id in profile_ids
    }

    for entry_id in entry_ids:
        if entry_id in result:
            continue

        direct = PROFILES_DIR / f"{entry_id}.json"
        if direct.exists():
            continue

        # Prefix fast-path for common suffix variants (e.g., "-2027", "-residency").
        prefix_candidates = [pid for pid in profile_ids if entry_id.startswith(pid)]
        if len(prefix_candidates) == 1:
            result[entry_id] = prefix_candidates[0]
            continue

        match, _score = _best_match(entry_id, profile_ids)
        if match and match != entry_id:
            result[entry_id] = match

    return dict(sorted(result.items()))


def generate_legacy_map() -> dict[str, str]:
    entries = load_entries(dirs=ALL_PIPELINE_DIRS)
    entry_ids = sorted({e.get("id", "") for e in entries if e.get("id")})

    legacy_ids = sorted(
        p.stem for p in LEGACY_DIR.glob("*.md")
        if p.name != "README.md"
    )

    # Seed with curated canonical overrides when they still resolve.
    result: dict[str, str] = {
        legacy_id: entry_id
        for legacy_id, entry_id in STATIC_LEGACY_ID_MAP.items()
        if legacy_id in legacy_ids and entry_id in entry_ids
    }

    for legacy_id in legacy_ids:
        if legacy_id in result:
            continue

        # Direct map already aligned.
        if legacy_id in entry_ids:
            continue

        # Prefix fast-path.
        prefix_candidates = [eid for eid in entry_ids if eid.startswith(legacy_id)]
        if len(prefix_candidates) == 1:
            result[legacy_id] = prefix_candidates[0]
            continue

        match, _score = _best_match(legacy_id, entry_ids)
        if match and match != legacy_id:
            result[legacy_id] = match

    return dict(sorted(result.items()))


def _print_diff(label: str, generated: dict[str, str], existing: dict[str, str]) -> int:
    missing = sorted(set(existing) - set(generated))
    extra = sorted(set(generated) - set(existing))
    changed = sorted(k for k in set(generated) & set(existing) if generated[k] != existing[k])

    if not (missing or extra or changed):
        print(f"{label}: OK (generated matches existing map)")
        return 0

    print(f"{label}: differences detected")
    for key in missing:
        print(f"  MISSING: {key} -> {existing[key]}")
    for key in extra:
        print(f"  EXTRA:   {key} -> {generated[key]}")
    for key in changed:
        print(f"  CHANGED: {key}: existing={existing[key]} generated={generated[key]}")
    return 1


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate ID mapping suggestions")
    parser.add_argument("--write", action="store_true", help="Write generated mappings to strategy/id-mappings.generated.yaml")
    parser.add_argument("--output", default=str(OUTPUT_PATH), help="Output path for --write")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Exit non-zero if canonical static mappings drift from generated canonical mappings",
    )
    parser.add_argument(
        "--strict-check",
        action="store_true",
        help="When used with --check, compare full generated maps (including extra suggestions)",
    )
    args = parser.parse_args()

    profile_map = generate_profile_map()
    legacy_map = generate_legacy_map()

    payload = {
        "generated": Path(args.output).name,
        "profile_id_map": profile_map,
        "legacy_id_map": legacy_map,
    }

    print(f"Generated profile mappings: {len(profile_map)}")
    print(f"Generated legacy mappings:  {len(legacy_map)}")

    if args.check:
        failures = 0
        if args.strict_check:
            profile_check_map = profile_map
            legacy_check_map = legacy_map
        else:
            profile_check_map = {k: v for k, v in profile_map.items() if k in STATIC_PROFILE_ID_MAP}
            legacy_check_map = {k: v for k, v in legacy_map.items() if k in STATIC_LEGACY_ID_MAP}
            extra_profiles = sorted(set(profile_map) - set(STATIC_PROFILE_ID_MAP))
            extra_legacy = sorted(set(legacy_map) - set(STATIC_LEGACY_ID_MAP))
            if extra_profiles:
                print(
                    f"INFO: {len(extra_profiles)} additional profile suggestions "
                    "(ignored in canonical --check; use --strict-check to enforce exact match)"
                )
            if extra_legacy:
                print(
                    f"INFO: {len(extra_legacy)} additional legacy suggestions "
                    "(ignored in canonical --check; use --strict-check to enforce exact match)"
                )

        failures += _print_diff("PROFILE_ID_MAP", profile_check_map, STATIC_PROFILE_ID_MAP)
        failures += _print_diff("LEGACY_ID_MAP", legacy_check_map, STATIC_LEGACY_ID_MAP)
        if failures:
            raise SystemExit(1)

    if args.write:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(yaml.dump(payload, default_flow_style=False, sort_keys=False, allow_unicode=True))
        print(f"Wrote: {output.relative_to(REPO_ROOT)}")
    else:
        print(yaml.dump(payload, default_flow_style=False, sort_keys=False, allow_unicode=True))


if __name__ == "__main__":
    main()
