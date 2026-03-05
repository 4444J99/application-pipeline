#!/usr/bin/env python3
"""Monthly velocity report: submissions, conversions, block ROI, hypothesis accuracy.

Analyzes conversion-log.yaml to generate actionable insights about pipeline
performance, composition methods, block effectiveness, and hypothesis validation.

Usage:
    python scripts/velocity_report.py                  # This month
    python scripts/velocity_report.py --month 2        # Last 2 months
    python scripts/velocity_report.py --save           # Save to strategy/
"""

import argparse
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import yaml
from pipeline_lib import SIGNALS_DIR


def load_conversion_log() -> list[dict]:
    """Load conversion-log.yaml."""
    log_path = SIGNALS_DIR / "conversion-log.yaml"
    if not log_path.exists():
        return []
    
    with open(log_path) as f:
        data = yaml.safe_load(f) or []
    if isinstance(data, dict):
        entries = data.get("entries", [])
        return entries if isinstance(entries, list) else []
    return data if isinstance(data, list) else []


def load_hypotheses() -> list[dict]:
    """Load hypotheses.yaml."""
    hyp_path = SIGNALS_DIR / "hypotheses.yaml"
    if not hyp_path.exists():
        return []
    
    with open(hyp_path) as f:
        data = yaml.safe_load(f) or []
    if isinstance(data, dict):
        hypotheses = data.get("hypotheses", [])
        return hypotheses if isinstance(hypotheses, list) else []
    return data if isinstance(data, list) else []


def filter_by_date_range(entries: list[dict], months: int = 1) -> list[dict]:
    """Filter entries submitted within last N months."""
    if not months:
        return entries
    
    cutoff_date = datetime.now() - timedelta(days=30 * months)
    filtered = []
    
    for entry in entries:
        date_str = entry.get("submission_date") or entry.get("submitted")
        if not date_str:
            continue
        
        try:
            entry_date = datetime.strptime(date_str, "%Y-%m-%d")
            if entry_date >= cutoff_date:
                filtered.append(entry)
        except (ValueError, TypeError) as e:
            print(f"  Warning: Invalid date format for entry {entry.get('id', 'unknown')}: {e}")
    
    return filtered


def calculate_metrics(entries: list[dict]) -> dict:
    """Calculate conversion and composition metrics."""
    if not entries:
        return {
            "total_submissions": 0,
            "conversions": 0,
            "conversion_rate": 0.0,
            "by_outcome": {},
            "by_composition_method": {},
            "by_position": {},
            "by_channel": {},
        }
    
    # Overall metrics
    conversions = sum(1 for e in entries if e.get("outcome") == "accepted")
    total = len(entries)
    
    # By outcome
    outcomes = defaultdict(int)
    for e in entries:
        outcome = e.get("outcome", "pending")
        outcomes[outcome] += 1
    
    # By composition method
    methods = defaultdict(lambda: {"submissions": 0, "conversions": 0})
    for e in entries:
        method = e.get("composition_method", "unknown")
        methods[method]["submissions"] += 1
        if e.get("outcome") == "accepted":
            methods[method]["conversions"] += 1
    
    method_rates = {
        method: round(data["conversions"] / data["submissions"], 3) if data["submissions"] > 0 else 0
        for method, data in methods.items()
    }
    
    # By identity position
    positions = defaultdict(lambda: {"submissions": 0, "conversions": 0})
    for e in entries:
        position = e.get("identity_position", "unknown")
        positions[position]["submissions"] += 1
        if e.get("outcome") == "accepted":
            positions[position]["conversions"] += 1
    
    position_rates = {
        pos: round(data["conversions"] / data["submissions"], 3) if data["submissions"] > 0 else 0
        for pos, data in positions.items()
    }
    
    # By channel
    channels = defaultdict(lambda: {"submissions": 0, "conversions": 0})
    for e in entries:
        if isinstance(e.get("target"), dict):
            channel = (e.get("target") or {}).get("portal", "unknown")
        else:
            channel = e.get("portal", "unknown")
        channels[channel]["submissions"] += 1
        if e.get("outcome") == "accepted":
            channels[channel]["conversions"] += 1
    
    channel_rates = {
        ch: round(data["conversions"] / data["submissions"], 3) if data["submissions"] > 0 else 0
        for ch, data in channels.items()
    }
    
    return {
        "total_submissions": total,
        "conversions": conversions,
        "conversion_rate": round(conversions / total, 3) if total > 0 else 0.0,
        "by_outcome": dict(outcomes),
        "by_composition_method": {
            method: {
                "submissions": data["submissions"],
                "conversions": data["conversions"],
                "rate": method_rates[method]
            }
            for method, data in methods.items()
        },
        "by_position": {
            pos: {
                "submissions": data["submissions"],
                "conversions": data["conversions"],
                "rate": position_rates[pos]
            }
            for pos, data in positions.items()
        },
        "by_channel": {
            ch: {
                "submissions": data["submissions"],
                "conversions": data["conversions"],
                "rate": channel_rates[ch]
            }
            for ch, data in channels.items()
        },
    }


