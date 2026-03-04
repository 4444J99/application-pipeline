#!/usr/bin/env python3
"""Outcome risk model for pre-submit screening.

Trains a lightweight Naive Bayes model on historical entries with outcomes,
then estimates submission risk for a target entry.

Usage:
    python scripts/outcome_risk.py --target anthropic-software-engineer-agent-sdk-claude-code
    python scripts/outcome_risk.py --report
"""

from __future__ import annotations

import argparse
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pipeline_lib import PIPELINE_DIR_CLOSED, PIPELINE_DIR_SUBMITTED, load_entries, load_entry_by_id

SUCCESS_OUTCOMES = {"accepted"}
FAIL_OUTCOMES = {"rejected", "withdrawn", "expired"}
MIN_TRAINING_SAMPLES = 8


def _bucket_score(raw_score: float | int | None) -> str:
    if raw_score is None:
        return "unknown"
    try:
        score = float(raw_score)
    except (TypeError, ValueError):
        return "unknown"
    if score >= 8.0:
        return "high"
    if score >= 6.5:
        return "medium"
    return "low"


def _feature_map(entry: dict) -> dict[str, str]:
    fit = entry.get("fit", {}) if isinstance(entry.get("fit"), dict) else {}
    target = entry.get("target", {}) if isinstance(entry.get("target"), dict) else {}
    submission = entry.get("submission", {}) if isinstance(entry.get("submission"), dict) else {}

    variant_ids = submission.get("variant_ids", {}) if isinstance(submission.get("variant_ids"), dict) else {}
    portal_fields = entry.get("portal_fields", {}) if isinstance(entry.get("portal_fields"), dict) else {}
    status_meta = entry.get("status_meta", {}) if isinstance(entry.get("status_meta"), dict) else {}

    return {
        "track": str(entry.get("track", "unknown")),
        "identity_position": str(fit.get("identity_position", "unknown")),
        "portal": str(target.get("portal", "unknown")),
        "effort_level": str(submission.get("effort_level", "unknown")),
        "score_band": _bucket_score(fit.get("score")),
        "has_cover_letter": "yes" if bool(variant_ids.get("cover_letter")) else "no",
        "has_portal_fields": "yes" if bool(portal_fields.get("fields")) else "no",
        "reviewed": "yes" if bool(status_meta.get("reviewed_by")) else "no",
    }


def _label_from_outcome(outcome: str | None) -> int | None:
    if outcome in SUCCESS_OUTCOMES:
        return 1
    if outcome in FAIL_OUTCOMES:
        return 0
    return None


def collect_training_rows() -> list[tuple[dict[str, str], int]]:
    entries = load_entries(dirs=[PIPELINE_DIR_CLOSED, PIPELINE_DIR_SUBMITTED])
    rows: list[tuple[dict[str, str], int]] = []
    for entry in entries:
        label = _label_from_outcome(entry.get("outcome"))
        if label is None:
            continue
        rows.append((_feature_map(entry), label))
    return rows


def train_model(rows: list[tuple[dict[str, str], int]]) -> dict:
    label_counts = Counter()
    feature_counts: dict[str, dict[int, Counter[str]]] = defaultdict(lambda: {0: Counter(), 1: Counter()})
    feature_vocab: dict[str, set[str]] = defaultdict(set)

    for features, label in rows:
        label_counts[label] += 1
        for fname, fval in features.items():
            feature_counts[fname][label][fval] += 1
            feature_vocab[fname].add(fval)

    total = label_counts[0] + label_counts[1]
    prior_success = (label_counts[1] + 1) / (total + 2) if total else 0.5

    return {
        "total": total,
        "label_counts": label_counts,
        "feature_counts": feature_counts,
        "feature_vocab": feature_vocab,
        "prior_success": prior_success,
    }


def predict_success_probability(entry: dict, model: dict) -> dict:
    features = _feature_map(entry)
    total = int(model.get("total", 0))
    if total < MIN_TRAINING_SAMPLES:
        return {
            "available": False,
            "reason": f"insufficient training data ({total} < {MIN_TRAINING_SAMPLES})",
            "success_probability": None,
            "risk": None,
            "confidence": "low",
            "samples": total,
        }

    label_counts = model["label_counts"]
    feature_counts = model["feature_counts"]
    feature_vocab = model["feature_vocab"]

    # log-space Naive Bayes
    p1 = (label_counts[1] + 1) / (total + 2)
    p0 = (label_counts[0] + 1) / (total + 2)
    log_p1 = math.log(p1)
    log_p0 = math.log(p0)

    for fname, fval in features.items():
        vocab_n = max(1, len(feature_vocab.get(fname, set())))
        c1 = feature_counts[fname][1][fval]
        c0 = feature_counts[fname][0][fval]
        n1 = label_counts[1]
        n0 = label_counts[0]

        # Laplace smoothing per feature vocabulary size
        log_p1 += math.log((c1 + 1) / (n1 + vocab_n))
        log_p0 += math.log((c0 + 1) / (n0 + vocab_n))

    max_log = max(log_p1, log_p0)
    exp1 = math.exp(log_p1 - max_log)
    exp0 = math.exp(log_p0 - max_log)
    success_prob = exp1 / (exp1 + exp0)

    if total >= 40:
        confidence = "high"
    elif total >= 20:
        confidence = "medium"
    else:
        confidence = "low"

    return {
        "available": True,
        "reason": "",
        "success_probability": success_prob,
        "risk": 1.0 - success_prob,
        "confidence": confidence,
        "samples": total,
        "features": features,
    }


def predict_submission_risk(entry: dict) -> dict:
    rows = collect_training_rows()
    model = train_model(rows)
    return predict_success_probability(entry, model)


def _format_prediction(entry_id: str, prediction: dict) -> str:
    lines = [f"OUTCOME RISK — {entry_id}", "=" * 60]
    if not prediction.get("available"):
        lines.append(f"Model unavailable: {prediction.get('reason', 'unknown')}")
        return "\n".join(lines)

    success = prediction["success_probability"]
    risk = prediction["risk"]
    lines.append(f"Samples: {prediction['samples']} ({prediction['confidence']} confidence)")
    lines.append(f"Success probability: {success:.1%}")
    lines.append(f"Submission risk:    {risk:.1%}")

    if risk >= 0.70:
        lines.append("Risk tier: HIGH")
    elif risk >= 0.50:
        lines.append("Risk tier: MODERATE")
    else:
        lines.append("Risk tier: LOW")

    lines.append("\nFeatures:")
    for k, v in sorted(prediction.get("features", {}).items()):
        lines.append(f"  {k}: {v}")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Predict outcome risk for a pipeline entry")
    parser.add_argument("--target", help="Entry ID to score")
    parser.add_argument("--report", action="store_true", help="Print model data availability")
    args = parser.parse_args()

    rows = collect_training_rows()
    model = train_model(rows)

    if args.report:
        total = model.get("total", 0)
        print("OUTCOME RISK MODEL")
        print("=" * 60)
        print(f"Training rows: {total}")
        print(f"Success labels: {model['label_counts'][1]}")
        print(f"Failure labels: {model['label_counts'][0]}")
        print(f"Ready: {'yes' if total >= MIN_TRAINING_SAMPLES else 'no'}")
        return

    if not args.target:
        parser.error("Specify --target <entry-id> or --report")

    _, entry = load_entry_by_id(args.target)
    if not entry:
        print(f"Entry not found: {args.target}", file=sys.stderr)
        raise SystemExit(1)

    prediction = predict_success_probability(entry, model)
    print(_format_prediction(args.target, prediction))


if __name__ == "__main__":
    main()
