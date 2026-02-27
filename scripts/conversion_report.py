#!/usr/bin/env python3
"""Analyze conversion rates by track, identity position, and framing."""

import sys

from pipeline_lib import (
    SIGNALS_DIR, ALL_PIPELINE_DIRS, ALL_PIPELINE_DIRS_WITH_POOL,
    PIPELINE_DIR_RESEARCH_POOL, load_entries,
)

CONVERSION_LOG = SIGNALS_DIR / "conversion-log.yaml"


def analyze_by_dimension(entries: list[dict], dimension: str, extract_fn) -> dict:
    """Analyze outcomes grouped by a dimension."""
    groups: dict[str, dict] = {}

    for entry in entries:
        key = extract_fn(entry)
        if key is None:
            continue

        if key not in groups:
            groups[key] = {"total": 0, "submitted": 0, "outcomes": 0,
                           "accepted": 0, "rejected": 0, "pending": 0}

        groups[key]["total"] += 1

        status = entry.get("status", "")
        if status in ("submitted", "acknowledged", "interview", "outcome"):
            groups[key]["submitted"] += 1

        outcome = entry.get("outcome")
        if outcome:
            groups[key]["outcomes"] += 1
            if outcome == "accepted":
                groups[key]["accepted"] += 1
            elif outcome == "rejected":
                groups[key]["rejected"] += 1
        elif status in ("submitted", "acknowledged", "interview"):
            groups[key]["pending"] += 1

    return groups


def print_report(title: str, groups: dict):
    """Print a conversion analysis report."""
    print(f"\n{title}")
    print("-" * len(title))

    if not groups:
        print("  No data available.")
        return

    for key, stats in sorted(groups.items(), key=lambda x: -x[1]["total"]):
        total = stats["total"]
        submitted = stats["submitted"]
        accepted = stats["accepted"]
        outcomes = stats["outcomes"]

        rate = f"{accepted}/{outcomes} ({100*accepted/outcomes:.0f}%)" if outcomes > 0 else "no outcomes yet"
        print(f"\n  {key}:")
        print(f"    Pipeline: {total} | Submitted: {submitted} | Outcomes: {outcomes}")
        print(f"    Conversion: {rate}")


def response_time_analysis(entries: list[dict]):
    """Analyze response times by portal type and identity position."""
    from datetime import date
    from pipeline_lib import parse_date

    print("\nRESPONSE TIME ANALYSIS")
    print("-" * 40)

    # Collect entries with response time data
    by_portal: dict[str, list[int]] = {}
    by_position: dict[str, list[int]] = {}
    all_times = []

    for entry in entries:
        conversion = entry.get("conversion", {})
        if not isinstance(conversion, dict):
            continue

        ttr = conversion.get("time_to_response_days")
        if not ttr or not isinstance(ttr, (int, float)) or ttr <= 0:
            continue

        ttr = int(ttr)
        all_times.append(ttr)

        # By portal
        target = entry.get("target", {})
        portal = target.get("portal", "unknown") if isinstance(target, dict) else "unknown"
        by_portal.setdefault(portal, []).append(ttr)

        # By identity position
        fit = entry.get("fit", {})
        position = fit.get("identity_position", "unset") if isinstance(fit, dict) else "unset"
        by_position.setdefault(position, []).append(ttr)

    if not all_times:
        # Show entries waiting without response
        waiting = []
        for entry in entries:
            status = entry.get("status", "")
            if status not in ("submitted", "acknowledged"):
                continue
            timeline = entry.get("timeline", {})
            sub_date = parse_date(timeline.get("submitted")) if isinstance(timeline, dict) else None
            if sub_date:
                days_waiting = (date.today() - sub_date).days
                waiting.append((days_waiting, entry))

        if waiting:
            waiting.sort(key=lambda x: -x[0])
            print(f"  No response time data yet. {len(waiting)} entries awaiting response:")
            for days, e in waiting[:5]:
                name = e.get("name", e.get("id", "?"))
                target = e.get("target", {})
                portal = target.get("portal", "?") if isinstance(target, dict) else "?"
                print(f"    {name} — {days}d waiting [{portal}]")
                # Flag entries exceeding typical window
                if days > 21:
                    print(f"      !! Exceeds typical response window")
        else:
            print("  No response time data recorded yet.")
        return

    # Overall stats
    avg = sum(all_times) / len(all_times)
    sorted_times = sorted(all_times)
    median = sorted_times[len(sorted_times) // 2]
    print(f"\n  Overall ({len(all_times)} responses):")
    print(f"    Mean: {avg:.1f}d | Median: {median}d | Min: {min(all_times)}d | Max: {max(all_times)}d")

    # By portal
    if len(by_portal) > 1 or (by_portal and list(by_portal.keys())[0] != "unknown"):
        print(f"\n  By Portal Type:")
        for portal, times in sorted(by_portal.items(), key=lambda x: -len(x[1])):
            p_avg = sum(times) / len(times)
            print(f"    {portal:<20s} n={len(times):>3d}  mean={p_avg:.1f}d")

    # By identity position
    if len(by_position) > 1 or (by_position and list(by_position.keys())[0] != "unset"):
        print(f"\n  By Identity Position:")
        for position, times in sorted(by_position.items(), key=lambda x: -len(x[1])):
            p_avg = sum(times) / len(times)
            print(f"    {position:<25s} n={len(times):>3d}  mean={p_avg:.1f}d")


def main():
    # Operational entries for conversion rate calculations
    operational = load_entries(dirs=ALL_PIPELINE_DIRS)
    # Research pool entries (reported separately)
    pool = load_entries(dirs=[PIPELINE_DIR_RESEARCH_POOL])

    if not operational and not pool:
        print("No pipeline entries found.")
        sys.exit(1)

    print("=" * 60)
    print("CONVERSION REPORT")
    print("=" * 60)
    print(f"\nOperational pipeline entries: {len(operational)}")
    print(f"Research pool: {len(pool)} (not included in conversion rates)")

    # Overall stats (operational only — pool entries haven't been submitted)
    entries = operational
    submitted = sum(1 for e in entries if e.get("status") in ("submitted", "acknowledged", "interview", "outcome"))
    with_outcome = sum(1 for e in entries if e.get("outcome"))
    accepted = sum(1 for e in entries if e.get("outcome") == "accepted")

    print(f"Submitted: {submitted}")
    print(f"With outcome: {with_outcome}")
    if with_outcome:
        print(f"Accepted: {accepted}/{with_outcome} ({100*accepted/with_outcome:.0f}%)")
    else:
        print("Accepted: no outcomes yet")

    # By track
    by_track = analyze_by_dimension(
        entries, "track", lambda e: e.get("track"))
    print_report("BY TRACK", by_track)

    # By identity position
    by_position = analyze_by_dimension(
        entries, "identity_position",
        lambda e: e.get("fit", {}).get("identity_position") if isinstance(e.get("fit"), dict) else None)
    print_report("BY IDENTITY POSITION", by_position)

    # By fit score bracket
    def score_bracket(entry):
        fit = entry.get("fit", {})
        if not isinstance(fit, dict):
            return None
        score = fit.get("score")
        if score is None:
            return None
        if score >= 9:
            return "9-10 (excellent)"
        if score >= 7:
            return "7-8 (good)"
        if score >= 5:
            return "5-6 (moderate)"
        return "1-4 (low)"

    by_score = analyze_by_dimension(entries, "fit score", score_bracket)
    print_report("BY FIT SCORE", by_score)

    # Response time analysis
    response_time_analysis(entries)

    print()


if __name__ == "__main__":
    main()
