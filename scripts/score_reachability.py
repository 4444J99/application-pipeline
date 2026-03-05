"""Reachability and staged triage helpers extracted from score.py."""

from __future__ import annotations

_NETWORK_LEVELS = [
    ("acquaintance", 4),
    ("warm", 7),
    ("strong", 9),
    ("internal", 10),
]


def analyze_reachability(
    entry: dict,
    all_entries: list[dict] | None = None,
    threshold: float = 9.0,
    *,
    compute_dimensions,
    compute_composite,
) -> dict:
    """Per-entry gap analysis for network-based score lift scenarios."""
    entry_id = entry.get("id", "unknown")
    track = entry.get("track", "")
    dims = compute_dimensions(entry, all_entries)
    current_composite = compute_composite(dims, track)
    current_network = dims.get("network_proximity", 1)

    scenarios = []
    reachable_with = None
    for level_name, level_score in _NETWORK_LEVELS:
        if level_score <= current_network:
            continue
        test_dims = dict(dims)
        test_dims["network_proximity"] = level_score
        scenario_composite = compute_composite(test_dims, track)
        scenarios.append(
            {
                "level": level_name,
                "network_score": level_score,
                "composite": scenario_composite,
                "delta": round(scenario_composite - current_composite, 1),
                "crosses_threshold": scenario_composite >= threshold,
            }
        )
        if scenario_composite >= threshold and reachable_with is None:
            reachable_with = level_name

    return {
        "entry_id": entry_id,
        "current_composite": current_composite,
        "current_network": current_network,
        "threshold": threshold,
        "scenarios": scenarios,
        "reachable_with": reachable_with,
    }


def run_reachable(
    threshold: float = 9.0,
    *,
    load_entries_raw,
    all_pipeline_dirs_with_pool,
    analyze_reachability_fn,
):
    """Display reachability for actionable entries, grouped by outcome."""
    entries_raw = load_entries_raw(dirs=all_pipeline_dirs_with_pool)
    actionable = [e for e in entries_raw if e.get("status") in {"research", "qualified", "drafting", "staged"}]

    if not actionable:
        print("No actionable entries found.")
        return {"total_actionable": 0, "above": 0, "reachable": 0, "unreachable": 0, "threshold": threshold}

    reachable = []
    unreachable = []
    already_above = []

    for entry in actionable:
        result = analyze_reachability_fn(entry, entries_raw, threshold)
        if result["current_composite"] >= threshold:
            already_above.append(result)
        elif result["reachable_with"]:
            reachable.append(result)
        else:
            unreachable.append(result)

    print(f"REACHABILITY ANALYSIS (threshold: {threshold})")
    print("=" * 60)

    if already_above:
        print(f"\nALREADY ABOVE {threshold} ({len(already_above)}):")
        for row in sorted(already_above, key=lambda item: item["current_composite"], reverse=True):
            print(f"  {row['entry_id']:<40s} {row['current_composite']:>5.1f}  (network={row['current_network']})")

    if reachable:
        print(f"\nREACHABLE WITH NETWORK ({len(reachable)}):")
        for row in sorted(reachable, key=lambda item: item["current_composite"], reverse=True):
            best = row["reachable_with"]
            best_scenario = next(s for s in row["scenarios"] if s["level"] == best)
            print(
                f"  {row['entry_id']:<40s} {row['current_composite']:>5.1f} -> {best_scenario['composite']:.1f}  "
                f"(need {best}, +{best_scenario['delta']:.1f})"
            )

    if unreachable:
        print(f"\nUNREACHABLE EVEN WITH INTERNAL ({len(unreachable)}):")
        for row in sorted(unreachable, key=lambda item: item["current_composite"], reverse=True):
            max_scenario = row["scenarios"][-1] if row["scenarios"] else None
            max_str = f" -> {max_scenario['composite']:.1f} at internal" if max_scenario else ""
            print(f"  {row['entry_id']:<40s} {row['current_composite']:>5.1f}{max_str}")

    print(f"\n{'=' * 60}")
    print(f"Total: {len(already_above)} above | {len(reachable)} reachable | {len(unreachable)} unreachable")
    return {
        "total_actionable": len(actionable),
        "above": len(already_above),
        "reachable": len(reachable),
        "unreachable": len(unreachable),
        "threshold": threshold,
    }