def calculate_hypothesis_accuracy(hypotheses: list[dict]) -> dict:
    """Calculate how accurately hypotheses predicted outcomes."""
    validated = [h for h in hypotheses if h.get("actual_outcome")]
    if not validated:
        return {"accuracy": 0.0, "total": 0, "correct": 0}
    
    correct = sum(
        1 for h in validated
        if h.get("predicted_outcome") == h.get("actual_outcome")
    )
    
    return {
        "accuracy": round(correct / len(validated), 3),
        "total": len(validated),
        "correct": correct,
    }


def generate_report(entries: list[dict], hypotheses: list[dict], months: int = 1) -> str:
    """Generate markdown velocity report."""
    filtered_entries = filter_by_date_range(entries, months)
    metrics = calculate_metrics(filtered_entries)
    hyp_accuracy = calculate_hypothesis_accuracy(hypotheses)
    
    report = []
    report.append("# Monthly Velocity Report")
    report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append(f"Period: Last {months} month(s)")
    report.append("")
    
    # Summary
    report.append("## Summary")
    report.append(f"- **Submissions:** {metrics['total_submissions']}")
    report.append(f"- **Conversions:** {metrics['conversions']}")
    report.append(f"- **Conversion Rate:** {metrics['conversion_rate']*100:.1f}%")
    report.append("")
    
    # By Outcome
    report.append("## Outcome Distribution")
    for outcome, count in sorted(metrics["by_outcome"].items(), key=lambda x: x[1], reverse=True):
        pct = round(count / metrics["total_submissions"] * 100, 1) if metrics["total_submissions"] > 0 else 0
        report.append(f"- **{outcome}:** {count} ({pct}%)")
    report.append("")
    
    # By Composition Method
    report.append("## Composition Method Performance")
    for method, data in sorted(metrics["by_composition_method"].items(), key=lambda x: x[1].get("rate", 0), reverse=True):
        report.append(f"- **{method}:**")
        report.append(f"  - Submissions: {data['submissions']}")
        report.append(f"  - Conversions: {data['conversions']}")
        report.append(f"  - Rate: {data['rate']*100:.1f}%")
    report.append("")
    
    # By Identity Position
    report.append("## Performance by Identity Position")
    for pos, data in sorted(metrics["by_position"].items(), key=lambda x: x[1].get("rate", 0), reverse=True):
        report.append(f"- **{pos}:**")
        report.append(f"  - Submissions: {data['submissions']}")
        report.append(f"  - Conversions: {data['conversions']}")
        report.append(f"  - Rate: {data['rate']*100:.1f}%")
    report.append("")
    
    # By Channel
    report.append("## Performance by Channel")
    for channel, data in sorted(metrics["by_channel"].items(), key=lambda x: x[1].get("rate", 0), reverse=True):
        report.append(f"- **{channel}:**")
        report.append(f"  - Submissions: {data['submissions']}")
        report.append(f"  - Conversions: {data['conversions']}")
        report.append(f"  - Rate: {data['rate']*100:.1f}%")
    report.append("")
    
    # Hypothesis Accuracy
    report.append("## Hypothesis Validation")
    report.append(f"- **Total Validated:** {hyp_accuracy['total']}")
    report.append(f"- **Correct Predictions:** {hyp_accuracy['correct']}")
    report.append(f"- **Accuracy:** {hyp_accuracy['accuracy']*100:.1f}%")
    report.append("")
    
    return "\n".join(report)


def main():
    parser = argparse.ArgumentParser(description="Generate monthly velocity report")
    parser.add_argument("--month", type=int, default=1, help="Months to analyze (default: 1)")
    parser.add_argument("--save", action="store_true", help="Save report to strategy/velocity-report.md")
    args = parser.parse_args()
    
    entries = load_conversion_log()
    hypotheses = load_hypotheses()
    
    report = generate_report(entries, hypotheses, months=args.month)
    
    print(report)
    
    if args.save:
        report_path = Path("strategy/velocity-report.md")
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(report)
        print(f"\n✓ Report saved: {report_path}")


if __name__ == "__main__":
    main()