def run_triage_staged(
    dry_run: bool = True,
    yes: bool = False,
    submit_threshold: float = 8.5,
    demote_threshold: float = 7.0,
    *,
    load_entries_raw,
    all_pipeline_dirs_with_pool,
    compute_dimensions,
    compute_composite,
    analyze_reachability_fn,
    update_yaml_field,
    update_last_touched,
    atomic_write,
):
    """One-time triage: categorize staged entries into submit_ready / hold / demote."""
    if not dry_run and not yes:
        dry_run = True
        print("(Defaulting to dry-run. Use --yes to execute.)\n")

    entries_raw = load_entries_raw(dirs=all_pipeline_dirs_with_pool, include_filepath=True)
    staged = [e for e in entries_raw if e.get("status") == "staged"]

    if not staged:
        print("No staged entries found.")
        return {
            "total_staged": 0,
            "submit_ready": 0,
            "hold": 0,
            "demote": 0,
            "dry_run": dry_run,
            "submit_threshold": submit_threshold,
            "demote_threshold": demote_threshold,
        }

    all_raw = load_entries_raw(dirs=all_pipeline_dirs_with_pool)

    submit_ready = []
    hold = []
    demote_list = []

    for entry in staged:
        entry_id = entry.get("id", "unknown")
        filepath = entry.get("_filepath")
        dims = compute_dimensions(entry, all_raw)
        track = entry.get("track", "")
        composite = compute_composite(dims, track)
        network = dims.get("network_proximity", 1)

        if composite >= submit_threshold and network >= 7:
            submit_ready.append((entry_id, composite, network, filepath))
        elif composite < demote_threshold:
            demote_list.append((entry_id, composite, network, filepath))
        else:
            reachability = analyze_reachability_fn(entry, all_raw)
            hold.append((entry_id, composite, network, reachability, filepath))

    print(f"TRIAGE STAGED ENTRIES ({len(staged)} total)")
    print("=" * 60)

    if submit_ready:
        print(f"\nSUBMIT-READY (score >= {submit_threshold}, network >= 7): {len(submit_ready)}")
        for entry_id, score, network, _ in sorted(submit_ready, key=lambda item: item[1], reverse=True):
            print(f"  {entry_id:<40s} {score:>5.1f}  network={network}")

    if hold:
        print(f"\nHOLD — cultivate network ({demote_threshold} <= score < {submit_threshold}): {len(hold)}")
        for entry_id, score, network, reach, _ in sorted(hold, key=lambda item: item[1], reverse=True):
            hint = f"need {reach['reachable_with']}" if reach.get("reachable_with") else "unreachable"
            print(f"  {entry_id:<40s} {score:>5.1f}  network={network}  ({hint})")

    if demote_list:
        print(f"\nDEMOTE to qualified (score < {demote_threshold}): {len(demote_list)}")
        for entry_id, score, network, _filepath in sorted(demote_list, key=lambda item: item[1]):
            action = "[dry-run] " if dry_run else ""
            print(f"  {action}{entry_id:<40s} {score:>5.1f}  network={network}")

    if demote_list and not dry_run:
        for entry_id, _score, _network, filepath in demote_list:
            if filepath:
                content = filepath.read_text()
                content = update_yaml_field(content, "status", "qualified")
                content = update_last_touched(content)
                atomic_write(filepath, content)
                print(f"  Demoted {entry_id} to qualified")

    print(f"\n{'=' * 60}")
    label = " (dry-run)" if dry_run else ""
    print(f"Submit-ready: {len(submit_ready)} | Hold: {len(hold)} | Demote: {len(demote_list)}{label}")
    return {
        "total_staged": len(staged),
        "submit_ready": len(submit_ready),
        "hold": len(hold),
        "demote": len(demote_list),
        "dry_run": dry_run,
        "submit_threshold": submit_threshold,
        "demote_threshold": demote_threshold,
    }
